/**
 * What the map draws while the layout is still thinking.
 *
 * The layout runs on a background thread and answers later, so there is always a
 * window in which the map holds boxes nobody has found a place for. On this
 * machine that window is shorter than a frame and nobody ever sees it. On a
 * slower one it is long enough to read — and what is drawn in it is the whole of
 * what this file is about.
 *
 * **The window that matters is the first one**, because it is the only one in
 * which the layout has placed *nothing at all*. `useLayout` throws away an answer
 * whose map has changed underneath it, so when the first claim arrives before the
 * first answer has landed, that answer is discarded and the map has no places for
 * anything. Continuous integration found it on 2026-09-21: `heldWhenEachClaimArrived`
 * opened with a zero, meaning a claim stood on the glass with no reserved rectangle
 * anywhere — a growing map that had stopped saying where it was going.
 *
 * So the walk below is the worked run on that machine: the layout's first answer
 * loses the race to the first proposal, and from then on it keeps up. The layout
 * engine is run for real, in this process, because the places are the thing being
 * compared against and a stand-in would compare nothing.
 */

import ELK from "elkjs/lib/elk.bundled.js";
import { describe, expect, it } from "vitest";
import { A_REAL_RUN, THE_REAL_SENTENCE } from "../../stream/__tests__/aRealRun";
import { BELIEFS, THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import type { StreamEvent } from "../../stream/events";
import { fold, type Growth, waitingFor } from "../../stream/growth";
import {
  type LayoutEdge,
  type PinnedTile,
  type Position,
  pinsFor,
  readPositions,
  toElkGraph,
} from "../elkGraph";
import { type OnTheGlass, type PlacedBox, THE_ORIGIN, whatIsOnTheGlass } from "../onTheGlass";
import { toFlow } from "../toFlow";

const engine = new ELK();

/** Lay a map out and read the answer back, exactly as the page does. */
async function layout(
  tiles: readonly (readonly [string, number])[],
  edges: readonly LayoutEdge[],
  placed: ReadonlyMap<string, Position>,
): Promise<Map<string, Position>> {
  const laidOut = await engine.layout(
    toElkGraph(
      tiles.map(([id, height]) => ({ id, height })),
      edges,
      placed,
    ),
  );
  return readPositions(laidOut, placed);
}

/** One moment of a run: what was drawn, and what the layout had said by then. */
interface Frame {
  /** What the map had on the glass at that moment. */
  readonly glass: OnTheGlass;
  /** Where the layout had placed things when it was drawn. Empty until it answers. */
  readonly places: ReadonlyMap<string, Position>;
  /** Everything the screen knew, so a test can ask whether the map is finished. */
  readonly growth: Growth;
  /**
   * True when the layout had caught up with the map by then.
   *
   * Every event paints twice: once the instant it lands, with the places worked
   * out for the map before it, and once when the layout answers a moment later.
   * A reader spends almost all of a run looking at the second kind.
   */
  readonly settled: boolean;
}

/** The claims drawn at that moment. */
function claims(frame: Frame) {
  return frame.glass.boxes.filter((box) => box.type === "claim");
}

/** The reserved rectangles drawn at that moment. */
function rectangles(frame: Frame) {
  return frame.glass.boxes.filter((box) => box.type === "skeleton");
}

/**
 * Walk a stream on a machine where the layout's first answer is late.
 *
 * **Every event paints twice.** The instant it lands, the map is drawn with the
 * places worked out for the map *before* it — the layout has not been asked yet.
 * A moment later the layout answers and it is drawn again. Both are frames a
 * reader can see, and the first is the one nobody thinks about.
 *
 * **And the very first answer is thrown away.** `useLayout` discards an answer
 * whose map changed underneath it, so a first claim that arrives before the
 * layout has finished placing the first rectangle leaves the map with no places
 * for anything at all. That is the window continuous integration found, and the
 * rest of this walk is a machine fast enough to win every race after it.
 *
 * @param events The stream to walk.
 * @param typed The sentence the reader typed, which the first rectangle carries.
 */
async function theFirstAnswerIsLate(
  events: readonly StreamEvent[],
  typed: string,
): Promise<Frame[]> {
  const frames: Frame[] = [];
  let growth = waitingFor(typed, null);
  let standing: readonly PlacedBox[] = [];
  let places = new Map<string, Position>();
  let pinned = new Map<string, PinnedTile>();
  let thrownAway = false;

  for (const event of events) {
    growth = fold(growth, event);
    const drawing = toFlow(growth.world, undefined, growth.skeletons);
    const whenItLanded = whatIsOnTheGlass(drawing.nodes, places, standing);
    standing = whenItLanded.rectangles;
    frames.push({ glass: whenItLanded, places, growth, settled: false });

    if (!thrownAway) {
      // The first answer, lost to the first proposal. Nothing is placed and
      // nothing is pinned, because nothing was ever read back.
      thrownAway = true;
      continue;
    }
    const heights = new Map(drawing.tiles.map((tile) => [tile.id, tile.height]));
    places = await layout(
      drawing.tiles.map((tile) => [tile.id, tile.height] as const),
      drawing.layoutEdges,
      pinsFor(pinned, drawing.tiles),
    );
    pinned = new Map([...places].map(([id, at]) => [id, { at, height: heights.get(id) ?? 0 }]));

    const whenTheLayoutAnswered = whatIsOnTheGlass(drawing.nodes, places, standing);
    standing = whenTheLayoutAnswered.rectangles;
    frames.push({ glass: whenTheLayoutAnswered, places, growth, settled: true });
  }
  return frames;
}

/** The two runs every statement below is checked on, with the sentence each began from. */
const BOTH_RUNS: readonly (readonly [string, readonly StreamEvent[], string])[] = [
  ["the chapter's worked run", [...THE_GROWTH, BELIEFS], THE_SENTENCE],
  ["a real ten-claim run", A_REAL_RUN as readonly StreamEvent[], THE_REAL_SENTENCE],
];

describe("what the map draws while the layout is still thinking", () => {
  it("test_a_rectangle_stands_at_every_moment_the_map_is_still_growing", async () => {
    // **The growing edge never stops saying where the map is going.** A map with
    // claims still to come and no rectangle anywhere has gone quiet about its
    // own future — and that is what a reader on a slow machine met three times
    // in a ten-claim run: once when the very first claim landed, and again at
    // each turnover of a frontier that is one claim wide.
    //
    // The finished map is the exception and the only one: the set of claims
    // still open is empty once the likelihoods have been worked through, so no
    // rectangle may stand.
    for (const [which, events, typed] of BOTH_RUNS) {
      for (const [step, frame] of (await theFirstAnswerIsLate(events, typed)).entries()) {
        if (frame.growth.skeletons.length === 0) {
          continue;
        }
        expect(rectangles(frame).length, `${which}, after event ${step}`).toBeGreaterThan(0);
      }
    }
  });

  it("test_no_rectangle_stands_once_nothing_more_is_coming", async () => {
    // The other half of the same rule, and the reason holding one back cannot
    // become a way of leaving one up. A rectangle is a promise that a claim is
    // on its way; once the map is whole and the stream has said no claim is —
    // the likelihoods landing, a run breaking, a claim closed by its third
    // refusal — every rectangle is gone, including any that were being held.
    for (const [which, events, typed] of BOTH_RUNS) {
      for (const [step, frame] of (await theFirstAnswerIsLate(events, typed)).entries()) {
        if (!frame.settled || frame.growth.skeletons.length > 0) {
          continue;
        }
        expect(rectangles(frame), `${which}, after event ${step}`).toEqual([]);
      }
    }
  });

  it("test_a_claim_is_only_ever_drawn_where_the_layout_put_it", async () => {
    // A box the layout has not placed has no place, and drawing it at the map's
    // origin gives it one the layout never agreed to: the claim appears at the
    // origin and then hops to wherever the layout actually wanted it. Nothing
    // already on screen may move (INV-workbench.64, the promise that a late
    // arrival never shoves an early one), and a box that was never placed moving
    // is that promise broken on the very first tile.
    for (const [which, events, typed] of BOTH_RUNS) {
      for (const [step, frame] of (await theFirstAnswerIsLate(events, typed)).entries()) {
        for (const claim of claims(frame)) {
          expect(frame.places.get(claim.id), `${which}, ${claim.id} after event ${step}`).toEqual(
            claim.position,
          );
        }
      }
    }
  });

  it("test_the_first_rectangle_keeps_the_readers_own_words_until_the_layout_answers", async () => {
    // The one box the map places by itself carries the reader's own sentence,
    // and it goes on carrying it for as long as it stands. Handing the origin to
    // the next rectangle instead would quote a claim that is not on the map yet;
    // handing it to the claim is what put a claim on the glass with nothing
    // beside it.
    for (const [which, events, typed] of BOTH_RUNS) {
      for (const [step, frame] of (await theFirstAnswerIsLate(events, typed)).entries()) {
        if (frame.places.size > 0) {
          continue;
        }
        for (const box of frame.glass.boxes) {
          expect(box.position, `${which}, after event ${step}`).toEqual(THE_ORIGIN);
          expect(box.type, `${which}, after event ${step}`).toBe("skeleton");
          expect(box.data, `${which}, after event ${step}`).toEqual({ words: typed });
        }
      }
    }
  });

  it("test_no_two_boxes_are_ever_drawn_in_one_place", async () => {
    // The place two boxes would share is the map's origin, which is the only
    // place anything here puts a box without being told to.
    for (const [which, events, typed] of BOTH_RUNS) {
      for (const [step, frame] of (await theFirstAnswerIsLate(events, typed)).entries()) {
        const places = frame.glass.boxes.map((box) => `${box.position.x},${box.position.y}`);
        expect(new Set(places).size, `${which}, after event ${step}`).toBe(places.length);
      }
    }
  });

  it("test_a_map_the_layout_has_answered_for_is_drawn_exactly_as_it_was_placed", async () => {
    // Nothing above changes what a finished map looks like: once the layout has
    // spoken, every box it placed is drawn where it put it, every box it has not
    // placed is not drawn, and the map is holding nothing of its own.
    const growth = [...THE_GROWTH, BELIEFS].reduce(fold, waitingFor(THE_SENTENCE, null));
    const drawing = toFlow(growth.world, undefined, growth.skeletons);
    const places = await layout(
      drawing.tiles.map((tile) => [tile.id, tile.height] as const),
      drawing.layoutEdges,
      new Map(),
    );
    const glass = whatIsOnTheGlass(drawing.nodes, places, []);
    expect(glass.rectangles).toEqual([]);
    expect(glass.boxes.map((box) => box.id)).toEqual(drawing.nodes.map((node) => node.id));
    for (const box of glass.boxes) {
      expect(box.position).toEqual(places.get(box.id));
    }
  });
});
