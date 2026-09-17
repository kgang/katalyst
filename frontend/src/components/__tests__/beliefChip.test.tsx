/**
 * What a belief chip must never do.
 *
 * This is the one test in the browser half that holds the honesty rule up: two
 * significant figures, the range always, an absence with a reason rather than a
 * blank, and the word rather than a number when the reader has supposed a claim
 * true. It is the test decision record 0005 promised by name —
 * `test_chip_never_shows_more_than_two_significant_figures` is the first one
 * below — and every other test in this directory could pass while the product
 * still lied, if this one did not.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Known, Ranged } from "../../world";
import { BeliefChip, toMovement, toReading, toShare, toTwoFigures } from "../BeliefChip";

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

/** The line under the number: the range, or the invitation to add your own. */
function underOf(container: HTMLElement): string {
  return container.querySelector(".belief-chip__under")?.textContent ?? "";
}

/** A slot with a number in it. */
function known(p: number, lo: number, hi: number): Known<Ranged> {
  return { reading: { p, lo, hi } };
}

describe("a belief chip", () => {
  // The test decision record 0005 promised by name.
  it("test_chip_never_shows_more_than_two_significant_figures", () => {
    // Deliberately awkward numbers: ones that round up into a shorter string,
    // ones with a nought that has to be kept, one that rounds to a whole number,
    // and the two ends of the range.
    const awkward: [number, number, number][] = [
      [0.3456789, 0.2222222, 0.4987654],
      [0.06123456, 0.0198765, 0.1444444],
      [0.999, 0.9512345, 0.99999],
      [0.5, 0.125, 0.875],
      [0.049999, 0.001234, 0.0987654],
    ];

    for (const [p, lo, hi] of awkward) {
      const { container, unmount } = render(<BeliefChip owner="model" slot={known(p, lo, hi)} />);
      expect(significantFigures(readingOf(container))).toBeLessThanOrEqual(2);
      for (const end of underOf(container).split("–")) {
        expect(significantFigures(end)).toBeLessThanOrEqual(2);
      }
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
    expect(toReading(0.35, 0.22, 0.5)).toBe(".35 (.22–.50)");
  });

  it("test_chip_never_omits_the_range", () => {
    const { container } = render(<BeliefChip owner="model" slot={known(0.61, 0.45, 0.74)} />);
    expect(readingOf(container)).toBe(".61");
    expect(underOf(container)).toBe(".45–.74");
    // And the whole reading, the way it would be read out loud, carries both.
    expect(screen.getByRole("button")).toHaveAttribute("aria-label", "model: .61 (.45–.74)");
  });

  it("test_an_absent_number_renders_its_reason_and_never_a_blank", () => {
    const { container } = render(
      <BeliefChip
        owner="market"
        slot={{
          absence: {
            kind: "no_market",
            words: "no market",
            reason: "No venue quotes this claim, so there is no price to read.",
          },
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

  it("test_your_own_empty_slot_invites_a_number", () => {
    const { container } = render(
      <BeliefChip
        owner="user"
        slot={{
          absence: {
            kind: "not_said",
            words: "—",
            reason: "You have not put your own number on this yet.",
          },
        }}
      />,
    );
    expect(readingOf(container)).toBe("—");
    expect(underOf(container)).toBe("add yours");
  });

  it("test_a_supposed_claim_renders_the_word_not_a_number", () => {
    const { container } = render(
      <BeliefChip
        owner="model"
        slot={known(0.35, 0.22, 0.5)}
        standing={{
          words: "Supposed · Oct 1",
          reason: "You supposed this true on the 1st, so it holds in every simulated world.",
        }}
      />,
    );

    expect(readingOf(container)).toBe("Supposed · Oct 1");
    // Not `1.0`, not `.98`, and not the number the slot happens to hold.
    expect(container.textContent).not.toContain(".35");
    expect(container.textContent).not.toContain("1.0");
  });

  it("test_a_computed_chip_says_it_is_uncalibrated", () => {
    render(<BeliefChip owner="model" slot={known(0.35, 0.2, 0.49)} versions={2000} />);

    // No claim on any map has resolved, so the eight-in-ten below has never
    // been checked against anything. The label says that in one word rather
    // than letting a range that came out of two thousand runs pass for a range
    // somebody has tested.
    expect(
      screen.getByText(
        "model interval, uncalibrated · how sure we are of .35 — not how much the world can move",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Across 2 000 versions of this map — each one a set of numbers this model would have " +
          "stood behind — the answer landed between .20 and .49 eight times in ten. Nobody has " +
          "checked whether that 8-in-10 holds up; no claim on this map has resolved yet.",
      ),
    ).toBeInTheDocument();
  });

  // The test the decisions of 2026-09-17 asked for by name.
  it("test_model_chip_says_computed_only_when_a_world_computed_it", () => {
    // Nothing has run this number through a map, so the chip says the range is
    // the one whoever wrote the number down stated, and says nothing at all
    // about versions of the map.
    const stated = render(<BeliefChip owner="model" slot={known(0.35, 0.2, 0.49)} />);
    expect(screen.getByText("stated range · not computed")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This range is stated, not computed — it says how sure the elicitation was. " +
          "Nothing has worked this number through the map yet.",
      ),
    ).toBeInTheDocument();
    expect(stated.container.textContent).not.toContain("versions of this map");
    expect(stated.container.textContent).not.toContain("uncalibrated");
    stated.unmount();

    // A world that ran two thousand versions may say so, and counts them out.
    const computed = render(
      <BeliefChip owner="model" slot={known(0.35, 0.2, 0.49)} versions={2000} />,
    );
    expect(computed.container.textContent).toContain("Across 2 000 versions of this map");
    expect(computed.container.textContent).not.toContain("stated, not computed");

    // And it counts out whatever number it was actually given, not a fixed one.
    computed.unmount();
    render(<BeliefChip owner="model" slot={known(0.35, 0.2, 0.49)} versions={16} />);
    expect(screen.getByText(/Across 16 versions of this map/)).toBeInTheDocument();
  });

  // The certainty guard the decisions of 2026-09-17 asked for by name.
  it("test_chip_never_prints_a_certainty", () => {
    // Numbers that two-figure rounding would turn into `1.0` or `.0`, plus two
    // very small ones that it would not, to show the guard only fires where it
    // should. `.995` is here for a specific reason: a computer stores it a hair
    // *below* .995, so a formatter that asks the machine for two figures prints
    // `.99` — the one thing the rule forbids.
    const awkward = [0.995, 0.9962, 0.999, 1, 0, 0.004, 0.0004];

    for (const value of awkward) {
      const { container, unmount } = render(
        <BeliefChip owner="model" slot={known(value, value, value)} />,
      );
      const printed = [readingOf(container), ...underOf(container).split("–")];
      for (const one of printed) {
        expect(one).not.toBe("1.0");
        expect(one).not.toBe("1");
        expect(one).not.toBe(".0");
        expect(one).not.toBe("0.0");
        expect(significantFigures(one)).toBeLessThanOrEqual(2);
      }
      unmount();
    }

    // The worked table the shared chapter settles, row for row.
    expect(toTwoFigures(0.35)).toBe(".35");
    expect(toTwoFigures(0.347)).toBe(".35");
    expect(toTwoFigures(0.0712)).toBe(".071");
    expect(toTwoFigures(0.4999)).toBe(".50");
    expect(toTwoFigures(0.06)).toBe(".060");
    expect(toTwoFigures(0.0035)).toBe(".0035");
    expect(toTwoFigures(0.00012)).toBe(".00012");
    expect(toTwoFigures(0.995)).toBe(">.99");
    expect(toTwoFigures(0.9962)).toBe(">.99");
    expect(toTwoFigures(1)).toBe(">.99");
    expect(toTwoFigures(0)).toBe("<.01");
    // Rounding that carries into the next place keeps two figures, not three.
    expect(toTwoFigures(0.0999)).toBe(".10");

    // The guard applies to each end of the range on its own, unchanged: on one
    // end here, on both in the second.
    expect(toReading(0.9962, 0.988, 0.9995)).toBe(">.99 (.99–>.99)");
    expect(toReading(0.9962, 0.9971, 0.9999)).toBe(">.99 (>.99–>.99)");
  });

  it("test_a_share_is_a_whole_percentage_and_never_rounds_up_into_all_of_them", () => {
    // A share of something counted is not a likelihood: a hundred per cent
    // really can mean every one of them, so printing `>.99` over it would hide
    // a fact the machine actually counted. The only guard is the one that stops
    // rounding from inventing unanimity.
    expect(toShare(0.9663)).toBe("97%");
    expect(toShare(1)).toBe("100%");
    expect(toShare(0.9995)).toBe(">99%");
    expect(toShare(0)).toBe("0%");
    expect(toShare(0.0004)).toBe("<1%");
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

    // The size is printed by the same rule as every other number on screen, and
    // that rule keeps two figures however small the number gets — so a tiny move
    // reads as the tiny move it is. Only exactly nothing prints `<.01`, and a
    // move of exactly nothing is not a move.
    expect(toMovement(0.4, 0.4, 0.000004, "up")).toBe(".40 · up by .0000040");
    // The sign is already said by the word, so only the size is printed.
    expect(toMovement(0.4, 0.4, -0.000004, "down")).toBe(".40 · down by .0000040");
  });

  it("test_a_chip_is_reachable_by_keyboard_and_opens_no_dialog", () => {
    render(<BeliefChip owner="model" slot={known(0.35, 0.22, 0.5)} />);

    const chip = screen.getByRole("button");
    chip.focus();
    expect(document.activeElement).toBe(chip);

    // The note is described text on the chip, not a window over the page.
    const described = chip.getAttribute("aria-describedby");
    expect(described).not.toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
  });
});
