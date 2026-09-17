---
# ADR-0015: A claim starts with the range the model stated, labelled as stated — not yet an ensemble
status: accepted
date: 2026-09-17
decision-makers: Kent Gang
consulted: ADR-0014 section G (the question it deferred) and the research listed under its *More Information*; a read-only Opus design review of stack 04 on 2026-09-17, whose own recommendation this decision overturns; `spec/multiverse/diff.md` anti-pattern 4; `spec/vocabulary.md` (*agreement*, and *words we do not use*)
informed: agents working in `backend/src/katalyst/engine`, in `evals/`, and on the stack that builds FR-30's pastcast self-test
supersedes: none
superseded-by: none
spec-impact: spec/generation/proposals.md (where a claim's starting number and range come from), spec/generation/evaluation.md (the scorecard is the baseline any later ensemble is measured against), PRODUCT_REQUIREMENTS.md FR-8 and §13, ARCHITECTURE.md §10
---

# ADR-0015: A claim starts with the range the model stated, labelled as stated — not yet an ensemble

## Context and Problem Statement

Every claim on a generated map arrives with three numbers from the model: a likelihood and the two ends of a range around it — `.35 (.20–.49)`. Record 0014 settled what those numbers **mean**: the two ends are the 10th and 90th percentiles of the likelihood itself, so the range says *how sure we are of the number*, not *how much the world can move*. It did not settle where the three numbers **come from**, and said so in its section G: *"Whether a claim's starting range should come from measured disagreement across several independent model runs. Kent: decide in stack 04."*

The pull of the question is real. Record 0014 collected published evidence, as input rather than as a decision, that ranges a language model states about itself are reliably too narrow. The alternative on offer is to ask the same question several times and read the spread of the answers as the range — a measurement instead of a self-report, which is the rule this repository applies everywhere else. `PRODUCT_REQUIREMENTS.md` FR-8 had already written that alternative down as a requirement, in the strongest possible form: *N* independent generations of the whole map, reconciled into one.

So: **where does a claim's starting number and range come from — what the model stated once, or something measured across several runs? And if measured, measured over what — one claim, or a whole map?**

## Decision Drivers

* **One field, one meaning.** `lo` and `hi` are defined by record 0014 as percentiles of the likelihood. Anything else put in them makes the chip on screen mean two things at once.
* **The word *agreement* is already spoken for.** `spec/vocabulary.md` defines it as the share of versions of the map in which a change moved the same way — computed, never self-reported — and the delta rail's column is headed *same direction* on screen precisely so the word stays free for a run-to-run number the day one exists.
* **The traceability veto (D5-ii)** — no state that cannot be traced to an input, a rule or a cited source. A number that came out of three answers must be able to say which three, and whether they were independent.
* **Never re-prompt for a whole map** (`PRODUCT_REQUIREMENTS.md` §10, anti-pattern 2; `spec/multiverse/diff.md` anti-pattern 4).
* **Cost and waiting.** Record 0006 estimates a thirty-claim map at about forty model calls. Whatever multiplies that multiplies both the bill and the time the reader spends looking at an unfinished map — and FR-5 and UX-8 make the map growing *the loading state itself*, with no spinner anywhere.
* **Measure before you build.** The evaluation harness does not exist yet. Nothing here can be shown to be an improvement until there is a scorecard to compare against.

## Considered Options

* **E1. Ship the range the model stated, labelled as stated.** A model belief's likelihood and both range ends are what the proposal said, stamped `owner="model"` by us, and shown under record 0014's existing label — *model interval, uncalibrated*.
* **E2. An ensemble only when a recording is made.** Live runs use the stated range; `make record-demo` asks several times and stores a measured range, so the four committed recordings look better than the live product.
* **E3. An ensemble on every run.** For each claim, ask more than once — say three times — and take the middle answer as the point and the spread of the answers as the range, or the wider of that and the stated range.
* **E4. Whole-map reconciliation, as FR-8 literally says.** Run *N* independent generations of the whole map, match the claims of one against the claims of another, and reconcile them into a single map whose arrows carry how far the runs disagreed.

## Decision Outcome

Chosen option: **"E1 — the range the model stated, labelled as stated, and *not yet* an ensemble"**, because it is the only option that keeps one meaning in one field, keeps the word *agreement* honest, spends nothing it cannot yet show a return on, and leaves the door open in the one place where the return could actually be measured.

### What ships

A model belief's likelihood and its two range ends are **what the proposal stated**. Nothing rewrites them and nothing widens them. The label does not change either: record 0014's chip already reads *model interval, uncalibrated · how sure we are of `.35` — not how much the world can move*, and the two chip sentences settled on 2026-09-17 — one for a number a world has worked through the map, one for a number that has only been stated — already cover both cases (`spec/workbench/tiles-ports-wires.md`). There is **nothing new on screen, nothing new in code, and nothing extra in a recording**.

### Why not an ensemble now — four reasons anyone can check

1. **It would put a second meaning in a field that already has one.** Record 0014 defines `lo` and `hi` as the 10th and 90th percentiles of the likelihood itself — *if we somehow learned the true likelihoods, about eight times in ten the answer would land in here*. The spread of several answers to the same question measures a different thing: how much one model wobbles when asked twice. Both are interesting. They are not the same quantity, and one field must not carry two meanings.
2. **Re-asks are not independent runs, so calling their spread *agreement* would over-claim.** Every call in this pipeline shares one cached system prompt and one map-so-far (record 0006). Answers drawn from the same prompt and the same partial map are correlated by construction. `spec/vocabulary.md` reserves *agreement* for a number computed from things that were worked out independently; a measurement taken this way would not be one.
3. **It multiplies the bill and makes the reader wait.** Two further generations of a thirty-claim map is about eighty more calls, at record 0006's estimate of about forty calls per map; asking three times for each of thirty claims is ninety asks. The 2026-09-17 design review put the cost of an ensemble at **four to five times the stack's model spend — an estimate made in that review, not a measurement**. And a claim cannot be accepted onto the map until its numbers are settled, so every extra ask slows the map's own growth by that much — the opposite of what FR-5 and UX-8 ask for, which is a map that grows as fast as the model can propose.
4. **A "trimmed mean" of three answers is just the middle one.** Trim the highest and the lowest of three and one number is left. The phrase makes a median sound like a statistical procedure. If this is ever measured, the word to use is **median**.

### Never reconcile whole maps

Option E4 is refused outright, and not only for this stack. The warrant is one level up, in `spec/multiverse/diff.md` anti-pattern 4, quoted as it stands there:

> **4. Do not infer a difference by matching two maps.** *Because* a difference reconstructed after the fact cannot tell "the user supposed this" from "the model happened to number it differently this run", cannot recover the order the edits were made in, and turns a free, exact answer into a guess — the same reason `branches-and-worlds.md` refuses to derive a branch by diffing two maps. **Do** build both worlds from one base map, one seed and two branches, and read the difference off the two results.

Matching one generated map against another is that anti-pattern with nothing held fixed at all: not the base map, not the claims, not their wording, not their identifiers. Whatever such a comparison reported, no one could say how much of it was the world and how much was the model numbering things differently this run. **FR-8 is amended in the same pull request as this record** to say what ships instead, and the standing open question in `PRODUCT_REQUIREMENTS.md` §13 moves to the answered list with a sentence saying **the question changed** — not that it was answered.

### The known cost of this decision, said plainly

**Stated ranges run narrow.** Record 0014 records the evidence under its *More Information*, as input to this decision: **FermiEval (2025) — a nominal 90 per cent range covered the truth 28 per cent of the time**; QuantSightBench (2026) reproduced it; Paleka and colleagues (ICLR 2025) found stated ranges incoherent under rewording. Quote that figure with that source wherever it is repeated.

So the ranges this decision ships are, on published evidence, too narrow, and nothing here fixes that. What the product does instead is refuse to pretend otherwise: the chip says **uncalibrated**, in those words, for exactly this reason, and the Inspector says in a full sentence that nobody has checked whether the eight-in-ten holds up, because no claim on any map has resolved yet. A narrow range that says it is unchecked is honest. A wider range manufactured from three correlated answers, wearing the word *agreement*, would not be.

### What would reopen this

One route, and it runs through a measurement rather than through an argument:

1. **The eval scorecard is the baseline.** `spec/generation/evaluation.md` names the scorecard's fields in this same stack, so a later change has something to be compared against rather than being compared against a memory.
2. **The pastcast is the test.** FR-30 runs a chain on an event that has already resolved, with a date-frozen corpus, and reports the standard accuracy score for probability forecasts *including when it is bad*. That is the first moment this repository can see whether a stated range actually misses.
3. **If it misses badly, measure whether re-asking helps** — whether the **median** of several answers is a better point, and whether their spread widens the range *toward the truth* rather than merely widening it. Then decide, with numbers.

Until that day the word **agreement** stays free on screen: the delta rail's column is headed *same direction*, and the field behind it stays `agreement`, so nothing has to be renamed if a run-to-run number is ever earned.

### What it means for the code

* **No `engine/ensemble.py`**, and no code path that asks for a claim's numbers more than once.
* **No new field** on a belief, a link, a proposal or a world. In particular there is no `agreement` anywhere but the diff, and no second range beside the stated one.
* **Nothing extra in a recording.** A recording carries one answer per claim, so a replayed map is the map a live run would have drawn.
* **Nothing new on screen.** No card, no badge and no sentence saying *runs agree*.

### Consequences

* Good, because the number on a chip is the number the model gave, and the label says so — one hop from the screen to the source, which is what the traceability veto asks for.
* Good, because `lo` and `hi` keep exactly the meaning record 0014 gave them, so the two-loop engine, the width shares and the diff all keep reading the same quantity.
* Good, because the word *agreement* keeps one definition, and the day a run-to-run number is earned it can take the word without anything having to be renamed or explained away.
* Good, because the stack's money goes to building the pipeline, the stream, replay and the evals rather than to four or five times the calls for an improvement nobody can yet measure.
* Bad, because the ranges on a fresh map are, on published evidence, too narrow — FermiEval's nominal 90 per cent covering 28 per cent of outcomes — and this decision ships them anyway, mitigated only by saying *uncalibrated* out loud.
* Bad, because FR-8 as originally written is not built in version 1, and a reader who knew the old wording must be told the question changed; §13 says so rather than quietly dropping it.
* Neutral, because nothing here is hard to revisit: adding a second ask later touches the pipeline and one chapter, and adds no field to the domain.

### Confirmation

* `test_the_word_agreement_means_same_direction_and_nothing_else` — a test that reads our own source, in the manner of the existing `test_beliefs_never_merged`: the only `agreement` in `backend/` is the diff's same-direction share.
* `grep -rn "ensemble" backend/src` finds nothing.
* Review item: a proposal is asked for once per claim; no recording under `backend/recordings/` carries two answers for one claim.
* Review item: no screen and no prompt contains the words *runs agree*.
* `spec/generation/evaluation.md` names the scorecard's fields, so the baseline this decision would be reopened against exists before anything is compared to it.

## Pros and Cons of the Options

### E1. The range the model stated, labelled as stated (chosen)

* Good, because one field keeps one meaning, and the label already on screen is the true one.
* Good, because it costs nothing beyond the calls the map needs anyway, and no chip waits on a second answer.
* Bad, because the range is probably too narrow and the product can only say so, not fix it.

### E2. An ensemble only when a recording is made

* Good, because the cost lands once, on a command only the coordinator runs, rather than on every live generation.
* Bad, because the recordings are what a keyless reviewer sees, so the demonstrated product would be better than the shipped one. Record 0012's whole warrant is that a replay is the real thing played back; a replay built from numbers the live path never computes would break that.
* Bad, because it still puts a second meaning in `lo` and `hi`, only less often — which is worse, because now the same field means different things in different runs.

### E3. An ensemble on every run

* Good, because the range would be measured rather than self-reported, which is the rule everywhere else here.
* Good, because the published evidence says it widens ranges in the right direction.
* Bad, because the answers are not independent — one cached prompt, one shared map — so the measurement is of the model's wobble, not of disagreement between runs.
* Bad, because it multiplies the model spend four to five times (the 2026-09-17 design review's estimate) and slows the map's growth by every extra ask, since a claim is not accepted until its numbers are settled.
* Bad, because with three answers the "trimmed mean" is the middle answer, and the phrase hides that.

### E4. Whole-map reconciliation, as FR-8 literally says

* Good, because it is the strongest form of the idea: run the whole thing several times and keep what survives.
* Bad, because it is `spec/multiverse/diff.md` anti-pattern 4 with nothing held fixed — no shared base map, no shared identifiers, no shared wording — so no part of the result can be traced to a cause.
* Bad, because matching claims between maps needs a rule for when two sentences are the same claim, and that rule is itself a model call nobody can check.
* Bad, because it is the most expensive option by a wide margin and the least able to explain itself.

## More Information

* **Kent's decision, 2026-09-17**, taken through the question tool after a read-only Opus design review of the stack-04 plan. The review recommended an ensemble; the measurements above — the meaning of `lo` and `hi`, the shared prompt, the spend — were what changed the answer. Recorded in `plans/STATUS.md` and in the stack-04 decisions note of that date.
* **ADR-0014**, section G, which deferred this question to this stack, and its *More Information*, which holds the evidence quoted here with its sources: FermiEval (2025), QuantSightBench (2026), Paleka et al. (ICLR 2025), Farquhar et al. (*Nature*, 2024), Halawi (2024), the AIA Forecaster (2025).
* **ADR-0006** — one proposal per call, the cached system prompt, the receipt. Its *Consequences* note that an ensemble pass "becomes an extra stage over the same call shape"; that remains true as a description of the shape, and this record decides that the stage is not built in version 1.
* **ADR-0003** — the model proposes and our code disposes, which is why a stated number is stamped `owner="model"` by us and never merged with a user's or a market's.
* **ADR-0012** — a recording is the real stream played back, which is the argument against option E2.
* `spec/multiverse/diff.md` anti-pattern 4 (quoted above) · `spec/vocabulary.md` (*agreement*; *words we do not use*) · `spec/graph/belief.md` (what the range means and the uncalibrated wording) · `PRODUCT_REQUIREMENTS.md` FR-8, FR-30, §10 anti-pattern 2, §13.
