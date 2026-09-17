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
 * **Wires are plain here on purpose.** A wire is going to say five things at
 * once — what kind of push it is, how hard it pushes, whether it has to keep
 * holding, whether it loops back, and where it came from — and building that is
 * the next piece of work. What is drawn now is a deliberate placeholder: our
 * own stroke, our own arrowhead, one weight, so the shape of the map reads
 * while the wires still have nothing to say.
 */

import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xyflow/react/dist/base.css";
import { Tile } from "../components/Tile";
import { TileOverflow } from "../components/TileOverflow";
import type { WorldView } from "../world";
import { FeedbackWire } from "./FeedbackWire";
import { LARGEST_ZOOM, SMALLEST_ZOOM, TILE_WIDTH } from "./geometry";
import { useLayout } from "./layoutRunner";
import { type ClaimNode, type MapEdge, type MapNode, type OverflowNode, toFlow } from "./toFlow";
import "./canvas.css";

/** The two kinds of box the map draws. Defined once, outside render, so the
 * drawing library never has to rebuild its tiles because the object changed. */
const TILE_TYPES = {
  claim: ({ data }: { data: ClaimNode["data"] }) => (
    <Tile claim={data.claim} isHypothesis={data.isHypothesis} versions={data.versions} />
  ),
  overflow: ({ data }: { data: OverflowNode["data"] }) => <TileOverflow count={data.count} />,
};

/** The one wire that is not drawn by the library's own router. */
const WIRE_TYPES = { feedback: FeedbackWire };

/** How far above the highest tile the one backwards wire travels. */
const SKY_GAP = 56;

/** The name of the arrowhead every wire ends in, defined once below. */
const ARROWHEAD = "katalyst-arrowhead";

/**
 * How the map is framed the first time it is drawn: the whole of it — the one
 * backwards wire's run over the top included — with a margin of a twelfth of
 * the window around it, and never blown up past life size.
 *
 * The margin is as tight as it is on purpose. Whether the first frame shows the
 * full tiles or their summaries is decided by whether the whole map happens to
 * fit above the summary threshold, and a fat margin pushes a map that would
 * have fitted below it. On a window 1600 by 1000 this frames the stored example
 * at 0.88 — full tiles, with the smallest words landing at 11.4 pixels. On a
 * smaller window it lands below the threshold and the first frame is summaries,
 * which is the right answer there: the words stay legible and zooming in fills
 * the tiles.
 */
const FIRST_FRAME = { padding: 0.08, duration: 0 } as const;

/** Never blown up past life size on the first frame, however small the map. */
const FIRST_FRAME_MAX_ZOOM = 1;

/** The surface itself. Lives inside the provider so it can move the view. */
function MapSurface({ world }: { world: WorldView }) {
  const flow = useReactFlow();
  const surface = useRef<HTMLDivElement>(null);
  const [focused, setFocused] = useState<string | null>(null);

  const drawing = useMemo(() => toFlow(world), [world]);
  const layout = useLayout(drawing.tiles, drawing.layoutEdges);

  const nodes: MapNode[] = useMemo(
    () =>
      drawing.nodes.map((node) => ({
        ...node,
        position: layout.positions.get(node.id) ?? { x: 0, y: 0 },
      })),
    [drawing, layout],
  );

  // The one backwards wire travels above every tile, so it needs to be told
  // where the top of the map is. An edge cannot see the other tiles.
  const edges: MapEdge[] = useMemo(() => {
    const tops = [...layout.positions.values()].map((at) => at.y);
    const skyY = (tops.length > 0 ? Math.min(...tops) : 0) - SKY_GAP;
    return drawing.edges.map((edge) => {
      if (edge.type !== "feedback" || edge.data === undefined) {
        return edge;
      }
      return { ...edge, data: { ...edge.data, skyY } };
    });
  }, [drawing, layout]);

  /** How tall a tile turned out to be, so the view can be centred on its middle. */
  const heightOf = useCallback(
    (id: string) => drawing.tiles.find((tile) => tile.id === id)?.height ?? 0,
    [drawing],
  );

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
    const overhead = drawing.edges.some((edge) => edge.type === "feedback") ? SKY_GAP + 8 : 0;
    return { x: left, y: top - overhead, width: right - left, height: bottom - top + overhead };
  }, [drawing, layout, heightOf]);

  // Frame the whole map once, when it is first laid out, and never again.
  // Afterwards the view follows whatever the reader is looking at, because
  // losing your place because the map was rearranged is the single most
  // disorienting thing a canvas can do.
  //
  // The frame is worked out from the tiles *and* the sky the one backwards wire
  // runs along, because the library's own framing only knows about tiles and
  // would leave that wire hanging off the top edge — half a loop, which reads
  // as a mistake rather than as a loop.
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
   * Remember which tile the reader is on, and bring it into view if it is not.
   *
   * This catches the keyboard as well as the pointer, because moving focus with
   * the keyboard onto a tile that is off the edge of the screen would otherwise
   * leave the reader looking at nothing.
   */
  const onFocus = useCallback(
    (event: React.FocusEvent<HTMLDivElement>) => {
      const box = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node");
      const id = box?.dataset.id;
      if (id === undefined) {
        return;
      }
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
    [flow, heightOf],
  );

  return (
    <div className="canvas" ref={surface} onFocusCapture={onFocus}>
      {/* Our own arrowhead. The library draws a stock one; this is a thin open
          chevron that reads as a direction rather than as a blob. */}
      <svg className="canvas__marks" aria-hidden="true" focusable="false">
        <title>Drawing marks</title>
        <defs>
          <marker
            id={ARROWHEAD}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 1 1 L 9 5 L 1 9" />
          </marker>
        </defs>
      </svg>

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
        // A tile answers to the pointer and to the keyboard. It has to: the
        // drawing library switches a tile off from the pointer entirely unless
        // something can be done to it, and a tile you cannot point at is a tile
        // whose belief chips cannot be asked what they mean.
        elementsSelectable={true}
        nodesFocusable={true}
        edgesFocusable={false}
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

/** The map, ready to be dropped into a page. */
export function MapCanvas({ world }: { world: WorldView }) {
  return (
    <ReactFlowProvider>
      <MapSurface world={world} />
    </ReactFlowProvider>
  );
}
