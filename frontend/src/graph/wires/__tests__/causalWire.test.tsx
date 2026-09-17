/**
 * A wire says five things at once, and none of them is a colour.
 *
 * The drawing and the words are checked separately, because they are drawn into
 * two different places: the stroke is part of the map's drawing, and the mark
 * and the plate are ordinary page elements laid over it.
 */

import { render, screen } from "@testing-library/react";
import { Position, ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import { Inspector } from "../../../components/Inspector";
import { aWire, aWorld } from "../../../test/aMap";
import type { LinkView } from "../../../world";
import { CausalWire, type WireData, WireLabels } from "../CausalWire";

/** What a wire is handed, with anything a test cares about written over the top. */
function wireData(over: Partial<WireData> = {}): WireData {
  const link = aWire();
  return {
    shape: link.shape,
    strength: link.strength,
    mode: link.mode,
    lag: link.lag,
    reflexive: link.reflexive,
    provenance: link.provenance,
    conditional: link.conditional,
    ...over,
  };
}

/**
 * Draw one wire's stroke.
 *
 * The mark and the plate are drawn through a door the drawing library opens
 * only inside a real map, so outside one this renders the stroke alone — which
 * is exactly what a test about the stroke wants.
 */
function drawWire(data: WireData) {
  const view = render(
    <ReactFlowProvider>
      <svg aria-hidden="true">
        <title>A wire</title>
        <CausalWire
          id="X->Y"
          source="X"
          target="Y"
          sourceX={0}
          sourceY={0}
          targetX={200}
          targetY={40}
          sourcePosition={Position.Right}
          targetPosition={Position.Left}
          data={data}
        />
      </svg>
    </ReactFlowProvider>,
  );
  const stroke = view.container.querySelector("path.wire");
  if (stroke === null) {
    throw new Error("the wire drew no stroke");
  }
  return {
    view,
    stroke,
    split: view.container.querySelector("path.wire__split"),
    /** Everything about the stroke that a reader could see in a grey print. */
    drawing: {
      classes: stroke.getAttribute("class"),
      dashes: (stroke as SVGPathElement).style.strokeDasharray,
      width: (stroke as SVGPathElement).style.strokeWidth,
      pathLength: stroke.getAttribute("pathLength"),
      doubled: view.container.querySelector("path.wire__split") !== null,
    },
  };
}

describe("a wire's five encodings", () => {
  it("test_wire_carries_all_five_encodings", () => {
    // 1 — what kind of push it is: the stroke's pattern.
    const spike = drawWire(wireData({ shape: "impulse" })).drawing.dashes;
    const held = drawWire(wireData({ shape: "step" })).drawing.dashes;
    const climbing = drawWire(wireData({ shape: "ramp" })).drawing.dashes;
    expect(new Set([spike, held, climbing]).size).toBe(3);

    // 2 — how hard it pushes: the stroke's width, in four steps.
    expect(drawWire(wireData({ strength: 0.2 })).drawing.width).toBe("1");
    expect(drawWire(wireData({ strength: 0.9 })).drawing.width).toBe("2");
    expect(drawWire(wireData({ strength: 1.6 })).drawing.width).toBe("3");
    expect(drawWire(wireData({ strength: 2.4 })).drawing.width).toBe("4");

    // 3 — whether it has to keep holding: two strokes rather than one.
    expect(drawWire(wireData({ mode: "trigger" })).drawing.doubled).toBe(false);
    expect(drawWire(wireData({ mode: "sustain" })).drawing.doubled).toBe(true);

    // 4 — whether it loops back: it says so on itself, and it runs over the top
    //     of the map rather than back through it.
    expect(drawWire(wireData({ reflexive: true })).drawing.classes).toContain("wire--reflexive");
    expect(drawWire(wireData({ reflexive: false })).drawing.classes).not.toContain(
      "wire--reflexive",
    );

    // 5 — where it came from: a mark of one, two or three dots at the tail,
    //     never the stroke.
    for (const [provenance, dots] of [
      ["documented", 3],
      ["argued", 2],
      ["asserted", 1],
    ] as const) {
      const { container } = render(
        <WireLabels
          data={wireData({ provenance })}
          sourceX={0}
          sourceY={0}
          plateAt={[100, 20]}
          plateLayout="stacked"
          plateAnchor="-50%"
          selected={false}
        />,
      );
      expect(container.querySelectorAll(".wire-mark .origin-mark__dot")).toHaveLength(dots);
    }
  });

  it("test_the_stroke_is_never_a_hue", () => {
    // Nothing in the wire's own drawing sets a colour. Every wire takes the same
    // muted ink from the stylesheet, and a wire's hue says nothing at all.
    for (const shape of ["impulse", "step", "ramp"] as const) {
      const { stroke } = drawWire(wireData({ shape }));
      expect((stroke as SVGPathElement).style.stroke).toBe("");
    }
  });

  it("test_the_one_backwards_wire_never_crosses_a_tile", () => {
    // Given a route over the top of the map, the drawn path goes up to that line
    // and along it, rather than straight back between the two ends.
    const { stroke } = drawWire(wireData({ reflexive: true, plan: { kind: "sky", skyY: -400 } }));
    expect(stroke.getAttribute("d")).toContain("-400");
  });
});

describe("the mark and the word", () => {
  it("test_wire_and_inspector_draw_the_same_origin_mark", () => {
    // One component, drawn in two places. If the two ever disagreed, the map and
    // the panel would be telling a reader two different things about one arrow.
    const onTheWire = render(
      <WireLabels
        data={wireData({ provenance: "asserted" })}
        sourceX={0}
        sourceY={0}
        plateAt={[100, 20]}
        plateLayout="stacked"
        plateAnchor="-50%"
        selected={false}
      />,
    );
    const wireMark = onTheWire.container.querySelector(".wire-mark .origin-mark");
    const wireDots = wireMark?.querySelectorAll(".origin-mark__dot").length;

    const link: LinkView = aWire({ provenance: "asserted" });
    render(
      <Inspector world={aWorld({ links: [link] })} selection={{ kind: "wire", id: link.id }} />,
    );
    const panelMark = document.querySelector(".inspector__origin .origin-mark");
    const panelDots = panelMark?.querySelectorAll(".origin-mark__dot").length;

    expect(wireDots).toBe(1);
    expect(panelDots).toBe(wireDots);
    expect(panelMark?.getAttribute("data-step")).toBe(wireMark?.getAttribute("data-step"));

    // And the exact word of the seven is in the panel, where there is room for
    // it — never on the picture.
    expect(screen.getByText("asserted")).toBeInTheDocument();
  });
});
