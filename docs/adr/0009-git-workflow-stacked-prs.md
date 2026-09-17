---
# ADR-0009: Conventional commits, numbered stacks, and GitHub native stacked PRs
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md
informed: every agent that commits to this repo
supersedes: none
superseded-by: none
spec-impact: none (process); PRODUCT_REQUIREMENTS.md §12 defines the stack numbers this ADR names
---

# ADR-0009: Conventional commits, numbered stacks, and GitHub native stacked PRs

## Context and Problem Statement

A solo developer working with several agents on an open-ended garden (D7: no ship date, structure for continuous iteration) wants the repository's history to be navigable by a reviewer who was not there — which decision, which spec, which invariant, in what order. Engine and canvas are built in parallel (D11). How do we name branches, commits, and pull requests so the story reads itself, and how do we stack them: chain pull requests so each one builds on the one below?

## Decision Drivers

* NFR-5: every pull request names the invariant it satisfies; commits typed `spec:` and `adr:` form a decision timeline.
* D9, the decision-gated cadence: docs land before code, so the bottom of every stack is docs-only.
* D10: Kent chose GitHub's own stacked pull requests in the interview.
* D11: two stacks in flight at once must not collide.
* Taste: no tooling that costs the reviewer comprehension — which rules out alternative version-control front ends such as `jj` and `git-branchless` for this repo.

## Considered Options

* A. **GitHub's native stacked pull requests (public preview), with `git-spice` as fallback.** A stacked pull request is a chain in which each pull request targets the previous one's branch rather than `main`.
* B. `git-spice`, a stacking command-line tool, as primary.
* C. Graphite, a commercial stacking service.
* D. Plain `git` plus `gh pr create --base` (`gh` is GitHub's official command-line tool).

## Decision Outcome

Chosen option: "A", because it is zero tooling when it works, it appears directly in the pull-request interface the reviewer already uses, and Kent chose it; `git-spice` is the documented fallback if the preview is unavailable on `kgang/katalyst`.

Rules:

* **Commits.** Conventional Commits 1.0.0 — a message convention of `type(optional scope): short summary`. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `spec`, `adr`. Scope is the stack slug where it helps (`feat(engine): …`). Agent-authored commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. `git log --oneline --grep '^adr'` prints the decision timeline.
* **Branches.** `<type>/<NN>-<slug>`, where `NN` is the stack number from `PRODUCT_REQUIREMENTS.md` §12 (`docs/00-kickoff`, `feat/02-schema`, `feat/03-engine`, `feat/03-canvas`). `git branch --list '*03*'` lists a stack. Parallel stacks (03a, 03b) share `NN` and differ by slug.
* **Stacks.** One stack per roadmap row. The bottom pull request is docs-only (spec + decision record) and merges first; then domain types, then pure algorithms with their property tests, then the API surface, then the UI. Never deeper than four. Each pull-request body carries three headings: *What*, *Which invariant(s) this satisfies*, *Deliberately not here*. Agent-authored descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
* **Stacking tool.** Division of labour (owner decision, 2026-09-16): agents keep branches *stack-compatible* — each pull request's base is its parent branch, never `main` unless it is the bottom of a stack — and Kent assembles the stack in the GitHub web interface. The `gh` command-line tool (2.101.0) has no stack commands, so pull requests are opened with `gh pr create --base <parent-branch>`. `git-spice` remains the fallback if web-assembled stacks prove too thin at three or more deep.
* **Continuous integration** (the checks that run on every push). One workflow, four jobs: `backend`, `frontend`, `types-fresh`, `docker`. No API key in any of them (ADR-0008).
* **Before every commit.** `ruff` and `ruff-format` (Python linting and formatting), `biome` (the same for the frontend), `gitleaks` (a secret scanner), plus `end-of-file-fixer`, `check-yaml`, and `check-added-large-files`. Type checking runs in the build, not in the hook.
* **Merging.** Squash-merge each pull request — its commits collapse into a single commit on `main` — keeping the conventional prefix in the squashed message. `main` is always green.

### Consequences

* Good, because a reviewer can read `docs/adr/`, then `git log --grep '^spec\|^adr'`, then the stacks, and reconstruct why.
* Good, because docs-first bottoms enforce D9 mechanically.
* Bad, because the native preview may change or become unavailable; the fallback is documented and cheap.
* Bad, because squash-merging flattens the history inside a pull request; its body carries the narrative instead.
* Neutral, because the commit convention is enforced by review and a `commitizen check`, not by a server-side hook.

### Confirmation

* The `types-fresh` job fails if regenerating the schema produces a diff; `backend`, `frontend` and `docker` are required checks on `main`.
* `.github/pull_request_template.md` contains the three headings.
* `commitizen check`, a linter for commit messages, runs as a `commit-msg` hook.
* Stack 01's first pair of pull requests is the native-stack verification described above; its outcome is recorded under More Information.

## Pros and Cons of the Options

### A. GitHub native stacked pull requests (chosen)

* Good, because zero tooling; visible in the pull-request interface; Kent's choice.
* Bad, because it has only been in public preview since 2026-07-30 — behaviour may shift, and it needs verifying on the repo.

### B. `git-spice`

* Good, because a single Go binary over plain git branches, free, and `gs stack submit` retargets the whole chain for you.
* Bad, because one more tool for the reviewer to understand; kept as fallback.

### C. Graphite

* Good, because polished.
* Bad, because paid per user, and it pulls Node tooling into a Python repo.

### D. Plain git + gh

* Good, because nothing to install.
* Bad, because manual rebases and retargeting across two parallel stacks are exactly where hygiene slips.

## More Information

* Interview D7 (open-ended garden), D10 (GitHub native stacked pull requests), D11 (engine and canvas in parallel).
* `docs/research/04-engineering-structure.md` §7 (git hygiene) — GitHub changelog: https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ · docs: https://docs.github.com/en/pull-requests/get-started/about-stacked-prs · git-spice: https://abhinav.github.io/git-spice/ · Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
* Verification outcome (2026-09-16): `gh` 2.101.0 exposes no stack subcommand or flag; native stacks are assembled in the web interface. Agents chain bases; Kent stacks.
