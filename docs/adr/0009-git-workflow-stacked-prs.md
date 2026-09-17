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

A solo developer working with several agents on an open-ended garden (D7) wants the repository's history to be navigable by a reviewer who was not present: which decision, which spec, which invariant, in what order. Engine and canvas will be built in parallel (D11). How do we name branches, commits, and PRs so that the story reads itself, and which stacking tool do we adopt?

## Decision Drivers

* NFR-5: every PR names the invariant it satisfies; `spec:` and `adr:` commits form a decision timeline.
* D9: ADR-gated cadence — docs land before code, so the bottom of every stack is docs-only.
* D10: Kent chose GitHub native stacked PRs in the interview.
* D11: two stacks in flight at once must not collide.
* Tasteful: no tooling that costs the reviewer comprehension (rules out `jj`, `git-branchless` for this repo).

## Considered Options

* A. **GitHub native stacked PRs (public preview) with `git-spice` as fallback**
* B. `git-spice` as primary
* C. Graphite
* D. Plain `git` + `gh pr create --base`

## Decision Outcome

Chosen option: "A", because it is zero tooling when it works, is visible directly in the PR UI the reviewer already uses, and Kent chose it; `git-spice` is the documented fallback if the preview is unavailable on `kgang/katalyst`.

Rules:

* **Commits.** Conventional Commits 1.0.0. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `spec`, `adr`. Scope is the stack slug when useful (`feat(engine): …`). Agent-authored commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. `git log --oneline --grep '^adr'` is the decision timeline.
* **Branches.** `<type>/<NN>-<slug>` where `NN` is the stack number from `PRODUCT_REQUIREMENTS.md` §12 (`docs/00-kickoff`, `feat/02-schema`, `feat/03-engine`, `feat/03-canvas`). `git branch --list '*03*'` lists a stack. Parallel stacks (03a/03b) share `NN` and differ by slug.
* **Stacks.** One stack per roadmap row. The bottom PR is docs-only (spec + ADR) and merges first; then domain types → pure algorithms + property tests → API surface → UI. Never deeper than 4 PRs. Each PR body has three headings: *What*, *Which invariant(s) this satisfies*, *Deliberately not here*. PR descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` when agent-authored.
* **Stacking tool.** Division of labour (owner decision, 2026-09-16): agents keep branches *stack-compatible* — each PR's base is its parent branch, never `main` unless it is the bottom of a stack — and Kent assembles the stack in the GitHub web UI. The `gh` CLI (2.101.0) has no stack commands, so PRs are opened with `gh pr create --base <parent-branch>`. `git-spice` remains the fallback if UI-assembled stacks prove too thin at 3+ PRs deep.
* **CI.** One workflow, four jobs: `backend`, `frontend`, `types-fresh`, `docker`. No API key in CI (ADR-0008).
* **Pre-commit.** `ruff`, `ruff-format`, `biome`, `gitleaks`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`. Type checking runs in CI, not in the hook.
* **Merging.** Squash-merge each PR; the squash message keeps the conventional prefix. `main` is always green.

### Consequences

* Good, because a reviewer can read `docs/adr/`, then `git log --grep '^spec\|^adr'`, then the stacks, and reconstruct why.
* Good, because docs-first bottoms enforce D9 mechanically.
* Bad, because the native preview may change or be unavailable; the fallback is documented and cheap.
* Bad, because squash-merge flattens intra-PR history; the PR body carries the narrative instead.
* Neutral, because conventional-commit enforcement is by review and `commitizen` check, not a server-side hook.

### Confirmation

* CI job `types-fresh` fails on a regenerated-schema diff; jobs `backend`, `frontend`, `docker` are required checks on `main`.
* `.github/pull_request_template.md` contains the three headings.
* `commitizen check` runs in pre-commit's `commit-msg` stage.
* Stack 01's first PR pair is the native-stack verification described above; its outcome is noted in this ADR's More Information.

## Pros and Cons of the Options

### A. GitHub native stacked PRs (chosen)

* Good, because zero tooling; visible in the PR UI; Kent's choice.
* Bad, because public preview since 2026-07-30 — behaviour may shift; needs verification on the repo.

### B. `git-spice`

* Good, because single Go binary, plain git branches, free, `gs stack submit` handles retargeting.
* Bad, because one more tool for the reviewer to understand; kept as fallback.

### C. Graphite

* Good, because polished.
* Bad, because paid per user and pulls Node into a Python repo's tooling.

### D. Plain git + gh

* Good, because nothing to install.
* Bad, because manual rebases and retargets across two parallel stacks are exactly where hygiene slips.

## More Information

* Interview D7 (open-ended garden), D10 (GitHub native stacked PRs), D11 (parallel engine + canvas).
* `docs/research/04-engineering-structure.md` §7 (git hygiene) — GitHub changelog: https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ · docs: https://docs.github.com/en/pull-requests/get-started/about-stacked-prs · git-spice: https://abhinav.github.io/git-spice/ · Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
* Verification outcome (2026-09-16): `gh` 2.101.0 exposes no stack subcommand or flag; native stacks are assembled in the web UI. Agents chain bases; Kent stacks.
