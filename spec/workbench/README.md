# Workbench — what you see and touch

## The idea

The workbench is a visual-programming surface for arguments. Each proposition is a **tile**: a card with the claim, three belief chips (model / user / market), evidence clippings, and the resolve-by date — and, once the engine's day-by-day series is switched on, a small sparkline of how the likelihood moves over the window. Tiles have typed **ports**; links are **wires** whose stroke shows the signal's shape and whose weight shows its strength. A **world-state strip** shows the tradeable instruments as gauges that re-tick when you intervene, and time is a real axis on which lags are real distances — both decided (UX-3), neither drawn yet: they need numbers that move, and those arrive when the canvas is joined to the engine.

It borrows three things from simulation games: a visible world state, discrete ticks you can scrub, and the feeling that poking something has consequences you can see. It borrows one thing from mood boards: you can pin, group, and annotate tiles. It borrows nothing from component-library defaults — a template look is a veto condition.

## Terms this part owns

Workbench · Tile · Port · Wire · Inspector · Delta rail · World-state strip · Launchpad · Level of detail.

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
| [`streaming-growth.md`](streaming-growth.md) | How the map draws itself during generation: the eight stream events, skeleton tiles, growth in causal order, the refusal strip, the receipt strip, the Verify door's two cards, the input bar, the replay badge | stack 04a — written; the growing canvas is 04a's last pull request |

**"Built" here means drawn, not fed.** The canvas reads the stored example from `GET /api/fixtures/hormuz`; it does not yet ask the engine's world routes. So every chapter's *drawing* rules are built and tested, and every number a chapter says the engine would compute is on screen as an absence with its reason — "no engine yet". Joining the two is the first job of stack 04, and no component changes when it happens.

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

Kent vetoes a template-looking interface on sight, so every screenshot is checked for the template first. The chapters cite these lines by number; decision record 0007 promises this list lives here. A "no" on any line sends the work back.

1. Nothing looks like a component library's defaults — no rounded blue button, no drop shadow, no system font stack, no default focus ring.
2. There is no spinner, no pop-up, and no dialog that has to be dismissed.
3. Converted to greyscale, the screenshot still reads: every arrow still says what kind of push it is and where it came from, every direction still reads up or down, every tail still shows as texture (INV-12 — nothing is carried by hue alone).
4. No number shows more than two significant figures, and none is missing its range.
5. Every number's origin can be named in one click, and no empty slot has been filled in — a number nobody computed is an absence with a reason.
6. The map is layered left to right; it is not a hairball of crossings.
7. No text is below 11 pixels, and none is under 4.5 to 1 contrast, in either theme.
8. The tile is 280 pixels wide and on the 8-pixel grid — measured, not eyeballed.
9. Tabbing through the whole screen with the keyboard only, focus is always visible and arrow movement follows the wires.
10. With reduced motion on, the ordering is still there and the tweening is gone.
11. The six buttons and their badges are word for word the Interface words table in [`../vocabulary.md`](../vocabulary.md).
12. A claim that was supposed and then overridden says so on its tile (UX-14).
13. The map grew rather than appeared: a reserved rectangle stood where the next claim would go, no tile that was already placed moved when a later one arrived, every proposal the rules refused is on screen in the validator's own words, and the receipt says what the run cost.

Decision records behind this part: ADR-0007 (canvas technology), ADR-0012 (replay mode — with no model key the four examples run from recordings, through the same stream and the same canvas), ADR-0014 (what the range under a number means, and how a supposition ends — the words the chips and badges use).
