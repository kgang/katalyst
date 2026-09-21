/**
 * The shapes this half types by hand are the shapes the server describes.
 *
 * `events.ts`, `insert.ts` and `transcript.ts` were written by hand while the
 * route that produces them was being built beside this half: there was nothing
 * generated to read, so the only way to draw a map was to write down what the
 * chapter said would arrive. That is a debt, and this file is where it is paid.
 * The server's description of itself is generated into `api/schema.ts`, and
 * everything below fails to compile the day the two disagree.
 *
 * **`tsc` is the whole test.** There is nothing to run: the file exports
 * nothing, asserts nothing at run time, and costs one type-check. `npm run
 * typecheck` — and therefore `npm run check` and the build — goes red on drift.
 *
 * **Where the server's shape wins.** Everywhere. These are the server's facts
 * arriving over its own wire, and a browser that quietly disagreed about one
 * would draw a map nobody could account for. The only thing this half is
 * allowed to add is a field the wire genuinely does not carry, and there is
 * exactly one: `seed_as_written`, the seed's digits read off the raw text
 * because `JSON.parse` has already rounded a nineteen-digit number by the time
 * anything here sees it. It is marked below, once, with the reason.
 *
 * **There is one dated allowance at the foot of this file**, for one event,
 * `activity`, whose server half has not landed yet. It is written as a check
 * that fails the day the server's description gains the shape, so it cannot be
 * forgotten. Read it before adding a second one.
 *
 * **What is not pinned, and why it cannot be.** The eight stream events are not
 * in `schema.ts` at all: they travel as server-sent events, and OpenAPI has no
 * way to describe the body of a stream — it describes `text/event-stream` and
 * stops. So the eight are pinned at the joints instead, which is where drift
 * would actually hurt: every piece an event is built from — `Proposition`,
 * `Link`, `World`, `Violation`, `Belief` — is *aliased* to the generated type in
 * `events.ts` rather than retyped, so a change to any of them is a compile
 * error in this half without anybody writing a test. What is left unpinned is
 * the eight envelopes: their names, and which of those pieces each carries.
 * The guard for those is the running app — an event name this build does not
 * know is counted and shown (`growth.ts`) — and a server test that the stream
 * emits exactly those eight names.
 */

import type { components } from "../../api/schema";
import type { Activity, GenerateRequest, Receipt } from "../events";
import type { Drafted } from "../insert";
import type { Transcript, TranscriptLine } from "../transcript";

/** Every key of `Theirs` is a key of `Ours`, and no key of `Ours` is invented. */
type SameKeys<Ours, Theirs> = [keyof Ours] extends [keyof Theirs]
  ? [keyof Theirs] extends [keyof Ours]
    ? true
    : { theirsWeDoNotHave: Exclude<keyof Theirs, keyof Ours> }
  : { oursTheyDoNotHave: Exclude<keyof Ours, keyof Theirs> };

/** Fails to compile unless the two shapes hold the same field names. */
type Agree<Ours, Theirs> = SameKeys<Ours, Theirs> extends true ? true : SameKeys<Ours, Theirs>;

/** Assert one agreement. The value is never read; the type is the test. */
function pinned<T extends true>(_: T): void {
  // Nothing at run time. `tsc` has already done the only work there is.
}

/* ---- The receipt ---------------------------------------------------------
 *
 * Ten readings and a fingerprint. `effort` and `searches` are the two the
 * chapter has changed its mind about most, so they are the two most worth a
 * compiler watching. The stream's receipt, not the running total the engine
 * keeps while it spends — those are two shapes with one name in the server's
 * own description, and this is the one that reaches a screen.
 */
pinned<Agree<Omit<Receipt, "event">, components["schemas"]["katalyst__engine__events__Receipt"]>>(
  true,
);

/* ---- What the browser asks for -------------------------------------------
 *
 * The browser sends five of the seven the route takes. `versions` and `worlds`
 * are deliberately never sent — the engine's own are what every map in this
 * product is worked out with — so this one is a *subset* check rather than an
 * agreement: every field the browser sends must be a field the route takes.
 */
type Asks = keyof GenerateRequest extends keyof components["schemas"]["GenerateRequest"]
  ? true
  : {
      weSendWhatItDoesNotTake: Exclude<
        keyof GenerateRequest,
        keyof components["schemas"]["GenerateRequest"]
      >;
    };
pinned<Asks>(true);

/* ---- One drafted claim, and what it cost ---------------------------------- */
type TheDraftedArm = Extract<Drafted, { state: "drafted" }>;
pinned<Agree<Omit<TheDraftedArm, "state">, components["schemas"]["DraftedInsert"]>>(true);

/* ---- The working ---------------------------------------------------------
 *
 * One line per call, whether it arrives in an insert's answer or is read back
 * from the transcript route: one shape, so a reader who has learned to read one
 * working has learned to read the other.
 */
pinned<Agree<TranscriptLine, components["schemas"]["TranscriptLine"]>>(true);
pinned<Agree<Transcript, components["schemas"]["Transcript"]>>(true);

/* ---- One allowance, for one event, dated -----------------------------------
 *
 * **`activity` is hand-typed against the shapes sheet and pinned to nothing.**
 * *(2026-09-22, branch `feat/04d-the-strip-says-it`.)*
 *
 * The ninth event is being built in two halves at once — the server's in
 * `feat/04d-the-model-says-what-it-is-doing`, this one in the browser — against
 * one written sheet the two halves share. Until the server half lands there is
 * nothing generated to check this half against: `api/schema.ts` is generated
 * from the server's own description of itself, it is never edited by hand, and
 * it has no `Activity` in it at all.
 *
 * That is the honest position, and this block is it written down rather than
 * left unsaid. It is **not** a skipped check: the line below is a check, and
 * what it holds is the very fact that makes the allowance necessary. The day
 * the server's description gains the shape, this stops compiling — `npm run
 * typecheck`, `npm run check` and the build all go red — and whoever is at the
 * join deletes this whole block and pins `Activity` to the generated shape
 * exactly as the receipt above is pinned.
 *
 * Until then, `Activity` is named here for one reason: so that this file
 * mentions the event it is making an exception for, and `tsc` fails if the
 * event is ever deleted or renamed without this being revisited.
 */
type TheSchemasNamedActivity = Extract<keyof components["schemas"], `${string}Activity`>;
type NoGeneratedActivityYet = [TheSchemasNamedActivity] extends [never]
  ? true
  : {
      theServerNowDescribesActivity: TheSchemasNamedActivity;
      soDeleteThisBlockAndPinItLikeTheReceipt: true;
    };
pinned<NoGeneratedActivityYet>(true);

/** The one event with nothing generated to pin it to. Named so it cannot vanish quietly. */
type TheHandTypedNinth = Omit<Activity, "event">;
pinned<[keyof TheHandTypedNinth] extends [never] ? false : true>(true);
