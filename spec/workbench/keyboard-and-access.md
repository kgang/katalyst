# Keyboard and access — everything reachable, nothing by hue alone

## Purpose

A map you can only use with a mouse is a map you can only use slowly. This chapter puts the whole workbench on the keyboard — move along the wires, open a claim, fork a branch, flip between two worlds, without your hands leaving the keys — and it does the same job for the reader who never sees the canvas at all: the map also exists as a nested list, each claim read as a sentence, and a change announces itself out loud.

It also owns one small rendering rule that carries a lot of weight. **INV-7** — honest numbers: every likelihood stays between 0 and 1 and is *shown at two significant figures with its range* — is a rule about arithmetic in the engine and a rule about pixels here. The pixel half is this chapter's: a chip never shows more than two significant figures, and never omits its range.

Three chapters sit beside this one: `color-motion-type.md` carries the colour law and the motion budget, `tiles-ports-wires.md` says what is inside a tile and how a wire is drawn, and `inspector.md` says what the panel shows. This chapter says how you reach all of it without a mouse, and how a number is spelled.

## Data model

### The key map

```ts
/**
 * UX-9, the whole of it. The keys that walk the map are bound on the canvas
 * root, not on individual tiles.
 *
 * The three at the ends of this list — ⌘K, `?` and Escape — are bound on the
 * window instead, in one module every screen calls
 * (`frontend/src/keyboard/everyKey.ts`): the first screen, the map building
 * itself, and the stored map. Two of them are how a reader finds out what the
 * others do, so a screen where they do nothing teaches nobody anything — and
 * the screen a map builds on prints *Press ? for every key* under it. The
 * first screen has no commands to offer, so ⌘K does nothing there rather than
 * opening an empty list.
 */
const KEYS = {
  "Meta+k": "openPalette",   // ⌘K — the command palette
  j: "nextSibling",          // down the column you are in
  k: "previousSibling",      // up the column you are in
  h: "backAlongAWire",       // toward causes
  l: "forwardAlongAWire",    // toward effects
  E: "intervene",            // open the intervention panel on the focused claim
  B: "branch",               // fork a branch from here
  " ": "toggleWorlds",       // Space — A ⇄ A′, a hard switch
  O: "readAsAList",          // the map as a nested list instead of a picture
  P: "showOrHideThePanel",   // give the map the whole width, and take it back
  N: "theNextPanel",         // step to the next panel beside the map
  "?": "openShortcutsSheet",
  Escape: "closeTopOverlay",
} as const;
```

`N` is bound by the switcher at the head of the panel (`frontend/src/components/PanelSwitch.tsx`) rather than by the map, because it means nothing on a screen with no panels to step between — the first screen has none, and there the key does nothing rather than doing something else. Like the map's own keys it is left alone while the keyboard is in a field: **typing is never a shortcut**, and in a field an `n` is an `n`.

### The two overlays

```ts
interface OverlayProps {
  /** The canvas keeps drawing and stays live behind it. Never a blocking scrim. */
  open: boolean;
  /** Escape always closes. Nothing is pending; closing loses nothing. */
  onClose(): void;
}
```

### The outline

```ts
/** One item per claim. Built from the world, not from what happens to be on screen. */
interface OutlineItem {
  id: string;              // "H", "C", "B", …
  sentence: string;        // the whole claim, read aloud, in one line
  children: OutlineItem[]; // the claims this one causes, in wire order
}
```

### The chip's input

The belief chip takes a **`BeliefView`**, defined once in `tiles-ports-wires.md`. It carries the number at full precision — `0.347`, not `0.35` — together with its range and its owner. A slot with no number carries an **`Absence`** rather than a blank; `Known<T>` and `Absence` are defined once in `diff-view.md`.

The chip rounds. Nothing upstream of the chip rounds. See B6.

### Tokens this chapter reads

From `frontend/src/styles/tokens.css`: **`--focus`**, the ring drawn around whatever the keyboard is on. A **contrast ratio** says how much lighter a mark is than what sits behind it; 4.5 to 1 is the floor for text, and 3 to 1 for a mark that is not text. The focus ring measures 12.1 to 1 against the dark surface and 5.7 to 1 against the light one — findable at a glance in either theme.

Also `--text` and `--text-muted` (both clear 4.5 to 1 in either theme; the measured ratio is written beside each colour in that file), `--font-mono` for every number, and `--space-hair` for the gap between a glyph and the word beside it.

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses H, C, B, R, M1, M2 and N1, the two wires between B and R, and the claim **S** that the strike branch adds. Columns are as `layout-and-zoom.md` lays them out.

The **status line** referred to below is one line under the canvas, naming what the last keystroke did (Kent, 2026-09-17, with the `h`/`l` rule in B2).

### B1 — `j` and `k` walk a column

`j` moves down, `k` moves up, within the column the focused tile is in, in the order the layout put them.

Focus **C**, in column 1 alongside N1 and R. `j` reaches N1, `j` again reaches R, `j` again does nothing — *(proposed here)* **focus does not wrap**, because wrapping quietly teleports you to the top and you lose your place. The status line says *"last claim in this column"* rather than beeping.

### B2 — `h` and `l` walk the wires, not the screen

This is the part that matters. `l` follows a wire **out** of the focused claim, toward what it causes; `h` follows a wire **in**, toward what causes it. Neither has anything to do with where a tile sits on the glass.

Focus **B**, the busiest claim on the map. Three wires come in — from H, from C, from R — and three go out — to M1, to M2, and the reflexive one back to R.

- `h` from B reaches one of {H, C, R}.
- `l` from B reaches one of {M1, M2, R}.

**R is reachable both ways, from the same tile.** `R → B` is an ordinary arrow: announced restraint props the price back above the threshold. `B → R` is the feedback arrow: a run of sub-$68 settlements pressures OPEC+ revenue. Two different wires, opposite directions, same pair of claims. And `B → R` points *leftwards* on screen, because R sits in column 1 and B in column 2 — which is exactly why movement follows wires rather than geometry. Pressing `l` on B and landing on a tile to your left is correct.

**Feedback wires count here even though they do not count in the diff.** That is not a special case; it is one rule, written once in `spec/multiverse/interventions.md` (Kent, 2026-09-17):

> *The map the engine works through is the map with feedback arrows set aside. Anything that asks **what can move** reads that map — the affected set, diff states, propagation's ordering, layering. Anything that asks **what can I walk to** reads the whole map — the hover lens, `h`/`l`, the outline.*

Moving the keyboard asks what you can walk to, so `l` from B reaches R. Working out what your edit moved asks what can move, so R comes out `untouched` on the strike branch. Same map, two questions, one rule.

**When there are several wires** (Kent, 2026-09-17), the step lands on the neighbour nearest the focused tile's own vertical position, and the *others* become the `j`/`k` set at the tile you arrive on — so `h` then `j` reaches any of them in two keystrokes and nothing on the map is unreachable. The status line names the wire you just took: *"along the feedback arrow · 14 days"*. A chooser overlay listing the wires was the alternative, and it is a pop-up in all but name.

When there is no wire in that direction, focus does not move and the status line says so. M1 and M2 cause nothing, so `l` from either is a quiet no-op, not a jump.

### B3 — `E`, `B`, `Space`, `N`, `?`

- **`E`** opens the intervention panel on the focused claim: every operation this build has, word for word from `spec/vocabulary.md`'s Interface words table — **Suppose this is true** · **Suppose this is false** · **This happened** · **Add a claim** · **Change this push** · **My own number**. A panel beside the canvas, never a pop-up. **Split this claim** is not among them: it is not built, so it is not offered — the words are settled and the control arrives with the operation. The mouse reaches the same panel from the head of the Inspector, through the control [`../vocabulary.md`](../vocabulary.md) settles as **Change this claim**. Opening it puts the keyboard inside it, which is the reader's own act rather than a theft (B4 below).
- **`B`** forks a branch from the focused claim and names it.
- **`Space`** flips A ⇄ A′ — the base world and the branch — as a **hard switch**, not a crossfade. What is painted in each is `diff-view.md`.
- **`N`** steps to the next panel beside the map *(Kent, 2026-09-22)*. Which panels a screen has is `inspector.md`; what this key adds is that they are one press apart from wherever the reader is standing, including on the map. The names at the head of the panel are also a row of labels in their own right: Tab reaches the row once, and the left and right arrow keys walk it, which is the pattern a screen reader announces as a set of panels. Both of them, and a click, are the same act — and they are the only acts other than selecting a claim or an arrow that change which panel is on the glass.
- **`?`** opens the shortcuts sheet, which lists every key above and carries the line about dragging:

  > **Tiles do not move.** The layout is automatic, left to right. Drag the background to pan, scroll to zoom. Pinning, grouping and annotating arrive as buttons, not as dragging.

### B4 — What "no pop-ups" honestly means for a command palette

UX-10 says **no modals**: one persistent Inspector, and confirmations are undoable toasts. But a command palette is conventionally the most modal thing in a product, so be exact about what we are promising.

The palette and the shortcuts sheet are **overlays, not dialogs**. Four things make that true:

1. **Nothing waits on them.** No state is half-committed while one is open. Close it and the app is exactly where it was.
2. **The canvas stays live behind.** No dimming scrim, no `inert` page, no blur. The map keeps drawing.
3. **`Escape` always closes**, as does clicking anywhere outside, as does running a command.
4. **Neither is ever the only way to do anything.** Every command in the palette is also a button or a key.

**The honest tension.** For a screen-reader or keyboard-only user, an overlay you can Tab straight out of by accident is worse than one you cannot. So while the palette is open, Tab cycles within its own list — a focus *ring*, not a barricade. Whether that ring is also declared `aria-modal="true"` in the markup is a genuine question, because the word "modal" would then be in our own accessibility tree while the product's copy says there are none. **Under Open questions.** What is not open: no dimmed page, no scrim, no "OK / Cancel", no spinner.

### B5 — Reduced motion keeps the ordering and drops the tweening

Under `prefers-reduced-motion: reduce` the interface loses the easing and keeps the sequence. **The table of what each of the three animations becomes is in `color-motion-type.md`, which owns the motion budget.**

Two things this chapter adds to it. First: **never remove the ordering. The ordering is the causality.** That the premium claim resolves after the strait claim and before the oil claim is not decoration — it is the argument, drawn in time. Dropping the stagger and revealing everything at once throws away the one piece of meaning the animation carries and keeps the pretty part.

Second: the ordering survives in the outline view too, which never had tweening to lose. A reader on the outline gets the causal order by construction — it is the shape of the tree — which is the clearest evidence that the order, not the motion, is the thing worth keeping.

`frontend/src/styles/tokens.css` already sets `--duration-fast` to `0ms` under reduced motion.

### B6 — The rendering rule that makes INV-7 visible

**Two significant figures on the number and on both ends of its range — one rule, no exceptions. Always the range. Rounded once, at the moment of paint.** Settled by Kent on 2026-09-17; `spec/graph/belief.md`'s open question 5 closes pointing at the table below.

The view model carries the number the world carries, at full precision. Only the chip rounds, and it rounds for display only — nothing downstream ever reads a rounded value. Round in the view model and you have thrown away precision the Inspector needs; round twice and `.347 → .35 → .4` and now the screen is lying by a whole step.

### The certainty guard

**A chip never prints a certainty at either end, and the guard is read off the number as it would print.** In one sentence: *what two figures would print at `1.0` or above prints `>.99`, and what they would print below `.010` prints `<.01`* — and the same guard applies, unchanged, to each end of the range.

Two things fall out of that, and both are worth saying plainly.

- The `>.99` case catches **everything from .995 upward**, including 1 itself. A likelihood of 1 is a claim that something cannot fail, and this product does not make that claim about the world. (A claim whose value an edit fixed is different: it shows the word **Supposed**, **Happened** or **Did not happen** (Kent, 2026-09-21), not a number at all — `tiles-ports-wires.md`.)
- The `<.01` case catches **everything below a hundredth** *(Kent, 2026-09-20, G10; it previously caught only exactly zero)*. `.0099` reads `<.01`; `.010` reads `.010`; `.00996` rounds up onto the line and reads `.010`. The reason is the same as the top end's: a likelihood of three thousandths is a claim this product is not entitled to make about the world, and two figures on it would dress a guess as a measurement. `<.01` says "nothing here that we can see, and we are not calling it impossible".

### A size is not a likelihood

**How far a number moved, and how wide a band is, keep two significant figures however small they get** *(Kent, 2026-09-20, G10)*. They are measured on the likelihood scale and they are not likelihoods: a move of nine thousandths is a measurement rather than a claim about the world, and `<.01` would throw out the only thing the reader came for. So the delta rail's **how firm** column and every before-and-after reading print `.0090`, `.0035`, `.00012` — and a move of exactly one prints `1.0`, because a move of one is a real move.

The two rules live in one file each and are checked against each other: `toTwoFigures` and `toSize` in `frontend/src/components/BeliefChip.tsx`, and the engine's `two_figures` in `backend/src/katalyst/domain/belief.py`, which writes the same numbers into the one-line summary the world carries and into every sentence the server sends back about a likelihood. **They are one rule written twice and must move together** — a screen and a sentence that round the same number differently are two answers to one question.

### Worked examples

| Value carried | Chip reads | Why |
|---|---|---|
| `.35` | `.35` | Already two figures |
| `.347` | `.35` | The third figure is 7, so the second rounds up |
| `.0712` | `.071` | The leading zero is not significant; 7 and 1 are |
| `.4999` | `.50` | Two figures, and the trailing zero is one of them — `.5` would claim less precision than we have |
| `.06` | `.060` | Trailing zeros stay. "Two figures except when the second is a zero" would be a second rule for one ugly case |
| `.0104` | `.010` | Two figures, both printed, and on the near side of the line |
| `.0099` | `<.01` | Two figures would print below `.010`; the lower guard fires |
| `.0035` | `<.01` | Same. Small is not the same as certain, and it is not a measurement either |
| `.995` | `>.99` | Two figures would print `1.0`; the upper guard fires |
| `.9962` | `>.99` | Same |
| `0` | `<.01` | The floor of the same rule |

And the same values printed as a **size** — a move, or the width of a band — where no guard applies. These three are chosen to exercise the rule and are nobody's reading of anything; the moves the engine actually works out on the stored example are in [`docs/worked-numbers.txt`](../../docs/worked-numbers.txt), each on its own named line:

| Value carried | Reads | Why |
|---|---|---|
| `.0089679…` | `.0090` | Two figures, and rounding up carries into a trailing zero that is printed: `.009` would claim less precision than we have |
| `.0035` | `.0035` | Two figures, however small: a measurement, not a claim about the world |
| `1` | `1.0` | A move of one is a real move, and no guard stands in its way |

A range where the guard fires on one end only: `.9962 (.988–.9995)` prints **`>.99 (.99–>.99)`**. Where it fires on both: `.9962 (.9971–.9999)` prints **`>.99 (>.99–>.99)`**. That second one is ugly, and it is correct — it says every part of this estimate sits above .99 and none of it is being called certain. At the other end the same shape: `.006 (.0002–.030)` prints **`<.01 (<.01–.030)`**, which says the low end of this band is somewhere under a hundredth without pretending to know where.

**One implementation note, because the obvious shortcut gets the decided answer wrong.** JavaScript stores .995 as 0.99499999999999999556, so `(0.995).toPrecision(2)` returns `"0.99"` — under the guard, and the chip would print `.99` where Kent's rule says `>.99`. The formatter must round the decimal value half-up rather than lean on the double. `test_chip_never_prints_a_certainty` uses .995 precisely because it is the case that catches this.

### Which form appears where

The chip on a tile is **three stacked lines**: the owner, the number, the range beneath it (`tiles-ports-wires.md` draws it). The **one-line form `.40 (.28–.55)`** is what prose, the outline view and the accessible name use — so a reader who hears the chip hears it as one phrase rather than as three disconnected fragments. Same number, same rounding, same guard; two shapes.

The three Hormuz chips, in the one-line form:

- H, the hypothesis: model `.35 (.22–.50)` · user `.55 (.40–.70)` · market **no market**.
- M1, the Polymarket contract: model `.40 (.28–.55)` · market `.48 (.45–.52)`. Eight points apart, side by side, never averaged — that gap is the trade (INV-11: model, user and market beliefs are stored and rendered separately, and no code path averages them).
- S, the strike, on the branch: model `.060 (.020–.14)`.

The chip never drops its range to fit. If the space is too narrow for `.40 (.28–.55)`, the space gets wider — the range does not go. A number without its range is the fake-precise percentage the whole product is arguing against.

The range means one specific thing and the chip's label says which: **how sure we are of the number, not how much the world can move.** That label, and the sentence behind it on hover, are written out word for word in `tiles-ports-wires.md`.

### B7 — The outline view

The map also exists as a nested list with `role="tree"` — the standard markup for a collapsible hierarchy, so a screen reader announces levels and lets you walk them with arrow keys. It is not a fallback; it is the same world, read rather than drawn.

**A map is not a tree**, so the outline is a spanning tree: start at the hypothesis, walk out along wires in the order the map lists them, and give each claim **exactly one item**, at its first arrival. A claim with several causes does not appear twice — instead its sentence names every incoming wire. Nothing is lost and the tree stays a tree. Claims with no incoming wire at all are roots; the hypothesis is always the first of them, and on the strike branch **S** is the second.

Each item reads as a sentence. `trigger` arrows read **caused by**; `sustain` arrows read **held up by**; a negative strength reads **pushed the other way by**. Mode and sign arrive in words, so nothing here depends on seeing anything.

**A claim with no market price** reads "no market" and then the reason, which is chosen by the claim's kind (Kent, 2026-09-17; the words live once in `spec/vocabulary.md`). A `market` claim: *"no venue quotes this claim; what you would trade is on the payoff."* An `event` or `hypothesis`: *"no venue quotes this claim."* A `not_tradeable` ending keeps **its own stored reason**, because that one is a finding rather than an absence. The tile itself says only `no market`; the reason belongs to the Inspector, the hover, and this sentence.

The Hormuz map, spoken:

> **H** — *"The Strait of Hormuz reopens to unrestricted commercial transit. Model .35, range .22 to .50. Your own number .55, range .40 to .70. No market — no venue quotes this claim. The hypothesis — nothing on this map causes it. Three claims follow."*
> - **B** — *"Brent crude settles below $68 for five sessions. Model .28, range .15 to .42. Caused by the strait reopening, two days later. Held up by the war-risk premium falling. Pushed the other way by OPEC+ restraint. Three claims follow."*
>   - **M1** — *"A Polymarket contract, Brent below $70 on the 31st of October, resolves yes. Model .40, range .28 to .55. Market .48, range .45 to .52. A tradeable ending. Caused by Brent settling below $68, one day later."*
>   - **M2** — *"The energy fund XLE underperforms the S&P 500 fund SPY by more than 3 per cent over 20 trading days. Model .35, range .22 to .50. No market — no venue quotes this claim; what you would trade is on the payoff. A tradeable ending. Caused by Brent settling below $68, three days later."*
>   - **R** — *"OPEC+ announces output restraint. Model .18, range .080 to .32. Fed back into by Brent settling below $68, fourteen days later. It pushes back on Brent, already listed above."*
> - **C** — *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4 per cent. Model .30, range .18 to .45. Held up by the strait reopening, the same day. It reaches Brent crude, already listed above."*
> - **N1** — *"Omani-mediated United States–Iran talks resume publicly. Model .22, range .12 to .36. Not tradeable — no venue quotes a contract on a diplomatic round. Caused by the strait reopening, ten days later."*

A claim sitting behind a **"+n more"** tile (`layout-and-zoom.md`) still gets its item. The outline is built from the world, never from what happens to be painted — which is also why activating a "+n more" tile opens **this view, filtered to that column** (Kent, 2026-09-17). The collapsed claims already have items here; the tile just points at them.

### B8 — What the announcement can honestly say, today

When a branch re-propagates, an `aria-live="polite"` region speaks one line. Polite means it waits for a pause rather than cutting across what is being read.

**The line is said twice, because the two facts arrive at different moments.** What the edit did to the *shape* of the map is known the instant the branch opens; what it did to the *numbers* comes back from the engine seconds later. A reader who cannot see the screen needs both, and needs to be told that the second is coming rather than left wondering whether it is missing.

> *"Branch created. One claim added, <n> claims your edit can reach, one supposition retracted. The numbers are on their way from the engine."*

> *"Branch created. One claim added, <n> claims moved, one supposition retracted."*

**Every count comes from somewhere nameable.** The **added** count and the **your edit can reach** count are structure, computed from the branch by the reducer in `diff-view.md` with no arithmetic at all — on the strike branch that is S added, and R left out, because the only wire that could carry the edit to R is a feedback arrow and the diff sets those aside. The **moved** count is the engine's own word, one per claim, read off its difference. The **retracted** count is UX-14's, which `tiles-ports-wires.md` renders on H's tile.

**The browser never counts moved claims by comparing two numbers.** It reads how many claims the engine called `shifted`. That is why the two lines can differ — a claim the edit can reach is a claim that *could* move, and the engine decides whether it did — and why a reader hearing a smaller second number is hearing a real finding rather than a bug.

### B9 — Focus, contrast, and nothing by hue alone

Focus is **always** visible, drawn with `--focus`, on every interactive thing — tiles, chips, wires, buttons, palette rows, outline items. `outline: none` appears nowhere in the tree. Tab order follows the map's reading order, and Tab alone reaches everything.

All text and all glyphs clear **4.5 to 1** against the surface behind them, in the dark theme and the light one. `tokens.css` writes the measured ratio in a comment beside every colour, so the claim is checkable by reading the file rather than by trusting it.

**INV-12 — nothing is carried by hue alone.** Every direction of financial effect has a glyph and a sign as well as a hue; every tail risk is a hatch texture rather than a colour; every provenance is a three-step mark at the wire's tail. **The law itself lives in `color-motion-type.md`** — this chapter only depends on it, and the outline view is its strictest test: a rendering with no colour at all that still says everything.

### B10 — The fifth build job

The INVARIANTS table below names every test in this chapter. Two notes on top of it.

`frontend/src/components/__tests__/beliefChip.test.tsx` is the one test that holds **NFR-1** (honesty: beliefs render at two significant figures with their interval, never `.347`) upright. Nothing else in the tree stops a fake-precise number reaching the screen.

The build grows a fifth job, **`e2e`**, running the single Playwright test `frontend/e2e/hormuz.spec.ts`. **It has no model API key in its environment** — **INV-13**: the whole build runs with no model key, and the model boundary is exercised only through recorded responses. The `e2e` job needs none, because the screen it drives is fed by `GET /api/fixtures/hormuz`, which is a stored example and calls no model.

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it. "Visual review checklist `VRn`" is the line named `VRn` in the visual review checklist in [`README.md`](README.md) — a checklist line is a checkable thing; it is checked by a person.

| ID | Statement | Checked by |
|---|---|---|
| **INV-workbench.31** | For every interactive element in the app, it is reachable and operable with the keyboard alone | `frontend/e2e/hormuz.spec.ts`; visual review checklist `VR9` (tab through the whole screen) |
| **INV-workbench.32** | For every focused element, a focus ring drawn with `--focus` is visible against the surface behind it, in both themes | visual review checklist `VR9`; `frontend/e2e/hormuz.spec.ts` |
| **INV-workbench.33** | For every focused claim and every press of `h` or `l`, the claim focus lands on is joined to it by a wire; focus never moves to a claim that is merely nearby on screen | `test_h_and_l_land_only_on_a_wired_neighbour` in `frontend/src/keyboard/__tests__/focusMap.test.ts`; visual review checklist `VR9` (does arrow movement follow the wires?) |
| **INV-workbench.34** | For every overlay in the app, `Escape` closes it, the canvas stays live behind it, and nothing is left pending by closing it — there is no dialog anywhere that must be dismissed | visual review checklist `VR2` (is there a spinner, a pop-up, or a dialog you must dismiss?) |
| **INV-workbench.35** | For every animation, under `prefers-reduced-motion: reduce` the ordering is preserved and the tweening is absent | visual review checklist `VR10` |
| **INV-workbench.36** | For every belief rendered anywhere in the app, the chip shows two significant figures on the number and on both ends of its range, always shows the range, and prints no likelihood that two figures would put at `1.0` or above or below `.010` — those print `>.99` and `<.01`. A **size** — how far a number moved, how wide a band is — takes two figures and no guard | `test_chip_never_shows_more_than_two_significant_figures`, `test_chip_never_omits_the_range`, `test_chip_never_prints_a_certainty`, `test_the_lower_guard_begins_at_a_hundredth` and `test_a_size_is_not_a_likelihood_and_takes_no_guard`, all in `frontend/src/components/__tests__/beliefChip.test.tsx`; visual review checklist `VR4` |
| **INV-workbench.37** | For every belief, the view model carries the full precision the world carried, and rounding happens exactly once, in the chip, at paint | `test_the_view_model_keeps_full_precision` in `beliefChip.test.tsx` |
| **INV-workbench.38** | For every piece of text and every glyph, in both themes, the contrast ratio against the surface behind it is at least 4.5 to 1 | visual review checklist `VR7` |
| **INV-workbench.39** | For every claim in the world there is exactly one outline item, its sentence names every incoming wire, and the announcement names no number the world does not carry | `frontend/e2e/hormuz.spec.ts`; visual review checklist `VR5` (is there a number nobody computed?) |

## ANTI-PATTERNS

1. **Do not build the palette as a dialog over a dimmed page**, because a scrim and an "OK / Cancel" is the template look and the pop-up veto in one move. Build an overlay that closes on `Escape`, holds nothing pending, and lets the canvas keep drawing behind it.
2. **Do not move focus by screen geometry**, because the tile nearest your arrow key is often not connected to the one you are on, and a map's meaning is its wires. Follow the wires, and say which wire you took.
3. **Do not drop the ordering under reduced motion**, because the ordering *is* the causality — it is the one thing the animation was carrying. Drop the easing; keep the sequence.
4. **Do not round in the view model**, because the Inspector needs the precision the chip threw away, and a number rounded twice drifts a whole step. Carry the full number; round once, in the chip, at paint.
5. **Do not drop the range when the space is tight**, because a bare `.40` is the fake-precise number this product exists to argue against. Widen the space.
6. **Do not print `1.0` or `.0` on a chip**, because a likelihood of one is a claim that something cannot fail and this product does not make that claim. Print `>.99` and `<.01`, on the range's ends as well as on the number.
7. **Do not say a claim changed before the engine has said it did, and do not count the ones that did by comparing two numbers**, because a count nobody computed is a state nobody can trace, and a second count is a second answer. While the engine is being asked, say what is true — added, reachable, retracted — and say out loud that the numbers are coming. Afterwards, count the claims the engine itself called moved.
8. **Do not build the outline from the tiles on screen**, because a claim behind a "+n more" tile would silently vanish for the reader who needs the outline most. Build it from the world.
9. **Do not lean on hue for anything**, because roughly one reader in twelve will not see the difference and a greyscale screenshot is `VR3` of the visual review checklist. Every direction gets a glyph, every tail a texture, every provenance a mark.
10. **Do not write `outline: none`**, anywhere, for any reason. A focus ring you cannot see is a keyboard interface you cannot use. Restyle the ring with `--focus`; never remove it.

## Open questions

*Dated 2026-09-17. Each is something the plan does not settle; none is decided here.*

1. **Is the palette's focus ring declared `aria-modal="true"`?** Trapping Tab is right for the reader who needs it most; putting the word "modal" in our accessibility tree while the product's copy says there are no modals is uncomfortable. The visual rule is not open — no scrim, no dismissal — only the markup.
2. **Does `j`/`k` wrap at the end of a column?** B1 proposes not, because wrapping teleports you. Unsaid.
3. **Is there an announcement for ordinary focus movement?** The outline reads a claim when you land on it, but a sighted keyboard user moving quickly along wires gets only the status line. Whether that line is also an `aria-live` region, or whether that would be unbearable chatter, is untested.
4. **How is the outline reached?** `role="tree"` markup exists in the page; whether it is always present and visually hidden, toggled by a key, or a panel beside the canvas is unsaid. The plan says only that it exists — and now that a "+n more" tile opens it filtered, at least one route in is settled.

**Decided 2026-09-17 and now in the body:** the rounding rule, both range ends, and the certainty guard (B6) · which form of the chip appears where (B6) · how `h`/`l` picks among several wires, and the status line it writes to (B2) · that navigation follows every wire including feedback ones, under the one rule in `spec/multiverse/interventions.md` (B2) · where the reason beside an empty market slot comes from (B7).
