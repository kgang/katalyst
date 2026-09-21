/**
 * Folding a generation's events into a map that is being built.
 *
 * Everything here is checked on the chapter's own worked run — the Hormuz
 * generation, call by call — and on streams built on purpose to break a rule that
 * the engine happens never to break. **No test below asserts a value.** Where a
 * number is involved, the screen is compared with the thing it was handed rather
 * than with a figure written down here.
 */

import { describe, expect, it } from "vitest";
import { type PinnedTile, type Position, pinsFor, readPositions } from "../../graph/elkGraph";
import { toFlow } from "../../graph/toFlow";
import { inFewWords } from "../../world/naming";
import type { ProposalAccepted, StreamEvent } from "../events";
import type { Growth } from "../growth";
import { fold, foldAll, waitingFor } from "../growth";
import { A_REAL_RUN } from "./aRealRun";
import { B, BELIEFS, EVERY_ARROW, H, STARTED, THE_GROWTH, THE_SENTENCE, theWorld } from "./aStream";

/** Where a generation starts: a request has gone and nothing has come back. */
function fresh(): Growth {
  return waitingFor(THE_SENTENCE, null);
}

/** Every state the run passes through, in order, starting from the first. */
function everyStateOf(events: readonly StreamEvent[]): Growth[] {
  const states: Growth[] = [fresh()];
  for (const event of events) {
    states.push(fold(states[states.length - 1] as Growth, event));
  }
  return states;
}

describe("the first rectangle", () => {
  it("test_a_skeleton_tile_appears_before_the_first_claim", () => {
    const started = fold(fresh(), STARTED);

    // One rectangle, carrying the reader's own sentence, and not one claim.
    expect(started.skeletons).toHaveLength(1);
    expect(started.skeletons[0]?.words).toBe(THE_SENTENCE);
    expect(started.world.claims).toHaveLength(0);
    expect(started.phase).toBe("growing");
  });

  it("test_a_skeleton_carries_no_number_and_no_identifier", () => {
    // Walked over every state of the whole run, so the claim holds of the first
    // rectangle and of every one that hangs off an open claim afterwards.
    for (const state of everyStateOf(THE_GROWTH)) {
      const names = new Set(state.world.claims.map((one) => one.id));
      for (const box of state.skeletons) {
        // A box's name, never a claim's: it is absent from the map's claims, and
        // it is not one of the identifiers the engine minted.
        expect(names.has(box.id)).toBe(false);
        expect(box.id.startsWith("skeleton:")).toBe(true);
        // Every character it prints came off the stream: the reader's own
        // sentence, or the open claim's own words quoted back.
        const open = state.world.claims.find((one) => one.id === box.after);
        expect(box.words).toBe(
          box.after === null ? THE_SENTENCE : `one step on from "${inFewWords(open?.claim ?? "")}"`,
        );
        // There is no likelihood on it to be a number nobody computed, because
        // there is no slot on it at all.
        expect(Object.keys(box)).toEqual(["id", "words", "after"]);
      }
    }
  });
});

describe("the rectangles are the frontier, drawn", () => {
  it("test_a_closed_claim_loses_its_skeleton_on_the_event_that_closed_it", () => {
    // The strait reaches its full width on the arrows-only proposal, so that
    // event's frontier stops naming it — and its rectangle comes down there,
    // rather than at some later proposal that might never come.
    const beforeIt = foldAll(fresh(), THE_GROWTH.slice(0, 5));
    expect(beforeIt.skeletons.map((one) => one.after)).toContain("H");

    const after = fold(beforeIt, THE_GROWTH[5] as ProposalAccepted);
    expect(after.skeletons.map((one) => one.after)).not.toContain("H");

    // And a refusal does the same work: a claim closed by its third refusal in a
    // row is gone from the frontier on the refusal itself.
    const closedByRefusal = fold(after, {
      event: "proposal_rejected",
      at: 9,
      claim_in_words: "a third proposal for the same claim, refused like the two before it",
      violations: [
        { code: "missing_rationale", subject: "C", message: "The rule's own sentence." },
      ],
      frontier: ["B"],
    });
    expect(closedByRefusal.skeletons.map((one) => one.after)).toEqual(["B"]);
  });

  it("test_every_skeleton_goes_when_the_beliefs_arrive", () => {
    const grown = foldAll(fresh(), THE_GROWTH);
    expect(grown.skeletons.length).toBeGreaterThan(0);

    const finished = fold(grown, BELIEFS);
    expect(finished.skeletons).toEqual([]);
  });
});

describe("nothing already placed moves", () => {
  it("test_a_tile_keeps_its_place_when_a_later_tile_arrives", () => {
    // The real machinery, over the real run: at every step the map is laid out
    // again, and the rule the layout obeys — a tile that had a position keeps it,
    // to the pixel — is checked against what came out.
    let placed = new Map<string, PinnedTile>();
    let seen = new Map<string, Position>();

    for (const state of everyStateOf(THE_GROWTH)) {
      const drawing = toFlow(state.world, undefined, state.skeletons);
      const pins = pinsFor(placed, drawing.tiles);

      // Nothing that had a place lost its pin: a box whose size changed would
      // drop every pin at once, and a growing map must never do that.
      for (const tile of drawing.tiles) {
        if (placed.has(tile.id)) {
          expect(pins.has(tile.id)).toBe(true);
        }
      }

      // The layout engine is asked again and answers with somewhere new for
      // everything. What comes back keeps every pinned tile exactly where it was.
      const laidOut = {
        id: "map",
        children: drawing.tiles.map((tile, place) => ({
          id: tile.id,
          x: 1000 + place * 7,
          y: 2000 + place * 11,
        })),
      };
      const positions = readPositions(laidOut, pins);

      for (const [id, was] of seen) {
        if (positions.has(id)) {
          expect(positions.get(id)).toEqual(was);
        }
      }

      const heights = new Map(drawing.tiles.map((tile) => [tile.id, tile.height]));
      placed = new Map(
        [...positions].map(([id, at]) => [id, { at, height: heights.get(id) ?? 0 }]),
      );
      seen = new Map([...seen, ...positions]);
    }

    // And the claims really did arrive one after another rather than all at once,
    // or the walk above would have proved nothing.
    expect(seen.size).toBeGreaterThan(1);
  });
});

describe("a wire and its two ends", () => {
  it("test_a_wire_draws_only_after_both_ends_exist", () => {
    // The engine sends a claim and its incoming arrows in one event, so this
    // stream is **built** rather than assumed: an arrow arrives while one of its
    // ends is still nowhere.
    const early: StreamEvent[] = [
      STARTED,
      { event: "proposal_accepted", at: 0, proposition: H, links: [], frontier: ["H"] },
      {
        event: "proposal_accepted",
        at: 1,
        proposition: null,
        links: [EVERY_ARROW[3] as never],
        frontier: ["H"],
      },
    ];
    const held = foldAll(fresh(), early);

    // Half a wire is worse than no wire: it is held, not drawn.
    expect(held.world.links).toEqual([]);
    expect(held.waitingWires).toHaveLength(1);

    // The second end arrives, and the wire is drawn on that event.
    const joined = fold(held, {
      event: "proposal_accepted",
      at: 2,
      proposition: B,
      links: [],
      frontier: ["H", "B"],
    });
    expect(joined.world.links.map((one) => one.id)).toEqual(["H->B"]);
    expect(joined.waitingWires).toEqual([]);
  });

  it("test_every_arrow_that_arrived_is_still_drawn", () => {
    // The arrows accumulate. An earlier version of this reducer replaced the
    // list with whatever the latest event brought, so a map five claims deep was
    // drawn with one arrow — which the chapter's three-claim run was too small
    // to show and the real ten-claim run showed at once.
    const grown = foldAll(fresh(), A_REAL_RUN);
    expect(grown.world.claims).toHaveLength(10);
    expect(grown.world.links).toHaveLength(9);
    expect(new Set(grown.world.links.map((one) => one.id)).size).toBe(9);

    // And they arrive one at a time, never all at the end: the count only ever
    // goes up, it goes up more than once, and it ends where the map ends.
    const counts = everyStateOf(A_REAL_RUN).map((state) => state.world.links.length);
    expect(counts).toEqual([...counts].sort((one, other) => one - other));
    expect(counts.at(-1)).toBe(grown.world.links.length);
    expect(new Set(counts).size).toBeGreaterThan(2);
  });

  it("test_the_engines_own_run_never_holds_a_wire_back", () => {
    // The list is expected to stay empty for ever. It is kept because a picture
    // of something that is not true is worse than a picture that is late.
    for (const state of everyStateOf(THE_GROWTH)) {
      expect(state.waitingWires).toEqual([]);
    }
  });
});

describe("the chips", () => {
  it("test_chips_resolve_last_and_only_once", () => {
    // Not one likelihood at any point before the world arrives.
    for (const state of everyStateOf(THE_GROWTH)) {
      for (const claim of state.world.claims) {
        expect(claim.beliefs.model.reading).toBeUndefined();
        expect(claim.beliefs.model.absence?.words).toBe("no engine yet");
      }
    }

    // And afterwards, every chip is the world's own answer — compared with the
    // world that was handed in, never with a figure written down here.
    const grown = foldAll(fresh(), THE_GROWTH);
    const finished = fold(grown, BELIEFS);
    for (const claim of finished.world.claims) {
      expect(claim.beliefs.model.reading?.p).toBe(BELIEFS.world.beliefs[claim.id]?.p);
    }

    // A stream carrying two of them — which the engine does not produce, and
    // which is built here anyway — settles on the last and blends nothing.
    const second = { ...BELIEFS, world: theWorld([H, B], []) };
    const both = foldAll(grown, [BELIEFS, second]);
    const onlyTheLast = fold(grown, second);
    expect(both.world).toEqual(onlyTheLast.world);
  });
});

describe("an event this build does not know", () => {
  it("test_an_unknown_event_leaves_everything_else_alone", () => {
    const grown = foldAll(fresh(), THE_GROWTH);
    const after = foldAll(grown, [
      { event: "unknown", name: "a_call_went_out" } as never,
      { event: "unknown", name: "a_call_went_out" } as never,
    ]);

    expect(after.unknown.get("a_call_went_out")).toBe(2);
    // Everything else is exactly as it was.
    expect({ ...after, unknown: grown.unknown }).toEqual(grown);
  });
});
