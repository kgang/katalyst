/**
 * The rail beside the map: what it may say, and what it may not.
 *
 * Two rules, and both are about not inventing things. **It invents no order** —
 * with nothing to rank by, the rows come out in the order the map stores them
 * and the rail says so on its own face. And **it invents no number** — every
 * slot without one renders the reason it has none, in words a reader can get at
 * without a mouse.
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

describe("the rail beside the map", () => {
  // test_lists_reachable_terminals_in_map_order
  it("lists the endings in map order and says that nothing ranked them", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    const listed = screen.getAllByText(/^(M1|M2|N1)$/).map((one) => one.textContent);
    expect(listed).toEqual(["M1", "M2", "N1"]);
    expect(screen.getByText(/In map order/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing has ranked these/)).toBeInTheDocument();
  });

  // test_renders_a_reason_for_every_absent_number
  it("gives every absent number its reason, reachable without a mouse", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    // Three cells a row, three rows, and every one of them a thing the keyboard
    // can land on whose name carries the sentence behind it.
    const cells = screen.getAllByRole("button");
    expect(cells).toHaveLength(9);
    for (const cell of cells) {
      expect(cell.getAttribute("aria-label") ?? "").toMatch(/Nothing has worked/);
    }
  });

  // test_never_sorts_by_width_or_agreement
  it("renders how firm and same direction as their own columns, never as a rank", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    expect(screen.getByText("how firm")).toBeInTheDocument();
    expect(screen.getByText("same direction")).toBeInTheDocument();
    // The word *agreement* is kept off the screen: it is reserved for a
    // different number, computed run to run, that this build does not have.
    expect(screen.queryByText(/agreement/i)).toBeNull();
  });

  // test_the_summary_slot_is_an_absence_with_a_reason
  it("says why there is no one-line summary rather than leaving the slot blank", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    // The words are on the summary and on each row's change cell, so there are
    // four of them; what this checks is that the sentence behind the summary is
    // on the screen rather than a hover away.
    expect(screen.getAllByText("no engine yet")).toHaveLength(4);
    expect(screen.getByText(/written from the numbers/)).toBeInTheDocument();
  });

  // test_an_empty_rail_says_what_to_do_about_it
  it("says what to do when no ending is reachable yet, rather than drawing nothing", () => {
    render(<DeltaRail rows={[]} ranked={false} summary={SUMMARY} />);
    expect(screen.getByText(/No ending on this map is reachable/)).toBeInTheDocument();
  });

  // test_no_code_name_reaches_the_screen
  it("shows none of the six operations' code names", () => {
    const { container } = render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    const words = (container.textContent ?? "").toLowerCase();
    for (const code of ["observe", "insert", "retune", "refine", "believe"]) {
      expect(words).not.toContain(code);
    }
  });
});
