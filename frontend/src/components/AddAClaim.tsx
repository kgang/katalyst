/**
 * **Add a claim** — *"…but this also happens"*.
 *
 * The one thing a reader can do to a map that needs the model. It asks for one
 * intervention: a claim and its arrows, already drafted and already checked by
 * the same rules every proposal passes. It is not a generation — no stream, no
 * reserved rectangle, no receipt — and what it cost appears nowhere, which is an
 * open question the chapter records rather than a thing this control should
 * guess at.
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
import type { Drafted } from "../stream/insert";
import { draftAClaim } from "../stream/insert";
import "./addAClaim.css";

/** What the control needs to draw itself. */
export interface AddAClaimProps {
  /** The map the new claim would go onto. */
  readonly baseId: string;
  /** What to do with a claim that was drafted and passed the rules. */
  readonly onDrafted?: (drafted: Drafted) => void;
  /** How the request is made. The real one by default; a test hands in its own. */
  readonly draft?: typeof draftAClaim;
}

/** *"…but this also happens"*. */
export function AddAClaim({ baseId, onDrafted, draft = draftAClaim }: AddAClaimProps) {
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
          draft({ base_id: baseId, claim_in_words: words.trim() }).then((drafted) => {
            setAsking(false);
            setAnswer(drafted);
            onDrafted?.(drafted);
          });
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
        <p className="add-a-claim__line" data-answer="drafted">
          {`Drafted and checked: "${answer.insert.proposition.claim}". It is on your branch, like every other edit.`}
        </p>
      )}
    </section>
  );
}
