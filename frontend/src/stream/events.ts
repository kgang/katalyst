/**
 * The eight things that travel down a generation, as the browser types them.
 *
 * Written by hand, exactly as `WorldView` was, because the server's description
 * of itself and this canvas are built at the same time. The server's own copy is
 * `backend/src/katalyst/engine/events.py`; a later pull request pins the two
 * against each other with a type-level test, so that neither can drift.
 *
 * **Field names are the wire's, in full.** `input_tokens`, not `inputTokens`. A
 * second spelling of a field is a second thing that can drift, and these come
 * straight off the stream and are printed straight onto the screen. The browser's
 * own view model, `WorldView`, keeps its own spellings because it is a different
 * thing with a different life.
 *
 * **Two facts the eight deliberately do not carry twice.** Whether a destination
 * was reached is on the verdict and nowhere else — the reason a *generation*
 * stopped is a different question with a different answer. And whether the run
 * was live or played back, the day a recording was made and the fingerprint of
 * the prompt are on the receipt and nowhere else. Two places to read one fact
 * eventually disagree.
 *
 * **One fact they do carry twice, and it is not the same mistake.** The set of
 * claims still open rides on both growth events. It is not one fact worked out
 * two ways; it is one fact restated after every change to it, so that whichever
 * event arrives is enough on its own to redraw the reserved rectangles.
 */

import type { components } from "../api/schema";
import type { Ranged } from "../world/types";

/** An identifier the engine minted for a claim. Nothing in the browser ever makes one. */
export type PropositionId = string;

/** One claim, exactly as the rules layer writes one. */
export type Proposition = components["schemas"]["Proposition"];

/** One arrow, exactly as the rules layer writes one. */
export type Link = components["schemas"]["Link"];

/** One rule broken, with the rule's own code and the rule's own sentence. */
export type Violation = components["schemas"]["Violation"];

/** One finished world: a map with every likelihood worked through it. */
export type World = components["schemas"]["World"];

/** The run has started. The first thing that arrives, and it arrives at once. */
export interface GenerationStarted {
  readonly event: "generation_started";
  /** The engine's name for this run. What the transcript is asked for by. */
  readonly generation_id: string;
  /**
   * The seed every random draw in this run came from — always a number here,
   * even when the request left it out. Whoever chose it, this event is where the
   * browser reads it: the one the request sent, or the one the engine minted when
   * it sent none, or, on a replay, the one in the recording's header, which wins
   * over both. The browser prints what this says and never works out which case
   * it was.
   */
  readonly seed: number;
  /**
   * The same seed, exactly as it was written on the wire.
   *
   * **Put here by the reader, not by the server**, like the `event` field above
   * — and for a reason worth writing down. A seed is a whole number the engine
   * draws with, and it can be nineteen digits long; JavaScript holds a whole
   * number exactly only up to sixteen, so `seed` above is already rounded by the
   * time any code here sees it. The run this build was first watched on drew with
   * 4 803 646 386 380 448 080, and the browser's own reading of that ends 000.
   *
   * The browser never computes with a seed — it prints it, so that a reader can
   * ask for the same map again — so the honest thing to print is the digits that
   * came off the wire. Absent only when a reader handed the events over by hand
   * rather than reading them from a stream.
   */
  readonly seed_as_written?: string;
  /** The sentence the reader typed, in their own words. */
  readonly hypothesis: string;
  /** The Verify door's destination, in their words. Null when they used the Explore door. */
  readonly target: string | null;
}

/** One proposal the rules accepted. A claim, its incoming arrows, or both. */
export interface ProposalAccepted {
  readonly event: "proposal_accepted";
  /** Where this sits in the transcript, counting from 0. */
  readonly at: number;
  /** The new claim, with its identifier minted by the engine. Null for an arrows-only proposal. */
  readonly proposition: Proposition | null;
  /** Its incoming arrows, identifiers minted by the engine. */
  readonly links: readonly Link[];
  /** The claims still open to expand. What the reserved rectangles are drawn from. */
  readonly frontier: readonly PropositionId[];
}

/** One proposal the rules refused. An event, never an error. */
export interface ProposalRejected {
  readonly event: "proposal_rejected";
  readonly at: number;
  /** What the model wrote. Never minted, never drawn as a tile, only ever quoted. */
  readonly claim_in_words: string;
  /** The validator's own codes and its own sentences. One per rule broken. */
  readonly violations: readonly Violation[];
  /**
   * The claims still open to expand — the same field the accepted event carries,
   * and for the same reason. A claim closed by its third refusal in a row leaves
   * the frontier on this event, so its rectangle comes down at once instead of
   * standing there waiting for something that is not coming.
   */
  readonly frontier: readonly PropositionId[];
}

/** Every number, worked through the finished map, once. */
export interface BeliefsPropagated {
  readonly event: "beliefs_propagated";
  readonly world: World;
}

/** The Verify door's answer. Emitted only when the reader named a destination. */
export interface Verdict {
  readonly event: "verdict";
  readonly kind: "reached" | "no_path";
  /** The steps of the path, in order. Empty on `no_path`. */
  readonly path: readonly PropositionId[];
  /** The multiplied-out likelihood of those steps. Null on `no_path`. */
  readonly product: number | null;
  /** On `no_path`: the closest claim the map did reach. */
  readonly nearest: PropositionId | null;
  /** One plain sentence, the engine's own. */
  readonly why: string;
}

/** What the run cost. */
export interface Receipt {
  readonly event: "receipt";
  readonly model: string;
  readonly calls: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly cache_read_tokens: number;
  /**
   * How many web searches this run made. Billed apart from tokens, so `dollars`
   * cannot be accounted for without it — which is why it is a field of its own
   * rather than something a reader is expected to infer.
   */
  readonly searches: number;
  readonly dollars: number;
  readonly seconds: number;
  /** Live, or played from a recording. The only place in the stream this is said. */
  readonly mode: "live" | "replay";
  /** The day the recording was made, as the map writes a day: `2026-09-18`. Null when live. */
  readonly recording_date: string | null;
  /** A fingerprint of the prompt this run was made against. Always known. */
  readonly prompt_hash: string;
}

/** Why the generation stopped. Not whether the Verify door found anything — that is the verdict. */
export interface Done {
  readonly event: "done";
  readonly reason: StopReason;
  readonly claims: number;
  readonly links: number;
  readonly rejected: number;
}

/** The seven reasons a generation stops. There is no eighth, and none of them is `no_path`. */
export type StopReason =
  | "reached_terminal"
  | "depth_cap"
  | "width_cap"
  | "claim_cap"
  | "spend_cap"
  | "refusal_cap"
  | "no_terminal";

/** The run broke. One plain sentence, never a stack trace. */
export interface Failed {
  readonly event: "failed";
  readonly message: string;
}

/** Any one of the eight. The `event` field is what a `switch` walks. */
export type StreamEvent =
  | GenerationStarted
  | ProposalAccepted
  | ProposalRejected
  | BeliefsPropagated
  | Verdict
  | Receipt
  | Done
  | Failed;

/** The eight names, so a reader can tell one it knows from one it does not. */
export const EVENT_NAMES: readonly StreamEvent["event"][] = [
  "generation_started",
  "proposal_accepted",
  "proposal_rejected",
  "beliefs_propagated",
  "verdict",
  "receipt",
  "done",
  "failed",
];

/**
 * An event whose name this build does not know.
 *
 * It is a shape of its own rather than a hole in the union: the reader has to
 * hand something back for every line on the wire, and a name with a payload
 * nobody can read is still a thing that happened. What is done with one is the
 * reducer's business — count it, change nothing else, and say so in the
 * transcript.
 */
export interface UnknownEvent {
  readonly event: "unknown";
  /** The name the wire carried. */
  readonly name: string;
}

/** Everything the reader can hand back: one of the eight, or a name it does not know. */
export type ReadEvent = StreamEvent | UnknownEvent;

/** What the browser asks for when it asks for a map. */
export interface GenerateRequest {
  /**
   * The sentence the reader typed — and, with no key, the whole of how the server
   * knows which recording to play. Required, and never empty.
   */
  readonly hypothesis: string;
  /** The Verify door's destination, in the reader's words. Absent is the Explore door. */
  readonly target?: string;
  /** The reader's own likelihood on the hypothesis. Absent when they chose "I don't know". */
  readonly user_belief?: Ranged;
  /**
   * Only when reproducing a run we were handed a seed for.
   *
   * **The browser does not invent one.** With none, the engine mints one and the
   * first event says which, so the run is reproducible from the moment it starts
   * and the number on screen is still the engine's.
   */
  readonly seed?: number;
}
