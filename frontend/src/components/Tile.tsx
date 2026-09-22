/**
 * A claim, as a card on the map.
 *
 * A tile shows six things and no more, because a seventh always arrives at the
 * cost of the six:
 *
 *   1. the claim, wrapping to three lines and then stopping — never cut in the
 *      middle of a word;
 *   2. the belief chips, side by side and never averaged: the model's always,
 *      and the reader's and a market's where they hold a number. A column with
 *      nothing in it is two thirds of the belief area on a generated map, so
 *      it is not drawn — the absence and its own reason are read in full in the
 *      panel beside the map, which is where a reason has room to be a sentence;
 *   3. at most two evidence clippings, each a letter standing for a publication
 *      and one line of what it says;
 *   4. the day the claim is settled by;
 *   5. its outline, which says what kind of claim it is. Shape says it first
 *      and always; at the two ends of a map — the hypothesis and a tradeable
 *      outcome — a hue says it as well, so the eye lands on those two before
 *      it reads anything. Never the hue on its own: the shape and the printed
 *      word are both still there, so the kind survives a grey print;
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
 * grey — which a colour never does. Two of the four take a hue on that same
 * stroke as well (`tile.css` says which and why); the shape underneath is what
 * the grey print keeps.
 *
 * **It has three forms, and the zoom chooses between them** — `geometry.ts`
 * owns the two thresholds and both are worked out from the rule that no word is
 * ever drawn under eleven pixels. Near, it draws the six things above. Further
 * out it drops the heading and the foot and sets what is left in the largest
 * type size. Further out still, past the zoom at which even that size would
 * fall under eleven pixels, it draws **only its outline** — the shape and its
 * kind's hue, and not one word. Each step draws less; no step draws the same
 * thing smaller.
 */

import { Handle, useStore } from "@xyflow/react";
import { toDay } from "../graph/diff/days";
import { claimLines, detailAt, TILE_WIDTH, tileHeight } from "../graph/geometry";
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

/**
 * How big a mark has to be, in the map's own coordinates, to be seen at the
 * furthest the map zooms out.
 *
 * **Measured against the floor rather than chosen** *(2026-09-22)*. A mark has
 * to be about six pixels on the reader's screen to be a mark at all, and at the
 * floor the map is drawn at about a sixth of life size — so about forty pixels
 * in the map's own coordinates. Rounded up to the eight-pixel grid the whole
 * interface sits on: forty-eight.
 *
 * The greyscale check is what this is for. At the near sizes a tradeable
 * outcome's corner is cut eighteen pixels along each edge and a dead end is
 * notched fourteen deep, and both read from a foot away. At the floor they are
 * under three pixels — gone — and what was left telling those two kinds apart
 * was the hue, which is the one thing nothing in this product is allowed to
 * carry alone (INV-12: nothing is carried by hue alone). Measured on the
 * replayed generated map at the floor, in grey, on 2026-09-22: the four kinds
 * were two.
 */
const FAR_MARK = 48;

/**
 * The same four shapes, drawn for the zoom at which the shape is all there is.
 *
 * Each is its near form with its one distinguishing mark grown to `FAR_MARK`,
 * and nothing else changed — the same box, the same four shapes, the same thing
 * said louder. An `event` is the plain rectangle at both sizes, because what
 * says *event* is the absence of a mark and an absence cannot be grown.
 *
 * **The cut corner is fifty-six rather than forty-eight**, because it is
 * measured along the edge and runs at forty-five degrees: fifty-six along each
 * edge is forty deep, which is the figure `FAR_MARK` is.
 */
const FAR_CUT = 56;

const SILHOUETTES: Record<ClaimKind, (height: number) => string> = {
  hypothesis: (h) =>
    `M ${FAR_MARK + 0.5} 0.5 H ${TILE_WIDTH - 0.5} V ${h - 0.5} H ${FAR_MARK + 0.5} L 0.5 ${h / 2} Z`,
  // The one that does not grow, and the one shape here that is the near shape
  // itself rather than a copy of it: what says *event* is the absence of a
  // mark, and an absence cannot be made bigger.
  event: OUTLINES.event,
  market: (h) =>
    `M 0.5 0.5 H ${TILE_WIDTH - FAR_CUT - 0.5} L ${TILE_WIDTH - 0.5} ${FAR_CUT + 0.5} ` +
    `V ${h - 0.5} H 0.5 Z`,
  not_tradeable: (h) =>
    `M 0.5 0.5 H ${TILE_WIDTH - 0.5} V ${h / 2 - FAR_MARK} ` +
    `L ${TILE_WIDTH - FAR_MARK - 0.5} ${h / 2} L ${TILE_WIDTH - 0.5} ${h / 2 + FAR_MARK} ` +
    `V ${h - 0.5} H 0.5 Z`,
};

/**
 * The one corner a kind draws twice.
 *
 * A tradeable outcome's outline has its top right corner cut away like a
 * ticket. That diagonal is drawn a second time, over the outline, at twice the
 * width, so the corner reads from across the map rather than from a foot away.
 * It is the same line the outline already draws — no new mark, and nothing a
 * grey print would lose — and `tile.css` is the only place that says what
 * colour it takes.
 *
 * Only one kind has one. The other three draw their outline and nothing else.
 */
const CUT_CORNERS: Partial<Record<ClaimKind, string>> = {
  market: `M ${TILE_WIDTH - 18.5} 0.5 L ${TILE_WIDTH - 0.5} 18.5`,
};

/** The same second stroke, on the corner the silhouette cuts. */
const FAR_CUT_CORNERS: Partial<Record<ClaimKind, string>> = {
  market: `M ${TILE_WIDTH - FAR_CUT - 0.5} 0.5 L ${TILE_WIDTH - 0.5} ${FAR_CUT + 0.5}`,
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
   * The height the map reserved for this tile.
   *
   * Usually the same as the tile's own content needs. It differs only in a
   * diff, where one box has to hold whichever of the two paintings is taller, so
   * that flipping between them moves nothing.
   */
  readonly height?: number;
}

/** One claim's tile. */
export function Tile({ claim, isHypothesis, height: reserved }: TileProps) {
  // How far the map is zoomed out, and which of the tile's three forms that
  // asks for. Below the first threshold the tile stops showing everything and
  // shows a summary instead — the claim and its chips — because the alternative
  // is type too small to read. Below the second it stops showing words at all
  // and shows only its shape, because there is no type size left to fall back
  // to. The tile changes what it draws; it never shrinks what it draws.
  const zoom = useStore((state) => state.transform[2]);
  const detail = detailAt(zoom);
  // Which set of the four shapes to draw. The far set is the near set with each
  // kind's one distinguishing mark grown until it survives being drawn at a
  // sixth of life size — because out there the shape is the only thing saying
  // what kind of claim this is, and a shape that has shrunk to nothing leaves
  // the hue saying it alone.
  const shapes = detail === "silhouette" ? SILHOUETTES : OUTLINES;
  const cuts = detail === "silhouette" ? FAR_CUT_CORNERS : CUT_CORNERS;

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
        <path d={shapes[claim.kind](height)} />
        {cuts[claim.kind] === undefined ? null : (
          <path className="tile__cut" d={cuts[claim.kind]} />
        )}
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

      {/* **The silhouette draws none of this.** Out past the second threshold
          every word on the tile would land under eleven pixels however large it
          was set, so the words are not set smaller — they are not drawn. What
          the tile is still saying is drawn above: the shape that says what kind
          of claim it is, in the hue two of the four kinds take. Which claim it
          is, a reader asks for by pressing it, and the panel beside the map
          answers in full. The name it is read out by is on the box itself and
          does not change with the zoom, so a reader who hears the map rather
          than seeing it loses nothing out here. */}
      {detail === "silhouette" ? null : (
        <>
          <header className="tile__header">
            <span className="tile__kind">{KIND_WORDS[claim.kind]}</span>
            <time className="tile__resolves" dateTime={claim.resolvesBy}>
              {`resolves ${toDay(claim.resolvesBy)}`}
            </time>
          </header>

          <p className="tile__claim">{claim.claim}</p>

          <div className="tile__beliefs">
            {/* The model's column is always drawn — it is the one number every
                claim on every map has, and while a map is still being built it
                is the column that says so. The reader's and a venue's are drawn
                only where they hold a number; where they do not, the absence and
                its reason are read in full in the panel beside the map. */}
            <BeliefChip owner="model" slot={claim.beliefs.model} standing={claim.standing} />
            {claim.beliefs.user.reading === undefined ? null : (
              <BeliefChip owner="user" slot={claim.beliefs.user} />
            )}
            {claim.beliefs.market.reading === undefined ? null : (
              <BeliefChip owner="market" slot={claim.beliefs.market} />
            )}
          </div>

          {detail === "full" && hasFoot ? (
            // The foot of the tile. It is pushed to the bottom edge as one
            // block, so that on every tile alike the claim is at the top, the
            // beliefs are in the middle and whatever is left sits on the floor —
            // and the eye can read down a column without hunting for the line it
            // wants.
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

              {/* What the edits behind this claim did to it, in order. Empty on
                  a map nobody has edited, and then it takes no room at all. */}
              <Badges badges={badges} />
            </div>
          ) : null}
        </>
      )}
    </article>
  );
}
