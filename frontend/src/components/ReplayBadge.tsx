/**
 * The mark on the canvas saying this session is playing a recording back.
 *
 * It is a fact about the **session**, not a badge on a claim, and it is on screen
 * from the moment the run starts — long before the receipt that also says so
 * arrives. That is the whole reason it exists twice: the browser knows there is
 * no model key before the stream has said anything, and a reader should not watch
 * a map build itself for a minute before being told where it came from.
 *
 * **Two sources, and the receipt is the authority.** The badge is set from
 * whether a key is configured; the receipt, when it lands, carries the mode and
 * the day the recording was made. The receipt names the day here, and if it ever
 * says *live* where this badge says *replay*, the badge takes the receipt's word
 * and says out loud that the two disagreed. Two derivations of one line are
 * normally the thing this product refuses; this is the one place both are needed,
 * so the rule is written down rather than left to luck.
 */

import "./replayBadge.css";

/** What the badge needs to draw itself. */
export interface ReplayBadgeProps {
  /**
   * The day the recording was made, as the receipt reported it, or null before
   * the receipt has arrived. Never the browser's own clock and never a file name.
   */
  readonly recordingDate: string | null;
  /**
   * What the receipt says this run was, or null before it arrives. When it says
   * `live` and this badge is on screen, the two disagree and the badge says so.
   */
  readonly receiptMode: "live" | "replay" | null;
}

/** The mark in the corner of the map. */
export function ReplayBadge({ recordingDate: day, receiptMode }: ReplayBadgeProps) {
  const disagreed = receiptMode === "live";
  return (
    <p className="replay-badge" data-disagreed={disagreed ? "yes" : "no"}>
      <span className="replay-badge__word">replay</span>
      <span className="replay-badge__line">
        {disagreed
          ? "This session has no model key, so it played a recording — but the receipt says the " +
            "run was live. The receipt is the authority, and the two disagreeing is itself " +
            "worth seeing."
          : day === null
            ? "No model key is configured, so this map is a recording being played back through " +
              "the same route, the same events and the same canvas. The receipt will name the " +
              "day it was made."
            : "No model key is configured, so this map is a recording being played back through " +
              "the same route, the same events and the same canvas. It was made on:"}
      </span>
      {day === null ? null : <span className="replay-badge__day">{day}</span>}
    </p>
  );
}
