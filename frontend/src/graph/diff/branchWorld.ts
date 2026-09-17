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

import { toShare, toTwoFigures } from "../../components/BeliefChip";
import type {
  Absence,
  Badge,
  BranchView,
  ClaimView,
  DeltaRow,
  DiffState,
  DiffView,
  LinkView,
  Movement,
  Slot,
  WorldView,
} from "../../world/types";
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
 * What the engine answered about this branch, when it has answered.
 *
 * Both halves are needed together: the world is what the numbers are, and the
 * difference is what moved. Neither is worked out here.
 */
export interface Computed {
  /** The branch world, exactly as the engine built it. */
  readonly now: WorldView;
  /** What the engine says moved between the two worlds. */
  readonly change: DiffView;
}

/**
 * What a claim's tile says about an edit, once the engine has answered.
 *
 * **Two questions, and they are not the same question.** *Did this claim's
 * number move?* is the engine's to answer, and where it has an answer — the
 * claim arrived, the claim was forced false, the number moved — its word is the
 * one the tile carries. *Can my edit reach this claim at all?* is structural,
 * the browser reads it off the branch, and the engine's `unchanged` does not
 * answer it: a claim your edit can reach whose number happened to hold still is
 * not a claim your edit cannot reach, and saying so would be telling the reader
 * the opposite of the truth.
 *
 * So the engine's word wins wherever it has one, and the structural word fills
 * the rest. Where the two can be compared they must agree, and
 * `test_the_browser_states_agree_with_the_engine` is what says so.
 *
 * @param structural What the branch alone says about this claim.
 * @param engine What the engine says about it, when the engine mentions it.
 */
export function tileState(
  structural: DiffState,
  engine: DiffView | undefined,
  id: string,
): DiffState {
  const said = engine?.claims.get(id)?.state;
  if (said === "added" || said === "killed" || said === "shifted") {
    return said;
  }
  return structural;
}

/**
 * The chevron and the word each direction goes by on a tile.
 *
 * Neither is a colour. The two hues this product keeps for a direction mean
 * *which way the money moves*, and a likelihood going up is not that: the arrow
 * into *Brent settles below $68* pushes that claim toward true while the price
 * it describes falls. So a move is a chevron, two readings and a word, and never
 * one of those two hues.
 */
const WAY = {
  up: { chevron: "▲", word: "up" },
  down: { chevron: "▼", word: "down" },
} as const;

/**
 * How far this claim's number moved, as a line on its tile.
 *
 * It sits with the badges because it is one of the things the edits behind this
 * claim did to it, and because the tile already reserves room for whatever they
 * have to say. Both readings are the engine's, printed at two significant
 * figures like every other number on screen, and nothing here subtracts them.
 *
 * @param moved The engine's reading of how far this claim moved.
 */
function movedBadge(moved: Movement): Badge {
  const way = WAY[moved.way];
  const agreed = moved.sameDirection.reading;
  return {
    words: `${toTwoFigures(moved.from)} ${way.chevron} ${toTwoFigures(moved.to)}`,
    reason:
      `Your edit moved this claim ${way.word}, from ${toTwoFigures(moved.from)} to ` +
      `${toTwoFigures(moved.to)}, read on the day this claim is judged. ` +
      (agreed === undefined
        ? moved.sameDirection.absence.reason
        : `${toShare(agreed)} of the versions of the map moved the same way.`),
    movement: true,
  };
}

/**
 * The endings the rail lists, in the engine's own order, with one substitution.
 *
 * **A claim standing on the reader's own say-so has no move to report.** While a
 * supposition holds the claim is true in every version of the map, and the
 * engine stores a flat `1` on it so that a chain multiplied out has a factor for
 * it. No surface prints that number — and ".41 up to >.99" is that number with
 * the certainty guard in front of it. So such a row reads the word instead, the
 * same word the tile reads, and says why.
 *
 * Nothing else about a row is touched: not its place in the list, not its
 * ranking, not its two columns.
 *
 * @param computed What the engine answered about this branch.
 */
export function railRows(computed: Computed): readonly DeltaRow[] {
  const standing = new Map(
    computed.now.claims.flatMap((claim) =>
      claim.standing === undefined ? [] : [[claim.id, claim.standing] as const],
    ),
  );
  return computed.change.rows.map((row) => {
    const word = standing.get(row.claimId);
    if (word === undefined) {
      return row;
    }
    return {
      ...row,
      move: {
        absence: {
          kind: "no_engine" as const,
          words: word.words,
          reason:
            `${word.reason} So there is no likelihood here to compare with the one this ` +
            `ending had before.`,
        },
      },
    };
  });
}

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
 * @param computed What the engine answered about this branch, when it has
 *   answered. Left out, the map with your edits shows structure and an absence
 *   wherever a likelihood would have moved — which is what it shows while the
 *   engine is being asked, and what it shows for good when there is no engine.
 */
export function bothPaintings(
  base: WorldView,
  branch: BranchView,
  computed?: Computed,
): { now: WorldView; before: WorldView } {
  const now = branchWorld(base, branch, computed);
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
 * @param computed What the engine answered, when it has answered. Its claims
 *   carry the computed likelihoods, its badges are read off the world, and its
 *   difference says which claims moved.
 */
export function branchWorld(base: WorldView, branch: BranchView, computed?: Computed): WorldView {
  // The claims and arrows to draw. With the engine, they are the map its edits
  // left behind — which already holds whatever the branch added. Without it,
  // the base map plus whatever whole claims and arrows the branch supplied.
  const claims = computed === undefined ? [...base.claims, ...branch.claims] : computed.now.claims;
  const links = computed === undefined ? [...base.links, ...branch.links] : computed.now.links;
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
  // What the tiles say about the edits behind them. With the engine, the world
  // carries every value an edit fixed and every supposition a later edit
  // undermined, and the badges were read off it; without it they are derived
  // here from the branch. One line, one derivation, whichever it is.
  const derived = badgesByClaim(branch.edits, {
    words,
    arrows: new Map(
      branch.links.map((link) => [
        link.id,
        { source: link.source, mode: link.mode, strength: link.strength },
      ]),
    ),
  });
  const badges =
    computed === undefined
      ? derived
      : new Map(computed.now.claims.map((claim) => [claim.id, [...(claim.badges ?? [])]]));
  const standing =
    computed === undefined
      ? standingByClaim(branch.edits, derived)
      : new Map(
          computed.now.claims.flatMap((claim) =>
            claim.standing === undefined ? [] : [[claim.id, claim.standing] as const],
          ),
        );

  // Your own numbers, from every **My own number** edit on this branch. A later
  // one on the same claim replaces an earlier one on screen; both stay in the
  // branch, in order, because the branch is the audit trail.
  const yours = new Map(
    branch.edits.flatMap((edit) => (edit.op === "believe" ? [[edit.target, edit.belief]] : [])),
  );

  return {
    ...base,
    ...(computed === undefined
      ? {}
      : {
          // How the engine was run, so the chip can say whether its range was
          // computed and the line under the map can name the seed.
          versions: computed.now.versions,
          worldsPerVersion: computed.now.worldsPerVersion,
          seed: computed.now.seed,
          warnings: computed.now.warnings,
        }),
    branch,
    claims: claims.map((claim): ClaimView => {
      const ownNumber = yours.get(claim.id);
      const structural = diff.states.get(claim.id) ?? "untouched";
      const state = tileState(structural, computed?.change, claim.id);
      // How far the number moved — unless the claim is standing on the reader's
      // own say-so, in which case there is no number to have moved to. While a
      // supposition holds the claim is true in every version of the map, and the
      // engine stores a flat 1 on it so that a chain has a factor to multiply;
      // **no surface prints that number**, and a reading of ".40 up to >.99" is
      // that number wearing the certainty guard's clothes. The badge pair says
      // *Supposed · Oct 1* instead, which is what actually happened.
      const moved =
        state === "shifted" && standing.get(claim.id) === undefined
          ? computed?.change.claims.get(claim.id)?.moved
          : undefined;
      return {
        ...claim,
        diff: state,
        moved,
        badges: [
          ...(badges.get(claim.id) ?? []),
          ...(moved === undefined ? [] : [movedBadge(moved)]),
        ],
        standing: standing.get(claim.id),
        beliefs: {
          ...claim.beliefs,
          // With the engine, the model's number on this claim is the engine's
          // own answer for this branch and stays exactly as it came. Without it,
          // a claim the edit can reach shows an absence: the number on screen
          // would be the base map's, not this branch's, and leaving it there
          // would be the quietest lie in the product.
          model:
            computed === undefined && diff.canMove.has(claim.id)
              ? NO_ENGINE_SLOT
              : claim.beliefs.model,
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
      computed === undefined
        ? `${base.origin} This branch — "${branch.label}" — is the same map with ` +
          `${branch.edits.length === 1 ? "one edit" : `${branch.edits.length} edits`} folded ` +
          `onto it. What you can see of it is shape: which claim arrived, which arrows came ` +
          `with it, and which claims those arrows can reach. Every likelihood a branch would ` +
          `move reads "no engine yet", because nothing has worked one out.`
        : computed.now.origin,
  };
}
