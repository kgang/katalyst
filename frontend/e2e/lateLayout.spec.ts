/**
 * A map drawing itself while the thread that places its boxes starts late.
 *
 * **This is a fault put in on purpose, kept.** On 2026-09-21 the build went red
 * on its first run over something twenty cold runs on the developer's machine
 * had not shown: where the tiles go is worked out on a background thread, the
 * build machine's thread was slower to start, and the first claim to arrive took
 * the place of the rectangle that had been standing at the map's origin. The
 * growing edge went quiet — a map still arriving with nothing on it saying where
 * it was going — and a box was drawn somewhere the layout had never agreed to.
 *
 * **Throttling the processor did not reproduce it**, because that slows the page
 * and not the thread. Holding the thread's own script back for nine hundred
 * milliseconds reproduced it at once, in a build made by hand and thrown away.
 * This is that build, made permanent and made cheap: one test, twenty seconds,
 * on every run, so the condition is met by somebody who meant it rather than by
 * a slow machine at an unlucky moment.
 *
 * **Nothing in the product knows this test exists.** The delay is put on the
 * request for the layout engine's worker script, from outside the page — there
 * is no setting, no flag and no branch anywhere in `src/` that this reaches. A
 * product that had to be told to be slow would be a product whose slow path
 * nobody had ever really run.
 *
 * **What it asserts is what `generate.spec.ts` asserts**, from the same helpers
 * and about the same two promises: a rectangle stood at the growing edge every
 * step of the way, and nothing was ever drawn in another box's place. That is
 * the point — the claim is that a late layout makes the map *slower* and not
 * *wrong*, so the right statement is the ordinary one, made under the fault.
 *
 * Both tests make that statement through **one** helper, `watching.ts`'s
 * `theMapArrivedInSteps`, so neither can quietly drift into asking for
 * something the other does not.
 */

import { aDroppedFrameIsExpectedHere, expect, test } from "./theSuite.js";
import { whereTheTileSits } from "./waiting.js";
import {
  A_WHOLE_RUN,
  boxesRunningIntoEachOther,
  startWatching,
  THE_SENTENCE,
  theMapArrivedInSteps,
  waitUntilItStops,
  whatCanBeReplayed,
  whatItSaw,
} from "./watching.js";

/**
 * The row on the first screen that plays the committed recording of the one
 * sentence this file watches.
 *
 * **Two rows carry that sentence now**, since the first screen offers four ways
 * to start: *Watch the recording* plays it back for nothing, and *Run it live*
 * calls a model. So a row is named by its sentence **and** by what pressing it
 * does, which is how a reader tells the two apart as well.
 */
const THE_RECORDING_ROW = new RegExp(`${THE_SENTENCE}[\\s\\S]*Watch the recording`);

test.describe.configure({ timeout: A_WHOLE_RUN + 60_000 });

// **Every test here watches a map arrive, and a map arriving drops frames.**
// Said once for the file rather than in each test, with the whole reason, so
// that a reader who meets the browser's complaint finds the argument rather
// than a silenced warning.
test.beforeEach(() => {
  aDroppedFrameIsExpectedHere(
    "A map arriving draws its boxes in bursts, and the drawing library measures " +
      "every box it draws. When a burst is big enough the browser abandons the rest " +
      "of that frame's size notifications and says so. Measured on 2026-09-21, on " +
      "this file and with the layout thread held back and not: it comes and goes " +
      "with the size of the burst and not with anything this test injects, and at " +
      "the moment it fires the stage's and the panel's edge readings are both true " +
      "of where the boxes actually are, with no box left unpainted and no wire " +
      "missing. It is harmless here because nothing on this map waits to be " +
      "measured: `graph/toFlow.ts` declares every tile's box and both ends of every " +
      "wire, and `test_the_arrows_are_drawn_when_the_browser_drops_a_size_notification` " +
      "drops every tile's notification on purpose and the map still draws.",
  );
});

/**
 * How long the layout engine's worker script is held back, in milliseconds.
 *
 * The figure from the build made by hand on 2026-09-21, and it is chosen
 * against two bounds rather than by taste. It has to be longer than the gap
 * between two events of a replay, or the thread is not late for anything. It has
 * to be shorter than `layoutRunner.ts`'s own patience — after two seconds the
 * page gives up on the thread and lays the map out itself, which is a different
 * path and would test a different thing.
 */
const HOW_LATE = 900;

/**
 * Which request carries the layout engine's background thread.
 *
 * Matched on the script's own name rather than on a path, because where the
 * packaging puts it is the packaging's business and changes between a
 * development server and a built folder. `layoutRunner.ts` asks the bundler for
 * this file's address and hands the address to the thread; whatever address that
 * turns out to be, it ends in this name.
 *
 * **Anchored at the end, and that is the whole difference between delaying the
 * thread and delaying the app.** The development server hands the address over
 * as a little module of its own, at the same name with `?url` after it, and the
 * page loads *that* as part of its own import graph before it ever starts a
 * thread. Written without the anchor this pattern caught both — measured on
 * 2026-09-21: two held-back requests, one of them the app's own startup, which
 * is a different fault from the one this test is about. The thread's own load is
 * the bare script with nothing after it.
 */
const THE_LAYOUT_THREAD = /elk-worker[\w.-]*\.js$/;

/**
 * The other copy of the layout engine, the one that runs on the page's own
 * thread.
 *
 * `layoutRunner.ts` loads it — and only then — when the background thread has
 * not answered inside its patience, and lays the map out on the thread that
 * draws the page instead. **It must never be asked for here.** If it were, this
 * test would go on passing while testing a path its whole docstring is not
 * about: the delay above is wall-clock in this process, while the patience is a
 * budget the build machine spends about two and a half times slower, so a delay
 * that ever crossed it would quietly swap one path for the other with every
 * assertion still green.
 */
const THE_OTHER_COPY = /elk\.bundled/;

test("test_the_growing_edge_holds_when_the_layout_thread_starts_late", async ({ page }) => {
  // Held back before anything is asked for, so the very first layout is the late
  // one — which is the window that matters, the only one in which the layout has
  // placed nothing at all.
  const heldBack: string[] = [];
  const answered: string[] = [];
  const fellBack: string[] = [];
  page.on("response", (came) => {
    if (THE_LAYOUT_THREAD.test(came.url())) {
      answered.push(came.url());
    }
  });
  page.on("request", (asked) => {
    if (THE_OTHER_COPY.test(asked.url())) {
      fellBack.push(asked.url());
    }
  });
  await page.route(THE_LAYOUT_THREAD, async (route) => {
    heldBack.push(route.request().url());
    await new Promise((go) => setTimeout(go, HOW_LATE));
    await route.continue();
  });

  await page.goto("/");
  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no map to draw late.",
  );

  await startWatching(page);
  await page.getByRole("button", { name: THE_RECORDING_ROW }).click();

  // Where the first tile came to rest. Read before the run is over, so that
  // "nothing already placed moved" is a statement about a map that went on
  // growing underneath it.
  const firstTile = page.locator(".react-flow__node.react-flow__node-claim").first();
  const wasAt = await whereTheTileSits(firstTile);

  await waitUntilItStops(page);
  const claims = await page.locator(".tile").count();
  const saw = await whatItSaw(page);

  // **First: the fault was actually put in, and it is the fault this test says
  // it is.** A route that matched nothing would leave this test green while
  // testing an ordinary run — the worst kind of test, one that passes because it
  // did nothing. Three read-backs, each failing loudly with its own sentence,
  // and none of them meaning the map is unwell.
  //
  // The worker's script was asked for **exactly once** and held back once. Zero
  // would mean the bundler has renamed or inlined it and this test is delaying
  // nothing at all; more than one would mean the delay is landing somewhere
  // else, because `layoutRunner.ts` starts one thread and shares it. The URL is
  // in the message either way, because that is the thing a reader has to look at.
  expect(
    heldBack,
    `held back ${heldBack.length} request(s) instead of one: ${heldBack.join(", ") || "none"}`,
  ).toHaveLength(1);
  // It came back, so there was a background thread to be late.
  expect(answered.length, "the held-back worker script never arrived at all").toBe(1);
  // **And the background thread is the path that was taken.** The page gives up
  // on that thread and lays the map out itself when it has not answered inside
  // `layoutRunner.ts`'s patience, and every assertion below would still pass on
  // that path while testing something else entirely.
  expect(
    fellBack,
    "the page gave up on the background thread and laid the map out itself, so nothing " +
      "below is about a late thread: the delay has grown past `THREAD_PATIENCE`",
  ).toEqual([]);

  // **A rectangle stood at the growing edge every step of the way.** This is the
  // statement the build's first run broke: with the layout late, the map had no
  // place for anything, and the claim that arrived was painted where the
  // rectangle carrying the reader's own sentence had been. `graph/onTheGlass.ts`
  // is the rule that is no longer possible under — a box is drawn where the
  // layout put it and nowhere else, and a rectangle keeps saying where the next
  // claim goes until that claim is drawn.
  //
  // The last claim is the exception and the only one: the frontier empties when
  // it closes, and no rectangle may stand where nothing is coming.
  expect(saw.rectangleBeforeAnyClaim).toBe(true);
  expect(saw.firstRectangleSaid).toContain(THE_SENTENCE);

  // **The same statement `generate.spec.ts` makes, made under the fault.** Word
  // for word the same call, because that is the claim: a late layout makes the
  // map *slower*, not *wrong*. Measured here on 2026-09-21 with the thread held
  // back: eighteen claims over seventeen arrivals, one pair drawn together at
  // the moment the late thread caught up — which is the browser batching two
  // events into one render, and exactly why neither test asks for one render
  // per claim. `watching.ts` says the whole of it.
  theMapArrivedInSteps(saw, claims);

  // **And no box was ever drawn in another box's place**, which is the other
  // half of the same rule and the half a reader sees as a claim sitting on top
  // of the hypothesis.
  expect(saw.everStacked).toBe(false);
  expect(await boxesRunningIntoEachOther(page)).toEqual([]);

  // And the tile that was placed first is exactly where it was, with every other
  // claim on the map having arrived since.
  expect(await whereTheTileSits(firstTile)).toBe(wasAt);
});
