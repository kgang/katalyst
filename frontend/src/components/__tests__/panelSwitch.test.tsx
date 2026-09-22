/**
 * The switcher at the head of the panel beside the map.
 *
 * **The test that would have caught what Kent saw.** On 2026-09-22 he asked, of
 * the replay: *"could you have it so that clicking on a card will expand its
 * details on the right hand side panel?"* — and a click already did select the
 * tile, and the panel already read it out. It read it out **at the very bottom
 * of one long column**, under the verdict, every refusal in full, the receipt
 * and *Run details*, and nothing scrolled. So the details were on the page and
 * off the screen, and the click looked dead.
 *
 * Every case below is written against the screens rather than against the
 * switcher on its own, because what is claimed is about a screen: which panels
 * it offers, which one is on the glass, and what is allowed to move it. The
 * first one fails on `674acfd`, this branch's base, for the reason above — the
 * claim's words are in the panel, and so is everything else.
 *
 * **No case here asserts a line of copy and none asserts a typed-in number.** A
 * count is compared with how many events the test itself handed in; a label is
 * asked whether it is a word rather than which word it is.
 */

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { MapScreen } from "../../components/MapScreen";
import { B, REFUSED, THE_GROWTH, THE_SENTENCE } from "../../stream/__tests__/aStream";
import type { ProposalRejected, StreamEvent } from "../../stream/events";
import { GenerationScreen } from "../../stream/GenerationScreen";
import { fold, waitingFor } from "../../stream/growth";
import type { TheRun, WhereItHasGot } from "../../stream/theRun";
import { aClaim, aWorld } from "../../test/aMap";
import type { Selection, WorldView } from "../../world";

// The map draws on a canvas a simulated page cannot measure, and what it draws
// has tests of its own. Here it stands in for itself: one button per claim and
// one per arrow, each doing what pointing at that claim or that arrow does on
// the real canvas — it hands the screen a selection and nothing else.
vi.mock("../../graph/Canvas", () => ({
  MapCanvas: ({
    world,
    onSelect,
  }: {
    world: WorldView;
    onSelect: (selection: Selection) => void;
  }) => (
    <div data-testid="the-map">
      {world.claims.map((claim) => (
        <button
          key={claim.id}
          type="button"
          data-testid={`point-at-${claim.id}`}
          onClick={() => onSelect({ kind: "claim", id: claim.id })}
        >
          {claim.id}
        </button>
      ))}
      {world.links.map((link) => (
        <button
          key={link.id}
          type="button"
          data-testid={`point-at-${link.id}`}
          onClick={() => onSelect({ kind: "wire", id: link.id })}
        >
          {link.id}
        </button>
      ))}
    </div>
  ),
}));

beforeAll(() => {
  // A simulated page does no measuring at all, and the panel measures its own
  // edges the moment it is drawn.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

/**
 * A run somebody else is driving, so a test can hand it one event at a time.
 *
 * The real interface with the real fold behind it, and no request anywhere: the
 * screen watches what it is given and asks for nothing.
 */
function aRunWeDrive(): TheRun & { arrive: (event: StreamEvent) => void } {
  const opening = waitingFor(THE_SENTENCE, null);
  let where: WhereItHasGot = { growth: opening, saying: "" };
  const watchers = new Set<() => void>();
  return {
    asked: { hypothesis: THE_SENTENCE, target: null, belief: null },
    press: "press 1",
    now: () => where,
    watch: (told: () => void) => {
      watchers.add(told);
      return () => {
        watchers.delete(told);
      };
    },
    letGo: () => {},
    arrive: (event: StreamEvent) => {
      where = { growth: fold(where.growth, event), saying: where.saying };
      for (const told of watchers) {
        told();
      }
    },
  };
}

/** The panel that is actually on the glass, with whatever is in it. */
function thePanel(): HTMLElement {
  const dock = document.querySelector(".dock");
  expect(dock, "there is no panel beside the map").not.toBeNull();
  return dock as HTMLElement;
}

/** Every label the switcher offers, in the order it offers them. */
function theLabels(): string[] {
  return screen.getAllByRole("tab").map((tab) => (tab.textContent ?? "").trim());
}

/** Which panel is on the glass, by the label that chose it. */
function showing(): string {
  const chosen = screen
    .getAllByRole("tab")
    .find((tab) => tab.getAttribute("aria-selected") === "true");
  expect(chosen, "the switcher names no panel as the one on the glass").toBeDefined();
  return ((chosen as HTMLElement).textContent ?? "").trim();
}

/** The word on one label, without whatever count rides beside it. */
function theWordOn(tab: HTMLElement): string {
  return (tab.querySelector(".panel-switch__word")?.textContent ?? "").trim();
}

/** A map building itself, with these events already folded into it. */
function aRunThatHasGotTo(events: readonly StreamEvent[]) {
  const run = aRunWeDrive();
  const drawn = render(
    <GenerationScreen run={run} replaying={true} onRunAgain={() => {}} onLeave={() => {}} />,
  );
  act(() => {
    for (const event of events) {
      run.arrive(event);
    }
  });
  return { run, ...drawn };
}

/** The stored map, with two claims a reader can tell apart. */
function theStoredMap() {
  const world = aWorld({
    claims: [
      aClaim({ id: "H", kind: "hypothesis", claim: "The strait reopens to commercial transit." }),
      aClaim({ id: "B", claim: "Brent crude settles below sixty-eight dollars." }),
    ],
  });
  return render(
    <MapScreen
      base={world}
      branches={[]}
      source={
        {
          readWorld: () => Promise.resolve(world),
          // One arrow's own number is asked for when a reader selects that
          // arrow. Nothing here reads the answer; what is being tested is where
          // the question puts the panel.
          readConditional: () => new Promise(() => {}),
        } as never
      }
      insteadOfTheEngine={null}
      onLeave={() => {}}
    />,
  );
}

describe("a click on a tile shows that claim, at once, in the panel on the glass", () => {
  it("test_a_click_on_a_tile_during_a_replay_shows_that_claim_in_the_panel", () => {
    // Five events in: the run has started and four claims have arrived. The
    // recording is still coming — nothing has finished — which is when Kent
    // pressed.
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5));

    fireEvent.click(screen.getByTestId("point-at-B"));

    // The claim the reader pointed at, in its own words, in the panel that is on
    // the glass — not somewhere below it.
    expect(thePanel().textContent).toContain(B.claim);

    // And nothing stands in front of it. On the base of this branch the panel is
    // one long column and the run's own sections stood above the claim, which is
    // why the click looked dead.
    expect(thePanel().textContent).not.toContain("Refused by the rules");
    expect(thePanel().textContent).not.toContain("Run details");
  });

  it("test_a_click_on_an_arrow_shows_that_arrow_in_the_panel", () => {
    theStoredMap();
    fireEvent.click(screen.getByTestId("point-at-H->B"));

    // The panel on the glass reads the arrow out, and the branches are not
    // stacked on top of it. The label follows the subject, because the subject
    // is what the panel is about.
    expect(thePanel().textContent).not.toContain("Branches");
    expect(showing().toLowerCase()).toContain("arrow");
  });
});

describe("the switcher offers the panels this screen has, and no others", () => {
  it("test_the_switcher_offers_only_the_panels_this_context_has", () => {
    const { unmount } = aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    const onTheRun = theLabels();

    // Few. One per thing the screen stacks, and never a list a reader has to
    // read before choosing.
    expect(onTheRun.length).toBeGreaterThanOrEqual(2);
    expect(onTheRun.length).toBeLessThanOrEqual(4);
    // A map being built has no branches to open, so no panel offers any.
    expect(onTheRun.join(" · ")).not.toMatch(/branch/i);
    unmount();
  });

  it("test_the_stored_map_offers_its_own_panels_and_not_the_runs", () => {
    theStoredMap();
    const stored = theLabels();
    expect(stored.length).toBeGreaterThanOrEqual(2);
    expect(stored.length).toBeLessThanOrEqual(4);
    // Nobody generated a stored map here, so there is no run to read out.
    expect(stored.join(" · ")).not.toMatch(/\brun\b/i);
    expect(stored.join(" · ")).toMatch(/branch/i);
  });

  it("test_every_panel_label_is_a_word", () => {
    const { unmount } = aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    for (const tab of screen.getAllByRole("tab")) {
      expect(theWordOn(tab), "a panel is offered with no word on it").toMatch(
        /^[A-Za-z][A-Za-z ]+$/,
      );
    }
    unmount();

    theStoredMap();
    for (const tab of screen.getAllByRole("tab")) {
      expect(theWordOn(tab), "a panel is offered with no word on it").toMatch(
        /^[A-Za-z][A-Za-z ]+$/,
      );
    }
  });
});

describe("nothing but the reader's own selection moves the panel", () => {
  it("test_a_refusal_arriving_does_not_pull_the_reader_off_what_they_are_reading", () => {
    const { run } = aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    fireEvent.click(screen.getByTestId("point-at-B"));
    const wasShowing = showing();
    expect(thePanel().textContent).toContain(B.claim);

    // Two proposals the rules refuse, arriving while the reader is reading the
    // claim they chose. The second carries its own place in the working, so the
    // two are two rather than one counted twice.
    const second: ProposalRejected = { ...REFUSED, at: REFUSED.at + 2 };
    const refusals: readonly ProposalRejected[] = [REFUSED, second];
    act(() => {
      for (const refusal of refusals) {
        run.arrive(refusal);
      }
    });

    // The panel did not move, and what the reader was reading is still in it.
    expect(showing()).toBe(wasShowing);
    expect(thePanel().textContent).toContain(B.claim);

    // What changed is the label of the panel they landed in: it carries how
    // many, and how many is how many this test handed in.
    const marks = screen
      .getAllByRole("tab")
      .map((tab) => (tab.querySelector(".panel-switch__mark")?.textContent ?? "").trim())
      .filter((mark) => mark !== "");
    expect(marks.length, "a refusal arrived and no label said so").toBe(1);
    expect(marks[0]).toContain(String(refusals.length));
    expect(marks[0]?.toLowerCase()).toContain("refused");
  });
});

describe("the keyboard steps between the panels", () => {
  it("test_the_arrow_keys_move_between_the_labels", () => {
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    const labels = theLabels();
    const first = showing();
    const at = labels.indexOf(first);

    const tab = screen.getAllByRole("tab")[at] as HTMLElement;
    tab.focus();
    fireEvent.keyDown(tab, { key: "ArrowRight" });
    expect(showing()).toBe(labels[(at + 1) % labels.length]);

    fireEvent.keyDown(screen.getAllByRole("tab")[(at + 1) % labels.length] as HTMLElement, {
      key: "ArrowLeft",
    });
    expect(showing()).toBe(first);
  });

  it("test_the_one_key_steps_to_the_next_panel_from_anywhere_on_the_screen", () => {
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    const labels = theLabels();
    const at = labels.indexOf(showing());

    // Pressed with the keyboard nowhere near the switcher, which is the whole
    // reason it is one key rather than a Tab and an arrow.
    fireEvent.keyDown(document.body, { key: "n" });
    expect(showing()).toBe(labels[(at + 1) % labels.length]);

    // And it goes round, so one key reaches every panel.
    for (let press = 1; press < labels.length; press += 1) {
      fireEvent.keyDown(document.body, { key: "n" });
    }
    expect(showing()).toBe(labels[at]);
  });

  it("test_typing_is_never_a_shortcut", () => {
    theStoredMap();
    const before = showing();
    // A branch is named in a field, and in a field an `n` is an `n`.
    const field = document.createElement("input");
    document.body.append(field);
    field.focus();
    fireEvent.keyDown(field, { key: "n" });
    expect(showing()).toBe(before);
    field.remove();
  });
});

describe("the panel on the glass says which one it is", () => {
  it("test_the_panel_is_named_by_the_label_that_chose_it", () => {
    aRunThatHasGotTo(THE_GROWTH.slice(0, 5));
    const dock = thePanel();
    expect(dock.getAttribute("role")).toBe("tabpanel");
    const named = dock.getAttribute("aria-labelledby");
    expect(named, "the panel is not named by anything").not.toBeNull();
    const label = document.getElementById(named as string);
    expect(label, "the panel names a label that is not on the screen").not.toBeNull();
    expect((label as HTMLElement).getAttribute("aria-selected")).toBe("true");
    // The switcher is at the head of the panel and outside the part that
    // scrolls, so a reader who scrolls never loses the way back.
    expect(within(dock).queryAllByRole("tab").length).toBe(0);
  });
});
