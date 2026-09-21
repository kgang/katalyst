/**
 * What the screen says out loud when a branch is made, and how it changes when
 * the engine answers.
 *
 * A reader who is not looking at the picture needs the same two facts a reader
 * who is gets from it: what the edit did to the shape of the map, and what it
 * did to the numbers. Those arrive at different moments, so the line is said
 * twice — once the instant the branch opens, from the branch alone, and again
 * when the engine's answer lands, with the counts it worked out.
 *
 * **Every count comes from somewhere nameable.** What arrived and what was taken
 * back are read off the world; how many claims moved is read off the engine's
 * own difference, one word per claim, and never by the browser comparing two
 * numbers. While the engine is still being asked the line says so, because a
 * reader who cannot see the screen has no other way to know that the
 * likelihoods are on their way rather than missing.
 *
 * On the stored example's strike branch the two lines are, word for word:
 *
 * > Branch created. One claim added, six claims your edit can reach, one
 * > supposition retracted. The numbers are on their way from the engine.
 *
 * > Branch created. One claim added, six claims moved, one supposition
 * > retracted.
 */

import type { DiffView, WorldView } from "../world";
import { inWords } from "./sentences";

/** Make the first letter of a sentence a capital, and leave every other letter alone. */
function asSentence(line: string): string {
  return line.charAt(0).toUpperCase() + line.slice(1);
}

/**
 * The one line a branch announces itself with.
 *
 * @param world The world the branch made. On a world with no branch there is
 *   nothing to announce and the answer is an empty line.
 * @param change What the engine says moved, once it has said it. Left out, the
 *   line reports what the edit can reach and says the numbers are still coming.
 */
export function branchAnnouncement(world: WorldView, change?: DiffView): string {
  if (world.branch === undefined) {
    return "";
  }
  const added = world.claims.filter((claim) => claim.diff === "added").length;
  const supposedFalse = world.claims.filter((claim) => claim.diff === "killed").length;
  const retracted = world.claims.filter((claim) =>
    (claim.badges ?? []).some((badge) => badge.overrides === true),
  ).length;
  // How many claims moved is the engine's own word, one per claim, read off its
  // difference. The browser never counts it by comparing two numbers: that would
  // be a second answer to a question the engine has already answered.
  const moved =
    change === undefined
      ? null
      : [...change.claims.values()].filter((claim) => claim.state === "shifted").length;
  const reachable = world.claims.filter(
    (claim) => claim.diff === "downstream" || claim.diff === "shifted",
  ).length;

  const parts: string[] = [];
  if (added > 0) {
    parts.push(`${inWords(added)} ${added === 1 ? "claim" : "claims"} added`);
  }
  if (supposedFalse > 0) {
    parts.push(
      `${inWords(supposedFalse)} ${supposedFalse === 1 ? "claim" : "claims"} supposed false`,
    );
  }
  parts.push(
    moved === null
      ? `${inWords(reachable)} ${reachable === 1 ? "claim" : "claims"} your edit can reach`
      : `${inWords(moved)} ${moved === 1 ? "claim" : "claims"} moved`,
  );
  if (retracted > 0) {
    parts.push(
      `${inWords(retracted)} ${retracted === 1 ? "supposition" : "suppositions"} retracted`,
    );
  }

  const line = `Branch created. ${asSentence(parts.join(", "))}.`;
  return moved === null ? `${line} The numbers are on their way from the engine.` : line;
}
