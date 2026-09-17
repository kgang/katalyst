/**
 * The seam between the canvas and wherever its numbers come from, in one door.
 *
 * Components import from here and never reach past it into a particular source,
 * which is what makes swapping the stored example for the engine a one-line
 * change in `App.tsx`.
 */

export { ApiWorldSource } from "./apiSource";
export {
  type FixtureSummary,
  FixtureWorldSource,
  monogramFor,
  readExampleList,
} from "./fixtureSource";
export type { FixtureBundle, WorldSource } from "./source";
export type {
  Absence,
  BeliefOwner,
  BeliefSlots,
  ClaimKind,
  ClaimView,
  EvidenceClipping,
  LinkMode,
  LinkView,
  Ranged,
  Slot,
  Standing,
  WorldRequest,
  WorldView,
} from "./types";
