/**
 * Turning a world into the tiles and wires the canvas draws.
 *
 * One function, no arithmetic, and nothing invented: every tile below stands
 * for a claim the server sent, every wire for an arrow the server sent, and the
 * only judgement made here is which tiles there is room to draw.
 */

import type { Edge, Node } from "@xyflow/react";
import type { ClaimView, LinkMode, WorldView } from "../world";
import type { LayoutEdge, LayoutTile } from "./elkGraph";
import { TILE_MIN_HEIGHT, tileHeight } from "./geometry";
import { assignLayers, capLayers } from "./layers";

/** A tile standing for one claim. */
export type ClaimNode = Node<
  { claim: ClaimView; isHypothesis: boolean; versions?: number },
  "claim"
>;

/** A tile standing for the claims a column had no room for. */
export type OverflowNode = Node<{ count: number }, "overflow">;

/** Everything the canvas draws as a box. */
export type MapNode = ClaimNode | OverflowNode;

/**
 * A wire, carrying which kind of push it is so the wires work can read it.
 *
 * `skyY` is filled in by the canvas rather than here: it is the line the one
 * backwards wire travels along, above every tile, and only the canvas knows
 * where the tiles ended up.
 */
export type MapEdge = Edge<{ mode: LinkMode; reflexive: boolean; skyY?: number }>;

/** What the canvas needs in order to draw a world. */
export interface MapDrawing {
  /** The tiles, without positions — those come from the layout. */
  readonly nodes: readonly MapNode[];
  /** The wires, as they will be drawn. */
  readonly edges: readonly MapEdge[];
  /**
   * Every tile with the height it will be drawn at, which is the height the
   * layout reserves for it. One number, worked out once, used by both.
   */
  readonly tiles: readonly LayoutTile[];
  /**
   * The arrows the layout gets a look at.
   *
   * Not the same list as the wires. Feedback arrows are left out, because a
   * left-to-right order cannot be worked out from a map with a loop in it, and
   * an arrow that stands in for collapsed tiles is put in, so the collapsed tile
   * lands in the column it belongs to.
   */
  readonly layoutEdges: readonly LayoutEdge[];
}

/** Which socket a wire of this kind leaves from, and which it arrives at. */
function sockets(mode: LinkMode): { source: string; target: string } {
  return mode === "sustain"
    ? { source: "out-sustain", target: "in-sustain" }
    : { source: "out-trigger", target: "in-trigger" };
}

/** The identifier of the tile standing in for a column's collapsed claims. */
function overflowId(layer: number): string {
  return `more-in-column-${layer}`;
}

/**
 * Work out the tiles, the wires, and what the layout gets to see.
 *
 * @param world The world as the source handed it over.
 */
export function toFlow(world: WorldView): MapDrawing {
  const ids = world.claims.map((claim) => claim.id);
  const { shown, overflows } = capLayers(assignLayers(ids, world.links));
  const drawn = new Set(shown.map((one) => one.id));
  const byId = new Map(world.claims.map((claim) => [claim.id, claim]));

  const nodes: MapNode[] = [];
  for (const placed of shown) {
    const claim = byId.get(placed.id);
    if (claim === undefined) {
      continue;
    }
    nodes.push({
      id: claim.id,
      type: "claim",
      position: { x: 0, y: 0 },
      draggable: false,
      data: { claim, isHypothesis: claim.id === world.hypothesisId, versions: world.versions },
    });
  }
  for (const overflow of overflows) {
    nodes.push({
      id: overflowId(overflow.layer),
      type: "overflow",
      position: { x: 0, y: 0 },
      draggable: false,
      data: { count: overflow.count },
    });
  }

  // Only arrows between two tiles that are actually drawn become wires. An
  // arrow into a collapsed claim has nowhere to land, and the collapsed tile
  // says in words that those claims are still on the map.
  const edges: MapEdge[] = world.links
    .filter((link) => drawn.has(link.source) && drawn.has(link.target))
    .map((link) => {
      const { source, target } = sockets(link.mode);
      return {
        id: link.id,
        source: link.source,
        target: link.target,
        sourceHandle: source,
        targetHandle: target,
        // A feedback arrow is routed over the top of the map rather than
        // straight back through whatever tile is in the way. Every other wire
        // takes the ordinary orthogonal route.
        type: link.reflexive ? "feedback" : "smoothstep",
        data: { mode: link.mode, reflexive: link.reflexive },
      };
    });

  // What the layout sees. Feedback arrows are set aside: an arrow that points
  // backwards cannot help decide what comes first, and leaving it in would make
  // the map a loop with no beginning.
  const layoutEdges: LayoutEdge[] = world.links
    .filter((link) => !link.reflexive && drawn.has(link.source) && drawn.has(link.target))
    .map((link) => ({ id: link.id, source: link.source, target: link.target }));

  // The collapsed tile is pulled into the right column by the same arrows that
  // would have reached the claims it stands for. These are never drawn.
  for (const overflow of overflows) {
    const hidden = new Set(overflow.hidden);
    const causes = new Set(
      world.links
        .filter((link) => !link.reflexive && hidden.has(link.target) && drawn.has(link.source))
        .map((link) => link.source),
    );
    for (const cause of causes) {
      layoutEdges.push({
        id: `standing-in:${cause}->${overflowId(overflow.layer)}`,
        source: cause,
        target: overflowId(overflow.layer),
      });
    }
  }

  const tiles: LayoutTile[] = nodes.map((node) =>
    node.type === "claim"
      ? { id: node.id, height: tileHeight(node.data.claim) }
      : { id: node.id, height: TILE_MIN_HEIGHT },
  );

  return { nodes, edges, layoutEdges, tiles };
}
