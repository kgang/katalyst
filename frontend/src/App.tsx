/**
 * The whole screen: the launchpad, and the map you open from it.
 *
 * Two states and nothing in between. The launchpad names the two ways into the
 * tool and offers the four examples from the brief; opening the one that is
 * built swaps the page for the map. Everything on the map came over the wire
 * from the server, and the line under it says which address it came from — this
 * product does not put a number on screen that a reader cannot trace to an
 * input, a rule or a source, and that includes numbers a stored example happens
 * to carry.
 *
 * There is no spinner anywhere, and there never will be. A spinner says "wait"
 * without saying what for. While something is on its way the screen says what
 * it is waiting for and where it asked.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { About, FixtureSummary, Health, Readiness } from "./api/client";
import { readAbout, readExampleList, readHealth, readReadiness } from "./api/client";
import { Launchpad } from "./components/Launchpad";
import { MapCanvas } from "./graph/Canvas";
import { FixtureWorldSource, type WorldSource, type WorldView } from "./world";

/**
 * Everything the screen can know about one thing it asked for. Three states and
 * no others, which is what makes every pixel below traceable to a cause.
 */
type Answer<Reading> =
  | { state: "asking" }
  | { state: "answered"; value: Reading }
  | { state: "failed"; reason: string };

/** How loud a row's words are. Emphasis only — the words carry the meaning. */
type Tone = "good" | "quiet" | "loud";

/** One row of the strip at the foot of the launchpad. */
interface Reading {
  /** What is being reported, such as "server". */
  label: string;
  /** The value from the server, or null while the request is still in flight. */
  value: string | null;
  /** A mark beside the words. Never the only carrier of meaning. */
  glyph: string;
  /** What the value means, in plain words. On a failure, this is the failure. */
  state: string;
  tone: Tone;
}

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
            state: "no key configured — generating a map is not built yet",
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
        state: `reported by ${answer.value.name}`,
        tone: "good",
      };
    case "failed":
      return { label: "version", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/**
 * Why the three examples that need the model are not live, in one sentence.
 *
 * Read from the server's own answer rather than written into the page, so that
 * the reason on screen is the real one.
 */
function notLiveReason(answer: Answer<Readiness>): string {
  if (answer.state === "answered" && !answer.value.model_key_present) {
    return "Turning your own words into a map needs the model, and this server has no key for one.";
  }
  return "Turning your own words into a map is not built yet.";
}

/**
 * One row: a label, the value the server gave, and what that value means.
 *
 * While the value is missing the cell holds a bar of the same height, so the
 * row does not change size when the answer arrives. There is no spinner: a bar
 * where the value will land says the same thing without pretending to spin.
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

/** Which of the two screens is showing. */
type Screen =
  | { at: "launchpad" }
  | { at: "opening"; id: string }
  | { at: "map"; world: WorldView }
  | { at: "failed"; id: string; reason: string };

/**
 * Where maps come from.
 *
 * Today this reads the stored example the server ships with. When the engine's
 * world route lands, this one line becomes `new ApiWorldSource()` and every
 * number slot that reads as an absence today fills in. Nothing else on this
 * screen changes, which is the whole reason there is a seam here at all.
 */
const DEFAULT_SOURCE: WorldSource = new FixtureWorldSource();

/** What the screen needs. Both have defaults; both exist so they can be swapped. */
export interface AppProps {
  /** Where maps and worlds come from. */
  readonly source?: WorldSource;
  /** How the list of stored examples is read. */
  readonly listExamples?: () => Promise<FixtureSummary[]>;
}

/** The screen. */
export function App({ source = DEFAULT_SOURCE, listExamples = readExampleList }: AppProps = {}) {
  const health = useAnswer(readHealth);
  const readiness = useAnswer(readReadiness);
  const about = useAnswer(readAbout);
  const examples = useAnswer(listExamples);

  const [screen, setScreen] = useState<Screen>({ at: "launchpad" });

  const open = useCallback(
    (id: string) => {
      setScreen({ at: "opening", id });
      source.readWorld({ baseId: id }).then(
        (world) => setScreen({ at: "map", world }),
        (reason: unknown) => setScreen({ at: "failed", id, reason: inWords(reason) }),
      );
    },
    [source],
  );

  const toLaunchpad = useCallback(() => setScreen({ at: "launchpad" }), []);

  const readings = useMemo(
    () => [serverReading(health), modelKeyReading(readiness), versionReading(about)],
    [health, readiness, about],
  );

  if (screen.at !== "launchpad") {
    return (
      <main className="page page--map">
        <header className="map-bar">
          <button className="map-bar__back" type="button" onClick={toLaunchpad}>
            <span aria-hidden="true">←</span> Back to the launchpad
          </button>
          <h1 className="map-bar__title">
            {screen.at === "map" ? screen.world.title : "Strait of Hormuz"}
          </h1>
        </header>

        {screen.at === "map" ? (
          <>
            <MapCanvas world={screen.world} />
            <p className="map-origin">{screen.world.origin}</p>
          </>
        ) : (
          <div className="map-waiting">
            <p className="map-waiting__line">
              {screen.at === "opening"
                ? `Reading the stored map from /api/fixtures/${screen.id}.`
                : screen.reason}
            </p>
          </div>
        )}
      </main>
    );
  }

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

        <Launchpad
          examples={examples.state === "answered" ? examples.value : null}
          failure={examples.state === "failed" ? examples.reason : null}
          notLiveReason={notLiveReason(readiness)}
          onOpen={open}
        />

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
            <code>/api/readyz</code> and <code>/api/about</code>. The examples came from{" "}
            <code>/api/fixtures</code>. Nothing on this screen is written into the page.
          </p>
        </section>
      </div>
    </main>
  );
}
