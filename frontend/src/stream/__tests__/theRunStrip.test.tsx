/**
 * The test that would have caught what Kent saw.
 *
 * On 2026-09-21 he ran the app with his own model key, pressed *Watch it build*,
 * and said *"i don't see anything happening after pressing watch it build"*.
 * Nothing was broken: the run's first event says only that the run has started
 * — it is sent before any model call and arrives at once — and the **first
 * proposal** comes back about twenty-three seconds later, with later ones fifty
 * to a hundred and ten seconds apart. In between the screen held one dashed
 * rectangle and nothing else, and the one sentence that said what the run was
 * doing was passed to the frame as *spoken only* and clipped by a stylesheet to
 * a one-pixel box.
 *
 * That is the shape of every test below: the run starts, and then nothing for
 * twenty-three seconds.
 *
 * **No test in the suite could have seen it.** Every browser test runs with an
 * empty model key and plays a recording at four tenths of a second an event, so
 * no test had ever met a real silence — and the one browser test that looked at
 * this element **asserted the clipping**.
 *
 * So this test injects the adverse timing instead of waiting for it: fake
 * timers, a real fold of the real events, and the screen rendered into a
 * simulated page. It is tier 2 of decision record 0008 — a change whose
 * correctness is about timing gets a no-browser twin that produces the bad
 * timing on purpose — and it holds four things:
 *
 * 1. the strip is **visible**, and the sentence a screen reader hears is the
 *    sentence on the page, in one element;
 * 2. after twenty-three seconds of silence it reads the wait, and it names what
 *    is being held open;
 * 3. an arrival starts the count again;
 * 4. **a replay shows no seconds**, because at the pace we set a replay at the
 *    number would reset twice a second and would be measuring our own pacing.
 *
 * It asserts no value anywhere. The seconds it checks are the seconds it
 * advanced the clock by, which is the same number read back through the product
 * rather than a figure written down here.
 */

import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { theOpeningLine, whatChanged } from "../../a11y/growth";
import type { WorldView } from "../../world";
import { inFewWords } from "../../world/naming";
import type { Activity, StreamEvent } from "../events";
import { GenerationScreen } from "../GenerationScreen";
import { fold, type Growth, waitingFor } from "../growth";
import type { TheRun, WhereItHasGot } from "../theRun";
import {
  A_VERY_LONG_THOUGHT,
  activity,
  FOUND,
  REFUSED,
  SEARCHING,
  STARTED,
  THE_GROWTH,
  THE_SENTENCE,
  THINKING,
} from "./aStream";

// The map draws on a canvas the simulated page cannot measure, and what it draws
// has tests of its own. Here it stands in for itself: this file is about the
// foot of the screen.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({ world }: { world: WorldView }) => (
    <div data-testid="the-map">{`${world.claims.length} claims`}</div>
  ),
}));

/**
 * A run somebody else is driving, so the test can hand it one event at a time.
 *
 * It is the real interface, with the real fold behind it and the real sentences
 * the live region says — everything but the request. Nothing here paces itself:
 * the only clock in this file is the fake one.
 */
function aRunWeDrive(): TheRun & { arrive: (event: StreamEvent | Activity) => void } {
  const opening = waitingFor(THE_SENTENCE, null);
  let where: WhereItHasGot = { growth: opening, saying: theOpeningLine(opening) };
  const watchers = new Set<() => void>();
  return {
    asked: { hypothesis: THE_SENTENCE, target: null, belief: null },
    press: "press 1",
    now: () => where,
    watch: (told: () => void) => {
      watchers.add(told);
      return () => {
        watchers.delete(told);
      };
    },
    letGo: () => {},
    arrive: (event: StreamEvent | Activity) => {
      const grown = fold(where.growth, event);
      where = { growth: grown, saying: sayingFor(where.growth, grown, where.saying) };
      for (const told of watchers) {
        told();
      }
    },
  };
}

/** What the region says after this event, keeping the last line when nothing changed. */
function sayingFor(was: Growth, now: Growth, lastSaid: string): string {
  const said = whatChanged(was, now);
  return said === "" ? lastSaid : said;
}

/** The strip's printed sentence — the same element the live region is. */
function theSentence(): HTMLElement {
  const said = document.querySelector(".run-strip .map-live");
  expect(said, "there is no strip at the foot of the screen").not.toBeNull();
  return said as HTMLElement;
}

/** What the strip reads, whole: the word, the sentence and the reading. */
function theStrip(): HTMLElement {
  return document.querySelector(".run-strip") as HTMLElement;
}

/** Move the fake clock on, letting React redraw whatever the ticks changed. */
function waitOut(seconds: number): void {
  act(() => {
    vi.advanceTimersByTime(seconds * 1000);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the foot of the screen says what a live run is doing", () => {
  it("test_the_visible_strip_says_what_the_run_is_waiting_for", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );

    // The run has started — that event is sent before any model call and
    // arrives at once — and no proposal has come back. This is the moment Kent
    // sat in front of for twenty-three seconds.
    act(() => {
      run.arrive(STARTED);
    });

    // **Printed, not only spoken.** The sentence is inside the polite region
    // rather than beside a copy of it, so a change to one is a change to both.
    const said = theSentence();
    expect(said.getAttribute("aria-live")).toBe("polite");
    expect(said).toBeVisible();
    // And it is the run's own sentence, naming what is being held open.
    expect(said.textContent).toContain(THE_SENTENCE);
    expect(said.textContent).toContain("held open");
    // The state, in one word, in the box the foot already uses.
    expect(theStrip().getAttribute("data-state")).toBe("live");

    // Twenty-three seconds of nothing at all.
    waitOut(23);

    // The reading is what the clock was advanced by, read back through the
    // product. Nothing here is a figure somebody wrote down.
    expect(theStrip().textContent).toContain("nothing new on the map for 23 s");
    // It sits beside the region and never inside it: a number that ticked
    // inside a polite region would be announced once a second.
    expect(said.textContent).not.toContain("nothing new on the map for");
    expect(document.querySelector(".run-strip__waited")?.getAttribute("aria-hidden")).toBeNull();
  });

  it("test_an_arrival_resets_the_count", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
    });
    waitOut(23);
    expect(theStrip().textContent).toContain("nothing new on the map for 23 s");

    // The first proposal lands.
    const first = THE_GROWTH[1];
    expect(first, "the worked run has no first proposal").toBeDefined();
    act(() => {
      run.arrive(first as StreamEvent);
    });

    // The count starts again from the arrival, not from the press.
    expect(theStrip().textContent).toContain("nothing new on the map for 0 s");
    expect(theStrip().textContent).not.toContain("nothing new on the map for 23 s");
    // And the sentence says what arrived and what is now being worked on —
    // which is the frontier the event itself carried, never a guess.
    expect(theSentence().textContent).toContain("A claim arrived:");
    expect(theSentence().textContent).toContain("Working on what follows from");

    // Four more seconds of silence, and the reading follows the clock.
    waitOut(4);
    expect(theStrip().textContent).toContain("nothing new on the map for 4 s");
  });

  it("test_a_replay_shows_no_seconds", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={true} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
    });
    waitOut(23);

    // A replay is paced by the server, so a count of seconds would be measuring
    // our own pacing rather than any wait. The sentence is printed exactly as it
    // is on a live run; the reading is simply not there.
    expect(theStrip().getAttribute("data-state")).toBe("replay");
    expect(theSentence()).toBeVisible();
    expect(theSentence().textContent).toContain("held open");
    expect(theStrip().textContent).not.toContain("nothing new on the map for");
    expect(document.querySelector(".run-strip__waited")).toBeNull();
  });

  it("test_a_finished_run_stops_counting_and_keeps_its_sentence", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      for (const event of THE_GROWTH) {
        run.arrive(event);
      }
      run.arrive({ event: "done", reason: "reached_terminal", claims: 7, links: 8, rejected: 1 });
    });

    // Nothing is being waited for any more, so there is nothing to measure.
    expect(theStrip().getAttribute("data-state")).toBe("finished");
    expect(document.querySelector(".run-strip__waited")).toBeNull();
    waitOut(30);
    expect(theStrip().textContent).not.toContain("nothing new on the map for");

    // Why it stopped is said once, in the strip's own sentence, and printed
    // exactly once on the page. It used to be printed twice — once here and
    // once in a second strip of prose below it.
    const why = theSentence().textContent ?? "";
    expect(why).toContain("The map is finished");
    const printed = (document.body.textContent ?? "").split("The map is finished");
    expect(printed).toHaveLength(2);
  });

  it("test_the_run_details_in_the_panel_do_not_claim_arrivals_on_an_empty_map", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
    });

    // Where this map is coming from is in the panel now, not in an always-on
    // strip at the foot — and what it says is true of a map with nothing on it,
    // which is what the line it replaced was not.
    expect(screen.getByText("Run details")).toBeVisible();
    const panel = document.querySelector(".inspector")?.textContent ?? "";
    expect(panel).toContain(STARTED.generation_id);
    expect(panel).toContain("/api/generate");
    expect(panel).toContain("Nothing on this map is typed in");
    expect(panel).not.toContain("arrived from");

    // And nothing at the foot of the screen repeats it.
    expect(theStrip().textContent).not.toContain(STARTED.generation_id);
  });
});

/**
 * The two quiet lines under the sentence, whichever of them is there.
 *
 * They are read by the class the strip draws them with rather than by their
 * words, so that a test that looks for words the strip never printed fails on
 * the words rather than on finding nothing at all.
 */
function theQuietLines(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>(".run-strip__doing-line")];
}

/** Everything the two quiet lines say, joined, or the empty string when neither is there. */
function whatIsBeingDone(): string {
  return theQuietLines()
    .map((line) => line.textContent ?? "")
    .join(" ");
}

describe("the foot of the screen says what the model is doing right now", () => {
  it("test_the_strip_prints_the_search_the_model_just_ran", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
    });

    // Fourteen seconds into a call that will take another two minutes, the
    // model issues a web search. This is the first thing in this product that
    // reaches the screen inside a call rather than at the end of one.
    act(() => {
      run.arrive(SEARCHING);
    });
    expect(whatIsBeingDone()).toContain(`searching the web: "${SEARCHING.text}"`);

    // What came back replaces it: one line about the search, latest only, so
    // the strip never grows a list.
    act(() => {
      run.arrive(FOUND);
    });
    expect(whatIsBeingDone()).toContain(`found: ${FOUND.text}`);
    expect(whatIsBeingDone()).not.toContain(SEARCHING.text);

    // And the count of silence is untouched by it: the counter measures how
    // long it has been since anything landed **on the map**, which is what its
    // words say, and an activity line lands on neither.
    waitOut(9);
    expect(theStrip().textContent).toContain("nothing new on the map for 9 s");
  });

  it("test_the_thinking_line_is_the_models_own_words_and_says_so", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
      run.arrive(THINKING);
    });

    // Printed word for word, and labelled as the model's, because it is the one
    // line here about the model's mind rather than about a fact with a source.
    expect(whatIsBeingDone()).toContain(`the model, in its own words: ${THINKING.text}`);

    // The two lines stand together: a search and a thought are two different
    // things and neither replaces the other.
    act(() => {
      run.arrive(SEARCHING);
    });
    expect(whatIsBeingDone()).toContain(SEARCHING.text);
    expect(whatIsBeingDone()).toContain(THINKING.text);
    expect(theQuietLines()).toHaveLength(2);
  });

  it("test_a_long_line_is_cut_at_a_word_and_stays_one_line", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
      run.arrive(A_VERY_LONG_THOUGHT);
    });

    const printed = whatIsBeingDone();
    // Shorter than what arrived, ended with an ellipsis, and cut where a word
    // ends rather than through the middle of one.
    expect(printed).not.toContain(A_VERY_LONG_THOUGHT.text);
    expect(printed).toContain("…");
    const kept = printed.slice(0, printed.indexOf("…"));
    expect(A_VERY_LONG_THOUGHT.text.startsWith(kept.slice(kept.indexOf(":") + 2))).toBe(true);
    expect(A_VERY_LONG_THOUGHT.text.charAt(kept.slice(kept.indexOf(":") + 2).length)).toBe(" ");
  });

  it("test_both_lines_sit_outside_the_live_region", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
      run.arrive(SEARCHING);
      run.arrive(THINKING);
    });

    // They change every few seconds. A polite region that read them out would
    // be reading a stopwatch over the top of the map being built.
    expect(theSentence().textContent).not.toContain("searching the web");
    expect(theSentence().textContent).not.toContain("in its own words");
    expect(theQuietLines()).toHaveLength(2);
    for (const line of theQuietLines()) {
      // Never announced, and never hidden either: plain text a screen reader
      // reaches by walking the page, like every other quiet reading here.
      expect(line.closest("[aria-live]")).toBeNull();
      expect(line.getAttribute("aria-hidden")).toBeNull();
      expect(line.closest("[aria-hidden]")).toBeNull();
    }
  });

  it("test_a_claim_arriving_clears_the_lines_that_were_about_it", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    // Up to and including the claim the next call works on: the war-risk
    // premium, which is the claim the worked run's next proposal hangs off.
    act(() => {
      for (const event of THE_GROWTH.slice(0, 3)) {
        run.arrive(event);
      }
    });

    // Two calls are out. One is working on the reader's own claim; one is
    // working on the war-risk premium.
    act(() => {
      run.arrive(activity("searching", "an open-ended search about the strait itself", "H"));
      run.arrive(THINKING);
    });
    expect(whatIsBeingDone()).toContain("an open-ended search about the strait itself");
    expect(whatIsBeingDone()).toContain(THINKING.text);

    // The claim the second call was working on is answered: Brent arrives,
    // hanging off the war-risk premium.
    const answers = THE_GROWTH[4];
    expect(answers, "the worked run has no proposal hanging off the premium").toBeDefined();
    act(() => {
      run.arrive(answers as StreamEvent);
    });

    // The thinking line was about that claim and goes. The search line was
    // about a different claim, whose call is still out, and stays.
    expect(whatIsBeingDone()).not.toContain(THINKING.text);
    expect(whatIsBeingDone()).toContain("an open-ended search about the strait itself");
  });

  it("test_a_refusal_is_said_on_the_strip_in_the_models_own_words", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      for (const event of THE_GROWTH.slice(0, 7)) {
        run.arrive(event);
      }
      run.arrive(SEARCHING);
    });

    act(() => {
      run.arrive(REFUSED);
    });

    // This is the moment Kent is looking at the foot of the screen, not at the
    // panel: what the model proposed, in its own words, and the rule's own
    // sentence for why the map would not take it.
    const said = theSentence().textContent ?? "";
    expect(said).toContain("refused");
    expect(said).toContain(inFewWords(REFUSED.claim_in_words));
    for (const reason of REFUSED.violations) {
      expect(said).toContain(reason.message);
    }

    // And the call that was out has come back, so nothing claims it is still
    // searching.
    expect(whatIsBeingDone()).not.toContain(SEARCHING.text);
  });

  it("test_a_replay_shows_no_activity_even_if_one_is_fed_to_it", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={true} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      run.arrive(STARTED);
      run.arrive(SEARCHING);
      run.arrive(THINKING);
    });

    // A recording never holds one and a replay never sends one. If one reaches
    // this screen anyway, the screen shows nothing: it is the same difference a
    // replay already makes for the seconds.
    expect(theStrip().getAttribute("data-state")).toBe("replay");
    expect(theStrip().textContent).not.toContain("searching the web");
    expect(theStrip().textContent).not.toContain("in its own words");
    expect(theQuietLines()).toHaveLength(0);
    // And the sentence is the one a replay always said.
    expect(theSentence().textContent).toContain("held open");
  });

  it("test_a_run_that_has_stopped_says_nothing_about_what_the_model_is_doing", () => {
    const run = aRunWeDrive();
    render(
      <GenerationScreen run={run} replaying={false} onRunAgain={() => {}} onLeave={() => {}} />,
    );
    act(() => {
      for (const event of THE_GROWTH) {
        run.arrive(event);
      }
      run.arrive(SEARCHING);
      run.arrive(THINKING);
    });
    expect(theQuietLines()).toHaveLength(2);

    act(() => {
      run.arrive({ event: "done", reason: "reached_terminal", claims: 7, links: 8, rejected: 1 });
    });

    // Nothing is out, so nothing is being done. The lines go with the seconds.
    expect(theQuietLines()).toHaveLength(0);
    expect(theStrip().textContent).not.toContain("searching the web");
  });
});
