/**
 * The map: tiles, wires, panning and zooming.
 *
 * The drawing library owns four things and no more — panning, zooming, working
 * out what is under the pointer, and the sockets on the sides of a tile.
 * Everything you can see is ours. That is why only the library's bare
 * stylesheet is imported below and never its full one: the full one carries the
 * library's own look, and a tool that looks like the library it was built with
 * looks like a demo. A check in `npm run lint` fails the build if the full one
 * ever appears in this tree.
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
 *   3. **Whether a wire's plate has room for its words.** Below the same zoom at
 *      which a tile switches to its summary, a plate's words would land under
 *      eleven pixels on the glass, so the plates go. Nothing is scaled down to
 *      dodge the rule.
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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xyflow/react/dist/base.css";
import { Tile } from "../components/Tile";
import { TileOverflow } from "../components/TileOverflow";
import type { MapKeys } from "../keyboard/useMapKeys";
import { useMapKeys } from "../keyboard/useMapKeys";
import type { Selection, WorldView } from "../world";
import {
  firstFrame,
  LARGEST_ZOOM,
  SMALLEST_ZOOM,
  SUMMARY_BELOW_ZOOM,
  TILE_WIDTH,
} from "./geometry";
import { assignLayers } from "./layers";
import { useLayout } from "./layoutRunner";
import {
  type ClaimNode,
  type MapEdge,
  type MapNode,
  OVERFLOW_PREFIX,
  type OverflowNode,
  toFlow,
} from "./toFlow";
import { CausalWire } from "./wires/CausalWire";
import { onThePathFrom } from "./wires/lens";
import { type Box, planRoutes, SKY_GAP, tailOffsets } from "./wires/route";
import { ARROWHEAD, WireMarks } from "./wires/WireMarks";
import "./canvas.css";

/** The two kinds of box the map draws. Defined once, outside render, so the
 * drawing library never has to rebuild its tiles because the object changed. */
const TILE_TYPES = {
  claim: ({ data }: { data: ClaimNode["data"] }) => (
    <Tile
      claim={data.claim}
      isHypothesis={data.isHypothesis}
      versions={data.versions}
      height={data.height}
    />
  ),
  overflow: ({ data }: { data: OverflowNode["data"] }) => <TileOverflow count={data.count} />,
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
}

/** The surface itself. Lives inside the provider so it can move the view. */
function MapSurface({
  world,
  selection,
  onSelect,
  focused,
  onFocused,
  heights,
  mapKey,
  keys,
  onStatus,
  onOverflow,
  arriving,
}: SurfaceProps) {
  const flow = useReactFlow();
  const surface = useRef<HTMLDivElement>(null);
  const [pointingAt, setPointingAt] = useState<string | null>(null);

  const drawing = useMemo(() => toFlow(world, heights), [world, heights]);
  const layout = useLayout(drawing.tiles, drawing.layoutEdges, mapKey);

  // How far the map is zoomed out. Below the threshold a wire's plate would
  // have its words drawn under eleven pixels on the glass, which is the one
  // thing nothing in this product is allowed to do, so the plates go and the
  // stroke keeps saying what kind of push each wire is.
  const zoom = useStore((state) => state.transform[2]);
  const tooSmallForWords = zoom < SUMMARY_BELOW_ZOOM;

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
  const lens = useMemo(
    () => onThePathFrom(pointingAt ?? focused, world.links),
    [pointingAt, focused, world.links],
  );

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

  const nodes: MapNode[] = useMemo(
    () =>
      drawing.nodes.map((node) => {
        const ghost = node.type === "claim" && node.data.claim.ghost === true;
        return {
          ...node,
          position: layout.positions.get(node.id) ?? { x: 0, y: 0 },
          selected: selection?.kind === "claim" && selection.id === node.id,
          // Two classes and not one: the hover lens and the other world are both
          // opacity, and a tile that is off the hovered path *and* in the other
          // world has to land at the two multiplied together rather than at
          // whichever rule happened to win. `canvas.css` multiplies them.
          className: [
            lens !== null && !lens.claims.has(node.id) ? "is-dimmed" : "",
            ghost ? "is-ghost" : "",
          ]
            .filter((one) => one !== "")
            .join(" "),
        };
      }),
    [drawing, layout, lens, selection],
  );

  const edges: MapEdge[] = useMemo(() => {
    const routable = drawing.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      handle: edge.sourceHandle ?? "out-trigger",
      reflexive: edge.data?.reflexive === true,
    }));
    const plans = planRoutes(routable, boxes);
    const offsets = tailOffsets(routable);
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
          dimmed: lens !== null && !lens.wires.has(edge.id),
          tooSmallForWords,
        },
      };
    });
  }, [drawing, boxes, lens, selection, tooSmallForWords, world, column]);

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

  // Frame the map when it is a different map — the first time it is drawn, and
  // again when a branch adds a claim to it. Panning, zooming and walking around
  // never re-frame: losing your place because the map was rearranged is the most
  // disorienting thing a canvas can do.
  useEffect(() => {
    // Only once the positions really are this map's. Framing from the positions
    // worked out for the map before the branch would frame the wrong thing, and
    // the right thing would then arrive underneath it.
    if (layout.runs === 0 || layout.laidOutFor !== mapKey || framed.current === mapKey) {
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
    framed.current = mapKey;
    justFramed.current = true;
  }, [layout.runs, layout.laidOutFor, flow, mapBounds, mapKey]);

  // The view follows whatever the keyboard is on, so a step along a wire never
  // walks off the edge of the glass. It does not fight the framing above: when a
  // branch has just arrived and moved focus to the claim it added, the whole map
  // has already been framed and that claim is in it.
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
    const node = flow.getNode(focused);
    if (node === undefined) {
      return;
    }
    centredOn.current = focused;
    flow.setCenter(node.position.x + TILE_WIDTH / 2, node.position.y + heightOf(focused) / 2, {
      zoom: flow.getZoom(),
      duration: 0,
    });
  }, [focused, flow, heightOf, layout.runs]);

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
    if (tile?.dataset.id !== undefined) {
      return { kind: "claim", id: tile.dataset.id };
    }
    return null;
  }, []);

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
      if (under?.kind === "claim") {
        onFocused(under.id);
        // Pointing at a tile and reaching it with the keyboard land in the same
        // place, so the ring says where you are whichever way you got there.
        (event.target as HTMLElement)
          .closest<HTMLElement>(".react-flow__node")
          ?.focus({ preventScroll: true });
      }
    },
    [onSelect, whatIsUnder, onFocused, openColumn],
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
      onSelect(under);
      if (under.kind === "wire") {
        return;
      }
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
    (id: string) => world.claims.find((claim) => claim.id === id)?.claim ?? id,
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
      surface.current
        ?.querySelector<HTMLElement>(`.react-flow__node[data-id="${CSS.escape(id)}"]`)
        ?.focus();
    },
    onStatus,
    keys,
    words: claimWords,
  });

  // The keyboard map, bound once on the page. On the page rather than on the map
  // itself, because a key bound to the element you happen to be standing on is a
  // key that stops working the moment you press Tab — and every key below is left
  // alone while the keyboard is in a field.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      // A collapsed tile is reached with the keyboard like any other, and Enter
      // opens what is behind it — the same thing a press does.
      const at = (event.target as HTMLElement | null)?.closest<HTMLElement>(".react-flow__node");
      if (event.key === "Enter" && at?.dataset.id?.startsWith(OVERFLOW_PREFIX) === true) {
        event.preventDefault();
        openColumn(Number(at.dataset.id.slice(OVERFLOW_PREFIX.length)));
        return;
      }
      onKeyDown(event);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKeyDown, openColumn]);

  return (
    <div
      className="canvas"
      ref={surface}
      data-arriving={arriving ? "yes" : "no"}
      onFocusCapture={onFocus}
      onPointerDownCapture={onPointAt}
    >
      <WireMarks />

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
        onNodeMouseEnter={(_, node) => setPointingAt(node.id)}
        onNodeMouseLeave={() => setPointingAt(null)}
        // As far out as the map goes, and no further: past this the summary
        // tile's words would be drawn smaller than anything in this product is
        // allowed to be.
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
