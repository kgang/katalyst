/**
 * The colour law: one channel per meaning.
 *
 * A *channel* is one thing the eye can vary on its own — brightness, hue,
 * texture, stroke pattern, stroke width, shape, position. Six meanings, six
 * channels, and no channel doing two jobs, because every failure in this area is
 * two meanings fighting over one channel.
 *
 * Four of the six are checked automatically. This file checks the brightness
 * channel — the five-step ramp that says how likely a claim is — and that every
 * token the law names exists with a measured contrast ratio beside it. The
 * stroke and mark channels are checked in `graph/wires/__tests__`, and the hue
 * channel in `components/__tests__/directionReadout.test.tsx`. Texture and lane
 * colour are checked by eye, on `VR3` of the visual review checklist in
 * `spec/workbench/README.md` — convert the screenshot to grey and everything
 * still reads. The lines of that list carry names now, so a citation still
 * points at the check it meant when a line is added above it.
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

/** The five steps of the ramp, and the chips allowed to paint with them. */
const RAMP = ["--p-0", "--p-1", "--p-2", "--p-3", "--p-4"];
const MAY_PAINT_WITH_THE_RAMP = new Set([
  "/src/styles/tokens.css",
  // The bounded bar beside the number on a tile's belief chip.
  "/src/components/beliefChip.css",
  // The bounded bar behind the number in the panel's belief rows.
  "/src/components/inspector.css",
  // The bounded bar on a wire's plate, once the engine can supply a likelihood.
  "/src/graph/wires/wires.css",
]);

describe("the tokens the law names", () => {
  it("test_the_files_being_walked_are_really_there", () => {
    // A check that silently walks nothing is a check that always passes.
    expect(TOKENS.length).toBeGreaterThan(0);
    expect(Object.keys(STYLESHEETS).length).toBeGreaterThan(4);
  });

  it("test_every_token_the_law_names_exists_in_both_themes", () => {
    const named = [
      ...RAMP,
      "--branch-violet",
      "--branch-teal",
      "--branch-rose",
      "--branch-slate",
      "--dir-up",
      "--dir-down",
      "--tail",
      "--duration-wave",
      "--duration-stagger",
    ];
    for (const token of named) {
      expect(TOKENS).toContain(`${token}:`);
    }
    // The ramp and the branch palette are defined for the light page as well as
    // the dark one. A map that only works dark reads as a demo.
    const light = TOKENS.slice(TOKENS.indexOf('[data-theme="light"]'));
    for (const token of [...RAMP, "--branch-violet", "--branch-teal"]) {
      expect(light).toContain(`${token}:`);
    }
  });

  it("test_every_new_colour_carries_its_measured_ratio", () => {
    // Every colour token in this file has its contrast ratio written beside it,
    // because a colour whose ratio nobody measured is a colour somebody is about
    // to draw text on.
    for (const token of [
      ...RAMP,
      "--branch-violet",
      "--branch-teal",
      "--branch-rose",
      "--branch-slate",
    ]) {
      const at = TOKENS.indexOf(`${token}:`);
      const after = TOKENS.slice(at, at + 200);
      expect(after).toMatch(/to 1 on --surface/);
    }
  });

  // What reduced motion does to the three durations is the motion budget's own
  // statement, and it is checked where the chapter says it is:
  // `motionBudget.test.ts`, beside the rule that there are only three of them.
});

describe("the brightness channel", () => {
  it("test_likelihood_ramp_is_read_only_by_the_two_chips", () => {
    const offenders = Object.entries(STYLESHEETS)
      .filter(
        ([path, rules]) =>
          !MAY_PAINT_WITH_THE_RAMP.has(path) && RAMP.some((token) => rules.includes(token)),
      )
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it("test_no_rule_sets_a_text_colour_to_the_ramp", () => {
    // The ramp paints a bar, which is a graphic and needs three to one. A number
    // is always drawn in the text colour, so it always clears four and a half.
    for (const [path, rules] of Object.entries(STYLESHEETS)) {
      if (path === "/src/styles/tokens.css") {
        continue;
      }
      for (const token of RAMP) {
        expect(rules).not.toMatch(new RegExp(`\\bcolor:\\s*var\\(${token}\\)`));
      }
    }
  });

  it("test_the_ramp_never_paints_a_whole_tile", () => {
    // Tile-wide brightness and opacity are already spent: the old world is
    // painted faint in a diff, and the hover lens dims everything off the path.
    // Three meanings on one channel means none of them reads.
    const tile = STYLESHEETS["/src/components/tile.css"] ?? "";
    for (const token of RAMP) {
      expect(tile).not.toContain(token);
    }
  });
});

describe("three teals on one screen", () => {
  it("test_the_branch_teal_is_not_the_accent_teal_or_the_focus_teal", () => {
    // `--accent` is a teal meaning "this is fine" and `--focus` is a brighter
    // teal meaning "the keyboard is here". The branch palette adds a third, and
    // a third teal that looked like either of the other two would be a colour
    // carrying two meanings. The branch teal is deliberately darker and bluer.
    // It is also never the only thing saying which branch you are in: every
    // branch carries a name chip with its label.
    const values = (block: string) => ({
      accent: /--accent:\s*(#[0-9a-f]{6})/.exec(block)?.[1],
      focus: /--focus:\s*(#[0-9a-f]{6})/.exec(block)?.[1],
      branch: /--branch-teal:\s*(#[0-9a-f]{6})/.exec(block)?.[1],
    });
    const dark = values(TOKENS.slice(0, TOKENS.indexOf('[data-theme="light"]')));
    const light = values(TOKENS.slice(TOKENS.indexOf('[data-theme="light"]')));

    for (const theme of [dark, light]) {
      expect(theme.branch).toBeDefined();
      expect(theme.branch).not.toBe(theme.accent);
      expect(theme.branch).not.toBe(theme.focus);
    }
  });
});
