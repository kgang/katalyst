# Workbench — what you see and touch

## The idea

The workbench is a visual-programming surface for arguments. Each proposition is a **tile**: a card with the claim, three belief chips (model / user / market), a small distribution sparkline when the claim is quantitative, evidence clippings, and the resolve-by date. Tiles have typed **ports**; links are **wires** whose stroke shows the signal's shape and whose weight shows its strength. A **world-state strip** shows the tradeable instruments as gauges that re-tick when you intervene. Time is a real axis; lags are real distances.

It borrows three things from simulation games: a visible world state, discrete ticks you can scrub, and the feeling that poking something has consequences you can see. It borrows one thing from mood boards: you can pin, group, and annotate tiles. It borrows nothing from component-library defaults — a template look is a veto condition.

## Terms this part owns

Workbench · Tile · Port · Wire · Inspector · Delta rail · World-state strip · Launchpad · Level of detail.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-8 | Any displayed path shows the product of its link probabilities beside the narrative headline |
| INV-12 | No information is encoded in hue alone: every direction has a glyph, every tail a texture, every provenance a stroke style |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| `tiles-ports-wires.md` | Tile anatomy, port types, wire encodings, the conditional-probability chip | stack 03b |
| `layout-and-zoom.md` | Automatic layered layout, stable incremental re-layout, level of detail by zoom | stack 03b |
| `diff-view.md` | Ghost overlay of two worlds in a shared layout, the delta rail, A ⇄ A′ toggle | stack 03b |
| `inspector.md` | The persistent side panel: rationale, sources, base rate, three beliefs, "falsified if" | stack 03b |
| `color-motion-type.md` | The color law, the three budgeted animations, typography | stack 03b |
| `keyboard-and-access.md` | Keyboard map, outline view for screen readers, reduced motion, contrast | stack 03b |
| `streaming-growth.md` | How the map draws itself during generation | stack 04 |

Decision records behind this part: ADR-0007 (canvas technology).
