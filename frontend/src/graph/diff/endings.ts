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
 * visibly arbitrary and says so on screen, and where each number will go there is
 * an absence with its reason.
 *
 * The two columns beside the change are never folded into any ordering, before
 * the engine or after it:
 *
 * | On screen | The question it answers |
 * |---|---|
 * | **how firm** | How firm is this number? The width of this world's own range on the claim — the same quantity the tile shows, so the rail and the tile cannot disagree |
 * | **same direction** | Did it point the same way whatever numbers we started from? The share of the two thousand versions of the map that moved the same way |
 *
 * They answer different questions and a trader weighs them separately, which is
 * why they are columns and not one score. Folding the width into a rank would
 * sink exactly the claims that most deserve a second look.
 */

import type { Absence, DeltaRow, Known, WorldView } from "../../world/types";

/** Where the change itself will go. */
const NO_CHANGE_YET: Absence = {
  kind: "no_engine",
  words: "no engine yet",
  reason:
    "Nothing has worked this ending's number through the map, so there is no before and no " +
    "after to show.",
};

/** Where **how firm** will go. */
const NO_WIDTH_YET: Absence = {
  kind: "no_engine",
  words: "—",
  reason:
    "How firm a number is, is the width of this world's own range on the claim — the same " +
    "range the tile shows. There is no number yet, so there is no range around it.",
};

/** Where **same direction** will go. */
const NO_AGREEMENT_YET: Absence = {
  kind: "no_engine",
  words: "—",
  reason:
    "Whether an ending points the same way whatever numbers we started from is read across two " +
    "thousand versions of the map — each one a coherent set of numbers this model would have " +
    "stood behind. Nothing has run one yet.",
};

/** Where the one-line summary of the whole edit will go. */
export const NO_SUMMARY_YET: Known<string> = {
  absence: {
    kind: "no_engine",
    words: "no engine yet",
    reason:
      "The one line saying what this edit did to the trades is written from the numbers it " +
      "moved, and nothing has moved one. What the map can say without them is underneath: which " +
      "claim arrived, which claims your edit can reach, and which it provably cannot.",
  },
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
        rangeWidth: { absence: NO_WIDTH_YET },
        agreement: { absence: NO_AGREEMENT_YET },
      }),
    );
}
