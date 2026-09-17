/**
 * What an edit reached, and what it provably left alone.
 *
 * The one that matters most is the second: on the strike branch, *OPEC+
 * announces output restraint* comes out **untouched**. Its only incoming arrow
 * is the feedback arrow out of Brent — a market acting back on the world it
 * measures — and the map the engine works through is the map with feedback
 * arrows set aside. So the screen can say out loud: your strike moves the oil
 * price, the insurance premium, both contracts and the diplomatic ending, and it
 * cannot move OPEC's announcement. That sentence is the product.
 *
 * **Where the shape under test comes from.** The stored example's own structure
 * is written out below rather than fetched, so that these tests need no server
 * and no browser. That is a deliberate division of labour: this file checks the
 * reducer's rules against a stated shape, and `frontend/e2e/hormuz.spec.ts`
 * checks that the shape on screen really is the server's own — it drives the
 * real app against the real route. Neither test can stand in for the other.
 *
 * No likelihood appears anywhere below, because no likelihood is involved.
 * Following arrows is walking, not calculating.
 */

import { describe, expect, it } from "vitest";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { BranchView, Edit } from "../../world";
import { badgesByClaim, standingByClaim } from "../diff/badges";
import { bothPaintings, branchWorld } from "../diff/branchWorld";
import { readDiff } from "../diff/diffState";
import { endings } from "../diff/endings";
import type { Arrow } from "../diff/reach";

/** The seven claims of the stored example, in the order the map serves them. */
const CLAIMS = ["H", "C", "B", "R", "M1", "M2", "N1"] as const;

/**
 * The eight arrows of the stored example.
 *
 * `B → R` is the feedback arrow: a run of cheap Brent settlements pressing on
 * what OPEC+ announces. `R → B` is an ordinary arrow in the other direction —
 * announced restraint props the price back up. Two different arrows between the
 * same pair of claims, and only one of them is set aside.
 */
const ARROWS: Arrow[] = [
  { id: "H->B", source: "H", target: "B", reflexive: false },
  { id: "H->C", source: "H", target: "C", reflexive: false },
  { id: "H->N1", source: "H", target: "N1", reflexive: false },
  { id: "C->B", source: "C", target: "B", reflexive: false },
  { id: "B->M1", source: "B", target: "M1", reflexive: false },
  { id: "B->M2", source: "B", target: "M2", reflexive: false },
  { id: "B->R", source: "B", target: "R", reflexive: true },
  { id: "R->B", source: "R", target: "B", reflexive: false },
];

/** The three arrows the strike brings, all of them pushing against their targets. */
const STRIKE_ARROWS: Arrow[] = [
  { id: "S->B", source: "S", target: "B", reflexive: false },
  { id: "S->C", source: "S", target: "C", reflexive: false },
  { id: "S->H", source: "S", target: "H", reflexive: false },
];

/** The strike branch: suppose H from Oct 1, add S with three arrows, suppose S from Oct 2. */
const STRIKE_EDITS: Edit[] = [
  { op: "do", target: "H", value: true, at: "2026-10-01" },
  {
    op: "insert",
    claimId: "S",
    words: "A confirmed military strike on Iranian territory.",
    arrows: STRIKE_ARROWS.map(({ id, source, target }) => ({ id, source, target })),
  },
  { op: "do", target: "S", value: true, at: "2026-10-02" },
];

/** Read the strike branch against the stored example's shape. */
function strike() {
  return readDiff([...CLAIMS, "S"], [...ARROWS, ...STRIKE_ARROWS], STRIKE_EDITS);
}

describe("what an edit did to the map", () => {
  // test_computes_the_four_structural_states_for_the_strike_branch
  it("works out one word per claim from the branch alone", () => {
    const { states } = strike();
    expect(Object.fromEntries(states)).toEqual({
      S: "added",
      H: "downstream",
      C: "downstream",
      B: "downstream",
      N1: "downstream",
      M1: "downstream",
      M2: "downstream",
      R: "untouched",
    });
  });

  // test_r_comes_out_untouched
  it("says out loud that the strike cannot reach OPEC's announcement", () => {
    // The whole of the product's central correctness claim, in one assertion.
    expect(strike().states.get("R")).toBe("untouched");
  });

  // test_a_feedback_arrow_never_carries_a_change
  it("never carries a change along a feedback arrow", () => {
    // Set the feedback flag and R becomes reachable; that is the one line to
    // change the day feedback arrows are unrolled in time, and this test is the
    // thing that will fail loudly and point at it.
    const unrolled = ARROWS.map((arrow) =>
      arrow.id === "B->R" ? { ...arrow, reflexive: false } : arrow,
    );
    const asIs = readDiff([...CLAIMS, "S"], [...ARROWS, ...STRIKE_ARROWS], STRIKE_EDITS);
    const pretend = readDiff([...CLAIMS, "S"], [...unrolled, ...STRIKE_ARROWS], STRIKE_EDITS);
    expect(asIs.states.get("R")).toBe("untouched");
    expect(pretend.states.get("R")).toBe("downstream");
  });

  // test_the_showcase_depends_on_the_order_of_the_edits
  it("only lets the strike reach the strait because its arrow arrived afterwards", () => {
    // Supposing a claim cuts the arrows into it that exist at that moment. Move
    // the supposition to the end and it cuts the strike's arrow too, and the
    // strait is no longer something the strike can move. The order of the edits
    // is load-bearing, and this is where that is written down.
    const supposedLast: Edit[] = [
      STRIKE_EDITS[1] as Edit,
      STRIKE_EDITS[2] as Edit,
      STRIKE_EDITS[0] as Edit,
    ];
    const cut = readDiff([...CLAIMS, "S"], [...ARROWS, ...STRIKE_ARROWS], supposedLast);
    expect(cut.cutLinks.has("S->H")).toBe(true);
  });

  // test_a_supposition_that_is_false_kills_its_target
  it("marks the target of a supposition that it is false, and nothing else", () => {
    const { states } = readDiff(CLAIMS as unknown as string[], ARROWS, [
      { op: "do", target: "C", value: false, at: "2026-10-01" },
    ]);
    expect(states.get("C")).toBe("killed");
    // Everything C causes can still move; only C itself is forced.
    expect(states.get("B")).toBe("downstream");
    expect(states.get("H")).toBe("untouched");
  });

  // test_your_own_number_moves_nothing_the_map_computes
  it("does not blank a model number because you put your own beside it", () => {
    const { states, canMove } = readDiff(CLAIMS as unknown as string[], ARROWS, [
      { op: "believe", target: "M1", belief: { p: 0.4, lo: 0.3, hi: 0.5 } },
    ]);
    expect(states.get("M1")).toBe("downstream");
    // Your number is not pushed through the map, so the model's number on that
    // claim has not moved and must not read as absent.
    expect(canMove.has("M1")).toBe(false);
  });
});

describe("the second world", () => {
  /** The stored example's shape as a world, with claims and arrows a tile could draw. */
  function base() {
    return aWorld({
      baseId: "hormuz",
      hypothesisId: "H",
      claims: [
        aClaim({ id: "H", kind: "hypothesis" }),
        aClaim({ id: "C" }),
        aClaim({ id: "B" }),
        aClaim({ id: "R" }),
        aClaim({ id: "M1", kind: "market" }),
        aClaim({ id: "M2", kind: "market" }),
        aClaim({ id: "N1", kind: "not_tradeable" }),
      ],
      links: ARROWS.map((arrow) =>
        aWire({
          id: arrow.id,
          source: arrow.source,
          target: arrow.target,
          reflexive: arrow.reflexive,
        }),
      ),
    });
  }

  /** The strike branch, with the whole claim and the whole arrows the map supplies. */
  function branch(): BranchView {
    return {
      id: "br_hormuz_then_strike",
      label: "Hormuz opens, then Iran is struck",
      hue: "violet",
      edits: STRIKE_EDITS,
      claims: [aClaim({ id: "S", claim: "A confirmed military strike on Iranian territory." })],
      links: STRIKE_ARROWS.map((arrow) =>
        aWire({
          id: arrow.id,
          source: arrow.source,
          target: arrow.target,
          mode: "sustain",
          strength: -1.9,
        }),
      ),
    };
  }

  // test_a_claim_your_edit_can_reach_reads_its_absence
  it("puts an absence with a reason where a likelihood would have moved", () => {
    const world = branchWorld(base(), branch());
    const b = world.claims.find((claim) => claim.id === "B");
    expect(b?.beliefs.model.reading).toBeUndefined();
    expect(b?.beliefs.model.absence?.words).toBe("no engine yet");
    expect(b?.beliefs.model.absence?.reason).toMatch(/nothing has worked this number/i);
    // And the one claim it cannot reach keeps its number, unhedged.
    const r = world.claims.find((claim) => claim.id === "R");
    expect(r?.beliefs.model.reading).toBeDefined();
  });

  // test_never_shifts_on_an_absent_number
  it("never calls a claim shifted, because nothing here has two numbers to compare", () => {
    const world = branchWorld(base(), branch());
    expect(world.claims.map((claim) => claim.diff)).not.toContain("shifted");
  });

  // test_paints_both_worlds_from_one_position_map
  it("gives both paintings the same claims and the same arrows, in the same order", () => {
    const { now, before } = bothPaintings(base(), branch());
    expect(before.claims.map((claim) => claim.id)).toEqual(now.claims.map((claim) => claim.id));
    expect(before.links.map((link) => link.id)).toEqual(now.links.map((link) => link.id));
  });

  // test_space_changes_no_position
  it("draws the claim only one world has as a ghost rather than removing it", () => {
    const { now, before } = bothPaintings(base(), branch());
    // A tile that disappeared would be a change you could only catch by
    // remembering where it had been.
    expect(before.claims.find((claim) => claim.id === "S")?.ghost).toBe(true);
    expect(now.claims.find((claim) => claim.id === "S")?.ghost).not.toBe(true);
  });

  // test_the_map_as_it_was_written_keeps_its_own_numbers
  it("leaves every number in the other painting exactly as the map wrote it", () => {
    const { before } = bothPaintings(base(), branch());
    for (const claim of before.claims) {
      if (claim.id === "S") {
        continue;
      }
      expect(claim.beliefs.model.reading).toBeDefined();
      expect(claim.badges ?? []).toEqual([]);
    }
  });

  // test_agrees_with_the_servers_affected_set
  it.skip(
    "agrees with the server's own affected set — skipped until the engine's world route exists, " +
      "because there is nothing to compare against yet. It is skipped rather than deleted: the " +
      "day the browser and the engine disagree about what an edit reached is the day this " +
      "product stops being traceable, and this is the test that catches it.",
    () => {
      expect(true).toBe(true);
    },
  );
});

describe("what a tile says about the edits behind it", () => {
  const context = {
    words: new Map([
      ["H", "The Strait of Hormuz reopens to unrestricted commercial transit."],
      ["S", "A confirmed military strike on Iranian territory."],
    ]),
    arrows: new Map([["S->H", { source: "S", mode: "sustain" as const, strength: -1.9 }]]),
  };

  // test_h_reads_supposed_then_retracted_by_the_strike
  it("reads Supposed then Retracted, in order, word for word", () => {
    const badges = badgesByClaim(STRIKE_EDITS, context);
    expect((badges.get("H") ?? []).map((badge) => badge.words)).toEqual([
      "Supposed · Oct 1",
      'Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"',
    ]);
    expect((badges.get("S") ?? []).map((badge) => badge.words)).toEqual([
      "Added",
      "Supposed · Oct 2",
    ]);
  });

  // test_a_supposed_claim_shows_the_word_and_a_retracted_one_does_not
  it("shows the word where a likelihood would go only while the supposition holds", () => {
    const badges = badgesByClaim(STRIKE_EDITS, context);
    const standing = standingByClaim(STRIKE_EDITS, badges);
    expect(standing.get("S")?.words).toBe("Supposed · Oct 2");
    // H was supposed and then pushed back down, so it no longer stands on the
    // reader's say-so — and the pair of badges says so instead.
    expect(standing.has("H")).toBe(false);
  });

  // test_an_arrow_that_fires_once_cannot_take_back_a_supposition
  it("only lets a holding arrow retract a supposition", () => {
    // A toppled domino stays toppled: an arrow that fires once and fades cannot
    // take back the reader's word.
    const fires = {
      ...context,
      arrows: new Map([["S->H", { source: "S", mode: "trigger" as const, strength: -1.9 }]]),
    };
    const badges = badgesByClaim(STRIKE_EDITS, fires);
    expect((badges.get("H") ?? []).map((badge) => badge.words)).toEqual(["Supposed · Oct 1"]);
  });
});

describe("the endings the edit can reach", () => {
  // test_lists_reachable_terminals_in_map_order
  it("lists them in the order the map stores them and ranks nothing", () => {
    const world = branchWorld(
      aWorld({
        hypothesisId: "H",
        claims: [
          aClaim({ id: "H", kind: "hypothesis" }),
          aClaim({ id: "C" }),
          aClaim({ id: "B" }),
          aClaim({ id: "R" }),
          aClaim({ id: "M1", kind: "market" }),
          aClaim({ id: "M2", kind: "market" }),
          aClaim({ id: "N1", kind: "not_tradeable" }),
        ],
        links: ARROWS.map((arrow) =>
          aWire({
            id: arrow.id,
            source: arrow.source,
            target: arrow.target,
            reflexive: arrow.reflexive,
          }),
        ),
      }),
      {
        id: "b",
        label: "a branch",
        hue: "violet",
        edits: [{ op: "do", target: "H", value: true, at: "2026-10-01" }],
        claims: [],
        links: [],
      },
    );
    const rows = endings(world);
    // Map order, which is visibly arbitrary and says so on screen. R is not an
    // ending and never appears.
    expect(rows.map((row) => row.claimId)).toEqual(["M1", "M2", "N1"]);
    for (const row of rows) {
      expect(row.move.reading).toBeUndefined();
      expect(row.rangeWidth.reading).toBeUndefined();
      expect(row.agreement.reading).toBeUndefined();
      expect(row.move.absence?.reason.length ?? 0).toBeGreaterThan(20);
    }
  });
});
