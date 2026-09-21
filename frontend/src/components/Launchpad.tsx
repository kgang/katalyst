/**
 * The first screen: what you can start from, and the two ways in.
 *
 * No illustration and no empty box staring back. The two doors are named and
 * explained in a line each, the stored example opens a map that is already drawn,
 * and the four sentences from the brief each build one in front of you.
 *
 * **A card has three states and no others.** It runs live, it runs from a
 * recording, or it reads *not yet live* — and that last one now means one thing
 * only: **no model key and no recording**, an example nobody has recorded yet,
 * which is an honest state rather than the catch-all it used to be.
 *
 * **With no key, the four run from recordings through the same route, the same
 * eight events and the same canvas.** The sentence that says so is record 0012's,
 * word for word, and the day in it is read from the server's own readiness answer
 * — never from a file name, never from a build date, never from the browser's own
 * clock. Where the four were not all recorded on one day, the shared sentence
 * names the **oldest** day in the set and each card carries its own, so the
 * sentence is never more current than the oldest thing it describes.
 *
 * **This screen reads what can be replayed and whether a key is configured, and
 * ignores whether the server called itself ready.** A program with no key but
 * four recordings can do everything a reviewer came to see, and a card greyed out
 * because the whole server called itself not ready would be the most misleading
 * screen in the product.
 */

import type { FixtureSummary, Readiness } from "../api/client";
import { countInWords } from "../world/naming";
import type { Asked } from "./InputBar";
import { InputBar } from "./InputBar";
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

/** One of the four sentences from the brief, and which recording answers to it. */
export interface StartingSentence {
  /**
   * Which stored example this is.
   *
   * It is the name the readiness answer uses for a recording, so that a card can
   * say whether there is one to play. It is **not** a file name and it never
   * reaches a request: what a card sends is its sentence, exactly as a reader
   * would type it, which is what makes the replayed path and the live path send
   * byte-identical requests.
   */
  readonly example: string;
  /** The sentence, as a person would actually type it. */
  readonly sentence: string;
}

/** The four examples from the brief, in the order the brief lists them. */
export const STARTING_SENTENCES: readonly StartingSentence[] = [
  { example: "hormuz", sentence: "The Strait of Hormuz is going to open next week." },
  {
    example: "midterms",
    sentence: "Republicans win the House but Democrats take the Senate during the midterms.",
  },
  {
    example: "export-controls",
    sentence: "Models more capable than Fable get export restricted by the United States.",
  },
  { example: "photonics", sentence: "Photonic chips get adopted faster than expected." },
];

/**
 * Record 0012's sentence, word for word, with the day the readiness answer gave.
 *
 * **It is printed only when it is true**: when all four of the sentences below
 * can be played and all four were recorded on the same day. Anything else and it
 * would be a screen claiming something a reader can see is false — three cards
 * reading *not yet live* under a line saying these four run from recordings — and
 * the one screen this product cannot afford to be caught out on is the one that
 * exists to say what this copy can honestly do.
 *
 * @param day The day the recordings were made.
 */
export function keylessSentence(day: string): string {
  return `No model key configured — these four run from recordings made on ${day}.`;
}

/**
 * What this copy can play, in one or two sentences, and always true.
 *
 * Four shapes, and the first is record 0012's own words. The others say the same
 * kind of thing in the same voice: how many of the four can be played, how many
 * cannot, and the day — the **oldest** day, where there is more than one, so the
 * sentence is never more current than the oldest thing it describes.
 *
 * @param days The day each playable example was recorded on, in any order.
 * @param outOf How many sentences the screen offers altogether.
 */
export function whatThisCopyCanPlay(days: readonly string[], outOf: number): string | null {
  if (days.length === 0) {
    return null;
  }
  const sorted = [...days].sort();
  const oldest = sorted[0] as string;
  const allOfThem = days.length === outOf;
  const oneDay = sorted[sorted.length - 1] === oldest;

  if (allOfThem && oneDay) {
    return keylessSentence(oldest);
  }
  if (allOfThem) {
    return (
      `No model key configured — these ${countInWords(outOf)} run from recordings, the oldest ` +
      `made on ${oldest}.`
    );
  }
  const rest = outOf - days.length;
  const canPlay = days.length === 1 ? "runs" : "run";
  const cannot = rest === 1 ? "has" : "have";
  const theRest = rest === 1 ? "the other one" : `the other ${countInWords(rest)}`;
  const when = oneDay ? `made on ${oldest}` : `the oldest made on ${oldest}`;
  return (
    `No model key configured — ${countInWords(days.length)} of these ${countInWords(outOf)} ` +
    `${canPlay} from recordings, ${when}; ${theRest} ${cannot} nothing recorded yet.`
  );
}

/** What each card can do, which is one of exactly three things. */
type CardState = "live" | "replay" | "not-yet";

/** What the launchpad needs to draw itself. */
export interface LaunchpadProps {
  /**
   * The stored examples the server ships with, or null while the answer is still
   * on its way.
   */
  readonly examples: readonly FixtureSummary[] | null;
  /** Why the list could not be read, if it could not be. */
  readonly failure: string | null;
  /**
   * What the server said about itself: whether a key is configured, and what it
   * can play back. Null while that answer is still on its way.
   */
  readonly readiness: Readiness | null;
  /** Open a stored example's map, already drawn. */
  readonly onOpen: (id: string) => void;
  /** Build a map from a sentence. */
  readonly onBuild: (asked: Asked) => void;
}

/** The first screen. */
export function Launchpad({ examples, failure, readiness, onOpen, onBuild }: LaunchpadProps) {
  // The two facts this screen reads, and the one it deliberately does not.
  const hasKey = readiness?.model_key_present === true;
  const recorded = new Map(
    (readiness?.replayable ?? []).map((one) => [one.example, one.recording_date]),
  );
  // The day each of the four sentences was recorded on, for the ones that were.
  // Read off the cards rather than off the whole answer, so a recording of
  // something this screen does not offer cannot make its sentence wrong.
  const playable = STARTING_SENTENCES.map((one) => recorded.get(one.example)).filter(
    (day): day is string => day !== undefined,
  );
  const canPlay = whatThisCopyCanPlay(playable, STARTING_SENTENCES.length);
  const stateOf = (example: string): CardState =>
    hasKey ? "live" : recorded.has(example) ? "replay" : "not-yet";

  return (
    <div className="launchpad">
      <section className="launchpad__doors" aria-labelledby="doors-heading">
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

      <section className="launchpad__drawn" aria-labelledby="examples-heading">
        <h2 className="section-heading" id="examples-heading">
          A map that is already drawn
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
        </ul>
      </section>

      <section className="launchpad__build" aria-labelledby="build-heading">
        <h2 className="section-heading" id="build-heading">
          Or watch one build itself
        </h2>
        <ul className="examples">
          {STARTING_SENTENCES.map((one) => {
            const state = stateOf(one.example);
            const day = recorded.get(one.example);
            return (
              <li key={one.example}>
                {state === "not-yet" ? (
                  <div className="example example--waiting" data-state="not-yet">
                    <span className="example__claim">{one.sentence}</span>
                    <span className="example__line">
                      Would be turned into a map of what it causes, ending in trades.
                    </span>
                    <span className="example__action example__action--waiting">
                      <span className="example__badge">not yet live</span>
                      no model key, and nothing recorded for this one
                    </span>
                  </div>
                ) : (
                  <button
                    className="example example--live"
                    type="button"
                    data-state={state}
                    onClick={() =>
                      onBuild({ hypothesis: one.sentence, target: null, belief: null })
                    }
                  >
                    <span className="example__claim">{one.sentence}</span>
                    <span className="example__line">
                      {state === "replay"
                        ? "Plays the recording of this run back, claim by claim, through the same route and the same canvas."
                        : "Builds a map of what it would cause, claim by claim, ending in trades."}
                    </span>
                    {/* Not **Build the map**: that is the one button on the
                        input bar, and a word that names two controls names
                        neither. A card is a sentence somebody already typed. */}
                    <span className="example__action">
                      {state === "replay" ? (
                        <>
                          <span className="example__badge">replay</span>
                          {day === undefined ? "Watch it build" : `recorded ${day}`}
                        </>
                      ) : (
                        "Watch it build"
                      )}
                    </span>
                  </button>
                )}
              </li>
            );
          })}
        </ul>

        {/* Record 0012's sentence, word for word, under the four cards — and
            again under the field below, which is disabled with it. */}
        {canPlay === null || hasKey ? null : <p className="launchpad__keyless">{canPlay}</p>}
        {/* What *not yet live* means, said once in full rather than three times
            over: each card carries the short form, and this is the whole of it.
            It is the honest state now, not a catch-all — a key would run it, and
            a recording would play it, and this copy has neither. */}
        {hasKey || STARTING_SENTENCES.every((one) => recorded.has(one.example)) ? null : (
          <p className="launchpad__keyless launchpad__keyless--quiet">
            A card reads <b>not yet live</b> when this copy has no model key and nobody has recorded
            that example, so there is nothing it could honestly show you.
          </p>
        )}
        {/* **A recording that would not play is named, in the server's own
            sentence.** A reviewer who put a file in the recordings folder and
            then counts three cards where they expected four is owed the reason
            rather than left to wonder whether they put it in the wrong place —
            and a recording is a committed file that outlives the code that
            wrote it, so meeting one this engine cannot read is ordinary. It is
            quiet, under the cards, because it is about the copy rather than
            about the maps: the cards that do play are unaffected, which is the
            other half of the same rule. */}
        {(readiness?.unreadable ?? []).map((sentence) => (
          <p className="launchpad__keyless launchpad__keyless--quiet" key={sentence}>
            {sentence}
          </p>
        ))}
      </section>

      {/* A sentence of the reader's own. It is a section of its own rather than
          a footnote under the four cards, because typing your own event is the
          way in this product is for and the four are the shortcut. */}
      <section className="launchpad__yours" aria-labelledby="yours-heading">
        <h2 className="section-heading" id="yours-heading">
          Or start from a sentence of your own
        </h2>
        <InputBar
          disabledBecause={
            hasKey
              ? null
              : canPlay === null
                ? "This copy has no model key and no recordings, so a sentence of your own cannot be turned into a map."
                : `${canPlay} A sentence of your own needs the model, and there is no recording of one.`
          }
          onBuild={onBuild}
        />
      </section>
    </div>
  );
}
