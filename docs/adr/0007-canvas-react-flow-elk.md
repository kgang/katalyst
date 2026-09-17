---
# ADR-0007: Build the Workbench canvas on React Flow v12 with ELK layered layout
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/03-ui-ux-directions.md, docs/research/04-engineering-structure.md
informed: future agents working in frontend/src/graph
supersedes: none
superseded-by: none
spec-impact: spec/workbench/ (all sections), spec/multiverse/ (diff rendering)
---

# ADR-0007: Build the Workbench canvas on React Flow v12 with ELK layered layout

## Context and Problem Statement

The canvas is the product's first screen (D1, the hero use case). It must render 10–60 rich proposition tiles with typed ports and wires (UX-1, UX-2), grow while the model streams (UX-8), show two worlds at once as a faded-overlay diff (FR-16), and look nothing like a component-library demo (D5(i), the template-UI veto). Which drawing and layout libraries give one developer the most beauty per hour without fixing the look?

## Decision Drivers

* D3, the Workbench aesthetic: the rigor of a visual-programming tool × tiles rich with evidence × a simulation game's sense of world state.
* D5(i): a template-looking UI is a veto condition — we own every pixel.
* UX-4: detail changes with zoom, and text never shrinks below 11 px.
* UX-5: automatic layout by default; a re-layout keeps the focused tile where it sits on screen.
* UX-7: exactly three animations; everything else is opacity in ≤120 ms.
* FR-16 / INV-4 (an intervention changes only what lies downstream of it): the diff must show *only* what moved, in one stable shared layout.
* NFR-7: 60 tiles render and re-layout in under 100 ms.

## Considered Options

* A. **`@xyflow/react` (React Flow v12, a React library for node-and-wire canvases) + `elkjs` (ELK, an automatic graph-layout engine, compiled to JavaScript) + Motion, a React animation library**
* B. tldraw SDK 4.x — an infinite-whiteboard toolkit.
* C. d3 with d3-dag and a hand-written SVG renderer.
* D. Sigma.js, which draws graphs on the graphics card (WebGL).
* E. Fully custom canvas/SVG drawing.

## Decision Outcome

Chosen option: "A", because tiles stay ordinary React components — rich content, our typography, our tokens — while the library owns only panning, zooming, hit-testing and port handles, and ELK's layered algorithm handles branch fans and stable incremental layout that the older `dagre` library cannot.

Concretely:

* Import `@xyflow/react/dist/base.css` only — never `style.css`, which carries the library's own look. All visual styling is ours (D5(i)).
* Tiles are custom node types, fixed at 280 px wide with clamped height, so ELK can lay out before the browser finishes measuring them. Four silhouettes carry the proposition's `kind` (hypothesis, event, market, not-tradeable).
* Ports are typed handles: one input group, one output group. `sustain` and `trigger` wires attach to distinct handle ids, so a wire's meaning is visible at the socket.
* Wires are custom edges: stroke pattern encodes `shape` (impulse dot-dash, step solid, ramp gradient), stroke width encodes strength regardless of sign, a double stroke marks `sustain`, and a `reflexive` link loops back with a lag chip. The midpoint chip shows the conditional probability in the arrow-and-bar idiom of the forecasting site Metaculus, drawn through React Flow's `EdgeLabelRenderer`.
* Layout: ELK `layered`, `elk.direction: RIGHT`, `nodePlacement.strategy: NETWORK_SIMPLEX`, `crossingMinimization.semiInteractive: true`, `spacing.nodeNodeBetweenLayers: 120`, run in a Web Worker — a background browser thread, so layout never freezes the interface. Already-placed nodes are pinned by `elk.position`, so a newly streamed tile never reshuffles an existing layer. `fitView` frames the graph on first load only; after that `setCenter` follows the focused tile.
* Diff: lay out the union of both worlds once, then draw the new world at full opacity and the old at 20 % dashed in the same coordinates. Each node carries a diff state — `unchanged | shifted | added | killed` — that drives its styling.
* Detail by zoom: below 0.6 zoom a tile switches to a summary (claim + belief chips); text never scales below 11 px.
* Animation (Framer Motion) is spent on exactly the three budgeted moves: the propagation wave (wires draw in causal order, ~200 ms, 60 ms apart), branch creation, the belief number-roll. When the operating system asks for reduced motion (`prefers-reduced-motion`), ordering stays and tweening goes.
* The Inspector is a persistent side panel; there are no modals (UX-10). The UX-9 keyboard map lives on the canvas root, with arrow keys travelling along wires rather than across screen space.
* Tiles are not draggable in v1. Organizability (UX-5's pin, group, annotate) arrives as explicit actions, not free drag, until drag can be supported fully.

### Consequences

* Good, because tiles are React: sparklines, evidence clippings, three-up belief chips and our fonts are just JSX.
* Good, because ELK's layout is deterministic and layer-aware; pinning keeps streaming growth calm, not jumpy.
* Bad, because ELK costs about half a day of configuration and runs 50–150 ms on 60 nodes — hence the background thread.
* Bad, because React Flow's default look leaks easily; the `base.css`-only rule and a lint check guard it.
* Neutral, because React Flow is MIT-licensed for our use — free, including commercially — so no licence question arises, unlike tldraw.

### Confirmation

* `frontend/src/graph/__tests__/layout.test.ts` — pinned nodes keep their positions across an incremental layout, and the union layout used for a diff is stable.
* `frontend/src/graph/__tests__/diffState.test.ts` — the reducer maps a pair of worlds to `unchanged | shifted | added | killed` per INV-4.
* One end-to-end browser test (Playwright, a browser-automation tool): seed a hypothesis, tiles stream in, intervene — downstream tiles change, upstream tiles stay byte-identical.
* A visual review checklist in `spec/workbench/`, mapped to UX-1 through UX-13 and INV-12 (nothing encoded in hue alone: blue ▲ / amber ▼ with a glyph, hatching for tails, a dashed stroke for `asserted`).
* Lint rule: importing `@xyflow/react/dist/style.css` fails the `frontend` job in continuous integration.

## Pros and Cons of the Options

### A. React Flow + ELK + Motion (chosen)

* Good, because the highest beauty ceiling per hour; tiles are ordinary page elements, styling is ours, layout engine swappable.
* Bad, because it demands re-render discipline: memoized nodes, shallow store selectors.

### B. tldraw

* Good, because a polished infinite canvas out of the box.
* Bad, because a whiteboard's mental model, renderer and state fight a typed, loop-free graph; embedding it in production also needs a commercial licence.

### C. d3 + d3-dag custom

* Good, because the ceiling is unbounded — bespoke ribbons and all.
* Bad, because panning, zooming, hit-testing, selection and accessibility are all rebuilt by hand: weeks, not days.

### D. Sigma.js

* Good, because it handles 10,000+ nodes.
* Bad, because a node is a circle with a weak label — the wrong scale for 60 rich tiles.

### E. Custom canvas

* Bad, because everything above, plus no ecosystem.

## More Information

* **Amended 2026-09-17, when stack 03b's chapters were written.** Three details above have moved on, and the chapters in `spec/workbench/` are where they now live. (1) The animation library is published as `motion` — the same library and author as Framer Motion, under its current name. (2) Provenance is carried by a three-step origin mark at the wire's tail, not by a dashed stroke: the stroke already says what kind of push an arrow carries, and one channel cannot carry two meanings (`spec/workbench/color-motion-type.md`). (3) Until the engine's world route is switched on, the diff reducer reads a base map plus a branch — not a pair of worlds — and gives four structural states, `added | killed | downstream | untouched`; `shifted` joins them when the numbers arrive, and the engine's own difference keeps the four states named above (`spec/workbench/diff-view.md`, `spec/multiverse/diff.md`). The visual review checklist now maps to UX-1 through UX-14.
* Interview D3 (Workbench aesthetic) and D5(i) (template veto).
* `docs/research/03-ui-ux-directions.md` §1 (technology comparison and ELK settings), §2 (ghost overlay, delta rail), §5 (anti-patterns), §6 (accessibility).
* React Flow layouting: https://reactflow.dev/learn/layouting/layouting · ELK example: https://reactflow.dev/examples/layout/elkjs
