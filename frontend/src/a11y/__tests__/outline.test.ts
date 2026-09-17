/**
 * The map read rather than drawn, and what a branch may honestly say out loud.
 *
 * Two rules are worth the whole file. **Every claim gets exactly one item** — a
 * map is not a tree, so the outline is a spanning tree and a claim with several
 * causes names them in its own sentence instead of appearing twice. And **the
 * announcement says only what somebody computed**: with no engine, nothing has
 * changed, so the line says what arrived, what the edit can reach, what was
 * retracted, and that there are no numbers yet — out loud, rather than as a
 * silence the reader has to notice.
 */

import { describe, expect, it } from "vitest";
import { branchWorld } from "../../graph/diff/branchWorld";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { BranchView } from "../../world";
import { branchAnnouncement } from "../announcement";
import { flatten, outlineOf } from "../sentences";

/** The stored example's shape, as a world a tile could draw. */
function base() {
  return aWorld({
    hypothesisId: "H",
    claims: [
      aClaim({ id: "H", kind: "hypothesis", claim: "The Strait of Hormuz reopens." }),
      aClaim({ id: "C", claim: "Lloyd's war-risk premium falls below 0.4%." }),
      aClaim({ id: "B", claim: "Brent crude settles below $68 for five sessions." }),
      aClaim({ id: "R", claim: "OPEC+ announces output restraint." }),
      aClaim({ id: "M1", kind: "market", claim: "A Polymarket contract resolves YES." }),
      aClaim({ id: "M2", kind: "market", claim: "The energy fund XLE underperforms SPY." }),
      aClaim({ id: "N1", kind: "not_tradeable", claim: "Omani-mediated talks resume publicly." }),
    ],
    links: [
      aWire({ source: "H", target: "B", lag: 2 }),
      aWire({ source: "H", target: "C", mode: "sustain", lag: 0 }),
      aWire({ source: "H", target: "N1", lag: 10 }),
      aWire({ source: "C", target: "B", mode: "sustain", lag: 7 }),
      aWire({ source: "B", target: "M1", lag: 1 }),
      aWire({ source: "B", target: "M2", lag: 3 }),
      aWire({ source: "B", target: "R", reflexive: true, lag: 14 }),
      aWire({ source: "R", target: "B", strength: -1.2, lag: 14 }),
    ],
  });
}

/** The strike branch, with the whole claim and arrows the map supplies. */
function strike(): BranchView {
  return {
    id: "br_hormuz_then_strike",
    label: "Hormuz opens, then Iran is struck",
    hue: "violet",
    edits: [
      { op: "do", target: "H", value: true, at: "2026-10-01" },
      {
        op: "insert",
        claimId: "S",
        words: "A confirmed military strike on Iranian territory.",
        arrows: [
          { id: "S->B", source: "S", target: "B" },
          { id: "S->C", source: "S", target: "C" },
          { id: "S->H", source: "S", target: "H" },
        ],
      },
      { op: "do", target: "S", value: true, at: "2026-10-02" },
    ],
    claims: [aClaim({ id: "S", claim: "A confirmed military strike on Iranian territory." })],
    links: [
      aWire({ id: "S->B", source: "S", target: "B", mode: "sustain", strength: -2.4 }),
      aWire({ id: "S->C", source: "S", target: "C", mode: "sustain", strength: -2 }),
      aWire({ id: "S->H", source: "S", target: "H", mode: "sustain", strength: -1.9 }),
    ],
  };
}

describe("the map as a list", () => {
  // test_every_claim_has_exactly_one_item
  it("gives every claim exactly one item, however many causes it has", () => {
    const world = base();
    const items = flatten(outlineOf(world));
    expect(items).toHaveLength(world.claims.length);
    expect(new Set(items.map((item) => item.id)).size).toBe(world.claims.length);
  });

  // test_a_claims_sentence_names_every_wire_into_it
  it("names every wire coming into a claim, in words rather than in a picture", () => {
    const items = flatten(outlineOf(base()));
    const brent = items.find((item) => item.id === "B")?.sentence ?? "";
    // A trigger arrow reads "caused by", a sustain arrow "held up by", and a
    // push against its target "pushed the other way by". Nothing here depends on
    // seeing anything.
    expect(brent).toContain("Caused by: the Strait of Hormuz reopens, two days later.");
    expect(brent).toContain("Held up by: Lloyd's war-risk premium falls below 0.4%.");
    expect(brent).toContain("Pushed the other way by: OPEC+ announces output restraint.");
  });

  // test_the_feedback_arrow_is_read_as_one
  it("reads the feedback arrow as one, and does not list a claim twice", () => {
    const items = flatten(outlineOf(base()));
    const opec = items.find((item) => item.id === "R")?.sentence ?? "";
    expect(opec).toContain("Fed back into by: Brent crude settles below $68 for five sessions");
    expect(opec).toContain("already listed above");
  });

  // test_an_absent_number_is_read_as_its_absence
  it("reads an absent number as the reason it is absent, never as a blank", () => {
    const world = branchWorld(base(), strike());
    const brent = flatten(outlineOf(world)).find((item) => item.id === "B")?.sentence ?? "";
    expect(brent).toContain("Model — nothing has worked this number through the map yet.");
    expect(brent).toContain("Your edit can reach this claim.");
  });

  // test_it_says_what_the_edit_cannot_reach
  it("says out loud which claim the edit cannot reach", () => {
    const world = branchWorld(base(), strike());
    const opec = flatten(outlineOf(world)).find((item) => item.id === "R")?.sentence ?? "";
    expect(opec).toContain("Your edit cannot reach this claim.");
    // And it keeps the number the map was written with, unhedged.
    expect(opec).toMatch(/Model \.\d/);
  });
});

describe("what a branch says out loud", () => {
  // test_the_announcement_names_no_number_the_world_does_not_carry
  it("says what arrived, what the edit can reach, what was retracted, and no numbers yet", () => {
    const world = branchWorld(base(), strike());
    expect(branchAnnouncement(world)).toBe(
      "Branch created. One claim added, six claims your edit can reach, one supposition " +
        "retracted. No numbers yet.",
    );
  });

  // test_it_never_says_a_claim_changed
  it("never says a claim changed, because nothing computed a change", () => {
    const line = branchAnnouncement(branchWorld(base(), strike()));
    expect(line).not.toContain("changed");
    expect(line).toContain("No numbers yet.");
  });

  // test_the_base_world_announces_nothing
  it("has nothing to announce on a map nobody has edited", () => {
    expect(branchAnnouncement(base())).toBe("");
  });
});
