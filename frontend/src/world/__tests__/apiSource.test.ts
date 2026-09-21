/**
 * What the source that asks the engine must do, and what it must never do.
 *
 * The three questions it asks are the whole of the join, so the first test below
 * is about the requests themselves: which routes, with which map, which branch
 * and which seed. Everything after it is about the answers — that they are
 * carried across unchanged, that a supposed claim gets the word rather than the
 * `1` the engine stores for it, and that the badge saying a supposition was
 * taken back is read off the world rather than worked out a second time here.
 *
 * **The server is replaced by a stand-in.** Its answers below are the *shapes*
 * the engine produces, with numbers chosen to be obviously made up, and no test
 * here asserts that any of them is right — the engine's own tests do that. What
 * is checked is that a number handed over arrives on screen as the same number,
 * which is a claim about this file and not about arithmetic.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Belief, Diff, FixtureBundle, World } from "../../api/client";
import { RefusedBranch } from "../../api/client";
import { ApiWorldSource } from "../apiSource";
import type { BranchView } from "../types";

vi.mock("../../api/client", async () => {
  const real = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return {
    ...real,
    readExample: vi.fn(),
    readWorld: vi.fn(),
    readDiff: vi.fn(),
    readConditional: vi.fn(),
  };
});

import { readConditional, readDiff, readExample, readWorld } from "../../api/client";

/** One claim as the server writes one, with only what these tests read filled in. */
function proposition(id: string, by: string, over: Record<string, unknown> = {}) {
  return {
    id,
    claim: `${id} — a claim that will be true or false by a date.`,
    kind: "event",
    resolution: { criteria: "Checkable.", source: "A named source.", by },
    prior: { p: 0.3, lo: 0.1, hi: 0.5, owner: "model" },
    beliefs: { model: { p: 0.3, lo: 0.1, hi: 0.5, owner: "model" }, user: null, market: null },
    base_rate: null,
    evidence: [],
    payoff: null,
    not_tradeable_reason: null,
    ...over,
  };
}

/** The map, as the stored-example route serves it. */
const BUNDLE = {
  id: "example",
  title: "An example map",
  fixture_date: "2026-10-01",
  graph: {
    id: "example",
    hypothesis_id: "H",
    propositions: [
      proposition("H", "2026-11-01", { kind: "hypothesis" }),
      proposition("S", "2026-10-02"),
    ],
    links: [],
  },
  branches: [],
} as unknown as FixtureBundle;

/**
 * A world as the engine builds one: H supposed on the first, a strike added and
 * supposed on the second, and the supposition on H taken back by it.
 *
 * The numbers are plainly made up. What matters below is that they come out the
 * other side as themselves.
 */
const WORLD = {
  base_id: "example",
  branch_id: "b",
  seed: 20261001,
  versions: 2000,
  worlds: 8,
  day_zero: "2026-10-01",
  days: 60,
  graph: BUNDLE.graph,
  assignments: [
    { target: "H", value: true, at: "2026-10-01", by: 0, kind: "do" },
    { target: "S", value: true, at: "2026-10-02", by: 2, kind: "do" },
  ],
  retractions: [{ target: "H", at: "2026-10-02", by_link: "S->H", by_claim: "S", by: 1 }],
  beliefs: {
    H: { p: 0.081, lo: 0.04, hi: 0.13, owner: "model" },
    S: { p: 1, lo: 1, hi: 1, owner: "model" },
  },
  series_days: [0, 1, 31],
  series: { H: [1, 0.36, 0.081], S: [0.06, 1, 1] },
  states: {
    H: ["supposed", "withdrawn", "pushed"],
    S: ["sampled", "supposed", "supposed"],
  },
  conditionals: {},
  warnings: ["Fewer worlds survived than usual."],
} as unknown as World;

/** The branch that world came from, as the screen holds one. */
const BRANCH: BranchView = {
  id: "b",
  label: "Hormuz opens, then Iran is struck",
  hue: "violet",
  edits: [
    { op: "do", target: "H", value: true, at: "2026-10-01" },
    { op: "insert", claimId: "S", words: "A confirmed military strike.", arrows: [] },
    { op: "do", target: "S", value: true, at: "2026-10-02" },
  ],
  claims: [],
  links: [],
  wire: {
    id: "b",
    label: "Hormuz opens, then Iran is struck",
    parent: null,
    interventions: [{ kind: "do", target: "H", value: true, at: "2026-10-01" }],
  },
};

/** A difference as the engine writes one. */
const DIFFERENCE = {
  base_id: "example",
  branch_a: null,
  branch_b: "b",
  seed: 20261001,
  versions: 2000,
  worlds: 8,
  claims: {
    H: { target: "H", state: "shifted", before: 0.356, after: 0.081, delta: -0.275, agreement: 1 },
    S: { target: "S", state: "added", before: null, after: 1, delta: null, agreement: null },
  },
  rows: [],
  summary: "The branch moves one ending.",
  warnings: [],
} as unknown as Diff;

beforeEach(() => {
  vi.mocked(readExample).mockResolvedValue(BUNDLE);
  vi.mocked(readWorld).mockResolvedValue(WORLD);
  vi.mocked(readDiff).mockResolvedValue(DIFFERENCE);
  vi.mocked(readConditional).mockResolvedValue({
    p: 0.584,
    lo: 0.416,
    hi: 0.734,
    owner: "model",
  } as Belief);
});

describe("asking the engine", () => {
  it("test_the_api_source_asks_the_three_routes", async () => {
    const source = new ApiWorldSource();

    await source.readWorld({ baseId: "example", branch: BRANCH });
    await source.readDiff({ baseId: "example", branch: BRANCH });
    await source.readConditional({ baseId: "example", branch: BRANCH, linkId: "H->B" });

    // The map comes from the stored-example route, once, and is kept: a map is
    // written by hand and does not change while the page is open.
    expect(readExample).toHaveBeenCalledTimes(1);
    expect(readExample).toHaveBeenCalledWith("example");

    // Each of the three questions goes to its own route, with the whole branch —
    // there is nowhere to keep one — and with the seed read off the map's own
    // date, so that the same map, branch and seed always give the same answer.
    expect(readWorld).toHaveBeenCalledWith("example", BRANCH.wire, 20261001);
    expect(readDiff).toHaveBeenCalledWith("example", BRANCH.wire, 20261001);
    expect(readConditional).toHaveBeenCalledWith("example", BRANCH.wire, 20261001, "H->B");
  });

  it("test_the_seed_is_read_off_the_maps_own_date", async () => {
    // Not a number chosen here and not the clock: a world is rebuildable from
    // the map, the branch and the seed, so the seed has to be the same on every
    // visit. The map is set on the first of October 2026.
    const source = new ApiWorldSource();
    await source.readWorld({ baseId: "example" });
    expect(vi.mocked(readWorld).mock.calls[0]?.[2]).toBe(Number("20261001"));
  });

  it("test_every_number_arrives_exactly_as_the_engine_sent_it", async () => {
    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const h = world.claims.find((claim) => claim.id === "H");

    // Full precision, not rounded here: rounding is a display decision and is
    // made once, in the chip.
    expect(h?.beliefs.model.reading).toEqual({ p: 0.081, lo: 0.04, hi: 0.13 });
    // And how the engine was run, so the chip can say whether its range was
    // computed rather than merely stated.
    expect(world.versions).toBe(2000);
    expect(world.worldsPerVersion).toBe(8);
    expect(world.seed).toBe(20261001);
    // Whatever the engine wanted the reader to see, said once and unedited.
    expect(world.warnings).toEqual(["Fewer worlds survived than usual."]);
  });

  it("test_a_claim_whose_value_an_edit_fixed_gets_the_word_and_never_the_stored_one", async () => {
    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const strike = world.claims.find((claim) => claim.id === "S");

    // The engine stores a flat 1 on a claim whose supposition is holding, so
    // that a chain multiplied out has a factor for it. No surface prints that
    // number: every reader looks at the world's states first and writes the
    // word where the likelihood would go.
    expect(strike?.standing?.words).toBe("Supposed · Oct 2");
    expect(strike?.standing?.reason).toContain("settled in every version of the map");
  });

  it("test_a_claim_judged_on_a_day_the_series_does_not_draw_is_read_the_engines_way", async () => {
    // A window longer than 180 days is drawn at fewer points, so a claim's own
    // resolve-by day is not always one of them. The engine pins the day inside
    // the window and takes the first drawn day at or after it; the browser used
    // to want an exact match and gave up when it did not get one — which left
    // the reader looking at a flat 1 with no word beside it to say why.
    vi.mocked(readWorld).mockResolvedValue({
      ...WORLD,
      graph: {
        ...BUNDLE.graph,
        propositions: [
          proposition("H", "2026-11-01", { kind: "hypothesis" }),
          // Judged on a day the series does not draw: between the second and
          // the third of the three points this world was worked through at.
          proposition("S", "2026-10-15"),
        ],
      },
    } as unknown as World);

    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const strike = world.claims.find((claim) => claim.id === "S");
    expect(strike?.standing?.words).toBe("Supposed \u00b7 Oct 2");
  });

  it("test_an_observed_claim_gets_the_word_too", async () => {
    // One rule, not a rule about suppositions. A claim the reader reported as
    // news is true in every version of the map that survived the report, so the
    // engine stores a flat 1 on it exactly as it does for a supposition — and
    // `>.99` on the chip is that number wearing the certainty guard's clothes.
    // The two are found in different places: a supposition can be undermined, so
    // whether it still holds is a fact about a day and lives in `states`; news
    // cannot be taken back, holds across the window, and lives in the
    // assignments.
    vi.mocked(readWorld).mockResolvedValue({
      ...WORLD,
      assignments: [{ target: "S", value: true, at: null, by: 0, kind: "observe" }],
      retractions: [],
      states: { H: ["sampled", "sampled", "sampled"], S: ["sampled", "sampled", "sampled"] },
      beliefs: {
        ...WORLD.beliefs,
        S: { p: 1, lo: 1, hi: 1, owner: "model" },
      },
    } as unknown as World);

    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const news = world.claims.find((claim) => claim.id === "S");
    expect(news?.standing?.words).toBe("Happened · Oct 1");
    expect(news?.standing?.reason).toContain("settled in every version of the map");
  });

  it("test_news_that_something_did_not_happen_reads_the_mirror_word", async () => {
    // Read off the world rather than worked out from the branch, and the word
    // beside the number is the one the engine was told — *Did not happen ·
    // date*, the mirror of *Happened · date* (Kent, 2026-09-21, G12).
    vi.mocked(readWorld).mockResolvedValue({
      ...WORLD,
      assignments: [{ target: "S", value: false, at: null, by: 0, kind: "observe" }],
      retractions: [],
      states: { H: ["sampled", "sampled", "sampled"], S: ["sampled", "sampled", "sampled"] },
    } as unknown as World);

    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const news = world.claims.find((claim) => claim.id === "S");
    expect(news?.standing?.words).toBe("Did not happen \u00b7 Oct 1");
    expect((news?.badges ?? []).map((badge) => badge.words)).toContain(
      "Did not happen \u00b7 Oct 1",
    );
  });

  it("test_the_world_supplies_the_badges_and_the_standing", async () => {
    const world = await new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    const h = world.claims.find((claim) => claim.id === "H");

    // Read off `World.retractions` — which claim, which day, and whose doing —
    // rather than worked out a second time from the branch. Two derivations of
    // one line eventually disagree, so there is one.
    expect((h?.badges ?? []).map((badge) => badge.words)).toEqual([
      "Supposed · Oct 1",
      'Retracted · Oct 2 · by "S — a claim that will be true or false by a date"',
    ]);
    expect((h?.badges ?? [])[1]?.overrides).toBe(true);
    // And the claim no longer stands on the reader's say-so, because the badge
    // pair says what happened instead.
    expect(h?.standing).toBeUndefined();
  });

  it("test_a_refused_branch_arrives_with_every_reason", async () => {
    vi.mocked(readWorld).mockRejectedValue(
      new RefusedBranch([
        {
          code: "duplicate_id",
          subject: "B",
          message: "This map already has a claim called that.",
        },
        { code: "unknown_target", subject: "NOPE", message: "That claim is not on this map." },
      ]),
    );

    // A refusal is an event, not a breakage: it travels as its own kind of
    // error with the whole list, so the screen can print all of it at once.
    const asked = new ApiWorldSource().readWorld({ baseId: "example", branch: BRANCH });
    await expect(asked).rejects.toBeInstanceOf(RefusedBranch);
    await asked.catch((refusal: RefusedBranch) => {
      expect(refusal.reasons.map((one) => one.message)).toEqual([
        "This map already has a claim called that.",
        "That claim is not on this map.",
      ]);
    });
  });

  it("test_a_branch_that_cannot_be_written_down_is_not_half_sent", async () => {
    // A branch holding a claim the reader typed cannot be folded: a claim is its
    // wording plus how it is judged, by whom and by when, and nothing here
    // drafts those. It is refused in one sentence rather than sent without them.
    const half: BranchView = { ...BRANCH, wire: undefined };
    await expect(
      new ApiWorldSource().readWorld({ baseId: "example", branch: half }),
    ).rejects.toThrow(/drafts one/);
    expect(readWorld).not.toHaveBeenCalled();
  });

  it("test_the_engines_word_for_which_half_a_claim_failed_arrives_as_it_came", async () => {
    // A claim the engine calls `unchanged` failed one of the two halves of its
    // test, and the engine says which: the move was too small, or the versions
    // of the map did not agree which way it went. The two numbers below are
    // plainly made up; the words are what is under test.
    vi.mocked(readDiff).mockResolvedValue({
      ...DIFFERENCE,
      claims: {
        H: {
          target: "H",
          state: "unchanged",
          before: 0.3,
          after: 0.4,
          delta: 0.1,
          agreement: 0.5,
          moved_only_by_reweighting: false,
          unchanged_because: "versions_disagree",
        },
        S: {
          target: "S",
          state: "unchanged",
          before: 0.3,
          after: 0.3,
          delta: 0.001,
          agreement: 0.99,
          moved_only_by_reweighting: false,
          unchanged_because: "under_the_floor",
        },
      },
    } as unknown as Diff);

    const change = await new ApiWorldSource().readDiff({ baseId: "example", branch: BRANCH });
    // Carried across as the word it came as. The floor and the bar that decide
    // it are constants inside the engine and appear nowhere in its answer, so
    // this is the only way the browser can know which half a claim failed —
    // which is what stops a second engine growing here and disagreeing with
    // the first about which claims held still.
    expect(change.claims.get("H")?.moved?.unchangedBecause).toBe("versions_disagree");
    expect(change.claims.get("S")?.moved?.unchangedBecause).toBe("under_the_floor");
  });

  it("test_a_claim_the_engine_gave_no_word_for_carries_none", async () => {
    // The engine leaves the word out where there was no test to fail. The
    // browser leaves it out too rather than picking the likelier of the two:
    // an invented half would be a sentence nobody can trace to an answer.
    vi.mocked(readDiff).mockResolvedValue({
      ...DIFFERENCE,
      claims: {
        H: {
          target: "H",
          state: "unchanged",
          before: 0.3,
          after: 0.3,
          delta: 0,
          agreement: null,
          moved_only_by_reweighting: false,
          unchanged_because: null,
        },
      },
    } as unknown as Diff);

    const change = await new ApiWorldSource().readDiff({ baseId: "example", branch: BRANCH });
    expect(change.claims.get("H")?.moved?.unchangedBecause).toBeUndefined();
  });

  it("test_the_chain_product_stays_an_absence_that_says_why", async () => {
    const world = await new ApiWorldSource().readWorld({ baseId: "example" });
    for (const claim of world.claims) {
      // Nothing on a world is a chain multiplied out, and this half of the
      // product is forbidden from multiplying one — so the slot says exactly
      // that rather than being filled in.
      expect(claim.pathProduct.reading).toBeUndefined();
      expect(claim.pathProduct.absence?.reason).toContain("the engine does not carry one yet");
    }
  });
});
