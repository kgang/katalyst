---
# ADR-0003: The causal graph is a validated DAG owned by the domain layer; the LLM only proposes
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/01-landscape-and-competitors.md, docs/research/04-engineering-structure.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/graph/ (data model, INV-1/2/6/9), spec/generation/ (proposal contract)
---

# ADR-0003: The causal graph is a validated DAG owned by the domain layer; the LLM only proposes

## Context and Problem Statement

A language model will generate most of the graph's structure and numbers. The literature says such models are decent at *proposing* causal links and unstable at *asserting* them: they disagree with themselves run to run, invent loops, write claims no one can ever check, and attach numbers to nothing. Schema-constrained output — where the model must fill a fixed shape — guarantees well-formed JSON, not a sound graph. So who owns whether the graph is valid: the model, an automatic repair loop, or code we wrote and tested?

## Decision Drivers

* D5-ii (disgust veto: nothing unexplained) — every state traces to an input, a rule, or a source; a model-owned graph traces to nothing
* INV-1 (every proposition is resolvable) — criteria, adjudicating source, resolve-by date
* INV-2 (every link says why and where from) — rationale plus provenance; links claiming documents, history, or a market price must carry sources
* INV-6 (no loops) — the graph is a directed acyclic graph (a graph with no loops) once feedback links are set aside, and every feedback link has a delay
* INV-9 (every chain lands somewhere tradeable) — a `market` terminal, or an explicit "not tradeable, because…"
* NFR-2, NFR-3 — the core is pure, deterministic, and property-tested (thousands of generated cases, each failure shrunk to a minimal example)
* FR-13 (replay) — reproducing a world needs identifiers we mint, not ones the model invents

## Considered Options

* The domain layer owns validity: model output is a *proposal*, validated and rejected on failure; identifiers minted server-side
* Model-owned JSON passed straight to the UI with light shape checks
* Model plus an automatic repair loop: re-prompt on every validation failure until it passes
* User-built graphs only; the model never generates structure

## Decision Outcome

Chosen option: "Domain layer owns validity; the model proposes", because it is the only option under which INV-1, INV-2, INV-6, and INV-9 are *guaranteed by code we test* rather than requested of a model — and it makes the boundary between `domain/` (the rules) and `engine/` (the model-facing pipeline) the most legible design decision in the repo.

Rules:

1. `backend/src/katalyst/domain/` does no input or output, imports nothing model-related, and reads no clock. It defines `Proposition`, `Link`, `Belief`, `Graph`, and `validate(graph) -> list[Violation]`.
2. `engine/` receives a `GraphProposal` — the shape the model fills — and turns it into a `Graph` only through `domain.validate`. A proposal that breaks INV-1, INV-2, INV-6, or INV-9 is **rejected with the list of violations**, never silently patched up. `engine/` may then issue *one* targeted re-prompt naming those violations (bounded and logged); a second failure surfaces to the user as a proper error state, not a spinner.
3. Proposition and link identifiers are minted server-side as ULIDs (unique, time-sortable identifiers). The model refers to propositions by claim text and a position within its own proposal; `engine/` maps those to identifiers. This stops collisions when branches fork (FR-14).
4. Loops are found by running a cycle search over the graph with feedback links removed; any cycle is a violation, and so is a feedback link with no delay.
5. Provenance — where a number came from — is set by `engine/` from what actually happened: `documented` only if the retrieval step attached at least one source; otherwise `argued` or `asserted`. The model never declares its own provenance.

### Consequences

* Good, because the invariants are property tests over generated graphs, not instructions in a prompt.
* Good, because the UI can draw an `asserted` link honestly (dashed), since provenance is a fact about the pipeline rather than a claim by the model.
* Good, because a rejected proposal is an auditable artifact: the violation list is stored with the transcript (FR-13).
* Bad, because a strict validator rejects more often early on; mitigated by the single targeted re-prompt and by scored runs on the four assignment examples (ADR-0008).
* Neutral, because the domain model and the proposal schema are two sets of data shapes rather than one; they sit adjacent in the tree and the mapping between them is tested.

### Confirmation

* Import contract: `domain/` imports nothing from `engine/`, `api/`, `grounding/`, or the model SDK — enforced by an import-rule check (or a grep test) in the `backend` build job.
* Property tests: `test_validate_rejects_cycles`, `test_validate_rejects_unresolvable_proposition`, `test_validate_rejects_unsourced_documented_link`, `test_validate_requires_terminal`, each run over many generated graphs.
* A boundary test using a committed cassette — a recorded API response replayed in tests — in which the model returns a loop; the test asserts rejection with a non-empty violation list.
* Review item: no code path outside `engine/` builds a `Graph` from raw model output.

## Pros and Cons of the Options

### Domain layer owns validity; the model proposes

* Good, because correctness is enforced by tested code, and the model's job shrinks to what it is actually good at.
* Good, because identifiers, provenance, and validity are facts we control — which is exactly what replay (FR-13) needs.
* Bad, because there are two schemas, the proposal and the domain model, plus a mapping to maintain.

### Model-owned JSON passed through

* Good, because it is the least code.
* Bad, because every invariant becomes a polite request in a prompt; the first loop or the first false-precision number reaches the canvas. Fails the D5-ii veto.

### Model with an automatic repair loop

* Good, because it converges on a valid graph with no user involvement.
* Bad, because an unbounded loop hides failures, burns money, and yields graphs whose provenance is "the model eventually stopped violating things". One bounded re-prompt keeps the benefit without the opacity.

### User-built graphs only

* Good, because every number is the user's own.
* Bad, because it abandons the brief's core — generate the chain from a hypothesis — and the moment where the graph draws itself as the model reasons (FR-5).

## More Information

* Interview decisions D2 (truth source) and D5-ii (disgust: "not knowing why it did that"), 2026-09-16.
* `docs/research/02-causal-modeling-formalisms.md` §2 ("the model proposes, the human disposes, evidence adjudicates"), §3 (data model).
* `docs/research/01-landscape-and-competitors.md` §5(b), failure modes 1–3 and 5.
* `docs/research/04-engineering-structure.md` §2 (the `domain/`-versus-`engine/` split), §4 layers 1–2.
* Related: ADR-0004 (branches as patches), ADR-0005 (link semantics), ADR-0006 (schema-constrained model output).
