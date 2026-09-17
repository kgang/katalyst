/**
 * The seam between the canvas and wherever its numbers come from.
 *
 * There are two things behind this interface. Today it is the stored example
 * route, which serves a map that was written by hand and checked when the
 * server started. Later it is the engine, which computes a world from a map, a
 * branch and a seed. The canvas is written against neither: it is written
 * against the two methods below, so the day the engine lands the only change is
 * which object is handed in.
 *
 * Why a seam at all, rather than calling the route directly: the two halves of
 * this product are being built at the same time, by different people, against
 * routes that do not all exist yet. A seam is what lets the half that draws be
 * finished and looked at before the half that computes is written.
 */

import type { components } from "../api/schema";
import type { WorldRequest, WorldView } from "./types";

/**
 * One stored example in full: the base map and the branches that go with it.
 *
 * Taken from the server's own description of itself, because this shape really
 * is the server's and re-stating it here would let the two drift apart.
 */
export type FixtureBundle = components["schemas"]["FixtureBundle"];

/** Where the canvas gets a map and a world from. */
export interface WorldSource {
  /** The base map and its branches, as the stored-example route already serves them. */
  readBundle(id: string): Promise<FixtureBundle>;
  /**
   * One world.
   *
   * Its numbers are optional: every slot that holds a likelihood may instead
   * hold an absence with the reason it is absent. See `types.ts`.
   */
  readWorld(request: WorldRequest): Promise<WorldView>;
}
