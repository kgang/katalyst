/**
 * The whole of a generated map, zoomed out until it fits — and still workable.
 *
 * **Why this is a browser test.** Whether a map *fits* is a fact about laid-out
 * boxes against the stage they are drawn in, and no test without a browser has
 * either. The no-browser tests can say that the floor is derived and that a tile
 * at that zoom draws no words; only this can say that pressing the zoom-out
 * button enough times puts all eighteen claims of the generated map on the glass
 * at once, which is the thing Kent asked for on 2026-09-22: *"Can we make it so
 * it's possible to zoom out a lot more?"*
 *
 * **It plays the recording rather than the stored example**, because the stored
 * example is seven claims and fits at a readable zoom already. Eighteen is the
 * map that does not: at the zoom a full tile needs it is about 1 600 by 1 700
 * pixels on the glass against a stage of about 1 264 by 860, so most of it is
 * off the screen and the reader has to pan to find out what shape their own
 * argument came out.
 *
 * **Nothing below is a number typed into this file.** Every figure is read off
 * the screen — where the stage is, where the tiles are, what the panel says —
 * and compared with itself or with another reading of the same thing.
 */

import type { Page } from "@playwright/test";
import { aDroppedFrameIsExpectedHere, expect, test } from "./theSuite.js";
import { waitForTheLayout } from "./waiting.js";
import { A_WHOLE_RUN, THE_SENTENCE, waitUntilItStops, whatCanBeReplayed } from "./watching.js";

/** The row on the first screen that plays the committed recording of that sentence. */
const THE_RECORDING_ROW = new RegExp(`${THE_SENTENCE}[\\s\\S]*Watch the recording`);

/** How far a box may sit past the stage before it counts, in pixels on the glass. */
const A_PIXEL = 1;

/**
 * The most presses of the zoom-out button this test will make.
 *
 * A bound rather than a count: the loop stops when the button says it can go no
 * further, and this is only here so that a button that never disables fails as a
 * test rather than as a hang. Twenty is comfortably more than the ten or so the
 * floor is from the zoom a map opens at.
 */
const ENOUGH_PRESSES = 20;

// This test watches a whole recording play, so it needs room for one.
test.describe.configure({ timeout: A_WHOLE_RUN + 60_000 });

// A map arriving draws its boxes in bursts and the browser abandons some of that
// frame's size notifications; `generate.spec.ts` carries the full argument for
// why that is harmless here, and this is the short form of it.
test.beforeEach(() => {
  aDroppedFrameIsExpectedHere(
    "This test watches the same recording `generate.spec.ts` watches, and a map " +
      "arriving drops size notifications for the same reason: the boxes come in " +
      "bursts and every box is measured. Nothing on this map waits to be measured " +
      "— `graph/toFlow.ts` declares every tile's box and both ends of every wire — " +
      "and every reading below is taken after the run has stopped and the map has " +
      "come to rest.",
  );
});

test("test_the_whole_generated_map_fits_on_the_glass_at_the_zoom_floor", async ({ page }) => {
  const recorded = await whatCanBeReplayed(page);
  test.skip(recorded.length === 0, "nothing is recorded on this copy, so there is nothing to play");

  await page.goto("/");
  // Every row on the first screen is named by its sentence **and** by what
  // pressing it does, because two rows carry this sentence: one plays the
  // recording for nothing and one calls a model.
  await page.getByRole("button", { name: THE_RECORDING_ROW }).first().click();
  await waitUntilItStops(page);

  // How many claims the recording drew, and how many boxes the map holds,
  // counted off the screen rather than written here. They are two counts
  // because a column that ran out of room would add a box that is not a claim.
  const claims = await page.locator(".react-flow__node.react-flow__node-claim").count();
  const boxes = await page.locator(".react-flow__node").count();
  expect(claims, "the recording drew no claims").toBeGreaterThan(0);
  await waitForTheLayout(page, boxes);

  // **The map as it opens: too big for the stage.** This is the premise. If the
  // whole map already fitted, everything below would pass while proving nothing.
  expect(
    await howManyTilesAreOffTheStage(page),
    "the map already fitted before anything was zoomed out, so this test proves nothing",
  ).toBeGreaterThan(0);

  const presses = await zoomOutUntilItStops(page);
  expect(presses, "the zoom-out button never stopped").toBeLessThan(ENOUGH_PRESSES);

  // **Every tile is on the glass.** The whole argument, in one picture, which is
  // what zooming out is for.
  await expect
    .poll(() => howManyTilesAreOffTheStage(page), {
      message: "some of the map is still off the stage at the furthest the zoom goes",
    })
    .toBe(0);

  // **And not one word inside any of them.** Out here a tile is its shape and
  // nothing else: a word at this zoom would be drawn far under the eleven pixels
  // this product promises, so it is not drawn smaller, it is not drawn.
  expect(await wordsInsideTheTiles(page)).toEqual([]);
  // The plate in the middle of a wire is words too, and goes with them.
  await expect(page.locator(".wire-plate")).toHaveCount(0);
  // The shape is still there, on every claim, and still says which kind.
  await expect(page.locator('.tile[data-detail="silhouette"]')).toHaveCount(claims);
  expect(await page.locator(".tile__outline path").count()).toBeGreaterThanOrEqual(claims);

  // **Pressing one selects it, and the panel reads it out.** That is how a
  // reader learns what a silhouette is: the shape says which kind, and the panel
  // says which claim. Which claim is read off the map's own ring rather than off
  // the tile this test pointed at.
  await page.locator(".react-flow__node.react-flow__node-claim").first().click();
  await expect(page.getByRole("tab", { name: /This claim/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const chosen = page.locator(".react-flow__node.selected").first();
  await expect(chosen).toHaveCount(1);
  const panel = page.locator(".dock");
  const readOut = ((await panel.locator(".inspector__claim").textContent()) ?? "").trim();
  expect(readOut, "the panel turned to a claim with no words in it").not.toBe("");
  // The tile printed nothing, so what it is called is where its own words are —
  // and the panel is showing the same claim.
  const itsName = (await chosen.locator(".tile").getAttribute("aria-label")) ?? "";
  expect(itsName, `the ringed tile is not the claim the panel is reading: "${readOut}"`).toContain(
    readOut,
  );

  // **Zooming back in brings the words back**, on the tile the panel is still
  // reading — and they are the panel's words, which is the two readings of one
  // claim agreeing.
  await zoomInUntilTheTilesHaveWords(page);
  const itsWords = ((await chosen.locator(".tile__claim").textContent()) ?? "").trim();
  expect(itsWords, "zooming back in did not bring back the claim the panel is reading").toBe(
    readOut,
  );
});

/**
 * How many of the map's boxes are not wholly inside the stage they are drawn in.
 *
 * Both are read off the glass in the same frame, so this compares two
 * measurements of the same moment rather than a measurement against a number.
 *
 * @param page The page the map is on.
 */
async function howManyTilesAreOffTheStage(page: Page): Promise<number> {
  return page.evaluate((slack) => {
    const stage = document.querySelector(".map-stage")?.getBoundingClientRect();
    if (stage === undefined) {
      return -1;
    }
    return [...document.querySelectorAll(".react-flow__node")].filter((node) => {
      const box = node.getBoundingClientRect();
      return (
        box.left < stage.left - slack ||
        box.right > stage.right + slack ||
        box.top < stage.top - slack ||
        box.bottom > stage.bottom + slack
      );
    }).length;
  }, A_PIXEL);
}

/**
 * Every word really drawn inside a tile, which out at the floor must be none.
 *
 * Words kept for a screen reader are clipped to a pixel and are not ink, and
 * what a tile is *called* is an attribute rather than something drawn — so this
 * asks for the text the box holds, which is what a reader would see.
 *
 * @param page The page the map is on.
 */
async function wordsInsideTheTiles(page: Page): Promise<string[]> {
  return page.$$eval(".react-flow__node .tile", (found) =>
    found.map((tile) => (tile.textContent ?? "").trim()).filter((words) => words !== ""),
  );
}

/**
 * Press the zoom-out button until it says it will go no further, and say how
 * many presses that took.
 *
 * The button disables itself at the floor, so the floor is asked for rather than
 * counted to — a count would be this test writing down a number the product
 * owns.
 *
 * @param page The page the map is on.
 */
async function zoomOutUntilItStops(page: Page): Promise<number> {
  const button = page.locator(".react-flow__controls-zoomout");
  let presses = 0;
  while (presses < ENOUGH_PRESSES && !(await button.isDisabled())) {
    await button.click();
    presses += 1;
  }
  // The view is animated, so what is read afterwards is where it came to rest.
  await expect(button).toBeDisabled();
  return presses;
}

/**
 * Press the zoom-in button until the tiles are printing words again.
 *
 * It stops on the words rather than on a number of presses, because the words
 * coming back is the thing being checked.
 *
 * @param page The page the map is on.
 */
async function zoomInUntilTheTilesHaveWords(page: Page): Promise<void> {
  const button = page.locator(".react-flow__controls-zoomin");
  for (let press = 0; press < ENOUGH_PRESSES; press++) {
    if ((await wordsInsideTheTiles(page)).length > 0) {
      break;
    }
    await button.click();
  }
  await expect(page.locator('.tile[data-detail="silhouette"]')).toHaveCount(0);
}
