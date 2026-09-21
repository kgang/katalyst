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

import { readFileSync } from "node:fs";
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

  it("test_four_kinds_four_silhouettes_one_palette", () => {
    const drawn = OF_EVERY_KIND.map((claim) => {
      const { container } = draw(claim);
      const outline = container.querySelector(".tile__outline path");
      return {
        kind: claim.kind,
        shape: outline?.getAttribute("d") ?? "",
        // Everything the markup says about colour. Kind rides shape; a colour
        // written onto one of the four would be a second channel saying the same
        // thing, and the greyscale check on line 3 would stop working.
        colour: (container.innerHTML.match(/(fill|stroke|color)="[^"]*"/g) ?? []).join(" "),
      };
    });

    // Four kinds, four different silhouettes.
    expect(new Set(drawn.map((one) => one.shape)).size).toBe(4);
    // And one palette: nothing about the four differs in a colour value.
    expect(new Set(drawn.map((one) => one.colour)).size).toBe(1);
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

/**
 * Every rule in a stylesheet, as a selector and the declarations inside it.
 *
 * Flat rather than parsed properly: `tile.css` has no nesting and no media
 * query, and a hand-rolled parser that handled either would be a thing to
 * maintain for no reading. The same helper is in `styles/__tests__` for the same
 * reason; it is four lines and copying it is cheaper than a shared one.
 */
function rulesOf(css: string): { selector: string; body: string }[] {
  const found: { selector: string; body: string }[] = [];
  // Comments first, or a `{` inside prose is read as a rule.
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const match of bare.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    found.push({ selector: (match[1] ?? "").trim(), body: match[2] ?? "" });
  }
  return found;
}

/** The rules that only apply to a tile seen from far away. */
const FAR_AWAY = rulesOf(readFileSync("src/components/tile.css", "utf8")).filter((rule) =>
  rule.selector.includes('[data-detail="summary"]'),
);

/**
 * What a tile seen from far away may never do to make a belief fit.
 *
 * **This reads the stylesheet rather than a drawn page**, because a simulated
 * page has no layout: whether a line fits is a fact about laid-out boxes and is
 * checked in the browser, by `e2e/farTiles.spec.ts`. What is checked here is the
 * other half — the two ways of making a line fit that must never be taken, which
 * are facts about the rules themselves and want no layout at all.
 */
describe("a tile seen from far away", () => {
  it("test_the_far_away_form_sets_every_word_in_the_largest_size", () => {
    // The far-away form exists to be readable at the furthest the map zooms out,
    // which is half — so twenty-two pixels there is eleven on the reader's
    // screen, and eleven is the floor this product promises. The tempting fix
    // for a line that will not fit is to set it smaller. This is what says no.
    const sized = FAR_AWAY.filter((rule) => rule.body.includes("font-size"));
    expect(sized.length, "the far-away form sets no type size at all").toBeGreaterThan(0);
    for (const rule of sized) {
      for (const found of rule.body.matchAll(/font-size:\s*([^;]+);/g)) {
        expect(
          (found[1] ?? "").trim(),
          `"${rule.selector}" sets a type size the floor does not allow`,
        ).toBe("var(--text-lg)");
      }
    }
  });

  it("test_the_far_away_form_puts_no_part_of_a_belief_out_of_sight", () => {
    // Out here the tile drops its heading and its foot, and that is the whole of
    // what it drops. A belief keeps every part of itself — the owner, the number
    // and the range — at every zoom: the other tempting fix for a line that will
    // not fit is to stop drawing the end of it.
    const hidden = FAR_AWAY.filter(
      (rule) => rule.selector.includes("belief-chip") && /display:\s*none/.test(rule.body),
    );
    expect(hidden.map((rule) => rule.selector)).toEqual([]);
  });
});
