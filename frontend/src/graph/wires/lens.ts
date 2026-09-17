/**
 * The hover lens: what this claim has to do with anything.
 *
 * Point at a claim and everything **not** on its path — everything that is
 * neither one of its causes, however far back, nor one of the things it causes,
 * however far forward — drops to fifteen per cent. It is the single most useful
 * thing you can do to a map of this size, because it answers *what does this
 * claim reach* instantly and with no clicking.
 *
 * **It is reachability, not arithmetic.** Follow arrows backwards from the
 * claim and forwards from it, and mark what you land on. No push is added, no
 * likelihood is moved, no shape is evaluated. Following arrows is walking, and
 * walking is not a calculation.
 *
 * **The lens follows every wire, the one that loops back included.** That is not
 * a special case; it is one rule written once, in the chapter on interventions:
 * *the map the engine works through is the map with feedback arrows set aside;
 * anything that asks "what can move" reads that map, and anything that asks
 * "what can I walk to" reads the whole map.* The lens asks what you can walk to,
 * so a claim reached only through a feedback arrow stays lit — while the diff
 * states, which are a claim about what an edit moved, set those arrows aside.
 */

/** One arrow, as far as walking the map is concerned. */
export interface WalkableWire {
  readonly id: string;
  readonly source: string;
  readonly target: string;
}

/** What the lens leaves lit. */
export interface OnThePath {
  /** The claims on the path: the hovered one, its causes, and what it causes. */
  readonly claims: ReadonlySet<string>;
  /** The arrows joining two claims that are both on the path. */
  readonly wires: ReadonlySet<string>;
}

/** Everything lit, which is what the map looks like when nothing is hovered. */
export const EVERYTHING: OnThePath | null = null;

/**
 * Walk one way from a claim and give back everything it reached.
 *
 * **Each direction keeps its own record of where it has been**, and that is not
 * a detail. The map has a loop in it — the oil price feeds back on what the
 * producers do, and the producers push the oil price back — so a claim can be
 * both something you can reach going forwards and something you can reach going
 * backwards. Share one record between the two walks and the second walk stops at
 * the first thing the first walk already found, and everything beyond it is lost:
 * point at the producers and their own causes go dark.
 *
 * @param from The claim to start at.
 * @param steps Where each claim leads, in the direction being walked.
 */
function walk(from: string, steps: ReadonlyMap<string, string[]>): Set<string> {
  const reached = new Set<string>([from]);
  const queue = [from];
  while (queue.length > 0) {
    const here = queue.pop();
    if (here === undefined) {
      continue;
    }
    for (const next of steps.get(here) ?? []) {
      if (!reached.has(next)) {
        reached.add(next);
        queue.push(next);
      }
    }
  }
  return reached;
}

/**
 * Which claims and arrows are on this claim's path.
 *
 * @param claimId The claim being pointed at, or `null` when nothing is.
 * @param wires Every arrow on the map, the one that loops back included.
 */
export function onThePathFrom(
  claimId: string | null,
  wires: readonly WalkableWire[],
): OnThePath | null {
  if (claimId === null) {
    return EVERYTHING;
  }
  const forwards = new Map<string, string[]>();
  const backwards = new Map<string, string[]>();
  for (const wire of wires) {
    forwards.set(wire.source, [...(forwards.get(wire.source) ?? []), wire.target]);
    backwards.set(wire.target, [...(backwards.get(wire.target) ?? []), wire.source]);
  }

  const claims = new Set<string>([...walk(claimId, forwards), ...walk(claimId, backwards)]);

  // An arrow is on the path when both of its ends are. That is stricter than
  // "one end is", deliberately: an arrow with one end off the path leads
  // somewhere the reader has just asked to stop looking at, and drawing it at
  // full strength would point at a tile that is no longer there.
  const lit = new Set<string>();
  for (const wire of wires) {
    if (claims.has(wire.source) && claims.has(wire.target)) {
      lit.add(wire.id);
    }
  }
  return { claims, wires: lit };
}
