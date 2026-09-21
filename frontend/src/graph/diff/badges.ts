/**
 * What a tile says about the edits behind it.
 *
 * Six badges, copied word for word from the shared vocabulary's *Interface
 * words* table and never paraphrased, plus one that no button produces:
 *
 * | The button you pressed | The badge afterwards |
 * |---|---|
 * | **Suppose this is true** (and **Suppose this is false**) | **Supposed · date** |
 * | **This happened** | **Happened · date** |
 * | **Add a claim** | **Added** |
 * | **Change this push** | **Retuned** |
 * | **Split this claim** | **Split** |
 * | **My own number** | none — the three-up belief chip is the badge |
 *
 * and the derived one: **Retracted · date · by "…"**.
 *
 * **The derived badge is the point of the whole file.** A claim the reader
 * supposed true, and that a later edit in the same branch pushed back down, is
 * never drawn as plainly true. Its tile carries both states in order:
 *
 * > **Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on
 * > Iranian territory"**
 *
 * Every part of that line is read off the branch, and none of it is inference:
 *
 * - *Supposed · Oct 1* — the supposition itself carries its day.
 * - *Retracted · Oct 2* — the day the **cause** of the undermining arrow becomes
 *   true. Not the day that arrow's push arrives: a supposition ends when the
 *   news lands, and tying it to the push would let a delay of thirty days keep a
 *   supposition alive a month after the thing that broke it.
 * - *by "…"* — the undermining claim's own words.
 *
 * **What this build has and what it does not.** The badge pair is structure and
 * dates, and the branch carries both, so it is drawn here. The three-state series
 * that follows it — supposed, then withdrawn, then pushed — needs numbers, so
 * the tile's own likelihood reads its absence instead and says why. When the
 * engine lands, the world carries the retraction too and this derivation becomes
 * a hint the world must agree with.
 */

import type { Badge, Edit, LinkMode } from "../../world/types";
import { asQuoted, toDay } from "./days";

/** What an arrow has to be for a later edit to undermine a supposition through it. */
interface UnderminingArrow {
  /** The claim the arrow starts at. */
  readonly source: string;
  /** Whether the push survives its cause going away. */
  readonly mode: LinkMode;
  /** How hard it pushes, signed. */
  readonly strength: number;
}

/** What the badges need to know about the map around the edits. */
export interface BadgeContext {
  /** Every claim's own words, by identifier, so a badge can quote one. */
  readonly words: ReadonlyMap<string, string>;
  /** Every arrow that an **Add a claim** edit brought, by identifier. */
  readonly arrows: ReadonlyMap<string, UnderminingArrow>;
}

/**
 * The badge a supposition earns.
 *
 * Exported because a computed world earns the same badge from the values its
 * edits fixed, and one set of words for one badge is the whole point of this
 * file: the branch and the world must never say it two different ways.
 */
export function supposed(at: string, value: boolean): Badge {
  return {
    words: `Supposed · ${toDay(at)}`,
    reason: value
      ? `You supposed this is true, from ${toDay(at)}. Taken as given, with nothing said about ` +
        `what caused it.`
      : `You supposed this is false, from ${toDay(at)}. Taken as given, with nothing said about ` +
        `what caused it.`,
  };
}

/**
 * The badge the news earns. Exported for the same reason the one above is.
 *
 * **News can be that something did not happen, and the word for that is not
 * settled.** `spec/vocabulary.md` gives one badge for `observe` — *Happened ·
 * date* — and the panel only ever sends `value: true`, so no button on this
 * canvas can reach the other case. A branch written elsewhere can: the wire
 * format carries the value, the engine acts on it, and the world comes back
 * with it. Reading that world and printing *Happened* over it would be the
 * canvas telling the reader the opposite of what the engine was told.
 *
 * So the negative reads *Did not happen · date* here, and **that wording is
 * this file's guess and not Kent's**: the vocabulary has no row for it. It is
 * raised in the report for the chapter to settle, and when it does, this is the
 * one place the words change.
 *
 * @param at The day the news is reported on.
 * @param value What was reported: that it happened, or that it did not.
 */
export function happened(at: string, value: boolean): Badge {
  return {
    words: `${value ? "Happened" : "Did not happen"} · ${toDay(at)}`,
    reason: value
      ? `You reported this as news on ${toDay(at)}, so what came before it is read again in ` +
        `the light of it, not only what comes after.`
      : `You reported on ${toDay(at)} that this did not happen, so what came before it is read ` +
        `again in the light of that, not only what comes after.`,
  };
}

/** The badge a claim the reader added earns. Exported for the same reason. */
export const ADDED: Badge = {
  words: "Added",
  reason: "This claim, and the arrows that attach it, arrived as one edit on this branch.",
};

/**
 * The badge a supposition a later edit took back earns.
 *
 * **This one is derived: no button produces it.** A claim the reader supposed
 * true, and that a later edit in the same branch pushed back down, is never
 * drawn as plainly true.
 *
 * Exported because a computed world carries the retraction itself — which claim,
 * which day, which arrow, whose doing — and reading it off the world is better
 * than deriving it twice: two derivations of one line eventually disagree.
 *
 * @param at The day the supposition ended: the day the undermining arrow's
 *   cause was settled, never that day plus the arrow's delay.
 * @param cause The undermining claim in its own words, ready to be quoted.
 * @param supposedAt The day the supposition was made, for the sentence behind
 *   the badge.
 */
export function retracted(at: string, cause: string, supposedAt: string): Badge {
  return {
    words: `Retracted · ${toDay(at)} · by "${asQuoted(cause)}"`,
    reason:
      `You supposed this on ${toDay(supposedAt)}. A later edit added an arrow into it that ` +
      `only holds while its cause holds, and then made that cause true on ${toDay(at)} — ` +
      `so from that day we stop taking your word for this claim. The day the number moves ` +
      `is later still, because that arrow takes time to arrive; the gap is real and is not ` +
      `smoothed away.`,
    overrides: true,
  };
}

/**
 * Work out every badge on every claim, in the order the edits were made.
 *
 * @param edits The branch's edits, in order.
 * @param context The claims' words and the arrows the edits brought.
 * @returns One list of badges per claim that has any, in order.
 */
export function badgesByClaim(edits: readonly Edit[], context: BadgeContext): Map<string, Badge[]> {
  const badges = new Map<string, Badge[]>();
  const add = (claim: string, badge: Badge): void => {
    badges.set(claim, [...(badges.get(claim) ?? []), badge]);
  };

  // Which claims are under a supposition that still holds, and which arrows
  // could undermine one. An arrow only counts if it was added *after* the
  // supposition — supposing a claim cuts the arrows into it that exist at that
  // moment — and only if it is the holding-up kind pushing against the claim:
  // an arrow that fires once and fades cannot take back a supposition, because a
  // toppled domino stays toppled.
  const supposedNow = new Map<string, { at: string; index: number }>();
  const undermining = new Map<string, { source: string; from: number }[]>();

  edits.forEach((edit, index) => {
    switch (edit.op) {
      case "do":
        add(edit.target, supposed(edit.at, edit.value));
        if (edit.value) {
          supposedNow.set(edit.target, { at: edit.at, index });
        } else {
          supposedNow.delete(edit.target);
        }
        // A supposition cuts every arrow into its target that exists now, so
        // anything recorded as undermining it is gone.
        undermining.delete(edit.target);
        if (edit.value) {
          retractIfUndermined(edit.target, edit.at);
        }
        break;
      case "observe":
        add(edit.target, happened(edit.at, edit.value));
        if (edit.value) {
          retractIfUndermined(edit.target, edit.at);
        }
        break;
      case "insert":
        add(edit.claimId, ADDED);
        for (const arrow of edit.arrows) {
          const whole = context.arrows.get(arrow.id);
          if (whole === undefined || whole.mode !== "sustain" || whole.strength >= 0) {
            continue;
          }
          undermining.set(arrow.target, [
            ...(undermining.get(arrow.target) ?? []),
            { source: whole.source, from: index },
          ]);
        }
        break;
      case "retune":
      case "refine":
      case "believe":
        // **Change this push** and **Split this claim** are about an arrow and a
        // claim's internals rather than about a claim's standing, and the panel
        // lists them with their badges. **My own number** earns no badge at all:
        // the three-up belief chip is the badge.
        break;
    }
  });

  /**
   * If making this claim true undermines a supposition somewhere, say so on the
   * claim that was supposed.
   */
  function retractIfUndermined(nowTrue: string, at: string): void {
    for (const [claim, arrows] of undermining) {
      const live = supposedNow.get(claim);
      if (live === undefined) {
        continue;
      }
      const through = arrows.find((one) => one.source === nowTrue && one.from > live.index);
      if (through === undefined) {
        continue;
      }
      add(claim, retracted(at, context.words.get(nowTrue) ?? nowTrue, live.at));
      supposedNow.delete(claim);
      undermining.delete(claim);
    }
  }

  return badges;
}

/**
 * Which claims are standing on the reader's say-so at the end of the branch, and
 * from which day.
 *
 * A claim under a live supposition shows the **word** where a likelihood would
 * go — *Supposed · Oct 1*, never `1.0` and never `.98`. While it is supposed it
 * is true in every simulated version of the map, so there is no number to show,
 * and inventing one invites the reader to wonder about the missing two per cent
 * of a thing they themselves declared settled.
 *
 * @param edits The branch's edits, in order.
 * @param badges Every claim's badges, so that a supposition a later edit
 *   retracted is not still reported as standing.
 */
export function standingByClaim(
  edits: readonly Edit[],
  badges: ReadonlyMap<string, readonly Badge[]>,
): Map<string, { words: string; reason: string }> {
  const standing = new Map<string, { words: string; reason: string }>();
  for (const edit of edits) {
    if (edit.op !== "do") {
      continue;
    }
    const overridden = (badges.get(edit.target) ?? []).some((badge) => badge.overrides === true);
    if (overridden) {
      standing.delete(edit.target);
      continue;
    }
    const badge = supposed(edit.at, edit.value);
    standing.set(edit.target, {
      words: badge.words,
      reason: `${badge.reason} While a claim is supposed it is true in every version of the map, so there is no likelihood to show.`,
    });
  }
  return standing;
}
