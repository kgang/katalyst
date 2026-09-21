/**
 * The one strip at the foot of a map that says what is happening to it.
 *
 * **What it replaced.** The foot of a generating map used to carry three
 * stacked strips of prose and none of them was about the run: what the last
 * keystroke did, a live region clipped to a one-pixel box, and a line naming the
 * route, the generation and the seed — written from the run's first event, over
 * a map with nothing on it. So the one sentence that said what the run was doing
 * was spoken to a screen reader and never printed, and a reader who pressed the
 * button and watched nothing happen for twenty-three seconds had no way at all
 * to tell a working tool from a broken one.
 *
 * Now there is one strip: the state as a single word, then the run's own
 * sentence — the same sentence the screen reader hears — and, only while a live
 * run is open, how long it has been since anything arrived.
 *
 * **The sentence is the live region.** Not a copy of it, the region itself, so
 * the two can never drift apart again. It keeps saying what *changed*, which is
 * what a polite region is for.
 *
 * **The reading sits beside the region and never inside it.** A number that
 * ticks inside a polite region is announced once a second, which is a reader
 * being read a stopwatch instead of a map. It is plain text either way — never
 * hidden from a screen reader, just never announced.
 *
 * **And under all of it, on a live run, at most two quiet lines saying what the
 * model is doing this second** *(added 2026-09-22, Kent's R44 and R47)*: the
 * search it just issued or what that search returned, and its own summarised
 * thinking, labelled as its own words. They are outside the live region for the
 * same reason the seconds are and more so — they change every few seconds, and a
 * polite region that read them out would be reading a stopwatch over the top of
 * the map being built. A replay is given none: a recording holds no such line,
 * so there is nothing to replay, which is the difference a replay already makes
 * for the seconds.
 *
 * **Nothing here spins, pulses or sweeps.** The only thing that changes between
 * two events is a count of seconds, and it changes because time passed. That is
 * a measurement, not a movement: motion may carry information and may never
 * stand in for it. The two quiet lines are words arriving, which is the same
 * kind of thing: they say what is happening rather than that something is.
 */

import { type ReactNode, useEffect, useRef, useState } from "react";
import type { ActivityLine, WhatTheModelIsDoing } from "../stream/growth";
import "./runStrip.css";

/** What the strip needs. */
export interface RunStripProps {
  /**
   * The state, as one word, in the mono box the foot already uses: `live`,
   * `replay`, `finished`, `stored`, `asking`, `stopped`, `ended early`.
   */
  readonly word: string;
  /**
   * The one sentence about the run, said out loud and printed. Empty says
   * nothing rather than saying nothing loudly.
   */
  readonly saying: string;
  /**
   * How many events have arrived, or nothing at all when this strip counts no
   * seconds.
   *
   * A **number** turns the reading on: it prints how long it has been since
   * anything last arrived, and it starts again whenever this number changes.
   * It is on while the screen is waiting on the server — a live run between two
   * events, or a stored map whose world has been asked for and not come back.
   *
   * **Null turns it off**, and three states want it off. A stored map at rest is
   * not waiting for anything. A finished run is not waiting for anything. And a
   * **replay** is paced by us, at six tenths of a second an event, so the
   * reading would reset twice a second and would be measuring our own pacing
   * rather than any wait.
   */
  readonly arrivals: number | null;
  /**
   * What the model is doing right now, or nothing at all when this strip says
   * nothing about it.
   *
   * **Nothing is the answer for every screen but one.** A replay has none to
   * show — a recording never holds one — a stored map is not calling anything,
   * and a run that has stopped has nothing out. Only a live run that is still
   * open passes this, and when it does, the room for two lines is held open
   * whether or not either of them has anything in it yet, so that a line
   * arriving or going does not shove the map up and down the page.
   */
  readonly doing?: WhatTheModelIsDoing | null;
  /** Anything the screen wants at the end of the strip: counts, an offer. */
  readonly after?: ReactNode;
}

/**
 * How long it has been since the last arrival, in whole seconds, by the
 * browser's own clock.
 *
 * **It is a measurement of silence, never an estimate of what is left.** There
 * is no percentage, no bar and no "about a minute left": the caps a remaining
 * time would have to be divided by are the server's and are not on the wire.
 *
 * @param arrivals How many events have arrived, or null to count nothing. The
 *   clock starts again every time the number changes.
 * @returns The seconds, or null when there is nothing to count.
 */
function useSecondsOfSilence(arrivals: number | null): number | null {
  const since = useRef(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (arrivals === null) {
      return;
    }
    // The clock starts again here, on every arrival, which is the whole of what
    // "reset by every arrival" means.
    since.current = Date.now();
    setSeconds(0);
    // One tick a second, and the reading is worked out from the clock rather
    // than by adding one to itself — a browser that throttles a background tab
    // would otherwise count slower than the wait it is measuring.
    const tick = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - since.current) / 1000));
    }, 1000);
    return () => {
      window.clearInterval(tick);
    };
  }, [arrivals]);

  return arrivals === null ? null : seconds;
}

/**
 * How the reading reads. One word for the state, then the seconds.
 *
 * **It says *on the map*, and that is not padding** *(the words were widened
 * 2026-09-22)*. From the day the strip could also print what the model is doing
 * inside a call, *nothing new* on its own was ambiguous and, on a busy call,
 * false: a search line had just changed in front of the reader. What the number
 * has always measured is how long it has been since something reached the
 * **map**, which is the question a reader waiting two minutes is actually
 * asking, and the words now say so.
 */
export function nothingNewFor(seconds: number): string {
  return `nothing new on the map for ${seconds} s`;
}

/**
 * How long a line the strip prints before it cuts one.
 *
 * It is the length the server already cuts its own thinking line to, so the
 * browser is cutting only what the server did not — a query or a title that ran
 * long — rather than second-guessing it. Long enough that a whole search query
 * and most whole sentences arrive intact.
 */
const ENOUGH_OF_A_LINE = 160;

/**
 * One line's worth of the model's words, cut at a word if it runs long.
 *
 * **Cut at a word, closed with an ellipsis, never through the middle of one** —
 * the same rule a claim's own shortening obeys. The stylesheet holds the other
 * half of the promise: each line is exactly one line high whatever arrives, so
 * the strip can never grow past two extra lines and push the map up the page.
 *
 * @param text The model's own words, as they arrived.
 */
function inOneLine(text: string): string {
  const tidy = text.trim();
  if (tidy.length <= ENOUGH_OF_A_LINE) {
    return tidy;
  }
  const cut = tidy.slice(0, ENOUGH_OF_A_LINE);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > 0 ? cut.slice(0, lastSpace) : cut).replace(/[,;:.]$/, "")}…`;
}

/**
 * The fixed words each kind of line is printed with.
 *
 * They are fixed because they are the whole of what this browser adds: the text
 * after them is the model's, verbatim, and the words before them say which of
 * three things it is. The thinking line names whose words they are every time it
 * is drawn, because it is the one line here about a mind rather than about a
 * fact with a source.
 *
 * @param line What the model said, and which kind of saying it was.
 */
export function asALine(line: ActivityLine): string {
  const text = inOneLine(line.text);
  switch (line.kind) {
    case "searching":
      return `searching the web: "${text}"`;
    case "found":
      return `found: ${text}`;
    case "thinking":
      return `the model, in its own words: ${text}`;
  }
}

/** What the run is doing, in one strip, at the foot of the map. */
export function RunStrip({ word, saying, arrivals, doing, after }: RunStripProps) {
  const seconds = useSecondsOfSilence(arrivals);
  const quiet = doing ?? null;

  return (
    <div className="run-strip" data-state={word}>
      <div className="run-strip__line">
        {/* A word rather than a glyph, in the same box the last-key line uses: a
            mark that has to survive every typeface says less than the word does. */}
        <span className="run-strip__mark">{word}</span>

        {/* Said out loud for a reader who is not looking at the picture, and
            printed for one who is — one element, so there is no second copy to
            drift. Polite: it waits for a pause rather than cutting across
            whatever is being read. */}
        <p className="map-live run-strip__saying" aria-live="polite">
          {saying}
        </p>

        {after}

        {seconds === null ? null : (
          // Outside the live region on purpose. Plain text, reachable, never
          // announced.
          <span className="run-strip__waited">{nothingNewFor(seconds)}</span>
        )}
      </div>

      {quiet === null ? null : (
        // **Outside the live region, and the room is held whether or not there
        // is anything to put in it.** Both lines are drawn on every live run:
        // an empty one is an empty line rather than no line, so a search
        // arriving or a claim clearing one changes the words and never the
        // height, and the map above does not jump every few seconds.
        <div className="run-strip__doing">
          <span className="run-strip__doing-line">
            {quiet.searching === null ? "" : asALine(quiet.searching)}
          </span>
          <span className="run-strip__doing-line">
            {quiet.thinking === null ? "" : asALine(quiet.thinking)}
          </span>
        </div>
      )}
    </div>
  );
}
