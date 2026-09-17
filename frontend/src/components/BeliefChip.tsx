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
import type { BeliefOwner, Slot, Standing } from "../world";
import "./beliefChip.css";

/**
 * Print a number to two significant figures, the way this product prints one.
 *
 * A likelihood is between zero and one, so the leading zero is dropped: `.35`,
 * not `0.35`. Two significant figures means two digits that carry information,
 * and both of them are always printed — `.060` keeps its trailing nought,
 * because dropping it would claim less precision than we have, and "two figures
 * except when the second is a nought" would be a second rule for one ugly case.
 *
 * **It never prints a certainty.** Rounding to two figures turns .995 into
 * `1.0`, and nothing at all into `.0`, and both are claims nobody on this map
 * is entitled to make: one says the thing cannot fail, the other that it cannot
 * happen. So those two print as what they actually are, `>.99` and `<.01`. The
 * upper guard catches everything from .995 up, including 1 itself. The lower
 * one is rarer than it looks: two figures keeps two digits however small the
 * number gets, so `.0035` prints `.0035` and `.00012` prints `.00012`, and the
 * only value that would ever print as `.0` is exactly zero.
 *
 * **Why it does not use the obvious shortcut.** A computer stores .995 as
 * 0.99499999999999999556, so asking it directly for two figures gives `.99` —
 * under the guard, and the chip would print the one thing the rule forbids. So
 * the rounding is done on the number's own decimal digits instead: the shortest
 * decimal that reads back as this exact number, its point shifted by counting
 * rather than by multiplying, and then rounded half-up. `.995` shifts to
 * exactly 99.5, which rounds to 100, which is 1, which is `>.99`.
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
  // The shortest decimal that reads back as this exact number, split into its
  // digits and where the point sits: .995 becomes "9.95" and -1.
  const [mantissa = "0", place = "0"] = value.toExponential().split("e");
  let exponent = Number(place);
  // The two figures, as a whole number from 10 to 99. Shifting the point in the
  // text and letting the parser read the result is what keeps .995 at 99.5
  // rather than a hair under it.
  let figures = Math.round(Number(`${mantissa}e1`));
  if (figures >= 100) {
    // Rounding up carried into the next place: .0999 becomes .10, not .100.
    figures = 10;
    exponent += 1;
  }
  if (exponent >= 0) {
    return ">.99";
  }
  return `.${"0".repeat(-exponent - 1)}${figures}`;
}

/**
 * Print a range the way this product prints one: `.22–.50`.
 *
 * The dash is an en dash, the one used for a span between two numbers.
 */
export function toRange(lo: number, hi: number): string {
  return `${toTwoFigures(lo)}–${toTwoFigures(hi)}`;
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
  slot: Slot,
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
  readonly slot: Slot;
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
