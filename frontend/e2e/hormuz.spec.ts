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
 * 3. **The supposition the reader made still stands, and the *state* it was
 *    holding up falls.** The hypothesis reads *Supposed · Oct 1* where its
 *    likelihood would be, with no second badge behind it: nothing takes a
 *    supposition back (decision record 0017). What the strike ends is the claim
 *    that the strait *stays open* — a state, which is the only kind of claim a
 *    `sustain` arrow can switch off — and that claim's number falls. Both facts
 *    are read off the world the engine built.
 *
 * **The whole walk is done with the keyboard**, and that is not a flourish: it
 * is the check that the interface is usable without a mouse end to end. Every
 * step below is a keystroke a reader could make.
 *
 * It needs no model key. The screen it drives is fed by a stored example, which
 * calls nothing.
 */

import { expect, type Page } from "@playwright/test";
import { test } from "./theSuite.js";
import {
  readWhenReady,
  standingOn,
  standOn,
  waitForTheAnswer,
  waitForTheBranch,
  waitForTheLayout,
  whereTheMapCameToRest,
} from "./waiting.js";

/**
 * Every arrow the stored example has, on the glass, by name.
 *
 * **A causal map is its arrows.** A map that drew every claim and none of the
 * arrows between them is the wrong picture of the argument, and a silent one —
 * every tile is there, in its place, and nothing says how they are joined. The
 * suite met exactly that in the wild. On the stored example the only arrow ever
 * checked for was the one an edit is made to, so the other seven could have gone
 * without a word.
 *
 * By name rather than by count, because a map drawing eight of the ten is the
 * same fault arriving quieter.
 *
 * **Ten, not eight** *(2026-09-22)*. The curated map gained the claim that the
 * strait *stays open* — a state, sitting between the strait reopening and the
 * insurance premium — so the one arrow `H->C` became the two arrows `H->O` and
 * `O->C`, and it gained a contract on the reopening itself, `H->M3`.
 *
 * @param page The page the map is on.
 */
async function everyArrowIsDrawn(page: Page): Promise<void> {
  const ten = ["B->M1", "B->M2", "B->R", "C->B", "H->B", "H->M3", "H->N1", "H->O", "O->C", "R->B"];
  await expect(page.locator(".react-flow__edge")).toHaveCount(ten.length);
  await expect
    .poll(() =>
      page
        .locator(".react-flow__edge")
        .evaluateAll((wires) => wires.map((wire) => (wire as HTMLElement).dataset.id).sort()),
    )
    .toEqual(ten);
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
 * design rather than a shortfall: nine tiles and their chips as separate
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
 * Point at one arrow and open the six things you can do to it.
 *
 * **Two ways in, both retried, and the failure says which one got how far.** An
 * arrow is a curve: the middle of the box around it is usually a tile, and part
 * of the curve itself runs under one, so the spot to point at has to be looked
 * for rather than worked out. And the keyboard's way in — stand on the arrow
 * and press Enter — needs the standing to have taken, which a rebuild of the
 * arrow's element undoes. Either alone left this step failing about once in a
 * hundred and sixty runs; what is retried is the asking, and what is waited for
 * is the panel naming the arrow.
 *
 * @param page The page the map is on.
 * @param id The arrow, by the identifier it carries on the glass.
 */
async function openThePanelOnTheArrow(page: Page, id: string): Promise<void> {
  const arrow = page.locator(`.react-flow__edge[data-id="${id}"]`);
  const panel = page.locator(".intervene");
  const tried: string[] = [];
  // **The arrow is on the glass, or this fails here and says which arrow.**
  // This used to wait the missing arrow out and report what each attempt saw,
  // because the map really did lose one under load — a tile whose ports the
  // drawing library never measured has no arrows drawn to it. The ports are
  // declared rather than measured now, so the waiting is gone: if it ever comes
  // back, this is where it says so, by name, in fifteen seconds rather than
  // forty-five.
  await expect(arrow).toHaveCount(1);

  const until = Date.now() + 45_000;
  while (Date.now() < until) {
    const on = await arrow.evaluate((group, which) => {
      const line = group.querySelector("path") as SVGPathElement | null;
      const toTheScreen = line?.getScreenCTM();
      if (line === null || toTheScreen === null || toTheScreen === undefined) {
        return null;
      }
      const total = line.getTotalLength();
      for (let step = 1; step < 40; step += 1) {
        const along = line.getPointAtLength((total * step) / 40);
        const point = new DOMPoint(along.x, along.y).matrixTransform(toTheScreen);
        const under = document.elementFromPoint(point.x, point.y);
        if (under?.closest(".react-flow__edge")?.getAttribute("data-id") === which) {
          return { x: point.x, y: point.y };
        }
      }
      return null;
    }, id);
    if (on !== null) {
      await page.mouse.click(on.x, on.y);
    }
    await arrow.focus();
    const standingOnIt = await page.evaluate(
      () => document.activeElement?.closest<HTMLElement>(".react-flow__edge")?.dataset.id,
    );
    if (standingOnIt === id) {
      await page.keyboard.press("Enter");
    }
    await page.keyboard.press("e");
    // **Which arrow the panel is open on is read off the panel itself**, from
    // the identifier it carries for exactly this purpose — never from its
    // words. The words name an arrow by the claims at its two ends, in their own
    // sentences, because an identifier is never put on the screen; a test that
    // matched those words would break the day a claim was reworded, and one that
    // matched an identifier in them would be asking the screen to break its rule.
    const about = await panel.getAttribute("data-about").catch(() => null);
    const said = ((await panel.textContent().catch(() => "")) ?? "").trim();
    if (about === id) {
      return;
    }
    tried.push(
      `point ${on === null ? "none on the glass" : `${Math.round(on.x)},${Math.round(on.y)}`}` +
        ` · keyboard ${standingOnIt ?? "off the map"} · panel on ${about ?? "nothing"} "${said.slice(0, 50)}"`,
    );
    await page.waitForTimeout(250);
  }
  throw new Error(
    `the panel never opened on ${id}. What each attempt got:\n${tried.slice(-6).join("\n")}`,
  );
}

/**
 * Turn the panel beside the map to one of the panels its head names.
 *
 * **The panel is a few panels now, one at a time** (2026-09-22). It used to be
 * one column holding the branches, the change list and the answer to *why is
 * this number what it is* all at once, so a click on a tile filled the bottom of
 * a box nothing scrolled. A reader reaches a panel by its name; so does a test.
 *
 * @param page The page the map is on.
 * @param name The name at the head of the panel, as it is written there.
 */
async function turnThePanelTo(page: Page, name: RegExp): Promise<void> {
  const label = page.getByRole("tab", { name });
  await label.click();
  await expect(label).toHaveAttribute("aria-selected", "true");
}

/**
 * Every window this interface is held to.
 *
 * The whole of it was measured against the first; the other two are the two
 * laptop screens a reviewer is most likely to open it on, and every layout
 * defect the interface audit found showed up at one of them and not at 1600.
 */
const WINDOWS = [
  { width: 1600, height: 1000 },
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
] as const;

/**
 * Every control in the panel beside the map can actually be reached and pressed.
 *
 * **This is a geometric assertion and never a picture.** A stored screenshot
 * over a canvas with a background-threaded layout engine, two variable fonts and
 * an arrival animation is a flake generator, and this project has already paid
 * for chasing flakes. What it asserts instead is the thing every layout defect
 * the interface audit found had in common: something in the panel could be seen
 * in the markup and not used on the screen.
 *
 * **Three questions per control, and the third is the one that bites.**
 *
 * 1. It is drawn at a size at all.
 * 2. Scrolled to, it lies inside the panel's **client box** — the part of the
 *    panel that is actually on the glass, inside its border and beside its
 *    scrollbar. Scrolled out of view is fine and is why each control is scrolled
 *    to first: the panel scrolls as one and marks its edges, so below the fold is
 *    reachable.
 * 4. **The panel itself does not scroll sideways.** This is a question of its
 *    own and not a consequence of the second. The panel scrolls up and down, and
 *    a box that scrolls on one axis scrolls on the other as well unless it is
 *    told not to — so a field that runs past the right edge makes the panel
 *    wider inside than it is on the glass, scrolling to that field slides the
 *    whole panel left, and the field is then measured *inside* the client box.
 *    The first three questions pass on exactly the defect this helper was
 *    written for. Asking the panel how wide its content is cannot be fooled by
 *    where it happens to be scrolled to.
 * 3. **At its own centre, the topmost thing on the screen is the control** — or
 *    something inside it. That is the overlap test, and it is the only one of the
 *    three that catches a sibling drawn over a button, which is what "nothing is
 *    hidden behind anything" means. An earlier version of this helper asked only
 *    where boxes were, and against this stylesheet — one scrolling column whose
 *    sections all read `overflow: visible` — no box could ever land outside the
 *    content. It could not have failed.
 *
 * Each control is scrolled to over the wire and then measured in the page, which
 * is two round trips each rather than one for the lot. That is the price of
 * asking a question about what is *on the glass* rather than about what the
 * layout says.
 *
 * @param page The page the map is on.
 */
/**
 * How many tiles are drawn past the right edge of the stage.
 *
 * **This is not a count that has to be nought**, and that is the framing rule
 * rather than a shortcoming of it. The frame zooms to fit what it can and stops
 * at the zoom where a full tile's smallest words would fall under eleven pixels;
 * a map too wide to fit at that zoom is started at its beginning instead and the
 * reader pans to the rest. The stored example is five columns wide and does not
 * fit in this window — `src/graph/__tests__/layout.test.ts` works that out with
 * no browser, in pixels — so some of it is past the edge whatever the framing
 * does.
 *
 * What the count is for is the promise the map does make: it is never cut
 * silently. The stage marks the edge that has map beyond it, and the reading
 * below is what that mark is checked against.
 *
 * It is a count rather than a place, because the claim is about how many tiles a
 * reader can see and not about where any one of them is.
 *
 * @param page The page the map is on.
 */
async function tilesOffTheGlass(page: Page): Promise<number> {
  return page.evaluate(() => {
    const stage = document.querySelector(".canvas")?.getBoundingClientRect();
    if (stage === undefined) {
      return -1;
    }
    return [...document.querySelectorAll(".react-flow__node")].filter(
      (tile) => tile.getBoundingClientRect().right > stage.right + 1,
    ).length;
  });
}

async function everyControlInThePanelIsWhole(page: Page): Promise<void> {
  // **The column, not the scrolling box.** The names at the head of the panel
  // are controls a reader has to reach too, and they sit above the part that
  // scrolls so that they cannot scroll away — which puts them outside `.dock`
  // and outside the reach of a walk that started there.
  const column = page.locator(".dock-column");
  const dock = page.locator(".dock");
  await expect(dock).toBeVisible();
  const controls = column.locator("button, a, input");
  const many = await controls.count();
  expect(many, "the panel beside the map holds no controls at all").toBeGreaterThan(0);

  const wrong: string[] = [];
  for (let at = 0; at < many; at += 1) {
    const control = controls.nth(at);
    // Brought onto the glass first, because the question is about what a reader
    // can reach and a reader scrolls. The panel is the only thing that moves.
    await control.scrollIntoViewIfNeeded();
    const verdict = await control.evaluate((element) => {
      // Each control is measured against the box it actually lives in: the part
      // of the panel that scrolls, or the row of names above it.
      const panel =
        element.closest<HTMLElement>(".dock") ?? element.closest<HTMLElement>(".panel-switch");
      if (panel === null) {
        return "a control left the panel between being counted and being measured";
      }
      const name = (element.getAttribute("aria-label") ?? element.textContent ?? "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 60);
      const box = element.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) {
        return `"${name}" is drawn at no size at all`;
      }
      // The part of the panel that is on the glass: inside its border, and
      // beside its scrollbar rather than under it.
      const frame = panel.getBoundingClientRect();
      const left = frame.left + panel.clientLeft;
      const top = frame.top + panel.clientTop;
      const right = left + panel.clientWidth;
      const bottom = top + panel.clientHeight;
      if (
        box.left < left - 1 ||
        box.right > right + 1 ||
        box.top < top - 1 ||
        box.bottom > bottom + 1
      ) {
        return (
          `"${name}" is drawn at ${Math.round(box.left)},${Math.round(box.top)} to ` +
          `${Math.round(box.right)},${Math.round(box.bottom)}, outside the panel's ` +
          `${Math.round(left)},${Math.round(top)} to ${Math.round(right)},${Math.round(bottom)} — ` +
          `and it had already been scrolled to`
        );
      }
      // **What is actually on top at its centre.** A pseudo-element with
      // `pointer-events: none` — the rules the panel draws at its edges — is
      // not an answer to this question and the browser does not give one.
      const onTop = document.elementFromPoint(
        Math.round(box.left + box.width / 2),
        Math.round(box.top + box.height / 2),
      );
      if (onTop === null || !(onTop === element || element.contains(onTop))) {
        const over =
          onTop === null
            ? "nothing at all"
            : `<${onTop.tagName.toLowerCase()} class="${onTop.className}">`;
        return `"${name}" has ${over} drawn over its own middle`;
      }
      return null;
    });
    if (verdict !== null) {
      wrong.push(verdict);
    }
  }
  expect(wrong, "controls in the panel a reader cannot reach").toEqual([]);

  // Asked last, and of the panel rather than of any one control: by now every
  // control has been scrolled to, so anything that could widen the panel has.
  const sideways = await dock.evaluate((panel) => panel.scrollWidth - panel.clientWidth);
  expect(
    sideways,
    "the panel beside the map is wider inside than it is on the glass, so something in it runs past its edge",
  ).toBeLessThanOrEqual(1);

  // And of the names at its head, which wrap onto a second row rather than
  // scrolling: a name too long for the panel would run off its edge with
  // nothing saying so.
  const namesRunOver = await page
    .locator(".panel-switch")
    .evaluate((row) => row.scrollWidth - row.clientWidth);
  expect(
    namesRunOver,
    "a name at the head of the panel runs past the panel's own edge",
  ).toBeLessThanOrEqual(1);
}

/**
 * The page itself does not scroll sideways.
 *
 * **The one assertion here that varies with the window.** The panel is a fixed
 * 336 pixels whatever the screen is, so nothing measured inside it changes
 * between 1600 and 1280; the stage beside it takes the rest, and the two of them
 * together are what can stop fitting. A page that scrolls sideways is the whole
 * screen cut off rather than one control, and it is the defect a narrow window
 * produces that a wide one hides.
 *
 * @param page The page to measure.
 */
async function theScreenFitsItsWindow(page: Page): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const page_ = document.documentElement;
          return page_.scrollWidth - window.innerWidth;
        }),
      { timeout: 15_000, message: "the page never stopped scrolling sideways" },
    )
    .toBeLessThanOrEqual(1);
}

/**
 * The map read as a list is a list of sentences, not a list of words.
 *
 * **The defect this catches is a column, not a font.** An outline item is a grid
 * row, and a grid row whose text track has collapsed wraps one word to a line —
 * which turns a seven-claim map into a tree taller than the window and makes the
 * no-picture route, the accessibility story, unusable. A third of the outline's
 * own width is nowhere near a sentence and far away from two and a half
 * characters, so it catches the collapse without pinning a layout.
 *
 * @param page The page the outline is on.
 */
async function everyOutlineItemIsASentenceWide(page: Page): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const outline = document.querySelector<HTMLElement>(".outline");
          if (outline === null) {
            return ["the map is not being read as a list"];
          }
          const room = outline.clientWidth;
          if (room === 0) {
            // A third of nothing is nothing, and every item would pass.
            return ["the map read as a list is drawn at no width at all"];
          }
          const sentences = outline.querySelectorAll<HTMLElement>(".outline__sentence");
          if (sentences.length === 0) {
            return ["the map read as a list has no items in it"];
          }
          const thin: string[] = [];
          for (const sentence of sentences) {
            const width = sentence.getBoundingClientRect().width;
            if (width < room / 3) {
              thin.push(
                `an item is ${Math.round(width)} wide in an outline of ${Math.round(room)}`,
              );
            }
          }
          return thin;
        }),
      { timeout: 15_000, message: "the outline never settled at a readable width" },
    )
    .toEqual([]);
}

/** The first twelve counts as the map says them, which is how it says a count. */
const IN_WORDS = [
  "no",
  "one",
  "two",
  "three",
  "four",
  "five",
  "six",
  "seven",
  "eight",
  "nine",
  "ten",
  "eleven",
] as const;

/**
 * The shape of the line the map says out loud once the strike branch has been
 * folded on and the engine has answered.
 *
 * **One of its two counts is written down and the other is not.** One claim added
 * is a fact about the branch, so it reads the same on every machine. *How many
 * claims moved* is the engine's own count of the claims it called shifted, and it
 * changes whenever the arithmetic does — as every number on this map did at the
 * engine's flip. A test that wrote it down would be asserting today's arithmetic
 * in the one file that is supposed to be checking that the two halves are joined
 * up.
 *
 * **A third clause used to end it and is gone** *(2026-09-22; decision record
 * 0017)*: *one supposition retracted*. A later edit could undermine the cause of
 * an earlier supposition and the engine would take it back. Nothing takes a
 * supposition back now, so the count is always nought and the clause is never
 * said.
 *
 * **It refuses "no claims moved" by spelling out the words it will take.** With
 * a wildcard there it fitted a map that moved nothing at all, and the three
 * window tests wait on this line and nothing else — so an engine that had
 * stopped answering would have taken them straight past their own subject.
 *
 * It is still a real wait for the same reason. Before the engine answers the map
 * says *"…claims your edit can reach…"* and adds that the numbers are on their
 * way, which this does not fit; before the branch is opened there is no line at
 * all. The noun is allowed to be singular so that a branch moving exactly one
 * claim fails on the count below, where the message says what the map said,
 * rather than on a wait that runs out and says only that it ran out.
 */
const WHAT_THE_STRIKE_DID = new RegExp(
  `^Branch created\\. One claim added, (${IN_WORDS.slice(1).join("|")}) claims? moved\\.$`,
);

/** The same counts with a capital, for a count that begins its own sentence. */
const IN_WORDS_CAPITALISED = IN_WORDS.map(
  (word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`,
);

/**
 * The same shape for a branch that adds no claim — the reader reporting a piece
 * of news on a claim the map already has.
 *
 * **The count is the engine's and is never written here.** Reporting something
 * travels back up the arrows into its causes and out again along everything they
 * lead to, so how many claims that reaches is a fact about the arithmetic. What
 * this asserts is that the map said a count at all, and that the count is not
 * nought — the line before the engine answers is a different sentence, and *no
 * claims moved* is the answer to a branch with nothing in it.
 *
 * **The count is capitalised here and not in the shape above, because it starts
 * the sentence.** The line is built from clauses and the first letter of the
 * first clause is made a capital, so a branch that adds a claim reads *"Branch
 * created. One claim added, nine claims moved."* and a branch that adds none
 * reads *"Branch created. Nine claims moved."* That is the map's own sentence
 * casing and has been since the line was written; this shape was copied from the
 * one above when the retraction clause went, and asked the map to start a
 * sentence in lower case.
 */
const SOMETHING_MOVED = new RegExp(
  `^Branch created\\. (${IN_WORDS_CAPITALISED.slice(1).join("|")}) claims? moved\\.$`,
);

/**
 * How many claims the map said moved, read back out of the line it said.
 *
 * The count is never written into this file: it is the engine's own, one word
 * per claim it called shifted. Reading it off the page and then checking the
 * picture against it is the claim worth making — **a reader who cannot see the
 * map and a reader who can are told the same thing** — and it is a claim that
 * survives the day the engine's numbers all move at once.
 *
 * @param page The page the map is on.
 */
async function howManyTheMapSaidMoved(page: Page): Promise<number> {
  const live = page.locator(".map-live");
  await expect(live).toHaveText(WHAT_THE_STRIKE_DID);
  const said = /, (\w+) claims? moved,/.exec((await live.textContent()) ?? "")?.[1] ?? "";
  const many = IN_WORDS.indexOf(said as (typeof IN_WORDS)[number]);
  // Greater than one, not greater than nothing: the strike branch reaches the
  // oil price, the insurance premium and both contracts, so a map saying it
  // moved nothing — or exactly one thing — is a map that has stopped working,
  // and this says which of the two rather than timing out.
  expect(
    many,
    `the map said "${said} claims moved", which is not a count this branch can honestly reach`,
  ).toBeGreaterThan(1);
  return many;
}

/**
 * Open the stored map and fold the strike branch onto it, with the mouse and
 * the palette, and wait until the engine has answered.
 *
 * @param page The page to do it on.
 */
async function theStoredMapWithTheStrikeBranch(page: Page): Promise<void> {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  await page.keyboard.press("Meta+k");
  await expect(page.getByText(/Every command, by name/)).toBeVisible();
  await page.keyboard.type("Hormuz opens");
  await page.keyboard.press("Enter");
  await waitForTheBranch(page, "Hormuz opens, then Iran is struck", 10);
  // The engine has answered when the map says what the branch did, with the
  // counts in it — before that the panel is still holding the answer to the
  // question before this one.
  await waitForTheAnswer(page, WHAT_THE_STRIKE_DID);
}

/**
 * The panel holds everything it holds, at every window this interface is held
 * to, with a branch open and the operations open — which is the panel at its
 * fullest.
 *
 * **Every panel the head of it names, not merely the one that happens to be
 * showing** (2026-09-22). The panel used to be one column, so asking about it
 * once asked about all of it; now a control a reader cannot reach could sit on a
 * panel this test never turned to.
 */
for (const window of WINDOWS) {
  test(`test_nothing_in_the_panel_is_cut_off_at_${window.width}_by_${window.height}`, async ({
    page,
  }) => {
    // Three window sizes, a branch, an engine answer and every panel the head
    // of the panel names: longer than the walk the other tests take.
    test.setTimeout(120_000);
    await page.setViewportSize({ width: window.width, height: window.height });
    await theStoredMapWithTheStrikeBranch(page);

    // The panel is a fixed 336 pixels and the stage takes the rest, so this is
    // the one thing on this screen that a narrow window can break and a wide one
    // cannot.
    await theScreenFitsItsWindow(page);

    // **The names at the head of the panel are themselves controls**, and they
    // are the first thing asked about: a name drawn past the panel's own edge
    // would be a panel a reader cannot reach at all.
    const names = page.getByRole("tab");
    expect(await names.count(), "the panel offers no panels at all").toBeGreaterThan(1);
    await everyControlInThePanelIsWhole(page);

    // The claim panel at its fullest: whatever is selected, and — opened from
    // the Inspector's own head with the mouse — the things you can do to it.
    await page.locator('.react-flow__node[data-id="B"]').click();
    const wayIn = page.getByRole("button", { name: "Change this claim" });
    await expect(wayIn).toBeVisible();
    await wayIn.click();
    // Which claim the operations are open on, read off the panel's own mark
    // rather than off its sentence: matching a sentence is testing the copy.
    await expect(page.locator('.intervene[data-about="B"]')).toBeVisible();
    await everyControlInThePanelIsWhole(page);

    // And the field that opens inside it, which is the widest thing the panel
    // ever holds.
    await page.getByRole("button", { name: /^My own number/ }).click();
    await expect(page.getByLabel(/Your likelihood/)).toBeVisible();
    await everyControlInThePanelIsWhole(page);
    await theScreenFitsItsWindow(page);

    // Your branches and the change list, which is the panel the strike branch
    // fills: every branch, every edit on the open one, and a row per ending the
    // edit reaches.
    await turnThePanelTo(page, /Branches and changes/);
    await expect(page.locator(".branch-panel")).toBeVisible();
    await expect(page.locator(".delta-rail")).toBeVisible();
    await everyControlInThePanelIsWhole(page);
    await theScreenFitsItsWindow(page);

    // Then the same map read as a list, which is the panel the no-picture route
    // depends on. `O` is a map key, so the keyboard goes back on the map first —
    // the press is otherwise the button's, which is the product's rule rather
    // than this test's convenience.
    await standOn(page, "B");
    await page.keyboard.press("O");
    await expect(page.getByRole("tree")).toBeVisible();
    await everyOutlineItemIsASentenceWide(page);
    await everyControlInThePanelIsWhole(page);
    await theScreenFitsItsWindow(page);
  });
}

/**
 * The whole of the brief's core interaction, with the mouse and nothing else.
 *
 * **The keyboard walk above is the other half of this claim, not a substitute
 * for it.** The panel of operations used to open from `E` and from the command
 * palette and from nowhere else, so somebody working this screen by pointing at
 * things could click every tile, read the whole argument and never find a verb
 * on it. Not one key is pressed below.
 */
test("test_the_mouse_alone_reaches_the_six_things_you_can_do", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  // A claim, chosen by pointing at it. No branch is open, so the edit below
  // starts one of the reader's own — which is this product's own rule, and is
  // what makes this a journey rather than a button press.
  await page.locator('.react-flow__node[data-id="B"]').click();

  // The way in, in the panel's head, in the vocabulary's own words. It is not
  // there at all until something is selected, so waiting for it is waiting for
  // the pointer to have landed.
  const wayIn = page.getByRole("button", { name: "Change this claim" });
  await expect(wayIn).toBeVisible();
  await wayIn.click();

  // **Which claim the operations are open on is read off the panel's own mark,
  // never off its sentence.** The panel prints claims in their own words and
  // arrows as the two claims at their ends, and a test that matched those words
  // would be a test of the copy — which is how one end-to-end test came to fail
  // on every cold run after a sentence was improved.
  const operations = page.locator('.intervene[data-about="B"]');
  await expect(operations).toBeVisible();
  // And the difference between the two that are easiest to confuse is on the
  // screen before the choice rather than after it.
  await expect(operations).toContainText("Take this as given, and do not tell me what caused it");
  await expect(operations).toContainText("This is news — update what came before it too");

  await operations.getByRole("button", { name: /^Suppose this is true/ }).click();

  // **The branch gained the edit.** It is listed by the button that made it,
  // with the badge that button earns, on a branch that did not exist a moment
  // ago — read off the panel rather than out of this file. Your branches are a
  // panel of their own since 2026-09-22, one name away, and the name is pressed
  // here because this whole test is the mouse's walk and nothing else.
  await turnThePanelTo(page, /Branches and changes/);
  const branches = page.locator(".branch-panel");
  await expect(branches).toContainText("Your own branch");
  await expect(branches).toContainText("1 edit");
  await expect(branches.locator(".branch-panel__button-name")).toHaveText("Suppose this is true");
  await expect(branches.locator(".branch-panel__badge")).toHaveText(/^Supposed · /);

  // And the map says out loud that a branch was created, for a reader who is
  // not looking at the picture.
  await expect(page.locator(".map-live")).toContainText("Branch created.");
});

/**
 * What the hypothesis's tile must read, word for word, once the strike lands.
 *
 * **One badge, and it stands** *(2026-09-22; decision record 0017)*. You supposed
 * the strait reopens on the first, and it is still supposed after the strike: a
 * supposition holds until the reader lifts it, and nothing on the map takes one
 * back. There used to be a second badge here — *Retracted · Oct 2 · by "a
 * confirmed military strike on Iranian territory"* — with an arrow drawn between
 * the two so the pair read as a sequence. The engine cannot produce it any more,
 * so the pair, the arrow and the words are all gone.
 *
 * What the strike ends instead is the claim the map gained at the same time: *the
 * strait stays open to commercial transit through 1 November*, which is a **state**
 * rather than an event, and a state is the only kind of claim a `sustain` arrow can
 * switch off. That claim's number falls, and the check for it is below.
 */
const STILL_SUPPOSED = ["Supposed · Oct 1"];

test("the stored example, opened and edited by keyboard alone", async ({ page }) => {
  await page.goto("/");

  // The launchpad, reached and opened with the keyboard. Tab to the one example
  // that is live and press Enter.
  const hormuz = page.getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ }).first();
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
  // The seed, because a run is reproducible from it — and **not** how many
  // versions of the map the engine tried, nor how many worlds under each, which
  // Kent cut from this product on 2026-09-22 (R48).
  await expect(page.locator(".map-origin")).toContainText("at seed");
  await expect(page.locator(".map-origin")).not.toContainText("versions of the map");
  await expect(page.locator(".map-origin")).not.toContainText("worlds under each");
  await waitForTheLayout(page, 9);

  // And every arrow, by name. The map's claims are only half of what it says;
  // the other half is what points at what.
  await everyArrowIsDrawn(page);

  // Every tile is a whole tile on the first frame, not a summary. The zoom is
  // held at the point where a tile's smallest words land at eleven pixels, and
  // below that a tile changes what it draws rather than shrinking it. Counted
  // rather than read into a list, so that "all nine of them" is what is waited
  // for rather than what happened to be there when the list was taken.
  await expect(page.locator('.tile[data-detail="full"]')).toHaveCount(9);
  await expect(page.locator(".tile")).toHaveCount(9);

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

  // Every key, on one sheet — and it says out loud that you cannot move a tile.
  await page.keyboard.press("?");
  await expect(page.getByText(/You cannot move a tile/)).toBeVisible();
  // Escape closes it, and nothing was left half-done.
  await page.keyboard.press("Escape");
  await expect(page.getByText(/You cannot move a tile/)).toBeHidden();

  // Walking the wires. Tab onto the map, step forward along a wire out of the
  // hypothesis, and the line under the map names the wire that was taken.
  await page.evaluate(() => document.body.focus());
  const entered = await tabOntoTheMap(page);
  expect(entered).toBe("H");
  await page.keyboard.press("l");
  await expect(page.locator(".map-status")).toContainText("along an arrow");
  // Whatever it landed on is one of the four claims the strait's opening causes:
  // the oil price, the strait staying open, the contract on the reopening itself,
  // and the talks. Which one it is falls out of which is nearest on the glass, and
  // that rule is checked over every claim and both directions in
  // `src/keyboard/__tests__/focusMap.test.ts`.
  await landedOn(page, ["B", "M3", "N1", "O"]);

  // And back along a wire, toward what causes it.
  await page.keyboard.press("h");
  await expect(page.locator(".map-status")).toContainText("along an arrow");
  const standingWhenTheWalkFoldedThePanel = await landedOn(page, ["H", "C", "R"]);

  await test.step("test_the_panel_folds_from_a_control_and_the_key_brings_it_back", async () => {
    // **The control Kent asked for**, 2026-09-22: *"the … large, uncollapsible
    // side bar [is] somewhat garish. First, can you introduce a button to be
    // able to collapse and open the side bar."* The panel had always folded from
    // `P`, and nothing on screen said so — so a reader who found the key by
    // accident had a map and no way back to the panel.
    //
    // The two halves of the claim are measured rather than read: the panel
    // leaves the row, and the stage is wider afterwards than it was before. The
    // width is compared with itself across the press; no number is written here.
    const theStage = page.locator(".map-stage");
    const wide = async () => (await theStage.boundingBox())?.width ?? 0;
    const wasWide = await wide();
    expect(wasWide, "the stage was drawn at no width at all").toBeGreaterThan(0);
    const framedOpen = await whereTheMapCameToRest(page);

    await page.getByRole("button", { name: "Hide the panel beside the map" }).click();
    await expect(page.locator(".dock-column")).toHaveCount(0);
    await expect
      .poll(wide, { timeout: 5_000, message: "the stage never took the panel's width" })
      .toBeGreaterThan(wasWide);

    // And the way back for a reader with a pointer: a tab at the edge the panel
    // went behind, which is the only control on screen while it is away.
    await expect(page.getByRole("button", { name: "Show the panel beside the map" })).toBeVisible();

    // **The map is framed again for the stage it is now in, once, as a cut.**
    // 310 more pixels and the same map: framed for the narrower stage it would
    // sit off to one side of the wider one. The reading is the viewport's own
    // transform compared with itself across the press — no number is written
    // here — and it is taken once the map has stopped moving, because a
    // transform read while it is still changing is a reading of a moment.
    const framedWider = await whereTheMapCameToRest(page);
    expect(framedWider, "the map was not framed again when the panel folded").not.toBe(framedOpen);

    // **And it is framed honestly, which is not the same as everything fitting.**
    // This map is five columns of tiles, and at the zoom the frame holds — the
    // one where a full tile's smallest words still land at eleven pixels — it is
    // wider than the stage even with the panel gone. The rule for that case is
    // the rule a tile follows when it runs out of room: draw less rather than
    // draw it smaller. So the map is started at its beginning and the reader
    // pans, and the two promises worth reading are these two.
    //
    // The first: every tile is still a whole tile, which is what the zoom floor
    // exists for and the reason the map does not fit.
    await expect(page.locator('.tile[data-detail="full"]')).toHaveCount(9);
    // The second: the map never cuts itself silently. The stage carries a mark
    // for each edge that has map beyond it, and it says so exactly when there is
    // something out there — read as the two agreeing rather than as either one
    // on its own, so this says the same thing at a window the map does fit in.
    const cut = await tilesOffTheGlass(page);
    await expect(page.locator(".canvas")).toHaveAttribute(
      "data-more-right",
      cut > 0 ? "yes" : "no",
    );

    // **Walking the map does not bring the panel back.** Every step along a
    // wire selects the claim it lands on — reaching one with the keyboard and
    // pointing at one both fill the panel, which is this product's own rule —
    // so a panel that returned on any selection returned on the reader's first
    // keystroke, and a fold you cannot walk away from is a fold that does not
    // work. The keyboard goes back on the map first, which is the product's
    // rule about map keys rather than this test's convenience.
    await standOn(page, standingWhenTheWalkFoldedThePanel);
    await expect(page.locator(".dock-column")).toHaveCount(0);
    await page.keyboard.press("l");
    await expect(page.locator(".map-status")).toContainText("along an arrow");
    await expect(page.locator(".dock-column")).toHaveCount(0);

    // The key still brings it back, and the map is framed back to where it was.
    await page.keyboard.press("P");
    await expect(page.locator(".dock-column")).toHaveCount(1);
    await expect
      .poll(wide, { timeout: 5_000, message: "the stage never gave the panel's width back" })
      .toBe(wasWide);
    expect(await whereTheMapCameToRest(page)).toBe(framedOpen);

    // And the walk goes on from the claim it was on before this step.
    await standOn(page, standingWhenTheWalkFoldedThePanel);
  });

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

  // **There is no band to read, and that is the assertion** *(2026-09-22, R48)*.
  // This read the range under the number so that "the same number as before"
  // meant the same number *and* the same band; a chip is the owner, the mark and
  // the number now, and the line the range stood on is gone rather than empty.
  await expect(page.locator('.react-flow__node[data-id="R"] .belief-chip__under')).toHaveCount(0);

  await page.keyboard.press("Meta+k");
  await expect(page.getByText(/Every command, by name/)).toBeVisible();
  await page.keyboard.type("Hormuz opens");
  await page.keyboard.press("Enter");
  // The union of the two worlds is laid out again, once, before anything on it
  // can be read — ten tiles now, each in a place of its own.
  await expect(page.locator('.react-flow__node[data-id="S"]')).toBeVisible();
  await waitForTheBranch(page, "Hormuz opens, then Iran is struck", 10);
  // What the branch did, said out loud for a reader who is not looking at the
  // picture — the whole sentence, against the real engine. How many claims moved
  // is the engine's own count of the claims it called shifted, so it is read
  // back off the page rather than written down here, and the tiles below are
  // checked against it: a reader who cannot see the map and a reader who can
  // are told the same thing.
  const saidMoved = await howManyTheMapSaidMoved(page);

  // The claim the branch added is on the map, with the two badges its edits
  // earned, in the order they were made.
  const strike = page.locator('.react-flow__node[data-id="S"]');
  await expect(strike).toBeVisible();
  await expect(strike).toContainText("A confirmed military strike on Iranian territory.");
  await expect(strike.locator(".tile__badge-words")).toHaveText(["Added", "Supposed · Oct 2"]);
  // And while a claim is supposed, its tile shows the word where a likelihood
  // would go — never `1.0`, and never `.98`.
  await expect(strike.locator(".belief-chip__figure").first()).toHaveText("Supposed · Oct 2");

  // The hypothesis: the supposition the reader made, still standing, word for
  // word — read off the world the engine built rather than worked out twice. One
  // badge, and nothing behind it: nothing takes a supposition back, so there is no
  // second badge and no arrow drawn between a pair of them.
  const hypothesis = page.locator('.react-flow__node[data-id="H"]');
  await expect(hypothesis.locator(".tile__badge-words")).toHaveText(STILL_SUPPOSED);
  await expect(hypothesis.locator(".tile__badge-arrow")).toHaveCount(0);
  // And while a supposition holds, the tile says the word where the likelihood
  // would go rather than the flat `1` the engine stores behind it.
  await expect(hypothesis.locator(".belief-chip__figure").first()).toHaveText("Supposed · Oct 1");
  // Its numbers are the engine's now, not an absence: the branch was worked
  // through and the answer came back.
  await expect(hypothesis).not.toContainText("no engine yet");

  // **And the claim the strike actually ends.** *The strait stays open to
  // commercial transit through 1 November* is a state, which is the one kind of
  // claim a `sustain` arrow can switch off, and the strike switches it off — so
  // its reading goes down. The direction is asserted and neither number is
  // written here: the tile draws the reading it had and the reading it has, with
  // a chevron between them, and the chevron is which way it went.
  const staysOpen = page.locator('.react-flow__node[data-id="O"]');
  await expect(staysOpen.locator(".tile")).toHaveAttribute("data-diff", "shifted");
  await expect(
    staysOpen.locator('.tile__badge[data-badge="movement"] .tile__badge-words'),
  ).toHaveText(/^\.\d+ ▼ \.\d+$/);

  // The claim the edit provably cannot reach. Its number is the one it read
  // before the branch — the whole chip, unchanged.
  const opec = page.locator('.react-flow__node[data-id="R"]');
  await test.step("test_the_fully_separated_claim_does_not_change", async () => {
    await expect(opec).toContainText("OPEC+ announces a new output cut.");
    await expect(opec.locator(".belief-chip__reading").first()).toHaveText(opecBefore);
    await expect(opec).not.toContainText("no engine yet");
    await expect(opec.locator(".tile")).toHaveAttribute("data-diff", "untouched");
  });

  // test_the_browser_states_agree_with_the_engine — against the real engine.
  //
  // One claim arrived with the edit, exactly one is `untouched` — the one the
  // browser's own walk of the arrows says the edit cannot reach — and as many
  // tiles read `shifted` as the map said moved out loud. The browser puts
  // `untouched` on OPEC's tile and the engine leaves its number where it was;
  // the rule joining the two readings is checked claim by claim in
  // `src/graph/__tests__/diffState.test.ts`, and this is where it is checked
  // against the engine itself.
  await expect(page.locator(".tile")).toHaveCount(10);
  const states = await page
    .locator(".tile")
    .evaluateAll((tiles) => tiles.map((tile) => (tile as HTMLElement).dataset.diff ?? "none"));
  expect(states.filter((word) => word === "shifted")).toHaveLength(saidMoved);
  expect(states.filter((word) => word === "added")).toHaveLength(1);
  expect(states.filter((word) => word === "untouched")).toHaveLength(1);
  // **And whatever is left over is drawn as a claim the edit can reach.** A
  // claim the edit reaches whose number the engine will not call moved is not a
  // claim the edit cannot reach, and drawing it `untouched` would tell the
  // reader the opposite of the truth about their own edit. So every remaining
  // tile reads `downstream`, and none reads nothing at all — which is what says
  // no tile is in a state this test has not accounted for.
  expect(states.filter((word) => word === "downstream")).toHaveLength(
    states.length - saidMoved - 2,
  );
  expect(states.filter((word) => word === "none")).toHaveLength(0);

  // **And two of them by name, so the counts above cannot agree with each other
  // about nothing.** Every line so far reads the engine's word for each claim;
  // a run in which the engine answered but said the wrong thing about every
  // claim would satisfy all of them together. These two are the map's own
  // story: the strait is what you supposed, the strike pushes straight at it
  // and at the insurance premium, and both must come back moved. If the day
  // comes when the engine honestly says otherwise about one of them, the
  // branch's whole walk has changed and this is the right place to be told.
  for (const claim of ["H", "C"]) {
    await expect(page.locator(`.react-flow__node[data-id="${claim}"] .tile`)).toHaveAttribute(
      "data-diff",
      "shifted",
    );
  }

  // **The panel, turned with one key.** Opening the branch added a claim and
  // chose it, so the panel is on that claim — which is the one thing that moves
  // the panel by itself, and is what a reader wants when a branch adds
  // something. The change list is the next panel along, and `N` is how a reader
  // who never touches the mouse gets to it (2026-09-22).
  await page.keyboard.press("N");
  await expect(page.getByRole("tab", { name: /Branches and changes/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );

  // The rail beside the map lists the endings, in the engine's own order — and
  // **nothing beside them**: *how firm*, the width of the range around the new
  // number, and *same direction*, the share of the versions of the map that
  // moved the same way, were both cut on 2026-09-22 (R48).
  const rail = page.locator(".delta-rail");
  await expect(rail).toContainText("In the order the engine put them in");
  await expect(rail).not.toContainText("how firm");
  await expect(rail).not.toContainText("same direction");
  await expect(rail).not.toContainText("no engine yet");

  // **Exactly the endings the edit can reach are on the list, by name.** Which
  // those are is read off the map rather than written down: an ending is a
  // claim that names something you could trade or names why there is nothing to
  // trade, and the list carries the ones the edit reaches. Compared as a set of
  // names rather than as a count, because a row that vanished and a row that
  // was invented cancel out in a count and this is exactly the failure being
  // guarded — an ending the engine gives no row of its own used to be dropped
  // outright when the reader forced it false.
  const endings = await page.locator(".react-flow__node").evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const { kind, diff } = node.querySelector<HTMLElement>(".tile")?.dataset ?? {};
        return (kind === "market" || kind === "not_tradeable") && diff !== "untouched";
      })
      .map((node) => (node as HTMLElement).dataset.id ?? "?"),
  );
  expect(endings.length, "the map drew no ending this edit can reach").toBeGreaterThan(0);
  // Read in one go, and after the endings: a list taken while the rows are
  // still arriving is a list that agrees with itself and says nothing.
  const onTheList = await rail.locator(".delta-rail__row").evaluateAll((rows) =>
    rows.map((row) => ({
      about: (row as HTMLElement).dataset.about ?? "?",
      ranked: (row as HTMLElement).dataset.ranked ?? "?",
    })),
  );
  expect(onTheList.map((row) => row.about).sort()).toEqual([...endings].sort());

  // **Every ending this branch reaches is one the engine ranked** *(2026-09-22)*.
  // The talks used to be the quiet row written down here on purpose — the biggest
  // move on the map, behind the map's one bare assertion, and the engine would not
  // call it a move, because the two thousand versions of the map could not agree
  // which way it went. There is one version now, so a move has one direction, and
  // the strike moves every ending it reaches far enough to report. The quiet row
  // itself is not untested: `test_nothing_on_screen_names_versions_when_an_observation_moves_a_claim`
  // below reaches it against this same engine, and which words go with it are
  // pinned in `src/components/__tests__/deltaRail.test.tsx`.
  //
  // Read off the page rather than written down, so the day one of them holds
  // still the loop underneath has something to walk instead.
  const quiet = onTheList.filter((row) => row.ranked === "no");
  expect(
    quiet.length,
    "an ending this edit reaches held still, which this branch has not done since the flip",
  ).toBe(0);

  // Every row the engine ranked carries **one** reading and nothing else — the
  // count of cells tied to the count of rows read off the same page, so a rail
  // that drew one row cannot pass for a rail that drew three. It was three
  // readings a row until R48 took the other two columns (2026-09-22): *how firm*,
  // the width of the range around the new number, and *same direction*, the share
  // of the versions of the map that moved the same way.
  const ranked = rail.locator('.delta-rail__row[data-ranked="yes"]');
  const many = onTheList.length - quiet.length;
  expect(many, "the engine ranked no ending at all").toBeGreaterThan(0);
  await expect(ranked).toHaveCount(many);
  await expect(ranked.locator(".delta-rail__value")).toHaveCount(many);
  for (const cell of await ranked.locator(".delta-rail__values").all()) {
    // The two readings with a chevron between them, each at two significant
    // figures, and nothing after them.
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+$/);
  }

  // And every quiet row says what happened in words, and says why in words:
  // the engine's own verdict where a move would be, and under the ending's own
  // sentence the reason it ranked none. Which words go with which verdict is
  // pinned in `src/components/__tests__/deltaRail.test.tsx`; what is checked
  // here is that they reach the screen at all, rather than the row being
  // nothing but a paler shade of the rows above it.
  for (const row of await rail.locator('.delta-rail__row[data-ranked="no"]').all()) {
    await expect(row.locator(".delta-rail__value").first()).not.toBeEmpty();
    await expect(row.locator(".delta-rail__note")).not.toBeEmpty();
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
  await expect(outline.getByRole("treeitem")).toHaveCount(10);
  await expect(outline).toContainText("Your edit cannot reach this claim.");

  // And nothing anywhere on the screen is a pop-up: no dialog, and none of the
  // six operations' code names.
  await expect(page.getByRole("dialog")).toHaveCount(0);
  for (const code of ["observe", "retune", "refine"]) {
    await expect(page.locator("body")).not.toContainText(new RegExp(code, "i"));
  }
});

/**
 * Pressing **This happened** on the Brent claim puts the endings it reaches on
 * the rail.
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
 * likelihood even though nothing on the map pushes on it — and what the screen
 * says about that is the subject of the test after this one.
 */
test("test_this_happened_puts_rows_on_the_rail", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  // A branch of the reader's own, and then the news, on the Brent claim.
  await page.locator('.react-flow__node[data-id="B"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("Brent settled below $68");
  await page.getByRole("button", { name: "Start this branch" }).click();
  // The branch is folded on and the map is laid out again before the claim is
  // pointed at, because pointing at a tile that is still being placed points at
  // wherever it used to be.
  await waitForTheBranch(page, "Brent settled below $68", 9);
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
  await waitForTheAnswer(page, SOMETHING_MOVED);
  await waitForTheLayout(page, 9);

  // News about a claim travels back up the arrows into its causes and out again
  // along everything they lead to, so the endings hanging off Brent move — and
  // the rail is where a move turns into something a reader can act on. A rail
  // that stayed empty here would make **This happened** a button that does
  // nothing. It is on the panel your branches are on, which the edit above did
  // not turn to: an arrival never moves the panel, only the reader does
  // (2026-09-22).
  await turnThePanelTo(page, /Branches and changes/);
  const rail = page.locator(".delta-rail");
  await expect(rail).toContainText("In the order the engine put them in");

  // **How many rows is read off the map, never written down here.** An ending is
  // a claim that names something you could trade or names why there is nothing to
  // trade; the rail carries the ones this edit reaches, and how many that is is a
  // fact about the map and the arithmetic rather than about this file.
  const endings = await page.locator(".react-flow__node").evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const { kind, diff } = node.querySelector<HTMLElement>(".tile")?.dataset ?? {};
        return (kind === "market" || kind === "not_tradeable") && diff !== "untouched";
      })
      .map((node) => (node as HTMLElement).dataset.id ?? "?"),
  );
  expect(endings.length, "the map drew no ending this report can reach").toBeGreaterThan(0);
  const rows = rail.locator(".delta-rail__row");
  await expect(rows).toHaveCount(endings.length);
  await expect
    .poll(() =>
      rows.evaluateAll((drawn) =>
        drawn.map((row) => (row as HTMLElement).dataset.about ?? "?").sort(),
      ),
    )
    .toEqual([...endings].sort());

  // Every reading on a ranked row is the engine's, and none is typed in here.
  const moved = rail.locator('.delta-rail__row[data-ranked="yes"] .delta-rail__values');
  expect(await moved.count(), "the engine ranked no ending at all").toBeGreaterThan(0);
  for (const cell of await moved.all()) {
    await expect(cell).toHaveText(/^\.\d+ [▲▼] \.\d+$/);
  }
});

/**
 * **The sentence this test was written for is gone, and this is what took its
 * place** *(Kent, 2026-09-22, R48; decision record 0028)*.
 *
 * It was `test_a_claim_moved_only_by_reweighting_says_so_in_the_inspector`.
 * Reporting the insurance premium as news moves the strait's own likelihood even
 * though nothing on the map pushes on it: what moved it was the observation
 * making the versions of the map in which it was likely count for more, and the
 * panel said so in one sentence. The engine works out one version of the map now,
 * so there is nothing for a sentence about reweighting to be about. It reports the
 * field as `false` on every claim and `frontend/src/world/apiSource.ts` is where
 * it stops; both leave together in the follow-up that takes down the constant wire
 * fields.
 *
 * What is left to hold up is the stronger claim: the engine can reach this state
 * against the real map, and **nothing anywhere on the screen names a version, a
 * world or an interval when it does**. Reporting the premium still reaches back up
 * into the strait's own likelihood, which is the rule worth pinning; and the
 * endings the report does *not* move far enough still hold a row each, saying *no
 * change* in the engine's own words with its two readings behind them.
 */
test("test_nothing_on_screen_names_versions_when_an_observation_moves_a_claim", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  // The news is the insurance premium falling. Nothing on this map pushes on
  // the strait's own likelihood — it is the claim the map starts from — so this
  // is the one branch that reaches the state the cut sentence described.
  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("b");
  await page.getByLabel(/What is this branch called/).fill("The premium fell");
  await page.getByRole("button", { name: "Start this branch" }).click();
  await waitForTheBranch(page, "The premium fell", 9);
  await waitForTheAnswer(page, "Branch created. No claims moved.");

  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("e");
  await expect(page.locator(".intervene")).toContainText(
    "Lloyd's war-risk insurance premium for Gulf transits is under 0.4%.",
  );
  await page.getByRole("button", { name: /^This happened/ }).click();

  // The edit is finished when the map says what it did, and not before.
  await waitForTheAnswer(page, SOMETHING_MOVED);
  await waitForTheLayout(page, 9);

  // The panel, on the strait itself.
  await page.locator('.react-flow__node[data-id="H"]').click();

  await test.step("test_the_report_reaches_back_up_into_the_strait", async () => {
    // **The rule this branch exists for.** Nothing on the map pushes on the
    // strait's own likelihood — it is the claim the map starts from — and yet
    // reporting the insurance premium moves it, because news about an effect is
    // evidence about its causes. A browser that drew the strait *untouched* here
    // would be drawing the map as it was written over a number the engine had
    // moved. The direction is the engine's and neither number is written here.
    const strait = page.locator('.react-flow__node[data-id="H"]');
    await expect(strait.locator(".tile")).toHaveAttribute("data-diff", "shifted");
    await expect(
      strait.locator('.tile__badge[data-badge="movement"] .tile__badge-words'),
    ).toHaveText(/^\.\d+ [▲▼] \.\d+$/);
  });

  await test.step("test_the_tile_says_why_the_engine_reports_no_change", async () => {
    // The talks, on the same branch: the report reaches them, the engine will not
    // call what happened to them a move, and the tile says so — in words, with the
    // engine's own two readings in the sentence behind it, and with the engine's
    // one reason for the verdict rather than none.
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
    // The engine gives one reason now — the move is smaller than it will report at
    // all — so the tile names it rather than saying it has none to give.
    await expect(talks).toHaveAttribute("title", /smaller than it will report/);
    await expect(talks).not.toHaveAttribute("title", /gave no reason/);
  });

  await test.step("test_nothing_on_this_screen_names_a_version_or_a_world", async () => {
    // The whole screen, read as a reader would hear it: the map, the strip, the
    // line under it and whichever panel is open. The one address with the word
    // in it — where the engine is asked — is taken out first, because that is a
    // route rather than a sentence about the multiverse.
    for (const which of [/This claim/, /Branches and changes/, /Outline/]) {
      await turnThePanelTo(page, which);
      const said = (await page.locator("main").innerText()).replace(
        /\/api\/worlds(\/[a-z]+)?/g,
        " ",
      );
      for (const word of [
        /\bversions?\b/i,
        /\bworlds\b/i,
        /\binterval\b/i,
        /\buncalibrated\b/i,
        /middle 80/i,
      ]) {
        expect(said, `the screen says ${word}`).not.toMatch(word);
      }
      // And no reading on it is a pair of numbers with a dash between them.
      expect(said).not.toMatch(/[.>]\s*\d[\d.]*\s*[–—-]\s*[.<>]\s*\d/);
    }
  });
});

/**
 * A branch that reports a claim and then changes how hard one of its causes
 * pushes it — against the real engine, with the answer held in flight.
 *
 * **What it pins is the rule the engine amended on 2026-09-21**: an edit that
 * can move a claim some report was made about can move everything that report
 * is evidence about. The arrow's **source** is one of those: how much news about
 * an effect says about a cause depends on how hard that cause was pushing. A
 * browser that called the source *untouched* would be drawing the map as it was
 * written over a number the engine had moved — the quietest lie there is.
 *
 * **And it pins that nothing jumps.** The line saying how far a number moved is
 * reserved the moment the edit is made, not when the answer lands: a tile that
 * grows on arrival either shoves its neighbours or sits on top of them. The
 * engine's answer is held in flight here so that both moments can be looked at,
 * and the tile is measured in each.
 *
 * Not one number below is written into this file. The two readings are the
 * engine's, read off the screen, and the height is compared with itself.
 */
test("test_a_retune_under_a_report_moves_the_arrows_source", async ({ page }) => {
  // Two engine answers, one of them deliberately held, and a branch built a
  // button at a time — longer than the walk the other tests take.
  test.setTimeout(120_000);
  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  // A branch, and the news: the premium fell.
  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("b");
  await page
    .getByLabel(/What is this branch called/)
    .fill("The premium fell, then the push changed");
  await page.getByRole("button", { name: "Start this branch" }).click();
  await waitForTheBranch(page, "The premium fell, then the push changed", 9);
  await waitForTheAnswer(page, "Branch created. No claims moved.");

  await page.locator('.react-flow__node[data-id="C"]').click();
  await page.keyboard.press("e");
  await expect(page.locator(".intervene")).toContainText(
    "Lloyd's war-risk insurance premium for Gulf transits is under 0.4%.",
  );
  await page.getByRole("button", { name: /^This happened/ }).click();
  await waitForTheAnswer(page, SOMETHING_MOVED);
  await waitForTheLayout(page, 9);

  // The strait staying open causes the premium, so it is a claim the report is
  // evidence about. It must already be a claim the edit can reach.
  const staysOpen = page.locator('.react-flow__node[data-id="O"]');
  await expect(staysOpen.locator(".tile")).not.toHaveAttribute("data-diff", "untouched");

  // Hold the engine's next answer in flight, so the moment before it lands can
  // be looked at rather than guessed at.
  let holding = true;
  await page.route("**/api/worlds/diff", async (route) => {
    while (holding) {
      await new Promise((tick) => setTimeout(tick, 50));
    }
    await route.continue();
  });

  // Now change how hard the strait staying open pushes the premium. **It is
  // `O->C` rather than `H->C`** *(2026-09-22)*: the map gained the claim that the
  // strait *stays open* between the two, so the one arrow became two, and this is
  // the one whose source the report is evidence about.
  await openThePanelOnTheArrow(page, "O->C");
  // Asked for inside the panel of operations, by name. The Inspector's head
  // carries a control with these same words — it is the way in, and it is not
  // drawn while the panel it opens is already open — and scoping the ask here
  // says which of the two this step means whatever that rule becomes.
  await page
    .locator(".intervene")
    .getByRole("button", { name: /^Change this push/ })
    .click();
  await page.getByLabel(/How hard does this arrow push/).fill("3");
  await page.getByRole("button", { name: "Change it to that" }).click();

  // **Before the answer.** The line is already there, saying what it is waiting
  // for, and the tile is the size it will keep.
  const movement = staysOpen.locator('.tile__badge[data-badge="movement"]');
  await expect(movement).toBeVisible();
  // Word for word the sentence the engine's own absence carries while it is
  // being asked — not merely a sentence with "engine" in it, which the answer
  // has too. This is what makes the two moments below two moments.
  await expect(movement.locator(".tile__badge-words")).toHaveText("no engine yet");
  await expect(movement).toHaveAttribute(
    "title",
    /has been asked at \/api\/worlds .* and has not answered/,
  );
  const tile = staysOpen.locator(".tile");
  const whileWaiting = await tile.evaluate((el) => (el as HTMLElement).offsetHeight);

  holding = false;

  // **After the answer.** The line reads the engine's own two numbers, and the
  // tile is the same size it was: nothing grew when the answer landed.
  await expect(movement).toHaveAttribute("title", /\.\d+.*\.\d+/);
  await expect(staysOpen).not.toContainText("no engine yet");
  const said = (await movement.getAttribute("title")) ?? "";
  const readings = [...said.matchAll(/(?<![\d.])\.\d+/g)].map((one) => one[0]);
  expect(readings.length).toBeGreaterThanOrEqual(2);
  // The two are the engine's readings of this claim, and they are not the same
  // number — which is the whole point: the source moved.
  expect(readings[0]).not.toBe(readings[1]);
  // **And it moved the way the rule says it must, in the engine's own word.**
  // The claim reported as news is *the premium is under 0.4%*, and the arrow
  // retuned is the one that holds it there: the lane staying open keeps the rate
  // low, a push in favour rather than against. So news that the rate is low is
  // evidence that the lane is open, and pushing harder along that arrow can only
  // make the news say more of it — the source goes up. Which way it went is read
  // off the sentence the engine's own difference wrote rather than worked out
  // here by comparing the two numbers, and no number is written into this file
  // either way.
  await expect(movement).toHaveAttribute("title", /moved this claim up/);

  await expect
    .poll(() => tile.evaluate((el) => (el as HTMLElement).offsetHeight))
    .toBe(whileWaiting);
});

/**
 * The map keeps its arrows when the browser drops the tiles' size notifications.
 *
 * **This is the browser's own failure mode, made total and deterministic.** A
 * `ResizeObserver` is how the drawing library learns how big a thing is, and
 * when too many observations fall due in one frame the browser abandons the
 * rest — *"a ResizeObserver loop completed with undelivered notifications"* —
 * and an abandoned one is never delivered. #37 met that as tiles that never
 * appeared, and fixed it by telling the library each tile's box outright.
 *
 * **A wire needs more than a box.** It is drawn between two ports — the sockets
 * on a tile's edges — and where a port sits inside a tile used to be measured
 * through the very same notification. So with the tiles' notifications dropped
 * the map drew every claim, in its place, visible — and not one arrow. A causal
 * map is its arrows: what is left is the wrong picture of the argument, and a
 * silent one.
 *
 * **It is per tile, which is why it shows up as one missing arrow rather than
 * an empty map.** Measured, dropping one tile's notifications and keeping every
 * other: deafen the insurance premium and the arrows that touch it go, and only
 * those; deafen the strait and its own go. An arrow is not drawn when *either*
 * end was never measured. That is the shape the end-to-end suite met in the wild
 * — one arrow out of the strait absent from the glass, everything else in place
 * — about once in two hundred runs at six workers on a loaded machine.
 *
 * **Why it passes now, and why nothing is retried to make it pass.** Every
 * tile hands the drawing library its box and its four ports outright, worked
 * out by `graph/ports.ts` and written onto the tile in the same numbers, so
 * both ends of every arrow are known before the page has been measured once.
 * With the tiles deaf, this map is drawn exactly as it is drawn with them
 * hearing — which is the strongest form of the claim, and the reason nothing
 * here waits or asks again.
 *
 * The shim below drops only the tiles' notifications and lets the glass's own
 * through, because the library needs that one to draw anything at all.
 */
test("test_the_arrows_are_drawn_when_the_browser_drops_a_size_notification", async ({ page }) => {
  await page.addInitScript(() => {
    const Real = window.ResizeObserver;
    // Written as a plain function rather than a class on purpose: a private
    // field here is compiled to a helper the page has never heard of.
    function DropsTilesNotifications(given: ResizeObserverCallback) {
      const real = new Real((entries, observer) => {
        const kept = entries.filter((one) => one.target.closest(".react-flow__node") === null);
        if (kept.length > 0) {
          given(kept, observer);
        }
      });
      return {
        observe: (target: Element, options?: ResizeObserverOptions) =>
          real.observe(target, options),
        unobserve: (target: Element) => real.unobserve(target),
        disconnect: () => real.disconnect(),
      };
    }
    window.ResizeObserver = DropsTilesNotifications as unknown as typeof ResizeObserver;
  });

  await page.goto("/");
  await page
    .getByRole("button", { name: /Strait of Hormuz[\s\S]*Open the map/ })
    .first()
    .click();
  await waitForTheLayout(page, 9);

  // Every claim, visible — which is #37's half of this, and still holding.
  await expect
    .poll(() =>
      page
        .locator(".react-flow__node")
        .evaluateAll(
          (tiles) => tiles.filter((tile) => getComputedStyle(tile).visibility === "hidden").length,
        ),
    )
    .toBe(0);

  // And every arrow, by name — the same check the stored example gets with the
  // browser behaving, so that this test says *nothing changes* rather than
  // merely *something was drawn*.
  await everyArrowIsDrawn(page);
});
