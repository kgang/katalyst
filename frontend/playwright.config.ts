/**
 * How the one end-to-end test runs.
 *
 * There is one job and it drives the real app in a real browser against the real
 * server. Everything else about this product is checked by tests that need
 * neither — the rules of the map in the server's own suite, the components in a
 * simulated page. These exist for the thing neither can check: that the two
 * halves, started as a person would start them, actually draw the stored
 * example, that a mouse alone can do the thing the product is for, and that
 * nothing in the panel beside the map is cut off at any window this interface
 * is held to.
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
import { assertPortsAreFree, BACKEND_PORT, FRONTEND_PORT } from "./e2e/ports.js";

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

// Asked before anything is started, because nothing later is early enough.
assertPortsAreFree();

export default defineConfig({
  testDir: "./e2e",
  // One test, run once. A retry would hide a flake, and a flake in a test that
  // drives two servers is a fault worth seeing.
  retries: 0,
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
        // **The replay's pacing is left on, and that is deliberate.**
        //
        // `KATALYST_REPLAY_INSTANT` exists so a test need not wait out a delay
        // that is there for a reviewer's benefit, and for most tests it would be
        // free. It is not free here: `generate.spec.ts`'s whole subject is a map
        // *arriving* — a rectangle standing before any claim, the growing edge
        // moving, the chips resolving last and once — and with the pacing off
        // every event lands in one tick, React folds them into one render, and
        // the screen goes straight from nothing to a finished map. There is then
        // no moment at which the thing being tested is true, and the test fails
        // saying it could not find a rectangle. Turning the pacing off to make a
        // test faster would be turning off the behaviour the test is for.
        //
        // It costs seconds: the whole suite runs in about twenty.
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
  ],
});
