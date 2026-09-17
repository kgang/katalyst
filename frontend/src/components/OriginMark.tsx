/**
 * Where an arrow came from, as a mark of one, two or three dots.
 *
 * **One component, drawn in two places**: at the tail of every wire on the map,
 * where the arrow leaves its cause, and beside the word in the panel. That is
 * the whole reason it is a component at all — two renderings of one field drift
 * within a week, and then the map and the panel are telling a reader two
 * different things about the same arrow.
 *
 * | Mark | What it covers | What it means |
 * |---|---|---|
 * | ●●● | documented, historical, market implied | something was fetched, studied or priced |
 * | ●● | argued, user | a mechanism was stated, or a person typed it |
 * | ● | asserted, simulated | the model talking, or a probe |
 *
 * **Three steps, not seven.** The question a picture can answer at a glance is
 * *is there a document behind this, or is it the model talking*; the seven-way
 * distinction is not something anybody reads off a drawing, so the exact word
 * goes beside the mark in the panel. It is also carried here as the mark's own
 * accessible name, so a reader who never sees the picture never loses it.
 *
 * **Why the mark and not the stroke.** The stroke is fully spent: it says what
 * kind of push an arrow is — dot-dash for a one-time spike, solid for a switch
 * that holds, growing dashes for one that builds. A wire cannot be dot-dash
 * because it is a spike and dashed because it was argued at the same time; it
 * would be neither, legibly. One channel per meaning.
 *
 * **The mark sits at the tail**, where the arrow leaves its cause, and never at
 * the head. The head already carries the arrowhead, and a receipt belongs where
 * the claim was made.
 *
 * No colour is involved anywhere in this file: the dots are drawn in the same
 * ink as the words around them, and the count is the whole of the encoding.
 */

import { originInWords, originStep, originStepMeaning } from "../graph/wires/encodings";
import type { Provenance } from "../world";
import "./originMark.css";

/** What the mark needs to draw itself. */
export interface OriginMarkProps {
  /** Where the arrow and its number came from. */
  readonly provenance: Provenance;
  /**
   * How the mark is being used.
   *
   * `alone` is the mark by itself, on a wire, and it carries the exact word as
   * its accessible name because nothing beside it does. `beside-the-word` is the
   * mark in the panel, where the word is printed next to it — so the mark
   * itself is then hidden from a screen reader rather than read out twice.
   */
  readonly use: "alone" | "beside-the-word";
}

/** The mark of one, two or three dots that says where an arrow came from. */
export function OriginMark({ provenance, use }: OriginMarkProps) {
  const step = originStep(provenance);
  const dots = Array.from({ length: step }, (_, at) => at);
  const spoken = `where it came from: ${provenance.replace("_", " ")} — ${originInWords(provenance)}`;

  return (
    <span
      className="origin-mark"
      data-step={step}
      data-on-a-wire={use === "alone" ? "yes" : "no"}
      // A tooltip on the wire, where there is no room for the word. The panel
      // prints the word itself, so this is the one place it would otherwise be
      // missing.
      title={
        use === "alone" ? `${provenance.replace("_", " ")} — ${originStepMeaning(step)}` : undefined
      }
      // A picture, and it is named: the exact word of the seven is the whole of
      // what a reader who is not looking at it would otherwise lose. Beside the
      // word, the word itself is right there, so the mark steps out of the way
      // rather than saying the same thing twice.
      role="img"
      aria-label={spoken}
      aria-hidden={use === "beside-the-word" ? true : undefined}
    >
      {dots.map((at) => (
        <span className="origin-mark__dot" key={at} />
      ))}
    </span>
  );
}
