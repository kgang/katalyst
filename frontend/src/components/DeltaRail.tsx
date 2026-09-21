/**
 * The rail beside the map: the endings your edit can reach.
 *
 * An **ending** is where an argument turns into a position — a claim that names
 * something you could trade, or one that names why there is nothing to trade.
 * The rail lists the ones this edit can reach and, beside each, three things:
 * how far its number moved, **how firm** that number is, and whether it went the
 * **same direction** whatever numbers the map started from.
 *
 * **The rail ranks nothing.** When the engine has ordered these rows — largest
 * move along the best-backed route first — the rail draws them in that order and
 * says so. When nothing has, it lists them in the order the map stores them and
 * says *that*, because map order is visibly arbitrary while an invented ranking
 * looks like an answer, and a ranking is the one thing the rail exists to tell
 * you.
 *
 * **An ending that did not move still gets a row.** The engine lists the ones
 * that moved; an ending missing from that list could mean either "it held still"
 * or "it is not on this map", and silence cannot be told from absence. So the
 * unmoved ones follow the ranked ones, reading *no change*, never mixed in among
 * them.
 *
 * The two columns are never folded into any ordering. They answer different
 * questions and a trader weighs them separately; folding the width into a rank
 * would sink exactly the claims that most deserve a second look.
 */

import { useId, useState } from "react";
import { toDay } from "../graph/diff/days";
import type { DeltaRow, Known } from "../world";
import { toMovement, toShare, toSize } from "./BeliefChip";
import "./deltaRail.css";

/** What the rail needs to draw itself. */
export interface DeltaRailProps {
  /** The endings this edit can reach, in whatever order they arrived in. */
  readonly rows: readonly DeltaRow[];
  /**
   * Whether something has put these rows in an order that means something.
   *
   * True once the engine has ranked them. False before that, and the rail says
   * so out loud rather than letting map order be mistaken for a ranking.
   */
  readonly ranked: boolean;
  /** The one line saying what this edit did to the trades, or the reason there is none. */
  readonly summary: Known<string>;
}

/** What each kind of ending is, in a word. */
const KIND_WORDS: Record<string, string> = {
  market: "tradeable",
  not_tradeable: "not tradeable",
  event: "event",
  hypothesis: "hypothesis",
};

/**
 * One cell: the number, or the words standing where it would have been.
 *
 * A cell with no number is a button, because the reason it has no number is a
 * sentence and there is no room for a sentence in a column this narrow. Pressing
 * it prints the sentence under the rail; its accessible name carries the same
 * sentence, so a reader who never sees the rail gets it without pressing
 * anything.
 */
function Cell({
  value,
  onReason,
}: {
  value: Known<string>;
  onReason: (reason: string | null) => void;
}) {
  if (value.reading !== undefined) {
    return <span className="delta-rail__value">{value.reading}</span>;
  }
  const { words, reason } = value.absence;
  return (
    <button
      className="delta-rail__value delta-rail__value--absent"
      type="button"
      aria-label={`${words}. ${reason}`}
      onClick={() => onReason(reason)}
      onFocus={() => onReason(reason)}
      onMouseEnter={() => onReason(reason)}
    >
      {words}
    </button>
  );
}

/**
 * The change itself, as one cell reads it: `.50 ▼ .42`, and the day the two
 * worlds were furthest apart.
 *
 * A row is read on the **day of largest divergence** rather than on the claim's
 * own judging day, because a change that shows up for a fortnight and then
 * unwinds is the thing a trader acts on — so the row names that day.
 */
function changeOf(row: DeltaRow): Known<string> {
  const move = row.move.reading;
  if (move === undefined) {
    return { absence: row.move.absence };
  }
  return { reading: toMovement(move.from, move.to, move.by, move.way) };
}

/**
 * How firm the new number is: the width of its own range.
 *
 * A width is a **size**, not a likelihood: it is how far apart the two ends of a
 * band sit. So it takes no certainty guard — a band four thousandths wide is a
 * remarkably firm number and the reader wants to see it, where `<.01` would say
 * only that it is small.
 */
function firmnessOf(row: DeltaRow): Known<string> {
  return row.rangeWidth.reading === undefined
    ? { absence: row.rangeWidth.absence }
    : { reading: toSize(row.rangeWidth.reading) };
}

/** The share of versions of the map that moved the same way, as a whole percentage. */
function sameDirectionOf(row: DeltaRow): Known<string> {
  return row.agreement.reading === undefined
    ? { absence: row.agreement.absence }
    : { reading: toShare(row.agreement.reading) };
}

/** The rail beside the map. */
export function DeltaRail({ rows, ranked, summary }: DeltaRailProps) {
  const [reason, setReason] = useState<string | null>(null);
  const headingId = useId();

  return (
    <section className="delta-rail" aria-labelledby={headingId}>
      <h2 className="delta-rail__heading" id={headingId}>
        Where this edit ends up
      </h2>

      {/* The one line saying what the edit did to the trades. The engine writes
          it from a fixed template with its own numbers in the blanks; before it
          has, the slot says why there is none. */}
      <p className="delta-rail__summary">
        {summary.reading ?? summary.absence.words}
        {summary.reading === undefined ? (
          <span className="delta-rail__summary-reason">{summary.absence.reason}</span>
        ) : null}
      </p>

      {rows.length === 0 ? (
        <p className="delta-rail__empty">
          No ending on this map is reachable from your edits yet. Make one — press E on a claim —
          and the endings it can reach are listed here.
        </p>
      ) : (
        <>
          <p className="delta-rail__order">
            {ranked
              ? "In the order the engine put them in: the size of the move times the weakest arrow on the best-backed route behind it. Endings that did not move follow, and are not ranked."
              : "In map order. Nothing has ranked these, because nothing has worked out a number to rank them by."}
          </p>

          <div className="delta-rail__table">
            <div className="delta-rail__labels" aria-hidden="true">
              <span>change</span>
              <span>how firm</span>
              <span>same direction</span>
            </div>
            <ul className="delta-rail__rows">
              {rows.map((row, place) => (
                <li
                  className="delta-rail__row"
                  key={row.claimId}
                  data-moved={row.noChange === true ? "no" : "yes"}
                >
                  <p className="delta-rail__label">
                    {/* Where this ending sits in the engine's own order, which is
                        what the rail is for. It was the claim's identifier, and on
                        a generated map that is twenty-six characters nobody reads
                        (`world/naming.ts`). */}
                    <span className="delta-rail__id">{place + 1}</span>
                    {row.label}
                    <span className="delta-rail__kind">{KIND_WORDS[row.kind] ?? row.kind}</span>
                    {row.move.reading === undefined ? null : (
                      <span className="delta-rail__day">
                        {`${row.move.reading.way} · largest on ${toDay(row.move.reading.largestOn)}`}
                      </span>
                    )}
                  </p>
                  <div className="delta-rail__values">
                    <Cell value={changeOf(row)} onReason={setReason} />
                    <Cell value={firmnessOf(row)} onReason={setReason} />
                    <Cell value={sameDirectionOf(row)} onReason={setReason} />
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="delta-rail__reason">
            {reason ??
              "Every reading above is the engine's own, in the engine's own order. Reach one with " +
                "the keyboard, or point at it, and whatever it has to say is printed here."}
          </p>
        </>
      )}
    </section>
  );
}
