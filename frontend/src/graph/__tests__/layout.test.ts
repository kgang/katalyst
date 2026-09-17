/**
 * What the map's layout must never do.
 *
 * The one that matters most is the first: a tile that has already been placed
 * keeps its place. A map grows — a claim arrives, a branch adds one — and a
 * layout that reshuffled the tiles already on screen would move whatever the
 * reader was looking at out from under them. Everything else here is about the
 * map having a direction: left to right, with the one arrow allowed to point
 * backwards taken out of the reckoning.
 *
 * The layout engine is run for real, in this process rather than on a
 * background thread, because the settings are the thing being tested and a
 * stand-in would test nothing.
 */

import ELK from "elkjs/lib/elk.bundled.js";
import { describe, expect, it } from "vitest";
import type { ClaimView, LinkView } from "../../world";
import {
  LAYOUT_OPTIONS,
  type LayoutEdge,
  type Position,
  readPositions,
  toElkGraph,
} from "../elkGraph";
import {
  claimLines,
  LARGEST_ZOOM,
  SMALLEST_ZOOM,
  SUMMARY_BELOW_ZOOM,
  smallestTextAt,
  TEXT_FLOOR,
  TILE_MAX_HEIGHT,
  TILE_MIN_HEIGHT,
  TILES_PER_LAYER,
  tileHeight,
} from "../geometry";
import { assignLayers, capLayers } from "../layers";

const engine = new ELK();

/**
 * Lay a map out and read the answer back, exactly as the page does.
 *
 * Tiles are given a height here the way the page gives them one: worked out
 * from the claim, not measured from a drawn tile.
 */
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

/** An arrow, with the fields the layering cares about. */
function arrow(source: string, target: string, extra: Partial<LinkView> = {}): LinkView {
  return {
    id: `${source}->${target}`,
    source,
    target,
    mode: "trigger",
    reflexive: false,
    ...extra,
  };
}

describe("the map's layout", () => {
  it("is laid out with the settings the decision record names", () => {
    // Read as a list rather than poked at one key at a time, because the whole
    // point of the record is that these six are chosen together.
    expect(LAYOUT_OPTIONS).toMatchObject({
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.layered.crossingMinimization.semiInteractive": "true",
      "elk.layered.spacing.nodeNodeBetweenLayers": "120",
    });
  });

  it("keeps tiles that are already placed exactly where they are", async () => {
    const first = await layout(
      [
        ["H", 272],
        ["C", 216],
        ["B", 192],
      ],
      [
        { id: "H->C", source: "H", target: "C" },
        { id: "C->B", source: "C", target: "B" },
      ],
      new Map(),
    );
    expect(first.size).toBe(3);

    // A claim arrives, with two arrows, one of which lands on a tile that is
    // already on screen.
    const second = await layout(
      [
        ["H", 272],
        ["C", 216],
        ["B", 192],
        ["S", 232],
      ],
      [
        { id: "H->C", source: "H", target: "C" },
        { id: "C->B", source: "C", target: "B" },
        { id: "S->B", source: "S", target: "B" },
        { id: "S->C", source: "S", target: "C" },
      ],
      first,
    );

    for (const id of ["H", "C", "B"]) {
      expect(second.get(id)).toEqual(first.get(id));
    }
    // And the new one really was placed, rather than left in the corner with
    // everything else.
    expect(second.get("S")).toBeDefined();
    expect(second.size).toBe(4);
  });

  it("runs left to right, so a cause is always left of what it causes", async () => {
    const placed = await layout(
      [
        ["H", 272],
        ["C", 216],
        ["B", 192],
      ],
      [
        { id: "H->C", source: "H", target: "C" },
        { id: "C->B", source: "C", target: "B" },
      ],
      new Map(),
    );

    const h = placed.get("H");
    const c = placed.get("C");
    const b = placed.get("B");
    expect(h).toBeDefined();
    expect(c).toBeDefined();
    expect(b).toBeDefined();
    expect((h as Position).x).toBeLessThan((c as Position).x);
    expect((c as Position).x).toBeLessThan((b as Position).x);
  });

  it("gives each tile the height it will actually be drawn at", async () => {
    const placed = await layout(
      [
        ["short", TILE_MIN_HEIGHT],
        ["tall", TILE_MAX_HEIGHT],
      ],
      [{ id: "short->tall", source: "short", target: "tall" }],
      new Map(),
    );
    const short = placed.get("short");
    const tall = placed.get("tall");
    expect(short).toBeDefined();
    expect(tall).toBeDefined();
    // The two are in different columns, so a tile of one height never decides
    // where a tile of another height goes.
    expect((short as Position).x).toBeLessThan((tall as Position).x);
  });
});

describe("how tall a tile is", () => {
  /** A claim with nothing on it, which each test then gives what it needs. */
  function claimOf(text: string, extra: Partial<ClaimView> = {}): ClaimView {
    return {
      id: "X",
      claim: text,
      kind: "event",
      resolvesBy: "2026-11-01",
      resolutionSource: "A named source.",
      beliefs: {
        model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
        user: { absence: { words: "—", reason: "You have not said." } },
        market: { reading: { p: 0.48, lo: 0.45, hi: 0.52 } },
      },
      evidence: [],
      ...extra,
    };
  }

  it("is decided by the content, not fixed for every tile", () => {
    const bare = tileHeight(claimOf("A short claim."));
    const withReason = tileHeight(
      claimOf("A short claim.", {
        beliefs: {
          model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
          user: { absence: { words: "—", reason: "You have not said." } },
          market: { absence: { words: "no market", reason: "No venue quotes this claim." } },
        },
      }),
    );
    const withClippings = tileHeight(
      claimOf("A claim long enough to take three whole lines of the tile it is written on.", {
        evidence: [
          { line: "One.", monogram: "A", host: "a.com", direction: 1 },
          { line: "Two.", monogram: "B", host: "b.com", direction: -1 },
        ],
      }),
    );

    expect(bare).toBeLessThan(withReason);
    expect(withReason).toBeLessThan(withClippings);
  });

  it("stays on the eight-pixel grid and inside the floor and the ceiling", () => {
    const claims = [
      "A.",
      "A claim of about the length that takes two lines.",
      "A claim long enough to run past three lines of a tile and be stopped there, with more.",
    ];
    for (const text of claims) {
      const height = tileHeight(claimOf(text));
      expect(height % 8).toBe(0);
      expect(height).toBeGreaterThanOrEqual(TILE_MIN_HEIGHT);
      expect(height).toBeLessThanOrEqual(TILE_MAX_HEIGHT);
    }
  });

  it("shows between one and three lines of the claim, and never more", () => {
    expect(claimLines("Short.")).toBe(1);
    expect(claimLines("A".repeat(400))).toBe(3);
    // The number of lines the tile is built for is the number the claim is
    // allowed to draw, so the two can never disagree.
    expect(claimLines("")).toBe(1);
  });
});

describe("the eleven-pixel floor", () => {
  it("holds at every zoom the reader can reach", () => {
    // Swept rather than spot-checked, because the whole point of the floor is
    // that there is no zoom at which it fails.
    for (let zoom = SMALLEST_ZOOM; zoom <= LARGEST_ZOOM + 0.0001; zoom += 0.005) {
      const onGlass = smallestTextAt(zoom) * zoom;
      expect(onGlass).toBeGreaterThanOrEqual(TEXT_FLOOR - 0.0001);
    }
  });

  it("switches to the summary exactly where the full tile would fall below it", () => {
    // A hair under the threshold the summary is drawing; a hair over, the full
    // tile is — and both clear eleven pixels.
    expect(
      smallestTextAt(SUMMARY_BELOW_ZOOM - 0.001) * (SUMMARY_BELOW_ZOOM - 0.001),
    ).toBeGreaterThan(TEXT_FLOOR);
    expect(smallestTextAt(SUMMARY_BELOW_ZOOM) * SUMMARY_BELOW_ZOOM).toBeCloseTo(TEXT_FLOOR, 6);
    expect(smallestTextAt(SMALLEST_ZOOM) * SMALLEST_ZOOM).toBeCloseTo(TEXT_FLOOR, 6);
  });
});

describe("sorting a map into columns", () => {
  it("puts each claim as far right as the longest chain reaching it", () => {
    // The stored example's shape: the strait opens, insurance repricing and
    // talks follow, the oil price follows both, and two tradeable endings hang
    // off the oil price.
    const links = [
      arrow("H", "B"),
      arrow("H", "C"),
      arrow("H", "N1"),
      arrow("C", "B"),
      arrow("B", "M1"),
      arrow("B", "M2"),
    ];
    const layers = new Map(
      assignLayers(["H", "C", "B", "R", "M1", "M2", "N1"], links).map((one) => [one.id, one.layer]),
    );

    expect(layers.get("H")).toBe(0);
    expect(layers.get("C")).toBe(1);
    expect(layers.get("N1")).toBe(1);
    // B is reached through H directly and through C, and the longer chain wins.
    expect(layers.get("B")).toBe(2);
    expect(layers.get("M1")).toBe(3);
    expect(layers.get("M2")).toBe(3);
  });

  it("sets the feedback arrow aside, so the map still has a direction", () => {
    // The oil price feeds back on an output decision, which feeds back on the
    // oil price: a loop, and the only kind of loop the map allows. Left in, there
    // would be no leftmost claim at all.
    const links = [arrow("B", "R", { reflexive: true }), arrow("R", "B"), arrow("H", "B")];
    const layers = new Map(assignLayers(["H", "B", "R"], links).map((one) => [one.id, one.layer]));

    expect(layers.get("R")).toBe(0);
    expect(layers.get("H")).toBe(0);
    expect(layers.get("B")).toBe(1);
  });

  it("shows seven tiles in a column and collapses the rest into one", () => {
    const wide = Array.from({ length: 10 }, (_, index) => `n${index}`);
    const { shown, overflows } = capLayers(assignLayers(wide, []));

    expect(shown).toHaveLength(TILES_PER_LAYER);
    expect(overflows).toHaveLength(1);
    expect(overflows[0]?.count).toBe(3);
    // The claims that are not drawn are named, so the collapsed tile is standing
    // in for something rather than covering something up.
    expect(overflows[0]?.hidden).toEqual(["n7", "n8", "n9"]);
  });

  it("leaves a column alone when it fits", () => {
    const { shown, overflows } = capLayers(assignLayers(["a", "b", "c"], []));
    expect(shown.map((one) => one.id)).toEqual(["a", "b", "c"]);
    expect(overflows).toHaveLength(0);
  });
});
