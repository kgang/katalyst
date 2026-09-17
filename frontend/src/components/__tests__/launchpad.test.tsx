/**
 * The first screen with no model key.
 *
 * This is the screen a reviewer with nothing configured meets, so it is the
 * screen that has to be honest about what this copy can and cannot do — card by
 * card, in one sentence each, with nothing greyed out that would in fact work.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Readiness } from "../../stream/readiness";
import { keylessSentence, Launchpad, STARTING_SENTENCES } from "../Launchpad";

/** The one stored example the server ships with. */
const EXAMPLES = [
  {
    id: "hormuz",
    title: "Strait of Hormuz",
    one_line: "The strait reopens, and what that causes.",
  },
];

/** What the server says about itself when it has no key and one recording. */
const NO_KEY_ONE_RECORDING: Readiness = {
  // Deliberately `not_ready`: this screen reads what can be replayed and whether
  // a key is configured, and ignores this field. A program with no key and a
  // recording can do everything a reviewer came to see.
  status: "not_ready",
  model_key_present: false,
  replayable: [{ example: "hormuz", recording_date: "2026-09-18" }],
};

/** What it says when it has nothing at all. */
const NOTHING: Readiness = { status: "not_ready", model_key_present: false, replayable: [] };

/** Draw the first screen. */
function draw(readiness: Readiness) {
  return render(
    <Launchpad
      examples={EXAMPLES}
      failure={null}
      readiness={readiness}
      onOpen={() => undefined}
      onBuild={() => undefined}
    />,
  );
}

describe("with no model key", () => {
  it("test_the_keyless_sentence_is_word_for_word", () => {
    draw(NO_KEY_ONE_RECORDING);

    // Record 0012's sentence, word for word, with the day taken from the
    // readiness answer — never from a file name, a build date or a clock. It is
    // said twice: under the four cards, and again under the field it disables.
    expect(
      screen.getAllByText(
        "No model key configured — these four run from recordings made on 2026-09-18.",
      ),
    ).toHaveLength(2);
  });

  it("test_the_shared_sentence_names_the_oldest_day_it_describes", () => {
    draw({
      ...NO_KEY_ONE_RECORDING,
      replayable: [
        { example: "photonics", recording_date: "2026-09-20" },
        { example: "hormuz", recording_date: "2026-09-18" },
      ],
    });
    // Never more current than the oldest thing it describes.
    expect(screen.getAllByText(keylessSentence("2026-09-18")).length).toBeGreaterThan(0);
    expect(screen.queryByText(keylessSentence("2026-09-20"))).toBeNull();
  });

  it("test_nothing_is_silently_inert_without_a_key", () => {
    const { container } = draw(NO_KEY_ONE_RECORDING);

    // The card with a recording runs. It is a button, it is not disabled, and it
    // says on its own face that it plays a recording and when it was made.
    const recorded = screen.getByRole("button", {
      name: new RegExp(STARTING_SENTENCES[0]?.sentence ?? ""),
    });
    expect(recorded).not.toBeDisabled();
    expect(recorded.textContent).toContain("replay");
    expect(recorded.textContent).toContain("2026-09-18");

    // The three with nothing recorded are not buttons at all: they read *not yet
    // live*, with the reason underneath. There is no control that accepts an
    // interaction and does nothing.
    const notYet = container.querySelectorAll('[data-state="not-yet"]');
    expect(notYet).toHaveLength(STARTING_SENTENCES.length - 1);
    for (const card of notYet) {
      expect(card.querySelector("button")).toBeNull();
      expect(card.textContent).toContain("not yet live");
      expect(card.textContent).toContain("no model key");
    }

    // The field for a sentence of the reader's own is visibly disabled, and it
    // carries the same sentence saying why.
    const field = screen.getByLabelText("An event you think will happen");
    expect(field).toBeDisabled();
    const build = screen.getByRole("button", { name: "Build the map" });
    expect(build).toBeDisabled();
    expect(container.textContent).toContain(keylessSentence("2026-09-18"));
  });

  it("test_with_no_key_and_no_recording_every_card_says_so", () => {
    const { container } = draw(NOTHING);
    expect(container.querySelectorAll('[data-state="not-yet"]')).toHaveLength(
      STARTING_SENTENCES.length,
    );
    // And the shared sentence is not printed, because there is no day to name and
    // nothing it would be true of.
    expect(container.textContent).not.toContain("run from recordings made on");
    expect(screen.getByRole("button", { name: "Build the map" })).toBeDisabled();
  });

  it("test_the_map_that_is_already_drawn_still_opens", () => {
    draw(NOTHING);
    // The stored example needs no key and never did: it is a file on disk, and a
    // copy with nothing configured still reads the whole multiverse from it.
    expect(screen.getByRole("button", { name: /Strait of Hormuz/ })).not.toBeDisabled();
  });
});

describe("with a model key", () => {
  it("test_with_a_key_every_card_runs_live_and_nothing_says_replay", () => {
    const { container } = draw({ status: "ready", model_key_present: true, replayable: [] });

    expect(container.querySelectorAll('[data-state="not-yet"]')).toHaveLength(0);
    expect(container.textContent).not.toContain("No model key configured");
    expect(screen.getByLabelText("An event you think will happen")).not.toBeDisabled();
  });
});
