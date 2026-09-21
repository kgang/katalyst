/**
 * A tile seen from far away: every belief line is whole, inside its tile, and
 * printed over nothing.
 *
 * **Why this is a browser test.** Zoomed out, a tile stops being a row of
 * columns and becomes a few lines — the owner, the number, the range. Whether
 * two of those lines land on top of each other, or the end of a range runs off
 * the tile, is a fact about laid-out boxes, and the no-browser tests have no
 * layout: every one of them passed on 2026-09-22 while the one tile that holds a
 * venue's number printed its second line over its first, and while the two tiles
 * whose outline cuts into one side lost the end of their range.
 *
 * It runs on the stored example because that is the one map where a tile holds
 * two beliefs. It asserts places, never a number.
 */

import { expect, type Page } from "@playwright/test";
import { test } from "./theSuite.js";

/** How far a box may sit past another before it counts, in pixels on the glass. */
const A_PIXEL = 1;

test("test_a_tile_seen_from_far_away_prints_every_belief_line_whole", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await expect(page.locator(".react-flow__node .tile").first()).toBeVisible();

  // Zoom out until the tiles change to their far-away form. The map does not
  // zoom out past half, so this ends; if the form never comes, that is a failure
  // of this test's own premise and it says so.
  const farTiles = page.locator('.tile[data-detail="summary"]');
  for (let press = 0; press < 10 && (await farTiles.count()) === 0; press++) {
    await page.locator(".react-flow__controls-zoomout").click();
  }
  await expect(farTiles.first(), "the tiles never took their far-away form").toBeVisible();

  // The tile takes its far-away form in one frame and the height reserved for
  // that form in a later one, so what is asserted is where things come to rest:
  // the whole reading is taken again until it holds, and the last failure is the
  // one reported.
  await expect(async () => {
    await everyLineIsWhole(page);
  }).toPass({ timeout: 5_000 });
});

/** Read every tile's belief lines off the glass and hold them to the three rules. */
async function everyLineIsWhole(page: Page): Promise<void> {
  const tiles = await page.$$eval(".react-flow__node .tile", (found) =>
    found.map((tile) => {
      const row = tile.querySelector(".tile__beliefs")?.getBoundingClientRect();
      // The ink of one belief line: every piece of text on the chip's face that
      // is really drawn. The note a chip opens when it is pointed at is not part
      // of the line, and words kept for a screen reader are clipped to a pixel
      // and are not ink.
      const lines = [...tile.querySelectorAll(".belief-chip")].map((chip) => {
        const drawn = [...chip.querySelectorAll(".belief-chip__face *")]
          .filter((piece) => piece.children.length === 0 && piece.textContent?.trim())
          .map((piece) => piece.getBoundingClientRect())
          .filter((box) => box.width > 2 && box.height > 2);
        return {
          owner: chip.getAttribute("data-owner"),
          left: Math.min(...drawn.map((box) => box.left)),
          right: Math.max(...drawn.map((box) => box.right)),
          top: Math.min(...drawn.map((box) => box.top)),
          bottom: Math.max(...drawn.map((box) => box.bottom)),
        };
      });
      return {
        claim: tile.querySelector(".tile__claim")?.textContent ?? "",
        rowRight: row?.right ?? 0,
        rowBottom: tile.getBoundingClientRect().bottom,
        lines,
      };
    }),
  );

  // The premise: this map has a tile holding two beliefs. Without one the test
  // would pass while looking at nothing.
  expect(
    tiles.some((tile) => tile.lines.length > 1),
    "no tile on this map holds two beliefs",
  ).toBe(true);

  for (const tile of tiles) {
    for (const line of tile.lines) {
      expect(
        line.right,
        `"${tile.claim}": the ${line.owner} line runs past the end of its row`,
      ).toBeLessThanOrEqual(tile.rowRight + A_PIXEL);
      expect(
        line.bottom,
        `"${tile.claim}": the ${line.owner} line runs off the foot of its tile`,
      ).toBeLessThanOrEqual(tile.rowBottom + A_PIXEL);
    }
    for (const [at, one] of tile.lines.entries()) {
      for (const other of tile.lines.slice(at + 1)) {
        const apart =
          one.right <= other.left + A_PIXEL ||
          other.right <= one.left + A_PIXEL ||
          one.bottom <= other.top + A_PIXEL ||
          other.bottom <= one.top + A_PIXEL;
        expect(
          apart,
          `"${tile.claim}": the ${one.owner} line and the ${other.owner} line are printed over each other`,
        ).toBe(true);
      }
    }
  }
}
