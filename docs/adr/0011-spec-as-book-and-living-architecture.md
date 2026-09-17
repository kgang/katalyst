---
# ADR-0011: Organize the spec as a book by idea; keep a living ARCHITECTURE.md at the root
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: Kent's structure critique of 2026-09-16; AGENTS.md working agreements; ADR-0001
informed: every agent that writes a spec, an architecture doc, or a pull request in this repo
supersedes: none (this refines ADR-0001; it does not replace it)
superseded-by: none
spec-impact: spec/README.md (structure of the whole spec)
---

# ADR-0011: Organize the spec as a book by idea; keep a living ARCHITECTURE.md at the root

## Context and Problem Statement

The first pass at the spec directory was a flat run of numbered files — `spec/01-causal-graph.md` through `spec/06-probes.md` — mirroring the numbering of the decision records under `docs/adr/`. The owner's critique on 2026-09-16 was that the two directories are not the same kind of artifact. Decision records are produced one after another in time, so numbers are honest there. Specs are not: numbering them implied a reading sequence nobody intends, and readers arrive looking up *an idea* ("how does a link work?"), not step four. A second gap: nothing in the repo describes the system **as built**. `PRODUCT_REQUIREMENTS.md` states what the product must do for a user; the decision records state why each choice was made; neither tells a new reader or agent what actually exists today. How should durable knowledge be laid out so a reader can find an idea by name, and so the shape of the running system is never a guess?

## Decision Drivers

* The owner's critique of 2026-09-16 — numbers imply a false sequence; organize by idea, the way a book or an ontology (a named, structured inventory of the things in a domain) does.
* `AGENTS.md`: enduring context that must survive between agent sessions lives as ALL-CAPS documents at the repo root; every doc must stand alone, free of jargon and unexplained references.
* The kgents constitution's **Generative** principle — a spec is compression: a competent reader should be able to regenerate the implementation from the spec plus the architecture document. Compression fails if the reader cannot locate the part they need.
* Disgust-veto condition D5(ii), "not knowing why it did that." An architecture document that quietly drifts from the code is worse than none, because it is trusted and wrong.
* Solo developer plus several agents across many sessions: the layout must be maintainable by hand, with no generator to run and no index to regenerate.

## Considered Options

* **A.** Book-by-idea spec directories, plus a living `ARCHITECTURE.md` at the root.
* **B.** Flat numbered spec files — the previous layout, `spec/01-causal-graph.md` … `spec/06-probes.md`.
* **C.** One large spec document covering everything.
* **D.** Specs colocated with the code they describe.
* **E.** No `ARCHITECTURE.md`; rely on the product requirements plus the decision records.
* **F.** Architecture documentation generated automatically from the code.

## Decision Outcome

Chosen option: **A — book-by-idea spec directories plus a living `ARCHITECTURE.md`**, because it matches how readers actually search (by idea, not by ordinal), keeps enduring context in a root document as `AGENTS.md` requires, and gives the Generative principle the second half it was missing: what the system currently is, not only what it should become.

Two rules follow.

1. **The spec is a book.** One directory per idea — `graph/`, `multiverse/`, `thesis/`, `generation/`, `workbench/`, `probes/`. Each has a `README.md` landing page with three sections: **the idea** (one or two paragraphs), **what it owns** (the terms and the invariants — statements that must always hold — that belong to this part), and **its chapters** (a table of the files inside). Chapter files are unnumbered. A number is used only where a landing page deliberately states a reading order, and then the order is the point. Decision records under `docs/adr/` stay numbered: they are produced sequentially and a higher number supersedes a lower one, which makes them a journal, not a book.
2. **`ARCHITECTURE.md` at the repo root is living.** It is the technically focused counterpart to `PRODUCT_REQUIREMENTS.md`: components, boundaries, data flow, and deployment, describing the system both as built and as planned. Every section carries a **built** or **planned** marker, the document carries a **last verified** date, and it must be updated in the same pull request as any change that invalidates it.

### Consequences

* Good, because a reader looking for "how a branch is applied" opens `spec/multiverse/` and finds everything about it in one place, with no ordinal to decode.
* Good, because adding a seventh idea adds a directory and touches nothing else; adding a chapter does not renumber its siblings.
* Good, because `ARCHITECTURE.md` gives every new agent session one page that explains what exists, which is exactly the state the traceability veto demands.
* Bad, because a living architecture document is a standing maintenance cost, and a stale one is actively misleading; the same-pull-request rule and the "last verified" date are the countermeasures.
* Bad, because two root documents can drift from each other; the split is kept clean by scope — product requirements answer *what the user gets*, architecture answers *how it is put together*.
* Neutral, because directories are slightly deeper to navigate than a flat list; every landing page is the entry point, so depth costs one click.

### Confirmation

* `spec/` contains no numbered files, except where the enclosing landing page explicitly states a reading order. Checked by listing the directory in review; trivially scriptable later.
* Every subdirectory of `spec/` has a `README.md` containing the three sections: the idea, what it owns, its chapters.
* `ARCHITECTURE.md` contains a "last verified" line with a date, and every section carries a **built** or **planned** marker.
* The pull-request checklist gains one item: **"Does this change invalidate `ARCHITECTURE.md`? If yes, update it in this pull request."**

## Pros and Cons of the Options

### A. Book-by-idea spec plus a living ARCHITECTURE.md (chosen)

* Good, because lookup is by name, which is how anyone with a question actually searches.
* Good, because each part owns its terms and invariants, so ownership of a definition is unambiguous.
* Good, because the architecture document closes the gap between intent and reality that the requirements and decision records leave open.
* Bad, because it demands discipline: a landing page that is not updated when a chapter is added is a quiet lie.

### B. Flat numbered spec files (the previous layout)

* Good, because it is the simplest possible thing, and the numbers give every file a stable short name.
* Bad, because the numbers claim a reading order that does not exist, which was the owner's core objection.
* Bad, because inserting an idea between two existing ones forces a renumber or an awkward `03a`.

### C. One large spec document

* Good, because everything is in one file and cross-references are just anchors.
* Bad, because it grows past any comfortable read, and two agents editing different ideas collide in the same file.
* Bad, because a pull request touching one idea shows a diff against the whole spec, so review loses its focus.

### D. Specs colocated with the code they describe

* Good, because a spec next to its module is likelier to be updated with it.
* Bad, because ideas here span backend and frontend — the graph is both pydantic models (pydantic is the Python library that defines and validates data shapes) and canvas tiles — so colocation would split every idea in two.
* Bad, because the spec must exist and be accepted *before* the code, and there is no directory to put it next to yet.

### E. No ARCHITECTURE.md; rely on the requirements plus the decision records

* Good, because there is nothing extra to maintain, and no document can go stale.
* Bad, because reconstructing the current system means reading ten-plus decision records and mentally applying supersession — work repeated by every reader.
* Bad, because decision records are immutable by design: they record what was decided then, not what is true now.

### F. Auto-generated architecture documentation from code

* Good, because it can never drift from the code it reads.
* Bad, because it describes structure, not intent: it can list modules but cannot say why a boundary is where it is, or what is planned but unbuilt.
* Bad, because it adds a generator, a build step, and a checked-in artifact to a prototype that has not written its first module yet.

## More Information

* Kent's structure critique, 2026-09-16 (the interview session that produced this record): numbered specs implied a false sequence; readers look things up by idea; there is no document describing the system as built.
* ADR-0001 (record architecture decisions as MADR files, gated by owner acceptance). MADR — "Markdown Any Decision Records" — is the template these records follow: context, drivers, options, decision, consequences. This record refines ADR-0001 by distinguishing the numbered journal of decisions from the unnumbered book of specs; ADR-0001 remains in force unchanged.
* The kgents constitution's **Generative** principle: a specification is a compression of the system, and the test of the compression is whether a competent reader can regenerate the implementation from it. `ARCHITECTURE.md` supplies the half that describes what has already been generated.
* `spec/README.md` — the index this decision reshapes; `PRODUCT_REQUIREMENTS.md` §3 (owner decisions) and §12 (roadmap as pull-request stacks), which pair each spec part with the stack that writes it.
