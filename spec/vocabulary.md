# Vocabulary

Every document, identifier, and UI label uses these words exactly. If a better word appears, change it here first and then everywhere else (L2.21: understanding enables composition; shared words are the interface).

## Propositions and links

**Hypothesis.** The user's root input. A proposition asserted by `do()`, carrying the user's prior as a `user` belief. There is exactly one per graph.

**Proposition.** A node. A *resolvable* claim — something that will be true or false by a date, judged by a named source. Never a vibe ("tensions ease"); always a check ("≥14 consecutive days of unrestricted commercial transit per Lloyd's List by 2026-11-01").
- `kind`: `hypothesis` · `event` · `market` (terminal; names an instrument) · `not_tradeable` (terminal; names the reason).
- `resolution`: `{criteria, source, by}` — all required (INV-1).
- `prior`: the model's marginal belief before parents are considered.
- `base_rate` (optional): `{reference_class, k, n, sources}`.
- `evidence[]`: `{claim, url, direction ∈ {+1, −1}, weight}`.
- `payoff` (market only): one of two shapes, told apart by a `kind` field. A **contract payoff** — `kind: contract` — names a venue, the venue's own identifier for the contract, its title, and the side you would take (`yes` or `no`). A **price payoff** — `kind: price` — names an instrument, a direction (`long` or `short`), and `move`, how far the price is expected to move if the claim comes out true, as a fraction (0.03 is three per cent). The rule behind both: the domain names *what you would trade*; what it costs — price, spread, and when we looked — is a market belief, fetched live.

**Link.** An edge. A causal claim from one proposition to another.
- `mode`: `trigger` — horizontal/sequential causality (dominoes): fires once when the parent becomes true, effect persists and decays; removing the parent later does not undo it. `sustain` — vertical causality (the desk holds the apple): the effect exists only while the parent holds; removing the parent retracts the effect.
- `strength`: how much the link shifts the child's odds while active, on a log-odds scale (so several links add up instead of multiplying).
- `lag`: time from parent-true to link-active. `shape`: `impulse` (a one-time spike that fades with `half_life`) · `step` (switches on and holds) · `ramp` (builds up over `lag`).
- `rationale`: the mechanism in one to three sentences. `sources[]`. There is no field for how sure the model is about its own mechanism; `provenance` and the rationale carry that.
- `provenance`: see below. `reflexive`: market → world feedback; requires `lag > 0` (INV-6).

**Provenance.** Where a number or link came from. `asserted` (model, no evidence) · `argued` (model, mechanism stated) · `documented` (cited sources) · `market_implied` (a live price) · `historical` (event study) · `user` · `simulated` (a probe). Encoded on every chip and wire (INV-2, INV-12).

**Belief.** `{p, lo, hi, owner}` with `owner ∈ {model, user, market}` and `0 ≤ lo ≤ p ≤ hi ≤ 1` (INV-7). The three owners are stored and rendered separately and never averaged (INV-11). Rendered at two significant figures with the interval. `lo` and `hi` are the 10th and 90th percentiles of the likelihood itself — how sure we are of the number, not how much the world can move.

**Graph.** Propositions + links. A DAG after removing `reflexive` links; reflexive links unroll in time (INV-6). Has exactly one hypothesis and ≥1 terminal (INV-9). Immutable once created; changes are branches.

## The multiverse

**Intervention.** One operation on a graph:
- `do(n, value, at?)` — assert. Cuts the incoming links `n` has **at the moment the edit is applied**; a link inserted later is live. A timed assertion — `do(H, at=Oct 1)` says H holds from the 1st, not that H is sealed for ever. Ancestors unchanged (INV-3). This is what a hypothesis is.
- `observe(n, value)` — learn. Updates ancestors as well as descendants. Distinct verb in the UI.
- `insert(node, links[])` — "…but X happens." Adds a proposition and its links.
- `retune(link, strength)` — the user disagrees with a number.
- `refine(n → children[])` — split a proposition into finer sub-propositions; their combined likelihood must equal the original's (they *marginalize* back to `n`, INV-10). The brainstorm's "search deeper lines".
- `believe(n, belief)` — record the user's own belief on `n`. Lives in the branch so it replays and diffs; never alters `model` or `market` beliefs; not propagated in v1 (D8, INV-11). Propagating a user's world is a stretch (see `probes/`).

**Branch.** A named, ordered list of interventions over a base graph. A branch *is* a patch. Branches compose by concatenation; `apply(g, [])` is `g` (INV-5). Branches may have a parent branch.

**World.** A base graph with a branch applied and beliefs propagated. Replayable from `(base_id, branch, seed)` (INV-5, NFR-2). The base world is the empty branch.

**Diff.** Between two worlds: per proposition, `unchanged` · `shifted` (with before → after) · `added` · `killed`; plus a ranked list of terminal deltas and a one-line natural-language summary. **`killed` means forced false, and nothing else** (decided 2026-09-17) — never "its number got small", and never "no path reaches it from the hypothesis any more", which is a fact about the *path* and is reported by the Inspector's path bar in those words. The ranking is the size of the move times the weakest provenance weight on the **best-backed route** from a differing edit's subject to that ending: over every such route, the one whose weakest arrow is strongest. Two factors; range width and agreement are columns beside it and are never multiplied in.

**Version of the map.** One coherent set of numbers this model would have stood behind: every claim's likelihood drawn from its own stated range at once, never every low end together. The engine runs two thousand versions and eight worlds under each. The range on a computed number is the spread across versions; a change is read version by version, never by whether two ranges overlap.

**Agreement.** The share of versions of the map in which a change moved the same way. Computed, never self-reported. A claim counts as `shifted` when it moved by .005 or more **and** agreement is at least 90%; agreement is then shown as its own column beside the change, never multiplied into the ranking. **On screen that column is headed *same direction*** (decided 2026-09-17), and the width column beside it is headed *how firm*; the field names stay `agreement` and `range_width`. Keeping the word *agreement* off this screen leaves it free for stack 04's run-to-run number. Stack 04 may compute a second agreement number — how far several independent generation runs agreed on a claim's likelihood (decision record 0014 defers that question). Same idea, same rule; wherever both could be meant, say which.

**Locality.** An intervention changes only what is still connected to its subject in the graph the edit leaves behind (INV-4). Which claims those are depends on the operation, because the operations leave behind different graphs: `do` cuts the target's incoming arrows, so only the target and its descendants remain connected to it; `observe` cuts nothing, so its ancestors — and what those ancestors cause — are connected too. The per-operation **affected set** table in `multiverse/interventions.md` is the operational form, and the property test computes the set from the shape of the graph. The product's central correctness claim.

## Sensitivity and drill-down

**Sensitivity sweep.** One-at-a-time flip of every proposition; record Δ on each terminal.

**Invalidation.** The proposition whose flip most damages a terminal *and* resolves before it *and* is publicly observable (INV-14). This is the stop-loss. **Take-profit** is the symmetric case. **Unhedgeable**: sensitive but not observable in time; listed, never used as a stop.

**Tail.** A low-probability, high-magnitude proposition. Listed in its own strip with a suggested hedge; never averaged into an expected value.

**Probe** (stretch). A modeling resource attached to one proposition: `monte_carlo` · `bayes_subnet` · `persona_redteam`. Output re-enters the graph as a `simulated` belief with its own rationale.

**Value of information.** How much the trade depends on a proposition × how uncertain it is; ranks where a probe is worth its cost.

## The finale

**Thesis.** The compiled trade: `hypothesis`, `horizon`, `legs[]` (instrument, direction, size, driving proposition, model p, market p, edge), `entry`, `invalidation`, `take_profit`, `distribution` (p10/p50/p90, CVaR₅, max drawdown, P(ruin)), `tails[]`, `caveats` (weakest links, unhedgeable, crowding).

**Strategy export.** A declarative JSON rendering of a thesis with graph references justifying each leg; the shape a downstream trading agent could ingest.

## Surfaces

**Workbench.** The main screen: canvas + world-state strip + Inspector + tail strip + thesis dock.
**Tile.** A proposition's on-canvas card. **Port.** A typed input/output on a tile. **Wire.** A link's on-canvas rendering. **Inspector.** The persistent side panel; never a modal. **Delta rail.** The ranked terminal-delta list beside a diff. **Launchpad.** The empty state with the four seeded examples.

## Interface words

The six operations keep their code names in code, in the wire format and in this document — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — and none of those words appears on screen. These are the words the user reads. Change a button here first, then everywhere else.

| Code name | The button | The badge afterwards | What the interface says it means |
|---|---|---|---|
| `do` | **Suppose this is true** (and **Suppose this is false**) | **Supposed · date** | "Take this as given, and do not tell me what caused it" |
| `observe` | **This happened** | **Happened · date** | "This is news — update what came before it too" |
| `insert` | **Add a claim**, hinted as "…but this also happens" | **Added** | A claim and its arrows arrive together |
| `retune` | **Change this push** | **Retuned** | "You moved this arrow from +0.7 to +0.3" |
| `refine` | **Split this claim** | **Split** | The finer claims add back up to the one they replace |
| `believe` | **My own number** | none — the three-up belief chip is the badge | Your number sits beside the model's and the market's |

One more badge is **derived**: no button produces it. **Retracted · date · by "…"** appears on a claim that was supposed true and has since been pushed back down by a later edit — what was holding this up was removed. It names the edit responsible and the day it landed (UX-14; the mechanism is in `multiverse/interventions.md`).

## Words we do not use

*Prediction* (we model arguments, not oracles) · *scenario* (ambiguous between branch and world) · *edge* when we mean a link (reserve *edge* for model-vs-market spread) · *node* in UI copy (say tile or proposition) · *confidence*, at all — there is no confidence field on anything. A link's standing is its `provenance` (a receipt we write), its rationale, and the range on the belief; a number for how much things computed independently agreed is called *agreement* — defined under *The multiverse* above — and is computed, never self-reported.
