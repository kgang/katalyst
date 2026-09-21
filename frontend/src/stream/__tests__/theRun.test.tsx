/**
 * One press, one generation — and a stream that stops without saying so.
 *
 * Two properties that no component test of the map itself can see, because both
 * are about the **request**: how many of them a press makes, and what the screen
 * does when the one it made ends in the middle.
 *
 * Both are about money. A generation asked for twice is paid for twice, and a
 * map left growing after its connection went is a reader watching a screen that
 * will never change again while the transcript that says how far it really got
 * sits unread on the server.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../../App";
import { THE_STREAM_ENDED_EARLY } from "../../components/DoneLine";
import type { WorldView } from "../../world";
import { foldAll, hasStopped, theStreamEnded, waitingFor } from "../growth";
import { askForAMap } from "../theRun";
import { STARTED, THE_GROWTH, THE_SENTENCE } from "./aStream";

vi.mock("../../api/client", () => ({
  readHealth: vi.fn(),
  readReadiness: vi.fn(),
  readAbout: vi.fn(),
  readExampleList: vi.fn(),
}));

// The map draws on a canvas the simulated page cannot measure, and what it draws
// has tests of its own. Here it stands in for itself, counting what it was given.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({ world, reserved }: { world: WorldView; reserved?: readonly unknown[] }) => (
    <div data-testid="the-map">
      {`${world.claims.length} claims, ${(reserved ?? []).length} rectangles`}
    </div>
  ),
}));

import { readAbout, readExampleList, readHealth, readReadiness } from "../../api/client";

beforeEach(() => {
  vi.mocked(readHealth).mockResolvedValue({ status: "ok" });
  vi.mocked(readReadiness).mockResolvedValue({
    status: "ready",
    model_key_present: true,
    // A copy with a key plays nothing back and has no recordings folder to
    // have failed to read: the whole answer, as the server describes it.
    replayable: [],
    unreadable: [],
  });
  vi.mocked(readAbout).mockResolvedValue({ name: "Katalyst", version: "0.1.0" });
  vi.mocked(readExampleList).mockResolvedValue([]);
});

/** One wire block, in the shape the route writes them. */
function block(event: { event: string }): string {
  const { event: name, ...payload } = event;
  return `event: ${name}\ndata: ${JSON.stringify(payload)}\n\n`;
}

/**
 * A response whose body is those events and then simply ends.
 *
 * No `done`, no `failed`, nothing: exactly what a restarted server, an idling
 * proxy or a sleeping laptop leaves behind.
 */
function aBodyThatJustStops(events: readonly { event: string }[]): Response {
  const bytes = new TextEncoder().encode(events.map(block).join(""));
  return new Response(
    new ReadableStream<Uint8Array>({
      start(wire) {
        wire.enqueue(bytes);
        wire.close();
      },
    }),
    { status: 200, headers: { "content-type": "text/event-stream" } },
  );
}

describe("one press asks for one map", () => {
  it("test_one_press_makes_one_request_under_strict_mode", async () => {
    // **The mode this is about is the one every developer runs.** React's strict
    // mode mounts each screen, unmounts it and mounts it again, on purpose, to
    // find effects that are not safe to run twice. An effect that asked for a
    // generation would ask for two of them — two runs, two maps and two bills,
    // with the reader having pressed once — and the server log would show it on
    // every machine this product is built on.
    const asked: string[] = [];
    const fakeFetch = vi.fn(async (where: string | URL | Request) => {
      asked.push(String(where));
      return aBodyThatJustStops([STARTED]);
    });
    vi.stubGlobal("fetch", fakeFetch);

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    );

    const field = await screen.findByLabelText("An event you think will happen");
    fireEvent.change(field, { target: { value: THE_SENTENCE } });
    fireEvent.click(screen.getByRole("button", { name: "Build the map" }));

    await screen.findByTestId("the-map");
    // The screen has been mounted, torn down and mounted again by now. One
    // request, however many times that happened.
    await waitFor(() => {
      expect(asked.filter((one) => one.endsWith("/api/generate"))).toHaveLength(1);
    });

    vi.unstubAllGlobals();
  });
});

describe("a stream that ends without saying why", () => {
  it("test_a_stream_that_just_stops_takes_the_rectangles_down", () => {
    // The reducer's half of it, on the chapter's own worked run: rectangles
    // standing, and then the body ends.
    const grown = foldAll(waitingFor(THE_SENTENCE, null), THE_GROWTH);
    expect(grown.skeletons.length).toBeGreaterThan(0);
    expect(hasStopped(grown.phase)).toBe(false);

    const ended = theStreamEnded(grown);
    expect(ended.phase).toBe("ended_early");
    expect(hasStopped(ended.phase)).toBe(true);
    // No rectangle stands where nothing is coming, and nothing else moved: the
    // map that arrived is the map that is kept.
    expect(ended.skeletons).toEqual([]);
    expect(ended.world.claims).toEqual(grown.world.claims);
    expect(ended.world.links).toEqual(grown.world.links);
    expect(ended.refusals).toEqual(grown.refusals);
    // And it is not called a failure, because nothing here can name what failed.
    expect(ended.failure).toBeNull();
  });

  it("test_a_body_that_ends_after_done_is_a_body_ending_normally", () => {
    // A stream that said why it stopped and then closed is every ordinary run.
    // Reading the close as an early end would put *the stream ended early* under
    // the foot of every finished map in the product.
    const finished = foldAll(waitingFor(THE_SENTENCE, null), [
      ...THE_GROWTH,
      { event: "done", reason: "reached_terminal", claims: 7, links: 8, rejected: 1 },
    ]);
    expect(theStreamEnded(finished)).toBe(finished);
  });

  it("test_the_screen_says_the_stream_ended_and_offers_to_run_it_again", async () => {
    const asked: string[] = [];
    const fakeFetch = vi.fn(async (where: string | URL | Request) => {
      asked.push(String(where));
      return aBodyThatJustStops([STARTED]);
    });
    vi.stubGlobal("fetch", fakeFetch);

    render(<App />);

    const field = await screen.findByLabelText("An event you think will happen");
    fireEvent.change(field, { target: { value: THE_SENTENCE } });
    fireEvent.click(screen.getByRole("button", { name: "Build the map" }));

    // One plain sentence, in the one place under the map that says why a run
    // ended — never a second strip of prose saying the same thing.
    const said = await waitFor(() => {
      const line = document.querySelector('.done-line[data-kind="ended_early"]');
      expect(line).not.toBeNull();
      return line as HTMLElement;
    });
    expect(said.textContent).toContain(THE_STREAM_ENDED_EARLY);
    expect(document.querySelectorAll(".done-line")).toHaveLength(1);
    // And no rectangle is left standing.
    expect(screen.getByTestId("the-map").textContent).toContain("0 rectangles");

    // The offer, with its price on it. This copy has a key, so running it again
    // spends money, and the control says so before it is pressed.
    const again = screen.getByRole("button", { name: /Run it again/ });
    expect(again.textContent).toContain("spends again");

    fireEvent.click(again);
    await waitFor(() => {
      expect(asked.filter((one) => one.endsWith("/api/generate"))).toHaveLength(2);
    });

    vi.unstubAllGlobals();
  });

  it("test_a_cut_run_still_offers_its_working", async () => {
    // **The working is the only record of how far a cut run got**, and the
    // screen fetches it for exactly that reason. It used to be reachable only
    // from a refusal row or from a link inside the receipt strip — and a cut
    // run has neither: it refused nothing and it never got a receipt. So the
    // reader was handed a map that stops in the middle, with the one document
    // that says why sitting fetched and unreadable.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (where: string | URL | Request) =>
        String(where).includes("/transcript")
          ? new Response("{}", { status: 404 })
          : aBodyThatJustStops([STARTED]),
      ),
    );

    render(<App />);
    const field = await screen.findByLabelText("An event you think will happen");
    fireEvent.change(field, { target: { value: THE_SENTENCE } });
    fireEvent.click(screen.getByRole("button", { name: "Build the map" }));
    await waitFor(() => {
      expect(document.querySelector('.done-line[data-kind="ended_early"]')).not.toBeNull();
    });

    // One control, in the panel, in the same words the receipt's link used to
    // carry — and pressing it opens the run rather than a claim or an arrow.
    const read = screen.getByRole("button", { name: /Read the working of this run/ });
    fireEvent.click(read);
    expect(await screen.findByText("the run that built this map")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("test_the_working_can_be_opened_from_the_moment_there_is_a_generation", async () => {
    // Not only at the end: both chapters say the panel's view of the run is
    // drawn from the moment there is one, and a reader watching a nine-minute
    // run is exactly the reader who wants to see what it has asked so far.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => aBodyThatJustStops([STARTED])),
    );
    render(<App />);
    const field = await screen.findByLabelText("An event you think will happen");
    fireEvent.change(field, { target: { value: THE_SENTENCE } });
    fireEvent.click(screen.getByRole("button", { name: "Build the map" }));

    // The run has a name and no receipt, no refusal and no claim yet.
    await screen.findByRole("button", { name: /Read the working of this run/ });
    expect(document.querySelector(".receipt-strip")).toBeNull();
    expect(document.querySelector(".refusal-strip__open")).toBeNull();

    vi.unstubAllGlobals();
  });

  it("test_letting_go_of_a_run_folds_nothing_more", async () => {
    // Walking away stops the reading, which is what stops the spending — and a
    // run that was let go must not then draw itself as a run that broke.
    const run = askForAMap(
      { hypothesis: THE_SENTENCE, target: null, belief: null },
      { fetch: async () => aBodyThatJustStops([STARTED]) },
    );
    run.letGo();
    await Promise.resolve();
    await Promise.resolve();
    expect(run.now().growth.failure).toBeNull();
  });
});
