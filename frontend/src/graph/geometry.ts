/**
 * The size of a tile, in one place, because two things need to agree about it.
 *
 * The automatic layout has to know how big a tile is *before* the browser has
 * drawn one — it works out where every tile goes from the shape of the map
 * alone, and it cannot wait for measurements. So a tile is a fixed box and both
 * the layout and the stylesheet read its size from here.
 *
 * Every number is a multiple of eight, which is the grid the whole interface
 * sits on.
 */

/** How wide a tile is. Settled: 280 pixels, and measurable on any screenshot. */
export const TILE_WIDTH = 280;

/**
 * How tall a tile is.
 *
 * Clamped rather than fitted to its contents: a map of boxes that are all the
 * same height reads as a layout, and a map of boxes that are not reads as a
 * mess. What does not fit — the rest of a long claim, the rest of the evidence
 * — lives in the panel beside the map rather than stretching the box.
 */
export const TILE_HEIGHT = 272;

/**
 * Below this zoom a tile stops showing everything and shows a summary instead.
 *
 * The rule behind it: text never gets smaller than about eleven pixels on
 * screen. When the map is zoomed out far enough that it would, the tile changes
 * what it draws rather than shrinking what it draws.
 */
export const SUMMARY_BELOW_ZOOM = 0.6;

/**
 * The smallest a word may be drawn on the reader's screen, in pixels.
 *
 * Nothing in this product is designed below this size, and a zoomed-out map is
 * not allowed to sneak under it either — which is what `SMALLEST_ZOOM` is for.
 */
const SMALLEST_READABLE_TEXT = 11;

/**
 * The largest of the three type sizes, as `tokens.css` sets it.
 *
 * Repeated here, and only here, because the zoom floor below is worked out from
 * it and a stylesheet cannot be read from this file. If the token changes, this
 * changes with it.
 */
const LARGEST_TEXT = 22;

/**
 * How far out the map may be zoomed.
 *
 * A canvas shrinks everything on it as you zoom out, so "no word is ever smaller
 * than eleven pixels" is only true if there is a floor under the zoom. The
 * summary tile sets every word it draws in the largest of the three type sizes,
 * so the floor is the one zoom at which that size arrives at eleven pixels —
 * eleven divided by twenty-two, which is a half.
 */
export const SMALLEST_ZOOM = SMALLEST_READABLE_TEXT / LARGEST_TEXT;

/** How far in the map may be zoomed. Past this a tile is merely large. */
export const LARGEST_ZOOM = 1.4;

/** How many tiles a single layer may show before the rest are collapsed into one. */
export const TILES_PER_LAYER = 7;
