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

import { expect, type Locator, type Page, test } from "@playwright/test";

/*
 * ---- Waiting, and why every read below does it --------------------------
 *
 * **Nothing here reads a value the page has not settled on.** This test drives
 * two servers, a background layout thread and a drawing library that measures
 * its own boxes, so at any moment the screen may be showing the answer to the
 * question before last. Every read goes through one of the helpers below, and
 * each of them waits for a *named* signal rather than for a number of
 * milliseconds — a sleep is a guess, and the build machine is about two and a
 * half times slower than the machine it was guessed on.
 *
 * Two traps in particular are what these exist for.
 *
 * **`innerText` is not `textContent`.** `innerText` is what the page *renders*,
 * so it comes back empty for a tile the drawing library has not measured yet —
 * which is how a chip that plainly reads `.19` was read as `""`. Nothing below
 * calls `innerText`; the reads wait for the element to be visible and then take
 * `textContent`, which is the same string by then.
 *
 * **The old numbers stay on screen until the new ones arrive.** An edit asks
 * for a whole new world and a whole new difference, and until they come back
 * the map is still drawing the previous answer. So waiting for *a* number is
 * not waiting: each edit below waits for the thing that **changes** — the
 * sentence the map says out loud for that edit — before anything is read.
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
async function waitForTheLayout(page: Page, tiles: number): Promise<void> {
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
async function readWhenReady(where: Locator, shape: RegExp): Promise<string> {
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
async function waitForTheBranch(page: Page, branch: string, tiles: number): Promise<void> {
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
 * @param sentence The whole line, word for word.
 */
async function waitForTheAnswer(page: Page, sentence: string): Promise<void> {
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
async function whereTheMapCameToRest(page: Page): Promise<string> {
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
function standingOn(page: Page): Promise<string | undefined> {
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
async function standOn(page: Page, claim: string): Promise<void> {
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
 * Flip to one of the two maps with the keyboard, the way a reader does.
 *
 * The press is retried rather than assumed, and what is being retried is the
 * keyboard's place: a re-render landing between standing on the map and
 * pressing the key takes the keyboard off the map, and a map key pressed off
 * the map is *correctly* ignored. It presses only while the wrong map is in
 * front, so it can never press twice for one flip and land back where it
 * started.
 *
 * @param page The page the map is on.
 * @param side Which of the two maps should be in front afterwards, in the words
 *   the map bar uses for it.
 */
async function flipTo(page: Page, side: "as it was written" | "with your edits"): Promise<void> {
  const shown = page.locator(".map-bar__side");
  const inFront = async () => ((await shown.textContent()) ?? "").trim();
  await expect
    .poll(
      async () => {
        if ((await inFront()) === side) {
          return side;
        }
        await page.locator('.react-flow__node[data-id="H"]').focus();
        if ((await standingOn(page)) !== "H") {
          return await inFront();
        }
        await page.keyboard.press("Space");
        // A moment for the press to land before it is called lost, so that a
        // slow render is never mistaken for a keystroke that went nowhere.
        await expect(shown)
          .toHaveText(side, { timeout: 2_000 })
          .catch(() => undefined);
        return await inFront();
      },
      { timeout: 30_000, message: `the map never flipped to "${side}"` },
    )
    .toBe(side);
}

/**
 * Wait until the keyboard has landed on one of these claims, and say which.
 *
 * Moving along a wire changes two things — what the line under the map says and
 * where the keyboard is — and they are not written in the same breath. Reading
 * the second the moment the first appears is reading one keystroke early.
 *
 * @param page The page the map is on.
 * @param any The claims this step is allowed to land on.
 */
async function landedOn(page: Page, any: readonly string[]): Promise<string> {
  await expect
    .poll(() => standingOn(page) as Promise<string>, {
      timeout: 15_000,
      message: `the keyboard never landed on one of ${any.join(", ")}`,
    })
    .toMatch(new RegExp(`^(${any.join("|")})$`));
  return (await standingOn(page)) as string;
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
  await waitForTheLayout(page, 7);

  // Every tile is a whole tile on the first frame, not a summary. The zoom is
  // held at the point where a tile's smallest words land at eleven pixels, and
  // below that a tile changes what it draws rather than shrinking it. Counted
  // rather than read into a list, so that "all seven of them" is what is waited
  // for rather than what happened to be there when the list was taken.
  await expect(page.locator('.tile[data-detail="full"]')).toHaveCount(7);
  await expect(page.locator(".tile")).toHaveCount(7);

  // A tile is 280 pixels wide, measured rather than eyeballed — and measured
  // only once the framing animation has stopped, because a width read against a
  // zoom that is still changing is two measurements of different moments.
  await whereTheMapCameToRest(page);
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const tile = document.querySelector(".tile");
          const view = document.querySelector<HTMLElement>(".react-flow__viewport");
          const zoom = Number(/scale\(([0-9.]+)\)/.exec(view?.style.transform ?? "")?.[1] ?? 1);
          return Math.round((tile?.getBoundingClientRect().width ?? 0) / zoom);
        }),
      { timeout: 15_000, message: "a tile was never 280 wide" },
    )
    .toBe(280);

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
  await landedOn(page, ["B", "C", "N1"]);

  // And back along a wire, toward what causes it.
  await page.keyboard.press("h");
  await expect(page.locator(".map-status")).toContainText("along an arrow");
  await landedOn(page, ["H", "C", "R"]);

  await test.step("test_two_keys_in_one_frame_both_count", async () => {
    // The two steps again, pressed one after the other with nothing waited for
    // in between — which is what a reader typing quickly does, and what a
    // machine slow enough to deliver two keydowns in one task does to any
    // reader at all. **The second key has to start from where the first one
    // left the keyboard**, not from where it was before that: the page moves
    // the keyboard inside the keystroke, and a handler that believed the value
    // it was rendered with worked both keys out from the claim before the
    // first. Whichever of the three this walk is standing on, forward and then
    // back lands on a claim that causes something.
    await page.keyboard.press("l");
    await page.keyboard.press("h");
    await landedOn(page, ["H", "C", "R"]);
    // And the map never said this about a claim that has causes.
    await expect(page.locator(".map-status")).not.toContainText("nothing causes this claim");
  });

  await test.step("test_the_palette_takes_the_keyboard_and_the_map_leaves_it_alone", async () => {
    // **A move, and the palette opened in the same breath.** Putting the
    // keyboard on a tile is done twice — once now, and once after the drawing
    // library has rebuilt that tile's element — and the second landing waits on
    // animation frames. Frames are not a clock: a browser produces none while
    // nothing on the page is changing, so a landing scheduled by this move can
    // run at whatever frame comes next, and the frame that comes next is the
    // one the palette's arrival causes. A map that landed then would take the
    // keyboard straight out of the palette's field, and every letter the reader
    // typed would be read as a map shortcut while the palette sat there looking
    // open and doing nothing at all.
    //
    // Nothing is waited for between the two presses, which is what a reader
    // reaching for the palette does and what any reader at all gets on a
    // machine slow enough to deliver both keys inside one task.
    const before = await landedOn(page, ["H", "C", "R"]);
    await page.keyboard.press("l");
    await page.keyboard.press("Meta+k");
    await expect(page.getByText(/Every command, by name/)).toBeVisible();

    // Four letters, and every one of them is also a key on the map: o swaps the
    // panel for the map as a list, e opens the six things you can do to a
    // claim, p says where the panel is. So the field holding them and the map
    // holding still are the same statement made twice.
    const field = page.getByLabel("Type a few letters of a command");
    // Asked three times, because the map can take the keyboard back at any of
    // the frames in between: the palette has it, it still has it after four
    // keystrokes, and the four keystrokes are in it.
    await expect(field).toBeFocused();
    await page.keyboard.type("open");
    await expect(field).toHaveValue("open");
    await expect(field).toBeFocused();
    await expect(page.locator(".outline")).toHaveCount(0);
    await expect(page.locator(".intervene")).toHaveCount(0);

    await page.keyboard.press("Escape");
    await expect(page.getByText(/Every command, by name/)).toHaveCount(0);
    // And the keyboard goes back where this step found it, so what follows
    // walks from the same place it always did.
    await standOn(page, before);
  });

  // Down the column, which is about the picture rather than about the wires.
  await page.keyboard.press("j");
  await expect(page.locator(".map-status")).toContainText("column");

  // The command palette, by name, and the branch opened through it — so the
  // whole of what follows is reachable without a mouse.
  // What the claim the branch cannot reach reads BEFORE the branch is opened. The
  // test compares against this rather than against a number typed in here: the
  // stored example's numbers are curated and have already changed once, and the
  // claim being made is "the same number as before", not "this particular number".
  // Each of the three waits for the engine's answer in the shape it arrives in
  // before it is read. The map draws at once and the numbers come a moment
  // later, and a tile the drawing library has not measured renders as nothing at
  // all — so a value taken the instant the tile exists is sometimes taken from a
  // tile that is not showing anything yet.
  const opecBefore = await readWhenReady(
    page.locator('.react-flow__node[data-id="R"] .belief-chip__reading').first(),
    /^\.\d+$/,
  );

  // And what the hypothesis reads before the branch, for the same reason: the
  // flip back to the map as it was written has to land on the very same number.
  const hypothesisBefore = await readWhenReady(
    page.locator('.react-flow__node[data-id="H"] .belief-chip__reading').first(),
    /^\.\d+$/,
  );

  // And the band around that number, so that "the same number as before" means
  // the same number *and* the same band: a claim an edit cannot reach is
  // identical, not merely close.
  const opecBandBefore = await readWhenReady(
    page.locator('.react-flow__node[data-id="R"] .belief-chip__under').first(),
    /^\.\d+–\.\d+$/,
  );

  await page.keyboard.press("Meta+k");
  await expect(page.getByText(/Every command, by name/)).toBeVisible();
  await page.keyboard.type("Hormuz opens");
  await page.keyboard.press("Enter");
  // The union of the two worlds is laid out again, once, before anything on it
  // can be read — eight tiles now, each in a place of its own.
  await expect(page.locator('.react-flow__node[data-id="S"]')).toBeVisible();
  await waitForTheBranch(page, "Hormuz opens, then Iran is struck", 8);
  // What the branch did, said out loud for a reader who is not looking at the
  // picture — the whole sentence, against the real engine. How many claims moved
  // is the engine's own count of the claims it called shifted, which is the same
  // six the tiles are checked for below; a reader who cannot see the map and a
  // reader who can are told the same thing.
  await expect(page.locator(".map-live")).toHaveText(
    "Branch created. One claim added, six claims moved, one supposition retracted.",
  );

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
  await test.step("test_the_fully_separated_claim_does_not_change", async () => {
    await expect(opec).toContainText("OPEC+ announces output restraint.");
    await expect(opec.locator(".belief-chip__reading").first()).toHaveText(opecBefore);
    await expect(opec.locator(".belief-chip__under").first()).toHaveText(opecBandBefore);
    await expect(opec).not.toContainText("no engine yet");
    await expect(opec.locator(".tile")).toHaveAttribute("data-diff", "untouched");
  });

  // test_the_browser_states_agree_with_the_engine — against the real engine.
  //
  // Six claims moved, one arrived with the edit, and exactly one held still: the
  // one the browser's own walk of the arrows says the edit cannot reach. The
  // browser puts `untouched` on that tile and the engine leaves its number where
  // it was; the rule joining the two readings is checked claim by claim in
  // `src/graph/__tests__/diffState.test.ts`, and this is where it is checked
  // against the engine itself.
  await expect(page.locator('.tile[data-diff="untouched"]')).toHaveCount(1);
  await expect(page.locator('.tile[data-diff="added"]')).toHaveCount(1);
  await expect(page.locator('.tile[data-diff="shifted"]')).toHaveCount(6);
  // And those are all of them, so no tile is in a fourth state unaccounted for.
  await expect(page.locator(".tile")).toHaveCount(8);

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
  // Counted before they are walked: a list taken while the rows are still
  // arriving is a list that agrees with itself and says nothing.
  await expect(rail.locator(".delta-rail__values")).toHaveCount(3);
  for (const cell of await rail.locator(".delta-rail__values").all()) {
    // The change, then how firm, then the share that moved the same way. Every
    // one at two significant figures, and a share that is not quite all of them
    // printed as `>99%` rather than rounded up into all of them.
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+\.\d+[<>]?\d+%$/);
  }

  // The two worlds, flipped with one key, as a hard switch that moves nothing.
  await page.locator(".react-flow__pane").click({ position: { x: 12, y: 12 } });
  // On the map first, and the map at rest, before its place is written down.
  // Space is a map key, and a map key pressed while the keyboard is on a button
  // belongs to the button — which is the rule in `useMapKeys` rather than a
  // shortfall, and the reason this step used to fail about once in a hundred.
  await standOn(page, "H");
  const before = await whereTheMapCameToRest(page);
  await flipTo(page, "as it was written");
  // The map as it was written: the hypothesis has its own number back — the one
  // it read before the branch was opened, compared with itself rather than with
  // a number typed in here — and the strike is a ghost rather than a tile that
  // vanished.
  await expect(hypothesis.locator(".belief-chip__reading").first()).toHaveText(hypothesisBefore);
  await expect(strike.locator(".tile")).toBeVisible();
  // Nothing moved. Every difference you can see is a real difference — and this
  // is asserted rather than read, so a transform still being written when the
  // switch lands is waited out rather than caught half-done.
  await expect(page.locator(".react-flow__viewport")).toHaveAttribute("style", before);

  // The map as a list, which is the same world read rather than drawn.
  await flipTo(page, "with your edits");
  await page.keyboard.press("O");
  const outline = page.getByRole("tree");
  await expect(outline).toBeVisible();
  await expect(outline.getByRole("treeitem")).toHaveCount(8);
  await expect(outline).toContainText("Your edit cannot reach this claim.");

  // And nothing anywhere on the screen is a pop-up: no dialog, and none of the
  // six operations' code names.
  await expect(page.getByRole("dialog")).toHaveCount(0);
  for (const code of ["observe", "retune", "refine"]) {
    await expect(page.locator("body")).not.toContainText(new RegExp(code, "i"));
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
  await waitForTheLayout(page, 7);

  // A branch of the reader's own, and then the news, on the Brent claim.
  await page.locator('.react-flow__node[data-id="B"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("Brent settled below $68");
  await page.getByRole("button", { name: "Start this branch" }).click();
  // The branch is folded on and the map is laid out again before the claim is
  // pointed at, because pointing at a tile that is still being placed points at
  // wherever it used to be.
  await waitForTheBranch(page, "Brent settled below $68", 7);
  await waitForTheAnswer(page, "Branch created. No claims moved.");

  await page.locator('.react-flow__node[data-id="B"]').click();
  await page.keyboard.press("e");
  // The six things you can do, and the panel says which claim it will do them
  // to — so the news below cannot land on a claim the pointer missed.
  await expect(page.locator(".intervene")).toContainText(
    "Brent crude settles below $68 for five sessions.",
  );
  await page.getByRole("button", { name: /^This happened/ }).click();

  // **The edit is finished when the map says what it did.** Until the new world
  // and the new difference come back the rail is still showing the answer to
  // the question before this one, and "no claims moved" is a different sentence
  // from this one — so waiting for it is waiting rather than passing.
  await waitForTheAnswer(page, "Branch created. Three claims moved.");
  await waitForTheLayout(page, 7);

  // Both contracts hang off that claim, so both of them move — and the rail is
  // where a move turns into something a reader can act on. A rail that stayed
  // empty here would make **This happened** a button that does nothing.
  const rail = page.locator(".delta-rail");
  await expect(rail.locator('.delta-rail__row[data-moved="yes"]')).toHaveCount(2);
  await expect(rail).toContainText("In the order the engine put them in");
  // Every reading on those rows is the engine's, and none is typed in here.
  const moved = rail.locator('.delta-rail__row[data-moved="yes"] .delta-rail__values');
  await expect(moved).toHaveCount(2);
  for (const cell of await moved.all()) {
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+\.\d+[<>]?\d+%$/);
  }
});

test("test_a_claim_moved_only_by_reweighting_says_so_in_the_inspector", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz/ })
    .first()
    .click();
  await waitForTheLayout(page, 7);

  // The news is the insurance premium falling. Nothing on this map pushes on
  // the strait's own likelihood — it is the claim the map starts from — so the
  // only way it can move is the observation making some versions count for more.
  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("The premium fell");
  await page.getByRole("button", { name: "Start this branch" }).click();
  await waitForTheBranch(page, "The premium fell", 7);
  await waitForTheAnswer(page, "Branch created. No claims moved.");

  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("e");
  await expect(page.locator(".intervene")).toContainText(
    "Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.",
  );
  await page.getByRole("button", { name: /^This happened/ }).click();

  // The edit is finished when the map says what it did, and not before.
  await waitForTheAnswer(page, "Branch created. Two claims moved.");
  await waitForTheLayout(page, 7);

  // The panel, on the strait itself, word for word.
  await page.locator('.react-flow__node[data-id="H"]').click();
  await expect(
    page.getByText("this claim moved only because the observation made some versions count more."),
  ).toBeVisible();

  await test.step("test_the_tile_says_why_the_engine_reports_no_change", async () => {
    // The strait's own tile, on the same branch. The engine names one cause of
    // an unmoved number and only one — the observation changing how much each
    // version counts — and where it names it, the tile says it.
    const strait = page.locator(
      '.react-flow__node[data-id="H"] .tile__badge[data-badge="movement"]',
    );
    await expect(strait.locator(".tile__badge-words")).toHaveText("no change");
    await expect(strait).toHaveAttribute(
      "title",
      /inside every version of the map its number held still/,
    );

    // And the talks, which plainly did move and still came out unchanged
    // because the versions of the map did not agree on which way. **This is the
    // case the sentence was wrong about.** The tile used to tell this reader
    // that the number "did not move by enough to report" while the engine's own
    // two readings, a click away, were two points apart.
    const talks = page.locator(
      '.react-flow__node[data-id="N1"] .tile__badge[data-badge="movement"]',
    );
    await expect(talks.locator(".tile__badge-words")).toHaveText("no change");
    // Asserted on the element rather than read off it, so that a sentence still
    // being written when the badge's words land is waited out.
    await expect(talks).toHaveAttribute(
      "title",
      /reports no change on this claim: it read \.\d+ then \.\d+/,
    );
    await expect(talks).toHaveAttribute("title", /of the versions of the map moved the same way/);
    await expect(talks).toHaveAttribute(
      "title",
      /Which of the two it was is the engine's to say, and it does not say\./,
    );
    // It names no half of the engine's test, because the engine names none.
    await expect(talks).not.toHaveAttribute("title", /did not move by enough/);
  });
});
