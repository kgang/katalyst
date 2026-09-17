/**
 * A refused branch says everything that is wrong with it, at once.
 *
 * The rule this holds up is the one that makes a tool feel like a colleague
 * rather than a gate: a person fixing a branch one fault per attempt learns only
 * that the thing is hostile. The server gathers every reason an edit produced
 * and hands them over together; this block prints all of them, in the order they
 * arrived, in the server's own words.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Reason } from "../../world";
import { Refusal } from "../Refusal";

/**
 * Three reasons one edit really produces, taken from the engine's own answer to
 * a branch that adds a claim under an identifier the map already has, with one
 * arrow pointing at a claim that is not there and another under an identifier
 * that is taken.
 */
const THREE: Reason[] = [
  {
    code: "duplicate_id",
    subject: "B",
    message:
      'The claim "A claim the reader typed." cannot be added: this map already has a claim ' +
      "under that identifier.",
  },
  {
    code: "unknown_target",
    subject: "NOPE",
    message:
      'The arrow from "A claim the reader typed." to a claim that is not on this map joins a ' +
      "claim that is not on this map.",
  },
  {
    code: "duplicate_id",
    subject: "H->B",
    message:
      'The arrow from "The Strait of Hormuz reopens to unrestricted commercial transit." to "A ' +
      'claim the reader typed." cannot be added: this map already has an arrow under that ' +
      "identifier.",
  },
];

describe("a branch the engine would not fold", () => {
  it("test_a_refused_branch_shows_every_reason_at_once", () => {
    render(<Refusal asking="this map" reasons={THREE} />);

    // All three, not the first one and a promise of more.
    const listed = screen.getAllByRole("listitem");
    expect(listed).toHaveLength(3);
    expect(listed.map((one) => one.textContent)).toEqual(THREE.map((one) => one.message));

    // And the count is said out loud, so a reader knows there are three before
    // reading three.
    expect(screen.getByText(/gave 3 reasons/)).toBeInTheDocument();
  });

  it("test_a_refusal_never_shows_an_identifier_or_a_rule_name", () => {
    const { container } = render(<Refusal asking="this map" reasons={THREE} />);
    const words = container.textContent ?? "";

    // The rule that fired and the thing at fault are for the interface, so that
    // it can point at the right tile. What the reader gets is the sentence.
    expect(words).not.toContain("duplicate_id");
    expect(words).not.toContain("unknown_target");
  });

  it("test_a_refusal_is_not_a_dialog_and_leaves_the_map_alone", () => {
    render(<Refusal asking="this map" reasons={THREE} />);

    // Nothing in this product opens over the map, and a refusal is no
    // exception: it is a block in the panel beside it.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
    expect(screen.getByText(/Nothing was changed on the map/)).toBeInTheDocument();
  });

  it("test_a_refusal_says_why_one_claim_still_has_a_number", () => {
    render(<Refusal asking="this map" reasons={THREE} />);
    // Two tiles beside each other read differently and both are right: a claim
    // the edit can reach has no number because the branch was refused, and one
    // it cannot reach keeps the number the engine worked out for the map as it
    // was written. A reader seeing the pair deserves to be told which is which.
    expect(screen.getByText(/not worked out/)).toBeInTheDocument();
    expect(screen.getByText(/cannot reach keeps the number/)).toBeInTheDocument();
  });

  it("test_one_reason_reads_as_one_reason", () => {
    render(<Refusal asking="this map" reasons={[THREE[0] as Reason]} />);
    expect(screen.getByText(/gave one reason/)).toBeInTheDocument();
  });
});
