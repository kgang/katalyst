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

import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import { aClaim } from "../../test/aMap";
import type { ClaimView } from "../../world";
import { Tile } from "../Tile";

/** Draw one tile. The map's provider is what tells a tile how far it is zoomed. */
function draw(claim: ClaimView) {
  return render(
    <ReactFlowProvider>
      <Tile claim={claim} isHypothesis={false} versions={2000} />
    </ReactFlowProvider>,
  );
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
    user: { absence: { kind: "not_said", words: "—", reason: "You have not said." } },
    market: {
      absence: { kind: "no_market", words: "no market", reason: "no venue quotes this claim" },
    },
  },
  moved: {
    from: 0.456,
    to: 0.414,
    way: "down",
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

  it("test_a_tile_with_no_move_draws_no_movement_badge", () => {
    const { container } = draw(aClaim({ id: "R", diff: "untouched", badges: [] }));
    expect(container.querySelector('.tile__badge[data-badge="movement"]')).toBeNull();
    expect(container.querySelector(".tile")?.getAttribute("aria-label")).toContain(
      "your edit cannot reach this",
    );
  });
});
