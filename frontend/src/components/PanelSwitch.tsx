/**
 * The switcher at the head of the panel beside the map.
 *
 * **What it fixes.** The panel was one long column. On the screen a map builds
 * itself on it held, in this order, the Verify door's answer, every proposal the
 * rules refused printed in full, the receipt, the way into the working, and only
 * then whatever the reader had clicked on. So a click on a tile did select it,
 * and did fill the panel, and the reader saw nothing happen: the answer was
 * below the fold and nothing scrolled. Kent's words, 2026-09-22: *"it's a little
 * hard to find/navigate to/know what right hand side panels exist and how to
 * navigate to them."*
 *
 * So the column becomes a few panels with their names at the head of it, and one
 * of them on the glass at a time. The names are what say the others exist.
 *
 * **Every label is a WORD.** Kent asked for *buttons or icons*; a picture on its
 * own is a thing a reader has to learn before they can use it, and this product
 * has no icon set to learn from. A word costs one reading and is right in
 * greyscale, at every size, in both themes and out loud.
 *
 * **Which panel is on the glass is said three ways** — the word is in the text
 * colour rather than the quiet one, a hairline of the accent runs under it, and
 * `aria-selected` carries it for a reader who hears the screen instead of seeing
 * it. Nothing here is carried by hue alone (INV-12 — every meaning has a second
 * channel).
 *
 * **Nothing in it moves.** A label gains a count when what it names gains one,
 * and that is the whole of what changes: no pulse, no fade, no dot that grows.
 * The motion budget has three movements in it and none of them is a panel
 * asking to be looked at.
 *
 * It draws the labels and nothing else: which panel is showing is the screen's
 * own state, because only the screen knows what a selection should do to it.
 */

import { useEffect, useRef } from "react";
import "./panelSwitch.css";

/**
 * One panel the reader can turn to.
 *
 * @property name What the screen calls this panel in its own state. Never drawn.
 * @property label What it is called on screen. A word, or two words.
 * @property mark A count of what is in it, in the product's own words —
 *   *refused 3*. Read off state the screen already holds, never a typed-in
 *   number, and absent when there is nothing to count.
 */
export interface PanelChoice {
  readonly name: string;
  readonly label: string;
  readonly mark?: string;
}

/** What the switcher needs. */
export interface PanelSwitchProps {
  /** The panels this screen has, in the order they are offered. */
  readonly panels: readonly PanelChoice[];
  /** Which one is on the glass, by name. */
  readonly showing: string;
  /**
   * Put a different one on the glass.
   *
   * The screen does it rather than this component, because the screen is also
   * what says the line under the map naming what the last keystroke did.
   */
  readonly onShow: (name: string) => void;
}

/**
 * The one element the labels name.
 *
 * The panel beside the map is the scrolling box in `MapFrame`, and a label has
 * to be able to point at it for a screen reader to follow the pair.
 */
export const THE_PANEL_BESIDE_THE_MAP = "the-panel-beside-the-map";

/** The identifier one label carries, so the panel it chose can name it back. */
export function theLabelFor(name: string): string {
  return `panel-label-${name}`;
}

/**
 * The one key that steps to the next panel.
 *
 * `N` for *next*. It is free — `j`, `k`, `h`, `l`, `E`, `B`, `O`, `P`, `Space`,
 * `?`, `⌘K` and `Escape` are the whole of the rest of the keyboard — and it is
 * bound here rather than with the map's keys because it means nothing on a
 * screen that has no panels to step between.
 */
export const THE_NEXT_PANEL_KEY = "n";

/** True while the keyboard is in a field, where a letter is a letter. */
function typing(target: EventTarget | null): boolean {
  const on = target as HTMLElement | null;
  return on?.tagName === "INPUT" || on?.tagName === "TEXTAREA" || on?.isContentEditable === true;
}

/** The panels this screen has, and which of them is on the glass. */
export function PanelSwitch({ panels, showing, onShow }: PanelSwitchProps) {
  const labels = useRef<(HTMLButtonElement | null)[]>([]);

  // The listener is bound once and reads the latest panels through this, so a
  // screen that hands in a fresh list every render — which both of them do —
  // does not add and remove a window listener on every keystroke.
  const latest = useRef({ panels, showing, onShow });
  latest.current = { panels, showing, onShow };

  // **One key, from anywhere on the screen.** Bound on the window rather than on
  // the switcher, because a key that only works once you have tabbed to the
  // thing it drives is a key nobody presses — and the reader pressing it is
  // usually standing on the map.
  //
  // **Typing is never a shortcut.** In a field an `n` is an `n`.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (event.key.toLowerCase() !== THE_NEXT_PANEL_KEY || typing(event.target)) {
        return;
      }
      const { panels: offered, showing: now, onShow: show } = latest.current;
      if (offered.length === 0) {
        return;
      }
      event.preventDefault();
      const at = offered.findIndex((one) => one.name === now);
      const next = offered[(at + 1) % offered.length];
      if (next !== undefined) {
        show(next.name);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /**
   * The arrow keys walk the labels, which is what a reader who has met a row of
   * labels anywhere else expects. The panel changes as focus lands, because it
   * is already on the screen and there is nothing to wait for.
   */
  const walk = (event: React.KeyboardEvent<HTMLDivElement>): void => {
    const at = panels.findIndex((one) => one.name === showing);
    const step =
      event.key === "ArrowRight"
        ? 1
        : event.key === "ArrowLeft"
          ? -1
          : event.key === "Home"
            ? -at
            : event.key === "End"
              ? panels.length - 1 - at
              : 0;
    if (step === 0 || panels.length === 0) {
      return;
    }
    event.preventDefault();
    const to = (at + step + panels.length) % panels.length;
    const next = panels[to];
    if (next === undefined) {
      return;
    }
    onShow(next.name);
    labels.current[to]?.focus();
  };

  return (
    // One tab stop for the whole row, and the arrow keys inside it: a row of
    // labels that each took a Tab would put three more stops between the map and
    // the panel every reader crosses.
    //
    // A row of labels is a role rather than an element: there is no HTML tag
    // that means one, so the role is spelled out on the box that honestly holds
    // them.
    <div
      className="panel-switch"
      role="tablist"
      aria-label="Which panel is beside the map"
      onKeyDown={walk}
    >
      {panels.map((panel, at) => {
        const chosen = panel.name === showing;
        return (
          <button
            key={panel.name}
            id={theLabelFor(panel.name)}
            className="panel-switch__label"
            type="button"
            role="tab"
            aria-selected={chosen}
            aria-controls={THE_PANEL_BESIDE_THE_MAP}
            tabIndex={chosen ? 0 : -1}
            data-showing={chosen ? "yes" : "no"}
            ref={(node) => {
              labels.current[at] = node;
            }}
            onClick={() => onShow(panel.name)}
          >
            <span className="panel-switch__word">{panel.label}</span>
            {panel.mark === undefined ? null : (
              <span className="panel-switch__mark">{panel.mark}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
