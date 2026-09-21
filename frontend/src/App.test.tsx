/**
 * What the two screens must do.
 *
 * The server is replaced by stand-in functions, so these tests never make a
 * real request and never need a server running. The map itself is replaced too:
 * what is being checked here is that the launchpad offers the right things, that
 * opening one swaps the screen for a map and says where the map's numbers came
 * from, and that a failure is printed in the page rather than in a pop-up.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { aClaim, aWire, aWorld } from "./test/aMap";
import type { FixtureBundle, WorldSource, WorldView } from "./world";

vi.mock("./api/client", () => ({
  readHealth: vi.fn(),
  readReadiness: vi.fn(),
  readAbout: vi.fn(),
  readExampleList: vi.fn(),
}));

// The map draws on a canvas the simulated page cannot measure, and what it
// draws has tests of its own. Here it stands in for itself — with one button per
// arrow, because selecting an arrow is a thing the screen around the map has to
// answer for: it is what asks the engine for that arrow's own number.
vi.mock("./graph/Canvas", () => ({
  MapCanvas: ({
    world,
    onSelect,
    keys,
  }: {
    world: WorldView;
    onSelect: (selection: { kind: "wire" | "claim"; id: string }) => void;
    keys: { flipWorlds: () => void; intervene: () => void };
  }) => (
    <div data-testid="the-map">
      {`${world.claims.length} claims, ${world.links.length} arrows`}
      {world.links.map((link) => (
        <button key={link.id} type="button" onClick={() => onSelect({ kind: "wire", id: link.id })}>
          {`select ${link.id}`}
        </button>
      ))}
      {world.claims.map((claim) => (
        <button
          key={claim.id}
          type="button"
          onClick={() => onSelect({ kind: "claim", id: claim.id })}
        >
          {`select claim ${claim.id}`}
        </button>
      ))}
      {/* The two keys this screen's own behaviour hangs on: Space flips which of
          the two worlds is in front, and E opens the six things you can do to a
          claim. Both are the map's keys and both are answered outside it. */}
      <button type="button" onClick={keys.flipWorlds}>
        flip worlds
      </button>
      <button type="button" onClick={keys.intervene}>
        change this claim
      </button>
    </div>
  ),
}));

import { App } from "./App";
import { readAbout, readHealth, readReadiness } from "./api/client";
import { STARTING_SENTENCES } from "./components/Launchpad";
import { absence } from "./world/absence";

/** Set the three stand-ins to answer the way a healthy server with no key would. */
function serverAnswersNormally() {
  vi.mocked(readHealth).mockResolvedValue({ status: "ok" });
  vi.mocked(readReadiness).mockResolvedValue({
    status: "not_ready",
    model_key_present: false,
    // What a keyless server can replay. Empty here: this stand-in is a server
    // with nothing recorded, which is what "not ready" means on this screen.
    replayable: [],
    // And nothing in its recordings folder that it could not read.
    unreadable: [],
  });
  vi.mocked(readAbout).mockResolvedValue({ name: "Katalyst", version: "0.1.0" });
}

/** The one stored example, as the list route serves it. */
const EXAMPLES = [
  {
    id: "hormuz",
    title: "Strait of Hormuz",
    one_line: "If the Strait of Hormuz reopens, what happens to crude?",
  },
];

/** A world with two claims and one arrow, enough to prove the screen swapped. */
const WORLD: WorldView = aWorld({
  baseId: "hormuz",
  title: "Strait of Hormuz",
  claims: [
    aClaim({
      id: "H",
      claim: "The Strait of Hormuz reopens to unrestricted commercial transit.",
      kind: "hypothesis",
      beliefs: {
        model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
        user: { absence: absence("not_said", "You have not said.") },
        market: {
          absence: absence("no_market", "No venue quotes this claim."),
        },
      },
    }),
    aClaim({
      id: "B",
      claim: "Brent crude settles below $68 for five sessions.",
      resolvesBy: "2026-11-15",
      resolutionSource: "ICE Brent front-month settlement prices.",
      beliefs: {
        model: { reading: { p: 0.46, lo: 0.3, hi: 0.63 } },
        user: { absence: absence("not_said", "You have not said.") },
        market: {
          absence: absence("no_market", "No venue quotes this claim."),
        },
      },
    }),
  ],
  links: [aWire({ source: "H", target: "B" })],
  origin: "Every claim on this map was read from /api/fixtures/hormuz.",
});

/**
 * The stored example in full, as the route serves it.
 *
 * The screen asks for the world *and* the bundle: the world is what gets drawn,
 * and the bundle carries the branches somebody already made, which the panel
 * beside the map lists. This one has none.
 */
const BUNDLE = {
  id: "hormuz",
  title: "Strait of Hormuz",
  fixture_date: "2026-10-01",
  graph: { hypothesis_id: "H", propositions: [], links: [] },
  branches: [],
} as unknown as FixtureBundle;

/** A source that hands back the world above. */
function sourceThatAnswers(): WorldSource {
  return {
    readBundle: vi.fn().mockResolvedValue(BUNDLE),
    readWorld: vi.fn().mockResolvedValue(WORLD),
    readDiff: vi.fn().mockResolvedValue({
      claims: new Map(),
      rows: [],
      summary: { reading: "Nothing moved." },
      warnings: [],
    }),
    readConditional: vi.fn().mockResolvedValue({ reading: { p: 0.58, lo: 0.42, hi: 0.73 } }),
  };
}

/** A source that cannot answer any of the three questions the engine answers. */
function sourceThatCannot(reason: string): WorldSource {
  const refuse = vi.fn().mockRejectedValue(new Error(reason));
  return {
    readBundle: refuse,
    readWorld: refuse,
    readDiff: refuse,
    readConditional: refuse,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("the launchpad", () => {
  it("test_the_launchpad_offers_the_one_example_that_opens_and_says_what_it_cannot", async () => {
    serverAnswersNormally();
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);

    // The one example that opens something comes from the server, not from the
    // page: its words are the server's.
    expect(await screen.findByText("Strait of Hormuz")).toBeInTheDocument();
    expect(
      screen.getByText("If the Strait of Hormuz reopens, what happens to crude?"),
    ).toBeInTheDocument();

    // **This server has no key and nothing recorded, so there is nothing the
    // four sentences could honestly show and none of them is drawn as a card.**
    // They used to be four rows reading *not yet live* — four things a reader
    // counted and could not take up, under a heading offering to build them a
    // map. One sentence says it instead, and points at the thing that does work
    // with neither a key nor a recording.
    expect(
      await screen.findByText(/No model key configured, and nothing recorded/),
    ).toBeInTheDocument();
    expect(screen.getByText(/No model key configured, and nothing recorded/).textContent).toContain(
      "The map above is already drawn and needs neither.",
    );
    expect(screen.queryByText("Photonic chips get adopted faster than expected.")).toBeNull();
    expect(document.querySelectorAll(".example__badge")).toHaveLength(0);

    // Both doors are named and explained.
    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByText("Verify")).toBeInTheDocument();

    // Nothing spins and nothing pops up.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
  });

  it("test_a_readiness_ask_that_failed_is_not_drawn_as_one_still_in_flight", async () => {
    // **The screen is handed two different absent answers, not one.** Asking
    // and failed are both "no readiness answer", and folded together the first
    // screen said *asking the server* for ever over an ask that had ended —
    // while the strip below it printed the failure's own sentence. This is the
    // wiring that keeps them apart, from the request to the card.
    serverAnswersNormally();
    vi.mocked(readReadiness).mockRejectedValue(
      new Error("Nothing answered at /api/readyz — the server may not be running."),
    );
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);

    expect(await screen.findAllByText(/Nothing answered at \/api\/readyz/)).not.toHaveLength(0);
    // One row for each starting sentence, counted off the list itself.
    expect(document.querySelectorAll('[data-state="no-answer"]')).toHaveLength(
      STARTING_SENTENCES.length,
    );
    expect(document.body.textContent).not.toContain("Asking the server");
    expect(document.body.textContent).not.toContain("No model key configured");
    // And nothing pops up about it: a failure is printed in the page.
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("opening a map", () => {
  it("test_opening_an_example_swaps_the_screen_and_says_where_its_numbers_came_from", async () => {
    serverAnswersNormally();
    const source = sourceThatAnswers();
    render(<App source={source} listExamples={async () => EXAMPLES} />);

    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));

    expect(await screen.findByTestId("the-map")).toHaveTextContent("2 claims, 1 arrows");
    expect(source.readWorld).toHaveBeenCalledWith({ baseId: "hormuz" });

    // Every map carries the sentence that says where it came from.
    expect(
      screen.getByText("Every claim on this map was read from /api/fixtures/hormuz."),
    ).toBeInTheDocument();
  });

  it("test_the_conditional_is_fetched_once_and_cached", async () => {
    serverAnswersNormally();
    const source = sourceThatAnswers();
    render(<App source={source} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));
    await screen.findByTestId("the-map");

    // Nothing is asked for until somebody asks about an arrow: the number costs
    // a whole extra run of the map, for something most readers never open.
    expect(source.readConditional).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    await screen.findByText(".58 (.42–.73)");
    expect(source.readConditional).toHaveBeenCalledTimes(1);
    expect(source.readConditional).toHaveBeenCalledWith({
      baseId: "hormuz",
      branch: undefined,
      linkId: "H->B",
    });

    // Asking about the same arrow again, on the same map with the same branch
    // and the same seed, is the same question — so it is answered from what was
    // kept rather than asked again.
    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    await screen.findByText(".58 (.42–.73)");
    expect(source.readConditional).toHaveBeenCalledTimes(1);
  });

  it("test_a_wires_number_is_asked_again_when_the_branch_changes", async () => {
    serverAnswersNormally();
    const source = sourceThatAnswers();
    render(<App source={source} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));
    await screen.findByTestId("the-map");

    // A branch of the reader's own, and one arrow asked about.
    fireEvent.click(screen.getByRole("button", { name: "Start a branch" }));
    fireEvent.change(screen.getByLabelText(/What is this branch called/), {
      target: { value: "Your own branch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start this branch" }));
    fireEvent.click(await screen.findByRole("button", { name: "select H->B" }));
    await screen.findByText(".58 (.42–.73)");
    expect(source.readConditional).toHaveBeenCalledTimes(1);

    // Now an edit. The branch is append-only, so this is a different branch
    // with the same name — and the number worked out for the branch before the
    // edit is a number for a map that no longer exists.
    fireEvent.click(screen.getByRole("button", { name: "select claim B" }));
    fireEvent.click(screen.getByRole("button", { name: "change this claim" }));
    fireEvent.click(await screen.findByRole("button", { name: /^Suppose this is true/ }));

    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    await waitFor(() => expect(source.readConditional).toHaveBeenCalledTimes(2));
    // And the second question carries the branch as it now stands.
    const asked = vi.mocked(source.readConditional).mock.calls.at(-1)?.[0];
    expect(asked?.branch?.edits).toHaveLength(1);
  });

  it("test_the_keyboard_goes_into_the_operations_and_comes_back_out", async () => {
    // **Both directions of one rule.** The way in from the panel's head
    // unmounts the instant it is pressed, so without this a reader who tabbed
    // to *Change this claim* and pressed Enter would be standing on nothing and
    // the next Tab would start again at the top of the page. The panel takes
    // the keyboard — the reader's own act, since pressing that control can mean
    // nothing else — and **Done** puts it back on the control it came from,
    // which by then is a new element in the same place.
    serverAnswersNormally();
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));
    await screen.findByTestId("the-map");

    fireEvent.click(screen.getByRole("button", { name: "select claim B" }));
    const wayIn = await screen.findByRole("button", { name: "Change this claim" });
    wayIn.focus();
    expect(document.activeElement).toBe(wayIn);

    fireEvent.click(wayIn);
    const operations = await screen.findByRole("region", { name: "Change this claim" });
    expect(document.activeElement).toBe(operations);
    // And the way in is not on the screen at all while what it opens is open.
    expect(screen.queryByRole("button", { name: "Change this claim" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    const back = await screen.findByRole("button", { name: "Change this claim" });
    expect(document.activeElement).toBe(back);
    // A new element in the same place, which is why the screen has to put the
    // keyboard back rather than the panel restoring what it remembered.
    expect(back).not.toBe(wayIn);
  });

  it("test_an_ask_that_did_not_come_back_is_asked_again", async () => {
    serverAnswersNormally();
    const source = sourceThatAnswers();
    vi.mocked(source.readConditional).mockRejectedValueOnce(
      new Error("The server did not answer."),
    );
    render(<App source={source} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));
    await screen.findByTestId("the-map");

    // The first ask does not come back. What the panel says is what happened —
    // the attempt failed — and not that nothing has worked the number out.
    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    expect(await screen.findByText(/The server did not answer\./)).toBeInTheDocument();
    expect(screen.queryByText("no engine yet")).toBeNull();

    // Select it again and it is asked again. A failure kept in the cache would
    // tell a reader for the rest of the session that a number the engine can
    // work out cannot be worked out.
    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    await waitFor(() => expect(source.readConditional).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(".58 (.42\u2013.73)")).toBeInTheDocument();
  });

  it("test_a_wires_number_belongs_to_the_map_that_is_showing", async () => {
    serverAnswersNormally();
    const source = sourceThatAnswers();
    render(<App source={source} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));
    await screen.findByTestId("the-map");

    fireEvent.click(screen.getByRole("button", { name: "Start a branch" }));
    fireEvent.change(screen.getByLabelText(/What is this branch called/), {
      target: { value: "Your own branch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start this branch" }));
    fireEvent.click(await screen.findByRole("button", { name: "select H->B" }));
    await waitFor(() => expect(source.readConditional).toHaveBeenCalledTimes(1));
    expect(vi.mocked(source.readConditional).mock.calls[0]?.[0]?.branch).toBeDefined();

    // Flip to the map as it was written. The number on screen was worked out for
    // the other map, and a number that belongs to a map the reader is not
    // looking at is the one thing this product must never draw.
    fireEvent.click(screen.getByRole("button", { name: "flip worlds" }));
    await screen.findByText("as it was written");
    fireEvent.click(screen.getByRole("button", { name: "select H->B" }));
    await waitFor(() => expect(source.readConditional).toHaveBeenCalledTimes(2));
    // Asked for the map that is showing: no branch at all.
    expect(vi.mocked(source.readConditional).mock.calls[1]?.[0]?.branch).toBeUndefined();
  });

  it("test_a_missing_world_falls_back_and_says_so", async () => {
    serverAnswersNormally();
    const engine = sourceThatCannot(
      "Nothing answered at /api/worlds — the server may not be running.",
    );
    const stored = sourceThatAnswers();

    render(<App source={engine} fallback={stored} listExamples={async () => EXAMPLES} />);
    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));

    // A map you can still read beats a blank screen: the stored example draws.
    expect(await screen.findByTestId("the-map")).toHaveTextContent("2 claims, 1 arrows");

    // And the screen says, in the failure's own words, that these are not
    // computed numbers — so nobody takes a hand-written likelihood for one the
    // engine worked out.
    const said = await screen.findByText(/the stored example exactly as it was written/);
    expect(said).toHaveTextContent("Nothing answered at /api/worlds");
    expect(said).toHaveTextContent("illustrative");

    // Nothing pops up to tell you about it, here or anywhere.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
  });

  it("test_a_failure_is_printed_on_the_page_and_opens_nothing", async () => {
    serverAnswersNormally();
    // Neither the engine nor the stored example can answer, which is what it
    // looks like when the server itself is not there.
    const gone = sourceThatCannot("Nothing answered at /api/fixtures/hormuz.");
    render(<App source={gone} fallback={gone} listExamples={async () => EXAMPLES} />);

    fireEvent.click(await screen.findByRole("button", { name: /Strait of Hormuz/ }));

    expect(
      await screen.findByText("Nothing answered at /api/fixtures/hormuz."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();

    // And there is a way back, so a failure is not a dead end.
    expect(screen.getByRole("button", { name: /Back to the launchpad/ })).toBeInTheDocument();
  });
});

describe("the strip at the foot of the launchpad", () => {
  it("test_the_strip_reports_what_the_server_said_about_itself", async () => {
    serverAnswersNormally();
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);

    // **One labelled row, and it is the model key** — the one reading on this
    // screen that changes what a reader can do.
    expect(
      await screen.findByText("no key configured, and nothing recorded to play instead"),
    ).toBeInTheDocument();
    expect(document.querySelectorAll(".status-row")).toHaveLength(1);

    // Whether the server answered and which build answered are still here, in
    // one quiet line, still the server's own words and still traceable to the
    // addresses named under them. Nothing was dropped; it was given the weight
    // it has.
    expect(screen.getByText(/Server ok\./).textContent).toContain(
      "Build 0.1.0, reported by Katalyst.",
    );
    expect(document.querySelector(".status-value")?.textContent).toBe("absent");
  });
});
