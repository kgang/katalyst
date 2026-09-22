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
 * **What the engine says.** A claim comes out `shifted` only when its move
 * clears a floor, and `unchanged` when it does not. The engine says so on the
 * claim's own row, in one plain word: *under the floor* when the move is too
 * small to report at all.
 *
 * **So the browser reports the engine's word and works nothing out.** The floor
 * is a constant inside the engine and appears nowhere in its answer, so
 * re-running the test here is not possible even by accident — which is the
 * point. Where the engine gives no word, neither does this file.
 *
 * **Two of the engine's own answers are not shown at all** *(2026-09-22, R48)*.
 * It has a second reason for calling a claim unchanged — the two thousand
 * versions of the map disagreed which way it went — and a second finding about a
 * claim that did move: that it moved only because an observation made some of
 * those versions count for more. Both are facts about running the map many
 * times, and Kent cut running the map many times from this product. They are
 * still on the wire; `world/apiSource.ts` drops them on the way in, and they die
 * with the engine half. So a claim that failed on either of them reaches this
 * file with no word at all, and this file says so plainly rather than inventing
 * one.
 */

import { toTwoFigures } from "../../components/BeliefChip";
import type { Movement, Standing } from "../../world/types";
import { ENGINE_IN_WORDS, type EngineState } from "./agreement";
import { ADDED } from "./badges";

/** What the line reads where a move would go, when the engine says there was none. */
export const NO_CHANGE = "no change";

/**
 * Why this claim's difference was not called a move, in a handful of words.
 *
 * It is the caption on a greyed row of the change list — the same slot a row
 * that moved uses for *down · largest on Oct 4* — so that a row which held still
 * says **in words** why it is greyed. Words rather than a shade, because a
 * greyed row that is only paler than its neighbours says nothing at all once the
 * screen is read in grey, and nothing at all to somebody reading the list out.
 *
 * @param moved What the engine read on this claim: the two numbers, which way
 *   they went, and its own word for why it would not call that a move.
 * @returns The phrase, or nothing at all where the engine gave no word this
 *   product may show — in which case nothing is drawn, rather than a phrase
 *   nobody can account for.
 */
export function noChangeInAWord(moved: Movement | undefined): string | undefined {
  return moved?.unchangedBecause === "under_the_floor" ? "barely moved" : undefined;
}

/**
 * The sentence behind *no change* on one claim.
 *
 * @param moved What the engine read on this claim: the two numbers, which way
 *   they went, and its own word for why that is not a move. Absent when the
 *   engine reported no pair of readings for it at all — which happens only when
 *   one of the two worlds does not hold the claim.
 */
export function noChangeReason(moved: Movement | undefined): string {
  if (moved === undefined) {
    return (
      "The engine compared the two maps and reports no change on this claim. It gave no pair " +
      "of readings for it, so there is nothing here to put beside the verdict."
    );
  }
  // Why it is not a move is the engine's word, copied across. Nothing here
  // compares a move with a floor: the floor is not on the wire, so the browser
  // could not re-run the test if it wanted to.
  const why =
    moved.unchangedBecause === "under_the_floor"
      ? "It says why: the move is smaller than it will report at all."
      : "It gave no reason this product can show for that verdict, so none is written here.";
  return (
    `The engine compared the two maps and reports no change on this claim: it read ` +
    `${toTwoFigures(moved.from)} then ${toTwoFigures(moved.to)}. ${why}`
  );
}

/** What a change-list row says when the engine ranked no move on that ending. */
export interface QuietRow {
  /** What stands in the change column, where a move would have been. */
  readonly words: string;
  /** The sentence behind those words, which is what a reader gets on a press. */
  readonly reason: string;
  /**
   * The half-line under the ending's own words, or nothing where there is
   * nothing true to put in it.
   */
  readonly note: string | undefined;
}

/**
 * What a change-list row says when the engine gave that ending no row of its
 * own — **one rule for every reason it might not have one.**
 *
 * The engine ranks an ending only when it calls it `shifted`. Everything else
 * falls to the change list, and the change list keeps the row: an ending missing
 * from the list could mean it held still, or that it is not on this map, or that
 * you forced it false a moment ago, and a reader cannot tell those apart by
 * looking at a list something was left out of. Forcing an ending false is the
 * loudest thing an edit can do to one, and it used to be the quietest thing on
 * this screen — the row simply was not drawn.
 *
 * **Each state says its own true thing, read off the engine's word.** Nothing
 * here is decided by looking at a number.
 *
 * | The engine's word | What the row reads | Why |
 * |---|---|---|
 * | it did not move | *no change*, and the engine's own word for why | The engine compared two numbers and would not call the difference a move |
 * | it was supposed false | the word the tile shows — *Supposed · Oct 1* | Your edit fixed its value, so it is false in every world the engine works through and there is no likelihood to show |
 * | it arrived with the edit | *Added* | There is no earlier reading of it to put beside the new one |
 *
 * **A claim whose value an edit fixed shows the word, never a number**, here as
 * on its tile: the engine stores a flat `0` for a forced-false claim, and a row
 * reading `.46 ▼ <.01` would be that zero wearing the certainty guard's clothes.
 *
 * @param state The engine's own word for what happened to this ending, or
 *   nothing at all where the engine did not mention it.
 * @param moved What the engine read on it: the two numbers, which way they
 *   went, and its own word for why that is not a move.
 * @param standing The word this ending's tile shows instead of a likelihood,
 *   when an edit has fixed its value.
 */
export function quietRow(
  state: EngineState | undefined,
  moved: Movement | undefined,
  standing: Standing | undefined,
): QuietRow {
  if (state === "killed") {
    return {
      words: standing?.words ?? ENGINE_IN_WORDS.killed,
      reason:
        `${standing?.reason ?? "Your edit fixed this ending's value to false."} So there is no ` +
        `likelihood here to put beside the one this ending had before, and no move for the ` +
        `engine to rank. It is on the list because forcing an ending false is the loudest thing ` +
        `an edit can do to one, and a list it had vanished from would say nothing at all ` +
        `happened.`,
      note: ENGINE_IN_WORDS.killed,
    };
  }
  if (state === "added") {
    return {
      words: standing?.words ?? ADDED.words,
      reason:
        `${standing?.reason ?? ADDED.reason} There is no earlier reading of it to put beside ` +
        `this world's, so the engine ranked no move on it. It is on the list because an ending ` +
        `you added is still an ending your edit reaches.`,
      note: ENGINE_IN_WORDS.added,
    };
  }
  return {
    words: NO_CHANGE,
    reason:
      `${noChangeReason(moved)} It is listed so that holding still cannot be mistaken for not ` +
      `being here.`,
    // Why the engine would not call this a move — its own word, and nothing at
    // all where it gave none this product may show. *It did not move* is
    // already in the change cell beside it, so there is nothing to fall back
    // to and nothing lost: the row is still carried by words rather than by
    // being paler.
    note: noChangeInAWord(moved),
  };
}
