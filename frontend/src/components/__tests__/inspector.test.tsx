/**
 * The panel beside the map: why is this number what it is.
 *
 * The rule behind the whole panel: there is no number on this screen whose
 * origin cannot be named in one click, and no absent number that does not say
 * why it is absent. Everything below is one of those two halves.
 */

import { readFileSync } from "node:fs";
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
        // **A count this test made up, and it says so** *(2026-09-22)*. The panel
        // has to be shown a count to be tested for how it prints one, and there is
        // no longer a count anywhere on the curated map to borrow: the one that
        // used to sit on this claim counted Hormuz *disruptions* against a claim
        // about a *closure* — a different kind of event — and the fixture dropped
        // it rather than replace it with a number nobody had counted. So this one
        // belongs to the test, is about nothing in the world, and is never quoted
        // anywhere else.
        baseRate: {
          reading: {
            referenceClass: "A class this test invented, standing for whatever a map might count.",
            k: 4,
            n: 11,
            sources: [],
          },
        },
        beliefs: {
          model: { reading: { p: 0.35 } },
          user: { reading: { p: 0.55 } },
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
          model: { reading: { p: 0.46 } },
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

  // **Two tests stood here and are replaced by one** *(Kent, 2026-09-22, R48)*.
  // `test_picks_the_sentence_from_versions` checked that the panel said *stated
  // range · not computed* over a number nobody had worked out and *model
  // interval, uncalibrated · … Across 2 000 versions of this map…* over one the
  // engine had; `test_the_band_slot_is_never_drawn_without_versions` checked the
  // empty slot reserved under it for *why is this band wide?*. There is no
  // range, so neither sentence and neither slot has anything to be about.
  it("test_the_panel_says_nothing_about_a_range_or_about_versions", () => {
    for (const world of [hormuzish(), hormuzish({ workedOut: true })]) {
      const { unmount } = render(
        <Inspector world={world} selection={{ kind: "claim", id: "H" }} />,
      );
      const words = (document.body.textContent ?? "").toLowerCase();
      for (const forbidden of ["uncalibrated", "interval", "version", "worlds", "middle 80"]) {
        expect(words).not.toContain(forbidden);
      }
      // And nothing that reads as a pair of numbers with a dash between them.
      expect(document.body.textContent ?? "").not.toMatch(/[.>]\d+\s*[–-]\s*[.<>]/);
      expect(document.querySelector(".inspector__band-slot")).toBeNull();
      unmount();
    }
  });

  it("test_never_derives_a_displayed_number", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    // Four of eleven past cases came out true, by this test's own made-up count.
    // The panel prints the count and never the rate: dividing one by the other
    // would be this half of the product working out a number, and it would quietly
    // claim that .36 is the answer — which is what the prior is for and what it is
    // not.
    expect(screen.getByText("4 of 11")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(".36");
  });

  it("test_a_claim_with_no_count_behind_it_says_so_in_words", () => {
    // **The live path** *(2026-09-22)*. No claim on the curated map carries a
    // count of past cases, so what the panel actually draws beside a claim is this
    // absence — the words and the reason for them, never an empty slot and never a
    // number invented to fill one.
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "B" }} />);
    expect(document.body.textContent).not.toMatch(/\d+ of \d+/);
    expect(screen.getByText(/not said/i)).toBeInTheDocument();
  });

  it("test_every_rendered_number_resolves_to_a_subject", () => {
    // Every number in the panel belongs to the claim the panel is open on, and
    // the panel is opened on a claim by selecting its tile. The check here is
    // that the panel never prints a number belonging to something it has not
    // named: the claim's own beliefs, its prior and its base-rate count.
    render(<Inspector world={hormuzish()} selection={{ kind: "claim", id: "H" }} />);
    const numbers = (document.body.textContent ?? "").match(/\.\d\d/g) ?? [];
    for (const number of numbers) {
      expect([".35", ".55", ".28"]).toContain(number);
    }
  });

  it("test_the_decomposition_is_laid_out_and_never_added_up", () => {
    render(
      <Inspector world={hormuzish({ workedOut: true })} selection={{ kind: "claim", id: "B" }} />,
    );

    // What it started at, what pushes on it, and what it comes to — every line
    // read from somewhere nameable, and no line that is a sum.
    expect(screen.getByText("it started at")).toBeInTheDocument();
    expect(screen.getByText("it comes to")).toBeInTheDocument();
    expect(screen.getAllByText(/pushes/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nothing on this panel adds them up/)).toBeInTheDocument();

    // The result is the engine's own answer for this claim, printed as it came:
    // once on the belief row, once at the foot of the decomposition.
    expect(screen.getAllByText(".46").length).toBe(2);
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

  // **This test was `test_a_claim_moved_only_by_reweighting_says_so_in_the_inspector`**
  // and now asserts the sentence's absence (Kent, 2026-09-22, R48). The engine
  // still carries `moved_only_by_reweighting` on a claim's row; what it says is
  // that a claim moved only because an observation made some of the two thousand
  // versions of the map count for more than others, and there are no versions of
  // the map on this screen for it to be about. `world/apiSource.ts` is where it
  // stops, and it dies with the engine half.
  it("test_no_sentence_about_reweighting_reaches_the_panel", () => {
    render(
      <Inspector
        world={hormuzish({
          workedOut: true,
          claims: [
            aClaim({
              id: "H",
              kind: "hypothesis",
              diff: "shifted",
              moved: { from: 0.356, to: 0.365, way: "up", by: 0.008968 },
            }),
          ],
        })}
        selection={{ kind: "claim", id: "H" }}
      />,
    );
    const words = (document.body.textContent ?? "").toLowerCase();
    expect(words).not.toContain("count more");
    expect(words).not.toContain("reweight");
    expect(words).not.toContain("version");
  });

  // **This test was `test_a_moved_claim_shows_the_two_readings_and_the_share_that_agreed`.**
  // The share was *same direction* — how many of the two thousand versions of
  // the map moved the same way — and it went with them (Kent, 2026-09-22, R48).
  // What a moved claim shows is the two readings and the direction.
  it("test_a_moved_claim_shows_the_two_readings_and_the_direction", () => {
    const { container } = render(
      <Inspector
        world={hormuzish({
          workedOut: true,
          claims: [
            aClaim({
              id: "H",
              kind: "hypothesis",
              diff: "shifted",
              moved: { from: 0.356, to: 0.081, way: "down", by: -0.275 },
            }),
          ],
        })}
        selection={{ kind: "claim", id: "H" }}
      />,
    );
    expect(screen.getByText(".36 ▼ .081")).toBeInTheDocument();
    // The chevron is never the only thing saying which way it went.
    expect(screen.getByText("down")).toBeInTheDocument();
    // And nothing beside it counts anything: no column, no share, no percentage.
    expect(screen.queryByText("same direction")).toBeNull();
    expect(container.textContent ?? "").not.toMatch(/\d+%/);
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
            conditional: { reading: { p: 0.584 } },
          })),
        }}
        selection={{ kind: "wire", id: "H->B" }}
      />,
    );
    expect(screen.getByText(".58")).toBeInTheDocument();
    expect(screen.getByText(/supposed, never observed/)).toBeInTheDocument();
  });

  it("test_says_what_kind_of_push_and_what_it_does_over_time", () => {
    render(<Inspector world={hormuzish()} selection={{ kind: "wire", id: "H->B" }} />);
    expect(screen.getByText(/undoing the cause later does not undo it/)).toBeInTheDocument();
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

  it("test_the_way_in_is_a_word_with_a_hairline_round_it", () => {
    // **Read off the stylesheet, not off the component.** Asserting the class
    // the component itself writes would pass with the stylesheet deleted, which
    // is a test that cannot fail for the thing it is named after. What is
    // checked is the rule: a hairline round it, the panel's own surface behind
    // it, the interface face — the shape every button in this product takes —
    // and no fill drawn from the accent, which is what a template-looking
    // button is made of.
    const sheet = readFileSync("src/components/inspector.css", "utf8");
    const rule = /\.inspector__change \{([^}]*)\}/.exec(sheet)?.[1] ?? "";
    expect(rule, "inspector.css has no rule for the way in").not.toBe("");
    expect(rule).toMatch(/border:\s*1px solid var\(--hairline\)/);
    expect(rule).toMatch(/background:\s*var\(--surface\)/);
    expect(rule).toMatch(/font-family:\s*var\(--font-interface\)/);
    expect(rule).not.toMatch(/var\(--accent\)/);
    expect(rule).not.toMatch(/box-shadow/);

    // And it is in the head, beside what it is about, rather than somewhere
    // else in the panel.
    const { container } = render(
      <Inspector
        world={hormuzish()}
        selection={{ kind: "claim", id: "H" }}
        onChangeThis={() => undefined}
      />,
    );
    const control = screen.getByRole("button", { name: "Change this claim" });
    expect(control).toHaveClass("inspector__change");
    expect(container.querySelector(".inspector__head")?.contains(control)).toBe(true);
  });
});
