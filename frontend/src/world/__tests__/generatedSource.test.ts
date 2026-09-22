/**
 * What the source for a generated map must do, and what it must never do.
 *
 * A map somebody watched build itself is not in the store of examples: the
 * server is holding it in memory, under the identifier it minted for it, for the
 * life of its own process. So the one thing this source must never do is go
 * looking for it at the route that hands out the stored examples — that request
 * can only 404, and a 404 there would read on screen as *your edit could not be
 * worked out* rather than as *this map was never stored*.
 *
 * What it must do is ask the same three routes the stored map is asked of, with
 * the map's own identifier and **the run's own seed**. The seed is the one that
 * would go wrong quietly: a world built from another seed is a different world,
 * and the map a branch was folded onto would stop being the map the reader
 * watched arrive, with nothing on screen to say so.
 *
 * **The server is replaced by a stand-in.** Its answers are the shapes the
 * engine produces; no test here asserts that any number in them is right, which
 * is the engine's own tests' job.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Diff, World } from "../../api/client";
import { GeneratedMapSource } from "../generatedSource";
import type { BranchView, ClaimView } from "../types";

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

/** The identifier the engine minted for the map this run built. */
const THE_MAP = "01M2QYMDG3QNFECTM3W1J5C0MM";

/** The seed the run drew with, as the engine reported it. */
const THE_SEED = 4803646386380448;

/** One claim as the server writes one, with only what these tests read filled in. */
function proposition(id: string, over: Record<string, unknown> = {}) {
  return {
    id,
    claim: `${id} — a claim that will be true or false by a date.`,
    kind: "event",
    resolution: { criteria: "Checkable.", source: "A named source.", by: "2026-11-01" },
    prior: { p: 0.3, lo: 0.1, hi: 0.5, owner: "model" },
    beliefs: { model: { p: 0.3, lo: 0.1, hi: 0.5, owner: "model" }, user: null, market: null },
    base_rate: null,
    evidence: [],
    payoff: null,
    not_tradeable_reason: null,
    ...over,
  };
}

/** One world as the engine builds one, for the map above. */
const A_WORLD = {
  base_id: THE_MAP,
  branch_id: null,
  seed: THE_SEED,
  versions: 2000,
  worlds: 8,
  day_zero: "2026-09-17",
  days: 45,
  graph: {
    id: THE_MAP,
    hypothesis_id: "H",
    propositions: [proposition("H", { kind: "hypothesis" }), proposition("S")],
    links: [],
  },
  assignments: [],
  retractions: [],
  beliefs: {
    H: { p: 0.3, lo: 0.1, hi: 0.5, owner: "model" },
    S: { p: 0.4, lo: 0.2, hi: 0.6, owner: "model" },
  },
  series_days: [0],
  series: { H: [0.3], S: [0.4] },
  states: { H: ["pushed"], S: ["pushed"] },
  warnings: [],
} as unknown as World;

/** The engine's difference, with one ranked row. */
const A_DIFFERENCE = {
  base_id: THE_MAP,
  branch_a: null,
  branch_b: "br-mine",
  claims: { S: { state: "shifted", before: 0.4, after: 0.5, delta: 0.1, agreement: 0.9 } },
  rows: [
    {
      target: "S",
      before: 0.4,
      after: 0.5,
      peak_delta: 0.1,
      at_day: 3,
      range_width: 0.2,
      agreement: 0.9,
      rank: 0.09,
    },
  ],
  summary: "One ending moved.",
  warnings: [],
} as unknown as Diff;

/** The claims the screen watched arrive, in the shape the canvas draws them. */
const WATCHED_ARRIVE = [
  { id: "H", claim: "The first claim." },
  { id: "S", claim: "Something it would cause." },
] as unknown as readonly ClaimView[];

/** One branch of the reader's own, in the shape that goes over the wire. */
const MY_BRANCH = {
  id: "br-mine",
  label: "Suppose the first claim",
  hue: 1,
  edits: [],
  claims: [],
  wire: {
    id: "br-mine",
    label: "Suppose the first claim",
    parent: null,
    interventions: [{ kind: "do", target: "H", value: true, at: "2026-09-17" }],
  },
} as unknown as BranchView;

/** The source under test, told what the screen watched arrive. */
function theSource(): GeneratedMapSource {
  return new GeneratedMapSource({
    id: THE_MAP,
    title: "The Strait of Hormuz is going to open next week.",
    seed: THE_SEED,
    claims: WATCHED_ARRIVE,
  });
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("the source for a map this program generated", () => {
  it("test_every_question_names_the_generated_map_and_the_runs_own_seed", async () => {
    vi.mocked(readWorld).mockResolvedValue(A_WORLD);
    vi.mocked(readDiff).mockResolvedValue(A_DIFFERENCE);
    vi.mocked(readConditional).mockResolvedValue({ p: 0.5, lo: 0.4, hi: 0.6, owner: "model" });

    const source = theSource();
    await source.readWorld({ baseId: THE_MAP, branch: MY_BRANCH });
    await source.readDiff({ baseId: THE_MAP, branch: MY_BRANCH });
    await source.readConditional({ baseId: THE_MAP, branch: MY_BRANCH, linkId: "H->S" });

    // The map's own name and the run's own seed, on all three. Read off the
    // calls rather than written down twice: these are the two values that would
    // send a reader's edit to a different map without anything saying so.
    for (const call of [
      vi.mocked(readWorld).mock.calls[0],
      vi.mocked(readDiff).mock.calls[0],
      vi.mocked(readConditional).mock.calls[0],
    ]) {
      expect(call?.[0]).toBe(THE_MAP);
    }
    expect(vi.mocked(readWorld).mock.calls[0]?.[2]).toBe(THE_SEED);
    expect(vi.mocked(readDiff).mock.calls[0]?.[2]).toBe(THE_SEED);
    expect(vi.mocked(readConditional).mock.calls[0]?.[2]).toBe(THE_SEED);

    // **And the stored-example route is never asked.** There is no stored
    // example behind this map; asking would turn one honest absence into a 404
    // in the middle of an edit.
    expect(readExample).not.toHaveBeenCalled();
  });

  it("test_the_day_the_window_starts_on_is_the_engines_own", async () => {
    vi.mocked(readWorld).mockResolvedValue(A_WORLD);

    const view = await theSource().readWorld({ baseId: THE_MAP });

    // A generated map's day zero is the day its run happened, and the server is
    // the only thing that knows it — so it is read off the answer rather than
    // worked out here or carried from anywhere else.
    expect(view.today).toBe(A_WORLD.day_zero);
    expect(view.baseId).toBe(THE_MAP);
    expect(view.seed).toBe(A_WORLD.seed);
  });

  it("test_the_sentence_under_the_map_says_how_long_the_map_will_answer", async () => {
    vi.mocked(readWorld).mockResolvedValue(A_WORLD);

    const view = await theSource().readWorld({ baseId: THE_MAP });

    // The one thing true of this map and of no stored one. A reader who comes
    // back to a restarted server and finds the map gone should have been told.
    expect(view.origin).toContain(THE_MAP);
    expect(view.origin).toContain("for as long as the server that built it is running");
    expect(view.origin).toContain("/api/worlds");
  });

  it("test_a_row_of_the_change_list_is_named_from_the_claims_that_arrived", async () => {
    vi.mocked(readDiff).mockResolvedValue(A_DIFFERENCE);

    const change = await theSource().readDiff({ baseId: THE_MAP, branch: MY_BRANCH });

    // A difference carries identifiers and numbers, never words. The words come
    // from the claims the reader watched arrive — which is the only place this
    // source could get them, and the reason it is handed them at all.
    expect(change.rows.map((row) => row.label)).toEqual(["Something it would cause."]);
    expect(change.rows.map((row) => row.claimId)).toEqual(
      A_DIFFERENCE.rows.map((row) => row.target),
    );
  });

  it("test_there_is_no_stored_example_behind_a_generated_map_and_it_says_so", async () => {
    await expect(theSource().readBundle(THE_MAP)).rejects.toThrow(/generated rather than stored/);
    expect(readExample).not.toHaveBeenCalled();
  });
});
