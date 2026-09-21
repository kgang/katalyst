/**
 * Reading one request as a stream of events.
 *
 * The reader is given bytes and hands back the eight shapes a `switch` can walk.
 * Everything below drives it with bytes written the way the wire writes them —
 * split in the middle of a line where a real read would split, because that is
 * the case a reader written against whole lines gets wrong.
 */

import { describe, expect, it } from "vitest";
import type { GenerateRequest, ReadEvent } from "../events";
import { eventIn, generate, joined, wholeBlocks } from "../generate";
import { fold, waitingFor } from "../growth";
import { THE_SENTENCE } from "./aStream";

/** One `event:` and `data:` block, written the way the wire writes one. */
function block(name: string, payload: unknown): string {
  return `event: ${name}\ndata: ${JSON.stringify(payload)}\n\n`;
}

/** A fetch that answers with these pieces of body, in this order. */
function answering(pieces: readonly string[], status = 200): typeof globalThis.fetch {
  return ((_address: string, options?: RequestInit) => {
    sent.push(options?.body === undefined ? null : String(options.body));
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const piece of pieces) {
          controller.enqueue(new TextEncoder().encode(piece));
        }
        controller.close();
      },
    });
    return Promise.resolve(
      new Response(status === 200 ? body : null, {
        status,
        headers: { "content-type": "text/event-stream" },
      }),
    );
  }) as typeof globalThis.fetch;
}

/** Every body the reader sent, so a test can say what was and was not in one. */
const sent: (string | null)[] = [];

/** Read a whole stream into a list. */
async function everything(
  pieces: readonly string[],
  request: GenerateRequest = { hypothesis: THE_SENTENCE },
): Promise<ReadEvent[]> {
  const read: ReadEvent[] = [];
  for await (const event of generate(request, { fetch: answering(pieces) })) {
    read.push(event);
  }
  return read;
}

describe("joining a name to a payload", () => {
  it("test_the_name_comes_off_the_event_line_and_the_payload_off_the_data_line", () => {
    // On the wire the payload carries no name at all: the reader puts it there,
    // which is what makes the eight a union a switch can walk.
    const read = eventIn(
      block("done", { reason: "reached_terminal", claims: 6, links: 6, rejected: 1 }),
    );
    expect(read).toEqual({
      event: "done",
      reason: "reached_terminal",
      claims: 6,
      links: 6,
      rejected: 1,
    });
  });

  it("test_a_block_split_in_the_middle_is_put_back_together", () => {
    // A read from the network stops wherever it stops. What is left after the
    // last blank line is kept and joined to the next read.
    const whole = block("generation_started", {
      generation_id: "g",
      seed: 1,
      hypothesis: "s",
      target: null,
    });
    const { blocks, rest } = wholeBlocks(whole.slice(0, 20));
    expect(blocks).toEqual([]);
    expect(wholeBlocks(rest + whole.slice(20)).blocks).toHaveLength(1);
  });

  it("test_a_block_split_across_two_reads_reaches_the_reducer_whole", async () => {
    // The same case, driven through `generate` itself rather than through the
    // splitting alone — because the joining is only right if the generator is
    // the thing doing it, and a test of the helper leaves the generator free to
    // hand the halves on separately and draw a map from half a claim.
    const whole =
      block("generation_started", {
        generation_id: "g",
        seed: 3,
        hypothesis: THE_SENTENCE,
        target: null,
      }) + block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 });
    // A cut in the middle of the first payload, which is where a real read cuts.
    const cut = 30;
    const read = await everything([whole.slice(0, cut), whole.slice(cut)]);

    expect(read.map((one) => one.event)).toEqual(["generation_started", "done"]);
    expect(read[0]).toMatchObject({ hypothesis: THE_SENTENCE, generation_id: "g" });
  });

  it("test_a_wire_that_ends_its_lines_the_other_way_is_read_the_same", async () => {
    // Our own server writes `\n`; the format allows `\r\n`, and a proxy that
    // rewrites line endings on the way past is not something this browser gets
    // to rule out. A reader that knew one spelling would find no blocks at all
    // and draw an empty map from a stream that was perfectly correct.
    const written = (
      block("generation_started", {
        generation_id: "g",
        seed: 3,
        hypothesis: THE_SENTENCE,
        target: null,
      }) + block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 })
    ).replaceAll("\n", "\r\n");

    const read = await everything([written]);
    expect(read.map((one) => one.event)).toEqual(["generation_started", "done"]);
  });
});

describe("an event name this build does not know", () => {
  it("test_an_unknown_event_name_is_ignored_and_reported", async () => {
    const read = await everything([
      block("generation_started", {
        generation_id: "g",
        seed: 7,
        hypothesis: THE_SENTENCE,
        target: null,
      }),
      block("a_call_went_out", { about: "H" }),
      block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 }),
    ]);

    // Nothing threw, and nothing was dropped: the name came back as a name.
    expect(read.map((one) => one.event)).toEqual(["generation_started", "unknown", "done"]);
    expect(read[1]).toEqual({ event: "unknown", name: "a_call_went_out" });

    // And the reducer counts it and changes nothing else.
    const folded = read.reduce(fold, waitingFor(THE_SENTENCE, null));
    expect(folded.unknown.get("a_call_went_out")).toBe(1);
    expect(folded.done?.reason).toBe("reached_terminal");
  });

  it("test_a_payload_that_cannot_be_read_is_counted_rather_than_thrown", () => {
    expect(joined("receipt", "{not json")).toEqual({ event: "unknown", name: "receipt" });
  });
});

describe("what the browser asks for", () => {
  it("test_i_dont_know_sends_no_likelihood_at_all", async () => {
    sent.length = 0;
    await everything([
      block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 }),
    ]);

    const body = JSON.parse(sent[0] ?? "{}") as Record<string, unknown>;
    // Not a half, not a wide band, not a null that something downstream reads as
    // a half: the field is simply not there.
    expect("user_belief" in body).toBe(false);
    expect(body.hypothesis).toBe(THE_SENTENCE);
  });

  it("test_the_browser_invents_no_seed", async () => {
    sent.length = 0;
    await everything([
      block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 }),
    ]);

    const body = JSON.parse(sent[0] ?? "{}") as Record<string, unknown>;
    expect("seed" in body).toBe(false);
  });

  it("test_the_readers_own_number_is_named_as_theirs", async () => {
    sent.length = 0;
    const belief = { p: 0.55, lo: 0.4, hi: 0.7 };
    await everything(
      [block("done", { reason: "reached_terminal", claims: 0, links: 0, rejected: 0 })],
      { hypothesis: THE_SENTENCE, user_belief: belief },
    );

    const body = JSON.parse(sent[0] ?? "{}") as { user_belief?: Record<string, unknown> };
    // The three numbers are the reader's, untouched; the owner is a label rather
    // than a number, and it is the one thing the browser writes.
    expect(body.user_belief).toEqual({ ...belief, owner: "user" });
  });
});

describe("a request that never reached the route", () => {
  it("test_a_route_that_never_answered_is_one_plain_sentence", async () => {
    const reading = generate({ hypothesis: THE_SENTENCE }, { fetch: answering([], 503) });
    await expect(reading.next()).rejects.toThrow(/may not be running/);
  });
});
