# Architecture Decision Records

Format: [MADR 4.x](https://adr.github.io/madr/) with three project-local front-matter fields — `supersedes`, `superseded-by`, `spec-impact` — see [`template.md`](template.md). No tooling: copy the template, take the next number, add a row here.

Rules (from `AGENTS.md`): numbered in order; a higher-numbered record supersedes a lower-numbered one on the same question; an ADR is `proposed` until Kent accepts it, and nothing is implemented against a `proposed` ADR.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions in MADR 4.x, no tooling, ADR-gated cadence | accepted | 2026-09-16 |
| [0002](0002-python-backend-react-frontend.md) | Python/FastAPI backend with a React/TypeScript frontend; OpenAPI-generated types | accepted | 2026-09-16 |
| [0003](0003-domain-owns-the-graph.md) | The domain layer owns graph validity; the LLM only proposes | accepted | 2026-09-16 |
| [0004](0004-branches-are-patches.md) | Branches are ordered patch lists over an immutable base; `do` ≠ `observe`; beliefs never merged | accepted | 2026-09-16 |
| [0005](0005-link-semantics-and-propagation.md) | Typed links (trigger/sustain, log-odds, lag, shape) propagated by seeded forward Monte Carlo | accepted | 2026-09-16 |
| [0006](0006-llm-boundary-structured-outputs.md) | LLM boundary: Anthropic SDK, `claude-opus-5`, structured outputs, one proposal per call, SSE | accepted | 2026-09-16 |
| [0007](0007-canvas-react-flow-elk.md) | Canvas: React Flow v12 + ELK layered layout + Motion; typed ports; ghost diff; no modals | accepted | 2026-09-16 |
| [0008](0008-testing-layers-and-cassettes.md) | Four testing layers; VCR cassettes so CI runs without an API key; evals out-of-band | accepted | 2026-09-16 |
| [0009](0009-git-workflow-stacked-prs.md) | Conventional commits, `<type>/<NN>-<slug>` branches, GitHub native stacked PRs (git-spice fallback) | accepted | 2026-09-16 |
| [0010](0010-grounding-sources.md) | Grounding: Polymarket + FRED behind a `GroundingSource` Protocol; Metaculus/yfinance rejected | accepted | 2026-09-16 |
| [0011](0011-spec-as-book-and-living-architecture.md) | Spec organized as a book by idea (unnumbered chapters); living `ARCHITECTURE.md` at the root | accepted | 2026-09-16 |
| [0013](0013-payoff-names-the-trade-quote-names-the-price.md) | `Payoff` splits into a contract shape and a price shape; the domain names the trade, the quote names the price | accepted | 2026-09-17 |
