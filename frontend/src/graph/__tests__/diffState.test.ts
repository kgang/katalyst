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
import type { BranchView, DiffView, Edit } from "../../world";
import { disagreements, type EngineState } from "../diff/agreement";
import { badgesByClaim, standingByClaim } from "../diff/badges";
import { bothPaintings, branchWorld, railRows } from "../diff/branchWorld";
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
  it("test_computes_the_four_structural_states_for_the_strike_branch", () => {
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

  it("test_r_comes_out_untouched", () => {
    // The whole of the product's central correctness claim, in one assertion.
    expect(strike().states.get("R")).toBe("untouched");
  });

  it("test_a_feedback_arrow_never_carries_a_change", () => {
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

  it("test_the_showcase_depends_on_the_order_of_the_edits", () => {
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

  it("test_a_supposition_that_is_false_kills_its_target", () => {
    const { states } = readDiff(CLAIMS as unknown as string[], ARROWS, [
      { op: "do", target: "C", value: false, at: "2026-10-01" },
    ]);
    expect(states.get("C")).toBe("killed");
    // Everything C causes can still move; only C itself is forced.
    expect(states.get("B")).toBe("downstream");
    expect(states.get("H")).toBe("untouched");
  });

  it("test_your_own_number_moves_nothing_the_map_computes", () => {
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

  it("test_a_claim_your_edit_can_reach_reads_its_absence", () => {
    const world = branchWorld(base(), branch());
    const b = world.claims.find((claim) => claim.id === "B");
    expect(b?.beliefs.model.reading).toBeUndefined();
    expect(b?.beliefs.model.absence?.words).toBe("no engine yet");
    expect(b?.beliefs.model.absence?.reason).toMatch(/nothing has worked this number/i);
    // And the one claim it cannot reach keeps its number, unhedged.
    const r = world.claims.find((claim) => claim.id === "R");
    expect(r?.beliefs.model.reading).toBeDefined();
  });

  it("test_never_shifts_on_an_absent_number", () => {
    const world = branchWorld(base(), branch());
    expect(world.claims.map((claim) => claim.diff)).not.toContain("shifted");
  });

  it("test_paints_both_worlds_from_one_position_map", () => {
    const { now, before } = bothPaintings(base(), branch());
    expect(before.claims.map((claim) => claim.id)).toEqual(now.claims.map((claim) => claim.id));
    expect(before.links.map((link) => link.id)).toEqual(now.links.map((link) => link.id));
  });

  it("test_space_changes_no_position", () => {
    const { now, before } = bothPaintings(base(), branch());
    // A tile that disappeared would be a change you could only catch by
    // remembering where it had been.
    expect(before.claims.find((claim) => claim.id === "S")?.ghost).toBe(true);
    expect(now.claims.find((claim) => claim.id === "S")?.ghost).not.toBe(true);
  });

  it("test_a_supposed_claim_never_reports_a_move_to_the_number_it_is_supposed_to", () => {
    // The engine stores a flat 1 on a claim whose supposition is holding, so
    // that a chain multiplied out has a factor for it. No surface prints that
    // number — and ".41 up to >.99" is that number with the certainty guard in
    // front of it. The badge pair says *Supposed* instead.
    const supposed: BranchView = {
      id: "b",
      label: "Suppose Brent settles below $68",
      hue: "violet",
      edits: [{ op: "do", target: "B", value: true, at: "2026-10-01" }],
      claims: [],
      links: [],
    };
    const engineSays: DiffView = {
      claims: new Map([
        [
          "B",
          {
            state: "shifted" as const,
            moved: { from: 0.4, to: 1, way: "up" as const, sameDirection: { reading: 1 } },
          },
        ],
      ]),
      rows: [
        {
          claimId: "B",
          label: "Brent crude settles below $68 for five sessions.",
          kind: "market" as const,
          move: { reading: { from: 0.4, to: 1, largestOn: "2026-10-02", way: "up" as const } },
          rangeWidth: { reading: 0 },
          agreement: { reading: 1 },
        },
      ],
      summary: { reading: "It moves one ending." },
      warnings: [],
    };
    // The world the engine built. It says, in `states`, that B reads as a
    // supposition on the day it is judged, so the world source wrote the word
    // where the likelihood would go — and that word is what the guard reads.
    const world = base();
    const asTheEngineBuiltIt = {
      ...world,
      claims: world.claims.map((claim) =>
        claim.id === "B"
          ? {
              ...claim,
              badges: [{ words: "Supposed · Oct 1", reason: "You supposed this is true." }],
              standing: {
                words: "Supposed · Oct 1",
                reason: "While a claim is supposed it is true in every version of the map.",
              },
            }
          : claim,
      ),
    };

    const now = branchWorld(base(), supposed, {
      at: "answered",
      now: asTheEngineBuiltIt,
      change: engineSays,
    });
    const b = now.claims.find((claim) => claim.id === "B");
    expect(b?.standing?.words).toBe("Supposed · Oct 1");
    expect(b?.moved).toBeUndefined();
    expect((b?.badges ?? []).some((badge) => badge.movement === true)).toBe(false);

    // And the rail says the word rather than the number, in the same place the
    // reading would have gone.
    const listed = railRows(now, engineSays);
    expect(listed[0]?.move.reading).toBeUndefined();
    expect(listed[0]?.move.absence?.words).toBe("Supposed · Oct 1");
  });

  it("test_the_map_as_it_was_written_keeps_its_own_numbers", () => {
    const { before } = bothPaintings(base(), branch());
    for (const claim of before.claims) {
      if (claim.id === "S") {
        continue;
      }
      expect(claim.beliefs.model.reading).toBeDefined();
      expect(claim.badges ?? []).toEqual([]);
    }
  });

  /**
   * The browser's structural reading and the engine's own reading of the same
   * branch, side by side.
   *
   * **The engine is the authority and the browser is a hint.** Two rules tie
   * them together, and a break in either is the traceability veto wearing a
   * disguise:
   *
   * 1. A claim the browser says an edit **cannot reach** must be one the engine
   *    says did not move. That is the product's central correctness claim — an
   *    edit changes only what is still joined to its subject — and if the engine
   *    ever moves a claim the browser called untouched, the browser has told the
   *    reader the opposite of the truth.
   * 2. A claim the engine says **moved** must be one the browser said the edit
   *    could reach. The same rule read the other way round.
   *
   * The engine's words below are words, not numbers: which of its four states
   * each claim came out in. They are what it really answers for the stored
   * example's strike branch, and the end-to-end test drives the real server and
   * reads the same states off the screen — so nothing here stands in for a
   * measurement.
   */
  describe("the browser's reading against the engine's", () => {
    /** What the engine says about the strike branch, claim by claim. */
    const ENGINE: ReadonlyMap<string, EngineState> = new Map([
      ["S", "added"],
      ["H", "shifted"],
      ["C", "shifted"],
      ["B", "shifted"],
      ["N1", "shifted"],
      ["M1", "shifted"],
      ["M2", "shifted"],
      ["R", "unchanged"],
    ]);

    it("test_the_browser_states_agree_with_the_engine", () => {
      expect(disagreements(strike().states, ENGINE)).toEqual([]);
    });

    it("test_a_disagreement_with_the_engine_is_caught", () => {
      // A check that cannot fail is not a check. Pretend the engine moved the
      // one claim this branch provably cannot reach, and the comparison has to
      // say so and name it.
      const pretend = new Map(ENGINE).set("R", "shifted");
      expect(disagreements(strike().states, pretend)).toEqual([
        "R: the browser says an edit cannot reach this claim, and the engine says it moved",
      ]);

      // And the other way round: a claim the engine added that the browser
      // never noticed arriving.
      const missed = new Map(ENGINE).set("B", "added");
      expect(disagreements(strike().states, missed)).toEqual([
        "B: the browser says your edit can reach this, and the engine says it arrived with the edit",
      ]);
    });
  });
});

describe("what a tile says about the edits behind it", () => {
  const context = {
    words: new Map([
      ["H", "The Strait of Hormuz reopens to unrestricted commercial transit."],
      ["S", "A confirmed military strike on Iranian territory."],
    ]),
    arrows: new Map([["S->H", { source: "S", mode: "sustain" as const, strength: -1.9 }]]),
  };

  it("test_h_reads_supposed_then_retracted_by_the_strike", () => {
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

  it("test_a_supposed_claim_shows_the_word_and_a_retracted_one_does_not", () => {
    const badges = badgesByClaim(STRIKE_EDITS, context);
    const standing = standingByClaim(STRIKE_EDITS, badges);
    expect(standing.get("S")?.words).toBe("Supposed · Oct 2");
    // H was supposed and then pushed back down, so it no longer stands on the
    // reader's say-so — and the pair of badges says so instead.
    expect(standing.has("H")).toBe(false);
  });

  it("test_an_arrow_that_fires_once_cannot_take_back_a_supposition", () => {
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
  it("test_lists_reachable_terminals_in_map_order", () => {
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
