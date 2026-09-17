/**
 * The one rule a branch has to keep: **edits are appended, never rewritten.**
 *
 * The branch is the audit trail. Read it as a list and the surprising rule —
 * that a later addition outranks an earlier supposition — is obvious; met as a
 * number that moved on its own it reads as a bug. An audit trail you can edit
 * explains nothing, so the test below checks not only that the edits are in the
 * right order but that the earlier ones are the **same objects** they were.
 * Identity is a stronger claim than equality, and it is the claim that matters.
 */

import { describe, expect, it } from "vitest";
import * as branches from "../branchReducer";
import { appendEdit, forkBranch, openBranch, workshopOf } from "../branchReducer";
import type { BranchView, Edit } from "../types";

const SUPPOSE: Edit = { op: "do", target: "H", value: true, at: "2026-10-01" };
const ADD: Edit = {
  op: "insert",
  claimId: "S",
  words: "A confirmed military strike on Iranian territory.",
  arrows: [{ id: "S->H", source: "S", target: "H" }],
};
const SUPPOSE_AGAIN: Edit = { op: "do", target: "S", value: true, at: "2026-10-02" };

describe("your branches", () => {
  // test_appends_edits_in_order_and_never_rewrites_one
  it("test_appends_edits_in_order_and_never_rewrites_one", () => {
    let shop = forkBranch(workshopOf([]), "Hormuz opens, then Iran is struck");
    for (const edit of [SUPPOSE, ADD, SUPPOSE_AGAIN]) {
      shop = appendEdit(shop, edit);
    }
    const edits = shop.branches[0]?.edits ?? [];
    expect(edits).toHaveLength(3);
    // The order they were made in, and the very same objects.
    expect(edits[0]).toBe(SUPPOSE);
    expect(edits[1]).toBe(ADD);
    expect(edits[2]).toBe(SUPPOSE_AGAIN);
  });

  // test_there_is_no_way_to_change_an_edit
  it("test_there_is_no_way_to_change_or_remove_an_edit", () => {
    // The branch is the audit trail, so the only thing you can do to one is add
    // to it. This reads the module's own exports rather than trusting a comment:
    // the day somebody writes a `replaceEdit`, this fails and asks why.
    expect(Object.keys(branches).sort()).toEqual([
      "appendEdit",
      "forkBranch",
      "openBranch",
      "workshopOf",
    ]);
  });

  // test_the_base_map_is_never_edited
  it("test_the_map_as_it_was_written_is_never_edited", () => {
    // With no branch open there is nothing to append to, and the answer is the
    // branches unchanged rather than a quiet edit of the original.
    const shop = workshopOf([]);
    expect(appendEdit(shop, SUPPOSE)).toBe(shop);
  });

  // test_a_second_branch_takes_its_own_hue_and_its_own_edits
  it("test_each_branch_keeps_its_own_edits_and_its_own_hue", () => {
    let shop = forkBranch(workshopOf([]), "the first");
    shop = appendEdit(shop, SUPPOSE);
    shop = forkBranch(shop, "the second");
    shop = appendEdit(shop, ADD);
    expect(shop.branches.map((branch) => branch.edits.length)).toEqual([1, 1]);
    expect(shop.branches.map((branch) => branch.hue)).toEqual(["violet", "teal"]);
    expect(shop.branches.map((branch) => branch.label)).toEqual(["the first", "the second"]);
  });

  // test_opening_a_branch_that_is_not_there_changes_nothing
  it("test_the_branch_the_engine_is_sent_is_the_branch_on_screen", () => {
    // A branch is held in two shapes at once: the one the panel reads and the
    // one the engine is asked with. One function changes either, so the two
    // cannot come to hold different edits — and if they ever did, the map the
    // engine folded would not be the map on screen.
    let shop = forkBranch(workshopOf([]), "Your own branch");
    shop = appendEdit(shop, { op: "do", target: "B", value: true, at: "2026-10-01" });
    shop = appendEdit(shop, { op: "observe", target: "C", value: true, at: "2026-10-01" });
    shop = appendEdit(shop, { op: "retune", link: "H->B", strength: 0.3, wasStrength: 1.6 });

    const branch = shop.branches[0] as BranchView;
    expect(branch.edits).toHaveLength(3);
    expect(branch.wire?.interventions.map((one) => one.kind)).toEqual(["do", "observe", "retune"]);
    // Observing carries no day of its own: you can only report what has already
    // happened, and the map's window starts on its own first day.
    expect(branch.wire?.interventions[1]).toEqual({ kind: "observe", target: "C", value: true });
  });

  it("test_a_branch_that_is_not_there_is_ignored", () => {
    const shop = forkBranch(workshopOf([]), "the only one");
    expect(openBranch(shop, "nothing-by-that-name")).toBe(shop);
    expect(openBranch(shop, null).openId).toBeNull();
  });
});
