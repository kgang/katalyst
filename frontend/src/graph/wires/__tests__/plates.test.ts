/**
 * Nothing on the map lands on top of anything else.
 *
 * Checked on the two maps the product actually draws: the stored example, and
 * the union of the stored example with the strike branch laid over it. The
 * second is the one that matters — it carries the strike and its three arrows,
 * two of them crossing the middle of the map, and it is where per-wire placement
 * stopped being enough.
 *
 * The check is arithmetic on rectangles rather than a look at a screenshot,
 * which is the point of placing plates from the layout rather than from the
 * page: the answer is the same every time, and a test can have it without a
 * browser.
 */

import { describe, expect, it } from "vitest";
import { TILE_WIDTH } from "../../geometry";
import { MARK_STANDOFF, type PlateWire, planPlates, plateSize, socketsFor } from "../plates";
import { type Box, planRoutes, type RoutableWire, tailOffsets } from "../route";

/* ---- The two maps -------------------------------------------------------- */

/**
 * The stored example, laid out the way the layout lays it out.
 *
 * The numbers are the ones the running app produces — read off it once and
 * written down, so this test is about placement and not about the layout engine.
 */
const HORMUZ_TILES: [string, number, number][] = [
  // id, left edge, top edge — every tile is 280 wide.
  ["H", 12, 456],
  ["C", 412, 476],
  ["N1", 412, 212],
  ["R", 412, 12],
  ["B", 812, 484],
  ["M1", 1212, 447],
  ["M2", 1212, 687],
];

const HORMUZ_HEIGHTS: Record<string, number> = {
  H: 232,
  C: 192,
  N1: 216,
  R: 152,
  B: 176,
  M1: 192,
  M2: 192,
};

/** The eight arrows of the stored example, in the order the map lists them. */
const HORMUZ_WIRES: PlateWire[] = [
  wire("H", "B", { mode: "trigger", strength: 1.6, lag: 2 }),
  wire("H", "C", { mode: "sustain", strength: 1.1, lag: 0 }),
  wire("H", "N1", { mode: "trigger", strength: 0.7, lag: 10 }),
  wire("C", "B", { mode: "sustain", strength: 0.7, lag: 7 }),
  wire("B", "M1", { mode: "trigger", strength: 0.9, lag: 1 }),
  wire("B", "M2", { mode: "trigger", strength: 0.8, lag: 3 }),
  wire("B", "R", { mode: "trigger", strength: 0.6, lag: 14, reflexive: true }),
  wire("R", "B", { mode: "trigger", strength: -1.2, lag: 5 }),
];

/**
 * The union of the stored example and the strike branch.
 *
 * The branch adds S — *a confirmed military strike on Iranian territory* — and
 * three arrows out of it, two of which have to cross the middle of the map. Both
 * worlds are laid out once and painted into the same coordinates, so a ghosted
 * tile stands exactly where its solid twin does and is as much in the way.
 */
const UNION_TILES: [string, number, number][] = [
  ["S", 12, 126],
  ["H", 412, 82],
  ["N1", 812, 23],
  ["C", 812, 260],
  ["R", 812, 500],
  ["B", 1212, 179],
  ["M1", 1612, 142],
  ["M2", 1612, 382],
];

/** The strait grows a badge pair on this branch, so its tile is taller than on the base map. */
const UNION_HEIGHTS: Record<string, number> = { ...HORMUZ_HEIGHTS, H: 296, S: 208 };

const UNION_WIRES: PlateWire[] = [
  ...HORMUZ_WIRES,
  wire("S", "B", { mode: "trigger", strength: -2.4, lag: 0 }),
  wire("S", "C", { mode: "sustain", strength: -2, lag: 1 }),
  wire("S", "H", { mode: "sustain", strength: -1.9, lag: 3 }),
];

/** One arrow, with the fields placement reads. */
function wire(
  source: string,
  target: string,
  over: { mode: "trigger" | "sustain"; strength: number; lag: number; reflexive?: boolean },
): PlateWire {
  return {
    id: `${source}->${target}`,
    source,
    target,
    handle: over.mode === "sustain" ? "out-sustain" : "out-trigger",
    reflexive: over.reflexive ?? false,
    mode: over.mode,
    strength: over.strength,
    lag: over.lag,
  };
}

/** The tiles of one map, as the placement pass is handed them. */
function boxesOf(
  tiles: readonly [string, number, number][],
  heights: Record<string, number>,
): Map<string, Box> {
  return new Map(
    tiles.map(([id, x, y]) => [id, { x, y, width: TILE_WIDTH, height: heights[id] ?? 152 }]),
  );
}

/* ---- Rectangles ---------------------------------------------------------- */

interface Rect {
  readonly what: string;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

/** How far two boxes have to be apart before they count as clear of each other. */
const TOUCHING = 0.5;

function overlaps(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.width - TOUCHING &&
    a.x + a.width - TOUCHING > b.x &&
    a.y < b.y + b.height - TOUCHING &&
    a.y + a.height - TOUCHING > b.y
  );
}

/** Every box the placement pass produced on one map, named. */
function everythingOn(wires: readonly PlateWire[], boxes: Map<string, Box>) {
  const routable: readonly RoutableWire[] = wires;
  const plans = planRoutes(routable, boxes);
  const offsets = tailOffsets(routable);
  const spots = planPlates({ wires, boxes, plans, tailOffsets: offsets });

  const plates: Rect[] = [];
  const marks: Rect[] = [];
  for (const one of wires) {
    const spot = spots.get(one.id);
    const sockets = socketsFor(one, boxes);
    if (spot === undefined || sockets === null) {
      continue;
    }
    const size = plateSize(one, plans.get(one.id) ?? { kind: "direct" });
    plates.push({
      what: `plate ${one.id}`,
      x: spot.x - size.width / 2,
      y: spot.y - size.height / 2,
      width: size.width,
      height: size.height,
    });
    marks.push({
      what: `mark ${one.id}`,
      x: sockets.sourceX + MARK_STANDOFF,
      y: sockets.sourceY + (offsets.get(one.id) ?? 0) - 6.5,
      width: 23,
      height: 13,
    });
  }
  const tiles: Rect[] = [...boxes.entries()].map(([id, box]) => ({ what: `tile ${id}`, ...box }));
  return { plates, marks, tiles, plans, spots };
}

/** Every pair of boxes that touch, named, so a failure says which. */
function collisions(a: readonly Rect[], b: readonly Rect[], samePile: boolean): string[] {
  const found: string[] = [];
  for (const [i, one] of a.entries()) {
    for (const [j, other] of b.entries()) {
      if (samePile && j <= i) {
        continue;
      }
      if (overlaps(one, other)) {
        found.push(`${one.what} × ${other.what}`);
      }
    }
  }
  return found;
}

describe("every plate has a place of its own", () => {
  for (const [name, tiles, heights, wires] of [
    ["the stored example", HORMUZ_TILES, HORMUZ_HEIGHTS, HORMUZ_WIRES],
    ["the stored example with the strike laid over it", UNION_TILES, UNION_HEIGHTS, UNION_WIRES],
  ] as const) {
    describe(name, () => {
      const map = everythingOn(wires, boxesOf(tiles, heights));

      it("test_no_plate_lands_on_another_plate", () => {
        expect(collisions(map.plates, map.plates, true)).toEqual([]);
      });

      it("test_no_plate_lands_on_a_tile", () => {
        expect(collisions(map.plates, map.tiles, false)).toEqual([]);
      });

      it("test_no_plate_lands_on_a_mark", () => {
        expect(collisions(map.plates, map.marks, false)).toEqual([]);
      });

      it("test_no_mark_lands_on_another_mark", () => {
        expect(collisions(map.marks, map.marks, true)).toEqual([]);
      });

      it("test_every_wire_gets_a_plate", () => {
        expect(map.plates).toHaveLength(wires.length);
      });

      it("test_the_same_map_places_the_same_way_every_time", () => {
        const again = everythingOn(wires, boxesOf(tiles, heights));
        expect([...again.spots.entries()]).toEqual([...map.spots.entries()]);
      });
    });
  }

  it("test_two_wires_sharing_a_corridor_get_a_lane_each", () => {
    // On the union both the strait and the strike push the oil price directly,
    // and both have to cross the middle column. One lane would put two wires and
    // two plates on one line.
    const map = everythingOn(UNION_WIRES, boxesOf(UNION_TILES, UNION_HEIGHTS));
    const strait = map.plans.get("H->B");
    const strike = map.plans.get("S->B");
    expect(strait?.kind).toBe("corridor");
    expect(strike?.kind).toBe("corridor");
    if (strait?.kind !== "corridor" || strike?.kind !== "corridor") {
      throw new Error("expected two corridors");
    }
    expect(strait.corridorY).not.toBe(strike.corridorY);
    expect(Math.abs(strait.corridorY - strike.corridorY)).toBeGreaterThan(8);
  });
});

describe("where a wire leaves and arrives", () => {
  it("test_the_sockets_are_where_the_tile_draws_them", () => {
    const boxes = boxesOf(HORMUZ_TILES, HORMUZ_HEIGHTS);
    // Read off the running app: the strait's upper socket, and the insurance
    // claim's lower one. If these drift, every plate is placed against wires that
    // are somewhere else.
    const toBrent = socketsFor(HORMUZ_WIRES[0] as PlateWire, boxes);
    expect(toBrent?.sourceX).toBe(300);
    expect(toBrent?.sourceY).toBeCloseTo(544.2, 1);
    expect(toBrent?.targetX).toBe(804);
    expect(toBrent?.targetY).toBeCloseTo(550.9, 1);

    const toPremium = socketsFor(HORMUZ_WIRES[1] as PlateWire, boxes);
    expect(toPremium?.sourceY).toBeCloseTo(599.8, 1);
    expect(toPremium?.targetY).toBeCloseTo(595.0, 1);
  });
});
