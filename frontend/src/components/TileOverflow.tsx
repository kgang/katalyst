/**
 * The tile that stands in for the tiles a column has no room for.
 *
 * A column of the map shows seven claims. When a map fans out wider than that,
 * the eighth and everything after it collapse into this one tile, which says
 * how many there are. The cap is what keeps a wide map readable instead of a
 * wall; saying the number out loud is what keeps it honest, because a map that
 * quietly dropped claims would be lying about its own shape.
 *
 * It is drawn the same size as a claim's tile and with the same one-pixel
 * outline, so the column keeps its rhythm — but with a dashed line rather than
 * a solid one, because it is not a claim.
 */

import { TILE_HEIGHT, TILE_WIDTH } from "../graph/geometry";
import "./tile.css";

/** What the collapsed tile needs to draw itself. */
export interface TileOverflowProps {
  /** How many claims in this column are not drawn. */
  readonly count: number;
}

/** The "+n more" tile at the foot of a column that ran out of room. */
export function TileOverflow({ count }: TileOverflowProps) {
  const claims = count === 1 ? "claim" : "claims";
  return (
    <article
      className="tile tile--overflow"
      style={{ width: `${TILE_WIDTH}px`, height: `${TILE_HEIGHT}px` }}
      aria-label={`${count} more ${claims} in this column, not drawn`}
    >
      <svg
        className="tile__outline"
        width={TILE_WIDTH}
        height={TILE_HEIGHT}
        viewBox={`0 0 ${TILE_WIDTH} ${TILE_HEIGHT}`}
        aria-hidden="true"
        focusable="false"
      >
        <rect
          x="0.5"
          y="0.5"
          width={TILE_WIDTH - 1}
          height={TILE_HEIGHT - 1}
          rx="6"
          strokeDasharray="4 4"
        />
      </svg>
      <p className="tile__overflow-count" aria-hidden="true">
        {`+${count} more`}
      </p>
      <p className="tile__overflow-line">
        {`${claims} in this column that there is no room to draw side by side. They are on the map.`}
      </p>
    </article>
  );
}
