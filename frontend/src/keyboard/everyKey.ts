/**
 * The three keys that work on every screen, bound in one place.
 *
 * `?` opens the sheet of every key, `⌘K` (or `Ctrl+K`) opens the palette of
 * every command, and `Escape` closes whatever is open. They are lifted out of
 * the stored-map screen and given their own module because **two of them are
 * how a reader finds out what the others do**, and a key that only works on
 * one of three screens teaches nobody anything. The screen that was building a
 * map printed *Press ? for every key* while `?` did nothing at all on it.
 *
 * Bound on the window rather than on the map, so the key does the same thing
 * wherever the keyboard happens to be standing — on a tile, on a row of the
 * panel, or on nothing.
 *
 * **Typing is never a shortcut.** In a field a `?` is a `?`, so the sheet stays
 * shut while the keyboard is in one. `⌘K` and `Escape` are exempt: they are
 * chords or the way out, and both are expected to work from inside a field.
 *
 * **It never draws anything.** Each screen keeps its own overlay state and its
 * own sheet, because the map screens hang theirs inside the map's stage and the
 * first screen has no stage to hang one in.
 */

import { useEffect, useRef } from "react";
import "./everyKey.css";

/** What a screen does when one of the three keys is pressed. */
export interface EveryKeyPresses {
  /** `?` — show the sheet of every key, or hide it if it is already up. */
  readonly everyKey: () => void;
  /**
   * `⌘K` — show the palette of every command, or hide it.
   *
   * Left out by a screen that has no commands to offer, and then the chord does
   * nothing there rather than opening an empty list.
   */
  readonly palette?: () => void;
  /** `Escape` — close whatever this screen has open. Nothing is left half-done. */
  readonly escape: () => void;
}

/**
 * Make `?`, `⌘K` and `Escape` work on the screen that calls this.
 *
 * @param presses What the screen wants done for each of the three.
 */
export function useEveryKey(presses: EveryKeyPresses): void {
  // The listener is bound once and reads the latest presses through this, so a
  // screen that hands in fresh functions every render — which every screen here
  // does — does not add and remove a window listener on every keystroke.
  const latest = useRef(presses);
  latest.current = presses;

  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable === true;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        const palette = latest.current.palette;
        if (palette === undefined) {
          return;
        }
        event.preventDefault();
        palette();
        return;
      }
      if (event.key === "Escape") {
        latest.current.escape();
        return;
      }
      if (event.key === "?" && !typing) {
        event.preventDefault();
        latest.current.everyKey();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
