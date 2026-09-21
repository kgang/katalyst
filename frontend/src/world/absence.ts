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
 * **It is the only way to make one.** `Absence` carries a mark no code outside
 * this file can write, so a hand-built `{ kind, words, reason }` does not
 * compile. That is the difference between a module that says it is the one
 * place and a module that is: the words were written out by hand in six files
 * before, and "change them here first" meant nothing while the seventh was one
 * object literal away.
 *
 * @param kind Which of the five this is.
 * @param reason Why, in this particular case, in a whole sentence. It is what a
 *   reader sees on a hover and in the panel, so it says what to do about it
 *   wherever there is something to do.
 */
export function absence(kind: AbsenceKind, reason: string): Absence {
  // The mark is a promise to the compiler and nothing at runtime, so it is
  // made here by the one cast in this codebase that is allowed to make one.
  return { kind, words: ABSENCE_WORDS[kind], reason } as Absence;
}

/**
 * A slot with **no number for it to be about**, which is not the same as a
 * number nobody has worked out.
 *
 * The rail beside a diff has rows that only mean something about a claim that
 * moved: how firm its new number is, and whether the versions of the map agreed
 * on which way it went. On a claim that did not move there is no number for
 * either of them to describe — so *no engine yet* would be wrong twice over,
 * once by promising a number that is coming and once by suggesting something is
 * missing when nothing is.
 *
 * It is an em dash for the same reason an unsaid belief is: the row is there,
 * and there is nothing in it. It is a named function rather than a sixth
 * vocabulary row because it is a fact about a **rail cell** rather than about
 * the map, and it is named rather than hand-written so that there is still
 * exactly one place the words live.
 *
 * @param reason Which reading this is, and why it has nothing to say here.
 */
export function noReadingAtAll(reason: string): Absence {
  return { kind: "no_engine", words: "—", reason } as Absence;
}

/**
 * A slot whose words are **the engine's own verdict** rather than the
 * vocabulary's.
 *
 * The rail beside a diff has rows that say *no change* — which is not an
 * absence at all in the vocabulary's sense. Nothing is missing: the engine was
 * asked, it answered, and its answer was that this claim held still. The row
 * carries that answer in the words the engine's own wording module wrote, and
 * the reason says why a row that held still is in a list of rows that moved.
 *
 * It is a third named way in rather than a hand-written literal for the same
 * reason as the other two: a shape that can be written anywhere is a shape with
 * no one place. What it does **not** do is let a caller invent one of the five
 * vocabulary words — those come from `absence()` and nowhere else.
 *
 * @param words The engine's own words for this cell.
 * @param reason Why they are standing where a number would.
 */
export function inTheEnginesWords(words: string, reason: string): Absence {
  return { kind: "no_engine", words, reason } as Absence;
}
