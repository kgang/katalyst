/**
 * Turning a world into the tiles and wires the canvas draws.
 *
 * One function, no arithmetic, and nothing invented: every tile below stands
 * for a claim the server sent, every wire for an arrow the server sent, and the
 * only judgement made here is which tiles there is room to draw.
 */

import type { Node } from "@xyflow/react";
import type { ClaimView, WorldView } from "../world";
import type { LayoutEdge, LayoutTile } from "./elkGraph";
import { TILE_MIN_HEIGHT, TILE_WIDTH, tileHeight } from "./geometry";
import { assignLayers, capLayers } from "./layers";
import { portsForAWire, portsOf } from "./ports";
import type { CausalEdge } from "./wires/CausalWire";

/** A tile standing for one claim. */
export type ClaimNode = Node<
  { claim: ClaimView; isHypothesis: boolean; versions?: number; height: number },
  "claim"
>;

/** A tile standing for the claims a column had no room for. */
export type OverflowNode = Node<{ count: number }, "overflow">;

/** Everything the canvas draws as a box. */
export type MapNode = ClaimNode | OverflowNode;

/**
 * A wire, carrying everything it needs to say its five things at once.
 *
 * How it is routed is filled in by the canvas rather than here: a wire that has
 * to skip a column needs to know where the other tiles ended up, and only the
 * canvas knows that.
 */
export type MapEdge = CausalEdge;

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

/**
 * What the tile standing in for a column's collapsed claims is called.
 *
 * The canvas reads the column back out of it, so that activating one of those
 * tiles can open the outline filtered to that column — the claims behind it
 * already have items there, and the tile only has to point at them.
 */
export const OVERFLOW_PREFIX = "more-in-column-";

/** The identifier of the tile standing in for a column's collapsed claims. */
function overflowId(layer: number): string {
  return `${OVERFLOW_PREFIX}${layer}`;
}

/**
 * Work out the tiles, the wires, and what the layout gets to see.
 *
 * @param world The world as the source handed it over.
 * @param heights How tall each tile is to be drawn, when something outside knows
 *   better than this claim alone does. A diff draws two worlds in one coordinate
 *   space, and a claim can need more room in one of them than in the other — it
 *   grows badges when an edit touched it — so the box is reserved for the taller
 *   of the two and neither painting moves anything. Left out, each tile is as
 *   tall as its own content.
 */
export function toFlow(world: WorldView, heights?: ReadonlyMap<string, number>): MapDrawing {
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
      data: {
        claim,
        isHypothesis: claim.id === world.hypothesisId,
        versions: world.versions,
        height: heights?.get(claim.id) ?? tileHeight(claim),
      },
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
  const claimWords = new Map(world.claims.map((claim) => [claim.id, claim.claim]));
  const edges: MapEdge[] = world.links
    .filter((link) => drawn.has(link.source) && drawn.has(link.target))
    .map((link) => {
      const { source, target } = portsForAWire(link.mode);
      return {
        id: link.id,
        source: link.source,
        target: link.target,
        sourceHandle: source,
        targetHandle: target,
        // One kind of wire, drawn by us. How it gets from one end to the other
        // is worked out by the canvas, which is the only thing that knows where
        // the other tiles ended up.
        type: "causal" as const,
        // What a reader who never sees the picture hears instead. Everything
        // the stroke says, said in words.
        ariaLabel:
          `arrow from ${claimWords.get(link.source) ?? link.source} ` +
          `to ${claimWords.get(link.target) ?? link.target}`,
        data: {
          shape: link.shape,
          strength: link.strength,
          mode: link.mode,
          lag: link.lag,
          reflexive: link.reflexive,
          provenance: link.provenance,
          conditional: link.conditional,
        },
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

  // **Every tile is told how big it is and where its ports are, and the layout,
  // the tile and the drawing library are all told the same numbers.**
  //
  // A tile's box is not something to be discovered: it is 280 pixels wide
  // (`TILE_WIDTH`) and exactly as tall as the height this file worked out from
  // the claim, and the components draw themselves at precisely that size. The
  // layout engine has always been told. The drawing library was not — it was
  // left to measure each tile with a `ResizeObserver`, and **it draws nothing
  // it has not measured**: a node with no size is rendered `visibility:
  // hidden`, and a wire with no measured port at either end is not rendered at
  // all.
  //
  // That is a promise the browser does not keep. When too many size
  // observations fall due in one frame the browser abandons the rest of them —
  // *"a ResizeObserver loop completed with undelivered notifications"* — and an
  // abandoned one is never delivered. A tile whose box then never changes size
  // again is never observed again, so it stays invisible for the life of the
  // page, and its arrows stay off the glass for the life of the page: the map
  // holds its claims, in their places, and says nothing about how they are
  // joined. Both halves are reachable today, on a busy machine, on the stored
  // example.
  //
  // Saying it is not a guess and not a duplicate: it is the one set of numbers,
  // handed to every thing that needs them, from the one place that worked them
  // out. A port's box comes from `ports.ts`, which is also what the tile writes
  // onto the element it draws — so what is declared here is what the browser
  // would have measured, and the library correcting itself afterwards from its
  // own measurement changes nothing. Nothing downstream reads any of it back.
  const tiles: LayoutTile[] = [];
  const sized = nodes.map((node) => {
    const height = node.type === "claim" ? node.data.height : TILE_MIN_HEIGHT;
    tiles.push({ id: node.id, height });
    const box = { ...node, initialWidth: TILE_WIDTH, initialHeight: height };
    // Only a claim's tile has ports, because only a claim is ever at the end of
    // an arrow. The tile standing in for a column's collapsed claims has none,
    // and is told none.
    return node.type === "claim" ? { ...box, handles: portsOf(height) } : box;
  }) as MapNode[];

  return { nodes: sized, edges, layoutEdges, tiles };
}
