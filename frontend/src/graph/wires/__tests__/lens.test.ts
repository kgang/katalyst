/**
 * The hover lens: what this claim has to do with anything.
 *
 * Worked on the stored example's own shape. Point at the oil price and its
 * causes are the strait, the insurance premium and the producers; the things it
 * causes are the two tradeable endings and, through the feedback arrow, the
 * producers again. The one claim on that map with nothing to do with the oil
 * price is the diplomatic ending, and it is the one thing the lens dims.
 */

import { describe, expect, it } from "vitest";
import { onThePathFrom, type WalkableWire } from "../lens";

/** The stored example's eight arrows, with only the ends that matter here. */
const WIRES: WalkableWire[] = [
  { id: "H->B", source: "H", target: "B" },
  { id: "H->C", source: "H", target: "C" },
  { id: "H->N1", source: "H", target: "N1" },
  { id: "C->B", source: "C", target: "B" },
  { id: "B->M1", source: "B", target: "M1" },
  { id: "B->M2", source: "B", target: "M2" },
  { id: "B->R", source: "B", target: "R" },
  { id: "R->B", source: "R", target: "B" },
];

describe("the hover lens", () => {
  it("test_the_lens_lights_causes_and_what_they_cause_and_nothing_else", () => {
    const lit = onThePathFrom("B", WIRES);
    expect(lit).not.toBeNull();
    expect([...(lit?.claims ?? [])].sort()).toEqual(["B", "C", "H", "M1", "M2", "R"]);
    // The diplomatic ending is the one claim on this map that has nothing to do
    // with the oil price, and it is the one thing the lens puts out.
    expect(lit?.claims.has("N1")).toBe(false);
  });

  it("test_the_lens_follows_every_wire_including_the_one_that_loops_back", () => {
    // The producers are reached from the oil price only through the feedback
    // arrow. The lens asks what you can walk to, and you can walk to them. The
    // diff states ask what an edit can move, and they set that arrow aside —
    // one rule, two readers, written down once in the chapter on interventions.
    const lit = onThePathFrom("M1", WIRES);
    expect(lit?.claims.has("R")).toBe(true);
  });

  it("test_an_arrow_is_lit_only_when_both_its_ends_are", () => {
    const lit = onThePathFrom("B", WIRES);
    expect(lit?.wires.has("H->N1")).toBe(false);
    expect(lit?.wires.has("H->B")).toBe(true);
    expect(lit?.wires.has("B->R")).toBe(true);
  });

  it("test_a_loop_never_swallows_the_walk_going_the_other_way", () => {
    // Point at the producers. The oil price is both what they cause and what
    // causes them, because the two are joined by a loop — and the oil price's
    // own causes, the strait and the insurance premium, are still causes of the
    // producers and stay lit.
    const lit = onThePathFrom("R", WIRES);
    expect([...(lit?.claims ?? [])].sort()).toEqual(["B", "C", "H", "M1", "M2", "R"]);
  });

  it("test_pointing_at_nothing_leaves_everything_lit", () => {
    expect(onThePathFrom(null, WIRES)).toBeNull();
  });

  it("test_a_claim_is_always_on_its_own_path", () => {
    const lit = onThePathFrom("N1", WIRES);
    expect(lit?.claims.has("N1")).toBe(true);
    expect([...(lit?.claims ?? [])].sort()).toEqual(["H", "N1"]);
  });
});
