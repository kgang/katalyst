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
 * **Nothing here spins, pulses or sweeps.** The only thing that changes between
 * two events is a count of seconds, and it changes because time passed. That is
 * a measurement, not a movement: motion may carry information and may never
 * stand in for it.
 */

import { type ReactNode, useEffect, useRef, useState } from "react";
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
   * **Null turns it off**, and three screens want it off. A stored map is not
   * waiting for anything. A finished run is not waiting for anything. And a
   * **replay** is paced by the server, at six tenths of a second an event, so
   * the reading would reset twice a second and would be measuring our own pacing
   * rather than any wait.
   */
  readonly arrivals: number | null;
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

/** How the reading reads. One word for the state, then the seconds. */
export function nothingNewFor(seconds: number): string {
  return `nothing new for ${seconds} s`;
}

/** What the run is doing, in one strip, at the foot of the map. */
export function RunStrip({ word, saying, arrivals, after }: RunStripProps) {
  const seconds = useSecondsOfSilence(arrivals);

  return (
    <div className="run-strip" data-state={word}>
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
  );
}
