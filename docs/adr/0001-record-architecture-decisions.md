---
# ADR-0001: Record architecture decisions as MADR 4.x files, gated by owner acceptance
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md
informed: all agents working in this repo (see AGENTS.md)
supersedes: none
superseded-by: none
spec-impact: none (process decision; every later spec cites its ADRs)
---

# ADR-0001: Record architecture decisions as MADR 4.x files, gated by owner acceptance

## Context and Problem Statement

`AGENTS.md` requires that significant architectural decisions be recorded under `./docs/adr` in numbered order, with higher numbers superseding lower ones. The owner's disgust-veto (D5-ii) is "not knowing why it did that": any state of the repo that cannot be traced to a decision with a reason. Several agents (Claude, Codex) and one human will work here across many sessions. How do we record decisions so that the *why* survives the session that made them, and so that no agent implements something the owner has not yet accepted?

## Decision Drivers

* D5-ii — every architectural state must be traceable to a recorded, justified decision
* D9 — cadence is ADR-gated: draft ADR + spec → owner accepts → implement
* NFR-5 — legibility: every decision is an ADR, every PR names what it satisfies
* Solo developer plus agents: the format must be writable by hand and by an LLM without tooling drift
* Supersession must be greppable, not implied by file order

## Considered Options

* MADR 4.x markdown, no tooling
* Nygard-style ADRs (Context / Decision / Status / Consequences)
* `adr-tools` (shell scripts around templates)
* `log4brains` (static ADR site, Node dependency)
* No ADRs; rely on commit messages and PR descriptions

## Decision Outcome

Chosen option: "MADR 4.x markdown, no tooling", because MADR's *Decision Drivers* and *Pros and Cons of the Options* sections are precisely the rigor the owner asked for, the template is a single file any agent can copy, and adding tooling would introduce a dependency that earns nothing in a repo with one author.

Project-local rules layered on MADR:

1. Three extra front-matter fields: `supersedes`, `superseded-by`, `spec-impact`. Supersession is stated on *both* records.
2. Status lifecycle: `proposed` → `accepted` | `deprecated` | `superseded by ADR-NNNN`. Only the owner moves a record out of `proposed`.
3. **Nothing is implemented against a `proposed` ADR.** A PR that lands code whose design rests on a proposed ADR is a process bug, not a judgment call.
4. Every ADR's `Confirmation` section names a concrete check (test, CI job, lint rule, review item) so the decision can be audited later.
5. `docs/adr/README.md` is the index; a new ADR adds one row.

### Consequences

* Good, because the "why" of every structural choice lives next to the code and is versioned with it.
* Good, because supersession is explicit on both ends, so a reader landing on an old ADR is redirected.
* Good, because the acceptance gate makes the owner's authority (L1.13) structural rather than aspirational.
* Bad, because writing an ADR before every significant change slows the first stack; the garden cadence (D7) absorbs this.
* Neutral, because with no tooling the index is maintained by hand; a stale index is caught in review.

### Confirmation

* Review checklist item on every PR: "Does this PR rest on any ADR whose status is `proposed`? If yes, block."
* `docs/adr/README.md` row count equals the number of `docs/adr/0*.md` files (checked in review; trivially scriptable later).
* Every `docs/adr/0*.md` begins with the template's front-matter block including `supersedes`, `superseded-by`, `spec-impact`.

## Pros and Cons of the Options

### MADR 4.x markdown, no tooling

* Good, because it forces alternatives and drivers to be written down, not just the winner.
* Good, because it is the de facto standard with a maintained spec (4.0.0, 2024-09).
* Bad, because the template is long enough that trivial decisions feel heavy; the remedy is to not write ADRs for trivial decisions.

### Nygard-style ADRs

* Good, because they are short and fast to write.
* Bad, because they omit drivers and rejected options, which is exactly the content the owner wants for auditability.

### adr-tools

* Good, because it numbers and links files automatically.
* Bad, because it is an unmaintained shell wrapper around `cp`, and its template is Nygard-style.

### log4brains

* Good, because it renders a browsable site with a timeline.
* Bad, because it adds a Node dependency to a Python-first repo for a feature nobody will open.

### No ADRs

* Good, because it costs nothing up front.
* Bad, because it violates `AGENTS.md` and the D5-ii veto directly.

## More Information

* Interview decision D9 (ADR-gated cadence), 2026-09-16.
* `docs/research/04-engineering-structure.md` §5 — MADR vs Nygard, tooling verdict, first-eight-ADR proposal.
* MADR: https://adr.github.io/madr/
* Template: `docs/adr/template.md`
