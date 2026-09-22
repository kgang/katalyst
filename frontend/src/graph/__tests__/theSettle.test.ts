/**
 * When a tile may move, checked on two real streams and no browser.
 *
 * **The rule, in Kent's decision (record 0024):** a tile moves only when an
 * arrow would otherwise point backwards, and once when the run stops. In three
 * clauses a test can hold:
 *
 * 1. a tile keeps its **row** — its vertical place and its order within its
 *    column — for as long as the map is growing, unless the arrows send it into
 *    a column where that row is taken, and then it takes the nearest free row;
 * 2. a tile's **column** is re-read from the arrows on every pass, so no arrow
 *    points backwards at any moment;
 * 3. when the run stops, every pin is dropped and the map is laid out once,
 *    whole — the one moment a row may change.
 *
 * **Why two streams and not one made up here.** The defect Kent saw exists only
 * on a map built through the Verify door, where the destination claim arrives
 * second with nothing pointing at it yet. The one stream this repository already
 * held is an Explore run with no such claim, so on it nothing points backwards
 * and the rule proves nothing. Both are walked: the committed recording, because
 * it is the long map (eighteen claims, four columns), and one live Verify run
 * kept as a fixture beside this file, because it is the map with the defect on
 * it — three of its nine arrows were drawn pointing backwards before this rule.
 *
 * **Nothing here is reimplemented.** Each stream is folded through the real
 * `growth` reducer, handed to the real `toFlow`, pinned by the real `pinsFor`,
 * laid out by the real layout engine with the app's own options, and read back
 * by the real `readPositions` — the same five steps `useLayout` takes, in the
 * same order, on every arrival. The layout engine runs in this process rather
 * than on a background thread, because the settings are part of what is being
 * tested.
 *
 * **No number in this file was typed in.** Every statement is a direction (this
 * arrow points right), an ordering (this box sits above that one) or a value
 * compared with itself across a change (this tile's row now against its row
 * before).
 */

import { readFileSync } from "node:fs";
import ELK from "elkjs/lib/elk.bundled.js";
import { describe, expect, it } from "vitest";
import type { StreamEvent } from "../../stream/events";
import { fold, hasStopped, waitingFor } from "../../stream/growth";
import {
  COLUMN_GAP,
  type PinnedTile,
  type Position,
  pinsFor,
  readPositions,
  toElkGraph,
} from "../elkGraph";
import { TILE_WIDTH } from "../geometry";
import { toFlow } from "../toFlow";
import { A_LIVE_VERIFY_RUN } from "./fixtures/aLiveVerifyRun";

const engine = new ELK();

/**
 * The committed recording's events, read off the very file the server replays.
 *
 * Its first line is the recording's own header and carries no event; every line
 * after it is one event, as the wire writes it — a name and a payload, which the
 * reader of a live stream joins into one object in exactly this way.
 */
function theCommittedRecording(): StreamEvent[] {
  const lines = readFileSync("../backend/recordings/hormuz.jsonl", "utf8")
    .split("\n")
    .filter((line) => line.trim() !== "");
  const events: StreamEvent[] = [];
  for (const line of lines) {
    const parsed = JSON.parse(line) as { event?: string; data?: unknown };
    if (parsed.event === undefined) {
      continue;
    }
    events.push({ event: parsed.event, ...(parsed.data as object) } as StreamEvent);
  }
  return events;
}

/** One box on the map: where it is and how tall it turned out. */
interface Box {
  readonly at: Position;
  readonly height: number;
}

/** One arrow a reader can see, reduced to the two ends the picture is about. */
interface Arrow {
  readonly source: string;
  readonly target: string;
  readonly words: string;
}

/** The map as it stood after one event had been folded in. */
interface Frame {
  /** Where every box sits, reserved rectangles included. */
  readonly boxes: ReadonlyMap<string, Box>;
  /** Every arrow drawn between two claims. Feedback arrows are left out. */
  readonly arrows: readonly Arrow[];
  /** True once the run has stopped, by the same question every screen asks. */
  readonly stopped: boolean;
}

/**
 * Walk a stream the way the page walks it, and hand back the map after every
 * single event.
 *
 * One event is folded, the reducer's world and its reserved rectangles go to
 * `toFlow`, the pins that still hold are worked out, the layout engine is asked,
 * and its answer is read back. That is the page's own loop, and the settle is
 * the page's own settle: the pass on which the run stops drops every pin, which
 * is the one thing `useLayout` does that this walk has to say out loud, because
 * on the page it is driven by the same flag that re-frames the view.
 */
async function everyFrameOf(events: readonly StreamEvent[], landsEvery = 1): Promise<Frame[]> {
  const frames: Frame[] = [];
  let growth = waitingFor("the sentence this run was started from", null);
  let pinned = new Map<string, PinnedTile>();
  let settled = false;

  for (const [step, event] of events.entries()) {
    growth = fold(growth, event);
    const drawing = toFlow(growth.world, undefined, growth.skeletons);
    const stopped = hasStopped(growth.phase);
    // **A late layout thread, injected.** The layout runs off the page's thread
    // and `useLayout` throws away an answer a newer one has overtaken, so on a
    // slow machine most passes never land and the one that does covers several
    // events at once. `landsEvery` is how many events one landed pass covers:
    // one is this machine, more is the build machine. The pass that stops the
    // run always lands, because the settle is not something a reader can miss.
    if (step % landsEvery !== landsEvery - 1 && step !== events.length - 1 && !stopped) {
      continue;
    }
    // The one pass where the run has just stopped is the settle: every pin goes
    // and the map is laid out once, whole. After it, the pins hold again and
    // nothing moves.
    const theRunHasJustStopped = stopped && !settled;
    settled = settled || stopped;

    const holding = pinsFor(pinned, drawing.tiles, theRunHasJustStopped);
    const laidOut = await engine.layout(toElkGraph(drawing.tiles, drawing.layoutEdges, holding));
    const positions = readPositions(laidOut, holding);

    const heights = new Map(drawing.tiles.map((tile) => [tile.id, tile.height]));
    pinned = new Map([...positions].map(([id, at]) => [id, { at, height: heights.get(id) ?? 0 }]));

    const boxes = new Map(
      [...positions].map(([id, at]) => [id, { at, height: heights.get(id) ?? 0 }]),
    );
    const words = new Map(growth.world.claims.map((claim) => [claim.id, claim.claim]));
    const arrows = growth.world.links
      .filter((link) => !link.reflexive && boxes.has(link.source) && boxes.has(link.target))
      .map((link) => ({
        source: link.source,
        target: link.target,
        words: `${words.get(link.source) ?? link.source} → ${words.get(link.target) ?? link.target}`,
      }));

    frames.push({ boxes, arrows, stopped });
  }
  return frames;
}

/**
 * Every arrow on this frame that points the wrong way, named in the claims' own
 * words so a failure says which argument was drawn backwards.
 *
 * An arrow points the right way when its target's box sits **strictly right** of
 * its source's. An arrow that ends in the same column as it starts is not a
 * picture of one thing causing another either, so it counts here too.
 */
function pointingBackwards(frame: Frame): string[] {
  const wrong: string[] = [];
  for (const arrow of frame.arrows) {
    const from = frame.boxes.get(arrow.source);
    const to = frame.boxes.get(arrow.target);
    if (from === undefined || to === undefined) {
      continue;
    }
    if (to.at.x <= from.at.x) {
      wrong.push(arrow.words);
    }
  }
  return wrong;
}

/** Every pair of boxes that are drawn on top of each other, or too close to be read apart. */
function collide(frame: Frame): string[] {
  const boxes = [...frame.boxes].map(([id, box]) => ({ id, ...box }));
  const clashes: string[] = [];
  for (let one = 0; one < boxes.length; one += 1) {
    for (let other = one + 1; other < boxes.length; other += 1) {
      const a = boxes[one] as (typeof boxes)[number];
      const b = boxes[other] as (typeof boxes)[number];
      const sameColumn = Math.abs(a.at.x - b.at.x) < TILE_WIDTH;
      const overlapping =
        a.at.y < b.at.y + b.height + COLUMN_GAP && b.at.y < a.at.y + a.height + COLUMN_GAP;
      if (sameColumn && overlapping) {
        clashes.push(`${a.id} and ${b.id}`);
      }
    }
  }
  return clashes;
}

/** The two real streams this rule is checked on, each with a name a failure can print. */
const THE_REAL_STREAMS: readonly (readonly [string, readonly StreamEvent[]])[] = [
  ["the live Verify run of 2026-09-21", A_LIVE_VERIFY_RUN],
  ["the committed Hormuz recording", theCommittedRecording()],
];

describe("no arrow points backwards", () => {
  it("test_no_arrow_points_backwards_at_any_moment", async () => {
    for (const [name, events] of THE_REAL_STREAMS) {
      const frames = await everyFrameOf(events);

      // The walk has to have drawn something, or everything below it is true of
      // nothing. Asserted rather than assumed.
      expect(frames.length, name).toBe(events.length);
      expect(
        frames.some((frame) => frame.arrows.length > 0),
        name,
      ).toBe(true);

      for (const [step, frame] of frames.entries()) {
        expect(pointingBackwards(frame), `${name}, after event ${step}`).toEqual([]);
      }
    }
  });

  it("test_no_arrow_points_backwards_once_the_run_has_stopped", async () => {
    for (const [name, events] of THE_REAL_STREAMS) {
      const frames = await everyFrameOf(events);
      const last = frames[frames.length - 1] as Frame;

      // The stream really did end in a stop, or this is a statement about a
      // run that was still going.
      expect(last.stopped, name).toBe(true);
      expect(last.arrows.length, name).toBeGreaterThan(0);
      expect(pointingBackwards(last), name).toEqual([]);
    }
  });

  it("test_the_verify_run_is_the_map_this_rule_was_written_for", async () => {
    // Without this, the two tests above could pass on a stream where the
    // destination never changed column — which is every stream this repository
    // held before the fixture arrived, and is why the defect went unseen. So:
    // on the live Verify run, a claim really does end further right than it was
    // first drawn, and it really does gain arrows from claims placed after it.
    const frames = await everyFrameOf(A_LIVE_VERIFY_RUN);

    const firstColumn = new Map<string, number>();
    const lastColumn = new Map<string, number>();
    for (const frame of frames) {
      for (const [id, box] of frame.boxes) {
        if (!firstColumn.has(id)) {
          firstColumn.set(id, box.at.x);
        }
        lastColumn.set(id, box.at.x);
      }
    }
    const movedRight = [...firstColumn].filter(
      ([id, first]) => (lastColumn.get(id) as number) > first,
    );
    expect(movedRight.length).toBeGreaterThan(0);
  });
});

describe("a tile keeps its row while the map grows", () => {
  it("test_a_tile_keeps_its_row_while_the_map_grows", async () => {
    // The half of the rule that stops all of this becoming *never pin
    // anything*: the reader's vertical scan of the map survives every arrival.
    // **A box that stays in the column it is in never moves a pixel**, and the
    // only box that ever takes a new row while the map is growing is one the
    // arrows have just sent into a different column where that row was already
    // taken — and then it takes the nearest free row, which the test below is
    // about. Measured, 2026-09-22: that happens once in the whole of the live
    // Verify run, by 48 pixels, and not at all on the committed recording. See
    // `readPositions` for why holding the row regardless was worse: on the
    // recording it drew one claim 140 pixels on top of another.
    for (const [name, events] of THE_REAL_STREAMS) {
      const frames = await everyFrameOf(events);
      const was = new Map<string, Position>();

      for (const [step, frame] of frames.entries()) {
        for (const [id, box] of frame.boxes) {
          const before = was.get(id);
          if (before !== undefined && !frame.stopped) {
            const where = `${name}, ${id}, after event ${step}`;
            if (box.at.x === before.x) {
              expect(box.at.y, `${where} — it did not change column`).toBe(before.y);
            } else {
              // It changed column, which is the only thing that may move it.
              expect(box.at.x, `${where} — a column is only ever read afresh`).toBeGreaterThan(
                before.x,
              );
            }
          }
          was.set(id, box.at);
        }
      }

      // And the walk really did put more than one box down, or nothing above
      // was checked.
      expect(was.size, name).toBeGreaterThan(1);
    }
  });

  it("test_a_tile_sent_into_a_taken_row_takes_the_nearest_free_row", async () => {
    // The second half of the rule, said as a statement about distance rather
    // than about a coordinate. **A box built on purpose**: it is pinned in one
    // column, this pass puts it in another, and the row it wants there is held
    // by a reserved rectangle whose own row leaves a free row a little way
    // **above** it and a long way below. The rule this replaced only ever slid
    // downwards, which on Kent's own Verify run sent the destination tile 392
    // pixels down past a free row 48 pixels up.
    const column = TILE_WIDTH + COLUMN_GAP;
    const standing = { id: "a rectangle already there", at: { x: column, y: 1000 }, height: 200 };
    const mover = { id: "the tile the arrows moved", height: 100 };

    // The two rows that clear the rectangle, worked out from its own box rather
    // than written down: just above it, and just below it.
    const above = standing.at.y - COLUMN_GAP - mover.height;
    const below = standing.at.y + standing.height + COLUMN_GAP;
    // A row inside the rectangle's own span, so it really is taken — and nearer
    // the row above than the row below.
    const wanted = standing.at.y + COLUMN_GAP;

    const answer = readPositions(
      {
        id: "map",
        children: [
          { id: standing.id, x: standing.at.x, y: standing.at.y, height: standing.height },
          // Wherever the engine would have put it. The row it keeps is its pin's.
          { id: mover.id, x: column, y: 0, height: mover.height },
        ],
      },
      new Map([
        [standing.id, standing.at],
        [mover.id, { x: 0, y: wanted }],
      ]),
    );
    const took = answer.get(mover.id) as Position;

    // It went to the free row nearer the one it wanted, which here is upwards,
    // and it is not the row the old rule would have sent it to.
    expect(took.x).toBe(column);
    expect(Math.abs(took.y - wanted)).toBeLessThan(Math.abs(below - wanted));
    expect(took.y).toBe(above);
    // And the rectangle did not move, and is not drawn over.
    expect(answer.get(standing.id)).toEqual(standing.at);
    expect(took.y + mover.height + COLUMN_GAP).toBeLessThanOrEqual(standing.at.y);
  });

  it("test_a_tie_between_two_free_rows_goes_down", async () => {
    // Reading order breaks the tie: of two free rows the same distance away, the
    // one further down the map is the one the reader's eye reaches later, so it
    // disturbs less of what they have already read.
    const column = TILE_WIDTH + COLUMN_GAP;
    const standing = { id: "a tile already there", at: { x: column, y: 1000 }, height: 200 };
    const mover = { id: "the tile the arrows moved", height: 100 };
    const above = standing.at.y - COLUMN_GAP - mover.height;
    const below = standing.at.y + standing.height + COLUMN_GAP;
    // Exactly between the two, so neither is nearer.
    const wanted = (above + below) / 2;

    const answer = readPositions(
      {
        id: "map",
        children: [
          { id: standing.id, x: standing.at.x, y: standing.at.y, height: standing.height },
          { id: mover.id, x: column, y: 0, height: mover.height },
        ],
      },
      new Map([
        [standing.id, standing.at],
        [mover.id, { x: 0, y: wanted }],
      ]),
    );
    const took = answer.get(mover.id) as Position;

    // The tie is a real tie, or this is testing the case above again.
    expect(Math.abs(above - wanted)).toBe(Math.abs(below - wanted));
    expect(took.y).toBe(below);
  });

  it("test_a_late_layout_thread_never_moves_a_tile_that_is_already_placed", async () => {
    // **The build machine's fault, injected here rather than waited for.** The
    // layout answers on a thread of its own, and on a slow machine most of its
    // answers are overtaken before they land — so one landed pass covers three,
    // five, a dozen events at once instead of one. That changes how much map
    // exists the first time anything is placed, and so where the first tile
    // lands: on the committed recording it is drawn at row 12 when the first
    // pass covers one event, 24 at three, 212 at four, 456 at twelve. **Every
    // one of those is the layout engine's own answer for the map it was given**,
    // and the thing this test exists to say is that none of them moves
    // afterwards: whatever row a tile is first given, it keeps, until the run
    // stops. Nine rates, both real streams, every event.
    //
    // It is the no-browser half of decision record 0008's tier 2, and it is the
    // twin of `e2e/lateLayout.spec.ts`, which starts the real thread 900
    // milliseconds late in a real browser.
    for (const [name, events] of THE_REAL_STREAMS) {
      for (const landsEvery of [1, 2, 3, 4, 5, 6, 7, 9, 12]) {
        const frames = await everyFrameOf(events, landsEvery);
        const was = new Map<string, Position>();

        for (const [pass, frame] of frames.entries()) {
          for (const [id, box] of frame.boxes) {
            const before = was.get(id);
            if (before !== undefined && !frame.stopped && box.at.x === before.x) {
              expect(
                box.at.y,
                `${name}, one pass per ${landsEvery} events, ${id}, after pass ${pass}`,
              ).toBe(before.y);
            }
            was.set(id, box.at);
          }
          // And no box is ever drawn on another, at any rate.
          expect(collide(frame), `${name}, one pass per ${landsEvery}, pass ${pass}`).toEqual([]);
        }
      }
    }
  });

  it("test_no_two_boxes_are_drawn_on_top_of_each_other", async () => {
    // Freeing the column is what makes this worth asking again: two tiles that
    // sat in different columns, each at the top of its own, can be sent into the
    // same column on one arrival — and they keep their rows, which is what would
    // put them in the same space. Checked after every event of both real runs,
    // reserved rectangles counted as boxes.
    for (const [name, events] of THE_REAL_STREAMS) {
      for (const [step, frame] of (await everyFrameOf(events)).entries()) {
        expect(collide(frame), `${name}, after event ${step}`).toEqual([]);
      }
    }
  });
});
