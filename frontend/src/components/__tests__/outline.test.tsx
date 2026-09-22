/**
 * The map read as a list, and what it says when there is nothing to read.
 *
 * **The case that was missing.** The list drew its heading, drew the line
 * saying what it lists, and then drew nothing — on the one screen where that
 * happens for a good reason, a map that is still being built. A heading over
 * nothing reads as a view that has broken, and the reader has no way to tell it
 * from one that has. The empty case is a fact about the run, and this is the
 * test that it is stated.
 *
 * **No case here asserts a typed-in number.** The list is compared with the
 * items the test itself handed it.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OutlineItem } from "../../a11y/sentences";
import { NOTHING_YET, Outline } from "../Outline";

/** One claim, as the list takes it. Its sentence is the test's own words. */
function anItem(id: string, sentence: string, children: OutlineItem[] = []): OutlineItem {
  return { id, sentence, level: 1, children };
}

describe("the map as a list", () => {
  it("test_a_list_with_nothing_in_it_says_so_in_words", () => {
    render(<Outline items={[]} onPick={vi.fn()} focused={null} />);

    // The heading is still there — the panel is this view whatever it holds.
    expect(screen.getByRole("heading", { name: "The map as a list" })).toBeInTheDocument();
    // And under it, one sentence rather than a silence.
    expect(screen.getByText(NOTHING_YET)).toBeInTheDocument();
    // No empty tree for a screen reader to announce as a list of nothing.
    expect(screen.queryByRole("tree")).toBeNull();
  });

  it("test_a_list_with_claims_in_it_lists_them_and_says_nothing_about_being_empty", () => {
    const items = [anItem("H", "the first claim"), anItem("B", "the second claim")];
    render(<Outline items={items} onPick={vi.fn()} focused={null} />);

    // As many rows as the test handed in, counted rather than written down.
    expect(screen.getAllByRole("treeitem")).toHaveLength(items.length);
    for (const item of items) {
      expect(screen.getByText(item.sentence)).toBeInTheDocument();
    }
    expect(screen.queryByText(NOTHING_YET)).toBeNull();
  });

  it("test_a_filter_that_reaches_no_claim_says_the_same_thing", () => {
    // The one other way this view can come out empty: it is filtered to a
    // column, and nothing in it is on the map any more.
    render(
      <Outline
        items={[anItem("H", "the first claim")]}
        only={new Set<string>()}
        filter="The claims behind one tile."
        onPick={vi.fn()}
        focused={null}
      />,
    );

    expect(screen.getByText(NOTHING_YET)).toBeInTheDocument();
    expect(screen.queryByRole("treeitem")).toBeNull();
  });
});
