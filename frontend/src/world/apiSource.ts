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
import { filled, NO_PATH_PRODUCT, seedFor, toClaim, toLink } from "./fromTheServer";
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
  Slot,
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
 * @param world The world as the engine built it.
 * @param resolvesBy The claim's own resolve-by day.
 * @returns Where that day sits among the days the world was worked through, or
 *   nothing at all when the day is outside the window or was not one of the days
 *   drawn.
 */
function whereItsDaySits(world: World, resolvesBy: string): number | null {
  const day = daysApart(world.day_zero, resolvesBy);
  if (day === null) {
    return null;
  }
  const at = world.series_days.indexOf(day);
  return at === -1 ? null : at;
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
      add(fixed.target, happened(day));
    }
  }

  for (const end of world.retractions) {
    const cause = words.get(end.by_claim) ?? end.by_claim;
    add(end.target, retracted(end.at, cause, supposedOn.get(end.target) ?? end.at));
  }

  return badges;
}

/**
 * Which claims are standing on the reader's say-so, on their own judging day.
 *
 * While a claim is supposed it is true in every version of the map, so the
 * engine stores a flat `1` for it — and **no surface prints that number.** Every
 * reader looks at the world's own states first and writes the word where the
 * likelihood would go, because "suppose this is true" answered with a likelihood
 * is a tool arguing with the person using it.
 *
 * @param world The world as the engine built it.
 * @param claims The claims, so each one's resolve-by day can be found.
 * @param badges The badges, for the sentence behind the word.
 */
function standingFromTheWorld(
  world: World,
  claims: readonly ClaimView[],
  badges: ReadonlyMap<string, readonly Badge[]>,
): Map<string, Standing> {
  const standing = new Map<string, Standing>();
  for (const claim of claims) {
    const at = whereItsDaySits(world, claim.resolvesBy);
    if (at === null || world.states[claim.id]?.[at] !== "supposed") {
      continue;
    }
    const said = (badges.get(claim.id) ?? []).find((badge) => badge.words.startsWith("Supposed"));
    standing.set(claim.id, {
      words: said?.words ?? "Supposed",
      reason:
        `${said?.reason ?? "You supposed this claim."} While a claim is supposed it is true ` +
        `in every version of the map, so there is no likelihood to show.`,
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
 * Turn one computed world into the world the canvas draws.
 *
 * @param world The world as the engine built it.
 * @param bundle The stored example, for the map's title and its address.
 * @param branch The branch that was folded, or nothing on the base world.
 */
function toWorldView(world: World, bundle: FixtureBundle, branch?: BranchView): WorldView {
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
    baseId: bundle.id,
    title: bundle.title,
    today: bundle.fixture_date,
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
    origin: originOf(world, bundle, branch?.label ?? null),
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
    sameDirection:
      agreement === null
        ? {
            absence: {
              kind: "no_engine",
              words: "—",
              reason:
                "Only one of the two worlds holds this claim, so there is no direction for the " +
                "versions of the map to have agreed or disagreed about.",
            },
          }
        : { reading: agreement },
    // A claim with no causes of its own can move under **This happened** without
    // anything pushing on it: the observation makes the versions of the map in
    // which it was likely count for more, and the average shifts. The engine
    // says when that is the whole story, and the panel prints one sentence when
    // it does. **The browser never works this out for itself** — it is a fact
    // about how the engine read the numbers, and only the engine knows it.
    onlyReweighted: row.moved_only_by_reweighting,
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
      label: claim?.claim ?? row.target,
      kind: claim?.kind ?? "market",
      move: {
        reading: {
          from: row.before,
          to: row.after,
          largestOn: row.at_day,
          way: row.peak_delta < 0 ? "down" : "up",
        },
      },
      rangeWidth: { reading: row.range_width },
      agreement: { reading: row.agreement },
    };
  });

  // An ending the engine left off that list did not move. Silence cannot be
  // told from absence — a reader would not know whether the ending held still
  // or is simply not on this map — so it gets a quiet row of its own, after
  // every ranked row and never mixed in among them.
  const listed = new Set(ranked.map((row) => row.claimId));
  const held: DeltaRow[] = claims
    .filter(
      (claim) =>
        (claim.kind === "market" || claim.kind === "not_tradeable") &&
        !listed.has(claim.id) &&
        changed.get(claim.id)?.state === "unchanged",
    )
    .map((claim) => ({
      claimId: claim.id,
      label: claim.claim,
      kind: claim.kind,
      move: {
        absence: {
          kind: "no_engine" as const,
          words: "no change",
          reason:
            "This ending is on the map and your edit did not move it: the engine compared the " +
            "two worlds and found no move worth reporting. It is listed so that holding still " +
            "cannot be mistaken for not being here.",
        },
      },
      rangeWidth: {
        absence: {
          kind: "no_engine" as const,
          words: "—",
          reason: "How firm a number is only says something about a number that moved.",
        },
      },
      agreement: {
        absence: {
          kind: "no_engine" as const,
          words: "—",
          reason:
            "Whether the versions of the map agreed on a direction only says something about a " +
            "claim that had a direction.",
        },
      },
      noChange: true,
    }));

  const summary: Known<string> = { reading: difference.summary };
  return { claims: changed, rows: [...ranked, ...held], summary, warnings: difference.warnings };
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
    const view = toWorldView(world, bundle, branch);
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
    const claims = bundle.graph.propositions
      .map(toClaim)
      .concat(request.branch.claims.map((claim) => claim));
    return toDiffView(difference, claims);
  }

  /**
   * The number on one arrow: its target, with its cause **supposed** true.
   *
   * @param request Which map, which branch, and which arrow.
   */
  async readConditional(request: ConditionalRequest): Promise<Slot> {
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
