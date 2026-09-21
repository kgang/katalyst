/**
 * The mark saying this session is playing a recording back.
 *
 * It is a fact about the **session**, not a badge on a claim, and it is on screen
 * from the moment the run starts — long before the receipt that also says so
 * arrives. That is the whole reason it exists twice: the browser knows there is
 * no model key before the stream has said anything, and a reader should not watch
 * a map build itself for a minute before being told where it came from.
 *
 * **It is a badge, and it sits beside the title.** It used to be a paragraph
 * floating over the canvas, which was wrong twice: nothing in this product may
 * sit over the map, and on a real ten-claim map it covered tiles. So the mark is
 * a word and a day, up in the bar with the map's name, and the sentence that
 * explains it goes in the line under the map where every other sentence about
 * where this map came from already lives.
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

/** Whether the badge and the receipt disagree about what this run was. */
function theyDisagree(receiptMode: ReplayBadgeProps["receiptMode"]): boolean {
  return receiptMode === "live";
}

/**
 * The sentence that explains the badge, for the line under the map.
 *
 * It is written here, beside the badge it explains, so the two cannot drift —
 * and it is printed there rather than on the canvas, because nothing in this
 * product sits over the map.
 */
export function replaySentence({ recordingDate, receiptMode }: ReplayBadgeProps): string {
  if (theyDisagree(receiptMode)) {
    return (
      "This session has no model key, so it played a recording — but the receipt says the run " +
      "was live. The receipt is the authority, and the two disagreeing is itself worth seeing."
    );
  }
  const from =
    recordingDate === null
      ? "The receipt will name the day it was made."
      : `It was made on ${recordingDate}.`;
  return (
    "No model key is configured, so this map is a recording being played back through the same " +
    `route, the same events and the same canvas. ${from}`
  );
}

/** The mark beside the map's name: one word, and the day. */
export function ReplayBadge({ recordingDate, receiptMode }: ReplayBadgeProps) {
  const disagreed = theyDisagree(receiptMode);
  return (
    <span className="replay-badge" data-disagreed={disagreed ? "yes" : "no"}>
      <span className="replay-badge__word">replay</span>
      {recordingDate === null ? null : <span className="replay-badge__day">{recordingDate}</span>}
      {/* Said out loud for a reader who is not looking at the bar. The same
          sentence is printed in full under the map. */}
      <span className="replay-badge__spoken">{replaySentence({ recordingDate, receiptMode })}</span>
    </span>
  );
}
