/**
 * Which way the money moves — the only thing in this product that is allowed to
 * be a hue, and never a hue by itself.
 *
 * `--dir-up` is blue and `--dir-down` is amber. Never red and green: red-green
 * fails the most common form of colour blindness, and the loss-and-gain reading
 * is wrong half the time — a falling oil price is good news for an airline.
 *
 * **This is the one component that reads those two colours.** Everything else in
 * the tree is forbidden to name them, and a test checks that. The reason is not
 * tidiness: a direction has to carry a glyph *and* a sign *and* a word as well
 * as a hue, and the moment a second component reaches for the colour on its own,
 * one of those three gets dropped and the picture starts saying something by
 * hue alone.
 *
 * **The trap this component exists to prevent, and it is a live one.** The arrow
 * from *the strait reopens* to *Brent crude settles below $68* is `+1.6` —
 * positive, because it makes that claim come out **true** more often — and the
 * thing that claim describes is a **falling** price. Colour that arrow amber and
 * you have said the opposite of what it means. **A push's sign is not a
 * direction of financial effect.** A push is carried by its printed sign and by
 * the word *toward* or *against*, and never by one of these two hues.
 *
 * **Nothing in this build renders one.** There is no thesis card, no strip of
 * world state, no live price, and the ranked list of what moved needs the
 * engine. The component and its two colours are written now anyway, so that two
 * unused tokens cannot be quietly borrowed for something else in the meantime.
 */

import "./directionReadout.css";

/** Which way the money moves. */
export type Direction = "up" | "down";

/** What the readout needs to draw itself. */
export interface DirectionReadoutProps {
  /** Which way the money moves. */
  readonly direction: Direction;
  /**
   * How far, already written out the way this product writes a number — the
   * readout prints it as given and works nothing out.
   */
  readonly amount: string;
  /** What moved, in the words the reader would use for it. */
  readonly what: string;
}

/** The glyph, the sign and the word that go with each direction. */
const READINGS = {
  up: { glyph: "▲", sign: "+", word: "up" },
  down: { glyph: "▼", sign: "−", word: "down" },
} as const;

/** Which way the money moves: a glyph, a sign, a word and a hue — all four. */
export function DirectionReadout({ direction, amount, what }: DirectionReadoutProps) {
  const reading = READINGS[direction];
  return (
    <span className="direction-readout" data-direction={direction}>
      <span className="direction-readout__glyph" aria-hidden="true">
        {reading.glyph}
      </span>
      <span className="direction-readout__amount">{`${reading.sign}${amount}`}</span>
      <span className="direction-readout__word">{reading.word}</span>
      <span className="direction-readout__what">{what}</span>
    </span>
  );
}
