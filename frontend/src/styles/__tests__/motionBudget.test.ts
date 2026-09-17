/**
 * The motion budget: three moves, and everything else is an opacity change.
 *
 * The three are the propagation wave — the wires arriving in the order the
 * argument runs — a branch arriving, and a likelihood rolling from an old figure
 * to a new one. Everything else that appears or goes does so with an opacity
 * change of at most 120 milliseconds, and nothing at all loops, spins or sweeps.
 *
 * **Growth spends what is already budgeted and adds nothing.** A map building
 * itself is the case the wave was written for; a reserved rectangle appears and
 * goes with the ordinary 120 milliseconds of opacity. There is no fourth
 * animation, and a fourth would be the one that turns a budget into a
 * suggestion.
 *
 * Under reduced motion **the ordering survives and the tweening goes**. That is
 * the load-bearing half: the gap between one column of the map and the next is
 * the order the argument runs in, so it stays at sixty milliseconds while every
 * in-between frame goes to nothing.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Every stylesheet in the tree, by the path the rules below name it by. */
function everyStylesheet(from: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) {
      Object.assign(found, everyStylesheet(path));
    } else if (name.endsWith(".css")) {
      found[`/${path.replaceAll("\\", "/")}`] = readFileSync(path, "utf8");
    }
  }
  return found;
}

const STYLESHEETS = everyStylesheet("src");
const TOKENS = STYLESHEETS["/src/styles/tokens.css"] ?? "";

/**
 * The tokens a duration may be spelled with, and what each is for.
 *
 * A raw number of milliseconds anywhere else is a fourth duration nobody agreed
 * to, so the check is that every duration in the product is one of these names.
 */
const THE_ONLY_DURATIONS = ["--duration-fast", "--duration-wave", "--duration-stagger"];

describe("the motion budget", () => {
  it("test_no_duration_above_120ms_outside_the_three_budgeted_moves", () => {
    // The three tokens, and the values they are set to in one place.
    expect(TOKENS).toContain("--duration-fast: 120ms");
    expect(TOKENS).toContain("--duration-wave: 200ms");
    expect(TOKENS).toContain("--duration-stagger: 60ms");

    const wrong: string[] = [];
    for (const [path, whole] of Object.entries(STYLESHEETS)) {
      // A check that silently walks nothing is a check that always passes.
      expect(whole.length).toBeGreaterThan(0);

      // The rules, without the prose around them. Half these files explain in so
      // many words what each duration is for, and a check that read the prose
      // would punish saying so.
      const sheet = whole.replaceAll(/\/\*[\s\S]*?\*\//g, " ");

      // Where a duration is *set*, it is set in tokens.css and nowhere else.
      // Everywhere else spends one of the three by name.
      for (const spent of sheet.matchAll(/(animation|transition)[^;{]*:[^;}]*/g)) {
        const said = spent[0];
        if (!THE_ONLY_DURATIONS.some((token) => said.includes(token))) {
          wrong.push(`${path}: ${said.trim().replace(/\s+/g, " ")} spends no budgeted duration`);
        }
      }

      // And no raw duration is written down anywhere outside the tokens. A zero
      // is not a duration: it is the absence of one, and it is what a delay
      // starts at before a column's own stagger is added to it.
      if (path !== "/src/styles/tokens.css") {
        for (const raw of sheet.matchAll(/\b\d+m?s\b/g)) {
          if (raw[0] !== "0ms" && raw[0] !== "0s") {
            wrong.push(`${path}: writes the duration ${raw[0]} down rather than spending a token`);
          }
        }
      }
    }
    expect(wrong).toEqual([]);
  });

  it("test_reduced_motion_zeroes_every_tween_and_keeps_the_stagger", () => {
    // The tweening goes and the ordering stays. The gap between one column of
    // the map and the next is the order the argument runs in — the ordering is
    // the causality, and removing it would remove the one thing the movement was
    // for.
    const reduced = TOKENS.slice(TOKENS.indexOf("prefers-reduced-motion"));
    expect(reduced).toContain("--duration-fast: 0ms");
    expect(reduced).toContain("--duration-wave: 0ms");
    expect(reduced).not.toContain("--duration-stagger: 0ms");
  });
});
