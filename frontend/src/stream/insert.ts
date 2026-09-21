/**
 * **Add a claim** — the one thing a reader can do to a map that needs the model.
 *
 * *"…but this also happens"*. It asks for **one** intervention: a claim and its
 * arrows, already drafted and already checked by the same rules every proposal
 * passes. It is not a generation — no stream and no reserved rectangle — but it
 * **is** several model calls, so it carries a receipt of its own, drawn by the
 * same strip a generation's receipt is drawn by.
 *
 * **The field is `position`, not `at`.** `at` already means a place in a
 * transcript on a stream event and a date on an edit, and a word that means three
 * things is a word that means none.
 *
 * **With no key, one sentence works and every other is declined in plain words.**
 * Each recording carries the one scripted intervention its card offers, matched
 * on the exact words after trimming surrounding spaces — the same rule that picks
 * which recording plays. There is no fuzzy matching and there will not be: a
 * similarity score doing the model's job badly would be a piece of state nobody
 * could trace to an input, a rule or a source. Anything else comes back declined,
 * and the control says so rather than disappearing.
 *
 * The other five things a reader can do — *Suppose this is true*, *This
 * happened*, *Change this push*, *Split this claim*, *My own number* — call no
 * model at all. They are arithmetic in the engine's pure core, which is why a
 * reader with no key still gets the whole multiverse at full fidelity.
 */

import type { components } from "../api/schema";
import type { Receipt } from "./events";
import { INSERT_ADDRESS } from "./generate";

/** One claim and its arrows, arriving as a single edit. */
export type DraftedClaim = components["schemas"]["Insert"];

/**
 * What one drafted claim cost.
 *
 * **An insert is several model calls, not one**, so it carries a receipt of its
 * own — the same nine readings a generation's receipt carries, and drawn by the
 * same strip, because a cost shown two ways is two costs. It is what closes the
 * chapter's third open question: the route answers with a receipt beside the
 * intervention rather than the session growing a running total, which would be
 * the first number in this product added up by something other than the engine.
 */
export type InsertReceipt = Receipt;

/** What it takes to ask for one. */
export interface DraftRequest {
  /** The map the new claim is going onto. */
  readonly base_id: string;
  /** What the reader typed. */
  readonly claim_in_words: string;
  /** Where in the branch the new edit goes. */
  readonly position?: number;
}

/** How the ask turned out. Three answers, and a refusal is one of them. */
export type Drafted =
  | {
      readonly state: "drafted";
      readonly insert: DraftedClaim;
      /** What drafting it cost, when the route says. Null on a route that does not yet. */
      readonly receipt: InsertReceipt | null;
    }
  /** The rules would not have it, with every reason at once, in their own words. */
  | { readonly state: "refused"; readonly reasons: readonly string[] }
  /** It could not be drafted at all. One plain sentence, the server's own. */
  | { readonly state: "declined"; readonly reason: string };

/**
 * Ask for one claim to be drafted and checked.
 *
 * @param request The map, the sentence and where the edit goes.
 * @param ask The function that makes the request. The browser's own by default.
 */
export async function draftAClaim(
  request: DraftRequest,
  ask: typeof globalThis.fetch = globalThis.fetch,
): Promise<Drafted> {
  let answer: Response;
  try {
    answer = await ask(INSERT_ADDRESS, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ position: 0, ...request }),
    });
  } catch {
    return {
      state: "declined",
      reason: `Could not reach the server at ${INSERT_ADDRESS}. It may not be running.`,
    };
  }

  const body = (await answer.json().catch(() => null)) as unknown;
  if (answer.ok) {
    // **Two shapes, one reading.** The route is moving to answering with the
    // drafted claim *and* what drafting it cost — an insert is several model
    // calls, and a cost nobody is shown is a cost nobody can check. Until every
    // copy answers that way, a body that is the claim on its own is still read,
    // and the cost is then absent rather than invented.
    const both = body as { insert?: DraftedClaim; receipt?: InsertReceipt } | null;
    if (both?.insert !== undefined) {
      return { state: "drafted", insert: both.insert, receipt: both.receipt ?? null };
    }
    return { state: "drafted", insert: body as DraftedClaim, receipt: null };
  }

  const detail = (body as { detail?: unknown } | null)?.detail;
  // Every reason at once, in the rules' own sentences. A person fixing one fault
  // per attempt learns only that the tool is hostile.
  if (Array.isArray(detail)) {
    return {
      state: "refused",
      reasons: detail.map((one) =>
        typeof (one as { message?: unknown }).message === "string"
          ? String((one as { message: string }).message)
          : "The server would not carry this out and did not say why.",
      ),
    };
  }
  // The server's own plain sentence, printed word for word. With no key that is
  // *"drafting a new claim needs a model key."* and nothing else.
  return {
    state: "declined",
    reason:
      typeof detail === "string"
        ? detail
        : `The request to ${INSERT_ADDRESS} came back with no reading. The reply was numbered ${answer.status}.`,
  };
}
