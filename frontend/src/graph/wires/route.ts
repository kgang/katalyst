/**
 * Where a wire goes, when the short way would take it through a tile.
 *
 * The map is laid out in columns: causes on the left, what they cause on the
 * right, with a gutter between one column and the next. Most arrows join
 * neighbouring columns, and for those the ordinary orthogonal route is right —
 * out of the cause, across the gutter, into the effect, and it never touches
 * anything.
 *
 * Two arrows on the stored example are not like that.
 *
 * **An arrow that skips a column.** *The strait reopens* pushes *Brent settles
 * below $68* directly, and the insurance claim sits in the column between them.
 * The ordinary route runs straight through that tile. Because a tile is drawn
 * over a wire, the wire disappears behind it and comes out the other side — so
 * the picture says the insurance claim causes the oil price *and* that the
 * strait does not, which is the opposite of the map. A wire that vanishes is a
 * state nobody can trace, and that is a veto condition rather than a rough edge.
 *
 * So an arrow that skips a column travels along a **corridor**: a horizontal
 * lane between the tiles of the columns it has to cross, chosen as the free lane
 * nearest the straight line it would have taken. The corridor is worked out from
 * the layout, which is a pure function of the map, so the same map routes the
 * same way every time.
 *
 * **An arrow that runs backwards.** A market feeding back on the world is the
 * one arrow allowed to point leftwards, and there is no corridor for it: it
 * would have to cross every column between its two ends. It runs over the top of
 * the map instead, where there is nothing to cross, and carries the delay in
 * days so that the loop reads as something that takes time rather than as a
 * contradiction.
 *
 * Nothing here is arithmetic on the map's numbers. It is pixel geometry: which
 * boxes overlap which, and where the empty space is.
 */

/** A tile, as the layout placed it. */
export interface Box {
  /** The left edge. */
  readonly x: number;
  /** The top edge. */
  readonly y: number;
  /** How wide, which is the same for every tile. */
  readonly width: number;
  /** How tall, which is worked out from the claim's own content. */
  readonly height: number;
}

/** A corner of a wire's route. */
export type Point = readonly [number, number];

/** How far a wire stands off a tile before it turns. */
const STANDOFF = 24;

/** How round a wire's corners are. */
const CORNER = 8;

/** How far above the highest tile the one backwards wire travels. */
export const SKY_GAP = 56;

/** How much clear space a corridor needs before a wire will use it. */
const CORRIDOR_CLEARANCE = 24;

/** How close to a tile the edge of a clear band comes. */
const CORRIDOR_LIP = 8;

/**
 * Draw a path through these corners, with the corners rounded off.
 *
 * Each turn is cut back along both of its arms and joined with a curve, so the
 * wire bends rather than snapping. A corner is never cut back further than half
 * the arm it sits on, so two turns close together cannot cross each other.
 *
 * @param points The corners, in order, starting and ending at the two sockets.
 */
export function roundedPath(points: readonly Point[]): string {
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

/**
 * How a wire gets from one end to the other.
 *
 * `direct` is the ordinary orthogonal route between neighbouring columns, drawn
 * by the drawing library's own router. `corridor` is the route for an arrow that
 * skips a column. `sky` is the route for the one arrow that runs backwards.
 */
export type RoutePlan =
  | { readonly kind: "direct" }
  | {
      readonly kind: "corridor";
      /** The middle of the gutter just after the cause. */
      readonly fromX: number;
      /** The middle of the gutter just before the effect. */
      readonly toX: number;
      /** The clear horizontal lane the wire travels along between them. */
      readonly corridorY: number;
    }
  | { readonly kind: "sky"; readonly skyY: number };

/** One arrow, as far as routing is concerned. */
export interface RoutableWire {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  /** Which socket on the cause the arrow leaves from. */
  readonly handle: string;
  readonly reflexive: boolean;
}

/** How far apart two marks stack when their arrows leave the same socket. */
const MARK_PITCH = 14;

/**
 * How far each arrow's tail mark is moved off the wire so that two arrows
 * leaving the same socket do not draw their marks on top of each other.
 *
 * Three of the arrows on the stored example leave one claim through one socket —
 * the oil price pushes both tradeable endings and feeds back to the producers —
 * and for the first stretch out of that socket all three run along exactly the
 * same line. Their marks would land in the same place and the reader would see
 * one mark where there are three.
 *
 * So marks that share a socket **stack**, evenly spaced about the wire, in the
 * order the map lists the arrows. It is deterministic, it is the same every time
 * the map is drawn, and it says something true: these arrows leave from the same
 * place.
 *
 * @param wires Every arrow to be drawn.
 */
export function tailOffsets(wires: readonly RoutableWire[]): Map<string, number> {
  const bySocket = new Map<string, RoutableWire[]>();
  for (const wire of wires) {
    const socket = `${wire.source}:${wire.handle}`;
    bySocket.set(socket, [...(bySocket.get(socket) ?? []), wire]);
  }
  const offsets = new Map<string, number>();
  for (const sharing of bySocket.values()) {
    for (const [at, wire] of sharing.entries()) {
      offsets.set(wire.id, (at - (sharing.length - 1) / 2) * MARK_PITCH);
    }
  }
  return offsets;
}

/** Merge a set of vertical spans into the fewest that cover the same ground. */
function merged(spans: { from: number; to: number }[]): { from: number; to: number }[] {
  const sorted = [...spans].sort((a, b) => a.from - b.from);
  const out: { from: number; to: number }[] = [];
  for (const span of sorted) {
    const last = out[out.length - 1];
    if (last !== undefined && span.from <= last.to) {
      last.to = Math.max(last.to, span.to);
    } else {
      out.push({ ...span });
    }
  }
  return out;
}

/**
 * The clear horizontal lane nearest `preferredY` that crosses this strip of the
 * map without touching a tile — or `null` when there is no room anywhere.
 *
 * The lanes are the gaps between the tiles standing in the strip, plus the open
 * space above the highest and below the lowest. A gap has to be at least twice
 * the clearance wide before a wire will use it, so a wire never runs so close to
 * a tile's edge that it looks attached to it.
 *
 * @param boxes Every tile on the map, by identifier.
 * @param fromX The left edge of the strip the wire has to cross.
 * @param toX The right edge of the strip.
 * @param preferredY Where the wire would have run if nothing were in the way.
 */
export function freeCorridor(
  boxes: readonly Box[],
  fromX: number,
  toX: number,
  preferredY: number,
): number | null {
  const band = freeBand(boxes, fromX, toX, preferredY);
  return band === null ? null : (band.from + band.to) / 2;
}

/** A clear horizontal strip of the map, with room in it for one wire or several. */
export interface Band {
  /** The top of the clear strip. */
  readonly from: number;
  /** The bottom of it. */
  readonly to: number;
}

/**
 * The clear band nearest `preferredY` that crosses this strip of the map without
 * touching a tile — or `null` when there is no room anywhere.
 *
 * The bands are the gaps between the tiles standing in the strip, plus the open
 * space above the highest and below the lowest. A gap has to be at least twice
 * the clearance deep before a wire will use it, so a wire never runs so close to
 * a tile's edge that it looks attached to it.
 *
 * A band rather than a single line, because **two arrows can need the same gap**:
 * once the strike is laid over the base map, both the strait and the strike push
 * the oil price directly, and both have to cross the middle column. Sharing one
 * line would put two wires and two plates on top of each other, so the band is
 * given back whole and `planRoutes` divides it into lanes.
 *
 * @param boxes Every tile on the map, by identifier.
 * @param fromX The left edge of the strip the wire has to cross.
 * @param toX The right edge of the strip.
 * @param preferredY Where the wire would have run if nothing were in the way.
 */
export function freeBand(
  boxes: readonly Box[],
  fromX: number,
  toX: number,
  preferredY: number,
): Band | null {
  const inTheWay = boxes.filter((box) => box.x < toX && box.x + box.width > fromX);
  if (inTheWay.length === 0) {
    return { from: preferredY - CORRIDOR_CLEARANCE, to: preferredY + CORRIDOR_CLEARANCE };
  }
  const occupied = merged(inTheWay.map((box) => ({ from: box.y, to: box.y + box.height })));
  const bands: Band[] = [];

  const highest = occupied[0];
  const lowest = occupied[occupied.length - 1];
  if (highest !== undefined) {
    bands.push({
      from: highest.from - CORRIDOR_CLEARANCE * 3,
      to: highest.from - CORRIDOR_CLEARANCE,
    });
  }
  if (lowest !== undefined) {
    bands.push({ from: lowest.to + CORRIDOR_CLEARANCE, to: lowest.to + CORRIDOR_CLEARANCE * 3 });
  }
  for (let i = 0; i < occupied.length - 1; i += 1) {
    const above = occupied[i];
    const below = occupied[i + 1];
    if (above === undefined || below === undefined) {
      continue;
    }
    if (below.from - above.to >= CORRIDOR_CLEARANCE * 2) {
      bands.push({ from: above.to + CORRIDOR_LIP, to: below.from - CORRIDOR_LIP });
    }
  }
  if (bands.length === 0) {
    return null;
  }
  const middleOf = (band: Band) => (band.from + band.to) / 2;
  return bands.reduce((best, band) =>
    Math.abs(middleOf(band) - preferredY) < Math.abs(middleOf(best) - preferredY) ? band : best,
  );
}

/**
 * Work out how every wire on this map gets from one end to the other.
 *
 * @param wires Every arrow to be drawn.
 * @param boxes Where the layout put each tile, by identifier.
 */
export function planRoutes(
  wires: readonly RoutableWire[],
  boxes: ReadonlyMap<string, Box>,
): Map<string, RoutePlan> {
  const plans = new Map<string, RoutePlan>();
  const all = [...boxes.values()];

  // The one backwards wire runs above everything, so it needs to know where the
  // top of the map is. An arrow cannot see where the other tiles are.
  const tops = all.map((box) => box.y);
  const skyY = (tops.length > 0 ? Math.min(...tops) : 0) - SKY_GAP;

  // The columns, as the layout left them: every distinct left edge, in order.
  const columns = [...new Set(all.map((box) => box.x))].sort((a, b) => a - b);

  // Which arrows want which clear band, gathered before any of them is given a
  // line to run along. Two arrows that want the same gap have to be told apart,
  // and an arrow deciding on its own cannot know there is a second one.
  const wanting = new Map<
    string,
    { band: Band; wires: { id: string; fromX: number; toX: number }[] }
  >();

  for (const wire of wires) {
    if (wire.reflexive) {
      plans.set(wire.id, { kind: "sky", skyY });
      continue;
    }
    const from = boxes.get(wire.source);
    const to = boxes.get(wire.target);
    if (from === undefined || to === undefined) {
      plans.set(wire.id, { kind: "direct" });
      continue;
    }
    const fromColumn = columns.indexOf(from.x);
    const toColumn = columns.indexOf(to.x);
    // Neighbouring columns: the ordinary route crosses one gutter and nothing
    // else, so there is nothing to dodge.
    if (fromColumn < 0 || toColumn < 0 || toColumn - fromColumn <= 1) {
      plans.set(wire.id, { kind: "direct" });
      continue;
    }

    const nextColumn = columns[fromColumn + 1];
    const previousColumn = columns[toColumn - 1];
    if (nextColumn === undefined || previousColumn === undefined) {
      plans.set(wire.id, { kind: "direct" });
      continue;
    }
    // The middles of the two gutters the wire turns in: the one just after its
    // cause, and the one just before its effect. Every tile is the same width,
    // so a column's right edge is its left edge plus that width.
    const fromX = (from.x + from.width + nextColumn) / 2;
    const toX = (previousColumn + to.width + to.x) / 2;
    const band = freeBand(
      all,
      fromX,
      toX,
      // Where the wire would have gone if nothing were in the way: level with
      // the middle of the tile it is heading for.
      to.y + to.height / 2,
    );
    if (band === null) {
      // Nowhere to run. Better a wire that crosses a tile than no wire at all,
      // and the stored example never reaches this line — but a map that did
      // would still draw every arrow it has.
      plans.set(wire.id, { kind: "direct" });
      continue;
    }
    // **Keyed by the band, not by the strip.** Two arrows can cross different
    // stretches of the map and still want the same gap between the same two rows
    // of tiles — on the union, the strait and the strike both push the oil price
    // and both come through the middle. Their strips differ; the gap they want is
    // the same one, and it is the gap that has to be shared out.
    const shared = `${band.from}:${band.to}`;
    const sharing = wanting.get(shared);
    if (sharing === undefined) {
      wanting.set(shared, { band, wires: [{ id: wire.id, fromX, toX }] });
    } else {
      sharing.wires.push({ id: wire.id, fromX, toX });
    }
  }

  // **A band shared by two arrows is divided into lanes**, evenly, in the order
  // the map lists the arrows. One arrow gets the middle of the band; two get a
  // third and two thirds of it; and so on. The lanes are far enough apart that
  // neither the wires nor their plates can meet, and the answer is the same
  // every time because the order is the map's.
  for (const { band, wires: sharing } of wanting.values()) {
    for (const [at, one] of sharing.entries()) {
      const lane = band.from + ((band.to - band.from) * (at + 1)) / (sharing.length + 1);
      plans.set(one.id, { kind: "corridor", fromX: one.fromX, toX: one.toX, corridorY: lane });
    }
  }
  return plans;
}

/**
 * The corners of a wire that skips a column: out of its cause, along the
 * corridor, and down into its effect.
 *
 * @param sourceX Where the wire leaves its cause.
 * @param sourceY The height it leaves at.
 * @param targetX Where the wire arrives at its effect.
 * @param targetY The height it arrives at.
 * @param plan The corridor this wire was given.
 */
export function corridorCorners(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  plan: { readonly fromX: number; readonly toX: number; readonly corridorY: number },
): Point[] {
  return [
    [sourceX, sourceY],
    [plan.fromX, sourceY],
    [plan.fromX, plan.corridorY],
    [plan.toX, plan.corridorY],
    [plan.toX, targetY],
    [targetX, targetY],
  ];
}

/**
 * The corners of the one wire that runs backwards: out of its cause, over the
 * top of the map, and back down into its effect.
 *
 * @param sourceX Where the wire leaves its cause.
 * @param sourceY The height it leaves at.
 * @param targetX Where the wire arrives at its effect.
 * @param targetY The height it arrives at.
 * @param skyY The line above every tile that the wire travels along.
 */
export function skyCorners(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  skyY: number,
): Point[] {
  return [
    [sourceX, sourceY],
    [sourceX + STANDOFF, sourceY],
    [sourceX + STANDOFF, skyY],
    [targetX - STANDOFF, skyY],
    [targetX - STANDOFF, targetY],
    [targetX, targetY],
  ];
}

/**
 * The middle of the longest straight run of a route — where a chip goes.
 *
 * A wire's chip sits on its longest straight stretch rather than at the halfway
 * point of the whole path, because the halfway point of a path with corners in
 * it often lands on a corner, and a plate on a corner covers the turn that says
 * where the wire is going.
 *
 * @param corners The corners of the route, in order.
 */
export function longestRunMidpoint(corners: readonly Point[]): Point {
  let best: Point = corners[0] ?? [0, 0];
  let bestLength = -1;
  for (let i = 0; i < corners.length - 1; i += 1) {
    const from = corners[i];
    const to = corners[i + 1];
    if (from === undefined || to === undefined) {
      continue;
    }
    const length = Math.hypot(to[0] - from[0], to[1] - from[1]);
    if (length > bestLength) {
      bestLength = length;
      best = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];
    }
  }
  return best;
}
