import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Waiting, and why every read in a browser test goes through it.
 *
 * **Nothing here reads a value the page has not settled on.** These tests drive
 * two servers, a background layout thread and a drawing library that measures
 * its own boxes, so at any moment the screen may be showing the answer to the
 * question before last. Every read goes through one of the helpers below, and
 * each of them waits for a *named* signal rather than for a number of
 * milliseconds — a sleep is a guess, and the build machine is about two and a
 * half times slower than the machine it was guessed on.
 *
 * They live in a file of their own because both browser tests need them, and a
 * helper copied into a second file is a second helper: the day one of these
 * learns about a new way the screen can lie, only one test would learn it.
 */

/**
 * Wait until the map has been laid out, with every tile in a place of its own.
 *
 * Where the tiles go is worked out on a background thread, so for a moment after
 * the map appears the tiles are still stacked. Waiting for **every** tile to be
 * somewhere different is the honest signal, and it is the one that survives a
 * second layout: after a branch opens the tiles are already spread out from the
 * layout before it, so "more than one place" is satisfied before the new answer
 * has landed and says nothing at all.
 *
 * @param page The page the map is on.
 * @param tiles How many tiles this map has. A layered layout gives every tile a
 *   place of its own — two tiles on one spot is the collision the layout exists
 *   to prevent — so the count of places is the count of tiles exactly when the
 *   layout has landed.
 */
export async function waitForTheLayout(page: Page, tiles: number): Promise<void> {
  await expect(page.locator(".react-flow__node")).toHaveCount(tiles);
  await expect
    .poll(
      () =>
        page
          .locator(".react-flow__node")
          .evaluateAll(
            (nodes) => new Set(nodes.map((node) => (node as HTMLElement).style.transform)).size,
          ),
      { timeout: 30_000, message: "the map was never laid out" },
    )
    .toBe(tiles);
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
}

/**
 * Read one value off the screen, once the screen has settled on it.
 *
 * The shape is not decoration: it is what "settled" means here. A chip holds an
 * absence, then a number; waiting for the number's shape is waiting for the
 * engine. And the read itself is `textContent` rather than `innerText`, which
 * is empty until the drawing library has measured the tile.
 *
 * @param where The one element the value is in.
 * @param shape What the value looks like once it is there.
 */
export async function readWhenReady(where: Locator, shape: RegExp): Promise<string> {
  await expect(where).toBeVisible();
  await expect(where).toHaveText(shape);
  return ((await where.textContent()) ?? "").trim();
}

/**
 * Wait until the engine has answered for this branch and the map has been laid
 * out again.
 *
 * The line under the map names the branch it folded on, and it is written from
 * the world the engine handed back — so it is there exactly when that world is.
 *
 * @param page The page the map is on.
 * @param branch The branch's name, as the reader typed it.
 * @param tiles How many tiles the map has with this branch folded on.
 */
export async function waitForTheBranch(page: Page, branch: string, tiles: number): Promise<void> {
  await expect(page.locator(".map-bar__where")).toContainText(branch);
  await expect(page.locator(".map-origin")).toContainText(`the branch "${branch}" folded onto it`);
  await waitForTheLayout(page, tiles);
}

/**
 * Wait until the map has said, out loud, what this edit did.
 *
 * This is the signal an edit is finished. The counts in the sentence are the
 * engine's own, one per claim it called shifted, so the sentence cannot be there
 * until the difference is — and it is a *different* sentence from the one before
 * the edit, which is what makes waiting for it waiting rather than passing.
 *
 * @param page The page the map is on.
 * @param sentence The whole line — word for word, or the shape of it where one
 *   of its counts is the engine's own and so is not written into a test. A
 *   shape has to be narrow enough to be a real wait: it must not also fit the
 *   line the map says before the engine has answered, or the wait passes on the
 *   answer to the question before this one.
 */
export async function waitForTheAnswer(page: Page, sentence: string | RegExp): Promise<void> {
  await expect(page.locator(".map-live")).toHaveText(sentence);
}

/**
 * Wait until the map has stopped moving, and say where it came to rest.
 *
 * Framing the map is an animation, so the transform is read twice and believed
 * only when the two agree. What it is for is the claim that flipping between the
 * two worlds moves nothing: a transform read mid-frame would make that claim
 * about two different moments.
 */
export async function whereTheMapCameToRest(page: Page): Promise<string> {
  const viewport = page.locator(".react-flow__viewport");
  let last = "";
  await expect
    .poll(
      async () => {
        const now = (await viewport.getAttribute("style")) ?? "";
        const settled = now !== "" && now === last;
        last = now;
        return settled;
      },
      { timeout: 30_000, message: "the map never stopped moving" },
    )
    .toBe(true);
  return last;
}

/** Which claim the keyboard is standing on, or nothing when it is off the map. */
export function standingOn(page: Page): Promise<string | undefined> {
  return page.evaluate(
    () => document.activeElement?.closest<HTMLElement>(".react-flow__node")?.dataset.id,
  );
}

/**
 * Put the keyboard on one claim's tile, the way a reader would, and wait until
 * it is there.
 *
 * **A map key only works when the keyboard is on the map**, and that is the
 * product's rule rather than this test's convenience: Space belongs to whatever
 * button the keyboard is on, so `useMapKeys` hands it over when there is one and
 * flips the two worlds only when there is not. Where focus happens to be after
 * a command has run is not something a test may assume — under load it is
 * sometimes a button, and then the keystroke is correctly ignored and the test
 * fails for a reason that is not a fault.
 *
 * @param page The page the map is on.
 * @param claim The claim whose tile the keyboard should stand on.
 */
export async function standOn(page: Page, claim: string): Promise<void> {
  await expect
    .poll(
      async () => {
        // The focusing is inside the poll, not before it. A re-render replaces
        // the tile's element and the keyboard falls back to the page, so asking
        // again and again whether it landed would ask for ever; what has to be
        // retried is the standing, not the looking.
        await page.locator(`.react-flow__node[data-id="${claim}"]`).focus();
        return await standingOn(page);
      },
      { timeout: 15_000, message: `the keyboard never stood on ${claim}` },
    )
    .toBe(claim);
}

/**
 * Where one tile sits, once the drawing library has put it somewhere.
 *
 * **The place, and nothing else about the element.** The library writes several
 * things into a tile's style — its stacking order, whether the pointer may reach
 * it, and whether it is visible at all, which it turns off and on again as it
 * measures boxes — and only one of them is where the tile is. Comparing the
 * whole style across a change compares those too, and then "the tile kept its
 * place" fails on a tile that was merely being re-measured. For the same
 * reason this waits for the tile to have a **place** rather than for it to be
 * visible: where it sits is a fact about the layout, and whether it is painted
 * this instant is not.
 *
 * @param tile The tile's element on the map.
 */
export async function whereTheTileSits(tile: Locator): Promise<string> {
  await expect(tile).toHaveCount(1);
  await expect
    .poll(
      async () => /translate\([^)]*\)/.exec((await tile.getAttribute("style")) ?? "")?.[0] ?? "",
      { timeout: 30_000, message: "the tile was never placed" },
    )
    .not.toBe("");
  return /translate\([^)]*\)/.exec((await tile.getAttribute("style")) ?? "")?.[0] ?? "";
}
