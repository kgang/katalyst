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

This repo's standing instructions require that significant architectural decisions be written down under `docs/adr/` in numbered order, a higher number superseding a lower one. The owner's second disgust veto — D5-ii, "not knowing why it did that" — rules out any state of the repo that cannot be traced back to a decision and its reason. Several agents and one human work here across many sessions. How do we record decisions so the *why* outlives the session that made it, and so that no agent builds against something the owner has not yet accepted?

## Decision Drivers

* D5-ii (disgust veto: nothing unexplained) — every architectural state must point at a recorded, justified decision
* D9 (decision-gated cadence) — draft the record and spec, owner accepts, then implement
* NFR-5 (legibility) — every decision is a record; every pull request names what it satisfies
* One developer plus agents: the format must be writable by hand and by a language model, with no tooling that can drift out of date
* Supersession must be findable by plain-text search, not inferred from file order

## Considered Options

* MADR 4.x markdown, no tooling — MADR is a standard markdown template for decision records: context, drivers, options, outcome, consequences
* Nygard-style records — the original short form: context, decision, status, consequences
* `adr-tools` — shell scripts that copy a template and number the files
* `log4brains` — a generator that renders the records as a browsable site; needs Node.js
* No records; rely on commit messages and pull request descriptions

## Decision Outcome

Chosen option: "MADR 4.x markdown, no tooling", because MADR's *Decision Drivers* and *Pros and Cons of the Options* sections are precisely the rigor the owner asked for, the template is a single file any agent can copy, and tooling would add a dependency that earns nothing in a repo with one author.

Project-local rules layered on MADR:

1. Three extra fields in the front matter (the `---` block at the top of each file): `supersedes`, `superseded-by`, `spec-impact`. Supersession is stated on *both* records.
2. Status lifecycle: `proposed` → `accepted` | `deprecated` | `superseded by ADR-NNNN`. Only the owner moves a record out of `proposed`.
3. **Nothing is implemented against a `proposed` record.** A pull request landing code whose design rests on a proposed record is a process bug, not a judgment call.
4. Every record's `Confirmation` section names a concrete check — a test, a continuous-integration job, a lint rule, a review item — so the decision can be audited later.
5. `docs/adr/README.md` is the index; a new record adds one row.

### Consequences

* Good, because the "why" of every structural choice lives next to the code and is versioned with it.
* Good, because supersession is explicit at both ends, so a reader landing on an old record is redirected.
* Good, because the acceptance gate makes the owner's authority structural rather than aspirational.
* Bad, because writing a record before every significant change slows the first stack of pull requests; the open-ended, keep-iterating budget (D7) absorbs this.
* Neutral, because with no tooling the index is maintained by hand; a stale index is caught in review.

### Confirmation

* Review checklist item on every pull request: "Does this rest on any record whose status is `proposed`? If yes, block."
* `docs/adr/README.md` row count equals the number of `docs/adr/0*.md` files (checked in review; trivially scriptable later).
* Every `docs/adr/0*.md` opens with the template's front matter, including `supersedes`, `superseded-by`, `spec-impact`.

## Pros and Cons of the Options

### MADR 4.x markdown, no tooling

* Good, because it forces the alternatives and the drivers to be written down, not just the winner.
* Good, because it is the de facto standard with a maintained spec (4.0.0, 2024-09).
* Bad, because the template is long enough that trivial decisions feel heavy; the remedy is to not write records for trivial decisions.

### Nygard-style records

* Good, because they are short and fast to write.
* Bad, because they omit drivers and rejected options — exactly the content the owner wants for auditability.

### adr-tools

* Good, because it numbers and links files automatically.
* Bad, because it is an unmaintained shell wrapper around a file copy, and its template is the Nygard short form.

### log4brains

* Good, because it renders a browsable site with a timeline.
* Bad, because it adds a Node.js dependency to a Python-first repo for a feature nobody will open.

### No records

* Good, because it costs nothing up front.
* Bad, because it breaks the repo's standing instructions and the D5-ii veto directly.

## More Information

* Interview decision D9 (decision-gated cadence), 2026-09-16.
* Refined by ADR-0011 (the spec is organized as a book by idea; a living ARCHITECTURE.md is the technical counterpart to the product requirements).
* `docs/research/04-engineering-structure.md` §5 — MADR versus Nygard, tooling verdict, first-eight-record proposal.
* MADR: https://adr.github.io/madr/
* Template: `docs/adr/template.md`
