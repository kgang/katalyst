/**
 * The branches you have made, and the one rule that governs them: **edits are
 * appended, never rewritten.**
 *
 * A branch is a named, ordered list of edits over a base map. It holds no
 * likelihoods and no results — everything a branch shows on screen is worked out
 * from the base map plus this list, which is what makes the original safe to
 * leave untouched and what makes the whole thing replayable.
 *
 * **Why nothing here ever edits an edit in place.** The branch is the audit
 * trail. Press *Suppose this is true* on a claim, then press *Change this push*
 * on an arrow, and the two edits sit in the panel in that order — and the
 * surprising rule that a later addition outranks an earlier supposition reads as
 * a sequence rather than as a number that moved on its own. An audit trail you
 * can edit is not one. So every function below hands back a new branch whose
 * earlier edits are the very same objects, and there is no function that
 * replaces one.
 *
 * **Nothing here moves a number.** These functions build a list. Working out
 * what the list does to the map's likelihoods is the engine's job, and this half
 * of the product does none of it.
 */

import type { BranchHue, BranchView, Edit } from "./types";

/**
 * The branches on one map, and which of them is open.
 *
 * `openId` of `null` is the base world — the empty branch, the map as it was
 * written.
 */
export interface Workshop {
  /** Every branch on this map, in the order they arrived. */
  readonly branches: readonly BranchView[];
  /** Which branch is open, or `null` for the base world. */
  readonly openId: string | null;
}

/**
 * The four hues a branch may take, in the order they are handed out.
 *
 * Never amber: amber already means "the money moves down", and one hue cannot
 * mean two things. A fifth branch reuses the first hue rather than inventing a
 * fifth — every branch also carries a name chip with its label, so which branch
 * you are in is readable with no colour at all.
 */
const HUES: readonly BranchHue[] = ["violet", "teal", "rose", "slate"];

/**
 * Start from the branches a map arrived with, none of them open.
 *
 * @param branches The branches the map itself carries.
 */
export function workshopOf(branches: readonly BranchView[]): Workshop {
  return { branches, openId: null };
}

/**
 * Open a branch, or go back to the base world.
 *
 * @param shop The branches as they stand.
 * @param id The branch to open, or `null` for the base world.
 */
export function openBranch(shop: Workshop, id: string | null): Workshop {
  if (id !== null && !shop.branches.some((branch) => branch.id === id)) {
    return shop;
  }
  return { ...shop, openId: id };
}

/**
 * Make a new branch and open it.
 *
 * The new branch forks off the base map with no edits in it. It takes the next
 * hue in the list above, and its label is what the reader typed.
 *
 * @param shop The branches as they stand.
 * @param label What the reader is calling this branch. An unnamed branch is
 *   unusable once there are three of them.
 */
export function forkBranch(shop: Workshop, label: string): Workshop {
  const hue = HUES[shop.branches.length % HUES.length] ?? "violet";
  const made: BranchView = {
    id: `branch-${shop.branches.length + 1}`,
    label,
    hue,
    edits: [],
    claims: [],
    links: [],
  };
  return { branches: [...shop.branches, made], openId: made.id };
}

/**
 * Add one edit to the open branch, at the end.
 *
 * Every edit already in the branch comes through as the same object it was, so
 * that "nothing earlier was rewritten" is a property you can check by identity
 * rather than by reading fields back.
 *
 * @param shop The branches as they stand.
 * @param edit The edit the reader just made.
 * @returns The branches with the edit appended. Unchanged when no branch is
 *   open: the base map is never edited, and a branch is what an edit goes into.
 */
export function appendEdit(shop: Workshop, edit: Edit): Workshop {
  if (shop.openId === null) {
    return shop;
  }
  return {
    ...shop,
    branches: shop.branches.map((branch) =>
      branch.id === shop.openId ? { ...branch, edits: [...branch.edits, edit] } : branch,
    ),
  };
}
