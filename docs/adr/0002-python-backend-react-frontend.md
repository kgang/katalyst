---
# ADR-0002: Python/FastAPI backend with a React/TypeScript frontend, types generated from OpenAPI
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/03-ui-ux-directions.md
informed: all agents working in this repo
supersedes: none
superseded-by: none
spec-impact: spec/generation/ (SDK language), spec/workbench/ (frontend toolchain)
---

# ADR-0002: Python/FastAPI backend with a React/TypeScript frontend, types generated from OpenAPI

## Context and Problem Statement

The product is a graph-and-probability engine wearing a language-model hat, with a canvas the owner wants to be exceptional. We must pick the languages, the frameworks, and the mechanism by which the backend's data shapes reach the frontend without the two drifting apart. The repo carries only a Python ignore file; the owner settled on Python plus React/TypeScript in interview (D4). Which concrete toolchain, and how are types shared?

## Decision Drivers

* D4 (owner's choice of stack): Python backend, React/TypeScript frontend
* NFR-3 (tests) — the core graph code is property-tested; the model boundary runs on recorded responses
* NFR-2 (determinism) — propagation is pure and seeded; needs mature numeric and graph libraries
* NFR-4 (one command starts the app) — two container images are acceptable
* INV-11, INV-7 (beliefs stay separate and stay in bounds) — belief types cross the wire and must not drift between the two halves
* Solo-developer velocity: two toolchains are acceptable only if each is boring

## Considered Options

* Python + React/TypeScript, types generated from the backend's own API description
* All TypeScript (Next.js, or Vite plus Hono) with schemas shared directly
* Python only, with the page rendered on the server (HTMX or Streamlit class of tool)

## Decision Outcome

Chosen option: "Python + React/TypeScript with generated types", because the defensible core of the product — checking the graph has no loops, composing patches, keeping changes local, running thousands of random simulations — is where Python's `networkx` (graph algorithms) and `hypothesis` (property-based testing: it generates thousands of random inputs and shrinks any failure to a minimal example) pay off (NFR-2, NFR-3), while the canvas the owner cares about (D3, the *Workbench* look) needs React and a real component model that server-rendered pages cannot give.

Concrete toolchain (the skeleton stack cites this list):

**Backend** — Python 3.12; `uv` for packages, with the lockfile committed; FastAPI (a web framework that publishes a machine-readable description of its own endpoints and data shapes, in the OpenAPI format); pydantic v2, the library that defines and validates our data shapes, with `pydantic-settings` reading environment variables once in `settings.py`; `networkx`; `numpy`; the `anthropic` SDK. Layout: `backend/src/katalyst/{domain,engine,grounding,api}`, where `domain/` does no input or output and imports nothing model-related (ADR-0003). Lint and format with `ruff`; strict type checking on `domain/` only, in the shared build, not on commit; tests with `pytest`, `hypothesis`, and `pytest-recording` for cassettes (recorded API responses replayed in tests).

**Frontend** — Vite (build tool and dev server), React 19, TypeScript in strict mode, `@xyflow/react` for the canvas (ADR-0007), `biome` for lint and format (one binary, no second formatter), a type-check pass in the shared build, `vitest` plus Testing Library, and one end-to-end browser test with Playwright.

**Type sharing** — FastAPI emits the OpenAPI description from the pydantic models; `openapi-typescript` turns it into `frontend/src/api/schema.ts`; that file is committed, and a build job regenerates it and fails if the result differs. One direction, generated, no hand-written mirrors.

**Repo hygiene** — `pre-commit` hooks running `ruff`, `ruff-format`, `biome`, `gitleaks` (a secret scanner), end-of-file and YAML checks, and a large-file guard.

### Consequences

* Good, because graph invariants are tested with the strongest property-testing tool available, and read as the rigorous core a reviewer looks for.
* Good, because the frontend has the full React ecosystem for the Workbench (D3) without compromise.
* Good, because drift between the two halves becomes a build failure rather than a runtime surprise.
* Bad, because two toolchains, two lockfiles, two container images; mitigated by file-watching rebuilds and a single `compose.yaml`.
* Bad, because propagation cannot run in the browser for instant previews without a second implementation; accepted for v1 — the API is fast enough for 60 nodes (NFR-7).
* Neutral, because JavaScript graph libraries are thinner; irrelevant, since the frontend never computes propagation.

### Confirmation

* `backend/` and `frontend/` exist with the layout above; `backend/src/katalyst/domain/` imports nothing from `engine/`, `api/`, or `anthropic` (an import-rule contract or a grep test in the build).
* Build jobs named `backend`, `frontend`, `types-fresh`, `docker` all green (ADR-0009).
* `frontend/src/api/schema.ts` is committed, and `types-fresh` fails when regenerating it produces a difference.

## Pros and Cons of the Options

### Python + React/TypeScript, generated types

* Good, because `networkx` (no-loop checks, descendants, cycle finding) and `hypothesis` (stateful test machines, failure shrinking) are exactly the tools INV-4, INV-5, and INV-6 need.
* Good, because pydantic models serve triple duty: the schema the model must fill, the shape the API returns, and the source of the TypeScript types (ADR-0006).
* Bad, because two languages means two sets of idioms for one person to keep tasteful.

### All TypeScript

* Good, because one toolchain, one dependency tree, the simplest containers, and schemas shared with no generation step.
* Good, because the Anthropic TypeScript SDK is on par with Python's for schema-constrained model output.
* Bad, because its graph library is thinner than `networkx`, and its property-testing tool shrinks failures worse on stateful graph tests; the reviewer-facing core would be weaker or hand-rolled.
* Would be chosen if the backend were a thin streaming proxy with trivial logic, or if propagation moved into the browser.

### Python only, rendered on the server

* Good, because a single language and a single image.
* Bad, because the Workbench (UX-1 through UX-13) — typed ports, streaming growth, the faded before-and-after overlay, keyboard navigation — is not reachable with server-rendered fragments without badly rebuilding a frontend framework. Fails D5-i, the template-UI veto.

## More Information

* Interview decision D4 (stack), 2026-09-16; D3 (look and feel) motivates the frontend choice.
* `docs/research/04-engineering-structure.md` §1–§3, §7 — stack comparison, skeleton, containers, hygiene.
* `docs/research/03-ui-ux-directions.md` §1 — canvas technology verdict.
* networkx loop-free graph algorithms: https://networkx.org/documentation/stable/reference/algorithms/dag.html · hypothesis: https://hypothesis.readthedocs.io/ · openapi-typescript: https://openapi-ts.dev/
