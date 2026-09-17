/**
 * What the screen must do, checked three ways.
 *
 * The server is replaced by three stand-in functions, so these tests never make
 * a real request and never need a server running. What is being checked is the
 * screen's behaviour, not the server's.
 */

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api/client", () => ({
  readHealth: vi.fn(),
  readReadiness: vi.fn(),
  readAbout: vi.fn(),
}));

import { App } from "./App";
import { readAbout, readHealth, readReadiness } from "./api/client";

/** Set all three stand-ins to answer the way a healthy server with no key would. */
function serverAnswersNormally() {
  vi.mocked(readHealth).mockResolvedValue({ status: "ok" });
  vi.mocked(readReadiness).mockResolvedValue({ status: "not_ready", model_key_present: false });
  vi.mocked(readAbout).mockResolvedValue({ name: "Katalyst", version: "0.1.0" });
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("the status strip", () => {
  it("reports all three readings once the server has answered", async () => {
    serverAnswersNormally();
    render(<App />);

    // Before any answer arrives, each value cell holds a bar of the same height
    // where the value will land, and each row says in words what it is waiting
    // for. There is no spinner anywhere on the page.
    expect(document.querySelectorAll(".placeholder")).toHaveLength(3);
    expect(screen.getAllByText("asking the server")).toHaveLength(3);

    // The server is reachable and said so in one word.
    expect(await screen.findByText("reachable")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();

    // No key is configured, and the row says what that means rather than
    // leaving the reader to work it out.
    expect(screen.getByText("absent")).toBeInTheDocument();
    expect(
      screen.getByText("no key configured — generating a map is not built yet"),
    ).toBeInTheDocument();

    // The version row is derived from the server's own answer.
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("reported by Katalyst")).toBeInTheDocument();

    // Three rows, each one a term in the description list.
    expect(screen.getAllByRole("term")).toHaveLength(3);
  });

  it("prints a failed request in the row, in words, and opens nothing", async () => {
    serverAnswersNormally();
    vi.mocked(readHealth).mockRejectedValue(
      new Error("Could not reach the server at /api/healthz. It may not be running."),
    );
    render(<App />);

    const failure = await screen.findByText(
      "Could not reach the server at /api/healthz. It may not be running.",
    );
    expect(failure).toBeInTheDocument();

    // The failure sits inside the row it belongs to, beside the label "server".
    expect(failure.closest(".status-row")).toHaveTextContent("server");

    // Nothing pops up over the page: no dialog to dismiss, no alert to close.
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();

    // The other two readings are unaffected by the one that failed.
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
  });

  it("puts the version in the monospace face with fixed-width digits", async () => {
    serverAnswersNormally();
    render(<App />);

    // `status-value` is the single class that sets the monospace typeface and
    // `font-variant-numeric: tabular-nums` (see src/styles/app.css). Checking
    // for the class is a cheap stand-in for checking the rendered glyphs, which
    // a simulated page cannot measure.
    expect(await screen.findByText("0.1.0")).toHaveClass("status-value");
  });
});
