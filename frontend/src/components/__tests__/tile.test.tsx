/**
 * What a tile says about a claim whose number moved.
 *
 * The fifth state, `shifted`, is the one that needed the engine: it takes two
 * numbers to compare, so nothing in the browser can produce one and nothing
 * here works one out. The tile prints the two readings the engine gave, with a
 * chevron between them saying which way it went, and the sentence behind them
 * carries the word — so the direction survives a grey print and a reader who
 * never sees the tile.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import { TILE_MIN_HEIGHT, TILE_WIDTH, tileHeight } from "../../graph/geometry";
import type { ReadEvent } from "../../stream/events";
import { joined } from "../../stream/generate";
import { foldAll, waitingFor } from "../../stream/growth";
import { aClaim } from "../../test/aMap";
import type { BeliefOwner, ClaimView, WorldView } from "../../world";
import { absence } from "../../world/absence";
import { SkeletonTile } from "../SkeletonTile";
import { Tile } from "../Tile";

/** Draw one tile. The map's provider is what tells a tile how far it is zoomed. */
function draw(claim: ClaimView) {
  return render(
    <ReactFlowProvider>
      <Tile claim={claim} isHypothesis={false} versions={2000} />
    </ReactFlowProvider>,
  );
}

/** Whose belief columns this tile drew, in the order it drew them. */
function columnsOf(container: HTMLElement): (string | null)[] {
  return [...container.querySelectorAll(".belief-chip")].map((chip) =>
    chip.getAttribute("data-owner"),
  );
}

/** The two columns that are drawn only when they hold a number. */
const ON_REQUEST: readonly BeliefOwner[] = ["user", "market"];

/**
 * Every source file in the tree, by the path the rules below name it by.
 *
 * Read as text, so that a rule added in a stylesheet nobody thought about is
 * still found. It is the same technique the colour law and the no-spinner check
 * already use.
 */
function everySourceFile(from: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) {
      Object.assign(found, everySourceFile(path));
    } else if (/\.(ts|tsx|css)$/.test(name)) {
      found[`/${path.replaceAll("\\", "/")}`] = readFileSync(path, "utf8");
    }
  }
  return found;
}

const EVERY_SOURCE_FILE = everySourceFile("src");

/**
 * The map a reviewer with no key actually watches build, folded by the app's
 * own reducer from the recording the app itself replays.
 *
 * **Read off the committed recording rather than written here.** Every browser
 * test in this tree plays the curated example, which is the one map where a
 * reader's number and a venue's quote both exist — so two thirds of every real
 * tile's belief area being an absence was invisible to all of them. The
 * recording is the same bytes `/api/generate` sends back on a keyless copy: one
 * JSON object per line, the first the header and every line after it one event,
 * carrying the two fields the wire carries. So the events go through `joined`,
 * the same reader the stream uses, and through `foldAll`, the same reducer the
 * screen folds with. Nothing about this map is built here.
 */
function theGeneratedMap(): WorldView {
  const file = readFileSync("../backend/recordings/hormuz.jsonl", "utf8");
  const events: ReadEvent[] = [];
  for (const line of file.split("\n")) {
    if (line.trim() === "") {
      continue;
    }
    const recorded = JSON.parse(line) as { event?: string; data?: unknown };
    // The header line is the one line with no event name on it.
    if (recorded.event === undefined) {
      continue;
    }
    events.push(joined(recorded.event, JSON.stringify(recorded.data)));
  }
  // The sentence is the one the run was started from, and the run's own first
  // event repeats it back — so the reducer takes it from the recording too.
  return foldAll(waitingFor(""), events).world;
}

/**
 * A claim the engine says moved, as the branch world hands one to a tile.
 *
 * The badge is built where the engine's answer meets the claim, which is why it
 * is written out here rather than derived: this file is about what a tile draws
 * when it is given one.
 */
const MOVED: ClaimView = aClaim({
  id: "M1",
  kind: "market",
  claim: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
  diff: "shifted",
  beliefs: {
    model: { reading: { p: 0.414, lo: 0.284, hi: 0.553 } },
    user: { absence: absence("not_said", "You have not said.") },
    market: {
      absence: absence("no_market", "no venue quotes this claim"),
    },
  },
  moved: {
    from: 0.456,
    to: 0.414,
    way: "down",
    by: -0.0421,
    sameDirection: { reading: 0.9663 },
  },
  badges: [
    {
      words: ".46 ▼ .41",
      reason:
        "Your edit moved this claim down, from .46 to .41, read on the day this claim is " +
        "judged. 97% of the versions of the map moved the same way.",
      movement: true,
    },
  ],
});

describe("a tile whose number moved", () => {
  it("test_a_shifted_tile_shows_before_and_after_with_a_chevron", () => {
    const { container } = draw(MOVED);

    // The two readings the engine gave, at two significant figures, with the
    // chevron between them.
    expect(screen.getByText(".46 ▼ .41")).toBeInTheDocument();

    // The state is on the tile itself, so the picture can draw it and a test can
    // read it back.
    expect(container.querySelector(".tile")?.getAttribute("data-diff")).toBe("shifted");

    // Which way it went is also a word, in the sentence behind the badge and in
    // what the tile is called when it is read out — never a chevron on its own
    // and never a colour.
    const badge = screen.getByRole("button", { name: /moved this claim down/ });
    expect(badge).toBeInTheDocument();
    expect(container.querySelector(".tile")?.getAttribute("aria-label")).toContain(
      "your edit moved this number",
    );
  });

  it("test_a_moved_reading_is_set_in_the_number_face", () => {
    const { container } = draw(MOVED);
    // Two numbers with a direction between them, not a label: it takes the face
    // and the tabular digits every number in this product is set in.
    const badge = container.querySelector('.tile__badge[data-badge="movement"]');
    expect(badge).not.toBeNull();
  });

  it("test_the_retraction_badge_comes_from_the_world", () => {
    // The world carries the retraction itself — which claim, which day, which
    // arrow and whose doing — and the badge is read off that record rather than
    // derived a second time from the branch. Two derivations of one line
    // eventually disagree, so there is one. What this checks is the other half:
    // that the tile draws what it was handed, in order, with the arrow between
    // the two that says the second took back the first.
    const overridden = aClaim({
      id: "H",
      kind: "hypothesis",
      claim: "The Strait of Hormuz reopens to unrestricted commercial transit.",
      diff: "shifted",
      badges: [
        { words: "Supposed · Oct 1", reason: "You supposed this is true, from Oct 1." },
        {
          words: 'Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"',
          reason: "A later edit added an arrow into it and then made that cause true.",
          overrides: true,
        },
      ],
    });
    const { container } = draw(overridden);

    expect(
      [...container.querySelectorAll(".tile__badge-words")].map((one) => one.textContent),
    ).toEqual([
      "Supposed · Oct 1",
      'Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"',
    ]);
    expect(container.querySelector(".tile__badge-arrow")?.textContent?.trim()).toBe("→");

    // And a claim the world reports no retraction for carries no such badge.
    const plain = draw(aClaim({ id: "C", badges: [] }));
    expect(plain.container.textContent).not.toContain("Retracted");
  });

  it("test_a_tile_with_no_move_draws_no_movement_badge", () => {
    const { container } = draw(aClaim({ id: "R", diff: "untouched", badges: [] }));
    expect(container.querySelector('.tile__badge[data-badge="movement"]')).toBeNull();
    expect(container.querySelector(".tile")?.getAttribute("aria-label")).toContain(
      "your edit cannot reach this",
    );
  });
});

/**
 * The six things a tile draws, and the five statements about them that the
 * chapter names and nobody had written.
 *
 * Every one of them is checked over tiles **built** here rather than over one
 * written out by hand: four kinds, claims of several lengths, with and without
 * clippings, so that a statement of the form *for every tile* is checked against
 * more than one.
 */
describe("what a tile draws, and what it never draws", () => {
  /** One tile of each of the four kinds, which is the set every claim is one of. */
  const OF_EVERY_KIND: readonly ClaimView[] = [
    aClaim({ id: "H", kind: "hypothesis" }),
    aClaim({ id: "C", kind: "event" }),
    aClaim({ id: "M1", kind: "market" }),
    aClaim({
      id: "N1",
      kind: "not_tradeable",
      beliefs: {
        model: { reading: { p: 0.3, lo: 0.16, hi: 0.45 } },
        user: { absence: absence("not_said", "You have not said.") },
        market: {
          absence: absence("no_market", "No venue quotes whether talks resume."),
        },
      },
    }),
  ];

  it("test_tile_is_280_wide_and_on_the_eight_pixel_grid", () => {
    // Claims of several lengths, so that "for every tile" is checked against
    // tiles the content made different sizes rather than against one.
    const lengths = [8, 40, 120, 400];
    for (const length of lengths) {
      const claim = aClaim({ claim: "word ".repeat(Math.ceil(length / 5)).trim() });
      const { container } = draw(claim);
      const box = container.querySelector<HTMLElement>(".tile");

      // Measured off the tile's own box rather than eyeballed, and off the same
      // function the layout reserved room with — so the box the map held open and
      // the box the browser drew are the same box.
      expect(box?.style.width).toBe(`${TILE_WIDTH}px`);
      expect(box?.style.height).toBe(`${tileHeight(claim)}px`);
      expect(tileHeight(claim) % 8).toBe(0);
      expect(tileHeight(claim)).toBeGreaterThanOrEqual(TILE_MIN_HEIGHT);
    }
  });

  it("test_tile_draws_the_six_regions_and_no_seventh", () => {
    // Six things, and a seventh always arrives at the cost of the six: the claim,
    // the three chips, at most two clippings, the day it settles, the outline
    // that says what kind of claim it is, and a place for its badges.
    const REGIONS = new Set([
      "tile__outline",
      "tile__header",
      "tile__claim",
      "tile__beliefs",
      "tile__foot",
    ]);

    for (const claim of OF_EVERY_KIND) {
      const { container } = draw({
        ...claim,
        badges: [{ words: "Added", reason: "Your edit added this claim." }],
      });
      const drawn = [...(container.querySelector(".tile")?.children ?? [])]
        // Read off the attribute rather than the property, because the outline is
        // a drawing and a drawing's class property is not a string.
        .map((one) => one.getAttribute("class") ?? "")
        // The four sockets are not a content region: they are where a wire lands,
        // and the drawing library owns them.
        .filter((name) => !name.includes("tile__port"));
      for (const name of drawn) {
        expect(REGIONS.has(name)).toBe(true);
      }
      // The day it settles and what kind it is share the heading row, which is
      // why five elements carry six things.
      expect(container.querySelector(".tile__resolves")).not.toBeNull();
      expect(container.querySelector(".tile__kind")).not.toBeNull();
    }

    // **A skeleton is a box, not a tile**, and it is excluded by name. It has
    // none of the six: no chips, no clippings, no day, no kind, no badges — one
    // line of words and a border, and nothing else.
    const reserved = render(<SkeletonTile words="one step on from a claim that is still open" />);
    expect(reserved.container.querySelector(".tile")).toBeNull();
    expect(reserved.container.querySelector(".belief-chip")).toBeNull();
    expect(reserved.container.querySelector(".tile__clippings")).toBeNull();
    expect(reserved.container.querySelector("time")).toBeNull();
  });

  it("test_tile_draws_one_chip_per_voice_and_never_a_fourth", () => {
    for (const claim of OF_EVERY_KIND) {
      const { container } = draw(claim);
      // One chip per voice with something to say, in this order, and never a
      // fourth: if the model says .61 and the market says .48 the gap is the
      // thing worth trading, and .545 is a number nobody holds. None of these
      // four claims carries a reader's number or a venue's quote, so each draws
      // the model's column and nothing else.
      expect(columnsOf(container)).toEqual(["model"]);
    }
  });

  it("test_a_tile_says_its_kind_with_no_hue_at_all", () => {
    // Two of the four kinds now take a hue as well — the hypothesis the teal
    // accent it already borrowed, a tradeable outcome the one new hue — because
    // those two are the ends of the map and a reader is hunting for them. Hue is
    // the third saying of the kind and never the only one, so this reads the
    // tile with every colour taken away and asks the same question: can you
    // still tell the four apart? Nothing below looks at a colour value, so no
    // version of this test can ever pass on one.
    const drawn = OF_EVERY_KIND.map((claim) => {
      const { container } = draw(claim);
      return {
        kind: claim.kind,
        shape: container.querySelector(".tile__outline path")?.getAttribute("d") ?? "",
        word: container.querySelector(".tile__kind")?.textContent ?? "",
      };
    });

    // Four kinds, four different silhouettes, and four different words.
    expect(new Set(drawn.map((one) => one.shape)).size).toBe(4);
    expect(new Set(drawn.map((one) => one.word)).size).toBe(4);
    for (const one of drawn) {
      expect(one.shape).not.toBe("");
      expect(one.word).not.toBe("");
    }

    // And the one kind whose outline is drawn a second time — the cut corner of
    // a tradeable outcome — draws a line, not a colour: the same diagonal its
    // own silhouette already has, so a grey print keeps it too.
    const stub = draw(OF_EVERY_KIND.find((one) => one.kind === "market") as ClaimView);
    expect(stub.container.querySelector(".tile__outline .tile__cut")).not.toBeNull();
    for (const claim of OF_EVERY_KIND.filter((one) => one.kind !== "market")) {
      expect(draw(claim).container.querySelector(".tile__cut")).toBeNull();
    }
  });

  it("test_the_kind_hue_is_named_only_by_the_tiles_own_stylesheet", () => {
    // The tile's stylesheet is the one place allowed to say `--kind-market`.
    // Everywhere else naming it would be a second place a kind could be
    // coloured — and the place it must never reach is a number: a hue on a
    // number means which way the money moves, which is a different thing
    // entirely. This is the same walk that keeps the two direction colours
    // inside `DirectionReadout`.
    const allowed = new Set([
      "/src/styles/tokens.css",
      "/src/components/tile.css",
      "/src/components/__tests__/tile.test.tsx",
      "/src/styles/__tests__/colourLaw.test.ts",
    ]);
    // A check that silently walks nothing is a check that always passes.
    expect(Object.keys(EVERY_SOURCE_FILE).length).toBeGreaterThan(20);
    expect(EVERY_SOURCE_FILE["/src/components/tile.css"] ?? "").toContain("--kind-market");
    const offenders = Object.entries(EVERY_SOURCE_FILE)
      .filter(([path, text]) => !allowed.has(path) && text.includes("--kind-market"))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it("test_clipping_draws_a_monogram_and_requests_nothing_outside", () => {
    const withClippings = aClaim({
      evidence: [
        {
          line: "Transits resumed under naval escort on Friday.",
          monogram: "B",
          host: "bbc.com",
          direction: 1,
          url: "https://www.bbc.com/news/a-story",
        },
        {
          line: "Underwriters are holding their rates for now.",
          monogram: "L",
          host: "lloydslist.com",
          direction: -1,
          url: "https://lloydslist.com/a-story",
        },
      ],
    });
    const { container } = draw(withClippings);

    // The letter is the publication's own host name's first letter, out of the
    // clipping's own data — a letter rather than an icon, because an icon is a
    // request to somebody else's server.
    const monograms = [...container.querySelectorAll(".tile__monogram")].map(
      (one) => one.textContent,
    );
    expect(monograms).toEqual(["B", "L"]);
    for (const [place, mark] of monograms.entries()) {
      expect(mark).toBe(withClippings.evidence[place]?.host.slice(0, 1).toUpperCase());
    }

    // And nothing rendered would fetch anything from outside this app.
    const markup = container.innerHTML;
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("iframe")).toBeNull();
    expect(markup).not.toContain("src=");
    expect(markup).not.toContain("url(");
    expect(markup).not.toContain("https://");
  });

  it("test_a_belief_column_with_a_number_is_still_drawn", () => {
    // The other half of the rule, and the half a map full of absences cannot
    // show: where the reader has given a number and a venue is quoting one,
    // all three columns are there, in their order, exactly as before.
    //
    // The readings are the builder's own — this test is about which columns are
    // drawn and never about what is in them, so no number is typed here.
    const stated = aClaim().beliefs.model;
    const quoted = aClaim({ beliefs: { model: stated, user: stated, market: stated } });
    const { container } = draw(quoted);

    expect(columnsOf(container)).toEqual(["model", "user", "market"]);
    // And every one of them is showing a number rather than words.
    for (const chip of container.querySelectorAll(".belief-chip")) {
      expect(chip.getAttribute("data-reading")).toBe("number");
    }
  });

  it("test_no_tail_marking_is_drawn_from_fixture_data_alone", () => {
    // A tail is a claim that is unlikely and large enough to matter, and nothing
    // on the map says which claim that is without arithmetic. So nothing in this
    // stack draws one — not from a stored example, and not from a generated map.
    for (const claim of OF_EVERY_KIND) {
      const { container } = draw(claim);
      const markup = container.innerHTML;
      expect(markup).not.toContain("--tail");
      expect(markup).not.toContain("repeating-linear-gradient");
      // "tail" as a word of its own, so that the word inside *detail* — which is
      // how far a tile is zoomed and has nothing to do with a tail — does not
      // make this fail for the wrong reason.
      expect(markup).not.toMatch(/(^|[-_\s"])tail([-_\s"]|$)/);
    }
  });
});

/**
 * **A belief column with nothing in it is not drawn** — checked on the map a
 * reviewer with no key actually walks.
 *
 * Kent, 2026-09-21: *"In each of the nodes, the empty user specified values and
 * the market values add visual clutter. The user and market values should only
 * be viewable if they exist."*
 *
 * The rule is one line and takes no exception: **the model's column is always
 * drawn; the reader's and a venue's are drawn when they hold a number.** The
 * model's is always there because on a map that is still being built it is the
 * column that says so, and because it is the one voice every claim on every map
 * has.
 *
 * It is checked here on the recorded generation rather than on the curated
 * example, and that is the whole point of this block: the curated example is the
 * one map where a reader's number and a venue's quote both exist, so every
 * browser test in this tree passed over a map two thirds of whose belief cells
 * were absences without noticing one of them.
 *
 * **Where the absences went: nowhere new.** The panel beside the map draws all
 * three rows whatever they hold and prints each absence's own reason in full —
 * *no venue quotes this claim* — which is where a reason has room to be a
 * sentence. The tile stops repeating them down a column.
 */
describe("the belief columns a tile draws", () => {
  it("test_a_belief_column_with_no_number_is_not_drawn", () => {
    const map = theGeneratedMap();
    // The recording really did build a map — a fold that read nothing would
    // pass every statement below by having nothing to check.
    expect(map.claims.length).toBeGreaterThan(1);

    for (const claim of map.claims) {
      const { container } = draw(claim);
      // Exactly the model's column, plus whichever of the other two hold a
      // number — read off the claim the fold produced, never listed here.
      expect(columnsOf(container)).toEqual([
        "model",
        ...ON_REQUEST.filter((owner) => claim.beliefs[owner].reading !== undefined),
      ]);
      // And no column but the model's is standing there showing words.
      for (const chip of container.querySelectorAll(".belief-chip")) {
        if (chip.getAttribute("data-owner") === "model") {
          continue;
        }
        expect(chip.getAttribute("data-reading")).toBe("number");
      }
    }
  });

  it("test_on_the_generated_map_every_tile_is_down_to_one_column", () => {
    // What the rule is worth on this map, stated as the two counts it is worth
    // it because of. Not one of these claims carries a reader's number or a
    // venue's quote, so every tile loses two of its three columns — which is
    // the clutter Kent met and none of our tests had ever seen.
    const map = theGeneratedMap();
    const quiet = map.claims.filter(
      (claim) =>
        claim.beliefs.user.reading === undefined && claim.beliefs.market.reading === undefined,
    );
    expect(quiet).toHaveLength(map.claims.length);

    const drawn = map.claims.reduce((sofar, claim) => {
      const { container } = draw(claim);
      return sofar + columnsOf(container).length;
    }, 0);
    expect(drawn).toBe(map.claims.length);
  });

  it("test_the_reserved_height_is_the_same_whether_one_column_is_drawn_or_three", () => {
    // **The map measures nothing**, so a tile that changed size when a column
    // went would be a tile drawn in a box of another size — two tiles on one
    // spot, which is the collision the layout exists to prevent. The belief rail
    // is a constant: the same room is held whatever the chips hold, and a number
    // arriving later widens the survivors and re-lays out nothing.
    //
    // Checked over the whole generated map rather than one claim, so that
    // "whatever the claim" is checked against eighteen of them, each a different
    // length. The readings written over the top are the same slot the claim
    // already carries, so nothing here types a number.
    const stated = aClaim().beliefs.model;
    for (const quiet of theGeneratedMap().claims) {
      const quoted: ClaimView = {
        ...quiet,
        beliefs: { model: quiet.beliefs.model, user: stated, market: stated },
      };

      // The height the layout reserves is worked out from the claim, and the
      // claim is the same one.
      expect(tileHeight(quoted)).toBe(tileHeight(quiet));

      // And the box the browser is told to draw is the same box, both ways.
      const one = draw(quiet).container.querySelector<HTMLElement>(".tile");
      const three = draw(quoted).container.querySelector<HTMLElement>(".tile");
      expect(columnsOf(draw(quoted).container)).toHaveLength(3);
      expect(three?.style.height).toBe(one?.style.height);
      expect(three?.style.width).toBe(one?.style.width);
    }
  });
});
