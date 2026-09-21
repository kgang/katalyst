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
 * How long a whole run is allowed to take before this test gives up on it.
 *
 * **A replay takes as long as its recording**, because the pacing is the
 * server's and the number of events is the file's — a twenty-proposal run is
 * four times the twenty seconds a five-proposal one takes, and neither number
 * is this test's to know. So the bound below is not a measurement and is not
 * tuned to a machine: it is generous on purpose, and exists only so that a run
 * which has genuinely stopped fails as a test rather than hanging.
 *
 * The default fifteen seconds is the wrong bound for exactly one thing in this
 * file — waiting for a run to finish — and the right one everywhere else, so it
 * is named here and used there.
 */
const A_WHOLE_RUN = 120_000;

// Every test here plays a recording from beginning to end, so each needs room
// for one. It is set on the file rather than in the configuration because it is
// a fact about these tests: the stored example's tests next door are right to
// be held to a minute.
test.describe.configure({ timeout: A_WHOLE_RUN + 60_000 });

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
  /**
   * The words on the first rectangle, read at a moment when no claim had
   * arrived — so it is the one held open for the reader's own sentence and not
   * one of the frontier's, which carry *one step on from "…"*.
   *
   * Empty when no such moment was seen.
   */
  readonly firstRectangleSaid: string;
  /** The most rectangles that stood at once. */
  readonly mostRectangles: number;
  /**
   * True when, at some moment, two boxes on the map stood in the same place.
   *
   * The place they would share is the map's origin, where the hypothesis is:
   * a box the layout has not placed yet used to be drawn there, so every
   * arriving claim sat on top of the first one until the layout answered.
   */
  readonly everStacked: boolean;
  /**
   * How many rectangles stood at the moment each claim arrived, in order.
   *
   * The growing edge saying where the map is going, step by step, rather than
   * only at the start. **The last entry is allowed to be none**: the frontier
   * empties when the last claim closes, and no rectangle may stand where
   * nothing is coming.
   */
  readonly heldWhenEachClaimArrived: readonly number[];
  /**
   * How many claims were on the map, every time that number changed.
   *
   * The sequence rather than the largest of them: the largest is whatever the
   * map ended up with, which is a fact about the end and says nothing at all
   * about how the map got there. A map that appeared all at once and a map that
   * grew claim by claim have the same largest number and completely different
   * sequences.
   */
  readonly claimsWentOn: readonly number[];
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

/** Where the page keeps what it has seen of itself. */
declare global {
  interface Window {
    theRecord?: WhatItSaw & { rectangleBeforeAnyClaim: boolean };
    stopWatching?: () => void;
  }
}

/**
 * Have the page start watching itself, before anything is asked for.
 *
 * **Four of the things this test is for are about a screen that is moving**, and
 * a moving screen cannot be checked by looking at it once: *a rectangle is drawn
 * before any claim*, *rectangles stand at the growing edge*, *the claims arrive
 * one at a time* and *not one likelihood is on screen until the map is finished*
 * are each true at some moments and false at others, and by the time an
 * assertion has been written the moment it was about is gone. Polling for one of
 * them races the run; asserting after it is over asserts about the wrong moment.
 *
 * So the page watches itself. Every change to the page is looked at — which is
 * every moment the screen was different — and what was on it is written down.
 * Nothing here sleeps, and nothing here can miss a moment that a poll would have
 * stepped over.
 *
 * **It is installed before the press**, and awaited, so that the very first
 * frame of the run is inside the record. Starting it after the press leaves the
 * one moment the first assertion is about — a rectangle standing with no claim
 * beside it — outside the window being watched, on a fast replay.
 *
 * @param page The page the map will be on.
 */
async function startWatching(page: Page): Promise<void> {
  await page.evaluate(() => {
    const record = {
      rectangleBeforeAnyClaim: false,
      firstRectangleSaid: "",
      mostRectangles: 0,
      everStacked: false,
      heldWhenEachClaimArrived: [] as number[],
      claimsWentOn: [] as number[],
      whenTheNumbersCame: { claims: 0, numbers: 0 },
    };
    window.theRecord = record;

    const look = (): void => {
      const held = document.querySelectorAll(".skeleton-tile").length;
      const claims = document.querySelectorAll(".tile").length;
      // A chip says on its own face whether it is showing a number or words,
      // and that is the marker to count: every chip renders a reading, and on
      // a growing map most of them are reading an absence out.
      const numbers = document.querySelectorAll('.belief-chip[data-reading="number"]').length;

      if (held > 0 && claims === 0) {
        record.rectangleBeforeAnyClaim = true;
        // **Read here, and never again from the live page.** What the first
        // rectangle says is true of one moment: the moment after it is drawn
        // and before the first claim replaces it with the frontier's. Reading
        // it in a second round trip asks a screen that has moved on — and on a
        // cold machine the whole run can finish in between, so the rectangle is
        // not merely different, it is gone.
        record.firstRectangleSaid = document.querySelector(".skeleton-tile")?.textContent ?? "";
      }
      record.mostRectangles = Math.max(record.mostRectangles, held);
      if (record.claimsWentOn[record.claimsWentOn.length - 1] !== claims) {
        // What the growing edge was saying at the moment this claim arrived.
        if (claims > 0) {
          record.heldWhenEachClaimArrived.push(held);
        }
        record.claimsWentOn.push(claims);
      }
      // Two boxes in one place. The place they would share is the map's origin,
      // where a box the layout has not placed yet used to be drawn.
      const places = [...document.querySelectorAll(".react-flow__node")].map(
        (one) => (one as HTMLElement).style.transform,
      );
      if (new Set(places).size !== places.length) {
        record.everStacked = true;
      }
      if (numbers > 0 && record.whenTheNumbersCame.numbers === 0) {
        record.whenTheNumbersCame = { claims, numbers };
      }
    };

    const watching = new MutationObserver(look);
    window.stopWatching = () => watching.disconnect();
    watching.observe(document.body, { subtree: true, childList: true, attributes: true });
    look();
  });
}

/**
 * Stop watching, and read back what the page saw of itself.
 *
 * **It waits for nothing.** The waiting is done by the named signals above it,
 * which is where a test that has to give up belongs: a watcher that settled on a
 * signal of its own would hang until the whole test timed out on a run that
 * broke, and the failure a reader saw would be *"test timed out"* rather than
 * *"the run said it failed"*.
 *
 * @param page The page the map is on.
 */
async function whatItSaw(page: Page): Promise<WhatItSaw> {
  return await page.evaluate(() => {
    window.stopWatching?.();
    return window.theRecord as WhatItSaw;
  });
}

/**
 * Wait until the run is over, which is the receipt arriving and the map saying
 * why it stopped.
 *
 * Two signals rather than one, because they are two events: the receipt is what
 * the run cost and the closing line is why it ended, and a screen that had the
 * first and not the second would be read here as finished when it is not.
 *
 * **This is the one wait in this file with a bound of its own**, and it is the
 * one that needs one: everything else here is waiting for the page to catch up
 * with something that has already happened, where fifteen seconds is generous.
 * This waits for a whole recording to play, which takes as long as the
 * recording is — see `A_WHOLE_RUN`.
 */
async function waitUntilItStops(page: Page): Promise<void> {
  await expect(page.locator(".receipt-strip")).toBeVisible({ timeout: A_WHOLE_RUN });
  await expect(page.locator(".done-line")).toBeVisible({ timeout: A_WHOLE_RUN });
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

  // From here the page watches itself, because what follows is a screen that is
  // moving and four of the claims made about it are about moments, not about the
  // end. It starts **before** the press, so the very first frame is inside the
  // record; it is read at the bottom of this test.
  await startWatching(page);

  // The card that has a recording. It sends its sentence, exactly as a reader
  // would type it — the same request a live run sends — and it is opened with
  // the keyboard, because every way into this product is usable without a mouse.
  const card = page.getByRole("button", { name: new RegExp(THE_SENTENCE) });
  await card.focus();
  await expect(card).toBeFocused();
  await page.keyboard.press("Enter");

  // **The first paint is a reserved rectangle, not a spinner.** That it appeared
  // at all is asked of the live page; **what it said is read off the record the
  // page kept of itself**, at the bottom of this test, because the words on the
  // first rectangle are true of exactly one moment — after it is drawn and
  // before the first claim replaces it with the frontier's.
  await expect(page.locator(".skeleton-tile").first()).toBeVisible();

  // The badge says this session is a replay, from the first frame, before the
  // receipt that also says so has arrived — and it is beside the map's name
  // rather than over the map, because nothing in this product sits over the map.
  await expect(page.locator(".map-bar .replay-badge")).toBeVisible();
  await expect(page.locator(".canvas .replay-badge")).toHaveCount(0);

  // Nothing spins anywhere, at any point.
  await expect(page.getByRole("progressbar")).toHaveCount(0);

  // The map grows, and the first claim to arrive reads an absence where its
  // likelihood will go.
  await expect(page.locator(".tile").first()).toBeVisible();

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

  // The receipt: ten labelled readings, every one a field, none of them derived.
  const receipt = page.locator(".receipt-strip").first();
  await expect(receipt.locator(".receipt-strip__label")).toHaveText([
    "model",
    "calls",
    "tokens in",
    "tokens out",
    "read from cache",
    "web searches",
    "cost",
    // A replay's clock is the replay's, and the row says so: a few seconds of
    // paced playback beside a map that took eleven minutes to make.
    "the replay took",
    "how hard the model tried",
    "mode",
  ]);
  // How hard the model tried is a plain word, the one the service takes. Two
  // maps of the same sentence at the same seed can differ because of it alone,
  // so it is a reading rather than a footnote.
  await expect(receipt.locator('[data-field="effort"] .receipt-strip__reading')).toHaveText(
    /^(default|low|medium|high|xhigh|max)$/,
  );
  // A replay calls nothing and spends nothing, and that zero is printed rather
  // than hidden — as money, which has two places, and as an exact zero rather
  // than as the bound a run that spent less than a penny would print.
  await expect(receipt.locator('[data-field="mode"] .receipt-strip__reading')).toContainText(
    "replay",
  );
  await expect(receipt.locator('[data-field="dollars"] .receipt-strip__reading')).toHaveText(
    "$0.00",
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

  // The map says where it is cut. A ten-claim map framed so its tiles stay
  // readable does not fit the stage, and a map that is cut with nothing saying
  // so is read as a map that ends there — which for a causal map is the worst
  // thing it can be read as. The same two-pixel rule the panel beside it uses,
  // measured by the stage about itself.
  const stage = page.locator(".canvas");
  const edges = await stage.evaluate((it) => ({
    left: (it as HTMLElement).dataset.moreLeft,
    right: (it as HTMLElement).dataset.moreRight,
    above: (it as HTMLElement).dataset.moreAbove,
    below: (it as HTMLElement).dataset.moreBelow,
  }));
  // Every edge has an answer — never a missing attribute, which would draw
  // nothing and mean nothing.
  expect(Object.values(edges).every((one) => one === "yes" || one === "no")).toBe(true);
  // And what it says is true of where the tiles actually are, checked against
  // the page rather than against a number written here.
  const really = await page.evaluate(() => {
    const room = document.querySelector(".canvas")?.getBoundingClientRect();
    const boxes = [...document.querySelectorAll(".react-flow__node")].map((one) =>
      one.getBoundingClientRect(),
    );
    if (room === undefined || boxes.length === 0) {
      return null;
    }
    return {
      left: boxes.some((at) => at.left < room.left - 1) ? "yes" : "no",
      right: boxes.some((at) => at.right > room.right + 1) ? "yes" : "no",
      above: boxes.some((at) => at.top < room.top - 1) ? "yes" : "no",
      below: boxes.some((at) => at.bottom > room.bottom + 1) ? "yes" : "no",
    };
  });
  expect(edges).toEqual(really);

  // And what the screen did while it was moving, read off the record the page
  // kept of itself.
  const saw = await whatItSaw(page);
  // A rectangle stood before any claim had arrived: the first paint is the shape
  // of the thing being waited for, not a spinner — and it carried the reader's
  // own sentence, which is what makes it the shape of *this* wait rather than of
  // waiting in general.
  expect(saw.rectangleBeforeAnyClaim).toBe(true);
  expect(saw.firstRectangleSaid).toContain(THE_SENTENCE);
  // **Rectangles stood at the growing edge all the way through** — which is
  // what this now says, rather than "at some point there was one". A step with
  // no rectangle is a map that has stopped saying where it is going.
  //
  // The last claim is the exception and the only one: the frontier empties when
  // it closes, and no rectangle may stand where nothing is coming.
  expect(saw.mostRectangles).toBeGreaterThan(0);
  expect(saw.heldWhenEachClaimArrived.length).toBe(claims);
  for (const [step, held] of saw.heldWhenEachClaimArrived.slice(0, -1).entries()) {
    expect(held, `no rectangle stood when claim ${step + 1} arrived`).toBeGreaterThan(0);
  }
  // **And no box was ever drawn in another box's place.** A box the layout has
  // not placed is not drawn at all — except the very first, where the origin is
  // nobody's place and the alternative is a first paint with nothing on it. It
  // used to be every box: each arriving claim sat on the hypothesis for as long
  // as the layout took to answer.
  expect(saw.everStacked).toBe(false);
  // **The claims arrived one at a time.** The count went 0, 1, 2, … and reached
  // the number on screen by rising by exactly one each time: a map that appeared
  // all at once would have gone 0 and then that number, and a map that redrew
  // itself would have gone down somewhere. Comparing the largest count with the
  // final count says nothing at all — they are the same number by definition.
  expect(saw.claimsWentOn[0]).toBe(0);
  expect(saw.claimsWentOn[saw.claimsWentOn.length - 1]).toBe(claims);
  expect(saw.claimsWentOn).toEqual(saw.claimsWentOn.map((_, step) => step));
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

test("the edges of the stage and the panel stay true when the window changes", async ({ page }) => {
  await page.goto("/");
  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no map to resize around.",
  );

  await page.getByRole("button", { name: new RegExp(THE_SENTENCE) }).click();
  await waitUntilItStops(page);

  /**
   * What the two boxes say about their edges, and what is actually beyond them.
   *
   * Both are read off the page in the same breath, so the comparison is about
   * one moment rather than about two.
   */
  const bothReadings = () =>
    page.evaluate(() => {
      const stage = document.querySelector(".canvas") as HTMLElement;
      const room = stage.getBoundingClientRect();
      const boxes = [...document.querySelectorAll(".react-flow__node")].map((one) =>
        one.getBoundingClientRect(),
      );
      const yes = (it: boolean) => (it ? "yes" : "no");
      const frame = document.querySelector(".dock-frame") as HTMLElement;
      const dock = document.querySelector(".dock") as HTMLElement;
      return {
        stageSaid: {
          left: stage.dataset.moreLeft,
          right: stage.dataset.moreRight,
          above: stage.dataset.moreAbove,
          below: stage.dataset.moreBelow,
        },
        stageTruly: {
          left: yes(boxes.some((at) => at.left < room.left - 1)),
          right: yes(boxes.some((at) => at.right > room.right + 1)),
          above: yes(boxes.some((at) => at.top < room.top - 1)),
          below: yes(boxes.some((at) => at.bottom > room.bottom + 1)),
        },
        panelSaid: { above: frame.dataset.moreAbove, below: frame.dataset.moreBelow },
        panelTruly: {
          above: yes(dock.scrollTop > 1),
          below: yes(dock.scrollTop + dock.clientHeight < dock.scrollHeight - 1),
        },
      };
    });

  // **Five windows, including the one everything was designed against.** The
  // rule is *at each edge that has content beyond it and at no edge that has
  // not* (INV-workbench.77), and a window is neither a pan nor a layout — so
  // nothing but the stage watching its own size would ever hear about one.
  // Bigger: the whole map comes onto the glass and the rule below must go.
  // Smaller: tiles go off the right and a rule must appear.
  for (const size of [
    { width: 1600, height: 1000 },
    { width: 2000, height: 1400 },
    { width: 900, height: 620 },
    { width: 1200, height: 700 },
    { width: 700, height: 500 },
    { width: 1600, height: 1000 },
  ]) {
    await page.setViewportSize(size);
    // **Waited for, not slept through, and the wait is the statement.** The
    // edges are settled exactly when what the two boxes say is what is so; a
    // fixed pause would be a guess about how long a resize takes on whatever
    // machine this runs on.
    await expect
      .poll(
        async () => {
          const now = await bothReadings();
          return (
            JSON.stringify(now.stageSaid) === JSON.stringify(now.stageTruly) &&
            JSON.stringify(now.panelSaid) === JSON.stringify(now.panelTruly)
          );
        },
        {
          timeout: 15_000,
          message: `the edges never came true at ${size.width}x${size.height}: ${JSON.stringify(
            await bothReadings(),
          )}`,
        },
      )
      .toBe(true);
  }
});

test("a run that was cut still offers its working", async ({ page }) => {
  await page.goto("/");
  const replayable = await whatCanBeReplayed(page);
  test.skip(replayable.length === 0, "This server has no committed recording to cut short.");

  // The first six events of the real run, and then the body simply ends: no
  // `done`, no `failed`, no receipt — which is a restarted server, a proxy
  // giving up on an idle connection, a laptop asleep in a ten-minute run.
  const whole = await (
    await page.request.post("/api/generate", {
      headers: { "content-type": "application/json" },
      data: { hypothesis: THE_SENTENCE },
    })
  ).text();
  const cut = whole
    .split(/\r?\n\r?\n/)
    .filter((block) => block.trim() !== "")
    .slice(0, 6)
    .map((block) => `${block}\n\n`)
    .join("");
  await page.route("**/api/generate", async (route) => {
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: cut,
    });
  });

  await page.reload();
  await page.getByRole("button", { name: new RegExp(THE_SENTENCE) }).click();

  // It says the stream ended, and it offers to run it again with the price on
  // the control — this copy has no key, so playing it again spends nothing.
  await expect(page.locator('.done-line[data-kind="ended_early"]')).toBeVisible();
  await expect(page.getByRole("button", { name: /Play it again/ })).toBeVisible();
  // No rectangle stands where nothing is coming.
  await expect(page.locator(".skeleton-tile")).toHaveCount(0);
  // And the claims that did arrive are on the map — waited for rather than
  // counted on the spot, because a box is drawn when the layout has placed it
  // and the layout answers on a thread of its own.
  await expect(page.locator(".tile").first()).toBeVisible();

  // **The working is reachable**, which is the whole point: a cut run has no
  // receipt and no refusal, so before this there was no way in at all — while
  // the screen had already fetched the one document that says how far it got.
  const read = page.getByRole("button", { name: /Read the working of this run/ });
  await expect(read).toBeVisible();
  await read.click();
  await expect(page.locator(".inspector__claim")).toHaveText("This generation");

  // No box was ever drawn in another box's place while all that happened.
  expect(await boxesRunningIntoEachOther(page)).toEqual([]);
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
