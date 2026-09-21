/**
 * When the map may take the keyboard back, and when it may not.
 *
 * The map puts the keyboard on a tile twice: once now, and once after the
 * drawing library has rebuilt that tile's element, because the element that was
 * there the first time is sometimes the one about to be thrown away and focusing
 * it does nothing at all. That second landing is what keeps a keyboard-only
 * reader from being left behind on the tile they just walked off.
 *
 * **The second landing is scheduled on the next two animation frames, and
 * frames are not a clock.** A browser produces none while a tab is in the
 * background or while nothing on the page has changed, so "two frames later"
 * can be two milliseconds or it can be two minutes — and the next frame is very
 * often produced by the reader doing something else, which is exactly the moment
 * the landing must not happen. Press a key on the map and then open the command
 * palette, and the palette's field takes the keyboard, the frame the palette's
 * arrival caused runs the landing, and the tile takes it straight back: every
 * letter the reader types is read as a map shortcut, Enter does nothing, and the
 * palette sits there looking open.
 *
 * So the rule is small and it is about *somewhere* rather than about time:
 *
 * **The map takes the keyboard back from nowhere, and never from somewhere.**
 *
 * Nowhere is a page with nothing focused — which is what a rebuilt element
 * leaves behind, and the whole case the second landing exists for. Somewhere is
 * the palette, the shortcut sheet, a field in the panel, a button in the branch
 * bar: a reader who is there went there, and a map that pulled them out of it
 * would be taking a decision on their behalf that they had already taken for
 * themselves.
 *
 * It is written here, apart from the canvas, because it is a rule rather than a
 * piece of drawing — and because a rule with four ways of being wrong wants a
 * test that does not have to build a canvas to ask about them.
 */

/** Everything the decision reads. Nothing here is a time. */
export interface WhereTheKeyboardIs {
  /** The tile the map last asked the keyboard to stand on, if any. */
  readonly wanted: string | null;
  /** The tile this particular landing was for. */
  readonly forTile: string;
  /** The tile the keyboard is standing on now, when it is standing on one. */
  readonly standingOn: string | undefined;
  /** What holds the keyboard now, as the page reports it. */
  readonly active: Element | null;
  /** The map's own surface, so "on the map" can be asked. */
  readonly surface: Element | null;
}

/**
 * Is the keyboard nowhere at all?
 *
 * A page with nothing focused reports its own body, which is the page saying
 * *"nobody"* rather than naming anything. That is what a rebuilt element leaves
 * behind and it is the one state worth landing into.
 */
function nowhere(active: Element | null): boolean {
  return (
    active === null ||
    active === active.ownerDocument.body ||
    active === active.ownerDocument.documentElement
  );
}

/**
 * May the map put the keyboard back on this tile?
 *
 * @param where Everything the decision reads.
 * @returns True only when this is still the move the reader last asked for, it
 *   did not take, and the keyboard has not gone anywhere of its own.
 */
export function mayLandAgain(where: WhereTheKeyboardIs): boolean {
  // A later move won. Dragging the keyboard back to the first of two quick
  // steps is the fault this guard was written for.
  if (where.wanted !== where.forTile) {
    return false;
  }
  // It took the first time, which is the ordinary case.
  if (where.standingOn === where.forTile) {
    return false;
  }
  // Nowhere: nothing has it, so nothing is being taken from anybody.
  if (nowhere(where.active)) {
    return true;
  }
  // Somewhere: only if that somewhere is still the map.
  return where.surface?.contains(where.active) === true;
}
