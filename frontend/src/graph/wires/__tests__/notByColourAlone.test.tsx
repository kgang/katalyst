/**
 * Nothing on this map is carried by hue alone.
 *
 * Every comparison below leaves colour out, so no test here can ever pass on a
 * hue. What it checks is what a greyscale screenshot keeps: for each of the
 * three kinds of push the stroke's pattern differs, for each of the three steps
 * of a receipt the count of dots differs, and for each direction of financial
 * effect the glyph and the sign differ.
 *
 * This is the automated half of the rule. The other half is a person converting
 * a screenshot to grey and reading it again, which is line 3 of the visual
 * review checklist and runs on every screenshot rather than once at the end.
 */

import { render } from "@testing-library/react";
import { Position, ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import { DirectionReadout } from "../../../components/DirectionReadout";
import { OriginMark } from "../../../components/OriginMark";
import type { LinkShape } from "../../../world";
import { absence } from "../../../world/absence";
import { CausalWire, type WireData } from "../CausalWire";

/** The stroke's pattern for one kind of push, with everything else held still. */
function patternFor(shape: LinkShape) {
  const data: WireData = {
    shape,
    strength: 1.6,
    mode: "trigger",
    lag: 2,
    reflexive: false,
    provenance: "argued",
    conditional: {
      absence: absence("no_engine", "Nothing has worked it out."),
    },
  };
  const { container } = render(
    <ReactFlowProvider>
      <svg aria-hidden="true">
        <title>A wire</title>
        <CausalWire
          id={`X->Y:${shape}`}
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
  const path = container.querySelector("path.wire") as SVGPathElement | null;
  return `${path?.style.strokeDasharray}|${path?.getAttribute("pathLength")}`;
}

describe("the greyscale test", () => {
  it("test_nothing_is_carried_by_hue_alone", () => {
    // What kind of push it is: three patterns, all different, none a colour.
    const patterns = (["impulse", "step", "ramp"] as const).map(patternFor);
    expect(new Set(patterns).size).toBe(3);

    // Where it came from: three counts of dots, all different, none a colour.
    const counts = (["documented", "argued", "asserted"] as const).map((provenance) => {
      const { container } = render(<OriginMark provenance={provenance} use="alone" />);
      return container.querySelectorAll(".origin-mark__dot").length;
    });
    expect(counts).toEqual([3, 2, 1]);

    // Which way the money moves: a glyph and a sign, both different, as well as
    // the hue that is never allowed to travel on its own.
    const up = render(<DirectionReadout direction="up" amount=".18" what="the contract" />);
    const upGlyph = up.container.querySelector(".direction-readout__glyph")?.textContent;
    const upAmount = up.container.querySelector(".direction-readout__amount")?.textContent;
    const down = render(<DirectionReadout direction="down" amount=".18" what="the contract" />);
    const downGlyph = down.container.querySelector(".direction-readout__glyph")?.textContent;
    const downAmount = down.container.querySelector(".direction-readout__amount")?.textContent;

    expect(upGlyph).not.toBe(downGlyph);
    expect(upAmount).not.toBe(downAmount);
  });
});
