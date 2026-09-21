/**
 * The worked run from `spec/workbench/streaming-growth.md`, written out as the
 * events a browser would read.
 *
 * It is the Hormuz run the chapter walks call by call: the strait reopens, the
 * war-risk premium falls, a talks-resume ending that is not tradeable, Brent
 * settles below $68, a second arrow into Brent with no claim at all, two
 * tradeable endings, and one proposal the rules refused for closing a loop.
 *
 * **No number here is a measurement of a generation.** Nothing has been run
 * against a model, so there is nothing to have measured. The likelihoods on the
 * proposals are the model's *stated* ones, which is what a proposal carries, and
 * the world at the end carries each claim's own stated number straight through —
 * so that a test can say *the chips were absent and then they were the world's*
 * by comparing the screen with the world it handed in, never with a figure
 * somebody wrote down. **No test in this folder asserts a value.**
 *
 * The stream is built from ordinary data rather than pasted as JSON so that the
 * day the eight shapes change, this stops compiling rather than quietly testing
 * yesterday's shapes.
 */

import type { components } from "../../api/schema";
import type {
  BeliefsPropagated,
  Done,
  GenerationStarted,
  Link,
  ProposalAccepted,
  ProposalRejected,
  Proposition,
  Receipt,
  StreamEvent,
  Verdict,
  World,
} from "../events";

type Belief = components["schemas"]["Belief"];

/** The sentence the reader types, exactly as a person would type it. */
export const THE_SENTENCE = "The Strait of Hormuz is going to open next week.";

/** The destination a reader names at the Verify door, in their own words. */
export const THE_DESTINATION = 'the Polymarket contract "Brent below $70 on 2026-10-31"';

/** One likelihood the model stated for a claim it proposed. Never a computed one. */
function stated(p: number, lo: number, hi: number): Belief {
  return { p, lo, hi, owner: "model" };
}

/** One claim, in the shape the engine mints one. */
function claim(
  id: string,
  words: string,
  kind: Proposition["kind"],
  belief: Belief,
  over: Partial<Proposition> = {},
): Proposition {
  return {
    id,
    claim: words,
    kind,
    resolution: {
      criteria: `Whether ${words.replace(/\.$/, "")}, judged as the source below judges it.`,
      source: "Lloyd's List",
      by: "2026-11-01",
    },
    prior: belief,
    beliefs: { model: belief },
    evidence: [],
    ...over,
  };
}

/** One arrow, in the shape the engine mints one. */
function arrow(source: string, target: string, over: Partial<Link> = {}): Link {
  return {
    id: `${source}->${target}`,
    source,
    target,
    mode: "trigger",
    strength: 1.6,
    lag: 2,
    shape: "step",
    rationale: `Why ${source} moves ${target}, in the model's own words.`,
    sources: [],
    provenance: "argued",
    reflexive: false,
    ...over,
  };
}

/** The claim the reader's own sentence became. */
export const H = claim(
  "H",
  "The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days",
  "hypothesis",
  stated(0.35, 0.2, 0.49),
);

/** The war-risk premium falling. */
export const C = claim(
  "C",
  "Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%",
  "event",
  stated(0.42, 0.27, 0.58),
);

/** An ending with nothing to trade. It never joins the frontier. */
export const N1 = claim(
  "N1",
  "Omani-mediated United States-Iran talks resume publicly",
  "not_tradeable",
  stated(0.3, 0.16, 0.45),
  { not_tradeable_reason: "No venue quotes whether talks resume." },
);

/** Brent settling below $68. */
export const B = claim(
  "B",
  "Brent crude settles below $68 for five sessions",
  "event",
  stated(0.46, 0.3, 0.62),
);

/** A tradeable ending: the contract the Verify door asks about. */
export const M1 = claim(
  "M1",
  'A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES',
  "market",
  stated(0.51, 0.34, 0.68),
  {
    payoff: {
      kind: "contract",
      venue: "Polymarket",
      contract_id: "brent-below-70-2026-10-31",
      title: "Brent below $70 on 2026-10-31",
      side: "yes",
    },
  },
);

/** A second tradeable ending. */
export const M2 = claim(
  "M2",
  "The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days",
  "market",
  stated(0.39, 0.24, 0.55),
  { payoff: { kind: "price", instrument: "XLE", direction: "short", move: 0.03 } },
);

/** Every claim the run accepts, in the order it accepts them. */
export const EVERY_CLAIM: readonly Proposition[] = [H, C, N1, B, M1, M2];

/** Every arrow the run accepts, in the order it accepts them. */
export const EVERY_ARROW: readonly Link[] = [
  arrow("H", "C", { mode: "sustain" }),
  arrow("H", "N1", { lag: 10 }),
  arrow("C", "B", { mode: "sustain" }),
  arrow("H", "B"),
  arrow("B", "M1", { lag: 1 }),
  arrow("B", "M2", { lag: 3 }),
];

/** The run has started. */
export const STARTED: GenerationStarted = {
  event: "generation_started",
  generation_id: "gen_worked_run",
  seed: 20261001,
  hypothesis: THE_SENTENCE,
  target: null,
};

/** One accepted proposal, at its own place in the working. */
function accepted(
  at: number,
  proposition: Proposition | null,
  links: readonly Link[],
  frontier: readonly string[],
): ProposalAccepted {
  return { event: "proposal_accepted", at, proposition, links, frontier };
}

/**
 * The one refusal, with the validator's own sentence.
 *
 * Read on its own the model's sentence is reasonable; added to the map it closes
 * a loop, because the arrow the other way is already there. The message is the
 * validator's, word for word, and the rule's code is carried but never drawn.
 */
export const REFUSED: ProposalRejected = {
  event: "proposal_rejected",
  at: 6,
  claim_in_words: "cheaper crude reduces the incentive to close the strait",
  violations: [
    {
      code: "cycle",
      subject: "B->H",
      message:
        "These claims form a loop with no delay in it. Mark the arrow where a market feeds back " +
        "on the world as reflexive and give it a delay, or remove one arrow.",
    },
  ],
  frontier: ["C", "B"],
};

/** The eight growth events, in the order the chapter walks them. */
export const THE_GROWTH: readonly StreamEvent[] = [
  STARTED,
  accepted(0, H, [], ["H"]),
  accepted(1, C, [EVERY_ARROW[0] as Link], ["H", "C"]),
  accepted(2, N1, [EVERY_ARROW[1] as Link], ["H", "C"]),
  accepted(3, B, [EVERY_ARROW[2] as Link], ["H", "C", "B"]),
  // No claim at all: one new arrow between two claims already on the map. The
  // strait reaches its full width here and closes, so it leaves the frontier.
  accepted(4, null, [EVERY_ARROW[3] as Link], ["C", "B"]),
  accepted(5, M1, [EVERY_ARROW[4] as Link], ["C", "B"]),
  REFUSED,
  accepted(7, M2, [EVERY_ARROW[5] as Link], ["C", "B"]),
];

/**
 * The world the engine works through the finished map.
 *
 * Every likelihood in it is the claim's own stated one, carried straight
 * through. **That is not a claim about what an engine would compute** — nothing
 * has been run — and no test reads a value out of it. What the tests do with it
 * is compare the screen against this world: the chips were absent, and then they
 * were whatever this said.
 */
export function theWorld(
  claims: readonly Proposition[] = EVERY_CLAIM,
  links: readonly Link[] = EVERY_ARROW,
): World {
  const beliefs: Record<string, Belief> = {};
  const series: Record<string, number[]> = {};
  const states: Record<string, string[]> = {};
  for (const one of claims) {
    beliefs[one.id] = one.beliefs.model;
    series[one.id] = [one.beliefs.model.p];
    states[one.id] = ["pushed"];
  }
  return {
    base_id: "gen_worked_run",
    seed: 20261001,
    versions: 2000,
    worlds: 8,
    day_zero: "2026-10-01",
    days: 60,
    graph: {
      id: "gen_worked_run",
      propositions: [...claims],
      links: [...links],
      hypothesis_id: "H",
    },
    assignments: [],
    retractions: [],
    beliefs,
    series_days: [0],
    series,
    states: states as World["states"],
    warnings: [],
  };
}

/** The likelihoods, worked through the finished map, once. */
export const BELIEFS: BeliefsPropagated = { event: "beliefs_propagated", world: theWorld() };

/** What the run cost. Every figure on it is a field, and nothing adds them up. */
export const RECEIPT: Receipt = {
  event: "receipt",
  model: "a-model",
  calls: 9,
  input_tokens: 31_402,
  output_tokens: 8_211,
  cache_read_tokens: 24_880,
  searches: 3,
  dollars: 0.6132,
  seconds: 512.4,
  mode: "live",
  recording_date: null,
  // A live run asks for `medium`, which is the pinned default behind the one
  // setting (Kent, G13). A recording is made at the service's own.
  effort: "medium",
  prompt_hash: "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
};

/** The same receipt, as a replay rebuilds one: nothing called, nothing spent. */
export const REPLAY_RECEIPT: Receipt = {
  ...RECEIPT,
  calls: 0,
  input_tokens: 0,
  output_tokens: 0,
  cache_read_tokens: 0,
  searches: 0,
  dollars: 0,
  mode: "replay",
  recording_date: "2026-09-18",
  effort: "default",
};

/** Why the run stopped, and how big the map ended up. */
export const DONE: Done = {
  event: "done",
  reason: "reached_terminal",
  claims: 6,
  links: 6,
  rejected: 1,
};

/** The whole run, from the first event to the last. */
export const THE_WHOLE_RUN: readonly StreamEvent[] = [...THE_GROWTH, BELIEFS, RECEIPT, DONE];

/** The Verify door's answer when the destination was reached. */
export const REACHED: Verdict = {
  event: "verdict",
  kind: "reached",
  path: ["H", "B", "M1"],
  product: 0.0826,
  nearest: null,
  why: "The story reaches the Polymarket contract in 2 steps, along the best-backed route on this map.",
};

/** The Verify door's answer when nothing on the map reaches the destination. */
export const NO_PATH: Verdict = {
  event: "verdict",
  kind: "no_path",
  path: [],
  product: null,
  nearest: "B",
  why:
    "Nothing on this map reaches a Polymarket contract on European natural gas. The closest " +
    "claim the story does reach is Brent crude settles below $68 for five sessions, 2 arrows " +
    "away from it.",
};
