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
import { TILE_HEIGHT, TILE_WIDTH } from "./geometry";

/** Where a tile sits, in the map's own coordinates. */
export interface Position {
  readonly x: number;
  readonly y: number;
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
 * @param ids Every tile to place, in reading order.
 * @param edges Every arrow between them. Feedback arrows are left out by the
 *   caller: an arrow that points backwards has no say in a left-to-right order.
 * @param placed Where tiles already sit, for the ones that have been placed.
 */
export function toElkGraph(
  ids: readonly string[],
  edges: readonly LayoutEdge[],
  placed: ReadonlyMap<string, Position>,
): ElkNode {
  const children: ElkNode[] = ids.map((id) => {
    const already = placed.get(id);
    const child: ElkNode = { id, width: TILE_WIDTH, height: TILE_HEIGHT };
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
 * Read the layout engine's answer back, keeping every tile that was already
 * placed exactly where it was.
 *
 * The hint above asks the engine to leave placed tiles alone, and it mostly
 * does — but "mostly" is not a promise, and losing your place because a new
 * tile arrived is the thing this is here to prevent. So the rule is made
 * absolute on our side: **a tile that had a position keeps that position, to
 * the pixel, and only a tile that had none takes a new one.**
 *
 * @param laidOut What the layout engine returned.
 * @param placed Where tiles already sat before it ran.
 * @returns Where every tile sits now.
 */
export function readPositions(
  laidOut: ElkNode,
  placed: ReadonlyMap<string, Position>,
): Map<string, Position> {
  const positions = new Map<string, Position>();
  for (const child of laidOut.children ?? []) {
    const pinned = placed.get(child.id);
    if (pinned !== undefined) {
      positions.set(child.id, pinned);
      continue;
    }
    positions.set(child.id, { x: child.x ?? 0, y: child.y ?? 0 });
  }
  return positions;
}
