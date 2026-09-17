---
# ADR-0006: Elicit graph structure through Anthropic structured outputs, one proposal per call
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/04-engineering-structure.md, the claude-api skill (python/claude-api/README.md, tool-use.md, streaming.md)
informed: future agents working in backend/src/katalyst/engine
supersedes: none
superseded-by: none
spec-impact: spec/05-llm-boundary.md (all sections), spec/01-causal-graph.md (data model is the LLM schema)
---

# ADR-0006: Elicit graph structure through Anthropic structured outputs, one proposal per call

## Context and Problem Statement

The engine must turn a natural-language hypothesis into a graph of resolvable propositions and typed links (FR-4), stream it to the browser as it grows (FR-5, UX-8), ground links in evidence (FR-28), and leave a replayable, costed transcript (FR-13, NFR-6). How do we call the model so that its output is schema-valid by construction, arrives incrementally, and never owns graph validity (ADR-0003)?

## Decision Drivers

* D5(ii): every node must be traceable to an input, a rule, or a source — the transcript is part of the product.
* FR-5 / UX-8: streaming growth is the loading state; a spinner-then-dump is a veto condition.
* INV-1, INV-2, INV-6: schema validity is necessary but not sufficient; the domain layer must reject cycles, missing resolution criteria, and unsourced `documented` links.
* Constitution, Minimal Output Principle: `Agent: (Input, X) → Y`, not `(Input, [X]) → [Y]`; compose at the pipeline level.
* NFR-6: model, tokens, cache hits, and dollars recorded per generation.
* INV-13: the boundary must be recordable as cassettes (ADR-0008).

## Considered Options

* A. One giant prompt returning the whole graph as one structured object.
* B. Tool use with `strict: true` tools (`add_node`, `add_edge`) in an agentic loop.
* C. Free text + regex/JSON-repair.
* D. A framework abstraction (LangChain / LangGraph) over the SDK.
* E. **A pipeline of small structured calls, each returning one proposal, composed by domain code.**

## Decision Outcome

Chosen option: "E", because it is the only option that satisfies the Minimal Output Principle, streams naturally at proposal granularity, and keeps every accept/reject decision in typed domain code where it can be property-tested.

Concretely:

* **SDK and model.** `anthropic` Python SDK, `model="claude-opus-5"`, `thinking={"type": "adaptive"}`. No `temperature`/`top_p` (rejected on Opus 5); determinism comes from recording, not sampling parameters (NFR-2 is about propagation, not generation).
* **One pydantic model, three uses.** `Proposal` (a `Proposition` plus its incoming `Link`, or a typed `Stop`) is the `output_format=` passed to `client.messages.parse(...)`, whose `.parsed_output` is a validated instance; the same model is the FastAPI DTO; `openapi-typescript` derives the TS type (ADR-0007). There is no second schema anywhere.
* **Pipeline shape.** `expand(frontier_node)` calls `messages.parse` with the graph-so-far and the set of existing children, asking for *one* new child proposition + link or `Stop`. The pipeline repeats until `Stop` or a depth/width cap, runs frontier nodes concurrently, and emits one SSE event per accepted proposal. The domain layer (ADR-0003) validates each proposal — cycle, resolvability, provenance ⇒ sources — and rejects rather than repairs; a rejection is itself an SSE event ("proposal rejected: would create cycle").
* **Grounding.** The `web_search_20260209` server tool is declared on proposal calls that need evidence; `code_execution` is *not* also declared (dynamic filtering already runs it). Citations from search results populate `Link.sources`; a link with no result is marked `asserted`, never `documented`.
* **Caching.** The system prompt (vocabulary, schema guidance, house rules) is a stable first block with `cache_control={"type": "ephemeral"}`; the graph-so-far follows it. Each generation records `usage.cache_read_input_tokens`; a zero across a run fails the eval harness's cache check.
* **Refusals.** `stop_reason == "refusal"` is handled explicitly (read `stop_details`, surface as a rejected proposal with reason). Server-side `fallbacks="default"` (beta `server-side-fallback-2026-07-01`, via `client.beta.messages`) is *not* enabled in v1: a refusal in this domain should be visible, not silently rerouted (D5(ii)). Revisit if refusals are observed in evals.
* **Cost.** Every call's `usage` is folded into a `GenerationReceipt` (model, input/output/cached tokens, dollars at the cached price table) stored with the graph and shown in the Inspector transcript view.

### Consequences

* Good, because each proposal is a small, inspectable, replayable unit; the transcript reads as an argument being built.
* Good, because rejections are first-class — the model never "owns" a cycle or an unresolvable claim.
* Good, because cassettes (ADR-0008) are small and stable per call rather than one 40 KB blob.
* Bad, because more round-trips than option A: a 30-node graph is ~40 calls. Mitigated by caching (prefix is shared), concurrency across the frontier, and depth/width caps.
* Bad, because `messages.parse` does not stream tokens; within-call latency is a full proposal (~2–6 s). Acceptable because node-granularity streaming is what UX-8 needs. If it isn't, `client.messages.stream(..., output_format=Proposal)` with `get_final_message().parsed_output` is the drop-in upgrade path.
* Neutral, because ensemble (FR-8) and adversarial critique (FR-9) become additional pipeline stages over the same call shape.

### Confirmation

* `tests/boundary/test_expand_cassettes.py` — cassette-backed tests for `expand()` including a recorded cyclic proposal that the validator rejects (`test_expand_rejects_cycle`).
* `evals/cases/*.yaml` on the four assignment examples with structural assertions (DAG, ≥1 `market` terminal, every link has rationale, `documented ⇒ sources`), run via `make eval`.
* `test_generation_receipt_records_cache_reads` — receipt has non-zero `cache_read_input_tokens` after the second call in a run.
* Review checklist: no `output_config={"format": ...}` dicts alongside `output_format=Model`; no `budget_tokens`; no `temperature`.

## Pros and Cons of the Options

### A. One giant structured object

* Good, because one call, cheapest in round-trips.
* Bad, because no streaming until the end; a single cycle invalidates the whole object; violates the Minimal Output Principle; 40 KB cassettes.

### B. Strict tools in an agentic loop

* Good, because incremental by nature and `strict: true` guarantees argument shapes.
* Bad, because the loop's control flow lives in the model's `tool_use` choices, not in our pipeline; harder to cap, replay, and test than a pure function that returns one proposal.

### C. Free text + regex

* Bad, because unvalidated, brittle, and the transcript is prose the domain layer cannot reason over.

### D. Framework abstraction

* Bad, because it hides the exact SDK surface behind a moving abstraction; the reader wants to see the calls. Adds a dependency with no earned purpose (Tasteful).

### E. One proposal per call (chosen)

* Good, because small, typed, streamable, testable, replayable.
* Bad, because more calls; mitigated as above.

## More Information

* Interview D2 (LLM reasoning + explicit rationale; market-anchored) and D5(ii) (traceability).
* `docs/research/02-causal-modeling-formalisms.md` §2 (ensembling, adversarial critique) and §6 (what to build in week 1).
* `docs/research/04-engineering-structure.md` §1 (structured output ergonomics) and §4 (cassettes).
* claude-api skill: `python/claude-api/tool-use.md` → Structured Outputs; `README.md` → Prompt Caching, Stop Reasons; API-drift table (adaptive thinking, `web_search_20260209`).
