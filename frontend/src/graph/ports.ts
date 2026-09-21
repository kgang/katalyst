/**
 * Where a tile's ports are, and the one place that says so.
 *
 * A **port** is the socket a wire attaches to. Every tile has four: a pair on
 * the left edge for arrows arriving and a pair on the right for arrows leaving,
 * and in each pair the upper socket is for an arrow that fires once and stays
 * fired, the lower for one that only holds while its cause holds. What a wire
 * means is visible at the socket before you follow it anywhere.
 *
 * **A port's place is declared, not discovered — and that is the whole point of
 * this file.** The drawing library draws a wire between two ports, and left to
 * itself it finds out where a port is by measuring the page, through the very
 * same browser notification a busy browser drops. A wire whose ends were never
 * measured is not drawn at all: the map holds every claim, in its place, and
 * says nothing about how they are joined, which is the wrong picture of the
 * argument and a silent one. #37 met the same dropped notification as tiles
 * that never appeared and answered it by telling the library each tile's box
 * outright. A box is not a port, so the wire half of it was left over. This is
 * the rest of the same answer: told its box *and* where its ports sit, a tile
 * can have its wires drawn on the first frame with nothing measured at all.
 *
 * So every number a port has is written here, and written **once**. The tile
 * puts these numbers straight onto the element it draws; the drawing library is
 * handed the same numbers; `wires/plates.ts` places a plate against them. This
 * file must never read a port's place back off the screen, and nothing else may
 * write one down a second time — two places that have to agree are two places
 * that one day will not.
 */

import type { NodeHandle } from "@xyflow/react";
import { Position } from "@xyflow/react";
import type { LinkMode } from "../world";
import { TILE_WIDTH } from "./geometry";

/**
 * How wide a port is, in pixels — two steps of the eight-pixel grid the whole
 * interface sits on.
 *
 * It straddles the tile's edge, half of it inside and half outside, which is
 * why it is exactly twice the standoff below.
 */
export const PORT_WIDTH = 16;

/** How tall a port is, in pixels: enough for one bar, a gap and a second bar. */
export const PORT_HEIGHT = 6;

/**
 * How far past the tile's edge a wire attaches, in pixels.
 *
 * A wire that met the tile flush would have its last few pixels drawn under the
 * tile's own outline. Eight pixels clear is one step of the grid.
 */
export const PORT_STANDOFF = 8;

/**
 * How far down a tile each of the two sockets sits, as a share of its height.
 *
 * A share rather than a number of pixels, because a tile is as tall as its own
 * content: the pair has to stay evenly spaced about the middle on a tile of any
 * height. Read by `wires/plates.ts` as well, which has to know where a wire
 * will start before a single wire has been drawn.
 */
export const DOWN_THE_TILE: Readonly<Record<LinkMode, number>> = {
  trigger: 0.38,
  sustain: 0.62,
};

/** What a port is called. These four names are what a wire names its ends by. */
export type PortId = "in-trigger" | "in-sustain" | "out-trigger" | "out-sustain";

/** One socket on the edge of a tile. */
export interface Port {
  /** Its name, which is what a wire asks for. */
  readonly id: PortId;
  /** Whether wires leave from it or arrive at it. */
  readonly kind: "source" | "target";
  /** Which edge of the tile it is on. */
  readonly edge: Position;
  /** Which kind of push attaches here. Also what the socket is drawn as. */
  readonly mode: LinkMode;
}

/**
 * The four ports every tile has, in the order they are drawn.
 *
 * Arriving before leaving, and within each pair the one that fires once before
 * the one that holds — the same top-to-bottom order the sockets are drawn in,
 * so the list reads the way the tile looks.
 */
export const PORTS: readonly Port[] = [
  { id: "in-trigger", kind: "target", edge: Position.Left, mode: "trigger" },
  { id: "in-sustain", kind: "target", edge: Position.Left, mode: "sustain" },
  { id: "out-trigger", kind: "source", edge: Position.Right, mode: "trigger" },
  { id: "out-sustain", kind: "source", edge: Position.Right, mode: "sustain" },
];

/** A port's box, in the tile's own coordinates, with the tile's corner at zero. */
export interface PortBox {
  /** Its left edge. Negative on the left of a tile: the port straddles the edge. */
  readonly x: number;
  /** Its top edge. */
  readonly y: number;
  /** How wide it is. */
  readonly width: number;
  /** How tall it is. */
  readonly height: number;
}

/**
 * Where this port sits on a tile of this height.
 *
 * The one piece of arithmetic in this file, and every other number here and in
 * the tile comes out of it. The box straddles the tile's edge so that the wire
 * attaches a clear eight pixels outside it, and it is centred on the share of
 * the height the socket sits at.
 *
 * @param height How tall the tile is — the same number the layout reserved for
 *   it and the same number the tile is drawn at. A tile that grew a line
 *   because an edit touched it moves its ports down with it, and this is where
 *   that happens.
 * @param port Which of the four.
 */
export function portBox(height: number, port: Port): PortBox {
  return {
    x: port.edge === Position.Left ? -PORT_STANDOFF : TILE_WIDTH + PORT_STANDOFF - PORT_WIDTH,
    y: height * DOWN_THE_TILE[port.mode] - PORT_HEIGHT / 2,
    width: PORT_WIDTH,
    height: PORT_HEIGHT,
  };
}

/**
 * Every port of a tile this tall, in the shape the drawing library takes them.
 *
 * Handed over with the tile's box, so that the library knows where both ends of
 * every wire are before it has measured anything. It keeps measuring afterwards
 * and rebuilds these from what it measures; the numbers are the same numbers,
 * because the tile was drawn from them.
 *
 * @param height How tall the tile is.
 */
export function portsOf(height: number): NodeHandle[] {
  return PORTS.map((port) => ({
    id: port.id,
    type: port.kind,
    position: port.edge,
    ...portBox(height, port),
  }));
}

/**
 * Which port a wire of this kind leaves from, and which it arrives at.
 *
 * @param mode Whether the push fires once or has to keep holding.
 */
export function portsForAWire(mode: LinkMode): {
  readonly source: PortId;
  readonly target: PortId;
} {
  return mode === "sustain"
    ? { source: "out-sustain", target: "in-sustain" }
    : { source: "out-trigger", target: "in-trigger" };
}
