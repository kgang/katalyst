/**
 * The first screen: what you can start from, and the two ways in.
 *
 * No illustration and no empty box staring back. The two doors are named and
 * explained in a line each, the stored example opens a map that is already drawn,
 * and the four sentences from the brief each build one in front of you.
 *
 * **A card is only ever something you can take up.** It runs live or it runs
 * from a recording. A sentence this copy can do neither with gets no card at
 * all: it is named, with the others in its position, in the one line under the
 * cards that says what this copy can play. Three headstones beside one door,
 * taking the whole of the right-hand column, is what a reviewer with thirty
 * minutes met before — and *not yet live* on a row you cannot press is a
 * control a reader counted and cannot use.
 *
 * **Six states, and each says a different true thing.** They are listed here
 * because the two that look alike are the ones this screen got wrong twice: an
 * answer that has not arrived and an answer that never will.
 *
 * | What is true | What the screen shows |
 * |---|---|
 * | The readiness ask is in flight | Every sentence, each reading *Asking the server whether this one can be run here: whether a model key is configured, and whether there is a recording of it to play.* |
 * | The readiness ask did not come back | Every sentence, each reading *The ask did not come back, so nothing is known about whether this one can be run here*, and the server's own sentence once, under them |
 * | A model key is configured | Every sentence, as a card that runs live |
 * | No key, and this one has a recording | A card that plays it, badged *replay*, with the day it was made |
 * | No key, and this one has no recording | **No card.** The line under the cards names it with the others in its position |
 * | No key, and nothing at all is recorded | **No cards.** One line saying so, pointing at the map that is already drawn, which needs neither |
 *
 * The last three are one rule and not three: a card for everything this copy
 * can do. The first two are two rules on purpose, because a question in flight
 * invites waiting and an ask that got no reply invites asking again.
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
  /**
   * What this example is about, in two or three words.
   *
   * **It is how a sentence with no card of its own is still named.** A line
   * reading *the other three have nothing recorded yet* points at three
   * sentences that are no longer on the screen, which leaves a reader counting
   * what is missing rather than being told. The short name is authored here,
   * beside the sentence it belongs to, and it is not the recording's short name
   * (`hormuz`, `export-controls`): those are identifiers that name a file and a
   * card and an eval case, and an identifier is never words on the screen.
   */
  readonly about: string;
}

/** The four examples from the brief, in the order the brief lists them. */
export const STARTING_SENTENCES: readonly StartingSentence[] = [
  {
    example: "hormuz",
    sentence: "The Strait of Hormuz is going to open next week.",
    about: "the strait",
  },
  {
    example: "midterms",
    sentence: "Republicans win the House but Democrats take the Senate during the midterms.",
    about: "the midterms",
  },
  {
    example: "export-controls",
    sentence: "Models more capable than Fable get export restricted by the United States.",
    about: "export controls",
  },
  {
    example: "photonics",
    sentence: "Photonic chips get adopted faster than expected.",
    about: "photonic chips",
  },
];

/**
 * A few things, listed the way a sentence lists them: *a, b and c*.
 *
 * @param things What to list, in the order they should be read.
 */
export function asAList(things: readonly string[]): string {
  if (things.length <= 1) {
    return things[0] ?? "";
  }
  return `${things.slice(0, -1).join(", ")} and ${things[things.length - 1]}`;
}

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
 * **The ones that cannot be played are named**, because they have no card to be
 * seen on: a line reading *the other three have nothing recorded yet* points at
 * three sentences that are no longer on the screen, and a reader counting what
 * is missing is a reader being asked to do the screen's work.
 *
 * @param days The day each playable example was recorded on, in any order.
 * @param missing What each example with no recording is about, in a few words,
 *   in the order the screen offers them.
 */
export function whatThisCopyCanPlay(
  days: readonly string[],
  missing: readonly string[],
): string | null {
  if (days.length === 0) {
    return null;
  }
  const outOf = days.length + missing.length;
  const sorted = [...days].sort();
  const oldest = sorted[0] as string;
  const oneDay = sorted[sorted.length - 1] === oldest;

  if (missing.length === 0 && oneDay) {
    return keylessSentence(oldest);
  }
  if (missing.length === 0) {
    return (
      `No model key configured — these ${countInWords(outOf)} run from recordings, the oldest ` +
      `made on ${oldest}.`
    );
  }
  const canPlay = days.length === 1 ? "runs" : "run";
  const cannot = missing.length === 1 ? "has" : "have";
  const when = oneDay ? `made on ${oldest}` : `the oldest made on ${oldest}`;
  return (
    `No model key configured — ${countInWords(days.length)} of these ${countInWords(outOf)} ` +
    `${canPlay} from recordings, ${when}; ${asAList(missing)} ${cannot} nothing recorded yet.`
  );
}

/**
 * What this copy can do with one of the brief's sentences.
 *
 * **Five, and two of them never draw a card.** An example this copy can neither
 * run nor play is not a card a reader can take up, and three of those side by
 * side under a heading offering to build you a map is a graveyard with a door in
 * it. What is left of them is one quiet line under the cards that do work,
 * naming which they are — which is the same sentence that was already printed
 * there, in `whatThisCopyCanPlay`.
 *
 * **`asking` and `no-answer` are the two states before there is anything to
 * say**, and they are two states rather than one because they invite different
 * things. *Asking* is a question in flight and it will answer; *the ask did not
 * come back* is the server there and one attempt that got no reply, which stops
 * being true the moment somebody asks again. Collapsing them was the defect this
 * type exists to prevent: with them folded together a failed request left the
 * screen saying *asking the server* for ever, which is a screen asserting
 * something that is not happening.
 */
type CardState = "live" | "replay" | "not-yet" | "asking" | "no-answer";

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
   * can play back. Null while that answer is still on its way **or did not come
   * back at all** — which of the two is what `readinessFailure` says.
   */
  readonly readiness: Readiness | null;
  /**
   * Why the server could not be asked what this copy can do, if it could not be.
   *
   * **Null is not "still asking".** A request that failed and a request in
   * flight are both an absent answer, and a screen that cannot tell them apart
   * says *asking the server* for ever over an ask that ended minutes ago. The
   * sentence here is the failure's own, printed as it came.
   */
  readonly readinessFailure?: string | null;
  /** Open a stored example's map, already drawn. */
  readonly onOpen: (id: string) => void;
  /** Build a map from a sentence. */
  readonly onBuild: (asked: Asked) => void;
}

/** The first screen. */
export function Launchpad({
  examples,
  failure,
  readiness,
  readinessFailure = null,
  onOpen,
  onBuild,
}: LaunchpadProps) {
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
  const canPlay = whatThisCopyCanPlay(
    playable,
    STARTING_SENTENCES.filter((one) => !recorded.has(one.example)).map((one) => one.about),
  );
  const stateOf = (example: string): CardState =>
    readinessFailure !== null
      ? "no-answer"
      : readiness === null
        ? "asking"
        : hasKey
          ? "live"
          : recorded.has(example)
            ? "replay"
            : "not-yet";
  // The sentences that get a card: the ones this copy can actually do something
  // with, and — while nothing is known about any of them — all of them. The rest
  // are named in one line under the cards rather than drawn as rows nobody can
  // press.
  const shown = STARTING_SENTENCES.filter((one) => stateOf(one.example) !== "not-yet");

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
        {/* **Only what this copy can actually do gets a card.** The four
            sentences used to be four cards whatever the answer was, and with one
            recording committed that is one door and three headstones taking the
            whole of this column. What is left of the three is the line under the
            cards, which already named them.

            With nothing at all to offer there is no list, because an empty list
            under a heading that says *or watch one build itself* is worse than
            a sentence saying so. */}
        {shown.length === 0 ? (
          <p className="launchpad__keyless">
            {`No model key configured, and nothing recorded — so ` +
              `${asAList(STARTING_SENTENCES.map((one) => one.about))} cannot be shown building ` +
              `here. The map above is already drawn and needs neither.`}
          </p>
        ) : (
          <ul className="examples">
            {shown.map((one) => {
              const state = stateOf(one.example);
              const day = recorded.get(one.example);
              return (
                <li key={one.example}>
                  {state === "asking" || state === "no-answer" ? (
                    // **Nothing is known about this sentence, and the two ways
                    // of not knowing are told apart.** Before the server has
                    // answered, neither a key nor a recording is known, and
                    // saying either would be the screen asserting something
                    // nobody told it. After an ask that did not come back, the
                    // same is true and *asking the server* would be worse than
                    // silence: it says a question is in flight when none is. The
                    // words are the shared vocabulary's own for the two, and the
                    // server's own sentence is under the cards, once.
                    <div className="example example--waiting" data-state={state}>
                      <span className="example__claim">{one.sentence}</span>
                      <span className="example__line">
                        {state === "asking"
                          ? "Asking the server whether this one can be run here: whether a model key is configured, and whether there is a recording of it to play."
                          : "The ask did not come back, so nothing is known about whether this one can be run here."}
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
        )}

        {/* Record 0012's sentence, word for word, under the cards — and again
            under the field below, which is disabled with it. It is also what
            names the sentences that have no card: *…the other three have
            nothing recorded yet* is the whole of what there is to say about
            them, and it was already being said here. */}
        {canPlay === null || hasKey || readinessFailure !== null ? null : (
          <p className="launchpad__keyless">{canPlay}</p>
        )}
        {/* **The server's own sentence, once, under the cards that cannot say
            what they are.** It is printed here rather than on each of them
            because it is one fact about this copy and not four facts about four
            examples — and it says what to do about it, which is what tells an
            ask that did not come back apart from an answer that said no. */}
        {readinessFailure === null ? null : (
          <p className="launchpad__keyless">
            {`${readinessFailure} This page asks once: reload it to ask again. Until it answers, nothing here is offered as if it could run.`}
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
            readinessFailure !== null
              ? `${readinessFailure} This page asks once: reload it to ask again. Until it answers, whether a sentence of your own could be turned into a map is not known.`
              : readiness === null
                ? "Asking the server whether a model key is configured. A sentence of your own needs the model, and nothing recorded can stand in for one."
                : hasKey
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
