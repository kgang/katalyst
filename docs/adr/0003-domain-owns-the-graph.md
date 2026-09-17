---
# ADR-0003: The causal graph is a validated DAG owned by the domain layer; the LLM only proposes
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/01-landscape-and-competitors.md, docs/research/04-engineering-structure.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/01-causal-graph.md (data model, INV-1/2/6/9), spec/05-llm-boundary.md (proposal contract)
---

# ADR-0003: The causal graph is a validated DAG owned by the domain layer; the LLM only proposes

## Context and Problem Statement

An LLM will generate most of the graph's structure and numbers. The literature says LLMs are decent at *proposing* causal edges and unstable at *asserting* them: run-to-run inconsistency, invented cycles, non-resolvable "vibe" propositions, unsourced numbers (`docs/research/02` §2). Structured outputs guarantee schema-valid JSON, not a semantically valid graph. Who owns graph validity — the model, a repair loop, or code we wrote and tested?

## Decision Drivers

* D5-ii — every state must be traceable to an input, a rule, or a source; a model-owned graph is untraceable
* INV-1 — every proposition is resolvable (criteria, source, resolve-by)
* INV-2 — every link has rationale and provenance; documented/historical/market-implied links have sources
* INV-6 — DAG after ignoring `reflexive` links; reflexive links have `lag > 0`
* INV-9 — every graph terminates in a `market` node or an explicit `not_tradeable`
* NFR-2, NFR-3 — the domain is pure, deterministic, and property-tested
* FR-13 — worlds are replayable; replay requires deterministic, server-minted identity

## Considered Options

* Domain layer owns validity: LLM output is a *proposal*, validated and rejected on failure; IDs minted server-side
* LLM-owned JSON passed through to the UI with light schema checks
* LLM with an automatic repair loop (re-prompt on validation failure until it passes)
* User-built graph only; the LLM never generates structure

## Decision Outcome

Chosen option: "Domain layer owns validity; LLM proposes", because it is the only option under which INV-1/2/6/9 are *guaranteed by code we test* rather than requested of a model, and it makes the `domain/` ↔ `engine/` boundary the most legible design decision in the repo.

Rules:

1. `backend/src/katalyst/domain/` has no I/O, no `anthropic` import, no clock. It defines `Proposition`, `Link`, `Belief`, `Graph` and a `validate(graph) -> list[Violation]`.
2. `engine/` receives a `GraphProposal` (LLM schema) and converts it to a `Graph` through `domain.validate`. A proposal that violates INV-1/2/6/9 is **rejected with the violation list**, never silently repaired. `engine/` may then issue *one* targeted re-prompt naming the violations (bounded, logged); a second failure surfaces to the user as a first-class error state.
3. Proposition and link IDs are minted server-side (ULIDs). The LLM refers to propositions by the claim text and a proposal-local index; `engine/` maps to IDs. This prevents collisions across branches (FR-14).
4. Cycles are detected with `networkx.simple_cycles` on the graph with `reflexive` links removed; any cycle is a violation. A `reflexive` link with `lag == 0` is a violation.
5. Provenance is set by `engine/` from what actually happened: `documented` only if the retrieval step attached ≥1 source; otherwise `argued` or `asserted`. The model does not self-declare provenance.

### Consequences

* Good, because the invariants are property tests over generated graphs, not prompt instructions.
* Good, because the UI can render an `asserted` link honestly (dashed), since provenance is a fact about the pipeline, not a claim by the model.
* Good, because a rejected proposal is an auditable artifact: the violation list is stored with the transcript (FR-13).
* Bad, because a strict validator will reject proposals more often early on; mitigated by the single targeted re-prompt and by evals on the four assignment examples (ADR-0008).
* Neutral, because the domain model and the LLM proposal schema are two pydantic models, not one; they are kept adjacent and the mapping is tested.

### Confirmation

* Import contract: `domain/` imports nothing from `engine/`, `api/`, `grounding/`, or `anthropic` — enforced by an `import-linter` contract (or a grep test) in the `backend` CI job.
* Property tests: `test_validate_rejects_cycles`, `test_validate_rejects_unresolvable_proposition`, `test_validate_rejects_unsourced_documented_link`, `test_validate_requires_terminal`, over a `hypothesis` graph strategy.
* Boundary test with a committed cassette in which the model returns a cycle; the test asserts rejection with a non-empty violation list.
* Review item: no code path outside `engine/` constructs a `Graph` from raw model output.

## Pros and Cons of the Options

### Domain layer owns validity; LLM proposes

* Good, because correctness is enforced by tested code; the model's job shrinks to what it is good at.
* Good, because IDs, provenance, and validity are facts we control, which is what replay (FR-13) needs.
* Bad, because two schemas (proposal, domain) and a mapping to maintain.

### LLM-owned JSON passed through

* Good, because it is the least code.
* Bad, because every invariant becomes a prompt request; the first cycle or `.347` reaches the canvas. Fails D5-ii.

### LLM with automatic repair loop

* Good, because it converges to a valid graph without user involvement.
* Bad, because unbounded loops hide failures, burn cost, and produce graphs whose provenance is "the model eventually stopped violating"; a single bounded re-prompt keeps the benefit without the opacity.

### User-built graph only

* Good, because every number is the user's.
* Bad, because it abandons the brief's core (generate chains from a hypothesis) and the streaming demo moment (FR-5).

## More Information

* Interview decision D2 (truth source) and D5-ii (disgust: "not knowing why it did that"), 2026-09-16.
* `docs/research/02-causal-modeling-formalisms.md` §2 (LLM causal discovery: "LLM proposes, human disposes, evidence adjudicates"), §3 (data model).
* `docs/research/01-landscape-and-competitors.md` §5(b) failure modes 1–3, 5.
* `docs/research/04-engineering-structure.md` §2 (`domain/` ↔ `engine/` split), §4 layer 1–2.
* Related: ADR-0004 (patches), ADR-0005 (link semantics), ADR-0006 (structured outputs).
