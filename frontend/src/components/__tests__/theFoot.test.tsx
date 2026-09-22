/**
 * One band at the foot of a map, never three.
 *
 * **What Kent saw.** He ran the app live on 2026-09-22 and said of the foot:
 * *"the triple nested bottom bar … [is] somewhat garish"*. Three boxes were
 * stacked across the bottom of the screen, each with its own hairline and its
 * own raised surface — what the last keystroke did, what the run was doing, and
 * where every number on the map came from. Three rules say three unrelated
 * things are competing and nothing says which one to read.
 *
 * So the foot is one band with at most two rows in every state, and this holds
 * that line in the four states a reader can put the screen into: a stored map, a
 * replay still arriving, a live run with the model saying what it is doing, and
 * a run that has finished.
 *
 * **What a reader needs at the foot, and where each of the four lives.** What
 * the run is doing, and how long since anything happened — the run's own row.
 * The last key they pressed, and where this map came from — the quiet grey row
 * under it. Never more than those two rows: while a live run is saying what the
 * model is doing, that *is* the second row, and the quiet one stands down until
 * it stops.
 *
 * **Nothing here asserts a line of copy.** Each state is asked how many rows it
 * drew and which boxes they are in, never which words are in them: the words of
 * the run's sentence, the seconds and the provenance belong to other chapters
 * and are being rewritten beside this one.
 */

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { SEARCHING, THE_GROWTH, THE_SENTENCE, THINKING } from "../../stream/__tests__/aStream";
import type { Activity, StreamEvent } from "../../stream/events";
import { GenerationScreen } from "../../stream/GenerationScreen";
import { fold, waitingFor } from "../../stream/growth";
import type { TheRun, WhereItHasGot } from "../../stream/theRun";
import { aClaim, aWorld } from "../../test/aMap";
import type { Selection, WorldView } from "../../world";
import { MapScreen } from "../MapScreen";

// The map draws on a canvas a simulated page cannot measure, and what it draws
// has tests of its own. Here it stands in for itself: one button per claim, each
// doing what pointing at that claim on the real canvas does.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({
    world,
    onSelect,
  }: {
    world: WorldView;
    onSelect: (selection: Selection) => void;
  }) => (
    <div data-testid="the-map">
      {world.claims.map((claim) => (
        <button
          key={claim.id}
          type="button"
          data-testid={`point-at-${claim.id}`}
          onClick={() => onSelect({ kind: "claim", id: claim.id })}
        >
          {claim.id}
        </button>
      ))}
    </div>
  ),
}));

beforeAll(() => {
  // A simulated page does no measuring at all, and the panel measures its own
  // edges the moment it is drawn.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

/** A run somebody else is driving, so a test can hand it one event at a time. */
function aRunWeDrive(): TheRun & { arrive: (event: StreamEvent | Activity) => void } {
  const opening = waitingFor(THE_SENTENCE, null);
  let where: WhereItHasGot = { growth: opening, saying: "" };
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
      where = { growth: fold(where.growth, event), saying: where.saying };
      for (const told of watchers) {
        told();
      }
    },
  };
}

/** The one band at the foot. There is exactly one, and this is it. */
function theBand(): HTMLElement {
  const bands = document.querySelectorAll<HTMLElement>(".map-foot");
  expect(bands.length, "the foot of the map is not one band").toBe(1);
  return bands[0] as HTMLElement;
}

/**
 * How many rows the band drew.
 *
 * Every row carries the one class that says it is one, so a row added in either
 * of the two components that fill this band is counted here rather than missed.
 */
function howManyRows(): number {
  return document.querySelectorAll(".map-foot__row").length;
}

/** Every box the foot used to be three of, and whether it is inside the band. */
function whatIsInTheBand(): Record<string, boolean | "not on the screen"> {
  const band = theBand();
  const answer: Record<string, boolean | "not on the screen"> = {};
  for (const hook of [".run-strip", ".map-status", ".map-origin", ".map-status__mark"]) {
    const found = document.querySelector(hook);
    answer[hook] = found === null ? "not on the screen" : band.contains(found);
  }
  return answer;
}

/** A map building itself, with these events already folded into it. */
function aRunThatHasGotTo(events: readonly (StreamEvent | Activity)[], replaying: boolean) {
  const run = aRunWeDrive();
  const drawn = render(
    <GenerationScreen run={run} replaying={replaying} onRunAgain={() => {}} onLeave={() => {}} />,
  );
  act(() => {
    for (const event of events) {
      run.arrive(event);
    }
  });
  return { run, ...drawn };
}

/** The stored map, with two claims a reader can tell apart. */
function theStoredMap() {
  const world = aWorld({
    claims: [
      aClaim({ id: "H", kind: "hypothesis", claim: "The strait reopens to commercial transit." }),
      aClaim({ id: "B", claim: "Brent crude settles below sixty-eight dollars." }),
    ],
  });
  return render(
    <MapScreen
      base={world}
      branches={[]}
      source={
        {
          readWorld: () => Promise.resolve(world),
          readConditional: () => new Promise(() => {}),
        } as never
      }
      insteadOfTheEngine={null}
      onLeave={() => {}}
    />,
  );
}

describe("the foot of a map is one band with at most two rows", () => {
  it("test_a_stored_map_draws_one_band_with_one_quiet_row", () => {
    theStoredMap();

    // Nothing is being generated and nothing has been asked of the engine, so
    // the only row is the quiet one: what the last key did, and where every
    // number on this map came from.
    expect(howManyRows()).toBe(1);
    expect(whatIsInTheBand()[".map-status"]).toBe(true);
    expect(whatIsInTheBand()[".map-origin"]).toBe(true);
    // The mark the keyboard-only walk reads is still there and still in the band.
    expect(whatIsInTheBand()[".map-status__mark"]).toBe(true);
  });

  it("test_a_replay_still_arriving_draws_one_band_with_two_rows", () => {
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5), true);

    // The run's own row, and under it the quiet one. A replay is given no line
    // about what the model is doing, because a recording holds none.
    expect(howManyRows()).toBe(2);
    const inside = whatIsInTheBand();
    expect(inside[".run-strip"]).toBe(true);
    expect(inside[".map-status"]).toBe(true);
    expect(document.querySelectorAll(".run-strip__doing-line")).toHaveLength(0);
  });

  it("test_a_live_run_saying_what_the_model_is_doing_still_draws_two_rows", () => {
    const { run } = aRunThatHasGotTo(THE_GROWTH.slice(0, 5), false);
    act(() => {
      run.arrive(SEARCHING);
      run.arrive(THINKING);
    });

    // The model's two lines ARE the second row. This is the state that would
    // have been three rows if the quiet one had stayed, which is the whole of
    // what was wrong with the foot before.
    expect(howManyRows()).toBe(2);
    expect(document.querySelectorAll(".run-strip__doing-line")).toHaveLength(2);
    // And the quiet row has stood down rather than stacked under them.
    expect(whatIsInTheBand()[".map-status"]).toBe("not on the screen");
  });

  it("test_a_finished_run_gives_the_quiet_row_back", () => {
    const { run } = aRunThatHasGotTo(THE_GROWTH, false);
    act(() => {
      run.arrive(SEARCHING);
    });
    expect(whatIsInTheBand()[".map-status"]).toBe("not on the screen");

    act(() => {
      run.arrive({ event: "done", reason: "reached_terminal", claims: 7, links: 8, rejected: 1 });
    });

    // Nothing is out, so nothing is being done — and the row those lines were
    // holding goes back to the last key pressed.
    expect(howManyRows()).toBe(2);
    expect(document.querySelectorAll(".run-strip__doing-line")).toHaveLength(0);
    expect(whatIsInTheBand()[".map-status"]).toBe(true);
  });

  it("test_the_foot_is_one_band_in_every_state_and_holds_every_hook", () => {
    // The four states above, asked the one question that is the same in all of
    // them: is the foot one box, and is everything that used to be a box of its
    // own inside it.
    const states: (() => { unmount: () => void })[] = [
      () => theStoredMap(),
      () => aRunThatHasGotTo(THE_GROWTH.slice(0, 5), true),
      () => aRunThatHasGotTo(THE_GROWTH.slice(0, 5), false),
      () =>
        aRunThatHasGotTo(
          [
            ...THE_GROWTH,
            { event: "done", reason: "reached_terminal", claims: 7, links: 8, rejected: 1 },
          ],
          false,
        ),
    ];
    for (const state of states) {
      const { unmount } = state();
      expect(theBand()).toBeTruthy();
      expect(howManyRows()).toBeLessThanOrEqual(2);
      expect(howManyRows()).toBeGreaterThan(0);
      for (const [hook, where] of Object.entries(whatIsInTheBand())) {
        expect(where, `${hook} is on the screen and outside the one band at the foot`).not.toBe(
          false,
        );
      }
      unmount();
    }
  });

  it("test_the_polite_region_is_still_the_printed_sentence", () => {
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5), true);

    // The one thing the band must not have changed: the sentence a screen reader
    // hears is the sentence on the page, one element, so the two cannot drift.
    const said = theBand().querySelector(".run-strip .map-live");
    expect(said, "the run's sentence is not in the band").not.toBeNull();
    expect((said as HTMLElement).getAttribute("aria-live")).toBe("polite");
    expect(said).toBeVisible();
  });

  it("test_the_quiet_row_says_what_the_last_key_did", () => {
    theStoredMap();
    // The map's own keys move the reader, and the quiet row is where the map
    // says what the last one did. Read through the product rather than written
    // down here: the row is asked whether it changed, not what it says.
    const before = (document.querySelector(".map-status") as HTMLElement).textContent ?? "";
    fireEvent.keyDown(document.body, { key: "n" });
    const after = (document.querySelector(".map-status") as HTMLElement).textContent ?? "";
    expect(after).not.toBe(before);
    expect(screen.getByText("last key")).toBeVisible();
  });
});
