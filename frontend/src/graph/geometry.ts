/**
 * How big a tile is, and how far the map may be zoomed.
 *
 * The automatic layout has to know how big every tile is *before* the browser
 * has drawn one — it works out where the tiles go from the shape of the map
 * alone, and it cannot wait for measurements. So a tile's height is computed
 * here, from the claim's own content, by a plain function of plain data. That
 * keeps the layout a pure function of the map: the same map lays out the same
 * way every time, and the layout can be tested without a browser.
 *
 * The block heights below were measured once in the browser against the stored
 * example and are written down rather than read back at run time. If the tile's
 * stylesheet changes a line height or a gap, these change with it — and the
 * check for that is visual: a tile whose numbers are wrong has a gap at the
 * bottom or loses its last line.
 */

import type { ClaimView } from "../world";

/** How wide a tile is. Settled: 280 pixels, and measurable on any screenshot. */
export const TILE_WIDTH = 280;

/**
 * How tall a tile may be, at the least and at the most.
 *
 * "Clamped height" is a floor and a ceiling with the content deciding in
 * between — not one height for every tile. The floor is what a tile holding
 * only a heading, a one-line claim and the three belief chips comes to; the
 * ceiling is what the densest tile in the stored example needs, which is the
 * hypothesis, with a three-line claim, a reason and two evidence clippings.
 * Both are on the eight-pixel grid.
 */
export const TILE_MIN_HEIGHT = 152;
/**
 * The ceiling was 272, which was what the densest tile in the stored example
 * needed **before a tile could carry badges**. A claim the reader supposed and a
 * later edit pushed back down says so on its own face, in one line that names
 * the edit responsible — *Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed
 * military strike on Iranian territory"* — and that line is three lines wide on
 * a 280-pixel tile. A ceiling that cut it off would hide the one thing the tile
 * is there to say.
 */
export const TILE_MAX_HEIGHT = 320;

/* ---- The blocks a tile is made of, in pixels --------------------------- *
 * Measured in the browser, at the type sizes and line heights `tile.css`
 * sets. Every one of them is a height the browser actually produced. */

/** Top and bottom padding together: twelve pixels each. */
const PADDING = 24;

/** The gap between one block and the next. */
const GAP = 8;

/** The heading row: what kind of claim this is, and when it settles. */
const HEADER = 21;

/**
 * One line of the claim, at fifteen pixels over a line height of 1.35.
 *
 * Rounded up wherever it is used, never down: a line that is given a quarter of
 * a pixel less than it needs loses the bottom of its descenders.
 */
const CLAIM_LINE = 20.25;

/**
 * The belief chips: owner and number, with the rule above them.
 *
 * **It is still 69, and the range line is not why** *(re-measured 2026-09-22,
 * after R48 took the range off the chip)*. The rail has to hold the tallest chip
 * a tile can ever draw, because the height is reserved before anything is drawn
 * and the layout cannot know what a chip will end up reading. That tallest chip
 * is not a number: it is a reading that is **words** in a narrow column, wrapping
 * to the two lines the stylesheet allows it.
 *
 * Measured in the browser on the stored example, at 1600 × 1000, with the real
 * stylesheet:
 *
 * | What the row holds | What it comes to |
 * |---|---|
 * | one chip, a number | 52 |
 * | three chips, all numbers | 52 |
 * | two chips, one reading *Supposed · Oct 1* | **69** |
 * | three chips, one reading *the ask did not come back* | **69** |
 *
 * So the constant stays where it was, and a tile whose chips all read one line
 * carries seventeen pixels it does not use. Shrinking it to 52 would take the
 * second line off a supposed claim on the stored example's own strike branch —
 * the one tile the diff view is there to show.
 */
const BELIEF_RAIL = 69;

/**
 * The line a dead end prints saying why nothing here can be traded. Clamped to
 * two lines, and the only reason any tile prints for itself.
 */
const FINDING = 35;

/** One evidence clipping, and the gap between two of them. */
const CLIPPING = 21;
const CLIPPING_GAP = 4;

/**
 * One line of a claim's badges, and the hairline and padding the badges
 * themselves add to the block once.
 *
 * Thirteen pixels over a line height of 1.35 is 17.5, and each badge is drawn
 * with a hairline round it and a pixel of padding, which lifts a line box to
 * about 19. Both measured in the browser against the stored example's strike
 * branch, where the tallest badge line in the product — *Supposed · Oct 1 →
 * Retracted · Oct 2 · by "…"* — runs to three lines.
 */
const BADGE_LINE = 19;
const BADGE_PADDING = 4;

/**
 * Roughly how many characters of a badge fit on one line.
 *
 * The badges flow across the same 256 pixels the claim wraps in, set at thirteen
 * pixels in the interface face, whose average character is about six and a half
 * pixels wide — so about thirty-eight. An estimate, and safe to be one for the
 * same reason the claim's is: the same number decides both how tall the tile is
 * and how much room the badges get, so the two cannot disagree.
 */
const BADGE_CHARACTERS_PER_LINE = 38;

/** The separator drawn between one badge and the next, counted into the width. */
const BADGE_SEPARATOR = " → ";

/**
 * Roughly how many characters of the claim fit on one line.
 *
 * The claim has 256 pixels to wrap in (244 on the two tiles whose outline cuts
 * into one side) and is set at fifteen pixels in the interface face, whose
 * average character is about eight pixels wide — so about thirty-three.
 *
 * It is an estimate, and it is safe to be one because the same number decides
 * both how tall the tile is and how many lines the claim is allowed to show.
 * The two cannot disagree: if the estimate is generous the tile has a little
 * room to spare, and if it is mean the claim stops one line earlier than it
 * might have. Neither case can push a word out of the box.
 */
const CLAIM_CHARACTERS_PER_LINE = 33;

/** The most lines of the claim a tile ever shows. The rest lives in the panel. */
const CLAIM_MAX_LINES = 3;

/**
 * How many lines of the claim this tile shows.
 *
 * @param claim The claim, in the words the map serves it in.
 */
export function claimLines(claim: string): number {
  const wanted = Math.ceil(claim.length / CLAIM_CHARACTERS_PER_LINE);
  return Math.min(CLAIM_MAX_LINES, Math.max(1, wanted));
}

/**
 * How many lines this claim's badges take.
 *
 * Zero when it has none, which is every claim on a map nobody has edited.
 *
 * @param claim The claim the tile is for.
 */
export function badgeLines(claim: ClaimView): number {
  const badges = claim.badges ?? [];
  if (badges.length === 0) {
    return 0;
  }
  const characters =
    badges.reduce((sum, badge) => sum + badge.words.length, 0) +
    BADGE_SEPARATOR.length * (badges.length - 1);
  return Math.max(1, Math.ceil(characters / BADGE_CHARACTERS_PER_LINE));
}

/** Round up to the eight-pixel grid the whole interface sits on. */
function toGrid(height: number): number {
  return Math.ceil(height / 8) * 8;
}

/**
 * How tall this claim's tile wants to be, before the grid, the floor and the
 * ceiling are put to it.
 *
 * Kept apart from the bounding below because a height that has been bounded is
 * no longer a height you can do arithmetic with: two clamped numbers added
 * together can land outside the very bounds each of them was clamped into.
 *
 * @param claim The claim the tile is for.
 * @param badges How many lines the badges take. Passed in rather than read off
 *   the claim so that a caller reserving a line of its own for one badge can
 *   say so without building a second claim to say it with.
 */
function naturalHeight(claim: ClaimView, badges: number): number {
  const blocks: number[] = [HEADER, Math.ceil(CLAIM_LINE * claimLines(claim.claim)), BELIEF_RAIL];

  // The foot of the tile: the reason a slot has no number, and the evidence
  // clippings. It is only there when there is something to put in it — and
  // when the badges arrive, having one of those will put it there too.
  const foot: number[] = [];
  if (claim.kind === "not_tradeable" && claim.beliefs.market.absence !== undefined) {
    foot.push(FINDING);
  }
  const clippings = claim.evidence.length;
  if (clippings > 0) {
    foot.push(CLIPPING * clippings + CLIPPING_GAP * (clippings - 1));
  }
  if (badges > 0) {
    foot.push(BADGE_LINE * badges + BADGE_PADDING);
  }
  if (foot.length > 0) {
    blocks.push(foot.reduce((a, b) => a + b, 0) + GAP * (foot.length - 1));
  }

  return PADDING + blocks.reduce((a, b) => a + b, 0) + GAP * (blocks.length - 1);
}

/** Put a wanted height on the eight-pixel grid, inside the floor and the ceiling. */
function bounded(natural: number): number {
  return Math.min(TILE_MAX_HEIGHT, Math.max(TILE_MIN_HEIGHT, toGrid(natural)));
}

/**
 * How tall this claim's tile is: as tall as its own content, on the grid, and
 * inside the floor and the ceiling.
 *
 * @param claim The claim the tile is for.
 */
export function tileHeight(claim: ClaimView): number {
  return bounded(naturalHeight(claim, badgeLines(claim)));
}

/**
 * How tall a box this claim's tile needs when how far its number moved gets a
 * line of its own.
 *
 * A tile is as tall as its own content, and the layout has to know that before
 * the browser has drawn one — so the height is a plain function of the claim.
 * This adds one thing to it: **the movement line is not packed in with whatever
 * the edits had to say.** On the busiest tile on the map, *Supposed · Oct 1 →
 * Retracted · Oct 2 · by "…"* already runs to three lines, and stringing a
 * reading on the end of that run pushes a line out of the box.
 *
 * The extra line is measured rather than written down — the words and the
 * reading are each measured on their own — so if the badge line height ever
 * changes, this changes with it.
 *
 * **The wanted height is worked out once and bounded once.** This was first
 * written as three already-bounded heights added and subtracted — with the
 * badges, with the reading, less the empty tile — and a bounded height is not a
 * number to do arithmetic with. The floor is added twice and taken off once, so
 * an ordinary tile is handed more room than its content needs (the busiest tile
 * on the stored example: 296 pixels reserved against the 280 it wants), and
 * nothing holds the total under the ceiling that each of the three was clamped
 * into.
 *
 * @param claim The claim the tile is for.
 */
export function roomFor(claim: ClaimView): number {
  const badges = claim.badges ?? [];
  const said = badges.filter((badge) => badge.movement !== true);
  const moved = badges.filter((badge) => badge.movement === true);
  const lines =
    said.length === 0 || moved.length === 0
      ? badgeLines(claim)
      : badgeLines({ ...claim, badges: said }) + badgeLines({ ...claim, badges: moved });
  return bounded(naturalHeight(claim, lines));
}

/* ---- Zoom --------------------------------------------------------------- */

/**
 * The smallest a word may be drawn on the reader's screen, in pixels.
 *
 * This is the rule the two zoom numbers below are worked out from, rather than
 * a number chosen for how it looked.
 */
const SMALLEST_READABLE_TEXT = 11;

/** The smallest and largest of the three type sizes, as `tokens.css` sets them. */
const SMALLEST_TEXT = 13;
const LARGEST_TEXT = 22;

/**
 * Below this zoom a tile stops showing everything and shows a summary instead.
 *
 * **This was 0.6, and it is now eleven over thirteen — about 0.85.** The plan
 * settled on 0.6 before the type scale was settled, and the two turned out not
 * to fit together: a full tile's smallest words are thirteen pixels, so at 0.6
 * zoom they arrive on the glass at under eight, which breaks the rule that
 * nothing is ever drawn below eleven. Eleven over thirteen is the exact zoom at
 * which thirteen-pixel type lands at eleven pixels, so a full tile is only ever
 * shown at or above it, and below it the summary takes over — which sets every
 * word in the largest size and so clears the floor down to the zoom at which
 * even that size would fall under it, `SILHOUETTE_BELOW_ZOOM`.
 */
export const SUMMARY_BELOW_ZOOM = SMALLEST_READABLE_TEXT / SMALLEST_TEXT;

/**
 * Below this zoom a tile stops showing words at all and shows its shape.
 *
 * The summary sets every word it draws in the largest of the three type sizes,
 * so this is the one zoom at which that size arrives at eleven pixels: eleven
 * over twenty-two, which is a half. Below it there is no size left to fall back
 * to — the largest one has run out — so the answer is the same answer the tile
 * gave at the first threshold, taken one step further: draw less rather than
 * draw it smaller, and what is left when the last word goes is the shape.
 *
 * **This was the floor until 2026-09-22.** Kent asked whether the map could
 * zoom out a lot more; it can, because below this line the eleven-pixel rule
 * has nothing left to say about a tile that prints nothing. The number has not
 * moved and is derived exactly as it was — it has stopped being the end of the
 * zoom and become the last of the three forms.
 */
export const SILHOUETTE_BELOW_ZOOM = SMALLEST_READABLE_TEXT / LARGEST_TEXT;

/**
 * The smallest a thing the reader points at may be drawn, in pixels.
 *
 * Twenty-four by twenty-four, from the Web Content Accessibility Guidelines
 * 2.2, success criterion 2.5.8 *Target Size (Minimum)*, at level AA. It is the
 * published floor for anything a pointer has to land on, and it is what the
 * zoom floor below is worked out from — the same way the text floor above
 * works out the other two zoom numbers.
 */
const SMALLEST_TARGET = 24;

/**
 * How far out the map may be zoomed.
 *
 * **It is derived, not chosen** *(2026-09-22, Kent: "Can we make it so it's
 * possible to zoom out a lot more?")*. Below the silhouette threshold there is
 * no word left on a tile to keep above eleven pixels, so the eleven-pixel rule
 * has stopped being the thing that decides. The next question down is the one
 * that decides instead: **how small may a tile's box get and still be something
 * a reader can point at, and tell apart from a wire?**
 *
 * The shortest box this map ever draws is `TILE_MIN_HEIGHT` — a hundred and
 * fifty-two pixels, the floor of a tile's clamped height, and the exact height
 * of a reserved rectangle and of a "+n more" tile as well. So the floor is the
 * zoom at which that shortest side lands on the smallest target anything may be
 * drawn at: twenty-four over a hundred and fifty-two, about 0.158.
 *
 * **The other side of the box comes out of it for free, and is worth writing
 * down.** At that zoom a tile's two hundred and eighty pixels of width land at
 * 44.2 — clear of the forty-four by forty-four of the same guidelines' stricter
 * rule, success criterion 2.5.5 *Target Size* at level AAA, which Apple's
 * interface guidelines name as well. So the smallest box on the map is
 * forty-four across and twenty-four down: a target in both directions, and
 * nothing like the one-pixel stroke of a wire.
 *
 * The old floor, eleven over twenty-two, is `SILHOUETTE_BELOW_ZOOM` above.
 */
export const SMALLEST_ZOOM = SMALLEST_TARGET / TILE_MIN_HEIGHT;

/** How far in the map may be zoomed. Past this a tile is merely large. */
export const LARGEST_ZOOM = 1.4;

/**
 * Which of the three forms a tile takes, from nearest to furthest.
 *
 * - **full** — everything: the heading, the claim, the chips, the foot.
 * - **summary** — the claim and the chips, set in the largest type size.
 * - **silhouette** — the shape and its kind's colour, and no words at all.
 */
export type TileDetail = "full" | "summary" | "silhouette";

/**
 * Which form a tile takes at this zoom.
 *
 * Written once, here, beside the two thresholds it reads, because three things
 * have to agree on it: the tile itself, the plate in the middle of a wire —
 * which is words, and goes when the words go — and the reserved rectangles at a
 * growing map's edge.
 *
 * @param zoom How far the map is zoomed in, where 1 is life size.
 */
export function detailAt(zoom: number): TileDetail {
  if (zoom < SILHOUETTE_BELOW_ZOOM) {
    return "silhouette";
  }
  return zoom < SUMMARY_BELOW_ZOOM ? "summary" : "full";
}

/**
 * The smallest type size a tile draws at this zoom, in pixels, before the map's
 * own scaling is applied — or nothing at all, where the tile draws no words.
 *
 * Multiply it by the zoom and you have what lands on the reader's screen, which
 * is what `layout.test.ts` checks never falls below eleven. Below the
 * silhouette threshold the answer is `null` rather than a number, because there
 * is no smallest word where there is no word: a size returned there would be a
 * size nothing is set in, and the eleven-pixel check would be checking a
 * fiction.
 *
 * @param zoom How far the map is zoomed in, where 1 is life size.
 */
export function smallestTextAt(zoom: number): number | null {
  if (zoom < SILHOUETTE_BELOW_ZOOM) {
    return null;
  }
  return zoom < SUMMARY_BELOW_ZOOM ? LARGEST_TEXT : SMALLEST_TEXT;
}

/** The smallest a word is ever drawn on the reader's screen, in pixels. */
export const TEXT_FLOOR = SMALLEST_READABLE_TEXT;

/* ---- The first frame ----------------------------------------------------- */

/** A rectangle in the map's own coordinates. */
export interface Box {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

/** How far the map is moved and zoomed to put something in front of the reader. */
export interface Frame {
  /** How far in the map is zoomed, where 1 is life size. */
  readonly zoom: number;
  /** How far the map is slid sideways, in screen pixels. */
  readonly x: number;
  /** How far the map is slid up or down, in screen pixels. */
  readonly y: number;
}

/** The breathing room left around the map when it is framed, as a share of its size. */
const FIRST_FRAME_MARGIN = 0.04;

/**
 * How far the zoom buttons float in from the corner of the canvas: `--space-2`,
 * which is the margin `canvas.css` gives `.react-flow__controls`.
 */
const CONTROLS_INSET = 16;

/**
 * How wide the column of zoom buttons is: `--space-4` for the button itself and
 * the hairline drawn around the stack of them. Measured on the page at two
 * window sizes on 2026-09-22: they stand from 16 to 50 pixels in from the left
 * edge of the canvas.
 */
const CONTROLS_WIDE = 34;

/**
 * How far in from the left edge of the canvas the zoom buttons reach.
 *
 * Exported so that the promise *the map never starts under a control* can be
 * checked against the buttons' own geometry rather than against the frame's own
 * constant, which would be a test of nothing.
 */
export const PAST_THE_ZOOM_BUTTONS = CONTROLS_INSET + CONTROLS_WIDE;

/**
 * The clear space the frame leaves at the edge of the canvas.
 *
 * **It is the room the zoom buttons take, and that is the whole point**
 * *(2026-09-22)*. The buttons float over the bottom-left corner of the canvas,
 * and this gap used to be `--space-2` — the same sixteen pixels the buttons
 * themselves are inset by — so a map that did not fit was started at exactly the
 * place they sit, and its bottom-left tile was drawn underneath them. Measured
 * on the stored example at 1280 × 800: the hypothesis, the one tile a reader
 * looks at first, with the zoom buttons over its corner.
 *
 * So the map starts on the far side of them, with the same gap again between the
 * two, and nothing a reader has to read is ever behind a control.
 */
const EDGE_GAP = PAST_THE_ZOOM_BUTTONS + CONTROLS_INSET;

/**
 * The same gap at the top, where nothing floats over the map.
 *
 * The left edge has to clear the zoom buttons; the top has only to not touch, so
 * it keeps the plain `--space-2` it always had. One constant each, rather than
 * one constant doing two jobs and pushing fifty pixels of map off the bottom of
 * the window to make room for buttons that are not up there.
 */
const TOP_GAP = CONTROLS_INSET;

/**
 * How the map is framed the first time it is drawn — and the one promise that
 * framing makes: **the first frame never shows summary tiles.**
 *
 * **And so it never shows silhouettes either** *(2026-09-22)*. The frame is
 * held at or above the zoom at which a full tile would have to become a
 * summary, and the third form begins further out still — so the promise covers
 * both without being widened. The map now zooms out a great deal further than
 * it did; the reader goes there by asking, and never by opening a map.
 *
 * The obvious rule is "fit the whole map". On a wide screen with the panel beside
 * it that lands at about 0.8 zoom on the stored example, which is under the zoom
 * at which a full tile's smallest words would be drawn below eleven pixels — so
 * every tile would open as a summary, and the reader's first sight of the
 * product would be seven boxes with a headline and three numbers in them.
 *
 * So the rule has a floor, and the floor is the same eleven-pixel rule
 * everything else here is derived from: frame the whole map if it fits at a
 * readable size, and if it does not, keep the readable size and start at the
 * map's beginning, on the left, where the hypothesis is. The reader pans to the
 * rest. A tile changes representation rather than shrinking; the same principle,
 * applied to the frame rather than to the tile.
 *
 * **And when it does not fit, it starts on the far side of the zoom buttons**
 * *(2026-09-22)*. This gap was `--space-2`, the very sixteen pixels the buttons
 * themselves are inset by, so a map that did not fit began exactly where they
 * float — and at 1280 × 800 on the stored example the hypothesis, the first
 * tile anybody reads, was drawn underneath them. See `EDGE_GAP`.
 *
 * **What this does not fix, measured the same day.** The stored map was four
 * columns then, and at 1600 × 1000 it *did* fit: 1252 pixels of map at the
 * readable zoom in a stage 1264 wide, centred with six pixels to spare on each
 * side and its last column all but touching the panel. That was not a margin
 * somebody forgot — there were twelve pixels in the whole stage to share out,
 * and leaving a proper gap would have made the map stop fitting and be cut
 * instead, which is worse.
 *
 * **It is five columns now, and it no longer fits at all** *(2026-09-22, when
 * the map gained the claim that the strait stays open)*. Five columns is 1880
 * pixels of map, 1591 at the readable zoom, against 1264 of stage with the panel
 * beside it and 1574 with the panel folded away — so the map is started at its
 * beginning and its last column is past the right edge either way, which is what
 * the rule above says to do and what the stage's own *there is more this way*
 * mark is for. The fix for both of these is a narrower panel or a lower floor on
 * the zoom, and it is neither of them here.
 *
 * @param map Everything the frame has to hold, in the map's own coordinates.
 * @param canvas How much room there is for it, in screen pixels.
 */
export function firstFrame(map: Box, canvas: { width: number; height: number }): Frame {
  const fits = Math.min(
    canvas.width / (map.width * (1 + FIRST_FRAME_MARGIN)),
    canvas.height / (map.height * (1 + FIRST_FRAME_MARGIN)),
  );
  // Never blown up past life size, however small the map; never shrunk past the
  // point where a full tile would have to become a summary.
  const zoom = Math.max(SUMMARY_BELOW_ZOOM, Math.min(1, fits));
  const place = (room: number, gap: number, start: number, size: number): number => {
    const shown = size * zoom;
    return shown <= room ? (room - shown) / 2 - start * zoom : gap - start * zoom;
  };
  return {
    zoom,
    // The left edge is the one the zoom buttons float over, so a map that has to
    // start there starts past them. The top has nothing over it.
    x: place(canvas.width, EDGE_GAP, map.x, map.width),
    y: place(canvas.height, TOP_GAP, map.y, map.height),
  };
}

/** How many tiles a single layer may show before the rest are collapsed into one. */
export const TILES_PER_LAYER = 7;
