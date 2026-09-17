/**
 * The whole keyboard map, in one place, and the words the sheet reads it back
 * with.
 *
 * Bound on the map itself rather than on each tile, so the same key does the
 * same thing wherever you happen to be standing on the map — and so that typing
 * a claim into a field in the panel beside the map never moves the view.
 */

/** What one key does, and how the shortcuts sheet says it. */
export interface Shortcut {
  /** The key as a reader would write it. */
  readonly key: string;
  /** What it does, in plain words. */
  readonly does: string;
}

/**
 * Every shortcut, in the order the sheet lists them.
 *
 * The order is the order you would learn them in: find something, move around,
 * change something, look at it another way.
 */
export const SHORTCUTS: readonly Shortcut[] = [
  { key: "⌘K", does: "Every command, by name. Type a few letters and press Enter." },
  { key: "j", does: "Down the column you are in. Focus does not wrap round." },
  { key: "k", does: "Up the column you are in." },
  {
    key: "h",
    does: "Back along a wire, toward what causes this claim. The line under the map names the wire it took.",
  },
  {
    key: "l",
    does: "Forward along a wire, toward what this claim causes. It follows the wire, not the screen — so it can land you on a tile to your left.",
  },
  {
    key: "E",
    does: "Change this claim: the six things you can do to it, in a panel beside the map.",
  },
  { key: "B", does: "Start a branch from here and name it." },
  {
    key: "Space",
    does: "Flip between the map as it was and the map with your edits. A hard switch, never a fade.",
  },
  { key: "O", does: "Read the map as a list instead of a picture." },
  {
    key: "P",
    does: "Show or hide the panel beside the map, when you want the whole width for the map.",
  },
  { key: "?", does: "This sheet." },
  { key: "Escape", does: "Close whatever is open. Nothing is ever left half-done by closing it." },
];

/**
 * The one line the sheet carries about dragging, said out loud rather than left
 * for a reader to discover by failing.
 */
export const NO_DRAGGING =
  "Tiles do not move. The layout is automatic, left to right. Drag the background to pan, " +
  "scroll to zoom. Pinning, grouping and annotating arrive as buttons, not as dragging.";
