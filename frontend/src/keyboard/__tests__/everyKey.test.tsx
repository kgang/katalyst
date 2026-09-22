/**
 * `?` and `Escape`, screen by screen.
 *
 * Three screens exist in this app: the first screen (`App.tsx`, which draws
 * `Launchpad`), the map building itself (`stream/GenerationScreen.tsx`) and the
 * stored map (`components/MapScreen.tsx`). This file presses `?` on each one and
 * asks whether the sheet of every key appears — then presses `Escape` and asks
 * whether it goes away.
 *
 * **It began as evidence rather than as a test.** Kent reported that "the ? to
 * open the hotkeys panel is not working"; these four cases, written to find out
 * where, passed on `03794cf` with the two screens below asserting that nothing
 * happened. `?` was bound in one window listener inside the stored map, so the
 * stored map is the control: it proves the press reaches a window listener in
 * this harness, which is what makes the other two failures an absence and not
 * plumbing. Flipping the two assertions is the whole of the fix, and running
 * this file against `03794cf`'s screens is how it stays a fix.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { App } from "../../App";
import { MapScreen } from "../../components/MapScreen";
import { GenerationScreen } from "../../stream/GenerationScreen";
import { waitingFor } from "../../stream/growth";
import type { TheRun } from "../../stream/theRun";
import { aWorld } from "../../test/aMap";

beforeAll(() => {
  // The drawing library measures the page; a simulated browser has no measuring
  // at all, so both of these are stood in for.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
  // Whatever transform it is handed, this one reports no zoom — which is all
  // the drawing library reads off it here.
  globalThis.DOMMatrixReadOnly ??= class {
    m22 = 1;
  } as unknown as typeof DOMMatrixReadOnly;
});

/** Press `?` the way a reader does: shift and the slash key. */
function pressTheQuestionMark(): void {
  fireEvent.keyDown(document.body, { key: "?", code: "Slash", shiftKey: true });
}

/** A run that has been asked for and has said nothing yet. Nothing is fetched. */
function aRunThatHasSaidNothing(): TheRun {
  const growth = waitingFor("The Strait of Hormuz is going to open next week.", null);
  const where = { growth, saying: "" };
  return {
    asked: { hypothesis: growth.world.title, target: null, belief: null },
    press: "press-1",
    now: () => where,
    watch: () => () => {},
    letGo: () => {},
  };
}

/** The map building itself, with nothing arrived yet. */
function theGenerationScreen() {
  return (
    <GenerationScreen
      run={aRunThatHasSaidNothing()}
      replaying={true}
      onRunAgain={() => {}}
      onLeave={() => {}}
    />
  );
}

/** The stored map, drawn from the example every other test in this tree uses. */
function theStoredMap() {
  return (
    <MapScreen
      base={aWorld()}
      branches={[]}
      source={
        {
          readWorld: () => Promise.resolve(aWorld()),
          readBundle: () => Promise.resolve({ base: aWorld(), branches: [] }),
        } as never
      }
      insteadOfTheEngine={null}
      onLeave={() => {}}
    />
  );
}

describe("the ? key, screen by screen", () => {
  it("the generation screen: ? opens the sheet, and Escape closes it", () => {
    render(theGenerationScreen());
    // The top bar's own control says the key works. This is the screen that
    // also prints *Press ? for every key* under the map.
    expect(screen.getByRole("button", { name: /Every key/ })).toBeInTheDocument();
    pressTheQuestionMark();
    expect(screen.getByText(/You cannot move a tile/)).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(screen.queryByText(/You cannot move a tile/)).toBeNull();
  });

  it("the generation screen: the top-bar control opens the same sheet", () => {
    render(theGenerationScreen());
    fireEvent.click(screen.getByRole("button", { name: /Every key/ }));
    expect(screen.getByText(/You cannot move a tile/)).toBeInTheDocument();
  });

  it("the stored map: ? opens it — the control that proves the press lands", () => {
    render(theStoredMap());
    pressTheQuestionMark();
    expect(screen.getByText(/You cannot move a tile/)).toBeInTheDocument();
  });

  it("the first screen: ? opens it, and Escape closes it", () => {
    render(<App listExamples={() => Promise.resolve([])} />);
    pressTheQuestionMark();
    expect(screen.getByText(/You cannot move a tile/)).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(screen.queryByText(/You cannot move a tile/)).toBeNull();
  });
});
