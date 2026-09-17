/**
 * Keeping Tab inside an overlay while it is open — a ring, not a barricade.
 *
 * The two overlays in this product, the command palette and the shortcuts sheet,
 * are deliberately **not dialogs**: nothing waits on them, the map keeps drawing
 * behind them with no scrim and no blur, Escape always closes them, and neither
 * is ever the only way to do anything.
 *
 * But an overlay you can Tab straight out of by accident is worse than one you
 * cannot, for exactly the reader who most needs the keyboard. So while one is
 * open, Tab cycles within its own list and comes back round to the top. Closing
 * it puts focus back where it was, because losing your place is the one thing a
 * keyboard reader cannot recover from quickly.
 */

import { type RefObject, useEffect } from "react";

/** Everything inside this element that the keyboard can land on, in order. */
function reachable(within: HTMLElement): HTMLElement[] {
  return [
    ...within.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((one) => !one.hasAttribute("disabled"));
}

/**
 * Hold Tab inside an element while it is open, and give focus back when it
 * closes.
 *
 * @param within The overlay.
 * @param open Whether it is open.
 */
export function useFocusRing(within: RefObject<HTMLElement | null>, open: boolean): void {
  useEffect(() => {
    const element = within.current;
    if (!open || element === null) {
      return;
    }
    const cameFrom = document.activeElement as HTMLElement | null;
    reachable(element)[0]?.focus();

    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== "Tab") {
        return;
      }
      const stops = reachable(element);
      const first = stops[0];
      const last = stops[stops.length - 1];
      if (first === undefined || last === undefined) {
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    element.ownerDocument.addEventListener("keydown", onKey);
    return () => {
      element.ownerDocument.removeEventListener("keydown", onKey);
      cameFrom?.focus();
    };
  }, [within, open]);
}
