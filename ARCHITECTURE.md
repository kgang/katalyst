# ARCHITECTURE.md — Katalyst

> The technical counterpart to `PRODUCT_REQUIREMENTS.md`. That document says what the tool must do and why; this one says how the system is shaped, where each rule is enforced, and how it runs. It describes the system **as built and as planned**, and each section says which.

**Living document.** Last verified: 2026-09-16. Any pull request that changes a boundary, a layer, a data flow, or a runtime dependency updates this file in the same PR. A stale architecture doc is worse than none: it is the "not knowing why it did that" failure in written form.

**Status markers.** `[planned]` — decided, not yet in the repo. `[built]` — in the repo and covered by the tests named. `[stretch]` — designed for, not scheduled.

---

## 1. The system in one picture `[planned]`

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

Two halves, one contract: the backend publishes an OpenAPI description (a machine-readable list of every route and data shape); the frontend's TypeScript types are generated from it and committed, and continuous integration fails if regeneration would change them. The two halves cannot drift silently.

---

## 2. The one rule that shapes everything `[planned]`

**The model proposes; the domain layer disposes.**

The language model never edits the graph. It returns *proposals* — one proposition or one link per call — and code the team wrote checks each proposal against the rules of the graph. A proposal is accepted (and gets a server-minted identifier) or rejected with a reason. Both outcomes are events on the stream, so the user sees the model's misses as well as its hits.

This is why `domain/` is pure: no network, no model, no clock, no randomness except an explicit seed. It is the part of the system whose correctness is *proven by tests* rather than *requested of a model*, and it is the part a reviewer should read first.

Enforced by: an import-boundary check in continuous integration (`domain/` may not import `engine/`, `api/`, `grounding/`, or the vendor SDK), and a recorded test in which the model returns a graph with a loop and the validator rejects it.

---

## 3. The flow of a generation `[planned]`

```
 1  user types a hypothesis (+ optional target, + optional own likelihood)
 2  api/ opens an event stream to the browser
 3  engine/ asks the model for ONE proposal at a time
       ├─ system prompt is stable and cached (cheaper repeated calls)
       ├─ the model may call the vendor's web-search tool for evidence
       └─ the answer is a pydantic object (schema-guaranteed JSON)
 4  domain/ validates the proposal → accept (mint id) | reject (reason)
 5  api/ emits the event; the canvas draws the tile or wire immediately
 6  repeat 3–5 until the graph reaches a tradeable terminal or a stop rule
 7  domain/ propagates beliefs (seeded), emits per-tile belief events
 8  the generation receipt (model, tokens, cache hits, dollars) is stored
```

One proposal per call is deliberate: each is small enough to validate, stream, and retry, and the pipeline — not the model — composes them into a graph. This is the constitution's *minimal output principle* applied.

---

## 4. Data model at a glance `[planned]`

Defined once as pydantic models in `domain/`; the same models serve as the model's output schema, the API's request/response shapes, and the source of the frontend's types. Full definitions live in `spec/graph/` and `spec/multiverse/`; the vocabulary is in `spec/vocabulary.md`.

| Type | What it is | Key rule |
|------|-----------|----------|
| `Proposition` | A claim checkable by a date, judged by a named source | Must carry criteria, source, resolve-by (INV-1) |
| `Link` | A causal claim from one proposition to another: mechanism, strength (log-odds), lag, signal shape, `trigger` (one-time shove) or `sustain` (continuous hold), provenance | Must carry a rationale and a provenance; evidence-claiming links carry sources (INV-2) |
| `Belief` | A likelihood with a range and an owner: model, user, or market | Never averaged across owners (INV-11) |
| `Graph` | Propositions + links; no loops except delayed reflexive links | Immutable once created (INV-5, INV-6) |
| `Intervention` | One of `do`, `observe`, `insert`, `retune`, `refine`, `believe` | `do` cuts a proposition from its causes; `observe` does not (INV-3) |
| `Branch` | An ordered list of interventions over a base graph | A branch is a patch; worlds replay from (base, branch, seed) (INV-5) |
| `World` | A base graph with a branch applied and beliefs propagated | Only downstream of an intervention changes (INV-4) |
| `Thesis` | Legs, entry, invalidation, take-profit, distribution, tails, caveats | The invalidation resolves before its terminal and is observable (INV-14) |

---

## 5. Where each invariant is enforced `[planned]`

| Invariant | Layer | How it is checked |
|-----------|-------|-------------------|
| INV-1, 2, 6, 9 (a proposition is checkable; a link says why; no loops; ends in a trade) | `domain/` validation | Property tests over generated graphs; the recorded-loop rejection test |
| INV-3, 4, 5, 10 (assert vs observe; locality; branches are patches; refinement adds up) | `domain/` interventions and propagation | Property tests: identity, concatenation, locality, round-trip, marginalization; a state-machine test over random intervention sequences |
| INV-7 (beliefs stay in range; two significant figures) | `domain/` + frontend chips | Property test on bounds; a rendering test that a chip never shows more than two significant figures |
| INV-8, 12 (path product shown; no meaning in hue alone) | frontend | Component tests on the path bar and the encoding tokens; a review checklist |
| INV-11 (owners never merged) | `domain/` + frontend | A test that no function returns one number derived from two owners |
| INV-13 (CI needs no API key) | test suite | Recorded responses replayed with recording disabled in CI |
| INV-14 (invalidation is observable in time) | `domain/` thesis derivation | Unit tests on the timing and observability filters |

---

## 6. Runtime `[planned]`

- **Development.** `docker compose watch` runs both halves with hot reload: source changes sync into the containers; dependency-file changes rebuild. The frontend waits on the backend's health check.
- **Production-ish.** Two multi-stage images: a slim Python image containing only the built virtual environment, and a static-file image serving the built frontend with `/api` proxied to the backend on the same origin (no cross-origin configuration to explain).
- **State.** One SQLite file (a single-file database, no server) on a volume. No database service, no accounts, no multi-tenancy in v1.
- **Configuration.** `.env.example` lists every variable; the real `.env` is git-ignored; values are read once in `settings.py` and the process fails fast with a clear message if a required key is missing.
- **Health.** `/healthz` (process is up) and `/readyz` (a model key is configured).

---

## 7. Testing layers `[planned]`

| Layer | What it covers | Runs in CI? |
|-------|----------------|-------------|
| Pure domain, property-based | Graph rules, propagation, interventions, patch algebra — thousands of generated cases, failures shrunk to a minimal example | Yes, milliseconds |
| Model boundary, recorded | Real vendor responses recorded once, scrubbed of keys, replayed; includes malformed and refused responses | Yes, no key needed |
| Evaluation set | The four assignment examples run live; structural checks (no loops, ends in a trade, every link has a rationale, verify mode never fabricates a bridge) | No — manual, costs money |
| Frontend | Component tests for reducers and the inspector; one end-to-end smoke: type → graph → intervene → downstream changes, upstream does not | Yes |

Deliberately skipped in v1: snapshot tests of rendered graphs, load tests, coverage thresholds outside `domain/`, more than one end-to-end test.

---

## 8. Repository layout `[planned]`

```
katalyst/
├── AGENTS.md  ASSIGNMENT.md  PRODUCT_REQUIREMENTS.md  ARCHITECTURE.md   enduring context
├── docs/adr/            numbered decision records (a journal)
├── docs/research/       the four research reports that fed the PRD
├── spec/                the spec, organized as a book by idea
├── backend/
│   ├── pyproject.toml  uv.lock
│   └── src/katalyst/   domain/  engine/  grounding/  api/  settings.py
├── frontend/
│   └── src/            api/ (generated types)  graph/  features/  components/
├── tests/              unit/ (domain)  boundary/ (recorded)  api/  cassettes/
├── evals/              golden inputs and structural assertions; run by hand
├── docker/             Dockerfile.backend  Dockerfile.frontend  nginx.conf
├── scripts/            gen-types  record-cassettes  eval
├── compose.yaml  compose.prod.yaml  .env.example
└── .github/workflows/ci.yml     jobs: backend · frontend · types-fresh · docker
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
| ADR-0008 | Four testing layers; recorded responses so CI needs no key | accepted |
| ADR-0009 | Conventional commits; numbered stacks; PR bases chained by agents, stacks assembled in the GitHub UI | accepted |
| ADR-0010 | Polymarket and FRED as grounding sources; Metaculus and yfinance rejected | accepted |
| ADR-0011 | The spec is a book by idea; this file is the living technical counterpart to the PRD | accepted |

---

## 10. Not yet built, and known unknowns

Nothing under `backend/` or `frontend/` exists yet; stack 01 creates the skeleton. Open technical questions, dated:

- **2026-09-16** Reflexive links (market → world, delayed): schema in stack 02, propagation deferred to stack 06.
- **2026-09-16** Propagation engine: a deterministic topological sweep first, or seeded simulation from the start? ADR-0005 names the three conditions that force simulation.
- **2026-09-16** Ensemble size for generation (how many independent runs to reconcile) and its cost per graph. Measure in stack 04.
- **2026-09-16** Whether the GitHub web UI's stacked-PR view is enough at three PRs deep, or `git-spice` is needed.
