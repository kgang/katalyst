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

import type { BranchHue, BranchView, Edit, WireBranch, WireEdit } from "./types";

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
  const id = `branch-${shop.branches.length + 1}`;
  const made: BranchView = {
    id,
    label,
    hue,
    edits: [],
    claims: [],
    links: [],
    // The same branch in the shape the engine is asked with. It is built here,
    // beside the drawable one, so that the two can never hold different edits:
    // there is one function below that appends to both at once and no other way
    // to change either.
    wire: { id, label, parent: null, interventions: [] },
  };
  return { branches: [...shop.branches, made], openId: made.id };
}

/**
 * One edit in the shape the server writes one, or nothing when this build
 * cannot write it down in full.
 *
 * Four of the six operations are the same few fields on both sides and cross
 * over untouched. Two do not, and both say so on screen rather than being
 * quietly dropped here:
 *
 * - **Add a claim** brings a whole claim — its wording, how it is judged, by
 *   whom, by when, what it started from — and the part of this product that
 *   drafts one is not connected. The button says so and appends nothing.
 * - **Split this claim** is not built at all. The button says so and appends
 *   nothing.
 *
 * So neither ever reaches this function from the screen. It answers for them
 * anyway, with nothing rather than with a guess, because an edit written down
 * half-way would be folded onto the map as if it were whole.
 *
 * @param edit The edit the reader just made.
 */
function asWireEdit(edit: Edit): WireEdit | null {
  switch (edit.op) {
    case "do":
      return { kind: "do", target: edit.target, value: edit.value, at: edit.at };
    case "observe":
      // Observing carries no day of its own: you can only report what has
      // already happened, and the map's window starts on its own first day.
      return { kind: "observe", target: edit.target, value: edit.value };
    case "retune":
      return { kind: "retune", link: edit.link, strength: edit.strength };
    case "believe":
      return {
        kind: "believe",
        target: edit.target,
        belief: { p: edit.belief.p, lo: edit.belief.lo, hi: edit.belief.hi, owner: "user" },
      };
    case "insert":
    case "refine":
      return null;
  }
}

/**
 * The branch with one more edit written the server's way, or nothing at all when
 * the edit cannot be written that way.
 *
 * A branch that loses its wire form keeps it lost: half a branch folded onto a
 * map is a map nobody can account for.
 */
function wireWith(branch: BranchView, edit: Edit): WireBranch | undefined {
  const written = asWireEdit(edit);
  if (branch.wire === undefined || written === null) {
    return undefined;
  }
  return { ...branch.wire, interventions: [...branch.wire.interventions, written] };
}

/**
 * Add one edit to the open branch, at the end.
 *
 * Every edit already in the branch comes through as the same object it was, so
 * that "nothing earlier was rewritten" is a property you can check by identity
 * rather than by reading fields back.
 *
 * The branch is held in two shapes at once — the one the panel reads and the
 * one the engine is asked with — and this is the only function that changes
 * either, so the two cannot come to hold different edits.
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
      branch.id === shop.openId
        ? { ...branch, edits: [...branch.edits, edit], wire: wireWith(branch, edit) }
        : branch,
    ),
  };
}
