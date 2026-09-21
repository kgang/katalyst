/**
 * The working of a run, drawn once for both of the things that have one.
 *
 * A generation's working is read back from the server, which holds it for the
 * life of the process. An insert's arrives in the answer to the insert, because
 * there is nowhere else it could be: an insert is one request and one answer,
 * nothing about it is remembered, so there is no identifier to ask by and no
 * route to ask at. Two different journeys, one list of lines, and **one
 * component** — a reader who has learned to read one of them has learned to read
 * the other, and the two cannot come to disagree about what a refusal looks like.
 *
 * **Every line is in the engine's own words.** An accepted line names the claim
 * it became by quoting it; a refused line quotes what the model wrote and then
 * carries the validator's own sentence, one per rule broken, with nothing added;
 * a stopped line carries the model's own one-sentence reason. Nothing here
 * composes a sentence about any of the three, and no identifier is printed.
 *
 * **Three kinds of line, not two.** A proposal was accepted, a proposal was
 * refused, or the model answered *Stop* on a line and it closed with nothing
 * added. The third is the one a reader would otherwise never see: it makes no
 * event on the stream, because nothing about the map changed. **A stopped line
 * carries no place in the working** — the count counts what was proposed, and a
 * stop proposed nothing — so the numbers have gaps in them, and the gaps are the
 * stops.
 *
 * **Two things a line says that are not about the map, and are drawn when they
 * are there.** An address the model cited that the search never returned, named
 * rather than silently dropped — otherwise an arrow that says it *argued* looks
 * like one that said it *documented*. And a reference class offered with nothing
 * behind it, said as a class with **no number beside it**, because a figure with
 * no page behind it reads as measured however it is marked.
 */

import type { TranscriptLine } from "../stream/transcript";
import "./inspector.css";

/** What the list needs to draw itself. */
export interface TheWorkingProps {
  /** Every line, in the order it happened. */
  readonly lines: readonly TranscriptLine[];
  /**
   * Which line the reader arrived at, when they arrived at one — a refusal
   * opened from the strip beside the map. Left out, nothing is marked.
   */
  readonly openAt?: number | null;
}

/** Every call a run took, in order. */
export function TheWorking({ lines, openAt = null }: TheWorkingProps) {
  return (
    <ol className="inspector__transcript">
      {lines.map((line, place) => (
        <li
          className="inspector__line"
          // Two lines can genuinely carry the same words on different claims,
          // and a stopped line has no place of its own, so its position in the
          // list is the only stable name it has.
          // biome-ignore lint/suspicious/noArrayIndexKey: the working arrives as one list from one answer and is never reordered, added to or removed.
          key={`${place}-${line.at ?? "stopped"}`}
          data-what={line.what}
          data-open={line.at !== null && line.at === openAt ? "yes" : "no"}
        >
          <span className="inspector__line-at">{line.at === null ? "—" : line.at}</span>
          <span className="inspector__line-what">{line.what}</span>
          <span className="inspector__line-words">
            {line.in_words}
            {line.violations.map((violation) => (
              <span className="inspector__line-reason" key={violation.message}>
                {violation.message}
              </span>
            ))}
            {(line.dropped ?? []).map((address) => (
              <span className="inspector__line-reason" key={address}>
                {`This call cited ${address}, which the search never returned, so nothing on the map is documented by it.`}
              </span>
            ))}
            {line.no_reference_class === null || line.no_reference_class === undefined ? null : (
              <span className="inspector__line-reason">
                {`A count was offered for "${line.no_reference_class}" with nothing behind it, so the number is not carried and none is shown.`}
              </span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}
