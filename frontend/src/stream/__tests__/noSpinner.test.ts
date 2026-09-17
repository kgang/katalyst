/**
 * There is no spinner anywhere in this product, and there never will be.
 *
 * A spinner says only "wait". The thing being waited for has a shape — a claim at
 * a column, a number in a slot — and the shape says "wait" *and* what for *and*
 * where it will land. It is also a named veto condition: a spinner followed by a
 * dump is one of the two things that end a line of work on sight.
 *
 * So this walks every stylesheet and every component in the tree and holds three
 * lines.
 *
 * 1. **Nothing spins, pulses or sweeps.** Every animation in the product changes
 *    opacity and nothing else. Nothing rotates, scales, moves, grows, or slides a
 *    gradient across itself, and nothing loops.
 * 2. **Nothing is an indeterminate progress indicator.** No element is given the
 *    part a screen reader reads as "progress" without a value to read.
 * 3. **Nothing calls itself a spinner, or a loader, or loading.** A word is a
 *    good proxy for an intention, and the intention is what this test is about.
 *
 * It is the same technique the colour law uses: read the files as text and walk
 * them, so that a rule added in a stylesheet nobody thought about is still found.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Every file of a kind in the tree, by the path the rules below name it by. */
function everyFile(from: string, ending: readonly string[]): Record<string, string> {
  const found: Record<string, string> = {};
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) {
      Object.assign(found, everyFile(path, ending));
    } else if (ending.some((one) => name.endsWith(one))) {
      found[`/${path.replaceAll("\\", "/")}`] = readFileSync(path, "utf8");
    }
  }
  return found;
}

const STYLESHEETS = everyFile("src", [".css"]);
const COMPONENTS = everyFile("src", [".tsx", ".ts"]);

/**
 * The only property an animation in this product is allowed to change.
 *
 * Everything else is a movement, and the motion budget has three movements in it
 * — the propagation wave, a branch arriving, and a likelihood rolling from an old
 * figure to a new one — none of which is a thing pretending to be busy.
 */
const THE_ONE_PROPERTY = "opacity";

/** Every `@keyframes` block in a stylesheet, with the name it goes by. */
function keyframesIn(sheet: string): { name: string; body: string }[] {
  const found: { name: string; body: string }[] = [];
  const at = /@keyframes\s+([\w-]+)\s*\{/g;
  let match = at.exec(sheet);
  while (match !== null) {
    // Walk from the opening brace to the one that closes it, counting depth, so
    // the nested `from {}` and `to {}` blocks are kept with their own rule.
    let depth = 1;
    let place = at.lastIndex;
    while (place < sheet.length && depth > 0) {
      if (sheet[place] === "{") {
        depth += 1;
      } else if (sheet[place] === "}") {
        depth -= 1;
      }
      place += 1;
    }
    found.push({ name: match[1] ?? "", body: sheet.slice(at.lastIndex, place - 1) });
    at.lastIndex = place;
    match = at.exec(sheet);
  }
  return found;
}

/**
 * One module with its comments taken out.
 *
 * The words below are looked for in the **code**, not in the prose around it —
 * half this product's files explain in so many words why there is no spinner in
 * them, and a check that failed on those would be a check that punished saying so.
 */
function withoutComments(source: string): string {
  return source.replaceAll(/\/\*[\s\S]*?\*\//g, " ").replaceAll(/\/\/[^\n]*/g, " ");
}

/** Every property a block of rules sets, by name. */
function propertiesIn(body: string): string[] {
  return [...body.matchAll(/(^|[{;\s])([a-z-]+)\s*:/g)]
    .map((one) => one[2] ?? "")
    .filter((one) => one !== "" && !one.startsWith("--"));
}

describe("there is no spinner anywhere", () => {
  it("test_there_is_no_spinner_anywhere", () => {
    const wrong: string[] = [];

    for (const [path, sheet] of Object.entries(STYLESHEETS)) {
      // A check that silently walks nothing is a check that always passes.
      expect(sheet.length).toBeGreaterThan(0);

      for (const { name, body } of keyframesIn(sheet)) {
        for (const property of propertiesIn(body)) {
          if (property !== THE_ONE_PROPERTY) {
            wrong.push(`${path}: @keyframes ${name} changes ${property}`);
          }
        }
      }

      // Nothing loops. A loop is the whole of what a spinner is.
      for (const declaration of sheet.matchAll(/animation[^;]*;/g)) {
        const said = declaration[0];
        if (said.includes("infinite") || /animation-iteration-count/.test(said)) {
          wrong.push(`${path}: ${said.trim()} loops`);
        }
      }
    }

    for (const [path, whole] of Object.entries(COMPONENTS)) {
      if (path.includes("__tests__")) {
        continue;
      }
      const source = withoutComments(whole);
      if (source.includes('role="progressbar"') || source.includes("'progressbar'")) {
        wrong.push(`${path}: renders an indeterminate progress indicator`);
      }
      for (const word of ["spinner", "Spinner", "loader", "Loader", "isLoading"]) {
        if (source.includes(word)) {
          wrong.push(`${path}: names a ${word}`);
        }
      }
    }

    expect(wrong).toEqual([]);
  });

  it("test_the_files_being_walked_are_really_there", () => {
    // The two files this test would be most embarrassing to have missed.
    expect(STYLESHEETS["/src/components/skeletonTile.css"] ?? "").not.toBe("");
    expect(COMPONENTS["/src/components/SkeletonTile.tsx"] ?? "").not.toBe("");
  });
});
