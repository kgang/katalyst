# 00 — Vocabulary

Every document, identifier, and UI label uses these words exactly. If a better word appears, change it here first and then everywhere else (L2.21: understanding enables composition; shared words are the interface).

## Propositions and links

**Hypothesis.** The user's root input. A proposition asserted by `do()`, carrying the user's prior as a `user` belief. There is exactly one per graph.

**Proposition.** A node. A *resolvable* claim — something that will be true or false by a date, judged by a named source. Never a vibe ("tensions ease"); always a check ("≥14 consecutive days of unrestricted commercial transit per Lloyd's List by 2026-11-01").
- `kind`: `hypothesis` · `event` · `market` (terminal; names an instrument) · `not_tradeable` (terminal; names the reason).
- `resolution`: `{criteria, source, by}` — all required (INV-1).
- `prior`: the model's marginal belief before parents are considered.
- `base_rate` (optional): `{reference_class, k, n, sources}`.
- `evidence[]`: `{claim, url, direction ∈ {+1, −1}, weight}`.
- `payoff` (market only): instrument, direction, magnitude.

**Link.** An edge. A causal claim from one proposition to another.
- `mode`: `trigger` — horizontal/sequential causality (dominoes): fires once when the parent becomes true, effect persists and decays; removing the parent later does not undo it. `sustain` — vertical causality (the desk holds the apple): the effect exists only while the parent holds; removing the parent retracts the effect.
- `strength`: Δ log-odds applied to the child while the link is active.
- `lag`: time from parent-true to link-active. `shape`: `impulse` (Dirac; decays with `half_life`) · `step` (Heaviside; holds) · `ramp` (grows over `lag`).
- `rationale`: the mechanism in one to three sentences. `sources[]`. `confidence`: `speculative` · `argued` · `documented`.
- `provenance`: see below. `reflexive`: market → world feedback; requires `lag > 0` (INV-6).

**Provenance.** Where a number or link came from. `asserted` (model, no evidence) · `argued` (model, mechanism stated) · `documented` (cited sources) · `market_implied` (a live price) · `historical` (event study) · `user` · `simulated` (a probe). Encoded on every chip and wire (INV-2, INV-12).

**Belief.** `{p, lo, hi, owner}` with `owner ∈ {model, user, market}` and `0 ≤ lo ≤ p ≤ hi ≤ 1` (INV-7). The three owners are stored and rendered separately and never averaged (INV-11). Rendered at two significant figures with the interval.

**Graph.** Propositions + links. A DAG after removing `reflexive` links; reflexive links unroll in time (INV-6). Has exactly one hypothesis and ≥1 terminal (INV-9). Immutable once created; changes are branches.

## The multiverse

**Intervention.** One operation on a graph:
- `do(n, value, at?)` — assert. Cuts `n`'s incoming links; ancestors unchanged (INV-3). This is what a hypothesis is.
- `observe(n, value)` — learn. Updates ancestors as well as descendants. Distinct verb in the UI.
- `insert(node, links[])` — "…but X happens." Adds a proposition and its links.
- `retune(link, strength)` — the user disagrees with a number.
- `refine(n → children[])` — expand a proposition into sub-propositions; children must marginalize to `n` (INV-10). The brainstorm's "search deeper lines".
- `believe(n, belief)` — record the user's own belief on `n`. Lives in the branch so it replays and diffs; never alters `model` or `market` beliefs; not propagated in v1 (D8, INV-11). Propagating a user's world is a stretch (spec 06).

**Branch.** A named, ordered list of interventions over a base graph. A branch *is* a patch. Branches compose by concatenation; `apply(g, [])` is `g` (INV-5). Branches may have a parent branch.

**World.** A base graph with a branch applied and beliefs propagated. Replayable from `(base_id, branch, seed)` (INV-5, NFR-2). The base world is the empty branch.

**Diff.** Between two worlds: per proposition, `unchanged` · `shifted` (with before → after) · `added` · `killed`; plus a ranked list of terminal deltas and a one-line natural-language summary.

**Locality.** An intervention on `n` changes only `descendants(n) ∪ {n}` (INV-4). The product's central correctness claim.

## Sensitivity and drill-down

**Sensitivity sweep.** One-at-a-time flip of every proposition; record Δ on each terminal.

**Invalidation.** The proposition whose flip most damages a terminal *and* resolves before it *and* is publicly observable (INV-14). This is the stop-loss. **Take-profit** is the symmetric case. **Unhedgeable**: sensitive but not observable in time; listed, never used as a stop.

**Tail.** A low-probability, high-magnitude proposition. Listed in its own strip with a suggested hedge; never averaged into an expected value.

**Probe** (stretch). A modeling resource attached to one proposition: `monte_carlo` · `bayes_subnet` · `persona_redteam`. Output re-enters the graph as a `simulated` belief with its own rationale.

**Value of information.** Sensitivity × interval width; ranks where a probe is worth its cost.

## The finale

**Thesis.** The compiled trade: `hypothesis`, `horizon`, `legs[]` (instrument, direction, size, driving proposition, model p, market p, edge), `entry`, `invalidation`, `take_profit`, `distribution` (p10/p50/p90, CVaR₅, max drawdown, P(ruin)), `tails[]`, `caveats` (weakest links, unhedgeable, crowding).

**Strategy export.** A declarative JSON rendering of a thesis with graph references justifying each leg; the shape a downstream trading agent could ingest.

## Surfaces

**Workbench.** The main screen: canvas + world-state strip + Inspector + tail strip + thesis dock.
**Tile.** A proposition's on-canvas card. **Port.** A typed input/output on a tile. **Wire.** A link's on-canvas rendering. **Inspector.** The persistent side panel; never a modal. **Delta rail.** The ranked terminal-delta list beside a diff. **Launchpad.** The empty state with the four seeded examples.

## Words we do not use

*Prediction* (we model arguments, not oracles) · *scenario* (ambiguous between branch and world) · *edge* when we mean a link (reserve *edge* for model-vs-market spread) · *node* in UI copy (say tile or proposition) · *confidence* when we mean probability (confidence is the model's certainty about its own number).
