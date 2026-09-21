/**
 * Why the engine reports no change on a claim — one short phrase and one
 * sentence, both written here and nowhere else.
 *
 * **There is one of each in the product and this is where they live.** The
 * tile's movement line, the change list's greyed row and the panel's *what your
 * edit did* all read them from here. Before this file there were four such
 * sentences, written apart, and each named a different cause — which is how two
 * of them came to be flatly false about half the claims they appeared on.
 *
 * **What the engine says.** A claim comes out `shifted` only when *both* halves
 * of its test pass: the move clears a floor, and the versions of the map agree
 * on which way it went (`spec/multiverse/diff.md`, and
 * `backend/src/katalyst/domain/diff.py` where the two constants live).
 * `unchanged` is what a claim gets when either half fails — **and the engine now
 * says which half**, on the claim's own row, in one plain word: *under the
 * floor* when the move is too small to report, *versions disagree* when the move
 * was big enough and the versions of the map did not agree which way. The floor
 * is read first, so a claim that fails both halves says the floor.
 *
 * **So the browser reports the engine's word and works nothing out.** The floor
 * and the bar are constants inside the engine and appear nowhere in its answer,
 * so re-running the test here is not possible even by accident — which is the
 * point. Where the engine gives no word, neither does this file.
 *
 * One case the engine names on its own row and which outranks the word: a claim
 * that moved only because an observation changed how much each version counts.
 * Both are true of such a claim — the half it failed really is the
 * same-direction half — but *the versions did not agree on a direction* is a
 * thin way of saying *every version that counts moved by exactly nothing*, so
 * the fuller of the two is the one shown.
 */

import { toShare, toTwoFigures } from "../../components/BeliefChip";
import type { Movement } from "../../world/types";

/** What the line reads where a move would go, when the engine says there was none. */
export const NO_CHANGE = "no change";

/**
 * The half of the test this claim failed, in a handful of words.
 *
 * It is the caption on a greyed row of the change list — the same slot a row
 * that moved uses for *down · largest on Oct 4* — so that a row which held still
 * says **in words** why it is greyed. Words rather than a shade, because a
 * greyed row that is only paler than its neighbours says nothing at all once the
 * screen is read in grey, and nothing at all to somebody reading the list out.
 *
 * @param moved What the engine read on this claim: the two numbers, which way
 *   they went, the share of versions that agreed, and its own word for which
 *   half of the test the claim failed.
 * @returns The phrase, or nothing at all where the engine gave no word — in
 *   which case nothing is drawn, rather than a phrase nobody can account for.
 */
export function noChangeInAWord(moved: Movement | undefined): string | undefined {
  if (moved === undefined) {
    return undefined;
  }
  if (moved.onlyReweighted === true) {
    return "only how much each version counts moved";
  }
  if (moved.unchangedBecause === "under_the_floor") {
    return "barely moved";
  }
  if (moved.unchangedBecause === "versions_disagree") {
    return "the versions disagreed which way";
  }
  return undefined;
}

/**
 * The sentence behind *no change* on one claim.
 *
 * @param moved What the engine read on this claim: the two numbers, which way
 *   they went, the share of versions that agreed, and which half of the test it
 *   failed. Absent when the engine reported no pair of readings for it at all —
 *   which happens only when one of the two worlds does not hold the claim.
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
  // Which half of the test failed is the engine's word, copied across. Nothing
  // here compares a move with a floor or a share with a bar: neither constant
  // is on the wire, so the browser could not re-run the test if it wanted to.
  const whichHalf =
    moved.unchangedBecause === "under_the_floor"
      ? `The engine says which half it failed: the move is smaller than the engine will report ` +
        `at all.`
      : moved.unchangedBecause === "versions_disagree"
        ? `The engine says which half it failed: the move is far enough, and the versions of ` +
          `the map did not agree which way it went.`
        : `The engine gave no word for which half it failed, which it does only where no ` +
          `version of the map counted in both numbers — so there was no direction for them to ` +
          `agree about.`;
  return (
    `The engine compared the two worlds and reports no change on this claim: it read ` +
    `${toTwoFigures(moved.from)} then ${toTwoFigures(moved.to)}${versions}. A move is reported ` +
    `only when it is far enough and the versions agree on its direction, and this one did not ` +
    `clear both. ${whichHalf}`
  );
}
