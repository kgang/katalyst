/**
 * The whole screen, for now.
 *
 * It names the product, says in one line what the product does, and reports
 * what the server just told us about itself. That report is the interesting
 * part: three readings, each one traceable to the route it came from, each one
 * in one of exactly three named states — waiting for an answer, answered, or
 * failed. There is no fourth state, and nothing on the screen is drawn from
 * anything but those three.
 *
 * Which product rules this serves (PRODUCT_REQUIREMENTS.md section 7):
 *
 *   UX-6  Meaning is never carried by colour alone: every reading has a glyph
 *         and a word beside it, and the word is what says what happened.
 *   UX-7  While a request is in flight the value cell holds a plain bar of the
 *         same height, so nothing moves when the answer lands. There is no
 *         spinner: a spinner says "wait" without saying what for.
 *   UX-10 A failure is printed in the row it belongs to, in a sentence. It is
 *         never a pop-up dialog the reader has to dismiss.
 *   UX-11 Values sit in the monospace face with fixed-width digits.
 *   UX-12 The readings are a description list, so the relationship between a
 *         label and its value survives being read aloud.
 */

import { useEffect, useState } from "react";
import type { About, Health, Readiness } from "./api/client";
import { readAbout, readHealth, readReadiness } from "./api/client";

/**
 * Everything the screen can know about one reading. There are three states and
 * no others, which is what makes every pixel below traceable to a cause.
 */
type Answer<Reading> =
  | { state: "asking" }
  | { state: "answered"; value: Reading }
  | { state: "failed"; reason: string };

/**
 * How loud a row's words are. This changes emphasis only — the words carry the
 * meaning, so a reader who cannot see the difference loses nothing.
 */
type Tone = "good" | "quiet" | "loud";

/** One row of the strip, already turned into the words that will be printed. */
type Reading = {
  /** What is being reported, such as "server". */
  label: string;
  /** The value from the server, or null while the request is still in flight. */
  value: string | null;
  /** A mark beside the words. Never the only carrier of meaning. */
  glyph: string;
  /** What the value means, in plain words. On a failure, this is the failure. */
  state: string;
  tone: Tone;
};

/** Turn whatever a failed request threw into one sentence. */
function inWords(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The reason was not recorded.";
}

/**
 * Make one request when the screen first appears and report where it got to.
 *
 * @param ask The request to make. It must be the same function on every render,
 *   so pass one defined at module level rather than one written inline.
 */
function useAnswer<Reading>(ask: () => Promise<Reading>): Answer<Reading> {
  const [answer, setAnswer] = useState<Answer<Reading>>({ state: "asking" });

  useEffect(() => {
    let stillOnScreen = true;
    ask().then(
      (value) => {
        if (stillOnScreen) {
          setAnswer({ state: "answered", value });
        }
      },
      (reason: unknown) => {
        if (stillOnScreen) {
          setAnswer({ state: "failed", reason: inWords(reason) });
        }
      },
    );
    return () => {
      stillOnScreen = false;
    };
  }, [ask]);

  return answer;
}

/** The row that says whether the server answered at all. */
function serverReading(answer: Answer<Health>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "server",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return {
        label: "server",
        value: answer.value.status,
        glyph: "●",
        state: "reachable",
        tone: "good",
      };
    case "failed":
      return { label: "server", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/** The row that says whether a key for the language model is configured. */
function modelKeyReading(answer: Answer<Readiness>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "model key",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return answer.value.model_key_present
        ? {
            label: "model key",
            value: "present",
            glyph: "●",
            state: "ready to generate",
            tone: "good",
          }
        : {
            label: "model key",
            value: "absent",
            glyph: "○",
            state: "no key configured — generation arrives in stack 04",
            tone: "quiet",
          };
    case "failed":
      return { label: "model key", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/** The row that says which build answered. */
function versionReading(answer: Answer<About>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "version",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return {
        label: "version",
        value: answer.value.version,
        glyph: "●",
        state: `named ${answer.value.name}`,
        tone: "good",
      };
    case "failed":
      return { label: "version", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/**
 * One row: a label, the value the server gave, and what that value means.
 *
 * While the value is missing the cell holds a bar of the same height, so the
 * row does not change size when the answer arrives. Once there is a value the
 * cell fades it in over a single duration token and then stops moving.
 */
function StatusRow({ reading }: { reading: Reading }) {
  const waiting = reading.value === null;
  return (
    <div className="status-row">
      <dt className="status-label">{reading.label}</dt>
      <dd className="status-value" data-settled={waiting ? "no" : "yes"}>
        {waiting ? <span className="placeholder" aria-hidden="true" /> : reading.value}
      </dd>
      <dd className="status-state" data-tone={reading.tone}>
        <span className="glyph" aria-hidden="true">
          {reading.glyph}
        </span>
        <span className="state-words">{reading.state}</span>
      </dd>
    </div>
  );
}

/** The screen. */
export function App() {
  const health = useAnswer(readHealth);
  const readiness = useAnswer(readReadiness);
  const about = useAnswer(readAbout);

  const readings = [serverReading(health), modelKeyReading(readiness), versionReading(about)];

  return (
    <main className="page">
      <div className="column">
        <header className="masthead">
          <h1 className="wordmark">Katalyst</h1>
          <p className="purpose">
            Type an event you think will happen. See what it would cause, step by step, ending in
            trades.
          </p>
        </header>

        <section aria-labelledby="status-heading">
          <h2 className="section-heading" id="status-heading">
            What this build can do right now
          </h2>
          <dl className="status-strip">
            {readings.map((reading) => (
              <StatusRow key={reading.label} reading={reading} />
            ))}
          </dl>
          <p className="provenance">
            Every reading above came from the server, at <code>/api/healthz</code>,{" "}
            <code>/api/readyz</code> and <code>/api/about</code>. Nothing on this screen is written
            into the page.
          </p>
        </section>
      </div>
    </main>
  );
}
