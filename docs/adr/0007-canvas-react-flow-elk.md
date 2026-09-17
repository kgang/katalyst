---
# ADR-0007: Build the Workbench canvas on React Flow v12 with ELK layered layout
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/03-ui-ux-directions.md, docs/research/04-engineering-structure.md
informed: future agents working in frontend/src/graph
supersedes: none
superseded-by: none
spec-impact: spec/04-canvas.md (all sections), spec/02-interventions.md (diff rendering)
---

# ADR-0007: Build the Workbench canvas on React Flow v12 with ELK layered layout

## Context and Problem Statement

The canvas is the product's first screen (D1) and must render 10–60 rich proposition tiles with typed ports and wires (UX-1, UX-2), grow while streaming (UX-8), show two worlds as a ghost-overlay diff (FR-16), and still look nothing like a component-library demo (D5(i)). Which rendering and layout stack gives the highest beauty-per-hour for one developer without locking the look?

## Decision Drivers

* D3: visual-programming rigor × rich tiles × simulation-game world state.
* D5(i): template UI is a veto condition — we must own every pixel.
* UX-4: level of detail by zoom without shrinking text below 11px.
* UX-5: auto-layout by default; re-layout preserves the focused tile's screen position.
* UX-7: exactly three animations; everything else ≤120 ms opacity.
* FR-16 / INV-4: the diff must show *only* what moved, in a stable shared layout.
* NFR-7: 60 tiles render and re-layout in <100 ms.

## Considered Options

* A. **`@xyflow/react` (React Flow v12) + `elkjs` layered layout + Motion**
* B. tldraw SDK 4.x
* C. d3 + d3-dag with a custom SVG renderer
* D. Sigma.js (WebGL)
* E. Fully custom Canvas/SVG

## Decision Outcome

Chosen option: "A", because tiles are ordinary React components (rich content, our typography, our tokens), the library owns only pan/zoom/hit-testing/handles, and ELK's layered algorithm handles branch fans and stable incremental layout that dagre cannot.

Concretely:

* Import `@xyflow/react/dist/base.css` only — never `style.css`. All visual styling is ours (D5(i)).
* Tiles are custom node types with fixed width (280 px) and clamped height so ELK can lay out before measurement settles. Four silhouettes carry `kind` (hypothesis, event, market, not-tradeable).
* Ports are typed handles: one input port group, one output port group; `sustain` and `trigger` wires attach to distinct handle ids so the wire's semantics are visible at the socket.
* Wires are custom edges: stroke pattern encodes `shape` (impulse dot-dash, step solid, ramp gradient), stroke width encodes |strength|, double stroke for `sustain`, a looped path with a lag chip for `reflexive`. The midpoint chip renders the conditional in the Metaculus arrow-and-bar idiom via `EdgeLabelRenderer`.
* Layout: ELK `layered`, `elk.direction: RIGHT`, `nodePlacement.strategy: NETWORK_SIMPLEX`, `crossingMinimization.semiInteractive: true`, `spacing.nodeNodeBetweenLayers: 120`; run in a Web Worker; already-placed nodes pinned by `elk.position` so streaming a new tile never reshuffles an existing layer. `fitView` on first load only; afterwards `setCenter` on the focused tile.
* Diff: lay out the union of A and A′ once; render A′ at full opacity and A at 20 % dashed in the same coordinates; nodes carry a diff state (`unchanged | shifted | added | killed`) that drives styling.
* LOD: below 0.6 zoom, tiles switch to a summary representation (claim + belief chips); text never scales below 11 px.
* Motion (Framer Motion) is used for exactly the budgeted three: propagation wave (wires draw in causal order, ~200 ms, 60 ms stagger), branch creation, belief number-roll. `prefers-reduced-motion` drops tweening, keeps ordering.
* Inspector is a persistent side panel; there are no modals (UX-10). Keyboard map per UX-9 is implemented on the canvas root, with arrow traversal along wires, not screen space.
* Nodes are non-draggable in v1; organizability (UX-5 pin/group/annotate) is delivered as explicit actions, not free drag, until drag can be fully supported.

### Consequences

* Good, because tiles are React: sparklines, evidence clippings, belief three-ups, and our fonts are just JSX.
* Good, because ELK gives deterministic, layer-aware layout; pinning makes streaming growth calm.
* Bad, because ELK costs ~½ day of configuration and runs ~50–150 ms on 60 nodes — hence the Worker.
* Bad, because React Flow's default look leaks easily; the `base.css`-only rule and a lint check guard it.
* Neutral, because React Flow is MIT for our use; no license question arises (unlike tldraw).

### Confirmation

* `frontend/src/graph/__tests__/layout.test.ts` — vitest: pinned nodes keep positions across incremental layout; union layout for diff is stable.
* `frontend/src/graph/__tests__/diffState.test.ts` — reducer maps world pairs to `unchanged | shifted | added | killed` per INV-4.
* One Playwright smoke: seed hypothesis → tiles stream in → intervene → downstream tiles change, upstream tiles byte-identical.
* Visual review checklist in `spec/04-canvas.md` mapped to UX-1…UX-13 and INV-12 (no hue-only information; blue▲/amber▼ with glyph; hatch for tails; dashed for `asserted`).
* Lint rule: importing `@xyflow/react/dist/style.css` fails CI (`frontend` job).

## Pros and Cons of the Options

### A. React Flow + ELK + Motion (chosen)

* Good, because highest beauty ceiling per hour; DOM tiles; full styling control; layout engine is pluggable.
* Bad, because re-render discipline is required (memoized nodes, shallow store selectors).

### B. tldraw

* Good, because polished infinite canvas.
* Bad, because a whiteboard mental model and its own renderer/state fight a typed DAG; commercial license for embedded production use.

### C. d3 + d3-dag custom

* Good, because unbounded ceiling (bespoke ribbons).
* Bad, because pan/zoom, hit-testing, selection, and a11y are rebuilt by hand; weeks, not days.

### D. Sigma.js

* Good, because 10k+ nodes.
* Bad, because node = circle, weak labels, wrong scale for 60 rich tiles.

### E. Custom canvas

* Bad, because everything above, plus no ecosystem.

## More Information

* Interview D3 (Workbench aesthetic) and D5(i) (template veto).
* `docs/research/03-ui-ux-directions.md` §1 (tech comparison and ELK config), §2 (ghost overlay, delta rail), §5 (anti-patterns), §6 (accessibility).
* React Flow layouting: https://reactflow.dev/learn/layouting/layouting · ELK example: https://reactflow.dev/examples/layout/elkjs
