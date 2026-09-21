/**
 * The first screen with no model key.
 *
 * This is the screen a reviewer with nothing configured meets, so it is the
 * screen that has to be honest about what this copy can and cannot do — card by
 * card, in one sentence each, with nothing greyed out that would in fact work.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Readiness } from "../../api/client";
import { keylessSentence, Launchpad, STARTING_SENTENCES } from "../Launchpad";

/** The one stored example the server ships with. */
const EXAMPLES = [
  {
    id: "hormuz",
    title: "Strait of Hormuz",
    one_line: "The strait reopens, and what that causes.",
  },
];

/** What the server says when it has no key and all four examples recorded, one day. */
const NO_KEY_ALL_FOUR: Readiness = {
  status: "not_ready",
  model_key_present: false,
  replayable: STARTING_SENTENCES.map((one) => ({
    example: one.example,
    recording_date: "2026-09-18",
  })),
  unreadable: [],
};

/** What the server says about itself when it has no key and one recording. */
const NO_KEY_ONE_RECORDING: Readiness = {
  // Deliberately `not_ready`: this screen reads what can be replayed and whether
  // a key is configured, and ignores this field. A program with no key and a
  // recording can do everything a reviewer came to see.
  status: "not_ready",
  model_key_present: false,
  replayable: [{ example: "hormuz", recording_date: "2026-09-18" }],
  unreadable: [],
};

/** What it says when it has nothing at all. */
const NOTHING: Readiness = {
  status: "not_ready",
  model_key_present: false,
  replayable: [],
  unreadable: [],
};

/**
 * What it says when a file in the recordings folder could not be read.
 *
 * The one that could is still on the list and still plays: a bad file never
 * hides the good ones, and it never hides itself either.
 */
const ONE_BAD_FILE: Readiness = {
  status: "not_ready",
  model_key_present: false,
  replayable: [{ example: "hormuz", recording_date: "2026-09-18" }],
  unreadable: [
    "gulf-2026-08-02.jsonl could not be read: its header names no example, so there is nothing to offer it against.",
  ],
};

/**
 * The section that offers to build a map, on its own.
 *
 * The screen holds two lists of the same shape — the maps already drawn, and
 * the sentences that build one — and counting rows across both couples a claim
 * about one to the fixture behind the other.
 */
function building(container: HTMLElement): HTMLElement {
  return container.querySelector(".launchpad__build") as HTMLElement;
}

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
    draw(NO_KEY_ALL_FOUR);

    // Record 0012's sentence, word for word, with the day taken from the
    // readiness answer — never from a file name, a build date or a clock. It is
    // under the four cards, and the field it disables carries it too.
    expect(
      screen.getByText(
        "No model key configured — these four run from recordings made on 2026-09-18.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("An event you think will happen")).toBeDisabled();
  });

  it("test_the_shared_sentence_is_printed_only_when_it_is_true", () => {
    // **One recording out of four.** Record 0012's sentence would be a screen
    // claiming something a reader can see is false — three cards reading *not
    // yet live* under a line saying these four run from recordings.
    const { container } = draw(NO_KEY_ONE_RECORDING);
    expect(container.textContent).not.toContain("these four run from recordings");
    expect(
      screen.getByText(
        "No model key configured — one of these four runs from recordings, made on " +
          "2026-09-18; the midterms, export controls and photonic chips have nothing " +
          "recorded yet.",
      ),
    ).toBeInTheDocument();

    // **All four, but not all on one day.** The sentence is never more current
    // than the oldest thing it describes, and it says there is more than one day.
    const several = draw({
      ...NO_KEY_ALL_FOUR,
      replayable: STARTING_SENTENCES.map((one, place) => ({
        example: one.example,
        recording_date: place === 0 ? "2026-09-18" : "2026-09-20",
      })),
    });
    expect(several.container.textContent).toContain(
      "No model key configured — these four run from recordings, the oldest made on 2026-09-18.",
    );
    expect(several.container.textContent).not.toContain(keylessSentence("2026-09-20"));
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

    // **The three with nothing recorded get no card at all.** They used to be
    // three rows reading *not yet live*, side by side with the one door, taking
    // the whole of this column — a graveyard with a door in it. What is left of
    // them is the line under the card, which already named them: *the other
    // three have nothing recorded yet*. Nothing on this screen accepts an
    // interaction and does nothing, and now nothing on it is a row that cannot
    // be taken up either.
    expect(container.querySelectorAll('[data-state="not-yet"]')).toHaveLength(0);
    // Counted inside the section that offers them, so that the list of maps
    // already drawn — a different section, fed by a different route — cannot
    // change this number.
    expect(building(container).querySelectorAll(".example")).toHaveLength(1);
    expect(container.textContent).not.toContain("not yet live");
    // **The three with no card are named**, because they are not on the screen
    // to be counted: a line reading *the other three* points at sentences that
    // are no longer there. The short name is not the recording's short name —
    // `export-controls` is an identifier, and an identifier is never words on
    // the screen.
    expect(container.textContent).toContain(
      "the midterms, export controls and photonic chips have nothing recorded yet",
    );
    // And the three sentences themselves are not on the screen as dead text.
    for (const gone of STARTING_SENTENCES.slice(1)) {
      expect(container.textContent).not.toContain(gone.sentence);
    }

    // The field for a sentence of the reader's own is visibly disabled, and it
    // says why in the same words, with the one thing that is true of it added:
    // there is no recording of a sentence somebody just typed.
    const field = screen.getByLabelText("An event you think will happen");
    expect(field).toBeDisabled();
    const build = screen.getByRole("button", { name: "Build the map" });
    expect(build).toBeDisabled();
    expect(container.textContent).toContain(
      "A sentence of your own needs the model, and there is no recording of one.",
    );
  });

  it("test_with_no_key_and_no_recording_the_section_says_so_in_one_line", () => {
    const { container } = draw(NOTHING);
    // No cards, because there is nothing to offer — and a heading reading *or
    // watch one build itself* over an empty list is worse than a sentence.
    expect(container.querySelectorAll("[data-state]")).toHaveLength(0);
    expect(container.textContent).toContain(
      "No model key configured, and nothing recorded — so the strait, the midterms, export " +
        "controls and photonic chips cannot be shown building here.",
    );
    // It points at the thing that does work with neither, which is the whole
    // multiverse from a file on disk.
    expect(container.textContent).toContain("The map above is already drawn and needs neither.");
    // And the shared sentence is not printed, because there is no day to name and
    // nothing it would be true of.
    expect(container.textContent).not.toContain("run from recordings made on");
    expect(screen.getByRole("button", { name: "Build the map" })).toBeDisabled();
  });

  it("test_nothing_is_claimed_before_the_server_has_answered", () => {
    // **Null is not "no key".** Until the readiness answer arrives, nothing is
    // known about a key or a recording, and a screen that reads *no model key*
    // in the meantime is asserting something nobody told it — which is the
    // traceability rule, on the first screen a reviewer sees.
    const { container } = render(
      <Launchpad
        examples={EXAMPLES}
        failure={null}
        readiness={null}
        onOpen={() => undefined}
        onBuild={() => undefined}
      />,
    );
    expect(container.textContent).not.toContain("No model key configured");
    expect(container.textContent).not.toContain("not yet live");
    // Every sentence is still on the screen, each saying what is being waited
    // for — and none of them is a control yet.
    expect(container.querySelectorAll('[data-state="asking"]')).toHaveLength(
      STARTING_SENTENCES.length,
    );
    for (const one of STARTING_SENTENCES) {
      expect(container.textContent).toContain(one.sentence);
    }
    expect(screen.getByLabelText("An event you think will happen")).toBeDisabled();
    expect(container.textContent).toContain("Asking the server whether a model key is configured.");
  });

  it("test_an_ask_that_did_not_come_back_is_not_an_ask_still_in_flight", () => {
    // **The state this screen got wrong twice.** A request that failed and a
    // request in flight are both an absent answer, and with them folded into
    // one the launchpad said *asking the server* for ever over an ask that
    // ended minutes ago — while the strip below it printed the failure. A
    // screen asserting a question that is not being asked is a state nobody
    // can trace to an input, on the first screen a reviewer sees.
    const said = "Nothing answered at /api/readyz — the server may not be running.";
    const { container } = render(
      <Launchpad
        examples={EXAMPLES}
        failure={null}
        readiness={null}
        readinessFailure={said}
        onOpen={() => undefined}
        onBuild={() => undefined}
      />,
    );

    // Not a word about a question in flight, because none is.
    expect(container.textContent).not.toContain("Asking the server");
    // Nor a word about what this copy can do, because nobody has said.
    expect(container.textContent).not.toContain("No model key configured");
    expect(container.textContent).not.toContain("not yet live");

    // Every sentence is still there, each in the vocabulary's own words for an
    // ask that got no reply, and none of them is a control.
    const cards = container.querySelectorAll('[data-state="no-answer"]');
    expect(cards).toHaveLength(STARTING_SENTENCES.length);
    for (const card of cards) {
      expect(card.querySelector("button")).toBeNull();
      expect(card.textContent).toContain("The ask did not come back");
    }

    // And the server's own sentence, printed as it came, **once under the
    // cards** rather than on each of them: it is one fact about this copy and
    // not four facts about four examples. The field below carries it a second
    // time because the field is a different control with a different reason to
    // be disabled — which is exactly what record 0012's own sentence does.
    const section = building(container).textContent ?? "";
    expect(section).toContain(said);
    expect(section.split(said).length - 1).toBe(1);

    // The field is disabled and says the same thing, with the one part that is
    // true of it: nothing recorded can stand in for a sentence nobody has typed.
    expect(screen.getByLabelText("An event you think will happen")).toBeDisabled();
    expect(container.textContent).toContain(
      "whether a sentence of your own could be turned into a map is not known",
    );
  });

  it("test_a_recording_that_would_not_play_is_named_and_hides_nothing", () => {
    // A reviewer who put a file in the recordings folder and then counts three
    // cards where they expected four is owed the reason, in the server's own
    // sentence, rather than left to wonder whether they put it in the wrong
    // place. It is quiet and under the cards, because it is about this copy
    // rather than about any map.
    const { container } = draw(ONE_BAD_FILE);
    const said = ONE_BAD_FILE.unreadable[0] as string;
    expect(screen.getByText(said)).toBeInTheDocument();
    // The browser writes none of it: the whole sentence came from the server.
    expect(container.textContent).toContain(said);

    // **And the good file still plays.** A bad one never hides the others, so
    // the card with a recording still offers its run.
    const playing = container.querySelectorAll('[data-state="replay"]');
    expect(playing).toHaveLength(1);
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
    const { container } = draw({
      status: "ready",
      model_key_present: true,
      replayable: [],
      unreadable: [],
    });

    expect(container.querySelectorAll('[data-state="not-yet"]')).toHaveLength(0);
    expect(container.textContent).not.toContain("No model key configured");
    expect(screen.getByLabelText("An event you think will happen")).not.toBeDisabled();

    // **All four are offered, and every one of them is a control.** With a key
    // there is nothing this copy cannot run, so nothing is collapsed away — the
    // rule is *a card for everything this copy can do*, and with a key that is
    // all of them.
    expect(container.querySelectorAll('[data-state="live"]')).toHaveLength(
      STARTING_SENTENCES.length,
    );
    for (const one of STARTING_SENTENCES) {
      expect(screen.getByRole("button", { name: new RegExp(one.sentence) })).not.toBeDisabled();
    }
  });

  it("test_a_key_and_some_recordings_still_offers_all_four_live", () => {
    // The fourth case: a key **and** recordings. The key wins — every card runs
    // live — and nothing says *replay*, because nothing is being replayed.
    const { container } = draw({
      status: "ready",
      model_key_present: true,
      replayable: [{ example: "hormuz", recording_date: "2026-09-18" }],
      unreadable: [],
    });
    expect(container.querySelectorAll('[data-state="live"]')).toHaveLength(
      STARTING_SENTENCES.length,
    );
    expect(container.textContent).not.toContain("replay");
    expect(container.textContent).not.toContain("No model key configured");
  });
});
