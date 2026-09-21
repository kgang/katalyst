/**
 * The whole keyboard map, bound once on the map itself.
 *
 * Bound once on the page rather than on each tile, so that the same key does the
 * same thing wherever you are standing: on a tile, on a chip inside a tile, on a
 * row of the panel beside the map, or on nothing at all. A key bound to the tile
 * you happen to be on is a key that stops working the moment you press Tab.
 *
 * **Typing is never a shortcut.** While the keyboard is in a field — naming a
 * branch, writing a claim, giving your own number — every key below is left
 * alone, because in a field a `j` is a `j`.
 *
 * | Key | What it does |
 * |---|---|
 * | `j` / `k` | Down and up the column you are in. No wrapping: wrapping teleports you |
 * | `h` / `l` | Back and forward **along a wire** — toward causes, toward effects |
 * | `E` | The six things you can do to this claim, in the panel beside the map |
 * | `B` | Start a branch from here and name it |
 * | `Space` | Flip between the map as it was and the map with your edits |
 * | `O` | Read the map as a list |
 * | `P` | Show or hide the panel beside the map |
 * | `?` | Every key, on one sheet |
 * | `⌘K` | Every command, by name |
 * | `Escape` | Close whatever is open |
 *
 * **Every move says what it did.** One line under the map names the last
 * keystroke's result — which wire it took, or that there was no wire that way,
 * or that you are at the end of a column. A movement you cannot account for is
 * the same failure as a number you cannot account for, in a smaller place.
 */

import { useCallback, useRef } from "react";
import { inDays } from "../graph/wires/encodings";
import type { LinkView } from "../world";
import { alongWire, inColumn, type PositionMap, stepThrough } from "./focusMap";

/** What the keys that are not about moving are wired to. */
export interface MapKeys {
  /** `E` — the six things you can do to the focused claim. */
  readonly intervene: () => void;
  /** `B` — start a branch from here. */
  readonly branch: () => void;
  /** `Space` — flip between the two maps, as a hard switch. */
  readonly flipWorlds: () => void;
  /** `O` — read the map as a list. */
  readonly outline: () => void;
  /** `P` — show or hide the panel beside the map. */
  readonly panel: () => void;
  /** `⌘K` — every command, by name. */
  readonly palette: () => void;
}

/** What the key handler needs to know about the map it is on. */
export interface MapKeysNeeds {
  /** Every arrow on the map, feedback arrows included: this is walking, not moving numbers. */
  readonly wires: readonly LinkView[];
  /** Where every tile ended up. */
  readonly positions: PositionMap;
  /** Which claim the keyboard is on. */
  readonly focused: string | null;
  /** Put the keyboard on a claim. */
  readonly onFocused: (id: string) => void;
  /** Say what the last keystroke did. */
  readonly onStatus: (line: string) => void;
  /** Everything the keys that are not about moving are wired to. */
  readonly keys: MapKeys;
  /** What a claim is called, for the line under the map. */
  readonly words: (id: string) => string;
}

/**
 * How a wire reads in the line under the map.
 *
 * It names the kind of push rather than the identifier, because the identifier
 * says nothing and the kind is what decides whether the step you just took was
 * the one you meant.
 */
function wireInWords(wire: LinkView): string {
  const kind = wire.reflexive
    ? "the feedback arrow"
    : wire.mode === "sustain"
      ? "an arrow that only holds while its cause holds"
      : "an arrow that fires once and fades";
  return `along ${kind} · ${inDays(wire.lag)}`;
}

/**
 * Bind the keyboard map to the map surface.
 *
 * @returns The handler to put on the surface, and a way to clear the set that a
 *   sideways step left behind.
 */
export function useMapKeys(needs: MapKeysNeeds) {
  // The neighbours a sideways step passed over. They become the up-and-down set
  // where you land, so nothing on the map is more than two keystrokes away and
  // there is no chooser overlay — which would be a pop-up in all but name.
  const leftOver = useRef<{ at: string; others: readonly string[] } | null>(null);

  const { wires, positions, focused, onFocused, onStatus, keys, words } = needs;

  /**
   * Where the keyboard is **now**, which is not always where the last render
   * said it was.
   *
   * This handler moves the keyboard itself, synchronously: by the time it
   * returns, the tile it moved to already has focus. The value it was handed,
   * `focused`, is state, and state lands a render later. So two keys pressed
   * inside one frame — a reader typing quickly, or a machine slow enough to
   * deliver two keydowns in a single task — were **both** worked out from the
   * claim the reader was on before the first one. The second key then did
   * nothing at all, and the map said *"nothing causes this claim on this map"*
   * about a claim with three causes.
   *
   * So the handler keeps its own note of where it put the keyboard, and follows
   * `focused` whenever that changes for a reason other than its own move: Tab,
   * a click, a branch opening on the claim it added.
   */
  const at = useRef(focused);
  const lastSaid = useRef(focused);
  if (lastSaid.current !== focused) {
    lastSaid.current = focused;
    at.current = focused;
  }

  return useCallback(
    (event: KeyboardEvent): void => {
      /** Move the keyboard, and remember it now rather than a render from now. */
      const moveTo = (id: string): void => {
        at.current = id;
        onFocused(id);
      };

      const target = event.target as HTMLElement;
      const typing =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable === true;
      if (typing) {
        return;
      }

      const upDown = (way: 1 | -1): void => {
        const from = at.current;
        if (from === null) {
          return;
        }
        const set =
          leftOver.current?.at === from && leftOver.current.others.length > 0
            ? [from, ...leftOver.current.others]
            : inColumn(from, positions);
        const landed = stepThrough(from, set, positions, way);
        if (landed === null) {
          onStatus(way === 1 ? "last claim in this column" : "first claim in this column");
          return;
        }
        moveTo(landed);
        onStatus(`${way === 1 ? "down" : "up"} the column · ${words(landed)}`);
      };

      const sideways = (way: "in" | "out"): void => {
        const from = at.current;
        if (from === null) {
          return;
        }
        const step = alongWire(from, way, wires, positions);
        if (step === null) {
          onStatus(
            way === "out"
              ? "nothing follows from this claim — it is where the chain ends"
              : "nothing causes this claim on this map",
          );
          return;
        }
        leftOver.current = { at: step.to, others: step.others };
        moveTo(step.to);
        onStatus(`${wireInWords(step.wire)} · ${words(step.to)}`);
      };

      // Every command, by name. Checked before the plain letters, or a k with the
      // command key held would walk down a column instead.
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        keys.palette();
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }

      switch (event.key) {
        case "j":
          event.preventDefault();
          upDown(1);
          return;
        case "k":
          event.preventDefault();
          upDown(-1);
          return;
        case "h":
          event.preventDefault();
          sideways("in");
          return;
        case "l":
          event.preventDefault();
          sideways("out");
          return;
        case "E":
        case "e":
          event.preventDefault();
          keys.intervene();
          onStatus("the six things you can do to this claim, in the panel beside the map");
          return;
        case "B":
        case "b":
          event.preventDefault();
          keys.branch();
          onStatus("name the branch in the panel beside the map");
          return;
        case "O":
        case "o":
          event.preventDefault();
          keys.outline();
          return;
        case "P":
        case "p":
          event.preventDefault();
          keys.panel();
          return;
        case " ":
          // Space activates whatever button the keyboard happens to be on, so it
          // only flips the two maps when the keyboard is on the map itself.
          if (target.closest("button") !== null) {
            return;
          }
          event.preventDefault();
          keys.flipWorlds();
          return;
        default:
          return;
      }
    },
    // `focused` is not here on purpose: where the keyboard is is read from the
    // note above, which is right as of this keystroke rather than as of the last
    // render. Leaving it in would rebuild this handler — and rebind the listener
    // carrying it — on every step across the map, for nothing.
    [wires, positions, onFocused, onStatus, keys, words],
  );
}
