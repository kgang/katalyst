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
* **Branches.** `<type>/<NN>-<slug>`, where `NN` is the stack number from `PRODUCT_REQUIREMENTS.md` §12. The names used so far: `docs/00-kickoff`; then stack 01 as `docs/01-readme`, `feat/01-backend-skeleton`, `feat/01-frontend-skeleton`, `chore/01-docker-ci`; then stack 02 as `spec/02-graph-and-multiverse`, `feat/02-domain-models`, `feat/02-validity`, `feat/02-hormuz-fixture`, `adr/02-replay-mode`. Next are `feat/03-engine` and `feat/03-canvas`. `git branch --list '*03*'` lists a stack. Parallel stacks (03a, 03b) share `NN` and differ by slug. One stack is several branches, so the stack number, not the slug, is what ties them together.
* **Stacks.** One stack per roadmap row. The bottom pull request is docs-only (spec + decision record) and merges first; then domain types, then pure algorithms with their property tests, then the API surface, then the UI. Never deeper than four. Each pull-request body carries three headings: *What*, *Which invariant(s) this satisfies*, *Deliberately not here*. Agent-authored descriptions end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
* **Stacking tool.** Division of labour (owner decision, 2026-09-16): agents keep branches *stack-compatible* — each pull request's base is its parent branch, never `main` unless it is the bottom of a stack — and Kent assembles the stack in the GitHub web interface. The `gh` command-line tool (2.101.0) has no stack commands, so pull requests are opened with `gh pr create --base <parent-branch>`. `git-spice` remains the fallback if web-assembled stacks prove too thin at three or more deep.
* **Continuous integration** (the checks that run on every push). One workflow, four jobs: `backend`, `frontend`, `types-fresh`, `docker`. *(Amended 2026-09-17: five — stack 03b added `e2e`, one keyboard-only browser test that starts both halves itself. Still no key in any of them.)* *(Amended again 2026-09-20: six — stack 04b adds `recordings`, which reads every committed recording and needs no key. See the amendment at the foot of this record.)* No API key in any of them (ADR-0008).
* **Before every commit.** `ruff` and `ruff-format` (Python linting and formatting), `biome` (the same for the frontend), `gitleaks` (a secret scanner), plus `end-of-file-fixer`, `check-yaml`, and `check-added-large-files`. Type checking runs in the build, not in the hook.
* **Merging.** Squash-merge each pull request — its commits collapse into a single commit on `main` — keeping the conventional prefix in the squashed message. `main` is always green.

### Consequences

* Good, because a reviewer can read `docs/adr/`, then `git log --grep '^spec\|^adr'`, then the stacks, and reconstruct why.
* Good, because docs-first bottoms enforce D9 mechanically.
* Bad, because the native preview may change or become unavailable; the fallback is documented and cheap.
* Bad, because squash-merging flattens the history inside a pull request; its body carries the narrative instead.
* Neutral, because the commit convention is enforced by review and a `commitizen check`, not by a server-side hook.

### Confirmation

* The `types-fresh` job fails if regenerating the schema produces a diff; `backend`, `frontend` and `docker` are required checks on `main`. *(Amended 2026-09-20: `recordings` joins that list — see the amendment at the foot of this record.)*
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
* **Verification outcome (2026-09-17).** GitHub's native stacked pull requests work on `kgang/katalyst`. A pull request whose base is another pull request's branch shows up as a stack in the interface, and GitHub re-targets the children itself as each one merges. Stacks 01 and 02 were merged this way; `git-spice` was not needed. Two things about *merging* a stack are not obvious, and both cost an afternoon the first time.

  `gh pr merge` refuses a stacked pull request outright: it answers that the pull request must be merged using the asynchronous merge REST API. The route that works, one pull request at a time:

  ```sh
  gh api -X PUT repos/<owner>/<repo>/pulls/<n>/merge-async \
    -f merge_method=squash \
    -f commit_title="<conventional title> (#n)" \
    -f commit_message="<the pull request's What section>" \
    -f sha=<head sha>
  ```

  That call hands back a job identifier rather than a result. Poll `GET repos/<owner>/<repo>/pulls/<n>/merge-async/<uuid>` until its `status` field reads `merged`, and only then start the next one. Merge bottom-up, one at a time. GitHub re-stacks the remaining children itself after each merge, but a child that had carried a merge of a *sibling* stack may still refuse until `git merge origin/main` is run in its own worktree and pushed. The asynchronous merge does not delete the head branch either, so branches are deleted afterwards by hand.

  **The trap, learned the hard way.** `gh pr merge` on the *top* pull request of a stack does not refuse — it succeeds, and merges that pull request into its parent branch rather than into `main`. That is how #11 (Docker, continuous integration, pre-commit, the Makefile) reached `main` folded inside #6's squashed commit rather than as a commit of its own: nothing was lost, but `git log` on `main` shows no #11. Use the asynchronous route for every pull request in a stack, the top one included.

## Amendment (2026-09-20) — a sixth build job, `recordings`

Stack 04b adds a sixth continuous-integration job, **`recordings`**. It reads every committed recording under `backend/recordings/` — the files a keyless reviewer's replay plays back (ADR-0012) — and checks that each one parses and that each carries a prompt hash equal to the current prompt's. **It needs no model key**, so INV-13 still holds: not one job in the workflow has one. It **passes on an empty folder**, so it is green from the commit that adds it.

The jobs are therefore `backend`, `frontend`, `types-fresh`, `docker`, `e2e` and `recordings`, and **`recordings` joins `backend`, `frontend` and `docker` as a required check on `main`.** It earns that place because a stale recording is the one failure no other job can see: nothing crashes, the demo simply plays old wording at a reviewer.

**The job itself lands in stack 04b's stream pull request**, beside the recordings it reads. This record only names it and puts it on the required list.

Nothing else changes: one workflow, no key anywhere in it, and the standing rule that a pull request which changes a prompt re-records whatever depended on it.

## Second amendment (2026-09-21) — a stack is two deep

**In force from today.** Kent decided this on 2026-09-21, and unlike the other amendments proposed that day it waits on no record: it is a change to how we work, it is his to make, and he made it.

**The rule, as the dated decisions note records his choice** (row R13). A stack is **at most two deep** — a docs-only pull request at the bottom, and **one** code pull request on top of it; otherwise straight onto `main`. The sentence *"Never deeper than four"* under **Stacks** above is replaced by that, and nothing else in this record changes.

**Why.** Four-deep stacks cost stack 04 a three-case rebase recipe, a file-ownership table nobody could hold in their head, and four days with `main` static while the bottom waited. The cost is not linear: every pull request below yours is a rebase you will do, and a `main` that cannot move is a review nobody can check against the thing that shipped.

**Everything else in this record is unchanged** — Conventional Commits and its eight types; `<type>/<NN>-<slug>` branch names with the stack number from `PRODUCT_REQUIREMENTS.md` §12; a docs-only bottom, which is how the decision-gated cadence is enforced mechanically; the three pull-request headings *What* · *Which invariant(s) this satisfies* · *Deliberately not here*; squash-merge; `main` always green; the pre-commit set; the six build jobs and the four required checks; and the asynchronous-merge recipe above, which still applies to a two-deep stack exactly as written, including its trap about the top pull request.

*An observation rather than a rule:* with stacks two deep, the bottom of a stack tends to carry more — a docs pull request now usually holds the decision records **and** the chapters they bind, because there is no third floor to put the chapters on.
