/**
 * The one wire that runs backwards.
 *
 * A map reads left to right: causes on the left, what they cause on the right.
 * Exactly one kind of arrow is allowed to break that — a market feeding back on
 * the world — and on the stored example it is the oil price feeding back on an
 * output decision that then pushes the oil price the other way.
 *
 * Left to the ordinary router, that arrow takes the shortest orthogonal path
 * back across the map and passes straight through whatever tile is in the way.
 * On the stored example it ran behind the dead-end tile, which made that tile
 * look as though it had a wire leaving it towards the two tradeable endings —
 * a picture that says something untrue. So this one wire is routed over the
 * top of the map instead, where there is nothing to cross.
 *
 * **This is a placeholder and it is meant to be replaced.** The wires are about
 * to carry five things at once — what kind of push this is, how hard, whether
 * it has to keep holding, whether it loops back, and where it came from — and a
 * feedback arrow's proper drawing is a loop with the delay written on it. The
 * dashed stroke below says one thing only, *this one runs backwards*, and the
 * work that gives the stroke its real job takes it away again.
 */

import { BaseEdge, type Edge, type EdgeProps } from "@xyflow/react";

/** What a feedback wire needs beyond its two ends. */
export interface FeedbackWireData extends Record<string, unknown> {
  /**
   * The line the wire travels along, above every tile on the map.
   *
   * Worked out from the layout — the top of the highest tile, less a gap — and
   * handed in, because an edge cannot see where the other tiles are.
   */
  readonly skyY?: number;
}

/** A feedback wire as the canvas knows it. */
export type FeedbackEdge = Edge<FeedbackWireData, "feedback">;

/** How far the wire stands off a tile before it turns. */
const STANDOFF = 24;

/** How round the corners are. */
const CORNER = 8;

/**
 * Draw a path through these corners, with the corners rounded off.
 *
 * Each turn is cut back along both of its arms and joined with a curve, so the
 * wire bends rather than snapping. A corner is never cut back further than half
 * the arm it sits on, so two turns close together cannot cross each other.
 *
 * @param points The corners, in order, starting and ending at the two sockets.
 */
export function roundedPath(points: readonly (readonly [number, number])[]): string {
  const first = points[0];
  const last = points[points.length - 1];
  if (first === undefined || last === undefined) {
    return "";
  }
  let path = `M ${first[0]},${first[1]}`;
  for (let i = 1; i < points.length - 1; i += 1) {
    const before = points[i - 1];
    const here = points[i];
    const after = points[i + 1];
    if (before === undefined || here === undefined || after === undefined) {
      continue;
    }
    const inLength = Math.hypot(here[0] - before[0], here[1] - before[1]);
    const outLength = Math.hypot(after[0] - here[0], after[1] - here[1]);
    const cut = Math.min(CORNER, inLength / 2, outLength / 2);
    const startX = here[0] + ((before[0] - here[0]) / (inLength || 1)) * cut;
    const startY = here[1] + ((before[1] - here[1]) / (inLength || 1)) * cut;
    const endX = here[0] + ((after[0] - here[0]) / (outLength || 1)) * cut;
    const endY = here[1] + ((after[1] - here[1]) / (outLength || 1)) * cut;
    path += ` L ${startX},${startY} Q ${here[0]},${here[1]} ${endX},${endY}`;
  }
  return `${path} L ${last[0]},${last[1]}`;
}

/** The feedback wire: out of its cause, over the map, and back down into its effect. */
export function FeedbackWire({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  data,
}: EdgeProps<FeedbackEdge>) {
  // Above the highest tile if we were told where that is; otherwise above
  // whichever of the two ends is higher, which is still out of the way of both.
  const sky = data?.skyY ?? Math.min(sourceY, targetY) - 64;
  const path = roundedPath([
    [sourceX, sourceY],
    [sourceX + STANDOFF, sourceY],
    [sourceX + STANDOFF, sky],
    [targetX - STANDOFF, sky],
    [targetX - STANDOFF, targetY],
    [targetX, targetY],
  ]);
  return <BaseEdge id={id} path={path} markerEnd={markerEnd} className="wire--feedback" />;
}
