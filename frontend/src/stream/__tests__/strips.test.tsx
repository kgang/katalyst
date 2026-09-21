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
import { outlineOf } from "../../a11y/sentences";
import { toTwoFigures } from "../../components/BeliefChip";
import { Inspector } from "../../components/Inspector";
import { asMoney, ReceiptStrip } from "../../components/ReceiptStrip";
import { RefusalStrip } from "../../components/RefusalStrip";
import { ReplayBadge } from "../../components/ReplayBadge";
import { VerdictCard } from "../../components/VerdictCard";
import { foldAll, waitingFor } from "../growth";
import { A_REAL_RUN, THE_REAL_SENTENCE } from "./aRealRun";
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
  /** The ten labels, in the order the chapter prints them. */
  const LABELS = [
    "model",
    "calls",
    "tokens in",
    "tokens out",
    "read from cache",
    "web searches",
    "cost",
    "took",
    "how hard the model tried",
    "mode",
  ];

  it("test_the_receipt_strip_prints_every_field_and_adds_nothing_up", () => {
    const { container } = render(<ReceiptStrip receipt={RECEIPT} />);

    const labels = [...container.querySelectorAll(".receipt-strip__label")].map(
      (one) => one.textContent,
    );
    // Ten fields, each labelled, none omitted and none derived.
    expect(labels).toEqual(LABELS);

    const figures = [...container.querySelectorAll(".receipt-strip__reading")]
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
  });

  it("test_the_cost_is_drawn_in_one_place_and_the_panel_points_at_it", () => {
    // The ten readings used to be drawn twice, one above the other in a
    // 320-pixel column: on the strip, and again in the panel's section for the
    // run. Two copies of one cost read as two costs, and the second was the one
    // no number on screen could be traced to.
    const { container } = render(
      <Inspector
        world={theFinishedRun().world}
        selection={{ kind: "generation", id: "gen_worked_run" }}
        generation={{
          seed: "4803646386380448080",
          promptFingerprint: RECEIPT.prompt_hash,
          working: { state: "reading" },
          unknown: new Map(),
          openAt: null,
        }}
      />,
    );

    expect(container.querySelectorAll(".receipt-strip__line")).toHaveLength(0);
    // And it says where the cost is instead of leaving a reader to find it.
    expect(container.textContent).toContain("on the strip beside the map");
  });

  it("test_the_panel_prints_the_prompt_fingerprint_whole", () => {
    // A fingerprint cut to its first eight characters is a fingerprint nobody
    // can compare with anything — and cutting one is the browser deriving a
    // reading, which is the one thing the receipt's own rule forbids.
    const { container } = render(
      <Inspector
        world={theFinishedRun().world}
        selection={{ kind: "generation", id: "gen_worked_run" }}
        generation={{
          seed: "4803646386380448080",
          promptFingerprint: RECEIPT.prompt_hash,
          working: { state: "reading" },
          unknown: new Map(),
          openAt: null,
        }}
      />,
    );

    const printed = container.textContent ?? "";
    expect(printed).toContain(RECEIPT.prompt_hash);
    expect(printed).toContain("prompt fingerprint");
    // Said in words a reader can act on, rather than left as eight characters
    // of hex with nothing beside them.
    expect(printed).toContain("which wording of our instructions produced this run");
  });

  it("test_the_panel_is_drawn_before_anything_has_arrived", () => {
    // From the moment there is a generation, with whatever has arrived in it. A
    // section that appeared only once everything had landed would be a panel
    // that is empty exactly while a reader is most likely to open it.
    const { container } = render(
      <Inspector
        world={theFinishedRun().world}
        selection={{ kind: "generation", id: "gen_worked_run" }}
        generation={{
          seed: null,
          promptFingerprint: null,
          working: { state: "reading" },
          unknown: new Map(),
          openAt: null,
        }}
      />,
    );

    expect(container.textContent).toContain("the run that built this map");
    expect(container.textContent).toContain("What it was run against");
    // Two slots with nothing in them yet, each an em dash rather than a zero,
    // a blank or a placeholder that reads as a value.
    const waiting = [...container.querySelectorAll(".inspector__mono")].map(
      (one) => one.textContent,
    );
    expect(waiting).toEqual(["—", "—"]);
  });

  it("test_a_replayed_run_prints_its_zero_rather_than_hiding_it", () => {
    const { container } = render(<ReceiptStrip receipt={REPLAY_RECEIPT} />);
    const mode = container.querySelector('[data-field="mode"] .receipt-strip__reading');
    expect(mode?.textContent).toContain("replay");
    expect(mode?.textContent).toContain(String(REPLAY_RECEIPT.recording_date));

    const cost = container.querySelector('[data-field="dollars"] .receipt-strip__reading');
    // A computed zero — the recording was played, nothing was called, nothing was
    // spent — printed rather than hidden, and printed as an exact zero rather
    // than as a bound: `<$0.01` here would say a free run cost something.
    expect(cost?.textContent).toBe("$0.00");
  });

  it("test_money_prints_in_the_two_places_money_has", () => {
    // It printed up to four — `$0.6132` — which is the same fake precision the
    // two-significant-figures rule exists to stop, in the place a reader is
    // most likely to compare two runs.
    const spent = render(<ReceiptStrip receipt={RECEIPT} />);
    const said =
      spent.container.querySelector('[data-field="dollars"] .receipt-strip__reading')
        ?.textContent ?? "";
    expect(said).toMatch(/^\$\d+\.\d\d$/);
    // Rounded for the page, never for the arithmetic: the figure on the receipt
    // is untouched, and the string is worked out from it here.
    expect(said).toBe(asMoney(RECEIPT.dollars));
    expect(RECEIPT.dollars.toString()).not.toBe(said);
  });

  it("test_a_run_that_spent_less_than_a_penny_says_so_rather_than_saying_nothing", () => {
    // **A guard word exactly when it is true.** `$0.00` on a run that spent a
    // third of a penny would be the strip saying a run was free when it was
    // not; the `<` is the whole of the difference between a figure and a bound,
    // and it is used only where there is a bound to state.
    expect(asMoney(0)).toBe("$0.00");
    expect(asMoney(0.0001)).toBe("<$0.01");
    expect(asMoney(0.009)).toBe("<$0.01");
    expect(asMoney(0.01)).toBe("$0.01");
    expect(asMoney(1.32289925)).toBe("$1.32");
  });

  it("test_the_strip_says_how_hard_the_model_tried", () => {
    // **Two maps of the same sentence can differ because of this and for no
    // other reason** — a recording is made at the service's own effort and a
    // live run asks for `medium` (Kent, G13) — so a reader comparing one with
    // the other has to be able to see which they are looking at. It is a plain
    // word, the one the service takes, rather than a number this browser would
    // have had to translate it into.
    const live = render(<ReceiptStrip receipt={RECEIPT} />);
    expect(
      live.container.querySelector('[data-field="effort"] .receipt-strip__reading')?.textContent,
    ).toBe(RECEIPT.effort);
    expect(
      live.container.querySelector('[data-field="effort"] .receipt-strip__label')?.textContent,
    ).toBe("how hard the model tried");

    const played = render(<ReceiptStrip receipt={REPLAY_RECEIPT} />);
    expect(
      played.container.querySelector('[data-field="effort"] .receipt-strip__reading')?.textContent,
    ).toBe(REPLAY_RECEIPT.effort);
    // And the two really do differ, or this test compares a word with itself.
    expect(REPLAY_RECEIPT.effort).not.toBe(RECEIPT.effort);
  });

  it("test_the_mode_row_says_the_mode_and_the_day_and_nothing_else", () => {
    // It used to carry `prompt 93f85980` as well: eight unexplained characters
    // of hex, cut here from the whole the engine sent, on a strip whose whole
    // promise is that every reading is a field and none is derived.
    const live = render(<ReceiptStrip receipt={RECEIPT} />);
    const liveMode = live.container.querySelector(
      '[data-field="mode"] .receipt-strip__reading',
    )?.textContent;
    expect(liveMode).toBe("live");

    const played = render(<ReceiptStrip receipt={REPLAY_RECEIPT} />);
    const playedMode =
      played.container.querySelector('[data-field="mode"] .receipt-strip__reading')?.textContent ??
      "";
    expect(playedMode).toBe(`replay · recorded ${REPLAY_RECEIPT.recording_date}`);
    expect(playedMode).not.toContain(RECEIPT.prompt_hash.slice(0, 8));
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

    // The route the engine named, in the engine's order — each claim in its own
    // words, numbered by where it sits. **No identifier is printed**: on a
    // generated map an identifier is twenty-six characters nobody reads.
    const steps = [...container.querySelectorAll(".verdict-card__step-id")].map(
      (one) => one.textContent,
    );
    expect(steps).toEqual(["start", "1", "2"]);
    const named = [...container.querySelectorAll(".verdict-card__step-claim")].map(
      (one) => one.textContent,
    );
    expect(named).toEqual(REACHED.path.map((id) => world.claims.find((c) => c.id === id)?.claim));

    // **How long the route is is said once, and the engine says it.** The card
    // used to work it out again as one fewer than the claims on the path and
    // print that under the engine's own sentence — two derivations of one fact,
    // agreeing until the day the engine counts a step differently.
    expect(container.textContent).toContain(REACHED.why);
    expect(container.textContent).not.toMatch(/steps? from the hypothesis/);

    // The number is the one on the verdict, at two significant figures, and the
    // honest wart is beside it in the one place it is written. The figure it is
    // compared with is worked out by the same function the screen uses, never
    // typed in: a test with a number in it is a test that checks the number
    // somebody typed.
    const reading = container.querySelector('[data-reading="number"]');
    expect(reading?.textContent).toBe(toTwoFigures(REACHED.product as number));
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

/**
 * Not one identifier reaches the screen, on a real generated map.
 *
 * On the stored example the identifiers are `H`, `C` and `M1`, which read like
 * names — and that accident let them onto a dozen surfaces. On a generated map
 * the same code prints `01M2QYMMJYA27CAZ91N8VPA6NK`, which is not a name but a
 * piece of the engine's bookkeeping. So every surface is drawn from a real
 * ten-claim run and the whole rendering is searched for one.
 */
describe("a generated map never prints an identifier", () => {
  /** Every identifier the real run minted, claims and arrows alike. */
  function everyIdentifier(): string[] {
    const found = new Set<string>();
    for (const event of A_REAL_RUN) {
      if (event.event === "proposal_accepted") {
        if (event.proposition !== null) {
          found.add(event.proposition.id);
        }
        for (const link of event.links) {
          found.add(link.id);
        }
      }
      if (event.event === "generation_started") {
        found.add(event.generation_id);
      }
    }
    return [...found];
  }

  it("test_no_identifier_reaches_the_screen", () => {
    const grown = foldAll(waitingFor(THE_REAL_SENTENCE, null), A_REAL_RUN);
    const claims = grown.world.claims;
    // The run really is the one this test is about: ten claims, nine arrows,
    // identifiers nobody could read, and not one refusal.
    expect(claims).toHaveLength(10);
    expect(grown.world.links).toHaveLength(9);
    expect(claims.every((one) => one.id.length === 26)).toBe(true);
    expect(grown.refusals).toEqual([]);

    const drawn: string[] = [];
    const take = (markup: { container: HTMLElement }) =>
      drawn.push(markup.container.textContent ?? "");

    take(render(<RefusalStrip refusals={grown.refusals} finished={true} />));
    take(render(<ReceiptStrip receipt={grown.receipt as never} />));
    take(
      render(
        <VerdictCard
          verdict={{
            event: "verdict",
            kind: "reached",
            path: [claims[0]?.id ?? "", claims[3]?.id ?? "", claims[6]?.id ?? ""],
            product: 0.0412,
            nearest: null,
            why: "The story reaches it in 2 steps, along the best-backed route on this map.",
          }}
          target="a contract on European gas"
          world={grown.world}
        />,
      ),
    );
    take(
      render(
        <VerdictCard
          verdict={{
            event: "verdict",
            kind: "no_path",
            path: [],
            product: null,
            nearest: claims[6]?.id ?? "",
            why: "Nothing on this map reaches it.",
          }}
          target="a contract on European gas"
          world={grown.world}
        />,
      ),
    );
    for (const claim of claims) {
      take(render(<Inspector world={grown.world} selection={{ kind: "claim", id: claim.id }} />));
    }
    for (const wire of grown.world.links) {
      take(render(<Inspector world={grown.world} selection={{ kind: "wire", id: wire.id }} />));
    }
    // And with one of those arrows read as a market acting back on the world it
    // measures, because the panel lists a feedback arrow in a place of its own
    // and that place is one more place an identifier could reach the screen.
    const withFeedback = {
      ...grown.world,
      links: grown.world.links.map((one, place) =>
        place === 0 ? { ...one, reflexive: true, lag: 14 } : one,
      ),
    };
    for (const claim of claims) {
      take(render(<Inspector world={withFeedback} selection={{ kind: "claim", id: claim.id }} />));
    }
    take(
      render(
        <Inspector
          world={grown.world}
          selection={{ kind: "generation", id: grown.generationId ?? "" }}
          generation={{
            seed: grown.seed,
            promptFingerprint: grown.receipt?.prompt_hash ?? null,
            working: { state: "reading" },
            unknown: new Map(),
            openAt: null,
          }}
        />,
      ),
    );

    // The reserved rectangles the map held open while it grew, and every
    // sentence the outline reads out.
    const everyRectangle: { words: string }[] = [];
    for (const event of A_REAL_RUN) {
      everyRectangle.push(...foldAll(waitingFor(THE_REAL_SENTENCE, null), [event]).skeletons);
    }
    drawn.push(everyRectangle.map((one) => one.words).join(" "));
    drawn.push(
      outlineOf(grown.world)
        .map((one) => one.sentence)
        .join(" "),
    );

    const whole = drawn.join("\n");
    for (const identifier of everyIdentifier()) {
      expect(whole, `an identifier reached the screen: ${identifier}`).not.toContain(identifier);
    }
    // And nothing that merely looks like one, either.
    expect(whole).not.toMatch(/\b01[0-9A-HJKMNP-TV-Z]{24}\b/);
  });
});
