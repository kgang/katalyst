/**
 * The four things a generation puts beside the map: the refusals, the receipt,
 * the Verify door's two answers, and the mark that says this run is a recording.
 *
 * Every one of them prints what it was handed. Nothing here composes a sentence
 * about a refusal, nothing adds two numbers together, and nothing draws a route
 * to a place the map did not reach.
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Inspector } from "../../components/Inspector";
import { ReceiptStrip } from "../../components/ReceiptStrip";
import { RefusalStrip } from "../../components/RefusalStrip";
import { ReplayBadge } from "../../components/ReplayBadge";
import { VerdictCard } from "../../components/VerdictCard";
import { foldAll, waitingFor } from "../growth";
import {
  BELIEFS,
  NO_PATH,
  REACHED,
  RECEIPT,
  REFUSED,
  REPLAY_RECEIPT,
  THE_GROWTH,
  THE_SENTENCE,
} from "./aStream";

/** The finished map of the chapter's worked run, with its likelihoods on it. */
function theFinishedRun() {
  return foldAll(waitingFor(THE_SENTENCE, null), [...THE_GROWTH, BELIEFS]);
}

describe("every refusal is on screen, in the validator's words", () => {
  it("test_a_rejected_proposal_is_shown_not_hidden", () => {
    // Two refusals, one of them breaking two rules: a proposal that broke two
    // and showed one is a refusal the reader has half seen.
    const second = {
      at: 9,
      claimInWords: "a claim with nothing that would settle it",
      reasons: [
        "The claim has no test that would settle it, and no day by which it is settled.",
        "The claim says it was documented and cites nothing.",
      ],
    };
    const { container } = render(
      <RefusalStrip
        refusals={[
          {
            at: REFUSED.at,
            claimInWords: REFUSED.claim_in_words,
            reasons: [REFUSED.violations[0]?.message ?? ""],
          },
          second,
        ]}
      />,
    );

    // What the model wrote, quoted — and never drawn as a tile or given a name.
    expect(screen.getByText(REFUSED.claim_in_words)).toBeInTheDocument();
    expect(container.querySelector(".tile")).toBeNull();

    // One line per rule broken, each the rule's own sentence with nothing added.
    const printed = [...container.querySelectorAll(".refusal-strip__reason")].map(
      (one) => one.textContent,
    );
    expect(printed).toEqual([REFUSED.violations[0]?.message, ...second.reasons]);

    // The rule's stable code is carried on the event and drawn nowhere.
    expect(container.textContent).not.toContain("cycle");
    expect(container.textContent).not.toContain("missing_resolution");

    // Its place in the working is printed, so the row can be found again.
    expect(screen.getByText(`proposal ${REFUSED.at}`)).toBeInTheDocument();
  });

  it("test_before_the_first_refusal_there_is_no_strip", () => {
    const { container } = render(<RefusalStrip refusals={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("the receipt", () => {
  /** The nine labels, in the order the chapter prints them. */
  const LABELS = [
    "model",
    "calls",
    "tokens in",
    "tokens out",
    "read from cache",
    "web searches",
    "cost",
    "took",
    "mode",
  ];

  it("test_the_receipt_strip_prints_every_field_and_adds_nothing_up", () => {
    // One test, both renderings: beside the map, and in the panel's own section
    // for the run that produced it.
    const beside = render(<ReceiptStrip receipt={RECEIPT} />);
    const inPanel = render(
      <Inspector
        world={theFinishedRun().world}
        selection={{ kind: "generation", id: "gen_worked_run" }}
        generation={{
          receipt: RECEIPT,
          working: { state: "reading" },
          unknown: new Map(),
          openAt: null,
        }}
      />,
    );

    for (const drawn of [beside.container, inPanel.container]) {
      const labels = [...drawn.querySelectorAll(".receipt-strip__label")].map(
        (one) => one.textContent,
      );
      // Nine fields, each labelled, none omitted and none derived.
      expect(labels).toEqual(LABELS);

      const figures = [...drawn.querySelectorAll(".receipt-strip__reading")]
        .map((one) => (one.textContent ?? "").replaceAll(" ", ""))
        .join(" ");

      // Every reading is the field it came from.
      expect(figures).toContain(String(RECEIPT.calls));
      expect(figures).toContain(String(RECEIPT.input_tokens));
      expect(figures).toContain(String(RECEIPT.output_tokens));
      expect(figures).toContain(String(RECEIPT.cache_read_tokens));
      expect(figures).toContain(String(RECEIPT.searches));
      expect(figures).toContain(RECEIPT.model);

      // And nothing is a sum of two of them. The two token counts are never
      // totalled, and nothing works a cost out of a token count and a price.
      expect(figures).not.toContain(String(RECEIPT.input_tokens + RECEIPT.output_tokens));
      expect(figures).not.toContain(
        String(RECEIPT.input_tokens + RECEIPT.output_tokens + RECEIPT.cache_read_tokens),
      );
    }
  });

  it("test_a_replayed_run_prints_its_zero_rather_than_hiding_it", () => {
    const { container } = render(<ReceiptStrip receipt={REPLAY_RECEIPT} />);
    const mode = container.querySelector('[data-field="mode"] .receipt-strip__reading');
    expect(mode?.textContent).toContain("replay");
    expect(mode?.textContent).toContain(String(REPLAY_RECEIPT.recording_date));

    const cost = container.querySelector('[data-field="dollars"] .receipt-strip__reading');
    // A computed zero — the recording was played, nothing was called, nothing was
    // spent — printed rather than hidden.
    expect(cost?.textContent).toMatch(/^\$0\.0+$/);
  });
});

describe("the Verify door's two answers", () => {
  it("test_no_path_renders_its_own_card", () => {
    const world = theFinishedRun().world;
    const { container } = render(
      <VerdictCard
        verdict={NO_PATH}
        target="a Polymarket contract on European natural gas"
        world={world}
      />,
    );

    // The engine's own sentence, printed as it came.
    expect(screen.getByText(NO_PATH.why)).toBeInTheDocument();
    // The nearest claim the map did reach, named by its words.
    const nearest = world.claims.find((one) => one.id === NO_PATH.nearest);
    expect(screen.getByRole("button", { name: nearest?.claim })).toBeInTheDocument();

    // Nothing is drawn between that claim and the destination. No wire, no tile,
    // no dashed anything — the card draws no route at all.
    expect(container.querySelectorAll(".verdict-card__step")).toHaveLength(0);
    expect(container.querySelector(".verdict-card__route")).toBeNull();
    expect(container.querySelector("svg")).toBeNull();
    expect(container.textContent).not.toContain("probably");
  });

  it("test_a_graded_path_prints_the_product_and_multiplies_nothing", () => {
    const world = theFinishedRun().world;
    const { container } = render(
      <VerdictCard verdict={REACHED} target="the Polymarket contract" world={world} />,
    );

    // The steps of the route the engine named, in the engine's order.
    const steps = [...container.querySelectorAll(".verdict-card__step-id")].map(
      (one) => one.textContent,
    );
    expect(steps).toEqual([...REACHED.path]);

    // The number is the one on the verdict, at two significant figures, and the
    // honest wart is beside it in the one place it is written.
    const reading = container.querySelector('[data-reading="number"]');
    expect(reading?.textContent).toBe(".083");
    expect(container.textContent).toContain(
      "it is not the chance of the whole chain happening together",
    );
  });

  it("test_a_reached_verdict_with_no_number_says_so", () => {
    const world = theFinishedRun().world;
    render(
      <VerdictCard
        verdict={{ ...REACHED, product: null }}
        target="the Polymarket contract"
        world={world}
      />,
    );
    expect(screen.getByText("no engine yet")).toBeInTheDocument();
  });
});

describe("the replay badge", () => {
  it("test_the_replay_badge_names_the_recording_date", () => {
    // Before the receipt it is on screen and says it has no day yet.
    const early = render(<ReplayBadge recordingDate={null} receiptMode={null} />);
    expect(within(early.container).getByText("replay")).toBeInTheDocument();
    expect(early.container.querySelector(".replay-badge__day")).toBeNull();

    // When the receipt lands it names the day the recording was made.
    const later = render(
      <ReplayBadge
        recordingDate={REPLAY_RECEIPT.recording_date}
        receiptMode={REPLAY_RECEIPT.mode}
      />,
    );
    expect(later.container.querySelector(".replay-badge__day")?.textContent).toBe(
      REPLAY_RECEIPT.recording_date,
    );
  });

  it("test_when_the_two_sources_disagree_the_receipt_wins_and_the_badge_says_so", () => {
    const { container } = render(<ReplayBadge recordingDate={null} receiptMode="live" />);
    expect(container.firstElementChild).toHaveAttribute("data-disagreed", "yes");
    expect(container.textContent).toContain("the receipt says the run was live");
  });
});
