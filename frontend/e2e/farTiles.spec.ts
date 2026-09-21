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
 * **Why it reads the map twice.** The first version of this test read the base
 * map only, and the base map is the easy one: every likelihood on it has two
 * figures, and two figures just fit beside their owner and their range on one
 * line at this size. Open the stored branch and the engine prints three —
 * `.074  .029–.13` — and the line no longer fits. Nobody saw that, because
 * nothing read the far-away tiles with a branch open. So this opens the stored
 * branch, zooms out again (opening a branch re-frames the map to full zoom) and
 * reads every line a second time, and it ends by checking that the branch really
 * did print a belief the base map could not print on one line — otherwise the
 * second reading is the first one again.
 *
 * It runs on the stored example because that is the one map where a tile holds
 * two beliefs. It asserts places, never a number.
 */

import { expect, type Page } from "@playwright/test";
import { test } from "./theSuite.js";
import { waitForTheBranch, waitForTheLayout } from "./waiting.js";

/** How far a box may sit past another before it counts, in pixels on the glass. */
const A_PIXEL = 1;

/** The branch the stored example is shipped with, by the name the reader sees. */
const THE_STRIKE_BRANCH = "Hormuz opens, then Iran is struck";

test("test_a_tile_seen_from_far_away_prints_every_belief_line_whole", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz/ })
    .first()
    .click();
  await waitForTheLayout(page, 7);

  await zoomOutUntilTheTilesAreFarAway(page);
  // The tile takes its far-away form in one frame and the height reserved for
  // that form in a later one, so what is asserted is where things come to rest:
  // the whole reading is taken again until it holds, and the last failure is the
  // one reported.
  await expect(async () => {
    await everyLineIsWhole(page, "on the base map");
  }).toPass({ timeout: 5_000 });

  // The stored branch, opened the way a reader opens it: by pressing its name in
  // the panel. The map re-frames to full zoom when it opens, so it has to be
  // zoomed out again before there is anything far away to read.
  await page
    .getByRole("button", { name: new RegExp(THE_STRIKE_BRANCH) })
    .first()
    .click();
  await waitForTheBranch(page, THE_STRIKE_BRANCH, 8);

  await zoomOutUntilTheTilesAreFarAway(page);
  await expect(async () => {
    await everyLineIsWhole(page, "with the branch open");
  }).toPass({ timeout: 5_000 });

  // **The premise of the second reading.** The fault this test was extended for
  // only shows itself where a belief will not fit on one line and its range has
  // to take one of its own. So the map with the branch open must hold such a
  // belief: without one the second reading looked at nothing harder than the
  // first, and proves nothing.
  expect(
    await howManyBeliefsTookASecondLine(page),
    "no belief with the branch open needed a second line, so reading it proved nothing",
  ).toBeGreaterThan(0);
});

/**
 * Zoom out until the tiles change to their far-away form.
 *
 * The map does not zoom out past half, so this ends; if the form never comes,
 * that is a failure of this test's own premise and it says so.
 *
 * @param page The page the map is on.
 */
async function zoomOutUntilTheTilesAreFarAway(page: Page): Promise<void> {
  const farTiles = page.locator('.tile[data-detail="summary"]');
  for (let press = 0; press < 10 && (await farTiles.count()) === 0; press++) {
    await page.locator(".react-flow__controls-zoomout").click();
  }
  await expect(farTiles.first(), "the tiles never took their far-away form").toBeVisible();
}

/** One tile's far-away belief lines, as boxes on the glass. */
interface FarTile {
  readonly claim: string;
  readonly rowRight: number;
  readonly rowBottom: number;
  readonly lines: readonly {
    readonly owner: string | null;
    /** `number` when this belief prints a likelihood, `words` when it prints an absence. */
    readonly reading: string | null;
    /** How much of the widest piece of this line has been cut off, in pixels. */
    readonly cutOff: number;
    readonly left: number;
    readonly right: number;
    readonly top: number;
    readonly bottom: number;
  }[];
}

/**
 * Read every tile's belief lines off the glass.
 *
 * The ink of one belief line: every piece of text on the chip's face that is
 * really drawn. The note a chip opens when it is pointed at is not part of the
 * line, and words kept for a screen reader are clipped to a pixel and are not
 * ink.
 *
 * @param page The page the map is on.
 */
async function theBeliefLines(page: Page): Promise<FarTile[]> {
  return page.$$eval(".react-flow__node .tile", (found) =>
    found.map((tile) => {
      const row = tile.querySelector(".tile__beliefs")?.getBoundingClientRect();
      const lines = [...tile.querySelectorAll(".belief-chip")].map((chip) => {
        const pieces = [...chip.querySelectorAll(".belief-chip__face *")].filter(
          (piece) => piece.children.length === 0 && piece.textContent?.trim(),
        );
        const drawn = pieces
          .map((piece) => piece.getBoundingClientRect())
          .filter((box) => box.width > 2 && box.height > 2);
        return {
          owner: chip.getAttribute("data-owner"),
          reading: chip.getAttribute("data-reading"),
          // What a box holds against what it shows. A word that has been cut
          // short has more of itself than it is showing, and the ellipsis the
          // stylesheet draws in its place is not part of the word.
          cutOff: Math.max(...pieces.map((piece) => piece.scrollWidth - piece.clientWidth)),
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
}

/**
 * How many beliefs on this map printed their range on a line of its own.
 *
 * No height is written down here. A belief that fits beside its number is the
 * short kind and a belief whose range took a second line is taller than that —
 * so the shortest line on the map is what one line is, and anything taller than
 * it has wrapped. Two measurements of the same thing, compared with each other.
 *
 * **Only the beliefs that print a likelihood are counted.** A belief that prints
 * words instead — *no engine yet*, *Supposed · Oct 2* — wraps to two lines of
 * its own accord and always did, so counting those would let the premise pass
 * for a reason that has nothing to do with a range.
 *
 * @param page The page the map is on.
 */
async function howManyBeliefsTookASecondLine(page: Page): Promise<number> {
  const tiles = await theBeliefLines(page);
  const heights = tiles.flatMap((tile) =>
    tile.lines.filter((line) => line.reading === "number").map((line) => line.bottom - line.top),
  );
  const oneLine = Math.min(...heights);
  return heights.filter((height) => height > oneLine + A_PIXEL).length;
}

/**
 * Hold every belief line on the map to the four rules: nothing on it cut short,
 * inside its row on the right, inside its tile at the foot, printed over
 * nothing.
 *
 * @param page The page the map is on.
 * @param where Which reading this is, so a failure names the state the map was
 *   in — the base map and the same map with a branch open fail differently.
 */
async function everyLineIsWhole(page: Page, where: string): Promise<void> {
  const tiles = await theBeliefLines(page);

  // The premise: this map has a tile holding two beliefs. Without one the test
  // would pass while looking at nothing.
  expect(
    tiles.some((tile) => tile.lines.length > 1),
    `no tile on this map holds two beliefs (${where})`,
  ).toBe(true);

  for (const tile of tiles) {
    for (const line of tile.lines) {
      // Nothing on the line is shortened to make it fit: not the range, and not
      // the owner, who is never abbreviated. A line that will not fit takes a
      // second line; it never gives a word up.
      expect(
        line.cutOff,
        `${where}, "${tile.claim}": the ${line.owner} line has been cut short to make it fit`,
      ).toBeLessThanOrEqual(A_PIXEL);
      expect(
        line.right,
        `${where}, "${tile.claim}": the ${line.owner} line runs past the end of its row`,
      ).toBeLessThanOrEqual(tile.rowRight + A_PIXEL);
      expect(
        line.bottom,
        `${where}, "${tile.claim}": the ${line.owner} line runs off the foot of its tile`,
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
          `${where}, "${tile.claim}": the ${one.owner} line and the ${other.owner} line are printed over each other`,
        ).toBe(true);
      }
    }
  }
}
