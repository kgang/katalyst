/**
 * The mark saying this session is playing a recording back.
 *
 * It is a fact about the **session**, not a badge on a claim, and it is on screen
 * from the moment the run starts — long before the receipt that also says so
 * arrives. That is the whole reason it exists twice: the browser knows the reader
 * asked for the recording before the stream has said anything, and a reader should
 * not watch a map build itself for a minute before being told where it came from.
 *
 * **It is a badge, and it sits beside the title.** It used to be a paragraph
 * floating over the canvas, which was wrong twice: nothing in this product may
 * sit over the map, and on a real ten-claim map it covered tiles. So the mark is
 * a word and a day, up in the bar with the map's name, and the sentence that
 * explains it goes in the line under the map where every other sentence about
 * where this map came from already lives.
 *
 * **Two sources, and they are never merged.** The badge is set from what the
 * reader asked for — *Watch the recording* — and never from whether a key is
 * configured (record 0012, amended 2026-09-21: a recording is reachable with a
 * key, so a key says nothing about this). The browser knows what was asked
 * before the stream says anything, which is the whole reason the badge can be on
 * screen from the first frame.
 * The receipt, when it lands, carries the mode and the day the recording was
 * made, and it names the day here, because a day is a fact only the receipt
 * has.
 *
 * **And when the two disagree, neither wins: the disagreement is the finding.**
 * A session with no key that gets a receipt saying `live` is a copy that has
 * done something nobody can account for, and the honest screen is the one that
 * shows both readings and says they differ — under the map, in the line where
 * every other sentence about where this map came from already lives. The badge
 * stays, marked as disagreed, because it is still true that this session had no
 * key; the receipt stays, because it is still true that the run reported
 * itself live. Resolving it in favour of either would be this screen deciding
 * which of two things it was told to believe, which is the one decision it must
 * not make on a reader's behalf.
 *
 * *(The chapter used to say the badge takes the receipt's word. It does not, and
 * should not — settled here, 2026-09-21, and B9 now says what this does.)*
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
      "A recording was asked for — but the receipt says the run was live. The receipt is the " +
      "authority, and the two disagreeing is itself worth seeing."
    );
  }
  const from =
    recordingDate === null
      ? "The receipt will name the day it was made."
      : `It was made on ${recordingDate}.`;
  return (
    "You asked to watch the recording, so this map is a recording being played back through the " +
    `same route, the same events and the same canvas. No model was called and nothing was spent. ${from}`
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
