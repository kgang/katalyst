/**
 * Every proposal the map's own rules turned down, on screen, in the validator's
 * own words.
 *
 * **A rejected proposal is an event, not an error.** Nothing is retried quietly
 * out of sight and nothing is swallowed. The engine may try again — up to three
 * fresh proposals for one open claim, none of them told why the last was refused
 * — and every one of those attempts that was refused is here.
 *
 * This strip is half the product. It is the moment a reader can see that our own
 * code, not the model, decides what the map is allowed to contain — and each row
 * says the one thing that would have made the proposal legal, which is the
 * difference between a rejection and an insult.
 *
 * **Two rules it obeys, both inherited rather than invented.** The sentence is
 * the validator's, as it wrote it: `spec/graph/validity.md` owns that copy, and
 * its rules are that a message names the claim by its words, never by its
 * identifier, and says what is missing rather than that something failed. This
 * file composes no sentence about a refusal and never draws a rule's code. And a
 * refused claim is never drawn as a tile and never given an identifier — its
 * words are quoted and nothing else is done with them, because the moment it has
 * a box it needs a name, and then the model would have caused an identifier to
 * exist.
 */

import type { Refusal } from "../stream/growth";
import "./refusalStrip.css";

/** What the strip needs to draw itself. */
export interface RefusalStripProps {
  /** Every refusal, in the order they happened. Newest last. */
  readonly refusals: readonly Refusal[];
  /** Open the working of the run at this refusal's own line. */
  readonly onOpen?: (at: number) => void;
  /** Which line the panel beside the map is open at, when it is open at one. */
  readonly openAt?: number | null;
  /**
   * True once the run is over.
   *
   * A run that has refused nothing **so far** is not a run that refused nothing:
   * while it is still going, the strip has nothing to say and takes no room. The
   * moment it is over, "nothing was refused" is a finding, and a finding is said
   * out loud rather than left as an empty space a reader has to interpret.
   */
  readonly finished?: boolean;
}

/** One row per refusal. Nothing is trimmed, merged or summarised away. */
export function RefusalStrip({ refusals, onOpen, openAt, finished }: RefusalStripProps) {
  if (refusals.length === 0) {
    // Nothing yet, and the run is still going: there is nothing to say.
    if (finished !== true) {
      return null;
    }
    // Nothing at all, and the run is over. **Kent decided a recording need not
    // contain a refusal**, so this is an ordinary outcome rather than a missing
    // one — and it is said, because an empty space where the refusals go reads
    // as a strip that failed to draw.
    return (
      <section className="refusal-strip" aria-label="Proposals the rules refused">
        <h3 className="refusal-strip__heading">Refused by the rules</h3>
        <p className="refusal-strip__line">The rules refused nothing in this run.</p>
      </section>
    );
  }
  return (
    <section className="refusal-strip" aria-label="Proposals the rules refused">
      <h3 className="refusal-strip__heading">Refused by the rules</h3>
      <p className="refusal-strip__line">
        {refusals.length === 1
          ? "One proposal was turned down on the way past. It is here in full, in the words the " +
            "rule itself wrote."
          : `${refusals.length} proposals were turned down on the way past. Every one of them is ` +
            `here in full, in the words the rules themselves wrote.`}
      </p>
      <ol className="refusal-strip__rows">
        {refusals.map((refusal) => (
          <li className="refusal-strip__row" key={`${refusal.at}-${refusal.claimInWords}`}>
            <button
              className="refusal-strip__open"
              type="button"
              data-open={openAt === refusal.at ? "yes" : "no"}
              onClick={() => onOpen?.(refusal.at)}
            >
              {/* The engine's own position in the working, printed so the row can
                  be found again. It is a place in a list, not a time. */}
              <span className="refusal-strip__at">{`proposal ${refusal.at}`}</span>
              <span className="refusal-strip__verdict">refused</span>
              {/* What the model wrote, quoted and given nothing else. */}
              <q className="refusal-strip__words">{refusal.claimInWords}</q>
            </button>
            {/* One line per rule broken. A proposal that broke three rules and
                showed one is a refusal the reader has half seen. */}
            <ul className="refusal-strip__reasons">
              {refusal.reasons.map((reason) => (
                <li className="refusal-strip__reason" key={reason}>
                  {reason}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}
