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
import type { WorldView } from "../world";
import { LARGEST_ZOOM, SMALLEST_ZOOM, SUMMARY_BELOW_ZOOM, TILE_WIDTH } from "./geometry";
import { useLayout } from "./layoutRunner";
import { type ClaimNode, type MapEdge, type MapNode, type OverflowNode, toFlow } from "./toFlow";
import { CausalWire } from "./wires/CausalWire";
import { onThePathFrom } from "./wires/lens";
import { type Box, planRoutes, SKY_GAP, tailOffsets } from "./wires/route";
import { ARROWHEAD, WireMarks } from "./wires/WireMarks";
import "./canvas.css";

/** The two kinds of box the map draws. Defined once, outside render, so the
 * drawing library never has to rebuild its tiles because the object changed. */
const TILE_TYPES = {
  claim: ({ data }: { data: ClaimNode["data"] }) => (
    <Tile claim={data.claim} isHypothesis={data.isHypothesis} versions={data.versions} />
  ),
  overflow: ({ data }: { data: OverflowNode["data"] }) => <TileOverflow count={data.count} />,
};

/** One kind of wire, ours, saying five things at once. */
const WIRE_TYPES = { causal: CausalWire };

/** What the panel beside the map is open on. */
export type Selection =
  | { readonly kind: "claim"; readonly id: string }
  | { readonly kind: "wire"; readonly id: string }
  | null;

/**
 * How the map is framed the first time it is drawn: the whole of it — the one
 * backwards wire's run over the top included — with a margin of a twelfth of
 * the window around it, and never blown up past life size.
 *
 * The margin is as tight as it is on purpose. Whether the first frame shows the
 * full tiles or their summaries is decided by whether the whole map happens to
 * fit above the summary threshold, and a fat margin pushes a map that would
 * have fitted below it.
 */
const FIRST_FRAME = { padding: 0.08, duration: 0 } as const;

/** Never blown up past life size on the first frame, however small the map. */
const FIRST_FRAME_MAX_ZOOM = 1;

/** What the map needs beyond the world it draws. */
interface SurfaceProps {
  /** The world to draw. */
  readonly world: WorldView;
  /** What the panel beside the map is open on. */
  readonly selection: Selection;
  /** Called when the reader selects a claim or an arrow, by pointer or by keyboard. */
  readonly onSelect: (selection: Selection) => void;
}

/** The surface itself. Lives inside the provider so it can move the view. */
function MapSurface({ world, selection, onSelect }: SurfaceProps) {
  const flow = useReactFlow();
  const surface = useRef<HTMLDivElement>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const [pointingAt, setPointingAt] = useState<string | null>(null);

  const drawing = useMemo(() => toFlow(world), [world]);
  const layout = useLayout(drawing.tiles, drawing.layoutEdges);

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

  const nodes: MapNode[] = useMemo(
    () =>
      drawing.nodes.map((node) => ({
        ...node,
        position: layout.positions.get(node.id) ?? { x: 0, y: 0 },
        selected: selection?.kind === "claim" && selection.id === node.id,
        className: lens !== null && !lens.claims.has(node.id) ? "is-dimmed" : undefined,
      })),
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
    return drawing.edges.map((edge) => {
      if (edge.data === undefined) {
        return edge;
      }
      return {
        ...edge,
        selected: selection?.kind === "wire" && selection.id === edge.id,
        data: {
          ...edge.data,
          plan: plans.get(edge.id),
          tailOffset: offsets.get(edge.id),
          dimmed: lens !== null && !lens.wires.has(edge.id),
          tooSmallForWords,
        },
      };
    });
  }, [drawing, boxes, lens, selection, tooSmallForWords]);

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

  // Frame the whole map once, when it is first laid out, and never again.
  // Afterwards the view follows whatever the reader is looking at, because
  // losing your place because the map was rearranged is the single most
  // disorienting thing a canvas can do.
  useEffect(() => {
    if (layout.runs === 0) {
      return;
    }
    if (layout.runs === 1) {
      const frame = mapBounds();
      if (frame !== null) {
        flow.fitBounds(frame, FIRST_FRAME);
        if (flow.getZoom() > FIRST_FRAME_MAX_ZOOM) {
          flow.zoomTo(FIRST_FRAME_MAX_ZOOM, { duration: 0 });
        }
      }
      return;
    }
    if (focused !== null) {
      const node = flow.getNode(focused);
      if (node) {
        flow.setCenter(node.position.x + TILE_WIDTH / 2, node.position.y + heightOf(focused) / 2, {
          zoom: flow.getZoom(),
          duration: 0,
        });
      }
    }
  }, [layout.runs, flow, focused, heightOf, mapBounds]);

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
      onSelect(under);
      if (under?.kind === "claim") {
        setFocused(under.id);
      }
    },
    [onSelect, whatIsUnder],
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
      const id = under.id;
      const box = target.closest<HTMLElement>(".react-flow__node");
      setFocused(id);
      const frame = surface.current?.getBoundingClientRect();
      const tile = box?.getBoundingClientRect();
      if (frame === undefined || tile === undefined) {
        return;
      }
      const offScreen =
        tile.left < frame.left ||
        tile.right > frame.right ||
        tile.top < frame.top ||
        tile.bottom > frame.bottom;
      if (!offScreen) {
        return;
      }
      const node = flow.getNode(id);
      if (node) {
        flow.setCenter(node.position.x + TILE_WIDTH / 2, node.position.y + heightOf(id) / 2, {
          zoom: flow.getZoom(),
          duration: 0,
        });
      }
    },
    [flow, heightOf, onSelect, whatIsUnder],
  );

  return (
    <div className="canvas" ref={surface} onFocusCapture={onFocus} onPointerDownCapture={onPointAt}>
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
export interface MapCanvasProps {
  /** The world to draw. */
  readonly world: WorldView;
  /** What the panel beside the map is open on. */
  readonly selection: Selection;
  /** Called when the reader selects a claim or an arrow. */
  readonly onSelect: (selection: Selection) => void;
}

/** The map, ready to be dropped into a page. */
export function MapCanvas({ world, selection, onSelect }: MapCanvasProps) {
  return (
    <ReactFlowProvider>
      <MapSurface world={world} selection={selection} onSelect={onSelect} />
    </ReactFlowProvider>
  );
}
