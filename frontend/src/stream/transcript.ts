/**
 * The working of one generation, read back after the map is drawn.
 *
 * A map is the answer; the transcript is the working. Every proposal, accepted or
 * refused, in the order it happened, with the rules' own sentences beside the
 * ones that were refused — and the lines where the model said a part of the story
 * was finished, which make no event on the stream because nothing about the map
 * changed, and which are the one thing a reader would otherwise never see.
 *
 * **Typed by hand, like the eight events, and for the same reason**: the server's
 * description of itself and this canvas are built at the same time. A later pull
 * request pins the two against each other.
 *
 * **It lives for the life of the server process.** There is no storage in this
 * stack, so a restart is enough to lose one — and when that has happened the
 * route says so in a plain sentence, which is printed as it came rather than
 * turned into an empty section a reader would read as a run that proposed
 * nothing.
 */

import type { Violation } from "./events";
import { transcriptAddress } from "./generate";

/** One thing that was proposed, and what happened to it. */
export interface TranscriptLine {
  /**
   * Where this sits on the stream, counting from 0 across accepted and refused
   * proposals together. **Null on a line that made no event**, which is how the
   * gaps in the stream's numbering are explained.
   */
  readonly at: number | null;
  /** What happened to it. Three kinds of line and no others. */
  readonly what: "accepted" | "refused" | "stopped";
  /** The claim the call was asking about, when it was asking about one. */
  readonly about: string | null;
  /** What the model wrote: the claim, the arrow's reason, or the sentence closing a line. */
  readonly in_words: string;
  /** Every reason the map's own rules gave, in their words. Empty unless refused. */
  readonly violations: readonly Violation[];
}

/** The whole working of one generation, in the order it happened. */
export interface Transcript {
  readonly generation_id: string;
  readonly hypothesis: string;
  readonly target: string | null;
  readonly seed: number;
  /** The day this generation ran, which is its map's day zero. */
  readonly on: string;
  readonly mode: "live" | "replay";
  readonly lines: readonly TranscriptLine[];
}

/** How the working turned out to be readable, or the plain reason it was not. */
export type Working =
  | { readonly state: "reading" }
  | { readonly state: "read"; readonly transcript: Transcript }
  | { readonly state: "gone"; readonly reason: string };

/**
 * Read the working of one generation back.
 *
 * @param generationId The identifier the stream's first event carried.
 * @param ask The function that makes the request. The browser's own by default.
 */
export async function readTranscript(
  generationId: string,
  ask: typeof globalThis.fetch = globalThis.fetch,
): Promise<Working> {
  const address = transcriptAddress(generationId);
  let answer: Response;
  try {
    answer = await ask(address);
  } catch {
    return {
      state: "gone",
      reason: `Could not reach the server at ${address}. It may not be running.`,
    };
  }
  if (!answer.ok) {
    // The server's own sentence when it no longer holds this generation, printed
    // as it came. A transcript lives for the life of the process that made it.
    const body = (await answer.json().catch(() => null)) as { detail?: unknown } | null;
    const said = typeof body?.detail === "string" ? body.detail : null;
    return {
      state: "gone",
      reason:
        said ??
        `The working of this run could not be read at ${address}. The reply was numbered ${answer.status}.`,
    };
  }
  // **A 200 is not a promise that the body is the working.** A proxy answering
  // for a server that is not there, a login page where an API used to be, a
  // half-written body from a connection that dropped: each of those is a 200
  // whose body is not JSON. Reading one without a guard leaves the panel saying
  // *Reading the working…* for as long as the tab is open, which is the one
  // sentence on that screen that is then false.
  const body = (await answer.json().catch(() => null)) as Transcript | null;
  if (body === null || !Array.isArray(body.lines)) {
    return {
      state: "gone",
      reason:
        `The working of this run came back from ${address} in a shape this build cannot read. ` +
        `Nothing here guesses at what it said.`,
    };
  }
  return { state: "read", transcript: body };
}
