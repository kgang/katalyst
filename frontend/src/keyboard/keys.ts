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
    does:
      "Show or hide the panel beside the map, when you want the whole width for the map. The " +
      "chevron at the head of the panel does the same, and while the panel is away a tab at the " +
      "edge of the map brings it back.",
  },
  {
    key: "N",
    does:
      "The next panel beside the map. Their names are at the head of the panel, and clicking a " +
      "claim or an arrow turns to the one that reads it out.",
  },
  { key: "?", does: "This sheet." },
  { key: "Escape", does: "Close whatever is open. Nothing is ever left half-done by closing it." },
];

/**
 * The one line the sheet carries about dragging, said out loud rather than left
 * for a reader to discover by failing.
 *
 * **It stopped saying *tiles do not move* on 2026-09-22** *(decision record
 * 0024)*. That was true of a finished map and false of one being written: while
 * a map builds itself a tile changes column rather than let a later arrow point
 * backwards, and the whole map takes its final places once at the moment the run
 * stops. What was always true, and is what a reader needs from this line, is
 * that they cannot move a tile themselves.
 */
export const NO_DRAGGING =
  "You cannot move a tile: the layout is automatic, left to right, and a tile moves only when an " +
  "arrow would otherwise point backwards, or once when a run stops. Drag the background to pan, " +
  "scroll to zoom. Pinning, grouping and annotating arrive as buttons, not as dragging.";
