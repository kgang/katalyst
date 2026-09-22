/**
 * What a belief chip must never do.
 *
 * This is the one test in the browser half that holds the honesty rule up: two
 * significant figures, **one number and never a range** (Kent, 2026-09-22,
 * R48), an absence with a reason rather than a blank, and the word rather than a
 * number when the reader has supposed a claim true. It is the test decision
 * record 0005 promised by name —
 * `test_chip_never_shows_more_than_two_significant_figures` is the first one
 * below — and every other test in this directory could pass while the product
 * still lied, if this one did not.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Known, Likelihood } from "../../world";
import { absence } from "../../world/absence";
import { BeliefChip, toMovement, toSize, toTwoFigures } from "../BeliefChip";

/**
 * Count the significant figures in a printed number.
 *
 * Every digit counts except the noughts in front: `.060` has two — the six and
 * the nought after it, which is there because we know the figure to that place
 * — and `.35` has two.
 */
function significantFigures(printed: string): number {
  return printed.replace(/[^0-9]/g, "").replace(/^0+/, "").length;
}

/** The number a chip is showing. */
function readingOf(container: HTMLElement): string {
  return container.querySelector(".belief-chip__reading")?.textContent ?? "";
}

/** A slot with a number in it. */
function known(p: number): Known<Likelihood> {
  return { reading: { p } };
}

describe("a belief chip", () => {
  // The test decision record 0005 promised by name.
  it("test_chip_never_shows_more_than_two_significant_figures", () => {
    // Deliberately awkward numbers: ones that round up into a shorter string,
    // ones with a nought that has to be kept, and one that rounds to a whole
    // number.
    const awkward = [0.3456789, 0.06123456, 0.999, 0.5, 0.049999];

    for (const p of awkward) {
      const { container, unmount } = render(<BeliefChip owner="model" slot={known(p)} />);
      expect(significantFigures(readingOf(container))).toBeLessThanOrEqual(2);
      unmount();
    }
  });

  it("test_the_nought_that_carries_information_is_kept", () => {
    // Two significant figures means two digits that say something. Printing
    // `.06` for either of the first two would claim less precision than we have.
    expect(toTwoFigures(0.06)).toBe(".060");
    expect(toTwoFigures(0.0498)).toBe(".050");
    expect(toTwoFigures(0.06123)).toBe(".061");
    expect(toTwoFigures(0.35)).toBe(".35");
  });

  // **This test was `test_chip_never_omits_the_range`** and now asserts its
  // absence: R48 cut the range from this product, so a chip is the owner, the
  // mark and the number, and there is no fourth line for a range to stand on.
  it("test_no_chip_draws_a_range", () => {
    const { container } = render(<BeliefChip owner="model" slot={known(0.61)} />);
    expect(readingOf(container)).toBe(".61");
    // Nothing on the chip is a pair of numbers with a dash between them, and
    // nothing under the number at all: the line that held one is gone, not
    // merely empty.
    expect(container.querySelector(".belief-chip__under")).toBeNull();
    expect(container.textContent).not.toMatch(/[.\d]\s*[–-]\s*[.>]/);
    // And what the chip is called is what it reads: the owner, then the number.
    expect(container.textContent).toContain("model");
    expect(container.textContent).toContain(".61");
  });

  it("test_an_absent_number_renders_its_reason_and_never_a_blank", () => {
    const { container } = render(
      <BeliefChip
        owner="market"
        slot={{
          absence: absence(
            "no_market",
            "No venue quotes this claim, so there is no price to read.",
          ),
        }}
      />,
    );

    expect(readingOf(container)).toBe("no market");
    expect(readingOf(container)).not.toBe("");
    // Nothing anywhere on the chip is a zero standing in for a number nobody has.
    expect(container.textContent).not.toMatch(/(^|[^.\d])0([^.\d]|$)/);
    expect(
      screen.getByText("No venue quotes this claim, so there is no price to read."),
    ).toBeInTheDocument();
  });

  it("test_your_own_empty_slot_is_a_dash_with_a_reason", () => {
    const { container } = render(
      <BeliefChip
        owner="user"
        slot={{
          absence: absence("not_said", "You have not put your own number on this yet."),
        }}
      />,
    );
    expect(readingOf(container)).toBe("—");
    // The invitation *add yours* stood on the line the range used to share, and
    // that line went with the range (2026-09-22, R48). The tile no longer draws
    // an empty column at all, so there was nothing left for it to invite.
    expect(container.textContent).not.toContain("add yours");
    expect(container.textContent).toContain("You have not put your own number on this yet.");
  });

  it("test_a_supposed_claim_renders_the_word_not_a_number", () => {
    const { container } = render(
      <BeliefChip
        owner="model"
        slot={known(0.35)}
        standing={{
          words: "Supposed · Oct 1",
          reason: "You supposed this true on the 1st, so it holds wherever the engine looks.",
        }}
      />,
    );

    expect(readingOf(container)).toBe("Supposed · Oct 1");
    // Not `1.0`, not `.98`, and not the number the slot happens to hold.
    expect(container.textContent).not.toContain(".35");
    expect(container.textContent).not.toContain("1.0");
  });

  // **Two tests stood here and are deleted** *(2026-09-22, R48)*:
  // `test_a_computed_chip_says_it_is_uncalibrated` and
  // `test_model_chip_says_computed_only_when_a_world_computed_it`. Both asserted
  // the shelf behind a chip — *model interval, uncalibrated*, and *Across 2 000
  // versions of this map…* against *stated range · not computed*. There is no
  // range, no shelf and no count of versions, so there is nothing for either to
  // be about. What replaces them is
  // `test_nothing_on_a_tile_or_in_the_panel_mentions_versions_or_worlds` in
  // `graph/__tests__/noRange.test.tsx`, which walks the whole rendered map.

  // The certainty guard the decisions of 2026-09-17 asked for by name.
  it("test_chip_never_prints_a_certainty", () => {
    // Numbers that two-figure rounding would turn into `1.0` or `.0`, plus two
    // very small ones that it would not, to show the guard only fires where it
    // should. `.995` is here for a specific reason: a computer stores it a hair
    // *below* .995, so a formatter that asks the machine for two figures prints
    // `.99` — the one thing the rule forbids.
    const awkward = [0.995, 0.9962, 0.999, 1, 0, 0.004, 0.0004];

    for (const value of awkward) {
      const { container, unmount } = render(<BeliefChip owner="model" slot={known(value)} />);
      const one = readingOf(container);
      expect(one).not.toBe("1.0");
      expect(one).not.toBe("1");
      expect(one).not.toBe(".0");
      expect(one).not.toBe("0.0");
      expect(significantFigures(one)).toBeLessThanOrEqual(2);
      unmount();
    }

    // The worked table the shared chapter settles, row for row.
    expect(toTwoFigures(0.35)).toBe(".35");
    expect(toTwoFigures(0.347)).toBe(".35");
    expect(toTwoFigures(0.0712)).toBe(".071");
    expect(toTwoFigures(0.4999)).toBe(".50");
    expect(toTwoFigures(0.06)).toBe(".060");
    expect(toTwoFigures(0.995)).toBe(">.99");
    expect(toTwoFigures(0.9962)).toBe(">.99");
    expect(toTwoFigures(1)).toBe(">.99");
    expect(toTwoFigures(0)).toBe("<.01");
    // Rounding that carries into the next place keeps two figures, not three.
    expect(toTwoFigures(0.0999)).toBe(".10");
  });

  // **`test_a_share_is_a_whole_percentage_and_never_rounds_up_into_all_of_them`
  // is deleted** *(2026-09-22, R48)*. The only share this product ever printed
  // was *same direction* — how many of the two thousand versions of the map
  // moved the same way — and the printer that wrote it went with the column.

  it("test_the_lower_guard_begins_at_a_hundredth", () => {
    // Kent, 2026-09-20, G10. The guard is applied to the number **as it would
    // print**: what two figures would print below `.010` prints `<.01`, and
    // what they would print at `.010` or above prints its figures. A likelihood
    // of a thousandth is not a number this product is entitled to call anything
    // more precise than "small".
    expect(toTwoFigures(0.0099)).toBe("<.01");
    expect(toTwoFigures(0.0035)).toBe("<.01");
    expect(toTwoFigures(0.00012)).toBe("<.01");
    // On the line, and just under it after rounding carries.
    expect(toTwoFigures(0.01)).toBe(".010");
    expect(toTwoFigures(0.00996)).toBe(".010");
    expect(toTwoFigures(0.0104)).toBe(".010");
    expect(toTwoFigures(0.011)).toBe(".011");
  });

  it("test_a_size_is_not_a_likelihood_and_takes_no_guard", () => {
    // How far a number moved, and how wide a band is, are measured on the
    // likelihood scale and are not likelihoods. `<.01` on a likelihood is a
    // claim about the world — "small, but we are not calling it impossible".
    // A move of nine thousandths is a measurement, and rounding it away would
    // throw out the only thing the reader came for.
    expect(toSize(0.008967961923746659)).toBe(".0090");
    expect(toSize(0.0035)).toBe(".0035");
    expect(toSize(0.00012)).toBe(".00012");
    // The sign is said in words elsewhere, so only the size is printed.
    expect(toSize(-0.0035)).toBe(".0035");
    // And no guard at the top either: a move of exactly one is a real move.
    expect(toSize(1)).toBe("1.0");
    expect(toSize(0.995)).toBe("1.0");
    expect(toSize(0)).toBe("0");
  });

  it("test_no_chevron_between_two_readings_that_print_the_same", () => {
    // Two figures is the whole of what this product shows, so a move smaller
    // than the second figure leaves the before and the after printing the same.
    // A chevron between them says "it went up" and "it is where it was" in one
    // breath, and reads as a fault in the tool. Where they print the same the
    // row is the one reading and the size of the move in words.
    //
    // The numbers are the engine's own for observing the insurance premium,
    // which moves the strait from .3557 to .3647 — nine thousandths, invisible
    // at two figures.
    expect(toMovement(0.3557703617587686, 0.36473832368251524, 0.008967961923746659, "up")).toBe(
      ".36 · up by .0090",
    );
    expect(toMovement(0.456, 0.414, -0.0421, "down")).toBe(".46 ▼ .41");

    // A size keeps two figures however small, so a tiny move reads as the tiny
    // move it is — where the likelihoods on either side of it would have been
    // guarded down to `<.01`.
    expect(toMovement(0.4, 0.4, 0.000004, "up")).toBe(".40 · up by .0000040");
    // The sign is already said by the word, so only the size is printed.
    expect(toMovement(0.4, 0.4, -0.000004, "down")).toBe(".40 · down by .0000040");
    // And nothing moved at all is not a direction: the reading stands alone.
    expect(toMovement(0.19, 0.19, 0, "up")).toBe(".19");
  });

  // **This test was `test_a_chip_is_reachable_by_keyboard_and_opens_no_dialog`**
  // and now asserts the opposite of its first half: with the range gone there is
  // nothing behind a chip to open, so the chip is not a control at all. A button
  // that does nothing when it is pressed is worse than no button — it is a
  // promise the product cannot keep, and a stop on every keyboard walk of the
  // map for nothing.
  it("test_a_chip_is_not_a_control_and_opens_nothing", () => {
    const { container } = render(<BeliefChip owner="model" slot={known(0.35)} />);

    expect(screen.queryByRole("button")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
  });
});
