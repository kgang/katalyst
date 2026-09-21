/**
 * **Add a claim** — what it sends, and what it shows of what came back.
 *
 * Three facts, each of them the settlement of something that was open.
 *
 * **It sends three fields and no fourth.** A drafted edit goes at the end of the
 * branch, which is the only place this product ever puts one; the field that
 * said otherwise is gone from the route, and while it was there a reader who
 * sent something else got a 200 for an edit the world route then refused.
 *
 * **It shows what drafting cost**, in the same strip a generation's receipt is
 * printed in, because an insert is several model calls and the person who
 * pressed the button is the person who should see the bill.
 *
 * **And it shows every call it took**, in the same list a generation's working
 * is drawn in — from the answer itself, because there is nowhere else it could
 * be: an insert is one request and one answer, nothing about it is remembered on
 * the server, so there is no identifier to ask by and no route to ask at.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AddAClaim } from "../../components/AddAClaim";
import type { DraftedClaim, DraftRequest } from "../insert";
import type { TranscriptLine } from "../transcript";
import { RECEIPT } from "./aStream";

/** The claim the route drafts, in the shape it answers with. */
const DRAFTED = {
  kind: "insert",
  proposition: {
    id: "01M2QYMMJYA27CAZ91N8VPA6NM",
    claim: "A confirmed military strike on Iranian territory is reported within seven days.",
    kind: "event",
    resolution: {
      criteria: "As two major wire services report it.",
      source: "Reuters",
      by: "2026-11-01",
    },
    prior: { p: 0.2, lo: 0.1, hi: 0.35, owner: "model" },
    beliefs: { model: { p: 0.2, lo: 0.1, hi: 0.35, owner: "model" } },
    evidence: [],
  },
  links: [],
} as unknown as DraftedClaim;

/** Two calls, as the route reports them: one to draft the claim, one for an arrow. */
const WORKING: readonly TranscriptLine[] = [
  {
    at: 0,
    what: "accepted",
    about: null,
    in_words: "A confirmed military strike on Iranian territory is reported within seven days.",
    violations: [],
    calls: 1,
    searches: 2,
    seconds: 18.4,
  },
  {
    at: 1,
    what: "accepted",
    about: "01M2QYMMJYA27CAZ91N8VPA6NM",
    in_words: "A strike closes the strait to commercial traffic within days.",
    violations: [],
    dropped: ["https://example.invalid/report"],
    no_reference_class: "military strikes on Iranian territory since 1990",
    calls: 1,
    searches: 1,
    seconds: 11.2,
  },
];

/** Draft a claim, and hand back the one request that was made. */
async function draftOne(answer: Parameters<typeof AddAClaim>[0]["draft"]) {
  render(<AddAClaim baseId="a-map" andThen="It goes on a branch." draft={answer} />);
  fireEvent.change(screen.getByLabelText("…but this also happens"), {
    target: { value: "…but Iran is struck the next day" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Draft this claim" }));
}

describe("what Add a claim sends", () => {
  it("test_the_request_carries_three_fields_and_no_position", async () => {
    const sentToTheRoute: DraftRequest[] = [];
    const asked = async (request: DraftRequest) => {
      sentToTheRoute.push(request);
      return { state: "drafted" as const, insert: DRAFTED, receipt: RECEIPT, working: [] };
    };
    await draftOne(asked);
    await waitFor(() => expect(sentToTheRoute).toHaveLength(1));

    const sent = sentToTheRoute[0] as unknown as Record<string, unknown>;
    expect(Object.keys(sent).sort()).toEqual(["base_id", "claim_in_words"]);
    expect(sent.claim_in_words).toBe("…but Iran is struck the next day");
    // Not "position is zero": the field is gone. A drafted edit goes at the end
    // of the branch, which is the only place this product puts one.
    expect(sent).not.toHaveProperty("position");
  });
});

describe("the branch the claim is judged against", () => {
  it("test_the_open_branch_is_sent_with_the_claim", async () => {
    // The route drafts and judges the new claim against the map **with the
    // branch folded on**, which is the map the reader is looking at. Leaving it
    // out asks the rules about a map nobody has in front of them: a claim that
    // contradicts an edit made two minutes ago comes back accepted, and then
    // breaks the branch it is added to.
    const sentToTheRoute: DraftRequest[] = [];
    const branch = {
      id: "01M3BRANCH",
      label: "Brent settled below $68",
      interventions: [{ kind: "observe", target: "B", value: true }],
    } as unknown as NonNullable<DraftRequest["branch"]>;

    render(
      <AddAClaim
        baseId="a-map"
        branch={branch}
        andThen="It goes on a branch."
        draft={async (request) => {
          sentToTheRoute.push(request);
          return { state: "drafted" as const, insert: DRAFTED, receipt: RECEIPT, working: [] };
        }}
      />,
    );
    fireEvent.change(screen.getByLabelText("…but this also happens"), {
      target: { value: "…but Iran is struck the next day" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Draft this claim" }));
    await waitFor(() => expect(sentToTheRoute).toHaveLength(1));

    // Sent whole, in the engine's own shape, with every edit in it.
    expect(sentToTheRoute[0]?.branch).toEqual(branch);
  });

  it("test_a_branch_that_cannot_be_written_down_sends_none", async () => {
    // A branch holding an edit this build cannot write the engine's way cannot
    // be folded, and half a branch is worse than none: the rules would judge
    // the claim against a map that is neither the one on screen nor the one
    // underneath it.
    const sentToTheRoute: DraftRequest[] = [];
    render(
      <AddAClaim
        baseId="a-map"
        andThen="It goes on a branch."
        draft={async (request) => {
          sentToTheRoute.push(request);
          return { state: "drafted" as const, insert: DRAFTED, receipt: RECEIPT, working: [] };
        }}
      />,
    );
    fireEvent.change(screen.getByLabelText("…but this also happens"), {
      target: { value: "…but Iran is struck the next day" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Draft this claim" }));
    await waitFor(() => expect(sentToTheRoute).toHaveLength(1));

    expect(sentToTheRoute[0]).not.toHaveProperty("branch");
  });
});

describe("what Add a claim shows of the answer", () => {
  it("test_every_call_it_took_is_shown_from_the_answer_itself", async () => {
    await draftOne(async () => ({
      state: "drafted" as const,
      insert: DRAFTED,
      receipt: RECEIPT,
      working: WORKING,
    }));

    const lines = await screen.findAllByText(
      (_, element) => element?.className === "inspector__line-words",
    );
    expect(lines).toHaveLength(WORKING.length);
    // Each line in the engine's own words, and never an identifier — the claim
    // a call was about is twenty-six characters of the engine's bookkeeping.
    const said = lines.map((one) => one.textContent ?? "").join(" ");
    for (const line of WORKING) {
      expect(said).toContain(line.in_words);
    }
    expect(document.body.textContent).not.toContain("01M2QYMMJYA27CAZ91N8VPA6NM");

    // An address the model cited that the search never returned is named, not
    // silently dropped: otherwise an arrow that says it argued looks like one
    // that says it documented.
    expect(document.body.textContent).toContain("https://example.invalid/report");
    // And a reference class offered with nothing behind it is said as a class,
    // with no number beside it — a figure with no page behind it reads as
    // measured however it is marked.
    expect(document.body.textContent).toContain("military strikes on Iranian territory since 1990");
  });

  it("test_a_route_that_says_nothing_about_its_working_shows_no_working", async () => {
    await draftOne(async () => ({
      state: "drafted" as const,
      insert: DRAFTED,
      receipt: RECEIPT,
      working: [],
    }));
    await screen.findByText(/Drafted and checked/);
    // Absent rather than invented, like every other slot in this product.
    expect(document.querySelector(".add-a-claim__working")).toBeNull();
  });
});
