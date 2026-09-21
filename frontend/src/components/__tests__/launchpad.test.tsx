/**
 * The first screen, read twice: once with a model key and once without one.
 *
 * **The second reading is the new half, and it is the blind spot a reader walked
 * into.** Every browser test in this repository has run keyless, so nobody ever
 * saw what a copy with a key actually offered — four rows that all called a
 * model, and a committed recording that could not be reached at all.
 *
 * So every claim below is made twice where the key could change it: the same
 * ways, in the same order, in the same words; a way that cannot be taken saying
 * why beside itself; and the recording still asking for a recording when a key
 * is present.
 *
 * **No figure in this file is typed.** What a live run costs is read off the
 * committed recording's own receipt — the same line the server reads — and the
 * screen is checked against that file rather than against a number somebody
 * wrote down here.
 */

import { readFileSync } from "node:fs";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Readiness, RecordingSummary } from "../../api/client";
import { howLong, Launchpad, STARTING_SENTENCES } from "../Launchpad";
import { asMoney } from "../ReceiptStrip";

/** The one stored example the server ships with. */
const EXAMPLES = [
  {
    id: "hormuz",
    title: "Strait of Hormuz",
    one_line: "The strait reopens, and what that causes.",
  },
];

/** Where the committed recording lives, read from the browser half's own folder. */
const THE_RECORDING_FILE = "../backend/recordings/hormuz.jsonl";

/**
 * The committed recording's own receipt and the day it was made, read off the
 * file the server reads.
 *
 * **The only measured price this product owns.** It is read here rather than
 * copied here so that a test claiming the screen prints what the server said is
 * comparing the screen with a measurement, not with a number somebody typed into
 * a fixture. Nothing at all when the file is not in this checkout, which is the
 * one case the whole suite already tolerates: a recording is made against a real
 * key by whoever holds one.
 */
function theRecordedRun(): RecordingSummary | null {
  let whole: string;
  try {
    whole = readFileSync(THE_RECORDING_FILE, "utf8");
  } catch {
    return null;
  }
  const lines = whole.trim().split("\n");
  const header = JSON.parse(lines[0] ?? "{}") as { recording_date?: string };
  for (const line of [...lines].reverse()) {
    const read = JSON.parse(line) as { event?: string; data?: Record<string, number> };
    if (read.event === "receipt" && read.data !== undefined) {
      return {
        example: "hormuz",
        recording_date: header.recording_date ?? "",
        calls: read.data.calls ?? null,
        seconds: read.data.seconds ?? null,
        dollars: read.data.dollars ?? null,
      };
    }
  }
  return null;
}

const RECORDED = theRecordedRun();

/** A recording with no receipt this engine could read: the three are absent together. */
const NO_RECEIPT: RecordingSummary = {
  example: "hormuz",
  recording_date: "2026-09-18",
  calls: null,
  seconds: null,
  dollars: null,
};

/**
 * What the server says about itself.
 *
 * @param key Whether a model key is configured.
 * @param replayable What it can play back, with what each recorded run cost.
 */
function saying(key: boolean, replayable: readonly RecordingSummary[] = []): Readiness {
  return {
    // Deliberately varied away from what the screen draws: this screen reads
    // the key and what can be played, and ignores whether the server called
    // itself ready. A copy with no key and a recording can do everything a
    // reviewer came to see.
    status: key || replayable.length > 0 ? "ready" : "not_ready",
    model_key_present: key,
    replayable: [...replayable],
    unreadable: [],
  };
}

/** Draw the first screen, with a way of catching what a press asks for. */
function draw(readiness: Readiness | null, readinessFailure: string | null = null) {
  const asked = vi.fn();
  const drawn = render(
    <Launchpad
      examples={EXAMPLES}
      failure={null}
      readiness={readiness}
      readinessFailure={readinessFailure}
      onOpen={() => undefined}
      onBuild={asked}
    />,
  );
  return { ...drawn, asked };
}

/** Every way on the screen, in the order it is drawn: its number, name and price. */
function theWays(container: HTMLElement): string[] {
  return [...container.querySelectorAll(".way__head")].map((head) =>
    [".way__number", ".way__name", ".way__cost"]
      .map((part) => head.querySelector(part)?.textContent ?? "")
      .join(" · "),
  );
}

/** The section of the screen one way to start is drawn in. */
function way(container: HTMLElement, which: string): HTMLElement {
  return container.querySelector(`.way--${which}`) as HTMLElement;
}

describe("the same four ways, with a key and without one", () => {
  it("test_the_same_ways_in_the_same_order_in_the_same_words_for_both_states_of_the_key", () => {
    // **INV-workbench.82.** One rendering read twice: the ways a reader is
    // offered do not depend on a setting nobody told them about.
    const withNone = draw(saying(false, RECORDED === null ? [] : [RECORDED]));
    const spelled = theWays(withNone.container);
    const withKey = draw(saying(true, RECORDED === null ? [] : [RECORDED]));

    expect(theWays(withKey.container)).toEqual(spelled);
    // And the words themselves, so that "the same both times" cannot be
    // satisfied by the same wrong words twice.
    expect(spelled).toEqual([
      "1 · Open the map · free · instant",
      "2 · Watch the recording · free",
      "3 · Run it live · calls a model",
      "4 · Build the map · calls a model",
    ]);
  });

  it("test_a_way_that_cannot_be_taken_says_why_beside_itself", () => {
    const { container } = draw(saying(false, RECORDED === null ? [] : [RECORDED]));

    // The two ways that call a model are drawn, not pressable, and carry the
    // reason in place — not in a banner over the screen, and not as a control
    // that has quietly gone missing.
    const live = way(container, "live");
    const rows = live.querySelectorAll("button.example");
    expect(rows).toHaveLength(STARTING_SENTENCES.length);
    for (const row of rows) {
      expect(row).toBeDisabled();
    }
    expect(within(live).getByText(/No model key is configured/).textContent).toContain(
      "The first two ways need none.",
    );

    // The same sentence under the form, which is the other way that calls a
    // model — and the form is visibly disabled rather than silently inert.
    const yours = way(container, "yours");
    expect(within(yours).getByLabelText("An event you think will happen")).toBeDisabled();
    expect(within(yours).getByRole("button", { name: "Build the map" })).toBeDisabled();
    expect(within(yours).getByText(/No model key is configured/)).toBeInTheDocument();

    // And the two free ways are untouched: no key was ever needed for either.
    expect(within(way(container, "open")).getByRole("button")).not.toBeDisabled();
  });

  it("test_with_a_key_nothing_is_greyed_and_the_recording_is_still_there", () => {
    const { container } = draw(saying(true, RECORDED === null ? [] : [RECORDED]));

    expect(container.querySelectorAll("button.example:disabled")).toHaveLength(0);
    expect(container.textContent).not.toContain("No model key is configured");
    expect(screen.getByLabelText("An event you think will happen")).not.toBeDisabled();

    // **The case that could not happen before.** With a key, the recording is
    // still on the screen and still pressable — which is how a reviewer who
    // holds a key tests the half of the product that needs none.
    const watching = within(way(container, "recording")).getByRole("button", {
      name: /Watch the recording/,
    });
    expect(watching).not.toBeDisabled();
    expect(watching.textContent).toContain("replay");
  });
});

describe("what each press asks for", () => {
  it("test_with_a_key_the_recording_still_asks_for_a_recording", () => {
    // The whole point of the field on the request: a key no longer means live.
    const { container, asked } = draw(saying(true, RECORDED === null ? [] : [RECORDED]));
    if (RECORDED === null) {
      return;
    }
    within(way(container, "recording"))
      .getByRole("button", { name: /Watch the recording/ })
      .click();

    expect(asked).toHaveBeenCalledTimes(1);
    expect(asked.mock.calls[0]?.[0]).toEqual({
      hypothesis: STARTING_SENTENCES[0]?.sentence,
      target: null,
      belief: null,
      start: "replay",
    });
  });

  it("test_a_live_row_asks_for_a_live_run_and_sends_the_sentence_as_typed", () => {
    const { container, asked } = draw(saying(true));
    const rows = within(way(container, "live")).getAllByRole("button", { name: /Run it live/ });
    expect(rows).toHaveLength(STARTING_SENTENCES.length);
    rows[0]?.click();

    expect(asked.mock.calls[0]?.[0]).toEqual({
      // Exactly as a reader would type it, which is what makes the replayed and
      // the live request identical bar the one field naming the start.
      hypothesis: STARTING_SENTENCES[0]?.sentence,
      target: null,
      belief: null,
      start: "live",
    });
  });

  it("test_a_sentence_of_your_own_is_a_live_run_and_says_so", () => {
    const { container, asked } = draw(saying(true));
    const yours = way(container, "yours");

    // It says out loud that it calls a model, and that its own price is not
    // known — with the one measurement this product owns named as another
    // example's rather than offered as an estimate of theirs.
    expect(yours.textContent).toContain("A sentence of your own calls a model");
    expect(yours.textContent).toContain("What it costs is not known before it runs");
    expect(yours.textContent).toContain("not an estimate of yours");

    const field = within(yours).getByLabelText("An event you think will happen");
    (field as HTMLInputElement).focus();
    const typed = "Something nobody has recorded.";
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(field, typed);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    within(yours).getByRole("button", { name: "Build the map" }).click();

    expect(asked.mock.calls[0]?.[0]).toMatchObject({ hypothesis: typed, start: "live" });
  });
});

describe("what a live run costs, said before the press", () => {
  it.skipIf(RECORDED === null)(
    "test_the_live_way_prints_what_the_recorded_receipt_says_and_the_day",
    () => {
      const receipt = RECORDED as RecordingSummary;
      const { container } = draw(saying(false, [receipt]));
      const measured = within(way(container, "live")).getByText(/The recorded run of/).textContent;

      // **Every figure compared with the file it came from**, never with a
      // number written into this test: the calls the receipt counted, the money
      // printed the way this product prints money, the duration in the words
      // this screen puts it in, and the day it was measured.
      expect(measured).toContain(`${receipt.calls} model calls`);
      expect(measured).toContain(asMoney(receipt.dollars as number));
      expect(measured).toContain(howLong(receipt.seconds as number));
      expect(measured).toContain(receipt.recording_date);

      // And it says whose run it describes, so nobody reads it as a quote.
      expect(way(container, "live").textContent).toContain(
        "made at the effort a recording is made with",
      );
    },
  );

  it("test_a_recording_with_no_readable_receipt_prints_no_figure_at_all", () => {
    // **INV-workbench.83.** A replay rebuilds the receipt rather than emitting
    // the recorded one, so a file that plays perfectly well can carry a receipt
    // this engine cannot read. That is an absence with a reason, never a guess
    // and never a blank.
    const { container } = draw(saying(false, [NO_RECEIPT]));
    const live = way(container, "live");

    expect(live.textContent).toContain("no measured price to state");
    expect(live.textContent).not.toContain("The recorded run of");
    // Nothing anywhere on the screen reads as money or as a length of time.
    expect(container.textContent).not.toMatch(/\$\s*\d/);
    expect(container.textContent).not.toMatch(/\d+\s+(seconds?|minutes?|model calls?)/);
  });

  it("test_nothing_is_printed_about_a_price_before_the_server_has_answered", () => {
    const { container } = draw(null);
    expect(container.textContent).not.toMatch(/\$\s*\d/);
    expect(container.textContent).toContain("no measured price to state");
  });
});

describe("what this copy can play", () => {
  it("test_the_sentences_with_nothing_recorded_are_named_rather_than_counted", () => {
    const { container } = draw(saying(false, RECORDED === null ? [] : [RECORDED]));
    if (RECORDED === null) {
      return;
    }
    const recording = way(container, "recording");

    // One row, for the one sentence there is a recording of.
    expect(recording.querySelectorAll("button.example")).toHaveLength(1);
    // And the other three are **named**, because they are not on this list to
    // be counted. The short name is not the recording's short name —
    // `export-controls` is an identifier, and an identifier is never words on
    // the screen.
    expect(recording.textContent).toContain(
      "Nothing is recorded yet for the midterms, export controls and photonic chips",
    );
    expect(recording.textContent).not.toContain("export-controls");
  });

  it("test_with_nothing_recorded_the_recording_way_says_why_and_stays_on_the_screen", () => {
    const { container } = draw(saying(true));
    const recording = way(container, "recording");

    // The way is still drawn, in its place, in its own words — and it says what
    // is missing. A way that vanished would teach a reader they imagined it.
    expect(recording.querySelectorAll("button.example")).toHaveLength(0);
    expect(recording.textContent).toContain("no recording of any of these sentences");
    // It does not blame the key, because watching a recording never needed one.
    expect(recording.textContent).not.toContain("No model key is configured");
  });

  it("test_a_recording_that_would_not_play_is_named_and_hides_nothing", () => {
    if (RECORDED === null) {
      return;
    }
    const said =
      "gulf-2026-08-02.jsonl could not be read: its header names no example, so there is " +
      "nothing to offer it against.";
    const { container } = draw({ ...saying(false, [RECORDED]), unreadable: [said] });

    // The server's own sentence, printed as it came — and the good recording
    // still plays, which is the other half of the same rule.
    expect(screen.getByText(said)).toBeInTheDocument();
    expect(way(container, "recording").querySelectorAll("button.example")).toHaveLength(1);
  });

  it("test_the_map_that_is_already_drawn_still_opens_with_nothing_configured", () => {
    const { container } = draw(saying(false));
    // The stored example needs no key and never did: it is a file on disk, and a
    // copy with nothing configured still reads the whole multiverse from it.
    expect(within(way(container, "open")).getByRole("button")).not.toBeDisabled();
  });
});

describe("before the server has answered, and after an ask that did not come back", () => {
  it("test_nothing_is_claimed_before_the_server_has_answered", () => {
    // **Null is not "no key".** Until the readiness answer arrives, nothing is
    // known about a key or a recording, and a screen reading *no model key* in
    // the meantime is asserting something nobody told it.
    const { container } = draw(null);

    expect(container.textContent).not.toContain("No model key is configured");
    expect(container.textContent).toContain("Asking the server whether a model key is configured.");
    expect(container.textContent).toContain("Asking the server which of these it has a recording");
    // The four ways are all there, so the screen does not grow rows as answers
    // land; what cannot be taken yet is drawn and says what is being waited for.
    expect(theWays(container)).toHaveLength(4);
    expect(container.querySelectorAll("button.example:disabled")).toHaveLength(
      STARTING_SENTENCES.length,
    );
  });

  it("test_an_ask_that_did_not_come_back_is_not_an_ask_still_in_flight", () => {
    // A request that failed and a request in flight are both an absent answer,
    // and with them folded into one the screen said *asking the server* for
    // ever over an ask that ended minutes ago.
    const said = "Nothing answered at /api/readyz — the server may not be running.";
    const { container } = draw(null, said);

    expect(container.textContent).not.toContain("Asking the server");
    expect(container.textContent).not.toContain("No model key is configured");
    // The server's own sentence, printed as it came, beside each way it
    // disables — and what to do about it, which is what tells an ask that got
    // no reply apart from an answer that said no.
    expect(
      screen.getAllByText(new RegExp(said.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))).length,
    ).toBeGreaterThan(0);
    expect(container.textContent).toContain("This page asks once: reload it to ask again.");
    expect(
      within(way(container, "yours")).getByLabelText("An event you think will happen"),
    ).toBeDisabled();
  });
});

describe("no figure on this screen was typed into it", () => {
  it("test_no_file_drawing_the_four_ways_holds_a_price_or_a_duration", () => {
    // **INV-workbench.83, read off the source.** A price or a duration written
    // into a component is a number nobody computed, sitting on the first thing a
    // reviewer reads — and it moves every time the prompt or the effort changes.
    // The prose is stripped first, because this chapter's own argument quotes
    // the shape of the sentence and a check that read the prose would punish
    // saying so.
    for (const path of ["src/components/Launchpad.tsx", "src/components/launchpad.css"]) {
      const whole = readFileSync(path, "utf8");
      expect(whole.length).toBeGreaterThan(0);
      const code = whole.replaceAll(/\/\*[\s\S]*?\*\//g, " ").replaceAll(/\/\/[^\n]*/g, " ");
      expect(code).not.toMatch(/\$\s*\d/);
      expect(code).not.toMatch(/\d+\s*(dollars?|minutes?|hours?)\b/);
    }
  });
});
