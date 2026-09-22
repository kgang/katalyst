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
 * **A growing map needs signals the stored one does not**, and they are in
 * `watching.ts` beside this file: on a stored map everything arrives at once,
 * and here the screen is *correct* and *incomplete* at the same moment for
 * minutes at a time. So every read below waits for the count it is about — this
 * many claims, this many rectangles, the receipt — rather than for the page. The
 * page also watches itself, because four of the things this file is for are true
 * of moments rather than of the end; `watching.ts` says how and why.
 *
 * Nothing here is a number typed into this file. Every figure is read off the
 * screen and compared with itself across a change, or checked for its shape.
 */

import { aDroppedFrameIsExpectedHere, expect, test } from "./theSuite.js";
import { whereTheMapCameToRest, whereTheTileSits } from "./waiting.js";
import {
  A_WHOLE_RUN,
  boxesRunningIntoEachOther,
  startWatching,
  THE_SENTENCE,
  theMapArrivedInSteps,
  waitUntilItStops,
  whatCanBeReplayed,
  whatItSaw,
} from "./watching.js";

/**
 * The row on the first screen that plays the committed recording of the one
 * sentence this file watches.
 *
 * **Two rows carry that sentence now**, since the first screen offers four ways
 * to start: *Watch the recording* plays it back for nothing, and *Run it live*
 * calls a model. So a row is named by its sentence **and** by what pressing it
 * does, which is how a reader tells the two apart as well.
 */
const THE_RECORDING_ROW = new RegExp(`${THE_SENTENCE}[\\s\\S]*Watch the recording`);

// Every test here plays a recording from beginning to end, so each needs room
// for one. It is set on the file rather than in the configuration because it is
// a fact about these tests: the stored example's tests next door are right to
// be held to a minute.
test.describe.configure({ timeout: A_WHOLE_RUN + 60_000 });

// **Every test here watches a map arrive, and a map arriving drops frames.**
// Said once for the file rather than in each test, with the whole reason, so
// that a reader who meets the browser's complaint finds the argument rather
// than a silenced warning.
test.beforeEach(() => {
  aDroppedFrameIsExpectedHere(
    "A map arriving draws its boxes in bursts, and the drawing library measures " +
      "every box it draws. When a burst is big enough the browser abandons the rest " +
      "of that frame's size notifications and says so. Measured on 2026-09-21, on " +
      "this file and with the layout thread held back and not: it comes and goes " +
      "with the size of the burst and not with anything this test injects, and at " +
      "the moment it fires the stage's and the panel's edge readings are both true " +
      "of where the boxes actually are, with no box left unpainted and no wire " +
      "missing. It is harmless here because nothing on this map waits to be " +
      "measured: `graph/toFlow.ts` declares every tile's box and both ends of every " +
      "wire, and `test_the_arrows_are_drawn_when_the_browser_drops_a_size_notification` " +
      "drops every tile's notification on purpose and the map still draws.",
  );
});

test("a map draws itself from a recording, with no model key", async ({ page }) => {
  await page.goto("/");

  const replayable = await whatCanBeReplayed(page);
  test.skip(
    replayable.length === 0,
    "This server has no committed recording to play, so there is no generation to watch.",
  );

  // **The four ways to start are all four, on a copy with no key.** Nothing has
  // gone missing and nothing is silently inert: the two that call a model are
  // drawn, cannot be pressed, and carry the reason beside them, while the two
  // free ones are untouched. The field for a sentence of your own is disabled
  // with the same sentence, because a field that takes typing and then does
  // nothing reads as a broken tool.
  await expect(page.locator(".way__name")).toHaveText([
    "Open the map",
    "Watch the recording",
    "Run it live",
    "Build the map",
  ]);
  const whyNotLive = page.locator(".way--live .launchpad__why");
  await expect(whyNotLive).toBeVisible();
  await expect(whyNotLive).toHaveText(
    /^No model key is configured, so this copy cannot call a model\./,
  );
  await expect(page.locator(".way--live button.example").first()).toBeDisabled();
  await expect(page.getByLabel("An event you think will happen")).toBeDisabled();

  // **And what a live run would cost is on screen before any press**, read from
  // the recorded run's own receipt and dated — never a figure typed into the
  // page. A recording with no receipt this engine can read prints none, so what
  // is asserted here is the shape and the date, not a number.
  await expect(page.locator(".way--live .way__measure-line").first()).toHaveText(
    /^The recorded run of .+ made \d+ model calls?, took about \d+ (seconds?|minutes?) and cost (\$[\d.]+|<\$0\.01), on \d{4}-\d{2}-\d{2}\.$/,
  );

  // From here the page watches itself, because what follows is a screen that is
  // moving and four of the claims made about it are about moments, not about the
  // end. It starts **before** the press, so the very first frame is inside the
  // record; it is read at the bottom of this test.
  await startWatching(page);

  // The card that has a recording. It sends its sentence, exactly as a reader
  // would type it — the same request a live run sends — and it is opened with
  // the keyboard, because every way into this product is usable without a mouse.
  const card = page.getByRole("button", { name: THE_RECORDING_ROW });
  await card.focus();
  await expect(card).toBeFocused();
  await page.keyboard.press("Enter");

  // **The first paint is a reserved rectangle, not a spinner.** That it appeared
  // at all is asked of the live page; **what it said is read off the record the
  // page kept of itself**, at the bottom of this test, because the words on the
  // first rectangle are true of exactly one moment — after it is drawn and
  // before the first claim replaces it with the frontier's.
  await expect(page.locator(".skeleton-tile").first()).toBeVisible();

  // **And the foot of the screen says, in words, what is being waited for.**
  // Until 2026-09-21 this line asserted the opposite — that the sentence about
  // the run carried `map-live--spoken`, the class that clipped it to a
  // one-pixel box — which is why no test in this suite could catch the thing
  // Kent saw with his own key: a screen that says nothing at all for
  // twenty-three seconds. It is visible now, it is the same element a screen
  // reader hears, and it names what is being held open.
  const runStrip = page.locator(".run-strip");
  await expect(runStrip).toBeVisible();
  const runSentence = runStrip.locator(".map-live");
  await expect(runSentence).toBeVisible();
  await expect(runSentence).toHaveAttribute("aria-live", "polite");
  await expect(runSentence).toContainText(/held open|Working on what follows from/);
  // A replay counts no seconds: it is paced by us, so the number would reset
  // twice a second and would be measuring our own pacing rather than a wait.
  await expect(runStrip).toHaveAttribute("data-state", "replay");
  await expect(page.locator(".run-strip__waited")).toHaveCount(0);

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

  // Where the first tile came to rest, before any of the others arrive. A tile
  // keeps its row while the map grows, and this is what that promise is checked
  // against — **while it is still growing**, because the map settles once at the
  // moment it stops and a reading taken after that would fail by design
  // (decision record 0024, 2026-09-21).
  const firstTile = page.locator(".react-flow__node.react-flow__node-claim").first();
  const wasAt = await whereTheTileSits(firstTile);

  // **A click on a tile while the recording is still arriving**, which is the
  // press Kent made and watched do nothing. It did select the tile and it did
  // fill the panel — at the bottom of a column that also held the refusals, the
  // receipt and *Run details*, and nothing scrolled. The claim's own words are
  // read off the tile rather than written down here, so this is a test of the
  // panel and never of the recording's copy.
  await page.locator(".react-flow__node.react-flow__node-claim").first().click();

  // The panel on the glass is the one that reads that claim out, and it says so
  // at its own head. **Which claim is read off the map's own ring** rather than
  // off the tile this test pointed at: the map pans as claims arrive, so the
  // honest question is whether the claim the map says is chosen is the claim the
  // panel is showing.
  const panel = page.locator(".dock");
  await expect(page.getByRole("tab", { name: /This claim/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const chosen = page.locator(".react-flow__node.selected").first();
  const itsWords = ((await chosen.locator(".tile__claim").textContent()) ?? "").trim();
  expect(itsWords, "the map drew a ring round a tile with no claim on it").not.toBe("");
  await expect(panel.locator(".inspector__claim")).toHaveText(itsWords);
  // And nothing about the run is stacked in front of it.
  await expect(panel).not.toContainText("Run details");

  // Back to the run, which is where the rest of this test reads. One press of
  // the name at the head of the panel, exactly as a reader does it.
  await page.getByRole("tab", { name: /The run/ }).click();
  await expect(panel).toContainText("Run details");

  // **`?` while the map is still arriving** — the one press no browser test had
  // ever made. This screen prints *Press ? for every key* under the map, and the
  // key was bound on the stored map alone, so every press in the suite was made
  // on a map that had finished. The sheet opens over the map, and Escape puts it
  // away and leaves the run running.
  const sheet = page.locator(".sheet");
  await page.keyboard.press("?");
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText("Tiles do not move");
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();

  // **And the first tile has not moved, with the map still growing under it.**
  // Taken here, with more claims on the map than there were when the reading
  // above was taken and more still on their way: that is what makes it a
  // statement about a map that went on growing rather than about one frame.
  await expect(page.locator(".tile").nth(1)).toBeVisible();
  expect(await whereTheTileSits(firstTile)).toBe(wasAt);

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

  // The map is framed once more when it stops, and settles in the same moment —
  // every pin dropped, the whole map laid out as one thing — and then it stays
  // still.
  const atRest = await whereTheMapCameToRest(page);
  expect(atRest).not.toBe("");

  // **And the settle really happened.** On this recording it moves every one of
  // the eighteen tiles, the first among them, so the tile read while the map was
  // growing is no longer where it was. If this ever reads the same place again,
  // the map stopped settling and half of decision record 0024 is gone.
  expect(await whereTheTileSits(firstTile)).not.toBe(wasAt);

  // No two boxes on the map overlap. A claim drawn on top of another is the one
  // failure a growing map makes that a finished one never does.
  expect(await boxesRunningIntoEachOther(page)).toEqual([]);

  // And not one claim's or arrow's identifier reached the map. On a generated
  // map they are twenty-six characters of the engine's own bookkeeping, and a
  // reader learns nothing from one.
  const onTheMap = (await page.locator(".map-stage").textContent()) ?? "";
  expect(onTheMap).not.toMatch(/\b01[0-9A-HJKMNP-TV-Z]{24}\b/);

  // **The run's own name is the exception, and it is deliberate.** Somebody has
  // to be able to ask for this answer again — the map, the seed and the working
  // — and the working is asked for by the generation's name. So it is on the
  // screen, in *Run details* in the panel beside the route and the seed, and it
  // is **the only identifier anywhere on it**: every twenty-six-character name
  // the page shows is that one name. It moved into the panel on 2026-09-21
  // (R16), from a strip of prose at the foot that also claimed, over an empty
  // map, that every claim on it had already arrived.
  const names =
    ((await page.locator(".map-body").textContent()) ?? "").match(
      /\b01[0-9A-HJKMNP-TV-Z]{24}\b/g,
    ) ?? [];
  expect(names.length).toBeGreaterThan(0);
  expect(new Set(names).size).toBe(1);
  await expect(page.locator(".inspector")).toContainText("Run details");
  await expect(page.locator(".inspector")).toContainText("/api/generate");

  // Why the run stopped, in the engine's words for that reason — **printed once
  // and said once, in one element.** The polite region is now the printed
  // sentence rather than a one-pixel box beside a copy of it, which is the whole
  // of what this branch changed: until 2026-09-21 this line asserted that the
  // live region carried `map-live--spoken`, so the suite was holding the fault
  // in place. What it holds now is that the sentence is visible and appears
  // exactly once on the page.
  const why = page.locator(".run-strip .map-live");
  await expect(why).toBeVisible();
  await expect(why).toHaveAttribute("aria-live", "polite");
  const stopped = ((await why.textContent()) ?? "").trim();
  expect(stopped).not.toBe("");
  const howOften = await page.evaluate(
    (sentence) => (document.body.textContent ?? "").split(sentence).length - 1,
    stopped,
  );
  expect(howOften).toBe(1);

  // The state, in one word, in front of it — and a finished run counts no
  // seconds, because nothing is being waited for.
  await expect(page.locator(".run-strip")).toHaveAttribute("data-state", "finished");
  await expect(page.locator(".run-strip__waited")).toHaveCount(0);

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
  // **The map arrived in steps, and a rectangle stood at the growing edge at
  // every one of them but the last.** The whole statement, and the reason it is
  // not written out here, are in `watching.ts` — including why it does not ask
  // for one render per claim, which is a promise about the browser's scheduling
  // that no browser makes, and where the stream's own one-at-a-time promise is
  // tested instead.
  //
  // **Continuous integration read a zero in this record, at the first claim, on
  // 2026-09-21 and nowhere else.** The layout answers on a background thread,
  // and on a machine where its first answer lost the race to the first proposal
  // the map had no place for anything — so the claim was painted at the origin,
  // where the rectangle carrying the reader's own sentence had been, and the
  // growing edge went quiet. `frontend/src/graph/onTheGlass.ts` is the rule that
  // is no longer possible under, `graph/__tests__/onTheGlass.test.ts` is the same
  // statement made without a browser, and `e2e/lateLayout.spec.ts` is this test
  // run with that thread held back on purpose.
  theMapArrivedInSteps(saw, claims);
  // **And no box was ever drawn in another box's place.** A box the layout has
  // not placed is not drawn at all — except the very first, which is a reserved
  // rectangle and never a claim: the origin is nobody's place before the layout
  // has answered anything, and the alternative is a first paint with nothing on
  // it. It used to be every box: each arriving claim sat on the hypothesis for
  // as long as the layout took to answer.
  expect(saw.everStacked).toBe(false);
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

  await page.getByRole("button", { name: THE_RECORDING_ROW }).click();
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
      // **The panel may not be there at all.** It folds away from 2026-09-22,
      // and then the stage has the whole width — which is the one change to
      // this screen's layout that nothing else on it causes, and so the one the
      // stage's own edges are most likely to be wrong about.
      const frame = document.querySelector(".dock-frame") as HTMLElement | null;
      const dock = document.querySelector(".dock") as HTMLElement | null;
      const folded = "the panel is folded away";
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
        panelSaid:
          frame === null
            ? folded
            : { above: frame.dataset.moreAbove, below: frame.dataset.moreBelow },
        panelTruly:
          dock === null
            ? folded
            : {
                above: yes(dock.scrollTop > 1),
                below: yes(dock.scrollTop + dock.clientHeight < dock.scrollHeight - 1),
              },
      };
    });

  /** Both boxes say what is beyond them, and both are right, at this window. */
  const theEdgesComeTrue = async (where: string) => {
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
          message: `the edges never came true ${where}: ${JSON.stringify(await bothReadings())}`,
        },
      )
      .toBe(true);
  };

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
    await theEdgesComeTrue(`at ${size.width}x${size.height}`);
  }

  // **And the same claim with the panel folded away** *(2026-09-22)*. Folding it
  // gives the stage 310 more pixels without the window changing at all, which is
  // a resize nothing outside this screen causes — so if the stage watched only
  // the window, the rule at its right edge would go on claiming tiles that are
  // now comfortably on the glass.
  await page.getByRole("button", { name: "Hide the panel beside the map" }).click();
  await expect(page.locator(".dock-column")).toHaveCount(0);
  for (const size of [
    { width: 1600, height: 1000 },
    { width: 900, height: 620 },
  ]) {
    await page.setViewportSize(size);
    await theEdgesComeTrue(`with the panel folded at ${size.width}x${size.height}`);
  }

  // And the panel comes back, with both boxes telling the truth again.
  await page.getByRole("button", { name: "Show the panel beside the map" }).click();
  await expect(page.locator(".dock-column")).toHaveCount(1);
  await page.setViewportSize({ width: 1600, height: 1000 });
  await theEdgesComeTrue("with the panel back");
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
  await page.getByRole("button", { name: THE_RECORDING_ROW }).click();

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

  await page.getByRole("button", { name: THE_RECORDING_ROW }).click();
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
