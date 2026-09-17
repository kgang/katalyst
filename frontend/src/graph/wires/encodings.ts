/**
 * What an arrow's data turns into on screen — every lookup in one place.
 *
 * A wire has to say five things at once, and every one of them has to survive a
 * screenshot printed in grey:
 *
 *   1. **what kind of push it is** — the stroke's pattern;
 *   2. **how hard it pushes** — the stroke's width, in four steps;
 *   3. **whether it has to keep holding** — a wire that holds is drawn as two
 *      parallel strokes, a wire that fires once as a single stroke;
 *   4. **whether it loops back** — it runs over the top of the map and carries
 *      the delay in days;
 *   5. **where it came from** — a mark of one, two or three dots at its tail.
 *
 * Not one of those is a colour. Every wire is drawn in the same muted ink, and a
 * wire's hue says nothing at all.
 *
 * One more lookup lives here because it is the same kind of thing: which of the
 * five brightness steps a likelihood is painted with, which is the only part of
 * the colour law that needs a function rather than a stylesheet.
 *
 * **Nothing in this file is arithmetic.** Picking a stroke width or a band of
 * words is a *comparison* of one number against fixed thresholds written down
 * below — the same kind of thing as asking whether a date is in the past. No
 * expression here adds, multiplies or averages two numbers read off the map, and
 * none may ever be added: the moment the canvas works out a number of its own
 * there are two engines on the map and they disagree.
 */

import type { LinkMode, LinkShape, Provenance } from "../../world";

/* ---- How likely a claim is: the one lookup the colour law needs ---------- *
 *
 * Brightness is the channel that carries how likely a claim is, and the five
 * steps of it are `--p-0` … `--p-4` in `styles/tokens.css`. This is the lookup
 * that says which step a likelihood is painted with. It lives here, beside the
 * arrow's lookups, because it is the same kind of thing: a comparison against
 * fixed thresholds, never a calculation. */

/** One of the five brightness steps a likelihood is painted with. */
export type LikelihoodStep = 0 | 1 | 2 | 3 | 4;

/**
 * Which of the five brightness steps this likelihood is painted with.
 *
 * | Likelihood | Step |
 * |---|---|
 * | 0 to under .2 | 0 |
 * | .2 to under .4 | 1 |
 * | .4 to under .6 | 2 |
 * | .6 to under .8 | 3 |
 * | .8 to 1 | 4 |
 *
 * Five steps are a glance, never a reading. The exact number and its range are
 * printed beside the bar every time, so nobody is ever asked to tell step two
 * from step three by eye.
 *
 * @param p How likely the claim is to come out true, from 0 to 1.
 */
export function likelihoodStep(p: number): LikelihoodStep {
  if (p < 0.2) {
    return 0;
  }
  if (p < 0.4) {
    return 1;
  }
  if (p < 0.6) {
    return 2;
  }
  if (p < 0.8) {
    return 3;
  }
  return 4;
}

/* ---- How hard it pushes: four widths and five bands of words ------------- *
 *
 * The two granularities differ on purpose and nothing is lost by it, because
 * the signed number is printed beside the words every time: `+1.6 · a strong
 * push toward`. The stroke is a glance; the words and the number are the
 * reading.
 *
 * Four widths, because a fifth is not tellable apart at a hairline. Five bands
 * of words, because prose can carry a distinction a hairline cannot — the four
 * anchors the map's own rules name (half, one, two and three) with the gaps
 * between them filled and one band added below a quarter. */

/** The four stroke widths, in pixels, from thinnest to thickest. */
export const WIRE_WIDTHS = [1, 2, 3, 4] as const;

/** A stroke width, in pixels. */
export type WireWidth = (typeof WIRE_WIDTHS)[number];

/**
 * The size of a push, without its sign.
 *
 * Width comes from how hard an arrow pushes and never from which way: an arrow
 * that makes its target less likely is drawn exactly like one that makes it
 * more likely, and the sign is carried by the printed sign and by a word.
 *
 * @param strength How hard the arrow pushes, signed, at full precision.
 */
function sizeOf(strength: number): number {
  return strength < 0 ? -strength : strength;
}

/**
 * Which of the four stroke widths this push is drawn at.
 *
 * A comparison against three thresholds, and nothing else:
 *
 * | The size of the push | Stroke |
 * |---|---|
 * | under 0.5 | 1 pixel |
 * | 0.5 to under 1.25 | 2 pixels |
 * | 1.25 to under 2.25 | 3 pixels |
 * | 2.25 and over | 4 pixels |
 *
 * @param strength How hard the arrow pushes, signed, at full precision.
 */
export function widthFor(strength: number): WireWidth {
  const size = sizeOf(strength);
  if (size < 0.5) {
    return 1;
  }
  if (size < 1.25) {
    return 2;
  }
  if (size < 2.25) {
    return 3;
  }
  return 4;
}

/** One band of the words a push reads back as, and the two sizes it is drawn at. */
interface Band {
  /** Everything below this size falls in this band. `Infinity` for the top one. */
  readonly under: number;
  /** What a push this size, pushing its target toward coming true, reads as. */
  readonly toward: string;
  /** What a push this size, pushing its target away from coming true, reads as. */
  readonly against: string;
}

/**
 * The five bands, smallest first.
 *
 * The anchors behind them: half a point roughly shifts the odds by a fifth, one
 * point triples them, two points is a strong shove and three is close to
 * settling the question. Between the anchors the interface reads a push back in
 * these five bands.
 */
const BANDS: readonly Band[] = [
  { under: 0.25, toward: "a faint push toward", against: "a faint push against" },
  { under: 0.75, toward: "a nudge toward", against: "a nudge against" },
  { under: 1.5, toward: "a clear push toward", against: "a clear push against" },
  { under: 2.5, toward: "a strong push toward", against: "a strong push against" },
  { under: Number.POSITIVE_INFINITY, toward: "close to decisive", against: "close to ruled out" },
];

/**
 * What this push reads back as in words.
 *
 * Which way it pushes is carried by the last word — *toward* or *against* — so
 * the direction survives a picture with no colour in it at all, and so that a
 * push is never mistaken for a direction of financial effect. Those are
 * different things: the arrow into *Brent settles below $68* pushes that claim
 * **toward** coming true, and the price it describes is **falling**.
 *
 * @param strength How hard the arrow pushes, signed, at full precision.
 */
export function pushInWords(strength: number): string {
  const size = sizeOf(strength);
  const band = BANDS.find((one) => size < one.under) ?? BANDS[BANDS.length - 1];
  if (band === undefined) {
    // Unreachable: the last band's ceiling is infinity, so `find` always hits.
    return "a push";
  }
  return strength < 0 ? band.against : band.toward;
}

/**
 * The push as a signed number, the way the interface prints one: `+1.6`, `−1.2`.
 *
 * A proper minus sign rather than a hyphen, and a plus sign always written out,
 * because a reader scanning a column of pushes should never have to work out
 * whether a missing sign means positive or means somebody forgot.
 *
 * One figure after the point, which is the precision the map's own arrows are
 * elicited at. This is not a likelihood and the two-significant-figures rule
 * does not reach it: a push is a signed amount on the scale where separate
 * pushes add up, not a probability.
 *
 * @param strength How hard the arrow pushes, signed, at full precision.
 */
export function pushAsNumber(strength: number): string {
  const size = sizeOf(strength).toFixed(1);
  return strength < 0 ? `−${size}` : `+${size}`;
}

/**
 * The whole reading a wire's chip shows: the number, then the words.
 *
 * @param strength How hard the arrow pushes, signed, at full precision.
 */
export function pushReading(strength: number): string {
  return `${pushAsNumber(strength)} · ${pushInWords(strength)}`;
}

/* ---- What kind of push it is: the stroke's pattern ----------------------- */

/** How one of the three signal shapes is drawn, and what it says. */
interface ShapeDrawing {
  /**
   * The dashes and gaps the stroke is drawn with, or `null` for an unbroken
   * line. Written in the wire's own units when the pattern should look the
   * same on every wire, and in hundredths of the wire's length when it should
   * run its course exactly once from tail to head — see `growsAlongTheWire`.
   */
  readonly dashes: string | null;
  /**
   * True when the pattern is measured in hundredths of this wire's own length,
   * so that it climbs from fine to coarse the same way however long the wire is.
   */
  readonly growsAlongTheWire: boolean;
  /** What this shape does over time, in one line, for the panel. */
  readonly sentence: string;
}

/**
 * The three shapes.
 *
 * - **A one-time spike** is drawn dot-dash: a mark, a gap, a dash, a gap, over
 *   and over. It reads as something that happened once and is fading.
 * - **A switch that holds** is drawn solid. Nothing is broken about it.
 * - **A push that builds** is drawn as dashes that grow from fine at the cause
 *   to coarse at the effect, so the picture itself climbs. A gradient along the
 *   stroke was the other option and it was not taken: brightness already means
 *   how likely a claim is, and a wire that got brighter along its length would
 *   be a second meaning on that channel — and it would read as a lighting
 *   effect rather than as a signal.
 */
const SHAPES: Record<LinkShape, ShapeDrawing> = {
  impulse: {
    dashes: "1 4 7 4",
    growsAlongTheWire: false,
    sentence: "a one-time spike that fades away",
  },
  step: {
    dashes: null,
    growsAlongTheWire: false,
    sentence: "switched on when the delay has run, and held from then on",
  },
  ramp: {
    // Five dashes that grow, one to five, with a gap between each: twenty-five
    // hundredths of the wire's own length, so the climb runs four times from
    // tail to head on a wire of any length.
    //
    // Four times rather than once, and that is the whole of the thinking here.
    // A single climb along the wire is the truer picture, but on a long wire its
    // last stretch is one dash a fifth of the wire long — and a fifth of a wire
    // is a stretch a reader meets on its own, where it is a plain line and says
    // *a switch that holds*. Repeating the climb means that wherever the eye
    // lands, the pattern is growing, which is the thing that had to be legible.
    dashes: "1 2 2 2 3 2 4 2 5 2",
    growsAlongTheWire: true,
    sentence: "climbs from nothing to full size across the delay, then holds",
  },
};

/**
 * How a wire of this shape is stroked.
 *
 * @param shape What the push does over time.
 */
export function strokeFor(shape: LinkShape): ShapeDrawing {
  return SHAPES[shape];
}

/**
 * What this shape does over time, in one line — with the half-life spelled out
 * when there is one.
 *
 * @param shape What the push does over time.
 * @param halfLife Days for a one-time spike to fall to half its size, or null.
 */
export function shapeInWords(shape: LinkShape, halfLife: number | null): string {
  const base = SHAPES[shape].sentence;
  if (shape === "impulse" && halfLife !== null) {
    return `${base}, half gone after ${inDays(halfLife)}`;
  }
  return base;
}

/* ---- Whether it has to keep holding ------------------------------------- */

/** What each of the two kinds of push means, in a sentence rather than a word. */
const MODES: Record<LinkMode, string> = {
  trigger:
    "a domino — it fires once when the cause becomes true, and the effect stays " +
    "pushed and fades on its own. Standing the first domino back up does not " +
    "stand this one back up",
  sustain:
    "an apple on a desk — the push exists only while the cause holds, and it " +
    "vanishes the moment the cause stops",
};

/**
 * What this kind of push means, in a sentence.
 *
 * @param mode Whether the push survives its cause going away.
 */
export function modeInWords(mode: LinkMode): string {
  return MODES[mode];
}

/* ---- How long it takes --------------------------------------------------- */

/**
 * A number of days, the way the interface says one.
 *
 * Whole days are written without a decimal point, because "2.0 days" reads as a
 * measurement and a lag is a count.
 *
 * @param days A number of days.
 */
export function inDays(days: number): string {
  const figure = Number.isInteger(days) ? `${days}` : days.toFixed(1);
  return days === 1 ? "1 day" : `${figure} days`;
}

/**
 * How long after its cause this push arrives, in words.
 *
 * @param lag Days from the cause becoming true to the push reaching full size.
 */
export function lagInWords(lag: number): string {
  return lag === 0 ? "same day" : `after ${inDays(lag)}`;
}

/* ---- Where it came from: one, two or three dots -------------------------- */

/** How many dots an arrow's mark carries. Three steps, never seven. */
export type OriginStep = 1 | 2 | 3;

/**
 * The three steps, and which of the seven receipts fall in each.
 *
 * Three rather than seven, because the question a picture can answer is *is
 * there a document behind this, or is it the model talking*. The seven-way
 * distinction is not something anybody reads off a picture, so the exact word
 * lives in the panel beside the map, where there is room for it — drawn by the
 * same component, so the mark and the word can never drift apart.
 */
const ORIGIN_STEPS: Record<Provenance, OriginStep> = {
  documented: 3,
  historical: 3,
  market_implied: 3,
  argued: 2,
  user: 2,
  asserted: 1,
  simulated: 1,
};

/** What each of the three steps means, in one line. */
const STEP_MEANINGS: Record<OriginStep, string> = {
  3: "something was fetched, studied or priced",
  2: "a mechanism was stated, or a person typed it",
  1: "the model talking, or a probe",
};

/**
 * How many dots this receipt is drawn with.
 *
 * @param provenance Where the arrow and its number came from.
 */
export function originStep(provenance: Provenance): OriginStep {
  return ORIGIN_STEPS[provenance];
}

/**
 * What a mark of this many dots means, in one line.
 *
 * @param step How many dots the mark carries.
 */
export function originStepMeaning(step: OriginStep): string {
  return STEP_MEANINGS[step];
}

/**
 * What each of the seven receipts says about itself, in the panel.
 *
 * These are facts about our own pipeline, not claims a model makes about its own
 * work. The model never fills one of these in; our code writes it from what
 * actually happened.
 */
const ORIGIN_SENTENCES: Record<Provenance, string> = {
  documented: "sources were fetched and cited, and they are listed above",
  historical: "it comes from a study of what happened in past cases like this one",
  market_implied: "it was read off a price somebody is actually quoting",
  argued: "the model stated a mechanism, and no retrieval step has run for this arrow",
  user: "you put this arrow on the map yourself",
  asserted: "the model asserted it without stating a mechanism — the weakest of the seven",
  simulated: "it came out of a probe run against this claim, not out of the world",
};

/**
 * What this receipt says about itself, in one line.
 *
 * @param provenance Where the arrow and its number came from.
 */
export function originInWords(provenance: Provenance): string {
  return ORIGIN_SENTENCES[provenance];
}
