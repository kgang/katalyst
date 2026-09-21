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
import { NO_CHANGE, noChangeInAWord, noChangeReason } from "../../graph/diff/noChange";
import type { DeltaRow, Movement } from "../../world";
import { absence, inTheEnginesWords, noReadingAtAll } from "../../world/absence";
import { DeltaRail } from "../DeltaRail";

/** Where a number will go, and why it is not there yet. */
const NOT_YET = {
  absence: noReadingAtAll("Nothing has worked this number through the map yet."),
};

/** Three endings, in the order the stored example's map holds them. */
const ROWS: DeltaRow[] = [
  {
    claimId: "M1",
    label: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind: "market",
    move: {
      absence: absence("no_engine", "Nothing has worked this ending's number through the map."),
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
  {
    claimId: "M2",
    label: "The energy fund XLE underperforms SPY by more than 3%.",
    kind: "market",
    move: {
      absence: absence("no_engine", "Nothing has worked this ending's number through the map."),
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
  {
    claimId: "N1",
    label: "Omani-mediated talks resume publicly.",
    kind: "not_tradeable",
    move: {
      absence: absence("no_engine", "Nothing has worked this ending's number through the map."),
    },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
  },
];

/** The rail's one-line summary, which is an absence with its reason too. */
const SUMMARY = {
  absence: absence(
    "no_engine",
    "The one line saying what this edit did to the trades is written from the numbers.",
  ),
};

/**
 * The talks, as the change list carries an ending the engine left off its
 * ranking.
 *
 * It is built **through the one module that owns the words** rather than out of
 * sentences written here, so that what the tests below check is the rail drawing
 * the engine's own word — not this file's idea of what that word ought to look
 * like.
 *
 * The two readings and the share are plainly made up and nothing below reads
 * them; what is real is the engine's word for which half of its test the claim
 * failed, which is the only thing that changes between one call and the next.
 *
 * @param because The engine's own word, or nothing at all where it gave none.
 */
function heldFor(because: Movement["unchangedBecause"]): DeltaRow {
  const moved: Movement = {
    from: 0.2,
    to: 0.3,
    way: "up",
    by: 0.1,
    sameDirection: { reading: 0.5 },
    unchangedBecause: because,
  };
  return {
    claimId: "N1",
    label: "Omani-mediated talks resume publicly.",
    kind: "not_tradeable",
    move: { absence: inTheEnginesWords(NO_CHANGE, noChangeReason(moved)) },
    rangeWidth: NOT_YET,
    agreement: NOT_YET,
    noChange: true,
    noChangeBecause: noChangeInAWord(moved),
  };
}

/**
 * Three ranked rows, in the order they were handed over.
 *
 * Deliberately **not** map order — the map holds M1, M2, N1 and this list puts
 * N1 last — so that a rail which re-sorted would come back in a different order
 * and every test below would see it.
 *
 * **Every number here is a shape, not a measurement, and none of them is the
 * engine's answer for any real branch.** What is checked is that what came in
 * comes out, in the order it came in. On the stored example's strike branch the
 * engine ranks two endings and leaves the talks off the ranking altogether,
 * which is the case
 * `test_an_unmoved_terminal_is_a_greyed_row_not_a_missing_one` is about.
 */
const RANKED: DeltaRow[] = [
  {
    claimId: "M1",
    label: 'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind: "market",
    move: {
      reading: { from: 0.496, to: 0.417, largestOn: "2026-10-04", way: "down", by: -0.0791 },
    },
    rangeWidth: { reading: 0.269 },
    agreement: { reading: 0.9663 },
  },
  {
    claimId: "M2",
    label: "The energy fund XLE underperforms SPY by more than 3%.",
    kind: "market",
    move: { reading: { from: 0.432, to: 0.363, largestOn: "2026-10-06", way: "down", by: -0.069 } },
    rangeWidth: { reading: 0.278 },
    agreement: { reading: 0.9553 },
  },
  {
    claimId: "N1",
    label: "Omani-mediated talks resume publicly.",
    kind: "not_tradeable",
    move: { reading: { from: 0.281, to: 0.369, largestOn: "2026-10-11", way: "up", by: 0.0877 } },
    rangeWidth: { reading: 0.316 },
    agreement: { reading: 0.9995 },
  },
];

/**
 * Which endings the rail listed, in the order it drew them.
 *
 * Read off each row's own words rather than off an identifier: the rail names an
 * ending by what it says, and numbers the rows by where they sit in the order it
 * was given. On a generated map an identifier is twenty-six characters nobody
 * reads, so none is printed anywhere (`world/naming.ts`).
 */
function inOrder(): string[] {
  const which = (words: string): string =>
    words.includes("Polymarket")
      ? "M1"
      : words.includes("energy fund")
        ? "M2"
        : words.includes("talks")
          ? "N1"
          : words;
  return [...document.querySelectorAll(".delta-rail__label")].map((one) =>
    which(one.textContent ?? ""),
  );
}

describe("the rail beside the map", () => {
  it("test_lists_reachable_terminals_in_map_order", () => {
    render(<DeltaRail rows={ROWS} ranked={false} summary={SUMMARY} />);
    expect(inOrder()).toEqual(["M1", "M2", "N1"]);
    expect(screen.getByText(/In map order/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing has ranked these/)).toBeInTheDocument();
  });

  it("test_the_rail_keeps_the_engines_order", () => {
    // The rows arrive ranked and are drawn in that order. Nothing here sorts
    // them, and nothing here re-ranks them: a ranking is a claim about which
    // change matters most, and it is the engine's claim to make.
    const { rerender } = render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);
    expect(inOrder()).toEqual(["M1", "M2", "N1"]);

    // Hand the same three rows over in a different order and the rail draws
    // them in that order too — which is what says the order on screen is the
    // one it was given rather than one it worked out.
    const shuffled = [RANKED[2], RANKED[0], RANKED[1]] as DeltaRow[];
    rerender(<DeltaRail rows={shuffled} ranked={true} summary={SUMMARY} />);
    expect(inOrder()).toEqual(["N1", "M1", "M2"]);

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
    expect(inOrder()).toEqual(["M1", "M2", "N1"]);

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
    //
    // This is the ending the whole rule was written for. On the stored
    // example's strike branch the talks make the biggest move on the map and
    // the engine still will not call it a move, because the one arrow into them
    // is the map's one bare assertion and the versions of the map end up
    // disagreeing which way the talks went. A list that dropped it would drop
    // the most interesting thing on the map without saying so.
    const { container } = render(
      <DeltaRail
        rows={[RANKED[0] as DeltaRow, heldFor("versions_disagree")]}
        ranked={true}
        summary={SUMMARY}
      />,
    );
    expect(screen.getByText("no change")).toBeInTheDocument();
    expect(screen.getByText(/Endings that did not move follow/)).toBeInTheDocument();

    // It is on the list, it is the row it says it is, and it is marked as one
    // that held still — read off the row rather than off its words, because the
    // rail names an ending in the ending's own sentence and a test that matched
    // that sentence would be a test of the copy.
    const rows = [...container.querySelectorAll(".delta-rail__row")];
    expect(rows.map((row) => row.getAttribute("data-about"))).toEqual(["M1", "N1"]);
    expect(rows.map((row) => row.getAttribute("data-moved"))).toEqual(["yes", "no"]);
  });

  it("test_the_no_change_sentence_comes_from_the_engines_own_word", () => {
    // A claim that barely moved and a claim whose versions of the map
    // disagreed which way are two different findings, and the reader is told
    // which. The word is the engine's, on the claim's own row; the browser
    // picks the words that go with it and works nothing out, because the floor
    // and the bar that decide it are constants inside the engine and are on no
    // wire.
    const { rerender } = render(
      <DeltaRail rows={[heldFor("versions_disagree")]} ranked={true} summary={SUMMARY} />,
    );
    const disagreed = screen.getByText("no change");
    expect(screen.getByText("the versions disagreed which way")).toBeInTheDocument();
    expect(screen.queryByText("barely moved")).toBeNull();
    expect(disagreed.getAttribute("aria-label") ?? "").toMatch(/did not agree which way it went/);

    rerender(<DeltaRail rows={[heldFor("under_the_floor")]} ranked={true} summary={SUMMARY} />);
    expect(screen.getByText("barely moved")).toBeInTheDocument();
    expect(screen.queryByText("the versions disagreed which way")).toBeNull();
    expect(screen.getByText("no change").getAttribute("aria-label") ?? "").toMatch(
      /smaller than the engine will report/,
    );

    // And where the engine gave no word, neither does the rail: a half-line
    // nobody can account for is exactly what this product refuses to draw.
    rerender(<DeltaRail rows={[heldFor(undefined)]} ranked={true} summary={SUMMARY} />);
    expect(screen.queryByText("barely moved")).toBeNull();
    expect(screen.queryByText("the versions disagreed which way")).toBeNull();
  });

  it("test_a_greyed_row_is_not_greyed_by_colour_alone", () => {
    // Convert the screen to grey, or read the list out loud, and a row that is
    // merely a shade quieter than its neighbours says nothing at all. So the
    // row says it twice: the change cell reads the engine's verdict in words,
    // and the half-line under the ending says which half of the engine's test
    // it failed. Neither is a colour.
    const { container } = render(
      <DeltaRail rows={[heldFor("versions_disagree")]} ranked={true} summary={SUMMARY} />,
    );
    const row = container.querySelector('.delta-rail__row[data-moved="no"]') as HTMLElement;
    const words = (row.textContent ?? "").toLowerCase();
    expect(words).toContain("no change");
    expect(words).toContain("the versions disagreed which way");
  });

  it("test_a_ranked_row_names_the_day_the_two_worlds_are_furthest_apart", () => {
    render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);
    // A row is read on the day of largest divergence rather than on the claim's
    // own judging day, so the row says which day that was. A number whose day is
    // not said is a number nobody can check. The day is written the way every
    // other day on this canvas is written, rather than in the format the wire
    // carries it in.
    expect(screen.getByText(/down · largest on Oct 4/)).toBeInTheDocument();
    expect(screen.getByText(/up · largest on Oct 11/)).toBeInTheDocument();
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

  it("test_the_rows_are_the_first_thing_in_the_rail", () => {
    // **What did my edit do, ranked** is the best artefact in this product and
    // it was the last thing a reader landed on: heading, then a summary four or
    // five lines long at this width, then a three-line note about how the order
    // was arrived at, and only then the rows. The rows come first now; the note
    // is the caption it always read like, and the summary closes.
    const { container } = render(<DeltaRail rows={RANKED} ranked={true} summary={SUMMARY} />);
    const rail = container.querySelector(".delta-rail") as HTMLElement;
    const where = (selector: string): number =>
      [...rail.children].findIndex((child) => child.matches(selector));

    expect(where(".delta-rail__heading")).toBe(0);
    expect(where(".delta-rail__table")).toBe(1);
    expect(where(".delta-rail__table")).toBeLessThan(where(".delta-rail__order"));
    expect(where(".delta-rail__table")).toBeLessThan(where(".delta-rail__summary"));
    // And none of the three went missing in the move.
    for (const part of [".delta-rail__order", ".delta-rail__summary", ".delta-rail__reason"]) {
      expect(where(part)).toBeGreaterThan(1);
    }
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
