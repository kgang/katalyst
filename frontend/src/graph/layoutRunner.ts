/**
 * Working out where every tile goes, on a thread that is not the one drawing
 * the page.
 *
 * Laying out a map of sixty tiles takes the layout engine somewhere between
 * fifty and a hundred and fifty milliseconds. On the thread that draws the page
 * that is three to nine dropped frames: the page freezes, the map stutters as it
 * grows, and a tool that stutters reads as a tool that is struggling. So the
 * work happens on a background thread, and the page carries on drawing while it
 * waits.
 *
 * The background thread is the layout engine's own. Its package ships the
 * algorithm as a script written to be run that way — ask it for a copy of that
 * script's address and hand the address over, and it starts the thread itself.
 * Writing our own wrapper thread around it, which was the first attempt, does
 * not work: the script checks whether it is already inside a background thread
 * and, finding that it is, wires itself up as that thread rather than handing
 * back something to call.
 *
 * Nothing on this thread ever sees a likelihood. A tile, to the layout engine,
 * is an identifier and a box.
 */

import ELK, { type ELK as LayoutEngine } from "elkjs/lib/elk-api.js";
import elkWorkerAddress from "elkjs/lib/elk-worker.min.js?url";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  type LayoutEdge,
  type LayoutTile,
  type PinnedTile,
  type Position,
  pinsFor,
  readPositions,
  toElkGraph,
} from "./elkGraph";

/** Where every tile sits, and which run of the layout put it there. */
export interface Layout {
  /** Where each tile sits, by identifier. Empty until the first answer arrives. */
  readonly positions: ReadonlyMap<string, Position>;
  /**
   * How many layouts have finished.
   *
   * Zero means none has, and so nothing should be drawn yet. It goes up by one
   * each time, which is what lets the canvas tell "the map has just been laid
   * out for the first time" — frame the whole map — from "it has been laid out
   * again" — stay where the reader was.
   */
  readonly runs: number;
  /**
   * Which map these positions are for.
   *
   * It lags the map on screen by exactly as long as the layout takes, and that
   * matters: framing the view from positions worked out for the map *before* the
   * branch would frame the wrong thing, and then the right thing would arrive
   * underneath it.
   */
  readonly laidOutFor: string;
  /** What went wrong, in a sentence, if anything did. */
  readonly failure: string | null;
}

/**
 * One background thread, shared by everything on the page that needs a layout.
 *
 * Started the first time it is asked for rather than when this file loads,
 * because a test running in a simulated page has no threads to start and should
 * not have one started for it.
 */
let engine: LayoutEngine | null = null;

function layoutEngine(): LayoutEngine {
  engine ??= new ELK({ workerUrl: elkWorkerAddress });
  return engine;
}

/**
 * How long the background thread gets before the page does the work itself.
 *
 * The background thread is the normal path and it answers in well under a tenth
 * of a second. But a thread that never answers leaves every tile stacked in the
 * top left corner with nothing on screen saying why — which is the "why did it
 * do that" failure in its purest form. Some browsers, and some browsers under
 * instrumentation, will not run the layout engine's own worker script at all.
 *
 * So after this long the page lays the map out on its own thread instead. That
 * costs a few dropped frames once; a map that never arrives costs everything.
 */
const THREAD_PATIENCE = 2000;

/** What the race below hands back when the background thread has not answered. */
const TOO_SLOW = Symbol("the background thread has not answered");

/**
 * Lay the map out on the background thread, or — if that thread does not answer
 * — on this one.
 *
 * The fallback is loaded only if it is needed, so the packaged app does not
 * carry a second copy of the layout engine unless a reader's browser makes it
 * necessary.
 */
async function laidOut(graph: Parameters<LayoutEngine["layout"]>[0]) {
  const answer = await Promise.race([
    layoutEngine().layout(graph),
    new Promise<typeof TOO_SLOW>((settle) => {
      setTimeout(() => settle(TOO_SLOW), THREAD_PATIENCE);
    }),
  ]);
  if (answer !== TOO_SLOW) {
    return answer;
  }
  const onThisThread = await import("elkjs/lib/elk.bundled.js");
  return new onThisThread.default().layout(graph);
}

/** Say what went wrong in a sentence, whatever was thrown. */
function inWords(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The layout engine stopped without saying why.";
}

/**
 * Work out where every tile goes, on a background thread, and keep tiles that
 * have already been placed exactly where they are.
 *
 * @param tiles Every tile to place, with its height, in reading order.
 * @param edges Every arrow that gets a say in the left-to-right order. Feedback
 *   arrows are left out by the caller.
 * @param mapKey Which map this is. Pinning is for a map that **grows** — a tile
 *   arriving must never shove the tiles already on screen. A different map is a
 *   different question: opening a branch that adds a claim before the hypothesis
 *   moves every column one step right, and it has to, because a cause cannot be
 *   drawn to the right of what it causes. So when this changes, the pins go and
 *   the whole thing is laid out again, once, over the union of both worlds.
 *
 * **The pins also go when the map keeps its shape but a box changes size.**
 * The layout is handed a height per tile and the reader sees a tile of that
 * height, and the two have to be the same box — that is what `geometry.ts` means
 * by content-fit. A pin made for a shorter box no longer describes anything, so
 * the whole map is laid out again; see `pinsFor` for why it is all or none.
 */
export function useLayout(
  tiles: readonly LayoutTile[],
  edges: readonly LayoutEdge[],
  mapKey: string,
): Layout {
  // The map only changes when the claims or the arrows do, and comparing two
  // lists of strings is cheaper and steadier than comparing two arrays by
  // identity — a fresh array with the same contents must not start a re-layout.
  const shape = useMemo(
    () =>
      JSON.stringify([
        tiles.map((tile) => [tile.id, tile.height]),
        edges.map((edge) => [edge.id, edge.source, edge.target]),
      ]),
    [tiles, edges],
  );

  // Where tiles already sit, and how tall they were when they were put there.
  // Held across runs, because that is what pinning means: this is the memory
  // that stops a late arrival moving an early one. The height is kept with the
  // place because a pin is only good for the size it was made at — see
  // `pinsThatStillHold`.
  const placed = useRef(new Map<string, PinnedTile>());
  const laidOutFor = useRef(mapKey);
  const [layout, setLayout] = useState<Layout>({
    positions: new Map(),
    runs: 0,
    laidOutFor: "",
    failure: null,
  });

  useEffect(() => {
    let stillWanted = true;
    if (laidOutFor.current !== mapKey) {
      // A different map. Nothing is pinned, because the columns themselves have
      // moved: the union of two worlds is laid out once, together, and then
      // painted twice in those same coordinates.
      placed.current = new Map();
      laidOutFor.current = mapKey;
    }
    const [boxes, wires] = JSON.parse(shape) as [[string, number][], [string, string, string][]];
    const tiles: LayoutTile[] = boxes.map(([id, height]) => ({ id, height }));
    // The pins to hold — all of them, or none. A map whose boxes have changed
    // size is laid out again from scratch: holding a grown tile where its
    // shorter self went runs it into whatever sits below.
    const holding = pinsFor(placed.current, tiles);
    const graph = toElkGraph(
      tiles,
      wires.map(([id, source, target]) => ({ id, source, target })),
      holding,
    );
    laidOut(graph).then(
      (laidOut) => {
        if (!stillWanted) {
          return;
        }
        const positions = readPositions(laidOut, holding);
        const heights = new Map(tiles.map((tile) => [tile.id, tile.height]));
        placed.current = new Map(
          [...positions].map(([id, at]) => [id, { at, height: heights.get(id) ?? 0 }]),
        );
        setLayout((was) => ({
          positions,
          runs: was.runs + 1,
          laidOutFor: mapKey,
          failure: null,
        }));
      },
      (reason: unknown) => {
        if (stillWanted) {
          setLayout((was) => ({ ...was, failure: inWords(reason) }));
        }
      },
    );
    return () => {
      stillWanted = false;
    };
  }, [shape, mapKey]);

  return layout;
}
