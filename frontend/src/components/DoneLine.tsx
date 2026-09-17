/**
 * Why the generation stopped, in the engine's words for each reason — and, when
 * something broke instead, the one plain sentence it left.
 *
 * **One reason arrives, never a list**, and it names what closed the last claim
 * that was still open, with the spending limit and the no-ending case overriding
 * everything above them.
 *
 * Two things the seven sentences do on purpose. **No sentence blames the model
 * for our own rules**: three refusals in a row is our validator turning proposals
 * down and our cap deciding that three is enough, and a sentence reading *"the
 * model stopped answering"* would be a screen accusing a third party of a
 * decision we took. And **each one names the cap and not its value**, because the
 * stream carries no value — a limit printed from memory would be a number nobody
 * on this screen computed, and a limit that had quietly changed on the server
 * would then be a number that was wrong.
 */

import type { Done, StopReason } from "../stream/events";
import "./doneLine.css";

/** What the strip says for each of the seven reasons a run can stop. */
export const WHY_IT_STOPPED: Record<StopReason, string> = {
  reached_terminal:
    "The last line closed properly: it reached something you could trade, or a stated reason " +
    "there is nothing to trade, or the model had nothing more to add.",
  depth_cap:
    "The last line still open ran as far from your sentence as one generation goes, and stopped " +
    "there.",
  width_cap:
    "The last line still open was closed because that claim already has every effect one " +
    "generation draws from it.",
  claim_cap: "The last line still open was closed because the map was full.",
  spend_cap:
    "The run reached its spending limit and stopped where it was. The receipt says what it spent.",
  refusal_cap: "One line was abandoned: three proposals in a row for it were refused.",
  no_terminal:
    "One last call asked every open claim where it ends, and none of them ends in something you " +
    "could trade.",
};

/** What the line needs to draw itself. */
export interface DoneLineProps {
  /** The closing event, when the run closed. */
  readonly done: Done | null;
  /** The one sentence a broken run left, when one broke. */
  readonly failure: string | null;
}

/** Why the run ended, said once, under the map. */
export function DoneLine({ done, failure }: DoneLineProps) {
  if (failure !== null) {
    return (
      <p className="done-line" data-kind="failed">
        <span className="done-line__word">stopped</span>
        {/* One plain sentence, never a stack trace. The map that had been built
            stays exactly where it is: a reader whose run broke after twenty
            claims keeps the twenty claims. */}
        <span className="done-line__why">{failure}</span>
      </p>
    );
  }
  if (done === null) {
    return null;
  }
  return (
    <p className="done-line" data-kind={done.reason}>
      <span className="done-line__word">finished</span>
      <span className="done-line__why">{WHY_IT_STOPPED[done.reason]}</span>
      <span className="done-line__counts">
        {`${done.claims} claims · ${done.links} arrows · ${done.rejected} refused`}
      </span>
    </p>
  );
}
