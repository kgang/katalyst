/**
 * The endings your edit can reach, in the order the map stores them.
 *
 * An **ending** is a claim the chain stops at: one that names an instrument you
 * could trade, or one that names why there is nothing to trade. They are what
 * the rail beside the map lists, because they are where an argument turns into a
 * position.
 *
 * **This build does not rank them and does not compute anything.** With the
 * engine, the rail is the endings whose numbers moved, in the order the engine
 * put them in — biggest move along the best-backed route first. Before the
 * engine there is no such order, and inventing one would be inventing the single
 * thing the rail exists to tell you. So the order is **map order**, which is
 * visibly arbitrary and says so on screen, and where the change will go there is
 * an absence with its reason.
 *
 * **A row used to carry two more columns and no longer does** *(Kent,
 * 2026-09-22, R48)*. *How firm* was the width of the range around the new
 * number; *same direction* was the share of the two thousand versions of the map
 * that moved the same way. Both read a range or the versions that made one, and
 * both are cut. A row is the ending, its number before and after, and the
 * direction.
 */

import { absence } from "../../world/absence";
import type { Absence, DeltaRow, Known, WorldView } from "../../world/types";

/** Where the change itself will go. */
const NO_CHANGE_YET: Absence = absence(
  "no_engine",
  "Nothing has worked this ending's number through the map, so there is no before and no " +
    "after to show.",
);

/** Where the one-line summary of the whole edit will go. */
export const NO_SUMMARY_YET: Known<string> = {
  absence: absence(
    "no_engine",
    "The one line saying what this edit did to the trades is written from the numbers it " +
      "moved, and nothing has moved one. What the map can say without them is underneath: which " +
      "claim arrived, which claims your edit can reach, and which it provably cannot.",
  ),
};

/**
 * The endings this branch can reach, in map order.
 *
 * @param world A world with a branch folded onto it. On the base world nothing
 *   has been edited, so nothing is reachable and the list is empty.
 * @returns One row per reachable ending, each with its absences.
 */
export function endings(world: WorldView): DeltaRow[] {
  return world.claims
    .filter(
      (claim) =>
        (claim.kind === "market" || claim.kind === "not_tradeable") &&
        claim.diff !== undefined &&
        claim.diff !== "untouched",
    )
    .map(
      (claim): DeltaRow => ({
        claimId: claim.id,
        label: claim.claim,
        kind: claim.kind,
        move: { absence: NO_CHANGE_YET },
      }),
    );
}
