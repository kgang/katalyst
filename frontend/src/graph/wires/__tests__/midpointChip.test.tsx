/**
 * The plate in the middle of a wire never invents a number.
 *
 * What it will eventually show is the likelihood of this arrow's target with its
 * cause supposed true. That number costs a whole extra run of the map per arrow,
 * so the engine works one out only when a wire is asked about — and that route
 * does not exist yet. Until it does the plate reads the arrow's own push back in
 * words, which is data already on the arrow and needs no arithmetic.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Known, Likelihood } from "../../../world";
import { absence } from "../../../world/absence";
import { WireChip } from "../WireChip";

/** The absence every arrow carries in this build, and the reason beside it. */
const NO_ENGINE: Known<Likelihood> = {
  absence: absence("no_engine", "Nothing has worked this number through the map yet."),
};

describe("the plate in the middle of a wire", () => {
  it("test_midpoint_chip_reads_the_push_in_words_until_the_engine_answers", () => {
    render(
      <WireChip
        strength={1.6}
        lag={2}
        conditional={NO_ENGINE}
        detail="full"
        layout="stacked"
        reflexive={false}
      />,
    );

    expect(screen.getByText("+1.6")).toBeInTheDocument();
    expect(screen.getByText("a strong push toward")).toBeInTheDocument();
    expect(screen.getByText("after 2 days")).toBeInTheDocument();
  });

  it("test_the_plate_never_shows_a_likelihood_nobody_computed", () => {
    const { container } = render(
      <WireChip
        strength={1.6}
        lag={2}
        conditional={NO_ENGINE}
        detail="full"
        layout="stacked"
        reflexive={false}
      />,
    );
    // No likelihood anywhere: not the push turned into one, not the target's own
    // number, not a dash that looks like a number that failed to load.
    // A likelihood in this product is printed with no leading zero — `.61`. The
    // plate prints `+1.6`, which is a push and not a likelihood, so what is
    // looked for is a decimal point with nothing but a sign or a space in front
    // of it.
    expect(container.textContent).not.toMatch(/(^|[^0-9])\.\d/);
    expect(container.textContent).not.toContain("no engine yet");
  });

  it("test_a_push_against_says_so_in_the_last_word", () => {
    render(
      <WireChip
        strength={-1.2}
        lag={5}
        conditional={NO_ENGINE}
        detail="full"
        layout="stacked"
        reflexive={false}
      />,
    );
    expect(screen.getByText("−1.2")).toBeInTheDocument();
    expect(screen.getByText("a clear push against")).toBeInTheDocument();
  });

  it("test_the_plate_shows_the_engines_answer_the_day_there_is_one", () => {
    // The seam. Nothing produces this in the current build; the branch exists so
    // that switching the world source on changes nothing in this component.
    render(
      <WireChip
        strength={1.6}
        lag={2}
        conditional={{ reading: { p: 0.61, lo: 0.45, hi: 0.74 } }}
        detail="full"
        layout="stacked"
        reflexive={false}
      />,
    );
    expect(screen.getByText(".61")).toBeInTheDocument();
    expect(screen.getByText("with its cause supposed true")).toBeInTheDocument();
    expect(screen.getByText(".45–.74")).toBeInTheDocument();
  });

  it("test_the_one_backwards_wire_keeps_its_delay_when_zoomed_out", () => {
    // A loop that takes no time is not feedback, it is a contradiction — so the
    // time is the part of that one arrow that may not be dropped.
    render(
      <WireChip
        strength={0.6}
        lag={14}
        conditional={NO_ENGINE}
        detail="summary"
        layout="inline"
        reflexive={true}
      />,
    );
    expect(screen.getByText("after 14 days")).toBeInTheDocument();
  });

  it("test_zoomed_out_the_plate_draws_less_rather_than_smaller", () => {
    const { container } = render(
      <WireChip
        strength={1.6}
        lag={2}
        conditional={NO_ENGINE}
        detail="summary"
        layout="stacked"
        reflexive={false}
      />,
    );
    expect(screen.getByText("+1.6")).toBeInTheDocument();
    // The words and the delay are one click away in the panel; nothing here is
    // shrunk below the size the type scale allows.
    expect(container.textContent).toBe("+1.6");
  });
});
