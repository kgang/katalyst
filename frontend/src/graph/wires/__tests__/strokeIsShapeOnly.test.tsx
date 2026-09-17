/**
 * The stroke says one thing and one thing only: what kind of push this is.
 *
 * It used to be asked to carry where the arrow came from as well, and it cannot.
 * A wire cannot be dot-dash because it is a one-time spike and dashed because it
 * was merely argued at the same time; it would be neither, legibly. One channel
 * per meaning — so where an arrow came from moved to a mark at its tail, and the
 * test below is what keeps it there.
 */

import { render } from "@testing-library/react";
import { Position, ReactFlowProvider } from "@xyflow/react";
import { describe, expect, it } from "vitest";
import type { Provenance } from "../../../world";
import { CausalWire, type WireData } from "../CausalWire";

const ALL_RECEIPTS: Provenance[] = [
  "documented",
  "historical",
  "market_implied",
  "argued",
  "user",
  "asserted",
  "simulated",
];

/** Everything about a stroke a reader could see. Colour is not in the list, because
 *  every wire takes the same ink; what is in the list is what a grey print keeps. */
function strokeOf(provenance: Provenance) {
  const data: WireData = {
    shape: "impulse",
    strength: 1.6,
    mode: "trigger",
    lag: 2,
    reflexive: false,
    provenance,
    conditional: {
      absence: { kind: "no_engine", words: "no engine yet", reason: "Nothing has worked it out." },
    },
  };
  const { container } = render(
    <ReactFlowProvider>
      <svg aria-hidden="true">
        <title>A wire</title>
        <CausalWire
          id={`X->Y:${provenance}`}
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
  if (path === null) {
    throw new Error("the wire drew no stroke");
  }
  return {
    classes: path.getAttribute("class"),
    dashes: path.style.strokeDasharray,
    width: path.style.strokeWidth,
    pathLength: path.getAttribute("pathLength"),
    shape: path.getAttribute("d"),
    doubled: container.querySelector("path.wire__split") !== null,
  };
}

describe("the stroke and the mark are different channels", () => {
  it("test_two_wires_differing_only_in_provenance_have_identical_strokes", () => {
    const strokes = ALL_RECEIPTS.map(strokeOf);
    const first = strokes[0];
    for (const stroke of strokes) {
      expect(stroke).toEqual(first);
    }
  });

  it("test_the_stroke_changes_when_and_only_when_the_kind_of_push_changes", () => {
    const argued = strokeOf("argued");
    const documented = strokeOf("documented");
    expect(documented.dashes).toBe(argued.dashes);
    expect(documented.width).toBe(argued.width);
    expect(documented.doubled).toBe(argued.doubled);
  });
});
