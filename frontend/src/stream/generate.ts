/**
 * The one place the browser asks for a map and reads it as it is built.
 *
 * **One request, read as a stream, and never an `EventSource`.** Two reasons,
 * both hard. The request carries a body — the sentence, an optional destination,
 * the reader's own likelihood, a seed — and an `EventSource` can only send a GET
 * with no body. And an `EventSource` reconnects by itself, which would silently
 * re-run a generation and spend the money twice. The wire format is still
 * server-sent events — an `event:` line naming the event and a `data:` line
 * carrying one JSON object — so the whole thing stays readable in a terminal.
 *
 * **The `event` field is put there by this reader, not by the server.** On the
 * wire the name is the `event:` line and the payload is the `data:` line, so the
 * payload itself carries no name. Joining them is what makes the nine a live run
 * may send — the eight a recording holds and the ephemeral `activity` — a union
 * a `switch` can walk, and it is the one place a name this build does not know
 * can be caught.
 *
 * **No component talks to the network.** Everything on screen is fed by the
 * reducer this generator hands events to.
 *
 * What this file must never do
 * ----------------------------
 * - Never invent a seed, a likelihood or any other number. It writes down what
 *   the reader typed and nothing else.
 * - Never retry. A generation that ran twice would spend twice.
 * - Never throw on an event name it does not know, and never drop one either.
 */

import type { Activity, GenerateRequest, ReadEvent, StreamEvent } from "./events";
import { NAMES_A_LIVE_RUN_MAY_SEND } from "./events";

/** Where a generation is asked for. Relative, like every other address in this app. */
export const GENERATE_ADDRESS = "/api/generate";

/** Where one claim a reader asked for is drafted. */
export const INSERT_ADDRESS = "/api/generate/insert";

/** Where the working of a generation is read back. */
export function transcriptAddress(generationId: string): string {
  return `/api/generate/${generationId}/transcript`;
}

/** What the reader can be given instead of the real thing, for a test. */
export interface HowToAsk {
  /**
   * The function that makes the request. The browser's own by default; a test
   * hands in one that answers from a string.
   */
  readonly fetch?: typeof globalThis.fetch;
  /** Stop the run when this says so — what a reader leaving the page sets. */
  readonly signal?: AbortSignal;
}

/**
 * Turn the request the screen made into the body the route takes.
 *
 * Two things happen here and nothing else. A field the reader left out is left
 * out — **"I don't know" sends no likelihood at all**, not a `.5` and not a
 * null, because a reader who has not said what they think has not said what they
 * think. And the reader's own likelihood is named as theirs, which is a label
 * rather than a number: the number in it is the one the slider handed over,
 * untouched.
 *
 * **The route still asks for a bottom and a top, and there is no longer either**
 * *(2026-09-22, R48)*. The reader gives one number, so the bottom and the top
 * sent with it are that same number: a range of nothing, which is what "one
 * likelihood, no range" is when it has to be written in the old shape. It is
 * the reader's own number in all three places and nothing is invented. Both
 * fields go when the engine half lands.
 *
 * `start` follows the same rule as the rest: sent when the caller said, left out
 * when they did not. Left out, the server plays a recording.
 *
 * @param request What the screen asked for.
 */
function bodyOf(request: GenerateRequest): Record<string, unknown> {
  const body: Record<string, unknown> = { hypothesis: request.hypothesis };
  if (request.target !== undefined && request.target !== "") {
    body.target = request.target;
  }
  if (request.user_belief !== undefined) {
    const { p } = request.user_belief;
    body.user_belief = { p, lo: p, hi: p, owner: "user" };
  }
  if (request.seed !== undefined) {
    body.seed = request.seed;
  }
  if (request.start !== undefined) {
    body.start = request.start;
  }
  return body;
}

/**
 * Is this a name this build knows — one of the eight a recording holds, or the
 * ephemeral ninth a live run may send?
 */
function isKnown(name: string): name is (StreamEvent | Activity)["event"] {
  return (NAMES_A_LIVE_RUN_MAY_SEND as readonly string[]).includes(name);
}

/**
 * Join one `event:` name and one `data:` payload into the shape the reducer
 * folds.
 *
 * A name this build does not know comes back as the one extra shape, so that
 * nothing throws and nothing is silently dropped: a browser that crashes on a new
 * event makes the server unable to add one, and a browser that swallows one makes
 * a missing feature look like a working one.
 *
 * @param name The name from the `event:` line.
 * @param data The single line of JSON from the `data:` line.
 */
export function joined(name: string, data: string): ReadEvent {
  if (!isKnown(name)) {
    return { event: "unknown", name };
  }
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    // A payload this reader cannot read is a name it cannot act on, so it is
    // counted and nothing is changed — the same handling as a name this build
    // does not know, and **not the same sentence**. The name was one of the
    // eight: this build knows what a `done` is and could not read the one that
    // arrived, which means the map may be missing something, where an unknown
    // name means only that the server has learned a word since this build was
    // made. `growth.ts` keeps them apart.
    return { event: "unknown", name, unreadable: true };
  }
  const joinedOn = { ...(payload as object), event: name } as ReadEvent;
  if (joinedOn.event !== "generation_started") {
    return joinedOn;
  }
  // The seed, as its digits rather than as what JavaScript made of them. A whole
  // number longer than sixteen digits is already rounded by the time `JSON.parse`
  // hands it back, and the seed is printed under every map so a reader can ask
  // for the same one again — so a rounded seed is a number on screen that is
  // simply wrong. Nothing computes with it; it is read off the wire and printed.
  const digits = /"seed"\s*:\s*(-?\d+)/.exec(data)?.[1];
  return digits === undefined ? joinedOn : { ...joinedOn, seed_as_written: digits };
}

/**
 * Split whatever has arrived so far into whole wire blocks, keeping the tail.
 *
 * A server-sent-events block is its lines followed by a blank line, and a read
 * from the network stops wherever it stops — often halfway through a line. So
 * whatever is left after the last blank line is kept and joined to the next read.
 *
 * **A blank line is two of them, or two of the other kind.** Our own server
 * writes `\n`, and the format allows `\r\n`; a proxy or a tunnel that rewrites
 * line endings on the way past is not a thing this browser gets to rule out, and
 * a reader that only knew one spelling would hand back no blocks at all and draw
 * an empty map from a stream that was perfectly correct.
 *
 * @param buffer Everything read and not yet handed on.
 * @returns The whole blocks, and what is left over.
 */
export function wholeBlocks(buffer: string): { blocks: string[]; rest: string } {
  const parts = buffer.split(/\r?\n\r?\n/);
  const rest = parts.pop() ?? "";
  return { blocks: parts.filter((block) => block.trim() !== ""), rest };
}

/**
 * Read one wire block into an event, or nothing when it carries no name.
 *
 * @param block One block: an `event:` line, a `data:` line, and nothing else.
 */
export function eventIn(block: string): ReadEvent | null {
  let name: string | null = null;
  const payload: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      name = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      payload.push(line.slice("data:".length).trim());
    }
  }
  return name === null ? null : joined(name, payload.join(""));
}

/**
 * One plain sentence for a request that never got as far as the stream.
 *
 * It is the sentence the screen prints, so it says what was asked for and where,
 * and never a status code a reader would have to look up.
 */
function couldNotAsk(status: number): string {
  if (status === 502 || status === 503 || status === 504) {
    return `Nothing answered at ${GENERATE_ADDRESS} — the server may not be running.`;
  }
  return (
    `The request to ${GENERATE_ADDRESS} did not start a generation. The reply was ` +
    `numbered ${status}.`
  );
}

/**
 * Ask for a map and hand back every event as it arrives.
 *
 * The generator ends when the stream ends. A run that broke ends with a `failed`
 * event carrying one plain sentence rather than by throwing — a refusal, a cap
 * and a breakage are all things that happened, and the screen draws all three.
 * The one thing that does throw is never reaching the route at all, because then
 * there is no stream to read and nothing to draw.
 *
 * @param request The sentence, and everything optional beside it.
 * @param how Where to make the request, and what stops it. Left out, the
 *   browser's own.
 */
export async function* generate(
  request: GenerateRequest,
  how: HowToAsk = {},
): AsyncGenerator<ReadEvent> {
  const ask = how.fetch ?? globalThis.fetch;
  let answer: Response;
  try {
    answer = await ask(GENERATE_ADDRESS, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(bodyOf(request)),
      ...(how.signal === undefined ? {} : { signal: how.signal }),
    });
  } catch {
    throw new Error(`Could not reach the server at ${GENERATE_ADDRESS}. It may not be running.`);
  }
  if (!answer.ok || answer.body === null) {
    throw new Error(couldNotAsk(answer.status));
  }

  const lines = answer.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await lines.read();
      if (value !== undefined) {
        buffer += value;
        const { blocks, rest } = wholeBlocks(buffer);
        buffer = rest;
        for (const block of blocks) {
          const event = eventIn(block);
          if (event !== null) {
            yield event;
          }
        }
      }
      if (done) {
        break;
      }
    }
    // Whatever is left when the stream ends, in case the last block arrived
    // without its blank line. Dropping it would drop a `done` or a `receipt`.
    const last = eventIn(buffer);
    if (last !== null) {
      yield last;
    }
  } finally {
    // A reader that has walked away stops the run: the route checks whether the
    // client is still there before its next model call, so letting go of the
    // stream is what stops the spending.
    await lines.cancel().catch(() => undefined);
  }
}
