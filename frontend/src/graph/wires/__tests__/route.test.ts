/**
 * Where a wire goes when the short way would take it through a tile.
 *
 * The case that matters is on the stored example: the strait pushes the oil
 * price directly, and the insurance claim sits in the column between them. Left
 * to the ordinary route the wire runs straight through that tile — and because a
 * tile is drawn over a wire, the wire disappears behind it and comes out the
 * other side. The picture then says the insurance claim causes the oil price and
 * the strait does not, which is the opposite of the map.
 */

import { describe, expect, it } from "vitest";
import {
  type Box,
  corridorCorners,
  freeCorridor,
  longestRunMidpoint,
  planRoutes,
  type RoutableWire,
  roundedPath,
  tailOffsets,
} from "../route";

/** Three columns, with two tiles stacked in the middle one and a gap between them. */
const BOXES = new Map<string, Box>([
  ["H", { x: 0, y: 200, width: 280, height: 200 }],
  ["N1", { x: 400, y: 0, width: 280, height: 200 }],
  ["C", { x: 400, y: 260, width: 280, height: 200 }],
  ["B", { x: 800, y: 220, width: 280, height: 160 }],
]);

const WIRES: RoutableWire[] = [
  { id: "H->C", source: "H", target: "C", handle: "out-sustain", reflexive: false },
  { id: "H->N1", source: "H", target: "N1", handle: "out-trigger", reflexive: false },
  { id: "H->B", source: "H", target: "B", handle: "out-trigger", reflexive: false },
  { id: "C->B", source: "C", target: "B", handle: "out-sustain", reflexive: false },
  { id: "B->N1", source: "B", target: "N1", handle: "out-trigger", reflexive: true },
];

describe("how a wire is routed", () => {
  it("test_an_arrow_between_neighbouring_columns_takes_the_ordinary_route", () => {
    const plans = planRoutes(WIRES, BOXES);
    expect(plans.get("H->C")?.kind).toBe("direct");
    expect(plans.get("H->N1")?.kind).toBe("direct");
    expect(plans.get("C->B")?.kind).toBe("direct");
  });

  it("test_an_arrow_that_skips_a_column_travels_a_clear_corridor", () => {
    const plan = plans().get("H->B");
    expect(plan?.kind).toBe("corridor");
    if (plan?.kind !== "corridor") {
      throw new Error("expected a corridor");
    }
    // The corridor is the gap between the two tiles in the middle column, and
    // it touches neither of them.
    expect(plan.corridorY).toBeGreaterThan(200);
    expect(plan.corridorY).toBeLessThan(260);
    // It turns in the gutters either side of that column, which are empty.
    expect(plan.fromX).toBeGreaterThan(280);
    expect(plan.fromX).toBeLessThan(400);
    expect(plan.toX).toBeGreaterThan(680);
    expect(plan.toX).toBeLessThan(800);
  });

  it("test_the_one_backwards_arrow_runs_over_the_top_of_the_map", () => {
    const plan = plans().get("B->N1");
    expect(plan?.kind).toBe("sky");
    if (plan?.kind !== "sky") {
      throw new Error("expected a sky route");
    }
    // Above the highest tile on the map, so it crosses nothing at all.
    expect(plan.skyY).toBeLessThan(0);
  });

  it("test_a_corridor_never_runs_through_a_tile", () => {
    const boxes = [...BOXES.values()];
    const lane = freeCorridor(boxes, 300, 780, 300);
    expect(lane).not.toBeNull();
    for (const box of boxes) {
      const crosses =
        box.x < 780 &&
        box.x + box.width > 300 &&
        box.y < (lane ?? 0) &&
        box.y + box.height > (lane ?? 0);
      expect(crosses).toBe(false);
    }
  });

  it("test_the_same_map_routes_the_same_way_every_time", () => {
    expect(planRoutes(WIRES, BOXES)).toEqual(planRoutes(WIRES, BOXES));
  });

  function plans() {
    return planRoutes(WIRES, BOXES);
  }
});

describe("two arrows leaving the same socket", () => {
  it("test_their_marks_stack_rather_than_landing_on_top_of_one_another", () => {
    const offsets = tailOffsets(WIRES);
    // Three arrows leave the first claim, two of them through the same socket.
    expect(offsets.get("H->N1")).not.toBe(offsets.get("H->B"));
    // One arrow alone on its socket sits on the wire, not beside it.
    expect(offsets.get("H->C")).toBe(0);
  });

  it("test_the_stack_is_centred_on_the_wire", () => {
    const offsets = tailOffsets(WIRES);
    const shared = [offsets.get("H->N1") ?? 0, offsets.get("H->B") ?? 0];
    expect(shared[0] ?? 0).toBe(-(shared[1] ?? 0));
  });
});

describe("the shape a wire is drawn as", () => {
  it("test_a_route_with_no_corners_is_a_straight_line", () => {
    expect(roundedPath([[0, 0]])).toBe("M 0,0 L 0,0");
  });

  it("test_a_corner_is_rounded_rather_than_snapped", () => {
    const path = roundedPath([
      [0, 0],
      [100, 0],
      [100, 100],
    ]);
    expect(path).toContain("Q");
  });

  it("test_the_plate_sits_on_the_longest_straight_run", () => {
    const corners = corridorCorners(0, 0, 800, 100, { fromX: 100, toX: 700, corridorY: 50 });
    const at = longestRunMidpoint(corners);
    // The long horizontal run along the corridor, and its middle.
    expect(at[1]).toBe(50);
    expect(at[0]).toBe(400);
  });
});
