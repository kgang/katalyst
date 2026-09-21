/**
 * The map takes the keyboard back from nowhere, and never from somewhere.
 *
 * The second landing exists because the drawing library rebuilds a tile's
 * element when what it knows about it changes, so the first landing sometimes
 * lands on the element about to be thrown away and the reader is left behind on
 * the tile they walked off (#36). It is scheduled on the next two animation
 * frames — and **a browser produces no frames while nothing on the page is
 * changing**, so "two frames later" can be minutes later, and the frame that
 * finally runs it is very often one the reader caused by doing something else.
 *
 * That is not a hypothetical. Press a key on the map, then open the command
 * palette: the palette's field takes the keyboard, the frame the palette's
 * arrival caused runs the landing, and the tile takes the keyboard straight
 * back. Every letter typed is then read as a map shortcut, Enter does nothing,
 * and the palette sits there looking open and doing nothing at all.
 */

import { describe, expect, it } from "vitest";
import { mayLandAgain } from "../theKeyboard";

/** A map surface with one tile on it, and a palette that is not on the map. */
function aPage() {
  const surface = document.createElement("div");
  const tile = document.createElement("div");
  tile.tabIndex = 0;
  surface.append(tile);
  const palette = document.createElement("input");
  document.body.append(surface, palette);
  return { surface, tile, palette };
}

describe("the map takes the keyboard back from nowhere", () => {
  it("test_a_landing_that_did_not_take_is_made_again", () => {
    // The case the second landing exists for: the element was rebuilt, so the
    // focus call did nothing and the page has nobody standing anywhere.
    const { surface } = aPage();
    expect(
      mayLandAgain({
        wanted: "B",
        forTile: "B",
        standingOn: undefined,
        active: document.body,
        surface,
      }),
    ).toBe(true);
    // And a page that reports nothing at all is the same statement.
    expect(
      mayLandAgain({ wanted: "B", forTile: "B", standingOn: undefined, active: null, surface }),
    ).toBe(true);
  });

  it("test_a_landing_that_took_is_left_alone", () => {
    const { surface } = aPage();
    expect(
      mayLandAgain({ wanted: "B", forTile: "B", standingOn: "B", active: null, surface }),
    ).toBe(false);
  });

  it("test_a_later_move_wins", () => {
    // Two quick steps must not drag the keyboard back to the first of them.
    const { surface } = aPage();
    expect(
      mayLandAgain({ wanted: "C", forTile: "B", standingOn: undefined, active: null, surface }),
    ).toBe(false);
  });

  it("test_the_map_never_takes_the_keyboard_out_of_the_palette", () => {
    // **The defect.** The palette is open, its field has the keyboard, and a
    // landing scheduled before it opened finally runs. The map must leave it
    // exactly where the reader put it.
    const { surface, palette } = aPage();
    palette.focus();
    expect(document.activeElement).toBe(palette);
    expect(
      mayLandAgain({
        wanted: "B",
        forTile: "B",
        standingOn: undefined,
        active: document.activeElement,
        surface,
      }),
    ).toBe(false);
  });

  it("test_a_landing_still_works_when_the_keyboard_is_elsewhere_on_the_map", () => {
    // Somewhere on the map is not somewhere else: the reader has not left, and
    // a landing that has not been overtaken is still the move they asked for.
    const { surface, tile } = aPage();
    tile.focus();
    expect(
      mayLandAgain({
        wanted: "B",
        forTile: "B",
        standingOn: undefined,
        active: document.activeElement,
        surface,
      }),
    ).toBe(true);
  });

  it("test_a_map_that_has_gone_takes_nothing_back", () => {
    // The screen was left while the landing was pending. There is no surface to
    // be on, so there is nothing to be taken back to.
    expect(
      mayLandAgain({
        wanted: "B",
        forTile: "B",
        standingOn: undefined,
        active: document.createElement("input"),
        surface: null,
      }),
    ).toBe(false);
  });
});
