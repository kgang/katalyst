/**
 * **A box that measures itself may not change itself.**
 *
 * The panel beside the map reads how far it is scrolled and how much it holds,
 * and from that draws a two-pixel rule at the edge that has more beyond it. For
 * a while it drew those rules as sticky pseudo-elements of the scrolling box
 * itself — which put two more children into a flex column with a one-pixel gap,
 * so turning one on changed the scroll height of the very box whose scroll
 * height had just been measured.
 *
 * That is a loop, and the browser ends a size-observation loop by abandoning the
 * rest of that frame's observations: *"a ResizeObserver loop completed with
 * undelivered notifications."* The observations it abandons are whichever
 * happen to be queued, and on this screen the drawing library's are queued
 * beside ours — it measures every tile that way, and it draws nothing it has not
 * measured. The map then holds its claims, in their places, drawn
 * `visibility: hidden`, for the life of the page.
 *
 * So the rules are drawn on a **frame** around the panel: a box that does not
 * scroll, positioned, with the rules absolutely placed inside it, taking no
 * space in anything and changing no measurement. This checks the stylesheet
 * rather than a rendered page, because a simulated page has no layout to
 * measure and the fact being checked is a fact about the rules themselves.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const APP_CSS = readFileSync("src/styles/app.css", "utf8");

/**
 * Every rule in the stylesheet, as a selector and the declarations inside it.
 *
 * Flat rather than parsed properly: this file has no nesting and no media query
 * around the rules below, and a hand-rolled parser that handled either would be
 * a thing to maintain for no reading.
 */
function rules(css: string): { selector: string; body: string }[] {
  const found: { selector: string; body: string }[] = [];
  // Comments first, or a `{` inside prose is read as a rule.
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const match of bare.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    found.push({ selector: (match[1] ?? "").trim(), body: match[2] ?? "" });
  }
  return found;
}

const RULES = rules(APP_CSS);

describe("the panel's own rules take no space in it", () => {
  it("test_the_scrolling_panel_draws_nothing_inside_itself", () => {
    // The panel is the box that scrolls, and it is the box that is measured.
    const scroller = RULES.find((rule) => rule.selector === ".dock");
    expect(scroller, "there is no .dock rule to check").toBeDefined();
    expect(scroller?.body).toContain("overflow-y: auto");

    // Nothing may be drawn as a child of it by the stylesheet. A pseudo-element
    // of a flex column is a flex item: it takes a row, and with `gap` it takes a
    // gap as well, and both change the scroll height that decides whether it is
    // drawn at all.
    const inside = RULES.filter(
      (rule) => /(^|,)\s*\.dock\s*::(before|after)/.test(rule.selector) && rule.body.trim() !== "",
    );
    expect(inside.map((rule) => rule.selector)).toEqual([]);
  });

  it("test_the_rules_are_drawn_on_a_frame_that_does_not_scroll", () => {
    const frame = RULES.find((rule) => rule.selector === ".dock-frame");
    expect(frame, "there is no .dock-frame to draw the rules on").toBeDefined();
    // A frame that scrolled would be the same fault one box further out.
    expect(frame?.body).not.toContain("overflow");
    expect(frame?.body).toContain("position: relative");

    const drawn = RULES.filter((rule) => /\.dock-frame\s*::(before|after)/.test(rule.selector));
    expect(drawn.length).toBeGreaterThan(0);
    const placed = drawn.find((rule) => rule.body.includes("content:"));
    expect(placed, "the rules are never given their box").toBeDefined();
    // Out of the flow entirely: it cannot take a row, a gap or a pixel.
    expect(placed?.body).toContain("position: absolute");
  });
});
