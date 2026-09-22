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
import { toMovement } from "../../components/BeliefChip";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { Badge, BranchView, ClaimView, DiffView, Edit, Movement } from "../../world";
import { disagreements, type EngineState } from "../diff/agreement";
import { badgesByClaim, standingByClaim } from "../diff/badges";
import { bothPaintings, branchWorld, railRows } from "../diff/branchWorld";
import { toDay } from "../diff/days";
import { readDiff } from "../diff/diffState";
import { endings } from "../diff/endings";
import { noChangeInAWord, noChangeReason } from "../diff/noChange";
import type { Arrow } from "../diff/reach";
import { badgeLines } from "../geometry";

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
      { op: "believe", target: "M1", belief: { p: 0.4 } },
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
            moved: { from: 0.4, to: 1, way: "up" as const, by: 0.6 },
          },
        ],
      ]),
      rows: [
        {
          claimId: "B",
          label: "Brent crude settles below $68 for five sessions.",
          kind: "market" as const,
          move: {
            reading: { from: 0.4, to: 1, largestOn: "2026-10-02", way: "up" as const, by: 0.6 },
          },
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

  /**
   * Why the engine says a claim did not move — the one sentence, in one place.
   *
   * The engine calls a claim `shifted` only when its move clears a floor, and
   * `unchanged` when it does not — **and it says so on the claim's own row**, in
   * one plain word: *under the floor*.
   *
   * So the browser copies that word across and turns it into words. It still
   * works nothing out: the floor is a constant inside the engine and is nowhere
   * in its answer, so re-running the test here is not possible even by accident.
   * Where the engine gives no word, neither does the browser — guessing would
   * mean printing a sentence that is flatly false about half the claims it
   * appears on, which is the traceability veto in plain sight.
   *
   * **The engine has a second word and this product no longer shows it** *(Kent,
   * 2026-09-22, R48)*: *the versions of the map disagreed which way it went*. It
   * is a fact about running the map two thousand times, which is the thing Kent
   * cut, so `world/apiSource.ts` drops it on the way in and a claim that failed
   * on it reaches here with no word at all — the case the second test below is
   * about.
   */
  describe("why the engine reports no change", () => {
    /** The engine's answer: every claim untouched but one, which it calls unchanged. */
    function saysUnchanged(moved: Movement, id = "B"): DiffView {
      return {
        claims: new Map([[id, { state: "unchanged" as const, moved }]]),
        rows: [],
        summary: { reading: "Nothing it can reach moved." },
        warnings: [],
      };
    }

    /** B's tile line, as the tile draws it, for one reading of the engine's. */
    function tileLine(moved: Movement) {
      const now = branchWorld(base(), branch(), {
        at: "answered",
        now: base(),
        change: saysUnchanged(moved),
      });
      const b = now.claims.find((claim) => claim.id === "B");
      return (b?.badges ?? []).find((badge) => badge.movement === true);
    }

    it("test_the_no_change_reason_names_the_reason_the_engine_named", () => {
      // It moved a hair and the engine says so. The sentence names the engine's
      // own reason and the engine's own two numbers, and nothing else.
      const aHair = tileLine({
        from: 0.41,
        to: 0.412,
        way: "up",
        by: 0.002,
        unchangedBecause: "under_the_floor",
      });
      expect(aHair?.words).toBe("no change");
      expect(aHair?.reason).toMatch(/smaller than it will report/);
      expect(aHair?.reason).toContain(".41");
    });

    it("test_the_no_change_reason_invents_no_reason_the_engine_left_out", () => {
      // The engine leaves the word out where there was no test to fail, and it
      // is also left out where the word it gave is one this product may not show
      // — *the versions of the map disagreed which way* (2026-09-22, R48).
      // Either way the browser cannot work the reason out for itself, because
      // the floor is nowhere in the engine's answer, so no reason is named.
      const silent = tileLine({ from: 0.41, to: 0.46, way: "up", by: 0.05 });
      expect(silent?.words).toBe("no change");
      expect(silent?.reason).not.toMatch(/smaller than it will report/);
      expect(silent?.reason).toMatch(/gave no reason this product can show/);
      // And nothing about versions of the map, on a sentence that used to name
      // them twice.
      expect(silent?.reason.toLowerCase()).not.toContain("version");
    });

    it("test_the_tile_and_the_rail_give_one_reason_and_not_two", () => {
      const moved: Movement = {
        from: 0.41,
        to: 0.46,
        way: "up",
        by: 0.05,
        unchangedBecause: "under_the_floor",
      };
      const line = tileLine(moved);
      // The rail lists endings, so this half of the test asks about one: M1, a
      // market the strike can reach through B.
      const change = saysUnchanged(moved, "M1");
      const held = railRows(
        branchWorld(base(), branch(), { at: "answered", now: base(), change }),
        change,
      ).find((row) => row.claimId === "M1");
      expect(held?.move.absence?.words).toBe("no change");
      expect(held?.move.absence?.reason).toContain(noChangeReason(moved));
      expect(line?.reason).toBe(noChangeReason(moved));

      // And the row's own half-line — the words a reader gets without pressing
      // anything — comes from the same module and the same engine word, so the
      // glance and the sentence behind it cannot say two different things.
      expect(held?.note).toBe(noChangeInAWord(moved));
      expect(held?.note).toBe("barely moved");
    });

    it("test_an_ending_the_engine_will_not_call_moved_stays_on_the_list", () => {
      // The rule this whole block exists for, stated as a rule about the list
      // rather than about a sentence: an ending the engine will not call moved
      // is **on the change list**, marked as one that held still. On the stored
      // example's strike branch that is the talks — the biggest move on the map,
      // behind the map's one bare assertion — and a list that quietly dropped it
      // would drop the most interesting thing on the map without saying so.
      //
      // The engine's reason for that one is *the versions of the map disagreed
      // which way*, which this product no longer shows (2026-09-22, R48), so the
      // move reaches the browser with no word at all: the row is still there,
      // still marked, and simply carries no half-line.
      const moved: Movement = { from: 0.28, to: 0.38, way: "up", by: 0.1 };
      const change = saysUnchanged(moved, "N1");
      const listed = railRows(
        branchWorld(base(), branch(), { at: "answered", now: base(), change }),
        change,
      );
      expect(listed.map((row) => row.claimId)).toContain("N1");
      const talks = listed.find((row) => row.claimId === "N1");
      expect(talks?.unranked).toBe(true);
      expect(talks?.move.absence?.words).toBe("no change");
      expect(talks?.note).toBeUndefined();
    });

    it("test_an_ending_you_forced_false_stays_on_the_list_and_is_not_no_change", () => {
      // **The loudest thing an edit can do to an ending used to be the quietest
      // thing on this screen.** Suppose the Brent contract false and the engine
      // calls it `killed`; it ranks only what it calls moved, so it gives that
      // ending no row — and the change list used to add one only for an ending
      // it called `unchanged`. The reader forced an ending false and the list
      // said nothing at all.
      const edits: Edit[] = [{ op: "do", target: "M1", value: false, at: "2026-10-01" }];
      const forcedFalse: BranchView = {
        id: "br_kill_the_contract",
        label: "Suppose the Brent contract does not come true",
        hue: "violet",
        edits,
        claims: [],
        links: [],
      };
      const change: DiffView = {
        claims: new Map([["M1", { state: "killed" as const }]]),
        rows: [],
        summary: { reading: "It moves no ending." },
        warnings: [],
      };
      // The world the engine built, in which the contract carries the word its
      // tile shows instead of a likelihood. The word is not written out here:
      // it comes from the one function that makes one.
      const said = standingByClaim(edits, new Map());
      expect(said.get("M1")?.words).toMatch(/^Supposed · /);
      const asTheEngineBuiltIt = {
        ...base(),
        claims: base().claims.map((claim) =>
          claim.id === "M1" ? { ...claim, standing: said.get("M1") } : claim,
        ),
      };
      const listed = railRows(
        branchWorld(base(), forcedFalse, { at: "answered", now: asTheEngineBuiltIt, change }),
        change,
      );

      const contract = listed.find((row) => row.claimId === "M1");
      expect(contract).toBeDefined();
      expect(contract?.unranked).toBe(true);
      // And it says what is true rather than what is convenient. *No change* is
      // flatly false of an ending the reader has just forced false, and a
      // likelihood would be the flat zero the engine stores for it wearing the
      // certainty guard's clothes. It reads the word its tile reads.
      expect(contract?.move.absence?.words).toBe(said.get("M1")?.words);
      expect(contract?.move.absence?.words).not.toBe("no change");
      expect(contract?.note).toBe("it was supposed false");
      expect(contract?.move.absence?.reason).toContain("supposed this is false");
    });

    it("test_a_forced_false_ending_is_on_the_list_even_with_no_word_to_show", () => {
      // The same rule with the browser's own half missing: whatever else is or
      // is not known, an ending the engine called `killed` is **on the list**.
      // The row falls back to the engine's own word for what happened rather
      // than to silence or to *no change*, either of which would be untrue.
      const forcedFalse: BranchView = {
        id: "br_kill_the_contract",
        label: "Suppose the Brent contract does not come true",
        hue: "violet",
        edits: [{ op: "do", target: "M1", value: false, at: "2026-10-01" }],
        claims: [],
        links: [],
      };
      const change: DiffView = {
        claims: new Map([["M1", { state: "killed" as const }]]),
        rows: [],
        summary: { reading: "It moves no ending." },
        warnings: [],
      };
      const contract = railRows(
        branchWorld(base(), forcedFalse, { at: "answered", now: base(), change }),
        change,
      ).find((row) => row.claimId === "M1");
      expect(contract?.unranked).toBe(true);
      expect(contract?.move.absence?.words).not.toBe("no change");
      expect(contract?.note).toBe("it was supposed false");
    });
  });

  /**
   * **One claim, two pairs of numbers, two different days.**
   *
   * The tile's line reads the claim on the day it is judged. The change list
   * beside the map reads each ending on the day the two maps are furthest
   * apart, and says so on the row. Somebody who notices that the same claim
   * carries two different readings, with only one of them dated, concludes that
   * one of the two is wrong — and neither is.
   *
   * So the tile's line names its own day and names the other. **In the sentence
   * behind it, never in the words it draws**: how many lines the badges take is
   * what reserves the tile's height before the browser has drawn one, and the
   * clause takes the line over the width a tile has.
   */
  describe("the day the tile's line is read on", () => {
    /** The engine's answer: B shifted, with these two readings. */
    function saysShifted(moved: Movement): DiffView {
      return {
        claims: new Map([["B", { state: "shifted" as const, moved }]]),
        rows: [],
        summary: { reading: "It moves one ending." },
        warnings: [],
      };
    }

    /** B's tile line, as the tile draws it, for one reading of the engine's. */
    function shiftedLine(moved: Movement) {
      const now = branchWorld(base(), branch(), {
        at: "answered",
        now: base(),
        change: saysShifted(moved),
      });
      const b = now.claims.find((claim) => claim.id === "B");
      return (b?.badges ?? []).find((badge) => badge.movement === true);
    }

    /** A move the engine could have read on B. */
    const MOVED: Movement = {
      from: 0.5,
      to: 0.42,
      way: "down",
      by: -0.08,
    };

    it("test_the_line_says_which_day_it_is_read_on_and_that_the_rail_reads_another", () => {
      const line = shiftedLine(MOVED);
      // The day is the claim's own judging day, written the way every other day
      // on this canvas is written — read off the claim, never typed in here.
      const judged = base().claims.find((claim) => claim.id === "B")?.resolvesBy as string;
      expect(line?.reason).toContain(toDay(judged));
      expect(line?.reason).toContain("the day this claim is judged");
      // And it names the other reading rather than leaving a reader to find it.
      expect(line?.reason).toMatch(/change list/i);
      expect(line?.reason).toMatch(/furthest apart/i);
    });

    it("test_the_clause_costs_the_tile_no_height", () => {
      // The words are the two readings and the chevron between them, and
      // nothing else — which is one badge line at the width a tile has. Every
      // other state this line can be in is shorter or the same, so the tile is
      // the same height whichever answer came back, which is what stops the map
      // laying itself out again when one lands.
      const line = shiftedLine(MOVED);
      expect(line?.words).toBe(toMovement(MOVED.from, MOVED.to, MOVED.by, MOVED.way));
      expect(line?.words).not.toMatch(/judged|change list/i);
      expect(badgeLines({ ...(aClaim({ id: "B" }) as ClaimView), badges: [line as Badge] })).toBe(
        1,
      );
    });
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

    /**
     * What the engine really answers for a branch that reports a claim and then
     * changes how hard one of its causes pushes it.
     *
     * Words, not numbers, and measured from the running server rather than
     * chosen: `POST /api/worlds/diff` on the stored example at seed 20261001.
     * The arrow's source reads *unchanged* here — it moves, but by less than
     * the engine reports — and the browser must still say the edit can reach
     * it, because the reader's tile shows the number either way.
     */
    const REPORTED_THEN_RETUNED: ReadonlyMap<string, EngineState> = new Map([
      ["C", "shifted"],
      ["H", "unchanged"],
      ["B", "unchanged"],
      ["N1", "unchanged"],
      ["M1", "unchanged"],
      ["M2", "unchanged"],
      ["R", "unchanged"],
    ]);

    it("test_a_retune_under_a_report_agrees_with_the_engine", () => {
      // Report the premium fell, then change how hard the strait's opening
      // pushes it. The engine moves the **source** of that arrow — how much
      // news about an effect says about a cause depends on how hard that cause
      // was pushing — and the browser has to have said the edit could reach it.
      const branch = readDiff(CLAIMS, ARROWS, [
        { op: "observe", target: "C", value: true, at: "2026-10-01" },
        { op: "retune", link: "H->C", strength: 3, wasStrength: 1.6 },
      ]);
      expect(branch.states.get("H")).toBe("downstream");
      expect(branch.states.get("R")).toBe("untouched");
      expect(disagreements(branch.states, REPORTED_THEN_RETUNED)).toEqual([]);
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

/**
 * The rule that reaches further than any row of the table.
 *
 * > An edit that can move a claim some report was made about can move
 * > everything that report is evidence about — and that applies again to any
 * > further report whose own claim has just been brought in.
 *
 * **This is one rule written twice**: here, and in `affected_set` in
 * `backend/src/katalyst/domain/patch.py`. The engine's own tests for it are
 * `test_an_edit_under_an_observation_may_move_what_the_observation_is_about`
 * and `test_a_retune_under_an_observation_moves_the_arrows_source`; these are
 * the browser's half, and the two must move together.
 *
 * **Why the cases below are about reach and not about numbers.** The engine
 * reports only moves that clear its floor *and* that the versions of the map
 * agree about, so a claim this rule brings in often comes out `unchanged`
 * while its number has plainly moved — on the stored example, reporting OPEC's
 * announcement and then hanging a claim off it moves the insurance premium
 * from `.3977` to `.3925` and calls it unchanged. The four words cannot catch
 * that; the tile can, which is why the end-to-end test reads the numbers off
 * the screen and this reads the shape.
 */
describe("an edit that can move a reported claim", () => {
  /** The stored example's shape, with a claim the branch hangs off the talks. */
  const WITH_A_STRIKE = [...CLAIMS, "S"];

  /** Report OPEC's announcement, then hang a new claim between the talks and it. */
  const REPORT_THEN_ATTACH: Edit[] = [
    { op: "observe", target: "R", value: true, at: "2026-10-01" },
    {
      op: "insert",
      claimId: "S",
      words: "A confirmed military strike on Iranian territory.",
      arrows: [
        { id: "N1->S", source: "N1", target: "S" },
        { id: "S->R", source: "S", target: "R" },
      ],
    },
  ];

  it("test_an_edit_that_can_move_a_reported_claim_can_move_what_the_report_is_about", () => {
    const read = readDiff(WITH_A_STRIKE, ARROWS, REPORT_THEN_ATTACH);

    // The new arrows make the talks a cause of the claim that was reported,
    // so the report is now evidence about the talks — and about the strait
    // that causes them, and about the premium that strait also causes. An
    // edit that can move the reported claim can move all of it.
    for (const id of ["N1", "H", "C"]) {
      expect(read.states.get(id), id).toBe("downstream");
    }
    // And those are numbers the browser must not draw from the map as it was
    // written while it waits for the engine.
    for (const id of ["N1", "H", "C"]) {
      expect(read.canMove.has(id), id).toBe(true);
    }
  });

  it("test_your_own_number_never_reaches_through_a_report", () => {
    // The one edit the rule never widens, and the reason it has a row of its
    // own: your number sits beside the model's and is not pushed through the
    // map, so it cannot change which versions of the map survive and cannot
    // change what a report says about anything.
    const read = readDiff(CLAIMS, ARROWS, [
      { op: "observe", target: "R", value: true, at: "2026-10-01" },
      { op: "believe", target: "N1", belief: { p: 0.9 } },
    ]);
    // Your number reaches the claim you wrote it on and nothing else. The
    // report speaks about OPEC's announcement and what that leads to; the
    // belief brings none of it in, and brings in nothing of its own either.
    expect(read.states.get("N1")).toBe("downstream");
    expect(read.canMove.has("N1")).toBe(false);
    for (const id of ["H", "C"]) {
      expect(read.states.get(id), id).toBe("untouched");
    }
  });

  it("test_an_edit_that_cannot_touch_the_reported_claim_is_not_widened", () => {
    // The other half of the same sentence. Without it, a report anywhere on a
    // map would make every later edit touch everything, and the promise that
    // an edit leaves the rest of the map alone would say nothing at all.
    const read = readDiff(CLAIMS, ARROWS, [
      { op: "observe", target: "R", value: true, at: "2026-10-01" },
      { op: "retune", link: "H->N1", strength: 3, wasStrength: 0.7 },
    ]);
    // The report speaks about OPEC's announcement, the price it moves and the
    // two contracts hanging off that. The retune reaches the talks and
    // nothing else: it cannot move the claim that was reported, so none of
    // what the report is about comes in with it.
    expect(read.states.get("N1")).toBe("downstream");
    for (const id of ["H", "C"]) {
      expect(read.states.get(id), id).toBe("untouched");
    }
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

  it("test_news_that_something_did_not_happen_reads_the_mirror_of_happened", () => {
    // The panel sends only `value: true` today, so no button on this canvas
    // reaches this case — but the wire format carries the value and a branch
    // written elsewhere does. Printing *Happened* over it would tell the reader
    // the opposite of what the engine was told. The word is Kent's
    // (2026-09-21, G12) and lives in `spec/vocabulary.md`.
    const news = badgesByClaim(
      [
        { op: "observe", target: "H", value: true, at: "2026-10-01" },
        { op: "observe", target: "S", value: false, at: "2026-10-02" },
      ],
      context,
    );
    expect((news.get("H") ?? []).map((badge) => badge.words)).toEqual(["Happened \u00b7 Oct 1"]);
    expect((news.get("S") ?? []).map((badge) => badge.words)).toEqual([
      "Did not happen \u00b7 Oct 2",
    ]);
    expect((news.get("S") ?? [])[0]?.reason).toContain("that this did not happen");
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
      expect(row.move.absence?.reason.length ?? 0).toBeGreaterThan(20);
      // And a row is the ending and its change, and nothing else: *how firm*
      // and *same direction* were readings of a range and of the versions of
      // the map behind one, and both went with them (2026-09-22, R48).
      expect("rangeWidth" in row).toBe(false);
      expect("agreement" in row).toBe(false);
    }
  });
});
