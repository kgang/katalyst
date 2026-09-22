# Workbench — what you see and touch

## The idea

The workbench is a visual-programming surface for arguments. Each proposition is a **tile**: a card with the claim, three belief chips (model / user / market), evidence clippings, and the resolve-by date — and, once the engine's day-by-day series is switched on, a small sparkline of how the likelihood moves over the window. Tiles have typed **ports**; links are **wires** whose stroke shows the signal's shape and whose weight shows its strength. A **world-state strip** shows the tradeable instruments as gauges that re-tick when you intervene, and time is a real axis on which lags are real distances — both decided (UX-3), neither drawn yet: they need numbers that move, and those arrive when the canvas is joined to the engine.

It borrows three things from simulation games: a visible world state, discrete ticks you can scrub, and the feeling that poking something has consequences you can see. It borrows one thing from mood boards: you can pin, group, and annotate tiles. It borrows nothing from component-library defaults — a template look is a veto condition.

## Terms this part owns

Workbench · Tile · Port · Wire · Inspector · Delta rail · World-state strip · Launchpad · Level of detail · Skeleton tile · Refusal strip · Receipt strip · Replay badge.

The last four belong to a map that is being generated and are defined, with the button that starts one, in [`../vocabulary.md`](../vocabulary.md).

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-8 | Any displayed path shows the multiplied-out likelihood of its steps beside the narrative headline |
| INV-12 | No information is encoded in hue alone: every direction has a glyph, every tail a texture, every provenance a mark — a three-step origin mark at the wire's tail, never the stroke, which says the kind of push and nothing else |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`tiles-ports-wires.md`](tiles-ports-wires.md) | Tile anatomy, port types, wire encodings, the chip at a wire's midpoint | stack 03b — written, canvas built |
| [`layout-and-zoom.md`](layout-and-zoom.md) | Automatic layered layout, stable incremental re-layout, level of detail by zoom | stack 03b — written, canvas built |
| [`diff-view.md`](diff-view.md) | Ghost overlay of two worlds in a shared layout, the delta rail, A ⇄ A′ toggle | stack 03b — written, canvas built |
| [`inspector.md`](inspector.md) | The persistent side panel: rationale, sources, base rate, three beliefs, "falsified if" | stack 03b — written, canvas built |
| [`color-motion-type.md`](color-motion-type.md) | The color law, the three budgeted animations, typography | stack 03b — written, built bar the number-roll, which has nothing to roll until a number changes |
| [`keyboard-and-access.md`](keyboard-and-access.md) | Keyboard map, outline view for screen readers, reduced motion, contrast | stack 03b — written, canvas built |
| [`streaming-growth.md`](streaming-growth.md) | How the map draws itself during generation: the eight stream events, skeleton tiles, growth in causal order, the refusal strip, the receipt strip, the Verify door's two cards, the input bar, the replay badge | stack 04a — written, canvas built |
| [`first-screen.md`](first-screen.md) | The screen a reader meets first: four ways to start, the same with a key and without one, each saying what it costs and why it cannot be taken | stack 04c — written, not built |

**"Built" here now means fed and grown as well as drawn.** The canvas reads the map from `GET /api/fixtures/hormuz` and asks the engine's three world routes for everything computed: `POST /api/worlds` for a world, `POST /api/worlds/diff` for what an edit moved, and `POST /api/worlds/conditional` for the number on one arrow, asked one arrow at a time. And it reads `POST /api/generate` as a stream, folding the eight events into a map as they arrive. So the numbers on screen are the engine's own, worked out from the map, the branch and one seed — whether the map was stored or written a minute ago.

**What is still an absence, and why, is the part worth reading.** A number nobody has worked out is still never drawn: while the engine is being asked, while it is refusing a branch that does not fit the map, while a map is still growing and no likelihood has been worked through, and where the engine carries nothing at all — a chain's multiplied-out likelihood (INV-8) is on no world, only on the Verify door's own verdict — the slot holds words and a reason, exactly as it did before. And when the engine cannot be reached the stored example stands in, with a line under the map saying so in the failure's own words. Joining the two was the first job of stack 04, and no component changed when it happened.

## The worked example

Every chapter in this part works its examples on one map: the Strait of Hormuz, served by `GET /api/fixtures/hormuz` and written out, with a reason beside every number, in `backend/src/katalyst/fixtures/hormuz.py`. That file is the source of truth; this table is the cast, so a chapter can say "B" and be understood.

| Letter | Kind | The claim, in the fixture's words |
|---|---|---|
| **H** | hypothesis | The Strait of Hormuz reopens to unrestricted commercial transit. |
| **C** | event | Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%. |
| **B** | event | Brent crude settles below $68 for five sessions. |
| **R** | event | OPEC+ announces output restraint. |
| **M1** | market | A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES. |
| **M2** | market | The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days. |
| **N1** | not tradeable | Omani-mediated United States-Iran talks resume publicly. |
| **S** | event — added by the branch | A confirmed military strike on Iranian territory. |

**Eight arrows on the base map.** `H → B`, `H → C`, `H → N1`, `C → B`, `B → M1`, `B → M2`, `R → B`, and one that feeds back: `B → R`, a *reflexive* arrow — a market reacting on the world it measures — which always carries a delay. `R → B` is the only one that pushes against its target. `H → N1` is the only one the model merely asserted; the rest are argued.

**One branch,** labelled "Hormuz opens, then Iran is struck" (`br_hormuz_then_strike`), with three edits in order: suppose H is true from Oct 1; add S with three arrows, `S → B`, `S → C` and `S → H`, all pushing against their targets; suppose S is true from Oct 2. Because `S → H` was added *after* H was supposed, it is live — which is what lets the strike retract the strait's opening, and what UX-14's badge exists to say.

## Visual review checklist

Kent vetoes a template-looking interface on sight, so every screenshot is checked for the template first. Decision record 0007 promises this list lives here. A "no" on any line sends the work back.

**Each line has a name — `VR1` to `VR14`, for *visual review* — and that name is how a chapter cites it.** A name survives the list growing: insert a fifteenth check between two of these and every citation still points at the check it meant, where a position would quietly slide by one. The names are in the list's own order, so `VR8` is the eighth line and an older citation reading *"visual review checklist line 8"* means the same check. Those older citations are renamed as each chapter is next edited for another reason, never as a sweep of its own.

1. **VR1** — Nothing looks like a component library's defaults — no rounded blue button, no drop shadow, no system font stack, no default focus ring.
2. **VR2** — There is no spinner, no pop-up, and no dialog that has to be dismissed.
3. **VR3** — Converted to greyscale, the screenshot still reads: every arrow still says what kind of push it is and where it came from, every direction still reads up or down, every tail still shows as texture, and every tile still says what kind of claim it is — its silhouette, and the kind spelled out in its heading *(added 2026-09-22, when the two kinds at the ends of a map took a hue as well)* (INV-12 — nothing is carried by hue alone).
4. **VR4** — No number shows more than two significant figures, and **no range appears anywhere on the screen**: not under a chip, not in the panel, not on the change list, not in the sentence under the map *(rewritten 2026-09-22 — it read "and none is missing its range" until Kent's R48 cut the range from this product)*.
5. **VR5** — Every number's origin can be named in one click, and no empty slot has been filled in — a number nobody computed is an absence with a reason.
6. **VR6** — The map is layered left to right; it is not a hairball of crossings.
7. **VR7** — No text is below 11 pixels, and none is under 4.5 to 1 contrast, in either theme.
8. **VR8** — The tile is 280 pixels wide and on the 8-pixel grid — measured, not eyeballed.
9. **VR9** — Tabbing through the whole screen with the keyboard only, focus is always visible and arrow movement follows the wires.
10. **VR10** — With reduced motion on, the ordering is still there and the tweening is gone.
11. **VR11** — The six buttons and their badges are word for word the Interface words table in [`../vocabulary.md`](../vocabulary.md).
12. **VR12** — A claim that was supposed and then overridden says so on its tile (UX-14).
13. **VR13** — The map grew rather than appeared: a reserved rectangle stood where the next claim would go, no tile that was already placed moved when a later one arrived, every proposal the rules refused is on screen in the validator's own words, and the receipt says what the run cost.
14. **VR14** — No tile draws a belief column with no number in it: the reader's and a venue's are there only where they hold one, and the reasons they are not are read in the panel. (The model's column is the exception that proves it: while a map is still being built it stands alone saying *no engine yet*, because nothing has been worked through the map. On a finished map every column on every tile has a number in it.)

**Part of this list is now checked by a machine, at three windows, and none of it by a stored picture.** `frontend/e2e/hormuz.spec.ts` opens the stored map at 1600 × 1000, 1440 × 900 and 1280 × 800 with a branch open and the operations open, and asks three questions of **every button, link and field in the panel beside the map**: it is drawn at a size at all; scrolled to, it lies inside the part of the panel that is on the glass; and **at its own centre the topmost thing on the screen is that control** — which is the one of the three that catches a sibling drawn over a button. Scrolled out of view is fine and is why each control is scrolled to first: the panel scrolls as one and marks its edges. **A fourth question is asked of the panel itself: its content is no wider than the panel is on the glass.** The first three cannot see a field that runs past the right edge, because a box that scrolls up and down also scrolls sideways unless told not to, and scrolling to the field slides the whole panel left until the field measures as inside. It also asserts that the page never scrolls sideways, which is the only measurement here that changes with the window, since the panel is a fixed 336 pixels and the stage beside it takes the rest. And it asserts that an item in the map-read-as-a-list is wider than a third of the list, which is the collapse that made the no-picture route unusable below 1600.

**What that does and does not cover.** It covers *the second half of `VR2`* — no control in the panel is hidden behind anything — and the readability of the list. It does not cover the map: tiles, wires and plates overlapping each other are checked by the layout's own tests and by eye. It does not touch `VR1` (the template), `VR3` (greyscale), `VR7` (contrast) or `VR8` (the eight-pixel grid), all of which still need a person and a picture. **A stored screenshot is deliberately not used**: a pixel baseline over a canvas with a background-threaded layout engine, two variable fonts and an arrival animation fails for reasons that are not faults, and this project has already paid for chasing those.

Decision records behind this part: ADR-0007 (canvas technology), ADR-0012 (replay mode — with no model key an example runs from a committed recording, through the same stream and the same canvas; one is committed, and a card with nothing recorded says so), ADR-0014 (how a supposition ends, and how wide an arrow's push is drawn — the words the badges and origin marks use. **Its range half no longer holds**: Kent's R48, 2026-09-22, cut the range and the two thousand versions of the map it came from, and the record's own amendment is the stack 05 session's).
