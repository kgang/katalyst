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
 * recordings are made against a real key by the person who holds it; until one is
 * committed under `backend/recordings/`, this test has nothing to play and says
 * that rather than failing. The moment one lands it runs, with no change here.
 *
 * **Nothing below reads a value the screen has not settled on.** The waiting is
 * `waiting.ts`'s, the same helpers the stored example's test uses: a named signal
 * every time, never a sleep, and never `innerText` — which is empty until the
 * drawing library has measured a tile, and which is how a chip that plainly read
 * `.19` was once read as nothing at all.
 *
 * **A growing map needs one signal the stored one does not**, and it is the
 * reason this file has helpers of its own: on a stored map everything arrives at
 * once, and here the screen is *correct* and *incomplete* at the same moment for
 * minutes at a time. So every read below waits for the count it is about — this
 * many claims, this many rectangles, the receipt — rather than for the page.
 *
 * Nothing here is a number typed into this file. Every figure is read off the
 * screen and compared with itself across a change, or checked for its shape.
 */

import { expect, type Page, test } from "@playwright/test";
import { whereTheMapCameToRest, whereTheTileSits } from "./waiting.js";

/** The sentence the first screen's first card carries, as a reader would type it. */
const THE_SENTENCE = "The Strait of Hormuz is going to open next week.";

/**
 * What this copy of the server says it can play back without a key.
 *
 * Asked of the server rather than read off the screen: whether this test has
 * anything to do at all is a fact about the server, and reading it off the page
 * would make the skip depend on the very screen being tested.
 */
async function whatCanBeReplayed(page: Page): Promise<{ example: string }[]> {
  const answer = await page.request.get("/api/readyz");
  const said = (await answer.json()) as { replayable?: { example: string }[] };
  return said.replayable ?? [];
}

/** What watching a whole run saw. */
interface WhatItSaw {
  /** True when, at some moment, a rectangle stood and not one claim had arrived. */
  readonly rectangleBeforeAnyClaim: boolean;
  /** The most rectangles that stood at once. */
  readonly mostRectangles: number;
  /** The most claims that were on the map at once. */
  readonly mostClaims: number;
  /**
   * How many claims were on the map the first time any likelihood appeared, and
   * how many appeared at that moment.
   *
   * Both are zero when none ever did. Together they are the statement that the
   * chips resolve **last** and **once**: the first number arrives when the map
   * is complete, and every other number arrives in the same breath.
   */
  readonly whenTheNumbersCame: { readonly claims: number; readonly numbers: number };
}

/**
 * Watch the whole run, and say what the screen did while it grew.
 *
 * **Three of the things this test is for are about a screen that is moving**, and
 * a moving screen cannot be checked by looking at it once: *a rectangle is drawn
 * before any claim*, *rectangles stand at the growing edge*, and *not one
 * likelihood is on screen until the map is finished* are each true at some
 * moments and false at others, and by the time an assertion has been written the
 * moment it was about is gone. Polling for one of them races the run; asserting
 * after it is over asserts about the wrong moment.
 *
 * So the page watches itself. Every change to the page is looked at — which is
 * every moment the screen was different — what was on it is recorded, and the
 * whole record is handed back when the receipt arrives. Nothing here sleeps, and
 * nothing here can miss a moment that a poll would have stepped over.
 *
 * It is started the instant the run is asked for and awaited at the end.
 *
 * @param page The page the map is on.
 */
function watchItGrow(page: Page): Promise<WhatItSaw> {
  return page.evaluate(
    () =>
      new Promise<WhatItSaw>((settle) => {
        let rectangleBeforeAnyClaim = false;
        let mostRectangles = 0;
        let mostClaims = 0;
        let whenTheNumbersCame = { claims: 0, numbers: 0 };

        const look = (): void => {
          const held = document.querySelectorAll(".skeleton-tile").length;
          const claims = document.querySelectorAll(".tile").length;
          // A chip says on its own face whether it is showing a number or words,
          // and that is the marker to count: every chip renders a reading, and on
          // a growing map most of them are reading an absence out.
          const numbers = document.querySelectorAll('.belief-chip[data-reading="number"]').length;

          if (held > 0 && claims === 0) {
            rectangleBeforeAnyClaim = true;
          }
          mostRectangles = Math.max(mostRectangles, held);
          mostClaims = Math.max(mostClaims, claims);
          if (numbers > 0 && whenTheNumbersCame.numbers === 0) {
            whenTheNumbersCame = { claims, numbers };
          }
          if (document.querySelector(".receipt-strip") !== null) {
            watching.disconnect();
            settle({
              rectangleBeforeAnyClaim,
              mostRectangles,
              mostClaims,
              whenTheNumbersCame,
            });
          }
        };

        const watching = new MutationObserver(look);
        watching.observe(document.body, { subtree: true, childList: true, attributes: true });
        look();
      }),
  );
}

/**
 * Wait until the run is over, which is the receipt arriving and the map saying
 * why it stopped.
 *
 * Two signals rather than one, because they are two events: the receipt is what
 * the run cost and the closing line is why it ended, and a screen that had the
 * first and not the second would be read here as finished when it is not.
 */
async function waitUntilItStops(page: Page): Promise<void> {
  await expect(page.locator(".receipt-strip")).toBeVisible({ timeout: 180_000 });
  await expect(page.locator(".done-line")).toBeVisible({ timeout: 30_000 });
  // Every rectangle goes when the likelihoods land: the set of claims still open
  // is empty by definition once the map is finished.
  await expect(page.locator(".skeleton-tile")).toHaveCount(0);
}

/** Every pair of boxes on the map that overlap. Empty is the only right answer. */
async function boxesRunningIntoEachOther(page: Page): Promise<string[]> {
  return await page.locator(".react-flow__node").evaluateAll((boxes) => {
    const seen = boxes.map((box) => ({
      id: (box as HTMLElement).dataset.id ?? "?",
      at: box.getBoundingClientRect(),
    }));
    const found: string[] = [];
    for (let one = 0; one < seen.length; one += 1) {
      for (let other = one + 1; other < seen.length; other += 1) {
        const a = seen[one];
        const b = seen[other];
        if (
          a !== undefined &&
          b !== undefined &&
          a.at.left < b.at.right &&
          b.at.left < a.at.right &&
          a.at.top < b.at.bottom &&
          b.at.top < a.at.bottom
        ) {
          found.push(`${a.id} runs into ${b.id}`);
        }
      }
    }
    return found;
  });
}

test("a map draws itself from a recording, with no model key", async ({ page }) => {
  await page.goto("/");

  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no generation to watch.",
  );

  // The first screen says what this copy is, and says only what is true. Record
  // 0012's sentence — *these four run from recordings made on <day>* — is
  // printed word for word when all four can be played and all four were made on
  // one day; anything else says how many there really are, in the same voice.
  // Either way it names a day from the server's own readiness answer, and either
  // way the field for a sentence of your own is disabled with it, because a
  // field that takes typing and then does nothing reads as a broken tool.
  const keyless = page.locator(".launchpad__keyless").first();
  await expect(keyless).toBeVisible();
  await expect(keyless).toHaveText(/^No model key configured — .*\d{4}-\d{2}-\d{2}/);
  const said = ((await keyless.textContent()) ?? "").trim();
  expect(said.includes("these four run from recordings")).toBe(replayable.length === 4);
  await expect(page.getByLabel("An event you think will happen")).toBeDisabled();

  // The card that has a recording. It sends its sentence, exactly as a reader
  // would type it — the same request a live run sends — and it is opened with
  // the keyboard, because every way into this product is usable without a mouse.
  const card = page.getByRole("button", { name: new RegExp(THE_SENTENCE) });
  await card.focus();
  await expect(card).toBeFocused();
  await page.keyboard.press("Enter");

  // From here the page watches itself, because what follows is a screen that is
  // moving and the three claims made about it are about moments, not about the
  // end. The record is read at the bottom of this test.
  const grew = watchItGrow(page);

  // **The first paint is a reserved rectangle, not a spinner**, and it carries
  // the reader's own sentence.
  await expect(page.locator(".skeleton-tile").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".skeleton-tile").first()).toContainText(THE_SENTENCE);

  // The badge says this session is a replay, from the first frame, before the
  // receipt that also says so has arrived — and it is beside the map's name
  // rather than over the map, because nothing in this product sits over the map.
  await expect(page.locator(".map-bar .replay-badge")).toBeVisible();
  await expect(page.locator(".canvas .replay-badge")).toHaveCount(0);

  // Nothing spins anywhere, at any point.
  await expect(page.getByRole("progressbar")).toHaveCount(0);

  // The map grows, and the first claim to arrive reads an absence where its
  // likelihood will go.
  await expect(page.locator(".tile").first()).toBeVisible({ timeout: 60_000 });

  // Where the first tile came to rest, before any of the others arrive. Nothing
  // already placed may move, and this is what that promise is checked against.
  const firstTile = page.locator(".react-flow__node.react-flow__node-claim").first();
  const wasAt = await whereTheTileSits(firstTile);

  // Every proposal the rules refused is on screen, in the validator's own words
  // — and a run that refused nothing says that, rather than leaving an empty
  // space a reader has to interpret. Which of the two this recording shows is
  // the recording's business: **a recording need not contain a refusal** (Kent,
  // 2026-09-20), and what is checked here is that the strip is never silent.
  await waitUntilItStops(page);
  const strip = page.locator(".refusal-strip");
  await expect(strip).toBeVisible();
  const refusals = await page.locator(".refusal-strip__row").count();
  if (refusals > 0) {
    await expect(page.locator(".refusal-strip__reason").first()).not.toBeEmpty();
  } else {
    await expect(strip).toContainText("The rules refused nothing in this run.");
  }
  // The rule's stable code is carried on the event and drawn nowhere.
  await expect(strip).not.toContainText("cycle");

  // The receipt: nine labelled readings, every one a field, none of them derived.
  const receipt = page.locator(".receipt-strip").first();
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
  // than hidden — as money, which is two places at the least.
  await expect(receipt.locator('[data-field="mode"] .receipt-strip__reading')).toContainText(
    "replay",
  );
  await expect(receipt.locator('[data-field="dollars"] .receipt-strip__reading')).toHaveText(
    /^\$0\.00$/,
  );

  // The likelihoods land once, at the end, all together: every claim on the map
  // now reads a number at two significant figures with its range, and none of
  // them reads an absence any more.
  const claims = await page.locator(".tile").count();
  await expect(page.locator('.belief-chip[data-owner="model"][data-reading="number"]')).toHaveCount(
    claims,
  );
  await expect(page.locator(".tile").first()).not.toContainText("no engine yet");

  // The map is framed once more when it stops — the one moment nothing on it is
  // moving — and then it stays still.
  const atRest = await whereTheMapCameToRest(page);
  expect(atRest).not.toBe("");

  // And the tile that was placed first is exactly where it was.
  expect(await whereTheTileSits(firstTile)).toBe(wasAt);

  // No two boxes on the map overlap. A claim drawn on top of another is the one
  // failure a growing map makes that a finished one never does.
  expect(await boxesRunningIntoEachOther(page)).toEqual([]);

  // And not one claim's or arrow's identifier reached the map or the panel
  // beside it. On a generated map they are twenty-six characters of the engine's
  // own bookkeeping, and a reader learns nothing from one.
  //
  // **The run's own name is the exception, and it is deliberate.** The line under
  // the map exists so that somebody can ask for this answer again — the map, the
  // seed, and the working — and the working is asked for by the generation's
  // name. It is printed once, there, beside the seed, and nowhere else.
  const onTheMap = (await page.locator(".map-body").textContent()) ?? "";
  expect(onTheMap).not.toMatch(/\b01[0-9A-HJKMNP-TV-Z]{24}\b/);

  // Why the run stopped, in the engine's words for that reason — **printed once**
  // and said once. The live region is still a live region and still reads the
  // whole line out; what it no longer does is print it, because the same sentence
  // in two of three stacked strips of prose is the foot of the screen repeating
  // itself.
  const why = page.locator(".done-line__why");
  await expect(why).toBeVisible();
  const stopped = ((await why.textContent()) ?? "").trim();
  expect(stopped).not.toBe("");
  await expect(page.locator(".map-live")).toHaveClass(/map-live--spoken/);
  const howOften = await page.evaluate((sentence) => {
    const times = (text: string): number => text.split(sentence).length - 1;
    const spoken = document.querySelector(".map-live")?.textContent ?? "";
    return times(document.body.textContent ?? "") - times(spoken);
  }, stopped);
  expect(howOften).toBe(1);

  // And what the screen did while it was moving, read off the record the page
  // kept of itself.
  const saw = await grew;
  // A rectangle stood before any claim had arrived: the first paint is the shape
  // of the thing being waited for, not a spinner.
  expect(saw.rectangleBeforeAnyClaim).toBe(true);
  // Rectangles stood at the growing edge all the way through.
  expect(saw.mostRectangles).toBeGreaterThan(0);
  // The claims arrived one at a time rather than all at the end.
  expect(saw.mostClaims).toBe(claims);
  // **And the chips resolved last, and once.** The first likelihood to reach the
  // screen reached it when every claim was already on the map, and every other
  // likelihood reached it in the same breath — one event, one world, every
  // number. A chip that filled in as its causes arrived would have shown four
  // numbers nobody computed, three of them answers about a map that no longer
  // existed.
  expect(saw.whenTheNumbersCame.claims).toBe(claims);
  expect(saw.whenTheNumbersCame.numbers).toBe(claims);

  // Nothing anywhere on this screen is a pop-up.
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("add a claim on a generated map declines in the server's own words", async ({ page }) => {
  await page.goto("/");

  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no map to add a claim to.",
  );

  await page.getByRole("button", { name: new RegExp(THE_SENTENCE) }).click();
  await waitUntilItStops(page);

  // A sentence no recording scripted. With no key there is nothing that could
  // draft it, and the control says so in the route's own words rather than
  // disappearing — a control that vanishes teaches a reader they imagined it.
  const field = page.getByLabel("…but this also happens");
  await expect(field).toBeVisible();
  await field.fill("…but a hurricane closes the Gulf");
  await page.getByRole("button", { name: "Draft this claim" }).click();
  const declined = page.locator('[data-answer="declined"]');
  await expect(declined).toBeVisible({ timeout: 30_000 });
  await expect(declined).toHaveText("drafting a new claim needs a model key.");

  // And the map is exactly as it was: nothing was recorded, and nothing moved.
  expect(await boxesRunningIntoEachOther(page)).toEqual([]);
  await expect(page.locator(".done-line")).toBeVisible();
});
