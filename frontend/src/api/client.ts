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

/** One stored example as it appears in a list, before the map itself is drawn. */
export type FixtureSummary = components["schemas"]["FixtureSummary"];

/** One stored example in full: the base map and the branches that go with it. */
export type FixtureBundle = components["schemas"]["FixtureBundle"];

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
    const numbered = answer.response.status;
    // A web server that forwards requests on to another program replies with
    // 502, 503 or 504 when that program did not answer at all. In practice that
    // means the server is not running, so say so rather than repeating a number
    // the reader would have to look up.
    const reason =
      numbered === 502 || numbered === 503 || numbered === 504
        ? `Nothing answered at ${address} — the server may not be running.`
        : `The request to ${address} came back with no reading.`;
    throw new Error(`${reason} The reply was numbered ${numbered}.`);
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

/** Ask for the list of stored examples this server ships with. */
export function readExampleList(): Promise<FixtureSummary[]> {
  return read<FixtureSummary[]>("/api/fixtures", () => server.GET("/api/fixtures"));
}

/**
 * Ask for one stored example in full: its map, and the branches that go with it.
 *
 * @param id The short name the example is asked for by, such as `hormuz`.
 */
export function readExample(id: string): Promise<FixtureBundle> {
  return read<FixtureBundle>(`/api/fixtures/${id}`, () =>
    server.GET("/api/fixtures/{fixture_id}", { params: { path: { fixture_id: id } } }),
  );
}
