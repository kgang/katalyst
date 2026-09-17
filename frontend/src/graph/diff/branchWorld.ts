/**
 * The second world: the base map with a branch folded onto it, as far as
 * structure goes and not one step further.
 *
 * **What this builds is real, and what it leaves out is left out on purpose.**
 * Applying a branch properly means running the map's numbers again, and that is
 * the engine's work. This half of the product does none of it. So the world
 * below carries everything the branch says about *shape* — which claim arrived,
 * which arrows came with it, which arrows a supposition cut, which claims the
 * edit can reach and which it provably cannot — and, wherever a likelihood would
 * have moved, **an absence with its reason** rather than the old number left
 * lying there looking current.
 *
 * That is the honest half and it is the useful half: *here is what your edit can
 * reach, and here is what it cannot* is this product's central correctness claim
 * made visible, and it needs no arithmetic at all.
 *
 * Three rules hold it together:
 *
 * 1. **A claim your edit can reach shows its model number's absence.** The
 *    number on the base map is the base map's number; on this branch it would be
 *    something else, and nothing has worked out what. Leaving the old one on
 *    screen would be the quietest lie in the product.
 * 2. **A claim your edit provably cannot reach keeps its number, unhedged.**
 *    That is not optimism: an edit reaches only what is still joined to its
 *    subject, and everything else is identical.
 * 3. **Your own number is yours.** *My own number* writes into your own slot and
 *    is never averaged with the model's or a market's, and it is not pushed
 *    through the map — so it fills in immediately and moves nothing else.
 */

import type { Absence, BranchView, ClaimView, LinkView, Slot, WorldView } from "../../world/types";
import { badgesByClaim, standingByClaim } from "./badges";
import { readDiff } from "./diffState";
import type { Arrow } from "./reach";

/**
 * What stands where a likelihood would go on a claim this edit can reach.
 *
 * The words are the shared vocabulary's; the sentence says which number is
 * missing and who would have to work it out.
 */
export const NO_ENGINE: Absence = {
  kind: "no_engine",
  words: "no engine yet",
  reason:
    "Nothing has worked this number through the map yet. Your edit can reach this claim, so " +
    "its likelihood would move — and the part of this product that works out where to is not " +
    "connected. The old number would be the base map's, not this branch's.",
};

/** That slot, ready to be dropped into a claim. */
const NO_ENGINE_SLOT: Slot = { absence: NO_ENGINE };

/**
 * The two paintings of one diff: the map with your edits, and the map as it was.
 *
 * **One layout, two paintings.** Both worlds hold exactly the same claims and the
 * same arrows, in the same order — so the union is laid out once and nothing
 * moves when you flip between them. What differs is what each tile *says*: in
 * the map as it was, the strike is a ghost and every number is the one the map
 * was written with; in the map with your edits, the strike is a real tile with
 * an accent ring and every number your edit could move reads its absence.
 *
 * A claim or an arrow that only one of the two has is drawn in the other as a
 * **ghost** — faint, in the same place — rather than vanishing. A tile that
 * disappeared would be a change you could only catch by remembering where it had
 * been.
 *
 * @param base The base world, exactly as the map was written.
 * @param branch The branch to fold onto it.
 */
export function bothPaintings(
  base: WorldView,
  branch: BranchView,
): { now: WorldView; before: WorldView } {
  const now = branchWorld(base, branch);
  const added = new Set(branch.claims.map((claim) => claim.id));
  const addedArrows = new Set(branch.links.map((link) => link.id));
  return {
    now: {
      ...now,
      // An arrow a supposition cut is not in the map with your edits: supposing a
      // claim says "do not tell me what caused it". It is still drawn, faint, in
      // the place it was.
      links: now.links.map((link) => ({ ...link, ghost: link.change === "cut" })),
    },
    before: {
      ...base,
      claims: [
        ...base.claims,
        ...branch.claims.map((claim) => ({ ...claim, ghost: true, diff: "added" as const })),
      ],
      links: [
        ...base.links,
        ...branch.links.map((link) => ({ ...link, ghost: true, change: "added" as const })),
      ],
      origin:
        `${base.origin} This is the map as it was written, with the ` +
        `${addedArrows.size === 1 ? "one arrow" : `${addedArrows.size} arrows`} and the ` +
        `${added.size === 1 ? "claim" : "claims"} your branch adds drawn faint, in the places ` +
        `they take on the other side of the switch — so that flipping between the two moves ` +
        `nothing.`,
    },
  };
}

/** Every arrow, as working out what an edit reaches needs it. */
function asArrows(links: readonly LinkView[]): Arrow[] {
  return links.map((link) => ({
    id: link.id,
    source: link.source,
    target: link.target,
    reflexive: link.reflexive,
  }));
}

/**
 * Fold a branch onto a base world and hand back the second world.
 *
 * Both worlds are drawn in one coordinate space afterwards, so nothing here
 * moves a claim: the union of the two maps is laid out once and painted twice.
 *
 * @param base The base world, exactly as the map was written.
 * @param branch The branch: its edits in order, and whatever whole claims and
 *   arrows the map supplied for them.
 */
export function branchWorld(base: WorldView, branch: BranchView): WorldView {
  const claims = [...base.claims, ...branch.claims];
  const links = [...base.links, ...branch.links];
  const diff = readDiff(
    claims.map((claim) => claim.id),
    asArrows(links),
    branch.edits,
  );

  const words = new Map(claims.map((claim) => [claim.id, claim.claim]));
  for (const edit of branch.edits) {
    if (edit.op === "insert" && !words.has(edit.claimId)) {
      words.set(edit.claimId, edit.words);
    }
  }
  const badges = badgesByClaim(branch.edits, {
    words,
    arrows: new Map(
      branch.links.map((link) => [
        link.id,
        { source: link.source, mode: link.mode, strength: link.strength },
      ]),
    ),
  });
  const standing = standingByClaim(branch.edits, badges);

  // Your own numbers, from every **My own number** edit on this branch. A later
  // one on the same claim replaces an earlier one on screen; both stay in the
  // branch, in order, because the branch is the audit trail.
  const yours = new Map(
    branch.edits.flatMap((edit) => (edit.op === "believe" ? [[edit.target, edit.belief]] : [])),
  );

  return {
    ...base,
    branch,
    claims: claims.map((claim): ClaimView => {
      const ownNumber = yours.get(claim.id);
      return {
        ...claim,
        diff: diff.states.get(claim.id) ?? "untouched",
        badges: badges.get(claim.id) ?? [],
        standing: standing.get(claim.id),
        beliefs: {
          ...claim.beliefs,
          model: diff.canMove.has(claim.id) ? NO_ENGINE_SLOT : claim.beliefs.model,
          user: ownNumber === undefined ? claim.beliefs.user : { reading: ownNumber },
        },
        // A whole chain's likelihood is multiplied out where the map's numbers
        // are worked out, and never here. It was an absence on the base world
        // and it is the same absence on this one.
        pathProduct: claim.pathProduct,
      };
    }),
    links: links.map(
      (link): LinkView => ({
        ...link,
        change: diff.addedLinks.has(link.id)
          ? "added"
          : diff.cutLinks.has(link.id)
            ? "cut"
            : diff.retunedLinks.has(link.id)
              ? "retuned"
              : undefined,
      }),
    ),
    origin:
      `${base.origin} This branch — "${branch.label}" — is the same map with ` +
      `${branch.edits.length === 1 ? "one edit" : `${branch.edits.length} edits`} folded onto ` +
      `it. What you can see of it is shape: which claim arrived, which arrows came with it, and ` +
      `which claims those arrows can reach. Every likelihood a branch would move reads "no ` +
      `engine yet", because nothing has worked one out.`,
  };
}
