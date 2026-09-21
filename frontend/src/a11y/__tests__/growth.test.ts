/**
 * What a growing map says out loud, and how often it says it.
 *
 * The rule the whole file is about: **a live region says what changed.** It used
 * to say the whole run — where it had got to, every refusal, the last one again,
 * the verdict — on every single arrival. On the coordinator's ten-claim run that
 * is the same sentences read out ten times over, with the thing that just
 * happened arriving last, after a minute of things the reader already knew.
 *
 * Nothing here composes a sentence about a refusal or a verdict: both are read
 * out in the words their own author wrote.
 */

import { describe, expect, it } from "vitest";
import { THE_STREAM_ENDED_EARLY } from "../../components/DoneLine";
import { A_REAL_RUN, THE_REAL_SENTENCE } from "../../stream/__tests__/aRealRun";
import { BELIEFS, REFUSED, THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import type { StreamEvent } from "../../stream/events";
import type { Growth } from "../../stream/growth";
import { fold, theStreamEnded, waitingFor } from "../../stream/growth";
import { theOpeningLine, whatChanged } from "../growth";

/** Every line the region would speak, walking a whole stream in order. */
function everythingSaid(events: readonly StreamEvent[]): string[] {
  let growth: Growth = waitingFor(THE_SENTENCE, null);
  const said = [theOpeningLine(growth)];
  for (const event of events) {
    const next = fold(growth, event);
    const line = whatChanged(growth, next);
    if (line !== "") {
      said.push(line);
    }
    growth = next;
  }
  return said;
}

describe("the live region says what changed", () => {
  it("test_a_refusal_is_read_out_once_and_not_again", () => {
    const said = everythingSaid([...THE_GROWTH, BELIEFS]);
    const sentence = REFUSED.violations[0]?.message ?? "";
    expect(sentence).not.toBe("");

    // Said once, in the rule's own words, at the moment it happened — and never
    // again on any later arrival.
    const times = said.filter((line) => line.includes(sentence));
    expect(times).toHaveLength(1);
    expect(times[0]).toContain("A proposal was refused.");
  });

  it("test_every_claim_that_arrives_is_announced_by_its_own_words", () => {
    // Walked over the real ten-claim run, because the identifiers there are the
    // engine's own twenty-six characters. A fixture with single-letter names
    // cannot tell an identifier from a word that happens to contain that letter.
    let growth: Growth = waitingFor(THE_REAL_SENTENCE, null);
    let announced = 0;
    for (const event of A_REAL_RUN) {
      const next = fold(growth, event);
      const line = whatChanged(growth, next);
      if (next.world.claims.length > growth.world.claims.length) {
        const arrived = next.world.claims[next.world.claims.length - 1];
        // The claim's own words, never an identifier: on a generated map an
        // identifier is twenty-six characters of the engine's bookkeeping and a
        // reader learns nothing from one.
        expect(line).toContain("A claim arrived:");
        expect(line).toContain((arrived?.claim ?? "").slice(0, 20));
        expect(line).not.toContain(arrived?.id ?? "no id");
        announced += 1;
      }
      growth = next;
    }
    // And the walk really did watch claims arrive, or it proved nothing.
    expect(announced).toBeGreaterThan(1);
  });

  it("test_the_likelihoods_landing_is_one_line_of_its_own", () => {
    let growth: Growth = waitingFor(THE_SENTENCE, null);
    for (const event of THE_GROWTH) {
      growth = fold(growth, event);
    }
    const landed = fold(growth, BELIEFS);
    expect(whatChanged(growth, landed)).toContain("Every likelihood has been worked out");
  });

  it("test_a_stream_that_ended_early_says_so_in_the_same_words_the_page_prints", () => {
    let growth: Growth = waitingFor(THE_SENTENCE, null);
    for (const event of THE_GROWTH) {
      growth = fold(growth, event);
    }
    const ended = theStreamEnded(growth);
    const line = whatChanged(growth, ended);
    // The one sentence, shared with the line under the map, so the reader who
    // hears it and the reader who sees it are told the same thing.
    expect(line).toContain(THE_STREAM_ENDED_EARLY);
    expect(line).toContain("arrived before it did");
  });

  it("test_nothing_is_said_when_nothing_a_listener_needs_changed", () => {
    // The receipt arriving changes what is on screen and changes nothing a
    // listener has to be told about mid-run: the cost is on the strip, and the
    // run's own ending is announced by the event that ends it.
    let growth: Growth = waitingFor(THE_SENTENCE, null);
    for (const event of THE_GROWTH) {
      growth = fold(growth, event);
    }
    const withReceipt = fold(growth, {
      event: "receipt",
      model: "a model",
      calls: 1,
      input_tokens: 1,
      output_tokens: 1,
      cache_read_tokens: 0,
      searches: 0,
      dollars: 0,
      seconds: 1,
      mode: "replay",
      recording_date: "2026-09-17",
      prompt_hash: "0".repeat(32),
    });
    expect(whatChanged(growth, withReceipt)).toBe("");
  });
});
