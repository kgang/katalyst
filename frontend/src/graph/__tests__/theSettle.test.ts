/**
 * When a tile may move, checked on two real streams and no browser.
 *
 * **The rule, in Kent's decision (record 0024):** a tile moves only when an
 * arrow would otherwise point backwards, and once when the run stops. In three
 * clauses a test can hold:
 *
 * 1. a tile keeps its **row** — its vertical place and its order within its
 *    column — for as long as the map is growing;
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
async function everyFrameOf(events: readonly StreamEvent[]): Promise<Frame[]> {
  const frames: Frame[] = [];
  let growth = waitingFor("the sentence this run was started from", null);
  let pinned = new Map<string, PinnedTile>();
  let settled = false;

  for (const event of events) {
    growth = fold(growth, event);
    const drawing = toFlow(growth.world, undefined, growth.skeletons);
    const stopped = hasStopped(growth.phase);
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
    // A box that stays in the column it is in never moves a pixel — and the
    // only box that ever takes a new row while the map is growing is one the
    // arrows have just sent into a different column, where the row it wants was
    // taken. (Measured, 2026-09-21: that happens twice on the live Verify run
    // and once on the committed recording, always to the tile that moved. See
    // `readPositions` for why the alternative is two claims drawn on top of
    // each other.)
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
