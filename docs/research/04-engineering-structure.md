# Engineering Structure Report — Catalyst Causal-Graph Prototype

*Research only. No files written. ~2,400 words.*

---

## 1. Stack recommendation: **(A) Python backend + React/TS frontend**

| Axis | (A) FastAPI + uv + pydantic / Vite+React | (B) All-TypeScript |
|---|---|---|
| **LLM SDK + structured output** | `client.messages.parse(..., output_format=CausalGraph)` returns a validated pydantic instance in `.parsed_output`. Your domain model *is* your LLM schema — zero duplication. | `client.messages.parse({..., output_config: {format: zodOutputFormat(Schema)}})`. Equally good ergonomically; zod→JSON-Schema is the same trick. **Tie.** |
| **Numerics / graph algos** | `networkx` for free: `is_directed_acyclic_graph`, `topological_sort`, `descendants`, `ancestors`, `simple_cycles`, `condensation`. `numpy` for Monte Carlo. stdlib `graphlib.TopologicalSorter` if you want zero deps. | `graphology` + its standard library is the only serious option and is thinner than networkx; DAG-specific coverage is not at parity. Monte Carlo in JS is hand-rolled. **A wins decisively.** |
| **Testing** | pytest + `hypothesis` (the reference property-based testing implementation) + `pytest-recording`/vcrpy for cassettes. | vitest + `fast-check` + `msw` or nock. Good, but hypothesis's shrinking and stateful testing are better for graph invariants. **A wins.** |
| **Docker** | Two images, two Dockerfiles. uv makes the Python image fast and small (multi-stage + `--frozen` + bytecode compile). | One runtime if you go Next.js — genuinely simpler. **B wins.** |
| **Type sharing** | FastAPI emits OpenAPI from pydantic for free → `openapi-typescript openapi.json -o src/api/schema.ts`, commit the output, CI fails if regeneration produces a diff. One-way, generated, no drift. | Shared zod package in a monorepo — no codegen step at all. **B wins slightly**, but A's generated path is ~30 min of setup and is a *feature* you can point at in an ADR. |
| **Solo dev velocity** | Two toolchains, two lockfiles, but each is boring. | One toolchain, one `node_modules`. |

**Recommendation: (A).** The decisive factor is that this product is a *graph-algorithms + probability propagation* app wearing an LLM hat. The interesting, testable, defensible core — DAG validation, topological re-propagation, intervention algebra, Monte Carlo over branch probabilities — is exactly where Python's library depth and hypothesis's shrinking pay off, and exactly what a reviewer will read. Writing `simple_cycles` by hand in TypeScript is not a good use of take-home hours.

**When I'd pick (B):** if the product were mostly a streaming UI over a thin LLM call with trivial backend logic; if you needed to ship to Vercel in one deploy; or if you were materially faster in TS than Python (velocity beats theoretical fit on a 1–2 week clock). B also gets genuinely simpler if the propagation runs client-side.

Sources: [networkx](https://networkx.org/documentation/stable/reference/algorithms/dag.html) · [graphology](https://github.com/graphology/graphology) · [openapi-typescript](https://openapi-ts.dev/) · [hypothesis](https://hypothesis.readthedocs.io/)

---

## 2. Repo skeleton

Backend/frontend split, not a monorepo tool. `pnpm`/`turbo` earn nothing here.

```
katalyst/
├── AGENTS.md ASSIGNMENT.md PRODUCT_REQUIREMENTS.md README.md   # enduring context (per your rules)
├── docs/adr/            # numbered ADRs, higher supersedes lower
├── spec/                # feature specs w/ INVARIANTS + ANTI-PATTERNS
│   └── diagrams/        # mermaid sources, rendered in-line in specs
├── backend/
│   ├── pyproject.toml uv.lock
│   └── src/katalyst/
│       ├── domain/      # PURE: graph model, propagation, interventions. No I/O, no LLM.
│       ├── engine/      # LLM boundary: prompts, schemas, expansion orchestration
│       ├── grounding/   # external data adapters (FRED, Polymarket, Kalshi) behind a Protocol
│       ├── api/         # FastAPI routers, DTOs, SSE streaming
│       └── settings.py  # pydantic-settings; the only place env vars are read
├── frontend/
│   ├── package.json vite.config.ts
│   └── src/
│       ├── api/         # generated OpenAPI types + thin fetch client (schema.ts is generated)
│       ├── graph/       # React Flow canvas, layout, node/edge renderers
│       ├── features/    # thesis builder, intervention panel, multiverse diff
│       └── components/  # dumb presentational components
├── tests/               # backend tests: unit/ (pure domain), boundary/ (cassettes), api/
│   └── cassettes/       # committed VCR recordings, secrets scrubbed
├── evals/               # golden inputs (the 4 assignment events) + structural assertions
├── docker/              # Dockerfile.backend, Dockerfile.frontend, nginx.conf
├── scripts/             # gen-types.sh, record-cassettes.sh, eval.sh
├── compose.yaml  compose.prod.yaml  .env.example
└── .github/workflows/ci.yml
```

The `domain/` ↔ `engine/` split is the single most legible design decision you can make: it says "the LLM is a *source of proposals*; the graph's correctness is enforced by code I wrote and property-tested." Make that ADR-001 territory.

---

## 3. Docker

**Dev (`compose.yaml`)** — use Compose Watch rather than bind-mount spaghetti. It's GA since v2.22/2.23 and expresses intent per-file-class:

```yaml
services:
  backend:
    build: {context: ./backend, dockerfile: ../docker/Dockerfile.backend, target: dev}
    command: uv run uvicorn katalyst.api.main:app --host 0.0.0.0 --reload
    environment: [ANTHROPIC_API_KEY, FRED_API_KEY]   # pass-through from host/.env
    ports: ["8000:8000"]
    develop:
      watch:
        - {path: ./backend/src, action: sync, target: /app/src}
        - {path: ./backend/pyproject.toml, action: rebuild}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')"]
      interval: 10s, timeout: 3s, retries: 5, start_period: 10s
  frontend:
    build: {context: ./frontend, target: dev}
    command: npm run dev -- --host
    depends_on: {backend: {condition: service_healthy}}
    develop:
      watch:
        - {path: ./frontend/src, action: sync, target: /app/src}
        - {path: ./frontend/package.json, action: rebuild}
```

Run `docker compose watch`. ([Compose Watch docs](https://docs.docker.com/compose/how-tos/file-watch/))

**Prod-ish (`compose.prod.yaml`)** — two multi-stage Dockerfiles, same files, different targets:
- Backend: `ghcr.io/astral-sh/uv` builder → `uv sync --frozen --no-dev --compile-bytecode` into `/app/.venv` → copy only the venv into `python:3.13-slim`, non-root user, no uv in the runtime. ([uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/))
- Frontend: `npm ci && npm run build` → copy `dist/` into `nginx:alpine` with an `/api` proxy_pass to the backend. One origin, no CORS config to explain.

**Keeping it simple (solo-dev rules):**
- **No database in v1.** Sessions live in memory or a single SQLite file on a volume. A Postgres service is three more failure modes and zero take-home credit.
- Two compose files, not five. `docker compose -f compose.yaml -f compose.prod.yaml` is already one too many layers.
- Healthchecks only on the backend; `depends_on: service_healthy` on the frontend. Add `/healthz` (liveness, no deps) and `/readyz` (checks an Anthropic key is present) — it makes the compose file self-documenting.

**.env handling:** commit `.env.example` with every key listed and empty values; `.gitignore` the real `.env`. Compose auto-loads `.env` from the project root. In the service, use `environment: [ANTHROPIC_API_KEY]` (bare-name pass-through) rather than `env_file` so you can see at a glance which service needs which secret. Read it exactly once, via `pydantic-settings`, and fail fast at startup with a clear message. Add `gitleaks` or `detect-secrets` to pre-commit — cheap, and it's what stops a cassette leaking a key.

---

## 4. Testing strategy

**Layer 1 — pure domain, property-based (the layer that wins you the take-home).** All of `domain/` has no network and no LLM, so it runs in milliseconds. Use `hypothesis` with a `@composite` strategy that generates arbitrary causal graphs. Invariants worth asserting:
- `add_node` / `add_edge` never creates a cycle (rejected, not silently accepted).
- Propagation is **idempotent**: `propagate(propagate(g)) == propagate(g)`.
- Propagation is **order-independent**: shuffling the topological tie-breaks yields identical node probabilities.
- Every node probability stays in `[0, 1]` after any sequence of interventions.
- **Patch algebra**: `apply(apply(g, p1), p2) == apply(g, compose(p1, p2))`; `apply(g, identity) == g`; `revert(apply(g, p), p) == g`. This is the "multiverse" correctness story in one test.
- **Locality**: an intervention on node `n` changes only `descendants(n) ∪ {n}` — assert that every non-descendant is byte-identical. This is the single most valuable test in the repo; it's the whole product claim.
- Hypothesis `RuleBasedStateMachine` for a sequence of random user edits, checking DAG-ness + bounds after every step.

**Layer 2 — LLM boundary, cassettes.** `pytest-recording` (vcrpy) with `@pytest.mark.vcr`, `record_mode=none` in CI, `filter_headers=["x-api-key", "authorization"]` in `vcr_config`. Commit cassettes under `tests/cassettes/`. CI then runs green with no `ANTHROPIC_API_KEY` at all — call that out in the README, it reads as senior. A `scripts/record-cassettes.sh` with `--record-mode=rewrite` is the re-record path. ([pytest-recording](https://github.com/kiwicom/pytest-recording) · [Simon Willison's TIL](https://til.simonwillison.net/pytest/pytest-recording-vcr))

Also test the *parse failure* path: a cassette where the model returns a graph with a cycle, asserting your validator rejects it rather than the UI rendering nonsense. Structured outputs (`output_config.format` / `output_format=`) guarantee schema-valid JSON, **not** semantically valid graphs — that gap is your domain layer's reason to exist.

**Layer 3 — eval harness (small, ~150 lines).** `evals/cases/*.yaml` with the four assignment events as golden inputs. Run live against `claude-opus-5`, assert *structural* properties, never exact text:
- output is a DAG, ≥N nodes, ≤M depth, terminates in ≥1 node tagged `financial_effect`
- every probability in `[0,1]`; every edge carries a non-empty `mechanism` rationale
- every leaf node has ≥1 citation/grounding reference
- a "does A lead to B?" case returns a path or an explicit `no_path` verdict, not a fabricated chain

Emit a scorecard TSV, keep results in `evals/runs/`. Gate it behind `make eval` — **not** CI (costs money, non-deterministic). Mention in the README that it's the regression harness for prompt changes.

**Layer 4 — frontend.** vitest + `@testing-library/react` for the intervention panel and the node editor reducer only. One Playwright smoke: type event → graph renders → edit a node → downstream nodes change, upstream don't.

**SKIP for a prototype:** LLM-as-judge grading of narrative quality; snapshot tests of graph SVGs; contract tests; load/perf tests; mutation testing; >1 e2e; mocking FastAPI's own routing; coverage thresholds. Aim for ~85% coverage of `domain/`, and be explicit in the README that `api/` and `engine/` are deliberately thin and lightly tested.

---

## 5. ADRs

**Use MADR 4.x**, not Nygard. Nygard's four sections are fine but MADR's *Decision Drivers* and *Pros and Cons of the Options* are precisely the "rigorously documented" quality you're after, and it's the de-facto standard with a maintained spec. Latest is 4.0.0 (2024-09-17). Template sections: front-matter (`status`, `date`, `decision-makers`, `consulted`, `informed`) then **Context and Problem Statement · Decision Drivers · Considered Options · Decision Outcome · Consequences · Confirmation · Pros and Cons of the Options · More Information**. ([MADR](https://adr.github.io/madr/) · [repo](https://github.com/adr/madr))

Add two project-local sections to the template: **Supersedes / Superseded by** (your higher-number rule made explicit and greppable) and **Spec impact** (which `./spec` doc this decision changes).

**Tooling: none.** Copy `adr-template.md` to `docs/adr/0001-*.md` by hand, plus a `docs/adr/README.md` index table. `adr-tools` is an unmaintained shell wrapper around `cp`; log4brains gives you a static site you do not need and a Node dependency in a Python repo. Skipping tooling is itself a defensible ADR.

**First eight ADRs:**

| # | Title | Gist |
|---|---|---|
| 0001 | Record architecture decisions in MADR 4.x format | Establishes the process; supersession by number; no tooling. |
| 0002 | Python/FastAPI backend with a React/TypeScript frontend | The stack decision above, with all-TS as the rejected alternative. |
| 0003 | The causal graph is a validated DAG owned by the domain layer, not the LLM | LLM proposes, typed domain code disposes; cycles rejected at the boundary. |
| 0004 | Elicit graph structure via Anthropic structured outputs (`messages.parse` + pydantic) | One pydantic model serves as LLM schema, API DTO, and TS type source; alternatives were tool-use and free-text+regex. |
| 0005 | Interventions are immutable patches over a base graph; branches are patch chains | Defines the multiverse data model and makes re-propagation locality provable. |
| 0006 | Propagate probabilities by topological sweep (v1), with Monte Carlo deferred | Names the simplification and the exact condition that would force the upgrade. |
| 0007 | Generate frontend types from the FastAPI OpenAPI schema; commit the artifact | `openapi-typescript`; CI fails on a regeneration diff; alternative was hand-written interfaces. |
| 0008 | Test the LLM boundary with committed VCR cassettes; evals run out-of-band | CI needs no API key; evals are a manual, costed gate. |

Likely 0009–0010 as you go: SSE vs WebSocket for streaming node-by-node graph expansion; in-memory/SQLite session persistence.

---

## 6. Spec-driven development

The honest framing: SDD in 2026 means **the spec is the version-controlled source of truth an agent implements from**, not prose you write after. [GitHub Spec Kit](https://github.com/github/spec-kit) is the reference toolkit (`/speckit.specify → .plan → .tasks → .implement`); you don't need to adopt the tool, but steal its discipline — and its *constitution* idea maps directly onto your AGENTS.md. Good background: [Microsoft's SDD walkthrough](https://developer.microsoft.com/blog/spec-driven-development-spec-kit/) · [Spec Kit docs](https://github.github.com/spec-kit/).

**`spec/branching-interventions.md` shape:**

1. **Purpose** — one paragraph; what a user can do that they couldn't before.
2. **Vocabulary** — `Graph`, `Node`, `Edge`, `Intervention`, `Patch`, `Branch`, `Baseline`, `Multiverse`. Define each once; every other doc and identifier uses these words exactly.
3. **Data model** — the pydantic models verbatim, plus a mermaid ER/class diagram.
4. **Behaviour** — numbered user-visible flows (`B1: user pins a node's probability to 1.0 → …`), each with a worked example using a real assignment event.
5. **INVARIANTS** — numbered, each written as a *checkable predicate over generated inputs*, with the property test named:
   - `INV-1` For all graphs `g` and interventions `i`: `apply(g, i)` is acyclic. → `test_apply_preserves_dag`
   - `INV-2` For all `g, i` on node `n`: `∀ m ∉ descendants(g, n) ∪ {n}`, `apply(g,i)[m] == g[m]`. → `test_intervention_locality`
   - `INV-3` `revert(apply(g, i), i) == g` for all `g, i`. → `test_patch_roundtrip`
   - `INV-4` For all `g`: `∀ n, 0.0 ≤ g[n].probability ≤ 1.0`. → `test_probability_bounds`
   - `INV-5` Branch order-independence: `apply(apply(g,i₁),i₂) == apply(apply(g,i₂),i₁)` when `i₁,i₂` touch disjoint subtrees.
   The phrasing rule: **"for all X, P(X)"** with X drawn from a hypothesis strategy you actually have. If you can't name the strategy, it isn't an invariant — it's a wish, and it belongs in Behaviour.
6. **ANTI-PATTERNS** — phrased as *"Do not X, because Y; do Z instead"*, each traceable to a real temptation:
   - "Do not mutate the baseline graph in place when branching — branch comparison needs both versions live. Return a new graph."
   - "Do not re-prompt the LLM for the whole graph after an edit — it breaks auditability and locality (INV-2). Re-prompt only the affected subtree."
   - "Do not let the LLM assign node IDs — it will collide across branches. IDs are minted server-side."
   - "Do not store probabilities as display strings. Store floats; format at the edge."
7. **Open questions** — dated, so the doc visibly ages.

Cross-link: every INVARIANT cites its ADR, and every ADR's *Spec impact* cites back.

---

## 7. Git hygiene for solo + agents

- **Conventional Commits 1.0.0** ([spec](https://www.conventionalcommits.org/en/v1.0.0/)). Types: `feat, fix, refactor, test, docs, chore, spec, adr`. Adding `spec:` and `adr:` makes `git log --oneline --grep '^adr'` a decision timeline. Enforce with `commitizen` (Python-native, plays well with uv) or a `commit-msg` hook; skip `semantic-release` — no versioning needed.
- **PR stacks: use `git-spice`.** Single Go binary, stays on plain git branches, tokens in the OS keychain, works with normal GitHub URLs. Graphite is $20–40/user/month and pulls in Node. ([git-spice](https://abhinav.github.io/git-spice/) · [comparison](https://www.knusbaum.org/posts/graphite-vs-git-spice)) **Check GitHub's native stacked PRs first** — public preview since 2026-07-30 and built into the normal PR workflow; if it works on your repo, it's zero tooling and a better story. ([changelog](https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/) · [docs](https://docs.github.com/en/pull-requests/get-started/about-stacked-prs)) Don't use `jj` or `git-branchless` on a take-home — both are excellent and both cost reviewer comprehension.
- **Branch naming:** `<type>/<NN>-<slug>` where `NN` matches the spec or ADR number: `spec/03-branching`, `feat/03-intervention-patches`, `feat/03-propagation-locality`. A stack's branches share the number, so `git branch --list '*03*'` is the stack.
- **Stack workflow:** one stack per spec document. Bottom branch = the spec + ADR (docs only, merges instantly). Then domain types → pure algorithms + property tests → API surface → UI. Each PR body: *what*, *which INVARIANT it satisfies*, *what's deliberately not here*. `gs stack submit` after each rebase. Never exceed ~4 PRs deep.
- **CI (`.github/workflows/ci.yml`)** — one workflow, four jobs, ~4 minutes, no API key:
  1. `backend`: `uv sync --frozen` → `ruff check` + `ruff format --check` → type check → `pytest` (cassettes, `--record-mode=none`)
  2. `frontend`: `npm ci` → `biome ci` → `tsc --noEmit` → `vitest run`
  3. `types-fresh`: regenerate `schema.ts` from the app's OpenAPI and `git diff --exit-code`
  4. `docker`: `docker build` both images (buildx cache), no push
- **pre-commit** ([pre-commit.com](https://pre-commit.com/)): `ruff` + `ruff-format`, `biome` (one binary replaces eslint+prettier — worth it solo), `gitleaks`, plus the stock `end-of-file-fixer` / `check-yaml` / `check-added-large-files`. **Type checking:** use `mypy --strict` on `src/katalyst/domain` only, in CI not pre-commit (too slow for a hook). Astral's `ty` is fast but still beta as of 2026 and not a drop-in — [pyrefly](https://pyrefly.org/) is the more conformant fast option if mypy's speed annoys you. On the frontend, `tsc --noEmit` in CI; Biome doesn't type-check. ([ty status](https://astral.sh/blog/ty))

---

## 8. Data sources for grounding

Verdicts from primary docs (Sept 2026):

| Source | Auth | Limits | v1? |
|---|---|---|---|
| **FRED** | Free key, instant, query param | ~120 req/min *(widely cited but **not** in official docs — treat as folklore)* | **Yes, first.** ALFRED vintage data lets you show what was knowable *at the time* — a real differentiator. Must display the attribution line: *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* |
| **Polymarket Gamma** | **None** | 4,000/10s general; `/events` 500/10s; `/markets` 300/10s. Over-limit is throttled, not 429'd | **Yes.** Geo-gate applies only to CLOB order placement, not reads. |
| **Kalshi v2** | **None for public market-data GETs** (RSA-PSS only for account/orders/WebSocket) | Authenticated: Basic tier 200 read / 100 write tokens per sec. *Unauthenticated read throttling is undocumented* | **Yes, read-only.** Skip RSA entirely. Strong on Fed/CPI markets — pairs naturally with FRED. |
| **Metaculus** | Token required; **all** endpoints now authenticated | ~1,000/hr (third-party reported) | **No.** As of 2026-03-09 Community Prediction aggregates were removed from general API access — the one thing you wanted. ([announcement](https://www.metaculus.com/notebooks/42554/changes-to-the-metaculus-api/)) |
| **yfinance** | None (scrapes; no official API since 2017) | Undocumented, adversarial; 429s and silent empties | **Offline backfill only.** ToS gray area. Never on the demo path; cache to Parquet. |

**Better equity option:** **Finnhub** — free tier is 60 calls/minute, a real documented contract, unlike yfinance. Alpha Vantage's free tier is now ~25 req/**day** and is unusable.

**Prediction-market consensus** must now be *constructed*: query Polymarket + Kalshi directly and surface cross-venue disagreement as a signal ("the two venues price this differently — here's the mechanism"). That's a better product beat than a single fetched consensus number.

**Is it worth it in v1?** Yes, but narrowly: **two adapters — FRED + Polymarket** — behind a `GroundingSource` Protocol, with responses cached to disk. Their value is that every leaf node can cite a real number, which turns "auditable" from a claim into a link. Add Kalshi third if time allows. Then write a short *Sources considered and rejected* section covering Metaculus's March 2026 lockdown and yfinance's ToS profile — that analysis reads better than a fourth integration.

**Uncertainty flags:** FRED's 120/min and Metaculus's 1,000/hr are not in official docs; Kalshi's unauthenticated read throttle is undocumented; GitHub's native stacked PRs are still public preview, so verify on your repo before committing to them over git-spice.
