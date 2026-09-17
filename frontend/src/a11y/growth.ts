/**
 * What a map being built says out loud.
 *
 * A reader who never sees the canvas should hear the map being built rather than
 * a silence followed by a finished list. So one polite line is said at each thing
 * that happened: the run starting, each claim arriving, each proposal the rules
 * turned down, the likelihoods landing, and why the run stopped.
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

import { WHY_IT_STOPPED } from "../components/DoneLine";
import type { Growth } from "../stream/growth";
import { inWords } from "./sentences";

/**
 * The one line a reader hears about where the generation has got to.
 *
 * It is said again whenever any of it changes, which is what a polite live region
 * wants: one settled sentence rather than a running commentary that cuts across
 * itself.
 *
 * @param growth Everything the screen knows about the run.
 */
export function growthAnnouncement(growth: Growth): string {
  const parts: string[] = [];

  switch (growth.phase) {
    case "waiting":
      parts.push(
        `Asked for a map of "${growth.hypothesis}". A rectangle is held open where the first ` +
          `claim will go.`,
      );
      break;
    case "growing":
      parts.push(
        `Building the map. ${asClaims(growth.world.claims.length)} so far, ` +
          `${asRectangles(growth.skeletons.length)} still to come.`,
      );
      break;
    case "settled":
    case "stopped":
      parts.push(
        `The map is finished: ${asClaims(growth.done?.claims ?? growth.world.claims.length)}, ` +
          `${asArrows(growth.done?.links ?? growth.world.links.length)}. ` +
          `${growth.done === null ? "" : WHY_IT_STOPPED[growth.done.reason]}`.trim(),
      );
      break;
    case "failed":
      parts.push(`The run stopped. ${growth.failure ?? ""}`.trim());
      break;
  }

  if (growth.refusals.length > 0) {
    parts.push(
      growth.refusals.length === 1
        ? "One proposal was refused by the map's own rules, and the reason is beside the map."
        : `${asCount(growth.refusals.length)} proposals were refused by the map's own rules, ` +
            `and every reason is beside the map.`,
    );
  }

  const last = growth.refusals[growth.refusals.length - 1];
  if (last !== undefined) {
    parts.push(`The last of them: ${last.reasons.join(" ")}`);
  }

  if (growth.verdict !== null) {
    parts.push(growth.verdict.why);
  }

  return parts.join(" ");
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
