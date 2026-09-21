/**
 * The suite's own `test`, and the one thing it holds every browser test to that
 * no assertion inside a test would ever catch.
 *
 * **The browser complains in the log, and a log is not a test.** When too many
 * size observations fall due in one frame, the browser abandons the rest of them
 * and says so — *"ResizeObserver loop completed with undelivered notifications"*.
 * The development server forwards it, and it scrolls past among the rest of the
 * output while every test goes on passing. Three of them went past in one run on
 * 2026-09-21 and nothing anywhere went red.
 *
 * That exact message was the root of a real defect in this stack: the drawing
 * library draws nothing it has not measured, so an abandoned notification left a
 * tile invisible and its arrows off the glass for the life of the page
 * (`graph/toFlow.ts` tells the whole story). That harm is prevented at the root
 * now — every tile's box and both ends of every wire are **declared**, so nothing
 * waits to be measured — but two things on screen still read sizes that arrive
 * this way: the rule at the stage's edges and the rules at the panel's. A
 * dropped notification there is a rule that lies until the next change.
 *
 * So: **a test that meets this message fails, and says so in the browser's own
 * words** — unless it has said out loud that it expects one, and why.
 *
 * Every browser test in this folder takes its `test` from here rather than from
 * the library, so that there is no way to write one that quietly does not have
 * this.
 *
 * **Why the page is asked rather than the driver.** The obvious way to catch
 * this is `page.on("pageerror")`, and it does not work: measured on 2026-09-21
 * against a loop caused on purpose, Chromium does not deliver this one to the
 * driver as a page error at all. It is delivered to the page, as an `error`
 * event on `window`, which is how the development server sees it — so that is
 * where this listens, installed before anything else runs. What it finds is kept
 * in the page's own session store rather than in a variable, so that a test that
 * reloads the page does not lose what happened before the reload.
 */

import { test as playwrights } from "@playwright/test";

/** What the browser says when it has abandoned a frame's size notifications. */
const THE_BROWSER_GAVE_UP = "ResizeObserver loop";

/** Where the page keeps what it heard, across a reload. */
const KEPT_UNDER = "katalyst.theBrowserGaveUp";

/** How a test records that it expects one, and why. */
const EXPECTED = "expects a dropped frame of size notifications";

/**
 * Say that this test expects the browser to abandon a frame's size
 * notifications, and why that is harmless here.
 *
 * **The reason is the point, not the permission.** It is written into the test's
 * own record, so a reader who meets the message later finds the argument for why
 * it was allowed rather than a warning somebody silenced.
 *
 * @param why What it is about this test that makes a dropped frame expected, and
 *   what makes it harmless.
 */
export function aDroppedFrameIsExpectedHere(why: string): void {
  playwrights.info().annotations.push({ type: EXPECTED, description: why });
}

export const test = playwrights.extend<{ theBrowsersOwnComplaints: undefined }>({
  theBrowsersOwnComplaints: [
    async ({ page }, andThen) => {
      await page.addInitScript(
        ([marker, where]) => {
          window.addEventListener("error", (it) => {
            if (!String(it.message).includes(marker)) {
              return;
            }
            try {
              const heard = JSON.parse(window.sessionStorage.getItem(where) ?? "[]") as string[];
              heard.push(String(it.message).slice(0, 160));
              window.sessionStorage.setItem(where, JSON.stringify(heard));
            } catch {
              // A page with no session store of its own tells us nothing, and
              // must not fail the test it is watching.
            }
          });
        },
        [THE_BROWSER_GAVE_UP, KEPT_UNDER] as const,
      );

      // The fixture carries nothing — it only listens — and the library's type
      // wants that nothing handed over by name.
      await andThen(undefined);

      // **Asked of the page while it is still open.** This fixture is built on
      // `page`, so it is taken down before `page` is, which is the one moment
      // the question can still be answered.
      let complaints: string[] = [];
      try {
        complaints = await page.evaluate((where) => {
          try {
            return JSON.parse(window.sessionStorage.getItem(where) ?? "[]") as string[];
          } catch {
            return [];
          }
        }, KEPT_UNDER);
      } catch {
        // A test that never opened the app, or one whose page has already gone,
        // has nothing to answer with.
        return;
      }

      const said = playwrights.info().annotations.find((one) => one.type === EXPECTED);
      if (complaints.length === 0 || said !== undefined) {
        return;
      }
      throw new Error(
        `The browser abandoned a frame's size notifications ${complaints.length} time(s) ` +
          "during this test, and this test did not say it expected that:\n\n" +
          `    ${complaints.join("\n    ")}\n\n` +
          "The drawing library draws nothing it has not measured, and the rules at the " +
          "stage's and the panel's edges are read from sizes that arrive this way — so a " +
          "dropped frame can leave a box unpainted or a rule saying something untrue " +
          "until the next change. Find what resized what; or, if it is expected here, " +
          "call `aDroppedFrameIsExpectedHere` and say why it is harmless.",
      );
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
