/**
 * The seam between the canvas and wherever its numbers come from, in one door.
 *
 * Components import from here and never reach past it into a particular source,
 * which is what makes swapping the stored example for the engine a one-line
 * change in `App.tsx`.
 */

export { ApiWorldSource } from "./apiSource";
export { FixtureWorldSource, monogramFor } from "./fixtureSource";
export type { FixtureBundle, WorldSource } from "./source";
export type {
  Absence,
  BaseRateView,
  BeliefOwner,
  BeliefSlots,
  ClaimKind,
  ClaimView,
  EvidenceClipping,
  LinkMode,
  LinkShape,
  LinkView,
  Provenance,
  Ranged,
  Slot,
  SourceView,
  Standing,
  WorldRequest,
  WorldView,
} from "./types";
