# ARCHITECTURE.md — Katalyst

> The technical counterpart to `PRODUCT_REQUIREMENTS.md`. That document says what the tool must do and why; this one says how the system is shaped, where each rule is enforced, and how it runs. It describes the system **as built and as planned**, and each section says which.

**Living document.** Last verified: 2026-09-17. Any pull request that changes a boundary, a layer, a data flow, or a runtime dependency updates this file in the same PR. A stale architecture doc is worse than none: it is the "not knowing why it did that" failure in written form.

**Status markers.** `[planned]` — decided, not yet in the repo. `[built]` — in the repo and covered by the tests named. `[stretch]` — designed for, not scheduled.

---

## 1. The system in one picture `[built]`

Both halves of the drawing below run today; the event stream, the model pipeline, the grounding adapters and the stored state are decided but unwritten, and are named again under it.

```
 ┌──────────────────────────── browser ─────────────────────────────┐
 │  React + TypeScript (Vite)                                       │
 │  workbench canvas · inspector · world-state strip · thesis dock  │
 └───────────────▲───────────────────────────────▲──────────────────┘
        HTTP JSON │                               │ server-sent events
                  │                               │ (one-way stream: proposals,
                  ▼                               │  rejections, propagation)
 ┌──────────────────────────── backend ─────────────────────────────┐
 │  FastAPI (Python web framework)                                  │
 │                                                                  │
 │  api/        routes, request/response shapes, the event stream   │
 │  engine/     talks to the model; turns answers into proposals    │
 │  domain/     PURE: graph rules, propagation, branches. No I/O.   │
 │  grounding/  adapters for outside data (Polymarket, FRED)        │
 │  settings.py the only place environment variables are read       │
 │                                                                  │
 │  storage: one SQLite file on a volume (sessions, branches,       │
 │           generation transcripts)                                │
 └──────┬──────────────────────┬────────────────────────┬───────────┘
        ▼                      ▼                        ▼
   Anthropic API         Polymarket Gamma API        FRED API
   (claude-opus-5,       (prediction-market          (economic series,
    web search tool)      prices, no key)             free key)
```

**What runs, and what is drawn ahead.** The browser app and the Python server both start, and `api/` answers three things for real: whether the server is up, what it calls itself, and the stored worked example. `domain/` holds the rules and nothing else. `[planned]` Four parts of the drawing have no code behind them. There is no event stream — every route today is an ordinary request and its answer. `engine/` holds identifier minting alone; nothing has ever called Anthropic's API. `grounding/` is an empty package; nothing has ever called Polymarket or FRED. There is no storage: no database file, no volume declared in either compose file, nothing kept between requests. Inside the browser box only a status screen exists; the canvas, the inspector, the world-state strip and the thesis dock are drawn because they are decided, not because they are written.

Two halves, one contract: the backend publishes an OpenAPI description (a machine-readable list of every route and data shape); the frontend's TypeScript types are generated from it and committed, and continuous integration fails if regeneration would change them. The two halves cannot drift silently.

---

## 2. The one rule that shapes everything `[built]`

Half of this is mechanical today: the boundary that keeps the rules layer pure is checked on every pull request, and `validate` already refuses a bad map. The other half — a recorded model answer carrying a loop, refused by that same validator — waits for stack 04, because nothing calls a model yet.

**The model proposes; the domain layer disposes.**

The language model never edits the graph. It returns *proposals* — one proposition or one link per call — and code the team wrote checks each proposal against the rules of the graph. A proposal is accepted (and gets a server-minted identifier) or rejected with a reason. Both outcomes are events on the stream, so the user sees the model's misses as well as its hits.

This is why `domain/` is pure: no network, no model, no clock, no randomness except an explicit seed. It is the part of the system whose correctness is *proven by tests* rather than *requested of a model*, and it is the part a reviewer should read first.

Enforced by `test_domain_imports_nothing_impure`, in `backend/tests/unit/test_import_boundary.py`: it reads every file under `domain/` and fails if one of them imports `engine/`, `api/`, `grounding/`, or a model client. It runs in the `backend` check on every pull request, and two further tests in the same file check the checker itself, so a boundary test that has quietly stopped looking cannot pass by accident. The same checker is pointed the other way by `test_the_rules_layer_never_reads_the_examples`, so whether a map is valid can never come to depend on which worked examples we ship.

The disposing half exists too: `validate` in `domain/validity.py` walks a whole map and returns every fault at once, each named in the claim's own words rather than by identifier. `[planned]` The recorded test — the model returns a graph with a loop and the validator rejects it — arrives with stack 04.

---

## 3. The flow of a generation `[planned]`

**Two of the eight steps are real code now; the flow that would call them in this order is not.** Nothing here has ever called a model, no route streams anything, and no receipt is stored. The two that exist are marked in the drawing and named underneath it.

```
 1  user types a hypothesis (+ optional target, + optional own likelihood)      [planned]
 2  api/ opens an event stream to the browser                                   [planned]
 3  engine/ asks the model for ONE proposal at a time                           [planned]
       ├─ system prompt is stable and cached (cheaper repeated calls)
       ├─ the model may call the vendor's web-search tool for evidence
       └─ the answer is a pydantic object (schema-guaranteed JSON)
 4  domain/ validates the proposal → accept (mint id) | reject (reason)         [built]
 5  api/ emits the event; the canvas draws the tile or wire immediately         [planned]
 6  repeat 3–5 until the graph reaches a tradeable terminal or a stop rule      [planned]
 7  domain/ propagates beliefs (seeded), emits per-tile belief events           [built, minus the events]
 8  the generation receipt (model, tokens, cache hits, dollars) is stored       [planned]
```

**Step 4 is built.** `validate` in `domain/validity.py` walks a whole map and returns every fault at once — fourteen stable codes, each with a plain sentence naming the claim or the arrow by its words. It refuses; it never repairs. What is missing is only the thing on the other side of it: nothing produces a *proposal* yet, so today it is called on whole maps rather than on one proposition or link at a time. Minting the identifier of an accepted proposal is built too, in `engine/ids.py`.

**Step 7 is built, minus the event stream.** `propagate` in `domain/propagation.py` turns a map and the values its edits fixed into a world: a likelihood and a range for every claim on the day it is judged, a likelihood for every day of the window, and a named word beside each of those days. It is seeded — the same map, branch and seed give a byte-identical world on any machine — and it runs two nested loops, two thousand versions of the map by eight worlds each (decision record 0014). `domain/diff.py` then compares two worlds. Three routes serve all of it: `POST /api/worlds`, `POST /api/worlds/diff` and `POST /api/worlds/conditional`. They are ordinary requests and answers; there are no per-tile belief events, because there is no event stream.

Measured on the stored Hormuz example, eight claims over a sixty-one-day window: a world takes about **70 ms**, and a difference — two worlds, plus the version-by-version numbers behind each of them worked out again — about **200 ms**.

One proposal per call is deliberate: each is small enough to validate, stream, and retry, and the pipeline — not the model — composes them into a graph. This is the constitution's *minimal output principle* applied.

---

## 4. Data model at a glance `[built]`

Defined once as frozen pydantic models in `domain/`; the same models serve as the model's output schema, the API's response shapes, and the source of the frontend's types (`frontend/src/api/schema.ts`, generated by `scripts/gen-types.sh` and committed). Full definitions live in `spec/graph/` and `spec/multiverse/`; the vocabulary is in `spec/vocabulary.md`.

One row below is still **planned** and says so. The rest exist as code, and the last column names the thing that actually enforces the rule — a function in `domain/validity.py`, a validator that runs when the object is built, or the test that would fail.

| Type | What it is | Key rule, and what enforces it |
|------|-----------|----------|
| `Proposition` | A claim checkable by a date, judged by a named source. Kinds: `hypothesis`, `event`, `market` (names a contract to take a side of, or an instrument that moves), `not_tradeable` (names the reason) | Criteria, judge and resolve-by required (INV-1): `_claims_say_how_they_are_judged`, `test_validate_rejects_unresolvable_proposition`. A `market` claim names a payoff — `ContractPayoff` or `PricePayoff`, told apart by `kind`, neither naming a price — and a `not_tradeable` one a reason (INV-9): `test_validate_requires_payoff_on_market`, `test_validate_requires_reason_on_not_tradeable`. Identity of the trade — venue, contract, instrument — lives in `domain/`; its price lives in `grounding/` (ADR-0013) |
| `Link` | A causal claim from one proposition to another: mechanism, strength (log-odds), lag, signal shape, `trigger` (one-time shove) or `sustain` (continuous hold), provenance, `reflexive`. It carries no self-reported confidence: the rationale is the argument, provenance is the receipt | Rationale required, and a provenance claiming evidence cites a source (INV-2): `_arrows_say_why` and `_arrows_claiming_evidence_cite_it`, `test_validate_rejects_link_without_rationale`, `test_validate_rejects_unsourced_documented_link` |
| `Belief`, `Beliefs` | A likelihood with a range and an owner — model, user, market — in three named slots, never a dictionary | `0 ≤ lo ≤ p ≤ hi ≤ 1` refused at construction and re-checked over a whole map (INV-7): `_likelihoods_sit_inside_their_own_range`. Never averaged across owners (INV-11): `test_beliefs_never_merged`, which reads our own source code rather than trusting good intentions |
| `Graph` | Propositions + links + which claim started it. Immutable | Exactly one hypothesis, at least one terminal, and no loops once reflexive links are set aside — each of which needs a delay (INV-6, INV-9): `_exactly_one_starting_claim`, `_map_ends_somewhere_actionable`, `_no_loops_once_feedback_is_set_aside`, `_feedback_arrows_take_time`. Frozen: `test_models_are_frozen` |
| `Intervention` | Six frozen types — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — told apart by a `kind` field, which is what makes the generated TypeScript a tagged union. **Applying one is built**: `apply` in `domain/patch.py` folds a branch's edits onto a map in order and returns the map they left behind plus every value they fixed | `believe` refuses any belief but the user's own, at construction: `test_believe_requires_user_owner`. The union discriminates on `kind`: `test_intervention_discriminator`. That `do` cuts a claim from its causes and `observe` does not (INV-3) is enforced by `test_do_leaves_ancestors_unchanged` and `test_observe_may_update_ancestors`. An edit that does not fit comes back as a list of violations and never a half-applied branch: `test_apply_rejects_unknown_subject`. `refine` — splitting a claim into finer claims — is refused with a sentence saying it arrives in stack 06, never half-done and never silently dropped |
| `Branch` | A name, an optional parent branch, and an ordered list of interventions. Holds no propositions, links or results | A branch *is* a patch: `test_branch_round_trip`. Replay from (base, branch, seed) (INV-5) arrives with `apply` in stack 03a |
| `World` | A base map with a branch folded onto it and every likelihood worked through: a number and a range for each claim on the day it is judged, a number for every day of the window, a named word beside each of those days (`sampled` · `supposed` · `withdrawn` · `pushed`), every supposition a later edit undermined, and plain sentences for anything the reader should be told. **A computed result, never a source of truth** — it can always be thrown away and rebuilt from the base map, the branch and the seed | Only what is still connected to the edit may change (INV-4): `test_intervention_locality` over two propagated worlds, `GraphEditMachine` over sequences of edits, and `test_a_feedback_arrow_never_carries_a_change` for the rule that the map the engine works through is the map with feedback arrows set aside. Replay from (base, branch, seed) (INV-5, NFR-2): `test_world_replays_from_base_branch_seed` and `test_same_seed_same_world`, which covers both seed streams. Every number between 0 and 1 with its range around it (INV-7): `test_probability_bounds` |
| `Diff` | What moved between two worlds built from one map and one seed: a word per claim — `unchanged`, `shifted`, `added`, `killed` — the endings that moved in ranked order, and one sentence from a fixed template. `SensitivityRow` is the same engine run one flip at a time | A change is read off the **paired** difference, version by version, never off whether two ranges overlap: `test_shifted_needs_agreement`. `killed` means forced false and nothing else: `test_killed_means_forced_false`. The rank has two factors, the size of the move times the weakest arrow on the best-backed route, and range width and agreement are columns beside it: `test_rank_has_two_factors`. Two worlds from different raw material are refused rather than compared: `test_diff_refuses_mismatched_worlds` |
| `Thesis` | **Planned (stack 05).** Legs, entry, invalidation, take-profit, distribution, tails, caveats | No type and no code today. The rule it will carry: the invalidation resolves before its terminal and is publicly observable (INV-14) |

**One worked example, in `fixtures/`.** `fixtures/hormuz.py` holds the Strait of Hormuz map and the branch where Iran is struck the next day, written as commented Python so every number can say where it came from, and checked by `validate` the moment the file loads. It is what stack 03a measures its arithmetic against and what stack 03b draws. `GET /api/fixtures` and `GET /api/fixtures/{id}` serve it read-only. `fixtures/` may read `domain/`; `domain/` must never read `fixtures/`, because a rule about whether a map is valid must not depend on which examples we ship — `test_the_rules_layer_never_reads_the_examples` enforces that, using the same import checker as `test_domain_imports_nothing_impure`.

---

## 5. Where each invariant is enforced `[built]`

Seven of the fourteen invariants are fully checked today, three are partly checked, and four wait for code that does not exist yet — the canvas (stack 03b), the model boundary (04), the thesis (05), refinement (06). Applying an edit and working the likelihoods through, which four of these rows were waiting on, landed in stack 03a. Every test named below is real and runs in `make test`.

| Invariant | Enforced in | Named tests today | Still planned |
|-----------|-------------|-------------------|---------------|
| INV-1 — a claim is checkable: criteria, a named judge, a resolve-by date | `domain/validity.py` | `test_validate_rejects_unresolvable_proposition`, `test_valid_graphs_have_no_violations`, `test_every_resolve_by_date_falls_after_the_day_the_example_is_set_on` | — |
| INV-2 — an arrow says why, and one claiming evidence cites it; every likelihood has an owner | `domain/validity.py`, `domain/belief.py` | `test_validate_rejects_link_without_rationale`, `test_validate_rejects_unsourced_documented_link`, `test_no_arrow_claims_evidence_it_does_not_cite`, `test_owner_matches_slot`, `test_prior_is_owned_by_the_model` | — |
| INV-3 — asserting a claim is not observing it | `domain/intervention.py`, `domain/patch.py`, `domain/propagation.py` | `test_intervention_discriminator`, `test_intervention_rejects_an_unknown_kind` — the six kinds exist and are told apart by `kind`; `test_do_leaves_ancestors_unchanged` — supposing a claim moves nothing that could have caused it; `test_observe_may_update_ancestors` — learning one did reaches back into its causes, because observing keeps only the worlds it happened in | — |
| INV-4 — locality: only what is still connected to the edit may move | `domain/patch.py` (`affected_set`), `domain/propagation.py`, `domain/diff.py` | `test_apply_touches_only_the_affected_set` (the two maps), `test_intervention_locality` (the two worlds — one case per operation, each pinning a claim the edit provably cannot reach), `GraphEditMachine` (locality, the no-loops rule and the 0-to-1 bounds re-checked after every step of a generated sequence of edits), `test_a_feedback_arrow_never_carries_a_change` (a claim reached only through a market feeding back on the world is identical to the byte — the rule that the map the engine works through is the map with feedback arrows set aside), and `test_diff_states_respect_locality` (every claim outside a branch's reach comes out `unchanged`). Each of those works the reach out itself from the shape of the map and never asks the engine what it touched | — |
| INV-5 — the base is never touched; a branch is an ordered patch list; a world replays from (base, branch, seed) | `domain/branch.py`, `domain/graph.py`, `domain/patch.py`, `domain/propagation.py`, `domain/diff.py` | `test_branch_round_trip`, `test_intervention_round_trip`, `test_seeds_are_whole_numbers`, `test_models_are_frozen`, `test_generated_models_are_frozen`; the three laws themselves — `test_apply_empty_is_identity`, `test_patch_concat_equals_sequential_apply`, `test_base_graph_unchanged_after_apply`, `test_child_branch_applies_parent_first`; and replay — `test_same_seed_same_world` (both seed streams, the versions and the dice inside them), `test_world_replays_from_base_branch_seed`, `test_diff_replays_from_base_branches_seed` | — |
| INV-6 — no loops once feedback arrows are set aside, and every feedback arrow takes time | `domain/validity.py` | `test_validate_rejects_cycles`, `test_an_arrow_from_a_claim_to_itself_is_a_loop`, `test_reflexive_links_have_positive_lag`, `test_the_map_has_a_feedback_arrow_and_it_takes_time` | — |
| INV-7 — a likelihood sits inside its own range, and is shown at two significant figures | `domain/belief.py`, `domain/validity.py`, `domain/propagation.py`; later the browser app | `test_belief_bounds_at_construction`, `test_belief_bounds_at_construction_over_raw_fields`, `test_validate_rejects_belief_out_of_range`, `test_every_likelihood_is_a_range_and_never_a_point`, and after any run of edits `test_probability_bounds` and `test_belief_bounds_after_any_sequence` — every computed likelihood and every day of every series lies between 0 and 1 with its range around it | The showing half — a chip never renders more than two significant figures — stack 03b |
| INV-8 — a path drawn on screen shows the product of its arrows | browser app | none | A component test on the path bar. Stack 03b |
| INV-9 — every map ends in something to trade, or says why it cannot | `domain/validity.py` | `test_validate_requires_terminal`, `test_validate_requires_payoff_on_market`, `test_validate_requires_reason_on_not_tradeable`, `test_every_tradeable_ending_names_something_to_trade`, `test_the_ending_that_cannot_be_traded_says_why`, `test_the_two_endings_use_the_two_payoff_shapes` | — |
| INV-10 — splitting a claim into finer claims adds back up | `domain/` propagation | none | A test that the parts recombine to the original within a small tolerance. Stack 06, with `refine` |
| INV-11 — model, user and market likelihoods are never merged | `domain/` | `test_beliefs_never_merged`, which reads our own source code looking for an average taken across two owners, plus its four self-checks — `test_the_checker_catches_two_likelihoods_averaged`, `test_the_checker_catches_a_merge_hidden_in_a_structure`, `test_the_checker_leaves_honest_functions_alone`, `test_the_checker_is_pointed_at_the_real_rules_layer` | The same rule on the browser side, once three chips are drawn side by side. Stack 03b |
| INV-12 — nothing carries meaning in colour alone | browser app | none | Component tests on glyphs, tail textures and the origin mark that carries provenance. Stack 03b |
| INV-13 — the checks run with no model key | the test suite, `.github/workflows/ci.yml` | `test_healthz_is_ok_with_no_environment_variables_set`, `test_readyz_reports_not_ready_when_no_model_key_is_configured`, `test_readyz_treats_an_empty_key_as_no_key`, `test_readyz_reports_ready_when_a_model_key_is_configured`. Beyond the tests: `--record-mode=none` is on by default in `backend/pyproject.toml`, so an unrecorded call fails instead of dialling out, and `make test` unsets both keys before running | The recordings themselves. `backend/tests/cassettes/` is empty; the first one arrives with stack 04 |
| INV-14 — the thing that would prove you wrong resolves in time, and in public | `domain/` thesis derivation | none | Unit tests on the timing and observability filters. Stack 05, with `Thesis` |

More tests belong beside these, though they guard no numbered product invariant. `test_domain_imports_nothing_impure` keeps the rules layer pure, and `test_the_rules_layer_never_reads_the_examples` keeps it independent of the worked examples we ship (§2).

**There are nineteen violation codes now: fourteen faults in a map and five refusals.** The fourteen are what `validate` finds — the last two added on 2026-09-17, a half-life on a push that holds and a spike that never says how fast it fades, which are one idea checked both ways: a shape and the numbers describing it must agree. `test_validate_rejects_half_life_without_impulse` and `test_validate_rejects_impulse_without_half_life` guard them. Four of the five refusals are what folding a branch onto a map finds in an *edit*: `unknown_target`, `unknown_link`, `duplicate_id` and `edit_not_applicable`. The fifth, `worlds_not_comparable`, is the one that is not about an edit at all — two worlds built from different maps, seeds or loop sizes are refused rather than compared, because subtracting one from the other would leave noise rather than the change somebody made. No map can carry any of the five. They are local invariants of the graph and multiverse chapters rather than any of the fourteen, and every one of them is decided by our own code and reported as a plain sentence a person can act on.

Three rules the engine rests on have named tests of their own, each written because a plausible wrong implementation passes everything else and fails exactly one of them. `test_band_is_not_sampling_noise` freezes every prior at a point and demands a range of no width — an engine reporting how much its own sampling wobbled would fail only here. `test_range_matches_analytic_first_order_on_fixture` checks the sampled range against a second, independent method. `test_shifted_needs_agreement` measures two ranges that overlap across half their width while every version of the map moves the same way, which is why a change is read off the paired difference and never off whether two ranges overlap.

---

## 6. Runtime `[built]`

Everything below runs today except stored state, which is marked `[planned]` in its own bullet and has no code, no database file and no volume behind it.

- **Development.** `docker compose watch` (or `make dev`) runs both halves with reload. The browser app answers on <http://localhost:5173> and the Python server on <http://localhost:8000>. Edited files under `backend/src` and `frontend/src` are copied into the running containers, which reload themselves; a change to a file that says *which packages are installed* — `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`, `frontend/package-lock.json` — rebuilds the image instead, because copying a file cannot install a package. The browser app does not start until the server answers its health check.
- **Production-like.** `docker compose -f compose.yaml -f compose.prod.yaml up --build` (or `make prod`), on <http://localhost:8080>. Two multi-stage images. The server is a `python:3.12-slim` image holding only the built virtual environment — no package installer, no lock file, no source tree — run as a user that is not root. The browser app is a folder of built files served by `nginx:alpine`, and that same web server forwards anything beginning with `/api` to the Python server, so the whole app is one origin. The server is not published on the host at all: only the web server can reach it.
- **Versions.** Python 3.12 (`backend/.python-version`, `python:3.12-slim`), packages installed by `uv` 0.12 taken from the image its authors publish, Node 24 (a long-term-support release). The same versions are pinned in the Dockerfiles and in the four checks, so a laptop's newer Node cannot make a pull request pass that a deployment would fail.
- **State.** `[planned]` One SQLite file (a single-file database, no server) on a volume. No database service, no accounts, no multi-tenancy in v1. Nothing is stored yet — the app keeps nothing between requests, and no volume is declared in either compose file.
- **Configuration.** `.env.example` lists every variable; the real `.env` is git-ignored, and `docker compose` reads it from the top of the repository on its own. Values are read once in `settings.py`. Both keys (`ANTHROPIC_API_KEY`, `FRED_API_KEY`) are optional today: the app starts, the first screen loads, and every test passes without either.
- **Health.** `/api/healthz` (the process is up; depends on nothing) and `/api/readyz` (reports whether a model key is configured, never the key). Every browser-facing route lives under `/api/`, so the static-file server forwards one prefix. The container health check calls `/api/healthz` using Python's own `urllib`, because the small images carry neither `curl` nor `wget`.

---

## 7. Testing layers `[built]`

Four of the six rows below exist. Decision record 0008 named four layers and was amended on 2026-09-17 to add the fifth, the worked-example row, which grew out of stack 02. The recorded model boundary and the evaluation set are named here so that adding them is filling a slot rather than inventing one.

| Layer | What it covers | Where | State |
|-------|----------------|-------|-------|
| Pure rules, property-based | Map validity over maps nobody wrote by hand. `backend/tests/strategies.py` builds maps that are correct by construction and maps damaged on exactly one rule; the `hypothesis` library runs each test against hundreds of them and shrinks any failure to the smallest example that still breaks | `backend/tests/unit/domain/` | `[built]` — twenty-one property tests over `validate`. Propagation, interventions and patch algebra arrive with stack 03a |
| Model boundary, recorded | Real vendor answers recorded once, scrubbed of keys, replayed; including malformed and refused answers | `backend/tests/boundary/`, recordings in `backend/tests/cassettes/` | `[planned]` — the directory, the settings that strip keys from a recording (`backend/tests/conftest.py`), and the rule that an unrecorded call fails rather than dials out are all in place; the first recording arrives with stack 04 |
| Routes | Each route answers, and answers the shape it says it does | `backend/tests/api/` | `[built]` — health, about, and the two stored-example routes |
| Worked example | The Strait of Hormuz map and its branch: every rule it must obey, and every shape it is there to exercise | `backend/tests/unit/fixtures/` | `[built]` |
| Browser app | Component tests for the status screen; later the canvas, the reducers and the inspector; one end-to-end smoke test | `frontend/src/**/*.test.tsx` | `[built]` for components; the end-to-end test is `[planned]` |
| Evaluation set | The four assignment examples run live; structural checks (no loops, ends in a trade, every link has a rationale, verify mode never fabricates a bridge) | `evals/` | `[planned]` — arrives with stack 04. `make eval` says so out loud rather than pretending |

`make test` today runs 137 server tests and 3 browser tests, all without a key and without the network. Coverage is measured on the rules layer alone — `backend/src/katalyst/domain/` — and stands at 100% of lines and branches; no other layer has a coverage threshold, on purpose (decision record 0008).

The one test that matters most is still `backend/tests/unit/test_import_boundary.py`. `test_domain_imports_nothing_impure` reads every file under `domain/` — nine of them now — and fails if any imports the engine, the routes, the grounding layer, or a model client. It is the rule "the model proposes; our code decides" made mechanical.

**Runs on every pull request**, in four checks named `backend`, `frontend`, `types-fresh` and `docker` (`.github/workflows/ci.yml`). None of them is given an API key, and none needs one. `types-fresh` regenerates `frontend/src/api/schema.ts` from the server's own description of itself and fails if the result differs from what is committed, which is what stops the two halves drifting apart.

Deliberately skipped in v1: snapshot tests of rendered graphs, load tests, coverage thresholds outside `domain/`, more than one end-to-end test.

---

## 8. Repository layout `[built]`

Python tests live inside `backend/`, next to the project they test, so `pytest` and `uv` run from one root (decided 2026-09-16). Nothing is created before it holds something, so a directory that is still empty is marked below: `grounding/`, `backend/tests/boundary/` and `backend/tests/cassettes/` hold a package marker and nothing else, and `evals/` does not exist at all.

```
katalyst/
├── AGENTS.md  ASSIGNMENT.md  PRODUCT_REQUIREMENTS.md  ARCHITECTURE.md   enduring context
├── README.md            what this is, and how to run it
├── Makefile             every task: dev  up  down  prod  test  lint  types  eval
├── docs/adr/            numbered decision records (a journal)
├── docs/research/       the four research reports that fed the requirements
├── spec/                the spec, organized as a book by idea
├── backend/
│   ├── pyproject.toml  uv.lock  .python-version
│   ├── src/katalyst/   domain/  engine/  grounding/ [planned]  api/  fixtures/  settings.py
│   └── tests/          unit/ (domain/  fixtures/)  api/  boundary/ [planned]
│                       cassettes/ [planned]  conftest.py
│                       strategies.py  the generators the property tests draw maps from
├── frontend/
│   ├── package.json  package-lock.json  vite.config.ts  biome.jsonc
│   └── src/            App.tsx and its test  api/ (client and generated types)
│                       styles/ (design tokens)  test/ (test setup)
├── scripts/
│   └── gen-types.sh    rewrites frontend/src/api/schema.ts from the server
├── docker/             Dockerfile.backend  Dockerfile.frontend  nginx.conf
├── compose.yaml        both halves, with reload, while working
├── compose.prod.yaml   the same two, packaged, laid over the file above
├── .env.example  .dockerignore  .pre-commit-config.yaml  .cz.toml
├── evals/              [planned] saved examples and structural checks; run by hand
└── .github/
    ├── workflows/ci.yml        checks: backend · frontend · types-fresh · docker
    └── pull_request_template.md
```

---

## 9. Decisions this architecture rests on

| Record | Decision | Status |
|--------|----------|--------|
| ADR-0001 | Decision records in a standard markdown template; nothing is built against a `proposed` record | accepted |
| ADR-0002 | Python backend + React/TypeScript frontend; frontend types generated from the API description | accepted |
| ADR-0003 | The domain layer owns graph validity; the model only proposes | accepted |
| ADR-0004 | Branches are patch lists over an immutable base; assert and observe are distinct | accepted |
| ADR-0005 | Typed links (trigger/sustain, log-odds strength, lag, shape) propagated by seeded simulation | accepted |
| ADR-0006 | Vendor SDK, `claude-opus-5`, schema-guaranteed output, one proposal per call, streamed | accepted |
| ADR-0007 | React Flow canvas with automatic layered layout; own the look; no modals | accepted |
| ADR-0008 | Five testing layers (four decided, a worked-example layer added by amendment); recorded responses so CI needs no key | accepted |
| ADR-0009 | Conventional commits; numbered stacks; PR bases chained by agents, stacks assembled in the GitHub UI | accepted |
| ADR-0010 | Polymarket and FRED as grounding sources; Metaculus and yfinance rejected | accepted |
| ADR-0011 | The spec is a book by idea; this file is the living technical counterpart to the PRD | accepted |
| ADR-0012 | Replay mode: with no model key, the four example hypotheses play from committed generation transcripts through the same event stream | accepted |
| ADR-0013 | A payoff names what you would trade — contract or price; what it costs is a live quote | accepted |
| ADR-0014 | A supposition holds until its cause is undermined; the range is how sure we are of the number, computed from two thousand versions of the map | accepted |

---

## 10. Not yet built, and known unknowns

Stacks 00, 01 and 02 are merged, and **stack 03a — the engine — is built**: `apply` folds a branch's edits onto a map and hands back the map they left behind plus every value they fixed; `propagate` works every likelihood through time into a `World`; `diff` says what moved between two worlds and ranks the endings that did; `sensitivity` flips each claim in turn and records what each flip would move; and three routes serve them — `POST /api/worlds`, `POST /api/worlds/diff`, `POST /api/worlds/conditional`. What that leaves, each with the stack that will build it:

- **The canvas.** Tiles, typed ports and wires, automatic layered layout, the ghost diff, the inspector. The browser app today is one status screen reading three routes. Stack 03b.
- **The model pipeline.** `engine/` holds identifier minting and nothing else. No route streams, nothing has ever called a model, and `backend/tests/cassettes/` is empty. Stack 04.
- **Grounding.** `grounding/` is an empty package. There is no Polymarket adapter and no FRED adapter, so a market likelihood on a map today is a number a person wrote down by hand with its source beside it. Stack 05.
- **The thesis.** Legs, entry, invalidation, take-profit, the outcome distribution, tails, caveats, export. The one-at-a-time sweep the derived invalidation reads — flip each claim and see what it does to every ending — is already built and comes back unranked, because which direction hurts depends on the trade. Nothing on screen reads it. Stack 05.
- **Probes.** `refine` — splitting a claim into finer claims, which folding a branch refuses today with a sentence saying so — the simulated outcome distribution, value-of-information ranking, and the propagation of reflexive links, a market feeding back on the world it is measuring, which the engine sets aside rather than working through. The engine already carries `range_shares` — how much of each claim's range comes from not being sure of each prior — and no route reads it. Stack 06.
- **Storage.** Nothing is kept between requests: no database file, no volume in either compose file, no session.

Open technical questions, dated:

- **2026-09-16** Ensemble size for generation — how many independent runs to reconcile into one map, and what a graph then costs. Measure in stack 04.
- **2026-09-17** Replay mode — with no model key, the four example hypotheses play from committed generation transcripts through the live event stream — decided in record 0012, accepted the same day; built in stack 04.

Settled since this list was first written, kept here so the change is visible:

- **Propagation engine** (asked 2026-09-16, settled 2026-09-17, **built in stack 03a**). The question was whether to ship a single deterministic sweep first and add sampling later. Decision record 0014 answered it: the engine is **two nested loops** — two thousand versions of the map, eight worlds under each — because there are two kinds of not-knowing and they must be kept apart. How the dice fall is already inside the likelihood; how sure we are of the numbers put in is the range around it. A single deterministic sweep cannot say the second thing at all, so it was never an option. What shipped is exactly that: sixteen thousand worlds, the likelihood kept rather than the coin flip, and the spread of the eight worlds inside a version subtracted back out so the range is not a report on our own sampling. Measured on the stored Hormuz example — eight claims over a sixty-one-day window — a world takes about **70 ms** and a difference about **200 ms**; a sixty-claim map read on a single day takes about **40 ms**, and over a sixty-one-day window about **470 ms**, because the cost is claims times days times worlds and the window is the term that grows.
- **Reflexive links** (asked 2026-09-16, settled 2026-09-17). Schema in stack 02 — built, and the stored Hormuz example carries one, checked by `test_the_map_has_a_feedback_arrow_and_it_takes_time`. Propagation in stack 06.
- **Stacked pull requests** (asked 2026-09-16, settled 2026-09-17). GitHub's native stacked pull requests work on this repository. `gh pr merge` refuses a stacked pull request and the asynchronous merge route does the job; the verified method is written down under *More Information* in decision record 0009.
