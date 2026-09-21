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
import type { StreamEvent } from "../events";
import { GenerationScreen } from "../GenerationScreen";
import { fold, type Growth, waitingFor } from "../growth";
import type { TheRun, WhereItHasGot } from "../theRun";
import { STARTED, THE_GROWTH, THE_SENTENCE } from "./aStream";

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
function aRunWeDrive(): TheRun & { arrive: (event: StreamEvent) => void } {
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
    arrive: (event: StreamEvent) => {
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
    expect(theStrip().textContent).toContain("nothing new for 23 s");
    // It sits beside the region and never inside it: a number that ticked
    // inside a polite region would be announced once a second.
    expect(said.textContent).not.toContain("nothing new for");
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
    expect(theStrip().textContent).toContain("nothing new for 23 s");

    // The first proposal lands.
    const first = THE_GROWTH[1];
    expect(first, "the worked run has no first proposal").toBeDefined();
    act(() => {
      run.arrive(first as StreamEvent);
    });

    // The count starts again from the arrival, not from the press.
    expect(theStrip().textContent).toContain("nothing new for 0 s");
    expect(theStrip().textContent).not.toContain("nothing new for 23 s");
    // And the sentence says what arrived and what is now being worked on —
    // which is the frontier the event itself carried, never a guess.
    expect(theSentence().textContent).toContain("A claim arrived:");
    expect(theSentence().textContent).toContain("Working on what follows from");

    // Four more seconds of silence, and the reading follows the clock.
    waitOut(4);
    expect(theStrip().textContent).toContain("nothing new for 4 s");
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
    expect(theStrip().textContent).not.toContain("nothing new for");
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
    expect(theStrip().textContent).not.toContain("nothing new for");

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
