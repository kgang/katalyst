/**
 * The eight things that travel down a generation, as the browser types them —
 * and, from 2026-09-22, one more that only a live run sends.
 *
 * **The grammar is split in two, and the split is load-bearing.** The eight are
 * what a recording holds, line for line, and everything that reaches the map
 * comes from them. The ninth, `activity`, says what the model is doing inside a
 * call that has not come back yet; it is ephemeral by rule — never recorded,
 * never transcribed, never replayed, never invented by a replay — and it reaches
 * the run strip and nothing else (Kent, R44 and R47, 2026-09-22).
 *
 * Written by hand, exactly as `WorldView` was, because the server's description
 * of itself and this canvas are built at the same time. The server's own copy is
 * `backend/src/katalyst/engine/events.py`.
 *
 * **What pins the two together, and what cannot be pinned.**
 * `frontend/src/stream/__tests__/eventsMatchSchema.test-d.ts` fails the build
 * when this half and the generated `api/schema.ts` disagree — `tsc` is the
 * whole test, so there is nothing to run and nothing to remember to run.
 *
 * It cannot pin the eight **envelopes**, and nothing could: they travel as
 * server-sent events, and OpenAPI describes `text/event-stream` and stops. So
 * it pins them at the joints, which is where drift would actually hurt: every
 * piece an event is built from — `Proposition`, `Link`, `World`, `Violation`,
 * `Belief` — is aliased to the generated type below rather than retyped, so a
 * change to any of them is a compile error here without anybody writing a test.
 * And it pins the four shapes that do travel as JSON: the receipt, the request,
 * the drafted insert and the working.
 *
 * What is left is the eight names and which pieces each carries. The guard for
 * those is the running app — an event name this build does not know is counted
 * and shown (`growth.ts`), which turns a divergence into a number on screen
 * rather than into tiles that quietly never appear — and the server's own test
 * that the stream emits exactly those eight.
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
import type { Likelihood } from "../world/types";

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
  /**
   * How hard the model was asked to try, as a plain word.
   *
   * `default` when nothing was asked for and the service's own applied,
   * otherwise `low`, `medium`, `high`, `xhigh` or `max`. One setting with two
   * pinned defaults behind it: **a recording is made rich and a live run is
   * made fast** (Kent, G13, 2026-09-21), so two maps of the same sentence can
   * differ for a reason that has nothing to do with the sentence — and a reader
   * of a map is entitled to know which this was.
   *
   * It is a plain word rather than a number because it is the word the service
   * takes, and a number would be this browser translating one thing into
   * another and printing the translation.
   */
  readonly effort: string;
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

/** Which of the three things the model was doing when it said so. */
export type ActivityKind = "searching" | "found" | "thinking";

/**
 * The ninth kind of line: what the model is doing **right now**.
 *
 * **It is not one of the eight, and the split is the whole point.** The eight
 * above are what a recording holds, line for line, and a replay is those eight
 * played back. This one is sent on a live run and is never written to a
 * recording, never written to a transcript, never replayed, never invented by a
 * replay, never counted by the `at` counter and never folded into the map. So a
 * recording is still the real stream line for line, which is what made a ninth
 * event possible at all: the thing it reports does not exist in a replay, the
 * same way the seconds counter's wait does not (Kent, R44 and R47, 2026-09-22).
 *
 * **What it carries is the model's own words and nothing composed by us.** The
 * search it just issued, verbatim; the title of one thing that search returned,
 * verbatim, with the host after it when a host is known; its own summarised
 * thinking, verbatim. There is no progress estimate here, no percentage and no
 * time remaining — the caps those would be worked out from are the server's and
 * are not on the wire.
 *
 * **Where it may be shown is the run strip and nowhere else.** Never on the map,
 * never in the panel, and never inside the polite live region: these lines
 * change every few seconds, and a region that read them out would be reading a
 * stopwatch over the top of the map being built.
 */
export interface Activity {
  readonly event: "activity";
  /**
   * The open claim the model call is working on — one of the identifiers in the
   * latest `frontier` — or null when the call is about no one claim, which is
   * the opening call that proposes the reader's own sentence as a claim.
   */
  readonly about: PropositionId | null;
  /** Which of the three things it is doing. */
  readonly kind: ActivityKind;
  /** The model's own words, verbatim. Never paraphrased, never composed here. */
  readonly text: string;
}

/** The ninth name. Live only, and a recording never holds it. */
export const ACTIVITY_NAME = "activity";

/**
 * The nine names a **live** run may send: the eight a recording holds, and the
 * ephemeral one.
 *
 * The reader matches on this list rather than on the eight, because a name that
 * is not on it comes back as *a name this build does not know* and is counted
 * on screen — which is the right answer for a server that has learned a tenth
 * word and the wrong one for a word this build knows perfectly well.
 */
export const NAMES_A_LIVE_RUN_MAY_SEND: readonly (StreamEvent | Activity)["event"][] = [
  ...EVENT_NAMES,
  ACTIVITY_NAME,
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
  /**
   * True when the **name** was one of the eight and its payload could not be
   * read.
   *
   * Two different things end up here, and a screen that told a reader they were
   * the same would be telling them something false. *This build has no name for
   * that* is a browser older than its server, and the map it drew is a correct
   * map of the events it understood. *This build knows that name and could not
   * read what came with it* is a broken line on the wire, and the map may be
   * missing a claim — which is a different thing to be told, and a worse one.
   */
  readonly unreadable?: boolean;
}

/**
 * Everything the reader can hand back: one of the eight, the ephemeral ninth, or
 * a name it does not know.
 */
export type ReadEvent = StreamEvent | Activity | UnknownEvent;

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
  readonly user_belief?: Likelihood;
  /**
   * Only when reproducing a run we were handed a seed for.
   *
   * **The browser does not invent one.** With none, the engine mints one and the
   * first event says which, so the run is reproducible from the moment it starts
   * and the number on screen is still the engine's.
   */
  readonly seed?: number;
  /**
   * How this run starts: `live` calls a model, `replay` plays the committed
   * recording of this sentence back.
   *
   * **The caller says which, and the server never chooses** (record 0012,
   * amended 2026-09-21). Left out, the server plays a recording, because a
   * request that did not ask to spend money must never spend it.
   */
  readonly start?: "replay" | "live";
}
