/**
 * What your edit did to the map, worked out from the branch and nothing else.
 *
 * Two maps exist the moment you make an edit, and one question matters: **what
 * did my edit reach, and what did it provably leave alone?** This file answers
 * it. It reads the base map and the list of edits, and hands back one word per
 * claim. **No arithmetic anywhere**: no strength is added, no likelihood is
 * moved, no shape is evaluated. Following arrows is walking, not calculating —
 * see `reach.ts` for the one rule about which arrows count.
 *
 * The four words, and where each comes from:
 *
 * | Word | Worked out by |
 * |---|---|
 * | `added` | The claim arrives in an **Add a claim** edit |
 * | `killed` | The claim is the target of a **Suppose this is false** — full stop |
 * | `downstream` | The claim is in the affected set of at least one edit |
 * | `untouched` | Everything else, and the map can say so without hedging |
 *
 * The fifth word, `shifted`, needs two numbers to compare. Nothing here ever
 * produces one, and the check for that is a test: a diff over worlds whose
 * likelihoods are absent never shifts anything.
 *
 * **Edits are applied in order, to a map that changes as they go.** That is not
 * a nicety; it is the whole of the stored example's showcase. *Suppose the
 * strait reopens* cuts the arrows into that claim **that exist at that moment** —
 * none, because it is the hypothesis. The next edit hangs a new arrow onto it,
 * and an arrow added afterwards is live. So the strike can push the strait's
 * opening back down even though the reader supposed it, and the reason is
 * visible as a sequence of three edits rather than as a number that moved on its
 * own.
 *
 * **Which claims each operation reaches** is settled once, in
 * `spec/multiverse/interventions.md`'s affected-set table, and copied here:
 *
 * | Operation | Reaches |
 * |---|---|
 * | **Suppose this is true / false** | The target and everything it causes |
 * | **This happened** | The target, what it causes, what causes it, and what those cause |
 * | **Add a claim** | The new claim and everything it causes |
 * | **Change this push** | The claim at the arrow's head, and everything that claim causes |
 * | **Split this claim** | The target's own internals — not built |
 * | **My own number** | One slot on one claim: your own number on the target |
 */

import type { DiffState, Edit } from "../../world/types";
import { type Arrow, ancestors, descendants, forward } from "./reach";

/** What reading a branch against its base map tells you. */
export interface DiffReading {
  /** One word per claim: what the edits did to it. */
  readonly states: ReadonlyMap<string, DiffState>;
  /**
   * The claims whose **computed** numbers an edit can move.
   *
   * Nearly the same set as the `downstream` claims, and deliberately not
   * identical: **My own number** reaches a claim — it writes your number into
   * your own slot on it — but it is not pushed through the map, so the model's
   * number on that claim has not moved and must not be blanked out. This set is
   * what decides whether a claim's model number reads its absence.
   */
  readonly canMove: ReadonlySet<string>;
  /** Arrows an **Add a claim** edit brought with it. */
  readonly addedLinks: ReadonlySet<string>;
  /**
   * Arrows a **Suppose this is true** or **Suppose this is false** cut.
   *
   * Supposing a claim cuts the arrows into it that exist at that moment: you are
   * saying "take this as given, and do not tell me what caused it". A cut arrow
   * is still drawn — faint and dashed, the same way the other world is drawn —
   * because an arrow that vanished would be a change nobody could see.
   */
  readonly cutLinks: ReadonlySet<string>;
  /** Arrows a **Change this push** edit moved. */
  readonly retunedLinks: ReadonlySet<string>;
}

/** Add everything in one set to another. */
function addAll(into: Set<string>, from: Iterable<string>): void {
  for (const one of from) {
    into.add(one);
  }
}

/**
 * Read a branch against its base map: one word per claim, and what happened to
 * the arrows.
 *
 * @param claimIds Every claim on the union of the two maps — the base map's
 *   claims and any the branch adds — in the order the map serves them.
 * @param arrows Every arrow on the union of the two maps. Feedback arrows are
 *   set aside inside this function, because it is being asked what an edit can
 *   move.
 * @param edits The branch's edits, in the order they were made.
 */
export function readDiff(
  claimIds: readonly string[],
  arrows: readonly Arrow[],
  edits: readonly Edit[],
): DiffReading {
  // The map as it stands while the edits are applied, one after another. It
  // starts as the base map with feedback arrows set aside, loses the arrows a
  // supposition cuts, and gains the arrows an addition brings.
  let working = forward(arrows.filter((arrow) => !isAddedByAnEdit(arrow.id, edits)));

  const affected = new Set<string>();
  const canMove = new Set<string>();
  const added = new Set<string>();
  const killed = new Set<string>();
  const addedLinks = new Set<string>();
  const cutLinks = new Set<string>();
  const retunedLinks = new Set<string>();

  /** Everything this claim reaches, itself included. */
  const fromHere = (claim: string): Set<string> => {
    const reached = descendants(claim, working);
    reached.add(claim);
    return reached;
  };

  for (const edit of edits) {
    switch (edit.op) {
      case "do": {
        // "Take this as given, and do not tell me what caused it": the arrows
        // into the target that exist right now are cut. An arrow added later is
        // live, which is what lets a later edit push a supposed claim back down.
        for (const arrow of working) {
          if (arrow.target === edit.target) {
            cutLinks.add(arrow.id);
          }
        }
        working = working.filter((arrow) => arrow.target !== edit.target);
        const reached = fromHere(edit.target);
        addAll(affected, reached);
        addAll(canMove, reached);
        if (!edit.value) {
          killed.add(edit.target);
        }
        break;
      }
      case "observe": {
        // "This is news": nothing is cut, so what is learned travels back up the
        // arrows into the causes and out again along everything they lead to.
        const reached = fromHere(edit.target);
        for (const cause of ancestors(edit.target, working)) {
          addAll(reached, fromHere(cause));
        }
        addAll(affected, reached);
        addAll(canMove, reached);
        break;
      }
      case "insert": {
        // The claim and its arrows arrive together, so the map is never left
        // holding a claim that causes nothing.
        for (const arrow of edit.arrows) {
          addedLinks.add(arrow.id);
          working.push({ ...arrow, reflexive: false });
        }
        added.add(edit.claimId);
        const reached = fromHere(edit.claimId);
        addAll(affected, reached);
        addAll(canMove, reached);
        break;
      }
      case "retune": {
        // One number on one arrow. The earliest thing that can move is the claim
        // that arrow points at.
        const arrow = working.find((one) => one.id === edit.link);
        retunedLinks.add(edit.link);
        if (arrow !== undefined) {
          const reached = fromHere(arrow.target);
          addAll(affected, reached);
          addAll(canMove, reached);
        }
        break;
      }
      case "refine":
        // Splitting a claim into finer ones is not built. The edit is recorded
        // in the branch, and the panel says plainly that it is not live, so that
        // nothing here quietly claims a reach it does not have.
        break;
      case "believe":
        // Your own number sits beside the model's and the market's and is never
        // averaged with either. It is not pushed through the map, so it reaches
        // this claim and moves nothing the map computes.
        affected.add(edit.target);
        break;
    }
  }

  const states = new Map<string, DiffState>();
  for (const id of claimIds) {
    states.set(
      id,
      killed.has(id)
        ? "killed"
        : added.has(id)
          ? "added"
          : affected.has(id)
            ? "downstream"
            : "untouched",
    );
  }

  return { states, canMove, addedLinks, cutLinks, retunedLinks };
}

/** True when this arrow is one an **Add a claim** edit brings, rather than one the base map had. */
function isAddedByAnEdit(id: string, edits: readonly Edit[]): boolean {
  return edits.some((edit) => edit.op === "insert" && edit.arrows.some((arrow) => arrow.id === id));
}
