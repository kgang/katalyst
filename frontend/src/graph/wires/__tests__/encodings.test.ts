/**
 * What an arrow's data turns into on screen.
 *
 * Two granularities are checked here and they differ on purpose: a stroke has
 * **four** widths because a fifth is not tellable apart at a hairline, and the
 * words have **five** bands because prose can carry a distinction a hairline
 * cannot. Nothing is lost by the difference, because the signed number is
 * printed beside the words every time.
 */

import { describe, expect, it } from "vitest";
import type { Provenance } from "../../../world";
import {
  inDays,
  lagInWords,
  likelihoodStep,
  modeInWords,
  originInWords,
  originStep,
  pushAsNumber,
  pushInWords,
  pushReading,
  shapeInWords,
  strokeFor,
  WIRE_WIDTHS,
  widthFor,
} from "../encodings";

describe("how hard an arrow pushes", () => {
  it("test_width_has_four_steps_and_ignores_the_sign", () => {
    // Four thresholds, and the same answer on each side of zero: width says how
    // hard, never which way.
    expect(widthFor(0.2)).toBe(1);
    expect(widthFor(0.49)).toBe(1);
    expect(widthFor(0.5)).toBe(2);
    expect(widthFor(1.24)).toBe(2);
    expect(widthFor(1.25)).toBe(3);
    expect(widthFor(2.24)).toBe(3);
    expect(widthFor(2.25)).toBe(4);
    expect(widthFor(9)).toBe(4);

    for (const size of [0.2, 0.6, 1.6, 2.4, 9]) {
      expect(widthFor(-size)).toBe(widthFor(size));
    }
  });

  it("test_width_is_never_a_fifth_step", () => {
    const seen = new Set<number>();
    for (let strength = -4; strength <= 4; strength += 0.01) {
      seen.add(widthFor(strength));
    }
    expect([...seen].sort()).toEqual([...WIRE_WIDTHS]);
  });

  it("test_the_words_come_in_five_bands_and_say_which_way", () => {
    expect(pushInWords(0.1)).toBe("a faint push toward");
    expect(pushInWords(0.5)).toBe("a nudge toward");
    expect(pushInWords(1.1)).toBe("a clear push toward");
    expect(pushInWords(1.6)).toBe("a strong push toward");
    expect(pushInWords(3)).toBe("close to decisive");

    expect(pushInWords(-0.1)).toBe("a faint push against");
    expect(pushInWords(-0.4)).toBe("a nudge against");
    expect(pushInWords(-1.2)).toBe("a clear push against");
    expect(pushInWords(-2.4)).toBe("a strong push against");
    expect(pushInWords(-3)).toBe("close to ruled out");
  });

  it("test_the_sign_is_always_printed", () => {
    // A reader scanning a column of pushes should never have to work out
    // whether a missing sign means positive or means somebody forgot.
    expect(pushAsNumber(1.6)).toBe("+1.6");
    expect(pushAsNumber(-1.2)).toBe("−1.2");
    expect(pushAsNumber(0)).toBe("+0.0");
    // A proper minus sign, not a hyphen.
    expect(pushAsNumber(-2.4)).not.toContain("-");
  });

  it("test_the_reading_is_the_number_and_then_the_words", () => {
    expect(pushReading(1.6)).toBe("+1.6 · a strong push toward");
    expect(pushReading(-1.2)).toBe("−1.2 · a clear push against");
  });
});

describe("what kind of push it is", () => {
  it("test_each_shape_has_its_own_stroke_pattern", () => {
    const patterns = [strokeFor("impulse"), strokeFor("step"), strokeFor("ramp")].map(
      (one) => one.dashes,
    );
    expect(new Set(patterns).size).toBe(3);
    // A switch that holds is an unbroken line; the other two are broken.
    expect(strokeFor("step").dashes).toBeNull();
    expect(strokeFor("impulse").dashes).not.toBeNull();
    expect(strokeFor("ramp").dashes).not.toBeNull();
  });

  it("test_the_growing_pattern_climbs_and_fits_a_wire_of_any_length", () => {
    const ramp = strokeFor("ramp");
    expect(ramp.growsAlongTheWire).toBe(true);
    const parts = (ramp.dashes ?? "").split(" ").map(Number);
    // Measured in hundredths of the wire's own length, and the cycle divides a
    // hundred exactly — otherwise the pattern would be cut off part-way through
    // a climb at the head of the wire.
    const cycle = parts.reduce((sum, one) => sum + one, 0);
    expect(100 % cycle).toBe(0);
    // And it really climbs: each dash is longer than the one before it.
    const dashes = parts.filter((_, at) => at % 2 === 0);
    for (let at = 1; at < dashes.length; at += 1) {
      expect(dashes[at] ?? 0).toBeGreaterThan(dashes[at - 1] ?? 0);
    }
  });

  it("test_the_other_two_patterns_are_the_same_size_on_every_wire", () => {
    expect(strokeFor("impulse").growsAlongTheWire).toBe(false);
    expect(strokeFor("step").growsAlongTheWire).toBe(false);
  });

  it("test_a_one_time_spike_says_when_it_is_half_gone", () => {
    expect(shapeInWords("impulse", 30)).toContain("half gone after 30 days");
    expect(shapeInWords("impulse", null)).not.toContain("half gone");
    expect(shapeInWords("step", null)).not.toContain("half gone");
  });

  it("test_each_kind_of_push_reads_as_a_sentence_not_a_word_to_look_up", () => {
    // Each one says what the push does and what follows from it, in the words
    // a reader already has. The two differ in exactly one thing — whether the
    // push survives its cause going away — so that is what each sentence leads
    // with.
    expect(modeInWords("trigger")).toContain("fires once");
    expect(modeInWords("trigger")).toContain("undoing the cause later does not undo it");
    expect(modeInWords("sustain")).toContain("holds while the cause holds");
    expect(modeInWords("sustain")).toContain("goes the moment it stops");
  });

  it("test_no_kind_of_push_is_explained_by_a_picture_of_something_else", () => {
    // Kent, 2026-09-21: "avoid the more idiosyncratic examples of an apple on a
    // desk and dominoes and aim to present vocabulary and concepts in a more
    // terse, professional manner." Both sentences reach a reader — on the
    // arrow's `kind` row and on every line of a number's working — so neither
    // may stand something in for the thing itself.
    for (const mode of ["trigger", "sustain"] as const) {
      expect(modeInWords(mode)).not.toContain("domino");
      expect(modeInWords(mode)).not.toContain("apple");
      expect(modeInWords(mode)).not.toContain("desk");
    }
  });
});

describe("how long it takes", () => {
  it("test_days_are_counted_not_measured", () => {
    expect(inDays(1)).toBe("1 day");
    expect(inDays(2)).toBe("2 days");
    expect(inDays(14)).toBe("14 days");
    expect(inDays(0.5)).toBe("0.5 days");
  });

  it("test_no_delay_reads_as_the_same_day", () => {
    expect(lagInWords(0)).toBe("same day");
    expect(lagInWords(2)).toBe("after 2 days");
  });
});

describe("where an arrow came from", () => {
  const ALL: Provenance[] = [
    "documented",
    "historical",
    "market_implied",
    "argued",
    "user",
    "asserted",
    "simulated",
  ];

  it("test_seven_receipts_fall_into_three_steps", () => {
    expect(originStep("documented")).toBe(3);
    expect(originStep("historical")).toBe(3);
    expect(originStep("market_implied")).toBe(3);
    expect(originStep("argued")).toBe(2);
    expect(originStep("user")).toBe(2);
    expect(originStep("asserted")).toBe(1);
    expect(originStep("simulated")).toBe(1);
  });

  it("test_every_receipt_has_a_sentence_of_its_own", () => {
    const sentences = ALL.map(originInWords);
    expect(new Set(sentences).size).toBe(ALL.length);
    for (const sentence of sentences) {
      expect(sentence.length).toBeGreaterThan(20);
    }
  });
});

describe("how likely a claim is", () => {
  it("test_the_brightness_ramp_has_five_steps", () => {
    expect(likelihoodStep(0)).toBe(0);
    expect(likelihoodStep(0.19)).toBe(0);
    expect(likelihoodStep(0.2)).toBe(1);
    expect(likelihoodStep(0.45)).toBe(2);
    expect(likelihoodStep(0.61)).toBe(3);
    expect(likelihoodStep(0.8)).toBe(4);
    expect(likelihoodStep(1)).toBe(4);
  });
});
