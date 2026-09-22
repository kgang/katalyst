/**
 * One arrow on the map, drawn so that the picture says what the arrow says.
 *
 * Five things at once, and **not one of them is a colour**:
 *
 * | What | How it is drawn | What survives a grey print |
 * |---|---|---|
 * | What kind of push it is | The stroke's pattern: dot-dash for a one-time spike, solid for a switch that holds, dashes that grow for one that builds | the pattern |
 * | How hard it pushes | The stroke's width, in four steps, from the size of the push regardless of its sign | the width |
 * | Whether it has to keep holding | Two parallel strokes when it does, one when it fires once | the doubling |
 * | Whether it loops back | It runs over the top of the map and carries the delay | the loop |
 * | Where it came from | A mark of one, two or three dots at the tail | the count of dots |
 *
 * **The stroke says one thing and one thing only: what kind of push this is.**
 * It used to be asked to carry where the arrow came from as well, and it cannot:
 * a wire cannot be dot-dash because it is a spike and dashed because it was
 * merely argued at the same time — it would be neither, legibly. One channel per
 * meaning. So where it came from moved to the mark at the tail, and the exact
 * word of the seven moved to the panel, where there is room for it.
 *
 * **A push's sign is not a direction of financial effect**, and this file is
 * where that matters most. The arrow into *Brent settles below $68* is `+1.6` —
 * positive, because it makes that claim come out true more often — and the
 * price it describes is falling. Colour that arrow amber and you have said the
 * opposite of what it means. So no wire reads a direction colour, ever; the sign
 * is printed and the word says *toward* or *against*.
 *
 * Nothing here does arithmetic on the map's numbers. Choosing a width or a band
 * of words is a comparison against fixed thresholds, and everything else in this
 * file is pixel geometry.
 */

import {
  BaseEdge,
  type Edge,
  EdgeLabelRenderer,
  type EdgeProps,
  getSmoothStepPath,
} from "@xyflow/react";
import { OriginMark } from "../../components/OriginMark";
import type { Known, LinkMode, LinkShape, Provenance, Ranged } from "../../world";
import type { TileDetail } from "../geometry";
import { strokeFor, widthFor } from "./encodings";
import { MARK_STANDOFF } from "./plates";
import {
  corridorCorners,
  longestRunMidpoint,
  type Point,
  type RoutePlan,
  roundedPath,
  skyCorners,
} from "./route";
import { WireChip } from "./WireChip";
import "./wires.css";

/** Everything a wire needs beyond where its two ends are. */
export interface WireData extends Record<string, unknown> {
  /** What the push does over time. The stroke's pattern, and nothing else. */
  readonly shape: LinkShape;
  /** How hard it pushes, signed, at full precision. The stroke's width. */
  readonly strength: number;
  /** Whether the push survives its cause going away. Doubled when it does. */
  readonly mode: LinkMode;
  /** Days from the cause becoming true to the push reaching full size. */
  readonly lag: number;
  /** True when this arrow is a market feeding back on the world. */
  readonly reflexive: boolean;
  /** Where the arrow and its number came from. The mark at the tail. */
  readonly provenance: Provenance;
  /** The likelihood with this arrow's cause supposed true. Absent in this build. */
  readonly conditional: Known<Ranged>;
  /** How this wire gets from one end to the other, worked out from the layout. */
  readonly plan?: RoutePlan;
  /** True when the hover lens has put this wire off the path. */
  readonly dimmed?: boolean;
  /**
   * Which of the three forms the map is drawing, worked out from the zoom by
   * `geometry.ts` and handed to every wire at once.
   *
   * The plate follows the tile: whole near to, the push alone once a
   * thirteen-pixel word would land under eleven on the glass, and gone
   * altogether once there is no type size left that would clear the floor. Left
   * out, the wire draws its whole plate, which is what it does when it is drawn
   * on its own in a test.
   */
  readonly detail?: TileDetail;
  /**
   * How far the mark at this arrow's tail is moved off the wire, so that two
   * arrows leaving the same socket do not draw their marks on top of each other.
   */
  readonly tailOffset?: number;
  /**
   * Where this wire's plate goes, worked out for the whole map at once.
   *
   * A wire cannot see its neighbours, and on a map with two worlds laid over
   * each other that is not enough: plates began landing on one another. So the
   * spot is decided in one pass over every wire — `plates.ts` — and handed in.
   * Left out, the wire falls back to placing its own, which is what it does when
   * it is drawn on its own in a test.
   */
  readonly plateAt?: { readonly x: number; readonly y: number };
  /**
   * Which column of the map this wire belongs to, for the one animation the map
   * spends on causality.
   *
   * The wire itself is revealed by a stylesheet rule keyed on a class the canvas
   * puts on it. Its plate and its mark are drawn in another layer entirely, so
   * they are given the same delay here — otherwise the reading arrives a beat
   * before the wire it is a reading of.
   */
  readonly wave?: number;
}

/** A wire as the canvas knows it. */
export type CausalEdge = Edge<WireData, "causal">;

/**
 * How far the plate is nudged along the wire, away from the mark at its tail.
 *
 * The gutter between one column and the next is 120 pixels, and it has to hold
 * both: the mark takes the first twenty at the tail end, and the plate takes the
 * rest. Without the nudge the plate would sit in the middle of the gutter and
 * swallow the mark.
 */
const PLATE_NUDGE = 16;

/** How round a corner drawn by the library's own router is. */
const CORNER = 8;

/**
 * How tall a stacked plate is, near enough.
 *
 * Only used to decide whether a wire drops far enough for its plate to sit in
 * the middle of the drop. Nothing is positioned by it, so it does not have to be
 * exact — and it is written down here rather than measured off the drawn plate,
 * because measuring would make where a plate goes depend on the order the page
 * happened to draw things in.
 */
const PLATE_HEIGHT = 96;

/** How far clear of the wire a plate sits when it cannot sit on it. */
const PLATE_STANDOFF = 8;

/** The class names that carry a wire's five encodings into the stylesheet. */
function wireClasses(data: WireData, width: number, selected: boolean): string {
  return [
    "wire",
    `wire--${data.shape}`,
    `wire--${data.mode}`,
    `wire--step-${width}`,
    data.reflexive ? "wire--reflexive" : "",
    data.dimmed ? "is-dimmed" : "",
    selected ? "is-selected" : "",
  ]
    .filter((one) => one !== "")
    .join(" ");
}

/** What a wire draws on the glass rather than in the drawing: its mark and its plate. */
export interface WireLabelsProps {
  /** Everything the wire knows about the arrow. */
  readonly data: WireData;
  /** Where the wire leaves its cause. */
  readonly sourceX: number;
  /** The height it leaves at. */
  readonly sourceY: number;
  /** Where the plate sits. */
  readonly plateAt: Point;
  /** The shape of the room the plate has. */
  readonly plateLayout: "stacked" | "inline";
  /** Where the plate's own box is pinned to the point it was given. */
  readonly plateAnchor: string;
  /** True when the panel beside the map is open on this arrow. */
  readonly selected: boolean;
}

/**
 * The mark at the tail and the plate in the middle.
 *
 * These are drawn as ordinary page elements rather than as part of the drawing,
 * because words set in a drawing cannot wrap, cannot be read out by a screen
 * reader as words, and cannot be styled from the same stylesheet as the rest of
 * the interface. They are its own component so that they can be looked at on
 * their own, without a whole map around them.
 */
export function WireLabels({
  data,
  sourceX,
  sourceY,
  plateAt,
  plateLayout,
  plateAnchor,
  selected,
}: WireLabelsProps) {
  // The wire itself is revealed a column at a time by a rule in `canvas.css`,
  // keyed on a class the canvas puts on it. Its plate and its mark are drawn in
  // another layer, outside that rule's reach, so they are given the same delay
  // here — otherwise the reading of a wire arrives before the wire.
  const waveDelay = {
    "--wave-delay": `calc(${data.wave ?? 0} * var(--duration-stagger))`,
  } as React.CSSProperties;
  // Drawn on its own, with no map around it, a wire is at life size and draws
  // its whole plate.
  const plateDetail = data.detail ?? "full";

  return (
    <>
      {/* The mark that says where this arrow came from, at the tail, where the
          arrow leaves its cause. The head already has the arrowhead, and a
          receipt belongs where the claim was made. */}
      <div
        className="wire-mark"
        data-dimmed={data.dimmed ? "yes" : "no"}
        style={{
          ...waveDelay,
          transform:
            `translate(0, -50%) translate(${sourceX + MARK_STANDOFF}px, ` +
            `${sourceY + (data.tailOffset ?? 0)}px)`,
        }}
      >
        <OriginMark provenance={data.provenance} use="alone" />
      </div>

      {/* The plate, which follows the tile through the same three forms at the
          same two thresholds. Below the first it keeps the signed push alone,
          set large enough to clear the eleven-pixel floor. Below the second it
          is **not drawn at all**: a plate is words, there is no size left that
          would clear the floor, and drawing an empty box in its place would be
          a mark that says nothing. The stroke still says what kind of push the
          wire is, and the words are one press away in the panel. */}
      {plateDetail === "silhouette" ? null : (
        <div
          className="wire-plate"
          data-detail={plateDetail}
          data-layout={plateLayout}
          data-dimmed={data.dimmed ? "yes" : "no"}
          data-selected={selected ? "true" : "false"}
          style={{
            ...waveDelay,
            transform: `translate(-50%, ${plateAnchor}) translate(${plateAt[0]}px, ${plateAt[1]}px)`,
          }}
        >
          <WireChip
            strength={data.strength}
            lag={data.lag}
            conditional={data.conditional}
            detail={plateDetail}
            layout={plateLayout}
            reflexive={data.reflexive}
          />
        </div>
      )}
    </>
  );
}

/**
 * Draw one wire.
 *
 * The stroke is painted twice for an arrow that has to keep holding: once wide
 * in the wire's own ink, and once narrower in the colour of the page, which
 * leaves two parallel lines with a clear gap down the middle. Both passes use
 * the same dashes, so the gap only appears where there is ink to split.
 */
export function CausalWire({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  selected,
  data,
}: EdgeProps<CausalEdge>) {
  if (data === undefined) {
    return null;
  }
  const plan: RoutePlan = data.plan ?? { kind: "direct" };
  const drawing = strokeFor(data.shape);
  const width = widthFor(data.strength);

  // Where the wire goes, and where its plate sits. The ordinary route is the
  // drawing library's own; the other two are ours, because the library has no
  // idea where the tiles ended up and would take both of them straight through
  // one — and a wire that disappears behind a tile has told the reader that the
  // tile causes what the wire causes, which is a lie the picture tells all by
  // itself.
  let path: string;
  let chipAt: Point;
  if (plan.kind === "direct") {
    const [drawn, labelX, labelY] = getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      sourcePosition,
      targetPosition,
      borderRadius: CORNER,
    });
    path = drawn;
    chipAt = [labelX, labelY];
  } else {
    const corners =
      plan.kind === "sky"
        ? skyCorners(sourceX, sourceY, targetX, targetY, plan.skyY)
        : corridorCorners(sourceX, sourceY, targetX, targetY, plan);
    path = roundedPath(corners);
    chipAt = longestRunMidpoint(corners);
  }

  const doubled = data.mode === "sustain";
  // Two parallel lines of `width`, with a clear gap between them, come to one
  // stroke of twice the width plus the gap — with the gap painted back out in
  // the colour of the page.
  const outer = doubled ? width * 2 + 2 : width;
  const dashes = drawing.dashes ?? undefined;
  // Measured in hundredths of this wire's own length when the pattern has to run
  // its course exactly once from tail to head, whatever the wire's length.
  const pathLength = drawing.growsAlongTheWire ? 100 : undefined;

  // Where the plate sits, which is three different answers for the three routes.
  //
  // A wire that takes the ordinary route crosses one gutter, and that gutter has
  // to hold the mark at the tail as well as the plate — so the plate moves along
  // the wire, away from the tail.
  //
  // A wire that skips a column turns into its corridor in the gutter just after
  // its cause, and a gutter is the one strip of the map with nothing in it. The
  // plate goes there rather than halfway along the corridor, which would put it
  // over the tile the corridor runs past.
  //
  // A wire that runs over the top of the map has nothing but sky around it.
  // A wire that crosses one gutter drops as far as its two sockets are apart,
  // and on this map that is anything from two pixels to five hundred. Where the
  // drop is long the plate sits in the middle of it and the wire shows above and
  // below. Where it is short there is no middle to sit in, and a plate on the
  // wire would cover the whole of it — so the plate steps up and sits just clear
  // of the wire instead, and what the stroke says can be read again.
  const drop = targetY > sourceY ? targetY - sourceY : sourceY - targetY;
  const ridesAside = plan.kind === "direct" && drop < PLATE_HEIGHT;
  // **Which side it steps to is decided by the socket the wire leaves.** A tile
  // has two: an arrow that fires once leaves the upper one and an arrow that has
  // to keep holding leaves the lower one. So the first kind's plates take the
  // space above the wire and the second kind's take the space below, and two
  // plates from one tile can never land on each other — or on the marks at the
  // other socket's tails, which is what went wrong before this rule existed.
  const asideBelow = ridesAside && data.mode === "sustain";
  const ownPlateAt: Point = asideBelow
    ? [chipAt[0], (targetY > sourceY ? targetY : sourceY) + PLATE_STANDOFF]
    : ridesAside
      ? [chipAt[0], (targetY < sourceY ? targetY : sourceY) - PLATE_STANDOFF]
      : plan.kind === "direct"
        ? [chipAt[0] + PLATE_NUDGE, chipAt[1]]
        : plan.kind === "corridor"
          ? [(plan.fromX + plan.toX) / 2, plan.corridorY]
          : chipAt;

  // The spot the whole-map pass gave this plate, when there was one. It is
  // already the middle of the plate's box, so nothing is pinned to an edge.
  const planned = data.plateAt;
  const plateAt: Point = planned === undefined ? ownPlateAt : [planned.x, planned.y];

  /** Where the plate's own box is pinned to the point above. */
  const plateAnchor =
    planned !== undefined ? "-50%" : asideBelow ? "0" : ridesAside ? "-100%" : "-50%";

  const plateLayout = plan.kind === "direct" ? "stacked" : "inline";

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        className={wireClasses(data, width, selected === true)}
        style={{ strokeWidth: outer, strokeDasharray: dashes }}
        pathLength={pathLength}
      />
      {doubled ? (
        // The gap down the middle. It is the same path drawn again, narrower and
        // in the colour of the page, which turns one stroke into two.
        <path
          className="wire__split"
          d={path}
          style={{ strokeDasharray: dashes }}
          pathLength={pathLength}
        />
      ) : null}

      <EdgeLabelRenderer>
        <WireLabels
          data={data}
          sourceX={sourceX}
          sourceY={sourceY}
          plateAt={plateAt}
          plateLayout={plateLayout}
          plateAnchor={plateAnchor}
          selected={selected === true}
        />
      </EdgeLabelRenderer>
    </>
  );
}
