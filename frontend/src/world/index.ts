/**
 * The seam between the canvas and wherever its numbers come from, in one door.
 *
 * Components import from here and never reach past it into a particular source,
 * which is what makes swapping the stored example for the engine a one-line
 * change in `App.tsx`.
 */

export { ApiWorldSource } from "./apiSource";
export { appendEdit, forkBranch, openBranch, type Workshop, workshopOf } from "./branchReducer";
export { branchesOf, FixtureWorldSource } from "./fixtureSource";
export { monogramFor, seedFor } from "./fromTheServer";
export type { FixtureBundle, WorldSource } from "./source";
export type {
  Absence,
  AbsenceKind,
  AddedArrow,
  Badge,
  BaseRateView,
  BeliefOwner,
  BeliefSlots,
  BranchHue,
  BranchView,
  ClaimChange,
  ClaimKind,
  ClaimView,
  ConditionalRequest,
  DeltaRow,
  DiffRequest,
  DiffState,
  DiffView,
  Edit,
  EvidenceClipping,
  Known,
  Likelihood,
  LinkMode,
  LinkShape,
  LinkView,
  Movement,
  Provenance,
  Reason,
  Selection,
  SourceView,
  Standing,
  WireBranch,
  WireEdit,
  WorldRequest,
  WorldView,
} from "./types";
