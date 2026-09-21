/**
 * The canvas does no arithmetic on the map's numbers.
 *
 * Not one line of the files below adds a push, evaluates a shape, multiplies a
 * likelihood or averages anything. Every number drawn arrives from the server
 * and is carried, untouched and at full precision, to the moment it is printed.
 * The reason is not tidiness: the moment this half of the product works out a
 * number of its own there are two engines on the map, they disagree about half a
 * point, and nobody can say which is right.
 *
 * **Three things that are not arithmetic and are allowed by name.** Comparing a
 * push against a fixed threshold to pick a stroke width or a band of words.
 * Following arrows to find what is reachable. And working out where pixels go —
 * which is why the file that routes a wire around a tile is not on the list
 * below, and why its own tests are about geometry rather than about numbers.
 *
 * The check walks the syntax tree of each file rather than its text, so a
 * multiplication split over two lines, or hidden inside a template string, is
 * still found. It is the same technique the server uses to prove that nothing
 * anywhere averages two beliefs.
 */

import ts from "typescript";
import { describe, expect, it } from "vitest";

/**
 * Every module in the tree, read as text by the build tool rather than off the
 * disk — so this test needs nothing but the browser types the rest of the app is
 * written against.
 */
const SOURCE = import.meta.glob("/src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/**
 * Every file that touches one of the map's numbers and draws it.
 *
 * Deliberately not the whole tree: the file that works out where a wire goes
 * does nothing but pixel geometry, and pixel geometry is arithmetic on pixels.
 */
const DRAWS_THE_MAPS_NUMBERS = [
  "/src/graph/wires/encodings.ts",
  "/src/graph/wires/WireChip.tsx",
  "/src/graph/wires/CausalWire.tsx",
  "/src/graph/wires/lens.ts",
  "/src/components/Inspector.tsx",
  "/src/components/PathBar.tsx",
  "/src/components/OriginMark.tsx",
  // A generation's own numbers arrive on events and are printed straight onto
  // the screen. The reducer that folds them holds a likelihood, a route's
  // multiplied-out likelihood and a receipt, and combines not one of them.
  "/src/components/VerdictCard.tsx",
  "/src/components/ReceiptStrip.tsx",
  ...Object.keys(SOURCE).filter(
    (path) => path.startsWith("/src/stream/") && !path.includes("__tests__"),
  ),
];

/**
 * The names a number off the map goes by.
 *
 * `p`, `lo` and `hi` are a likelihood and the range around it; `strength` is how
 * hard an arrow pushes; `prior` is the likelihood before an arrow's causes are
 * taken into account; `weight` is how much a piece of evidence counts. If an
 * expression combines two of anything, and either side reads one of these, the
 * canvas has started doing the engine's job.
 *
 * **The second group is the stream's own**, and it is the reason this list grew
 * when the walk did. Adding `frontend/src/stream/` to the files walked, and
 * leaving the names alone, checked those files for arithmetic on fields none of
 * them has: `receipt.input_tokens + receipt.output_tokens` — the exact sum the
 * receipt strip exists to refuse — would have walked straight past. A guard
 * pointed at the right files and the wrong names is a guard that always passes,
 * and INV-workbench.68 names this test by name.
 *
 * `product` is a route's multiplied-out likelihood; `versions` is how many
 * versions of the map the engine ran; `at` is a place in a transcript, and two
 * of those added together would be a place in nothing.
 */
const A_NUMBER_OFF_THE_MAP = new Set([
  "p",
  "lo",
  "hi",
  "strength",
  "prior",
  "weight",
  "pathProduct",
  "conditional",
  "reading",
  // The receipt's nine readings, by the names they travel under.
  "dollars",
  "seconds",
  "input_tokens",
  "output_tokens",
  "cache_read_tokens",
  "calls",
  "searches",
  // And the three other numbers a generation puts on the wire.
  "product",
  "versions",
  "at",
]);

/** The four operators that would combine two numbers into a third. */
const COMBINES = new Set([
  ts.SyntaxKind.PlusToken,
  ts.SyntaxKind.MinusToken,
  ts.SyntaxKind.AsteriskToken,
  ts.SyntaxKind.SlashToken,
  ts.SyntaxKind.PlusEqualsToken,
  ts.SyntaxKind.MinusEqualsToken,
  ts.SyntaxKind.AsteriskEqualsToken,
  ts.SyntaxKind.SlashEqualsToken,
]);

/** Does this expression read one of the map's own numbers? */
function readsAMapNumber(node: ts.Node): boolean {
  let found = false;
  const look = (here: ts.Node): void => {
    if (ts.isPropertyAccessExpression(here) && A_NUMBER_OFF_THE_MAP.has(here.name.text)) {
      found = true;
    }
    if (ts.isIdentifier(here) && A_NUMBER_OFF_THE_MAP.has(here.text)) {
      found = true;
    }
    ts.forEachChild(here, look);
  };
  look(node);
  return found;
}

/** Every place a file combines two things, with at least one of them a map number. */
function combinationsOfMapNumbers(path: string): string[] {
  const source = ts.createSourceFile(
    path,
    SOURCE[path] ?? "",
    ts.ScriptTarget.ESNext,
    true,
    path.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const found: string[] = [];
  const walk = (node: ts.Node): void => {
    if (ts.isBinaryExpression(node) && COMBINES.has(node.operatorToken.kind)) {
      if (readsAMapNumber(node.left) || readsAMapNumber(node.right)) {
        const { line } = source.getLineAndCharacterOfPosition(node.getStart(source));
        found.push(`${path}:${line + 1} ${node.getText(source)}`);
      }
    }
    ts.forEachChild(node, walk);
  };
  ts.forEachChild(source, walk);
  return found;
}

describe("the canvas does no arithmetic", () => {
  it("test_canvas_never_combines_two_model_numbers", () => {
    const found = DRAWS_THE_MAPS_NUMBERS.flatMap(combinationsOfMapNumbers);
    expect(found).toEqual([]);
  });

  it("test_the_files_being_walked_are_really_there", () => {
    // A check that silently walks nothing is a check that always passes.
    for (const path of DRAWS_THE_MAPS_NUMBERS) {
      expect((SOURCE[path] ?? "").length).toBeGreaterThan(0);
    }
  });
});
