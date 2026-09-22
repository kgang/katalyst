/**
 * The panel beside the map folds away, and there is something on screen to fold
 * it with.
 *
 * **What Kent saw.** After his first live run, 2026-09-22: *"the … large,
 * uncollapsible side bar [is] somewhat garish. First, can you introduce a button
 * to be able to collapse and open the side bar."* The panel had always folded —
 * `P` did it, on the stored map — but nothing on screen said so, and a reader
 * who found `P` by accident was left with a map and no way to get the panel
 * back. On the screen a map builds itself on, `P` did not even do that: it
 * printed a line saying the panel was beside the map and left it there.
 *
 * So there are now three ways to ask for the same thing, on both map screens: a
 * chevron at the head of the panel's own names, the key, and — while it is away
 * — a tab at the edge of the map. This holds that all three are there, that each
 * is a control with a name rather than a key somebody has to know about, and
 * that choosing a claim brings the panel back, because choosing a claim is the
 * reader asking to read something.
 *
 * **What it cannot hold, and what does.** A simulated page measures nothing, so
 * *the stage widens* is checked in the browser, in the keyboard-only walk
 * (`e2e/hormuz.spec.ts`). What is checked here is the half that fails first: the
 * panel leaves the row entirely rather than being drawn over or shrunk, and a
 * tab of its own takes its place.
 */

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { SHORTCUTS } from "../../keyboard/keys";
import { THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import type { StreamEvent } from "../../stream/events";
import { GenerationScreen } from "../../stream/GenerationScreen";
import { fold, waitingFor } from "../../stream/growth";
import type { TheRun, WhereItHasGot } from "../../stream/theRun";
import { aClaim, aWorld } from "../../test/aMap";
import type { Selection, WorldView } from "../../world";
import { MapScreen } from "../MapScreen";

// The map stands in for itself: one button per claim, each doing what pointing
// at that claim on the real canvas does — it hands the screen a selection.
//
// **And one more button for `P`.** The map's keys are bound on the map surface
// (`keyboard/useMapKeys.ts`, which has its own tests), and the surface is what
// is standing in here — so the key is pressed the way the real surface presses
// it, by calling the screen's own `panel`. What is being asked below is what the
// screen does about it, which is the half that was missing on one of them.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({
    world,
    onSelect,
    keys,
  }: {
    world: WorldView;
    onSelect: (selection: Selection) => void;
    keys: { panel: () => void };
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
      <button type="button" data-testid="press-P-on-the-map" onClick={() => keys.panel()}>
        P
      </button>
    </div>
  ),
}));

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

/** A run somebody else is driving, so a test can hand it one event at a time. */
function aRunWeDrive(): TheRun & { arrive: (event: StreamEvent) => void } {
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
    arrive: (event: StreamEvent) => {
      where = { growth: fold(where.growth, event), saying: where.saying };
      for (const told of watchers) {
        told();
      }
    },
  };
}

/** A map building itself, five events in — the moment a reader starts reading. */
function aMapBuildingItself() {
  const run = aRunWeDrive();
  const drawn = render(
    <GenerationScreen run={run} replaying={true} onRunAgain={() => {}} onLeave={() => {}} />,
  );
  act(() => {
    for (const event of THE_GROWTH.slice(0, 5)) {
      run.arrive(event);
    }
  });
  return drawn;
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

/** Is the panel beside the map, and is its column taking room in the row? */
function thePanelIsThere(): boolean {
  return document.querySelector(".dock-column") !== null;
}

/** The two screens, each opened fresh, so every case below is made twice. */
const BOTH_MAP_SCREENS: readonly [string, () => { unmount: () => void }][] = [
  ["a stored map", theStoredMap],
  ["a map building itself", aMapBuildingItself],
];

describe("there is a control on screen that folds the panel away", () => {
  for (const [screenName, open] of BOTH_MAP_SCREENS) {
    it(`test_the_fold_is_a_control_with_a_name_on_${screenName.replaceAll(" ", "_")}`, () => {
      const { unmount } = open();

      // A control with words, not a key somebody has to have read about. The
      // words say what it does and what it does it to.
      const fold = screen.getByRole("button", { name: /Hide the panel beside the map/ });
      expect(fold).toBeVisible();
      // It says which way the panel is, for a reader who hears the screen.
      expect(fold.getAttribute("aria-expanded")).toBe("true");
      unmount();
    });

    it(`test_folding_takes_the_panel_out_of_the_row_on_${screenName.replaceAll(" ", "_")}`, () => {
      const { unmount } = open();
      expect(thePanelIsThere()).toBe(true);

      fireEvent.click(screen.getByRole("button", { name: /Hide the panel beside the map/ }));

      // **Out of the row, not drawn over and not shrunk.** The column is gone,
      // so the stage takes the width it was holding — which is the whole of what
      // the reader asked for.
      expect(thePanelIsThere()).toBe(false);
      expect(document.querySelector(".dock")).toBeNull();

      // And a tab at the edge it went behind, which is the only control on
      // screen that can bring it back with a pointer.
      const tab = screen.getByRole("button", { name: /Show the panel beside the map/ });
      expect(tab).toBeVisible();
      expect(tab.getAttribute("aria-expanded")).toBe("false");

      fireEvent.click(tab);
      expect(thePanelIsThere()).toBe(true);
      unmount();
    });

    it(`test_the_key_still_folds_and_unfolds_on_${screenName.replaceAll(" ", "_")}`, () => {
      const { unmount } = open();

      // `P` pressed on the map, which is what it always did on a stored map and
      // what it never did on a generating one — there it printed a line saying
      // the panel was beside the map and left it there.
      const pressP = screen.getByTestId("press-P-on-the-map");
      fireEvent.click(pressP);
      expect(thePanelIsThere()).toBe(false);
      fireEvent.click(pressP);
      expect(thePanelIsThere()).toBe(true);
      unmount();
    });

    it(`test_choosing_a_claim_brings_the_panel_back_on_${screenName.replaceAll(" ", "_")}`, () => {
      const { unmount } = open();
      fireEvent.click(screen.getByRole("button", { name: /Hide the panel beside the map/ }));
      expect(thePanelIsThere()).toBe(false);

      // The reader points at a claim. That is a request to read something, and
      // the place it is read is the panel — so the panel comes back rather than
      // the answer landing off screen, which is the defect the panels were split
      // up to fix in the first place.
      const claims = screen.getAllByTestId(/^point-at-/);
      expect(claims.length, "the map drew no claim to point at").toBeGreaterThan(0);
      fireEvent.click(claims[0] as HTMLElement);

      expect(thePanelIsThere()).toBe(true);
      unmount();
    });
  }

  it("test_the_key_sheet_says_where_the_control_is", () => {
    // A key that has a control on screen must say so on the sheet, or the sheet
    // is teaching a reader the long way round a thing they can see.
    const panelKey = SHORTCUTS.find((one) => one.key === "P");
    expect(panelKey, "the sheet does not mention the panel key at all").toBeDefined();
    expect((panelKey as { does: string }).does).toMatch(/head of the panel/);
    expect((panelKey as { does: string }).does).toMatch(/tab at the edge/);
  });

  it("test_the_names_of_the_panels_are_still_names_and_the_fold_is_not_one_of_them", () => {
    const { unmount } = aMapBuildingItself();

    // The fold sits beside the names and outside the row of them: a row of
    // labels is a row of labels, and a control that is not one of them has no
    // business being read as one.
    const names = screen.getAllByRole("tab");
    expect(names.length).toBeGreaterThan(1);
    for (const name of names) {
      expect(name.getAttribute("aria-label") ?? "").not.toMatch(/Hide the panel/);
    }
    const fold = screen.getByRole("button", { name: /Hide the panel beside the map/ });
    expect(fold.getAttribute("role")).toBeNull();
    expect(fold.closest('[role="tablist"]')).toBeNull();
    expect(fold.closest(".panel-switch")).not.toBeNull();
    unmount();
  });
});
