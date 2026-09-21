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
import { aClaim, aWire } from "../../test/aMap";
import type { ClaimView, LinkView } from "../../world";
import {
  LAYOUT_OPTIONS,
  type LayoutEdge,
  type Position,
  pinsFor,
  readPositions,
  toElkGraph,
} from "../elkGraph";
import {
  claimLines,
  firstFrame,
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
  return aWire({ source, target, ...extra });
}

describe("the map's layout", () => {
  it("test_layout_options_are_the_five_named", () => {
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

  it("test_pinned_tiles_keep_their_positions", async () => {
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

  it("test_a_cause_is_always_left_of_what_it_causes", async () => {
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

  it("test_the_layout_is_given_the_height_the_tile_is_drawn_at", async () => {
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
    return aClaim({
      claim: text,
      beliefs: {
        model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
        user: { absence: { kind: "not_said", words: "—", reason: "You have not said." } },
        market: { reading: { p: 0.48, lo: 0.45, hi: 0.52 } },
      },
      ...extra,
    });
  }

  /** The three slots, with no market number in the market slot. */
  const noMarket = {
    model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
    user: { absence: { kind: "not_said", words: "—", reason: "You have not said." } },
    market: {
      absence: { kind: "no_market", words: "no market", reason: "no venue quotes this claim" },
    },
  } as const;

  it("test_tile_height_is_decided_by_the_content", () => {
    const bare = tileHeight(claimOf("A short claim.", { beliefs: noMarket }));
    const deadEnd = tileHeight(
      claimOf("A short claim.", { kind: "not_tradeable", beliefs: noMarket }),
    );
    const withClippings = tileHeight(
      claimOf("A claim long enough to take three whole lines of the tile it is written on.", {
        evidence: [
          { line: "One.", monogram: "A", host: "a.com", direction: 1, url: "https://a.com/" },
          { line: "Two.", monogram: "B", host: "b.com", direction: -1, url: "https://b.com/" },
        ],
      }),
    );

    expect(bare).toBeLessThan(deadEnd);
    expect(deadEnd).toBeLessThan(withClippings);
  });

  it("test_only_a_claim_that_prints_a_reason_gets_room_for_one", () => {
    // Every claim without a market number says "no market" in two words on its
    // chip. Only the kind that ends the map without an instrument prints why on
    // the face of the tile, so only that one is given room for the sentence.
    const short = "A short claim.";
    expect(tileHeight(claimOf(short, { beliefs: noMarket }))).toBe(
      tileHeight(claimOf(short, { kind: "market", beliefs: noMarket })),
    );
    expect(
      tileHeight(claimOf(short, { kind: "not_tradeable", beliefs: noMarket })),
    ).toBeGreaterThan(tileHeight(claimOf(short, { beliefs: noMarket })));
  });

  it("test_tile_height_is_content_fit_within_152_and_320", () => {
    // The two numbers in this test's name are the two in the chapter, so they
    // are checked rather than taken on trust: a floor and a ceiling that drifted
    // from the words describing them would leave the name lying.
    expect(TILE_MIN_HEIGHT).toBe(152);
    expect(TILE_MAX_HEIGHT).toBe(320);

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

  it("test_claim_wraps_to_three_lines_and_never_cuts_mid_word", () => {
    expect(claimLines("Short.")).toBe(1);
    expect(claimLines("A".repeat(400))).toBe(3);
    // The number of lines the tile is built for is the number the claim is
    // allowed to draw, so the two can never disagree.
    expect(claimLines("")).toBe(1);
  });
});

describe("the eleven-pixel floor", () => {
  it("test_no_text_lands_under_eleven_pixels_at_any_zoom", () => {
    // Swept rather than spot-checked, because the whole point of the floor is
    // that there is no zoom at which it fails.
    for (let zoom = SMALLEST_ZOOM; zoom <= LARGEST_ZOOM + 0.0001; zoom += 0.005) {
      const onGlass = smallestTextAt(zoom) * zoom;
      expect(onGlass).toBeGreaterThanOrEqual(TEXT_FLOOR - 0.0001);
    }
  });

  it("test_the_summary_starts_exactly_where_a_full_tile_would_fall_below_the_floor", () => {
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
  it("test_within_layer_order_is_stable", () => {
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

  it("test_reflexive_links_are_set_aside_for_layering", () => {
    // The oil price feeds back on an output decision, which feeds back on the
    // oil price: a loop, and the only kind of loop the map allows. Left in, there
    // would be no leftmost claim at all.
    const links = [arrow("B", "R", { reflexive: true }), arrow("R", "B"), arrow("H", "B")];
    const layers = new Map(assignLayers(["H", "B", "R"], links).map((one) => [one.id, one.layer]));

    expect(layers.get("R")).toBe(0);
    expect(layers.get("H")).toBe(0);
    expect(layers.get("B")).toBe(1);
  });

  it("test_layer_cap_collapses_the_rest", () => {
    const wide = Array.from({ length: 10 }, (_, index) => `n${index}`);
    const { shown, overflows } = capLayers(assignLayers(wide, []));

    expect(shown).toHaveLength(TILES_PER_LAYER);
    expect(overflows).toHaveLength(1);
    expect(overflows[0]?.count).toBe(3);
    // The claims that are not drawn are named, so the collapsed tile is standing
    // in for something rather than covering something up.
    expect(overflows[0]?.hidden).toEqual(["n7", "n8", "n9"]);
  });

  it("test_a_column_that_fits_is_left_alone", () => {
    const { shown, overflows } = capLayers(assignLayers(["a", "b", "c"], []));
    expect(shown.map((one) => one.id)).toEqual(["a", "b", "c"]);
    expect(overflows).toHaveLength(0);
  });
});

describe("the union of two worlds", () => {
  /** The stored example's shape, as a list of tiles and the arrows between them. */
  const BASE: [string, number][] = [
    ["H", 280],
    ["C", 192],
    ["B", 176],
    ["R", 152],
    ["M1", 192],
    ["M2", 192],
    ["N1", 216],
  ];
  const BASE_ARROWS: LayoutEdge[] = [
    { id: "H->B", source: "H", target: "B" },
    { id: "H->C", source: "H", target: "C" },
    { id: "H->N1", source: "H", target: "N1" },
    { id: "C->B", source: "C", target: "B" },
    { id: "B->M1", source: "B", target: "M1" },
    { id: "B->M2", source: "B", target: "M2" },
    { id: "R->B", source: "R", target: "B" },
  ];

  it("test_union_layout_is_stable", async () => {
    // The strike adds S with three arrows, one of them into the hypothesis
    // itself — so every base claim moves one column right. That has to happen: a
    // cause cannot be drawn to the right of what it causes. What must **not**
    // happen is the two worlds being laid out separately, because then every
    // tile would appear to have moved and the diff would say nothing.
    const union: [string, number][] = [...BASE, ["S", 208]];
    const unionArrows: LayoutEdge[] = [
      ...BASE_ARROWS,
      { id: "S->B", source: "S", target: "B" },
      { id: "S->C", source: "S", target: "C" },
      { id: "S->H", source: "S", target: "H" },
    ];

    const once = await layout(union, unionArrows, new Map());
    const again = await layout(union, unionArrows, new Map());

    // One coordinate per claim, and the same one every time: the layout is a
    // pure function of the map.
    expect([...once.keys()].sort()).toEqual([...union.map(([id]) => id)].sort());
    expect(Object.fromEntries(again)).toEqual(Object.fromEntries(once));

    // And the union really is a map with a direction: the strike sits before the
    // claim it pushes against, which is what a diff over it can then be read on.
    expect(once.get("S")?.x ?? 0).toBeLessThan(once.get("H")?.x ?? 0);
    expect(once.get("H")?.x ?? 0).toBeLessThan(once.get("B")?.x ?? 0);
  });

  /**
   * The gap the layout leaves between two tiles that sit straight under one
   * another, as `LAYOUT_OPTIONS` sets it. Read back rather than written down
   * twice, so changing the setting changes what this checks.
   */
  const GAP = Number(LAYOUT_OPTIONS["elk.spacing.nodeNode"]);

  /**
   * Every pair of tiles in one column that leave less room between them than
   * they need.
   *
   * **Two different gaps, and only one of them is `nodeNode`.** Where nothing
   * passes between two tiles the layout leaves the full gap. Where a wire has to
   * cross that column on its way somewhere further right, the layout puts the
   * wire's lane between them instead, and the tiles sit closer with the lane in
   * the middle — on the stored example the wires from the hypothesis to Brent
   * run between the talks and the insurance premium, and take that room. That is
   * the layout doing its job, not two tiles crowding.
   *
   * So what is checked is the thing that is always wrong: **a pair that
   * overlaps, or touches.** A tile drawn taller than the box the layout reserved
   * for it shows up here and nowhere else.
   *
   * @param placed Where every tile ended up.
   * @param heights How tall each one will actually be drawn.
   */
  function collide(
    placed: ReadonlyMap<string, Position>,
    heights: ReadonlyMap<string, number>,
  ): string[] {
    const found: string[] = [];
    const tiles = [...placed].map(([id, at]) => ({ id, at, height: heights.get(id) ?? 0 }));
    for (const one of tiles) {
      for (const other of tiles) {
        if (one.id >= other.id || one.at.x !== other.at.x) {
          continue;
        }
        const [above, below] = one.at.y <= other.at.y ? [one, other] : [other, one];
        const between = below.at.y - (above.at.y + above.height);
        if (between <= 0) {
          found.push(`${above.id} runs into ${below.id}: ${between} between them`);
        }
      }
    }
    return found;
  }

  /** The tiles in one column, top to bottom, with the gaps between them. */
  function column(
    placed: ReadonlyMap<string, Position>,
    heights: ReadonlyMap<string, number>,
    ids: readonly string[],
  ): number[] {
    const tiles = ids
      .map((id) => ({ id, at: placed.get(id), height: heights.get(id) ?? 0 }))
      .filter((tile): tile is { id: string; at: Position; height: number } => tile.at !== undefined)
      .sort((a, b) => a.at.y - b.at.y);
    return tiles.slice(1).map((tile, i) => {
      const above = tiles[i] as { at: Position; height: number };
      return tile.at.y - (above.at.y + above.height);
    });
  }

  it("test_no_two_tiles_in_a_column_collide", async () => {
    // The map as it was written. Its one crowded column holds the talks, the
    // insurance premium and OPEC's announcement, and the whole gap is left
    // between the two of them that have nothing passing between.
    const heights = new Map(BASE);
    const asWritten = await layout(BASE, BASE_ARROWS, new Map());
    expect(collide(asWritten, heights)).toEqual([]);
    expect(column(asWritten, heights, ["N1", "C", "R"]).at(-1)).toBe(GAP);

    // And the strike branch, where six of the eight tiles are taller than they
    // were on the base map: each one that the edit can reach carries a line
    // saying how far its number moved. **That is the case this test exists for.**
    // Those tiles are placed on the branch's own layout and never at coordinates
    // worked out for the shorter boxes, so the gap survives the growth.
    const grown: [string, number][] = [
      ["H", 320],
      ["C", 224],
      ["B", 208],
      ["R", 152],
      ["M1", 224],
      ["M2", 224],
      ["N1", 248],
      ["S", 208],
    ];
    const branchArrows: LayoutEdge[] = [
      ...BASE_ARROWS,
      { id: "S->B", source: "S", target: "B" },
      { id: "S->C", source: "S", target: "C" },
      { id: "S->H", source: "S", target: "H" },
    ];
    const onTheBranch = await layout(grown, branchArrows, new Map());
    expect(collide(onTheBranch, new Map(grown))).toEqual([]);
    expect(column(onTheBranch, new Map(grown), ["N1", "C", "R"]).at(-1)).toBe(GAP);
  });

  it("test_a_pin_is_dropped_when_its_tile_changes_size", async () => {
    // The failure this prevents, in one run: lay the map out, then grow two
    // tiles and lay it out again with the old pins. A pin that survived the
    // growth would hold each grown tile where its shorter self went, and the
    // tile below it would be run into.
    const first = await layout(BASE, BASE_ARROWS, new Map());
    const placed = new Map(
      [...first].map(([id, at]) => [id, { at, height: new Map(BASE).get(id) ?? 0 }]),
    );

    const grown: [string, number][] = BASE.map(([id, height]) =>
      id === "C" || id === "M1" ? [id, height + 48] : [id, height],
    );
    const tiles = grown.map(([id, height]) => ({ id, height }));

    // Every pin goes, not only the two that changed size. A tile's place in a
    // column is decided by its neighbours as much as by itself, so keeping one
    // neighbour pinned while the other is placed afresh is what puts the two of
    // them in the same space.
    expect([...pinsFor(placed, tiles).keys()]).toEqual([]);

    const again = await layout(grown, BASE_ARROWS, pinsFor(placed, tiles));
    expect(collide(again, new Map(grown))).toEqual([]);
  });

  it("test_a_tile_arriving_keeps_every_pin", async () => {
    // The other half of the same rule, and the half the reader feels: a map that
    // grows must not move what is already drawn.
    const first = await layout(BASE, BASE_ARROWS, new Map());
    const placed = new Map(
      [...first].map(([id, at]) => [id, { at, height: new Map(BASE).get(id) ?? 0 }]),
    );
    const withOneMore: [string, number][] = [...BASE, ["M3", 192]];
    const tiles = withOneMore.map(([id, height]) => ({ id, height }));

    const holding = pinsFor(placed, tiles);
    expect([...holding.keys()].sort()).toEqual([...BASE.map(([id]) => id)].sort());

    const again = await layout(
      withOneMore,
      [...BASE_ARROWS, { id: "B->M3", source: "B", target: "M3" }],
      holding,
    );
    for (const [id] of BASE) {
      expect(again.get(id)).toEqual(first.get(id));
    }
  });

  it("test_the_first_frame_never_shows_a_summary_tile", () => {
    // The map is four columns wide and about eight hundred tall; the panel
    // beside it takes 336 pixels, the bar at the top and the two lines at the
    // foot take about 150, and what is left is what the map gets. Fitting the
    // whole thing into that lands just under the zoom at which a full tile has
    // to become a summary — so the frame is held at that zoom instead, and the
    // reader's first sight of the product is tiles they can read.
    const map = { x: 0, y: 0, width: 1480, height: 800 };
    const room = { width: 1600 - 336, height: 1000 - 150 };
    const frame = firstFrame(map, room);
    expect(frame.zoom).toBeGreaterThanOrEqual(SUMMARY_BELOW_ZOOM);
    expect(smallestTextAt(frame.zoom) * frame.zoom).toBeGreaterThanOrEqual(TEXT_FLOOR);
    // Never blown up past life size, however small the map.
    expect(firstFrame({ x: 0, y: 0, width: 300, height: 200 }, room).zoom).toBe(1);
  });

  it("test_a_map_too_big_to_fit_is_framed_from_its_beginning", () => {
    // The union is five columns wide, which does not fit beside the panel at a
    // readable zoom. The answer is the same one a tile gives when it runs out of
    // room: change what is shown, never shrink it below eleven pixels. So the
    // frame starts where the map starts and the reader pans to the rest.
    const frame = firstFrame(
      { x: 0, y: 0, width: 1880, height: 800 },
      { width: 1264, height: 850 },
    );
    expect(frame.zoom).toBe(SUMMARY_BELOW_ZOOM);
    expect(frame.x).toBeGreaterThan(0);
    expect(frame.x).toBeLessThan(40);
  });
});
