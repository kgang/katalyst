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
 * **A pin is only good for the boxes it was made with.** Pinning exists for a
 * map that *grows*: a claim arriving must not shove the claims already drawn, so
 * every tile that has a place keeps it to the pixel. A tile that **changes
 * size** is a different question with a different answer, and holding a grown
 * tile where its shorter self went runs it into whatever sits below.
 *
 * It has to be all or none, and the reason is worth writing down: a tile's place
 * in a column is decided by its neighbours as much as by itself. Drop one tile's
 * pin and keep its neighbour's, and the engine places the unpinned one freely
 * while we force the pinned one back to a coordinate worked out for a map that
 * no longer exists — and the two meet in the middle. So the moment any box is a
 * different size from the one it was placed at, **every** pin goes and the map is
 * laid out again from scratch.
 *
 * That costs nothing the reader can see. The layout is a pure function of the
 * map, so the answer is the same every time; columns cannot slide, because which
 * column a tile is in is decided by the arrows and never by a height; and the
 * reader's place is kept by the view centring on whatever the keyboard is on,
 * which is what `layout-and-zoom.md` asks for and what the canvas already does.
 *
 * @param placed Where tiles sat after the last layout, with the heights they
 *   were placed at.
 * @param tiles Every tile to place now, with the height it will be drawn at.
 */
export function pinsFor(
  placed: ReadonlyMap<string, PinnedTile>,
  tiles: readonly LayoutTile[],
): Map<string, Position> {
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
 * placed exactly where it was — and making a tile that has just arrived find a
 * gap rather than land on one of them.
 *
 * The hint in `toElkGraph` asks the engine to leave placed tiles alone, and it
 * mostly does — but "mostly" is not a promise, and losing your place because a
 * new tile arrived is the thing this is here to prevent. So the rule is made
 * absolute on our side: **a tile that had a position keeps that position, to the
 * pixel, and only a tile that had none takes a new one.**
 *
 * **That half alone is not enough, and a map that builds itself is where it
 * shows.** `elk.position` is a hint about the *order* of a column, not a
 * coordinate the engine is bound by: it lays the whole map out freshly, moving
 * the placed tiles as it sees fit, and then we put those back where they were.
 * The tile that arrived keeps a coordinate worked out for an arrangement that no
 * longer exists — and the two meet in the middle, which on the Hormuz run put
 * one claim exactly on top of another.
 *
 * So the arriving tiles are settled afterwards, in the order the engine proposed
 * them: each keeps its column, starts where the engine put it, and slides **down**
 * until it clears every box already settled by the column's own gap. Nothing that
 * was already placed moves a pixel; the late arrival finds a gap, which is what
 * the chapter says happens and what nothing was making happen.
 *
 * Reserved rectangles are boxes here like any other. A claim drawn on top of the
 * rectangle that was held open for it is the same mistake as two claims on top of
 * each other.
 *
 * @param laidOut What the layout engine returned.
 * @param placed Where tiles already sat before it ran.
 * @returns Where every tile sits now.
 */
export function readPositions(
  laidOut: ElkNode,
  placed: ReadonlyMap<string, Position>,
): Map<string, Position> {
  const settled: Placed[] = [];
  const arriving: Placed[] = [];

  for (const child of laidOut.children ?? []) {
    const height = child.height ?? 0;
    const pinned = placed.get(child.id);
    if (pinned !== undefined) {
      settled.push({ id: child.id, at: pinned, height });
    } else {
      arriving.push({ id: child.id, at: { x: child.x ?? 0, y: child.y ?? 0 }, height });
    }
  }

  // The engine's own order, so the same map always settles the same way. The
  // identifier breaks a tie, because two boxes proposed at the same height must
  // not depend on which the engine happened to list first.
  arriving.sort((one, other) => one.at.y - other.at.y || one.id.localeCompare(other.id));

  for (const box of arriving) {
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
