/**
 * A map drawing itself, in a real browser, against a real server, **with no
 * model key at all**.
 *
 * It is the one thing no component test can claim: that a reviewer who has
 * configured nothing can open the first screen, press a card, and watch a map
 * build itself claim by claim — with a reserved rectangle standing where the next
 * claim will go, every proposal the rules refused on screen in the validator's
 * own words, and a receipt at the end saying what it cost.
 *
 * **It plays a recording, through the same route, the same eight events and the
 * same canvas a live run uses.** The only substitution anywhere is where the
 * bytes came from, which is what makes this evidence about the live route rather
 * than about a second one.
 *
 * **It skips itself when there is nothing recorded**, in one line saying so. The
 * recordings are made by the half of this stack that owns the model boundary, and
 * the first real one is made against a real key by the person who holds it; until
 * one is committed under `backend/recordings/`, this test has nothing to play and
 * says that rather than failing. The moment one lands it runs, with no change
 * here.
 *
 * Nothing below is a number typed into this file. Every figure is read off the
 * screen and compared with itself across a change, or checked for its shape.
 */

import { expect, type Page, test } from "@playwright/test";

/**
 * Wait until the map has been laid out.
 *
 * Where the tiles go is worked out on a background thread, so for a moment after
 * a claim arrives every box is still stacked in the same place. Waiting for them
 * to be somewhere is the honest signal; waiting a fixed number of milliseconds is
 * a guess that is wrong on a slow machine.
 */
async function waitForTheLayout(page: Page): Promise<void> {
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
    .toBeGreaterThan(1);
}

/** What this copy of the server says it can play back without a key. */
async function whatCanBeReplayed(page: Page): Promise<{ example: string }[]> {
  const answer = await page.request.get("/api/readyz");
  const said = (await answer.json()) as { replayable?: { example: string }[] };
  return said.replayable ?? [];
}

test("a map draws itself from a recording, with no model key", async ({ page }) => {
  await page.goto("/");

  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no generation to watch.",
  );

  // The first screen says what this copy is, word for word, with the day taken
  // from the server's own readiness answer. It is said twice — under the four
  // cards, and again under the field it disables — and both are checked, because
  // a field that takes typing and then does nothing reads as a broken tool.
  const keyless = page.getByText(
    /^No model key configured — these four run from recordings made on \d{4}-\d{2}-\d{2}\.$/,
  );
  await expect(keyless).toHaveCount(2);
  await expect(keyless.first()).toBeVisible();

  // The card that has a recording. It sends its sentence, exactly as a reader
  // would type it — the same request a live run sends.
  const card = page.getByRole("button", {
    name: /The Strait of Hormuz is going to open next week/,
  });
  await card.focus();
  await expect(card).toBeFocused();
  await page.keyboard.press("Enter");

  // **The first paint is a reserved rectangle, not a spinner.** It is on screen
  // before any claim is, and it carries the reader's own sentence.
  const reserved = page.locator(".skeleton-tile");
  await expect(reserved.first()).toBeVisible({ timeout: 15_000 });
  await expect(reserved.first()).toContainText("The Strait of Hormuz is going to open next week.");
  expect(await page.locator(".tile").count()).toBe(0);

  // The badge says this session is a replay, from the first frame, before the
  // receipt that also says so has arrived.
  await expect(page.locator(".replay-badge")).toBeVisible();

  // Nothing spins anywhere, at any point.
  expect(await page.getByRole("progressbar").count()).toBe(0);

  // The map grows. Claims arrive one after another, and the reserved rectangles
  // are the claims still open to expand.
  await expect(page.locator(".tile").first()).toBeVisible({ timeout: 30_000 });
  await waitForTheLayout(page);

  // While it grows, not one likelihood is on screen: they are worked through the
  // whole map at once, when the map is finished.
  await expect(page.locator(".tile").first()).toContainText("no engine yet");

  // Nothing that was already placed moves. Where the first tile sits is read
  // before the rest arrive and compared with itself afterwards.
  const firstTile = page.locator(".react-flow__node.react-flow__node-claim").first();
  const wasAt = await firstTile.getAttribute("style");

  // Every proposal the rules refused is on screen, in the validator's own words.
  const refusals = page.locator(".refusal-strip__row");
  await expect(refusals.first()).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".refusal-strip__reason").first()).not.toBeEmpty();
  // The rule's stable code is carried on the event and drawn nowhere.
  await expect(page.locator(".refusal-strip")).not.toContainText("cycle");

  // The receipt, when the run is over: nine labelled readings, every one a field.
  const receipt = page.locator(".receipt-strip");
  await expect(receipt).toBeVisible({ timeout: 120_000 });
  await expect(receipt.locator(".receipt-strip__label")).toHaveText([
    "model",
    "calls",
    "tokens in",
    "tokens out",
    "read from cache",
    "web searches",
    "cost",
    "took",
    "mode",
  ]);
  // A replay calls nothing and spends nothing, and that zero is printed rather
  // than hidden.
  await expect(receipt.locator('[data-field="mode"] .receipt-strip__reading')).toContainText(
    "replay",
  );
  await expect(receipt.locator('[data-field="dollars"] .receipt-strip__reading')).toHaveText(
    /^\$0\.0+$/,
  );

  // The likelihoods land once, at the end, all together: every chip that read an
  // absence now reads a number at two significant figures with its range.
  await expect(page.locator(".belief-chip__reading").first()).toHaveText(/^[.>]\d/, {
    timeout: 30_000,
  });

  // Every reserved rectangle has gone: the frontier is empty once the map is
  // finished, so there is nothing left for one to stand for.
  await expect(page.locator(".skeleton-tile")).toHaveCount(0);

  // And the tile that was placed first is exactly where it was.
  expect(await firstTile.getAttribute("style")).toBe(wasAt);

  // Why the run stopped, in the engine's words for that reason.
  await expect(page.locator(".done-line")).toBeVisible();

  // Nothing anywhere on this screen is a pop-up.
  expect(await page.getByRole("dialog").count()).toBe(0);
});
