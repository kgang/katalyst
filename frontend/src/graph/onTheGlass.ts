/**
 * Which boxes the map draws, and where.
 *
 * The layout runs on a background thread and **answers later**, so at every
 * moment a map is growing there are boxes nobody has found a place for yet. This
 * file is the one answer to what happens to them, written apart from the canvas
 * so that it can be read, and checked, without a browser.
 *
 * On this machine the window is shorter than a frame and nobody ever sees it. On
 * a slower one it is long enough to read, and what is drawn in it is the whole of
 * what this file is about.
 */

import type { Position } from "./elkGraph";
import type { MapNode } from "./toFlow";

/** Where the map starts. The only place this file ever puts a box itself. */
export const THE_ORIGIN: Position = { x: 0, y: 0 };

/** One box, and the place it is drawn at. */
export type PlacedBox = MapNode & { position: Position };

/** What the map has on the glass. */
export interface OnTheGlass {
  /** Every box that is drawn, each with the place it is drawn at. */
  readonly boxes: readonly PlacedBox[];
  /**
   * The reserved rectangles among them, with their places.
   *
   * Handed back so that the next answer can be worked out from this one: a
   * rectangle comes down when the claim it was holding a place for is drawn, and
   * that cannot be decided without knowing which rectangles were standing.
   */
  readonly rectangles: readonly PlacedBox[];
}

/** Is this box a reserved rectangle rather than a claim? */
function isRectangle(box: MapNode): boolean {
  return box.type === "skeleton";
}

/**
 * Work out what the map draws.
 *
 * Three rules, which are one rule seen from three sides: **the map draws a box
 * where the layout put it, and a reserved rectangle keeps saying where the next
 * claim goes until that claim is drawn.**
 *
 * **A box is drawn where the layout put it, and nowhere else.** A box the layout
 * has not placed has no place, and drawing it at the map's origin gives it one
 * the layout never agreed to — so it appears at the origin and then hops to
 * wherever the layout actually wanted it. A tile does move on this screen, but
 * only when an arrow would otherwise point backwards, and once when the run
 * stops (INV-workbench.64, decision record 0024) — a hop from a place nobody
 * worked out is not one of those, and is what this file exists to prevent.
 *
 * **A reserved rectangle stands until the claim it was holding a place for is on
 * the glass** — not until the event carrying that claim arrived. Those are
 * different moments, and everything between them is a map with a claim on its
 * way and no rectangle anywhere: a growing map that has stopped saying where it
 * is going. It is not a corner case. A generated map's frontier is usually one
 * claim wide, so it turns over completely every few proposals, and each turnover
 * is one of these moments. The rectangle goes the instant the map is whole
 * again, and a rectangle whose claim closed with nothing coming after it — a
 * third refusal, a broken run, the likelihoods landing — goes at once, because
 * then nothing on the map is waiting for a place.
 *
 * **And before the layout has answered anything at all, the map holds the first
 * rectangle at the origin itself.** The origin is nobody's place then: there is
 * nothing to be drawn on top of, and a generation's first paint may not be an
 * empty stage (INV-workbench.61 — a rectangle carrying the reader's own sentence
 * is on screen before the first proposal comes back). The box that takes it is a
 * rectangle and never a claim.
 *
 * @param boxes Every box the map holds, in reading order.
 * @param places Where the layout has said each box goes. Empty until it answers.
 * @param standing The rectangles this returned last time it was asked, so the
 *   ones still holding a place can go on holding it.
 */
export function whatIsOnTheGlass(
  boxes: readonly MapNode[],
  places: ReadonlyMap<string, Position>,
  standing: readonly PlacedBox[],
): OnTheGlass {
  const drawn: PlacedBox[] = [];
  let somethingHasNowhereToGo = false;
  for (const box of boxes) {
    const at = places.get(box.id);
    if (at === undefined) {
      somethingHasNowhereToGo = true;
      continue;
    }
    drawn.push({ ...box, position: at });
  }
  if (!somethingHasNowhereToGo) {
    return { boxes: drawn, rectangles: drawn.filter(isRectangle) };
  }

  // Something on the map is waiting for a place, so every rectangle that was
  // standing goes on standing: each of them is holding the place of a claim that
  // is on its way and not yet drawn. They were placed in the arrangement that is
  // still on the glass, so none of them can land on anything.
  const alreadyDrawn = new Set(drawn.map((box) => box.id));
  const held = standing.filter((box) => !alreadyDrawn.has(box.id));

  // Nothing has ever been placed, and nothing is being held. This is a
  // generation's first paint: the map puts its own first rectangle at the origin
  // rather than show an empty stage. A map with no rectangles at all — every
  // finished map — waits, because it has nothing to say yet and no reason to
  // guess where it would go.
  const first =
    drawn.length === 0 && held.length === 0
      ? boxes
          .filter(isRectangle)
          .slice(0, 1)
          .map((box) => ({ ...box, position: THE_ORIGIN }))
      : [];

  const all = [...drawn, ...held, ...first];
  return { boxes: all, rectangles: all.filter(isRectangle) };
}
