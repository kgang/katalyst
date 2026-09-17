/**
 * Every command, by name.
 *
 * **It is an overlay, not a dialog**, and the difference is four things:
 *
 * 1. **Nothing waits on it.** No state is half-committed while it is open. Close
 *    it and the screen is exactly where it was.
 * 2. **The map stays live behind it.** No dimming, no blur, nothing made inert.
 * 3. **Escape always closes it**, as does pressing anywhere outside it, as does
 *    running a command.
 * 4. **It is never the only way to do anything.** Every command below is also a
 *    button somewhere or a key on the map.
 *
 * What it does hold is Tab: while it is open, Tab cycles round its own list
 * rather than wandering off behind it, because for the reader who most needs the
 * keyboard an overlay you fall out of by accident is worse than one you do not.
 * Closing it hands focus back where it came from.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useFocusRing } from "../keyboard/focusRing";
import "./commandPalette.css";

/** One thing the palette can do. */
export interface Command {
  /** What it is called. The same words as the button or the key that also does it. */
  readonly name: string;
  /** What it does, in plain words, and where else you could have done it. */
  readonly does: string;
  /** Do it. */
  readonly run: () => void;
}

/** What the palette needs. */
export interface CommandPaletteProps {
  /** Whether it is open. */
  readonly open: boolean;
  /** Close it. Nothing is pending; closing loses nothing. */
  readonly onClose: () => void;
  /** Everything it can do. */
  readonly commands: readonly Command[];
}

/** Every command, by name. */
export function CommandPalette({ open, onClose, commands }: CommandPaletteProps) {
  const [typed, setTyped] = useState("");
  const [at, setAt] = useState(0);
  const shell = useRef<HTMLDivElement>(null);
  useFocusRing(shell, open);

  const matching = useMemo(() => {
    const wanted = typed.trim().toLowerCase();
    return wanted === ""
      ? commands
      : commands.filter((command) => command.name.toLowerCase().includes(wanted));
  }, [commands, typed]);

  useEffect(() => {
    if (open) {
      setTyped("");
      setAt(0);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="palette" ref={shell}>
      <p className="palette__what">
        Every command, by name. Each one is also a button on the screen or a key on the map.
      </p>
      <input
        className="palette__field"
        aria-label="Type a few letters of a command"
        value={typed}
        // biome-ignore lint/a11y/noAutofocus: this opened because the reader asked for it with a keystroke, and typing is the only thing it is for.
        autoFocus
        onChange={(event) => {
          setTyped(event.target.value);
          setAt(0);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setAt((was) => Math.min(was + 1, matching.length - 1));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setAt((was) => Math.max(was - 1, 0));
          } else if (event.key === "Enter") {
            event.preventDefault();
            const chosen = matching[at];
            if (chosen !== undefined) {
              chosen.run();
              onClose();
            }
          }
        }}
      />
      <ul className="palette__list">
        {matching.length === 0 ? (
          <li className="palette__nothing">
            Nothing here is called that. Press Escape and the screen is exactly where it was.
          </li>
        ) : (
          matching.map((command, index) => (
            <li key={command.name}>
              <button
                className="palette__command"
                type="button"
                data-at={index === at ? "yes" : "no"}
                onFocus={() => setAt(index)}
                onClick={() => {
                  command.run();
                  onClose();
                }}
              >
                <span className="palette__name">{command.name}</span>
                <span className="palette__does">{command.does}</span>
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
