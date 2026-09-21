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

/**
 * The words the vocabulary settles, and the only words these buttons may use.
 *
 * *Split this claim* is not among them: it is not built, so it is not offered.
 * The vocabulary still owns its wording, and the test below is what says it is
 * not on the panel.
 */
const BUTTONS = [
  "Suppose this is true",
  "Suppose this is false",
  "This happened",
  "Add a claim",
  "Change this push",
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
  wire: {
    id: "br_hormuz_then_strike",
    label: "Hormuz opens, then Iran is struck",
    parent: null,
    interventions: [{ kind: "do", target: "H", value: true, at: "2026-10-01" }],
  },
};

describe("the branch panel", () => {
  it("test_lists_the_edits_in_the_order_they_were_made", () => {
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

  it("test_renders_only_interface_words", () => {
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

  it("test_an_unedited_map_says_where_its_numbers_came_from", () => {
    // Two different claims about the same screen, and the map must make the one
    // that is true: the engine worked these numbers out, or nobody did.
    const computed = render(
      <BranchPanel
        branches={[STRIKE]}
        openId={null}
        world={{ ...WORLD, versions: 2000 }}
        onOpen={vi.fn()}
        onFork={vi.fn()}
        naming={false}
        onNaming={vi.fn()}
      />,
    );
    expect(screen.getByText(/worked out by the engine/)).toBeInTheDocument();
    expect(computed.container.textContent).not.toContain("the stored example carries");
    computed.unmount();

    render(
      <BranchPanel
        branches={[STRIKE]}
        openId={null}
        world={WORLD}
        onOpen={vi.fn()}
        onFork={vi.fn()}
        naming={false}
        onNaming={vi.fn()}
      />,
    );
    expect(screen.getByText(/the stored example carries/)).toBeInTheDocument();
  });

  it("test_a_map_nobody_has_edited_says_so", () => {
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

  it("test_naming_a_branch_happens_in_the_panel", () => {
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

  it("test_the_six_buttons_are_word_for_word_the_vocabulary", () => {
    open();
    for (const words of BUTTONS) {
      expect(screen.getByRole("button", { name: new RegExp(`^${words}`) })).toBeInTheDocument();
    }
  });

  it("test_no_code_name_reaches_the_screen", () => {
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

  it("test_a_button_appends_an_edit_and_asks_the_engine_for_the_numbers", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^Suppose this is true/ }));
    expect(made).toEqual([{ op: "do", target: "B", value: true, at: WORLD.today }]);
    // Read off the line at the foot of the panel rather than off the panel as a
    // whole: the same sentence is the button's own subtitle now, said before the
    // press as well as after it, and a query over the whole panel would find
    // both and not be able to say which one it meant.
    expect(document.querySelector(".intervene__said")?.textContent ?? "").toMatch(
      /Take this as given/,
    );
  });

  it("test_add_a_claim_opens_the_one_field_that_needs_the_model", () => {
    // A claim is not its wording: it is the wording plus the test that settles
    // it, who judges it and by when. Those are drafted by the one part of this
    // product that calls the model, and this is the one control that asks it.
    // Nothing is recorded by pressing the button — a sentence has to be typed
    // first, and what comes back has to pass the same rules as any proposal.
    const made = open();
    const add = screen.getByRole("button", { name: /^Add a claim/ });
    expect(add).toHaveTextContent("…but this also happens");
    expect(add).not.toBeDisabled();
    fireEvent.click(add);
    expect(made).toEqual([]);
    expect(screen.getByLabelText("…but this also happens")).toBeInTheDocument();
    // And no stack number on screen: a reader does not know what a stack is.
    expect(screen.queryByText(/stack \d/i)).toBeNull();
    expect(screen.queryByText(/pull request/i)).toBeNull();
  });

  it("test_split_this_claim_is_not_offered_at_all", () => {
    // **It used to be a row that said it could do nothing.** That was honest
    // and it was still a seventh of the one menu this product is demonstrated
    // from spent on an absence: a reader counting what they can do to a claim
    // counted one they cannot. What it would do is written where the rest of
    // the unbuilt work is, in `spec/multiverse/interventions.md`, and the words
    // it will come back with are already settled in the vocabulary.
    open();
    expect(screen.queryByRole("button", { name: /Split this claim/ })).toBeNull();
    expect(screen.queryByText(/Split this claim/)).toBeNull();
    // And nothing else took its place as a control that explains itself instead
    // of working: every button on this panel does something when it is pressed.
    expect(screen.queryByText(/not yet built/)).toBeNull();
  });

  it("test_the_two_that_are_easiest_to_confuse_say_the_difference_before_the_press", () => {
    // **The distinction this product beats every competitor on, said before the
    // choice rather than after it.** Both buttons fix a claim's value; they
    // differ in what else may move, and until now the only place that was said
    // was the line printed *after* the press — by which time the reader has
    // already chosen. Each subtitle is the shared vocabulary's own meaning for
    // that operation, word for word from the *Interface words* table.
    open();
    expect(screen.getByRole("button", { name: /^Suppose this is true/ })).toHaveTextContent(
      "Take this as given, and do not tell me what caused it",
    );
    expect(screen.getByRole("button", { name: /^This happened/ })).toHaveTextContent(
      "This is news — update what came before it too",
    );
  });

  it("test_an_arrow_is_named_by_the_claims_at_its_two_ends_never_by_an_identifier", () => {
    open("wire");
    const panel = screen.getByRole("region", { name: "Change this claim" });
    const subject = panel.querySelector(".intervene__subject")?.textContent ?? "";

    // Which arrow a reader is about to change is said in the two claims' own
    // words, the way the Inspector's head says it.
    expect(subject).toContain("The Strait of Hormuz reopens.");
    expect(subject).toContain("→");
    expect(subject).toContain("Brent crude settles below $68");
    // An identifier is never words on the screen — and "H->B" is one.
    expect(subject).not.toContain("H->B");
    expect(subject).not.toMatch(/\bH\b|\bB\b/);
    // It is carried where a test or a tool can read it, the way a tile carries
    // its own: the end-to-end suite asks the panel which arrow it is open on.
    expect(panel).toHaveAttribute("data-about", "H->B");
  });

  it("test_the_panel_says_which_claim_it_is_open_on", () => {
    open("claim");
    expect(screen.getByRole("region", { name: "Change this claim" })).toHaveAttribute(
      "data-about",
      "B",
    );
  });

  it("test_change_this_push_asks_for_an_arrow_instead_of_going_inert", () => {
    const made = open();
    fireEvent.click(screen.getByRole("button", { name: /^Change this push/ }));
    expect(made).toEqual([]);
    expect(screen.getByText(/Choose an arrow on the map first/)).toBeInTheDocument();
  });

  it("test_change_this_push_reads_the_old_number_back_in_words", () => {
    const made = open("wire");
    fireEvent.click(screen.getByRole("button", { name: /^Change this push/ }));
    fireEvent.change(screen.getByLabelText(/How hard does this arrow push/), {
      target: { value: "0.3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change it to that" }));
    expect(made).toEqual([{ op: "retune", link: "H->B", strength: 0.3, wasStrength: 1.6 }]);
    expect(screen.getByText(/You moved this arrow from \+1\.6 to \+0\.3/)).toBeInTheDocument();
  });

  it("test_your_own_number_is_refused_when_the_range_does_not_hold_it", () => {
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

  it("test_your_own_number_sits_beside_the_models", () => {
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

  it("test_opening_the_operations_puts_the_keyboard_in_them", () => {
    // **The way in unmounts the moment it is pressed**, so without this a
    // reader who tabbed to *Change this claim* and pressed Enter would be
    // standing on nothing at all and the next Tab would start again at the top
    // of the page. Taking the keyboard here is not the theft
    // `graph/theKeyboard.ts` forbids: that rule is about who decided, and the
    // one thing pressing this can mean is that the reader wants to be in here.
    //
    // The box takes it rather than the first button inside it, because landing
    // on *Suppose this is true* would leave a reader one stray Space away from
    // an edit they never asked for.
    open();
    const panel = screen.getByRole("region", { name: "Change this claim" });
    expect(document.activeElement).toBe(panel);
    expect(panel).toHaveAttribute("tabindex", "-1");
  });

  it("test_nothing_here_is_disabled", () => {
    render(<InterventionPanel world={WORLD} selection={null} onEdit={vi.fn()} onClose={vi.fn()} />);
    for (const button of screen.getAllByRole("button")) {
      expect(button).not.toBeDisabled();
    }
  });
});
