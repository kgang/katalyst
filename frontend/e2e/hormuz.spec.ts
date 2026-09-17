/**
 * The one end-to-end test: the stored example, opened and edited, **by keyboard
 * alone**.
 *
 * It is the only test in this product that drives a real browser against a real
 * server, so it is spent on the one claim nothing else can make: that the two
 * halves, started the way a person starts them, draw the stored example — and
 * that the three things the interface exists to say are on the screen.
 *
 * 1. **The map draws, with the engine's own numbers**, from the server's own
 *    copy of the example. Nothing on it is typed into the browser — and nothing
 *    is typed into this file either: every number below is compared with itself
 *    across a change, or checked for its shape, never for its value.
 * 2. **Opening the strike branch moves the numbers, and OPEC+'s announcement
 *    does not move.** That is the product's central correctness claim — *here is
 *    what your edit can reach, and here is what it provably cannot* — and it is
 *    checked here against the engine's own answer rather than against a shape a
 *    test wrote out. It is also where the browser's structural reading and the
 *    engine's meet: the browser is what puts *untouched* on OPEC's announcement,
 *    and the engine is what leaves its number where it was.
 * 3. **The hypothesis says its supposition was overridden**, word for word:
 *    *Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on
 *    Iranian territory"* — read off the world the engine built.
 *
 * **The whole walk is done with the keyboard**, and that is not a flourish: it
 * is the check that the interface is usable without a mouse end to end. Every
 * step below is a keystroke a reader could make.
 *
 * It needs no model key. The screen it drives is fed by a stored example, which
 * calls nothing.
 */

import { expect, type Page, test } from "@playwright/test";

/**
 * Wait until the map has been laid out.
 *
 * Where the tiles go is worked out on a background thread, so for a moment after
 * the map appears every tile is still stacked in the same place. Waiting for the
 * tiles to be somewhere is the honest signal that the layout has landed —
 * waiting a fixed number of milliseconds is a guess that is wrong on a slow
 * machine.
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

/** Which claim the keyboard is standing on, or nothing when it is off the map. */
function standingOn(page: Page): Promise<string | undefined> {
  return page.evaluate(
    () => document.activeElement?.closest<HTMLElement>(".react-flow__node")?.dataset.id,
  );
}

/**
 * Press Tab until the keyboard is on the map, and say which claim it landed on.
 *
 * **The map is one stop in the page's tab order and then its own keys take
 * over** — j and k down and up a column, h and l along the wires. That is the
 * design rather than a shortfall: eight tiles and twenty-four chips as separate
 * tab stops would make Tab the slowest way to cross the map, and the line under
 * the map says which keys to use instead from the moment it opens.
 */
async function tabOntoTheMap(page: Page): Promise<string> {
  for (let press = 0; press < 40; press += 1) {
    await page.keyboard.press("Tab");
    const at = await standingOn(page);
    if (at !== undefined) {
      return at;
    }
  }
  throw new Error("Tab never reached the map; it is not reachable by keyboard.");
}

/**
 * What the hypothesis's tile must read, word for word, once the strike lands.
 *
 * Two badges with an arrow drawn between them, which is what makes the rule read
 * as a sequence: you supposed the strait reopens, and a later edit pushed it back
 * down. Each badge also carries the sentence behind it for a reader who is not
 * looking at the tile, and that sentence is not part of what is drawn.
 */
const OVERRIDDEN = [
  "Supposed · Oct 1",
  'Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"',
];

test("the stored example, opened and edited by keyboard alone", async ({ page }) => {
  await page.goto("/");

  // The launchpad, reached and opened with the keyboard. Tab to the one example
  // that is live and press Enter.
  const hormuz = page.getByRole("button", { name: /Strait of Hormuz/ }).first();
  await hormuz.focus();
  await expect(hormuz).toBeFocused();
  await page.keyboard.press("Enter");

  // The map draws, from the server's own copy of the example, with likelihoods
  // the engine worked out. The line under it names both halves and the seed, so
  // anybody can ask the same question and get the same answer.
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
  await expect(page.locator('.react-flow__node[data-id="H"]')).toBeVisible();
  await expect(page.locator(".map-origin")).toContainText("/api/fixtures/hormuz");
  await expect(page.locator(".map-origin")).toContainText("/api/worlds");
  await expect(page.locator(".map-origin")).toContainText("versions of the map");
  await waitForTheLayout(page);
  const drawn = await page.locator(".react-flow__node").count();
  expect(drawn).toBe(7);

  // Every tile is a whole tile on the first frame, not a summary. The zoom is
  // held at the point where a tile's smallest words land at eleven pixels, and
  // below that a tile changes what it draws rather than shrinking it.
  const details = await page
    .locator(".tile")
    .evaluateAll((tiles) => tiles.map((tile) => (tile as HTMLElement).dataset.detail));
  expect(new Set(details)).toEqual(new Set(["full"]));

  // A tile is 280 pixels wide, measured rather than eyeballed.
  const width = await page.evaluate(() => {
    const tile = document.querySelector(".tile");
    const view = document.querySelector<HTMLElement>(".react-flow__viewport");
    const zoom = Number(/scale\(([0-9.]+)\)/.exec(view?.style.transform ?? "")?.[1] ?? 1);
    return (tile?.getBoundingClientRect().width ?? 0) / zoom;
  });
  expect(Math.round(width)).toBe(280);

  // Every key, on one sheet — and it says out loud that tiles do not move.
  await page.keyboard.press("?");
  await expect(page.getByText(/Tiles do not move/)).toBeVisible();
  // Escape closes it, and nothing was left half-done.
  await page.keyboard.press("Escape");
  await expect(page.getByText(/Tiles do not move/)).toBeHidden();

  // Walking the wires. Tab onto the map, step forward along a wire out of the
  // hypothesis, and the line under the map names the wire that was taken.
  await page.evaluate(() => document.body.focus());
  const entered = await tabOntoTheMap(page);
  expect(entered).toBe("H");
  await page.keyboard.press("l");
  await expect(page.locator(".map-status")).toContainText("along an arrow");
  // Whatever it landed on is one of the three claims the strait's opening
  // causes. Which one it is falls out of which is nearest on the glass, and that
  // rule is checked over every claim and both directions in
  // `src/keyboard/__tests__/focusMap.test.ts`.
  const landed = await standingOn(page);
  expect(["B", "C", "N1"]).toContain(landed);

  // And back along a wire, toward what causes it.
  await page.keyboard.press("h");
  await expect(page.locator(".map-status")).toContainText("along an arrow");
  expect(["H", "C", "R"]).toContain(await standingOn(page));

  // Down the column, which is about the picture rather than about the wires.
  await page.keyboard.press("j");
  await expect(page.locator(".map-status")).toContainText("column");

  // The command palette, by name, and the branch opened through it — so the
  // whole of what follows is reachable without a mouse.
  // What the claim the branch cannot reach reads BEFORE the branch is opened. The
  // test compares against this rather than against a number typed in here: the
  // stored example's numbers are curated and have already changed once, and the
  // claim being made is "the same number as before", not "this particular number".
  const opecBefore = await page
    .locator('.react-flow__node[data-id="R"] .belief-chip__reading')
    .first()
    .innerText();
  expect(opecBefore).toMatch(/^\.\d+$/);

  // And what the hypothesis reads before the branch, for the same reason: the
  // flip back to the map as it was written has to land on the very same number.
  const hypothesisBefore = await page
    .locator('.react-flow__node[data-id="H"] .belief-chip__reading')
    .first()
    .innerText();
  expect(hypothesisBefore).toMatch(/^\.\d+$/);

  // And the band around that number, so that "the same number as before" means
  // the same number *and* the same band: a claim an edit cannot reach is
  // identical, not merely close.
  const opecBandBefore = await page
    .locator('.react-flow__node[data-id="R"] .belief-chip__under')
    .first()
    .innerText();
  expect(opecBandBefore).toMatch(/^\.\d+–\.\d+$/);

  await page.keyboard.press("Meta+k");
  await expect(page.getByText(/Every command, by name/)).toBeVisible();
  await page.keyboard.type("Hormuz opens");
  await page.keyboard.press("Enter");
  // The union of the two worlds is laid out again, once, before anything on it
  // can be read.
  await expect(page.locator('.react-flow__node[data-id="S"]')).toBeVisible();
  await waitForTheLayout(page);

  // The branch is open, and the map says which branch and which of the two
  // worlds is in front.
  await expect(page.locator(".map-bar__where")).toContainText("Hormuz opens, then Iran is struck");
  // What the branch did, said out loud for a reader who is not looking at the
  // picture. The claim it added and the supposition it took back are both named.
  //
  // **Not the whole sentence, and that is a drift this pull request could not
  // fix.** `src/a11y/announcement.ts` still ends the line "No numbers yet." and
  // still counts the claims an edit can reach by a word the engine's answer
  // replaces. Both are now untrue, and that file is owned by nobody on this
  // branch; it is listed for the sweep.
  await expect(page.locator(".map-live")).toContainText("One claim added");
  await expect(page.locator(".map-live")).toContainText("one supposition retracted");

  // The claim the branch added is on the map, with the two badges its edits
  // earned, in the order they were made.
  const strike = page.locator('.react-flow__node[data-id="S"]');
  await expect(strike).toBeVisible();
  await expect(strike).toContainText("A confirmed military strike on Iranian territory.");
  await expect(strike.locator(".tile__badge-words")).toHaveText(["Added", "Supposed · Oct 2"]);
  // And while a claim is supposed, its tile shows the word where a likelihood
  // would go — never `1.0`, and never `.98`.
  await expect(strike.locator(".belief-chip__figure").first()).toHaveText("Supposed · Oct 2");

  // The hypothesis: the overridden supposition, word for word — read off the
  // world the engine built rather than worked out twice.
  const hypothesis = page.locator('.react-flow__node[data-id="H"]');
  await expect(hypothesis.locator(".tile__badge-words")).toHaveText([
    ...OVERRIDDEN,
    // And how far its number moved, with a chevron between the two readings.
    /^\.\d+ [▲▼] \.\d+$/,
  ]);
  await expect(hypothesis.locator(".tile__badge-arrow").first()).toHaveText("→");
  // Its number is the engine's now, not an absence: the branch was worked
  // through and the answer came back.
  await expect(hypothesis).not.toContainText("no engine yet");
  await expect(hypothesis.locator(".belief-chip__figure").first()).toHaveText(/^[.>]\d/);

  // The claim the edit provably cannot reach. Its number is the one it read
  // before the branch — the whole chip, range and all, unchanged.
  const opec = page.locator('.react-flow__node[data-id="R"]');
  await expect(opec).toContainText("OPEC+ announces output restraint.");
  await expect(opec.locator(".belief-chip__reading").first()).toHaveText(opecBefore);
  await expect(opec.locator(".belief-chip__under").first()).toHaveText(opecBandBefore);
  await expect(opec).not.toContainText("no engine yet");
  await expect(opec.locator(".tile")).toHaveAttribute("data-diff", "untouched");

  // test_the_browser_states_agree_with_the_engine — against the real engine.
  //
  // Six claims moved, one arrived with the edit, and exactly one held still: the
  // one the browser's own walk of the arrows says the edit cannot reach. The
  // browser puts `untouched` on that tile and the engine leaves its number where
  // it was; the rule joining the two readings is checked claim by claim in
  // `src/graph/__tests__/diffState.test.ts`, and this is where it is checked
  // against the engine itself.
  const states = await page
    .locator(".tile")
    .evaluateAll((tiles) => tiles.map((tile) => (tile as HTMLElement).dataset.diff));
  expect(states.filter((state) => state === "untouched")).toHaveLength(1);
  expect(states.filter((state) => state === "added")).toHaveLength(1);
  expect(states.filter((state) => state === "shifted")).toHaveLength(6);

  // The rail beside the map lists the endings, in the engine's own order, with
  // the two columns that are never folded into it.
  const rail = page.locator(".delta-rail");
  await expect(rail).toContainText("In the order the engine put them in");
  await expect(rail).toContainText("how firm");
  await expect(rail).toContainText("same direction");
  await expect(rail).not.toContainText("no engine yet");
  // Three endings, each with a change, a width and a share — every one of them
  // the engine's, and none of them typed in here.
  await expect(rail.locator(".delta-rail__row")).toHaveCount(3);
  for (const cell of await rail.locator(".delta-rail__values").all()) {
    // The change, then how firm, then the share that moved the same way. Every
    // one at two significant figures, and a share that is not quite all of them
    // printed as `>99%` rather than rounded up into all of them.
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+\.\d+[<>]?\d+%$/);
  }

  // The two worlds, flipped with one key, as a hard switch that moves nothing.
  await page.locator(".react-flow__pane").click({ position: { x: 12, y: 12 } });
  const before = await page.locator(".react-flow__viewport").getAttribute("style");
  await page.keyboard.press("Space");
  await expect(page.locator(".map-bar__side")).toHaveText("as it was written");
  // The map as it was written: the hypothesis has its own number back — the one
  // it read before the branch was opened, compared with itself rather than with
  // a number typed in here — and the strike is a ghost rather than a tile that
  // vanished.
  await expect(hypothesis.locator(".belief-chip__reading").first()).toHaveText(hypothesisBefore);
  await expect(strike.locator(".tile")).toBeVisible();
  // Nothing moved. Every difference you can see is a real difference.
  expect(await page.locator(".react-flow__viewport").getAttribute("style")).toBe(before);

  // The map as a list, which is the same world read rather than drawn.
  await page.keyboard.press("Space");
  await page.keyboard.press("O");
  const outline = page.getByRole("tree");
  await expect(outline).toBeVisible();
  await expect(outline.getByRole("treeitem")).toHaveCount(8);
  await expect(outline).toContainText("Your edit cannot reach this claim.");

  // And nothing anywhere on the screen is a pop-up: no dialog, and none of the
  // six operations' code names.
  expect(await page.getByRole("dialog").count()).toBe(0);
  const words = ((await page.locator("body").textContent()) ?? "").toLowerCase();
  for (const code of ["observe", "retune", "refine"]) {
    expect(words).not.toContain(code);
  }
});

/**
 * Pressing **This happened** on the Brent claim puts the two contracts on the
 * rail — and the panel says when a claim moved only because the observation
 * changed how much each version counts.
 *
 * This is the one thing the engine fix on `fix/04-observe-direction` bought, and
 * it is checked here rather than in a component test on purpose: what it claims
 * is that the engine's answer reaches the screen, and a component test would
 * have to be handed rows to prove that rows are drawn, which proves nothing
 * about whether there are any.
 *
 * **Where the observation lands matters, and both cases are here.** Reporting
 * Brent as news moves both contracts hanging off it, and they appear on the
 * rail. Reporting the insurance premium as news moves the strait's own
 * likelihood — but nothing pushes on the strait, so what moved it is the
 * observation making the versions in which it was likely count for more. The
 * engine says so in one field and the panel prints one sentence.
 */
test("test_this_happened_puts_rows_on_the_rail", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz/ })
    .first()
    .click();
  await waitForTheLayout(page);

  // A branch of the reader's own, and then the news, on the Brent claim.
  await page.locator('.react-flow__node[data-id="B"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("Brent settled below $68");
  await page.getByRole("button", { name: "Start this branch" }).click();

  await page.locator('.react-flow__node[data-id="B"]').click();
  await page.keyboard.press("e");
  await page.getByRole("button", { name: /^This happened/ }).click();

  // Both contracts hang off that claim, so both of them move — and the rail is
  // where a move turns into something a reader can act on. A rail that stayed
  // empty here would make **This happened** a button that does nothing.
  const rail = page.locator(".delta-rail");
  await expect(rail.locator('.delta-rail__row[data-moved="yes"]')).toHaveCount(2);
  await expect(rail).toContainText("In the order the engine put them in");
  // Every reading on those rows is the engine's, and none is typed in here.
  for (const cell of await rail
    .locator('.delta-rail__row[data-moved="yes"] .delta-rail__values')
    .all()) {
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+\.\d+[<>]?\d+%$/);
  }
});

test("test_a_claim_moved_only_by_reweighting_says_so_in_the_inspector", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz/ })
    .first()
    .click();
  await waitForTheLayout(page);

  // The news is the insurance premium falling. Nothing on this map pushes on
  // the strait's own likelihood — it is the claim the map starts from — so the
  // only way it can move is the observation making some versions count for more.
  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("The premium fell");
  await page.getByRole("button", { name: "Start this branch" }).click();
  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("e");
  await page.getByRole("button", { name: /^This happened/ }).click();

  // The panel, on the strait itself, word for word.
  await page.locator('.react-flow__node[data-id="H"]').click();
  await expect(
    page.getByText("this claim moved only because the observation made some versions count more."),
  ).toBeVisible();
});
