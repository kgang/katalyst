/**
 * The rail beside the map: what it may say, and what it may not.
 *
 * Two rules, and both are about not inventing things. **It invents no order** —
 * with the engine, the rows come out in the engine's own order and are never
 * re-sorted here; without it, in the order the map stores them, and the rail
 * says so on its own face. And **it invents no number** — every slot without one
 * renders the reason it has none, in words a reader can get at without a mouse.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DeltaRow } from "../../world";
import { DeltaRail } from "../DeltaRail";

/** Where a number will go, and why it is not there yet. */
const NOT_YET = {
  absence: {
    kind: "no_engine" as const,
    words: "—",
    reason: "Nothing has worked this number through the map yet.",
  },
};

/** Three endings, in the order the stored example's map holds them. */
const ROWS: DeltaRow[] = [
  {
    claimId: "M1",
    label: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind: "market",
    move: {
      absence: {
        kind: "no_engine",
        words: "no engine yet",
        reason: "Nothing has worked this ending's number through the map.",
      },
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
  {
    claimId: "M2",
    label: "The energy fund XLE underperforms SPY by more than 3%.",
    kind: "market",
    move: {
      absence: {
        kind: "no_engine",
        words: "no engine yet",
        reason: "Nothing has worked this ending's number through the map.",
      },
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
  {
    claimId: "N1",
    label: "Omani-mediated talks resume publicly.",
    kind: "not_tradeable",
    move: {
      absence: {
        kind: "no_engine",
        words: "no engine yet",
        reason: "Nothing has worked this ending's number through the map.",
      },
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
];

/** The rail's one-line summary, which is an absence with its reason too. */
const SUMMARY = {
  absence: {
    kind: "no_engine" as const,
    words: "no engine yet",
    reason: "The one line saying what this edit did to the trades is written from the numbers.",
  },
};

/**
 * The rail the engine gives back, in the engine's own order.
 *
 * Deliberately **not** map order — the map holds M1, M2, N1 and the engine's
 * ranking on this branch puts N1 last for a reason worth reading: it has the
 * biggest move on the map, and the only arrow into it is a bare assertion. If
 * the rail ever re-sorted, this list would come back in a different order.
 *
 * Every number below is a shape, not a measurement: what is checked is that what
 * came in comes out, in the order it came in.
 */
const RANKED: DeltaRow[] = [
  {
    claimId: "M1",
    label: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind: "market",
    move: { reading: { from: 0.496, to: 0.417, largestOn: "2026-10-04", way: "down" } },
    rangeWidth: { reading: 0.269 },
    agreement: { reading: 0.9663 },
  },
  {
    claimId: "M2",
    label: "The energy fund XLE underperforms SPY by more than 3%.",
    kind: "market",
    move: { reading: { from: 0.432, to: 0.363, largestOn: "2026-10-06", way: "down" } },
    rangeWidth: { reading: 0.278 },
    agreement: { reading: 0.9553 },
  },
  {
    claimId: "N1",
    label: "Omani-mediated talks resume publicly.",
    kind: "not_tradeable",
    move: { reading: { from: 0.281, to: 0.369, largestOn: "2026-10-11", way: "up" } },
    rangeWidth: { reading: 0.316 },
    agreement: { reading: 0.9995 },
  },
];

describe("the rail beside the map", () => {
  it("test_lists_reachable_terminals_in_map_order", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    const listed = screen.getAllByText(/^(M1|M2|N1)$/).map((one) => one.textContent);
    expect(listed).toEqual(["M1", "M2", "N1"]);
    expect(screen.getByText(/In map order/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing has ranked these/)).toBeInTheDocument();
  });

  it("test_the_rail_keeps_the_engines_order", () => {
    // The rows arrive ranked and are drawn in that order. Nothing here sorts
    // them, and nothing here re-ranks them: a ranking is a claim about which
    // change matters most, and it is the engine's claim to make.
    const { rerender } = render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);
    expect(screen.getAllByText(/^(M1|M2|N1)$/).map((one) => one.textContent)).toEqual([
      "M1",
      "M2",
      "N1",
    ]);

    // Hand the same three rows over in a different order and the rail draws
    // them in that order too — which is what says the order on screen is the
    // one it was given rather than one it worked out.
    const shuffled = [RANKED[2], RANKED[0], RANKED[1]] as DeltaRow[];
    rerender(<DeltaRail rows={shuffled} ranked={true} summary={SUMMARY} />);
    expect(screen.getAllByText(/^(M1|M2|N1)$/).map((one) => one.textContent)).toEqual([
      "N1",
      "M1",
      "M2",
    ]);

    // And it says whose order it is, rather than letting the reader guess.
    expect(screen.getByText(/In the order the engine put them in/)).toBeInTheDocument();
  });

  it("test_how_firm_and_same_direction_are_columns_not_factors", () => {
    render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);

    // Two headings, two columns, every row carrying both — and neither of them
    // anywhere near the order the rows are drawn in. They answer different
    // questions, a trader weighs them separately, and blending either into a
    // rank would bury exactly the wide claims worth researching.
    expect(screen.getByText("how firm")).toBeInTheDocument();
    expect(screen.getByText("same direction")).toBeInTheDocument();

    // Widest band first would be N1, M2, M1; most agreement first would be N1,
    // M1, M2. The rail shows neither, because it shows the order it was given.
    expect(screen.getAllByText(/^(M1|M2|N1)$/).map((one) => one.textContent)).toEqual([
      "M1",
      "M2",
      "N1",
    ]);

    // Both are printed at two significant figures, like every number on screen,
    // and a share is printed as a whole percentage because it is counted rather
    // than estimated.
    expect(screen.getByText(".27")).toBeInTheDocument();
    expect(screen.getByText("97%")).toBeInTheDocument();
    // A share that is not quite all of them never rounds up into all of them.
    expect(screen.getByText(">99%")).toBeInTheDocument();
  });

  it("test_an_unmoved_terminal_is_a_greyed_row_not_a_missing_one", () => {
    // Silence cannot be told from absence: an ending missing from the engine's
    // list could mean "it did not move" or "it is not on this map". So it gets
    // a quiet row of its own, after the ranked ones and never among them.
    const held: DeltaRow = {
      claimId: "N1",
      label: "Omani-mediated talks resume publicly.",
      kind: "not_tradeable",
      move: {
        absence: { kind: "no_engine", words: "no change", reason: "The engine found no move." },
      },
      rangeWidth: NOT_YET,
      agreement: NOT_YET,
      noChange: true,
    };
    render(<DeltaRail rows={[RANKED[0] as DeltaRow, held]} ranked={true} summary={SUMMARY} />);
    expect(screen.getByText("no change")).toBeInTheDocument();
    expect(screen.getByText(/Endings that did not move follow/)).toBeInTheDocument();
  });

  it("test_a_ranked_row_names_the_day_the_two_worlds_are_furthest_apart", () => {
    render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);
    // A row is read on the day of largest divergence rather than on the claim's
    // own judging day, so the row says which day that was. A number whose day is
    // not said is a number nobody can check.
    expect(screen.getByText(/down · largest on 2026-10-04/)).toBeInTheDocument();
    expect(screen.getByText(/up · largest on 2026-10-11/)).toBeInTheDocument();
    // And which way it went is a chevron between the two readings as well as a
    // word, so neither carries it alone.
    expect(screen.getByText(".50 ▼ .42")).toBeInTheDocument();
  });

  it("test_renders_a_reason_for_every_absent_number", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    // Three cells a row, three rows, and every one of them a thing the keyboard
    // can land on whose name carries the sentence behind it.
    const cells = screen.getAllByRole("button");
    expect(cells).toHaveLength(9);
    for (const cell of cells) {
      expect(cell.getAttribute("aria-label") ?? "").toMatch(/Nothing has worked/);
    }
  });

  it("test_never_sorts_by_width_or_agreement", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    expect(screen.getByText("how firm")).toBeInTheDocument();
    expect(screen.getByText("same direction")).toBeInTheDocument();
    // The word *agreement* is kept off the screen: it is reserved for a
    // different number, computed run to run, that this build does not have.
    expect(screen.queryByText(/agreement/i)).toBeNull();
  });

  it("test_the_summary_slot_is_an_absence_with_a_reason", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    // The words are on the summary and on each row's change cell, so there are
    // four of them; what this checks is that the sentence behind the summary is
    // on the screen rather than a hover away.
    expect(screen.getAllByText("no engine yet")).toHaveLength(4);
    expect(screen.getByText(/written from the numbers/)).toBeInTheDocument();
  });

  it("test_an_empty_rail_says_what_to_do_about_it", () => {
    render(<DeltaRail rows={[]} ranked={false} summary={SUMMARY} />);
    expect(screen.getByText(/No ending on this map is reachable/)).toBeInTheDocument();
  });

  it("test_no_code_name_reaches_the_screen", () => {
    const { container } = render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    const words = (container.textContent ?? "").toLowerCase();
    for (const code of ["observe", "insert", "retune", "refine", "believe"]) {
      expect(words).not.toContain(code);
    }
  });
});
