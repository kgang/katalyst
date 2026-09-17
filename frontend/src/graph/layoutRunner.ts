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
  type Position,
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

  // Where tiles already sit. Held across runs, because that is what pinning
  // means: this is the memory that stops a late arrival moving an early one.
  const placed = useRef(new Map<string, Position>());
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
    const graph = toElkGraph(
      boxes.map(([id, height]) => ({ id, height })),
      wires.map(([id, source, target]) => ({ id, source, target })),
      placed.current,
    );
    layoutEngine()
      .layout(graph)
      .then(
        (laidOut) => {
          if (!stillWanted) {
            return;
          }
          const positions = readPositions(laidOut, placed.current);
          placed.current = positions;
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
