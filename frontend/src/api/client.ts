/**
 * The one place this app talks to the server.
 *
 * Every type below is taken from `schema.ts`, which is generated from the
 * server's own description of itself by `scripts/gen-types.sh`. Nothing here
 * re-states a shape the server already describes: if a field is renamed on the
 * server and this file is not updated, the type check fails rather than the
 * browser silently showing a blank.
 *
 * Addresses are relative — `/api/...`, never a full web address with a host
 * name. In development the build tool forwards `/api` to the server on port
 * 8000; in the packaged app a single web server serves these files and forwards
 * `/api` to the server. The same line of code is correct in both.
 *
 * Failures come back as an ordinary error whose message is already a plain
 * sentence, because that sentence is what the screen shows the reader. The
 * screen does not translate error codes; it prints what it was told.
 */

import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

/** What the server says when asked whether it is running. */
export type Health = components["schemas"]["Health"];

/** What the server says when asked whether it can do its job yet. */
export type Readiness = components["schemas"]["Readiness"];

/** What the server calls itself, and which build is running. */
export type About = components["schemas"]["About"];

/**
 * The typed caller. An empty base address keeps every request relative to
 * whatever address this page was served from.
 */
const server = createClient<paths>({ baseUrl: "" });

/**
 * Make one request and return its reading, or throw an error whose message is a
 * sentence the screen can print as it stands.
 *
 * @param address The route being read, named in the failure message so a reader
 *   can see which of the three readings went wrong.
 * @param request The already-typed call to make.
 */
async function read<Reading>(
  address: string,
  request: () => Promise<{ data?: Reading; response: Response }>,
): Promise<Reading> {
  let answer: { data?: Reading; response: Response };
  try {
    answer = await request();
  } catch {
    throw new Error(`Could not reach the server at ${address}. It may not be running.`);
  }
  if (answer.data === undefined) {
    throw new Error(
      `The server answered ${address} with status ${answer.response.status} and no reading.`,
    );
  }
  return answer.data;
}

/** Ask whether the server is running. Depends on nothing else being configured. */
export function readHealth(): Promise<Health> {
  return read<Health>("/api/healthz", () => server.GET("/api/healthz"));
}

/** Ask whether the server can generate a map yet, and whether a model key is configured. */
export function readReadiness(): Promise<Readiness> {
  return read<Readiness>("/api/readyz", () => server.GET("/api/readyz"));
}

/** Ask what the server calls itself and which build is running. */
export function readAbout(): Promise<About> {
  return read<About>("/api/about", () => server.GET("/api/about"));
}
