// Throwaway: the repository's own config on ports nobody else on this machine
// is using, and starting its own servers rather than reusing whatever happens
// to be answering. Another worktree serves its branch on 8015 and 5187, which
// are the repo config's ports, and `reuseExistingServer` is true locally — so
// the repo config silently tested that branch's app instead of this one.
import { defineConfig, devices } from "@playwright/test";

const SERVER_PORT = 8072;
const APP_PORT = 5172;

export default defineConfig({
  testDir: "/Users/kentgang/git3/katalyst-wt/feat-04a-growth/frontend/e2e",
  testMatch: "generate.spec.ts",
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${APP_PORT}`,
    viewport: { width: 1600, height: 1000 },
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1000 } },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn katalyst.api.main:app --port ${SERVER_PORT}`,
      cwd: "/Users/kentgang/git3/katalyst-wt/feat-04a-growth/backend",
      url: `http://localhost:${SERVER_PORT}/api/healthz`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ANTHROPIC_API_KEY: "",
        FRED_API_KEY: "",
        KATALYST_RECORDINGS:
          "/private/tmp/claude-501/-Users-kentgang-git3-katalyst/ef0fe818-4a51-417f-a20d-5479dc442258/scratchpad/g-shots/backend/recordings",
      },
    },
    {
      command: `npm run dev -- --port ${APP_PORT} --strictPort`,
      cwd: "/Users/kentgang/git3/katalyst-wt/feat-04a-growth/frontend",
      url: `http://localhost:${APP_PORT}/`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { KATALYST_API_URL: `http://localhost:${SERVER_PORT}` },
    },
  ],
});
