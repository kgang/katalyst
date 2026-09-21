/**
 * Why the engine reports no change on a claim, in one sentence.
 *
 * **There is one of these sentences in the product and this is it.** The tile's
 * movement line, the rail's greyed row and the panel's *what your edit did* all
 * read it from here. Before this file there were four of them, written apart,
 * and each named a different cause — which is how two of them came to be flatly
 * false about half the claims they appeared on.
 *
 * **What the engine actually says.** A claim comes out `shifted` only when
 * *both* halves of its test pass: the move clears a floor, and the versions of
 * the map agree on which way it went (`spec/multiverse/diff.md`, and
 * `backend/src/katalyst/domain/diff.py` where the two constants live).
 * `unchanged` is the default — it is what a claim gets when *either* half fails,
 * and the engine does not record which. Neither does its answer: the floor and
 * the bar are constants inside the engine and appear nowhere on the wire.
 *
 * **So this sentence names no cause.** It gives the engine's verdict and the
 * engine's own two numbers and stops. Working the cause out here would mean
 * hard-coding the engine's floor and its bar in the browser and re-running the
 * `shifted` test against them — a second engine on the map, disagreeing with the
 * first about which claims held still, with nobody able to say which was right.
 * The one exception is the case the engine *does* name, on its own row: a claim
 * that moved only because an observation changed how much each version counts.
 *
 * If the reader should be told which half failed, the engine is the one that can
 * say it — either by naming the two constants in its answer or by saying on the
 * row which half a claim failed. Until it does, this sentence is the honest one.
 */

import { toShare, toTwoFigures } from "../../components/BeliefChip";
import type { Movement } from "../../world/types";

/** What the line reads where a move would go, when the engine says there was none. */
export const NO_CHANGE = "no change";

/**
 * The sentence behind *no change* on one claim.
 *
 * @param moved What the engine read on this claim: the two numbers, which way
 *   they went, and the share of versions that agreed. Absent when the engine
 *   reported no pair of readings for it at all — which happens only when one of
 *   the two worlds does not hold the claim.
 */
export function noChangeReason(moved: Movement | undefined): string {
  if (moved === undefined) {
    return (
      "The engine compared the two worlds and reports no change on this claim. It gave no pair " +
      "of readings for it, so there is nothing here to put beside the verdict."
    );
  }
  if (moved.onlyReweighted === true) {
    // The one cause the engine states outright, on the claim's own row. Inside
    // every version of the map the number held exactly still; what moved was how
    // much each version counts, which is why no direction was there to agree on.
    return (
      `The engine reports no change on this claim: inside every version of the map its number ` +
      `held still, and what moved was how much each version counts — from ` +
      `${toTwoFigures(moved.from)} to ${toTwoFigures(moved.to)} across the lot of them.`
    );
  }
  const agreed = moved.sameDirection.reading;
  const versions =
    agreed === undefined
      ? ""
      : `, and ${toShare(agreed)} of the versions of the map moved the same way`;
  return (
    `The engine compared the two worlds and reports no change on this claim: it read ` +
    `${toTwoFigures(moved.from)} then ${toTwoFigures(moved.to)}${versions}. A move is reported ` +
    `only when it is far enough and the versions agree on its direction, and this one did not ` +
    `clear both. Which of the two it was is the engine's to say, and it does not say.`
  );
}
