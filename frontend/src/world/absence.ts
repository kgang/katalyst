/**
 * **The words for a number that is not there, in one place.**
 *
 * `spec/vocabulary.md` says *"these are the words; change them here first"*, and
 * for that instruction to mean anything there has to be a *here* on this side
 * too. The five short labels were written out by hand in six files — the world
 * reader, the branch's world, the endings rail, the screen, the growth reducer —
 * which is five chances for one of them to read *no engine* where the others
 * read *no engine yet*, and a reader who cannot tell two absences apart will
 * wait for an answer that is never coming or repair something that was never
 * broken.
 *
 * **The words are shared; the reason never is.** Each of the five kinds has one
 * label and many reasons: *no market* on an `event` and *no market* on a
 * `not_tradeable` ending are the same two words with two different sentences
 * behind them, and the second of those sentences is a finding the claim itself
 * carries. So this module owns the labels and nothing else, and every caller
 * says why for itself.
 *
 * **Five kinds, not three.** *No engine yet* says nothing has run and invites
 * waiting. *Not worked out* says the engine was asked, answered, and would not —
 * which invites repairing what it turned down, and which will say the same thing
 * every time until somebody does. *The ask did not come back* says the engine is
 * there, it was asked, and one attempt got no reply — which invites asking
 * again. Three different facts about the same empty slot.
 */

import type { Absence, AbsenceKind } from "./types";

/**
 * The words each kind of absence shows on the tile.
 *
 * Written as a record over the kind so that adding a sixth kind to the type
 * fails to compile here, rather than reaching a screen with nothing to print.
 */
export const ABSENCE_WORDS: Record<AbsenceKind, string> = {
  no_market: "no market",
  not_said: "—",
  no_engine: "no engine yet",
  refused: "not worked out",
  ask_failed: "the ask did not come back",
};

/**
 * One absence: the vocabulary's words for its kind, and this caller's own
 * reason.
 *
 * @param kind Which of the five this is.
 * @param reason Why, in this particular case, in a whole sentence. It is what a
 *   reader sees on a hover and in the panel, so it says what to do about it
 *   wherever there is something to do.
 */
export function absence(kind: AbsenceKind, reason: string): Absence {
  return { kind, words: ABSENCE_WORDS[kind], reason };
}
