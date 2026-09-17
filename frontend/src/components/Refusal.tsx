/**
 * A branch the engine would not fold onto the map, with **every** reason at
 * once.
 *
 * **A refusal is an event, not a breakage.** The branch is something the reader
 * built and can repair, so the whole list of what is wrong with it arrives
 * together and all of it is printed. A tool that hands back one fault per
 * attempt teaches a person only that it is hostile.
 *
 * **Nothing opens over the map.** This is a block in the panel beside it, like
 * everything else in this product: the map stays on screen, drawn from the last
 * thing the engine did answer, so the reader can see the branch they are fixing
 * while they read what is wrong with it.
 *
 * **Nothing here is repaired, and nothing is dropped.** The sentences are the
 * server's own, printed as they came. This file writes no explanation of its
 * own: a refusal explained twice, once by the rule that fired and once by the
 * interface, is two explanations waiting to disagree.
 */

import { useId } from "react";
import type { Reason } from "../world";
import "./refusal.css";

/** What the block needs to draw itself. */
export interface RefusalProps {
  /** What was being asked for, in the reader's words, such as "a world". */
  readonly asking: string;
  /** Every reason the engine gave, in the order it gave them. */
  readonly reasons: readonly Reason[];
}

/** Every reason a branch was refused, printed at once. */
export function Refusal({ asking, reasons }: RefusalProps) {
  const headingId = useId();

  return (
    <section className="refusal" aria-labelledby={headingId}>
      <h2 className="refusal__heading" id={headingId}>
        This branch does not fit the map
      </h2>
      <p className="refusal__line">
        {reasons.length === 1
          ? `The engine would not work out ${asking} from this branch, and gave one reason.`
          : `The engine would not work out ${asking} from this branch, and gave ` +
            `${reasons.length} reasons — all of them, so you can fix all of them at once.`}
      </p>
      <ol className="refusal__reasons">
        {reasons.map((reason, place) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: the reasons arrive as one list from one answer and are never reordered, added to or removed, so a reason's place in the list is a stable name for it — and two rules can genuinely fire with the same sentence on two different claims.
          <li className="refusal__reason" key={`${place}-${reason.message}`}>
            {reason.message}
          </li>
        ))}
      </ol>
      <p className="refusal__note">
        Nothing was changed on the map. The branch is still yours to edit, and the map above is the
        last one the engine did work out.
      </p>
    </section>
  );
}
