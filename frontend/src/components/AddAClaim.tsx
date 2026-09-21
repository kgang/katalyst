/**
 * **Add a claim** — *"…but this also happens"*.
 *
 * The one thing a reader can do to a map that needs the model. It asks for one
 * intervention: a claim and its arrows, already drafted and already checked by
 * the same rules every proposal passes. It is not a generation — no stream and
 * no reserved rectangle — but it **is** several model calls, so it carries a
 * receipt of its own, drawn by the same strip a generation's receipt is drawn
 * by (settled 2026-09-20, `spec/generation/streaming.md`).
 *
 * **It is never silently inert.** When it cannot draft — no key and no recorded
 * intervention for what was typed — the server says so in one plain sentence and
 * this control prints that sentence rather than disappearing. A control that
 * vanishes teaches a reader that they imagined it; a control that says why teaches
 * them what this copy can do.
 *
 * The other five things a reader can do to a map call no model at all. They are
 * arithmetic in the engine's pure core, which is why a reader with no key still
 * gets the whole multiverse at full fidelity.
 */

import { useId, useState } from "react";
import type { components } from "../api/schema";
import type { Drafted, DraftedClaim } from "../stream/insert";
import { draftAClaim } from "../stream/insert";
import { asOneSentence } from "../world/failures";
import { ReceiptStrip } from "./ReceiptStrip";
import "./addAClaim.css";

/** What the control needs to draw itself. */
export interface AddAClaimProps {
  /** The map the new claim would go onto. */
  readonly baseId: string;
  /**
   * The branch built so far, sent whole, so that the claim is drafted and
   * checked against the map the reader is actually looking at. Left out when no
   * branch is open.
   */
  readonly branch?: components["schemas"]["Branch"];
  /** Where in the branch the new edit goes: the number of edits already in it. */
  readonly position?: number;
  /** What to do with a claim that was drafted and passed the rules. */
  readonly onDrafted?: (drafted: DraftedClaim) => void;
  /**
   * One line about what happens to a claim once it is drafted, in the words of
   * the screen this control is on. Beside a stored map it goes onto the branch;
   * beside a map that has just been generated there is no branch panel yet.
   */
  readonly andThen: string;
  /** How the request is made. The real one by default; a test hands in its own. */
  readonly draft?: typeof draftAClaim;
}

/** *"…but this also happens"*. */
export function AddAClaim({
  baseId,
  branch,
  position = 0,
  onDrafted,
  andThen,
  draft = draftAClaim,
}: AddAClaimProps) {
  const fieldId = useId();
  const [words, setWords] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<Drafted | null>(null);

  return (
    <section className="add-a-claim" aria-label="Add a claim to this map">
      <h3 className="add-a-claim__heading">Add a claim</h3>
      <form
        className="add-a-claim__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (asking || words.trim() === "") {
            return;
          }
          setAsking(true);
          setAnswer(null);
          draft({
            base_id: baseId,
            ...(branch === undefined ? {} : { branch }),
            claim_in_words: words.trim(),
            position,
          }).then(
            (drafted) => {
              setAsking(false);
              setAnswer(drafted);
              if (drafted.state === "drafted") {
                onDrafted?.(drafted.insert);
              }
            },
            // **A rejection puts the control back.** Without this the button
            // stays disabled reading *Drafting the claim* for as long as the tab
            // is open, which is a control that is silently inert in the exact
            // way INV-workbench.74 forbids — and the reader has no way of
            // knowing whether their claim is still being worked on.
            (failure: unknown) => {
              setAsking(false);
              setAnswer({ state: "declined", reason: asOneSentence(failure) });
            },
          );
        }}
      >
        <label className="add-a-claim__label" htmlFor={fieldId}>
          …but this also happens
        </label>
        <input
          className="add-a-claim__text"
          id={fieldId}
          type="text"
          autoComplete="off"
          placeholder="…but Iran is struck the next day"
          value={words}
          onChange={(event) => setWords(event.target.value)}
        />
        <button className="add-a-claim__ask" type="submit" disabled={asking || words.trim() === ""}>
          {asking ? "Drafting the claim" : "Draft this claim"}
        </button>
      </form>

      {asking ? (
        <p className="add-a-claim__line">
          {/* Not a spinner: the shape of the thing being waited for, said in
              words. One claim is being drafted and checked against this map. */}
          One claim is being drafted and checked against this map, by the same rules every proposal
          passes.
        </p>
      ) : null}

      {answer === null ? null : answer.state === "declined" ? (
        // The server's own sentence, word for word. With no key that is
        // "drafting a new claim needs a model key." and nothing else.
        <p className="add-a-claim__line" data-answer="declined">
          {answer.reason}
        </p>
      ) : answer.state === "refused" ? (
        <div className="add-a-claim__line" data-answer="refused">
          <p className="add-a-claim__refused">
            The map&rsquo;s own rules would not take this claim, and gave every reason at once.
          </p>
          <ul className="add-a-claim__reasons">
            {answer.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="add-a-claim__line" data-answer="drafted">
          <p className="add-a-claim__drafted">
            {`Drafted and checked: "${answer.insert.proposition.claim}" ${andThen}`}
          </p>
          {/* What drafting it cost, in the same nine readings and the same strip
              a generation's receipt is printed in. An insert is several model
              calls — one to draft the claim, then one per arrow — so it spends
              real money, and the person who pressed the button is the person who
              should see the bill. Absent only on a copy of the route older than
              the receipt, and then nothing is invented in its place. */}
          {answer.receipt === null ? null : (
            <ReceiptStrip receipt={answer.receipt} heading="What drafting it cost" />
          )}
        </div>
      )}
    </section>
  );
}
