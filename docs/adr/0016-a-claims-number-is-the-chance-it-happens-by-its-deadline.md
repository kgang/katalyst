---
# ADR-0016: A claim's number is the chance it happens by its deadline; whether is solved exactly, when is sampled
status: accepted
date: 2026-09-21
decision-makers: Kent Gang
consulted:
  - the stack-05 spike, both rounds, and the composition analysis, all 2026-09-21; scripts and logs kept locally under `plans/analysis/scripts/spike-05/`
  - the engine digest of 2026-09-21 and the adversarial pass over the design that followed it
  - ADR-0005, ADR-0014, ADR-0015
informed: agents in `backend/src/katalyst/domain` and `engine`, on the canvas, and on stacks 05–07
supersedes: none
superseded-by: none
spec-impact: spec/multiverse/propagation.md (rewritten), spec/multiverse/diff.md (the reweighting and range passages), spec/graph/belief.md, spec/workbench/inspector.md (one sentence), PRODUCT_REQUIREMENTS.md §12 and NFR-7
---

# ADR-0016: A claim's number is the chance it happens by its deadline; whether is solved exactly, when is sampled

> **In short.** A claim's number becomes **the chance it happens by its deadline**. Whether each claim happens is solved exactly; when it happens comes from one forward pass. Causes **add** to a claim's rate — each an independent route (Kent, R18): two causes that each alone take a claim from 10% to 40% give **59%** together, not 91%. Where two causes really work through one mechanism the repair is the map, not the arithmetic (R22).
>
> **On screen.** Every number on the Hormuz map changes once, in one reviewable diff. *This happened* on Brent moves what caused it, where today it leaves the cause at `.3000` and the hand-worked answer is `.4562`. Supposing the insurance premium or OPEC+ restraint moves both endings, where today they move by `0.0000`.
>
> **What it costs.** One world with its range on a twenty-claim map: **360 ms** at 2 000 versions, **538 ms** when three claims are held back by an arrow, **644 ms** with five states feeding `sustain` arrows. The limit is now **a target proportional to the map** (Kent, R24, superseding R19's fixed **600 ms**, itself a relaxation after the spike's 300 ms criterion failed twice) — **30 ms a claim** at 2 000 versions, derived from the 600 ms measured at twenty claims. Met on all-event maps, **not yet met with states**. On four-claim maps at 50 000 worlds, no number is off by more than **`.005`**. **Five to seven sessions.**
>
> **Also decided.** One sentence in the Inspector, on a branch where *This happened* is in force, says the answer rests on a seeded sample (Kent, R25); the ordinary screen says nothing.

## Context and Problem Statement

Every tile's sentence says *the chance this claim comes out true by its deadline*; the engine computes a likelihood read on one day. Three defects follow, all reproduced on `main` (`d44634a`) under a suite green at 100% coverage of the pure core and measured at `48eb562` — `backend/src/katalyst/domain`, where all three live, is byte-identical between the two (`git diff 48eb562 d44634a -- backend/src/katalyst/domain` prints nothing). One command re-runs them and saves its output beside it (`plans/analysis/scripts/adr-05/`, kept locally; re-run 2026-09-21 by this record's author).

| | What happens | Root cause |
|---|---|---|
| **1. Telling the map something happened never reaches what caused it** | On the two-claim map `verify_observe.py` builds, *This happened* on the effect leaves the cause at `.3000` against a hand-worked `.4562`, and *Suppose this is true* prints the same `.3000` — two verbs, one behaviour. Down a three-claim chain, `.3500` against `.4015` and `.4040` against `.5971`, a miss of `−.1931` (`recheck.py` §3) | Each claim's worked-out likelihood is kept and the coin flip thrown away (`propagation.py:1470`); for a causeless claim that likelihood is the same in every world, so discarding worlds cannot move it |
| **2. The tradeable endings are deaf to half their causes** | On Hormuz, *Suppose the war-risk insurance premium falls* moves *Brent settles below $68* `.3925 → .4759` and moves **both** endings by exactly `0.0000`; OPEC+ restraint moves Brent to `.2197`, both endings again `0.0000` (`verify_trigger_read_day.py`) | An arrow reads its source on the day the source's **earliest** incoming arrow lands — one integer doing two jobs (`propagation.py:842`, read at `:1463`). For Brent that is day 2; the premium's push lands day 7 and OPEC+'s day 5, *inside* Brent's own series, identical through day 6 and separating at day 7, `.492` against `.409` |
| **3. A claim nobody believes deletes the reader's own assertion** | Suppose the strait open on 1 October, then insert a claim the map gives one chance in a thousand with a `−0.01` arrow into it: the tile never reads *Supposed* on any day — day-states `withdrawn, withdrawn, pushed, …` from day zero, the number its own prior `.30` throughout (`recheck.py` §1) | A supposition ends on a calendar read off the map's shape (`propagation.py:940-948`), and the test for which arrows oppose it reads only the sign of the push (`:888-895`) — neither the opposing claim's likelihood nor the size of its push enters |

**And a range made of coin flips.** With every stated range frozen to a point, so the honest answer is zero width, two claims on a six-claim chain report `.0157` and `.0187`, and under *This happened* on a three-claim chain the middle claim reports `.1571` (`recheck.py` §2, §3). *(Record 0014 calls this the band; the vocabulary's word, used here, is the **range**.)*

## Decision Drivers

* **The traceability veto** (Kent): no state that cannot be traced to an input, a rule or a cited source. A number wrong by `.19` that cannot say so is that state.
* **INV-3, assert is not observe** — defect 1 makes the two verbs identical. **INV-4, locality** is kept, and ideally made easier to prove. **INV-7** wants two significant figures, and a second figure that moves with the dice is not one.
* **Kent's direction** (R1): an exact core with a sampler on top, the time model kept and made sound. **Stack 06 needs event days** to say whether a stop is touched before a target.

## Considered Options

Three terms, each once. A **rate** (the standard name is a *hazard*) is how likely a claim is to happen on a given day, given it has not happened yet; added up across its window it gives the chance it has happened by the end — a **first passage** probability. **Variable elimination** solves a sparse network of yes/no claims exactly: multiply the small tables and sum out one claim at a time. **Likelihood weighting** keeps every world, weighted by how well it matches the evidence, instead of discarding the inconsistent ones.

| | Measured |
|---|---|
| **A. Repair the defects inside today's engine** | Defect 2 has **no** repair: the right day is per world, so the settled day becomes random, and the grid, the day-states, retraction and the locality proof are all built on it being fixed. Defect 1's cheap repair kills the range — a yes/no flag's within-version **variance** is about `0.25` against an across-version `0.01`, so the noise correction clamps to zero and every range under *This happened* collapses to a point. Restoring it needs ~30× the worlds: one `propagate` on the fixture is **61.1 ms** at 2 000 versions × 8 worlds (`7.7 ms` at 250 × 8), so **about 2 s**. 1.5 sessions, `+120 / −60`, defect 3 still standing. *(Engine digest §3a; timings `recheck.py` §5 — a wall-clock timing is a band, and the three runs that day gave 65.7, 66.4 and 61.1 ms.)* |
| **B. One variable per claim whose value is *the day it first happened*, solved exactly over those days** — one of the two reviews' design | Generated 20-claim maps, ≤3 causes a claim, **at 12 slices**: **0.7–7.8 s** a range, largest table **4.8–62.7 million entries**; at 30 claims **58–119 s** or out of memory. At the 24 slices this design runs, B is worse still. *(Engine digest §0(2), `ve_cost.py`.)* |
| **C. The number becomes *the chance it happens by its deadline*; arrows bend a rate; *when* comes from one forward pass, *whether* is solved exactly over yes/no truths** | **The model is right and this design adopts it** — its calibration reproduces the elicited numbers to four places, and observing a claim gives exact Bayes upstream. The cost is what the engine digest got wrong: it sold the design on **0.5 ms** at 20 claims, and **that timed the elimination only** — `ve_cost.py` builds its tables from a random logistic with no time model (`truth_factor`, `:135-145`) before the clock starts inside `all_marginals` (`:205`). The table-building pass was never costed, and it is what the spike killed the design on. *(Spike round one, verdict 5; lines re-read on `main` by this record's author.)* |
| **D. Do nothing** | A thesis card resting on endings that do not move when half their causes do (defect 2) |

**C as first designed needed three amendments**, judged against B over 140 adversarially generated four-claim maps and 9 520 numbers at **24 slices with an arrival taken at the slice's last day** (adversarial pass M1; the spike's faster code reproduces the red team's enumerator to `0.000e+00`). *Suppose this is true* was right from the start — **0.2%** of 4 480 numbers over `.005`, worst `.0259` — and *This happened* was not: **6.6%** over, worst **`.2043`**. The arithmetic is exact, but the **table** is built from timing worked out before the evidence, and evidence moves *when* a cause happened as well as *whether*. It bites when the observed claim is itself a cause of another cause and the reach is through impulse arrows; a plain chain is exact. *(The full comparison table is in the owed-edits note.)*

## Decision Outcome

Chosen option: **C with three amendments the spike measured** — an additive rate, a weighted forward sample for *This happened*, and the middle-of-the-slice convention. The only option measured to honour both halves of Kent's direction inside his time target, and the only one that hands stack 06 event days it can trust.

**What a number means.** The chance the claim resolves YES by its own deadline — what the tile already says. Not a snapshot on one day, and **an event that has happened never un-happens**.

**The time model stays on the arrow.** `strength`, `lag`, `shape`, `half_life` keep their names and meanings and bend a **rate** rather than a likelihood read on one day. An impulse's whole area now counts, so the answer no longer depends on where a deadline falls against a half-life — record 0014's admitted wart; attacked with half-lives of one and two days landing four days before a deadline, the gaps were `.0000` to `.0001`.

**What the screen says about *This happened*** (Kent, R25). Nothing on the ordinary screen, and one sentence in the Inspector on a branch where *This happened* is in force: *"learning moves numbers upstream; this one is worked out by a seeded sample of 50 000 worlds, and on the four-claim maps the judge can check, no number was off by more than `.005`."* It claims only what was measured — four-claim maps, not maps of any size. `spec/workbench/inspector.md` carries the sentence, through the owed-edits note.

### How two causes combine — Kent's decision R18

**Causes add to a claim's rate: each is an independent route by which the effect may come about.** The chance none of them brings it about is the product of the chances that none severally does. A claim at 10% on its own, two causes each of which *alone* would take it to 40% by the same deadline, both happening on day one (`model_diff.py`, round two §4):

| | neither | one cause | **both** |
|---|---|---|---|
| **causes add — independent routes (chosen)** | `.100` | `.392` | **`.590`** |
| causes multiply — the first design | `.100` | `.392` | **`.910`** |

By hand: each independent cause removes a third of the ways the claim could fail, leaving `.40` of the failure — `.600`, against the table's `.590` because the cause sits at the middle of the first slice rather than at day zero. Multiplying instead multiplies the rate about fivefold per cause, twenty-five for two.

**Given up: causes never amplify one another.** *Hormuz reopens* and *OPEC+ restraint holds* may be worth more together than apart; here they are not. Nobody stated the amplification — one number per arrow, plus the claim's own, and neither is about two causes coinciding — so the old form put it there itself. Genuine reinforcement needs a third elicited number on the pair, which version one does not have.

**Where the assumption breaks: two arrows working through one mechanism.** Across every map the repository holds, 65 claims and 75 arrows:

| | |
|---|---|
| **The fact**, structural (`classify.py`, re-run 2026-09-21) | eight claims have two or more causes *pushing* them, and on **8 of 8** one of those causes is already a cause of another, so it reaches the effect two ways at once |
| **The judgement**, one analyst reading the arrows' own stated reasons | three *the same route* · one *needs both* · four *cannot tell*. **None cleanly independent** |
| **The size**, *if* a shortcut arrow's number includes what already flows along the drawn path (`compose.py` §2b) | `.003` to `.075`, median **`.049`**, on half of them. An upper estimate: these maps predate R6, which asks for *the chance if this cause happens and no other cause on this map does* — the direct effect alone. **Nobody has measured how much R6 alone repairs** |

**The remedy is the map, not the arithmetic** (Kent, R22). The shared mechanism is already a claim in all eight, so the repair is one fewer arrow, not one more rule: **no new field, no new arrow type, no engine code.** Two prompt paragraphs ride the shape freeze and amend record 0006, drafted in the owed-edits note — draw the arrow into the step the map already names, straight in only when it really is a second way; and write two things that only matter together as their own claim, switching on at the **latest** of its causes' days (exact to `3.220e-15`, `+5 ms` at 200 versions, `compose.py` §3). Deleting the shortcut arrows takes the twenty-claim map from `40.1` to `29.9 ms` at 200 versions and `321.0` to `228.2` at 2 000, width 4 → 3 (`cost.py`). Two Inspector lines say how causes were combined. **Declined:** one stated number per pair, **8.6× over budget** at 2 000 versions (`2 590.4 ms`); and a label on every multi-cause claim. **Not repaired: a shared cause nobody drew** — drawn ones are on the map as arrows and the exact solve holds the whole joint; one never drawn is a generation question.

### How it is worked out

***Whether*** is solved exactly by variable elimination over yes/no truths; ***when*** comes from **one forward pass** over **24 slices** of each claim's window, causes first, and because the rate adds that pass averages **one cause at a time** rather than over every combination of arrival days — the whole of the cost result below, and exact: one cause at a time equals averaging the full table to **`4.4e-16`** (`check.py`, round two §1). ***This happened*** is answered by a **weighted forward sample** with that exact solve as its **control variate** — the same world drawn twice with the same random numbers, so only the *difference* is sampled — seeded, one sample serving a whole range and both readers, the numbers on screen and the event days stack 06 reads. **An arrival inside a slice is taken at the slice's middle, not its end**, which at 24 slices moves the worst gap against a fine reference from `.0290` to **`.0027`**; and the grid is **24 slices, not 12**, though twelve halves the cost, because 12's grid error alone puts **2.50%** of *This happened* numbers over `.005` where 24 with the middle-day convention puts **0.00%** (`midpoint.log` §A, observe rows).

Two properties come free: **locality becomes a theorem**, a claim cut off from the evidence having a factor that sums to one, and **the width shares** (FR-21) become exact, one extra solve each. **Observations stay undated in version one:** `Observe` carries a target and a value and no date (`intervention.py:70-85`), and *this happened on day 5* would need the yes/no question re-cut per evidence day.

*The step-by-step arithmetic, with the rest of its proofs, is held for the `spec/multiverse/propagation.md` rewrite — which cannot be edited until stack 04 has landed — in §11 of the owed-edits note.*

### The kill criterion, and the time target it became

> *The spike's criterion: a candidate passes if it holds `.005` on 99% of the adversarial set **and** runs inside 300 ms on a 20-claim map (up to 3 causes a claim) for one world with its range.*

**It fired, twice, and this record does not claim 300 ms was met** — round one missed by **10×** at 200 versions and 12 slices, round two by **1.2×** at the 2 000 versions a range needs and at 24 slices, where like for like at 2 000 versions round one's own table reads 29 527 ms. Kent relaxed the criterion to a fixed **600 ms** at 2 000 versions (R19) with those all-event measurements in front of him; when the states re-run put the same map at **644 ms** he replaced the fixed number with a proportional target (**R24, superseding R19**), the decisions note recording his words: *"The recalculation speed limit can be proportional to the size of the map. What's important is to have good UX."*

| | accuracy, *This happened*, 4 480 numbers | one world with its range, 20 claims |
|---|---|---|
| **round one** — multiplicative rate, 12 slices | sample + control variate: 99.98% at 50 000 worlds, 100.00% at 200 000 | **3.0 s at 200 versions**; the binding cost was the shared forward pass at **2 879 ms**, not the sampler at 110 ms, and at 2 000 versions the same table reads **29 527 ms** |
| **round two** — additive rate, 24 slices, middle day: the tables alone | mean `.00103`, 99th pct `.0127`, worst `.0420`, **5.36% over `.005`** | 39 ms at 200 versions · 305 ms at 2 000 |
| **round two** — the sample + control variate, 50 000 worlds | mean `.00028`, 99th pct `.0020`, worst **`.0042`**, **0.00% over `.005`**; *no edit* worst `.0025`, *Suppose* worst `.0027` | **97 ms at 200 versions · 360 ms at 2 000**; with three claims held back by an arrow, 113 ms and **538 ms** |
| the same, with **five of the twenty claims states** feeding `sustain` arrows (record 0017) | unchanged — a state is more accurate under this rate, not less | 126 ms at 200 versions · **644 ms at 2 000** |

*(`candidates_add.py`, `timing20.py`, `timing_add.py`.)* The additive rate improves the tables markedly and still fails the 99% bar, **so the sampler is required**; its effective sample size is 96.9% of the worlds drawn on average, 42.9% at worst. **The other candidates:** the prior-timing tables are row two, which fails; re-cutting the yes/no variable per evidence day leaves 4.38% over `.005` — round one, multiplicative rate — and can be *worse* than doing nothing; the widening that does pass widens three claims of four, which is option **B** with one sink left over, at B's cost.

**The target, and where this design stands against it.** Recalculation gets **a target proportional to the map, not a gate and not a kill**, and what it protects is good UX: an edit should feel responsive. The reference point stays what was measured — 600 ms for one world with its range on a **twenty**-claim map at 2 000 versions — which is **30 ms a claim**, derived by dividing those two and not itself measured. The prototype meets it on all-event maps, at `538`–`568 ms` with three arrows that hold a claim back, and **not on the hard case**, at `644 ms` with five states feeding `sustain` arrows. Nothing is gated on the number.

**The speed-ups likely to succeed are built into the core pull request.** One is not:

| | Why it is likely to work | Measured |
|---|---|---|
| **the cheap path for a state that no `sustain` arrow leaves** | it skips work nobody reads — only a `sustain` child needs the on–off joint, and a state without one needs its holding curve alone | the joint is `236.8 ms` of the five states' `508.9 ms` forward pass at 2 000 versions (states round two) |
| **the two-pass solve** | a standard algorithm, one junction tree passed over twice, in place of one elimination pass per claim | about **80 ms** of solve at 2 000 versions, landing the all-event case near **295 ms** |
| **deleting the shortcut arrows** (R22) | already decided for the map's sake, and every arrow deleted helps | `321.0 → 228.2 ms` at 2 000 versions (`cost.py`) |
| *investigate, adopt only if measured safe:* **the on–off joint at a coarser grid than the on-process** | a `sustain` child is its only reader — but it trades accuracy, and how much is unmeasured | unmeasured |

**Everything beyond those is performance work after this first iteration is built**, not a condition on this record.

**A range needs 2 000 versions**, and the sample is a fixed cost rather than a per-version one because its correction is shared across a range. *(Both measurements — how far a band end wanders at 2 000 versions against 200, and what the shared correction costs under each rate — are written out for the `propagation.md` rewrite in the owed-edits note.)*

### What `World.series` now means, and what stays

Today `series` is a per-day likelihood allowed to **fall**, and the golden test pins it (`test_hormuz_golden.py:117-120`): `1.0` on day zero, between `.25` and `.45` on days one and three — the same value on both — and below `.10` on day four. **Under "the chance it has happened by day *t*" a series can only rise**, so that test cannot survive; the events-and-states reading of the same branch replaces it, record 0017's to write. What the field keeps, how a day between grid points is read, and what all this does to `DeltaRow.peak_delta`, `at_day` and the golden domino assertion are carried by the owed-edits note.

**A supposed claim's stored `p = 1.0` stays** — three live readers, not the one the first draft assumed: `diff.py:817-818`, `diff.py:460`, and the browser's `world/apiSource.ts:266` (browser line numbers here and below are `feat-04b-evals`, which is what `main` will hold). `Belief.p` allows no gap (`belief.py:39-45`), so removing it is a wire break.

**What this record amends:** **ADR-0005** and **ADR-0014**, neither superseded; **`lo` and `hi` keep their meaning**; **ADR-0015 is untouched**. The dated amendments appended to 0005 and 0014 in this same pull request say which sentences move, one by one.

### Consequences

* Good, because the number answers the sentence beside it, and because stack 06 gets event days it can trust: over 40 maps at **200 000 worlds** (`when_table.py`, round one §7) the weighted sample's day distributions are within `.0064` of exact at worst and its median arrival is at most **one slice** out, where drawing truths exactly and then days under the prior moves a median arrival by **four slices — ten days**, worst distribution gap `.2143`. *(Measured under the multiplicative rate and at 200 000 worlds; the design runs 50 000, and this was not re-run.)*
* Bad, because **every number on the map changes once**, hence a flip of its own; because causes no longer amplify one another, and no version-one map can say that two of them do; and because the clock was relaxed twice to fit the measurements rather than the measurements fitting the clock — 300 ms to a fixed 600 ms (R19), then to a proportional target (R24).
* Neutral, because the wire shapes keep their names and types: `series` and `moved_only_by_reweighting` change what they carry, and `Verdict.product` becomes always empty under record 0022.

### Still open, and where it can go wrong

**The hard case is over the target and the margin on the easy one is thin.** The same twenty-claim map at 2 000 versions:

| | Measured |
|---|---|
| three arrows that hold a claim back | **538 ms** — forward pass `404.5 ms`, solve `81.6 ms`, sample `52.2 ms`; about **568 ms** taking the slowest of each across those runs (`427.9`, `81.6`, `58.0`) |
| five states feeding `sustain` arrows | the forward pass goes `224.4 → 508.9 ms` and the total to **644 ms** (`cost2.py`, `cost2.log`); at 200 versions the same map is 126 ms. A `sustain` child reads the state's whole on–off interval, and that joint costs versions × slices **cubed** — `78.9 ms` per state against `3.6 ms` for the state's own holding curve |
| both at once | **nobody has measured it**, though three holding-back arrows alone added `180 ms` to the forward pass |

* **A lever nobody has decided on, offered here as an option:** one version — the numbers without their range — measures a forward pass of `5.4 ms` and a solve of `4.4 ms` with every arrow helping, and `6.0` and `4.5 ms` with three claims held back (`timing_add.log`), some 10 ms together. The number could therefore be shown at once and its range filled in when the 2 000 versions finish. Nothing is designed for this and it is not proposed.
* **The grid and the integration points carry an error of their own, larger than every tolerance here.** The design runs 24 slices with **eight integration points inside each**; against a dense integral of the rate that reproduces an arrow's stated chance to `1.81e-2` and the rate itself to `1.88e-2`, where 32 points brings both to about `5e-3` (`check.log`, round two §1). **Nobody has costed 32.** It does not invalidate the `.005` oracle — that oracle judges at the same grid, so the grid error cancels — which is why it is said here: `.005` is the distance to an enumerator on the same grid, not to the truth.
* **An arrow that holds a claim back is the one place the cost still multiplies**, forcing an enumeration over the days it might have arrived on: three cost **1.8×** the forward pass, eight `5.4×`, the generator's own ten **70×**, 15.9 s at 2 000 versions (`inhibitors.py`, `timing_add.py`). Real maps carry at most one per claim today, **but the freeze intends to add a *what would stop this step* sentence to the prompt, which will raise that count**, and nobody has measured the map it produces. The lever is a cap per claim, not proposed here because there is nothing yet to size it against. **They also saturate:** **30.0%** of the holding-back arrows in the adversarial set were clamped short of their stated chance (`candidates_add.py`).
* **Accuracy is measured on four-claim maps only** — the judge is not computable above that — while the cost numbers are from twenty-claim maps; the two sets never meet.

### Confirmation

**Two oracles, two tolerances, proving two different things.** An enumerator built from the core's own tables proves the summing and is blind to a wrong table, so one alone could not have caught the error above.

1. **`test_the_elimination_is_exact`** — tolerance `1e-9`, over the core's **own** yes/no tables, summing the joint by hand. Proves the elimination, the supposition surgery and the conditioning. Blind to timing.
2. **`test_the_tables_agree_with_integrating_over_time`** — forbidden the core's tables, built from the arrow parameters alone, enumerating the full joint of event times on maps of four claims or fewer. Tolerance **`.005` on each of the three questions, with the sample size named**: the worsts at 50 000 worlds are the kill-criterion table's third row, and at 200 000 worlds under the same additive rate they are `.0012` no edit, `.0021` *Suppose this is true*, `.0017` *This happened* (`candidates_add.log`). **Two conditions:** the enumerator runs at the **same number of slices and the same within-slice convention** as the core — 24 slices judged by 60 with a different convention differs by `.0290` on its own, swallowing the tolerance — and **the sample is seeded**, so the test is deterministic.

**The locality oracle, restated and stricter:** *cut off from the evidence ⇒ bit for bit* — byte-identical, not merely close. `test_band_is_not_sampling_noise` survives and tightens to zero width exactly. `test_an_observation_moves_a_cause_even_when_no_arrow_pushes` (`test_propagation.py:544`) is **reversed into an assertion of invariance**: record 0014's 2026-09-17 amendment decided deliberately that an observation moves a causeless claim through the version weights, and this record removes the mechanism.

**No test gates on the clock.** The core pull request records its own timings on one benchmark — twenty claims, up to three causes each, five states feeding `sustain` arrows, three arrows that hold a claim back, 2 000 versions, 24 slices — and reads them against the per-claim target, which is a target and not a gate (R24).

### How it lands

| Step | Contents | `main` after |
|---|---|---|
| **1** | The two oracles and their enumerators, the second committed under `backend/tests/`. Failing cases marked strictly expected-to-fail, by name. Reverse the invariance test | Green. Two tests documenting two defects |
| **2** | The new core beside the old, behind a flag, **default unchanged**, with the two likely speed-ups built in and the benchmark timed and recorded. Both oracles run against both | Green. **Every screen still shows today's numbers** |
| **3** | **The flip, alone.** Default changes; Hormuz re-derived; the generated numbers file regenerated, **its diff the complete reviewable statement of which numbers moved**. The two nested loops, the noise correction, the version weights and `moved_only_by_reweighting` go; `diff.py` moves over; the browser readers listed under *Honest cost* are corrected | Green. Every number changes **once** |
| **4** | Separately: record 0022's three quantities, and record 0017's events and states | Green |

The generated numbers file must exist *before* step 3, or the flip also carries a sweep of several hundred numbers across the chapters and nobody can review it.

### Honest cost

**Five to seven sessions for this record's work** (adversarial pass M5; a session is about three focused hours); record 0017's events and states add about **1.3** (engine digest §5.3), so **six to nine together**; the whole of stack 05 about **nine and a half** (S4) — which also notes this repository has never kept session accounts, so every figure is a first estimate. For calibration, `d9c853e` (#38) fixed **one** defect class and cost **1 335 insertions across 12 files**.

The first estimate of three missed four things, verified on `main` unless marked: **`diff.py`**, 1 459 lines, where the version weights, the reweighting flag, the range import and two more readers die or change; **the browser**, budgeted at zero, where three rendering readers of the reweighting flag, its mapper and its *"worlds under each"* sentence are corrected, and the retraction badge's height is baked into the tile's geometry; **34 of `test_propagation.py`'s 46** tests (46 confirmed by count), plus the locality oracle, rewritten and stricter; and **every decimal in the two multiverse chapters** — on `feat-04b-evals`, 259 in `propagation.md` and 189 in `diff.md`.

*The file-and-line inventory behind those four is held for the flip in §11 of the owed-edits note.*

## Open for Kent

**Nothing.** The two questions this record carried are decided: **R24** made the time limit a target proportional to the map rather than a gate, and **R25** put one sentence in the Inspector and nothing on the ordinary screen.

## More Information

* **Accepted by Kent on 2026-09-21**, decisions note row **R32**, in his words: *“All these ADRs written are accepted!”*
* **Kent's decisions, 2026-09-21**, in the dated decisions note kept locally under `plans/notes/`: **R1**, an exact core with a sampler on top and the time model kept and made sound, behind a spike with a kill criterion; **R18**, causes add as independent routes; **R19**, a 600 ms budget at 2 000 versions, **superseded by R24**, a target proportional to the map; **R22**, the remedy for causes that share a route is the map; **R25**, one Inspector sentence about the sample. *(Those are the decisions note's words for his choices, except where a sentence is quoted and attributed to it.)*
* **The evidence.** The stack-05 spike's two rounds, the composition analysis, and the engine digest and adversarial pass that preceded them, all 2026-09-21, kept locally under `plans/analysis/` with their scripts. Every measurement here is quoted from one of those reports with its script named, or was re-run on 2026-09-21 by this record's author.
* **Related.** ADR-0005 and ADR-0014 (amended, not superseded) · ADR-0015 (intact) · ADR-0017, ADR-0021, ADR-0022. Chapters rewritten: `spec/multiverse/propagation.md`, `spec/multiverse/diff.md`.

## Amendment (2026-09-22) — what the core's pull request built, and where it departed from this record

**A record is a journal. Nothing above is rewritten.** This is what the core's own pull request — step 2 of *How it lands* — did differently from what is written above, and what it corrects, each line with the evidence that made it necessary. Six departures and two corrections. Every measurement named here is quoted from the file and line that carries it.

### The departures — decisions note row R40, taken by the coordinator under Kent's instruction to cut scope

Kent's instruction that evening, his words as the decisions note records them: *"Cut scope if there's significant complexity and you can justify that the payoff isn't impactful relative to its effort."* The three below were taken under it and were **not** put to him; each says how to overturn it.

* **The two-pass solve is cut, and its seam is kept.** The row at *The kill criterion* above lists it among *"the speed-ups likely to succeed are built into the core pull request"*. It is not built. What it was worth is this record's own arithmetic on one measured line: `timing_add.log:60` (the *with the exponentials taken once up front* block — twenty claims, 2 000 versions, 24 slices, every arrow helping, 50 000 worlds) reads a forward pass of `224.4 ms`, a solve of `80.4 ms` and a sample of `54.9 ms`, a whole world of `359.7 ms`; the table above puts the two-pass solve at *"about 80 ms of solve … landing the all-event case near 295 ms"*, so the saving claimed is about **65 ms of 359.7**. That is a fifth of one world, on the case that already meets its target, against a junction tree written from scratch inside a pull request that had four other writers in it. What is kept is the **seam**: `all_marginals` answers every claim in one call, so a second pass can be put behind it later without a caller changing. **To overturn:** say so; it is a self-contained piece of `domain/solving.py`. The other speed-up this record names, the cheap path for a state no `sustain` arrow leaves, **is** built (`domain/states.py`'s `needs_the_joint`, with `test_states.py` asserting on four shapes of map which way it goes).
* **The exact per-prior share of a claim's range is cut.** *Section C keeps its quantity and changes its method* in record 0014's second amendment reads it as one extra exact solve per stated range. Costed at twenty extra solves a world — `20 × 80.4 ms`, about **1.6 s** — for a number no route reads until stack 06. `World.range_shares` keeps today's meaning and today's six lines, read off the **exact** per-version answers instead of an eight-world sampled average. **To overturn:** say so; it is the same six lines run once per frozen range.
* **The oracles landed as the core's own first commit rather than as a pull request of their own.** *How it lands* step 1 is a landing; it became commit one of step 2 (`24fd771`, the two enumerators and the three defect tests marked strictly expected-to-fail; the marks come off in the same pull request, which is what step 1 and step 2 were separated to guarantee and is guaranteed here by construction instead). **Why:** a pull request that lands failing-by-design tests on `main` and nothing that fixes them leaves `main` in a state nobody can read, and the stack is two deep (R13). **To overturn:** say so before the branch lands.

### Record 0017 is split between the flip and the freeze — decisions note row R39, the coordinator's call

*How it lands* step 4 puts record 0017's events and states after the flip. **That leaves the brief's central story broken on `main` in between:** the flip deletes automatic retraction, and until `persistence` exists on a claim, *"Hormuz opens, then Iran is struck"* moves nothing at all. So record 0017 is split at the model boundary — `persistence` on the domain model, the state arithmetic and the fixture's state claim ride **with the flip**; the prompt, the validity rule, the `event → step` rename and the re-recording ride **with the freeze**. Between the two, the one place that mints a claim from a recorded proposal states `persistence = event` out loud, with a dated comment naming the freeze.

**This is the coordinator's call under Kent's delegation of 2026-09-22, not Kent's own decision**, and it is written down here so that reading the record never leaves a reader thinking he chose it. **To overturn:** say so; the flip and the state arithmetic then land as one tight train instead.

### Each claim is cut into 24 slices over its OWN window, not one window per map

*How it is worked out* says twenty-four slices and does not say twenty-four slices **of what**. The core cuts every claim from **its own resolve-by day**, so two claims on one map have different slice boundaries.

**Why, and it is not a nicety.** Cutting every claim from the map's longest window makes every boundary on the map depend on the map's latest deadline — so inserting one claim judged six months out moves every slice boundary everywhere, and claims the insertion cannot reach move with them. That is the locality promise, broken by the grid rather than by the arithmetic. This repository has been bitten by exactly that shape of defect once already: thinning the days a series was drawn at re-timed a claim in a wholly separate piece of the map by **`.096`** when an inserted claim stretched a window from 31 days to 365. Locality is now a theorem of the solve *and* of the grid, and `test_a_longer_window_moves_nothing_it_cannot_reach` is what says so.

### Correction — the cheap path's figure above claims a saving the measurement had already taken

The table at *The kill criterion* gives the cheap path for a state no `sustain` arrow leaves as worth *"the joint is `236.8 ms` of the five states' `508.9 ms` forward pass at 2 000 versions"*. **The two numbers are not of the same five states.** On that map only **three** of the five have a `sustain` arrow leaving them (`cost2.log:15`), and the joint was timed for those three alone: `78.93 ms` each, `236.79` for three, under a column headed `x5 states` (`cost2.log:28`). The `508.92 ms` total on the line below it (`cost2.log:32`) therefore **already** skips the joint for the two states nothing reads the stretch of. The cheap path takes nothing further out of that number; what it does is make the code behave the way that measurement already assumed.

**The cheap path is built anyway, and no measured saving is claimed for it.** It is the right shape — only a `sustain` child reads a state's whole on–off interval, and that joint costs versions times slices **cubed** — and a source check asserts the joint is not built when nothing reads it. What is now written down is that nobody has measured what it saves on a map where a state without a `sustain` child would otherwise have paid.

### Correction — *Still open*, the bullet on arrows that hold a claim back

That bullet says the cost multiplies because such an arrow forces *"an enumeration over the days it might have arrived on"*. **The enumeration is over the different pushes those days produce, which is fewer.** A cause judged long after the claim it pushes has arrival slices that begin after that claim's deadline, and an arrow whose cause arrives then pushes nothing at all over the window — the same array of noughts, again and again. Kept once between them, the two arrows holding Brent back on the committed strike branch go from **625 combinations to 125** (`plans/analysis/scripts/stack-05-core/perf-2/where_the_ten_seconds_go.after.log:31`, the `B` row, columns `combos` and `kept`), and the largest working array on that branch from **750 million numbers to 60 million** (`where_the_ten_seconds_go.log:42` against `where_the_ten_seconds_go.after.log:45`).

Everything else the bullet says stands: the count still multiplies, the freeze's *what would stop this step* sentence would have raised it, and R40 cut that sentence for this reason among others.

### The benchmark this record asks for, and where it is written down

*Confirmation* requires the core's pull request to record its own timings on one benchmark and read them against the per-claim target, with no test gating on the clock. `backend/benchmarks/by_deadline.py` is that benchmark and nothing gates on it. The readings are in **`docs/measurements.md`**, two dated entries of 2026-09-22 — *the by-deadline engine, first timings* and *the by-deadline engine after the second speed round*, the second superseding the first's figures and rewriting none of its words. Read against the thirty-milliseconds-a-claim target, at 2 000 versions and 24 slices:

| the twenty-claim map | measured | against its 600 ms |
|---|---|---|
| no states, nothing holding a claim back | **451.6 ms** | inside |
| no states, three arrows holding a claim back | **787.5 ms** | 1.3× over, from 1.6× |
| five states feeding `sustain` arrows, three arrows holding a claim back | **3 294.9 ms** | 5.5× over, from 9.9× |

The committed worked example is **71.1 ms** for the base map and **0.72 s** for the strike branch, both inside their own targets, where the strike branch did not finish at 2 000 versions at all when this record was written. **The five-state case is the one thing still badly over**, and where its time goes is measured rather than guessed: of a 3.05 s profiled forward pass, `1.507 s` is inside `numpy`'s own `einsum` and `1.088 s` in the helping arrows' averaging (`perf-2/what_is_left_on_the_states_map.log:50-51`). Under R24 that is performance work after the first iteration, not a gate on the flip.

### Correction — how many tests of `test_propagation.py` the flip touches

*Honest cost* says *"**34 of `test_propagation.py`'s 46** tests (46 confirmed by count)"*. Counted again on `main` at the day the core landed: the file holds **51** tests at module level and none nested (`grep -c '^def test_'`). The share the flip rewrites was never re-counted against 51 and is not restated here; what is corrected is the denominator.

## Amendment (2026-09-22) — Kent cuts the versions and the range; the engine half rides the flip

**Decisions note row R48**, his words as it records them: *"The 2,000 runs thing is confusing. Can we cut that from the scope of this project completely for the sake of defending its design and also potentially to make the speed of the real time map construction a lot snappier and quicker?"* He was told first that the engine pass is a tenth of a millisecond and the model calls are the time, so the cut buys **simplicity, not speed**, and chose it with that in front of him. **Cut from the engine too: one likelihood per claim, computed once, and no range anywhere, ever** — not on a tile, not in the panel, not on the change list (*same direction 95%* is a share of versions and goes with them), not in a footer sentence, not in a hover note. It **reverses record 0005's and record 0014's range** — *how sure we are of the numbers we put in* — and the product requirements' *two significant figures with an interval*.

**What this does to the passages above.** Everything this record says about the range is superseded: *a range needs 2 000 versions*, the band as the tenth and ninetieth percentiles across versions, `World.range_shares`, and every timing here measured at 2 000 versions. The measurements stay as measurements — they say what a run did on its day — but the budget they were read against is about to be a budget for a thing that no longer exists.

**Nothing of it is in the core's own pull request, on purpose.** The core keeps its version axis exactly as built. From the flip it runs at **length one**, which needs no surgery: the version axis is an array axis and a version enters as a scalar multiplying arrays built once, so one version is the same arithmetic with a shorter first dimension. The whole oracle comparison already runs that way — one version whose stated range is a point — so the agreement to `.005` and the elimination's `1e-9` are measured **at length one** and nothing rests on two thousand. Ripping the axis out now would rewrite five modules and both enumerators inside a pull request that is closing, and would have to be reviewed against nothing.

**The removal lands once, at the flip**, with the rest of what changes on the same day: the range on the wire, `range_shares`, the version weights, the provenance-derived spread, the browser's readers, and the chapters. Until then the wire may still carry `lo` and `hi` and the browser ignores them, which is the screen half of R48 and is landing separately in the UX round.

**Record 0028 carries the reversal of records 0005 and 0014.** The dated amendments this record appended to those two say the band's *meaning* survives; under R48 it does not survive at all, and that is a decision of its own rather than a line at the foot of this one.
