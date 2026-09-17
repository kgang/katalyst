/**
 * The panel beside the map: why is this number what it is.
 *
 * The rule behind the whole panel: there is no number on this screen whose
 * origin cannot be named in one click, and no absent number that does not say
 * why it is absent. Everything below is one of those two halves.
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { Provenance, WorldView } from "../../world";
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
          market: { absence: { words: "no market", reason: "no venue quotes this claim" } },
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
          user: { absence: { words: "—", reason: "You have not said." } },
          market: { absence: { words: "no market", reason: "no venue quotes this claim" } },
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
              absence: {
                words: "—",
                reason: "nobody fetched this; a person put the address in by hand",
              },
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
      const { container, unmount } = render(<Inspector world={world} subject={subject} />);
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
    render(<Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />);
    expect(
      screen.getByText("At least 14 consecutive days of unrestricted commercial transit."),
    ).toBeInTheDocument();
    expect(screen.getByText("Lloyd's List transit counts.")).toBeInTheDocument();
    expect(screen.getByText("2026-11-01")).toBeInTheDocument();
  });

  it("test_renders_three_owners_and_never_averages_them", () => {
    render(<Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />);
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
    render(<Inspector world={hormuzish()} subject={{ kind: "claim", id: "B" }} />);
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
      <Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />,
    );
    expect(screen.getByText("stated range · not computed")).toBeInTheDocument();
    expect(document.body.textContent).toContain("This range is stated, not computed");
    expect(document.body.textContent).not.toContain("uncalibrated");
    unmount();

    render(
      <Inspector world={hormuzish({ versions: 2000 })} subject={{ kind: "claim", id: "H" }} />,
    );
    expect(document.body.textContent).toContain("model interval, uncalibrated");
    expect(document.body.textContent).toContain("Across 2 000 versions of this map");
    expect(document.body.textContent).toContain("eight times in ten");
  });

  it("test_the_band_slot_is_never_drawn_without_versions", () => {
    const { unmount } = render(
      <Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />,
    );
    expect(document.querySelector(".inspector__band-slot")).toBeNull();
    unmount();

    render(
      <Inspector world={hormuzish({ versions: 2000 })} subject={{ kind: "claim", id: "H" }} />,
    );
    // The slot is reserved so the layout does not jump the day the sentence
    // arrives — and it is empty, because a sentence naming a percentage nobody
    // computed is a number nobody computed wearing words.
    const slot = document.querySelector(".inspector__band-slot");
    expect(slot).not.toBeNull();
    expect(slot?.textContent).toBe("");
  });

  it("test_never_derives_a_displayed_number", () => {
    render(<Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />);
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
    render(<Inspector world={hormuzish()} subject={{ kind: "claim", id: "H" }} />);
    const numbers = (document.body.textContent ?? "").match(/\.\d\d/g) ?? [];
    for (const number of numbers) {
      expect([".35", ".22", ".50", ".55", ".40", ".70", ".28", ".15", ".42"]).toContain(number);
    }
  });
});

describe("the panel, on an arrow", () => {
  it("test_reads_the_push_back_in_words", () => {
    render(<Inspector world={hormuzish()} subject={{ kind: "wire", id: "H->B" }} />);
    expect(screen.getByText("+1.6")).toBeInTheDocument();
    expect(screen.getByText(/a strong push toward/)).toBeInTheDocument();
  });

  it("test_says_what_kind_of_push_and_what_it_does_over_time", () => {
    render(<Inspector world={hormuzish()} subject={{ kind: "wire", id: "H->B" }} />);
    expect(screen.getByText(/domino/)).toBeInTheDocument();
    expect(screen.getByText(/half gone after 30 days/)).toBeInTheDocument();
    expect(screen.getByText(/2 days after its cause becomes true/)).toBeInTheDocument();
  });

  it("test_renders_a_fetch_day_or_its_reason", () => {
    render(<Inspector world={hormuzish()} subject={{ kind: "wire", id: "H->B" }} />);
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
        <Inspector world={world} subject={{ kind: "wire", id: "H->B" }} />,
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
    render(<Inspector world={hormuzish()} subject={null} />);
    expect(screen.getByText("Nothing selected")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Choose a claim or an arrow on the map");
  });
});
