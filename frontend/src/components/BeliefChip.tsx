/**
 * One likelihood, with the range that says how sure we are of it — or, when
 * there is no likelihood, the absence and the reason for it.
 *
 * This is the smallest component in the product and the one carrying the most
 * of its honesty rule, so it is worth reading in full.
 *
 * **Two significant figures and the range, always.** A likelihood is printed as
 * `.35` and never as `.348` — a third figure claims an accuracy nobody has —
 * and it is never printed without the range under it. The rounding happens
 * here, once, at the moment of display; everything upstream carries the number
 * at full precision so that nothing is rounded twice.
 *
 * **What the range means, said out loud.** It is *how sure we are of the
 * number*, not how much the world can move. How much the world can move is
 * already inside the likelihood itself. That distinction is not a footnote: a
 * reader who takes a wide range to mean a volatile event has been misled by the
 * interface, so the model chip says which it is in its own label and spells it
 * out in full when you look at it.
 *
 * **An absent number is an absence, never a blank.** There is no path through
 * this component that prints nothing, prints a zero, or prints a stand-in. A
 * slot with no number shows the words for its absence and carries the reason
 * for it. A claim standing on the reader's own say-so shows the word — *Supposed
 * · Oct 1* — because while it is supposed it is true in every simulated world
 * and there is no number to show.
 */

import { useId, useState } from "react";
import { type LikelihoodStep, likelihoodStep } from "../graph/wires/encodings";
import type { BeliefOwner, Known, Ranged, Standing } from "../world";
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
 * Print a **likelihood** — or an end of the range around one, which is a
 * likelihood too — the way this product prints one.
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
 * Print a **size** on the likelihood scale: how far a number moved, or how wide
 * a band is.
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

/**
 * Print a range the way this product prints one: `.22–.50`.
 *
 * Both ends are likelihoods, so both take the guard: a band whose bottom end
 * sits under a hundredth reads `<.01–.03`, which says the low end is small
 * without calling it impossible.
 *
 * The dash is an en dash, the one used for a span between two numbers.
 */
export function toRange(lo: number, hi: number): string {
  return `${toTwoFigures(lo)}–${toTwoFigures(hi)}`;
}

/**
 * Print a share of something counted — *how many of the two thousand versions
 * of the map moved the same way* — as a whole percentage.
 *
 * A share is not a likelihood. It is a count of things that happened divided by
 * how many there were, so a hundred per cent really can mean *every one of
 * them*, and printing `>.99` over it would hide a fact the machine actually
 * counted. So the only guard here is the one that stops rounding from inventing
 * unanimity: a share that is not quite all of them never prints as all of them.
 *
 * Two figures, like everything else on screen: `97%`, never `96.63%`.
 *
 * @param share A share from 0 to 1, at full precision.
 */
export function toShare(share: number): string {
  if (!Number.isFinite(share)) {
    return "—";
  }
  const whole = Math.round(share * 100);
  if (whole >= 100 && share < 1) {
    return ">99%";
  }
  if (whole <= 0 && share > 0) {
    return "<1%";
  }
  return `${whole}%`;
}

/**
 * The whole reading, in the form a sentence would use: `.35 (.22–.50)`.
 *
 * This is what the chip is called when it is read aloud, and what the tile uses
 * when it needs the reading inside a longer sentence.
 */
export function toReading(p: number, lo: number, hi: number): string {
  return `${toTwoFigures(p)} (${toRange(lo, hi)})`;
}

/** The word each owner is called by on screen. */
const OWNER_WORDS: Record<BeliefOwner, string> = {
  model: "model",
  user: "user",
  market: "market",
};

/**
 * The note a chip opens when you look at it: one label, one sentence.
 *
 * It is not a pop-up. It is a shelf that slides out from the bottom edge of the
 * tile, drawn on the tile's own surface, and it needs no dismissing — look
 * away, or move the keyboard on, and it closes itself.
 */
interface Note {
  /** The chip's label, printed as the first line of the shelf. */
  readonly label: string;
  /** The sentence under it. */
  readonly sentence: string;
}

/** Group a count in thousands the way the sentence below writes it: `2 000`. */
function inThousands(count: number): string {
  return count.toLocaleString("en-GB").replace(/,/g, " ");
}

/**
 * What the model chip says about itself — and there are two answers, because
 * there are two different things a range can be.
 *
 * **When a world computed these numbers**, the range came out of running the
 * map many times over, each run a coherent set of numbers the model would have
 * stood behind, and the sentence says so and then admits in its last clause
 * that nobody has checked the claim against anything that resolved.
 *
 * **When nothing computed them** — which is every number in this build, because
 * the engine's route does not exist yet — the range is what whoever wrote the
 * number down said about how sure they were. Saying "across 2 000 versions of
 * this map" over a number nobody ran through a map would be the plainest kind
 * of lie this product can tell, so it says the other thing instead.
 *
 * The chip picks between them by one fact: whether the world it is drawing
 * reports how many versions were run. Nothing else changes when the engine
 * lands.
 */
function modelNote(p: number, lo: number, hi: number, versions: number | undefined): Note {
  if (versions === undefined) {
    return {
      label: "stated range · not computed",
      sentence:
        "This range is stated, not computed — it says how sure the elicitation was. " +
        "Nothing has worked this number through the map yet.",
    };
  }
  return {
    label:
      `model interval, uncalibrated · how sure we are of ${toTwoFigures(p)} — ` +
      `not how much the world can move`,
    sentence:
      `Across ${inThousands(versions)} versions of this map — each one a set of numbers this ` +
      `model would have stood behind — the answer landed between ${toTwoFigures(lo)} and ` +
      `${toTwoFigures(hi)} eight times in ten. Nobody has checked whether that 8-in-10 holds ` +
      `up; no claim on this map has resolved yet.`,
  };
}

/** What the reader's own chip says about itself. */
function userNote(p: number, lo: number, hi: number): Note {
  return {
    label: `your own number · ${toReading(p, lo, hi)}`,
    sentence:
      "This is the number you gave. It sits beside the model's and the market's and is " +
      "never averaged with either of them.",
  };
}

/** What a market chip says about itself. */
function marketNote(lo: number, hi: number): Note {
  return {
    label: "market, as a venue is quoting it",
    sentence:
      `The likelihood is the middle of the best bid and the best offer; the range, ` +
      `${toRange(lo, hi)}, is the spread between them. It is what somebody will trade this ` +
      `claim at, not an opinion about it.`,
  };
}

/** Work out the three lines a chip shows, and the note behind it. */
function readChip(
  owner: BeliefOwner,
  slot: Known<Ranged>,
  standing: Standing | undefined,
  versions: number | undefined,
): {
  reading: string;
  under: string | null;
  spoken: string;
  note: Note;
  numeric: boolean;
  step: LikelihoodStep | null;
} {
  // A claim the reader has supposed true is true in every simulated world, so
  // the chip shows the word rather than a number. Inventing one — .98, or 1.0 —
  // would invite the reader to wonder about the other two per cent of a thing
  // they themselves declared settled.
  if (standing !== undefined) {
    return {
      reading: standing.words,
      under: null,
      spoken: `${OWNER_WORDS[owner]}: ${standing.words}`,
      note: { label: standing.words, sentence: standing.reason },
      numeric: false,
      step: null,
    };
  }

  if (slot.reading === undefined) {
    const absence = slot.absence;
    return {
      reading: absence.words,
      // The reader's own empty slot says what to do about it; every other
      // absence keeps its sentence for the shelf, where there is room for it.
      under: owner === "user" ? "add yours" : null,
      spoken: `${OWNER_WORDS[owner]}: ${absence.words}. ${absence.reason}`,
      note: { label: absence.words, sentence: absence.reason },
      numeric: false,
      step: null,
    };
  }

  const { p, lo, hi } = slot.reading;
  const note =
    owner === "model"
      ? modelNote(p, lo, hi, versions)
      : owner === "user"
        ? userNote(p, lo, hi)
        : marketNote(lo, hi);
  return {
    reading: toTwoFigures(p),
    under: toRange(lo, hi),
    spoken: `${OWNER_WORDS[owner]}: ${toReading(p, lo, hi)}`,
    note,
    numeric: true,
    step: likelihoodStep(p),
  };
}

/** What a belief chip needs to draw itself. */
export interface BeliefChipProps {
  /** Whose number this is. There are three, and they are never averaged. */
  readonly owner: BeliefOwner;
  /** The number, or the absence that stands where it would have been. */
  readonly slot: Known<Ranged>;
  /** A word shown instead of a likelihood, when the claim stands on the reader's say-so. */
  readonly standing?: Standing;
  /**
   * How many versions of the map were run to produce this number.
   *
   * Absent means nothing computed it, and the model chip then says so rather
   * than describing a run that never happened.
   */
  readonly versions?: number;
}

/** One of the three belief chips on a tile. */
export function BeliefChip({ owner, slot, standing, versions }: BeliefChipProps) {
  const noteId = useId();
  const [pinned, setPinned] = useState(false);
  const { reading, under, spoken, note, numeric, step } = readChip(owner, slot, standing, versions);

  return (
    <span className="belief-chip" data-owner={owner} data-reading={numeric ? "number" : "words"}>
      {/* The face of the chip is the thing you can reach, so that looking at it
          with a pointer and arriving at it with the keyboard do the same thing.
          Pressing it pins the note open, for a reader who wants both hands free
          while they read it; pressing again puts it away. It is named by the
          whole reading — the number and its range together — because that is how
          the chip would be said out loud, and the range is never left off. */}
      <button
        className="belief-chip__face"
        type="button"
        aria-label={spoken}
        aria-describedby={noteId}
        aria-controls={noteId}
        aria-expanded={pinned}
        onClick={() => setPinned((was) => !was)}
      >
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
        <span className="belief-chip__under">{under ?? ""}</span>
      </button>
      <span className="belief-chip__note" id={noteId} data-pinned={pinned ? "yes" : "no"}>
        <span className="belief-chip__note-label">{note.label}</span>
        <span className="belief-chip__note-sentence">{note.sentence}</span>
      </span>
    </span>
  );
}
