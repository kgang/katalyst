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

import { Handle, useStore } from "@xyflow/react";
import { toDay } from "../graph/diff/days";
import { claimLines, SUMMARY_BELOW_ZOOM, TILE_WIDTH, tileHeight } from "../graph/geometry";
import { PORTS, portBox } from "../graph/ports";
import type { Badge, ClaimKind, ClaimView } from "../world";
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
 * What an edit did to this claim, in the words a reader hears rather than the
 * word the code uses. Read out before the claim itself, so a reader who never
 * sees the tile learns the same thing first.
 */
const DIFF_WORDS: Record<string, string> = {
  added: "added by your edit",
  killed: "supposed false by your edit",
  downstream: "your edit can reach this",
  untouched: "your edit cannot reach this",
  shifted: "your edit moved this number",
};

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

/**
 * What a claim's tile says about the edits behind it, in the order they were
 * made.
 *
 * Two badges in a row are drawn as a sequence with an arrow between them, which
 * is the whole point of UX-14: *Supposed · Oct 1 → Retracted · Oct 2 · by "a
 * confirmed military strike on Iranian territory"*. Met as a sequence the rule
 * that a later edit outranks an earlier supposition is obvious; met as a number
 * that moved on its own it reads as a bug.
 *
 * Every badge is also a thing the keyboard can land on, because each one carries
 * a sentence saying what it means, and a reason you cannot reach is not a reason.
 */
function Badges({ badges }: { badges: readonly Badge[] }) {
  // How far the number moved is a reading, not a word about an edit, so it gets
  // a line of its own under the run rather than being strung on the end of it.
  // Two reasons, and the second is the load-bearing one: *Supposed · Oct 1 →
  // Retracted · Oct 2 · by "…"* already runs to three lines on a 280-pixel tile,
  // and a fourth thing on that run pushes a line out of the box. The layout
  // reserves the extra line; see `App.tsx`, where the box is measured.
  const said = badges.filter((badge) => badge.movement !== true);
  const moved = badges.find((badge) => badge.movement === true);
  if (said.length === 0 && moved === undefined) {
    return null;
  }
  return (
    <>
      {said.length === 0 ? null : (
        <p className="tile__badges">
          {said.map((badge, index) => (
            <span className="tile__badge-run" key={badge.words}>
              {index === 0 ? null : (
                <span className="tile__badge-arrow" aria-hidden="true">
                  {" → "}
                </span>
              )}
              <button className="tile__badge" type="button" title={badge.reason} data-badge="words">
                <span className="tile__hidden">{`${badge.reason} `}</span>
                <span className="tile__badge-words">{badge.words}</span>
              </button>
            </span>
          ))}
        </p>
      )}
      {moved === undefined ? null : (
        // Drawn in the number face, so that `.40 ▼ .30` reads as two numbers
        // with a direction between them rather than as a label.
        <p className="tile__badges tile__badges--movement">
          <button className="tile__badge" type="button" title={moved.reason} data-badge="movement">
            <span className="tile__hidden">{`${moved.reason} `}</span>
            <span className="tile__badge-words">{moved.words}</span>
          </button>
        </p>
      )}
    </>
  );
}

/** What a tile needs to draw itself. */
export interface TileProps {
  /** The claim this tile is for. */
  readonly claim: ClaimView;
  /** True when this claim is the one the reader started from. */
  readonly isHypothesis: boolean;
  /**
   * How many versions of the map were run to produce this world's numbers.
   *
   * Absent means nothing computed them, and the model chip says so instead of
   * describing a run that never happened.
   */
  readonly versions?: number;
  /**
   * The height the map reserved for this tile.
   *
   * Usually the same as the tile's own content needs. It differs only in a
   * diff, where one box has to hold whichever of the two paintings is taller, so
   * that flipping between them moves nothing.
   */
  readonly height?: number;
}

/** One claim's tile. */
export function Tile({ claim, isHypothesis, versions, height: reserved }: TileProps) {
  // How far the map is zoomed out. Below the threshold a tile stops showing
  // everything and shows a summary instead — the claim and the three chips —
  // because the alternative is type too small to read. The tile changes what it
  // draws; it never shrinks what it draws.
  const zoom = useStore((state) => state.transform[2]);
  const detail = zoom < SUMMARY_BELOW_ZOOM ? "summary" : "full";

  // Only one claim in four prints why it has no market: the kind that ends the
  // map without an instrument. That reason is a finding — somebody looked and
  // wrote down what they found — and it belongs on the face of the tile. For
  // every other claim "no market" is a fact about the world's plumbing, the
  // chip says it in two words, and the sentence behind it is on the chip's
  // shelf and in what the chip is called when it is read out loud.
  const finding = claim.kind === "not_tradeable" ? claim.beliefs.market.absence : undefined;
  // As tall as this claim's own content, worked out the same way the layout
  // worked it out, so the box the map reserved and the box the browser draws
  // are the same box.
  const height = reserved ?? tileHeight(claim);
  const lines = claimLines(claim.claim);
  // The foot only exists when it has something in it. An empty one would still
  // take a gap above it, and the tile would have a step of dead space at the
  // bottom — which is the whole thing a clamped height is meant to avoid. When
  // the badges arrive, having one of those puts the foot there too.
  const badges = claim.badges ?? [];
  const hasFoot = finding !== undefined || claim.evidence.length > 0 || badges.length > 0;
  // What an edit did to this claim, said in words before the claim itself for a
  // reader who never sees the tile. Absent on a map nobody has edited.
  const diffWords = claim.diff === undefined ? "" : `${DIFF_WORDS[claim.diff] ?? claim.diff}. `;

  return (
    <article
      className="tile"
      data-kind={claim.kind}
      data-detail={detail}
      data-hypothesis={isHypothesis ? "yes" : "no"}
      data-diff={claim.diff ?? "none"}
      style={{
        width: `${TILE_WIDTH}px`,
        height: `${height}px`,
        // How many lines of the claim to show. The same number the height was
        // worked out from, so the claim stops exactly where the box ends.
        ["--tile-claim-lines" as string]: `${lines}`,
      }}
      aria-label={`${diffWords}${KIND_WORDS[claim.kind]}: ${claim.claim}`}
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

      {/* The ports. An arrow that fires once and an arrow that has to keep
          holding are different claims about the world, so they arrive at
          different sockets and leave from different sockets — what a wire means
          is visible where it lands, before you follow it anywhere.

          **Each one's box is written on it rather than left to a stylesheet**,
          because where a port sits depends on how tall this tile turned out to
          be, and because the drawing library is handed these very numbers so
          that it can draw a wire before it has measured anything. `ports.ts`
          works them out; this writes them down; nothing measures them. */}
      {PORTS.map((port) => {
        const box = portBox(height, port);
        return (
          <Handle
            key={port.id}
            type={port.kind}
            position={port.edge}
            id={port.id}
            className={`tile__port tile__port--${port.mode}`}
            style={{
              left: `${box.x}px`,
              // The library's own stylesheet pins a port to the edge it is on
              // and then shifts it by half its own size. Both are said here
              // instead, in full, so that the box on the screen is the box that
              // was declared and there is nothing left to work out.
              right: "auto",
              top: `${box.y}px`,
              width: `${box.width}px`,
              height: `${box.height}px`,
              transform: "none",
            }}
          />
        );
      })}

      <header className="tile__header">
        <span className="tile__kind">{KIND_WORDS[claim.kind]}</span>
        <time className="tile__resolves" dateTime={claim.resolvesBy}>
          {`resolves ${toDay(claim.resolvesBy)}`}
        </time>
      </header>

      <p className="tile__claim">{claim.claim}</p>

      <div className="tile__beliefs">
        <BeliefChip
          owner="model"
          slot={claim.beliefs.model}
          standing={claim.standing}
          versions={versions}
        />
        <BeliefChip owner="user" slot={claim.beliefs.user} />
        <BeliefChip owner="market" slot={claim.beliefs.market} />
      </div>

      {detail === "full" && hasFoot ? (
        // The foot of the tile. It is pushed to the bottom edge as one block, so
        // that on every tile alike the claim is at the top, the beliefs are in
        // the middle and whatever is left sits on the floor — and the eye can
        // read down a column without hunting for the line it wants.
        <div className="tile__foot">
          {finding === undefined ? null : <p className="tile__absence">{finding.reason}</p>}

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

          {/* What the edits behind this claim did to it, in order. Empty on a
              map nobody has edited, and then it takes no room at all. */}
          <Badges badges={badges} />
        </div>
      ) : null}
    </article>
  );
}
