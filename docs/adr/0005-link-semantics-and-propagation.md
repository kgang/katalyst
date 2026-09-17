---
# ADR-0005: Links carry trigger/sustain mode, log-odds strength, lag and shape; beliefs propagate by seeded forward Monte Carlo
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/initial-brainstorming.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/01-causal-graph.md (Link fields, INV-7), spec/02-interventions.md (propagation, retraction, observe sampling), spec/04-canvas.md (wire encoding UX-2, rendering NFR-1)
---

# ADR-0005: Links carry trigger/sustain mode, log-odds strength, lag and shape; beliefs propagate by seeded forward Monte Carlo

## Context and Problem Statement

"Modify a node and see downstream effects" needs a propagation rule. It must be elicitable from an LLM with O(parents) numbers per node, explainable one link at a time, honest about uncertainty, and able to express the brainstorm's two kinds of causality: sequential/horizontal (a domino, which stays fallen if the earlier domino is reset) and sustaining/vertical (a desk holding an apple, which falls when the desk is removed). It must also handle timing — impulses that decay versus steps that persist — because "Hormuz opens, Iran struck the next day" is a timing question. Which formalism, and which execution engine?

## Decision Drivers

* FR-15 — local re-propagation with `sustain` retraction and `trigger` persistence
* FR-19, FR-22, FR-23, FR-24 — sensitivity sweep, tails, invalidation derivation, payoff distribution all need a sampled or analytic distribution over worlds
* INV-3 — `observe` must be a distinct operation with parent updating
* INV-7 — beliefs bounded in [0,1] with `lo ≤ p ≤ hi`; rendered at 2 significant figures with interval (NFR-1)
* NFR-2 — pure, seeded, deterministic
* Elicitation cost: one number plus one rationale per link, not 2^k per node
* Brainstorm: horizontal vs vertical causality; Heaviside/Dirac impulse vs continuous input; "getting wiped out"

## Considered Options

* Log-odds link aggregation (noisy-OR class) with typed links, executed by seeded forward Monte Carlo; `observe` via rejection sampling
* Full-CPT discrete Bayesian network with exact inference
* Scenario / decision trees
* Markov chains with steady-state analysis
* Agent-based / LLM role-play simulation
* Pure LLM narration re-prompted per world

## Decision Outcome

Chosen option: "Log-odds link aggregation with typed links, forward Monte Carlo", because it is the only option that is simultaneously O(parents) to elicit, explainable per link, capable of `do`/`observe` semantics, and able to produce the distributions FR-22/23/24 need — while the rejected options are either unelicitable (CPTs), non-composable across shared nodes (trees), the wrong physics (Markov), or unauditable (simulation, narration).

Link fields (`spec/01-causal-graph.md` carries the pydantic model):

| Field | Meaning |
|---|---|
| `mode` | `trigger` — fires when the parent becomes true; effect persists and decays by `half_life`; resetting the parent later does not undo it. `sustain` — effect holds only while the parent holds; removing the parent retracts it |
| `strength` | Δ log-odds applied to the child when the parent is true (signed) |
| `lag` | delay before the effect begins |
| `shape` | `impulse` (Dirac-like, decays with `half_life`), `step` (Heaviside, persists), `ramp` (linear onset over `lag`) |
| `half_life` | decay constant for `impulse`; unused otherwise |
| `reflexive` | market→world feedback; requires `lag > 0` (INV-6) |

Child aggregation at time `t`:

```
logit P(child, t) = logit(prior_child) + Σ_{active links} strength · shape(t − t_parent)
```

Execution: draw `N` (default 10 000) seeded worlds; each proposition is sampled in topological order from its aggregated logit; `do` fixes a value and severs parents; `observe` fixes a value and keeps only consistent samples (rejection sampling; warn loudly below ~2% acceptance); beliefs are sample means with a Wilson interval; terminal payoffs are per-sample so p10/p50/p90, CVaR₅, P(ruin) fall out for free.

**Staged delivery.** Stack 03a may ship a deterministic topological sweep computing the mean logit only, provided the API and types are those of the sampled engine. The sweep must be replaced by Monte Carlo no later than the first of: (a) `observe` is exposed in the UI (INV-3 requires parent updating, which the sweep cannot do), (b) FR-24 distribution rows appear on the thesis card, (c) `refine` ships (INV-10 marginalization is checked on samples).

Rendering: two significant figures and the interval, always (`.35 (.2–.5)`); the canvas never receives more precision than that (NFR-1).

### Consequences

* Good, because every belief decomposes into a prior plus one term per link, each with its own rationale — the audit trail is the formula.
* Good, because `trigger` vs `sustain` makes the Hormuz-then-strike branch behave correctly: the transit impulse already fired and decays; the insurance step retracts when the strike removes the sustaining condition. This is ~30 lines of propagation code and the best idea in the brainstorm.
* Good, because tails and wipe-outs are read off the sample distribution rather than hidden in an expected value (anti-pattern 6).
* Bad, because log-odds addition assumes link independence given the parents; correlated causes will be over-counted. Mitigated by `refine` (split the shared cause into an explicit parent) and by rendering intervals, not points.
* Bad, because the interval is sampling noise plus elicited `lo/hi`, and readers may take it as a calibration claim. The Inspector labels it "model interval, uncalibrated".
* Neutral, because Monte Carlo at 10 000 samples over 60 nodes is milliseconds in numpy; no performance concern at v1 scale (NFR-7).

### Confirmation

* Property tests in `tests/unit/domain/test_propagation.py`: `test_probability_bounds` (INV-7), `test_propagation_idempotent`, `test_propagation_order_independent` (shuffled topological tie-breaks), `test_trigger_persists_after_parent_reset`, `test_sustain_retracts_when_parent_removed`, `test_reflexive_requires_positive_lag`, `test_same_seed_same_world` (NFR-2).
* Golden test on the Hormuz fixture (stack 02): the "Iran struck next day" branch lowers the Brent-below-threshold terminal and raises the insurance terminal, in the directions given in `docs/research/02` §3.
* Rendering test in the frontend: a belief chip never displays more than two significant figures and always displays an interval.
* Review item at stack 04/05/06: if any of the three upgrade conditions holds and the sweep is still in place, block.

## Pros and Cons of the Options

### Log-odds aggregation + typed links + forward Monte Carlo

* Good, because elicitation is one number and one sentence per link; explanation is the same sentence.
* Good, because `do` and `observe` are both natural: sever, or reject.
* Bad, because independence-given-parents is an approximation; made visible rather than hidden.

### Full-CPT Bayesian network

* Good, because exact inference and textbook semantics.
* Bad, because 2^k numbers per node, which the LLM will invent and no human can audit at k > 3. High fake-precision risk.

### Scenario / decision trees

* Good, because each path reads as a story.
* Bad, because shared downstream nodes are duplicated across branches, the tree explodes, and coverage is a lie (branches never sum to reality).

### Markov chains / steady states

* Good, because the brainstorm named them and the math is clean.
* Bad, because these events are one-shot and non-ergodic; a stationary distribution is a fiction here. The legitimate form of the idea — time-unrolling lagged links — is already in the chosen option (`lag`, `reflexive`).

### Agent-based / LLM role-play simulation

* Good, because it could surface second-order behaviour the graph lacks.
* Bad, because there is no validation story, high variance, high cost, and the audience will read it as theater. Kept only as red-team personas that propose missing structure (FR-9, P2).

### Pure LLM narration per world

* Good, because it is trivial to build.
* Bad, because nothing is held fixed between worlds; the "diff" is noise. Violates INV-4, INV-5, D5-ii.

## More Information

* Interview decision D2 (truth source; drill-down stretch), 2026-09-16; brainstorm notes on vertical/horizontal causality, Heaviside/Dirac, actuarial wipe-out (`docs/initial-brainstorming.md`).
* `docs/research/02-causal-modeling-formalisms.md` §1 (formalism table), §3 (link fields, aggregation formula, Hormuz example), §4 (build/bend/bin verdicts), §6.
* Pearl's causal hierarchy (rung 2 only; rung 3 out of reach without exogenous noise terms): https://www.emergentmind.com/topics/pearl-s-causal-hierarchy-pch
* Related: ADR-0003, ADR-0004; the `refine` op and probes (FR-18/20) extend this ADR in stack 06.
