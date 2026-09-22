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
 *
 * **One thing here is taken from the generated description after all, and it is
 * the exception that proves the rule:** a branch, in the shape the server writes
 * one. That shape is not a view of anything — it is what travels back over the
 * wire when a world is asked for — so re-stating it by hand would be writing
 * down the server's own words and waiting for them to drift.
 */

import type { components } from "../api/schema";

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
 * One likelihood, at full precision. **One number, and never a range**
 * *(Kent, 2026-09-22, R48)*.
 *
 * There used to be a bottom and a top beside it, and the pair said how sure we
 * were of the number. They are gone from the screen and from this view model:
 * one claim, one likelihood. The server still writes a `lo` and a `hi` beside
 * every number it sends, because the engine that computes them is being rewritten
 * in another stack; the reader at the wire drops them on the way in, and nothing
 * on this side of the wire has anywhere to put them.
 *
 * Rounding to two significant figures happens once, at the moment of display,
 * and never here.
 */
export interface Likelihood {
  /** How likely the claim is to come out true, from 0 to 1. */
  readonly p: number;
}

/**
 * Which of the five absences this is. It is what picks the words.
 *
 * - `no_engine` — nothing has worked this number through the map yet.
 * - `no_market` — no venue quotes this claim.
 * - `not_said` — nobody has given a number. The one dash on screen with a
 *   meaning: the reader's own empty slot, inviting a number.
 * - `refused` — the engine was asked and **would not** work this number out. It
 *   is its own kind rather than a shade of `no_engine`, because the two are
 *   different facts: *nothing has run yet* invites waiting, and *the engine
 *   turned this down, here is why* invites repairing the thing it turned down.
 *   Reusing one word for both would make the reason on screen the only thing
 *   telling them apart, and a reason is not something code can read back.
 * - `ask_failed` — the engine was asked and one attempt did not come back. It is
 *   the only absence that is not a fact about the map, so it is the only one
 *   that is never kept: ask again and it may well be gone.
 *
 * **The last two are not the same and must not be merged.** A refusal is an
 * answer — the engine looked and said no, and said why — and it will say the
 * same thing every time until the thing it refused is repaired. A failed ask is
 * not an answer at all.
 */
export type AbsenceKind = "no_engine" | "no_market" | "not_said" | "refused" | "ask_failed";

/**
 * A number that is not here, and why.
 *
 * `words` is what the reader sees where the number would have been — "no
 * market", "no engine yet", "not worked out", or a dash. `reason` is the sentence
 * that says why, so no slot on screen is ever merely empty. `kind` is which of
 * the five this is, so that code can tell one absence from another without
 * reading its words back — the dash that invites a number is not the dash that
 * means nothing was computed, and neither of those is a refusal or an ask that
 * did not come back.
 */
/**
 * The mark that says an absence came from the one place absences are made.
 *
 * **It exists only for the compiler.** It is declared and never defined, so
 * nothing is on the object at run time and nothing is carried over a wire — and
 * a hand-built `{ kind, words, reason }` does not compile anywhere but
 * `world/absence.ts`, which is the one module allowed to promise it. The
 * vocabulary says *"these are the words; change them here first"*, and that
 * instruction means nothing while a seventh spelling is one object literal away
 * — as six files proved by holding one each.
 */
declare const WRITTEN_HERE: unique symbol;

export interface Absence {
  /** Which absence this is. */
  readonly kind: AbsenceKind;
  /** What is printed where the number would be. Never blank, never a zero. */
  readonly words: string;
  /** Why there is no number, in plain words. */
  readonly reason: string;
  /** Made by `absence()` or `noReadingAtAll()`, and by nothing else. */
  readonly [WRITTEN_HERE]: true;
}

/**
 * A value we may not have, with the reason standing in its place when we do not.
 *
 * `reading` is optional — every number slot in this view model is — and when it
 * is missing, `absence` is present and says why. The two halves are written as
 * a choice between two shapes so that the type itself forbids an empty slot
 * with no reason attached: there is no way to write one down.
 */
export type Known<T> =
  | { readonly reading: T; readonly absence?: undefined }
  | { readonly reading?: undefined; readonly absence: Absence };

/** The three voices on one claim, each in its own slot, never merged. */
export interface BeliefSlots {
  /** What the model thinks. */
  readonly model: Known<Likelihood>;
  /** What the reader thinks. Absent until they say. */
  readonly user: Known<Likelihood>;
  /** What a venue is pricing. Absent when no venue quotes this claim. */
  readonly market: Known<Likelihood>;
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
  readonly prior: Likelihood;
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
  readonly pathProduct: Known<Likelihood>;
  /** A word shown instead of a likelihood, when the claim is standing on the reader's say-so. */
  readonly standing?: Standing;
  /**
   * What an edit did to this claim, in one word. Absent on a world with no
   * edits behind it — the base map, where nothing has been changed.
   */
  readonly diff?: DiffState;
  /**
   * How far this claim's likelihood moved, when the engine says it moved.
   *
   * Both numbers are the engine's, read on this claim's own resolve-by day, and
   * the browser subtracts nothing: which way it went is the engine's own word.
   * Absent on every claim the engine did not call `shifted`.
   */
  readonly moved?: Movement;
  /**
   * What this claim's tile says about the edits behind it, in order.
   *
   * Two badges in a row read as a sequence: *Supposed · Oct 1* then *Retracted
   * · Oct 2 · by "…"*. Empty on a claim no edit touched.
   */
  readonly badges?: readonly Badge[];
  /**
   * True when this claim is **not** in the world you are looking at.
   *
   * Two worlds are laid out once, together, and painted twice in the same
   * coordinates. A claim that only one of them has is still drawn in the other,
   * faint and dashed, so that flipping between them moves nothing and every
   * difference you see is a real difference rather than a re-layout.
   */
  readonly ghost?: boolean;
}

/**
 * How far a claim's likelihood moved between two worlds, as the engine read it.
 *
 * Both numbers arrive from the engine at full precision and are printed as they
 * came. Which way it went is a word the engine's own reading decides, never a
 * subtraction done here — this half of the product does no arithmetic on the
 * map's numbers, and "is the second bigger than the first" would be the first
 * step down that road.
 */
export interface Movement {
  /** The first world's likelihood, on the claim's own resolve-by day. */
  readonly from: number;
  /** The second world's likelihood, on the same day. */
  readonly to: number;
  /** Which way it went. */
  readonly way: "up" | "down";
  /**
   * How far it moved, as the engine reported it.
   *
   * Carried beside the two readings because a move can be smaller than the
   * second significant figure: when the before and the after print the same,
   * this is the only thing that says anything moved at all.
   */
  readonly by: number;
  /**
   * Why the engine would not call this claim's difference a move, in its own
   * word — **carried, and never printed as it is spelled.**
   *
   * `under_the_floor` says the move is smaller than the engine will report at
   * all, and it is the only word the engine writes. The word is carried rather
   * than dropped because R4 is the older rule and the stronger one: every quiet
   * row on the change list says why, in words, and a row with no reason is what
   * R4 forbids. `graph/diff/noChange.ts` turns it into *barely moved*.
   *
   * **`versions_disagree` is still in the list and is never written**
   * *(2026-09-22; decision record 0028, Kent's row R48)*. It meant the move was
   * far enough to report and the two thousand versions of the map had not agreed
   * on a direction. The engine works out one version now, so a move has one
   * direction and nothing can disagree; the spelling stays here only because the
   * server still declares it, and it leaves both places together in the follow-up
   * that takes down the other constant wire fields. **Nothing reads it.**
   *
   * **Nothing in the browser decides this.** The floor is a constant inside the
   * engine and is on no wire, so the browser can copy the word and cannot re-run
   * the test. Absent on every claim the engine did not call `unchanged`, and on an
   * `unchanged` claim the engine gave no word for.
   */
  readonly unchangedBecause?: "under_the_floor" | "versions_disagree";
}

/**
 * What an edit did to a claim.
 *
 * Four of the five are worked out from the branch alone, with no arithmetic
 * anywhere: following arrows is walking, not calculating.
 *
 * - `added` — the claim arrives in an **Add a claim** edit.
 * - `killed` — the claim is the target of a **Suppose this is false**. Forced
 *   false, full stop. "No path from the hypothesis reaches this any more" is a
 *   fact about a route, and the panel's path bar reports it in those words.
 * - `downstream` — the claim is in the affected set of at least one edit: a
 *   claim your change **can** move. Drawn live, its model number reading its
 *   absence, because nothing has worked the new number out.
 * - `untouched` — everything else. Identical to the base world, and the map can
 *   say so without hedging, because that is a proven property of an edit.
 * - `shifted` — the number moved, with a before and an after. It needs two
 *   numbers to compare, so only the engine ever produces one, and the browser
 *   copies the word across rather than deciding it.
 *
 * **Which of the two readings wins.** Once the engine has answered, its own word
 * is the authority wherever it has one — `added`, `killed` and `shifted` are
 * the engine's. `downstream` and `untouched` stay the browser's, because they
 * answer a different question: *can* your edit reach this claim, rather than
 * *did* its number move. A claim the edit can reach whose number did not move is
 * `downstream`, and saying `untouched` about it would be telling the reader
 * their change cannot reach something it can.
 */
export type DiffState = "added" | "killed" | "downstream" | "untouched" | "shifted";

/**
 * One thing a tile says about an edit behind it — *Added*, *Supposed · Oct 1*,
 * *Retracted · Oct 2 · by "…"*.
 *
 * The words are copied from the shared vocabulary and never paraphrased, and
 * none of the six operations' code names ever appears in one.
 */
export interface Badge {
  /** The words on the badge. */
  readonly words: string;
  /** What the badge means, for the reader who asks. */
  readonly reason: string;
  /**
   * True when this badge says an earlier one no longer holds, so the tile can
   * draw the pair as a sequence with an arrow between them.
   */
  readonly overrides?: boolean;
  /**
   * True when this badge is how far the number moved — `.40 → .30 ▼` — rather
   * than a word about an edit.
   *
   * It sits with the badges because it is what the edits did to this claim, and
   * because the tile already reserves room for whatever they have to say. It is
   * drawn differently: the two readings in the number face with a chevron
   * between the old and the new.
   */
  readonly movement?: boolean;
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
  readonly conditional: Known<Likelihood>;
  /**
   * True when this arrow is a market feeding back on the world. A feedback
   * arrow is the one arrow allowed to close a loop, and it is set aside when
   * the map is sorted into layers — otherwise there would be no left-to-right
   * order to sort it into.
   */
  readonly reflexive: boolean;
  /**
   * What an edit did to this arrow. Absent when no edit touched it.
   *
   * - `added` — an **Add a claim** edit brought it.
   * - `cut` — a supposition cut it: "take this as given, and do not tell me what
   *   caused it". It is still drawn, faint and dashed, because an arrow that
   *   simply vanished would be a change nobody could see.
   * - `retuned` — a **Change this push** edit moved its number.
   */
  readonly change?: "added" | "cut" | "retuned";
  /**
   * True when this arrow is **not** in the world you are looking at. Drawn faint
   * in the same place, so that flipping between the two worlds moves nothing.
   *
   * A ghost arrow is carried by how faint it is and by nothing else. Its stroke
   * is fully spent saying what kind of push it is — dot-dash for a spike that
   * fades, solid for a switch that holds, doubled when the push only lasts while
   * its cause does — and dashing it to say "other world" as well would leave it
   * saying neither clearly.
   */
  readonly ghost?: boolean;
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
  /**
   * The day the map is set on, as the map itself writes it: `2026-10-01`.
   *
   * Every resolve-by date on the map is a span from this day, and an edit the
   * reader makes takes effect on it, so the map reads the same whenever it is
   * opened. The browser's own clock is never consulted: a supposition dated by
   * the reader's time zone would make the same map read differently in two
   * places.
   */
  readonly today: string;
  /**
   * The branch this world has applied, when it has one.
   *
   * Absent on the base world, which is the empty branch. What the branch panel
   * lists, and what every diff state on the claims above was worked out from.
   */
  readonly branch?: BranchView;
  /** The claim the reader started from. */
  readonly hypothesisId: string;
  /** Every claim on the map. */
  readonly claims: readonly ClaimView[];
  /** Every arrow on the map. */
  readonly links: readonly LinkView[];
  /**
   * True when the engine worked these likelihoods out from this map.
   *
   * Absent on a map whose numbers are the stored example's own, written by hand
   * to show the shape of an answer. It is the one thing that tells the two apart,
   * and the panel, the branch list and the line read out to a screen reader each
   * say a different, true sentence for each.
   *
   * **It was a count of versions of the map** *(until 2026-09-22, R48)*. The
   * count was carried here only so that a chip could say whether its range came
   * out of running the map many times or was merely stated; there is no range
   * any more, and the only question left is the one this answers.
   */
  readonly workedOut?: true;
  /**
   * The one number every random draw behind these likelihoods came from.
   *
   * A world is replayable from three things — the map, the branch and this — so
   * it is carried here and named under the map. Absent on a world nobody
   * computed.
   */
  readonly seed?: number;
  /**
   * Plain sentences the engine wanted the reader to see under the map.
   *
   * The engine writes these itself — for instance when an observation leaves it
   * too little to work an answer out from. They are printed as they came and
   * never summarised.
   */
  readonly warnings?: readonly string[];

  /**
   * Where these numbers came from, in one sentence a reader can check.
   *
   * It is printed under the map. A world whose numbers cannot say where they
   * came from is exactly the state this product refuses to show.
   */
  readonly origin: string;
}

/**
 * Which world to read: a base map, optionally with a branch folded onto it.
 *
 * The branch is sent **whole**, not by name, because there is nowhere to keep
 * one yet: the browser holds the branch it built and hands it over with every
 * question. That is also what makes an answer reproducible from three things —
 * the map, the branch and the seed.
 */
export interface WorldRequest {
  /** The stored example or map to read. */
  readonly baseId: string;
  /** The branch to fold. Left out, this is the base world — the empty branch. */
  readonly branch?: BranchView;
}

/** Which two worlds to compare: one map, one seed, one branch against the base world. */
export interface DiffRequest {
  /** The stored example or map both worlds are built from. */
  readonly baseId: string;
  /**
   * The branch the second world has and the first does not.
   *
   * The first world is always the base map with nothing done to it, because
   * that is the comparison the screen offers: the map as it was written against
   * the map with your edits.
   */
  readonly branch: BranchView;
}

/** Which arrow's number is wanted, and in which world. */
export interface ConditionalRequest {
  /** The stored example or map. */
  readonly baseId: string;
  /** The branch to fold first. Left out, the map as it was written. */
  readonly branch?: BranchView;
  /** The arrow whose number is wanted. */
  readonly linkId: string;
}

/** What the engine says happened to one claim between two worlds. */
export interface ClaimChange {
  /** The engine's own word for what happened to it. */
  readonly state: "unchanged" | "shifted" | "added" | "killed";
  /** How far it moved, when it moved. */
  readonly moved?: Movement;
}

/**
 * What the engine says moved between two worlds.
 *
 * Every part of it is the engine's. The browser ranks nothing, re-orders
 * nothing and adds nothing up: `rows` is drawn in the order it arrived, and the
 * two columns beside each row are printed as they came.
 */
export interface DiffView {
  /** Every claim either world holds, by identifier, with what happened to it. */
  readonly claims: ReadonlyMap<string, ClaimChange>;
  /** The endings, largest rank first, exactly as the engine ordered them. */
  readonly rows: readonly DeltaRow[];
  /** The one line saying what this edit did to the trades. */
  readonly summary: Known<string>;
  /** Plain sentences either world wanted the reader to see, each said once. */
  readonly warnings: readonly string[];
}

/**
 * One reason a branch could not be folded onto a map.
 *
 * `message` is the sentence the reader reads; `subject` is the identifier of the
 * claim or the arrow at fault, which is what lets the screen point at the right
 * thing and is never shown. `code` is the stable name of the rule that was
 * broken, for the same reason.
 */
export interface Reason {
  /** Which rule was broken, when the server named one. */
  readonly code?: string;
  /** The identifier of the thing at fault, when the server named one. Never shown. */
  readonly subject?: string;
  /** One plain sentence naming the claim or the arrow by its words. */
  readonly message: string;
}

/* ---- Editing the map: branches, and the six operations ------------------- */

/**
 * One arrow an **Add a claim** edit brings with it.
 *
 * Only the two ends, because that is all working out what an edit can reach
 * needs. When the map itself supplied the arrow — as the stored example's own
 * branch does — the whole arrow is on the branch's `links` as well, and that is
 * what gets drawn.
 */
export interface AddedArrow {
  /** The arrow's identifier. */
  readonly id: string;
  /** The claim the arrow starts at. */
  readonly source: string;
  /** The claim the arrow ends at. */
  readonly target: string;
}

/**
 * One edit in a branch.
 *
 * The six operations keep their code names — `do`, `observe`, `insert`,
 * `retune`, `refine`, `believe` — **in code, in the wire format and in the
 * spec, and nowhere on screen.** What the reader sees is the button they
 * pressed and the badge it earns, both copied word for word from the shared
 * vocabulary. `frontend/src/components/BranchPanel.tsx` is the one place those
 * words are written.
 */
export type Edit =
  /** Take this as given, and do not tell me what caused it. */
  | {
      readonly op: "do";
      /** The claim being supposed true or false. */
      readonly target: string;
      /** True to suppose it holds, false to suppose it does not. */
      readonly value: boolean;
      /** The day the supposition takes effect, as the map writes a day. */
      readonly at: string;
    }
  /** This is news — update what came before it too. */
  | {
      readonly op: "observe";
      readonly target: string;
      readonly value: boolean;
      readonly at: string;
    }
  /** A claim and its arrows arrive together. */
  | {
      readonly op: "insert";
      /** The new claim's identifier on the map. */
      readonly claimId: string;
      /** The new claim in its own words, which is what the badge quotes. */
      readonly words: string;
      /** The arrows that attach it. */
      readonly arrows: readonly AddedArrow[];
      /**
       * The whole claim and its arrows, exactly as the engine drafted them.
       *
       * Present when the part of this product that drafts a claim answered, and
       * absent on a branch a stored example shipped with. It is what lets this
       * edit be written the server's way and folded back onto the map: a claim is
       * not its wording, it is the wording plus how it is judged, by whom, by
       * when and what it started from, and a branch carrying only the words
       * cannot be folded at all.
       */
      readonly drafted?: components["schemas"]["Insert"];
    }
  /** One number on one arrow moves. */
  | {
      readonly op: "retune";
      /** The arrow whose push is being changed. */
      readonly link: string;
      /** The new push, signed, on the same scale the arrow carries. */
      readonly strength: number;
      /** What the push was before, so the panel can read the change back. */
      readonly wasStrength: number;
    }
  /** The finer claims add back up to the one they replace. Not built yet. */
  | { readonly op: "refine"; readonly target: string }
  /** The reader's own likelihood, beside the model's and the market's. */
  | { readonly op: "believe"; readonly target: string; readonly belief: Likelihood };

/** The four hues a branch may take. Never amber: amber means "the money moves down". */
export type BranchHue = "violet" | "teal" | "rose" | "slate";

/**
 * A named, ordered list of edits over a base map. A branch *is* the edits.
 *
 * It holds no likelihoods and no results. `claims` and `links` are the drawable
 * detail for what an **Add a claim** edit brought with it, when the map
 * supplied a whole claim rather than only its words — the stored example's own
 * branch does; a claim the reader types does not, and is shown in the branch
 * panel rather than drawn as a tile.
 */
export interface BranchView {
  /** This branch's identifier. */
  readonly id: string;
  /** The name the reader reads. */
  readonly label: string;
  /** Which of the four hues its lane and its name chip take. */
  readonly hue: BranchHue;
  /** The edits, in the order they were made. Appended to, never rewritten. */
  readonly edits: readonly Edit[];
  /** Whole claims an edit added, when the map supplied them. */
  readonly claims: readonly ClaimView[];
  /** Whole arrows an edit added, when the map supplied them. */
  readonly links: readonly LinkView[];
  /**
   * This same branch written the way the server writes one, so it can be sent
   * back to be folded onto the map — when it can be.
   *
   * It is carried rather than rebuilt from `edits` for one reason: an **Add a
   * claim** edit brings a whole claim — how it is judged, by whom, by when, what
   * it started from — and the drawable form above keeps only what a tile needs.
   * Rebuilding the server's form from the drawable one would quietly drop the
   * rest, and the map the engine folded would not be the map on screen.
   *
   * **Absent when this branch cannot be written down in full.** Adding a claim
   * of your own needs the part of this product that drafts one, and that is not
   * connected — so a branch holding one cannot be folded, and asking for its
   * world says exactly that rather than sending half of it.
   *
   * Where it is present the two forms are built side by side, from the same
   * source, and hold the same edits in the same order.
   */
  readonly wire?: WireBranch;
}

/**
 * A branch exactly as the server writes one.
 *
 * Taken from the server's own description of itself, because this shape really
 * is the server's: it is what goes back over the wire when a world is asked
 * for, and re-stating it here would let the two drift apart.
 */
export type WireBranch = components["schemas"]["Branch"];

/** One edit as the server writes one. */
export type WireEdit = components["schemas"]["Branch"]["interventions"][number];

/**
 * One ending the edit can reach, as the rail beside the map lists it.
 *
 * **A row is the ending, its number before and after, and the direction**
 * *(Kent, 2026-09-22, R48)*. It used to carry two more columns — *how firm*, the
 * width of the range around the new number, and *same direction*, the share of
 * two thousand versions of the map that moved the same way. Both were readings
 * of a range and of the versions that produced it, and both are gone.
 *
 * Every number on a row is optional, and before the engine answers it is an
 * absence with its reason. **The rail ranks nothing and computes nothing**: when
 * the engine has ordered these rows the browser draws them in that order, and
 * when it has not the browser says so on its own face.
 */
export interface DeltaRow {
  /** The ending's identifier on the map. */
  readonly claimId: string;
  /** The ending in its own words. */
  readonly label: string;
  /** What kind of ending it is, which is what says whether anything trades. */
  readonly kind: ClaimKind;
  /** How far the number moved, and the day it moved furthest. */
  readonly move: Known<{
    readonly from: number;
    readonly to: number;
    readonly largestOn: string;
    readonly way: "up" | "down";
    /** How far it moved on that day, as the engine reported it. */
    readonly by: number;
  }>;
  /**
   * True when the engine gave this ending no row of its own.
   *
   * The engine ranks an ending only when it calls it **shifted**. An ending
   * missing from that ranking could mean it held still, or that it is not on
   * this map, or that you forced it false a moment ago — and a reader cannot
   * tell those apart by looking at a list something was left out of. So the
   * change list keeps a quieter row for **every** ending the edit can reach
   * that the engine left out, after the ones it ranked and never mixed in among
   * them. What each such row says is `graph/diff/noChange.ts`'s one rule.
   */
  readonly unranked?: boolean;
  /**
   * The half-line under the ending's own words: why the engine ranked no move
   * on it, in a handful of words.
   *
   * It stands in the same slot a row that moved uses for *down · largest on Oct
   * 4*, so a quieter row carries its reason **in words** rather than only in
   * being paler than its neighbours — which says nothing in grey and nothing at
   * all read aloud. A claim that barely moved, a claim you supposed false and a
   * claim that arrived with the edit say different, true things.
   *
   * **`graph/diff/noChange.ts` writes it and nothing else does**, from the
   * engine's own word for what happened to the claim. Absent where there is
   * nothing true to put in it, and on every row that moved.
   */
  readonly note?: string;
}

/**
 * What the panel beside the map is open on, and what the map draws a ring
 * around. One name for one thing: the map, the panel and the keyboard all mean
 * the same shape by it.
 */
export type Selection =
  | { readonly kind: "claim"; readonly id: string }
  | { readonly kind: "wire"; readonly id: string }
  /**
   * The run that produced the map, rather than anything on it.
   *
   * The panel's third subject: not a claim and not an arrow, but the generation
   * itself — what it cost and every proposal it made, accepted or refused. The
   * identifier is the one the engine minted and sent on the run's first event.
   * Nothing on the canvas draws a ring for it, because there is nothing on the
   * canvas that is it.
   */
  | { readonly kind: "generation"; readonly id: string }
  | null;
