---
# ADR-0021: What version one does not build
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted:
  - the adversarial pass over the 2026-09-21 design, finding S6, which counted six functional requirements cut with no record at all; and that design's own list of what is not being built — both kept locally under `plans/`
  - ADR-0015, which already forbids an ensemble; ADR-0010, which fixes what grounding exists
informed: every agent on stacks 05, 06 and 07, and any reviewer reading `PRODUCT_REQUIREMENTS.md` against what shipped
supersedes: none
superseded-by: none
spec-impact: PRODUCT_REQUIREMENTS.md FR-8, FR-17, FR-18, FR-20, FR-24, FR-29, FR-30, FR-31, INV-10, anti-pattern 12; spec/vocabulary.md (*Probe*, *Value of information*, *Provenance*, *Thesis*); spec/probes/ (its subject is not built); spec/multiverse/ (`refine` stays a refusal)
---

# ADR-0021: What version one does not build

> **The number is 0021 on purpose.** 0018, 0019 and 0020 are reserved for stack 06 — like with like, a stop is a price the reader owns, and quotes recorded first. **Only 0019 is Kent's**, decided on 2026-09-21; 0018 and 0020 come from the coordinator's plan and are written when that stack opens.

> **In short.** One record accounts for everything in the requirements that version one does not build, because the finishing checklist wants an accepted record behind every cut. **Not built:** three or more branches side by side (FR-17), splitting a claim into finer ones (FR-18), probes (FR-20), three quantities inside FR-24 — the average loss in the worst 5% of runs, the largest peak-to-trough loss and the chance of being wiped out — the historical-analog panel (FR-29) and the pastcast self-test (FR-30). **INV-10** is met by a refusal the product already returns in its own sentence. **FR-31 is shrunk, not cut** (Kent, R12): a finished generation is served back by its id from the same line-by-line file a recording is — one format, one loader, **no database in version one at all**.
>
> **On screen.** Nothing new. Each requirement keeps its words and gains a dated line pointing here, so an absence can be traced to a decision.
>
> **What it costs.** Nothing here is started. Cutting FR-30 removes the one condition that could have reopened an ensemble, so none is built in version one.
>
> **Open for Kent.** **FR-17 and FR-29** are cut here for the first time, with no earlier decision behind them.

## Context and Problem Statement

This project's finishing checklist requires **every decision, including every requirement cut, to have an accepted record.** Six functional requirements and one invariant are cut, and one requirement shrunk, and until this record exists all seven are cut nowhere and built nowhere. A reader comparing `PRODUCT_REQUIREMENTS.md` against what ships would find them simply missing — the same shape of dishonesty as a number nobody computed.

**Who decided what, exactly.** **Kent decided FR-31's shrink** (2026-09-21). **Everything else on this page is the coordinator's call, written `proposed` here so that Kent accepts it or names one back.** Two of them — **FR-17 and FR-29** — appear on this page for the first time and have no prior decision behind them at all; their reasons below are the coordinator's, offered as proposals, and both are put to Kent under *Open for Kent*.

This record is short on purpose: one entry each, the requirement in its own words and one sentence of reason.

## Decision Drivers

* **The finishing checklist**: every cut requirement has a record, or the box does not tick.
* **The brief.** Nothing cut here is asked for by the assignment; each was our own addition to the roadmap.
* **The traceability veto** (Kent): a reader must be able to trace what is on screen — and what is absent — to a decision.
* **Where the remaining sessions go**: stacks 05, 06 and 07 are the engine's soundness, the trade, and a map you can argue with. Everything below competes with those.

## Considered Options

**A.** One short record listing every cut, amending the requirements in the same pull request. · **B.** A record per cut — seven pages each saying one thing. · **C.** Delete the requirements and say nothing.

## Decision Outcome

Chosen option: **A**, because the cuts share one reason — they are research projects or dashboards competing with the three things the brief actually asks for — and seven records would make a reader read seven pages to learn it once; and because C is the traceability veto in its plainest form.

### The cuts

**FR-17 (P1)** — *"Compare ≥3 branches as small multiples; at most 4 branches visible, rest collapsed to a list; branches must be named."*
**Not built** *(coordinator's proposal; no prior decision).* Three or more branches side by side is a dashboard, the ranked change list already answers that question two worlds at a time, and how one ranking is read across three lists is undesigned — an open question in the diff chapter rather than a plan item.

**FR-18 (P1)** — *"`refine`: expand a proposition into sub-propositions; the children's combined likelihood must equal the parent's — they marginalize back (INV-10). This is the brainstorm's 'search deeper lines'."*
**Not built.** Making finer claims add back up to the claim they replace means re-deriving the parent's number by summing the children out of the joint, every time either changes — a research project on top of an exact core — and nothing in the brief asks for it.

**INV-10** — *"Refinement adds up. After a proposition is split into finer sub-propositions, their combined likelihood equals the original's within a small tolerance."*
**Met by a named refusal, not a feature.** The `refine` operation exists as a shape so nothing has to be retrofitted, and asking for it returns one violation in our own sentence: *"Splitting the claim … into finer claims is not built yet, so this edit cannot be folded onto this map"* (`backend/src/katalyst/domain/patch.py:657-691`, code `edit_not_applicable`, pinned by `test_splitting_a_claim_says_it_is_not_built_yet` in `backend/tests/unit/domain/test_patches.py:877`). An invariant about an operation the product refuses to perform is satisfied by the refusal, and the checklist says so rather than leaving the box blank.

**FR-20 (P2)** — *"Probes: attach a Monte Carlo, a Bayesian sub-net, or a persona red-team to one proposition; results re-enter as `simulated` beliefs with their own provenance and rationale."*
**Not built.** A second engine bolted onto one claim produces a second set of answers to reconcile; the honest part of the idea — a persona that argues with a step of the map — lands in stack 07 as *challenge this arrow*, on machinery that exists.

**FR-24 (P1), in part** — *"Payoff distribution from thousands of random simulations: the 10th / 50th / 90th-percentile outcomes, **the average loss in the worst 5% of runs (CVaR₅), the largest peak-to-trough loss, and the chance of being wiped out.** The actuarial 'wiped out' case gets its own row."*
**The three emphasised quantities are not built.** Each needs a capital base and a portfolio — how much the reader has, and what else they hold — and the product asks for neither, so all three would be arithmetic dressed as risk management. The percentile outcomes stay and are built in stack 06 from the reader's own position.

**FR-29 (P2)** — *"Historical-analog panel: for a link, past instances and how prices moved around them, with an uncertainty band (an event study)."*
**Not built** *(coordinator's proposal; no prior decision).* It needs dated past instances **and** the price history around them; record 0010's grounding has a live prediction-market read and a public economic-data read and nothing historical. The base-rate work shows how thin the ground is: 93 searches across eighteen claims bought **five base rates**, three of them counts of *0 of 2*, *2 of 3* and *1 of 1*.

**FR-30 (P2)** — *"Pastcast self-test: run a chain on a resolved 2024–25 event with a date-frozen corpus and show the Brier score (the standard accuracy score for probability forecasts; lower is better), including when it is bad."* (The gloss of the Brier score is the requirement's own.)
**Not built.** It needs the evidence frozen as it stood before each event, which the pipeline cannot do — it searches the live web — and one resolved event is not a track record. One honest sentence about it goes on the *what I would do next* page.

**A consequence of cutting FR-30, stated here so nobody has to find it.** FR-8 forbids an ensemble — *"no claim is asked about twice"* — and names exactly one condition that would reopen it: *"if FR-30's pastcast shows stated ranges missing badly against the evaluation scorecard."* Cutting FR-30 throws away the only key to that lock. **So no ensemble is built in version one, and nothing can reopen it within version one.** Record 0015 stands unchanged; this record only removes its escape hatch, and says so rather than letting a later plan schedule an ensemble anyway.

### The one requirement shrunk rather than cut

**FR-31 (P0)** — *"Sessions (graph + branches + transcripts) persist to a single SQLite file (a one-file database, no server) and are addressable by URL. No accounts in v1."*

Today nothing is stored at all: the app keeps nothing between requests and no volume is declared (`ARCHITECTURE.md`, §6 Runtime, the *State* bullet). **Amended — Kent's decision, 2026-09-21** — to what we already write:

> **FR-31 (P0)** A finished generation is served back by its id from the same line-by-line file a recording is. One format, one loader, no database. Sessions are addressable by that id in the URL. No accounts in v1.

A kept run already writes that file and the replay path already reads it. Anti-pattern 12's closing clause, *"SQLite file on a volume"*, is amended with it: there is no database in version one at all.

### Cut in the same pass, touching no requirement

* **Undoing an edit (*Release*)** — in no requirement, no invariant and no clause of the brief; a change to the domain, the wire and the generated types wearing a button.
* **A probability slider** — every edit appends to an audit trail with no undo, so scrubbing writes thirty edits or opens a second, unaudited path.
* **Drafting a whole map in one streamed call** — a speed idea, and the demonstration runs from a recording.
* **Unrolling feedback arrows over time** — INV-6's checkable half stands and is tested; unrolling is asked for nowhere.
* **A fifth, price-valued kind of claim, and two-sided payoffs** — a position already carries the spot price, the volatility and the horizon, none of which a model can supply; and the losing leg *is* the stop.
* **Screenshot baselines and a wall-clock gate in the build** — two reliable sources of failures that mean nothing.

### Cut nowhere, and belonging elsewhere

So this record cannot be read as the complete list of everything absent. **The path product** (FR-11, INV-8) is replaced, not cut, by proposed record 0022. **The derived stop-loss** (INV-14, FR-22, FR-23 and the rest of FR-24) is reshaped by proposed record 0019 in stack 06. **The other three example inputs** (FR-3) are not cut: all four are recorded once at stack 05's shape freeze. **Kalshi**, the third venue named in FR-26, is **scheduled nowhere and cut nowhere** — it belongs to no record yet, and this one does not claim it.

### Consequences

* Good, because a reader can hold `PRODUCT_REQUIREMENTS.md` beside the product and account for every line — the checklist's *"every decision has an accepted record"* becomes true rather than aspirational — and work nobody has started moves onto the *what I would do next* page, where it can be described honestly instead of half-built.
* Bad, because two P0 and two P1 requirements are affected, and a reviewer who read the roadmap first will find less than it promised. The requirements themselves carry the amendment, so the promise and its retraction sit in one place.
* Bad, because cutting FR-30 leaves the product with no measurement of whether its numbers are any good — the honest sentence on the *what I would do next* page is the whole of the answer.
* Neutral, because nothing here is hard to revisit: each cut is a feature nobody has started.

### Confirmation

* Every requirement named above carries, in `PRODUCT_REQUIREMENTS.md`, a dated line pointing at this record — so the cut is found by a reader of the requirements, not only by a reader of the records.
* `test_splitting_a_claim_says_it_is_not_built_yet` (`backend/tests/unit/domain/test_patches.py:877`) — INV-10's named refusal, already green.
* Record 0015's own check, kept in force permanently and stated so it can pass: **no module, class, function or configuration field in `backend/` has a name containing *ensemble*, and no code path asks for one claim's numbers twice.** (A plain text search finds one hit today — a docstring in `engine/expand.py` saying there is no ensemble — which is the rule being obeyed, not broken.)
* The checklist's line *"every invariant has a named test — INV-10 by a named refusal, and this list says so"* names the test above.
* A review item at stack 07: the *what I would do next* page names the pastcast, the probes, `refine`, the analog panel and small multiples, each in one sentence, and claims none of them is nearly done.

## Open for Kent

**FR-17 and FR-29 are cut on this page for the first time**, with no earlier decision behind them. Both are P1/P2 and neither is scheduled anywhere.

* *Recommended:* accept both cuts as written. Cost: nothing is started, and the reasons above are the whole case.
* Alternative, FR-17: build the small multiples anyway. Cost: an undesigned ranking across three lists, plus a dashboard on a screen that has no spare room.
* Alternative, FR-29: keep it open rather than cut. Cost: a P2 that is scheduled nowhere still looks like a promise, which is what this record exists to stop.

## Pros and Cons of the Options

One line: **A** is chosen because the cuts share one reason and a reader should learn it once; **B** hides that reason across seven pages; **C** leaves a requirement that vanishes with nothing to trace it to. A's own cost is that superseding one line at a time is harder — a later record naming the requirement it revives is the answer.

## More Information

* **Kent's decision, 2026-09-21**, recorded as row R12 of the dated decisions note kept locally under `plans/notes/`: shrink FR-31 to the file we already write — a finished generation served back by its id from the same line-by-line file a recording is; one format, one loader, no database. *(The decisions note's words for his choice, not a transcript of his own.)*
* **What prompted this record**: the adversarial pass of 2026-09-21, finding S6 — six functional requirements cut with no record at all, against a checklist requiring one for every decision.
* **Related.** ADR-0015 (no ensemble; this record removes the one condition that would have reopened it) · ADR-0013 · ADR-0010 (why the analog panel has nothing to read) · ADR-0012 (the file FR-31 now uses) · proposed ADR-0016, 0017 and 0022 (which replace rather than cut) · 0018–0020, reserved for stack 06.
