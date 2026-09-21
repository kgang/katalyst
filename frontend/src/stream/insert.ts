/**
 * **Add a claim** — the one thing a reader can do to a map that needs the model.
 *
 * *"…but this also happens"*. It asks for **one** intervention: a claim and its
 * arrows, already drafted and already checked by the same rules every proposal
 * passes. It is not a generation — no stream and no reserved rectangle — but it
 * **is** several model calls, so it carries a receipt of its own, drawn by the
 * same strip a generation's receipt is drawn by.
 *
 * **A drafted edit goes at the end of the branch, and nothing says where.** A
 * branch is append-only everywhere else in this product, so the end is the only
 * place the browser ever puts one — and the field that let it say otherwise was
 * read by nothing, while a reader who sent one got a 200 for an edit the world
 * route then refused (Kent, 2026-09-21).
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
import type { TranscriptLine } from "./transcript";

/** One claim and its arrows, arriving as a single edit. */
export type DraftedClaim = components["schemas"]["Insert"];

/**
 * What one drafted claim cost.
 *
 * **An insert is several model calls, not one** — the starting-claim shape
 * drafts the reader's sentence, and then the ordinary walk proposes its arrows,
 * one call each — so it spends real money, and NFR-6 has no exception for money
 * spent outside a stream. It carries a receipt of its own: the same nine
 * readings a generation's receipt carries, drawn by the same strip, because a
 * cost shown two ways is two costs.
 *
 * **This is the chapter's third open question, settled 2026-09-20**
 * (`spec/generation/streaming.md`): the route answers `DraftedInsert` — the edit
 * and its own receipt — rather than the session growing a running total, which
 * would have been the first number in this product added up by something other
 * than the engine, and would have vanished on a page reload.
 */
export type InsertReceipt = Receipt;

/** What it takes to ask for one. */
export interface DraftRequest {
  /** The map the new claim is going onto, by the map's own identifier. */
  readonly base_id: string;
  /**
   * The branch built so far, sent whole.
   *
   * **The claim is drafted and validated against the map with the branch folded
   * in**, which is the map the reader is looking at. Leaving it out asks the
   * rules about a map nobody has in front of them: a claim that contradicts an
   * edit made two minutes ago comes back accepted, and then breaks the branch it
   * is added to. Left out on a map with no branch open, which is every
   * generated map today.
   */
  readonly branch?: components["schemas"]["Branch"];
  /** What the reader typed. */
  readonly claim_in_words: string;
}

/** How the ask turned out. Three answers, and a refusal is one of them. */
export type Drafted =
  | {
      readonly state: "drafted";
      readonly insert: DraftedClaim;
      /** What drafting it cost, in the shape the stream's receipt event carries. */
      readonly receipt: InsertReceipt | null;
      /**
       * Every call it took, in order — the insert's own working.
       *
       * **It arrives in the answer because there is nowhere else it could be.**
       * An insert is one request and one answer, not a generation: nothing is
       * remembered on the server, so there is no identifier to ask about it by
       * and no route to ask at. Filing it in the generation store instead made
       * every insert unfindable and evicted the map it was being added to
       * (Kent, 2026-09-21).
       */
      readonly working: readonly TranscriptLine[];
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
      // `{base_id, branch, claim_in_words}` — the route's three fields, and the
      // branch is one of them. A claim drafted against the stored map when the
      // reader is looking at the map plus two edits is a claim checked against a
      // map nobody has in front of them.
      //
      // **There is no `position`, and the browser never sent a meaningful one.**
      // A drafted edit goes at the end of the branch, which is the only place
      // this product ever puts one — a branch is append-only everywhere else in
      // it. The field is gone from the route (Kent, 2026-09-21), and while it
      // was there a reader who sent something other than the end got a 200 for
      // an edit the world route then refused.
      body: JSON.stringify(request),
    });
  } catch {
    return {
      state: "declined",
      reason: `Could not reach the server at ${INSERT_ADDRESS}. It may not be running.`,
    };
  }

  const body = (await answer.json().catch(() => null)) as unknown;
  if (answer.ok) {
    // **The route answers a `DraftedInsert`: the edit, and its own receipt.**
    // An insert is several model calls, so it spends real money, and a cost
    // nobody is shown is a cost nobody can check.
    const both = body as {
      insert?: DraftedClaim;
      receipt?: InsertReceipt;
      working?: readonly TranscriptLine[];
    } | null;
    if (both?.insert !== undefined) {
      return {
        state: "drafted",
        insert: both.insert,
        receipt: both.receipt ?? null,
        working: both.working ?? [],
      };
    }
    // A 200 that is not that shape is not a drafted claim, whatever else it is.
    // It used to be read as one — the body handed straight through as the edit —
    // which turned a body that was `null`, or an older route's bare `Insert`,
    // into a screen that threw while drawing and took the whole page with it.
    // Saying so is a worse answer for nobody and a readable one for everybody.
    return {
      state: "declined",
      reason:
        `The request to ${INSERT_ADDRESS} came back with something this build cannot read as a ` +
        `drafted claim. Nothing has been added to the map.`,
    };
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
