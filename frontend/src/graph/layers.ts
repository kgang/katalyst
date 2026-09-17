/**
 * Sorting a map into left-to-right layers, and capping how wide a layer gets.
 *
 * Two jobs, both of them about shape and neither about numbers. Nothing in this
 * file reads a likelihood, a strength or a date: it follows arrows, which is
 * counting steps, not arithmetic.
 *
 * **Why we work out the layers ourselves when the layout engine does it too.**
 * The cap — seven tiles across, then a "+n more" tile — has to be applied
 * before the layout engine is asked to place anything, or it would lay out
 * tiles it is about to be told to forget. So the layering is computed here,
 * used to decide what is shown, and the layout engine is handed the survivors.
 *
 * **Feedback arrows are set aside first.** A map is a left-to-right ordering of
 * claims, which needs there to be no loops in it. The one arrow allowed to
 * close a loop is a market feeding back on the world, and it is marked as such
 * on the map itself. Set it aside and an ordering exists again; the arrow is
 * still drawn, it just does not get a vote on who comes first.
 */

import type { LinkView } from "../world";
import { TILES_PER_LAYER } from "./geometry";

/** One claim placed in a layer. */
export interface Placed {
  /** The claim's identifier. */
  readonly id: string;
  /** Which layer it sits in, counting from zero on the left. */
  readonly layer: number;
}

/** A layer that had more tiles in it than it is allowed to show. */
export interface Overflow {
  /** Which layer overflowed. */
  readonly layer: number;
  /** How many tiles are not shown. */
  readonly count: number;
  /** The claims that are not shown, so nothing has been silently dropped. */
  readonly hidden: readonly string[];
}

/** What a map looks like once it has been sorted and capped. */
export interface Layered {
  /** The claims that are shown, each with its layer. */
  readonly shown: readonly Placed[];
  /** One entry for each layer that had to collapse some tiles. */
  readonly overflows: readonly Overflow[];
}

/**
 * Put every claim in a layer: as far right as the longest chain of arrows
 * reaching it.
 *
 * A claim with nothing pointing at it sits in layer zero. Every other claim
 * sits one layer to the right of the furthest-right claim that points at it, so
 * an arrow always travels left to right and a chain of three arrows is three
 * layers long. This is the reading order of the map, and it is why the map is
 * never a hairball: the picture has a direction.
 *
 * @param ids Every claim on the map, in the order the map serves them.
 * @param links Every arrow on the map, feedback arrows included — they are set
 *   aside here rather than by the caller.
 * @returns Each claim's layer, in the same order the claims came in.
 */
export function assignLayers(ids: readonly string[], links: readonly LinkView[]): Placed[] {
  const present = new Set(ids);
  // Feedback arrows are set aside: they are the ones allowed to point backwards,
  // and a backwards arrow has no place in deciding what comes first.
  const forward = links.filter(
    (link) => !link.reflexive && present.has(link.source) && present.has(link.target),
  );

  const causes = new Map<string, string[]>();
  for (const id of ids) {
    causes.set(id, []);
  }
  for (const link of forward) {
    causes.get(link.target)?.push(link.source);
  }

  const layer = new Map<string, number>();
  // Depth-first, remembering answers, with a guard against the loop that should
  // not be there. If a loop survived the feedback filter — a map that broke its
  // own rules — the claim lands in layer zero rather than hanging the browser.
  const inProgress = new Set<string>();
  const layerOf = (id: string): number => {
    const known = layer.get(id);
    if (known !== undefined) {
      return known;
    }
    if (inProgress.has(id)) {
      return 0;
    }
    inProgress.add(id);
    let furthest = -1;
    for (const cause of causes.get(id) ?? []) {
      furthest = Math.max(furthest, layerOf(cause));
    }
    inProgress.delete(id);
    const answer = furthest + 1;
    layer.set(id, answer);
    return answer;
  };

  return ids.map((id) => ({ id, layer: layerOf(id) }));
}

/**
 * Show at most seven tiles in a layer and collapse the rest into one.
 *
 * Seven is a cap on how wide the map gets, not a judgement about which claims
 * matter: the tiles kept are the first seven in the order the map served them,
 * and the ones that are not shown are named in the overflow so the collapsed
 * tile can say exactly what it is standing in for. A map that quietly dropped
 * claims would be lying about its own shape.
 *
 * @param placed Every claim with its layer, from `assignLayers`.
 * @returns What is shown, and one overflow entry per layer that had too many.
 */
export function capLayers(placed: readonly Placed[]): Layered {
  const byLayer = new Map<number, Placed[]>();
  for (const one of placed) {
    const existing = byLayer.get(one.layer);
    if (existing === undefined) {
      byLayer.set(one.layer, [one]);
    } else {
      existing.push(one);
    }
  }

  const shown: Placed[] = [];
  const overflows: Overflow[] = [];
  for (const [layerNumber, inLayer] of [...byLayer.entries()].sort((a, b) => a[0] - b[0])) {
    if (inLayer.length <= TILES_PER_LAYER) {
      shown.push(...inLayer);
      continue;
    }
    const kept = inLayer.slice(0, TILES_PER_LAYER);
    const hidden = inLayer.slice(TILES_PER_LAYER);
    shown.push(...kept);
    overflows.push({
      layer: layerNumber,
      count: hidden.length,
      hidden: hidden.map((one) => one.id),
    });
  }

  // Back into the order the map served them, so the picture does not depend on
  // the order the layers happened to be walked in.
  const order = new Map(placed.map((one, index) => [one.id, index]));
  shown.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0));

  return { shown, overflows };
}
