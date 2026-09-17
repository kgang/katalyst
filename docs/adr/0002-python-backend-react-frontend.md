---
# ADR-0002: Python/FastAPI backend with a React/TypeScript frontend, types generated from OpenAPI
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/03-ui-ux-directions.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/05-llm-boundary.md (SDK language), spec/04-canvas.md (frontend toolchain)
---

# ADR-0002: Python/FastAPI backend with a React/TypeScript frontend, types generated from OpenAPI

## Context and Problem Statement

The product is a graph-algorithms and probability-propagation engine wearing an LLM hat, with a canvas UI the owner wants to be exceptional. We need to pick the languages, frameworks, and the mechanism by which the backend's domain types reach the frontend without drift. The repo carries only a Python `.gitignore`; the owner confirmed Python + React/TS in interview (D4). Which concrete toolchain, and how are types shared?

## Decision Drivers

* D4 — owner's choice: Python backend, React/TypeScript frontend
* NFR-3 — the domain layer must be property-tested; the LLM boundary tested with cassettes
* NFR-2 — propagation is pure, seeded, deterministic; needs mature numeric and graph libraries
* NFR-4 — `docker compose up` yields a working app; two images acceptable
* INV-11, INV-7 — belief types are shared across the wire and must not drift between halves
* Solo-developer velocity: two toolchains are acceptable only if each is boring

## Considered Options

* Python (FastAPI, pydantic, uv, networkx, hypothesis) + React/TypeScript (Vite), types via OpenAPI codegen
* All TypeScript (Next.js or Vite + Hono, shared zod schemas)
* Python only, server-rendered UI (HTMX / Streamlit-class)

## Decision Outcome

Chosen option: "Python + React/TypeScript with OpenAPI-generated types", because the defensible core of the product — DAG validation, patch algebra, locality, Monte Carlo — is where `networkx` and `hypothesis`'s shrinking pay off (NFR-2, NFR-3), while the canvas the owner cares about (D3) needs React Flow and a real component model that a server-rendered UI cannot give.

Concrete toolchain (the skeleton stack cites this list):

**Backend** — Python 3.12, `uv` (lockfile committed), FastAPI, pydantic v2 + `pydantic-settings` (env read once in `settings.py`), `networkx`, `numpy`, `anthropic` SDK. Layout: `backend/src/katalyst/{domain,engine,grounding,api}`; `domain/` has no I/O and no LLM imports (ADR-0003). Lint/format `ruff`; `mypy --strict` on `domain/` only (CI, not pre-commit); tests `pytest` + `hypothesis` + `pytest-recording`.

**Frontend** — Vite, React 19, TypeScript strict, `@xyflow/react` (ADR-0007), `biome` for lint + format (one binary; no eslint/prettier), `tsc --noEmit` in CI, `vitest` + Testing Library, one Playwright smoke.

**Type sharing** — FastAPI emits OpenAPI from pydantic; `openapi-typescript` generates `frontend/src/api/schema.ts`; the artifact is committed; a CI job regenerates and fails on diff. One direction, generated, no hand-written mirrors.

**Repo hygiene** — `pre-commit` with `ruff`, `ruff-format`, `biome`, `gitleaks`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`.

### Consequences

* Good, because graph invariants are tested with the best property-testing tool available and read as the rigorous core a reviewer looks for.
* Good, because the frontend has the full React ecosystem for the Workbench (D3) without compromise.
* Good, because generated types make drift a CI failure rather than a runtime surprise.
* Bad, because two toolchains, two lockfiles, two Dockerfiles; mitigated by Compose Watch and a single `compose.yaml`.
* Bad, because propagation cannot run client-side for instant previews without a second implementation; accepted for v1 — the API is fast enough for 60 nodes (NFR-7).
* Neutral, because JS graph libraries are thinner than networkx; irrelevant since the frontend never computes propagation.

### Confirmation

* `backend/` and `frontend/` directories exist with the layout above; `backend/src/katalyst/domain/` imports nothing from `engine/`, `api/`, or `anthropic` (import-linter contract or a grep test in CI).
* CI jobs named `backend`, `frontend`, `types-fresh`, `docker` all green (ADR-0009).
* `frontend/src/api/schema.ts` is committed and `types-fresh` fails on regeneration diff.

## Pros and Cons of the Options

### Python + React/TypeScript, OpenAPI codegen

* Good, because `networkx` (`is_directed_acyclic_graph`, `descendants`, `simple_cycles`) and `hypothesis` (`RuleBasedStateMachine`, shrinking) are exactly the tools INV-4/5/6 need.
* Good, because pydantic models serve triple duty: LLM output schema, API DTO, TS type source (ADR-0006).
* Bad, because two languages means two sets of idioms for one person to keep tasteful.

### All TypeScript

* Good, because one toolchain, one `node_modules`, simplest Docker, shared zod with zero codegen.
* Good, because the Anthropic TS SDK's structured outputs are on par with Python's.
* Bad, because `graphology` is thinner than networkx and `fast-check` shrinks worse than hypothesis on stateful graph tests; the reviewer-facing core would be weaker or hand-rolled.
* Would be chosen if the backend were a thin streaming proxy with trivial logic, or if propagation moved client-side.

### Python only, server-rendered

* Good, because a single language and image.
* Bad, because the Workbench (UX-1 … UX-13) — typed ports, streaming growth, ghost diff, keyboard nav — is not achievable with server-rendered fragments without rebuilding a frontend framework badly. Fails D5-i.

## More Information

* Interview decision D4 (stack), 2026-09-16; D3 (aesthetic) motivates the frontend choice.
* `docs/research/04-engineering-structure.md` §1–§3, §7 — stack comparison, skeleton, Docker, hygiene.
* `docs/research/03-ui-ux-directions.md` §1 — canvas tech verdict (React Flow + ELK).
* networkx DAG algorithms: https://networkx.org/documentation/stable/reference/algorithms/dag.html · hypothesis: https://hypothesis.readthedocs.io/ · openapi-typescript: https://openapi-ts.dev/
