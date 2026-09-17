This is a take home coding assignment for https://catalyst.app/.

Catalyst is the agent layer for finance. We turn natural language — a thesis, strategy, hedge, or trading idea — into live execution across any market, venue, or asset class from prediction markets to commodities to tokens to private markets. It is a seed stage company with investments from Sequoia, Jump Trading, and Lux Capital.

Here are more details about Catalyst: https://coastalhq.co/scoop/e3a34548-1964-4b30-96ea-52801a558dd2

The goal of the project is to create a functional protoype of the concept behind Catalyst as a company. The full brief I was provided for this is located at ./ASSIGNMENT.md

## Map

| Where | What |
|-------|------|
| `PRODUCT_REQUIREMENTS.md` | The compressed seed: decisions, requirements, invariants, anti-patterns, roadmap as PR stacks |
| `docs/adr/` | Numbered decision records (MADR format: context, options, decision, consequences); `template.md`; `README.md` index. Higher number supersedes |
| `spec/` | Feature specs with INVARIANTS and ANTI-PATTERNS; `00-vocabulary.md` is the shared language |
| `docs/research/` | Four independent research reports (2026-09-16) that fed the PRD; inputs, not decisions |
| `docs/initial-brainstorming.md` | Kent's raw notes; the origin of trigger/sustain links and refinement |

## Working agreements (interview, 2026-09-16)

* **ADR-gated cadence.** An agent drafts the ADR and spec first; Kent accepts, rejects, or amends; only then is code written. Nothing is implemented against a `proposed` ADR. Decisions Kent has already taken are listed in `PRODUCT_REQUIREMENTS.md` §3 — do not re-litigate them.
* **Disgust veto.** Two conditions end a line of work immediately: a template-looking UI, and any state that cannot be traced to an input, a rule, or a cited source.
* **Vocabulary is the interface.** Use `spec/00-vocabulary.md` words exactly in docs, code, and UI copy.
* **Every number can say why.** Beliefs carry owner, interval, and provenance; two significant figures; model, user, and market beliefs are never merged.
* **Stacks tell the story.** One stack per spec; the bottom PR is docs-only; branch names are `<type>/<NN>-<slug>` with `NN` the stack number from the PRD roadmap. Conventional commits with `spec:` and `adr:` types in addition to the usual.
* **Research reports are inputs.** Where a report and an ADR disagree, the ADR wins; where an ADR and the PRD disagree, fix the drift in the same PR.

RULES FOR THIS REPO

* Significant architectural decisions should be recorded at ./docs/adr in a numbered order. Higher number records supersede lower numbered ones.
* Enduring context between agents should live as all caps docs in the root of the repo, e.g. AGENTS.md, ASSIGNMENT.md, PRODUCT_REQUIREMENTS.md. These should always be kept up to date if you notice them drifting.
* More detailed descriptions, diagrams about particular systems or complex features should be written to ./spec
* Specs should follow best practices regarding spec-driven development. Some key aspects of specs for this repo should include invariants and anti-patterns
* This is an experimental prototype and I am a solo developer. However, I would like to use best practices regarding commit messages, PRs, and PR stacks to maintain the navigability, hygiene, and legibility of this repo.
* Docs should avoid jargon, reference to other docs, or unexplained abbreviations and symbols. They should be self-contained as much as possible. That is, explain in doc what the concepts being referenced are. This also extends to doc strings and comments in the code.
* Be concise, punchy, and succinct without sacrificing clarity. Use formatting as a communication and legibility aid.