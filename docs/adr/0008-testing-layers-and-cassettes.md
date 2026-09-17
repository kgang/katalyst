---
# ADR-0008: Four test layers; the LLM boundary is tested with committed cassettes and CI needs no API key
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/02-causal-modeling-formalisms.md
informed: future agents adding tests or prompts
supersedes: none
superseded-by: none
spec-impact: spec/05-llm-boundary.md (Testing), spec/01-causal-graph.md and spec/02-interventions.md (Invariants → test names)
---

# ADR-0008: Four test layers; the LLM boundary is tested with committed cassettes and CI needs no API key

## Context and Problem Statement

The product's correctness claims are mathematical (locality, patch algebra, bounds) while its inputs are stochastic (an LLM). Tests must prove the invariants in `PRODUCT_REQUIREMENTS.md` §9 over *generated* inputs, exercise the LLM boundary without spending money or leaking keys, and still let us measure prompt quality when we choose to. Where does each kind of test live, and what do we deliberately not test?

## Decision Drivers

* INV-3, INV-4, INV-5, INV-6, INV-7, INV-10 must be property-tested, not example-tested (NFR-3).
* INV-13: `ci.yml` runs green with no `ANTHROPIC_API_KEY`.
* NFR-8: cassettes must never contain a key.
* D5(ii): a test failure must say *which invariant* broke.
* Solo developer: test suite must run in seconds locally.

## Considered Options

* A. **Four layers: pure-domain property tests · cassette-backed boundary tests · out-of-band eval harness · thin frontend tests**
* B. Hand-written mocks of the SDK client
* C. Live API calls in CI behind a secret
* D. No tests at the LLM boundary; test only the domain

## Decision Outcome

Chosen option: "A", because it puts the weight where the claims are (the domain), makes the boundary deterministic and key-free, and keeps prompt quality measurable without making CI non-deterministic or expensive.

**Layer 1 — pure domain (`tests/unit/`).** `hypothesis` strategies generate arbitrary valid graphs, branches, and intervention sequences. Named tests map to invariants:

| Invariant | Test |
|---|---|
| INV-3 | `test_do_leaves_ancestors_unchanged`, `test_observe_may_update_ancestors` |
| INV-4 | `test_intervention_locality` — non-descendants byte-identical |
| INV-5 | `test_apply_empty_is_identity`, `test_patch_concat_equals_sequential_apply`, `test_world_replays_from_base_branch_seed` |
| INV-6 | `test_apply_preserves_dag`, `test_reflexive_links_have_positive_lag` |
| INV-7 | `test_belief_bounds_after_any_sequence` |
| INV-10 | `test_refine_marginalizes_to_parent` |

A `RuleBasedStateMachine` (`GraphEditMachine`) applies random interventions and checks INV-4/6/7 after every step. Target ≥85 % coverage of `domain/`.

**Layer 2 — LLM boundary (`tests/boundary/`).** `pytest-recording` (vcrpy) with `@pytest.mark.vcr`; `record_mode=none` in CI; `filter_headers=["x-api-key", "authorization"]`; cassettes committed under `tests/cassettes/`. `scripts/record-cassettes.sh` re-records with `--record-mode=rewrite` against a real key. Includes a deliberately recorded proposal that would create a cycle, asserting the validator rejects it (`test_expand_rejects_cycle`) — schema-valid is not graph-valid (ADR-0003, ADR-0006).

**Layer 3 — evals (`evals/`).** `evals/cases/*.yaml` hold the four `ASSIGNMENT.md` examples. `make eval` runs live against `claude-opus-5` and asserts structure only, never text: DAG; ≥1 `market` or `not_tradeable` terminal (INV-9); every link has `rationale` and `provenance`; `documented ⇒ sources ≠ ∅` (INV-2); every proposition has resolution criteria (INV-1); Verify cases return a path or explicit `no_path` (FR-7); second call in a run has non-zero `cache_read_input_tokens`. Results are written to `evals/runs/<date>.tsv`. Not in CI.

**Layer 4 — frontend.** vitest + Testing Library for the layout pinning logic, the diff-state reducer, and the intervention panel reducer. One Playwright smoke (ADR-0007 Confirmation).

**Deliberately skipped in v1:** LLM-as-judge grading of narrative quality; SVG snapshot tests; contract tests; load tests; mutation testing; more than one e2e; coverage thresholds outside `domain/`.

### Consequences

* Good, because a reviewer can run the whole suite with no key in under a minute and read invariant names as the test list.
* Good, because prompt changes have a regression harness (`make eval`) with a cost we choose to pay.
* Bad, because cassettes drift when prompts change; re-recording is a documented, scripted step and a PR that changes a prompt must re-record.
* Bad, because evals are non-deterministic; we assert structure, not exact output, and accept flakiness there by keeping them out of CI.
* Neutral, because `api/` and `engine/` orchestration are lightly tested by design; the README says so.

### Confirmation

* CI job `backend`: `uv sync --frozen` → `ruff check` → `ruff format --check` → `mypy --strict src/katalyst/domain` → `pytest --record-mode=none`. The job has no `ANTHROPIC_API_KEY` in its environment (INV-13); a test that needs one fails loudly with vcrpy's `CannotOverwriteExistingCassetteException`.
* `gitleaks` in pre-commit scans cassettes.
* PR template item: "prompt changed? cassettes re-recorded, `make eval` scorecard attached".

## Pros and Cons of the Options

### A. Four layers (chosen)

* Good, because deterministic CI, real HTTP shapes in cassettes, invariants as properties.
* Bad, because two tools (vcrpy, hypothesis) to learn; both are mature.

### B. Hand-written SDK mocks

* Good, because no cassette files.
* Bad, because mocks encode our assumptions about the SDK, not its behaviour; they rot silently and never catch a real shape change.

### C. Live API in CI

* Good, because always current.
* Bad, because non-deterministic, costs money per push, needs a secret in CI, and violates INV-13.

### D. No boundary tests

* Bad, because the rejection path (cycles, missing criteria) is exactly where the product's honesty lives.

## More Information

* Interview D5(ii) (traceability), D9 (ADR-gated cadence — invariants are named before code).
* `docs/research/04-engineering-structure.md` §4 (testing layers) and §6 (invariants phrased as `∀x, P(x)` with a named strategy).
* pytest-recording: https://github.com/kiwicom/pytest-recording · hypothesis: https://hypothesis.readthedocs.io/
