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
    return last === undefined ? "" : `A proposal was refused. ${last.reasons.join(" ")}`;
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
    return (
      `A claim arrived: "${inFewWords(arrived?.claim ?? "")}". ` +
      `${asClaims(now.world.claims.length)} so far, ` +
      `${asRectangles(now.skeletons.length)} still to come.`
    );
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

/** How many rectangles are being held open, in words. */
function asRectangles(count: number): string {
  return count === 1 ? "one place held open" : `${inWords(count)} places held open`;
}
