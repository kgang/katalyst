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
 *
 * **And one rule that reaches further than any row can say** *(amended
 * 2026-09-21)*, which is the same principle applied twice rather than an
 * exception to it:
 *
 * > An edit that can move a claim some observation was made about can move
 * > everything that observation is evidence about — and that applies again to
 * > any further observation whose own claim has just been brought in.
 *
 * An observation is not a number stored once. It is a filter re-read through the
 * map every time the map changes: which versions of the map survive is decided
 * by the reported claim's value, and every number the report touches is read off
 * the survivors. So changing anything that can move the reported claim changes
 * what the report says about all of them. The case that found it, in the engine:
 * report that a claim did not happen, then change how hard its one cause pushes
 * it, and **the cause** moves — how much news about an effect says about a cause
 * depends on how hard that cause was pushing. The row for **Change this push**
 * used to permit only the arrow's head and what that claim causes.
 *
 * **What that case does to this file was measured before this was written, and
 * it is not what it looks like.** This file reads a whole branch and unions what
 * its edits reach, and the report's own row already reaches the causes — so on a
 * branch holding both the report and the change of push, the arrow's source was
 * already in reach here. What was *not* in reach is a claim the map gains later:
 * attach a claim to the one that was reported and the new arrows carry the
 * evidence further, and everything joined only through them was read as out of
 * reach while the engine moved it. That is the case
 * `test_an_edit_that_can_move_a_reported_claim_can_move_what_the_report_is_about`
 * builds, and it is the one whose answer this changed.
 *
 * Two things about it are easy to get wrong, and both are load-bearing:
 *
 * - **A standing observation's reach is read off the map the edit STARTED
 *   from**, not the one it leaves behind. Suppose the very claim that was
 *   reported and the report stops holding, so everything it was evidence about
 *   moves again — but a supposition cuts the arrows into its target, so on the
 *   map afterwards the causes it has just stopped speaking about are no longer
 *   even connected to it.
 * - **My own number never triggers it.** Your number is not pushed through the
 *   map, so it cannot change which versions survive and cannot change what a
 *   report says about anything.
 *
 * **This rule is written twice and the two copies must move together**: here,
 * and in `affected_set` in `backend/src/katalyst/domain/patch.py`. The engine is
 * the authority and this is the browser's structural copy of it; where they
 * disagree, a tile says a claim cannot move while the engine moves it, which is
 * the traceability veto wearing a disguise.
 */

import type { DiffState, Edit } from "../../world/types";
import { type Arrow, descendants, evidenceAbout, forward } from "./reach";

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

  // Which claims are on the map at this point in the branch. A claim an **Add a
  // claim** edit brings is in `claimIds` from the start — that list is the union
  // of the two maps — but it is not on the map until its own edit runs, and an
  // earlier edit cannot reach a claim that is not there yet.
  const inserted = new Set(edits.flatMap((edit) => (edit.op === "insert" ? [edit.claimId] : [])));
  const present = new Set(claimIds.filter((id) => !inserted.has(id)));

  // The last word on each claim whose value an edit has fixed, over the edits
  // **before** the one being read. A later edit on the same claim overrides an
  // earlier one, so "this happened" followed by "suppose it did not" is a
  // supposition and the report throws no version of the map away any more.
  const lastWordOn = new Map<string, "do" | "observe">();

  /**
   * Grow a reach through every report still in force, until it stops growing.
   *
   * The trigger is the report's own claim being in the set already: an edit that
   * can move a reported claim changes what that report says about everything it
   * is evidence about. Bringing one report's claim in can bring in a claim a
   * **further** report was made about, so this is grown to a standstill rather
   * than swept once.
   *
   * @param reached The set to grow, in place.
   * @param startedFrom The map this edit started from, which is where a standing
   *   report's reach is read — see the note at the head of this file.
   */
  const widenThroughTheNews = (reached: Set<string>, startedFrom: readonly Arrow[]): void => {
    const standing = [...lastWordOn]
      .flatMap(([claim, word]) => (word === "observe" && present.has(claim) ? [claim] : []))
      .sort();
    let growing = true;
    while (growing) {
      growing = false;
      for (const observed of standing) {
        if (!reached.has(observed)) {
          continue;
        }
        for (const one of evidenceAbout(observed, startedFrom)) {
          if (present.has(one) && !reached.has(one)) {
            reached.add(one);
            growing = true;
          }
        }
      }
    }
  };

  for (const edit of edits) {
    // The map this edit started from. It is the same map it leaves behind for
    // five of the six — only a supposition cuts an arrow — and the difference is
    // what lets withdrawing the news move the causes it has stopped speaking
    // about.
    const startedFrom = working;
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
        widenThroughTheNews(reached, startedFrom);
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
        const reached = evidenceAbout(edit.target, working);
        widenThroughTheNews(reached, startedFrom);
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
        present.add(edit.claimId);
        const reached = fromHere(edit.claimId);
        widenThroughTheNews(reached, startedFrom);
        addAll(affected, reached);
        addAll(canMove, reached);
        break;
      }
      case "retune": {
        // One number on one arrow. The earliest thing that can move is the claim
        // that arrow points at — **and, where a report is in force, everything
        // that report is evidence about**, which is how changing how hard a
        // cause pushes moves the cause itself.
        const arrow = working.find((one) => one.id === edit.link);
        retunedLinks.add(edit.link);
        if (arrow !== undefined) {
          const reached = fromHere(arrow.target);
          widenThroughTheNews(reached, startedFrom);
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
        // this claim and moves nothing the map computes — and it is the one edit
        // a standing report never widens, for the same reason: a number that is
        // not pushed through the map cannot change which versions of it survive.
        affected.add(edit.target);
        break;
    }
    if (edit.op === "do" || edit.op === "observe") {
      lastWordOn.set(edit.target, edit.op);
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
