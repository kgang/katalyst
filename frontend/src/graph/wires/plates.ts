/**
 * Where every wire's plate goes — worked out for the whole map at once.
 *
 * A plate is the small board in the middle of a wire that reads the push back in
 * words. Until now each wire placed its own, and a wire cannot see its
 * neighbours: on the base map that was enough, because no two plates wanted the
 * same piece of empty space. Lay the branch over the base map and it stops being
 * enough. The union carries the strike and its three arrows, two of them
 * crossing the middle of the map, and the plates began landing on each other —
 * `−2.4 a strong push against` written over `a strong push toward`, with neither
 * readable.
 *
 * **The rule is one pass, in the map's own order.** Every plate is offered a
 * list of spots along its own wire — the natural one first, then further along
 * the same run, then stepped off to one side and the other — and it takes the
 * first whose rectangle touches no tile, no mark and no plate already placed.
 * Two wires that have to share a corridor are given separate lanes in it
 * ([`route.ts`](route.ts)), so their runs never coincide and neither can their
 * plates.
 *
 * Three things hold this together.
 *
 * **It is a pure function of the layout.** Where the tiles are, which claims the
 * arrows join, and nothing else. Nothing is measured off a drawn plate: a plate's
 * size is worked out from its own words, the same way a tile's height is worked
 * out from its claim, because a placement that read the screen back would depend
 * on the order the browser happened to draw things in.
 *
 * **The order is the map's.** Plates are placed in the order the map lists its
 * arrows, so the same map places the same way every time — and so the answer
 * never depends on which wire React happened to render first.
 *
 * **Both paintings share one coordinate space.** When two worlds are laid over
 * each other the old one is painted faint in the same place as the new, so a
 * ghosted tile is as much in the way as a solid one. The tiles handed in are the
 * union's, and that is exactly what this needs.
 */

import { DOWN_THE_TILE, PORT_STANDOFF } from "../ports";
import { lagInWords, pushAsNumber, pushInWords } from "./encodings";
import {
  type Box,
  corridorCorners,
  type Point,
  type RoutableWire,
  type RoutePlan,
  skyCorners,
} from "./route";

/* ---- Where a wire leaves and arrives ------------------------------------- */

/** Where a wire leaves its cause and where it arrives at its effect. */
export interface Sockets {
  readonly sourceX: number;
  readonly sourceY: number;
  readonly targetX: number;
  readonly targetY: number;
}

/**
 * Where this wire's two ends are, from the layout alone.
 *
 * **No port is measured to work this out, and none could be.** A plate has to
 * be placed before a single wire has been drawn, so the only thing that can say
 * where a wire will start is the arithmetic in `ports.ts` — the same arithmetic
 * the tile is drawn from and the drawing library is handed. A wire attaches a
 * clear `PORT_STANDOFF` outside the tile's edge, at the share of the tile's own
 * height its socket sits at.
 *
 * @param wire The arrow.
 * @param boxes Where the layout put each tile, by identifier.
 */
export function socketsFor(wire: RoutableWire, boxes: ReadonlyMap<string, Box>): Sockets | null {
  const from = boxes.get(wire.source);
  const to = boxes.get(wire.target);
  if (from === undefined || to === undefined) {
    return null;
  }
  const down = wire.handle.endsWith("sustain") ? DOWN_THE_TILE.sustain : DOWN_THE_TILE.trigger;
  return {
    sourceX: from.x + from.width + PORT_STANDOFF,
    sourceY: from.y + from.height * down,
    targetX: to.x - PORT_STANDOFF,
    targetY: to.y + to.height * down,
  };
}

/* ---- The mark at a wire's tail, which a plate must not cover -------------- */

/** How far past the socket the mark at the tail starts. */
export const MARK_STANDOFF = 2;

/** How wide and how tall a mark of three dots comes to, with its own padding. */
const MARK_WIDTH = 23;
const MARK_HEIGHT = 13;

/* ---- How big a plate is --------------------------------------------------- */

/**
 * How wide a character comes to in each of the two faces at thirteen pixels.
 *
 * Estimates, and it is safe for them to be estimates: they decide only how much
 * clear space a plate is given, so a generous one costs a little room and a mean
 * one costs a little overlap. They are not used to draw anything.
 */
const INTERFACE_CHARACTER = 6.4;
const MONO_CHARACTER = 7.9;

/** A stacked plate is as wide as the gutter has room for; see `wires.css`. */
const STACKED_WIDTH = 96;

/** What is left inside it once its padding and its hairline are taken off. */
const STACKED_CONTENT = STACKED_WIDTH - 18;

/** One line of thirteen-pixel words, and the two number lines above and below. */
const LINE = 17;
const STACKED_FURNITURE = 46;

/** A plate lying along its wire on one line is as tall as one line and its padding. */
const INLINE_HEIGHT = 26;

/** How wide and how tall a plate comes out, worked out from its own words. */
export interface PlateSize {
  readonly width: number;
  readonly height: number;
}

/**
 * How big this wire's plate will be.
 *
 * Worked out from the words it will hold, exactly as a tile's height is worked
 * out from its claim, and never read back from a drawn plate.
 *
 * The full plate is the one measured, not the smaller one the map switches to
 * when it is zoomed out. One geometry for both: a zoomed-out plate is strictly
 * smaller than the space its full form was given, so it fits wherever the full
 * one did — and a placement that moved as you zoomed would make the map restless.
 *
 * @param wire The arrow, for the words its plate will carry.
 * @param plan How the wire is routed, which decides the plate's shape.
 */
export function plateSize(wire: PlateWire, plan: RoutePlan): PlateSize {
  const words = pushInWords(wire.strength);
  if (plan.kind !== "direct") {
    // Lying along the wire on one line: the number, the words and the delay.
    const width =
      18 +
      pushAsNumber(wire.strength).length * MONO_CHARACTER +
      16 +
      (words.length + lagInWords(wire.lag).length) * INTERFACE_CHARACTER;
    return { width, height: INLINE_HEIGHT };
  }
  const lines = Math.max(1, Math.ceil((words.length * INTERFACE_CHARACTER) / STACKED_CONTENT));
  return { width: STACKED_WIDTH, height: STACKED_FURNITURE + lines * LINE };
}

/* ---- The pass ------------------------------------------------------------- */

/** One arrow, with what its plate needs to know as well as where it goes. */
export interface PlateWire extends RoutableWire {
  /** Whether the push survives its cause going away. It decides which side the plate steps to. */
  readonly mode: "trigger" | "sustain";
  /** How hard it pushes, signed. Only the words it reads back as are used here. */
  readonly strength: number;
  /** Days from the cause becoming true to the push reaching full size. */
  readonly lag: number;
}

/** Where one plate ended up: the middle of its box. */
export interface PlateSpot {
  readonly x: number;
  readonly y: number;
}

/** A box on the map that a plate has to stay out of. */
interface Rect {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

/** How far a plate keeps from a tile. */
const TILE_MARGIN = 4;

/** How far a plate keeps from another plate. */
const PLATE_MARGIN = 6;

/** How far a plate steps off its own wire when it cannot sit on it. */
const STEP_OFF = 8;

/** How far along the wire the plate is nudged, away from the mark at its tail. */
const ALONG_THE_WIRE = 20;

/** Do these two boxes touch, once the gap between them is allowed for? */
function meets(a: Rect, b: Rect, margin: number): boolean {
  return (
    a.x < b.x + b.width + margin &&
    a.x + a.width + margin > b.x &&
    a.y < b.y + b.height + margin &&
    a.y + a.height + margin > b.y
  );
}

/** The box a plate of this size centred on this spot would fill. */
function boxAround(spot: PlateSpot, size: PlateSize): Rect {
  return {
    x: spot.x - size.width / 2,
    y: spot.y - size.height / 2,
    width: size.width,
    height: size.height,
  };
}

/** A point some way along a straight run. */
function along(from: Point, to: Point, fraction: number): PlateSpot {
  return {
    x: from[0] + (to[0] - from[0]) * fraction,
    y: from[1] + (to[1] - from[1]) * fraction,
  };
}

/**
 * How far along a run a plate is offered a place, in order.
 *
 * The middle first, because that is where a label belongs, and then outward in
 * pairs so that a plate pushed off the middle goes the shortest distance it can.
 */
const ALONG = [0.5, 0.36, 0.64, 0.24, 0.76, 0.14, 0.86] as const;

/**
 * Every spot this wire's plate would accept, best first.
 *
 * @param wire The arrow.
 * @param plan How it is routed.
 * @param sockets Where its two ends are.
 * @param size How big its plate will be.
 */
function spotsFor(
  wire: PlateWire,
  plan: RoutePlan,
  sockets: Sockets,
  size: PlateSize,
): PlateSpot[] {
  const { sourceX, sourceY, targetX, targetY } = sockets;

  if (plan.kind === "sky") {
    // Over the top of the map, where there is nothing at all. The one place a
    // plate can always sit, and a second line above it for a map crowded enough
    // to need one.
    const corners = skyCorners(sourceX, sourceY, targetX, targetY, plan.skyY);
    const from = corners[2] ?? [sourceX, plan.skyY];
    const to = corners[3] ?? [targetX, plan.skyY];
    return [
      ...ALONG.map((fraction) => along(from, to, fraction)),
      ...ALONG.map((fraction) => {
        const at = along(from, to, fraction);
        return { x: at.x, y: at.y - size.height - STEP_OFF };
      }),
    ];
  }

  if (plan.kind === "corridor") {
    // Along the lane between two rows of tiles. The lane is clear by
    // construction, so the whole of it is fair game.
    const corners = corridorCorners(sourceX, sourceY, targetX, targetY, plan);
    const from = corners[2] ?? [plan.fromX, plan.corridorY];
    const to = corners[3] ?? [plan.toX, plan.corridorY];
    return ALONG.map((fraction) => along(from, to, fraction));
  }

  // The ordinary route across one gutter: out of the socket, down or up the
  // middle of the gutter, and into the other socket.
  const middleX = (sourceX + targetX) / 2;
  const top = targetY < sourceY ? targetY : sourceY;
  const bottom = targetY > sourceY ? targetY : sourceY;
  const drop = bottom - top;

  const spots: PlateSpot[] = [];

  // On the wire, where the drop is long enough to hold the plate with the wire
  // showing above and below it.
  if (drop >= size.height + STEP_OFF * 2) {
    for (const fraction of ALONG) {
      spots.push({ x: middleX + ALONG_THE_WIRE, y: top + drop * fraction });
    }
  }

  // Stepped clear of the wire. **Which side is the socket's**: an arrow that
  // fires once leaves the upper socket and takes the space above the wire, one
  // that has to keep holding leaves the lower socket and takes the space below.
  // Two plates from one tile can then never meet, nor land on the marks at the
  // other socket's tails.
  const sides = wire.mode === "sustain" ? [1, -1] : [-1, 1];
  const acrossTheGutter = [0, -24, 24, -44, 44];
  for (const step of [1, 2, 3]) {
    for (const side of sides) {
      const edge = side < 0 ? top - STEP_OFF : bottom + STEP_OFF;
      const y = edge + side * ((step - 1) * (size.height + STEP_OFF) + size.height / 2);
      for (const shift of acrossTheGutter) {
        spots.push({ x: middleX + shift, y });
      }
    }
  }
  return spots;
}

/** What `planPlates` is told about the map it is placing on. */
export interface PlateMap {
  /** Every arrow to be drawn, in the order the map lists them. */
  readonly wires: readonly PlateWire[];
  /** Where the layout put each tile — the union of both worlds, in one space. */
  readonly boxes: ReadonlyMap<string, Box>;
  /** How each wire is routed. */
  readonly plans: ReadonlyMap<string, RoutePlan>;
  /** How far each wire's tail mark is moved off the wire. */
  readonly tailOffsets: ReadonlyMap<string, number>;
}

/**
 * Place every plate on the map, in one pass.
 *
 * @param map The wires, the tiles, the routes and the tail offsets.
 * @returns Where each plate's middle goes, by the wire's identifier. A wire whose
 *   ends cannot be worked out is left out, and draws its plate the old way.
 */
export function planPlates(map: PlateMap): Map<string, PlateSpot> {
  const tiles: Rect[] = [...map.boxes.values()];
  const marks: Rect[] = [];
  for (const wire of map.wires) {
    const sockets = socketsFor(wire, map.boxes);
    if (sockets === null) {
      continue;
    }
    marks.push({
      x: sockets.sourceX + MARK_STANDOFF,
      y: sockets.sourceY + (map.tailOffsets.get(wire.id) ?? 0) - MARK_HEIGHT / 2,
      width: MARK_WIDTH,
      height: MARK_HEIGHT,
    });
  }

  const placed: Rect[] = [];
  const spots = new Map<string, PlateSpot>();

  for (const wire of map.wires) {
    const plan = map.plans.get(wire.id) ?? { kind: "direct" as const };
    const sockets = socketsFor(wire, map.boxes);
    if (sockets === null) {
      continue;
    }
    const size = plateSize(wire, plan);
    const offered = spotsFor(wire, plan, sockets, size);

    const taken =
      offered.find((spot) => {
        const box = boxAround(spot, size);
        return (
          !tiles.some((tile) => meets(box, tile, TILE_MARGIN)) &&
          !marks.some((mark) => meets(box, mark, 0)) &&
          !placed.some((other) => meets(box, other, PLATE_MARGIN))
        );
      }) ??
      // Nowhere clear. A plate is never dropped: a wire with no reading is a
      // wire that has stopped saying what it does, which is worse than a plate
      // that has to be moved out from under another one by hand.
      offered[0];

    if (taken === undefined) {
      continue;
    }
    spots.set(wire.id, taken);
    placed.push(boxAround(taken, size));
  }
  return spots;
}
