// Throwaway: run the generation browser test against the already-running app on
// 5143, which proxies to the stream half's server on 8043 with a recording in it.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "/Users/kentgang/git3/katalyst-wt/feat-04a-growth/frontend/e2e",
  testMatch: "generate.spec.ts",
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: "http://localhost:5143", viewport: { width: 1600, height: 1000 }, trace: "off" },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1000 } },
    },
  ],
});
