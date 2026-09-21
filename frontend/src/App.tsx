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
import type { Asked } from "./components/InputBar";
import { Launchpad } from "./components/Launchpad";
import { MapScreen } from "./components/MapScreen";
import { GenerationScreen } from "./stream/GenerationScreen";
import type { TheRun } from "./stream/theRun";
import { askForAMap } from "./stream/theRun";
import {
  ApiWorldSource,
  type BranchView,
  branchesOf,
  FixtureWorldSource,
  type WorldSource,
  type WorldView,
} from "./world";
import { asOneSentence } from "./world/failures";
import { countInWords } from "./world/naming";

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

/**
 * Ask what this copy can do.
 *
 * Defined at module level because the hook below runs it once and needs the
 * same function on every render.
 *
 * **It reads the generated description of the server and nothing else.** The
 * two fields the first screen lives on — which examples can be played, and one
 * sentence per recording this engine could not read — were written out by hand
 * here for as long as the route that owns them was being built beside this
 * half. They are in `schema.ts` now, so the hand-written copy is gone: two
 * descriptions of one answer eventually disagree, and the generated one is the
 * server's own.
 */
function askReadiness(): Promise<Readiness> {
  return readReadiness();
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
          setAnswer({ state: "failed", reason: asOneSentence(reason) });
        }
      },
    );
    return () => {
      stillOnScreen = false;
    };
  }, [ask]);

  return answer;
}

/**
 * Whether the server answered, and which build answered — in one quiet line.
 *
 * **They were two rows of the strip, and they are two facts a reader of this
 * screen is not making a decision about.** A route name and a build number
 * under the first screen make a take-home read as an implementation showcase at
 * the moment it should read as a decision tool. Nothing is lost: both readings
 * are still here, still the server's own, still traceable to the address the
 * line under them names. They are simply not given the weight of a labelled row
 * beside the one reading that changes what a reader can do, which is whether
 * there is a model key.
 *
 * Each half says where it has got to for itself, so a failure of one is not
 * hidden by the other answering.
 *
 * @param health What `/api/healthz` said, or where that question has got to.
 * @param about What `/api/about` said, or where that question has got to.
 */
function serverAndBuild(health: Answer<Health>, about: Answer<About>): string {
  const reachable =
    health.state === "asking"
      ? "Asking the server whether it is there."
      : health.state === "answered"
        ? `Server ${health.value.status}.`
        : health.reason;
  const build =
    about.state === "asking"
      ? "Asking which build answered."
      : about.state === "answered"
        ? `Build ${about.value.version}, reported by ${about.value.name}.`
        : about.reason;
  return `${reachable} ${build}`;
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
            state:
              answer.value.replayable.length === 0
                ? "no key configured, and nothing recorded to play instead"
                : `no key configured — ${countInWords(answer.value.replayable.length)} ` +
                  `${answer.value.replayable.length === 1 ? "example plays" : "examples play"} ` +
                  `from recordings`,
            tone: "quiet",
          };
    case "failed":
      return { label: "model key", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
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

/** Which of the screens is showing. */
type Screen =
  | { at: "launchpad" }
  | { at: "opening"; id: string }
  /**
   * A map being built in front of the reader, from a sentence they typed.
   *
   * **The run is here, not inside the screen**, because the press that made this
   * state is what asked for it. A screen that asked on mount would ask twice in
   * development, where React mounts every screen, unmounts it and mounts it
   * again on purpose — and *"never retry, a generation that ran twice would
   * spend twice"* would be broken on every machine this product is built on.
   */
  | { at: "growing"; run: TheRun }
  | {
      at: "map";
      world: WorldView;
      branches: readonly BranchView[];
      /**
       * Why the map on screen was read from the stored example rather than
       * worked out by the engine, or nothing when the engine answered.
       */
      insteadOfTheEngine: string | null;
    }
  | { at: "failed"; id: string; reason: string };

/**
 * Where maps come from: the engine.
 *
 * Every number on the map is worked out by it, from the stored map, the branch
 * and one seed. Nothing on this screen computes a likelihood, and nothing on
 * this screen shows one the engine did not produce.
 */
const DEFAULT_SOURCE: WorldSource = new ApiWorldSource();

/**
 * Where maps come from when the engine cannot be reached.
 *
 * A map you can still read beats a blank screen. The stored example's claims,
 * arrows, dates and sources are all real and all still worth reading — what is
 * missing is the working-out, and the screen says so in a line under the map
 * rather than letting a hand-written likelihood pass for a computed one.
 */
const FALLBACK_SOURCE: WorldSource = new FixtureWorldSource();

/**
 * The line under the map when the stored example is standing in for the engine.
 *
 * @param reason What went wrong, in the sentence the failure arrived with.
 */
function insteadOfTheEngine(reason: string): string {
  return (
    `The engine did not answer, so this map is the stored example exactly as it was written: ` +
    `its claims, arrows, dates and sources are real, and its likelihoods are the illustrative ` +
    `ones somebody wrote down rather than anything worked out. ${reason}`
  );
}

/** What the screen needs. All three have defaults; all three exist so they can be swapped. */
export interface AppProps {
  /** Where maps and worlds come from. */
  readonly source?: WorldSource;
  /** Where they come from when the first one cannot answer. */
  readonly fallback?: WorldSource;
  /** How the list of stored examples is read. */
  readonly listExamples?: () => Promise<FixtureSummary[]>;
}

/** The screen. */
export function App({
  source = DEFAULT_SOURCE,
  fallback = FALLBACK_SOURCE,
  listExamples = readExampleList,
}: AppProps = {}) {
  const health = useAnswer(readHealth);
  const readiness = useAnswer(askReadiness);
  const about = useAnswer(readAbout);
  const examples = useAnswer(listExamples);

  const [screen, setScreen] = useState<Screen>({ at: "launchpad" });
  const [using, setUsing] = useState<WorldSource>(source);

  const open = useCallback(
    (id: string) => {
      setScreen({ at: "opening", id });
      /**
       * The world and the map's own branches, together: the world is what gets
       * drawn, and the branches are the edits somebody already made to it, which
       * the panel lists and the diff view folds on.
       *
       * @param from Where to ask.
       */
      const ask = (from: WorldSource) =>
        Promise.all([from.readWorld({ baseId: id }), from.readBundle(id)]);

      ask(source).then(
        ([world, bundle]) => {
          setUsing(source);
          setScreen({ at: "map", world, branches: branchesOf(bundle), insteadOfTheEngine: null });
        },
        (failure: unknown) => {
          // The engine could not answer. Rather than a blank screen, the stored
          // example — and a line under the map saying, in the failure's own
          // words, that these are not computed numbers.
          ask(fallback).then(
            ([world, bundle]) => {
              setUsing(fallback);
              setScreen({
                at: "map",
                world,
                branches: branchesOf(bundle),
                insteadOfTheEngine: insteadOfTheEngine(asOneSentence(failure)),
              });
            },
            // Neither answered, which means the server itself is not there. That
            // is one sentence on the page, and a way back to the launchpad.
            (alsoFailed: unknown) =>
              setScreen({ at: "failed", id, reason: asOneSentence(alsoFailed) }),
          );
        },
      );
    },
    [source, fallback],
  );

  const toLaunchpad = useCallback(() => setScreen({ at: "launchpad" }), []);

  /**
   * Build a map from a sentence, and watch it arrive.
   *
   * **The request goes from here**, inside the press. Not from a render and not
   * from an effect: an effect runs twice in development by design, and this is
   * the one request in the product where running twice means paying twice.
   */
  // **The press says how the run starts; the route no longer reads the key to
  // decide** (record 0012, amended 2026-09-21). This is the expression the route
  // used to work out for itself, said here instead, so what happens with a key
  // and without one is exactly what happened before. The first screen replaces it
  // with what the reader chose, which is the whole point of moving it.
  const hasKey = readiness.state === "answered" && readiness.value.model_key_present;
  const build = useCallback(
    (asked: Asked) => {
      const run = askForAMap({ ...asked, start: hasKey ? "live" : "replay" });
      setScreen({ at: "growing", run });
    },
    [hasKey],
  );

  /**
   * Leave a generation: let go of it first, then go back.
   *
   * Letting go is what stops the spending — the route checks whether the client
   * is still there before its next model call — and it is done here, in the
   * press, rather than when the screen unmounts, for the same reason the run is
   * started in a press: a development-mode unmount would stop a run nobody left.
   */
  const leaveTheRun = useCallback(
    (run: TheRun) => () => {
      run.letGo();
      setScreen({ at: "launchpad" });
    },
    [],
  );

  /** Ask the same question again, which is a new run and a new screen. */
  const runAgain = useCallback(
    (run: TheRun) => () => {
      run.letGo();
      setScreen({ at: "growing", run: askForAMap(run.asked) });
    },
    [],
  );

  // **One labelled row, and one quiet line.** The row is the model key, because
  // it is the one reading on this screen that changes what a reader can do — it
  // is why a sentence has a recording behind it or nothing at all. Whether the
  // server answered and which build answered are still here, in the line under
  // it, where they are traceable without being the first thing read.
  const readings = useMemo(() => [modelKeyReading(readiness)], [readiness]);
  const behind = useMemo(() => serverAndBuild(health, about), [health, about]);

  if (screen.at === "growing") {
    return (
      <GenerationScreen
        // Named by the press that asked for it, so that asking the same question
        // again draws a fresh screen rather than a second map inside the first
        // one's selection and focus.
        key={screen.run.press}
        run={screen.run}
        // Known before the stream has said anything, which is the whole reason
        // the badge can be on screen from the first frame. When the receipt
        // arrives it is the authority, and the badge takes its word.
        replaying={readiness.state === "answered" && !readiness.value.model_key_present}
        onRunAgain={runAgain(screen.run)}
        onLeave={leaveTheRun(screen.run)}
      />
    );
  }

  if (screen.at === "map") {
    return (
      <MapScreen
        base={screen.world}
        branches={screen.branches}
        source={using}
        insteadOfTheEngine={screen.insteadOfTheEngine}
        onLeave={toLaunchpad}
      />
    );
  }

  if (screen.at !== "launchpad") {
    return (
      <main className="page page--map">
        <header className="map-bar">
          <button className="map-bar__back" type="button" onClick={toLaunchpad}>
            <span aria-hidden="true">←</span> Back to the launchpad
          </button>
          <h1 className="map-bar__title">Strait of Hormuz</h1>
        </header>

        <div className="map-waiting">
          <p className="map-waiting__line">
            {screen.at === "opening"
              ? `Reading the map from /api/fixtures/${screen.id} and asking /api/worlds to work ` +
                `its likelihoods through.`
              : screen.reason}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      {/* The first screen is the one wide column in this product: it holds the
          two doors, a map that is already drawn, the four sentences from the
          brief and the field you type your own into, and stacking all of that
          in the 660-pixel measure the rest of the page reads at pushes the
          field below the fold. `launchpad.css` owns the width. */}
      <div className="column column--launchpad">
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
          readiness={readiness.state === "answered" ? readiness.value : null}
          // **An absent answer is two different facts and the screen is handed
          // both.** Without this, a readiness request that failed looked exactly
          // like one still in flight, and the first screen said *asking the
          // server* for ever over an ask that had ended — while the strip below
          // it printed the failure's own sentence. A screen asserting a question
          // that is not being asked is a state nobody can trace to an input.
          readinessFailure={readiness.state === "failed" ? readiness.reason : null}
          onOpen={open}
          onBuild={build}
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
          <p className="provenance">{behind}</p>
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
