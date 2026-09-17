/**
 * The path bar renders. It never multiplies.
 *
 * A chain of four plausible steps is not a plausible chain, and the number that
 * says what four steps come to together is the number the map exists to produce.
 * It arrives on the world, computed where the map's numbers are computed. If it
 * is absent the bar says so with its reason; it does not fall back to working
 * one out.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { WorldView } from "../../world";
import { bestBackedRoute, PathBar } from "../PathBar";

/**
 * The stored example's own shape: the strait reaches the contract two ways, and
 * the producers are reachable only through the arrow that feeds back.
 */
function hormuzish(over: Partial<WorldView> = {}): WorldView {
  return aWorld({
    claims: ["H", "C", "B", "R", "M1"].map((id) =>
      aClaim({ id, kind: id === "H" ? "hypothesis" : "event" }),
    ),
    links: [
      aWire({ source: "H", target: "B", provenance: "argued" }),
      aWire({ source: "H", target: "C", provenance: "argued" }),
      aWire({ source: "C", target: "B", provenance: "argued" }),
      aWire({ source: "B", target: "M1", provenance: "argued" }),
      aWire({ source: "B", target: "R", provenance: "argued", reflexive: true }),
      aWire({ source: "R", target: "B", provenance: "argued" }),
    ],
    ...over,
  });
}

describe("which route the bar shows", () => {
  it("test_the_best_backed_route_wins_and_a_tie_goes_to_the_shorter", () => {
    // The contract is reached by H → B → M1 and by H → C → B → M1. Every arrow
    // on both is argued, so their weakest arrows tie — and the tie goes to the
    // shorter.
    const found = bestBackedRoute(hormuzish(), "M1");
    expect(found.found).toBe(true);
    if (!found.found) {
      throw new Error("expected a route");
    }
    expect(found.route.steps.map((step) => step.claim.id)).toEqual(["B", "M1"]);
  });

  it("test_a_better_backed_route_beats_a_shorter_one", () => {
    // Make the direct arrow the model merely asserting, and the long way round
    // becomes the better-backed route even though it takes an extra step.
    const world = hormuzish({
      links: [
        aWire({ source: "H", target: "B", provenance: "asserted" }),
        aWire({ source: "H", target: "C", provenance: "documented" }),
        aWire({ source: "C", target: "B", provenance: "documented" }),
        aWire({ source: "B", target: "M1", provenance: "documented" }),
      ],
    });
    const found = bestBackedRoute(world, "M1");
    if (!found.found) {
      throw new Error("expected a route");
    }
    expect(found.route.steps.map((step) => step.claim.id)).toEqual(["C", "B", "M1"]);
  });

  it("test_a_route_never_walks_the_arrow_that_feeds_back", () => {
    // The producers are reached from the oil price only through the feedback
    // arrow. A chain's likelihood is read on the map with those set aside, so
    // there is no route here — and the bar says so in words.
    expect(bestBackedRoute(hormuzish(), "R")).toEqual({
      found: false,
      why: "nothing-reaches-it",
    });
  });
});

describe("what the bar says", () => {
  it("test_renders_the_product_and_never_computes_one", () => {
    const world = hormuzish();
    const { container } = render(<PathBar world={world} claimId="M1" />);

    // The route by name, and the absence where the number will go.
    expect(screen.getByText("H → B → M1")).toBeInTheDocument();
    expect(screen.getByText("no engine yet")).toBeInTheDocument();
    expect(screen.getByText(/Nothing has worked it out/)).toBeInTheDocument();
    // No number was invented to stand in for the missing one.
    expect(container.querySelector('[data-reading="number"]')).toBeNull();

    // And when the world does carry one, the bar prints it as it was given.
    const withANumber = aWorld({
      ...world,
      claims: world.claims.map((claim) =>
        claim.id === "M1"
          ? aClaim({ ...claim, pathProduct: { reading: { p: 0.18, lo: 0.1, hi: 0.3 } } })
          : claim,
      ),
    });
    const second = render(<PathBar world={withANumber} claimId="M1" />);
    expect(second.container.querySelector('[data-reading="number"]')?.textContent).toBe(".18");
  });

  it("test_tells_no_route_apart_from_no_number", () => {
    // Three readings, and they are never allowed to stand in for one another.
    const world = hormuzish();

    const nothingSelected = render(<PathBar world={world} claimId={null} />);
    expect(
      nothingSelected.container.querySelector('[data-reading="no-path-shown"]')?.textContent,
    ).toBe("no path shown");
    nothingSelected.unmount();

    const noRoute = render(<PathBar world={world} claimId="R" />);
    expect(noRoute.container.querySelector('[data-reading="no-route"]')?.textContent).toBe(
      "no path from the hypothesis reaches this claim any more",
    );
    noRoute.unmount();

    const noNumber = render(<PathBar world={world} claimId="M1" />);
    expect(noNumber.container.querySelector('[data-reading="no-number"]')?.textContent).toBe(
      "no engine yet",
    );
  });

  it("test_the_wart_is_said_out_loud_rather_than_hidden", () => {
    render(<PathBar world={hormuzish()} claimId="M1" />);
    expect(document.body.textContent).toContain("read on its own resolve-by day");
    expect(document.body.textContent).toContain(
      "it is not the chance of the whole chain happening together",
    );
  });

  it("test_the_bar_never_disappears", () => {
    // A missing bar looks like a bar nobody needed. Every state renders one.
    for (const claimId of [null, "H", "R", "M1"]) {
      const { container, unmount } = render(<PathBar world={hormuzish()} claimId={claimId} />);
      expect(container.querySelector(".path-bar")).not.toBeNull();
      unmount();
    }
  });

  it("test_the_hypothesis_has_no_route_into_it_and_says_why", () => {
    render(<PathBar world={hormuzish()} claimId="H" />);
    expect(screen.getByText("no path shown")).toBeInTheDocument();
    expect(document.body.textContent).toContain("This is the claim the map starts from");
  });
});
