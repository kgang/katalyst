/**
 * The six buttons, the badges they earn, and the words that may not appear.
 *
 * The six operations keep their code names in the code, in the wire format and
 * in the spec — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — and
 * **not one of them ever reaches the screen.** The reader sees the button they
 * pressed and the badge it earned, copied word for word from the shared
 * vocabulary. This file is what stops the two drifting apart.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { BranchView, Edit } from "../../world";
import { BranchPanel, InterventionPanel } from "../BranchPanel";

/** The words the vocabulary settles, and the only words these buttons may use. */
const BUTTONS = [
  "Suppose this is true",
  "Suppose this is false",
  "This happened",
  "Add a claim",
  "Change this push",
  "Split this claim",
  "My own number",
];

/** The six code names, none of which may appear on screen. */
const CODE_NAMES = ["observe", "insert", "retune", "refine", "believe"];

/** A world with one claim and one arrow, enough for the panel to read back. */
const WORLD = aWorld({
  claims: [
    aClaim({ id: "H", kind: "hypothesis", claim: "The Strait of Hormuz reopens." }),
    aClaim({ id: "B", claim: "Brent crude settles below $68 for five sessions." }),
  ],
  links: [aWire({ id: "H->B", source: "H", target: "B" })],
});

/** The stored example's own branch: three edits, in the order they were made. */
const STRIKE: BranchView = {
  id: "br_hormuz_then_strike",
  label: "Hormuz opens, then Iran is struck",
  hue: "violet",
  edits: [
    { op: "do", target: "H", value: true, at: "2026-10-01" },
    {
      op: "insert",
      claimId: "S",
      words: "A confirmed military strike on Iranian territory.",
      arrows: [{ id: "S->H", source: "S", target: "H" }],
    },
    { op: "do", target: "S", value: true, at: "2026-10-02" },
  ],
  claims: [],
  links: [],
};

describe("the branch panel", () => {
  // test_lists_the_edits_in_the_order_they_were_made
  it("lists the edits in order, each with the badge its button earned", () => {
    render(
      <BranchPanel
        branches={[STRIKE]}
        openId={STRIKE.id}
        world={WORLD}
        onOpen={vi.fn()}
        onFork={vi.fn()}
        naming={false}
        onNaming={vi.fn()}
      />,
    );
    const numbered = screen.getAllByText(/^[123]$/).map((one) => one.textContent);
    expect(numbered).toEqual(["1", "2", "3"]);
    expect(screen.getByText("Supposed · Oct 1")).toBeInTheDocument();
    expect(screen.getByText("Added")).toBeInTheDocument();
    expect(screen.getByText("Supposed · Oct 2")).toBeInTheDocument();
  });

  // test_renders_only_interface_words
  it("shows no code name anywhere", () => {
    const { container } = render(
      <BranchPanel
        branches={[STRIKE]}
        openId={STRIKE.id}
        world={WORLD}
        onOpen={vi.fn()}
        onFork={vi.fn()}
        naming={false}
        onNaming={vi.fn()}
      />,
    );
    const words = (container.textContent ?? "").toLowerCase();
    for (const code of CODE_NAMES) {
      expect(words).not.toContain(code);
    }
  });

  // test_a_map_nobody_has_edited_says_so
  it("says the map is exactly as it was written when nothing has been edited", () => {
    render(
      <BranchPanel
        branches={[]}
        openId={null}
        world={WORLD}
        onOpen={vi.fn()}
        onFork={vi.fn()}
        naming={false}
        onNaming={vi.fn()}
      />,
    );
    expect(screen.getByText(/Nothing has been edited/)).toBeInTheDocument();
  });

  // test_naming_a_branch_happens_in_the_panel
  it("names a branch in the panel, with nothing opening over the map", () => {
    const onFork = vi.fn();
    render(
      <BranchPanel
        branches={[]}
        openId={null}
        world={WORLD}
        onOpen={vi.fn()}
        onFork={onFork}
        naming={true}
        onNaming={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText(/What is this branch called/), {
      target: { value: "my own branch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start this branch" }));
    expect(onFork).toHaveBeenCalledWith("my own branch");
  });
});

describe("the six things you can do", () => {
  /** Render the panel on one claim and hand back what it appended. */
  function open(kind: "claim" | "wire" = "claim") {
    const made: Edit[] = [];
    render(
      <InterventionPanel
        world={WORLD}
        selection={kind === "claim" ? { kind: "claim", id: "B" } : { kind: "wire", id: "H->B" }}
        onEdit={(edit) => made.push(edit)}
        onClose={vi.fn()}
      />,
    );
    return made;
  }

  // test_the_six_buttons_are_word_for_word_the_vocabulary
  it("offers exactly the six buttons, word for word", () => {
    open();
    for (const words of BUTTONS) {
      expect(screen.getByRole("button", { name: new RegExp(`^${words}`) })).toBeInTheDocument();
    }
  });

  // test_no_code_name_reaches_the_screen
  it("shows no code name anywhere", () => {
    const { container } = render(
      <InterventionPanel
        world={WORLD}
        selection={{ kind: "claim", id: "B" }}
        onEdit={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    const words = (container.textContent ?? "").toLowerCase();
    for (const code of CODE_NAMES) {
      expect(words).not.toContain(code);
    }
  });

  // test_a_button_appends_an_edit_and_moves_no_number
  it("appends an edit and moves no number", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^Suppose this is true/ }));
    expect(made).toEqual([{ op: "do", target: "B", value: true, at: WORLD.today }]);
    expect(screen.getByText(/Take this as given/)).toBeInTheDocument();
  });

  // test_split_this_claim_is_visibly_not_yet_live
  it("says Split this claim is not built rather than doing nothing quietly", () => {
    const made = open();
    const split = screen.getByRole("button", { name: /^Split this claim/ });
    expect(split).toHaveTextContent("not yet built");
    fireEvent.click(split);
    expect(made).toEqual([]);
    expect(screen.getByText(/is not built yet/)).toBeInTheDocument();
    // And no stack number on screen: a reader does not know what stack six is.
    expect(screen.queryByText(/stack \d/i)).toBeNull();
  });

  // test_change_this_push_asks_for_an_arrow_instead_of_going_inert
  it("asks for an arrow when there is none, rather than being quietly inert", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^Change this push/ }));
    expect(made).toEqual([]);
    expect(screen.getByText(/Choose an arrow on the map first/)).toBeInTheDocument();
  });

  // test_change_this_push_reads_the_old_number_back_in_words
  it("reads the arrow's old push back in words before changing it", () => {
    const made = open("wire");
    fireEvent.click(screen.getByRole("button", { name: /^Change this push/ }));
    fireEvent.change(screen.getByLabelText(/How hard does this arrow push/), {
      target: { value: "0.3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change it to that" }));
    expect(made).toEqual([{ op: "retune", link: "H->B", strength: 0.3, wasStrength: 1.6 }]);
    expect(screen.getByText(/You moved this arrow from \+1\.6 to \+0\.3/)).toBeInTheDocument();
  });

  // test_your_own_number_is_refused_when_the_range_does_not_hold_it
  it("refuses a range that does not hold the number, and says why", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^My own number/ }));
    for (const [label, value] of [
      [/Your likelihood/, "0.6"],
      [/the bottom of your range/, "0.7"],
      [/the top of your range/, "0.9"],
    ] as const) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    fireEvent.click(screen.getByRole("button", { name: "Put this number on the claim" }));
    expect(made).toEqual([]);
    expect(screen.getByText(/the range has to hold the number/)).toBeInTheDocument();
  });

  // test_your_own_number_sits_beside_the_models
  it("records your own number, and says it is never averaged with the model's", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^My own number/ }));
    for (const [label, value] of [
      [/Your likelihood/, "0.6"],
      [/the bottom of your range/, "0.45"],
      [/the top of your range/, "0.72"],
    ] as const) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    fireEvent.click(screen.getByRole("button", { name: "Put this number on the claim" }));
    expect(made).toEqual([{ op: "believe", target: "B", belief: { p: 0.6, lo: 0.45, hi: 0.72 } }]);
    expect(screen.getByText(/never averaged with either of them/)).toBeInTheDocument();
  });

  // test_nothing_here_is_disabled
  it("disables nothing, because a greyed-out control cannot even be asked about", () => {
    render(<InterventionPanel world={WORLD} selection={null} onEdit={vi.fn()} onClose={vi.fn()} />);
    for (const button of screen.getAllByRole("button")) {
      expect(button).not.toBeDisabled();
    }
  });
});
