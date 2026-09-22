/**
 * One likelihood with a name on it — or, when there is no likelihood, the
 * absence and the reason for it.
 *
 * This is the smallest component in the product and the one carrying the most
 * of its honesty rule, so it is worth reading in full.
 *
 * **A chip is three things: whose number it is, the mark, and the number**
 * *(Kent, 2026-09-22, R48)*. There used to be a fourth line under the number —
 * a range, `.24–.56`, saying how sure we were of it — and a shelf that slid out
 * of the tile to explain what the range meant and that it came out of running
 * the map two thousand times. Kent cut the two thousand versions of the map from
 * this product, and the range and its explanation went with them. One claim, one
 * likelihood.
 *
 * **Two significant figures, always.** A likelihood is printed as `.35` and
 * never as `.348` — a third figure claims an accuracy nobody has. The rounding
 * happens here, once, at the moment of display; everything upstream carries the
 * number at full precision so that nothing is rounded twice.
 *
 * **An absent number is an absence, never a blank.** There is no path through
 * this component that prints nothing, prints a zero, or prints a stand-in. A
 * slot with no number shows the words for its absence. A claim standing on the
 * reader's own say-so shows the word — *Supposed · Oct 1* — because while it is
 * supposed it is true in every world the engine works through and there is no
 * number to show. The sentence behind either is read in the panel beside the
 * map, where a reason has room to be one.
 *
 * **Which chips a tile draws is not decided here.** A chip draws whatever it is
 * handed; `Tile.tsx` decides that the model's column is always drawn and that
 * the reader's and a venue's are drawn only where they hold a number, because
 * that is a statement about a tile rather than about a chip.
 */

import { type LikelihoodStep, likelihoodStep } from "../graph/wires/encodings";
import type { BeliefOwner, Known, Likelihood, Standing } from "../world";
import "./beliefChip.css";

/**
 * A number at two significant figures, split into its digits and where the point
 * sits — or nothing at all, for a number there is no sense in printing.
 *
 * The value it stands for is `figures × 10^(exponent − 1)`: `.35` is 35 and −1,
 * `.0035` is 35 and −3, `1.0` is 10 and 0.
 *
 * **Why it does not use the obvious shortcut.** A computer stores .995 as
 * 0.99499999999999999556, so asking it directly for two figures gives `.99` —
 * and .995 is precisely the case the certainty guard exists for. So the rounding
 * is done on the number's own decimal digits instead: the shortest decimal that
 * reads back as this exact number, its point shifted by counting rather than by
 * multiplying, and then rounded half-up. `.995` shifts to exactly 99.5, which
 * rounds to 100, which carries to 1.
 *
 * @param value Any number from 0 up.
 */
function twoFigures(value: number): { figures: number; exponent: number } | null {
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  const [mantissa = "0", place = "0"] = value.toExponential().split("e");
  let exponent = Number(place);
  // The two figures, as a whole number from 10 to 99.
  let figures = Math.round(Number(`${mantissa}e1`));
  if (figures >= 100) {
    // Rounding up carried into the next place: .0999 becomes .10, not .100.
    figures = 10;
    exponent += 1;
  }
  return { figures, exponent };
}

/**
 * Write those two figures out.
 *
 * Both digits are always printed — `.060` keeps its trailing nought, because
 * dropping it would claim less precision than we have, and "two figures except
 * when the second is a nought" would be a second rule for one ugly case.
 */
function written({ figures, exponent }: { figures: number; exponent: number }): string {
  if (exponent < 0) {
    return `.${"0".repeat(-exponent - 1)}${figures}`;
  }
  const digits = `${figures}`;
  // A number at or above one: the point sits inside or after the two figures.
  return exponent === 0 ? `${digits[0]}.${digits[1]}` : digits + "0".repeat(exponent - 1);
}

/**
 * Print a **likelihood** the way this product prints one.
 *
 * **A likelihood, and only a likelihood.** How far a number moved and how wide a
 * band is are measured on the same scale and are not likelihoods; they take
 * `toSize` below, and the difference is the guard.
 *
 * **Two significant figures.** A likelihood is between zero and one, so the
 * leading zero is dropped: `.35`, not `0.35`. Both figures are always printed.
 *
 * **It never prints a certainty, at either end.** A likelihood of 1 says the
 * thing cannot fail and a likelihood of 0 says it cannot happen, and nothing on
 * this map is entitled to either. So the guard is applied to the number **as it
 * would print**: what two figures would print at or above `1.0` prints `>.99`,
 * and what they would print below `.010` prints `<.01` (Kent, 2026-09-20, G10).
 * `.0099` is below the line and reads `<.01`; `.010` is on it and reads `.010`.
 *
 * **This rule is written twice and the two copies must move together.** The
 * engine writes the same numbers into the one-line summary it carries, in
 * `backend/src/katalyst/domain/diff.py::_two_figures`. A screen and a sentence
 * that round the same number differently are two answers to one question.
 *
 * @param value A likelihood, at full precision.
 * @returns The number as it is shown on screen.
 */
export function toTwoFigures(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "<.01";
  }
  if (value >= 1) {
    return ">.99";
  }
  const rounded = twoFigures(value);
  if (rounded === null) {
    return "<.01";
  }
  // Read off the printed value rather than the one that came in. Two figures
  // put the point one place after them, so anything below a hundredth lands at
  // an exponent under −2 — and `.00996` rounds up to `.010` and stays.
  if (rounded.exponent >= 0) {
    return ">.99";
  }
  if (rounded.exponent < -2) {
    return "<.01";
  }
  return written(rounded);
}

/**
 * Print a **size** on the likelihood scale: how far a number moved.
 *
 * **A size is not a likelihood, and it takes no guard.** `<.01` on a likelihood
 * says "nothing here, but we are not calling it impossible" — a claim about the
 * world. A move of nine thousandths is not a claim about the world at all; it is
 * a measurement, and rounding it away to `<.01` would throw out the only thing
 * the reader came for. So two significant figures, however small: `.0090`,
 * `.0035`, `.00012` (Kent, 2026-09-20, G10).
 *
 * The other end takes no guard either: a move of exactly one is a real move, and
 * it prints `1.0`.
 *
 * **Nought and not-a-number are two different things.** A move of exactly
 * nothing prints `0` — two significant figures of nothing is still nothing, and
 * `.00` would claim a precision the measurement has not got. Anything that is
 * not a number at all prints the dash this product prints for a value that is
 * not there, rather than being rounded down to nought and read as a measurement.
 *
 * @param value A distance between two likelihoods, at full precision. Its sign
 *   is said in words elsewhere, so pass its size.
 */
export function toSize(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }
  const rounded = twoFigures(Math.abs(value));
  return rounded === null ? "0" : written(rounded);
}

/** The chevron and the word each direction goes by. Neither is a colour. */
const WAY = {
  up: { chevron: "▲", word: "up" },
  down: { chevron: "▼", word: "down" },
} as const;

/**
 * How far a number moved, in the one form every surface prints it in.
 *
 * **Never a chevron between two readings that print the same.** Two figures is
 * the whole of what this product shows, and a move smaller than the second
 * figure leaves the before and the after printing identically — `.36 ▲ .36`,
 * which says "it went up" and "it is where it was" in the same breath and reads
 * as a fault in the tool. So where the two readings differ the row is the pair
 * with the chevron between them, and where they do not it is the one reading and
 * the size of the move in words: `.36 · up by .0090`.
 *
 * The size is the engine's own, at two significant figures **and no guard**: a
 * move of nine thousandths is a measurement, not a claim about the world, and
 * rounding it away to `<.01` would throw out the only thing the reader came
 * for (Kent, 2026-09-20, G10).
 *
 * @param from The first world's likelihood, at full precision.
 * @param to The second world's likelihood, at full precision.
 * @param by How far it moved, as the engine reported it. Its sign is already
 *   said by `way`, so only its size is printed.
 * @param way Which way it went, as the engine read it.
 */
export function toMovement(from: number, to: number, by: number, way: "up" | "down"): string {
  const before = toTwoFigures(from);
  const after = toTwoFigures(to);
  if (before !== after) {
    return `${before} ${WAY[way].chevron} ${after}`;
  }
  // Nothing moved at all — the engine's own difference is zero — so there is no
  // direction to name. "up by 0" would be a direction invented for a number that
  // has none.
  if (by === 0) {
    return after;
  }
  return `${after} · ${WAY[way].word} by ${toSize(by)}`;
}

/* **Three printers used to live here and no longer do** *(2026-09-22, R48)*.
 * `toRange` wrote `.22–.50`; `toReading` wrote `.35 (.22–.50)`, which was what a
 * chip was called when it was read aloud; `toShare` wrote `97%`, the share of
 * the two thousand versions of the map that moved the same way. All three
 * printed a range or the versions behind one, so all three went with them. A
 * chip is called by its owner and its number now. */

/** The word each owner is called by on screen. */
const OWNER_WORDS: Record<BeliefOwner, string> = {
  model: "model",
  user: "user",
  market: "market",
};

/**
 * Work out the two lines a chip shows, and what it is called when it is read
 * out loud.
 *
 * **There used to be a third line and a shelf behind it** *(until 2026-09-22,
 * R48)*. The third line was the range, `.24–.56`; the shelf was a label and a
 * sentence saying what the range meant — *model interval, uncalibrated*, and
 * *across 2 000 versions of this map…*. There is no range, so there is nothing
 * left for either of them to say. The sentence behind an absence is still read
 * in full in the panel beside the map, where a reason has room to be a sentence.
 */
function readChip(
  slot: Known<Likelihood>,
  standing: Standing | undefined,
): {
  reading: string;
  alsoSaid: string | null;
  numeric: boolean;
  step: LikelihoodStep | null;
} {
  // A claim the reader has supposed true is true in every world the engine
  // works through, so the chip shows the word rather than a number. Inventing
  // one — .98, or 1.0 — would invite the reader to wonder about the other two
  // per cent of a thing they themselves declared settled.
  if (standing !== undefined) {
    return { reading: standing.words, alsoSaid: null, numeric: false, step: null };
  }

  if (slot.reading === undefined) {
    const absence = slot.absence;
    return { reading: absence.words, alsoSaid: absence.reason, numeric: false, step: null };
  }

  const { p } = slot.reading;
  return { reading: toTwoFigures(p), alsoSaid: null, numeric: true, step: likelihoodStep(p) };
}

/** What a belief chip needs to draw itself. */
export interface BeliefChipProps {
  /** Whose number this is. There are three, and they are never averaged. */
  readonly owner: BeliefOwner;
  /** The number, or the absence that stands where it would have been. */
  readonly slot: Known<Likelihood>;
  /** A word shown instead of a likelihood, when the claim stands on the reader's say-so. */
  readonly standing?: Standing;
}

/** One of the three belief chips on a tile. */
export function BeliefChip({ owner, slot, standing }: BeliefChipProps) {
  const { reading, alsoSaid, numeric, step } = readChip(slot, standing);

  return (
    <span className="belief-chip" data-owner={owner} data-reading={numeric ? "number" : "words"}>
      {/* **Two lines and nothing to press** *(2026-09-22, R48)*. The face was a
          button, because pressing it pinned open a shelf explaining the range
          under the number; with the range gone there is nothing behind the chip
          to open, and a control that does nothing is worse than no control.
          **And it needs no accessible name written onto it**: what it is called
          is what it reads — the owner, then the number — so the two lines below
          say it themselves and cannot drift from what is on the glass. */}
      <span className="belief-chip__face">
        <span className="belief-chip__owner">{OWNER_WORDS[owner]}</span>
        <span className="belief-chip__reading">
          {/* The bounded bar the likelihood rides on: one of five brightnesses,
              the same size whatever the number is. Brightness is the whole of
              what it says and the number printed beside it is the reading, so
              the bar only has to clear three to one while the number clears four
              and a half. It is drawn on the chip, never over a whole tile:
              tile-wide brightness is already spent on the other world in a diff
              and on the hover lens, and three meanings on one channel means none
              of them reads. */}
          {step === null ? null : (
            <span className="belief-chip__bar" data-step={step} aria-hidden="true" />
          )}
          <span className="belief-chip__figure">{reading}</span>
        </span>
        {/* Why there is no number, for a reader who hears the chip rather than
            seeing it. On the glass it is read in the panel beside the map, where
            a reason has room to be a sentence. */}
        {alsoSaid === null ? null : <span className="belief-chip__hidden">{alsoSaid}</span>}
      </span>
    </span>
  );
}
