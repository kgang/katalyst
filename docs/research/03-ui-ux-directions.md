# Causal Multiverse — UI/UX Research & Design Brief

## 1. Canvas / graph tech

**Verdict: `@xyflow/react` (React Flow v12) + `elkjs` (layered) + Motion (Framer Motion) for node/edge transitions.** Nothing else hits the same beauty-per-hour ratio for 10–60 nodes.

| Option | Beauty ceiling | Control | Dev speed | Verdict |
|---|---|---|---|---|
| **React Flow v12** | High — nodes are plain React/DOM, so Tailwind + shadcn + real typography, sparklines, mini-charts *inside* nodes | High: custom nodes, custom edges (you supply the SVG path), handles, viewport API | Fastest | **Pick this** |
| tldraw 4.x | High, but it's a *whiteboard* mental model; shapes are its own canvas renderer, styling is more fight than fit | High but you adopt their editor/state model | Medium | Wrong shape of problem; also a commercial license (~$6k/yr) for production embedded use |
| d3 + d3-dag | Highest ceiling (bespoke ribbons, alluvial edges) | Total | Slowest — you rebuild pan/zoom, hit-testing, selection, a11y | Only if you want a *diagram*, not an app |
| elkjs / dagre | Not renderers — **layout engines you pair with the above** | dagre = drop-in, fast, few knobs. ELK = layered/orthogonal routing, node-size-aware, ports, much better for branch fans | ELK costs ~half a day | Use ELK `layered`, `RIGHT` direction |
| Sigma.js | WebGL, built for 10k+ nodes, node = circle | Low styling control; labels are a known weak point | Medium | Overkill and under-pretty at this scale |
| Custom SVG/Canvas | Unbounded | Total | Weeks | No |

**Config that matters:** ELK `elk.algorithm: layered`, `elk.direction: RIGHT`, `elk.layered.nodePlacement.strategy: NETWORK_SIMPLEX`, `elk.edgeRouting: ORTHOGONAL` (or SPLINES for a softer look), `elk.layered.spacing.nodeNodeBetweenLayers: 120`, and `elk.layered.crossingMinimization.semiInteractive: true` so re-layouts after an intervention don't reshuffle the world.

**Pitfalls, with fixes:**
- **Layout jank on incremental/streamed nodes.** ELK is deterministic but not stable — adding one node can reorder a layer. Fix: pin already-placed nodes' layer order via `elk.position`, run layout in a Web Worker, and animate node positions with a spring rather than snapping (`useNodesState` + Motion `layoutId`).
- **Measurement race.** React Flow needs measured node dimensions before ELK runs. Fix: fixed-width node cards (e.g. 280px) with clamped height; only height varies.
- **Edge label collision.** Put the probability/lag on the edge *midpoint chip*, not a free-floating label; use a custom edge with `getSmoothStepPath` and render the chip in an `EdgeLabelRenderer` portal.
- **Perf.** 60 DOM nodes is nothing; the killer is re-rendering all nodes on every drag. Memoize node components, select state with `useStore` shallow selectors, never pass new object literals as node `data`.
- **Styling lock-in.** Import `@xyflow/react/dist/base.css` (not `style.css`) so you own the look entirely.

Refs: [React Flow layouting](https://reactflow.dev/learn/layouting/layouting) · [ELK example](https://reactflow.dev/examples/layout/elkjs) · [layout playground](https://xyflow.com/labs/react-flow-playground) · [licensing](https://xyflow.com/open-source) · [tldraw SDK 4.0](https://tldraw.dev/blog/tldraw-sdk-4-0)

## 2. Branching / multiverse visualization — what actually works

Surveyed patterns and their honest verdicts:

- **Git graph (GitKraken/Tower):** branches as colored swimlanes off a spine. Works because *the spine is canonical* and branches are visually subordinate. **Steal: the lane metaphor + branch color as identity.**
- **[Loom](https://generative.ink/posts/loom-interface-to-the-multiverse/)** (multiversal tree writer, [repo](https://github.com/socketteer/loom)): the canonical "multiverse" UI. Its real lesson is the **two-pane split — a tree navigator on the left, one *read* path on the right.** Trees are for *choosing*; linear reading is for *understanding*. Don't make the graph do both.
- **Sankey/alluvial:** beautiful for flow magnitude, terrible for causality + intervention. Skip as the main view; excellent as a **mini "probability mass flowing to outcomes" strip** at the bottom.
- **Ghost overlay diff:** render branch A′ at full opacity, A at 20% opacity dashed, in the *same* layout coordinates. This is the single cleanest two-world comparison and it is cheap to build. Requires computing a **stable union layout** (lay out A ∪ A′ once, then mask).
- **Side-by-side / small multiples:** honest but halves your pixel budget and forces eye saccades for the diff. Use only for ≥3 branches, as thumbnails.
- **[Metaculus conditional pairs](https://www.metaculus.com/questions/17173/introducing-conditional-continuous-questions/):** parent outcome = an arrow, each conditional probability = a bar. Dead simple, extremely legible. **Steal this exact idiom for edge weights.**
- **Guesstimate/Squiggle:** distributions rendered *inside* the node cell. **Steal: every quantitative node shows a tiny density sparkline, not a number.**
- **Polymarket/Kalshi cards:** title → big % → thin bar → volume/liquidity → two buttons. **Steal the vertical rhythm verbatim for terminal (tradeable) nodes.**
- **[Pax Historia](https://wiki.paxhistoria.co/wiki/Basic_Gameplay)'s rewind:** alter a past turn, get an alternate timeline. Confirms the interaction model: **intervene in place, fork implicitly, keep both.**

**The diff, concretely — a three-layer answer:**
1. **Structural diff on the canvas** (ghost overlay): nodes get a state of `unchanged` (neutral), `shifted` (probability moved — show `62% → 31%` with a directional chevron), `added` (in A′ only — solid, accent ring, slides in), `killed` (in A only — ghosted, strikethrough, desaturated).
2. **A "delta rail"** — a ranked list beside the canvas: *"Brent Δ −$9 · airline basket Δ +4.1% · KXOIL-26 Δ −18¢"*. Sorted by |Δ| × confidence. This is the thing a trader actually reads.
3. **A one-line natural-language diff** at the top: *"Striking Iran doesn't reopen the strait — it inverts the oil leg while leaving the airline leg intact."*

Never animate the diff as a crossfade; **animate it as a transition you can scrub**, with a A ⇄ A′ toggle bound to a single key.

## 3. Aesthetic references → concrete principles

**Typography.** One geometric/neo-grotesque UI face (Inter Display, or Geist) + one tabular-figures mono (Berkeley Mono, JetBrains Mono, Geist Mono) for *every number*. `font-variant-numeric: tabular-nums` globally, or your deltas will shimmy. Linear's real trick: only 3 type sizes (13/15/22) and 3 weights; hierarchy comes from *color and spacing*, not size.

**Density.** Bloomberg's lesson isn't "cram" — it's *no chrome between you and the data*. Kill card shadows, use 1px hairline borders at 8–10% foreground opacity. Node cards ≈ 280×96px, 12px internal padding, 8px grid.

**Color for probability & direction — keep these two axes orthogonal.** This is the most common failure mode.
- *Probability/confidence* → **luminance + fill saturation** of the node (low-confidence nodes are desaturated, hairline-dashed, slightly translucent). Never red-for-unlikely.
- *Direction of financial effect* → **hue, blue↑ / amber↓** (never red/green — fails deuteranopia and carries loss/gain baggage), **always paired with a glyph** (▲/▼) and a sign.
- *Branch identity* → a small ordered palette (violet, teal, amber, rose) used only on the branch's spine/lane and its chip, never on node semantics.
- *Tail risk / black swan* → a distinct **texture** channel, not a color: a hatched border + a small ⌁ mark. Texture survives every form of color blindness and dark/light inversion.

**Motion.** One rule: motion only communicates *causality and provenance*. Edges draw in the direction of propagation (200ms, `ease-out`, staggered 60ms down the DAG) so the user *sees* the chain reason. Everything else is 120ms opacity. No looping, no idle animation, no bouncing springs on a finance tool.

**Progressive disclosure / focus+context.** The graph shows ~6 fields per node max. Click → a right-side **Inspector** (never a modal) with evidence, sources, the distribution, the prior/posterior, and "what would falsify this." Hover → a *lens*: dim everything not on the hovered node's ancestor/descendant path to 15%. This one interaction does more for legibility than any layout tweak.

**Empty state.** Not an illustration — a **launchpad**: three seeded hypotheses as clickable cards ("Strait of Hormuz reopens", "Fed cuts 50bp in March", "TSMC Arizona fab delayed"), plus the two-mode switch (Verify A→B / Explore A→{…}) visible and pre-explained.

**Loading state = the killer feature.** Do *not* show a spinner then dump a graph. **Stream the graph as it's generated:** skeleton node appears at its layer with a shimmering title → title streams in → edge draws to it → probability chip resolves last with a brief number-roll. The user watches the model think in the shape of the artifact. Budget a day for this; it's the demo moment. Reserve layout space ahead of the stream (lay out a predicted 3-layer skeleton) so nothing reflows violently. Also: **stream the reasoning as edge tooltips**, so the audit trail arrives with the structure, not after.

Refs: [FutureSearch](https://futuresearch.ai/forecast/) · [Hypothetical Outcome Plots](https://medium.com/hci-design-at-uw/hypothetical-outcomes-plots-experiencing-the-uncertain-b9ea60d7c740) · [Wilke, *Visualizing uncertainty*](https://clauswilke.com/dataviz/visualizing-uncertainty.html) · [NetHOPs (uncertainty in graphs)](https://arxiv.org/abs/2108.09870)

## 4. Three design directions

### (a) "Instrument" — the calm terminal
Dense, quiet, monochrome-with-two-accents. A dark canvas (not black — `#0B0C0E`) with a hairline dot grid, node cards that look like Linear issues crossed with Kalshi market rows, and a persistent right inspector. Optimizes for **credibility and information density** — it reads as a professional instrument a PM would keep open. Branches live as tabs/lanes in a left rail; the graph area is one focused world at a time with ghost-overlay diffing. Intervening: select a node, press `E`, an inline editor expands *in place* on the card ("...BUT Iran is struck the next day"); on commit the card gets a violet left-edge, a new branch chip appears in the rail, and the downstream re-propagates as a left-to-right wave of re-resolving probability chips. Thesis card: a fixed bottom-right **dock** that's always present and always live — position, direction, entry, the two or three invalidators, and a "copy thesis" button.

```
┌───────────────────────────────────────────────────────────────────────────┐
│ ⌘ Hormuz reopens               [Verify] [Explore]      ⌥ base ⇄ A′   ☾ ⌕  │
├──────────┬─────────────────────────────────────────────┬──────────────────┤
│ BRANCHES │                                             │ INSPECTOR        │
│ ● base   │  ┌──────────┐   ┌──────────┐  ┌──────────┐  │ Brent −12%       │
│ ● A′ Iran│  │ Hormuz   │──▸│ Insurance│─▸│ Brent ▼  │  │ p .61 ±.14       │
│   strike │  │ reopens  │.86│ rates ▼  │ │ −12%  ⌁  │  │ ▁▃▆█▆▃▁          │
│ + new    │  └──────────┘   └──────────┘  └────┬─────┘  │ ─────────────    │
│          │        │        ┌ ─ ─ ─ ─ ┐        │        │ WHY  3 sources   │
│ DELTA    │        └───────▸┆ Tanker  ┆        ▼        │ · Lloyd's war-   │
│ Brent    │            .41  ┆ surge   ┆  ┌──────────┐   │   risk premia ↓  │
│  −9 ▼    │                 └ ─ ─ ─ ─ ┘  │ AAL ▲ +4%│   │ · 2019 analogue  │
│ AAL +4.1 │                   killed     └──────────┘   │ FALSIFIED IF     │
│ KXOIL−18 │                                             │ · strike <72h    │
├──────────┴─────────────────────────────────────────────┤──────────────────┤
│ ⌁ TAIL  Iran strikes 72h  p.09  → Brent +18%           │ THESIS  short CL │
│         Chinese escort convoy p.04 → no price effect   │ 1×2 put spread   │
│ ─────────────────────────────────────────────────────  │ stop $4 · tp $9  │
│ [P]robe  [E]dit node  [B]ranch  [/]command             │ [copy] [export]  │
└────────────────────────────────────────────────────────┴──────────────────┘
```

### (b) "Sandbox" — the simulation
World-state tiles, a tick/turn model, and auto-battler legibility: the left is a **world state panel** (oil, freight, equities, rates as little gauges), the center is the causal board, and time advances in discrete beats you can scrub. Optimizes for **play and intuition** — it makes the multiverse feel like a toy you want to poke, which is exactly the founder's RimWorld/TFT note. Intervening: drag an **"event card"** (Strike, Sanction, Cut, Freeze) from a tray onto a node — the board *shakes*, a fork spawns, and gauges re-tick with visible deltas. Thesis card: a "loadout" panel, like a build summary at the end of a run. Risk: it can read as a game, not a tool, to a finance team.

```
┌────────────────────────────────────────────────────────────────┐
│ WORLD  t+0 ──●──────○──────○──────○  t+21d      [⏵ simulate]   │
├──────────────┬─────────────────────────────────────────────────┤
│ Brent  ▓▓▓░░ │   ╭─ TIMELINE α ────────────────────────────╮   │
│  71 ▼        │   │ ▣ reopen ─▸ ▣ freight ─▸ ▣ CPI ─▸ ▣ AAL │   │
│ Freight ▓░░░ │   ╰──────────┬───────────────────────────────╯  │
│ Airlines ▓▓▓▓│              └▸╭─ TIMELINE β (struck) ───────╮  │
│ VIX  ▓▓░░░   │                │ ▣ strike ─▸ ▣ Brent ▲ ─▸ ⌁ │  │
│ ──────────── │                ╰───────────────────────────╯   │
│ EVENT CARDS  │                                                 │
│ [⚔ strike ]  │   ⌁ BLACK SWAN DECK   mine  09%   closure  04%  │
│ [🚫 sanction]│                                                 │
│ [✂ rate cut ]│   LOADOUT  short CL · long AAL · stop @ 4       │
└──────────────┴─────────────────────────────────────────────────┘
```

### (c) "Editorial" — the argument
A scrolling narrative column (Observable/NYT graphics) where the causal chain *reads as prose*, and the graph is a sticky companion figure that highlights the step you're reading. Optimizes for **comprehension and shareability** — the output is a document someone forwards. Intervening: inline, text-level — click any claim in the prose, get "...but what if?" and the paragraph *rewrites below* as a new indented branch, like a tracked change. Thesis card: the closing section, a printed-looking "position note." Risk: weakest at *exploring* many branches; scroll is a poor multiverse navigator.

```
┌────────────────────────────────────────────────────────────────┐
│  IF THE STRAIT REOPENS                        ▸ share  ▸ pdf   │
├─────────────────────────────────┬──────────────────────────────┤
│ Reopening removes a war-risk    │      ┌────────┐              │
│ premium of roughly $6–9/bbl…    │      │ reopen │◀ you are here│
│ ▁▃▆█▆▃▁  p .61                  │      └───┬────┘              │
│                                 │          ▼                   │
│ ⋮ but if Iran is struck ────────│      ┌────────┐  ┌────────┐  │
│   ⌐ the premium returns within  │      │freight │─▸│ Brent  │  │
│   ⌐ 48h and the airline leg …   │      └────────┘  └────────┘  │
│                                 │       ─ ─ ─ ─ ─ ghost: β     │
│ ── THE POSITION ─────────────── │                              │
│ Short CL via 1×2 put spread.    │  ⌁ tail 9%                   │
│ Invalidated by: strike <72h,    │                              │
│ OPEC cut >1mb/d.                │                              │
└─────────────────────────────────┴──────────────────────────────┘
```

**What I'd build:** **Instrument, with Editorial's thesis panel as the finale and exactly two Sandbox borrowings** — the event-card tray for interventions and the world-state strip. Reasoning: the audience is a finance-AI team; "impeccable style" reads to them as Linear-grade restraint, not particle effects. Instrument is also the cheapest to make *actually beautiful* in 1–2 weeks, because its beauty is typography, spacing and one good motion idea (streaming propagation) rather than bespoke illustration. Sandbox has the higher ceiling and a much higher floor-risk; Editorial can't demo the multiverse. Ship Instrument, and spend the saved days on the **streaming graph growth** and the **A ⇄ A′ ghost diff** — those two are the whole demo.

## 5. Anti-patterns → remedies

1. **Hairball** (force layout, crossing edges) → layered DAG, left→right, ELK crossing minimization; hard-cap 7 nodes per layer and collapse the rest into a "+4 more" node.
2. **Tiny unreadable labels** → never scale text with zoom below 11px; switch node rendering to a *summary* LOD (title + chip only) under 0.6 zoom instead of shrinking.
3. **Uniform node styling** → four explicit node *types* with different silhouettes: Event (rect), Mechanism (rounded, dimmer), Market Effect (rect + sparkline), Tradeable (card with ticker + price, hairline accent). Shape carries type, color carries direction.
4. **Fake-precise percentages** ("63.7%") → round to 5% and show a band: `60% ±15`. Better: show the sparkline density and the number in a lighter weight.
5. **Modal hell** → one persistent inspector panel, zero modals. Confirmations become undo-able toasts.
6. **Everything animated** → an animation budget: propagation wave, branch creation, number roll. That's it. Everything else ≤120ms opacity.
7. **No keyboard nav** → `⌘K` command palette, `j/k` traverse siblings, `h/l` traverse layers, `E` edit node, `B` branch, `Space` toggle A⇄A′, `?` shortcuts sheet. Arrow keys must move *along edges*, not in screen space.
8. **Lost viewport after re-layout** → preserve the focused node's screen position across layouts (`fitView` only on first load; afterwards `setCenter` on the focus node).
9. **Unauditable claims** → every edge carries a "why" with ≥1 source and a stated mechanism; an edge with no evidence renders **dashed + labeled "asserted"**. Never let the model's confidence and the *evidence's* strength collapse into one number.
10. **Branch explosion** → cap visible branches at 4, force-name them, and auto-collapse the rest into a "runs" list. A multiverse you can't compare is a mess.
11. **Dead ends** (chains that end in prose, not a trade) → every terminal node must resolve to an instrument, a market contract, or an explicit "not tradeable — here's why."
12. **Tail risk buried** → black swans get a dedicated fixed strip, never a node you have to find. They are the point.
13. **Drag-to-reposition fighting auto-layout** → make nodes non-draggable and say so; offer pan/zoom/focus instead. Half-supported dragging looks broken.
14. **Zoom as the only navigation** → add a minimap *and* a breadcrumb of the current path from root.

## 6. Accessibility & theming

- **Dark and light both, with semantic tokens** (`--surface`, `--hairline`, `--dir-up`, `--dir-down`, `--tail`), not raw hex. Design dark-first (it's the finance idiom) but verify light — a graph that only works dark reads as a demo.
- **Contrast:** hairlines may be low-contrast, but *all text and all glyphs* clear 4.5:1, including node labels at min zoom. Chip text on colored fills gets a computed foreground.
- **Color-blind-safe encoding:** blue/amber for direction (safe across deuter/protan/tritan) **plus** a redundant ▲/▼ glyph and a signed number — the rule is *no information in hue alone, ever*. Probability rides luminance/opacity, which is CVD-invariant. Tail risk rides a hatch texture. Branch identity rides color *and* a name chip, since branch lanes are also spatially separated.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` → the streaming propagation becomes instant per-layer reveals (still ordered, so causality is preserved), the number roll becomes a swap, ghost-diff transitions become a hard cut. Never remove the *ordering*, only the tweening.
- **Screen reader / structure:** the DAG also exists as a nested `<ul>` in the DOM (visually hidden or as a "outline view" toggle) — `role="tree"`, each node labeled `"Brent crude falls 12 percent, 61 percent likely, caused by falling insurance rates"`. React Flow gives focusable nodes; add `aria-describedby` to the inspector. Announce re-propagation with an `aria-live="polite"` summary: *"Branch created. 6 nodes changed, 2 removed."*
- **Text scaling:** node cards clamp height but let text wrap to 3 lines then ellipsize with the full text in the inspector — never truncate mid-word at the layout's convenience.

**Sources:** [React Flow layouting](https://reactflow.dev/learn/layouting/layouting) · [ELK example](https://reactflow.dev/examples/layout/elkjs) · [React Flow playground](https://xyflow.com/labs/react-flow-playground) · [xyflow open source/licensing](https://xyflow.com/open-source) · [tldraw SDK 4.0](https://tldraw.dev/blog/tldraw-sdk-4-0) · [Loom: interface to the multiverse](https://generative.ink/posts/loom-interface-to-the-multiverse/) · [socketteer/loom](https://github.com/socketteer/loom) · [Metaculus conditional continuous questions](https://www.metaculus.com/questions/17173/introducing-conditional-continuous-questions/) · [Metaculus conditional pairs announcement](https://www.lesswrong.com/posts/nQhmiKeYPvFaEZfWc/metaculus-introduces-new-conditional-pair-forecast-questions) · [Pax Historia gameplay wiki](https://wiki.paxhistoria.co/wiki/Basic_Gameplay) · [FutureSearch forecast](https://futuresearch.ai/forecast/) · [Hypothetical Outcome Plots](https://medium.com/hci-design-at-uw/hypothetical-outcomes-plots-experiencing-the-uncertain-b9ea60d7c740) · [NetHOPs](https://arxiv.org/abs/2108.09870) · [Wilke, Visualizing uncertainty](https://clauswilke.com/dataviz/visualizing-uncertainty.html) · [Catalyst](https://catalyst.app)
