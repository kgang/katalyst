/**
 * A claim, as a card on the map.
 *
 * A tile shows six things and no more, because a seventh always arrives at the
 * cost of the six:
 *
 *   1. the claim, wrapping to three lines and then stopping — never cut in the
 *      middle of a word;
 *   2. three belief chips, the model's, the reader's and a market's, side by
 *      side and never averaged;
 *   3. at most two evidence clippings, each a letter standing for a publication
 *      and one line of what it says;
 *   4. the day the claim is settled by;
 *   5. its outline, which says what kind of claim it is — shape carries that,
 *      never colour;
 *   6. a place for its badges, which arrive with the buttons that earn them.
 *
 * The rest — the full claim, the resolution criteria, the sources, the
 * reasoning behind a number — belongs in the panel beside the map, which is
 * built in the pull request after this one.
 *
 * **The outline is drawn rather than bordered.** The tile has no border of its
 * own; a line drawing sits behind it with a one-pixel stroke at a tenth of the
 * text colour, and its path is what makes a hypothesis look different from a
 * dead end. Four shapes, four kinds, and the shapes survive being printed in
 * grey — which a colour never does.
 */

import { Handle, Position, useStore } from "@xyflow/react";
import { claimLines, SUMMARY_BELOW_ZOOM, TILE_WIDTH, tileHeight } from "../graph/geometry";
import type { ClaimKind, ClaimView } from "../world";
import { BeliefChip } from "./BeliefChip";
import "./tile.css";

/**
 * The four outlines, as line drawings the width and height of a tile.
 *
 * Each one is drawn to the height its own tile turned out to be, because a tile
 * is as tall as its content. Every path is offset by half a pixel so that a
 * one-pixel stroke lands on a pixel boundary instead of straddling two and
 * going soft.
 *
 * - **hypothesis** — the left edge comes to a point. This is where the map
 *   starts: the claim the reader typed, with nothing before it.
 * - **event** — an ordinary rounded box. A step in the middle of the chain.
 * - **market** — the top right corner is cut away, the way a ticket is. There
 *   is something here you could actually trade.
 * - **not tradeable** — the right edge is notched inward. The chain really does
 *   end here, and there is nothing to plug into it.
 *
 * Two of the four cut into the space a word would sit in, so those two tiles are
 * given a wider margin on that side — see `tile.css`. A shape that crosses its
 * own words is not a shape, it is a mistake.
 */
const OUTLINES: Record<ClaimKind, (height: number) => string> = {
  hypothesis: (h) => `M 16.5 0.5 H ${TILE_WIDTH - 0.5} V ${h - 0.5} H 16.5 L 0.5 ${h / 2} Z`,
  event: (h) =>
    `M 6.5 0.5 H ${TILE_WIDTH - 6.5} A 6 6 0 0 1 ${TILE_WIDTH - 0.5} 6.5 V ${h - 6.5} ` +
    `A 6 6 0 0 1 ${TILE_WIDTH - 6.5} ${h - 0.5} H 6.5 A 6 6 0 0 1 0.5 ${h - 6.5} ` +
    `V 6.5 A 6 6 0 0 1 6.5 0.5 Z`,
  market: (h) => `M 0.5 0.5 H ${TILE_WIDTH - 18.5} L ${TILE_WIDTH - 0.5} 18.5 V ${h - 0.5} H 0.5 Z`,
  not_tradeable: (h) =>
    `M 0.5 0.5 H ${TILE_WIDTH - 0.5} V ${h / 2 - 14} L ${TILE_WIDTH - 14.5} ${h / 2} ` +
    `L ${TILE_WIDTH - 0.5} ${h / 2 + 14} V ${h - 0.5} H 0.5 Z`,
};

/** What each kind is called on screen. No underscores and no code names. */
const KIND_WORDS: Record<ClaimKind, string> = {
  hypothesis: "hypothesis",
  event: "event",
  market: "market",
  not_tradeable: "not tradeable",
};

/**
 * Print a date the way the map prints one: `Nov 1`.
 *
 * Read as a day in the map's own reckoning rather than in the reader's time
 * zone, because a claim settled on the first of November is settled on the
 * first of November wherever the reader happens to be sitting.
 */
export function toDay(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

/** One published item, as a clipping: a letter for the publication and one line. */
function Clipping({
  monogram,
  host,
  line,
  direction,
}: {
  monogram: string;
  host: string;
  line: string;
  direction: 1 | -1;
}) {
  // A sign, not a colour: "+" for an item that supports the claim, "−" for one
  // that cuts against it. A reader who cannot tell two hues apart loses nothing.
  const sign = direction === 1 ? "+" : "−";
  const inWords = direction === 1 ? "supports this claim" : "cuts against this claim";
  return (
    <li className="tile__clipping">
      <span className="tile__monogram" aria-hidden="true">
        {monogram}
      </span>
      <span className="tile__clipping-sign" aria-hidden="true">
        {sign}
      </span>
      <span className="tile__clipping-line">
        <span className="tile__hidden">{`${host}, ${inWords}: `}</span>
        {line}
      </span>
    </li>
  );
}

/** What a tile needs to draw itself. */
export interface TileProps {
  /** The claim this tile is for. */
  readonly claim: ClaimView;
  /** True when this claim is the one the reader started from. */
  readonly isHypothesis: boolean;
}

/** One claim's tile. */
export function Tile({ claim, isHypothesis }: TileProps) {
  // How far the map is zoomed out. Below the threshold a tile stops showing
  // everything and shows a summary instead — the claim and the three chips —
  // because the alternative is type too small to read. The tile changes what it
  // draws; it never shrinks what it draws.
  const zoom = useStore((state) => state.transform[2]);
  const detail = zoom < SUMMARY_BELOW_ZOOM ? "summary" : "full";

  const marketAbsence = claim.beliefs.market.absence;
  // As tall as this claim's own content, worked out the same way the layout
  // worked it out, so the box the map reserved and the box the browser draws
  // are the same box.
  const height = tileHeight(claim);
  const lines = claimLines(claim.claim);
  // The foot only exists when it has something in it. An empty one would still
  // take a gap above it, and the tile would have a step of dead space at the
  // bottom — which is the whole thing a clamped height is meant to avoid. When
  // the badges arrive, having one of those puts the foot there too.
  const hasFoot = marketAbsence !== undefined || claim.evidence.length > 0;

  return (
    <article
      className="tile"
      data-kind={claim.kind}
      data-detail={detail}
      data-hypothesis={isHypothesis ? "yes" : "no"}
      style={{
        width: `${TILE_WIDTH}px`,
        height: `${height}px`,
        // How many lines of the claim to show. The same number the height was
        // worked out from, so the claim stops exactly where the box ends.
        ["--tile-claim-lines" as string]: `${lines}`,
      }}
      aria-label={`${KIND_WORDS[claim.kind]}: ${claim.claim}`}
    >
      <svg
        className="tile__outline"
        width={TILE_WIDTH}
        height={height}
        viewBox={`0 0 ${TILE_WIDTH} ${height}`}
        aria-hidden="true"
        focusable="false"
      >
        <path d={OUTLINES[claim.kind](height)} />
      </svg>

      {/* The sockets. An arrow that fires once and an arrow that has to keep
          holding are different claims about the world, so they arrive at
          different sockets and leave from different sockets — what a wire means
          is visible where it lands, before you follow it anywhere. */}
      <Handle
        type="target"
        position={Position.Left}
        id="in-trigger"
        className="tile__port tile__port--trigger"
        style={{ top: "38%" }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="in-sustain"
        className="tile__port tile__port--sustain"
        style={{ top: "62%" }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="out-trigger"
        className="tile__port tile__port--trigger"
        style={{ top: "38%" }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="out-sustain"
        className="tile__port tile__port--sustain"
        style={{ top: "62%" }}
      />

      <header className="tile__header">
        <span className="tile__kind">{KIND_WORDS[claim.kind]}</span>
        <time className="tile__resolves" dateTime={claim.resolvesBy}>
          {`resolves ${toDay(claim.resolvesBy)}`}
        </time>
      </header>

      <p className="tile__claim">{claim.claim}</p>

      <div className="tile__beliefs">
        <BeliefChip owner="model" slot={claim.beliefs.model} standing={claim.standing} />
        <BeliefChip owner="user" slot={claim.beliefs.user} />
        <BeliefChip owner="market" slot={claim.beliefs.market} />
      </div>

      {detail === "full" && hasFoot ? (
        // The foot of the tile. It is pushed to the bottom edge as one block, so
        // that on every tile alike the claim is at the top, the beliefs are in
        // the middle and whatever is left sits on the floor — and the eye can
        // read down a column without hunting for the line it wants.
        <div className="tile__foot">
          {marketAbsence === undefined ? null : (
            <p className="tile__absence">{marketAbsence.reason}</p>
          )}

          {claim.evidence.length === 0 ? null : (
            <ul className="tile__clippings">
              {claim.evidence.map((item) => (
                <Clipping
                  key={item.line}
                  monogram={item.monogram}
                  host={item.host}
                  line={item.line}
                  direction={item.direction}
                />
              ))}
            </ul>
          )}

          {/* Where a claim's badges go — *Supposed · Oct 1*, *Retracted · Oct 2
              · by "…"*, *Added*, *Retuned*. Empty here, because nothing on this
              screen can edit the map yet: the buttons that earn a badge arrive
              with the branch panel. The space is kept so that a tile does not
              change height the day they do. */}
          <div className="tile__badges" />
        </div>
      ) : null}
    </article>
  );
}
