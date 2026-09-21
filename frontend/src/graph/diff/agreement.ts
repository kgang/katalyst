/**
 * Where the browser's reading of an edit and the engine's must agree.
 *
 * Two things read the same branch. The browser walks the arrows and says what
 * an edit **can reach**; the engine works every likelihood through and says what
 * **moved**. They answer different questions, so they are not the same list —
 * and where they *can* be compared they must agree, because a browser quietly
 * disagreeing with the engine about what an edit reached is the traceability
 * rule broken in the one place nobody would look.
 *
 * **The engine is the authority.** This file does not repair either reading and
 * does not prefer one: it hands back every place the two contradict each other,
 * in plain words, so that a test can fail with the claim named.
 *
 * Two rules, and they are the same rule read in both directions.
 *
 * | The browser says | The engine says | Verdict |
 * |---|---|---|
 * | your edit cannot reach this | it moved | a contradiction |
 * | your edit cannot reach this | it arrived with the edit | a contradiction |
 * | your edit can reach this | it arrived with the edit | a contradiction |
 * | your edit can reach this | it did not move | agreement — reachable is not moved |
 * | your edit cannot reach this | it did not move | agreement |
 *
 * The middle row is the one worth spelling out: a claim your edit can reach
 * whose number happened to hold still is **not** a claim your edit cannot reach,
 * so *reachable* and *unchanged* together are no contradiction at all.
 *
 * This file does no arithmetic and reads no likelihood. It compares words.
 */

import type { DiffState } from "../../world/types";

/** One of the four words the engine uses for what happened to a claim. */
export type EngineState = "unchanged" | "shifted" | "added" | "killed";

/**
 * What each of the engine's words means, in the reader's own.
 *
 * Exported because the change list says the same thing on a row the engine
 * ranked no move on, and one table read twice cannot drift the way two tables
 * written apart do.
 */
export const ENGINE_IN_WORDS: Record<EngineState, string> = {
  unchanged: "it did not move",
  shifted: "it moved",
  added: "it arrived with the edit",
  killed: "it was supposed false",
};

/** What each of the browser's words means, in the reader's own. */
const BROWSER_IN_WORDS: Record<DiffState, string> = {
  untouched: "an edit cannot reach this claim",
  downstream: "your edit can reach this",
  added: "it arrived with the edit",
  killed: "it was supposed false",
  shifted: "it moved",
};

/**
 * Is what the browser said and what the engine said about one claim a
 * contradiction?
 *
 * @param browser The word the browser worked out from the branch alone.
 * @param engine The word the engine worked out from the numbers.
 */
function contradicts(browser: DiffState, engine: EngineState): boolean {
  if (browser === "untouched") {
    // An edit changes only what is still joined to its subject. So a claim
    // outside its reach cannot have moved and cannot have arrived with it.
    return engine !== "unchanged";
  }
  if (browser === "added") {
    return engine !== "added";
  }
  if (browser === "killed") {
    return engine !== "killed";
  }
  // The browser said the edit can reach this claim. Whether it moved is the
  // engine's to say — both answers are consistent with being reachable — but a
  // claim that arrived with the edit should have been spotted as `added`.
  return engine === "added";
}

/**
 * Every place the browser's reading and the engine's contradict each other.
 *
 * @param browser One word per claim, as the browser worked it out from the
 *   branch: what the edit can reach and what it provably cannot.
 * @param engine One word per claim, as the engine worked it out from the
 *   numbers: what moved, what arrived and what was forced false.
 * @returns One sentence per contradiction, naming the claim and both readings.
 *   Empty when the two agree, which is what a passing test looks like.
 */
export function disagreements(
  browser: ReadonlyMap<string, DiffState>,
  engine: ReadonlyMap<string, EngineState>,
): string[] {
  const found: string[] = [];
  for (const [id, said] of engine) {
    const here = browser.get(id);
    if (here === undefined) {
      found.push(`${id}: the engine has this claim and the browser does not`);
      continue;
    }
    if (contradicts(here, said)) {
      found.push(
        `${id}: the browser says ${BROWSER_IN_WORDS[here]}, and the engine says ${ENGINE_IN_WORDS[said]}`,
      );
    }
  }
  for (const id of browser.keys()) {
    if (!engine.has(id)) {
      found.push(`${id}: the browser has this claim and the engine does not`);
    }
  }
  return found;
}
