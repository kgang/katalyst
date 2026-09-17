/**
 * What the canvas draws, written by hand rather than generated.
 *
 * This is the browser's own view of one world — a map with its numbers filled
 * in — and it is deliberately **not** taken from `src/api/schema.ts`. That file
 * is generated from the server's description of itself, and the routes that
 * serve a computed world are being written at the same time as this canvas. If
 * the canvas typed itself against those routes it could not be built until they
 * existed, and it would have to be rewritten every time they changed shape.
 *
 * The rule that shapes everything below: **every slot where a likelihood would
 * go is optional.** A number nobody has computed is not a zero and not a blank;
 * it is an absence, and an absence carries the reason it is absent — "no
 * market", "no engine yet", or a dash inviting the reader's own number. That is
 * the whole of the traceability rule as it reaches this layer: nothing on
 * screen may be a number nobody can account for.
 *
 * Nothing in this file, or anywhere under `src/world`, does arithmetic on a
 * likelihood. Numbers arrive from the server and are carried, unchanged and at
 * full precision, to the moment they are printed.
 */

/** What a claim is for. Its shape on the canvas carries this, never its colour. */
export type ClaimKind = "hypothesis" | "event" | "market" | "not_tradeable";

/**
 * How a push behaves when its cause goes away. `trigger` is a toppled domino —
 * it stays toppled. `sustain` is an apple on a desk — take the desk away and
 * the apple falls.
 */
export type LinkMode = "trigger" | "sustain";

/** Whose number this is. The three are never averaged into one. */
export type BeliefOwner = "model" | "user" | "market";

/**
 * A likelihood and the range around it, both at full precision.
 *
 * The range says **how sure we are of the number** — not how much the world can
 * move. How much the world can move is already inside `p`. Rounding to two
 * significant figures happens once, at the moment of display, and never here.
 */
export interface Ranged {
  /** How likely the claim is to come out true, from 0 to 1. */
  readonly p: number;
  /** The bottom of the range around `p`. Never above it. */
  readonly lo: number;
  /** The top of the range around `p`. Never below it. */
  readonly hi: number;
}

/**
 * A number that is not here, and why.
 *
 * `words` is what the reader sees where the number would have been — "no
 * market", "no engine yet", or a dash. `reason` is the sentence that says why,
 * so no slot on screen is ever merely empty.
 */
export interface Absence {
  /** What is printed where the number would be. Never blank, never a zero. */
  readonly words: string;
  /** Why there is no number, in plain words. */
  readonly reason: string;
}

/**
 * One slot where a likelihood belongs.
 *
 * `reading` is optional — every number slot in this view model is — and when it
 * is missing, `absence` is present and says why. The two halves are written as
 * a choice between two shapes so that the type itself forbids an empty slot
 * with no reason attached.
 */
export type Slot =
  | { readonly reading: Ranged; readonly absence?: undefined }
  | { readonly reading?: undefined; readonly absence: Absence };

/** The three voices on one claim, each in its own slot, never merged. */
export interface BeliefSlots {
  /** What the model thinks. */
  readonly model: Slot;
  /** What the reader thinks. Absent until they say. */
  readonly user: Slot;
  /** What a venue is pricing. Absent when no venue quotes this claim. */
  readonly market: Slot;
}

/**
 * What kind of push an arrow carries over time.
 *
 * `impulse` is a one-time spike that fades away by its own half-life. `step`
 * switches on and holds. `ramp` climbs from nothing to full size across the
 * delay and then holds. The wire's stroke pattern says which, and it is the
 * only thing the stroke says.
 */
export type LinkShape = "impulse" | "step" | "ramp";

/**
 * Where an arrow and its number came from — a receipt our own pipeline writes,
 * never something a model says about itself.
 *
 * Seven values, drawn on the map as a mark of one, two or three dots at the
 * arrow's tail, with the exact word beside the same mark in the panel.
 */
export type Provenance =
  | "documented"
  | "historical"
  | "market_implied"
  | "argued"
  | "user"
  | "asserted"
  | "simulated";

/** One published item behind an arrow, and the day we fetched it — or that nobody did. */
export interface SourceView {
  /** Where the reader goes to check it. */
  readonly url: string;
  /** What the reader will see when they get there, in the publisher's words. */
  readonly title: string;
  /** The host name the address points at, with any leading `www.` dropped. */
  readonly host: string;
  /** The day our own retrieval step fetched it, or the reason there is no day. */
  readonly retrieved: { readonly day: string } | { readonly absence: Absence };
}

/** How often this kind of thing has happened before, when there is an honest set to count. */
export interface BaseRateView {
  /** The set of past cases being counted, stated so somebody else could recount them. */
  readonly referenceClass: string;
  /** How many cases in that set came out true. */
  readonly k: number;
  /** How many cases are in the set altogether. */
  readonly n: number;
  /** Web addresses where the count can be checked. Empty means nobody has checked it. */
  readonly sources: readonly SourceView[];
}

/** One published item for or against a claim, as the tile shows it. */
export interface EvidenceClipping {
  /** What the source says, in one sentence, in our words. */
  readonly line: string;
  /**
   * A single letter standing for the publication, taken from the host name in
   * the source's own web address — `bbc.com` gives `B`.
   *
   * A letter rather than the publication's icon, on purpose: fetching an icon
   * is a request to somebody else's server, and the packaged demo draws its
   * first frame without making one.
   */
  readonly monogram: string;
  /** The host name the monogram came from, so the letter can be accounted for. */
  readonly host: string;
  /** `1` when the item supports the claim, `-1` when it cuts against it. */
  readonly direction: 1 | -1;
  /** Where to read it, so the reader can check us. */
  readonly url: string;
}

/**
 * A word shown where a likelihood would go.
 *
 * While the reader has supposed a claim true it is true in every simulated
 * world, so there is no number to show and inventing one would answer a
 * question nobody asked. The tile shows *Supposed · Oct 1* instead. Nothing in
 * this pull request produces one — the buttons that do arrive later — but the
 * chip can already render it, and its test proves it.
 */
export interface Standing {
  /** The words, such as "Supposed · Oct 1". */
  readonly words: string;
  /** Why the claim stands this way, for the reader who asks. */
  readonly reason: string;
}

/** One claim, as a tile draws it. */
export interface ClaimView {
  /** The claim's identifier on the map. */
  readonly id: string;
  /** The claim in one sentence, as a person would say it out loud. */
  readonly claim: string;
  /** What this claim is for. Carried on the tile by its shape. */
  readonly kind: ClaimKind;
  /** The day the claim is settled by, as the server wrote it: `2026-11-01`. */
  readonly resolvesBy: string;
  /** Who or what applies the test that settles it. */
  readonly resolutionSource: string;
  /**
   * The test itself, written so that two people reading it would agree on the
   * answer. Too long for a tile; the panel beside the map prints it in full.
   */
  readonly resolutionCriteria: string;
  /**
   * The model's likelihood for this claim before its causes are taken into
   * account. Never drawn on a tile — a second number beside the model's would
   * be a fourth voice — and always drawn in the panel, where the decomposition
   * starts from it.
   */
  readonly prior: Ranged;
  /** How often this kind of thing has happened before, or the reason there is no such count. */
  readonly baseRate: { readonly reading: BaseRateView } | { readonly absence: Absence };
  /** The three likelihoods, side by side. */
  readonly beliefs: BeliefSlots;
  /** At most two published items, for and against. What the tile has room for. */
  readonly evidence: readonly EvidenceClipping[];
  /**
   * Every published item on this claim, in the order the map stores them.
   *
   * The tile shows two; the panel shows all of them, because a claim you can
   * only see half the evidence for is a claim you cannot argue with.
   */
  readonly evidenceInFull: readonly EvidenceClipping[];
  /**
   * The multiplied-out likelihood of the steps of one route from the
   * hypothesis to this claim.
   *
   * A chain of four plausible steps is not a plausible chain, and this is the
   * number that says so. It arrives **on the world**, computed by the engine.
   * Nothing in the browser multiplies anything to fill it in, and the slot holds
   * its absence until the engine can answer.
   */
  readonly pathProduct: Slot;
  /** A word shown instead of a likelihood, when the claim is standing on the reader's say-so. */
  readonly standing?: Standing;
}

/** One arrow, as a wire draws it. */
export interface LinkView {
  /** The arrow's identifier: its two ends joined, such as `H->B`. */
  readonly id: string;
  /** The claim the arrow starts at. */
  readonly source: string;
  /** The claim the arrow ends at. */
  readonly target: string;
  /** Whether the push survives its cause going away. */
  readonly mode: LinkMode;
  /**
   * How hard this arrow pushes, signed, at full precision.
   *
   * It is signed **on the claim, not on the world**. The arrow into *Brent
   * settles below $68* is `+1.6` — positive, because it makes that claim come
   * out true more often — and the thing that claim describes is a *falling*
   * price. So a push's sign is not a direction of financial effect, it never
   * takes a direction hue, and it is carried by the printed sign and a word.
   *
   * Nothing on the canvas adds one of these to anything. Choosing a stroke
   * width or a word for it is a comparison against fixed thresholds.
   */
  readonly strength: number;
  /** Days from the cause becoming true to the push reaching full size. */
  readonly lag: number;
  /** What the push does over time. The wire's stroke pattern, and nothing else. */
  readonly shape: LinkShape;
  /** Days for an `impulse` push to fall to half its size. Absent on the other two shapes. */
  readonly halfLife: number | null;
  /** The mechanism in one to three plain sentences: why this cause moves this effect. */
  readonly rationale: string;
  /** What backs the arrow, each with the day it was fetched or the reason there is none. */
  readonly sources: readonly SourceView[];
  /** Where this arrow came from. Drawn as a mark at the tail, spelled out in the panel. */
  readonly provenance: Provenance;
  /**
   * The target's likelihood with this arrow's source supposed true.
   *
   * Not computed here and not carried on the world: it costs a whole extra
   * run of the map per arrow, so the engine works one out only when a wire is
   * asked about. Until then — and always, in this build, because that route
   * does not exist yet — the slot holds its absence and the wire's chip reads
   * the push back in words instead. Never a guessed number.
   */
  readonly conditional: Slot;
  /**
   * True when this arrow is a market feeding back on the world. A feedback
   * arrow is the one arrow allowed to close a loop, and it is set aside when
   * the map is sorted into layers — otherwise there would be no left-to-right
   * order to sort it into.
   */
  readonly reflexive: boolean;
}

/**
 * One world: a map with its numbers as they stand.
 *
 * "As they stand" is doing real work. In this pull request the numbers are the
 * stored example's own, read from the fixture route. When the engine's world
 * route lands they will be computed, and the slots that read as absences today
 * will fill in. Nothing here has to change for that to happen, because nothing
 * false was written.
 */
export interface WorldView {
  /** Which stored example or map this world was built from. */
  readonly baseId: string;
  /** What the map is called on screen. */
  readonly title: string;
  /** The claim the reader started from. */
  readonly hypothesisId: string;
  /** Every claim on the map. */
  readonly claims: readonly ClaimView[];
  /** Every arrow on the map. */
  readonly links: readonly LinkView[];
  /**
   * How many versions of the map the engine ran to produce these numbers.
   *
   * Absent when nothing was computed — which is every world in this build,
   * because the engine's route does not exist yet. It is the one thing that
   * tells a belief chip whether its range was *computed* across many versions
   * of the map or merely *stated* by whoever wrote the number down, and the
   * chip says a different sentence for each. Nothing else reads it.
   */
  readonly versions?: number;

  /**
   * Where these numbers came from, in one sentence a reader can check.
   *
   * It is printed under the map. A world whose numbers cannot say where they
   * came from is exactly the state this product refuses to show.
   */
  readonly origin: string;
}

/** Which world to read: a base map, optionally with a branch applied. */
export interface WorldRequest {
  /** The stored example or map to read. */
  readonly baseId: string;
  /** The branch to apply. Left out, this is the base world. */
  readonly branchId?: string;
}
