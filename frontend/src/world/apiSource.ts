/**
 * The world source for the engine — **a stub. Nothing uses it yet.**
 *
 * The routes it names do not exist. They are being written in parallel, and
 * this file is here so that the shape of the handover is visible now rather
 * than discovered later: when `POST /api/worlds` answers, this class fills in
 * and the object handed to the canvas changes in one line of `App.tsx`. No
 * component changes, because every component is written against `WorldSource`.
 *
 * Read this file as a promise about shape, not as working code. Both methods
 * throw a sentence saying what is missing. They do not return a placeholder
 * world, and they must never start doing so: a world full of numbers nobody
 * computed is precisely the thing this product refuses to draw.
 *
 * The request and reply shapes below are written out by hand rather than taken
 * from the server's generated description, because the server has nothing to
 * describe yet. When it does, these become the generated types and the hand
 * written ones are deleted.
 */

import type { FixtureBundle, WorldSource } from "./source";
import type { WorldRequest, WorldView } from "./types";

/**
 * What the engine will be asked for: a base map, an ordered list of edits, and
 * the seed that makes the answer reproducible.
 *
 * Not yet sent anywhere.
 */
export interface WorldCall {
  /** Which base map to start from. */
  readonly base_id: string;
  /** Which branch of edits to apply. Left out, this is the base world. */
  readonly branch_id?: string;
  /** The seed. The same map, branch and seed must give a byte-identical world. */
  readonly seed?: number;
}

/**
 * Calls the engine for a computed world.
 *
 * **Not wired up.** `App.tsx` hands the canvas a `FixtureWorldSource`; swapping
 * in this one is the whole of the change when the routes land.
 */
export class ApiWorldSource implements WorldSource {
  /**
   * The base map and its branches.
   *
   * This half already works today, from the stored-example route, so the stub
   * says which route it would use rather than pretending there is a second one.
   */
  async readBundle(_id: string): Promise<FixtureBundle> {
    throw new Error(
      "Reading a map from the engine is not built yet. The stored-example route at " +
        "/api/fixtures serves maps today, and FixtureWorldSource reads it.",
    );
  }

  /**
   * One computed world, from `POST /api/worlds`.
   *
   * When this answers, the slots that read "no engine yet" today fill in with
   * real numbers and their ranges, and a fifth state — a claim whose number
   * moved — becomes drawable. Nothing on the canvas is deleted at that point,
   * because nothing false was drawn.
   */
  async readWorld(_request: WorldRequest): Promise<WorldView> {
    throw new Error(
      "The engine's world route is not built yet, so there is no computed world to show. " +
        "Until it answers, every number slot it would fill reads as an absence with its " +
        "reason rather than as a guess.",
    );
  }
}
