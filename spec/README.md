# Specs

Spec-driven development: a spec is the version-controlled source of truth that implementation follows from, not prose written afterward. Each feature spec is the bottom PR of its stack (see `PRODUCT_REQUIREMENTS.md` §12) and merges before any code in that stack.

## Shape of a spec

1. **Purpose** — one paragraph; what a user can do that they could not before.
2. **Vocabulary** — uses `00-vocabulary.md` terms exactly; defines nothing twice.
3. **Data model** — the pydantic models verbatim, plus a Mermaid diagram where a picture shows a mechanism.
4. **Behaviour** — numbered user-visible flows (`B1`, `B2`, …), each with a worked example on a real `ASSIGNMENT.md` event.
5. **INVARIANTS** — numbered `INV-*` predicates over generated inputs, each naming the property test that checks it. The phrasing rule: *for all X drawn from strategy S, P(X)*. If no strategy can be named, it is a wish and belongs in Behaviour.
6. **ANTI-PATTERNS** — *do not X, because Y; do Z instead*, each traceable to a real temptation.
7. **Open questions** — dated.

Product-level invariants and anti-patterns are in `PRODUCT_REQUIREMENTS.md` §9–10 and are referenced by ID; specs refine them into testable form and may add local ones (`INV-2.3` style numbering: spec 02, local invariant 3).

## Index

| # | Spec | Stack | Owns |
|---|------|-------|------|
| 00 | [`00-vocabulary.md`](00-vocabulary.md) | 00 | Every term used across docs, code, and UI |
| 01 | `01-causal-graph.md` | 02 | Proposition, Link, Belief, Graph; INV-1, 2, 6, 7, 9, 11 |
| 02 | `02-interventions.md` | 02/03a | Intervention ops, Branch, World, Diff; INV-3, 4, 5, 10 |
| 03 | `03-thesis.md` | 05 | Sensitivity, invalidation derivation, Thesis, strategy export; INV-14 |
| 04 | `04-canvas.md` | 03b | Workbench UI: tiles, ports, wires, LOD, diff, Inspector; INV-8, 12 |
| 05 | `05-llm-boundary.md` | 04 | Generation pipeline, streaming, grounding, cassettes, evals; INV-13 |
| 06 | `06-probes.md` | 06 | Refine, Monte Carlo distribution, probes, value of information |

Specs 01–06 are written as the bottom PR of their stack, after the ADRs they depend on are accepted.

Diagrams live beside their spec as Mermaid in the markdown; rendered assets, if any, go in `spec/diagrams/`.
