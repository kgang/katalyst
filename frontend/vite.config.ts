/**
 * How the browser app is built, served in development, and tested.
 *
 * The one thing worth reading twice is the proxy. This app only ever asks for
 * relative addresses beginning with `/api`. In development the build tool's own
 * web server forwards those to the Python server, so the browser sees one
 * address and there is no cross-address configuration to explain. In the
 * packaged app a single web server does the same forwarding. The address is
 * read from the environment because inside a container the server answers to
 * the name `backend` rather than to `localhost`.
 */

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Listen on every network address, not just this machine's loopback, so the
    // app is reachable from outside the container it runs in.
    host: true,
    proxy: {
      "/api": {
        target: process.env.KATALYST_API_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    // Tests run against a simulated browser page rather than a real one.
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
