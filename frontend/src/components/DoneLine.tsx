/**
 * Why the generation stopped, in the engine's words for each reason — and, when
 * something broke instead, the one plain sentence it left.
 *
 * **The sentence itself is no longer printed here.** From 2026-09-21 the run's
 * one sentence lives in the strip at the foot of the map, which is also the
 * polite region a screen reader hears, so a copy of it here would be the same
 * words twice in two of three stacked strips of prose — which is exactly what
 * the strip was built to end. The seven sentences below are still written here,
 * because this is where they belong and because the spoken line reads them; what
 * this component now draws is the tail of the strip: the run's own counts, and
 * the offer to run a cut stream again.
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

/**
 * What a stream that simply stopped says.
 *
 * **It is not a failure and does not read as one.** Nothing here can name what
 * went wrong, because on this side of the connection nothing did: a server was
 * restarted, a proxy gave up on a connection it thought was idle, a laptop
 * slept. So the sentence says the one thing that is known — the stream ended
 * before the run said it had finished — and says what became of what arrived.
 *
 * It lives beside `WHY_IT_STOPPED` because it is the eighth thing this line can
 * say, and because the spoken line and the printed one must not drift.
 */
export const THE_STREAM_ENDED_EARLY =
  "The stream ended before this run said it had finished, so there is no telling whether the " +
  "map below is all of it.";

/** What the line needs to draw itself. */
export interface DoneLineProps {
  /** The closing event, when the run closed. */
  readonly done: Done | null;
  /** The one sentence a broken run left, when one broke. */
  readonly failure: string | null;
  /**
   * True when the stream stopped without a terminator of any kind.
   *
   * A different thing from either of the two above: `done` is the run saying it
   * finished and `failure` is the run saying it broke, and this is the run
   * saying nothing at all.
   */
  readonly endedEarly?: boolean;
  /**
   * Ask for the same sentence again, and whether doing so spends money.
   *
   * Left out, no offer is made — which is what a run that finished properly
   * wants, because there is nothing to offer: the map is on screen.
   */
  readonly runAgain?: {
    /** True for a live run, false when this copy plays recordings and spends nothing. */
    readonly costsMoney: boolean;
    readonly go: () => void;
  };
}

/**
 * What a run that has stopped puts at the end of the strip: its own counts, and
 * the offer to ask again when the stream was cut.
 *
 * Nothing until the run stops, because until then there is nothing to say that
 * the strip's sentence is not already saying.
 */
export function DoneLine({ done, failure, endedEarly = false, runAgain }: DoneLineProps) {
  const kind = endedEarly
    ? "ended_early"
    : failure !== null
      ? "failed"
      : done === null
        ? null
        : done.reason;
  if (kind === null) {
    return null;
  }
  return (
    <p className="done-line" data-kind={kind}>
      {/* The run's own three figures, exactly as the closing event counted
          them. Nothing here adds two numbers together. */}
      {done === null || endedEarly || failure !== null ? null : (
        <span className="done-line__counts">
          {`${done.claims} claims · ${done.links} arrows · ${done.rejected} refused`}
        </span>
      )}
      {endedEarly ? (
        <span className="done-line__counts">nothing was made up to fill the gap</span>
      ) : null}
      {runAgain === undefined ? null : (
        <button className="done-line__again" type="button" onClick={runAgain.go}>
          {/* The offer, with its price on it. A control that quietly spends
              money the second time it is pressed is the one control in this
              product that must say so before it is pressed. */}
          {runAgain.costsMoney
            ? "Run it again — this asks the model again, and spends again"
            : "Play it again — this plays the recording again, and spends nothing"}
        </button>
      )}
    </p>
  );
}
