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

/** One computed world: a map, the values its edits fixed, and every number worked through. */
export type World = components["schemas"]["World"];

/** What moved between two worlds: every claim, the endings that moved, one sentence. */
export type Diff = components["schemas"]["Diff"];

/** What happened to one claim between two worlds, with the numbers behind it. */
export type ClaimDiff = components["schemas"]["ClaimDiff"];

/** One likelihood with the range around it, and whose number it is. */
export type Belief = components["schemas"]["Belief"];

/** A branch as the server writes one: a name and an ordered list of edits. */
export type Branch = components["schemas"]["Branch"];

/** One thing wrong with a branch: the rule broken, the thing at fault, and a sentence. */
export type Violation = components["schemas"]["Violation"];

/**
 * A branch the server would not fold onto the map, with **every** reason at once.
 *
 * Never just the first. A person fixing a branch one fault per attempt learns
 * only that the tool is hostile, so the whole list travels together and the
 * screen prints all of it.
 *
 * It is an ordinary error, so a caller that does not care can let it go past
 * like any other failure; a caller that does reads `reasons`.
 */
export class RefusedBranch extends Error {
  /** Every reason, in the order the server put them in. */
  readonly reasons: readonly Violation[];

  /**
   * @param reasons Every reason the branch was refused.
   */
  constructor(reasons: readonly Violation[]) {
    super(
      reasons.length === 1
        ? (reasons[0]?.message ?? "This branch does not fit the map.")
        : `This branch does not fit the map, for ${reasons.length} reasons.`,
    );
    this.name = "RefusedBranch";
    this.reasons = reasons;
  }
}

/**
 * The typed caller. An empty base address keeps every request relative to
 * whatever address this page was served from.
 */
const server = createClient<paths>({ baseUrl: "" });

/**
 * Read every reason out of a refusal, whatever shape the refusal took.
 *
 * Two different bodies arrive under the same number. A branch that does not fit
 * the map comes back as the server's own list — a rule, the thing at fault, and
 * a sentence naming the claim or the arrow by its words. A body the web
 * framework could not read at all comes back as *its* list, which has a field
 * path and a message instead. Both are reasons a person can act on, so both are
 * turned into the same three fields here, and neither is swallowed.
 *
 * @param body Whatever came back beside the refusal.
 * @returns Every reason, in the order they arrived. Never empty: a refusal with
 *   nothing in it still gets one sentence, because a screen that says "refused"
 *   and nothing else is worse than no screen at all.
 */
function everyReason(body: unknown): Violation[] {
  const listed = (body as { detail?: unknown } | null)?.detail;
  if (!Array.isArray(listed) || listed.length === 0) {
    return [
      {
        code: "edit_not_applicable",
        subject: "",
        message:
          "The server would not carry this out and did not say why. Nothing was changed on the map.",
      },
    ];
  }
  return listed.map((one): Violation => {
    const reason = one as Partial<Violation> & { msg?: string; loc?: readonly unknown[] };
    if (typeof reason.message === "string") {
      return {
        code: reason.code ?? "edit_not_applicable",
        subject: reason.subject ?? "",
        message: reason.message,
      };
    }
    // The framework's own shape: a path to the field it could not read, and a
    // sentence about it. The path is the nearest thing to a subject there is.
    const where = (reason.loc ?? []).map(String).join(" → ");
    return {
      code: "edit_not_applicable",
      subject: where,
      message:
        where === ""
          ? (reason.msg ?? "The server could not read this request.")
          : `The server could not read this request at ${where}: ${reason.msg ?? "no reason given"}.`,
    };
  });
}

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
  request: () => Promise<{ data?: Reading; error?: unknown; response: Response }>,
): Promise<Reading> {
  let answer: { data?: Reading; error?: unknown; response: Response };
  try {
    answer = await request();
  } catch {
    throw new Error(`Could not reach the server at ${address}. It may not be running.`);
  }
  if (answer.data === undefined) {
    const numbered = answer.response.status;
    // A branch that does not fit the map is not a breakage: it is something the
    // reader can repair, and the server says every reason at once so that they
    // can repair all of it in one go. It comes back as its own kind of error so
    // that the screen can print the list rather than one sentence about it.
    if (numbered === 422) {
      throw new RefusedBranch(everyReason(answer.error));
    }
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

/**
 * Send a request without the two loop sizes, and let the engine pick them.
 *
 * Every world route takes two more numbers: how many versions of the map to try,
 * and how many worlds to run under each. **The browser does not get to decide
 * either.** They are how sure we are of the numbers put in and how the dice
 * fall, the engine holds the answer, and a second copy of it here would be a
 * number nobody computed sitting in the interface waiting to disagree.
 *
 * The description the server generates counts them as part of a request because
 * they have defaults, so the two are dropped here, once, with this sentence
 * beside it — rather than filled in three times with a guess.
 *
 * @param body Everything the route really needs: which map, which branch, which
 *   seed, and on one route which arrow.
 */
function engineChoosesTheLoops<Body extends { base_id: string; seed: number }>(
  body: Body,
): Body & { versions: number; worlds: number } {
  return body as Body & { versions: number; worlds: number };
}

/**
 * Ask the engine to fold a branch onto a map and work every likelihood through
 * time.
 *
 * @param baseId The short name of the stored example, such as `hormuz`.
 * @param branch The branch to fold, sent whole because there is nowhere to keep
 *   one yet. Left out, this is the base world — the map with nothing done to it.
 * @param seed The one number every random draw in the answer comes from. The
 *   same map, branch and seed always give the same world.
 */
export function readWorld(baseId: string, branch: Branch | null, seed: number): Promise<World> {
  return read<World>("/api/worlds", () =>
    server.POST("/api/worlds", {
      body: engineChoosesTheLoops({ base_id: baseId, branch, seed }),
    }),
  );
}

/**
 * Ask the engine what moved between the map as it was written and the map with
 * this branch folded onto it.
 *
 * @param baseId The short name of the stored example both worlds use.
 * @param branch The branch the second world has and the first does not.
 * @param seed The one seed both worlds are built from. One seed for the pair,
 *   so that what is left after the comparison is the edit rather than the edit
 *   plus a wash of sampling noise.
 */
export function readDiff(baseId: string, branch: Branch, seed: number): Promise<Diff> {
  return read<Diff>("/api/worlds/diff", () =>
    server.POST("/api/worlds/diff", {
      body: engineChoosesTheLoops({ base_id: baseId, branch_b: branch, seed }),
    }),
  );
}

/**
 * Ask the engine for the number on one arrow: its target, with its cause
 * **supposed** true.
 *
 * @param baseId The short name of the stored example.
 * @param branch The branch to fold first, or nothing for the map as written.
 * @param seed The one number every random draw comes from.
 * @param linkId The arrow whose number is wanted.
 */
export function readConditional(
  baseId: string,
  branch: Branch | null,
  seed: number,
  linkId: string,
): Promise<Belief> {
  return read<Belief>("/api/worlds/conditional", () =>
    server.POST("/api/worlds/conditional", {
      body: engineChoosesTheLoops({ base_id: baseId, branch, seed, link_id: linkId }),
    }),
  );
}
