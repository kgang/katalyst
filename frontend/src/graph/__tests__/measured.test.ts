/**
 * **Every tile is drawn, and no tile waits to be measured.**
 *
 * The drawing library draws nothing it has not measured: a node with no size is
 * rendered `visibility: hidden`, and it learns the size by watching the element
 * change size. That is a promise the browser does not keep. When too many size
 * observations fall due in one frame it abandons the rest of them — *"a
 * ResizeObserver loop completed with undelivered notifications"* — and an
 * abandoned one is never delivered. A tile whose box then never changes size
 * again is never observed again, so it stays invisible for the life of the page:
 * the map holds its claims, in their places, and a reader cannot see them.
 *
 * **It is reachable today.** On a cold machine the stored example opens with
 * every tile hidden, and the end-to-end test finds it as *"expected visible,
 * received hidden"* on `.react-flow__node`. Nothing has to go wrong for a reader
 * to meet it; the browser only has to be busy.
 *
 * We are not guessing at the size. A tile is 280 pixels wide and exactly as tall
 * as the height worked out from its claim, the components draw themselves at
 * precisely those numbers, and the layout engine is handed the same ones. So the
 * fix is to say it: one number, from the one place that worked it out, given to
 * both of the things that need it.
 *
 * Two statements, and the second is the one that matters. Every tile says how
 * big it is — and **what it says is the same number the layout was given**,
 * because a tile drawn at one size in a space reserved at another is two tiles
 * on one spot, which is the collision the layout exists to prevent.
 */

import { describe, expect, it } from "vitest";
import { A_REAL_RUN, THE_REAL_SENTENCE } from "../../stream/__tests__/aRealRun";
import { BELIEFS, THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import { foldAll, waitingFor } from "../../stream/growth";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import { TILE_WIDTH } from "../geometry";
import { toFlow } from "../toFlow";

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
      aWire({ source: "H", target: "C" }),
      aWire({ source: "C", target: "B" }),
      aWire({ source: "B", target: "M1" }),
    ],
  });
}

describe("no tile waits to be measured", () => {
  it("test_every_tile_tells_the_drawing_library_its_own_size", () => {
    const drawing = toFlow(stored());
    expect(drawing.nodes.length).toBeGreaterThan(0);

    for (const node of drawing.nodes) {
      expect(node.initialWidth, `${node.id} did not say how wide it is`).toBe(TILE_WIDTH);
      expect(node.initialHeight, `${node.id} did not say how tall it is`).toBeGreaterThan(0);
    }
  });

  it("test_what_a_tile_says_is_what_the_layout_was_given", () => {
    // Five maps, because a tile's height comes from three different places — its
    // own claim, a diff that reserved the taller of two paintings for it, and
    // the floor every box that is not a claim is drawn at — and because a map
    // that is still being built has a third kind of box on it. **A reserved
    // rectangle is the box that needs saying most**: it stands where a claim is
    // about to arrive, so it is on screen at the exact moment the page is
    // busiest and the browser is likeliest to drop an observation.
    const reserved = [{ id: "skeleton:H", words: "one step on from …", after: "H" }];
    const taller = new Map([["B", 400]]);
    const maps = [
      toFlow(stored()),
      toFlow(stored(), taller),
      toFlow(foldAll(waitingFor(THE_SENTENCE, null), THE_GROWTH).world, undefined, reserved),
      toFlow(foldAll(waitingFor(THE_SENTENCE, null), [...THE_GROWTH, BELIEFS]).world),
      toFlow(foldAll(waitingFor(THE_REAL_SENTENCE, null), A_REAL_RUN).world),
    ];

    for (const drawing of maps) {
      const reservedFor = new Map(drawing.tiles.map((tile) => [tile.id, tile.height]));
      expect(reservedFor.size).toBe(drawing.nodes.length);
      for (const node of drawing.nodes) {
        // Not "both are a number": the same number. A box drawn at one height in
        // a space reserved at another is the collision the layout prevents.
        expect(node.initialHeight, `${node.id} is drawn at a height nobody reserved`).toBe(
          reservedFor.get(node.id),
        );
      }
    }

    // And the map with a taller box in it really did have one, or the walk above
    // compared every tile with itself.
    const withTaller = maps[1];
    expect(withTaller?.nodes.find((node) => node.id === "B")?.initialHeight).toBe(400);
  });
});
