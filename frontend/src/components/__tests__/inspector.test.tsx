/**
 * The panel beside the map: why is this number what it is.
 *
 * The rule behind the whole panel: there is no number on this screen whose
 * origin cannot be named in one click, and no absent number that does not say
 * why it is absent. Everything below is one of those two halves.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { Provenance, WorldView } from "../../world";
import { absence } from "../../world/absence";
import { Inspector } from "../Inspector";

/** The map these tests read, with the two claims and the arrow they need. */
function hormuzish(over: Partial<WorldView> = {}): WorldView {
  return aWorld({
    claims: [
      aClaim({
        id: "H",
        kind: "hypothesis",
        claim: "The Strait of Hormuz reopens to unrestricted commercial transit.",
        resolutionCriteria: "At least 14 consecutive days of unrestricted commercial transit.",
        resolutionSource: "Lloyd's List transit counts.",
        resolvesBy: "2026-11-01",
        baseRate: {
          reading: {
            referenceClass: "Closure episodes since 1980 that ended within 90 days.",
            k: 7,
            n: 9,
            sources: [],
          },
        },
        beliefs: {
          model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
          user: { reading: { p: 0.55, lo: 0.4, hi: 0.7 } },
          market: {
            absence: absence("no_market", "no venue quotes this claim"),
          },
        },
        evidenceInFull: [
          {
            line: "An Omani-mediated round is reported, with both sides attending.",
            monogram: "B",
            host: "bbc.com",
            direction: 1,
            url: "https://www.bbc.com/news",
          },
        ],
      }),
      aClaim({
        id: "B",
        claim: "Brent crude settles below $68 for five sessions.",
        beliefs: {
          model: { reading: { p: 0.46, lo: 0.3, hi: 0.63 } },
          user: { absence: absence("not_said", "You have not said.") },
          market: {
            absence: absence("no_market", "no venue quotes this claim"),
          },
        },
      }),
    ],
    links: [
      aWire({
        source: "H",
        target: "B",
        rationale: "The war-risk premium priced into crude unwinds once transit data confirms it.",
        sources: [
          {
            url: "https://www.eia.gov/todayinenergy/detail.php?id=4430",
            title: "The Strait of Hormuz is the world's most important oil transit chokepoint",
            host: "eia.gov",
            retrieved: {
              absence: absence(
                "not_said",
                "nobody fetched this; a person put the address in by hand",
              ),
            },
          },
        ],
      }),
    ],
    ...over,
  });
}

describe("the panel, on a claim", () => {
  it("test_renders_no_dialog_for_any_subject", () => {
    const world = hormuzish();
    for (const subject of [
      null,
      { kind: "claim", id: "H" } as const,
      { kind: "claim", id: "B" } as const,
      { kind: "wire", id: "H->B" } as const,
    ]) {
      const { container, unmount } = render(<Inspector world={world} selection={subject} />);
      expect(container.querySelector("dialog")).toBeNull();
      expect(container.querySelector('[role="dialog"]')).toBeNull();
      expect(container.querySelector('[role="alertdialog"]')).toBeNull();
      expect(container.querySelector('[aria-modal="true"]')).toBeNull();
      unmount();
    }
  });

  it("test_always_renders_all_three_resolution_fields", () => {
    // A claim nobody can score is not a claim: the test, who applies it, and the
    // day it is applied by, all three, on every claim.
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    expect(
      screen.getByText("At least 14 consecutive days of unrestricted commercial transit."),
    ).toBeInTheDocument();
    expect(screen.getByText("Lloyd's List transit counts.")).toBeInTheDocument();
    expect(screen.getByText("2026-11-01")).toBeInTheDocument();
  });

  it("test_renders_three_owners_and_never_averages_them", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    const rows = document.querySelectorAll(".inspector__belief");
    expect(rows).toHaveLength(3);
    expect([...rows].map((row) => row.getAttribute("data-owner"))).toEqual([
      "model",
      "user",
      "market",
    ]);
    // The model says .35 and the reader says .55. The number halfway between
    // them is one nobody holds, and it is nowhere on the screen.
    expect(document.body.textContent).not.toContain(".45 (");
    expect(within(rows[0] as HTMLElement).getByText(/\.35/)).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText(/\.55/)).toBeInTheDocument();
  });

  it("test_renders_a_reason_for_every_absent_value", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "B" }} />);
    // No market, and why: a fact about the world rather than about our plumbing.
    expect(screen.getByText("no market")).toBeInTheDocument();
    expect(screen.getByText("no venue quotes this claim")).toBeInTheDocument();
    // No reference class, and why.
    expect(screen.getByText("no reference class recorded for this claim")).toBeInTheDocument();
    // Nothing has worked the number through the map, and it says so rather than
    // leaving a hole where a decomposition will go.
    // Twice, and both are honest: once where the decomposition will go, and
    // once where the whole chain's likelihood will.
    expect(screen.getAllByText("no engine yet").length).toBeGreaterThan(0);
    // No blank, no zero, no stand-in anywhere.
    expect(document.body.textContent).not.toContain("undefined");
    expect(document.body.textContent).not.toContain("NaN");
  });

  it("test_picks_the_sentence_from_versions", () => {
    // Nothing computed this number, so the range is what whoever wrote it down
    // said about how sure they were. Printing "uncalibrated" over it would claim
    // an arithmetic that never ran.
    const { unmount } = render(
      <Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />,
    );
    expect(screen.getByText("stated range · not computed")).toBeInTheDocument();
    expect(document.body.textContent).toContain("This range is stated, not computed");
    expect(document.body.textContent).not.toContain("uncalibrated");
    unmount();

    render(
      <Inspector world={hormuzish({ versions: 2000 })} selection={{ kind: "claim", id: "H" }} />,
    );
    expect(document.body.textContent).toContain("model interval, uncalibrated");
    expect(document.body.textContent).toContain("Across 2 000 versions of this map");
    expect(document.body.textContent).toContain("eight times in ten");
  });

  it("test_the_band_slot_is_never_drawn_without_versions", () => {
    const { unmount } = render(
      <Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />,
    );
    expect(document.querySelector(".inspector__band-slot")).toBeNull();
    unmount();

    render(
      <Inspector world={hormuzish({ versions: 2000 })} selection={{ kind: "claim", id: "H" }} />,
    );
    // The slot is reserved so the layout does not jump the day the sentence
    // arrives — and it is empty, because a sentence naming a percentage nobody
    // computed is a number nobody computed wearing words.
    const slot = document.querySelector(".inspector__band-slot");
    expect(slot).not.toBeNull();
    expect(slot?.textContent).toBe("");
  });

  it("test_never_derives_a_displayed_number", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    // Seven of nine past cases came out true. The panel prints the count and
    // never the rate: dividing one by the other would be this half of the
    // product working out a number, and it would quietly claim that .78 is the
    // answer — which is what the prior is for and what it is not.
    expect(screen.getByText("7 of 9")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(".78");
  });

  it("test_every_rendered_number_resolves_to_a_subject", () => {
    // Every number in the panel belongs to the claim the panel is open on, and
    // the panel is opened on a claim by selecting its tile. The check here is
    // that the panel never prints a number belonging to something it has not
    // named: the claim's own beliefs, its prior and its base-rate count.
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    const numbers = (document.body.textContent ?? "").match(/\.\d\d/g) ?? [];
    for (const number of numbers) {
      expect([".35", ".22", ".50", ".55", ".40", ".70", ".28", ".15", ".42"]).toContain(number);
    }
  });

  it("test_the_decomposition_is_laid_out_and_never_added_up", () => {
    render(
      <Inspector world={hormuzish({ versions: 2000 })} selection={{ kind: "claim", id: "B" }} />,
    );

    // What it started at, what pushes on it, and what it comes to — every line
    // read from somewhere nameable, and no line that is a sum.
    expect(screen.getByText("it started at")).toBeInTheDocument();
    expect(screen.getByText("it comes to")).toBeInTheDocument();
    expect(screen.getAllByText(/pushes/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nothing on this panel adds them up/)).toBeInTheDocument();

    // The result is the engine's own answer for this claim, printed as it came:
    // once on the belief row, once at the foot of the decomposition.
    expect(screen.getAllByText(".46 (.30–.63)").length).toBe(2);
    expect(screen.getByText(/the engine's own answer for this claim/)).toBeInTheDocument();
  });

  it("test_a_claim_with_no_causes_says_so_rather_than_showing_an_empty_list", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    expect(screen.getByText(/nothing on this map points at this claim/)).toBeInTheDocument();
  });

  it("test_a_feedback_arrow_is_not_one_of_the_pushes_on_this_number", () => {
    // A market acting back on the world it measures is the one arrow allowed to
    // point backwards, and the engine works the map through with those set
    // aside (spec/multiverse/interventions.md). So it is not one of the things
    // that made this number, and listing it among the pushes tells the reader
    // this number has a cause the engine never gave it. It is still on the map
    // and still worth naming, so it is named apart, in the outline's words.
    const world = hormuzish({
      claims: [aClaim({ id: "H", kind: "hypothesis" }), aClaim({ id: "B" }), aClaim({ id: "O" })],
      links: [
        aWire({ id: "B->O", source: "B", target: "O", reflexive: true }),
        aWire({ id: "H->B", source: "H", target: "B" }),
      ],
    });
    render(<Inspector world={world} selection={{ kind: "claim", id: "O" }} />);

    const why = document.querySelector(".inspector__decomposition") as HTMLElement;
    // Not among the pushes, and named apart in the words the outline already
    // reads it in. The only arrow into O is the feedback one, so the
    // decomposition also says outright that nothing pushes on this claim.
    const labels = [...why.querySelectorAll(".inspector__step-label")].map((step) =>
      step.textContent?.trim(),
    );
    expect(labels).toEqual(["it started at", "pushed on by", "fed back into by", "it comes to"]);
    expect(within(why).getByText(/nothing on this map points at this claim/)).toBeInTheDocument();
    // And told why it is apart, in a whole sentence rather than by its position.
    expect(
      within(why).getByText(
        "a market acting back on the world it measures, after 2 days — the engine works this map " +
          "through with feedback arrows set aside, so this arrow has not pushed on this number",
      ),
    ).toBeInTheDocument();
  });

  it("test_a_claim_moved_only_by_reweighting_says_so_in_the_inspector", () => {
    // The engine's difference carries `moved_only_by_reweighting` on the claim's
    // own row, and the browser must never work it out for itself — whether a
    // claim moved for that reason is a fact about how the engine read the
    // numbers. So the panel is driven here with the field set by hand, which
    // checks the one thing this side owns: that the sentence is printed, word
    // for word, exactly when the engine says so and never otherwise. The
    // end-to-end test drives the real engine into the same state.
    const moved = {
      from: 0.356,
      to: 0.365,
      way: "up" as const,
      by: 0.008968,
      sameDirection: { reading: 0 },
    };
    const sentence = "this claim moved only because the observation made some versions count more.";

    const quiet = render(
      <Inspector
        world={hormuzish({
          versions: 2000,
          claims: [aClaim({ id: "H", kind: "hypothesis", diff: "shifted", moved })],
        })}
        selection={{ kind: "claim", id: "H" }}
      />,
    );
    expect(screen.queryByText(sentence)).toBeNull();
    quiet.unmount();

    render(
      <Inspector
        world={hormuzish({
          versions: 2000,
          claims: [
            aClaim({
              id: "H",
              kind: "hypothesis",
              diff: "shifted",
              moved: { ...moved, onlyReweighted: true },
            }),
          ],
        })}
        selection={{ kind: "claim", id: "H" }}
      />,
    );
    expect(screen.getByText(sentence)).toBeInTheDocument();
  });

  it("test_a_moved_claim_shows_the_two_readings_and_the_share_that_agreed", () => {
    render(
      <Inspector
        world={hormuzish({
          versions: 2000,
          claims: [
            aClaim({
              id: "H",
              kind: "hypothesis",
              diff: "shifted",
              moved: {
                from: 0.356,
                to: 0.081,
                way: "down",
                by: -0.275,
                sameDirection: { reading: 1 },
              },
            }),
          ],
        })}
        selection={{ kind: "claim", id: "H" }}
      />,
    );
    expect(screen.getByText(".36 ▼ .081")).toBeInTheDocument();
    // The chevron is never the only thing saying which way it went.
    expect(screen.getByText("down")).toBeInTheDocument();
    expect(screen.getByText("same direction")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});

describe("the panel, on an arrow", () => {
  it("test_reads_the_push_back_in_words", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "wire", id: "H->B" }} />);
    expect(screen.getByText("+1.6")).toBeInTheDocument();
    expect(screen.getByText(/a strong push toward/)).toBeInTheDocument();
  });

  it("test_the_conditional_is_an_absence_until_the_arrow_is_asked_about", () => {
    const { unmount } = render(
      <Inspector world={hormuzish()} selection={{ kind: "wire", id: "H->B" }} />,
    );
    // It costs a whole extra run of the map, so it is asked for one arrow at a
    // time — and until it arrives the panel says that rather than showing a
    // dash that looks like a number that failed to load.
    expect(screen.getByText("With its cause supposed true")).toBeInTheDocument();
    expect(screen.getAllByText("no engine yet").length).toBeGreaterThan(0);
    unmount();

    const world = hormuzish();
    render(
      <Inspector
        world={{
          ...world,
          links: world.links.map((wire) => ({
            ...wire,
            conditional: { reading: { p: 0.584, lo: 0.416, hi: 0.734 } },
          })),
        }}
        selection={{ kind: "wire", id: "H->B" }}
      />,
    );
    expect(screen.getByText(".58 (.42–.73)")).toBeInTheDocument();
    expect(screen.getByText(/supposed, never observed/)).toBeInTheDocument();
  });

  it("test_says_what_kind_of_push_and_what_it_does_over_time", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "wire", id: "H->B" }} />);
    expect(screen.getByText(/domino/)).toBeInTheDocument();
    expect(screen.getByText(/half gone after 30 days/)).toBeInTheDocument();
    expect(screen.getByText(/2 days after its cause becomes true/)).toBeInTheDocument();
  });

  it("test_renders_a_fetch_day_or_its_reason", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "wire", id: "H->B" }} />);
    // Nothing was fetched for this arrow — a person put the address in by hand —
    // so the field says that rather than printing a day nobody fetched anything
    // on. A source with no retrieval day is never rendered as though it had one.
    expect(screen.getByText(/nobody fetched this/)).toBeInTheDocument();
    expect(screen.getByText("eia.gov")).toBeInTheDocument();
  });

  it("test_the_panels_mark_matches_the_wires_mark", () => {
    for (const [provenance, dots] of [
      ["documented", 3],
      ["argued", 2],
      ["asserted", 1],
    ] as [Provenance, number][]) {
      const world = hormuzish({ links: [aWire({ source: "H", target: "B", provenance })] });
      const { unmount } = render(
        <Inspector world={world} selection={{ kind: "wire", id: "H->B" }} />,
      );
      expect(document.querySelectorAll(".inspector__origin .origin-mark__dot")).toHaveLength(dots);
      // And the exact word of the seven, which is what this panel is for.
      expect(screen.getByText(provenance.replace("_", " "))).toBeInTheDocument();
      unmount();
    }
  });
});

describe("the panel, on nothing", () => {
  it("test_an_empty_selection_is_a_state_with_its_own_words", () => {
    render(<Inspector world={hormuzish()} selection={null} />);
    expect(screen.getByText("Nothing selected")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Choose a claim or an arrow on the map");
  });
});

describe("the way from reading to doing", () => {
  /**
   * **The panel of operations used to open from one key and one command and
   * nowhere else.** Somebody working this screen with a mouse could click every
   * tile, read the whole argument, find no verb anywhere on it and conclude the
   * tool is a viewer — which is the opposite of what this product is. The head
   * of the panel now carries the way in, on a claim and on an arrow, in the
   * shared vocabulary's own words.
   */
  it("test_the_head_opens_the_operations_on_a_claim_and_on_an_arrow", () => {
    const opened: string[] = [];
    const claim = render(
      <Inspector
        world={hormuzish()}
        selection={{ kind: "claim", id: "H" }}
        onChangeThis={() => opened.push("claim")}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Change this claim" }));
    expect(opened).toEqual(["claim"]);
    claim.unmount();

    render(
      <Inspector
        world={hormuzish()}
        selection={{ kind: "wire", id: "H->B" }}
        onChangeThis={() => opened.push("arrow")}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Change this push" }));
    expect(opened).toEqual(["claim", "arrow"]);
  });

  it("test_with_nothing_to_open_no_control_is_drawn", () => {
    // Two callers leave it out and both are right to: the screen that watches a
    // map build itself has no branch to edit, and the map screen leaves it out
    // while the panel is already open. A control that does nothing is not a
    // control — and on an arrow, a second one would put two buttons reading
    // *Change this push* on one screen.
    for (const subject of [
      { kind: "claim", id: "H" } as const,
      { kind: "wire", id: "H->B" } as const,
    ]) {
      const { unmount } = render(<Inspector world={hormuzish()} selection={subject} />);
      expect(screen.queryByRole("button", { name: "Change this claim" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Change this push" })).toBeNull();
      unmount();
    }
  });

  it("test_it_is_a_word_with_a_hairline_round_it_and_never_a_default_button", () => {
    // The shape a button takes in this product. Checked as the class the
    // stylesheet styles, because a component test has no layout engine and the
    // alternative — asserting a colour — is the thing this rule exists to
    // prevent.
    const { container } = render(
      <Inspector
        world={hormuzish()}
        selection={{ kind: "claim", id: "H" }}
        onChangeThis={() => undefined}
      />,
    );
    const control = screen.getByRole("button", { name: "Change this claim" });
    expect(control).toHaveClass("inspector__change");
    // In the head, beside what it is about, and not somewhere else in the panel.
    expect(container.querySelector(".inspector__head")?.contains(control)).toBe(true);
  });
});
