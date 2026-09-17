/**
 * The first screen: what you can start from, and the two ways in.
 *
 * No illustration and no empty box staring back. The four examples from the
 * brief are on the page as cards, the two doors are named and explained in a
 * line each, and one card opens a map right now.
 *
 * **The three cards that do not open anything say so.** Turning a sentence you
 * typed into a map needs the model, and that half is not built yet — so those
 * three carry the words *not yet live* and the reason underneath, read from the
 * server's own answer about whether it is ready. A card that quietly did
 * nothing when clicked would be the worse choice by a distance: the reader
 * would think the tool was broken rather than unfinished.
 */

import type { FixtureSummary } from "../api/client";
import "./launchpad.css";

/** One of the two ways into the tool. */
interface Door {
  readonly name: string;
  readonly line: string;
}

/**
 * The two doors, from the requirements: start from an event and follow it out,
 * or name where you think it ends and ask whether the chain really gets there.
 */
const DOORS: readonly Door[] = [
  {
    name: "Explore",
    line: "Start from an event and see what it would cause, out to the things you could trade.",
  },
  {
    name: "Verify",
    line: "Name where you think it ends, and see whether a chain really gets there — or that none does.",
  },
];

/**
 * The three examples from the brief that need the model.
 *
 * They are what a reader would type, written out so the shape of the input is
 * obvious before anyone has typed anything.
 */
const WAITING_EXAMPLES: readonly string[] = [
  "Republicans win the House but Democrats take the Senate during the midterms.",
  "Models more capable than Fable get export restricted by the United States.",
  "Photonic chips get adopted faster than expected.",
];

/** What the launchpad needs to draw itself. */
export interface LaunchpadProps {
  /**
   * The stored examples the server ships with, or null while the answer is
   * still on its way.
   */
  readonly examples: readonly FixtureSummary[] | null;
  /** Why the list could not be read, if it could not be. */
  readonly failure: string | null;
  /**
   * Why the other three cards are not live, in one sentence, worked out from
   * what the server said about itself.
   */
  readonly notLiveReason: string;
  /** Open a stored example's map. */
  readonly onOpen: (id: string) => void;
}

/** The first screen. */
export function Launchpad({ examples, failure, notLiveReason, onOpen }: LaunchpadProps) {
  return (
    <div className="launchpad">
      <section aria-labelledby="doors-heading">
        <h2 className="section-heading" id="doors-heading">
          Two ways in
        </h2>
        <ul className="doors">
          {DOORS.map((door) => (
            <li className="door" key={door.name}>
              <span className="door__name">{door.name}</span>
              <span className="door__line">{door.line}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="examples-heading">
        <h2 className="section-heading" id="examples-heading">
          Start from one of these
        </h2>
        <ul className="examples">
          {examples === null ? (
            <li className="example example--waiting">
              <span className="example__claim">
                {failure ?? "Asking the server which examples it ships with."}
              </span>
              {failure === null ? <span className="placeholder" aria-hidden="true" /> : null}
            </li>
          ) : (
            examples.map((example) => (
              <li key={example.id}>
                <button
                  className="example example--live"
                  type="button"
                  onClick={() => onOpen(example.id)}
                >
                  <span className="example__claim">{example.title}</span>
                  <span className="example__line">{example.one_line}</span>
                  <span className="example__action">Open the map</span>
                </button>
              </li>
            ))
          )}

          {WAITING_EXAMPLES.map((claim) => (
            <li className="example example--waiting" key={claim}>
              <span className="example__claim">{claim}</span>
              <span className="example__line">
                Would be turned into a map of what it causes, ending in trades.
              </span>
              <span className="example__action example__action--waiting">
                <span className="example__badge">not yet live</span>
                {notLiveReason}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
