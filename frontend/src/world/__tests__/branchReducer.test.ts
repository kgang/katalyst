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
import type { Edit } from "../types";

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
  it("appends every edit at the end and leaves the earlier ones untouched", () => {
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
  it("offers no way at all to change or remove an edit", () => {
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
  it("never edits the map as it was written", () => {
    // With no branch open there is nothing to append to, and the answer is the
    // branches unchanged rather than a quiet edit of the original.
    const shop = workshopOf([]);
    expect(appendEdit(shop, SUPPOSE)).toBe(shop);
  });

  // test_a_second_branch_takes_its_own_hue_and_its_own_edits
  it("keeps each branch's edits to itself, and gives each its own hue", () => {
    let shop = forkBranch(workshopOf([]), "the first");
    shop = appendEdit(shop, SUPPOSE);
    shop = forkBranch(shop, "the second");
    shop = appendEdit(shop, ADD);
    expect(shop.branches.map((branch) => branch.edits.length)).toEqual([1, 1]);
    expect(shop.branches.map((branch) => branch.hue)).toEqual(["violet", "teal"]);
    expect(shop.branches.map((branch) => branch.label)).toEqual(["the first", "the second"]);
  });

  // test_opening_a_branch_that_is_not_there_changes_nothing
  it("ignores a branch that is not there, and closes back to the map as written", () => {
    const shop = forkBranch(workshopOf([]), "the only one");
    expect(openBranch(shop, "nothing-by-that-name")).toBe(shop);
    expect(openBranch(shop, null).openId).toBeNull();
  });
});
