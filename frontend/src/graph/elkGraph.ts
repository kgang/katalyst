/**
 * How the map is handed to the automatic layout engine, and how its answer is
 * read back.
 *
 * Everything here is a plain function over plain data: no browser, no worker,
 * no React. That is on purpose — it is the part worth testing, and it is
 * testable without starting anything.
 *
 * The layout engine is ELK, which sorts a map into left-to-right layers and
 * places the tiles in each layer so that as few arrows cross as possible. It is
 * slow enough on a large map to be worth keeping off the thread that draws the
 * page, which is what `layoutRunner.ts` does with the functions below.
 */

import type { ElkExtendedEdge, ElkNode, LayoutOptions } from "elkjs/lib/elk-api";
import { TILE_WIDTH } from "./geometry";

/** Where a tile sits, in the map's own coordinates. */
export interface Position {
  readonly x: number;
  readonly y: number;
}

/**
 * Where a tile sits, and how tall it was when it was put there.
 *
 * The height is kept beside the place because a pin is only ever good for the
 * boxes it was made with. See `pinsFor`.
 */
export interface PinnedTile {
  /** Where it was put. */
  readonly at: Position;
  /** How tall it was when it was put there. */
  readonly height: number;
}

/**
 * The pins to hand the layout engine — all of them, or none.
 *
 * **A pin holds a tile's row.** Pinning exists for a map that *grows*: a claim
 * arriving must not shove the claims already drawn up or down, so every tile
 * that has a place keeps that row. It does not hold the tile's **column** — see
 * `readPositions`, which re-reads the column from the arrows on every pass, so
 * that no arrow is ever drawn pointing backwards.
 *
 * **Two things drop every pin at once.**
 *
 * A tile that **changes size** is a different question with a different answer,
 * and holding a grown tile where its shorter self went runs it into whatever
 * sits below. It has to be all or none, and the reason is worth writing down: a
 * tile's place in a column is decided by its neighbours as much as by itself.
 * Drop one tile's pin and keep its neighbour's, and the engine places the
 * unpinned one freely while we force the pinned one back to a coordinate worked
 * out for a map that no longer exists — and the two meet in the middle. So the
 * moment any box is a different size from the one it was placed at, **every**
 * pin goes and the map is laid out again from scratch.
 *
 * And **the run stopping** drops them all, once. That is the settle (decision
 * record 0024): a map written while a reader watched is laid out once, whole, at
 * the moment it stops, and never again. It is the one moment a tile may take a
 * new row, and it is what takes the finished picture from the arrangement a
 * chain of pins left behind to the arrangement the argument actually makes.
 * Whoever calls this says when that moment is; nothing here can know.
 *
 * Dropping every pin costs nothing the reader can see. The layout is a pure
 * function of the map, so the answer is the same every time; and the reader's
 * place is kept by the view centring on whatever the keyboard is on, which is
 * what `layout-and-zoom.md` asks for and what the canvas already does.
 *
 * @param placed Where tiles sat after the last layout, with the heights they
 *   were placed at.
 * @param tiles Every tile to place now, with the height it will be drawn at.
 * @param theRunHasJustStopped True on the one pass where a map that was being
 *   written has stopped being written. Every pin goes, so the whole map is laid
 *   out afresh. False on every other pass, including the ones after it.
 */
export function pinsFor(
  placed: ReadonlyMap<string, PinnedTile>,
  tiles: readonly LayoutTile[],
  theRunHasJustStopped = false,
): Map<string, Position> {
  if (theRunHasJustStopped) {
    return new Map();
  }
  const resized = tiles.some((tile) => {
    const pin = placed.get(tile.id);
    return pin !== undefined && pin.height !== tile.height;
  });
  if (resized) {
    return new Map();
  }
  const holding = new Map<string, Position>();
  for (const tile of tiles) {
    const pin = placed.get(tile.id);
    if (pin !== undefined) {
      holding.set(tile.id, pin.at);
    }
  }
  return holding;
}

/**
 * One tile, reduced to the two things the layout engine needs: what it is
 * called and how tall it is.
 *
 * The height comes from the claim's own content — see `geometry.ts` — rather
 * than from measuring a tile the browser has drawn. That is what keeps the
 * layout a plain function of the map, testable without a browser, and it is why
 * a tile's box and the box the layout reserved for it are always the same box.
 */
export interface LayoutTile {
  readonly id: string;
  readonly height: number;
}

/** One arrow, reduced to the two things the layout engine needs. */
export interface LayoutEdge {
  readonly id: string;
  readonly source: string;
  readonly target: string;
}

/**
 * The layout settings, written out in one place so the picture can be argued
 * with rather than guessed at.
 *
 * - **layered** — claims are sorted into columns and arrows travel between
 *   them. This is what makes the map readable left to right instead of a ball
 *   of string.
 * - **RIGHT** — causes on the left, effects on the right, which is the order an
 *   English sentence puts them in.
 * - **NETWORK_SIMPLEX** — how tiles are placed up and down within a column. It
 *   pulls each tile level with the tiles it is joined to, so an arrow is
 *   horizontal wherever it can be.
 * - **semiInteractive** — when a tile already has a position, keep its place in
 *   the order of its column rather than sorting it afresh. This is what stops
 *   the map rearranging itself as it grows.
 * - **120 between layers** — the gap between columns, which is also the length
 *   of the shortest wire, and so how much room a wire has to say something.
 * - **48 within a layer** — the gap between two tiles in the same column. Not
 *   settled anywhere; chosen so the note a tile opens when you look at a belief
 *   chip has somewhere to go.
 */
export const LAYOUT_OPTIONS: LayoutOptions = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.crossingMinimization.semiInteractive": "true",
  "elk.layered.spacing.nodeNodeBetweenLayers": "120",
  "elk.spacing.nodeNode": "48",
};

/**
 * Build the map the layout engine is asked to lay out.
 *
 * Tiles that already have a position are handed back with it, as a hint that
 * says "this one is already somewhere; work around it". That, together with the
 * semi-interactive setting above, is what keeps a tile arriving late from
 * shuffling the tiles that arrived before it.
 *
 * @param tiles Every tile to place, with its height, in reading order.
 * @param edges Every arrow between them. Feedback arrows are left out by the
 *   caller: an arrow that points backwards has no say in a left-to-right order.
 * @param placed Where tiles already sit, for the ones that have been placed.
 */
export function toElkGraph(
  tiles: readonly LayoutTile[],
  edges: readonly LayoutEdge[],
  placed: ReadonlyMap<string, Position>,
): ElkNode {
  const children: ElkNode[] = tiles.map(({ id, height }) => {
    const already = placed.get(id);
    const child: ElkNode = { id, width: TILE_WIDTH, height };
    if (already !== undefined) {
      return {
        ...child,
        x: already.x,
        y: already.y,
        layoutOptions: { "elk.position": `(${already.x},${already.y})` },
      };
    }
    return child;
  });

  const wires: ElkExtendedEdge[] = edges.map((edge) => ({
    id: edge.id,
    sources: [edge.source],
    targets: [edge.target],
  }));

  return { id: "map", layoutOptions: LAYOUT_OPTIONS, children, edges: wires };
}

/**
 * The gap the layout leaves between two boxes in one column.
 *
 * The same forty-eight pixels `LAYOUT_OPTIONS` asks the engine for, written here
 * as a number because the rule below has to leave it too, and one gap written in
 * two places is two gaps waiting to disagree.
 */
export const COLUMN_GAP = Number(LAYOUT_OPTIONS["elk.spacing.nodeNode"]);

/** Do these two boxes stand in the same column? */
function sameColumn(one: Placed, other: Placed): boolean {
  return Math.abs(one.at.x - other.at.x) < TILE_WIDTH;
}

/** Do these two boxes overlap, or touch, once the column's gap is counted? */
function runsInto(one: Placed, other: Placed): boolean {
  return (
    sameColumn(one, other) &&
    one.at.y < other.at.y + other.height + COLUMN_GAP &&
    other.at.y < one.at.y + one.height + COLUMN_GAP
  );
}

/** One box, where it is and how tall it is. */
interface Placed {
  readonly id: string;
  readonly at: Position;
  readonly height: number;
}

/**
 * Read the layout engine's answer back, keeping every tile that was already
 * placed in the row it was already in — and making a tile that has just arrived,
 * or just changed column, find a gap rather than land on one of them.
 *
 * **A tile keeps its row, and only its row** *(decision record 0024,
 * 2026-09-21; this used to keep the column too)*. The vertical place is what
 * keeps the reader's place: the map they are scanning does not shuffle up and
 * down under them while it is being written. The hint in `toElkGraph` asks the
 * engine to keep each column in the order it is already in, and it mostly does —
 * but "mostly" is not a promise, so the rule is made absolute on our side.
 *
 * **The column is taken from this pass's answer, every pass.** Which column a
 * claim belongs in is decided by the arrows into it, and arrows keep arriving. A
 * claim drawn before anything pointed at it — which on the Verify door is the
 * destination, every time — starts in the leftmost column and belongs three
 * columns right by the end of the run. Holding it where it started does not stop
 * the map changing; it only makes the four arrows into it be drawn doubling
 * back, which is a picture of an argument running the wrong way. So the claim
 * moves sideways instead, on the arrival that proves it, and keeps its row.
 *
 * **A tile that moved needs a gap as much as one that arrived.** `elk.position`
 * is a hint about the order of a column, not a coordinate the engine is bound
 * by: it lays the whole map out freshly and we put the rows back. A tile sent
 * into a column it has not been in before arrives at a row worked out for a
 * different arrangement, and so can land on a tile already standing there — the
 * same failure that once put one claim exactly on top of another. So every box
 * that is not staying exactly where it was is settled afterwards, in the order
 * the engine proposed them: each keeps its new column, starts at the row it
 * wants, and slides **down** until it clears every box already settled by the
 * column's own gap. On both real generated maps this repository holds, nothing
 * has ever had to slide — a tile that moves column keeps its row exactly — and
 * the rule is here so that the one map where two tiles want one row is drawn
 * honestly rather than drawn twice in one place.
 *
 * Reserved rectangles are boxes here like any other. A claim drawn on top of the
 * rectangle that was held open for it is the same mistake as two claims on top of
 * each other.
 *
 * @param laidOut What the layout engine returned.
 * @param placed Where tiles already sat before it ran. Empty at the settle, and
 *   then every tile takes the place this answer gives it, row included.
 * @returns Where every tile sits now.
 */
export function readPositions(
  laidOut: ElkNode,
  placed: ReadonlyMap<string, Position>,
): Map<string, Position> {
  const staying: Placed[] = [];
  const looking: Placed[] = [];

  for (const child of laidOut.children ?? []) {
    const height = child.height ?? 0;
    const column = child.x ?? 0;
    const pinned = placed.get(child.id);
    if (pinned === undefined) {
      looking.push({ id: child.id, at: { x: column, y: child.y ?? 0 }, height });
    } else if (column === pinned.x) {
      staying.push({ id: child.id, at: pinned, height });
    } else {
      // The arrows moved it sideways. It keeps the row it has.
      looking.push({ id: child.id, at: { x: column, y: pinned.y }, height });
    }
  }

  // The engine's own order, so the same map always settles the same way. The
  // identifier breaks a tie, because two boxes proposed at the same height must
  // not depend on which the engine happened to list first.
  looking.sort((one, other) => one.at.y - other.at.y || one.id.localeCompare(other.id));

  const settled: Placed[] = [...staying];
  for (const box of looking) {
    let at = box.at;
    // Each pass can only push the box further down, and there are finitely many
    // boxes below it, so this always settles.
    for (let pass = 0; pass <= settled.length; pass += 1) {
      const inTheWay = settled.find((other) => runsInto({ ...box, at }, other));
      if (inTheWay === undefined) {
        break;
      }
      at = { x: at.x, y: inTheWay.at.y + inTheWay.height + COLUMN_GAP };
    }
    settled.push({ ...box, at });
  }

  return new Map(settled.map((box) => [box.id, box.at]));
}
