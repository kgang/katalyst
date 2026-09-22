/**
 * The map: tiles, wires, panning and zooming.
 *
 * The drawing library owns four things and no more — panning, zooming, working
 * out what is under the pointer, and working out where each wire's two ends are
 * (the stroke between them is drawn by us). It is not told to find those ports: where each one sits is declared, in `ports.ts`, and
 * handed over with the tile's box. Everything you can see is ours. That is why
 * only the library's bare stylesheet is imported below and never its full one:
 * the full one carries the library's own look, and a tool that looks like the
 * library it was built with looks like a demo. A check in `npm run lint` fails
 * the build if the full one ever appears in this tree.
 *
 * Three things this file works out that no single wire could work out for
 * itself, because a wire cannot see where the other tiles are:
 *
 *   1. **How each wire is routed.** Most arrows join neighbouring columns and
 *      take the ordinary route. An arrow that skips a column would run straight
 *      through the tile in between and disappear behind it, so it is given a
 *      clear corridor to travel along instead; and the one arrow that runs
 *      backwards is sent over the top of the map, where there is nothing to
 *      cross.
 *   2. **The hover lens.** Point at a claim and everything not on its path —
 *      neither one of its causes nor one of the things it causes — drops to
 *      fifteen per cent.
 *   3. **Whether a wire's plate has room for its words.** It follows the tile
 *      through the same three forms at the same two thresholds: near, the whole
 *      plate; below the first, the push alone, set large; below the second, no
 *      plate at all, because a plate is words and out there the map draws none.
 *      Nothing is scaled down to dodge the eleven-pixel rule.
 */

import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  useStore,
} from "@xyflow/react";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xyflow/react/dist/base.css";
import { SkeletonTile } from "../components/SkeletonTile";
import { Tile } from "../components/Tile";
import { TileOverflow } from "../components/TileOverflow";
import type { Edges } from "../components/useTheEdges";
import { edgeMarks, NOTHING_BEYOND } from "../components/useTheEdges";
import type { MapKeys } from "../keyboard/useMapKeys";
import { useMapKeys } from "../keyboard/useMapKeys";
import type { Selection, WorldView } from "../world";
import { NOT_ON_THIS_MAP } from "../world/naming";
import { detailAt, firstFrame, LARGEST_ZOOM, SMALLEST_ZOOM, TILE_WIDTH } from "./geometry";
import { assignLayers } from "./layers";
import { useLayout } from "./layoutRunner";
import { type PlacedBox, whatIsOnTheGlass } from "./onTheGlass";
import { mayLandAgain } from "./theKeyboard";
import {
  type ClaimNode,
  type MapEdge,
  type MapNode,
  OVERFLOW_PREFIX,
  type OverflowNode,
  RESERVED_PREFIX,
  type ReservedBox,
  type SkeletonNode,
  toFlow,
} from "./toFlow";
import { CausalWire } from "./wires/CausalWire";
import { onThePathFrom } from "./wires/lens";
import { planPlates } from "./wires/plates";
import { type Box, planRoutes, SKY_GAP, tailOffsets } from "./wires/route";
import { ARROWHEAD, WireMarks } from "./wires/WireMarks";
import "./canvas.css";

/** The two kinds of box the map draws. Defined once, outside render, so the
 * drawing library never has to rebuild its tiles because the object changed. */
const TILE_TYPES = {
  claim: ({ data }: { data: ClaimNode["data"] }) => (
    <Tile claim={data.claim} isHypothesis={data.isHypothesis} height={data.height} />
  ),
  overflow: ({ data }: { data: OverflowNode["data"] }) => <TileOverflow count={data.count} />,
  skeleton: ({ data }: { data: SkeletonNode["data"] }) => <SkeletonTile words={data.words} />,
};

/** One kind of wire, ours, saying five things at once. */
const WIRE_TYPES = { causal: CausalWire };

/** What the map needs beyond the world it draws. */
interface SurfaceProps {
  /** The world to draw. */
  readonly world: WorldView;
  /** What the panel beside the map is open on. */
  readonly selection: Selection;
  /** Called when the reader selects a claim or an arrow, by pointer or by keyboard. */
  readonly onSelect: (selection: Selection) => void;
  /**
   * Called only when the reader **pointed at** one, and never when the keyboard
   * merely landed on it.
   *
   * Both fill the panel — `onSelect` says so and is unchanged. This is the
   * narrower fact, and one thing needs it: a panel the reader folded away stays
   * folded while they walk the map, and comes back when they point at something
   * to read. Every screen may ignore it.
   */
  readonly onPointedAt?: (selection: Selection) => void;
  /** Which claim the keyboard is on. Held outside the map, because the keys are. */
  readonly focused: string | null;
  /** Put the keyboard on a claim. */
  readonly onFocused: (id: string | null) => void;
  /**
   * How tall to draw each tile, when a diff needs one box to hold two paintings.
   * Left out, each tile is as tall as its own content.
   */
  readonly heights?: ReadonlyMap<string, number>;
  /**
   * Which map this is: the base map, or the base map with one branch folded on.
   *
   * Both paintings of one diff share it, so flipping between them moves nothing.
   * Opening a different branch changes it, and the union of the two worlds is
   * then laid out again from scratch — one layout, two paintings.
   */
  readonly mapKey: string;
  /** Everything the keys that are not about moving are wired to. */
  readonly keys: MapKeys;
  /** Say what the last keystroke did, under the map. */
  readonly onStatus: (line: string) => void;
  /**
   * The reader asked to see the claims a column had no room for.
   *
   * The collapsed tile does not expand: it opens the outline, filtered to that
   * column. The outline is built from the world rather than from what is
   * painted, so those claims already have items there and the tile only has to
   * point at them.
   */
  readonly onOverflow: (column: { layer: number; claims: readonly string[] }) => void;
  /**
   * True while the map is arriving, which is when the one animation it spends on
   * causality runs: the wires draw in the order the argument runs, a column at a
   * time. Under reduced motion the ordering survives and the drawing goes.
   */
  readonly arriving: boolean;
  /**
   * The rectangles the map is holding open at its growing edge, while a map is
   * still being built.
   *
   * Empty on every finished map, which is every map this canvas drew before
   * generation existed — so nothing about a stored example changes.
   */
  readonly reserved?: readonly ReservedBox[];
  /**
   * What the canvas says about the session it is in, such as that this run is a
   * recording being played back. Drawn in the corner of the surface, over
   * nothing.
   */
  readonly badge?: ReactNode;
  /**
   * A word that changes when the map should be framed again — and settled.
   *
   * The map is framed once, when it is first drawn, and never again — losing
   * your place because the map was rearranged is the most disorienting thing a
   * canvas can do. A map that **builds itself** has one more moment worth
   * framing: the one where it stops. The reader is about to start reading, and a
   * four-column map framed for its first single rectangle is a map they would
   * otherwise have to hunt around.
   *
   * **It is also the moment the map settles** (decision record 0024): every pin
   * is dropped and the whole map is laid out once, so that a picture written one
   * claim at a time becomes the picture the argument makes. The canvas hands
   * this same word to the layout, so the settle and the re-frame are one moment
   * and cannot come apart. It is a cut and not an animation: every tile is in
   * its new place in one frame.
   *
   * It is a word rather than a flag so that the effect has something to compare:
   * the map is framed once, and settled once, for each value it has ever had.
   */
  readonly frameAgainOn?: string;
  /**
   * A word that changes when the map should be framed again and **not** settled
   * *(2026-09-22)*.
   *
   * The stage can change width without the window changing and without a claim
   * arriving: the reader folds the panel away and the map is handed 310 more
   * pixels. Framing again is right there — the map was framed for a narrower
   * stage and now sits off to one side of a wider one — and settling would be
   * quite wrong, because a settle drops every pin and lays the whole map out
   * again. During a run that would move tiles that are already placed, which is
   * the one thing a growing map must never do.
   *
   * So it is a second word, and it goes nowhere near `useLayout`. `frameAgainOn`
   * means *frame and settle*; this means *frame*. Both compose: on a finished
   * generation the two are in the key together, and folding the panel re-frames
   * without settling a second time.
   *
   * A word rather than a flag, for the same reason as above: the map is framed
   * once for each value it has ever had. It is a cut, never a tween.
   */
  readonly frameAgainWhen?: string;
}

/** The surface itself. Lives inside the provider so it can move the view. */
function MapSurface({
  world,
  selection,
  onSelect,
  onPointedAt,
  focused,
  onFocused,
  heights,
  mapKey,
  keys,
  onStatus,
  onOverflow,
  arriving,
  reserved,
  badge,
  frameAgainOn,
  frameAgainWhen,
}: SurfaceProps) {
  const flow = useReactFlow();
  const surface = useRef<HTMLDivElement>(null);
  const [pointingAt, setPointingAt] = useState<string | null>(null);

  const drawing = useMemo(() => toFlow(world, heights, reserved), [world, heights, reserved]);
  // The same word twice, on purpose: the map settles and the view re-frames on
  // one moment, and there is nothing that could make them come apart.
  const layout = useLayout(drawing.tiles, drawing.layoutEdges, mapKey, frameAgainOn);

  // How far the map is zoomed out, said as which of the three forms everything
  // on the map is drawing. Below the first threshold a wire's plate would have
  // its words drawn under eleven pixels on the glass, which is the one thing
  // nothing in this product is allowed to do, so the plate keeps only its
  // number and the stroke keeps saying what kind of push the wire is. Below the
  // second there is no type size left that would clear the floor, so the plate
  // goes altogether — a plate is words, and out here the map draws no words.
  const zoom = useStore((state) => state.transform[2]);
  const detail = detailAt(zoom);

  /** How tall a tile turned out to be, so the view can be centred on its middle. */
  const heightOf = useCallback(
    (id: string) => drawing.tiles.find((tile) => tile.id === id)?.height ?? 0,
    [drawing],
  );

  /** Where every tile ended up, which is what routing a wire needs to know. */
  const boxes = useMemo(() => {
    const placed = new Map<string, Box>();
    for (const [id, at] of layout.positions) {
      placed.set(id, { x: at.x, y: at.y, width: TILE_WIDTH, height: heightOf(id) });
    }
    return placed;
  }, [layout, heightOf]);

  // What the hover lens leaves lit. `null` is everything, which is what the map
  // looks like when the reader is not pointing at anything. The claim the
  // keyboard is on counts as being pointed at, so the lens is not a mouse-only
  // feature.
  const lens = useMemo(() => {
    // **The lens only ever reads a claim that is on the map.** A box can leave
    // under the pointer — a reserved rectangle becomes a tile, a claim is
    // dropped by a branch — and the mouse never leaves it, because there is
    // nothing left to leave. What was pointed at is then a name the map does not
    // hold, nothing is on its path, and the whole map dims to fifteen per cent
    // with nothing lit. That is the lens answering a question about something
    // that is not there.
    const under = world.claims.some((claim) => claim.id === pointingAt) ? pointingAt : null;
    // **While a map is still arriving the lens is off unless the reader points
    // at something.** Focus moves by itself on a map that is building — every
    // claim that arrives takes it, so the view can follow the growing edge — and
    // dimming the rest of the map because the machine moved is the lens
    // answering a question nobody asked. Pointing at a tile still works.
    return onThePathFrom(under ?? (arriving ? null : focused), world.links);
  }, [pointingAt, focused, world.claims, world.links, arriving]);

  // Which column each claim sits in, for the one animation this map spends on
  // causality: the wires arrive in the order the argument runs, a column at a
  // time. The order is read from the map's own shape, never from the clock.
  const column = useMemo(() => {
    const placed = new Map<string, number>();
    for (const one of assignLayers(
      world.claims.map((claim) => claim.id),
      world.links,
    )) {
      placed.set(one.id, one.layer);
    }
    return placed;
  }, [world]);

  // **Which boxes are on the glass, and where.** The rule is `onTheGlass.ts`'s
  // and the whole of it is there: a box is drawn where the layout put it, a
  // reserved rectangle stands until the claim it was holding a place for is
  // drawn, and before the layout has answered anything the map puts its own
  // first rectangle at the origin.
  //
  // **The rectangles standing are carried from one answer to the next**, which
  // is why a ref and not a piece of state: it is not something the screen reacts
  // to, it is the last answer being handed back to work out the next one, and
  // asking for a second render to do it would paint the wrong frame first.
  const standing = useRef<readonly PlacedBox[]>([]);
  const glass = useMemo(
    () => whatIsOnTheGlass(drawing.nodes, layout.positions, standing.current),
    [drawing, layout],
  );
  standing.current = glass.rectangles;

  const nodes: MapNode[] = useMemo(
    () =>
      glass.boxes.map((node) => {
        const ghost = node.type === "claim" && node.data.claim.ghost === true;
        return {
          ...node,
          selected: selection?.kind === "claim" && selection.id === node.id,
          // Two classes and not one: the hover lens and the other world are both
          // opacity, and a tile that is off the hovered path *and* in the other
          // world has to land at the two multiplied together rather than at
          // whichever rule happened to win. `canvas.css` multiplies them.
          className: [
            // A rectangle held open for a claim that has not arrived is never
            // dimmed by the lens. The lens answers "what does this have to do
            // with anything", and a box standing for a claim that does not exist
            // yet is not on anybody's path — dimming it would hide the one thing
            // a reader watching a map build itself is waiting for.
            lens !== null && !lens.claims.has(node.id) && !node.id.startsWith(RESERVED_PREFIX)
              ? "is-dimmed"
              : "",
            ghost ? "is-ghost" : "",
          ]
            .filter((one) => one !== "")
            .join(" "),
        };
      }),
    [glass, lens, selection],
  );

  const edges: MapEdge[] = useMemo(() => {
    const routable = drawing.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      handle: edge.sourceHandle ?? "out-trigger",
      reflexive: edge.data?.reflexive === true,
      mode: edge.data?.mode ?? "trigger",
      strength: edge.data?.strength ?? 0,
      lag: edge.data?.lag ?? 0,
    }));
    const plans = planRoutes(routable, boxes);
    const offsets = tailOffsets(routable);
    // Where every plate goes, worked out for the whole map at once. A wire
    // cannot see its neighbours, and once two worlds are laid over each other
    // that is not enough: the union crowds the middle of the map and plates
    // began landing on one another.
    const plates = planPlates({ wires: routable, boxes, plans, tailOffsets: offsets });
    const wires = new Map(world.links.map((link) => [link.id, link]));
    return drawing.edges.map((edge) => {
      if (edge.data === undefined) {
        return edge;
      }
      const wire = wires.get(edge.id);
      return {
        ...edge,
        selected: selection?.kind === "wire" && selection.id === edge.id,
        // The wave's place in the order, and whether this wire belongs to the
        // world you are not looking at. Both are carried as classes, because a
        // class is what the drawing library puts on the group the wire is drawn
        // in, and a wire cannot know where the other wires are.
        className: [
          `wave-${Math.min(column.get(edge.source) ?? 0, 5)}`,
          wire?.ghost === true ? "is-ghost" : "",
          wire?.change === undefined ? "" : `is-${wire.change}`,
        ]
          .filter((one) => one !== "")
          .join(" "),
        data: {
          ...edge.data,
          plan: plans.get(edge.id),
          tailOffset: offsets.get(edge.id),
          plateAt: plates.get(edge.id),
          wave: Math.min(column.get(edge.source) ?? 0, 5),
          dimmed: lens !== null && !lens.wires.has(edge.id),
          detail,
        },
      };
    });
  }, [drawing, boxes, lens, selection, detail, world, column]);

  /**
   * Everything the first frame has to hold: every tile, and the strip of empty
   * space above them that the one backwards wire runs along.
   */
  const mapBounds = useCallback(() => {
    const placed = [...layout.positions.entries()];
    if (placed.length === 0) {
      return null;
    }
    const left = Math.min(...placed.map(([, at]) => at.x));
    const right = Math.max(...placed.map(([, at]) => at.x)) + TILE_WIDTH;
    const top = Math.min(...placed.map(([, at]) => at.y));
    const bottom = Math.max(...placed.map(([id, at]) => at.y + heightOf(id)));
    const overhead = drawing.edges.some((edge) => edge.data?.reflexive === true) ? SKY_GAP + 8 : 0;
    return { x: left, y: top - overhead, width: right - left, height: bottom - top + overhead };
  }, [drawing, layout, heightOf]);

  const framed = useRef<string | null>(null);
  const justFramed = useRef(false);
  const centredOn = useRef<string | null>(null);

  // **Which edges of the stage have map beyond them.**
  //
  // A ten-claim map framed so its tiles stay readable does not fit: two tiles
  // end up wholly off the glass and the bottom row is clipped. A map that is cut
  // with nothing saying so is read as a map that ends there, which for a causal
  // map is the worst thing it can be read as — the reader concludes the argument
  // stops where the window does.
  //
  // So the stage says it, with the same two-pixel rule the panel beside it uses
  // for the same fact (`useTheEdges.ts`). The measurement is different because
  // the box is: the panel is scrolled and the stage is panned, so this compares
  // where the tiles are, in the map's own coordinates, against what the viewport
  // is showing of them.
  const [beyond, setBeyond] = useState<Edges>(NOTHING_BEYOND);
  const measureTheEdges = useCallback(() => {
    const frame = mapBounds();
    const room = surface.current?.getBoundingClientRect();
    if (frame === null || room === undefined) {
      setBeyond((was) => (was === NOTHING_BEYOND ? was : NOTHING_BEYOND));
      return;
    }
    // A pixel of slack at each edge: a tile that ends exactly on the edge is not
    // beyond it, and a rule drawn for half a pixel of rounding would be the map
    // claiming something a reader can check by looking.
    const view = flow.getViewport();
    const onTheGlass = {
      left: frame.x * view.zoom + view.x,
      top: frame.y * view.zoom + view.y,
      right: (frame.x + frame.width) * view.zoom + view.x,
      bottom: (frame.y + frame.height) * view.zoom + view.y,
    };
    const next: Edges = {
      left: onTheGlass.left < -1,
      above: onTheGlass.top < -1,
      right: onTheGlass.right > room.width + 1,
      below: onTheGlass.bottom > room.height + 1,
    };
    setBeyond((was) =>
      was.left === next.left &&
      was.right === next.right &&
      was.above === next.above &&
      was.below === next.below
        ? was
        : next,
    );
  }, [flow, mapBounds]);

  // Measured whenever the map is laid out again, whenever a tile arrives,
  // whenever the reader pans or zooms — which is `onMove`, below — **and
  // whenever the stage itself changes size**. Missing any one of the four
  // leaves a rule at an edge with nothing beyond it, or none at an edge that
  // has plenty.
  //
  // The fourth is the window. A map framed at 1600 × 1000 and then given a
  // bigger window has its whole self on the glass while the rule below is still
  // drawn, and a map given a smaller one loses two tiles off the right with
  // nothing saying so. Neither pans and neither re-lays out, so nothing else
  // here would ever hear about it.
  //
  // **It measures and changes nothing it measures.** The rule it decides is
  // drawn by `.canvas::after`, which is absolutely positioned and takes no
  // space, so this observer cannot feed itself — the lesson the panel beside it
  // paid for, stated here so the next person to add a box does not pay it
  // again. One observer for the life of the surface.
  //
  // The measuring is read through a ref rather than captured, so that the
  // observer is built once and never rebuilt: asking the browser to watch a box
  // it is already watching makes it re-deliver that box's size, and rebuilding
  // this on every arrival would re-deliver it once per claim. That is the storm
  // that starved the drawing library's own measuring, and it is not being
  // started again here.
  const howToMeasure = useRef(measureTheEdges);
  howToMeasure.current = measureTheEdges;

  useEffect(() => {
    measureTheEdges();
  }, [measureTheEdges]);

  useEffect(() => {
    const it = surface.current;
    if (it === null || typeof ResizeObserver === "undefined") {
      return;
    }
    const watching = new ResizeObserver(() => howToMeasure.current());
    watching.observe(it);
    return () => watching.disconnect();
  }, []);

  // Frame the map when it is a different map — the first time it is drawn, and
  // again when a branch adds a claim to it. Panning, zooming and walking around
  // never re-frame: losing your place because the map was rearranged is the most
  // disorienting thing a canvas can do.
  useEffect(() => {
    // Only once the positions really are this map's. Framing from the positions
    // worked out for the map before the branch would frame the wrong thing, and
    // the right thing would then arrive underneath it.
    // Which framing this would be. While a map is being asked to frame again —
    // which is only ever when a generation has stopped — the layout's own run
    // count is part of the answer, so that a frame taken while the last claims
    // were still being placed is taken again when they have been. That same
    // moment settles the map (decision record 0024), which is one more layout,
    // so the last frame of all is taken on the map's settled shape and then
    // nothing lays it out again.
    //
    // **And the stage's own width is part of the answer too** *(2026-09-22)*.
    // `frameAgainWhen` changes when the reader folds the panel away or brings
    // it back, which hands the map 310 pixels it did not have and takes them
    // away again. It is on the end of the key rather than folded into the
    // settle's word because a settle drops every pin and lays the whole map out
    // again: right when a run stops, and quite wrong when a reader widens the
    // stage halfway through one. It never reaches `useLayout`.
    const frameFor =
      (frameAgainOn === undefined ? mapKey : `${mapKey}:${frameAgainOn}:${layout.runs}`) +
      (frameAgainWhen === undefined ? "" : `:${frameAgainWhen}`);
    if (layout.runs === 0 || layout.laidOutFor !== mapKey || framed.current === frameFor) {
      return;
    }
    const frame = mapBounds();
    const room = surface.current?.getBoundingClientRect();
    if (frame === null || room === undefined) {
      return;
    }
    // Framed to fit — but never zoomed out past the point where a full tile would
    // have to become a summary. The reader's first sight of the map is tiles they
    // can read; if the whole map does not fit at that size, it is framed from its
    // beginning, on the left, where the map starts, and they pan to the rest.
    flow.setViewport(firstFrame(frame, { width: room.width, height: room.height }), {
      duration: 0,
    });
    framed.current = frameFor;
    justFramed.current = true;
  }, [layout.runs, layout.laidOutFor, flow, mapBounds, mapKey, frameAgainOn, frameAgainWhen]);

  // The view follows whatever the keyboard is on, so a step along a wire never
  // walks off the edge of the glass — and so that a map building itself does not
  // build its fourth column off the side of the window while the reader watches
  // an empty one. Every claim that arrives takes focus, which is the rule
  // `layout-and-zoom.md` already states for a newly created claim; this is the
  // other half of the same rule, that the focused tile stays in the viewport.
  //
  // **It brings the tile in rather than centring on it.** The promise is that
  // the focused tile is on the glass, not that it is in the middle of it, and a
  // view that recentred on every arrival would yank the map out from under
  // somebody reading a tile that was perfectly visible. So: already on the
  // glass, nothing happens; off the edge, it is brought to the middle, once.
  useEffect(() => {
    if (focused === null || layout.runs === 0 || centredOn.current === focused) {
      // Only when the keyboard has actually moved. Flipping between the two
      // worlds redraws every tile and moves none of them, and a view that slid
      // sideways on the flip would make the reader hunt for what changed — which
      // is the one thing the flip exists to show.
      return;
    }
    if (justFramed.current) {
      justFramed.current = false;
      centredOn.current = focused;
      return;
    }
    // Where the layout put it, not where the drawing library thinks it is: a
    // tile that has just arrived is in the layout's answer a render before the
    // library has it, and reading the library's copy too early gave the origin
    // — which is how a map ended up centred on an empty corner.
    const at = layout.positions.get(focused);
    const room = surface.current?.getBoundingClientRect();
    if (at === undefined || room === undefined) {
      // Not placed yet. The layout runs again and this runs with it.
      return;
    }
    centredOn.current = focused;

    const middle = { x: at.x + TILE_WIDTH / 2, y: at.y + heightOf(focused) / 2 };
    const view = flow.getViewport();
    const onTheGlass = {
      x: at.x * view.zoom + view.x,
      y: at.y * view.zoom + view.y,
      width: TILE_WIDTH * view.zoom,
      height: heightOf(focused) * view.zoom,
    };
    const inside =
      onTheGlass.x >= 0 &&
      onTheGlass.y >= 0 &&
      onTheGlass.x + onTheGlass.width <= room.width &&
      onTheGlass.y + onTheGlass.height <= room.height;
    if (inside) {
      return;
    }
    flow.setCenter(middle.x, middle.y, { zoom: view.zoom, duration: 0 });
  }, [focused, flow, heightOf, layout]);

  /** Show the claims a column had no room for, as a list. */
  const openColumn = useCallback(
    (layer: number) => {
      onOverflow({
        layer,
        claims: [...column.entries()].filter(([, at]) => at === layer).map(([id]) => id),
      });
      onStatus(`the claims in column ${layer}, as a list`);
    },
    [column, onOverflow, onStatus],
  );

  /**
   * What the reader just pointed at, or `null` when it was the empty map.
   *
   * Read off the page rather than from the drawing library, deliberately. The
   * library reports a click on a tile only through the machinery that also drags
   * tiles around, and tiles here do not drag — so that report never arrives.
   * Asking the page what was under the pointer is one line, and it gives the
   * same answer for a wire, a tile and the empty map.
   */
  const whatIsUnder = useCallback((target: HTMLElement | null): Selection => {
    const wire = target?.closest<HTMLElement>(".react-flow__edge");
    if (wire?.dataset.id !== undefined) {
      return { kind: "wire", id: wire.dataset.id };
    }
    const tile = target?.closest<HTMLElement>(".react-flow__node");
    // A rectangle held open for a claim that has not arrived is a box, not a
    // claim: there is nothing behind it to read out, so pressing it does nothing
    // and the panel is left where it was.
    if (tile?.dataset.id !== undefined && !tile.dataset.id.startsWith(RESERVED_PREFIX)) {
      return { kind: "claim", id: tile.dataset.id };
    }
    return null;
  }, []);

  /**
   * Find a tile or a wire on the glass by the identifier it carries.
   *
   * By reading each element's own identifier rather than by asking the page for
   * a match: a wire is named after its two ends — `H->B` — and the arrow in the
   * middle of that is not a character an address for an element may contain.
   */
  const onTheGlass = useCallback((kind: "node" | "edge", id: string): HTMLElement | undefined => {
    const all = surface.current?.querySelectorAll<HTMLElement>(`.react-flow__${kind}`) ?? [];
    return [...all].find((one) => one.dataset.id === id);
  }, []);

  /** Which claim the keyboard is standing on right now, read off the glass. */
  const standingOn = useCallback(
    (): string | undefined =>
      document.activeElement?.closest<HTMLElement>(".react-flow__node")?.dataset.id,
    [],
  );

  /** The tile the keyboard was last asked to stand on, so a late move can be dropped. */
  const wantedTile = useRef<string | null>(null);

  /**
   * Put the keyboard on a tile, and make it stick.
   *
   * **A tile that is being rebuilt cannot be focused.** The drawing library
   * rebuilds a tile's element when what it knows about it changes — which
   * selecting one does — so the element found on the glass this instant is
   * sometimes the one about to be thrown away, and focusing it does nothing at
   * all. The keyboard then stays on the tile it was on while the ring, the
   * panel and the line under the map all move to the new one: the page says the
   * reader is on the hypothesis and the next keystroke walks from Brent.
   *
   * The same hazard is already handled for wires below, in the same way. Here
   * the move is made at once, and made again after the rebuild has been and
   * gone if it did not take — and only if it is still the move the reader last
   * asked for, so that two quick steps do not drag the keyboard back to the
   * first one.
   *
   * **And only from nowhere.** The second landing waits on animation frames,
   * and frames are not a clock: a browser produces none while nothing on the
   * page is changing, so it can run long after it was scheduled — and the frame
   * that finally runs it is very often one the reader caused by doing something
   * else. `theKeyboard.ts` has the rule and the reason.
   */
  const putTheKeyboardOn = useCallback(
    (id: string): void => {
      wantedTile.current = id;
      const land = (): void => onTheGlass("node", id)?.focus({ preventScroll: true });
      land();
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (
            !mayLandAgain({
              wanted: wantedTile.current,
              forTile: id,
              standingOn: standingOn(),
              active: document.activeElement,
              surface: surface.current,
            })
          ) {
            return;
          }
          land();
        });
      });
    },
    [onTheGlass, standingOn],
  );

  /**
   * Fill the panel with whatever was pressed, or empty it on a press on the map.
   *
   * It listens for the press rather than the click, and that is not a detail:
   * the drawing library grabs the pointer on the surface the moment a press
   * begins, so that dragging the map keeps working when the pointer wanders off
   * a tile — and from then on every event, the click included, is reported
   * against the surface rather than against what was actually under the pointer.
   * The press is the last moment the page can still say what was pressed.
   */
  const onPointAt = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const under = whatIsUnder(event.target as HTMLElement);
      // The zoom buttons and the library's own furniture are not the map.
      if (under === null && (event.target as HTMLElement).closest(".react-flow__controls")) {
        return;
      }
      if (under?.kind === "claim" && under.id.startsWith(OVERFLOW_PREFIX)) {
        openColumn(Number(under.id.slice(OVERFLOW_PREFIX.length)));
        return;
      }
      onSelect(under);
      // **This is the one path a reader POINTED at**, and the screen is told so
      // separately *(2026-09-22)*. Landing on a claim and pointing at one both
      // fill the panel, and that is right — but they are not the same request.
      // Walking the map is walking the map; pointing at a claim is asking to
      // read it. The screen needs the difference for one thing only: a panel
      // the reader has folded away stays folded while they walk, and comes back
      // when they point at something. Before this, every step along a wire
      // called `onSelect` and unfolded the panel again, which made the fold
      // useless to the reader it exists for.
      if (under !== null) {
        onPointedAt?.(under);
      }
      if (under?.kind === "claim") {
        onFocused(under.id);
        // Pointing at a tile and reaching it with the keyboard land in the same
        // place, so the ring says where you are whichever way you got there —
        // and the pointer's landing is made to stick for the same reason the
        // keyboard's is.
        putTheKeyboardOn(under.id);
      }
    },
    [onSelect, onPointedAt, whatIsUnder, onFocused, openColumn, putTheKeyboardOn],
  );

  /**
   * Remember what the reader is on, fill the panel with it, and bring it into
   * view if it is off the edge of the screen.
   *
   * This catches the keyboard as well as the pointer. Reaching a claim or an
   * arrow with the keyboard and reaching it with the pointer do the same thing:
   * the panel beside the map reads it out. Nothing opens over the map, and
   * there is nothing to dismiss.
   */
  const onFocus = useCallback(
    (event: React.FocusEvent<HTMLDivElement>) => {
      const target = event.target as HTMLElement;
      const under = whatIsUnder(target);
      if (under === null) {
        return;
      }
      if (under.kind === "wire") {
        // **Landing on a wire does not select it, and that is not an
        // oversight.** The drawing library rebuilds a wire's element when it
        // becomes selected, and rebuilding the element the keyboard is standing
        // on drops focus to the page — which made tabbing through the map
        // impossible, because the wires come before the tiles. So a wire fills
        // the panel when you press Enter on it, and the focus is put back on the
        // rebuilt wire straight afterwards, which is what the effect below is
        // for. Pointing at one with the mouse is unchanged.
        return;
      }
      onSelect(under);
      onFocused(under.id);
    },
    [onSelect, whatIsUnder, onFocused],
  );

  // Where every tile ended up, in the shape moving along a wire needs: the
  // keyboard asks what it can *walk to*, which reads the whole map, feedback
  // arrows included.
  const places = useMemo(() => {
    const map = new Map<string, { x: number; y: number; height: number }>();
    for (const [id, at] of layout.positions) {
      map.set(id, { x: at.x, y: at.y, height: heightOf(id) });
    }
    return map;
  }, [layout, heightOf]);

  const claimWords = useCallback(
    (id: string) => world.claims.find((claim) => claim.id === id)?.claim ?? NOT_ON_THIS_MAP,
    [world],
  );

  const onKeyDown = useMapKeys({
    wires: world.links,
    positions: places,
    focused,
    onFocused: (id) => {
      onFocused(id);
      // Reaching a tile with the keyboard and reaching it with the pointer do
      // the same thing: the panel beside the map reads it out. Nothing opens
      // over the map.
      onSelect({ kind: "claim", id });
      putTheKeyboardOn(id);
    },
    onStatus,
    keys,
    words: claimWords,
  });

  // A wire the reader has just asked for, so that focus can be put back on it
  // once the drawing library has rebuilt it.
  const askedForWire = useRef<string | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: the selection is not read inside — it is what this is waiting for. The wire is rebuilt because the selection changed, so the selection is exactly the right thing to hang this on.
  useEffect(() => {
    const id = askedForWire.current;
    if (id === null) {
      return;
    }
    askedForWire.current = null;
    // Two frames, not none. The drawing library keeps its own record of what is
    // selected and rebuilds the wire's element from it a frame later, so putting
    // focus back on the element that is there right now would put it on the one
    // about to be thrown away.
    //
    // And the same rule as a tile's landing: two frames later can be much later,
    // because a browser produces no frames while nothing changes — so this takes
    // the keyboard back from nowhere and never from somewhere.
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (
          !mayLandAgain({
            wanted: id,
            forTile: id,
            standingOn: undefined,
            active: document.activeElement,
            surface: surface.current,
          })
        ) {
          return;
        }
        onTheGlass("edge", id)?.focus();
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [selection, onTheGlass]);

  // The keyboard map, bound once on the page. On the page rather than on the map
  // itself, because a key bound to the element you happen to be standing on is a
  // key that stops working the moment you press Tab — and every key below is left
  // alone while the keyboard is in a field.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      // A collapsed tile is reached with the keyboard like any other, and Enter
      // opens what is behind it — the same thing a press does.
      const target = event.target as HTMLElement | null;
      const at = target?.closest<HTMLElement>(".react-flow__node");
      if (event.key === "Enter" && at?.dataset.id?.startsWith(OVERFLOW_PREFIX) === true) {
        event.preventDefault();
        openColumn(Number(at.dataset.id.slice(OVERFLOW_PREFIX.length)));
        return;
      }
      // Enter on a wire reads it out in the panel beside the map — the same
      // thing pointing at it does. It is Enter rather than merely landing on it
      // because of what the comment above `onFocus` explains.
      const wire = target?.closest<HTMLElement>(".react-flow__edge");
      if ((event.key === "Enter" || event.key === " ") && wire?.dataset.id !== undefined) {
        event.preventDefault();
        askedForWire.current = wire.dataset.id;
        onSelect({ kind: "wire", id: wire.dataset.id });
        onStatus(`this arrow, read out in the panel beside the map`);
        return;
      }
      onKeyDown(event);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKeyDown, openColumn, onSelect, onStatus]);

  return (
    <div
      className="canvas"
      ref={surface}
      data-arriving={arriving ? "yes" : "no"}
      // Which of the three forms the map is drawing, written once on the
      // surface so that the two boxes that are not claims — a rectangle held
      // open at a growing edge, and the "+n more" that stands for a column's
      // overflow — drop their words at the same zoom every tile does. Neither
      // is a tile, so neither carries the attribute itself; both are inside
      // this.
      data-detail={detail}
      {...edgeMarks(beyond)}
      onFocusCapture={onFocus}
      onPointerDownCapture={onPointAt}
    >
      <WireMarks />

      {badge}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={TILE_TYPES}
        edgeTypes={WIRE_TYPES}
        // Tiles do not move. Automatic layout decides where a claim sits, and a
        // tile you can drag half of the time — snapping back whenever the map is
        // laid out again — reads as broken. Pinning, grouping and annotating
        // arrive later as things you ask for, not as free dragging.
        nodesDraggable={false}
        nodesConnectable={false}
        // A tile and a wire both answer to the pointer and to the keyboard. A
        // wire has to: everything it says on the glass it says again in words in
        // the panel, and the only way to ask for those words is to reach it.
        elementsSelectable={true}
        nodesFocusable={true}
        edgesFocusable={true}
        // Selecting a wire must not lift it above the others. The drawing
        // library's default is to re-sort the wires when one is selected so the
        // selected one draws on top — and re-sorting them moves the element the
        // keyboard is standing on, which drops focus to the page and makes
        // tabbing through the map impossible. Nothing here needs the lift: a
        // selected wire is marked by a ring, and how wires cross is settled by
        // routing rather than by drawing order.
        elevateNodesOnSelect={false}
        onNodeMouseEnter={(_, node) => setPointingAt(node.id)}
        onNodeMouseLeave={() => setPointingAt(null)}
        // Panning and zooming both move what is on the glass, so both change
        // which edges have map beyond them.
        onMove={measureTheEdges}
        // As far out as the map goes, and no further: past this a tile's box
        // would be drawn smaller than anything a reader has to point at is
        // allowed to be. `geometry.ts` works it out.
        minZoom={SMALLEST_ZOOM}
        maxZoom={LARGEST_ZOOM}
        proOptions={{ hideAttribution: false }}
        // Named, not addressed: the drawing library writes the address around
        // the name itself.
        defaultEdgeOptions={{ markerEnd: ARROWHEAD }}
      >
        <Background variant={BackgroundVariant.Dots} gap={32} size={1} />
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>

      {layout.failure === null ? null : (
        <p className="canvas__failure">{`The map could not be laid out. ${layout.failure}`}</p>
      )}
    </div>
  );
}

/** What the map needs to be dropped into a page. */
export type MapCanvasProps = SurfaceProps;

/** The map, ready to be dropped into a page. */
export function MapCanvas(props: MapCanvasProps) {
  return (
    <ReactFlowProvider>
      <MapSurface {...props} />
    </ReactFlowProvider>
  );
}
