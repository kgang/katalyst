/**
 * The world source for a map this program **generated**, rather than one it stores.
 *
 * A finished generation is a map like any other. It has claims, arrows, dates
 * and sources; a branch folds onto it; the engine works every likelihood through
 * it from a seed. So the reader can do to it exactly what they can do to the
 * stored example — the six edits, a branch, the two worlds painted together, the
 * change list — and all of it goes through the same three routes:
 *
 * | The question | Where it is asked |
 * |---|---|
 * | What does this branch make the map say? | `POST /api/worlds` |
 * | What moved between the map as it was built and the map with my edits? | `POST /api/worlds/diff` |
 * | What is the number on this one arrow? | `POST /api/worlds/conditional` |
 *
 * **One thing is different, and it is the whole reason this is a second source.**
 * The stored source reads the map itself from `/api/fixtures/<name>` — its
 * claims, their wording, its date, and the seed every question about it is asked
 * with. A generated map is in no such store: the server is holding it in memory,
 * under the identifier it minted for it, for the life of its own process. There
 * is nothing to fetch. What this is handed instead is what the reader already
 * watched arrive — the map's own name, the sentence it was built from, the seed
 * the run drew with, and the claims — and it asks the same three routes with
 * them.
 *
 * **It computes nothing.** Every number comes off one of the three answers and
 * is carried untouched to the moment it is printed, through the same two
 * converters the stored map goes through. Two converters would be two engines,
 * and a generated map and a stored map would disagree about a number neither of
 * them worked out.
 */

import type { World } from "../api/client";
import { readConditional, readDiff, readWorld } from "../api/client";
import { sendable, toDiffView, toWorldView } from "./apiSource";
import { filled } from "./fromTheServer";
import type { FixtureBundle, WorldSource } from "./source";
import type {
  ClaimView,
  ConditionalRequest,
  DiffRequest,
  DiffView,
  Known,
  Ranged,
  WorldRequest,
  WorldView,
} from "./types";

/**
 * What the screen already knows about a map it watched build itself, and the
 * whole of what asking about it takes.
 *
 * Everything here arrived on the generation's own stream. Nothing is worked out
 * from it and nothing is written down twice.
 */
export interface TheGeneratedMap {
  /**
   * The map's own identifier, which the engine minted and sent with the
   * likelihoods. **Not the generation's** — a generation is a run and a map is a
   * thing it built, and the routes below ask about the map.
   */
  readonly id: string;
  /** What the map is called on screen: the sentence the reader typed. */
  readonly title: string;
  /**
   * The one number every likelihood on this map was drawn from, as the run
   * reported it.
   *
   * It has to be the run's own seed and not a seed of this screen's choosing, or
   * the map the reader watched arrive and the map a branch is folded onto would
   * be two different maps wearing one name.
   */
  readonly seed: number;
  /**
   * Every claim on the map, for the one thing the change list needs that a
   * difference does not carry: a claim's own words, so a row names an ending
   * rather than printing its identifier.
   */
  readonly claims: readonly ClaimView[];
}

/**
 * The one sentence under a generated map, saying where every number on it came
 * from — and for how long the map itself will answer.
 *
 * It names both halves, as the stored map's sentence does: where the claims and
 * arrows came from, and where the likelihoods were worked out. And it says the
 * one thing that is true of this map and of no stored one — the server is
 * holding it in memory and will forget it when its process ends — because a
 * reader who comes back to a restarted server and finds the map gone deserves to
 * have been told, rather than to be left thinking they mistyped something.
 *
 * @param world The world as the engine built it.
 * @param map What the screen knows about the map itself.
 * @param branchLabel The name of the branch folded on, or nothing on the base
 *   world.
 */
function originOf(world: World, map: TheGeneratedMap, branchLabel: string | null): string {
  const which =
    branchLabel === null
      ? "with nothing done to it"
      : `with the branch "${branchLabel}" folded onto it`;
  const spelled = world.versions.toLocaleString("en-GB").replace(/,/g, " ");
  return (
    `Every claim and arrow on this map was proposed at /api/generate and accepted by the map's ` +
    `own rules; every likelihood was worked out by /api/worlds from that map ${which}, at seed ` +
    `${world.seed}, over ${spelled} versions of the map with ${world.worlds} worlds under each. ` +
    `The map answers to ${map.id} for as long as the server that built it is running, and is ` +
    `forgotten when it restarts — nothing here is written to disk.`
  );
}

/**
 * Asks the engine about a map this program generated, and draws the answers it
 * gets back.
 *
 * It keeps nothing between calls. There is nothing it could keep: a world, a
 * difference and an arrow's number are all computed results, and a kept one
 * eventually disagrees with the three things it came from.
 */
export class GeneratedMapSource implements WorldSource {
  /** What the screen watched arrive, and the whole of what this source has. */
  readonly #map: TheGeneratedMap;

  /**
   * @param map The map's own name, its title, the run's seed and its claims.
   */
  constructor(map: TheGeneratedMap) {
    this.#map = map;
  }

  /**
   * There is no stored example behind a generated map, and saying so is the
   * honest answer.
   *
   * The stored source reads a bundle because a stored map is written by hand and
   * served from a route. This map was built in front of the reader and is held in
   * the server's memory; nothing fetches it, and a source that pretended
   * otherwise would send a generated map's identifier to the route that hands out
   * the examples and turn one 404 into a puzzle.
   *
   * @param id The name that was asked for, so the sentence can quote it.
   */
  readBundle(id: string): Promise<FixtureBundle> {
    return Promise.reject(
      new Error(
        `The map ${id} was generated rather than stored, so there is no stored example to ` +
          `read for it. Its claims and arrows arrived on the generation's own stream, and its ` +
          `likelihoods are worked out at /api/worlds.`,
      ),
    );
  }

  /**
   * One computed world: the generated map with this branch folded onto it and
   * every likelihood worked through time.
   *
   * @param request Which map, and which branch — sent whole, because there is
   *   nowhere to keep one yet.
   */
  async readWorld(request: WorldRequest): Promise<WorldView> {
    const branch = request.branch;
    const world = await readWorld(
      request.baseId,
      branch === undefined ? null : sendable(branch),
      this.#map.seed,
    );
    const view = toWorldView(
      world,
      {
        id: request.baseId,
        title: this.#map.title,
        // The day the map's window starts on, read off the answer itself. A
        // generated map's day zero is the day its run happened, which the server
        // holds beside the map — so the world it hands back is the one thing
        // that can say it, and the browser never works a date out.
        day: world.day_zero,
        origin: originOf(world, this.#map, branch?.label ?? null),
      },
      branch,
    );
    return branch === undefined ? view : { ...view, branch };
  }

  /**
   * What moved between the map as it was built and the map with this branch
   * folded onto it.
   *
   * @param request Which map and which branch.
   */
  async readDiff(request: DiffRequest): Promise<DiffView> {
    const difference = await readDiff(request.baseId, sendable(request.branch), this.#map.seed);
    // The claims are wanted only for their words and their kinds, so a row of the
    // change list can name an ending. The map's own, plus whatever the branch
    // added, which is not on the map yet.
    return toDiffView(difference, [...this.#map.claims, ...request.branch.claims]);
  }

  /**
   * The number on one arrow: its target, with its cause **supposed** true.
   *
   * @param request Which map, which branch, and which arrow.
   */
  async readConditional(request: ConditionalRequest): Promise<Known<Ranged>> {
    const answer = await readConditional(
      request.baseId,
      request.branch === undefined ? null : sendable(request.branch),
      this.#map.seed,
      request.linkId,
    );
    return filled(answer);
  }
}
