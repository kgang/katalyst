/**
 * The arrowhead every wire ends in, defined once.
 *
 * The drawing library ships a stock arrowhead and it is not used. This one is a
 * thin open chevron: it reads as a direction rather than as a blob, and it is
 * drawn in the same ink as the wire it belongs to.
 *
 * **It is measured in the map's own units, not in multiples of the stroke
 * width.** That matters more than it sounds. A wire's width is the whole of how
 * it says how hard it pushes, and an arrowhead that grew with the width would
 * put that meaning on a second thing — a four-step wire would end in a
 * four-times arrowhead, and the eye would read the head instead of the line. One
 * arrowhead, one size, on every wire.
 */

/** The name the wires reach for their arrowhead by. */
export const ARROWHEAD = "katalyst-arrowhead";

/** The drawing marks every wire shares. No ink of its own and no size. */
export function WireMarks() {
  return (
    <svg className="wire-marks" aria-hidden="true" focusable="false">
      <title>Drawing marks</title>
      <defs>
        <marker
          id={ARROWHEAD}
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerUnits="userSpaceOnUse"
          markerWidth="11"
          markerHeight="11"
          orient="auto-start-reverse"
        >
          <path d="M 1 1 L 9 5 L 1 9" />
        </marker>
      </defs>
    </svg>
  );
}
