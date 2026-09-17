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
  /** The three likelihoods, side by side. */
  readonly beliefs: BeliefSlots;
  /** At most two published items, for and against. */
  readonly evidence: readonly EvidenceClipping[];
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
