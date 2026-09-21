/**
 * The suite's first meeting with a real silence.
 *
 * **The blind spot this closes.** Every other browser test in this folder plays
 * a recording at four tenths of a second an event, so nothing here had ever seen
 * a screen with nothing happening on it. A live run is not like that: the first
 * proposal comes back about twenty-three seconds after the press and later ones
 * fifty to a hundred and ten seconds apart, and it was in that gap that Kent
 * pressed *Watch it build* on 2026-09-21 and said *"i don't see anything
 * happening"*. The fake-timer twin
 * (`src/stream/__tests__/theRunStrip.test.tsx`) produces that gap in a simulated
 * page; this produces it in a real browser, against a real server, **with no
 * model key and at no cost** — by playing the same committed recording with the
 * pace turned up instead.
 *
 * **How the pace is turned up, and why it is not a field on the request.** The
 * server refuses one on purpose: *"pacing is presentation and nothing else,
 * which is why it is not a field on the request: a client that could ask for an
 * instant replay would let anybody who opened the network tab skip the thing the
 * recording exists to show"* (`backend/src/katalyst/engine/replay.py`). It is one
 * setting, read from the environment. So this file runs against a **second pair
 * of servers on ports of their own**, started by `playwright.config.ts` with a
 * long pace, and it is the only file that runs in that project. Nothing on the
 * server changed.
 *
 * **What it asserts, and what it deliberately does not.** A replay shows no
 * seconds — at any pace we set, the reading would be measuring our own pacing
 * rather than a wait — so this does not look for a count. What it holds is the
 * thing Kent could not see: through a silence long enough to sit in front of,
 * the foot of the screen is **visible** and says, in words, what is being waited
 * for. Nothing spins while it does.
 */

import type { Page } from "@playwright/test";
import { expect, test } from "./theSuite.js";
import { THE_SENTENCE, whatCanBeReplayed } from "./watching.js";

/**
 * How long a gap this test insists on seeing.
 *
 * It is shorter than the pace the servers are started at, so that the whole of
 * this window is inside one gap however slowly the page loads. The pace itself
 * is in `playwright.config.ts`, beside the server that reads it.
 */
const A_SILENCE = 3_000;

test("the foot of the screen says what is happening through a real silence", async ({
  page,
}: {
  page: Page;
}) => {
  await page.goto("/");

  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no generation to watch.",
  );

  const card = page.getByRole("button", { name: new RegExp(THE_SENTENCE) });
  await card.click();

  // The run has started: the first event says so and is sent before any model
  // call, so it arrives at once. Nothing else will arrive for seconds.
  const strip = page.locator(".run-strip");
  const sentence = strip.locator(".map-live");
  await expect(strip).toBeVisible();
  await expect(sentence).toBeVisible();
  await expect(sentence).toHaveAttribute("aria-live", "polite");
  await expect(sentence).toContainText(THE_SENTENCE);
  await expect(sentence).toContainText("held open");

  // **Now sit in the gap.** Nothing is waited for and nothing is polled: the
  // page is simply left alone for longer than a reader would give it before
  // deciding the tool is broken.
  const before = ((await sentence.textContent()) ?? "").trim();
  const claimsBefore = await page.locator(".tile").count();
  await page.waitForTimeout(A_SILENCE);

  // The screen is a still picture, and it is still saying what it is doing —
  // which is the whole of what this test is for. Before 2026-09-21 this element
  // was a one-pixel box with its contents clipped away, and a browser test
  // asserted that it was.
  expect(await page.locator(".tile").count(), "the gap was not a gap").toBe(claimsBefore);
  await expect(sentence).toBeVisible();
  expect(((await sentence.textContent()) ?? "").trim()).toBe(before);
  await expect(strip).toHaveAttribute("data-state", "replay");

  // A replay shows no seconds, at any pace: the number would be measuring our
  // own pacing rather than a wait.
  await expect(page.locator(".run-strip__waited")).toHaveCount(0);

  // And nothing spins, anywhere, at any point in the silence.
  await expect(page.getByRole("progressbar")).toHaveCount(0);

  // Then the map goes on growing: the silence was a pace, not a stall.
  await expect(page.locator(".tile")).toHaveCount(claimsBefore + 1, { timeout: 30_000 });
  await expect(sentence).toContainText("A claim arrived:");
  // And the sentence names what the run is working on next, from the frontier
  // the event itself carried.
  await expect(sentence).toContainText("Working on what follows from");

  // Let the run go rather than leaving the server to play the whole recording
  // out at this pace. The press is what stops it, exactly as it is for a reader.
  await page.getByRole("button", { name: /Back to the launchpad/ }).click();
});
