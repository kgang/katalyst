---
# ADR-0006: Elicit graph structure through Anthropic structured outputs, one proposal per call
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/02-causal-modeling-formalisms.md, docs/research/04-engineering-structure.md, the claude-api skill (python/claude-api/README.md, tool-use.md, streaming.md)
informed: future agents working in backend/src/katalyst/engine
supersedes: none
superseded-by: none
spec-impact: spec/generation/ (all sections), spec/graph/ (data model is the LLM schema)
---

# ADR-0006: Elicit graph structure through Anthropic structured outputs, one proposal per call

## Context and Problem Statement

The engine turns a typed-in hypothesis into a graph of checkable claims joined by typed causal links (FR-4: every claim resolvable, every link sourced). It streams that graph to the browser as it grows (FR-5, UX-8), attaches evidence to links (FR-28), and leaves a transcript we can replay and price (FR-13, replay from graph, branch and seed; NFR-6, tokens and dollars per generation).

How do we call the model so its answer is guaranteed to fit our schema, arrives one piece at a time, and never decides whether the graph itself is legal — that job belongs to the domain layer (ADR-0003)?

## Decision Drivers

* D5(ii), the "not knowing why it did that" veto: every node traces to an input, a rule, or a cited source. The transcript is part of the product.
* FR-5 / UX-8: the graph growing *is* the loading state; a spinner then a finished graph is a veto condition.
* INV-1, INV-2, INV-6 (resolution criteria present; rationale and provenance present; no loops): fitting the schema is not enough. The domain layer must still reject loops, missing resolution criteria, and a link marked `documented` that cites nothing.
* Minimal Output Principle (house rule): one call takes one thing and returns one thing, never a list in and a list out. Lists are assembled by our pipeline.
* NFR-6: model, tokens, cache hits, and dollars recorded per generation.
* INV-13, the test suite runs with no API key: the boundary must be recordable as *cassettes* — real API responses saved to disk and replayed in tests (ADR-0008).

## Considered Options

* A. One giant prompt returning the whole graph as one structured object.
* B. Tool use with `strict: true` tools (`add_node`, `add_edge`) in an agentic loop — the model picks which tool to call, over and over, until it stops.
* C. Free text, then regular expressions and JSON repair.
* D. A framework abstraction (LangChain / LangGraph) over the vendor's own client library.
* E. **A pipeline of small structured calls, each returning one proposal, composed by domain code.**

## Decision Outcome

Chosen option: "E", because it alone keeps one call to one result, streams one proposal at a time, and leaves every accept/reject decision in typed domain code, where generated-input tests can hammer it.

Concretely:

* **Client library and model.** The `anthropic` Python SDK — the vendor's official client library — with `model="claude-opus-5"` and `thinking={"type": "adaptive"}`, which lets the model decide how much to think per call. No `temperature`, no `top_p`; both are rejected on Opus 5. Reproducibility comes from recording calls, not sampling settings; NFR-2 asks determinism of propagation, not generation.
* **One data model, three uses.** `Proposal` — a proposition plus its incoming link, or a typed `Stop` — is one pydantic model (a Python class that validates its own fields). It is the `output_format=` handed to `client.messages.parse(...)`, whose `.parsed_output` is a validated instance; it is what the web API returns; and `openapi-typescript` derives the TypeScript type from it (ADR-0007). No second schema, anywhere.
* **Pipeline shape.** `expand(frontier_node)` calls `messages.parse` with the graph so far and the children already there, asking for *one* new child proposition and link, or `Stop`. It repeats until `Stop` or a depth/width cap, runs frontier nodes concurrently, and emits one server-sent event — a one-way stream from server to browser — per accepted proposal. The domain layer (ADR-0003) checks each proposal for loops, resolvability, and the sources its provenance promises, then rejects rather than silently repairs. A rejection is itself a streamed event: "proposal rejected: would create a loop".
* **Grounding.** The `web_search_20260209` server-side tool is declared on calls that need evidence; `code_execution` is *not* also declared, since dynamic filtering already runs it. Citations from the results fill the link's `sources`; a link that turns up nothing is marked `asserted`, never `documented`.
* **Caching.** The system prompt (vocabulary, schema guidance, house rules) is a stable first block marked `cache_control={"type": "ephemeral"}`, so prompt caching applies: the API reuses the unchanged prefix and repeat calls cost less. The graph so far follows it. Each generation records `usage.cache_read_input_tokens`; a run where that stays zero fails the eval harness's cache check.
* **Refusals.** `stop_reason == "refusal"` is handled explicitly — read `stop_details`, surface it as a rejected proposal with its reason. Server-side `fallbacks="default"` (beta `server-side-fallback-2026-07-01`, via `client.beta.messages`), which quietly reroutes a refused call elsewhere, is *not* enabled in v1: a refusal here should be seen, not hidden (D5(ii)). Revisit if evals turn up refusals.
* **Cost.** Every call's `usage` folds into a `GenerationReceipt` — model, input, output and cached tokens, dollars at the cached price table — stored with the graph, shown in the Inspector's transcript view.

### Consequences

* Good, because each proposal is a small, inspectable, replayable unit; the transcript reads as an argument being built.
* Good, because rejections are first-class — the model never "owns" a loop or an unresolvable claim.
* Good, because cassettes are small and stable per call rather than one 40 KB blob.
* Bad, because more round-trips than option A: a 30-node graph is about 40 calls. Mitigated by the shared cached prefix, concurrency across the frontier, and depth and width caps.
* Bad, because `messages.parse` does not stream tokens; a call takes 2–6 s to return a whole proposal. Acceptable: UX-8 wants the graph to grow node by node, not word by word. If that proves wrong, `client.messages.stream(..., output_format=Proposal)` with `get_final_message().parsed_output` is the drop-in upgrade path.
* Neutral, because the ensemble pass (FR-8, several independent generations reconciled into one graph) and adversarial critique (FR-9) become extra stages over the same call shape.

### Confirmation

* `tests/boundary/test_expand_cassettes.py` — `expand()` against recorded responses, including a recorded proposal that would close a loop and must be rejected (`test_expand_rejects_cycle`).
* `evals/cases/*.yaml` on the four assignment examples, asserting structure and never wording: no loops; at least one terminal of kind `market`, which names a tradeable instrument; a rationale on every link; a source on every `documented` link. Run by `make eval`.
* `test_generation_receipt_records_cache_reads` — the receipt shows non-zero `cache_read_input_tokens` after the second call in a run.
* Review checklist: no `output_config={"format": ...}` dicts alongside `output_format=Model`; no `budget_tokens`; no `temperature`.

## Pros and Cons of the Options

### A. One giant structured object

* Good, because one call, cheapest in round-trips.
* Bad, because nothing can be shown until the end; one loop invalidates the whole object; it asks the model for a list instead of one thing; and it records as a 40 KB cassette.

### B. Strict tools in an agentic loop

* Good, because incremental by nature, and `strict: true` pins the shape of each tool's arguments.
* Bad, because the loop's control flow lives in the model's choice of tool calls, not in our pipeline — harder to cap, replay, and test than a pure function returning one proposal.

### C. Free text + regular expressions

* Bad, because nothing is validated, it breaks on wording changes, and the transcript is prose the domain layer cannot reason over.

### D. Framework abstraction

* Bad, because it hides the exact calls behind a moving abstraction when the reader wants to see the calls, and adds a dependency that has not earned its place.

### E. One proposal per call (chosen)

* Good, because small, typed, streamable, testable, replayable.
* Bad, because more calls; mitigated as above.

## More Information

* Interview D2 (the model reasons out loud; anchored to a market price where one exists) and D5(ii) (traceability).
* `docs/research/02-causal-modeling-formalisms.md` §2 (ensembling, adversarial critique) and §6 (what to build in week 1).
* `docs/research/04-engineering-structure.md` §1 (structured-output ergonomics) and §4 (cassettes).
* claude-api skill: `python/claude-api/tool-use.md` on structured outputs, `README.md` on prompt caching and stop reasons, and its API-drift table (adaptive thinking, `web_search_20260209`).
