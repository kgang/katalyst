/**
 * Moving along the wires rather than across the glass.
 *
 * The test that matters is the first: **every sideways step lands on a claim
 * joined to the one you were on by a wire.** A map's meaning is its wires, and a
 * step that landed on whatever tile happened to be nearest would be reading the
 * picture instead of the argument.
 *
 * The stored example has the case that proves it: pressing *forward* on *Brent
 * settles below $68* can land you on *OPEC+ announces output restraint*, which
 * sits in an **earlier** column — because the arrow between them is the feedback
 * arrow, a market acting back on the world it measures. Landing to your left
 * after pressing right is correct.
 */

import { describe, expect, it } from "vitest";
import { aWire } from "../../test/aMap";
import type { LinkView } from "../../world";
import { alongWire, inColumn, type PositionMap, stepThrough } from "../focusMap";

/** Where the stored example's tiles sit, in the columns the layout puts them in. */
const WHERE: PositionMap = new Map([
  ["H", { x: 0, y: 400, height: 280 }],
  ["C", { x: 400, y: 0, height: 200 }],
  ["N1", { x: 400, y: 240, height: 216 }],
  ["R", { x: 400, y: 500, height: 152 }],
  ["B", { x: 800, y: 300, height: 176 }],
  ["M1", { x: 1200, y: 120, height: 192 }],
  ["M2", { x: 1200, y: 400, height: 192 }],
]);

/** The eight arrows of the stored example, the feedback one included. */
const WIRES: LinkView[] = [
  aWire({ source: "H", target: "B" }),
  aWire({ source: "H", target: "C", mode: "sustain" }),
  aWire({ source: "H", target: "N1", lag: 10 }),
  aWire({ source: "C", target: "B", mode: "sustain" }),
  aWire({ source: "B", target: "M1", lag: 1 }),
  aWire({ source: "B", target: "M2", lag: 3 }),
  aWire({ source: "B", target: "R", reflexive: true, lag: 14 }),
  aWire({ source: "R", target: "B", strength: -1.2 }),
];

/** Every claim joined to this one by a wire, whichever way the wire points. */
function wiredTo(id: string): Set<string> {
  const joined = new Set<string>();
  for (const wire of WIRES) {
    if (wire.source === id) {
      joined.add(wire.target);
    }
    if (wire.target === id) {
      joined.add(wire.source);
    }
  }
  return joined;
}

describe("moving along the wires", () => {
  // test_h_and_l_land_only_on_a_wired_neighbour
  it("lands only on a claim a wire joins to the one you were on", () => {
    for (const id of WHERE.keys()) {
      for (const way of ["in", "out"] as const) {
        const step = alongWire(id, way, WIRES, WHERE);
        if (step === null) {
          continue;
        }
        expect(wiredTo(id)).toContain(step.to);
        // And the wire it says it took really does join the two.
        expect([step.wire.source, step.wire.target].sort()).toEqual([id, step.to].sort());
      }
    }
  });

  // test_a_feedback_arrow_is_still_something_you_can_walk_along
  it("walks the feedback arrow, which the diff sets aside", () => {
    // One rule, two questions. *What can move* reads the map with feedback
    // arrows set aside; *what can I walk to* reads the whole map.
    const out = alongWire("B", "out", WIRES, WHERE);
    const reachable = new Set(["M1", "M2", "R"]);
    expect(reachable).toContain(out?.to);
    expect(new Set([out?.to, ...(out?.others ?? [])])).toEqual(reachable);
  });

  // test_the_step_takes_the_nearest_and_leaves_the_rest_for_up_and_down
  it("takes the nearest neighbour and leaves the others a keystroke away", () => {
    // B sits at 300 and is 176 tall, so its middle is 388. M2's middle is 496
    // and M1's is 216, so M2 is nearer — and M1 and R become the set that up and
    // down walk at the tile you land on. Two keystrokes reach any neighbour, and
    // there is no chooser overlay, which would be a pop-up in all but name.
    const step = alongWire("B", "out", WIRES, WHERE);
    expect(step?.to).toBe("M2");
    expect(step?.others).toEqual(["M1", "R"]);
    expect(stepThrough("M2", step?.others ?? [], WHERE, -1)).toBe("M1");
  });

  // test_no_wire_that_way_is_a_quiet_no_op
  it("does not move when there is no wire that way", () => {
    // The endings of the map cause nothing, so pressing forward on one is a
    // quiet no-op rather than a jump to whatever was nearby.
    expect(alongWire("M1", "out", WIRES, WHERE)).toBeNull();
    expect(alongWire("H", "in", WIRES, WHERE)).toBeNull();
  });

  // test_a_step_never_lands_on_a_claim_the_map_is_not_drawing
  it("never lands on a claim the map is not drawing", () => {
    // A claim behind a collapsed tile has no position, and a step that landed on
    // one would put the keyboard somewhere with nothing to see.
    const hidden = new Map(WHERE);
    hidden.delete("M1");
    hidden.delete("M2");
    const step = alongWire("B", "out", WIRES, hidden);
    expect(step?.to).toBe("R");
  });
});

describe("walking a column", () => {
  // test_a_column_is_the_claims_at_the_same_remove_from_the_start
  it("reads a column from the top down", () => {
    expect(inColumn("N1", WHERE)).toEqual(["C", "N1", "R"]);
  });

  // test_focus_does_not_wrap
  it("stops at the end of a column rather than wrapping round", () => {
    // Wrapping teleports you to the other end and you lose your place. The line
    // under the map says "last claim in this column" instead.
    expect(stepThrough("R", inColumn("R", WHERE), WHERE, 1)).toBeNull();
    expect(stepThrough("C", inColumn("C", WHERE), WHERE, -1)).toBeNull();
    expect(stepThrough("C", inColumn("C", WHERE), WHERE, 1)).toBe("N1");
  });
});
