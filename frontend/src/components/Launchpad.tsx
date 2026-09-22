/**
 * The first screen: four ways to start, and the same four however this copy is
 * configured.
 *
 * **One screen, not two.** Before this file was rewritten, what a reader met
 * depended on something nobody had told them about: whether a model key was set
 * in the environment. With a key every example called a model and the committed
 * recording was unreachable; with none, one example played and the other three
 * were not drawn at all. Two readers, two screens, and no way from one to the
 * other except by editing a file.
 *
 * Now the four ways are always drawn, in the same order, in the same words. What
 * changes between the two readers is **what is enabled, and the reason printed
 * beside what is not** (INV-workbench.82 — the same ways both times, and a way
 * that cannot be taken says why, beside itself).
 *
 * | The way | What it is | What it sends |
 * |---|---|---|
 * | 1 · Open the map | The stored worked example, already drawn | nothing — no request, no model, no recording |
 * | 2 · Watch the recording | The committed recording of a sentence, badged *replay* | the sentence, with the start named `replay` |
 * | 3 · Run it live | One of the four sentences from the brief, calling a model | the sentence, with the start named `live` |
 * | 4 · Build the map | A sentence of the reader's own | what they typed, with the start named `live` |
 *
 * **Ways 1 and 2 need no key and never change.** They are first for that
 * reason: the most persuasive minute of this prototype should not sit behind a
 * decision about money. Way 2 is how a reviewer who *has* a key reaches the
 * keyless half of the product — Kent's own question of 2026-09-21, *"How can i
 * test out all the functionality if I run it with a valid anthropic key?"*
 *
 * **Every figure on this screen came from the server's answer about itself**
 * (INV-workbench.83). What a live run costs and how long it takes are read off
 * the recorded run's own receipt, which the readiness route carries, and are
 * printed with the day they were measured. Nothing here holds a price, a
 * duration or a count of calls: a recording whose receipt this engine could not
 * read prints no figure at all, and says that is why.
 *
 * **Three things this screen never does.** It never lets the key decide what is
 * offered — the key is a reason printed beside a disabled control and nothing
 * else. It never puts a mode switch at the top, because a control that silently
 * changes what four other controls do is the hidden mode that confused a reader
 * in the first place. And it never asserts anything before the server has
 * spoken: until the readiness answer arrives, each way that depends on it says
 * what is being waited for.
 */

import { useState } from "react";
import type { FixtureSummary, Readiness, RecordingSummary } from "../api/client";
import { useEveryKey } from "../keyboard/everyKey";
import type { Asked } from "./InputBar";
import { InputBar } from "./InputBar";
import "./launchpad.css";
import { asMoney } from "./ReceiptStrip";
import { ShortcutsSheet } from "./ShortcutsSheet";

/** One of the four sentences from the brief, and which recording answers to it. */
export interface StartingSentence {
  /**
   * Which stored example this is.
   *
   * It is the name the readiness answer uses for a recording, so that the
   * recording way can say which sentences it can play. It is **not** a file name
   * and it never reaches a request: what a row sends is its sentence, exactly as
   * a reader would type it, which is what makes the replayed path and the live
   * path send byte-identical requests bar the one field naming the start.
   */
  readonly example: string;
  /** The sentence, as a person would actually type it. */
  readonly sentence: string;
  /**
   * What this example is about, in two or three words.
   *
   * **It is how a sentence is named where its own words would not fit** — the
   * line saying which sentences have nothing recorded, and the line saying whose
   * run a measured price describes. It is authored here, beside the sentence it
   * belongs to, and it is not the recording's short name (`hormuz`,
   * `export-controls`): those are identifiers that name a file and an eval case,
   * and an identifier is never words on the screen.
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
 * Everything this screen knows about the copy it is running on.
 *
 * **Three states, and the two ways of not knowing are kept apart.** A request in
 * flight and a request that got no reply are both an absent answer, and a screen
 * that cannot tell them apart says *asking the server* for ever over an ask that
 * ended minutes ago. *Asking* invites waiting; *the ask did not come back*
 * invites asking again, and may well be gone by the time somebody does.
 */
type WhatTheServerSaid =
  | { heard: "nothing yet" }
  | { heard: "the ask did not come back"; sentence: string }
  | { heard: "this"; readiness: Readiness };

/**
 * How long something took, in the words a sentence would use.
 *
 * **Rounded for reading and never for arithmetic.** The seconds arrive on the
 * receipt at whatever precision they were measured with; this is a decision made
 * at the moment of printing, and nothing reads the string back. A minute and a
 * half is where the reading changes, because *about 95 seconds* is a figure
 * nobody thinks in.
 *
 * @param seconds The measured duration, in the receipt's own unit.
 */
export function howLong(seconds: number): string {
  if (seconds < 90) {
    const whole = Math.round(seconds);
    return `about ${whole} ${whole === 1 ? "second" : "seconds"}`;
  }
  const minutes = Math.round(seconds / 60);
  return `about ${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
}

/**
 * What the recorded run of one example cost, in one sentence, or nothing at all.
 *
 * **Every figure in it is the server's**, read off the receipt line inside the
 * committed recording and carried here on the readiness answer. The day is the
 * day it was measured, because a price with no date is a promise rather than a
 * measurement — the two readings this product has of the same example differ by
 * a factor of three.
 *
 * **Nothing at all when the receipt could not be read.** A replay rebuilds the
 * receipt rather than emitting the recorded one, so a file that plays perfectly
 * well can still carry a receipt this engine cannot read. The three figures come
 * back absent together, and an absence is printed as an absence.
 *
 * @param about What the example is about, in the reader's words.
 * @param summary What the server said about that recording.
 */
export function whatTheRecordedRunCost(about: string, summary: RecordingSummary): string | null {
  const { calls, seconds, dollars } = summary;
  if (
    calls === null ||
    calls === undefined ||
    seconds === null ||
    seconds === undefined ||
    dollars === null ||
    dollars === undefined
  ) {
    return null;
  }
  return (
    `The recorded run of ${about} made ${calls} model ${calls === 1 ? "call" : "calls"}, ` +
    `took ${howLong(seconds)} and cost ${asMoney(dollars)}, on ${summary.recording_date}.`
  );
}

/**
 * Why nothing here can call a model right now, in one sentence, or null when it
 * can.
 *
 * The same sentence disables ways 3 and 4, because it is one fact about this
 * copy rather than two facts about two controls — and it is printed on each of
 * them rather than in a banner over the screen, because a reader looking at a
 * control they cannot press is owed the reason there.
 *
 * @param said What the server has told this screen about itself.
 */
export function whyNoModelCanBeCalled(said: WhatTheServerSaid): string | null {
  switch (said.heard) {
    case "nothing yet":
      return "Asking the server whether a model key is configured. Until it answers, nothing here is offered as if it could run.";
    case "the ask did not come back":
      return `${said.sentence} This page asks once: reload it to ask again. Until it answers, nothing here is offered as if it could run.`;
    case "this":
      return said.readiness.model_key_present
        ? null
        : "No model key is configured, so this copy cannot call a model. The first two ways need none.";
  }
}

/**
 * Why there is no recording to watch, in one sentence, or null when there is.
 *
 * **A different reason from way 3's, on purpose.** Watching a recording needs no
 * key and never did; what it needs is a committed file. Printing *no model key*
 * beside it would be this screen blaming the wrong absence.
 *
 * @param said What the server has told this screen about itself.
 * @param playable How many of the four sentences have a recording here.
 */
export function whyNoRecording(said: WhatTheServerSaid, playable: number): string | null {
  switch (said.heard) {
    case "nothing yet":
      return "Asking the server which of these it has a recording of.";
    case "the ask did not come back":
      return `${said.sentence} This page asks once: reload it to ask again. Until it answers, nothing is known about what this copy can play.`;
    case "this":
      return playable > 0
        ? null
        : "This copy has no recording of any of these sentences, so there is nothing to watch. A recording is made against a real key by whoever holds one.";
  }
}

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
   * What the server said about itself: whether a key is configured, what it can
   * play, and what each recorded run cost. Null while that answer is still on
   * its way **or did not come back at all** — which of the two is what
   * `readinessFailure` says.
   */
  readonly readiness: Readiness | null;
  /**
   * Why the server could not be asked what this copy can do, if it could not be.
   *
   * **Null is not "still asking".** The sentence here is the failure's own,
   * printed as it came.
   */
  readonly readinessFailure?: string | null;
  /** Open a stored example's map, already drawn. */
  readonly onOpen: (id: string) => void;
  /**
   * Start a generation. The press names how it starts, which is the whole point
   * of this screen: the server no longer reads the key to choose (record 0012,
   * amended 2026-09-21).
   */
  readonly onBuild: (asked: Asked) => void;
}

/** The head of one way to start: its place in the order, its name, and its price. */
function WayHead({ number, name, cost }: { number: number; name: string; cost: string }) {
  return (
    <h2 className="way__head" id={`way-${number}`}>
      {/* The number is read out with the name rather than hidden from a screen
          reader: it is the order, and the order is something the words beside
          these headings promise. */}
      <span className="way__number">{number}</span>
      <span className="way__name">{name}</span>
      <span className="way__cost">{cost}</span>
    </h2>
  );
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
  // `?` opens the sheet of every key here too, from the one module that binds
  // it on every screen. There is no palette of commands on this screen and no
  // map to close, so ⌘K does nothing and Escape only puts the sheet away.
  const [sheetIsUp, setSheetIsUp] = useState(false);
  useEveryKey({
    everyKey: () => setSheetIsUp((was) => !was),
    escape: () => setSheetIsUp(false),
  });

  const said: WhatTheServerSaid =
    readinessFailure !== null
      ? { heard: "the ask did not come back", sentence: readinessFailure }
      : readiness === null
        ? { heard: "nothing yet" }
        : { heard: "this", readiness };

  // What this copy can play, in the order this screen offers the sentences —
  // read off the four rather than off the whole answer, so a recording of
  // something this screen does not offer cannot end up on it.
  const recorded = new Map(
    (readiness?.replayable ?? []).map((one): [string, RecordingSummary] => [one.example, one]),
  );
  const playable = STARTING_SENTENCES.filter((one) => recorded.has(one.example));
  const unrecorded = STARTING_SENTENCES.filter((one) => !recorded.has(one.example));

  const noModel = whyNoModelCanBeCalled(said);
  const noRecording = whyNoRecording(said, playable.length);

  // **The one measured price this product owns**, one line per recording that
  // carries a receipt this engine could read. Never a figure written here: a
  // price typed into a component is a number nobody computed, sitting on the
  // first thing a reviewer reads.
  const measured = playable
    .map((one) => whatTheRecordedRunCost(one.about, recorded.get(one.example) as RecordingSummary))
    .filter((line): line is string => line !== null);

  return (
    <div className="launchpad">
      <p className="launchpad__ways">
        <strong>Four ways to start.</strong> The first two are free and need no key. The other two
        call a model, and say what that costs before you press.
      </p>

      <section className="way way--open" aria-labelledby="way-1">
        <WayHead number={1} name="Open the map" cost="free · instant" />
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
                <button className="example" type="button" onClick={() => onOpen(example.id)}>
                  <span className="example__claim">{example.title}</span>
                  <span className="example__line">{example.one_line}</span>
                  <span className="example__foot">
                    <span className="example__action">Open the map</span>
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="way way--recording" aria-labelledby="way-2">
        <WayHead number={2} name="Watch the recording" cost="free" />
        {/* **The recording is reachable whatever the key says.** A reader who
            asks for it gets it: the same route, the same eight events and the
            same canvas a live run uses, with the replay badge on the map and a
            receipt of zeroes. That is not a fallback — record 0012 forbids the
            *server* choosing, and this is the reader choosing. */}
        {playable.length === 0 ? null : (
          <ul className="examples">
            {playable.map((one) => {
              const summary = recorded.get(one.example) as RecordingSummary;
              return (
                <li key={one.example}>
                  <button
                    className="example"
                    type="button"
                    data-start="replay"
                    onClick={() =>
                      onBuild({
                        hypothesis: one.sentence,
                        target: null,
                        belief: null,
                        start: "replay",
                      })
                    }
                  >
                    <span className="example__claim">{one.sentence}</span>
                    <span className="example__line">
                      Plays the recording of this run back, claim by claim, through the same route
                      and the same canvas. Calls nobody and spends nothing.
                    </span>
                    <span className="example__foot">
                      <span className="example__action">Watch the recording</span>
                      <span className="example__badge">replay</span>
                      <span className="example__aside">recorded {summary.recording_date}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {noRecording === null ? null : <p className="launchpad__why">{noRecording}</p>}
        {/* The sentences with no recording are **named**, because they are not
            on this list to be counted: a line reading *the other three* points
            at sentences that are somewhere else on the screen. */}
        {playable.length > 0 && unrecorded.length > 0 ? (
          <p className="launchpad__why launchpad__why--quiet">
            {`Nothing is recorded yet for ${asAList(unrecorded.map((one) => one.about))}; ` +
              `those can still be run live.`}
          </p>
        ) : null}
        {/* **A recording that would not play is named, in the server's own
            sentence.** A reviewer who dropped a file in the recordings folder
            and then counts one row where they expected two is owed the reason
            rather than left to wonder. The good recordings still play, which is
            the other half of the same rule. */}
        {(readiness?.unreadable ?? []).map((sentence) => (
          <p className="launchpad__why launchpad__why--quiet" key={sentence}>
            {sentence}
          </p>
        ))}
      </section>

      <section className="way way--live" aria-labelledby="way-3">
        <WayHead number={3} name="Run it live" cost="calls a model" />
        {/* **What it costs and how long it takes, before the press.** Read from
            the server's answer about itself and printed with the day it was
            measured — never worked out here, never typed here. */}
        {measured.length === 0 ? (
          <p className="launchpad__why">
            No recording here carries a receipt this copy could read, so there is no measured price
            to state. Nothing is printed in its place.
          </p>
        ) : (
          <div className="way__measure">
            {measured.map((line) => (
              <p className="way__measure-line" key={line}>
                {line}
              </p>
            ))}
            <p className="way__measure-note">
              That is the recorded run&rsquo;s own receipt, made at the effort a recording is made
              with. A run started here asks the model for less, so it will not take as long — and
              what it spends is not known until it has spent it.
            </p>
          </div>
        )}
        <ul className="examples">
          {STARTING_SENTENCES.map((one) => (
            <li key={one.example}>
              {/* **One line each.** Four sentences, and the same thing happens
                  to each of them, so a paragraph under every one would be the
                  same paragraph four times. What the row does is said beside the
                  sentence rather than under it — which is also what keeps the
                  list short enough to be read as a list. */}
              <button
                className="example example--terse"
                type="button"
                data-start="live"
                disabled={noModel !== null}
                onClick={() =>
                  onBuild({ hypothesis: one.sentence, target: null, belief: null, start: "live" })
                }
              >
                <span className="example__claim">{one.sentence}</span>
                <span className="example__foot">
                  <span className="example__action">Run it live</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {noModel === null ? null : <p className="launchpad__why">{noModel}</p>}
      </section>

      <section className="way way--yours" aria-labelledby="way-4">
        <WayHead number={4} name="Build the map" cost="calls a model" />
        {/* **Way 4 is a live run too, and says so.** It was the door a reader
            typed into and waited at, with no idea what it would cost — while the
            row above it quoted a measured price. Its own price cannot be quoted,
            because nobody has run their sentence; so the measurement above is
            offered as what it is, another example's run, and never as an
            estimate of theirs. */}
        <p className="way__measure-note">
          A sentence of your own calls a model, exactly as <strong>Run it live</strong> does. What
          it costs is not known before it runs, because nobody has run your sentence. The figures
          under <strong>Run it live</strong> are the recorded run of another example — the only
          measurement this product owns, and not an estimate of yours.
        </p>
        <InputBar
          disabledBecause={noModel}
          onBuild={(asked) => onBuild({ ...asked, start: "live" })}
        />
      </section>

      {/* The sheet of every key, in a pane the size of the window because this
          screen has no map stage to hang it in. It is drawn only when it is up,
          so nothing lies over this screen until a reader asks for it. */}
      {sheetIsUp ? (
        <div className="every-key-anchor">
          <ShortcutsSheet open={true} onClose={() => setSheetIsUp(false)} />
        </div>
      ) : null}
    </div>
  );
}
