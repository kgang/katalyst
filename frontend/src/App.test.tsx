/**
 * What the two screens must do.
 *
 * The server is replaced by stand-in functions, so these tests never make a
 * real request and never need a server running. The map itself is replaced too:
 * what is being checked here is that the launchpad offers the right things, that
 * opening one swaps the screen for a map and says where the map's numbers came
 * from, and that a failure is printed in the page rather than in a pop-up.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { aClaim, aWire, aWorld } from "./test/aMap";
import type { WorldSource, WorldView } from "./world";

vi.mock("./api/client", () => ({
  readHealth: vi.fn(),
  readReadiness: vi.fn(),
  readAbout: vi.fn(),
  readExampleList: vi.fn(),
}));

// The map draws on a canvas the simulated page cannot measure, and what it
// draws has tests of its own. Here it stands in for itself.
vi.mock("./graph/Canvas", () => ({
  MapCanvas: ({ world }: { world: WorldView }) => (
    <div data-testid="the-map">{`${world.claims.length} claims, ${world.links.length} arrows`}</div>
  ),
}));

import { App } from "./App";
import { readAbout, readHealth, readReadiness } from "./api/client";

/** Set the three stand-ins to answer the way a healthy server with no key would. */
function serverAnswersNormally() {
  vi.mocked(readHealth).mockResolvedValue({ status: "ok" });
  vi.mocked(readReadiness).mockResolvedValue({ status: "not_ready", model_key_present: false });
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
        user: { absence: { words: "\u2014", reason: "You have not said." } },
        market: { absence: { words: "no market", reason: "No venue quotes this claim." } },
      },
    }),
    aClaim({
      id: "B",
      claim: "Brent crude settles below $68 for five sessions.",
      resolvesBy: "2026-11-15",
      resolutionSource: "ICE Brent front-month settlement prices.",
      beliefs: {
        model: { reading: { p: 0.46, lo: 0.3, hi: 0.63 } },
        user: { absence: { words: "\u2014", reason: "You have not said." } },
        market: { absence: { words: "no market", reason: "No venue quotes this claim." } },
      },
    }),
  ],
  links: [aWire({ source: "H", target: "B" })],
  origin: "Every claim on this map was read from /api/fixtures/hormuz.",
});

/** A source that hands back the world above. */
function sourceThatAnswers(): WorldSource {
  return {
    readBundle: vi.fn(),
    readWorld: vi.fn().mockResolvedValue(WORLD),
  };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("the launchpad", () => {
  it("offers the stored example the server has, and says the other three are not live", async () => {
    serverAnswersNormally();
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);

    // The one example that opens something comes from the server, not from the
    // page: its words are the server's.
    expect(await screen.findByText("Strait of Hormuz")).toBeInTheDocument();
    expect(
      screen.getByText("If the Strait of Hormuz reopens, what happens to crude?"),
    ).toBeInTheDocument();

    // The other three are the examples from the brief, each one saying plainly
    // that it is not built yet — never silently doing nothing.
    expect(
      screen.getByText("Photonic chips get adopted faster than expected."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("not yet live")).toHaveLength(3);
    expect(
      await screen.findAllByText(
        "Turning your own words into a map needs the model, and this server has no key for one.",
      ),
    ).toHaveLength(3);

    // Both doors are named and explained.
    expect(screen.getByText("Explore")).toBeInTheDocument();
    expect(screen.getByText("Verify")).toBeInTheDocument();

    // Nothing spins and nothing pops up.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
  });
});

describe("opening a map", () => {
  it("swaps the screen for the map and says where its numbers came from", async () => {
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

  it("prints a failure on the page, in a sentence, and opens nothing", async () => {
    serverAnswersNormally();
    const source: WorldSource = {
      readBundle: vi.fn(),
      readWorld: vi.fn().mockRejectedValue(new Error("Nothing answered at /api/fixtures/hormuz.")),
    };
    render(<App source={source} listExamples={async () => EXAMPLES} />);

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
  it("reports what the server said about itself", async () => {
    serverAnswersNormally();
    render(<App source={sourceThatAnswers()} listExamples={async () => EXAMPLES} />);

    expect(await screen.findByText("reachable")).toBeInTheDocument();
    expect(screen.getByText("0.1.0")).toHaveClass("status-value");
    expect(
      screen.getByText("no key configured — generating a map is not built yet"),
    ).toBeInTheDocument();
  });
});
