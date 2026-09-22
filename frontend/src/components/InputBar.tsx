/**
 * The way in: type a sentence, and watch what it would cause.
 *
 * **Three fields, one button, and no more.**
 *
 *   1. The sentence — the hypothesis, in the reader's own words.
 *   2. Where it ends, optional. This is the Verify door, and it is **one extra
 *      field rather than a second screen**.
 *   3. The reader's own likelihood, with an explicit *I don't know* state.
 *
 * **The button is "Build the map", word for word, on both doors.** Not
 * *Generate*, which is the pipeline's word rather than the reader's, and not
 * *Explore* or *Verify*, which are the two doors and are already named by whether
 * the second field has anything in it — a button whose label changed as the
 * reader typed would be a control that moved under them.
 *
 * **"I don't know" is a state of the control, not a value.** It is where the
 * control starts, and while it holds, the request carries **no** likelihood at
 * all — not a `.5`, not a null that something downstream treats as a half. A reader who has not said what they think has not said what they
 * think, and a tool that fills that in for them has invented the one number it
 * had no business inventing.
 *
 * **With no model key the bar is visibly disabled and says why**, in the same
 * sentence the launchpad carries. Never silently inert: a field that takes typing
 * and then does nothing reads as a broken tool, where a field that says why reads
 * as an unfinished one, and only one of those is true.
 *
 * Nothing here computes anything. The number the slider holds is the one the
 * reader put there, and the guard that stops the control posting a certainty is
 * a bound on the track.
 *
 * **It was three handles and is one** *(Kent, 2026-09-22, R48)*: a likelihood,
 * the bottom of a range and the top. The range is cut from this product, so the
 * bar asks for the likelihood.
 */

import { useId, useState } from "react";
import type { Likelihood } from "../world";
import { toTwoFigures } from "./BeliefChip";
import "./inputBar.css";

/** What a reader asked for when they pressed the button. */
export interface Asked {
  /** The sentence they typed. Never empty: the button does not work without one. */
  readonly hypothesis: string;
  /** Where they said it ends, or nothing at all on the Explore door. */
  readonly target: string | null;
  /**
   * Their own likelihood, or nothing at all while the control is on *I don't
   * know*. Nothing at all is not a half.
   */
  readonly belief: Likelihood | null;
  /**
   * How the run starts: `live` calls a model, `replay` plays the committed
   * recording of this sentence back. Absent leaves it to the route's own default,
   * which is a recording.
   *
   * Not something this bar draws. It is set by whoever assembles the press,
   * because **the server no longer reads the key to choose** (record 0012,
   * amended 2026-09-21) — and when the first screen offers the choice, this is
   * the field the reader's press fills in.
   */
  readonly start?: "replay" | "live";
}

/** What the bar needs to draw itself. */
export interface InputBarProps {
  /**
   * Why nothing can be built from a sentence right now, in one sentence, or null
   * when it can.
   *
   * It is read from the server's own answer about itself rather than written into
   * the page, so the reason on screen is the real one.
   */
  readonly disabledBecause: string | null;
  /** Start a generation. */
  readonly onBuild: (asked: Asked) => void;
}

/**
 * The bottom and the top of the track.
 *
 * A likelihood of exactly 1 is a certainty, and this product does not print one:
 * the chip prints `>.99` instead, and a control that could post a `1.0` would
 * make that guard a lie about where the number came from. So the track stops one
 * step short at each end, and every step on it is a two-significant-figure value.
 */
const FLOOR = 0.01;
const CEILING = 0.99;
const STEP = 0.01;

/** Where the handle starts, once the reader turns the control on. */
const OPENING: Likelihood = { p: 0.5 };

/** Keep the number on the track: never a certainty at either end. */
function onTheTrack(belief: Likelihood): Likelihood {
  return { p: Math.min(CEILING, Math.max(FLOOR, belief.p)) };
}

/** The way in. */
export function InputBar({ disabledBecause, onBuild }: InputBarProps) {
  const sentenceId = useId();
  const targetId = useId();
  const [hypothesis, setHypothesis] = useState("");
  const [target, setTarget] = useState("");
  // Null is *I don't know*, and it is where the control starts. It is a state of
  // the control rather than a value, so it is held as the absence of one.
  const [belief, setBelief] = useState<Likelihood | null>(null);
  const off = disabledBecause !== null;
  const ready = hypothesis.trim() !== "";

  const handle = (over: Partial<Likelihood>): void => {
    setBelief((was) => onTheTrack({ ...(was ?? OPENING), ...over }));
  };

  return (
    <form
      className="input-bar"
      data-disabled={off ? "yes" : "no"}
      onSubmit={(event) => {
        event.preventDefault();
        if (off || !ready) {
          return;
        }
        onBuild({
          hypothesis: hypothesis.trim(),
          target: target.trim() === "" ? null : target.trim(),
          belief,
        });
      }}
    >
      <div className="input-bar__field">
        <label className="input-bar__label" htmlFor={sentenceId}>
          An event you think will happen
        </label>
        <input
          className="input-bar__text"
          id={sentenceId}
          type="text"
          autoComplete="off"
          disabled={off}
          placeholder="The Strait of Hormuz is going to open next week."
          value={hypothesis}
          onChange={(event) => setHypothesis(event.target.value)}
        />
      </div>

      <div className="input-bar__field">
        <label className="input-bar__label" htmlFor={targetId}>
          Where you think it ends — optional
        </label>
        <input
          className="input-bar__text"
          id={targetId}
          type="text"
          autoComplete="off"
          disabled={off}
          placeholder="A Polymarket contract on Brent below $70"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
        />
        <p className="input-bar__hint">
          Fill this in and the map is graded against it: the route, or a plain statement that none
          reaches it.
        </p>
      </div>

      <fieldset className="input-bar__belief" disabled={off}>
        <legend className="input-bar__label">How likely you think it is</legend>

        {belief === null ? (
          <div className="input-bar__unsaid">
            <p className="input-bar__reading" data-reading="unsaid">
              I don&rsquo;t know
            </p>
            <p className="input-bar__hint">
              Nothing is sent for this. A number put here for you would be the one number on the map
              nobody asked for.
            </p>
            <button
              className="input-bar__say"
              type="button"
              onClick={() => setBelief(onTheTrack(OPENING))}
            >
              Give my own number
            </button>
          </div>
        ) : (
          <div className="input-bar__track">
            <p className="input-bar__reading" data-reading="said">
              {toTwoFigures(belief.p)}
            </p>
            <label className="input-bar__handle">
              <span className="input-bar__handle-name">how likely</span>
              <input
                type="range"
                min={FLOOR}
                max={CEILING}
                step={STEP}
                value={belief.p}
                onChange={(event) => handle({ p: Number(event.target.value) })}
              />
            </label>
            <p className="input-bar__hint">
              Your own number sits beside the model&rsquo;s and a market&rsquo;s, and is never
              averaged with them.
            </p>
            <button className="input-bar__say" type="button" onClick={() => setBelief(null)}>
              Back to &ldquo;I don&rsquo;t know&rdquo;
            </button>
          </div>
        )}
      </fieldset>

      <div className="input-bar__go">
        <button className="input-bar__build" type="submit" disabled={off || !ready}>
          Build the map
        </button>
        {off ? (
          <p className="input-bar__why">{disabledBecause}</p>
        ) : ready ? null : (
          <p className="input-bar__why">
            Type an event above and this builds a map of what it would cause.
          </p>
        )}
      </div>
    </form>
  );
}
