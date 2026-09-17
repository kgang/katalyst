/**
 * Moving around the map without a mouse.
 *
 * Two movements, and the difference between them is the whole idea:
 *
 * - **Up and down** walks the column you are in, in the order the layout put the
 *   tiles in. It is about the picture.
 * - **Left and right walks the wires**, not the screen. Going right follows an
 *   arrow *out* of the claim you are on, toward what it causes; going left
 *   follows an arrow *in*, toward what causes it. Neither has anything to do
 *   with where a tile happens to sit on the glass, and on the stored example one
 *   of them lands you on a tile to your **left**: the feedback arrow out of
 *   *Brent settles below $68* points back at *OPEC+ announces restraint*, which
 *   sits in an earlier column. Landing left after pressing right is correct — a
 *   map's meaning is its wires.
 *
 * **Feedback arrows count here even though they do not count in the diff**, and
 * that is one rule rather than a special case. From
 * `spec/multiverse/interventions.md`: *the map the engine works through is the
 * map with feedback arrows set aside; anything that asks **what can move** reads
 * that map, and anything that asks **what can I walk to** reads the whole map.*
 * Moving the keyboard asks what you can walk to.
 *
 * **When several wires leave the same claim**, the step takes the one whose far
 * end sits nearest your own height on the glass, and the others become the
 * up-and-down set where you land. So two keystrokes reach any neighbour and
 * nothing on the map is unreachable — and there is no chooser overlay, which
 * would be a pop-up in all but name.
 */

import type { LinkView } from "../world";

/** Where one tile ended up, and how tall it turned out to be. */
export interface Placed {
  readonly x: number;
  readonly y: number;
  readonly height: number;
}

/** Where every tile ended up, by identifier. */
export type PositionMap = ReadonlyMap<string, Placed>;

/** One step along a wire: where you land, which wire took you, and what else was on offer. */
export interface WireStep {
  /** The claim focus lands on. */
  readonly to: string;
  /** The wire the step took, so the line under the map can name it. */
  readonly wire: LinkView;
  /**
   * The other claims the same key could have reached.
   *
   * They become the up-and-down set at the claim you land on, so the ones the
   * step passed over are two keystrokes away rather than unreachable.
   */
  readonly others: readonly string[];
}

/** The middle of a tile, up and down. Tiles differ in height, so the top edge will not do. */
function middleOf(at: Placed): number {
  return at.y + at.height / 2;
}

/**
 * Every claim in the same column as this one, from the top down.
 *
 * A column is the set of tiles the layout gave the same left edge. That is what
 * a column *is* here: the layout puts a claim as far right as the longest chain
 * of arrows reaching it, so tiles sharing a left edge are the claims at the same
 * remove from the start of the map.
 *
 * @param id The claim to start from. It is in the answer.
 * @param positions Where every tile ended up.
 */
export function inColumn(id: string, positions: PositionMap): string[] {
  const here = positions.get(id);
  if (here === undefined) {
    return [];
  }
  return [...positions.entries()]
    .filter(([, at]) => at.x === here.x)
    .sort((a, b) => a[1].y - b[1].y)
    .map(([other]) => other);
}

/**
 * Step up or down through a set of claims, without wrapping.
 *
 * Focus does not wrap, deliberately: wrapping quietly teleports you to the other
 * end of a column and you lose your place. At the end of the set the answer is
 * `null`, and the line under the map says so rather than beeping.
 *
 * @param from The claim focus is on.
 * @param through The claims to step through — the column, or the set of wired
 *   neighbours a sideways step left over.
 * @param positions Where every tile ended up, so the set can be put in order.
 * @param way `1` to go down, `-1` to go up.
 */
export function stepThrough(
  from: string,
  through: readonly string[],
  positions: PositionMap,
  way: 1 | -1,
): string | null {
  const ordered = [...new Set([from, ...through])]
    .filter((id) => positions.has(id))
    .sort((a, b) => (positions.get(a)?.y ?? 0) - (positions.get(b)?.y ?? 0));
  const at = ordered.indexOf(from);
  if (at === -1) {
    return null;
  }
  return ordered[at + way] ?? null;
}

/**
 * Step along a wire, toward causes or toward effects.
 *
 * @param from The claim focus is on.
 * @param way `"in"` follows an arrow toward what causes this claim; `"out"`
 *   follows one toward what it causes.
 * @param wires Every arrow on the map, feedback arrows included — this is the
 *   question about what you can walk to.
 * @param positions Where every tile ended up. A claim with no position is a
 *   claim the map is not drawing, and the step never lands on one.
 * @returns Where the step lands, or `null` when there is no wire that way. Focus
 *   then does not move, which is the honest answer: the endings of the map cause
 *   nothing, so going right from one is a quiet no-op rather than a jump.
 */
export function alongWire(
  from: string,
  way: "in" | "out",
  wires: readonly LinkView[],
  positions: PositionMap,
): WireStep | null {
  const here = positions.get(from);
  if (here === undefined) {
    return null;
  }
  const reachable = wires
    .filter((wire) => (way === "out" ? wire.source === from : wire.target === from))
    .map((wire) => ({ wire, to: way === "out" ? wire.target : wire.source }))
    .filter((one) => positions.has(one.to));
  if (reachable.length === 0) {
    return null;
  }
  // The nearest on the other axis: the neighbour whose middle sits closest to
  // your own. Ties keep the order the map served the arrows in, so the same
  // keystroke on the same map always goes the same way.
  let nearest = reachable[0] as { wire: LinkView; to: string };
  let best = Number.POSITIVE_INFINITY;
  for (const one of reachable) {
    const there = positions.get(one.to);
    if (there === undefined) {
      continue;
    }
    const apart = Math.abs(middleOf(there) - middleOf(here));
    if (apart < best) {
      best = apart;
      nearest = one;
    }
  }
  return {
    to: nearest.to,
    wire: nearest.wire,
    others: reachable.filter((one) => one.to !== nearest.to).map((one) => one.to),
  };
}
