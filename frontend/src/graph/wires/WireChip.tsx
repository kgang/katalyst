/**
 * The plate in the middle of a wire: what this arrow does, read back in words.
 *
 * **What it will eventually show** is the *conditional likelihood* — how likely
 * this arrow's target is with its cause supposed true — which is the one number
 * that turns an arrow into something you can argue about. That number is not on
 * the map and is not worked out here. It costs a whole extra run of the map per
 * arrow, so the engine works one out only when a wire is asked about, one at a
 * time, and the answer is cached.
 *
 * **Until it has one — and always, in this build, because that route does not
 * exist yet — the chip reads the arrow's push back in words**, which is data
 * already on the arrow and needs no arithmetic:
 *
 *     +1.6
 *     a strong push toward
 *     after 2 days
 *
 * **Never a guessed number.** Not the push converted into a likelihood, not the
 * target's current number, not a dash that looks like a number that failed to
 * load. A number nobody computed is exactly the state a reader cannot trace.
 *
 * The delay is on the plate as well as in the panel. It is data on the arrow, it
 * needs no arithmetic, and it is the one thing on this map that says time
 * passes — which is most of what makes a chain of causes read as a chain rather
 * than as a diagram.
 */

import { toRange, toTwoFigures } from "../../components/BeliefChip";
import type { Known, Ranged } from "../../world";
import type { TileDetail } from "../geometry";
import { lagInWords, likelihoodStep, pushAsNumber, pushInWords } from "./encodings";

/** What the chip needs to draw itself. */
export interface WireChipProps {
  /** How hard this arrow pushes, signed, at full precision. */
  readonly strength: number;
  /** Days from the cause becoming true to the push reaching full size. */
  readonly lag: number;
  /**
   * The likelihood of this arrow's target with its cause supposed true.
   *
   * Absent in this build, and the chip then reads the push in words. It is a
   * parameter rather than an assumption so that the day the engine answers,
   * this component already knows what to do with it.
   */
  readonly conditional: Known<Ranged>;
  /**
   * How much of the plate there is room for — the same three forms the tile
   * has, at the same two thresholds.
   *
   * Below the first, thirteen-pixel words would land under eleven pixels on the
   * glass, so the plate changes what it draws rather than drawing it smaller,
   * exactly as the tile does: the signed push alone, set in the largest size.
   * Below the second even that size would fall under eleven, and there is no
   * size left — so **nothing is drawn at all**. The words and the delay are one
   * press away in the panel, and the stroke still says what kind of push it is.
   */
  readonly detail: TileDetail;
  /**
   * The shape of the room this plate has.
   *
   * A wire that crosses one gutter has a tall narrow strip to sit in, so its
   * plate stacks: the push, then the words, then the delay. A wire that travels
   * a corridor between two rows of tiles, or runs over the top of the map, has a
   * wide short strip instead, so its plate lies along the wire on one line. Same
   * three things, laid out for the space rather than squeezed into it.
   */
  readonly layout: "stacked" | "inline";
  /**
   * True when this is the one arrow that runs backwards — a market acting back
   * on the world it measures.
   *
   * It changes one thing: such an arrow keeps its delay on the plate even when
   * the map is zoomed out far enough that every other plate has dropped to the
   * push alone. A loop that takes no time is not feedback, it is a
   * contradiction, so the time is the part of that arrow that may not go.
   */
  readonly reflexive: boolean;
}

/** The plate in the middle of a wire. */
export function WireChip({ strength, lag, conditional, detail, layout, reflexive }: WireChipProps) {
  // Out where the map draws no words, the plate is one of the things that goes.
  // Said here as well as in the wire that draws it, so that a plate can never
  // be asked for a form it has nothing to print in.
  if (detail === "silhouette") {
    return null;
  }

  if (detail === "summary") {
    return (
      <span className="wire-chip" data-reading="push" data-detail="summary" data-layout={layout}>
        <span className="wire-chip__push">{pushAsNumber(strength)}</span>
        {reflexive ? <span className="wire-chip__lag">{lagInWords(lag)}</span> : null}
      </span>
    );
  }

  // There is no path through this component that prints a likelihood nobody
  // computed. When the engine can answer, its answer lands in the first branch
  // below; until then the slot holds its absence and the arrow's own push is
  // what the plate reads.
  const answer = conditional.reading;
  if (answer !== undefined) {
    return (
      <span className="wire-chip" data-reading="likelihood" data-detail="full" data-layout={layout}>
        <span className="wire-chip__bar" data-step={likelihoodStep(answer.p)} aria-hidden="true" />
        <span className="wire-chip__push">{toTwoFigures(answer.p)}</span>
        <span className="wire-chip__words">with its cause supposed true</span>
        <span className="wire-chip__lag">{toRange(answer.lo, answer.hi)}</span>
      </span>
    );
  }

  return (
    <span className="wire-chip" data-reading="push" data-detail="full" data-layout={layout}>
      <span className="wire-chip__push">{pushAsNumber(strength)}</span>
      <span className="wire-chip__words">{pushInWords(strength)}</span>
      <span className="wire-chip__lag">{lagInWords(lag)}</span>
    </span>
  );
}
