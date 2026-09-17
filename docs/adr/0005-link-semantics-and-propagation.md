---
# ADR-0005: Links carry trigger/sustain mode, log-odds strength, lag and shape; beliefs propagate by seeded forward Monte Carlo
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/initial-brainstorming.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/graph/ (Link fields, INV-7), spec/multiverse/ (propagation, retraction, observe sampling), spec/workbench/ (wire encoding UX-2, rendering NFR-1)
---

# ADR-0005: Links carry trigger/sustain mode, log-odds strength, lag and shape; beliefs propagate by seeded forward Monte Carlo

## Context and Problem Statement

"Change a box and see what happens downstream" needs a rule for how likelihoods move along the arrows. That rule must be elicitable from a language model with one number per incoming link rather than one per combination of parents, explainable one link at a time, honest about uncertainty, and able to express the two kinds of causality from the brainstorm: sequential (a domino, which stays fallen even if you stand the earlier one back up) and sustaining (a desk holding an apple, where the apple falls the moment the desk goes). It must also handle timing — spikes that fade versus steps that hold — because "Hormuz opens, Iran struck the next day" is a timing question. Which formalism, and which engine runs it?

## Decision Drivers

* FR-15 (local recomputation) — sustaining effects retract when their cause goes; triggered ones persist
* FR-19, FR-22, FR-23, FR-24 — the sensitivity sweep, the tail strip, the derived stop-loss, and the payoff distribution all need a distribution over many possible worlds
* INV-3 (assert versus learn) — learning a proposition must also revise what came before it
* INV-7 (honest numbers) — every belief stays within `0 ≤ lo ≤ p ≤ hi ≤ 1`, rendered at two significant figures with its interval (NFR-1)
* NFR-2 — pure, seeded, deterministic
* Elicitation cost: one number and one sentence per link
* Brainstorm: sequential versus sustaining causality; a spike versus a lasting step; "getting wiped out"

## Considered Options

* Strengths added on a log-odds scale with typed links, run as thousands of seeded random simulations; learning handled by keeping only the consistent draws
* A full Bayesian network with one number per combination of parent values, solved exactly
* Scenario or decision trees
* Markov chains analyzed for their long-run steady state
* Agent-based or role-played simulation
* Pure model narration, re-prompted for each world

## Decision Outcome

Chosen option: "Log-odds strengths on typed links, run as forward random simulation", because it is the only option that is at once cheap to elicit (one number per link), explainable link by link, capable of both asserting and learning, and able to produce the distributions FR-22, FR-23, and FR-24 need — while the rejected options are either impossible to elicit honestly, non-composable where chains rejoin, the wrong physics, or unauditable.

Log-odds is the scale on which independent influences *add* instead of multiply: each link contributes a fixed push toward or away from its child, and the pushes sum.

Link fields (`spec/graph/` carries the data model):

| Field | Meaning |
|---|---|
| `mode` | `trigger` — fires when the parent becomes true; the effect persists and fades by `half_life`; resetting the parent later does not undo it. `sustain` — the effect holds only while the parent holds; remove the parent and it retracts |
| `strength` | how much the link shifts the child's log-odds while active, signed |
| `lag` | delay before the effect begins |
| `shape` | `impulse` (a spike that fades with `half_life`), `step` (switches on and holds), `ramp` (builds up over `lag`) |
| `half_life` | how fast an `impulse` decays; unused otherwise |
| `reflexive` | a market feeding back on the world; requires `lag > 0` (INV-6, no instantaneous loops) |

How a child's likelihood is computed at time `t`:

```
log-odds P(child, t) = log-odds(prior_child) + sum over active links of  strength × shape(t − t_parent)
```

In words: start from the child's own base likelihood, then add one term per active link — its strength, scaled by where we are in that link's shape.

Execution is Monte Carlo — thousands of random simulations whose spread is the answer. Draw `N` seeded worlds (default 10 000). In each, every proposition is sampled parents-first from its aggregated log-odds. Asserting fixes a value and cuts the incoming links; learning fixes a value and keeps only the draws consistent with it (warn loudly when fewer than about 2% survive). A belief is the share of worlds in which the proposition came out true, with a standard interval for such a share. Payoffs are computed per world, so the 10th/50th/90th-percentile outcomes, the average loss in the worst 5% of runs, and the chance of being wiped out all fall out for free.

**Staged delivery.** Stack 03a — the engine stack of pull requests — may ship a single deterministic pass that computes only the average log-odds, provided its API and types are the ones the sampling engine will use. That pass must be replaced by random simulation no later than the first of: (a) learning is exposed in the interface (INV-3 needs upstream revision, which one pass cannot do), (b) the distribution rows appear on the thesis card (FR-24), (c) `refine` ships (INV-10 checks the split against the samples).

Rendering: two significant figures and the interval, always (`.35 (.2–.5)`); the canvas never receives more precision than that (NFR-1).

### Consequences

* Good, because every belief decomposes into a base likelihood plus one term per link, each with its own rationale — the audit trail *is* the formula.
* Good, because `trigger` versus `sustain` makes the Hormuz-then-strike branch behave correctly: the shipping-transit spike already fired and is fading, while the insurance step retracts once the strike removes what was sustaining it. This is about thirty lines of code and the best idea in the brainstorm.
* Good, because tails and wipe-outs are read off the spread of simulated worlds instead of being buried in an average.
* Bad, because adding log-odds assumes the links are independent once their parents are known; correlated causes get double-counted. Mitigated by `refine` — split the shared cause out as an explicit parent — and by showing intervals rather than points.
* Bad, because that interval mixes simulation noise with the elicited range, and a reader may take it for a calibration claim. The Inspector labels it "model interval, uncalibrated".
* Neutral, because 10 000 simulations over 60 propositions is milliseconds of array arithmetic; no performance concern at v1 scale (NFR-7).

### Confirmation

* Property tests in `tests/unit/domain/test_propagation.py`, run over many generated graphs: `test_probability_bounds` (INV-7), `test_propagation_idempotent`, `test_propagation_order_independent` (shuffling ties in the parents-first ordering), `test_trigger_persists_after_parent_reset`, `test_sustain_retracts_when_parent_removed`, `test_reflexive_requires_positive_lag`, `test_same_seed_same_world` (NFR-2).
* Golden test on the Hormuz fixture (stack 02): the "Iran struck next day" branch lowers the Brent-below-threshold terminal and raises the insurance terminal, in the directions the research gives.
* Frontend rendering test: a belief chip never shows more than two significant figures and always shows an interval.
* Review item at stacks 04, 05, and 06: if any of the three upgrade conditions holds and the single-pass version is still in place, block.

## Pros and Cons of the Options

### Log-odds strengths, typed links, forward random simulation

* Good, because elicitation is one number and one sentence per link, and the explanation is that same sentence.
* Good, because asserting and learning are both natural: cut the incoming links, or discard the inconsistent draws.
* Bad, because independence-given-parents is an approximation; made visible rather than hidden.

### Full Bayesian network with per-combination tables

* Good, because inference is exact and the semantics are textbook.
* Bad, because a proposition with `k` parents needs a number for every combination of their truth values — doubling with each parent — which the model will invent and no human can audit past three. High risk of fake precision.

### Scenario or decision trees

* Good, because each path reads as a story.
* Bad, because a shared downstream proposition gets duplicated in every branch, the tree explodes, and claimed coverage is a lie — the branches never add up to reality.

### Markov chains and steady states

* Good, because the brainstorm named them and the math is clean.
* Bad, because these events are one-shot: they never repeat enough to settle into a long-run average, so a steady state is a fiction here. The legitimate part of the idea — unrolling lagged links over time — is already in the chosen option (`lag`, `reflexive`).

### Agent-based or role-played simulation

* Good, because it might surface knock-on behaviour the graph lacks.
* Bad, because there is no validation story, variance and cost are high, and the audience will read it as theater. Kept only as red-team personas that propose missing structure (FR-9).

### Pure model narration per world

* Good, because it is trivial to build.
* Bad, because nothing is held fixed between worlds, so the "diff" is noise. Breaks locality (INV-4), replay (INV-5), and the D5-ii veto.

## More Information

* Interview decision D2 (truth source; the drill-down stretch), 2026-09-16; brainstorm notes on sequential versus sustaining causality, spikes versus steps, and the actuarial wipe-out (`docs/initial-brainstorming.md`).
* `docs/research/02-causal-modeling-formalisms.md` §1 (formalism table), §3 (link fields, aggregation formula, Hormuz example), §4 (verdicts), §6.
* Judea Pearl's causal hierarchy — we work at its second level, intervention ("what if we made X happen"), not the third, counterfactuals about a specific past: https://www.emergentmind.com/topics/pearl-s-causal-hierarchy-pch
* Related: ADR-0003, ADR-0004; `refine` and probes (FR-18, FR-20) extend this record in stack 06.
