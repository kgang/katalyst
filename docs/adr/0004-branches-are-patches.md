---
# ADR-0004: Branches are ordered patch lists over an immutable base graph; do and observe are distinct
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/03-ui-ux-directions.md, docs/research/04-engineering-structure.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/multiverse/ (ops, patch algebra, INV-3/4/5/10/11), spec/workbench/ (diff rendering)
---

# ADR-0004: Branches are ordered patch lists over an immutable base graph; do and observe are distinct

## Context and Problem Statement

The multiverse is the product: "Hormuz opens, but Iran is struck the next day" must fork a world, recompute only what changed, and stay comparable to the original. We need a way to represent a branch that composes, diffs, replays, and keeps the user's own numbers separate from the model's and the market's. We also have to decide what "what if X" means: *asserting* X — Judea Pearl's `do`, where we make it so, which cuts the arrows coming into it — or *learning* X, which also revises what came before it. Most tools blur the two.

## Decision Drivers

* FR-14, FR-15, FR-16 — interventions fork a branch; only what is downstream recomputes; the two worlds can be diffed
* INV-3 (assert versus learn) — asserting a proposition changes nothing upstream of it; learning one may
* INV-4 (locality) — anything not downstream of the change is identical, byte for byte, between the base and the branch
* INV-5 (patches) — the base never changes; a branch is an ordered list of edits; applying no edits is a no-op; applying two lists in a row equals applying them joined; any world replays from base graph, branch, and random seed
* INV-10 (refine) — splitting a proposition into finer ones must leave the parent's likelihood intact
* INV-11 and D8 — the model's, the user's, and the market's numbers are stored separately; the user's own estimate is a first-class input
* FR-13 (replay) and NFR-2 (determinism)
* The faded before-and-after overlay needs both worlds alive at once

## Considered Options

* A branch is an ordered list of typed edits (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) over an untouched base; worlds are computed from it
* Copy on branch: every branch is a full, independent graph edited in place
* Re-prompt the model for a fresh graph per branch, seeded with the base narrative
* Learning only: one `set` operation that always revises upstream too; no way to assert

## Decision Outcome

Chosen option: "A branch is an ordered patch list over an immutable base", because a patch list is the only representation under which locality (INV-4) and replay (INV-5) are provable properties of pure functions, the diff is structural — the patch *is* the diff — and replay costs nothing.

Definitions (`spec/multiverse/` carries the full types):

* An intervention is exactly one of: `do(node, value, at?)`, `observe(node, value)`, `insert(node, links)`, `retune(link, strength)`, `refine(node, into: [nodes], reconcile: marginalize)`, `believe(node, belief)`.
* `Branch = {id, parent?: BranchId, label, interventions: [Intervention]}`. Branches compose by joining their lists; a child branch's edits are applied after its parent's.
* `World = propagate(apply(base, branch.interventions), seed)`. A world is never the source of truth; it is a cached result that can always be recomputed.
* `do` cuts the incoming links to the node for that branch and fixes its value; `observe` fixes the value and lets the parents move (by keeping only the consistent random draws, per ADR-0005). The interface offers them as two verbs — **"Suppose this is true"** and **"This happened"** (amended 2026-09-17; they read "assume" and "learn" when this record was written) — and never merges them.
* Beliefs live as `Proposition.beliefs: {model, user?, market?}`. A user editing a probability writes a `user` belief, never over the model's. That edit is the `believe` operation: recorded in the branch like any other, so it replays and diffs; it never touches the model's or the market's number; and in v1 it is not pushed through the graph — the user's number sits beside the model's. Propagating a user's whole world belongs to stack 06, the last stack of pull requests in the roadmap.
* Locality: the engine recomputes the changed proposition and its descendants and nothing else (with the retraction rule from ADR-0005); the rest is shared with the base outright.

### Consequences

* Good, because creating a branch is constant-time and a diff costs the size of the patch plus the descendants; four or more live branches stay cheap.
* Good, because the faded overlay and the ranked list of terminal changes share one layout, since the base is never mutated underneath them.
* Good, because the user's worldview (D8) is a visible, diffable layer instead of something lost inside the model's numbers.
* Bad, because `insert` may need a model call to propose links for the new proposition; that call is scoped to the affected subtree and recorded in the branch (FR-9), not a regeneration of the whole graph.
* Bad, because `refine` — splitting a proposition so the parts still add back up to the original — is the hardest operation; it ships in stack 06, but its type exists from stack 02, so nothing is retrofitted.
* Neutral, because deleting a base proposition is not an operation; "killed" in a diff means "forced false or cut off by an assertion", which is what the interface shows.

### Confirmation

* Property tests in `tests/unit/domain/test_patches.py`, each run over many generated graphs: `test_apply_empty_is_identity` (applying no edits changes nothing), `test_patch_concat_equals_sequential_apply` (applying two patches in sequence equals applying them joined), `test_intervention_locality` (INV-4), `test_do_leaves_ancestors_unchanged` and `test_observe_may_update_ancestors` (INV-3), `test_refine_marginalizes_to_parent` (INV-10, stack 06), `test_beliefs_never_merged` (INV-11 — no function returns a single number derived from two owners). *(Four of these names were corrected in place on 2026-09-17 to match ADR-0008, which is the record that owns test names; see the Amendment below.)*
* A stateful test that drives random sequences of interventions and asserts, after every step, that the graph still has no loops and that every probability stays within its interval (INV-7).
* Replay test: two worlds built from the same base graph, branch, and seed are byte-identical (NFR-2).
* Review item: the API exposes `POST /branches` taking interventions, never a call that mutates a base graph in place.

## Pros and Cons of the Options

### Patch list over an immutable base

* Good, because patches compose, diff, and replay by construction; locality is a theorem rather than a hope.
* Good, because storage is the base plus small patches.
* Bad, because every user action must be expressible as one of the six operations; this is a feature — auditability — that occasionally feels restrictive.

### Copy on branch, full graphs

* Good, because the mental model is simple: a branch is a file.
* Bad, because diffing then requires matching two graphs, locality cannot be asserted, the user's edits and the model's numbers blur together, and storage grows with every branch.

### Re-prompt the model per branch

* Good, because it could catch knock-on narrative effects the math misses.
* Bad, because nothing is held fixed between worlds, so the diff is signal and noise with no way to tell them apart; it breaks locality (INV-4) and replay (FR-13). Rejected outright.

### Learning only, with no way to assert

* Good, because it is one operation instead of two.
* Bad, because "Hormuz opens", posed as a hypothesis, must not quietly raise the odds that a US–Iran deal happened. That assert-versus-learn distinction is the one the audience will check.

## More Information

* Interview decisions D8 (the user's own estimates are first-class) and D1 (one map, two doors), 2026-09-16.
* `docs/research/02-causal-modeling-formalisms.md` §1 (assert versus learn), §3 (intervention and branch types, Hormuz worked example).
* `docs/research/03-ui-ux-directions.md` §2 (faded overlay, ranked delta list, two-pane lesson).
* `docs/research/04-engineering-structure.md` §4 layer 1 (patch tests), §6 (invariant phrasing).
* Related: ADR-0003 (the domain owns validity), ADR-0005 (propagation semantics).

## Amendment (2026-09-17)

This record stands; three of its statements are refined by decisions Kent took on 2026-09-17. Records are a journal, so the original text above is left as it was written, apart from the two places that already point here.

* **Locality (INV-4) is an affected set, not a downstream rule.** The invariant now reads: *an intervention changes only what is still connected to its subject in the graph the edit leaves behind.* One principle, from which the six operations get different reaches for a reason: `do` cuts the target's incoming arrows, so only its descendants stay connected to it, while `observe` cuts nothing, so its ancestors and what those ancestors cause stay connected too. The operational form — one affected set per operation, and the rule that the property test derives the set from the shape of the graph rather than from the engine's own bookkeeping — is the table in `spec/multiverse/interventions.md`. `PRODUCT_REQUIREMENTS.md` §9 carries the restated sentence.
* **`do` cuts the arrows present when it is applied; an arrow inserted later is live.** A `do` is a **timed assertion**: `do(H, at=1 October)` says H holds from the 1st, not that H is sealed for ever against anything the user adds next. That is the same reading of time the engine already uses for delays, shapes and half-lives (ADR-0005). It leaves INV-3 alone — `do(H)` still moves no ancestor of H — because H's later movement is attributed to the edits that caused it, `insert(S)` and `do(S)`, whose affected set includes H now that H is downstream of S. The interface consequence is the new UX-14: an assertion a later edit has overridden says so on the tile ("Supposed · Oct 1 → Retracted · Oct 2 by 'confirmed strike on Iranian territory'"), and a branch shows its edits in order.
* **The two verbs are "Suppose this is true" and "This happened".** Not "assume" and "learn", which were placeholders in the text above and read badly on a tile. The badges are **Supposed · date** and **Happened · date**, and the full set of six buttons and badges — plus one derived badge, **Retracted · date · by "…"** — is in `spec/vocabulary.md` under *Interface words*. The code names (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) are unchanged and never appear on screen.
* **Four test names in Confirmation were corrected in place**, rather than being left to contradict ADR-0008: `test_apply_empty_is_identity`, `test_patch_concat_equals_sequential_apply`, `test_observe_may_update_ancestors`, `test_refine_marginalizes_to_parent`. ADR-0008 owns test names; this record was drifting from it.
