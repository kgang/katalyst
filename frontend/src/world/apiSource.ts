/**
 * The world source that asks the engine, and draws the answers it gets back.
 *
 * This is where the two halves of the product meet. The canvas was written
 * against `WorldSource` and nothing else, so joining it to the engine changed no
 * component: the object handed in changed, the slots that used to read *no
 * engine yet* now hold computed numbers, and every absence that is still on
 * screen is still an absence for a reason it can name.
 *
 * **Three questions, three routes, and nothing else is asked.**
 *
 * | The question | Where it is asked |
 * |---|---|
 * | What does this branch make the map say? | `POST /api/worlds` |
 * | What moved between the map as written and the map with my edits? | `POST /api/worlds/diff` |
 * | What is the number on this one arrow? | `POST /api/worlds/conditional` |
 *
 * A fourth thing is read and is not the engine's: the map itself — the claims,
 * their wording, how each is judged, the arrows and what is cited for them —
 * which comes from the stored-example route. A map is written by hand; a world
 * never is. So the map is read once and kept, and the engine is asked again
 * every time an edit lands.
 *
 * **There is no arithmetic on a likelihood anywhere in this file.** Numbers
 * arrive from the engine and are carried, untouched and at full precision, to
 * the moment they are printed. Which way a claim moved is read off the sign of
 * the engine's own difference — a comparison, not a subtraction — and no two
 * numbers on this map are ever combined here.
 *
 * **Nothing here is invented.** A branch that does not fit comes back as every
 * reason at once and is thrown on for the screen to print. A claim under a live
 * supposition gets the word rather than the `1` the engine stores for it. And a
 * chain's multiplied-out likelihood, which the engine does not carry, stays an
 * absence that says exactly that rather than being worked out here.
 */

import type { ClaimDiff, Diff, World } from "../api/client";
import { readConditional, readDiff, readExample, readWorld } from "../api/client";
import { ADDED, happened, retracted, supposed } from "../graph/diff/badges";
import { daysApart } from "../graph/diff/days";
import { noReadingAtAll } from "./absence";
import { filled, NO_PATH_PRODUCT, seedFor, toClaim, toLink } from "./fromTheServer";
import { NOT_ON_THIS_MAP } from "./naming";
import type { FixtureBundle, WorldSource } from "./source";
import type {
  Badge,
  BranchView,
  ClaimChange,
  ClaimView,
  ConditionalRequest,
  DeltaRow,
  DiffRequest,
  DiffView,
  Known,
  Movement,
  Ranged,
  Standing,
  WireBranch,
  WorldRequest,
  WorldView,
} from "./types";

/**
 * Which likelihood on a claim's series is the one its tile shows.
 *
 * A tile's headline number is read on the claim's **own resolve-by day** — the
 * day the claim is judged, which every claim has and which the tile already
 * prints. So the word beside that number has to be read on the same day, or the
 * tile would say *Supposed* over a number worked out for a different morning.
 *
 * **This is the engine's own rule, written again.** `_read_on` in
 * `backend/src/katalyst/domain/diff.py` pins the day inside the window, then
 * takes the first drawn day at or after it, and never falls off the end. The
 * browser asked for an exact match instead, so a claim judged on a day the
 * series does not carry — a window longer than 180 days is drawn at fewer
 * points, and a claim added on a branch brings its own resolve-by day — got no
 * word beside its number at all, while the engine happily read one. Two rules
 * for *which day is this claim's day* is one too many, so this is that one.
 *
 * @param world The world as the engine built it.
 * @param resolvesBy The claim's own resolve-by day.
 * @returns Where that day sits among the days the world was worked through, or
 *   nothing at all when the date cannot be read or the world drew no days.
 */
function whereItsDaySits(world: World, resolvesBy: string): number | null {
  const offset = daysApart(world.day_zero, resolvesBy);
  const drawn = world.series_days;
  if (offset === null || drawn.length === 0) {
    return null;
  }
  // Inside the window first — a claim judged before day zero is read on day
  // zero, and one judged after the last day is read on the last day.
  const wanted = Math.min(Math.max(0, offset), world.days);
  const at = drawn.findIndex((day) => day >= wanted);
  return at === -1 ? drawn.length - 1 : at;
}

/**
 * What a tile says about the edits behind it, read off the world rather than
 * worked out from the branch.
 *
 * The world carries both halves: every value an edit fixed, in the order the
 * edits were made, and every supposition a later edit undermined with the day
 * and the arrow that did it. Reading the badges off those is what closes the
 * question the diff chapter left open — two derivations of one line eventually
 * disagree, so there is one, and it is the world's.
 *
 * One badge is not on the world and cannot be: **Added**. Whether a claim
 * arrived with an edit is a fact about the branch, and the branch is what says
 * so — the world only shows the map the edits left behind, in which an added
 * claim looks like any other.
 *
 * @param world The world as the engine built it.
 * @param words Every claim's own words, so a badge can quote one.
 * @param added The claims this branch brought with it.
 * @returns One list of badges per claim that has any, in the order they were
 *   earned.
 */
function badgesFromTheWorld(
  world: World,
  words: ReadonlyMap<string, string>,
  added: ReadonlySet<string>,
): Map<string, Badge[]> {
  const badges = new Map<string, Badge[]>();
  const add = (claim: string, badge: Badge): void => {
    badges.set(claim, [...(badges.get(claim) ?? []), badge]);
  };

  // A claim an edit brought with it earns **Added** before anything it is later
  // supposed to be: it has to be on the map before anything can be said about
  // it, so that is the order the two badges read in.
  for (const claim of added) {
    add(claim, ADDED);
  }

  const supposedOn = new Map<string, string>();
  for (const fixed of world.assignments) {
    const day = fixed.at ?? world.day_zero;
    if (fixed.kind === "do") {
      add(fixed.target, supposed(day, fixed.value));
      if (fixed.value) {
        supposedOn.set(fixed.target, day);
      }
    } else {
      add(fixed.target, happened(day, fixed.value));
    }
  }

  for (const end of world.retractions) {
    const cause = words.get(end.by_claim) ?? end.by_claim;
    add(end.target, retracted(end.at, cause, supposedOn.get(end.target) ?? end.at));
  }

  return badges;
}

/**
 * Which claims an edit has fixed the value of, on their own judging day.
 *
 * **One rule, and it is not a rule about suppositions.** A claim whose value an
 * edit fixed is true — or false — in every version of the map, so the engine
 * stores a flat `1` or `0` for it, and **no surface but the path product prints
 * that number.** Every other reader writes the word where the likelihood would
 * go: *Supposed · Oct 1* where the reader took it as given, *Happened · Oct 1*
 * where they reported it as news. Answering either with a likelihood is a tool
 * arguing with the person using it — and `>.99` is that number wearing the
 * certainty guard's clothes.
 *
 * **The two are found in different places, and that is the engine's shape rather
 * than ours.** A supposition can be undermined by a later edit, so whether it
 * still holds is a fact about a *day*, and the world's `states` carry it — H
 * reads *supposed* on the first and *pushed* by the day it is judged. An
 * observation is news: nothing takes it back, it holds across the whole window,
 * and the world records it as an assignment rather than as a state.
 *
 * @param world The world as the engine built it.
 * @param claims The claims, so each one's resolve-by day can be found.
 * @param badges The badges, for the words and the sentence behind them.
 */
function standingFromTheWorld(
  world: World,
  claims: readonly ClaimView[],
  badges: ReadonlyMap<string, readonly Badge[]>,
): Map<string, Standing> {
  // What each observed claim was reported to be, so the word beside it is the
  // one the engine was actually told rather than the one the button says.
  const observed = new Map(
    world.assignments
      .filter((fixed) => fixed.kind === "observe")
      .map((fixed) => [fixed.target, fixed.value] as const),
  );
  const standing = new Map<string, Standing>();
  for (const claim of claims) {
    const at = whereItsDaySits(world, claim.resolvesBy);
    const isSupposed = at !== null && world.states[claim.id]?.[at] === "supposed";
    const isNews = observed.has(claim.id);
    if (!isSupposed && !isNews) {
      continue;
    }
    const word = isSupposed ? "Supposed" : observed.get(claim.id) ? "Happened" : "Did not happen";
    const said = (badges.get(claim.id) ?? []).find((badge) => badge.words.startsWith(word));
    standing.set(claim.id, {
      words: said?.words ?? word,
      reason:
        `${said?.reason ?? "An edit fixed this claim's value."} It is settled in every version ` +
        `of the map, so there is no likelihood to show.`,
    });
  }
  return standing;
}

/**
 * The one sentence under a computed map, saying where every number on it came
 * from.
 *
 * It names both halves — the address the map was read from and the address its
 * likelihoods were worked out at — and the three things anyone would need to
 * rebuild the same answer: the map, the branch, and the seed.
 */
function originOf(world: World, bundle: FixtureBundle, branchLabel: string | null): string {
  const which =
    branchLabel === null
      ? "with nothing done to it"
      : `with the branch "${branchLabel}" folded onto it`;
  return (
    `Every claim, arrow and date came from /api/fixtures/${bundle.id}; every likelihood was ` +
    `worked out by /api/worlds from that map ${which}, at seed ${world.seed}, over ` +
    `${world.versions.toLocaleString("en-GB").replace(/,/g, " ")} versions of the map with ` +
    `${world.worlds} worlds under each. Nothing here was typed in: the same map, branch and ` +
    `seed give the same answer every time.`
  );
}

/**
 * The four things about a map that a computed world does not carry.
 *
 * A world knows its own numbers and the map the edits left behind; it does not
 * know what that map is called on screen, where it was read from, or the sentence
 * that says where its numbers came from. Those come from whoever asked — the
 * stored-example route here, a generation's own stream in `src/stream/growth.ts`
 * — which is what lets **one** function turn a world into what the canvas draws.
 * Two such functions would drift inside a week, and then a generated map and a
 * fetched map would disagree about a number neither of them computed.
 */
export interface WorldSummary {
  /** What this map is asked for by, such as `hormuz`, or a generation's own name. */
  readonly id: string;
  /** What the map is called on screen. */
  readonly title: string;
  /** The day the map is set on, as the map writes a day: `2026-10-01`. */
  readonly day: string;
  /** One sentence under the map saying where every number on it came from. */
  readonly origin: string;
}

/**
 * Turn one computed world into the world the canvas draws.
 *
 * **This is the only function that does it.** Both callers — the stored-example
 * source below and the reducer that folds a generation's stream — hand their
 * world through here, so a map that was fetched and a map that was watched being
 * built cannot say different things about the same claim.
 *
 * @param world The world as the engine built it.
 * @param from What this map is called and where it came from.
 * @param branch The branch that was folded, or nothing on the base world.
 */
export function toWorldView(world: World, from: WorldSummary, branch?: BranchView): WorldView {
  // The map the engine's edits left behind, which is the map to draw: a branch
  // that added a claim added it here too.
  const claims = world.graph.propositions.map(toClaim);
  const words = new Map(claims.map((claim) => [claim.id, claim.claim]));
  const added = new Set(
    (branch?.edits ?? []).flatMap((edit) => (edit.op === "insert" ? [edit.claimId] : [])),
  );
  const badges = badgesFromTheWorld(world, words, added);
  const standing = standingFromTheWorld(world, claims, badges);

  return {
    baseId: from.id,
    title: from.title,
    today: from.day,
    hypothesisId: world.graph.hypothesis_id,
    claims: claims.map((claim): ClaimView => {
      const computed = world.beliefs[claim.id];
      return {
        ...claim,
        // The engine's own answer for this claim, read on the day the claim is
        // judged. It replaces the likelihood the map was written with, and it
        // replaces nothing else: the reader's own number and a venue's price
        // are theirs.
        beliefs: {
          ...claim.beliefs,
          model: computed === undefined ? claim.beliefs.model : filled(computed),
        },
        badges: badges.get(claim.id) ?? [],
        standing: standing.get(claim.id),
        // A chain's multiplied-out likelihood is not on a world, so it stays an
        // absence that says so. Nothing here multiplies one.
        pathProduct: { absence: NO_PATH_PRODUCT },
      };
    }),
    links: world.graph.links.map(toLink),
    versions: world.versions,
    worldsPerVersion: world.worlds,
    seed: world.seed,
    warnings: world.warnings,
    origin: from.origin,
  };
}

/**
 * How far one claim moved, as the engine read it.
 *
 * Every part of it is the engine's own: the two readings, the sign that says
 * which way it went, the share of versions that agreed, and whether the move
 * came from nothing but the observation changing how much each version counts.
 * Nothing here subtracts, compares two numbers, or works anything out.
 *
 * @param row The claim's own row of the engine's difference.
 */
function movement(row: ClaimDiff): Movement | undefined {
  const { before, after, delta, agreement } = row;
  if (before === null || after === null || delta === null) {
    return undefined;
  }
  return {
    from: before,
    to: after,
    // Which way it went is the sign of the engine's own difference. Reading a
    // sign is a comparison against nought, not a subtraction: nothing here works
    // out how far anything moved.
    way: delta < 0 ? "down" : "up",
    by: delta,
    sameDirection:
      agreement === null
        ? {
            absence: noReadingAtAll(
              "Only one of the two worlds holds this claim, so there is no direction for the " +
                "versions of the map to have agreed or disagreed about.",
            ),
          }
        : { reading: agreement },
    // A claim with no causes of its own can move under **This happened** without
    // anything pushing on it: the observation makes the versions of the map in
    // which it was likely count for more, and the average shifts. The engine
    // says when that is the whole story, and the panel prints one sentence when
    // it does. **The browser never works this out for itself** — it is a fact
    // about how the engine read the numbers, and only the engine knows it.
    onlyReweighted: row.moved_only_by_reweighting,
    // And which half of its test a claim the engine called unchanged failed:
    // the move was too small, or the versions of the map disagreed which way.
    // Carried across as the word it came as. The floor and the bar that decide
    // it are constants inside the engine and are on no wire, so this is the
    // only way the browser can know — which is what stops a second engine
    // growing here and disagreeing with the first.
    unchangedBecause: row.unchanged_because ?? undefined,
  };
}

/** Turn the engine's difference into what the rail and the tiles read. */
function toDiffView(difference: Diff, claims: readonly ClaimView[]): DiffView {
  const byId = new Map(claims.map((claim) => [claim.id, claim]));

  const changed = new Map<string, ClaimChange>();
  for (const [id, one] of Object.entries(difference.claims)) {
    changed.set(id, {
      state: one.state,
      moved: movement(one),
    });
  }

  // The endings that moved, in the engine's own order, largest rank first.
  // Nothing here sorts, re-ranks or drops a row.
  const ranked: DeltaRow[] = difference.rows.map((row): DeltaRow => {
    const claim = byId.get(row.target);
    return {
      claimId: row.target,
      label: claim?.claim ?? NOT_ON_THIS_MAP,
      kind: claim?.kind ?? "market",
      move: {
        reading: {
          from: row.before,
          to: row.after,
          largestOn: row.at_day,
          way: row.peak_delta < 0 ? "down" : "up",
          by: row.peak_delta,
        },
      },
      rangeWidth: { reading: row.range_width },
      agreement: { reading: row.agreement },
    };
  });

  // **The endings the engine left off that list get their rows somewhere else,
  // and it matters that it is only somewhere else.** `rows` is what the engine
  // ranked, in the engine's order, and nothing more — which is what this field
  // says it is. Completing the list is `railRows` in `graph/diff/branchWorld.ts`:
  // it is the one that knows which endings the edit can reach and which claims
  // stand on the reader's own say-so, and a second builder here answered the
  // same question with less to go on. Two builders of one row is how a
  // forced-false ending came to be dropped by one of them and kept by neither.
  const summary: Known<string> = { reading: difference.summary };
  return { claims: changed, rows: ranked, summary, warnings: difference.warnings };
}

/**
 * The branch in the shape that goes over the wire, or a sentence saying why it
 * cannot go.
 *
 * A branch is only askable about when every edit in it can be written down the
 * way the server writes one. Today one edit cannot: a claim of your own needs
 * the part of this product that drafts a whole claim — its wording, how it is
 * judged, by whom, by when — and that is not connected.
 *
 * @param branch The branch the screen is showing.
 * @throws Error With one plain sentence, when the branch cannot be sent.
 */
function sendable(branch: BranchView): WireBranch {
  if (branch.wire === undefined) {
    throw new Error(
      `The branch "${branch.label}" has an edit this build cannot hand to the engine, so no ` +
        `world was asked for. Adding a claim of your own needs the part of this product that ` +
        `drafts one, and that is not connected yet.`,
    );
  }
  return branch.wire;
}

/**
 * Calls the engine for a computed world, for what an edit moved, and for the
 * number on one arrow.
 *
 * It keeps one thing between calls: the stored example itself, because a map is
 * written by hand and does not change while the page is open. It keeps no
 * world, no difference and no likelihood — those are computed results, and a
 * kept one eventually disagrees with the three things it came from.
 */
export class ApiWorldSource implements WorldSource {
  /** The stored examples this page has already read, by their short names. */
  readonly #maps = new Map<string, Promise<FixtureBundle>>();

  /** The base map and its branches, read once and kept for as long as the page is open. */
  async readBundle(id: string): Promise<FixtureBundle> {
    const already = this.#maps.get(id);
    if (already !== undefined) {
      return already;
    }
    const asked = readExample(id);
    this.#maps.set(id, asked);
    try {
      return await asked;
    } catch (failure) {
      // A map that could not be read is not a map we should go on pretending to
      // have. Forgetting it means the next attempt really asks again.
      this.#maps.delete(id);
      throw failure;
    }
  }

  /**
   * One computed world: the map with this branch folded onto it and every
   * likelihood worked through time.
   *
   * @param request Which map, and which branch — sent whole, because there is
   *   nowhere to keep one yet.
   */
  async readWorld(request: WorldRequest): Promise<WorldView> {
    const bundle = await this.readBundle(request.baseId);
    const branch = request.branch;
    const world = await readWorld(
      request.baseId,
      branch === undefined ? null : sendable(branch),
      seedFor(bundle),
    );
    const view = toWorldView(
      world,
      {
        id: bundle.id,
        title: bundle.title,
        day: bundle.fixture_date,
        origin: originOf(world, bundle, branch?.label ?? null),
      },
      branch,
    );
    return branch === undefined ? view : { ...view, branch };
  }

  /**
   * What moved between the map as it was written and the map with this branch
   * folded onto it.
   *
   * @param request Which map and which branch.
   */
  async readDiff(request: DiffRequest): Promise<DiffView> {
    const bundle = await this.readBundle(request.baseId);
    const difference = await readDiff(request.baseId, sendable(request.branch), seedFor(bundle));
    // The claims are needed only for their words and their kinds, so the rail
    // can name an ending rather than print its identifier.
    const claims = bundle.graph.propositions.map(toClaim).concat(request.branch.claims);
    return toDiffView(difference, claims);
  }

  /**
   * The number on one arrow: its target, with its cause **supposed** true.
   *
   * @param request Which map, which branch, and which arrow.
   */
  async readConditional(request: ConditionalRequest): Promise<Known<Ranged>> {
    const bundle = await this.readBundle(request.baseId);
    const answer = await readConditional(
      request.baseId,
      request.branch === undefined ? null : sendable(request.branch),
      seedFor(bundle),
      request.linkId,
    );
    return filled(answer);
  }
}
