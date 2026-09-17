---
# ADR-0004: Branches are ordered patch lists over an immutable base graph; do and observe are distinct
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/03-ui-ux-directions.md, docs/research/04-engineering-structure.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/02-interventions.md (ops, patch algebra, INV-3/4/5/10/11), spec/04-canvas.md (diff rendering)
---

# ADR-0004: Branches are ordered patch lists over an immutable base graph; do and observe are distinct

## Context and Problem Statement

The multiverse is the product: "Hormuz opens, but Iran is struck the next day" must fork a world, re-propagate only what changed, and stay comparable to the base. We need a representation of a branch that composes, diffs, replays, and keeps the user's beliefs distinct from the model's and the market's. We also need to decide whether "what if X" means *asserting* X (Pearl's `do`, cut incoming edges) or *learning* X (`observe`, update parents too) — most tools conflate them.

## Decision Drivers

* FR-14, FR-15, FR-16 — interventions, local re-propagation, diff
* INV-3 — `do(n)` changes no ancestor of `n`; `observe(n)` may
* INV-4 — locality: non-descendants byte-identical between base and branch
* INV-5 — base immutable; branch = ordered patch list; patch algebra; replay from `(base id, branch, seed)`
* INV-10 — `refine` marginalizes back to the parent
* INV-11, D8 — `model`, `user`, `market` beliefs stored separately; the user's prior is a first-class typed input
* FR-13 — replayability; NFR-2 — determinism
* UX: the ghost-overlay diff needs both worlds live at once (`docs/research/03` §2)

## Considered Options

* Branch = ordered list of typed interventions (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) applied to an immutable base; worlds are derived
* Copy-on-branch: each branch is a full independent graph, edited in place
* Re-prompt the LLM for a fresh graph per branch, seeded with the base narrative
* Conditioning only: a single `set` operation with observe semantics; no `do`

## Decision Outcome

Chosen option: "Branch = ordered patch list over an immutable base", because a patch list is the only representation under which INV-4 and INV-5 are provable properties of pure functions, diff is structural (the patch is the diff), and replay is free.

Definitions (`spec/02-interventions.md` carries the full types):

* `Intervention` is a tagged union: `do(node, value, at?)`, `observe(node, value)`, `insert(node, links)`, `retune(link, strength)`, `refine(node, into: [nodes], reconcile: marginalize)`, `believe(node, belief)`.
* `Branch = {id, parent?: BranchId, label, interventions: [Intervention]}`. Branch composition is list concatenation; a child branch's list is applied after its parent's.
* `World = propagate(apply(base, branch.interventions), seed)`. Worlds are never stored as the source of truth; they are cached derivations.
* `do` severs incoming links to the node for the branch and fixes its value; `observe` fixes the value and lets parents update (rejection sampling in ADR-0005). The UI offers them as different verbs ("assume" / "learn") and never merges them.
* Beliefs: `Proposition.beliefs: {model: Belief, user?: Belief, market?: Belief}`. A user edit to a probability is a `user` belief, never an overwrite of `model`. A patch that sets a user belief is the `believe` op: it is recorded in the branch like any other intervention (so it replays and diffs), it never alters `model` or `market` beliefs, and in v1 it is not propagated — the user's number is shown beside the model's, not pushed through the graph. Propagating a user's world ("your world") is stack 06 material.
* Locality: the propagation engine recomputes only `descendants(n) ∪ {n}` for an intervention on `n` (with `sustain`-retraction per ADR-0005); everything else is structurally shared with the base.

### Consequences

* Good, because branch creation is O(1) and diff is O(|patch| + |descendants|); 4+ live branches are cheap.
* Good, because the ghost overlay and delta rail read the same union layout, since the base is never mutated.
* Good, because the user's worldview (D8) is a visible, diffable layer rather than lost in the model's numbers.
* Bad, because `insert` may need an LLM call to propose links for the new proposition; that call is scoped to the affected subtree and recorded in the branch (FR-9), not a whole-graph regeneration.
* Bad, because `refine` with marginalization is the hardest op; it ships in stack 06, but the type exists from stack 02 so nothing is retrofitted.
* Neutral, because deleting a base proposition is not an op; "killed" in a diff means "value forced false / disconnected by `do`", which is what the UI shows.

### Confirmation

* Property tests in `tests/unit/domain/test_patches.py`: `test_apply_identity` (`apply(g, []) == g`), `test_apply_concat` (`apply(apply(g,p),q) == apply(g,p+q)`), `test_intervention_locality` (INV-4), `test_do_leaves_ancestors_unchanged` and `test_observe_may_change_ancestors` (INV-3), `test_refine_marginalizes` (INV-10, stack 06), `test_beliefs_never_merged` (INV-11: no function returns a single number derived from two owners).
* `hypothesis` `RuleBasedStateMachine` over random intervention sequences asserting DAG-ness and INV-7 bounds after every step.
* Replay test: two worlds from the same `(base id, branch, seed)` are byte-identical (NFR-2).
* Review item: the API exposes `POST /branches` taking interventions, never `PUT /graphs/{id}` mutating a base.

## Pros and Cons of the Options

### Patch list over immutable base

* Good, because patches compose, diff, and replay by construction; locality is a theorem, not a hope.
* Good, because storage is the base plus small patches.
* Bad, because every user action must be expressible as one of five ops; this is a feature (auditability) that occasionally feels restrictive.

### Copy-on-branch full graphs

* Good, because the mental model is simple: a branch is a file.
* Bad, because diff requires graph matching; locality cannot be asserted; the user's edits and the model's numbers blur; storage grows linearly with branches.

### Re-prompt the LLM per branch

* Good, because it captures second-order narrative effects the math misses.
* Bad, because nothing is held fixed between worlds, so the diff is noise plus signal with no way to tell which; breaks INV-4 and FR-13. Rejected outright (`docs/research/02` §1, "LLM-as-simulator").

### Conditioning only (no `do`)

* Good, because it is one operation.
* Bad, because "Hormuz opens" as a *hypothesis* must not update "a US–Iran deal happened" — that is the intervention/observation distinction the audience will check (`docs/research/01` §5(b) item 5).

## More Information

* Interview decisions D8 (user priors first-class) and D1 (one graph, two doors), 2026-09-16.
* `docs/research/02-causal-modeling-formalisms.md` §1 (do vs observe, Pearl rung 2), §3 (`Intervention`/`Branch` types, Hormuz worked example).
* `docs/research/03-ui-ux-directions.md` §2 (ghost overlay, delta rail, Loom two-pane lesson).
* `docs/research/04-engineering-structure.md` §4 layer 1 (patch algebra tests), §6 (INV phrasing).
* Related: ADR-0003 (domain owns validity), ADR-0005 (propagation semantics).
