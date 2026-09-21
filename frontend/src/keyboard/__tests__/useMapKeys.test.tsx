/**
 * Two keys pressed before the page has had a frame to think about the first.
 *
 * **The keyboard moves itself, and it has to remember that it did.** The handler
 * puts focus on the tile it moved to inside the keystroke it is handling, but
 * the value it is handed — which claim the keyboard is on — is React state, and
 * state lands a render later. A reader typing quickly, or a machine slow enough
 * to deliver two keydowns in one task, gets both keys worked out from the claim
 * they were on before the first one.
 *
 * What that looks like on screen is worse than a key that does nothing: the map
 * says *"nothing causes this claim on this map"* about a claim with three
 * causes, because it answered the question for a different claim.
 */

import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { aWire } from "../../test/aMap";
import type { LinkView } from "../../world";
import type { PositionMap } from "../focusMap";
import { type MapKeysNeeds, useMapKeys } from "../useMapKeys";

/** Where the stored example's tiles sit, in the columns the layout puts them in. */
const WHERE: PositionMap = new Map([
  ["H", { x: 0, y: 400, height: 280 }],
  ["C", { x: 400, y: 0, height: 200 }],
  ["N1", { x: 400, y: 240, height: 216 }],
  ["R", { x: 400, y: 500, height: 152 }],
  ["B", { x: 800, y: 300, height: 176 }],
  ["M1", { x: 1200, y: 120, height: 192 }],
  ["M2", { x: 1200, y: 400, height: 192 }],
]);

/** The eight arrows of the stored example, the feedback one included. */
const WIRES: LinkView[] = [
  aWire({ source: "H", target: "B" }),
  aWire({ source: "H", target: "C", mode: "sustain" }),
  aWire({ source: "H", target: "N1", lag: 10 }),
  aWire({ source: "C", target: "B", mode: "sustain" }),
  aWire({ source: "B", target: "M1", lag: 1 }),
  aWire({ source: "B", target: "M2", lag: 3 }),
  aWire({ source: "B", target: "R", reflexive: true, lag: 14 }),
  aWire({ source: "R", target: "B", strength: -1.2 }),
];

/** The six things the keys that are not about moving are wired to. */
const KEYS = {
  intervene: vi.fn(),
  branch: vi.fn(),
  flipWorlds: vi.fn(),
  outline: vi.fn(),
  panel: vi.fn(),
  palette: vi.fn(),
};

/**
 * One keystroke, delivered the way the page delivers one: dispatched on an
 * element and caught on the window, so the event has a real target and the
 * handler's guard against typing in a field has something to read.
 */
function press(handler: (event: KeyboardEvent) => void, key: string): void {
  const onKey = (event: Event): void => handler(event as KeyboardEvent);
  window.addEventListener("keydown", onKey);
  document.body.dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }),
  );
  window.removeEventListener("keydown", onKey);
}

/**
 * The handler, wired to a map, with the claim the keyboard is on **deliberately
 * left where it was**.
 *
 * That is not a contrivance: it is what the screen really hands the handler
 * inside one task, because the state has not been re-rendered yet. What the
 * handler must not do is believe it.
 */
function keysOn(focused: string | null) {
  const moved: string[] = [];
  const said: string[] = [];
  const needs: MapKeysNeeds = {
    wires: WIRES,
    positions: WHERE,
    focused,
    onFocused: (id) => moved.push(id),
    onStatus: (line) => said.push(line),
    keys: KEYS,
    words: (id) => id,
  };
  const { result } = renderHook(() => useMapKeys(needs));
  return { handler: result.current, moved, said };
}

describe("two keys in one frame", () => {
  it("test_a_second_key_moves_from_where_the_first_one_left_the_keyboard", () => {
    // Forward out of the hypothesis, then straight back toward what causes it,
    // with no render in between. The second step has to start from where the
    // first one landed.
    const { handler, moved, said } = keysOn("H");
    press(handler, "l");
    press(handler, "h");

    expect(moved[0]).toBe("B");
    // Not "H" again, and not nothing: B is caused by three claims on this map.
    expect(moved).toHaveLength(2);
    expect(["H", "C", "R"]).toContain(moved[1]);
    // And nothing was said about a claim having no causes, because the claim
    // the keyboard was on has three.
    expect(said.join(" ")).not.toContain("nothing causes this claim");
  });

  it("test_two_steps_down_a_column_do_not_both_start_at_the_top", () => {
    // The same fault, on the other pair of keys. C, N1 and R share a column.
    const { handler, moved } = keysOn("C");
    press(handler, "j");
    press(handler, "j");

    expect(moved).toEqual(["N1", "R"]);
  });

  it("test_a_key_still_follows_the_keyboard_when_something_else_moves_it", () => {
    // Tab, a click, or a branch opening on the claim it just added: the claim
    // the keyboard is on changes for a reason that is not this handler's own
    // move, and the next keystroke has to start from there.
    const moved: string[] = [];
    const needs = (focused: string | null): MapKeysNeeds => ({
      wires: WIRES,
      positions: WHERE,
      focused,
      onFocused: (id) => moved.push(id),
      onStatus: () => undefined,
      keys: KEYS,
      words: (id) => id,
    });
    const { result, rerender } = renderHook(({ on }: { on: string }) => useMapKeys(needs(on)), {
      initialProps: { on: "H" },
    });
    press(result.current, "l");
    expect(moved).toEqual(["B"]);

    // Now the keyboard is put on N1 by something else entirely.
    rerender({ on: "N1" });
    press(result.current, "h");
    // N1's one cause is the hypothesis.
    expect(moved).toEqual(["B", "H"]);
  });
});
