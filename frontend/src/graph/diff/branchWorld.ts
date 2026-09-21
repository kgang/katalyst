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

import { toMovement, toShare, toTwoFigures } from "../../components/BeliefChip";
import { absence, inTheEnginesWords, noReadingAtAll } from "../../world/absence";
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
  WorldView,
} from "../../world/types";
import { badgesByClaim, standingByClaim } from "./badges";
import { readDiff } from "./diffState";
import { NO_CHANGE, noChangeReason } from "./noChange";
import type { Arrow } from "./reach";

/**
 * What stands where a likelihood would go on a claim this edit can reach.
 *
 * The words are the shared vocabulary's; the sentence says which number is
 * missing and who would have to work it out.
 */
export const NO_ENGINE: Absence = absence(
  "no_engine",
  "Nothing has worked this number through the map yet. Your edit can reach this claim, so " +
    "its likelihood would move — and the part of this product that works out where to is not " +
    "connected. The old number would be the base map's, not this branch's.",
);

/**
 * Where the engine has got to with this branch.
 *
 * **Waiting is a state, not the absence of one.** The engine has been asked and
 * has not answered, or has refused, or could not be reached — and in every one
 * of those the screen owes the reader the same thing: the room the answer will
 * take, and a sentence saying why it is not there. What it must never do is
 * change size when the answer lands, so a claim the edit can reach keeps the
 * same tile in both states and only the words inside it change.
 *
 * Left out altogether means there is no engine behind this map at all — the
 * stored example standing in — and then nothing is reserved, because nothing is
 * coming.
 */
export type Engine =
  | {
      readonly at: "waiting";
      /** What stands where the numbers would be, and why. */
      readonly absence: Absence;
    }
  | {
      readonly at: "answered";
      /** The branch world, exactly as the engine built it. */
      readonly now: WorldView;
      /** What the engine says moved between the two worlds. */
      readonly change: DiffView;
    };

/** What the engine answered, or nothing when it has not. */
function answered(engine: Engine | undefined): { now: WorldView; change: DiffView } | undefined {
  return engine?.at === "answered" ? engine : undefined;
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
 * How far this claim's number moved, as a line on its tile.
 *
 * It sits with the badges because it is one of the things the edits behind this
 * claim did to it, and because the tile already reserves room for whatever they
 * have to say. Both readings are the engine's, printed at two significant
 * figures like every other number on screen, and nothing here subtracts them.
 *
 * **Every claim the edit can reach gets this line, whether or not it moved and
 * whether or not the engine has answered yet.** That is what stops the map
 * jumping: a line that appears when the answer lands is a tile that grows when
 * the answer lands, and a tile that grows after it has been placed either shoves
 * its neighbours or sits on top of them. So the room is reserved from the moment
 * the branch opens, and only the words inside it change — the reading when the
 * claim moved, *no change* when the engine says it did not, and the reason it is
 * not there yet while the engine is being asked.
 *
 * @param moved What the engine read on this claim — carried whether or not it
 *   called the claim shifted, because the sentence behind *no change* is built
 *   from the very same two numbers.
 * @param shifted Whether the engine called this claim shifted. The browser reads
 *   the verdict off the engine's word and never decides it by comparing the two
 *   numbers itself.
 * @param waiting What to say instead when the engine has not answered: its own
 *   word for where it has got to.
 */
function movedBadge(
  moved: Movement | undefined,
  shifted: boolean,
  waiting: Absence | undefined,
): Badge {
  if (waiting !== undefined) {
    return { words: waiting.words, reason: waiting.reason, movement: true };
  }
  if (!shifted || moved === undefined) {
    // Why it did not move is one sentence written in one place, because the
    // engine gives one verdict — and four sentences apart from one another is
    // how three of them came to name causes the engine never gave.
    return { words: NO_CHANGE, reason: noChangeReason(moved), movement: true };
  }
  const agreed = moved.sameDirection.reading;
  return {
    words: toMovement(moved.from, moved.to, moved.by, moved.way),
    reason:
      `Your edit moved this claim ${moved.way}, from ${toTwoFigures(moved.from)} to ` +
      `${toTwoFigures(moved.to)}, read on the day this claim is judged. ` +
      (agreed === undefined
        ? moved.sameDirection.absence.reason
        : `${toShare(agreed)} of the versions of the map moved the same way.`),
    movement: true,
  };
}

/**
 * Every ending the edit can reach, as the rail lists them.
 *
 * **The engine's rows first, in the engine's own order, and then the endings it
 * left out.** The engine's `rows` hold only the endings that came out `shifted`,
 * so a reader looking at that list alone cannot tell *"it did not move"* from
 * *"it is not on this map"* — and silence that could mean either is the state
 * the traceability rule exists to forbid. So the reachable endings the engine
 * left out follow, greyed and unranked, in map order, each reading **no change**
 * where the move would be.
 *
 * **Where the verdict comes from matters as much as the row.** *Did not move* is
 * read off `ClaimDiff.state`, which the engine states for every claim in either
 * world. The browser never decides it by comparing two numbers: that would be
 * the browser re-running the shifted test with its own floor and its own bar,
 * and two answers to that question is one too many.
 *
 * **A claim standing on the reader's own say-so has no move to report.** While a
 * supposition holds the claim is true in every version of the map, and the
 * engine stores a flat `1` on it so that a chain multiplied out has a factor for
 * it. No surface prints that number — and ".41 up to >.99" is that number with
 * the certainty guard in front of it. So such a row reads the word instead, the
 * same word the tile reads, and says why.
 *
 * Nothing else about a ranked row is touched: not its place in the list, not its
 * ranking, not its two columns.
 *
 * @param painted The map with the edits, as it is drawn — which is where the
 *   endings the edit can reach are known, and which claims stand on a
 *   supposition.
 * @param change What the engine answered.
 */
export function railRows(painted: WorldView, change: DiffView): readonly DeltaRow[] {
  const standing = new Map(
    painted.claims.flatMap((claim) =>
      claim.standing === undefined ? [] : [[claim.id, claim.standing] as const],
    ),
  );

  const ranked = change.rows.map((row) => {
    const word = standing.get(row.claimId);
    if (word === undefined) {
      return row;
    }
    return {
      ...row,
      move: {
        absence: inTheEnginesWords(
          word.words,
          `${word.reason} So there is no likelihood here to compare with the one this ` +
            `ending had before.`,
        ),
      },
    };
  });

  const listed = new Set(ranked.map((row) => row.claimId));
  const held: DeltaRow[] = painted.claims
    .filter(
      (claim) =>
        (claim.kind === "market" || claim.kind === "not_tradeable") &&
        claim.diff !== undefined &&
        claim.diff !== "untouched" &&
        !listed.has(claim.id) &&
        change.claims.get(claim.id)?.state === "unchanged",
    )
    .map((claim) => ({
      claimId: claim.id,
      label: claim.claim,
      kind: claim.kind,
      move: {
        absence: inTheEnginesWords(
          NO_CHANGE,
          `${noChangeReason(change.claims.get(claim.id)?.moved)} It is listed so that holding ` +
            `still cannot be mistaken for not being here.`,
        ),
      },
      rangeWidth: {
        absence: noReadingAtAll(
          "How firm a number is only says something about a number that moved.",
        ),
      },
      agreement: {
        absence: noReadingAtAll(
          "Whether the versions of the map agreed on a direction only says something about a " +
            "claim that had a direction.",
        ),
      },
      noChange: true,
    }));

  return [...ranked, ...held];
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
 * @param engine Where the engine has got to with this branch. Left out, there
 *   is no engine behind this map at all and every likelihood the edit could move
 *   reads its absence for good.
 */
export function bothPaintings(
  base: WorldView,
  branch: BranchView,
  engine?: Engine,
): { now: WorldView; before: WorldView } {
  const now = branchWorld(base, branch, engine);
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
 * @param engine Where the engine has got to. Once it has answered, its claims
 *   carry the computed likelihoods, its badges are read off the world, and its
 *   difference says which claims moved. While it is still being asked, the room
 *   those answers will take is reserved and says why it is empty.
 */
export function branchWorld(base: WorldView, branch: BranchView, engine?: Engine): WorldView {
  const computed = answered(engine);
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
      const supposed = standing.get(claim.id) !== undefined;
      // What the engine read on this claim: the two numbers, which way they
      // went, and whether the move came from nothing but the observation
      // changing how much each version counts. It is carried for **every** claim
      // the engine read, not only the ones it calls `shifted` — a claim can move
      // a hair and still come out unchanged, and when it did so purely by
      // reweighting the panel has a sentence for exactly that.
      const moved = supposed ? undefined : computed?.change.claims.get(claim.id)?.moved;
      // Which tiles reserve a line for how far their number moved: the ones the
      // edit can reach, and only those. A claim it added, one it forced false
      // and one it cannot reach have nothing to say there, and a claim standing
      // on the reader's say-so says the word instead. **The same set in both
      // states**, so the tile is the same size before and after the answer.
      const reserves = (state === "downstream" || state === "shifted") && !supposed;
      return {
        ...claim,
        diff: state,
        moved,
        badges: [
          ...(badges.get(claim.id) ?? []),
          // The tile's line reads the move only when the engine calls the claim
          // shifted. A claim that moved a hair and came out unchanged reads *no
          // change*, which is the engine's own verdict; the two numbers behind
          // it are one click away in the panel.
          ...(reserves && engine !== undefined
            ? [
                movedBadge(
                  moved,
                  state === "shifted",
                  engine.at === "waiting" ? engine.absence : undefined,
                ),
              ]
            : []),
        ],
        standing: standing.get(claim.id),
        beliefs: {
          ...claim.beliefs,
          // With the engine's answer, the model's number on this claim is the
          // engine's own for this branch and stays exactly as it came. Without
          // it, a claim the edit can reach shows an absence — the engine's own
          // word for where it got to when there is one, so that a branch it
          // refused says *that* rather than "no engine yet". The number on
          // screen would otherwise be the base map's, not this branch's, and
          // leaving it there would be the quietest lie in the product.
          model:
            computed === undefined && diff.canMove.has(claim.id)
              ? { absence: engine?.at === "waiting" ? engine.absence : NO_ENGINE }
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
          `move reads its absence, because nothing has worked one out.`
        : computed.now.origin,
  };
}
