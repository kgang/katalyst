/**
 * Following arrows: what can be reached from a claim, and what reaches it.
 *
 * **This is walking, not calculating.** Nothing here reads a likelihood, a
 * strength, a shape or a date. It follows arrows and collects identifiers, which
 * is why the rule that this half of the product does no arithmetic survives
 * having a diff view at all.
 *
 * **One named rule decides which arrows count**, and it is written once, in
 * `spec/multiverse/interventions.md`:
 *
 * > The map the engine works through is the map with feedback arrows set aside.
 * > Anything that asks **what can move** reads that map — the affected set, the
 * > diff states, the order the map is worked through, the columns. Anything that
 * > asks **what can I walk to** reads the whole map — the hover lens, moving
 * > along a wire with the keyboard, the outline.
 *
 * A *feedback arrow* is a market acting back on the world it measures: on the
 * stored example, a run of cheap Brent settlements pressing on what OPEC+
 * announces. It is the one arrow allowed to point backwards, and it always takes
 * time. This file is asked **what can move**, so the callers below set feedback
 * arrows aside — and that single fact is why *OPEC+ announces output restraint*
 * comes out untouched when you suppose a strike on Iran.
 */

/** One arrow, as reaching needs it: two ends and whether it points backwards. */
export interface Arrow {
  /** The arrow's identifier. */
  readonly id: string;
  /** The claim it starts at. */
  readonly source: string;
  /** The claim it ends at. */
  readonly target: string;
  /** True when this is a market acting back on the world it measures. */
  readonly reflexive: boolean;
}

/** Every arrow that gets a say in what an edit can move: the feedback ones are set aside. */
export function forward(arrows: readonly Arrow[]): Arrow[] {
  return arrows.filter((arrow) => !arrow.reflexive);
}

/** Walk arrows one way from a starting claim, collecting everything reached. */
function walk(from: string, next: ReadonlyMap<string, readonly string[]>): Set<string> {
  const reached = new Set<string>();
  const queue = [from];
  while (queue.length > 0) {
    const at = queue.pop();
    if (at === undefined) {
      break;
    }
    for (const step of next.get(at) ?? []) {
      if (!reached.has(step)) {
        reached.add(step);
        queue.push(step);
      }
    }
  }
  return reached;
}

/** Which claim each arrow leads to, from the claim it leaves. */
function outward(arrows: readonly Arrow[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const arrow of arrows) {
    map.set(arrow.source, [...(map.get(arrow.source) ?? []), arrow.target]);
  }
  return map;
}

/** Which claim each arrow comes from, from the claim it arrives at. */
function inward(arrows: readonly Arrow[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const arrow of arrows) {
    map.set(arrow.target, [...(map.get(arrow.target) ?? []), arrow.source]);
  }
  return map;
}

/**
 * Everything one observation is evidence about: up, down, and down again.
 *
 * Learning something is done by throwing away the worlds it did not happen in,
 * and that changes what the survivors say about the claim's **causes** as much
 * as about what it causes. So an observation reaches the claim observed,
 * everything it leads to, everything that leads to it, and everything those
 * causes go on to lead to — and nothing else. A claim joined to the observed one
 * by no chain of arrows either way, and sharing no cause with it, is independent
 * of what was reported.
 *
 * **This is one rule written twice, and the two copies must move together.** The
 * engine's copies are `_evidence_reach` in
 * `backend/src/katalyst/domain/patch.py` — which decides what an edit is allowed
 * to move — and `_observation_reach` in `.../propagation.py`, which decides
 * which worlds a number is read off. The set is the same in all three, and a day
 * when it is not is a day the browser tells a reader a claim cannot move while
 * the engine moves it.
 *
 * @param observed The claim the news is about.
 * @param arrows The arrows to follow, feedback arrows already set aside by the
 *   caller — this is a question about what can move.
 */
export function evidenceAbout(observed: string, arrows: readonly Arrow[]): Set<string> {
  const reached = descendants(observed, arrows);
  reached.add(observed);
  for (const cause of ancestors(observed, arrows)) {
    reached.add(cause);
    for (const one of descendants(cause, arrows)) {
      reached.add(one);
    }
  }
  return reached;
}

/**
 * Everything this claim causes, however many steps away.
 *
 * @param from The claim to start at. It is not itself in the answer.
 * @param arrows The arrows to follow. Feedback arrows are set aside by the
 *   caller, not here, so that a caller asking *what can I walk to* can pass all
 *   of them.
 */
export function descendants(from: string, arrows: readonly Arrow[]): Set<string> {
  return walk(from, outward(arrows));
}

/**
 * Everything that causes this claim, however many steps away.
 *
 * @param from The claim to start at. It is not itself in the answer.
 * @param arrows The arrows to follow.
 */
export function ancestors(from: string, arrows: readonly Arrow[]): Set<string> {
  return walk(from, inward(arrows));
}
