/**
 * How the end-to-end tests run.
 *
 * They drive the real app in a real browser against the real server. Everything
 * else about this product is checked by tests that need neither — the rules of
 * the map in the server's own suite, the components in a simulated page. These
 * exist for the things neither can check: that the two halves, started as a
 * person would start them, actually draw the stored example and the recorded
 * one; that a mouse alone can do the thing the product is for; and that nothing
 * in the panel beside the map is cut off at any window this interface is held
 * to.
 *
 * **Both halves are started here rather than by hand**, so that running it is
 * one command and so that the build job is the same command. The server is
 * started on a port of its own and the browser app is told where to find it, the
 * same way the packaged app is told.
 *
 * **No model key, anywhere.** The screen this test drives is fed by
 * `GET /api/fixtures/hormuz`, which is a stored example: it calls no model and
 * needs no key. The whole suite passes with nothing configured, which is the
 * rule the build is held to, and the environment below is written out in full so
 * that nothing is inherited by accident.
 */

import { defineConfig, devices } from "@playwright/test";
import {
  assertPortsAreFree,
  BACKEND_PORT,
  FRONTEND_PORT,
  SLOW_BACKEND_PORT,
  SLOW_FRONTEND_PORT,
} from "./e2e/ports.js";

/**
 * **Both ports come from the environment, and nothing is ever reused.**
 *
 * Several worktrees of this repository are often open on one machine and every
 * one of them wants these two numbers. Playwright's `reuseExistingServer` is
 * worse than a collision: it attaches to whatever is answering, so a run in one
 * worktree tests the branch checked out in another and reports it green. That
 * has happened here, in both directions, and neither side could tell from the
 * output. So the defaults are the numbers continuous integration has always
 * used, `KATALYST_E2E_BACKEND_PORT` and `KATALYST_E2E_FRONTEND_PORT` override
 * them, and `e2e/ports.ts` stops the run before the first test if either is
 * taken — naming the port and the variable that moves it.
 */
const SERVER_PORT = BACKEND_PORT;
const APP_PORT = FRONTEND_PORT;

/**
 * **The one test that watches a recording play slowly, and the file it lives
 * in.**
 *
 * Every other test here plays a recording at four tenths of a second an event,
 * which is why this suite had never met a silence — and a live run is fifty to a
 * hundred and ten seconds between events. How fast a replay plays is one setting
 * read from the environment and deliberately not a field on the request
 * (`backend/src/katalyst/engine/replay.py` says why in its own words), so the
 * only way to give one test a different pace without touching the server is a
 * second server, with a second browser app pointed at it, on ports of their own.
 *
 * That is what the project and the two extra web servers below are. Nothing on
 * the server side changed, no model key is involved and nothing is spent.
 */
const THE_SLOW_ONE = "**/slowReplay.spec.ts";

/**
 * How slowly that one server plays a recording back, in seconds between events.
 *
 * The shipped product is six tenths of a second and the rest of this suite is
 * four. Eight is chosen for a margin rather than for the number itself: the test
 * sits out three seconds of one gap, and the rest is room for the page to load
 * and the first assertions to run before that window opens — so a slow machine
 * still spends the whole window inside one gap. The test is over in about twelve
 * seconds, which is what the longest test in this suite already costs, and it
 * runs beside the others.
 */
const A_SLOW_PACE = "8";

// Asked before anything is started, because nothing later is early enough.
assertPortsAreFree();

export default defineConfig({
  testDir: "./e2e",
  // Run once. A retry would hide a flake, and a flake in a test that drives two
  // servers is a fault worth seeing.
  retries: 0,
  /**
   * **Every test runs beside every other**, rather than one file at a time.
   *
   * Left alone, Playwright runs files in parallel and the tests inside one file
   * in order — and five of this suite's tests watch a whole recording play at
   * the server's own pace, four of them in one file. Run in order they are four
   * waits end to end; run side by side they are one.
   *
   * **They may be**, and it is the server that decides. Each viewing of a
   * recording mints an identifier of its own, so **each viewing's transcript is
   * its own** and two people watching the same recording no longer overwrite
   * each other's working; the process holds eight generations and never drops
   * one still streaming, so five at once sit inside the bound with room; and the
   * stored example's routes — a map, a world, a difference — are pure functions
   * of the request body and keep nothing between calls.
   *
   * **One thing is shared, and it is named rather than glossed over.** Beside
   * each transcript the process keeps an index from a map's identifier back to
   * the generation that built it (`engine/transcript.py`), and every replay of
   * one recording builds a map with the same identifier — so five concurrent
   * replays are last-writer-wins on that one entry. It is harmless here for a
   * reason worth writing down rather than trusting: all five build the identical
   * map, and no end-to-end test asks the world routes for a generated map. The
   * day one does, this is the line to come back to.
   */
  fullyParallel: true,
  /**
   * How many browsers at once: five here, two on the build machine.
   *
   * **Five is the long pole on the suite as it stands.** Fourteen tests, of
   * which five watch a whole recording play — the four in `generate.spec.ts` and
   * the one in `lateLayout.spec.ts` — at about twelve seconds each. The other
   * nine are the stored example's and none has ever run for more than four
   * seconds, though four of them ask for budgets of two minutes: three measure
   * the panel whole at a window of their own, and one opens a branch and retunes
   * an arrow under a report. Five is what it takes to have every recording in
   * flight at once; a sixth browser would have only short tests left to overlap,
   * on a machine that is often shared.
   *
   * **The build machine gets two, and nothing has been measured on four cores.**
   * That number is reasoning rather than a reading: the runner has four cores to
   * this machine's fourteen, and the layout runs on a background thread that has
   * to answer between two events of a replay — leaving it no core to answer on
   * is precisely the condition that produced the layout race of 2026-09-21,
   * twenty clean runs here and red on the build's first.
   *
   * **And what actually changed for the build is not the worker count.** It
   * already ran this suite's two files side by side, so it already used two
   * browsers. What is new is that both of them can be watching a recording at
   * the same time: replay concurrency there goes from one to two. That is the
   * thing to look at if the build ever turns red on timing.
   */
  workers: process.env.CI ? 2 : 5,
  // Long enough for the layout engine's background thread to answer twice —
  // once for the map and once for the branch — on a slow build machine.
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${APP_PORT}`,
    // The window the whole interface is designed against. Every measurement in
    // the visual review was taken at this size.
    viewport: { width: 1600, height: 1000 },
    /**
     * **A trace is kept for every test that fails, and for no test that
     * passes.**
     *
     * This was `off`, and two failures in this suite were lost last week with
     * nothing kept about either of them: a line of output, no screen, no
     * network, no console, nothing to look at afterwards. A browser test that
     * fails on a machine nobody is sitting at and leaves no evidence has to be
     * reproduced before it can be read, and reproducing a rare one is the
     * expensive half of chasing it.
     *
     * **What it costs, said plainly**: a trace is recorded for every test,
     * pass or fail — the recording is the only way to have one if it fails —
     * and the ones that passed are deleted at the end. So a green run pays the
     * recording (a few per cent of the wall clock, and disk that is freed
     * again) and uploads nothing, and a red one keeps the whole of the
     * evidence. `on` would keep the green ones too: megabytes uploaded on every
     * build and opened by nobody. Worth it either way — two failures were lost
     * last week for want of this line.
     */
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      // The window last, on purpose: the device preset carries one of its own,
      // and the whole interface was measured against this one.
      use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1000 } },
      // Every file but the slow one, which needs a server paced differently and
      // gets the project below.
      testIgnore: THE_SLOW_ONE,
    },
    {
      // The same browser and the same window, pointed at the pair of servers
      // that plays a recording slowly — so that one test meets a real silence.
      name: "chromium-slow-replay",
      testMatch: THE_SLOW_ONE,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1600, height: 1000 },
        baseURL: `http://localhost:${SLOW_FRONTEND_PORT}`,
      },
    },
  ],
  webServer: [
    {
      // The Python half, from its own directory, with the two keys it might have
      // inherited explicitly unset. It needs neither: the stored example is a
      // file on disk.
      command: `uv run uvicorn katalyst.api.main:app --port ${SERVER_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${SERVER_PORT}/api/healthz`,
      // Never reused. A run that attaches to somebody else's server tests
      // somebody else's branch and says it was yours.
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ANTHROPIC_API_KEY: "",
        FRED_API_KEY: "",
        // **The replay stays paced, and the pace is shortened rather than
        // turned off.**
        //
        // **What the pace is for, now that it is for one thing.** The first
        // claim `generate.spec.ts` makes is that a reserved rectangle stood on
        // screen before any claim had arrived — the first paint is the shape of
        // the thing being waited for and not a spinner. That moment is exactly
        // one gap wide: it opens when `generation_started` paints the rectangle
        // and closes when the first `proposal_accepted` paints a claim. With no
        // pause at all the two land in one tick, React draws them in one render,
        // and the moment never exists to be seen. So the pace has to be
        // comfortably longer than one render on the slowest machine that runs
        // this, and that is the whole of its job.
        //
        // **What it is no longer for.** Until 2026-09-21 these tests also asked
        // for one render per claim — `heldWhenEachClaimArrived` holding exactly
        // as many entries as the map has claims. A browser makes no such
        // promise: React gathers whatever has landed since the last frame into
        // one render, so two events close together paint once. Measured that
        // day, running `generate.spec.ts` four browsers at a time on this
        // fourteen-core machine, twice at each pace: 0.40 and 0.25 green 8 of 8;
        // 0.15, 0.08 and 0.04 red on that assertion **and on nothing else**, at
        // 17, 14 and 17 arrivals for 18 claims; 0.02 red with the whole run
        // folded into a single change. The pace was holding up a statement about
        // the browser's scheduling rather than about the product. That statement
        // is gone — `watching.ts` says what replaced it and why — and the promise
        // that events leave the server one at a time is tested on the server's
        // own clock, where it can be tested honestly.
        //
        // **0.4 stays, and is now a generous margin on a weak requirement.** It
        // is not tuned to anything: one gap has to outlast one render, and four
        // tenths of a second is far more than that on any machine this runs on.
        // Coming down to 0.25 would save about four seconds of a twenty-four
        // second run and buy back a tail — two events fold whenever the main
        // thread happens to be busy longer than the gap, a garbage collection or
        // a loaded runner, and folding is only harmless because nothing asks
        // about it any more.
        //
        // The other reason the pace cannot go to nothing is the layout, which
        // runs on a background thread and has to answer between two events. It
        // is no longer the only thing holding that together: `onTheGlass.ts`
        // holds the growing edge's rectangle when the layout has placed nothing,
        // so a late answer is a slower map rather than a wrong one — and
        // `e2e/lateLayout.spec.ts` starts that thread nine hundred milliseconds
        // late on purpose, on every run, to keep it that way. That test is also
        // the joint-longest in this suite at about twelve seconds, so on the
        // build machine, at two workers, it costs roughly what the shortened
        // pace saves. It is worth it: what it buys is the one failure twenty
        // local runs did not find.
        KATALYST_REPLAY_PACE: "0.4",
      },
    },
    {
      // The browser half, told where the server is exactly as the packaged app
      // is told.
      command: `npm run dev -- --port ${APP_PORT} --strictPort`,
      url: `http://localhost:${APP_PORT}/`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { KATALYST_API_URL: `http://localhost:${SERVER_PORT}` },
    },
    {
      // **The second pair, for the one test that needs a real silence.**
      //
      // The same server, the same recordings, the same empty keys — one setting
      // apart. Pacing is not a field on the request and must not become one, so
      // a test that wants a different pace needs a process that was started with
      // one.
      command: `uv run uvicorn katalyst.api.main:app --port ${SLOW_BACKEND_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${SLOW_BACKEND_PORT}/api/healthz`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ANTHROPIC_API_KEY: "",
        FRED_API_KEY: "",
        KATALYST_REPLAY_PACE: A_SLOW_PACE,
      },
    },
    {
      // And its browser app, pointed at it. The address the app forwards `/api`
      // to is read when the development server starts, so one app cannot serve
      // two servers.
      command: `npm run dev -- --port ${SLOW_FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${SLOW_FRONTEND_PORT}/`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { KATALYST_API_URL: `http://localhost:${SLOW_BACKEND_PORT}` },
    },
  ],
});
