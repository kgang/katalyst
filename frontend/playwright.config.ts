/**
 * How the one end-to-end test runs.
 *
 * There is exactly one, and it drives the real app in a real browser against
 * the real server. Everything else about this product is checked by tests that
 * need neither — the rules of the map in the server's own suite, the components
 * in a simulated page. This one exists for the thing neither can check: that the
 * two halves, started as a person would start them, actually draw the stored
 * example.
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

/** The port the server answers on while this test runs. */
const SERVER_PORT = 8015;

/** The port the browser app is served on while this test runs. */
const APP_PORT = 5187;

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
    trace: "off",
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
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ANTHROPIC_API_KEY: "",
        FRED_API_KEY: "",
        // **A replay is paced on purpose, and a test is the one place that
        // pacing is not wanted.** The delay exists so that a reviewer watching a
        // recording sees a map arrive rather than appear — a replay that raced
        // would teach them the product is faster than it is — and it is fixed on
        // the server precisely so that no client can ask to skip it. A test run
        // is not a client: it sets the setting, in the environment, where the
        // person running the suite can see it.
        //
        KATALYST_REPLAY_INSTANT: "true",
      },
    },
    {
      // The browser half, told where the server is exactly as the packaged app
      // is told.
      command: `npm run dev -- --port ${APP_PORT} --strictPort`,
      url: `http://localhost:${APP_PORT}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { KATALYST_API_URL: `http://localhost:${SERVER_PORT}` },
    },
  ],
});
