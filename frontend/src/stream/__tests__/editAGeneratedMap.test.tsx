/**
 * A finished generation is a map like any other.
 *
 * Kent watched a map build itself and found no verb on it: *"I see that the
 * change this claim button and flow is available for the prebuilt map but
 * doesn't exist for the map that's generated live"* (2026-09-22). Nothing was
 * missing from the engine — the server holds a generated map under its own
 * identifier and folds a branch onto it exactly as onto a stored example — and
 * nothing was missing from the screen maps are edited on. What was missing was
 * the way from one to the other.
 *
 * So these tests hold the two halves of that way, and one rule over both:
 *
 * 1. a run that has stopped with a map offers **Change this claim**, on the
 *    claim the reader is pointing at, and hands both over;
 * 2. the screen it hands them to draws **the same six edits** for a generated
 *    claim as for a stored one, and folding one of them paints the two worlds
 *    and fills the change list.
 *
 * **Not one number is written down here.** Where a figure would prove something,
 * what is asserted instead is the same reading taken twice — the six controls on
 * a generated map against the six on a stored one — or a state, an ordering, or
 * the name the engine was asked with.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { theUneditedMap } from "../../components/BranchPanel";
import { MapScreen } from "../../components/MapScreen";
import { aClaim, aWire, aWorld } from "../../test/aMap";
import type { Selection, WorldSource, WorldView } from "../../world";
import { absence } from "../../world/absence";
import type { StreamEvent } from "../events";
import { GenerationScreen } from "../GenerationScreen";
import { foldAll, type Growth, waitingFor } from "../growth";
import type { TheRun, WhereItHasGot } from "../theRun";
import { BELIEFS, DONE, RECEIPT, THE_GROWTH, THE_SENTENCE, theWorld } from "./aStream";

// The map draws on a canvas the simulated page cannot measure, and what it draws
// has tests of its own. Here it stands in for itself, with one button per claim,
// because choosing a claim is what the whole of this is about.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({
    world,
    onSelect,
  }: {
    world: WorldView;
    onSelect: (selection: { kind: "claim"; id: string }) => void;
  }) => (
    <div data-testid="the-map">
      {`${world.claims.length} claims`}
      {world.claims.map((claim) => (
        <button
          key={claim.id}
          type="button"
          onClick={() => onSelect({ kind: "claim", id: claim.id })}
        >
          {`select claim ${claim.id}`}
        </button>
      ))}
    </div>
  ),
}));

// Nothing here asks a model anything. *Add a claim* is one of the six and it is
// the one that needs one, so the route it calls is replaced — a test that
// reached the network would be a test that could not run.
vi.mock("../../stream/insert", () => ({
  draftAClaim: vi.fn(),
}));

/** The whole run, from its first event to its last: a map that finished. */
const A_FINISHED_RUN: readonly StreamEvent[] = [...THE_GROWTH, BELIEFS, RECEIPT, DONE];

/** The same run stopped halfway: proposals arrived, no likelihoods, no ending. */
const A_RUN_STILL_GOING: readonly StreamEvent[] = THE_GROWTH;

/**
 * A run somebody else drove, already folded to wherever it got to.
 *
 * The real interface with the real fold behind it, and nothing that could make a
 * request. What the screen watches is what these events left.
 *
 * @param events The stream, in order, as far as it went.
 */
function aRunThatGotTo(events: readonly StreamEvent[]): TheRun {
  const growth: Growth = foldAll(waitingFor(THE_SENTENCE, null), events);
  const where: WhereItHasGot = { growth, saying: "The run has said what it is doing." };
  return {
    asked: { hypothesis: THE_SENTENCE, target: null, belief: null },
    press: "press 1",
    now: () => where,
    watch: () => () => {},
    letGo: () => {},
  };
}

/** The finished map, exactly as the reader watched it arrive. */
function theFinishedMap(): WorldView {
  return foldAll(waitingFor(THE_SENTENCE, null), A_FINISHED_RUN).world;
}

/** Every control inside the panel of six edits, by the words on it. */
function theSixEdits(): string[] {
  return [...document.querySelectorAll(".intervene__button")].map((one) =>
    (one.textContent ?? "").trim(),
  );
}

/**
 * A source that answers all three questions, and says what it was asked.
 *
 * The world it hands back for a branch is the same map with one claim's
 * likelihood replaced, which is enough for the screen to paint two worlds: what
 * is under test here is that the screen asks, and asks about the right map.
 *
 * @param base The map every answer is about.
 */
function aSourceThatAnswers(base: WorldView) {
  const afterTheEdit: WorldView = {
    ...base,
    claims: base.claims.map((claim) => ({ ...claim })),
  };
  const readWorld = vi.fn().mockResolvedValue(afterTheEdit);
  const readDiff = vi.fn().mockResolvedValue({
    claims: new Map([[base.claims[0]?.id ?? "H", { state: "shifted" as const }]]),
    rows: [
      {
        claimId: base.claims[0]?.id ?? "H",
        label: base.claims[0]?.claim ?? "an ending",
        kind: "market" as const,
        // One likelihood each side and how far it moved, in the shape the rail
        // reads now — no range, and no share of anything that agreed (R48).
        move: {
          reading: { from: 0.4, to: 0.6, largestOn: "2026-09-25", way: "up" as const, by: 0.2 },
        },
      },
    ],
    summary: { reading: "The edit moved one ending." },
    warnings: [],
  });
  const source: WorldSource = {
    readBundle: vi.fn().mockRejectedValue(new Error("a generated map has no stored example")),
    readWorld,
    readDiff,
    readConditional: vi.fn().mockResolvedValue({ reading: { p: 0.5 } }),
  };
  return { source, readWorld, readDiff };
}

describe("a run that has stopped offers the map it built", () => {
  it("test_a_finished_generation_offers_change_this_claim", async () => {
    const handedOver = vi.fn();
    render(
      <GenerationScreen
        run={aRunThatGotTo(A_FINISHED_RUN)}
        replaying={true}
        onRunAgain={() => {}}
        onLeave={() => {}}
        onChangeAClaim={handedOver}
      />,
    );

    // Nothing is offered until the reader is pointing at something: the six
    // edits are about a claim, and there is no claim until one is chosen.
    fireEvent.click(screen.getByRole("button", { name: "select claim H" }));

    const theWayIn = await screen.findByRole("button", { name: /Change this claim/ });
    fireEvent.click(theWayIn);

    // What goes over is the claim they pressed it about, and the run that built
    // the map — which is what the panel on the other side reads *Run details*
    // out of.
    expect(handedOver).toHaveBeenCalledTimes(1);
    const [selection, run] = handedOver.mock.calls[0] as [Selection, { generationId: string }];
    expect(selection).toEqual({ kind: "claim", id: "H" });
    expect(run.generationId).toBe(theWorld().base_id);
  });

  it("test_a_run_still_building_offers_no_edits_and_says_why", () => {
    const handedOver = vi.fn();
    render(
      <GenerationScreen
        run={aRunThatGotTo(A_RUN_STILL_GOING)}
        replaying={true}
        onRunAgain={() => {}}
        onLeave={() => {}}
        onChangeAClaim={handedOver}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "select claim H" }));

    // **A map that is still being built cannot be edited**, because every
    // likelihood is worked through the whole map at once when it is finished —
    // so there is no control, and nothing was handed anywhere.
    expect(screen.queryByRole("button", { name: /Change this claim/ })).toBeNull();
    expect(handedOver).not.toHaveBeenCalled();
  });
});

describe("the screen a map is edited on takes a generated map", () => {
  it("test_the_six_edits_render_for_a_claim_on_a_generated_map", async () => {
    const generated = theFinishedMap();
    const onTheGeneratedMap = aSourceThatAnswers(generated);
    const { unmount } = render(
      <MapScreen
        base={generated}
        branches={[]}
        source={onTheGeneratedMap.source}
        insteadOfTheEngine={null}
        changing={{ kind: "claim", id: "H" }}
        onLeave={() => {}}
      />,
    );

    // The panel is open from the first frame, because the press that opened
    // this screen was the press that asked for it.
    const onAGeneratedClaim = theSixEdits();
    expect(onAGeneratedClaim.length).toBeGreaterThan(0);
    unmount();

    // **The same six, on a map somebody wrote by hand.** This is the whole of
    // what "a map like any other" means, and it is asserted by taking the same
    // reading twice rather than by listing the words here — a list here would
    // be a seventh place the six are written down.
    const stored = aWorld({
      baseId: "hormuz",
      title: "Strait of Hormuz",
      claims: [
        aClaim({
          id: "H",
          claim: "The Strait of Hormuz reopens to unrestricted commercial transit.",
          kind: "hypothesis",
          beliefs: {
            model: { reading: { p: 0.35 } },
            user: { absence: absence("not_said", "You have not said.") },
            market: { absence: absence("no_market", "No venue quotes this claim.") },
          },
        }),
        aClaim({ id: "B", claim: "Brent crude settles below $68 for five sessions." }),
      ],
      links: [aWire({ source: "H", target: "B" })],
    });
    render(
      <MapScreen
        base={stored}
        branches={[]}
        source={aSourceThatAnswers(stored).source}
        insteadOfTheEngine={null}
        changing={{ kind: "claim", id: "H" }}
        onLeave={() => {}}
      />,
    );

    expect(theSixEdits()).toEqual(onAGeneratedClaim);
  });

  it("test_the_bar_says_built_on_a_map_the_reader_generated_and_written_on_a_stored_one", () => {
    // **The one word this screen must not get wrong.** The bar and the first row
    // of the branch panel both name the map with nothing done to it, and a map
    // the reader watched build itself was not *written* — nobody typed it out,
    // which is the whole of what this product is showing. The flag is
    // `generation`, which is the run that built the map and is absent on a
    // stored example, so it cannot drift from the fact.
    const generated = theFinishedMap();
    const built = render(
      <MapScreen
        base={generated}
        branches={[]}
        source={aSourceThatAnswers(generated).source}
        insteadOfTheEngine={null}
        generation={{
          generationId: "gen_a_run_the_reader_watched",
          seed: "4803646386380448080",
          promptFingerprint: null,
          working: { state: "reading" },
          unknown: new Map(),
          openAt: null,
        }}
        onLeave={() => {}}
      />,
    );
    expect(document.querySelector(".map-bar__where")?.textContent).toBe(theUneditedMap(true));
    built.unmount();

    render(
      <MapScreen
        base={generated}
        branches={[]}
        source={aSourceThatAnswers(generated).source}
        insteadOfTheEngine={null}
        onLeave={() => {}}
      />,
    );
    expect(document.querySelector(".map-bar__where")?.textContent).toBe(theUneditedMap(false));
  });

  it("test_a_supposition_on_a_generated_map_paints_two_worlds_and_lists_the_change", async () => {
    const generated = theFinishedMap();
    const asked = aSourceThatAnswers(generated);
    render(
      <MapScreen
        base={generated}
        branches={[]}
        source={asked.source}
        insteadOfTheEngine={null}
        changing={{ kind: "claim", id: "H" }}
        onLeave={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Suppose this is true/ }));

    // **Asked about the map that was generated**, by its own identifier — not
    // the run's, and not a stored example's. This is the one thing that would
    // send the whole flow to the wrong map without saying so.
    await waitFor(() => expect(asked.readWorld).toHaveBeenCalled());
    for (const call of [...asked.readWorld.mock.calls, ...asked.readDiff.mock.calls]) {
      expect((call[0] as { baseId: string }).baseId).toBe(generated.baseId);
    }

    // Two worlds, and the screen says which of them is in front. The branch is
    // the reader's own, forked by the edit itself, so its name is on the bar.
    const bar = document.querySelector(".map-bar__where");
    expect(bar?.textContent).toContain("with your edits");

    // And the change list is filled from the engine's own difference, in the
    // engine's own order. It is on the panel the branches are on, one name
    // away, which is where a reader turns for it on a stored map too.
    fireEvent.click(screen.getByRole("tab", { name: /Branches and changes/ }));
    await waitFor(() => {
      expect(document.querySelectorAll(".delta-rail__row").length).toBeGreaterThan(0);
    });
    expect(document.body.textContent).toContain("The edit moved one ending.");
  });
});
