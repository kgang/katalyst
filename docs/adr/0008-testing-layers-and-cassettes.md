---
# ADR-0008: Four test layers; the LLM boundary is tested with committed cassettes and CI needs no API key
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/02-causal-modeling-formalisms.md
informed: future agents adding tests or prompts
supersedes: none
superseded-by: none
spec-impact: spec/generation/ (Testing), spec/graph/ and spec/multiverse/ (Invariants → test names)
---

# ADR-0008: Four test layers; the LLM boundary is tested with committed cassettes and CI needs no API key

## Context and Problem Statement

The product's correctness claims are mathematical — an intervention touches only its descendants, edits compose, probabilities stay in bounds — while its inputs come from a language model and are never the same twice. Tests must prove the invariants in `PRODUCT_REQUIREMENTS.md` §9 over *generated* inputs, exercise the model boundary without spending money or leaking keys, and still let us measure prompt quality when we choose to. Where does each kind of test live, and what do we deliberately not test?

## Decision Drivers

* INV-3, INV-4, INV-5, INV-6, INV-7, INV-10 (assert versus observe, locality, patch replay, no loops, belief bounds, refinement adds back up) must be property-tested, not example-tested (NFR-3): thousands of generated inputs, with any failure shrunk to the smallest example that still breaks.
* INV-13: `ci.yml`, the continuous-integration workflow that runs on every push, passes with no `ANTHROPIC_API_KEY`.
* NFR-8: a recorded response must never contain a key.
* D5(ii): a failing test must say *which invariant* broke.
* Solo developer: the suite must run in seconds locally.

## Considered Options

* A. **Four layers: pure-domain property tests · boundary tests backed by cassettes (recorded API responses replayed in tests) · an out-of-band eval harness · thin frontend tests**
* B. Hand-written stand-ins for the vendor's client library.
* C. Live API calls in continuous integration, behind a stored secret.
* D. No tests at the model boundary; test only the domain.

## Decision Outcome

Chosen option: "A", because it puts the weight where the claims are (the domain), makes the boundary deterministic and key-free, and keeps prompt quality measurable without making the shared build slow, costly, or flaky.

**Layer 1 — pure domain (`backend/tests/unit/`).** The `hypothesis` library generates arbitrary valid graphs, branches, and intervention sequences. Named tests map to invariants:

| Invariant | Test |
|---|---|
| INV-3 | `test_do_leaves_ancestors_unchanged`, `test_observe_may_update_ancestors` |
| INV-4 | `test_intervention_locality` — non-descendants byte-identical |
| INV-5 | `test_apply_empty_is_identity`, `test_patch_concat_equals_sequential_apply`, `test_world_replays_from_base_branch_seed` |
| INV-6 | `test_apply_preserves_dag`, `test_reflexive_links_have_positive_lag` |
| INV-7 | `test_belief_bounds_after_any_sequence` |
| INV-10 | `test_refine_marginalizes_to_parent` |

`GraphEditMachine`, a `RuleBasedStateMachine` — a generated *sequence* of random interventions rather than one random input — re-checks INV-4, INV-6 and INV-7 after every step. Target: ≥85 % of `domain/` covered.

**Layer 2 — model boundary (`backend/tests/boundary/`).** `pytest-recording` (a wrapper over vcrpy) saves each real HTTP exchange to a cassette file and replays it from then on. Tests carry `@pytest.mark.vcr`; the build runs `record_mode=none`, so an unrecorded call fails rather than dialling out; `filter_headers=["x-api-key", "authorization"]` strips credentials before anything is written; cassettes are committed under `backend/tests/cassettes/`. `scripts/record-cassettes.sh` re-records with `--record-mode=rewrite` against a real key. One cassette deliberately holds a proposal that would close a loop, and the test asserts the validator rejects it (`test_expand_rejects_cycle`) — fitting the schema is not the same as being a valid graph (ADR-0003, ADR-0006).

**Layer 3 — evals (`evals/`).** `evals/cases/*.yaml` hold the four `ASSIGNMENT.md` examples. `make eval` runs live against `claude-opus-5` and asserts structure, never wording: no loops; at least one `market` or `not_tradeable` terminal (INV-9); `rationale` and `provenance` on every link; a source on every link marked `documented` (INV-2); resolution criteria on every proposition (INV-1); Verify cases return a graded path or an explicit `no_path` verdict (FR-7); non-zero `cache_read_input_tokens` on a run's second call, proving the prompt cache is hit. Results go to `evals/runs/<date>.tsv`. Not in the build.

**Layer 4 — frontend.** vitest with Testing Library for the layout-pinning logic, the diff-state reducer, and the intervention-panel reducer. One end-to-end browser test (ADR-0007 Confirmation).

**Deliberately skipped in v1:** a model grading narrative quality; image snapshot comparisons; contract tests between services; load tests; mutation testing (breaking code on purpose to see whether tests notice); more than one end-to-end test; coverage thresholds outside `domain/`.

### Consequences

* Good, because a reviewer can run the whole suite with no key in under a minute and read the invariant names as the test list.
* Good, because prompt changes have a regression harness (`make eval`) whose cost we choose when to pay.
* Bad, because cassettes drift when prompts change; re-recording is a scripted, documented step, and any pull request that changes a prompt must re-record.
* Bad, because evals are non-deterministic; we assert structure, not exact output, and keep them out of the build so flakiness never blocks a merge.
* Neutral, because `api/` and `engine/` orchestration are lightly tested by design; the README says so.

### Confirmation

* Continuous-integration job `backend`: `uv sync --frozen` (install the exact pinned dependencies) → `ruff check` and `ruff format --check` (lint and formatting) → `mypy --strict src/katalyst/domain` (type check) → `pytest --record-mode=none`. The job has no `ANTHROPIC_API_KEY` in its environment (INV-13); a test that needs one fails loudly, because vcrpy raises `CannotOverwriteExistingCassetteException` rather than making a live call.
* `gitleaks`, a secret scanner, runs before every commit and scans the cassettes.
* Pull-request template item: "prompt changed? cassettes re-recorded, `make eval` scorecard attached".

## Pros and Cons of the Options

### A. Four layers (chosen)

* Good, because the build is deterministic, cassettes carry real HTTP shapes, and invariants are checked over generated inputs.
* Bad, because two libraries to learn (vcrpy, hypothesis); both are mature.

### B. Hand-written stand-ins

* Good, because no cassette files.
* Bad, because a stand-in encodes our assumptions about the client library rather than its behaviour; it rots silently and never catches a real change of shape.

### C. Live API in continuous integration

* Good, because always current.
* Bad, because non-deterministic, costs money on every push, needs a secret in the build, and breaks INV-13.

### D. No boundary tests

* Bad, because the rejection path — loops, missing criteria — is exactly where the product's honesty lives.

## More Information

* Interview D5(ii) (traceability), D9 (decision-gated cadence — invariants are named before code).
* `docs/research/04-engineering-structure.md` §4 (testing layers) and §6 (invariants phrased as claims true for every input, each with a named generation strategy).
* pytest-recording: https://github.com/kiwicom/pytest-recording · hypothesis: https://hypothesis.readthedocs.io/
