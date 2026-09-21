/**
 * **A wire's two ends are declared, so no wire waits to be measured.**
 *
 * The drawing library draws a wire between two ports, and it refuses to draw
 * one whose ports it cannot place: `getEdgePosition` returns nothing when
 * either end is not initialised, and the whole arrow is then absent from the
 * page. Left to itself the library finds a port by measuring the rendered
 * tile — through the same size notification a busy browser abandons when too
 * many fall due in one frame, and an abandoned one is never delivered. Drop
 * every tile's notification and the map draws every claim, in its place, and
 * not one arrow. That is the wrong picture of the argument, and a silent one.
 * It was met in the wild about once in two hundred runs.
 *
 * So the ports are handed over, with the box, from the one place that worked
 * them out. The library accepts a declared port in place of a measured one, and
 * a map whose tiles all say where their ports are is fully drawable on the
 * first frame with nothing measured at all.
 *
 * **Three statements, and the third is the one that matters.** Every wire's two
 * ends are declared by name; the ports are placed from the very height the box
 * was declared at; and **what the tile draws is what the library was told** —
 * because the library keeps measuring afterwards, and a declared number that
 * disagreed with the measured one would jump a wire's ends back and forth
 * between them every time the map was redrawn.
 */

import { render } from "@testing-library/react";
import { Position, ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import { Tile } from "../../components/Tile";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import { TILE_WIDTH } from "../geometry";
import { PORTS, type Port, portBox, portsForAWire, portsOf } from "../ports";
import { toFlow } from "../toFlow";
import { socketsFor } from "../wires/plates";

/** The stored example's shape, which is the map every browser test opens. */
function stored() {
  return aWorld({
    hypothesisId: "H",
    claims: [
      aClaim({ id: "H", kind: "hypothesis", claim: "The Strait of Hormuz reopens." }),
      aClaim({ id: "C", claim: "Lloyd's war-risk premium falls below 0.4%." }),
      aClaim({ id: "B", claim: "Brent crude settles below $68 for five sessions." }),
      aClaim({ id: "R", claim: "OPEC+ announces output restraint." }),
      aClaim({ id: "M1", kind: "market", claim: "A Polymarket contract resolves YES." }),
    ],
    links: [
      aWire({ source: "H", target: "C", mode: "sustain" }),
      aWire({ source: "C", target: "B" }),
      aWire({ source: "B", target: "M1" }),
    ],
  });
}

/**
 * Where the drawing library will put this end of a wire, from a declared port.
 *
 * This is the library's own rule, restated in one line so that the check below
 * is a check and not a copy: a port on the left edge is attached to at its left
 * edge, one on the right at its right edge, and both halfway down their own
 * height. (`@xyflow/system`, `getHandlePosition`.)
 */
function whereTheWireAttaches(height: number, port: Port): { x: number; y: number } {
  const box = portBox(height, port);
  return {
    x: port.edge === Position.Left ? box.x : box.x + box.width,
    y: box.y + box.height / 2,
  };
}

describe("no wire waits for a port to be measured", () => {
  it("test_every_wire_names_two_ports_the_tiles_declare", () => {
    const drawing = toFlow(stored());
    expect(drawing.edges.length).toBeGreaterThan(0);

    const declared = new Map(drawing.nodes.map((node) => [node.id, node.handles ?? []]));
    for (const wire of drawing.edges) {
      // The library looks a wire's end up among the source ports of the tile it
      // leaves and the target ports of the tile it arrives at, by name. Either
      // lookup coming back empty is an arrow that is never drawn.
      const leaves = declared
        .get(wire.source)
        ?.filter((port) => port.type === "source")
        .map((port) => port.id);
      const arrives = declared
        .get(wire.target)
        ?.filter((port) => port.type === "target")
        .map((port) => port.id);
      expect(leaves, `${wire.id} leaves a tile that declared no port to leave from`).toContain(
        wire.sourceHandle,
      );
      expect(arrives, `${wire.id} arrives at a tile that declared no port to land in`).toContain(
        wire.targetHandle,
      );
    }
  });

  it("test_a_port_is_placed_from_the_height_the_box_was_declared_at", () => {
    // Two maps, because a tile's height comes from two places: its own claim,
    // and a diff that reserved the taller of two paintings for it so that
    // flipping between them moves nothing. A tile that grew has to take its
    // ports down with it, or its wires arrive where the tile no longer is.
    const taller = new Map([["B", 400]]);
    const maps = [toFlow(stored()), toFlow(stored(), taller)];

    for (const drawing of maps) {
      for (const node of drawing.nodes) {
        if (node.type !== "claim") {
          // Only a claim is ever at the end of an arrow, so only a claim's tile
          // has ports — and the tile standing in for a collapsed column is told
          // it has none rather than told the wrong ones.
          expect(node.handles).toBeUndefined();
          continue;
        }
        const height = node.initialHeight;
        expect(height, `${node.id} did not say how tall it is`).toBeGreaterThan(0);
        // Not "both are numbers": the ports the tile declared are the ports
        // that height produces, port for port.
        expect(node.handles).toEqual(portsOf(height ?? 0));
      }
    }

    // And the map with a taller box really did have one, or the walk above
    // compared every tile with itself.
    const grew = maps[1]?.nodes.find((node) => node.id === "B");
    const asItWas = maps[0]?.nodes.find((node) => node.id === "B");
    expect(grew?.initialHeight).toBe(400);
    expect(grew?.handles?.[0]?.y).toBeGreaterThan(asItWas?.handles?.[0]?.y ?? 0);
  });

  it("test_a_declared_port_is_where_the_tile_draws_it", () => {
    // A tile as tall as a tile in the stored example, taken from the drawing
    // rather than written down, so this cannot drift from what the map draws.
    const drawing = toFlow(stored());
    const one = drawing.nodes.find((node) => node.type === "claim");
    const height = one?.initialHeight ?? 0;
    expect(height).toBeGreaterThan(0);

    const page = render(
      <ReactFlowProvider>
        <Tile claim={aClaim({ id: "C" })} isHypothesis={false} height={height} />
      </ReactFlowProvider>,
    );

    const drawn = [...page.container.querySelectorAll<HTMLElement>(".tile__port")];
    expect(drawn).toHaveLength(PORTS.length);
    for (const [at, port] of PORTS.entries()) {
      const box = portBox(height, port);
      const element = drawn[at];
      expect(element?.dataset.handleid, "the ports are drawn in the declared order").toBe(port.id);
      // What is written on the element is what the library was handed. Anything
      // else and the wire's ends move by the difference, every time the library
      // measures the page and every time the map is redrawn afterwards.
      expect(element?.style.left).toBe(`${box.x}px`);
      expect(element?.style.top).toBe(`${box.y}px`);
      expect(element?.style.width).toBe(`${box.width}px`);
      expect(element?.style.height).toBe(`${box.height}px`);
      // The library's own stylesheet would otherwise shift a port by half its
      // own size and pin it to the edge it is on. Both are said in full above,
      // so both are turned off here.
      expect(element?.style.transform).toBe("none");
      expect(element?.style.right).toBe("auto");
    }
  });

  it("test_a_wire_attaches_where_the_plate_expects_it", () => {
    // The plate beside a wire has to be placed before a single wire is drawn,
    // so `plates.ts` works out where a wire will start from the layout alone.
    // If that ever disagrees with where the library actually attaches it, every
    // plate on the map is placed against wires that are somewhere else.
    const height = 200;
    const cause = { x: 0, y: 0, width: TILE_WIDTH, height };
    const effect = { x: 500, y: 40, width: TILE_WIDTH, height };
    const boxes = new Map([
      ["H", cause],
      ["C", effect],
    ]);

    for (const mode of ["trigger", "sustain"] as const) {
      const named = portsForAWire(mode);
      const sockets = socketsFor(
        { id: "H->C", source: "H", target: "C", handle: named.source, reflexive: false },
        boxes,
      );
      const leaves = PORTS.find((port) => port.id === named.source);
      const arrives = PORTS.find((port) => port.id === named.target);
      if (leaves === undefined || arrives === undefined) {
        throw new Error(`a wire that ${mode}s names a port no tile has`);
      }
      // The declared port's place is inside its tile; the plate's is on the
      // map. One is the other plus where the tile ended up.
      const from = whereTheWireAttaches(height, leaves);
      const to = whereTheWireAttaches(height, arrives);
      expect(sockets?.sourceX).toBeCloseTo(cause.x + from.x, 10);
      expect(sockets?.sourceY).toBeCloseTo(cause.y + from.y, 10);
      expect(sockets?.targetX).toBeCloseTo(effect.x + to.x, 10);
      expect(sockets?.targetY).toBeCloseTo(effect.y + to.y, 10);
    }
  });
});
