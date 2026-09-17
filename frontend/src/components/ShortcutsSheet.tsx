/**
 * Every key, on one sheet — and the one thing the map does not do.
 *
 * Like the command palette, this is an **overlay and not a dialog**: nothing
 * waits on it, the map keeps drawing behind it with no scrim, Escape closes it,
 * and every key it lists also works without it.
 *
 * It carries one line that is not a shortcut at all: **tiles do not move.** That
 * is said out loud here rather than left for a reader to discover by dragging
 * one and watching nothing happen. Half-supported dragging reads as broken, so
 * there is none, and the sheet says so.
 */

import { useRef } from "react";
import { useFocusRing } from "../keyboard/focusRing";
import { NO_DRAGGING, SHORTCUTS } from "../keyboard/keys";
import "./shortcutsSheet.css";

/** What the sheet needs. */
export interface ShortcutsSheetProps {
  /** Whether it is open. */
  readonly open: boolean;
  /** Close it. Nothing is pending; closing loses nothing. */
  readonly onClose: () => void;
}

/** Every key, on one sheet. */
export function ShortcutsSheet({ open, onClose }: ShortcutsSheetProps) {
  const shell = useRef<HTMLElement>(null);
  useFocusRing(shell, open);

  if (!open) {
    return null;
  }

  return (
    <section className="sheet" ref={shell} aria-label="Every key">
      <div className="sheet__head">
        <h2 className="sheet__heading">Every key</h2>
        <button className="sheet__close" type="button" onClick={onClose}>
          Escape closes this
        </button>
      </div>
      <dl className="sheet__keys">
        {SHORTCUTS.map((shortcut) => (
          <div className="sheet__row" key={shortcut.key}>
            <dt className="sheet__key">{shortcut.key}</dt>
            <dd className="sheet__does">{shortcut.does}</dd>
          </div>
        ))}
      </dl>
      <p className="sheet__dragging">{NO_DRAGGING}</p>
    </section>
  );
}
