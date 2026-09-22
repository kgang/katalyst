/**
 * **No range, and no versions of the map, anywhere on the screen.**
 *
 * Kent cut the two thousand versions of the map from this product on
 * 2026-09-22 (R48): one likelihood per claim, no range on a tile, in the panel,
 * on the change list, in a footer sentence or in a hover note. This file is the
 * one place that holds the whole of that rule up, the way
 * `styles/__tests__/colourLaw.test.ts` holds up the colour law: every other test
 * in this tree could pass while a range crept back onto one surface.
 *
 * Three walks, and each catches what the others cannot.
 *
 * 1. **Every tile**, on the curated map and on a real recording played back
 *    through the app's own reader. A tile is where a range lived longest and
 *    where a reader meets one first.
 * 2. **Every tile and the panel beside it**, read as a reader would hear them,
 *    for the words that only meant something under the versions: *version*,
 *    *versions*, *worlds*, *interval*, *uncalibrated*, *middle 80*.
 * 3. **Every string literal in the product's own source**, so that a sentence
 *    which is written but not reachable from these fixtures is caught too. A
 *    rendering test can only walk the states it can build.
 *
 * **Nothing here asserts a typed-in number.** It asserts shapes and words: that
 * no printed reading is a pair with a dash between it, that no forbidden word is
 * on the glass, and that the line a range used to stand on is gone rather than
 * empty.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { render } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import ts from "typescript";
import { describe, expect, it } from "vitest";
import { Inspector } from "../../components/Inspector";
import { Tile } from "../../components/Tile";
import { A_REAL_RUN, THE_REAL_SENTENCE } from "../../stream/__tests__/aRealRun";
import { BELIEFS, THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import { foldAll, waitingFor } from "../../stream/growth";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { ClaimView, WorldView } from "../../world";
import { absence } from "../../world/absence";

/**
 * The words that only ever meant something while the map was run two thousand
 * times, and that no surface may print now.
 *
 * *interval* is here as a whole word so that `setInterval` — an identifier, not
 * a sentence — is not what trips it.
 */
const FORBIDDEN = [
  /\bversions?\b/i,
  /\bworlds\b/i,
  /\binterval\b/i,
  /\buncalibrated\b/i,
  /middle 80/i,
  // The engine's own spelling, which an underscore hides from the pattern above.
  // It is a wire word and is never printed: `graph/diff/noChange.ts` turns it
  // into *the engine could not settle which way it moves*, which is what a
  // reader is owed under R4 and says nothing about versions of the map.
  /versions_disagree/i,
];

/**
 * The words the engine writes on a wire, which the browser copies and never
 * prints.
 *
 * They are taken out of a **source** file before the words above are looked for,
 * and never out of anything rendered: a wire word that reached the glass is
 * exactly the fault this file exists to catch, so the rendered walk keeps them
 * forbidden and only the source walk names the exemption.
 */
const WIRE_WORDS = /versions_disagree/g;

/**
 * A reading with a range in it, however it is spelled.
 *
 * `.22–.50` is the form the chip printed, `.35 (.22–.50)` the form a sentence
 * used, and `<.01–.03` the form the certainty guard gave the bottom end. All
 * three are one shape: a printed likelihood, a dash, and another printed
 * likelihood.
 */
const A_RANGE = /[.>]\s*\d[\d.]*\s*[–—-]\s*[.<>]\s*\d/;

/**
 * The one address on this screen with the word *worlds* in it, which is not a
 * word about the multiverse at all: it is where the engine is asked.
 *
 * It is taken out before the words are looked for, rather than the rule being
 * softened, so that the rule stays *no surface says worlds* and the one
 * exception is named here and nowhere else.
 */
const THE_ROUTE = /\/api\/worlds(\/[a-z]+)?/g;

/** The curated map, in the shape the stored example has: three voices on a claim. */
function curated(): WorldView {
  return aWorld({
    hypothesisId: "H",
    claims: [
      aClaim({
        id: "H",
        kind: "hypothesis",
        claim: "The Strait of Hormuz reopens to unrestricted commercial transit.",
        beliefs: {
          model: { reading: { p: 0.35 } },
          user: { reading: { p: 0.55 } },
          market: { absence: absence("no_market", "no venue quotes this claim") },
        },
      }),
      aClaim({
        id: "B",
        claim: "Brent crude settles below $68 for five sessions.",
        // A claim the reader's edit moved, which is where the panel used to
        // print the share of the versions that agreed.
        diff: "shifted",
        moved: { from: 0.456, to: 0.414, way: "down", by: -0.0421 },
      }),
      aClaim({
        id: "S",
        claim: "A confirmed military strike on Iranian territory.",
        // A claim standing on the reader's own say-so, which is the one chip
        // that shows a word where a likelihood would go.
        standing: {
          words: "Supposed · Oct 2",
          reason: "You supposed this true on the 2nd.",
        },
      }),
      aClaim({
        id: "M1",
        kind: "market",
        claim: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
        beliefs: {
          model: { reading: { p: 0.46 } },
          user: { absence: absence("not_said", "You have not said.") },
          market: { reading: { p: 0.48 } },
        },
      }),
      aClaim({
        id: "N1",
        kind: "not_tradeable",
        claim: "Omani-mediated United States-Iran talks resume publicly.",
      }),
    ],
    links: [
      aWire({ source: "H", target: "B" }),
      aWire({ source: "B", target: "M1" }),
      aWire({ source: "S", target: "B" }),
    ],
  });
}

/**
 * The same recording the app plays back, folded through the app's own reader.
 *
 * Two of them, because a growing map and a finished one draw different chips: on
 * the way up every likelihood reads its absence, and at the end every one of
 * them is the engine's own number arriving through `toWorldView`.
 */
function replayed(): WorldView[] {
  return [
    foldAll(waitingFor(THE_REAL_SENTENCE, null), A_REAL_RUN).world,
    foldAll(waitingFor(THE_SENTENCE, null), [...THE_GROWTH, BELIEFS]).world,
  ];
}

/** Draw one tile the way the map draws it, and hand back what is on the glass. */
function tileText(claim: ClaimView): { text: string; element: HTMLElement } {
  const { container, unmount } = render(
    <ReactFlowProvider>
      <Tile claim={claim} isHypothesis={claim.kind === "hypothesis"} />
    </ReactFlowProvider>,
  );
  const element = container.cloneNode(true) as HTMLElement;
  const text = container.textContent ?? "";
  unmount();
  return { text, element };
}

/** Open the panel on one claim, and hand back what it says. */
function panelText(world: WorldView, id: string): string {
  const { container, unmount } = render(
    <Inspector world={world} selection={{ kind: "claim", id }} />,
  );
  const text = container.textContent ?? "";
  unmount();
  return text;
}

describe("no tile draws a range", () => {
  it("test_the_maps_being_walked_are_really_there", () => {
    // A walk over nothing is a walk that always passes.
    expect(curated().claims.length).toBeGreaterThan(4);
    for (const world of replayed()) {
      expect(world.claims.length).toBeGreaterThan(4);
    }
  });

  it("test_no_tile_draws_a_range", () => {
    for (const world of [curated(), ...replayed()]) {
      for (const claim of world.claims) {
        const { text, element } = tileText(claim);
        expect(text, `${claim.id} prints a range`).not.toMatch(A_RANGE);
        // And the line a range stood on is gone rather than standing empty: an
        // empty line still takes its height, and this is the rule that says the
        // chip is two lines and not three.
        expect(element.querySelector(".belief-chip__under")).toBeNull();
        // Every chip that draws a number draws exactly one reading.
        for (const chip of element.querySelectorAll('.belief-chip[data-reading="number"]')) {
          expect([...chip.querySelectorAll(".belief-chip__face > *")]).toHaveLength(2);
        }
      }
    }
  });

  it("test_no_panel_draws_a_range", () => {
    for (const world of [curated(), ...replayed()]) {
      for (const claim of world.claims) {
        expect(panelText(world, claim.id), `the panel on ${claim.id} prints a range`).not.toMatch(
          A_RANGE,
        );
      }
    }
  });
});

describe("nothing on screen mentions versions or worlds", () => {
  it("test_nothing_on_screen_mentions_versions_or_worlds", () => {
    for (const world of [curated(), ...replayed()]) {
      for (const claim of world.claims) {
        const said = [tileText(claim).text, panelText(world, claim.id)]
          .join(" ")
          .replace(THE_ROUTE, " ");
        for (const word of FORBIDDEN) {
          expect(said, `${claim.id} says ${word}`).not.toMatch(word);
        }
      }
    }
  });

  it("test_the_sentence_under_a_map_keeps_the_seed_and_drops_the_versions", () => {
    // The route, the generation and the seed are facts a reader can act on: the
    // same map, branch and seed give the same answer again. How many versions of
    // the map the engine tried, and how many worlds it ran under each, are not.
    for (const world of replayed()) {
      const origin = world.origin.replace(THE_ROUTE, " ");
      for (const word of FORBIDDEN) {
        expect(origin).not.toMatch(word);
      }
    }
    const finished = replayed()[1] as WorldView;
    expect(finished.origin).toMatch(/seed/);
    expect(finished.origin).toMatch(/generation/);
  });
});

/* ---- The third walk: the product's own source --------------------------- */

/**
 * Every sentence written into the product's own source, with the code around it
 * left out.
 *
 * **It is read with the compiler's own reader**, rather than by hunting for
 * quotation marks: a file of this product is TypeScript with markup in it, and
 * an apostrophe in *Lloyd's war-risk premium* — which is markup, not a string —
 * is enough to send a hand-rolled scanner off into the rest of the file. So the
 * compiler parses it and this walks the tree, collecting the three things a
 * reader can end up seeing: a quoted string, a piece of a template, and the text
 * between two tags.
 *
 * A comment is not one of them, deliberately. This file's own commentary names
 * the words it forbids, and so does every passage that records why a sentence
 * was taken out.
 *
 * @param path What the file is called, which the compiler wants.
 * @param source The file's text.
 * @returns Every sentence in it, in the order they were written.
 */
function everySentence(path: string, source: string): string[] {
  const tree = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const walk = (node: ts.Node): void => {
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node) ||
      ts.isJsxText(node)
    ) {
      found.push(node.text);
    }
    ts.forEachChild(node, walk);
  };
  walk(tree);
  return found;
}

/** Every product file in the tree: no test, and nothing generated. */
function everyProductFile(from: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) {
      if (name === "__tests__" || name === "test") continue;
      Object.assign(found, everyProductFile(path));
      continue;
    }
    if (!/\.tsx?$/.test(name)) continue;
    if (/\.test\.|\.test-d\./.test(name)) continue;
    // Generated from the server's own description of itself and never edited by
    // hand, so the words in it are the server's field names, not our sentences.
    if (path.endsWith(join("api", "schema.ts"))) continue;
    found[`/${path.replaceAll("\\", "/")}`] = readFileSync(path, "utf8");
  }
  return found;
}

const PRODUCT = everyProductFile("src");

describe("no sentence in the product says versions or worlds", () => {
  it("test_the_files_being_walked_are_really_there", () => {
    expect(Object.keys(PRODUCT).length).toBeGreaterThan(40);
    expect(PRODUCT["/src/components/BeliefChip.tsx"]).toBeDefined();
    expect(PRODUCT["/src/components/Inspector.tsx"]).toBeDefined();
    // And the scanner really reads sentences rather than returning nothing.
    expect(
      everySentence("Tile.tsx", PRODUCT["/src/components/Tile.tsx"] ?? "").length,
    ).toBeGreaterThan(5);
  });

  it("test_no_string_in_the_product_mentions_versions_or_worlds", () => {
    const said: string[] = [];
    for (const [path, source] of Object.entries(PRODUCT)) {
      for (const sentence of everySentence(path, source)) {
        const words = sentence.replace(THE_ROUTE, " ").replace(WIRE_WORDS, " ");
        if (FORBIDDEN.some((word) => word.test(words))) {
          said.push(`${path}: ${sentence}`);
        }
      }
    }
    expect(said).toEqual([]);
  });

  it("test_no_string_in_the_product_prints_a_range", () => {
    const said: string[] = [];
    for (const [path, source] of Object.entries(PRODUCT)) {
      for (const sentence of everySentence(path, source)) {
        if (A_RANGE.test(sentence)) {
          said.push(`${path}: ${sentence}`);
        }
      }
    }
    expect(said).toEqual([]);
  });
});
