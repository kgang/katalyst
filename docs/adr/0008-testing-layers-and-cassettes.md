---
# ADR-0008: Four test layers (five since the 2026-09-17 amendment); the LLM boundary is tested with committed cassettes and CI needs no API key; three tiers of browser testing (2026-09-21)
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/02-causal-modeling-formalisms.md
informed: future agents adding tests or prompts
supersedes: none
superseded-by: none
spec-impact: spec/generation/ (Testing), spec/graph/ and spec/multiverse/ (Invariants → test names)
---

# ADR-0008: Four test layers (five since the 2026-09-17 amendment); the LLM boundary is tested with committed cassettes and CI needs no API key; three tiers of browser testing (2026-09-21)

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

**Layer 5 — worked examples (`backend/tests/unit/fixtures/`, added by amendment 2026-09-17).** The stored example maps — today the Strait of Hormuz map and its strike branch — are tested as data: each validates clean, exercises every shape the rules layer defines, and survives the trip to the browser. They are example tests, not property tests, and they are the golden inputs the engine and canvas stacks build on.

**Layer 4 — frontend.** vitest with Testing Library for the layout-pinning logic, the diff-state reducer, and the intervention-panel reducer, and a small suite of end-to-end browser tests that start both halves and drive the real app (ADR-0007 Confirmation). *(This said "One end-to-end browser test" until the 2026-09-21 amendment below; how many there are is deliberately not written here, because it moves with nearly every browser pull request. How much of the suite a change has to run is the thing worth recording, and the amendment says.)*

**Deliberately skipped in v1:** a model grading narrative quality; image snapshot comparisons; contract tests between services; load tests; mutation testing (breaking code on purpose to see whether tests notice); coverage thresholds outside `domain/`. *("More than one end-to-end test" was on this list until the 2026-09-21 amendment.)*

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

## Amendment (2026-09-17)

Stack 02 added a fifth kind of test that the four layers above did not name: the worked-example tests under `backend/tests/unit/fixtures/`, which check the stored example maps as data. Layer 5 above describes it. The four original layers, the cassette rules, and the keyless build are unchanged. Amended in place at Kent's request rather than superseded, because nothing in the decision changed — one layer was missing from the list.

## Amendment (2026-09-21) — how much browser testing a change needs

Kent asked on 2026-09-21 where the standing bar — *run the end-to-end tests twenty times from cold before a pull request* — was written down. **Nowhere in the committed repository.** No decision record, no spec chapter, no `Makefile` target, no line in the build: a search of everything committed found it in none of them. It was one coordinator's habit, kept only in git-ignored working notes, and it had grown out of five tests in stack 04 that were called flaky and were each a real defect a reader could hit.

**What was measured that day.** The twenty-three-minute bar was run twice in full and a third time to five runs of twenty — **about fifty-two minutes**, read off the queue's own log rather than multiplied out — and caught nothing that one run plus the build would not have caught.

* A wording mismatch between two branches failed **seventeen cold runs of seventeen**. One run finds that.
* A layout race passed **twenty cold runs of twenty** on the developer's machine and failed the build's **first** run on a slower one. Throttling the processor did not reproduce it — that slows the page, not the layout's background thread. Starting that thread nine hundred milliseconds late reproduced it at once, and it is now pinned by a test with no browser that runs in milliseconds.
* The same day a generated numbers file matched **byte for byte** across macOS/Arm and Linux/x86-64 and still failed its own margin test on Linux. With about two hundred and eighty numbers, some value sits on a rounding boundary on some machine at any digit count, so that check now compares numbers within a stated tolerance and every word exactly.

Nothing in the decision above changes — the layers, the recorded responses, the keyless build. What follows is how much of layer 4's browser suite a change has to run.

**Tier 1 — every pull request that touches the browser.** One run of the end-to-end tests from cold on the developer's machine, and the build. The build is a second machine, slower and different **on purpose**: it is the cheapest way there is to run the same tests under a different set of timings, and it is what found the layout race that twenty local runs missed.

**Tier 2 — a change to timing-sensitive code**: the canvas, the layout, the stream, the growing map, keyboard focus. Tier 1, and a test **with no browser** that injects the bad timing deliberately — a late layout answer, a dropped size notification. Two exist and are the pattern to copy:

| The bad timing | The test with no browser |
|---|---|
| The layout's background thread answers after the map has already moved on | `frontend/src/graph/__tests__/onTheGlass.test.ts` — walks two real runs on a machine whose first layout answer is thrown away |
| The browser abandons a tile's size notification when too many fall due in one frame, so a wire's ends are never measured | `frontend/src/graph/__tests__/ports.test.tsx` — every wire's two ends are declared rather than measured. Its end-to-end twin, `test_the_arrows_are_drawn_when_the_browser_drops_a_size_notification` in `frontend/e2e/hormuz.spec.ts`, makes the browser drop them on purpose |

**Tier 3 — a repeat bar, and only when a specific rare failure has been seen.** Then it is *that one test*, not the suite, and it is sized to the failure's own rate rather than to a round number.

Where the size comes from, in words: a fault that shows once in every thousand runs survives one clean run with a chance of 0.999, and survives *n* clean runs with 0.999 multiplied by itself *n* times. That falls under five per cent at about three thousand runs — so three thousand clean runs is what it costs to be ninety-five per cent sure it is gone. The same arithmetic at any rate: **a fault that shows once in every k runs costs about three times k.** Twenty runs, then, say almost nothing about anything rarer than one in ten. **And a rare failure is a bug until the evidence says otherwise**: five times in stack 04 "flaky" was a real defect.

**Two rules came with this.**

* A test that reads a **moment** — what stood on screen at the instant something arrived — gets a no-browser twin that injects the adverse timing on purpose. That is what pinned both of 2026-09-21's real races, in milliseconds.
* A check that compares **numbers** uses a stated tolerance, never text.

**And one correction.** Layer 4 above said "One end-to-end browser test", and "more than one end-to-end test" sat on the deliberately-skipped list. Both were out of date: there is a small suite now. Neither line carries a count, because the count moves with nearly every browser pull request and a number nobody updates is worse than no number.

Amended in place rather than superseded, because nothing in the decision changed — the layers, the cassettes and the keyless build stand exactly as they were, and this adds the one thing the record never said: how much of the browser suite a change owes.
