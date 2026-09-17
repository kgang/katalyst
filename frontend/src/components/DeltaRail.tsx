/**
 * The rail beside the map: the endings your edit can reach.
 *
 * An **ending** is where an argument turns into a position — a claim that names
 * something you could trade, or one that names why there is nothing to trade.
 * The rail lists the ones this edit can reach and, beside each, three things:
 * how far its number moved, **how firm** that number is, and whether it went the
 * **same direction** whatever numbers the map started from.
 *
 * **In this build all three are absences, and the order is map order.** Nothing
 * has worked a number through the map, so there is no move to report, nothing to
 * be firm about, and nothing that agreed or disagreed. And with no numbers there
 * is no ranking either — so the rail lists the endings in the order the map
 * stores them, says so on its own face, and invents nothing. A rail that made up
 * an ordering would be making up the single thing the rail exists to tell you.
 *
 * The two columns are never folded into any ordering, before the engine or
 * after it. They answer different questions and a trader weighs them separately;
 * folding the width into a rank would sink exactly the claims that most deserve
 * a second look.
 */

import { useId, useState } from "react";
import type { DeltaRow, Known } from "../world";
import "./deltaRail.css";

/** What the rail needs to draw itself. */
export interface DeltaRailProps {
  /** The endings this edit can reach, in the order the map stores them. */
  readonly rows: readonly DeltaRow[];
  /**
   * Whether something has put these rows in an order that means something.
   *
   * False in this build, and the rail says so out loud rather than letting map
   * order be mistaken for a ranking.
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

/** Turn a known number into the words a cell prints. */
function asWords(value: Known<number>): Known<string> {
  return value.reading === undefined ? { absence: value.absence } : { reading: `${value.reading}` };
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

      {/* The one line saying what the edit did to the trades. It is written from
          the numbers the edit moved, and nothing has moved one — so it says that
          instead, and says what the map *can* tell you underneath. */}
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
              ? "In the order the engine put them in: the size of the move along the best-backed route."
              : "In map order. Nothing has ranked these, because nothing has worked out a number to rank them by."}
          </p>

          <div className="delta-rail__table">
            <div className="delta-rail__labels" aria-hidden="true">
              <span>change</span>
              <span>how firm</span>
              <span>same direction</span>
            </div>
            <ul className="delta-rail__rows">
              {rows.map((row) => (
                <li className="delta-rail__row" key={row.claimId}>
                  <p className="delta-rail__label">
                    <span className="delta-rail__id">{row.claimId}</span>
                    {row.label}
                    <span className="delta-rail__kind">{KIND_WORDS[row.kind] ?? row.kind}</span>
                  </p>
                  <div className="delta-rail__values">
                    <Cell
                      value={
                        row.move.reading === undefined
                          ? { absence: row.move.absence }
                          : {
                              reading: `${row.move.reading.from} → ${row.move.reading.to}`,
                            }
                      }
                      onReason={setReason}
                    />
                    <Cell value={asWords(row.rangeWidth)} onReason={setReason} />
                    <Cell value={asWords(row.agreement)} onReason={setReason} />
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="delta-rail__reason">
            {reason ??
              "Every dash above carries the same reason as the words beside it. Reach one with " +
                "the keyboard, or point at it, and the reason is printed here."}
          </p>
        </>
      )}
    </section>
  );
}
