/**
 * What a map being built says out loud.
 *
 * A reader who never sees the canvas should hear the map being built rather than
 * a silence followed by a finished list. So one polite line is said at each thing
 * that happened: the run starting, each claim arriving, each proposal the rules
 * turned down, the likelihoods landing, and why the run stopped.
 *
 * **Each line says what changed, and only what changed.** A live region that
 * re-reads the whole run on every arrival reads out every refusal again for the
 * tenth time on the tenth claim — so a reader listening to a ten-claim run with
 * two refusals hears those two sentences twenty times, and hears the thing that
 * just happened last, after a minute of things they already knew. The line a
 * screen reader speaks is therefore about the event: *a claim arrived*, *a
 * proposal was refused, with the rule's sentence*, *the likelihoods landed*,
 * *this is why it stopped* — each said once, at the moment it became true.
 *
 * **The ordering is the causality**, here as much as on the canvas. The lines are
 * said in the order the events arrived, which is the order the argument was
 * built, and the outline beside them grows in the same order.
 *
 * Nothing here composes a sentence about a refusal: a refused proposal is read
 * out in the words the rule itself wrote. And nothing here counts anything the
 * stream did not count — the claim and arrow counts at the end are the fields the
 * closing event carried.
 *
 * **And each line about a growing map ends by naming what is still open**, from
 * the frontier both growth events carry (added 2026-09-21). These lines are now
 * printed as well as spoken, in the strip at the foot of the map, and they are
 * what a reader looks at during the fifty to a hundred and ten seconds between
 * two events of a live run: *what has arrived* is half the answer, and *what is
 * being worked on* is the other half.
 */

import { THE_STREAM_ENDED_EARLY, WHY_IT_STOPPED } from "../components/DoneLine";
import type { Growth } from "../stream/growth";
import { inFewWords } from "../world/naming";
import { inWords } from "./sentences";

/**
 * The first thing a reader hears: the request has gone, and a rectangle is held
 * open where the first claim will go.
 *
 * It is said once, when the screen appears, because it is the one statement that
 * is not about anything having changed.
 *
 * @param growth The run, as it stands before anything has come back.
 */
export function theOpeningLine(growth: Growth): string {
  return (
    `Asked for a map of "${growth.hypothesis}". A rectangle is held open where the first ` +
    `claim will go.`
  );
}

/**
 * The one line to say now, given what just changed.
 *
 * @param was Everything known before the event.
 * @param now Everything known after it.
 * @returns The sentence, or the empty string when nothing a listener needs to
 *   hear changed — in which case the region keeps saying whatever it last said,
 *   rather than falling silent.
 */
export function whatChanged(was: Growth, now: Growth): string {
  // A refusal, in the rule's own sentences, said once and never said again.
  // Accepted and refused are two different events, so only one of the two
  // branches below can be the reason for any one change.
  if (now.refusals.length > was.refusals.length) {
    const last = now.refusals[now.refusals.length - 1];
    return last === undefined
      ? ""
      : `A proposal was refused. ${last.reasons.join(" ")} ${whatIsOpen(now, null)}`.trim();
  }

  // The likelihoods landing: one event, one world, every number. It is the
  // engine's own world arriving that says so — a growing map has no count of
  // versions on it, because nothing has been run through it yet.
  if (was.world.versions === undefined && now.world.versions !== undefined) {
    return (
      "Every likelihood has been worked out, through the whole finished map, at once. Every " +
      "claim on the map now carries a number."
    );
  }

  if (now.world.claims.length > was.world.claims.length) {
    const arrived = now.world.claims[now.world.claims.length - 1];
    const many = now.world.claims.length;
    return (
      `A claim arrived: "${inFewWords(arrived?.claim ?? "")}". ` +
      `${asCount(many)} ${many === 1 ? "claim" : "claims"} so far. ` +
      `${whatIsOpen(now, arrived?.id ?? null)}`
    ).trim();
  }

  if (now.verdict !== null && was.verdict === null) {
    // The engine's own sentence about where the reader said it ends, printed as
    // it came. Nothing here composes one.
    return now.verdict.why;
  }

  if (now.phase !== was.phase) {
    return theEnd(now);
  }

  return "";
}

/**
 * What the run is working on now, named rather than counted.
 *
 * **It is read off the frontier, which the stream states on both growth
 * events** — the claims still open to expand, in the engine's own order. The
 * reserved rectangles on the canvas are that same frontier drawn, so the
 * sentence and the picture cannot disagree.
 *
 * **It names one and counts the rest.** A sentence listing five claims in full
 * is a sentence nobody finishes, and a sentence that only counts them — *three
 * places held open* — says how many without saying what, which is the thing a
 * reader waiting a minute actually wants to know.
 *
 * **It counts places, never calls.** How many calls are in flight is the
 * server's business and is not on the wire; the browser can count what it was
 * sent and nothing else.
 *
 * **And it says *it* rather than repeating a claim just quoted.** The claim that
 * has this moment arrived is usually the first thing still open, and a sentence
 * that names it twice in twelve words reads as a stutter.
 *
 * @param now Everything known after the event.
 * @param justArrived The claim this event brought, when it brought one, so the
 *   sentence can point back at it instead of quoting it again.
 * @returns The sentence, or the one that says nothing is open — which is what a
 *   map has just before the likelihoods land.
 */
function whatIsOpen(now: Growth, justArrived: string | null): string {
  const open = now.skeletons;
  const first = open[0];
  if (first === undefined) {
    return "No place is left open.";
  }
  const others = open.length - 1;
  const rest = others === 0 ? "" : ` and ${inWords(others)} ${others === 1 ? "other" : "others"}`;
  if (first.after !== null && first.after === justArrived) {
    return `Working on what follows from it${rest}.`;
  }
  // The rectangle carries the claim it hangs off; the claim's own words are on
  // the map. The first rectangle of all hangs off nothing and carries the
  // reader's own sentence, which is the right thing to name then.
  const words =
    first.after === null
      ? first.words
      : (now.world.claims.find((claim) => claim.id === first.after)?.claim ?? first.words);
  return `Working on what follows from "${inFewWords(words)}"${rest}.`;
}

/** What a run that has stopped says, in one line, whichever way it stopped. */
function theEnd(now: Growth): string {
  switch (now.phase) {
    case "settled":
    case "stopped":
      return (
        `The map is finished: ${asClaims(now.done?.claims ?? now.world.claims.length)}, ` +
        `${asArrows(now.done?.links ?? now.world.links.length)}. ` +
        `${now.done === null ? "" : WHY_IT_STOPPED[now.done.reason]}`
      ).trim();
    case "failed":
      return `The run stopped. ${now.failure ?? ""}`.trim();
    case "ended_early": {
      const many = now.world.claims.length;
      return `${THE_STREAM_ENDED_EARLY} ${asCount(many)} ${many === 1 ? "claim" : "claims"} arrived before it did, and they are on the map.`;
    }
    default:
      // `waiting` and `growing` are not ends. Reaching `growing` is the first
      // event arriving, and what a listener wants to hear then is the claim that
      // came with it — which the branch above has already said.
      return "";
  }
}

/** A count with its first letter a capital, for the start of a sentence. */
function asCount(count: number): string {
  const word = inWords(count);
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** How many claims, in words. */
function asClaims(count: number): string {
  return `${inWords(count)} ${count === 1 ? "claim" : "claims"}`;
}

/** How many arrows, in words. */
function asArrows(count: number): string {
  return `${inWords(count)} ${count === 1 ? "arrow" : "arrows"}`;
}
