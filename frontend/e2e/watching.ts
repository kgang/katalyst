/**
 * Watching a map arrive, and reading back what the screen did while it moved.
 *
 * **A growing map needs one thing a finished one does not**: several of the
 * claims made about it are about *moments*. *A rectangle stood before any claim
 * had arrived*, *a rectangle stood at the growing edge every step of the way*,
 * *the claims arrived one at a time*, *no likelihood appeared until the map was
 * whole* — each is true at some moments and false at others, and by the time an
 * assertion has been written the moment it was about is gone. Polling for one of
 * them races the run; asserting after it is over asserts about the wrong moment.
 *
 * So the page watches itself. Every change to the page is looked at — which is
 * every moment the screen was different — and what was on it is written down.
 * Nothing here sleeps, and nothing here can miss a moment a poll would have
 * stepped over.
 *
 * They live in a file of their own because **two** browser tests play a
 * recording and read the record back: `generate.spec.ts`, which watches an
 * ordinary run, and `lateLayout.spec.ts`, which watches one whose layout thread
 * was made to start late. A helper copied into a second file is a second helper:
 * the day one of them learns about a new way the screen can lie, only one test
 * would learn it.
 */

import { expect, type Page } from "@playwright/test";

/** The sentence the first screen's first card carries, as a reader would type it. */
export const THE_SENTENCE = "The Strait of Hormuz is going to open next week.";

/**
 * How long a whole run is allowed to take before a test gives up on it.
 *
 * **A replay takes as long as its recording**, because the pacing is the
 * server's and the number of events is the file's — a twenty-proposal run is
 * four times the twenty seconds a five-proposal one takes, and neither number
 * is a test's to know. So the bound below is not a measurement and is not tuned
 * to a machine: it is generous on purpose, and exists only so that a run which
 * has genuinely stopped fails as a test rather than hanging.
 *
 * The default fifteen seconds is the wrong bound for exactly one thing —
 * waiting for a run to finish — and the right one everywhere else, so it is
 * named here and used there.
 */
export const A_WHOLE_RUN = 120_000;

/** What watching a whole run saw. */
export interface WhatItSaw {
  /** True when, at some moment, a rectangle stood and not one claim had arrived. */
  readonly rectangleBeforeAnyClaim: boolean;
  /**
   * The words on the first rectangle, read at a moment when no claim had
   * arrived — so it is the one held open for the reader's own sentence and not
   * one of the frontier's, which carry *one step on from "…"*.
   *
   * Empty when no such moment was seen.
   */
  readonly firstRectangleSaid: string;
  /** The most rectangles that stood at once. */
  readonly mostRectangles: number;
  /**
   * True when, at some moment, two boxes on the map stood in the same place.
   *
   * The place they would share is the map's origin, where the hypothesis is:
   * a box the layout has not placed yet used to be drawn there, so every
   * arriving claim sat on top of the first one until the layout answered.
   */
  readonly everStacked: boolean;
  /**
   * How many rectangles stood at the moment each claim arrived, in order.
   *
   * The growing edge saying where the map is going, step by step, rather than
   * only at the start. **The last entry is allowed to be none**: the frontier
   * empties when the last claim closes, and no rectangle may stand where
   * nothing is coming.
   */
  readonly heldWhenEachClaimArrived: readonly number[];
  /**
   * How many claims were on the map, every time that number changed.
   *
   * The sequence rather than the largest of them: the largest is whatever the
   * map ended up with, which is a fact about the end and says nothing at all
   * about how the map got there. A map that appeared all at once and a map that
   * grew claim by claim have the same largest number and completely different
   * sequences.
   */
  readonly claimsWentOn: readonly number[];
  /**
   * How many claims were on the map the first time any likelihood appeared, and
   * how many appeared at that moment.
   *
   * Both are zero when none ever did. Together they are the statement that the
   * chips resolve **last** and **once**: the first number arrives when the map
   * is complete, and every other number arrives in the same breath.
   */
  readonly whenTheNumbersCame: { readonly claims: number; readonly numbers: number };
}

/** Where the page keeps what it has seen of itself. */
declare global {
  interface Window {
    theRecord?: WhatItSaw & { rectangleBeforeAnyClaim: boolean };
    stopWatching?: () => void;
  }
}

/**
 * What this copy of the server says it can play back without a key.
 *
 * Asked of the server rather than read off the screen: whether a test has
 * anything to do at all is a fact about the server, and reading it off the page
 * would make the skip depend on the very screen being tested.
 *
 * @param page The page to ask from, so the question goes to the server this run
 *   started and to no other.
 */
export async function whatCanBeReplayed(page: Page): Promise<{ example: string }[]> {
  const answer = await page.request.get("/api/readyz");
  const said = (await answer.json()) as { replayable?: { example: string }[] };
  return said.replayable ?? [];
}

/**
 * Have the page start watching itself, before anything is asked for.
 *
 * **It is installed before the press**, and awaited, so that the very first
 * frame of the run is inside the record. Starting it after the press leaves the
 * one moment the first assertion is about — a rectangle standing with no claim
 * beside it — outside the window being watched, on a fast replay.
 *
 * @param page The page the map will be on.
 */
export async function startWatching(page: Page): Promise<void> {
  await page.evaluate(() => {
    const record = {
      rectangleBeforeAnyClaim: false,
      firstRectangleSaid: "",
      mostRectangles: 0,
      everStacked: false,
      heldWhenEachClaimArrived: [] as number[],
      claimsWentOn: [] as number[],
      whenTheNumbersCame: { claims: 0, numbers: 0 },
    };
    window.theRecord = record;

    const look = (): void => {
      const held = document.querySelectorAll(".skeleton-tile").length;
      const claims = document.querySelectorAll(".tile").length;
      // A chip says on its own face whether it is showing a number or words,
      // and that is the marker to count: every chip renders a reading, and on
      // a growing map most of them are reading an absence out.
      const numbers = document.querySelectorAll('.belief-chip[data-reading="number"]').length;

      if (held > 0 && claims === 0) {
        record.rectangleBeforeAnyClaim = true;
        // **Read here, and never again from the live page.** What the first
        // rectangle says is true of one moment: the moment after it is drawn
        // and before the first claim replaces it with the frontier's. Reading
        // it in a second round trip asks a screen that has moved on — and on a
        // cold machine the whole run can finish in between, so the rectangle is
        // not merely different, it is gone.
        record.firstRectangleSaid = document.querySelector(".skeleton-tile")?.textContent ?? "";
      }
      record.mostRectangles = Math.max(record.mostRectangles, held);
      if (record.claimsWentOn[record.claimsWentOn.length - 1] !== claims) {
        // What the growing edge was saying at the moment this claim arrived.
        if (claims > 0) {
          record.heldWhenEachClaimArrived.push(held);
        }
        record.claimsWentOn.push(claims);
      }
      // Two boxes in one place. The place they would share is the map's origin,
      // where a box the layout has not placed yet used to be drawn.
      const places = [...document.querySelectorAll(".react-flow__node")].map(
        (one) => (one as HTMLElement).style.transform,
      );
      if (new Set(places).size !== places.length) {
        record.everStacked = true;
      }
      if (numbers > 0 && record.whenTheNumbersCame.numbers === 0) {
        record.whenTheNumbersCame = { claims, numbers };
      }
    };

    const watching = new MutationObserver(look);
    window.stopWatching = () => watching.disconnect();
    watching.observe(document.body, { subtree: true, childList: true, attributes: true });
    look();
  });
}

/**
 * Stop watching, and read back what the page saw of itself.
 *
 * **It waits for nothing.** The waiting is done by the named signals around it,
 * which is where a test that has to give up belongs: a watcher that settled on a
 * signal of its own would hang until the whole test timed out on a run that
 * broke, and the failure a reader saw would be *"test timed out"* rather than
 * *"the run said it failed"*.
 *
 * @param page The page the map is on.
 */
export async function whatItSaw(page: Page): Promise<WhatItSaw> {
  return await page.evaluate(() => {
    window.stopWatching?.();
    return window.theRecord as WhatItSaw;
  });
}

/**
 * Wait until the run is over, which is the receipt arriving and the map saying
 * why it stopped.
 *
 * Two signals rather than one, because they are two events: the receipt is what
 * the run cost and the closing line is why it ended, and a screen that had the
 * first and not the second would be read here as finished when it is not.
 *
 * **This is the one wait with a bound of its own**, and it is the one that needs
 * one: everything else is waiting for the page to catch up with something that
 * has already happened, where fifteen seconds is generous. This waits for a
 * whole recording to play, which takes as long as the recording is — see
 * `A_WHOLE_RUN`.
 *
 * @param page The page the map is on.
 */
export async function waitUntilItStops(page: Page): Promise<void> {
  await expect(page.locator(".receipt-strip")).toBeVisible({ timeout: A_WHOLE_RUN });
  await expect(page.locator(".done-line")).toBeVisible({ timeout: A_WHOLE_RUN });
  // Every rectangle goes when the likelihoods land: the set of claims still open
  // is empty by definition once the map is finished.
  await expect(page.locator(".skeleton-tile")).toHaveCount(0);
}

/**
 * Assert that the map **arrived in steps**, with the growing edge saying where
 * it was going at every one of them.
 *
 * **What this deliberately does not say: one render per claim.** It used to.
 * `heldWhenEachClaimArrived` has one entry per *moment the screen changed*, not
 * one per claim, and those are not the same thing — React gathers whatever has
 * landed since the last frame into a single render, so two events that arrive
 * close together paint once and the two claims they carried appear together.
 * That is the browser doing its job. Demanding one entry per claim was demanding
 * that the page never batch, which no browser promises and this product never
 * claimed: it held only while the server's pause between events was comfortably
 * longer than one render, so it was really a statement about the pace, and it
 * went red the moment the pace came down or a machine got busy.
 *
 * **Where the one-at-a-time promise really lives.** That the events leave the
 * server one at a time, rather than as one collected body, is a promise about
 * the stream (FR-5), and it is tested where it can be tested honestly — on the
 * server's own clock, in
 * `backend/tests/api/test_the_stream_is_not_buffered.py` ›
 * `test_the_events_of_a_replay_are_let_go_of_one_at_a_time`.
 *
 * **What is asserted here is what the map promises** (INV-workbench.79, which
 * names this very record): the map arrived over time rather than all at once;
 * the count of claims on screen only ever went up, one changed moment at a time,
 * from none to all of them; and **a reserved rectangle stood at every arrival
 * but the last**, which is the growing edge never going quiet about where the
 * map is going. The last arrival is the exception and the only one: the frontier
 * empties when the final claim closes, and no rectangle may stand where nothing
 * is coming.
 *
 * @param saw What the page recorded about itself while the map was arriving.
 * @param claims How many claims the finished map has, counted off the screen.
 */
export function theMapArrivedInSteps(saw: WhatItSaw, claims: number): void {
  // Over time, not at once. One arrival would be a map that appeared.
  expect(
    saw.heldWhenEachClaimArrived.length,
    `the map arrived in ${saw.heldWhenEachClaimArrived.length} step(s), which is not arriving`,
  ).toBeGreaterThan(1);
  // And never more arrivals than there are claims, which would mean the count
  // had gone up and come back down — a claim leaving the map.
  expect(saw.heldWhenEachClaimArrived.length).toBeLessThanOrEqual(claims);

  // From none to all of them, and never backwards or sideways. A map that
  // redrew itself would have gone down somewhere; a count written down twice
  // would mean a moment was recorded that was not a change at all.
  expect(saw.claimsWentOn[0]).toBe(0);
  expect(saw.claimsWentOn[saw.claimsWentOn.length - 1]).toBe(claims);
  for (const [step, count] of saw.claimsWentOn.slice(1).entries()) {
    expect(
      count,
      `the claims on screen went ${saw.claimsWentOn.join(", ")}, which is not a map growing`,
    ).toBeGreaterThan(saw.claimsWentOn[step] as number);
  }

  // **A rectangle stood at every arrival but the last.** This is the statement
  // the build broke on 2026-09-21: with the layout late the map had no place for
  // anything, the arriving claim was painted where the rectangle carrying the
  // reader's own sentence had been, and the growing edge went quiet.
  expect(saw.mostRectangles).toBeGreaterThan(0);
  for (const [step, held] of saw.heldWhenEachClaimArrived.slice(0, -1).entries()) {
    expect(held, `no rectangle stood when arrival ${step + 1} was drawn`).toBeGreaterThan(0);
  }
}

/**
 * Every pair of boxes on the map that overlap. Empty is the only right answer.
 *
 * @param page The page the map is on.
 */
export async function boxesRunningIntoEachOther(page: Page): Promise<string[]> {
  return await page.locator(".react-flow__node").evaluateAll((boxes) => {
    const seen = boxes.map((box) => ({
      id: (box as HTMLElement).dataset.id ?? "?",
      at: box.getBoundingClientRect(),
    }));
    const found: string[] = [];
    for (let one = 0; one < seen.length; one += 1) {
      for (let other = one + 1; other < seen.length; other += 1) {
        const a = seen[one];
        const b = seen[other];
        if (
          a !== undefined &&
          b !== undefined &&
          a.at.left < b.at.right &&
          b.at.left < a.at.right &&
          a.at.top < b.at.bottom &&
          b.at.top < a.at.bottom
        ) {
          found.push(`${a.id} runs into ${b.id}`);
        }
      }
    }
    return found;
  });
}
