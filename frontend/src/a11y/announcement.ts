/**
 * What the screen says out loud when a branch is made, and why it cannot yet say
 * the obvious thing.
 *
 * Once the engine is connected the line is *"Branch created. Six claims changed,
 * one retracted."* **In this build nothing has changed, because nothing computed
 * a change** — and saying "six claims changed" would be inventing exactly the
 * state that the rule *every number can say why* exists to stop.
 *
 * What is real is structure: which claim arrived, which claims the edit can
 * reach, which supposition a later edit took back. Every count below comes from
 * somewhere nameable — the diff reducer for the first two, the derived badge for
 * the third — and **no numbers yet** is said out loud rather than left as a
 * silence, because a reader who is not looking at the screen has no other way to
 * know that the likelihoods are absent on purpose.
 *
 * On the stored example's strike branch that line is, word for word:
 *
 * > Branch created. One claim added, six claims your edit can reach, one
 * > supposition retracted. No numbers yet.
 *
 * When the engine lands, "your edit can reach" becomes "changed" and the count
 * becomes a computed one. Nothing is deleted then, because nothing false was
 * said.
 */

import type { WorldView } from "../world";
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
 */
export function branchAnnouncement(world: WorldView): string {
  if (world.branch === undefined) {
    return "";
  }
  const added = world.claims.filter((claim) => claim.diff === "added").length;
  const reachable = world.claims.filter((claim) => claim.diff === "downstream").length;
  const supposedFalse = world.claims.filter((claim) => claim.diff === "killed").length;
  const retracted = world.claims.filter((claim) =>
    (claim.badges ?? []).some((badge) => badge.overrides === true),
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
  parts.push(`${inWords(reachable)} ${reachable === 1 ? "claim" : "claims"} your edit can reach`);
  if (retracted > 0) {
    parts.push(
      `${inWords(retracted)} ${retracted === 1 ? "supposition" : "suppositions"} retracted`,
    );
  }

  return `Branch created. ${asSentence(parts.join(", "))}. No numbers yet.`;
}
