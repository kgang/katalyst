/**
 * A direction of financial effect is never a hue on its own.
 *
 * Blue for up and amber for down, never red and green — and never colour by
 * itself: a glyph, a sign and a word, all three, every time. The second test is
 * the one that matters most, because it is what stops a component somewhere else
 * reaching for the colour and quietly dropping the other three.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DirectionReadout } from "../DirectionReadout";

describe("a direction", () => {
  it("test_direction_always_has_its_glyph_sign_and_word", () => {
    for (const direction of ["up", "down"] as const) {
      const { container, unmount } = render(
        <DirectionReadout direction={direction} amount=".18" what="the Polymarket contract" />,
      );
      const glyph = container.querySelector(".direction-readout__glyph")?.textContent ?? "";
      const amount = container.querySelector(".direction-readout__amount")?.textContent ?? "";
      const word = container.querySelector(".direction-readout__word")?.textContent ?? "";

      expect(["▲", "▼"]).toContain(glyph);
      expect(amount.startsWith("+") || amount.startsWith("−")).toBe(true);
      expect(["up", "down"]).toContain(word);
      unmount();
    }
  });
});

/** Every file under `src`, so nothing can hide a direction colour in a corner. */
function everyFile(from: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) {
      Object.assign(found, everyFile(path));
    } else if (/\.(ts|tsx|css)$/.test(name)) {
      found[`/${path.replaceAll("\\", "/")}`] = readFileSync(path, "utf8");
    }
  }
  return found;
}

const EVERY_FILE = everyFile("src");

describe("who is allowed to name a direction colour", () => {
  it("test_no_file_outside_direction_readout_names_a_direction_token", () => {
    // One component reads those two colours, and one stylesheet paints with
    // them. Everywhere else naming them would be a second place where a
    // direction could lose its glyph, its sign or its word — and where a push's
    // sign, which is not a direction of financial effect at all, could be
    // painted as though it were one.
    const allowed = new Set([
      "/src/components/directionReadout.css",
      "/src/components/DirectionReadout.tsx",
      "/src/components/__tests__/directionReadout.test.tsx",
      "/src/styles/tokens.css",
      "/src/styles/__tests__/colourLaw.test.ts",
    ]);
    // A check that silently walks nothing is a check that always passes.
    expect(Object.keys(EVERY_FILE).length).toBeGreaterThan(20);
    const offenders = Object.entries(EVERY_FILE)
      .filter(([path, text]) => !allowed.has(path) && /--dir-up|--dir-down/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
