---
# ADR-0016: A claim's number is the chance it happens by its deadline; whether is solved exactly, when is sampled
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted:
  - the stack-05 spike, both rounds, and the composition analysis, all 2026-09-21; scripts and logs kept locally under `plans/analysis/scripts/spike-05/`
  - the engine digest of 2026-09-21 and the adversarial pass over the design that followed it
  - ADR-0005, ADR-0014, ADR-0015
informed: agents in `backend/src/katalyst/domain` and `engine`, on the canvas, and on stacks 05–07
supersedes: none
superseded-by: none
spec-impact: spec/multiverse/propagation.md (rewritten), spec/multiverse/diff.md (the reweighting and range passages), spec/graph/belief.md, PRODUCT_REQUIREMENTS.md §12
---

# ADR-0016: A claim's number is the chance it happens by its deadline; whether is solved exactly, when is sampled

> **`proposed`.** Both rounds of the stack-05 spike and the composition analysis have reported and their numbers are in.

> **In short.** A claim's number becomes **the chance it happens by its deadline**. Whether each claim happens is solved exactly; when it happens comes from one forward pass. Causes **add** to a claim's rate — each an independent route (Kent, R18): two causes that each alone take a claim from 10% to 40% give **59%** together, not 91%. Where two causes really work through one mechanism the repair is the map, not the arithmetic (R22).
>
> **On screen.** Every number on the Hormuz map changes once, in one reviewable diff. *This happened* on Brent moves what caused it, where today it leaves the cause at `.3000` and the hand-worked answer is `.4562`. Supposing the insurance premium or OPEC+ restraint moves both endings, where today they move by `0.0000`.
>
> **What it costs.** One world with its range on a twenty-claim map: **360 ms** at 2 000 versions, **538 ms** when three claims are held back by an arrow — inside the **600 ms** Kent named (R19) after the spike's 300 ms criterion failed twice, but only on all-event maps. With five states feeding `sustain` arrows the same map measures **644 ms**, over it. On four-claim maps at 50 000 worlds, no number is off by more than **`.005`**. **Five to seven sessions.**
>
> **Open for Kent.** Whether the budget is a gate on the flip rather than on this record — and whether the screen says that *This happened* rests on a seeded sample.

## Context and Problem Statement

Every tile carries a number and the sentence beside it says *the chance this claim comes out true by its deadline*. The engine computes something else — a likelihood read on one day — and three defects follow. All three reproduce on `main` (`d44634a`) under a suite green at 100% coverage of the pure core. They were measured at `48eb562`; `backend/src/katalyst/domain`, where all three live, is byte-identical between the two (`git diff 48eb562 d44634a -- backend/src/katalyst/domain` prints nothing).

**What does a number on a tile mean, and what arithmetic works it out?** Re-run 2026-09-21 by this record's author; one command re-runs all three and saves its output beside it (`plans/analysis/scripts/adr-05/`, kept locally).

| | What happens | Root cause |
|---|---|---|
| **1. Telling the map something happened never reaches what caused it** | On the two-claim map `verify_observe.py` builds, **This happened** on the effect leaves the cause at `.3000` where the hand-worked answer is `.4562`, and **Suppose this is true** prints the identical `.3000` — two verbs, one behaviour. Down a three-claim chain: `.3500` against `.4015`, `.4040` against `.5971` — a miss of `−.1931` (`recheck.py` §3) | The engine keeps each claim's worked-out likelihood and throws away the coin flip (`propagation.py:1470`); for a causeless claim that likelihood is identical in every world, so discarding worlds cannot move it |
| **2. The tradeable endings are deaf to half their causes** | On Hormuz, **Suppose the war-risk insurance premium falls** moves *Brent settles below $68* `.3925 → .4759` and moves **both** endings by exactly `0.0000`; supposing OPEC+ restraint moves it to `.2197`, both endings again `0.0000` (`verify_trigger_read_day.py`) | An arrow reads its source on the day the source's **earliest** incoming arrow lands — one integer doing two jobs (`propagation.py:842`, read at `:1463`). For Brent that is day 2; the premium's push lands day 7 and OPEC+'s day 5, *inside* Brent's own series, which is identical through day 6 and separates at day 7, `.492` against `.409` |
| **3. A claim nobody believes deletes the reader's own assertion** | Suppose the strait open on 1 October, then insert a claim the map gives one chance in a thousand with a `−0.01` arrow into it: the tile never reads *Supposed* on any day — day-states `withdrawn, withdrawn, pushed, …` from day zero, the number its own prior `.30` throughout (`recheck.py` §1) | A supposition ends on a calendar read off the map's shape (`propagation.py:940-948`), and the test for which arrows oppose it reads only the sign of the push (`:888-895`). Neither the opposing claim's likelihood nor the size of its push enters |

**And a range made of coin flips.** With every stated range frozen to a point, so the honest answer is zero width, two claims on a six-claim chain report `.0157` and `.0187`; under **This happened** on a three-claim chain the middle claim reports `.1571` (`recheck.py` §2, §3). *(Record 0014 calls this the band; the vocabulary's word, used here, is the **range**.)*

## Decision Drivers

* **The traceability veto** (Kent): no state that cannot be traced to an input, a rule or a cited source. A number wrong by `.19` that cannot say so is that state.
* **INV-3, assert is not observe** — defect 1 makes the two verbs identical. **INV-4, locality** is kept, and ideally made easier to prove. **INV-7** wants two significant figures, and a second figure that moves with the dice is not one.
* **Kent's direction, 2026-09-21**, as the dated decisions note records it: an exact core with a sampler on top, the time model kept and made sound. **Stack 06 needs event days** to say whether a stop is touched before a target.

## Considered Options

Three terms, each once. A **rate** (the standard name is a *hazard*) is how likely a claim is to happen on a given day, given it has not happened yet; added up across its window it gives the chance it has happened by the end — a **first passage** probability. **Variable elimination** solves a sparse network of yes/no claims exactly: multiply the small tables and sum out one claim at a time. **Likelihood weighting** is the alternative to discarding inconsistent worlds: keep every world, weighted by how well it matches the evidence.

| | Measured | Source |
|---|---|---|
| **A. Repair the defects inside today's engine** | Defect 2 has **no** repair: the right day is per world, so the settled day becomes random, and the grid, the day-states, retraction and the locality proof are built on it being fixed. Defect 1's cheap repair kills the range — a yes/no flag's within-version **variance** is about `0.25` against an across-version `0.01`, so the noise correction clamps to zero and every range under **This happened** collapses to a point. Restoring it needs ~30× the worlds: one `propagate` on the fixture is **61.1 ms** at 2 000 versions × 8 worlds (`7.7 ms` at 250 × 8), so **about 2 s**. 1.5 sessions, `+120 / −60`, defect 3 still standing | engine digest §3a; timings `recheck.py` §5; the saved run is the last of three that day, and a wall-clock timing is a band — the three gave 65.7, 66.4 and 61.1 ms |
| **B. One variable per claim whose value is *the day it first happened*, solved exactly over those days** — one of the two reviews' design | Generated 20-claim maps, ≤3 causes a claim, **at 12 slices**: **0.7–7.8 s** a range, largest table **4.8–62.7 million entries**; at 30 claims **58–119 s** or out of memory. At the 24 slices this design runs, B is worse still | engine digest §0(2), `ve_cost.py` |
| **C. The number becomes *the chance it happens by its deadline*; arrows bend a rate; *when* comes from one forward pass, *whether* is solved exactly over yes/no truths** | **The model is right and this design adopts it** — its calibration reproduces the elicited numbers to four places and observing a claim gives exact Bayes upstream. What the engine digest got wrong is the cost: it sold the design on **0.5 ms** at 20 claims, and **that timed the elimination only** — `ve_cost.py` builds its tables from a random logistic with no time model (`truth_factor`, `:135-145`), before the clock starts inside `all_marginals` (`:205`). The pass that builds tables from the arrows was never costed, and it is what the spike killed the design on. Corrected figures below | spike round one, verdict 5; lines re-read on `main` by this record's author |
| **D. Do nothing** | A thesis card resting on endings that do not move when half their causes do | defect 2 |

**C as first designed, judged against B** — 140 adversarially generated four-claim maps, 9 520 numbers, **24 slices with an arrival taken at the slice's last day** (adversarial pass M1; the spike's faster code reproduces the red team's enumerator to `0.000e+00`):

| Query | compared | mean | 99th pct | worst | over `.005` |
|---|---|---|---|---|---|
| no edit | 560 | `.00027` | `.0046` | `.0175` | 0.9% |
| **Suppose this is true** | 4 480 | `.00007` | `.0015` | `.0259` | **0.2%** |
| **This happened** | 4 480 | `.00127` | `.0151` | **`.2043`** | **6.6%** |

*Suppose this is true* was right from the start; *This happened* was not. The arithmetic is exact, but the **table** is built from timing worked out before the evidence, and evidence moves *when* a cause happened as well as *whether*. It bites when the observed claim is itself a cause of another cause and the reach is through impulse arrows; a plain chain is exact.

## Decision Outcome

Chosen option: **C with three amendments the spike measured** — an additive rate, a weighted forward sample for *This happened*, and the middle-of-the-slice convention. It is the only option measured to honour both halves of Kent's direction inside the budget he has now named, and the only one that hands stack 06 event days it can trust.

**What a number means.** The chance the claim resolves YES by its own deadline — what the tile already says. Not a snapshot on one day, and **an event that has happened never un-happens**.

**The time model stays on the arrow.** `strength`, `lag`, `shape`, `half_life` keep their names and meanings and bend a **rate** rather than a likelihood read on one day. An impulse's whole area now counts, so the answer no longer depends on where a deadline falls against a half-life — record 0014's admitted wart; attacked with half-lives of one and two days landing four days before a deadline, the gaps were `.0000` to `.0001`.

### How two causes combine — Kent's decision R18

**Causes add to a claim's rate: each is an independent route by which the effect may come about.** The chance none of them brings it about is the product of the chances that none severally does — the independent-routes rule a reader can check by hand. A claim at 10% on its own, two causes each of which *alone* would take it to 40% by the same deadline, both happening on day one (`model_diff.py`, round two §4):

| | neither | one cause | **both** |
|---|---|---|---|
| **causes add — independent routes (chosen)** | `.100` | `.392` | **`.590`** |
| causes multiply — the first design | `.100` | `.392` | **`.910`** |

With no cause the claim fails nine times in ten; one cause cuts that to six in ten, removing a third of the ways it could fail; two independent causes each remove a third, leaving `.40` of the failure — a hand-check that gives `.600`, where the table reads `.590` because the cause sits at the middle of the first slice rather than at day zero. The multiplicative form instead multiplies the rate about fivefold per cause, twenty-five for two.

**What is given up: causes never amplify one another.** *Hormuz reopens* and *OPEC+ restraint holds* may really be worth more together than apart, and here they are not. What is not arguable is that **nobody stated the amplification** — the model is asked one number per arrow, plus the claim's own, and neither is about two causes coinciding, so the old form put it there itself. Genuine reinforcement needs a third elicited number on the pair, which version one does not have.

**What that assumes, and where it is wrong.** That two arrows into a claim are two separate ways for it to happen — which they are not, when both work through one mechanism. Across every map the repository holds (65 claims, 75 arrows):

| | |
|---|---|
| **The fact**, structural (`classify.py`, re-run 2026-09-21) | Eight claims have two or more causes *pushing* them. On **8 of 8**, one of those causes is already a cause of another, so it reaches the effect two ways at once |
| **The judgement** — one analyst reading the arrows' own stated reasons, and a reading is what it is | three *the same route* · one *needs both* · four *cannot tell*. **None cleanly independent** |
| **The size**, *if* a shortcut arrow's number includes what already flows along the drawn path (`compose.py` §2b) | `.003` to `.075`, median **`.049`** — the first printed figure, on half of them |

**That size is an upper estimate.** These maps predate R6, which asks for *the chance if this cause happens and no other cause on this map does* — exactly the direct effect, excluding the drawn path. **Nobody has measured how much R6 alone repairs.**

**The remedy is the map, not the arithmetic** (Kent, R22). In all eight the shared mechanism is *already a claim*, so the repair is one fewer arrow, not one more rule: **no new field, no new arrow type, no engine code.** Two paragraphs ride the shape freeze and amend record 0006 there — draw an arrow into the step the map already names, straight in only when it really is a second way; and write two things that only matter together as their own claim, whose rate switches on at the **latest** of its causes' days (exact to `3.220e-15`, `+5 ms` at 200 versions, `compose.py` §3). Deleting the shortcut arrows takes the twenty-claim map from `40.1` to `29.9 ms` at 200 versions, `321.0` to `228.2` at 2 000, width 4 → 3 (`cost.py`). Two Inspector lines say how causes were combined. **Declined:** one stated number per pair, **8.6× over budget** at 2 000 versions (`2 590.4 ms`); and a label on every multi-cause claim. **Not repaired by any of it: a shared cause nobody drew** — causes sharing a cause of their own are on the map as arrows and the exact solve holds the whole joint, but one never drawn is a generation question.

### How it is worked out

1. **The forward pass gives *when*.** Causes first, each claim's chance of having happened by each of **24 slices** across its window. Because the rate adds, the chance a claim has *not* happened is a product with one factor per cause, so the average is taken **one cause at a time** rather than over every combination of arrival days — the whole of the cost result below. Proved: one cause at a time equals averaging the full table to **`4.4e-16`**, the forward pass agrees to `2.1e-15`, and many versions in one pass equals one at a time to `0.0` (`check.py`, round two §1).
2. **Variable elimination gives *whether*, exactly.** **Suppose this is true** pins the claim to its day, redoes the forward pass and solves; **This happened** multiplies in a mask keeping only what agrees with the evidence, and renormalises. The versions ride as an array axis, so a range is one pass.
3. **A weighted forward sample answers *This happened*.** Worlds are drawn forward with arrival days; at the observed claim the world is not thrown away — the claim is set to what was observed and the world's weight multiplied by how likely that was. **The exact yes/no solve is the control variate**: the same world is drawn twice, once under the full time model and once under the yes/no model with the same random numbers, so only the *difference* is sampled and added to an answer already known exactly. Seeded. **One sample serves a whole range, and both readers** — the numbers on screen and the event days stack 06 reads.
4. **An arrival inside a slice is taken at the slice's middle, not its end.** One line; at 24 slices it moves the worst gap against a fine reference from `.0290` to **`.0027`**, and the last-day convention at 60 slices is worse than the middle-day one at 12 (`midpoint.py`, `convergence.py`).

**24 slices, not 12.** Twelve was measured and halves the cost, and its grid error alone puts **2.50%** of *This happened* numbers over `.005` against a fine reference, where 24 with the middle-day convention puts **0.00%** (`midpoint.log` §A, observe rows). Building to 12 would fail the tolerance this record's own *Confirmation* states.

Two properties become facts rather than machinery: **locality becomes a theorem**, a claim cut off from the evidence having a factor that sums to one; and **the width shares** (FR-21) become exact, one extra solve each. **Observations stay undated in version one** — `Observe` carries a target and a value and no date (`intervention.py:70-85`), and *this happened on day 5* would need the yes/no question re-cut per evidence day.

### The kill criterion, and Kent's new budget

> *A candidate passes if it holds `.005` on 99% of the adversarial set **and** runs inside 300 ms on a 20-claim map (up to 3 causes a claim) for one world with its range.*

**It fired, twice. This record does not claim the 300 ms criterion was met.**

| | accuracy, *This happened*, 4 480 numbers | one world with its range, 20 claims |
|---|---|---|
| **round one** — multiplicative rate, 12 slices | sample + control variate: 99.98% at 50 000 worlds, 100.00% at 200 000 | **3.0 s at 200 versions**. The binding cost was the shared forward pass at **2 879 ms**, not the sampler at 110 ms; at 2 000 versions the same table reads **29 527 ms** |
| **round two** — additive rate, 24 slices, middle day: the tables alone | mean `.00103`, 99th pct `.0127`, worst `.0420`, **5.36% over `.005`** | 39 ms at 200 versions · 305 ms at 2 000 |
| **round two** — the sample + control variate, 50 000 worlds | mean `.00028`, 99th pct `.0020`, worst **`.0042`**, **0.00% over `.005`**; *no edit* worst `.0025`, *Suppose* worst `.0027` | **97 ms at 200 versions · 360 ms at 2 000**; with three claims held back by an arrow, 113 ms and **538 ms** |
| the same, with **five of the twenty claims states** feeding `sustain` arrows (record 0017) | unchanged — a state is more accurate under this rate, not less | 126 ms at 200 versions · **644 ms at 2 000** — **over the 600 ms**, before any holding-back arrow is counted |

*(`candidates_add.py`, `timing20.py`, `timing_add.py`.)* The additive rate improves the tables markedly and still fails the 99% bar, **so the sampler is required**. Its effective sample size is 96.9% of the worlds drawn on average, 42.9% at worst. **The other candidates, one line each:** keeping the prior-timing tables is the second row, which fails; re-cutting the yes/no variable per evidence day leaves 4.38% over `.005` — measured in round one, under the multiplicative rate — and can be *worse* than doing nothing, while the widening that does pass widens three claims of four, which is option **B** with one sink left over, at B's cost.

**The two rounds' misses, at their own conditions.** Round one missed by **10×** at 200 versions and 12 slices; round two misses by **1.2×** at the 2 000 versions a range needs, and at 24 slices. Like for like at 2 000 versions, round one's own table reads 29 527 ms. **Kent relaxed the budget to 600 ms for one world with its range at 2 000 versions** (decision R19) with these measurements in front of him — and **they were all-event measurements.** The states re-run has since put the same map with five states at **644 ms**, so the budget is **met on all-event maps with a thin margin and not met on the benchmark with states**. This record does not present 600 ms as achieved; the *Open for Kent* item below is how it gets settled.

**Why the sample is a fixed cost, not a per-version one.** Its correction is shared across a range. Round one measured that on easy maps only and flagged the hard one; round two measured the hard one (trial 33, `hardmap.py`): under the multiplicative rate the correction is `.1172` and moves `.0805` between versions, so sharing would have been wrong by up to `.08` on a band end. **Under the additive rate it is `.0020` and moves `.0020`.** Redone per version, 2 000 versions would cost 110 seconds.

**And a range needs 2 000 versions.** Round one solved 20 000 versions of the same map exactly under an observation and resampled from that pool (`versions.py` §6): at **2 000** a band end wanders `.0086` on a wide band and `.0046` on a narrow one; at **200**, the count the engine digest proposed, it wanders `.0275`, a tenth of the width. **Keep 2 000; the inner eight worlds go, the outer loop does not.** What 2 000 buys is a *narrow* band's ends to two significant figures — a band `.25` across needs about **6 000** by the square-root rule that table obeys, and this record does not claim otherwise. *(Measured at 12 slices under the multiplicative rate and not re-run under the additive one, so it could move — round two §7.)*

### What `World.series` now means, and what stays

Today `series` is a per-day likelihood allowed to **fall**, and the golden test pins it (`test_hormuz_golden.py:117-120`): `1.0` on day zero, between `.25` and `.45` on days one and three — the same value on both — and below `.10` on day four. **Under "the chance it has happened by day *t*" a series can only rise**, so that test cannot survive; the events-and-states reading of the same branch replaces it, proposed record 0017's to write. An event's series is a rising curve; the field keeps its name and type, and days between grid points are read off the same added-up rate rather than re-solved (`propagation.py:110`, `SERIES_CAP = 180`). What that does to `DeltaRow.peak_delta`, to `at_day` and to the golden domino assertion is carried in full by the owed-edits list.

**A supposed claim's stored `p = 1.0` stays** — three live readers, not the one the first draft assumed: `diff.py:817-818`, `diff.py:460`, and the browser's `world/apiSource.ts:266` (browser line numbers here and below are `feat-04b-evals`, which is what `main` will hold). `Belief.p` allows no gap (`belief.py:39-45`), so removing it is a wire break.

**What this record amends:** **ADR-0005** and **ADR-0014**, neither superseded; **`lo` and `hi` keep their meaning**, and **ADR-0015 is untouched**. *The dated amendments appended to 0005 and 0014 in this same pull request say which sentences move, one by one.*

### Consequences

* Good, because the number answers the sentence beside it: **This happened** does something, supposing any cause on Hormuz moves what it points at, locality becomes a property of the arithmetic whose oracle can get **stricter**, and with every stated range frozen to a point the range is zero by construction.
* Good, because stack 06 gets event days it can trust. Measured against the judge over 40 maps at **200 000 worlds** (`when_table.py`, round one §7), the weighted sample's day distributions are within `.0064` of exact at worst and its median arrival is at most **one slice** out, where drawing truths exactly and then days under the prior moves a median arrival by **four slices — ten days**, worst distribution gap `.2143`. *(Measured under the multiplicative rate and at 200 000 worlds; the design runs 50 000, and this was not re-run.)*
* Bad, because **every number on the map changes once** — hence a flip of its own, reviewed as one file's diff.
* Bad, because causes no longer amplify one another, and no version-one map can say that two of them do.
* Bad, because the 300 ms criterion was not met: the budget was relaxed to fit the measurements rather than the measurements fitting the budget.
* Neutral, because the wire shapes keep their names and types: `series` and `moved_only_by_reweighting` change what they carry, and `Verdict.product` becomes always empty under record 0022.

### Still open, and where it can go wrong

* **The margin against the 600 ms budget is thin on all-event maps, and gone once states are on one.** At three holding-back arrows and 2 000 versions the chosen design measures **538 ms** — the log's own total from a forward pass of `404.5 ms`, a solve of `81.6 ms` and a sample of `52.2 ms` — and about **568 ms** taking the slowest of each measured across those runs (`427.9`, `81.6`, `58.0`): inside 600 ms by roughly five to ten per cent. With **five states feeding `sustain` arrows** the forward pass on the same map goes `224.4 → 508.9 ms` and the total to **644 ms** (`cost2.py`, `cost2.log`), which is over. The cause is the same shape as a holding-back arrow: a `sustain` child reads the state's whole on–off interval, and that joint costs versions × slices **cubed** — `78.9 ms` per state at 2 000 versions against `3.6 ms` for the state's own holding curve. **Nobody has measured states and holding-back arrows on one map**, though three of the latter alone added `180 ms` to the forward pass. At 200 versions the same map with states is 126 ms. Four things would widen the margin and **only the first is measured:** deleting the shortcut arrows the composition analysis found takes the same map's 2 000-version total from `321.0` to `228.2 ms` with every arrow helping (`cost.py`); giving a state that no `sustain` arrow leaves the cheap path only, since it then needs the holding curve and not the joint; computing the joint at a coarser grid than the on-process, a `sustain` child being its only reader; and the two-pass junction-tree solve in place of one elimination per claim (80 ms at 2 000 versions), which would land the all-event case near 295 ms.
* **The grid and the integration points carry an error of their own, and it is larger than every tolerance here.** The design runs 24 slices with **eight integration points inside each**. Against a dense integral of the rate, that configuration reproduces an arrow's stated chance to `1.81e-2` and matches the rate itself to `1.88e-2`; 32 points brings both to about `5e-3` (`check.log`, round two §1). **Nobody has costed 32.** This does not invalidate the `.005` oracle — that oracle judges at the same grid, so the grid error cancels — which is exactly why it is said here: `.005` is the distance to an enumerator on the same grid, not to the truth.
* **An arrow that holds a claim back is the one place the cost still multiplies**, forcing an enumeration over the days it might have arrived on. On the same map: three cost **1.8×** the forward pass, eight `5.4×`, the generator's own ten **70×** — 15.9 s at 2 000 versions (`inhibitors.py`, `timing_add.py`). Real maps carry at most one per claim today — **but the freeze intends to add a *what would stop this step* sentence to the prompt, which will raise that count**, and nobody has measured the map it produces. The lever is a cap per claim; it is not proposed here because there is nothing yet to size it against. **They also saturate:** **30.0%** of the holding-back arrows in the adversarial set were clamped short of their stated chance (`candidates_add.py`).
* **Accuracy is measured on four-claim maps only** — the judge is not computable above that — while the cost numbers are from twenty-claim maps; the two sets never meet. And proposed record 0017's states sweep is being re-run under the additive rate; that record carries the place for it.

### Confirmation

**Two oracles, two tolerances, proving two different things.** One alone could not have caught the error above: an enumerator built from the core's own tables proves the summing and is blind to a wrong table.

1. **`test_the_elimination_is_exact`** — tolerance `1e-9`, over the core's **own** yes/no tables, summing the joint by hand. Proves the elimination, the supposition surgery and the conditioning. Blind to timing.
2. **`test_the_tables_agree_with_integrating_over_time`** — forbidden the core's tables, built from the arrow parameters alone, enumerating the full joint of event times on maps of four claims or fewer. Tolerance **`.005` on each of the three questions, with the sample size named**: the measured worsts at 50 000 worlds are in the kill-criterion table above, and at 200 000 worlds under the same additive rate they are `.0012` no edit, `.0021` *Suppose this is true*, `.0017` *This happened* (`candidates_add.log`). **Two conditions:** the enumerator runs at the **same number of slices and the same within-slice convention** as the core — 24 slices judged by 60 with a different convention differs by `.0290` on its own, swallowing the tolerance — and **the sample is seeded**, so the test is deterministic.

**The locality oracle, restated and stricter:** *cut off from the evidence ⇒ bit for bit* — byte-identical, not merely close. `test_band_is_not_sampling_noise` survives and tightens to zero width exactly. `test_an_observation_moves_a_cause_even_when_no_arrow_pushes` (`test_propagation.py:544`) is **reversed into an assertion of invariance**: record 0014's 2026-09-17 amendment decided deliberately that an observation moves a causeless claim through the version weights; this record removes the mechanism.

### How it lands

| Step | Contents | `main` after |
|---|---|---|
| **1** | The two oracles and their enumerators, the second committed under `backend/tests/`. Failing cases marked strictly expected-to-fail, by name. Reverse the invariance test. | Green. Two tests documenting two defects. |
| **2** | The new core beside the old, behind a flag, **default unchanged**. Both oracles run against both. **If Kent takes option (A) below, this step also times the product's own core on the named benchmark**, and the flip below waits on that number. | Green. **Every screen still shows today's numbers.** |
| **3** | **The flip, alone.** Default changes; Hormuz re-derived; the generated numbers file regenerated — **its diff is the complete, reviewable statement of which numbers moved**. The two nested loops, the noise correction, the version weights and `moved_only_by_reweighting` go; `diff.py` moves over; the browser readers listed under *Honest cost* are corrected. | Green. Every number changes **once**. |
| **4** | Separately: record 0022's three quantities, and record 0017's events and states. | Green. |

The generated numbers file must exist *before* step 3, or the flip also carries a sweep of several hundred numbers across the chapters and nobody can review it.

### Honest cost

**Five to seven sessions for this record's work** (adversarial pass M5; a session is about three focused hours); record 0017's events and states add about **1.3** (engine digest §5.3), so **six to nine together**; the whole of stack 05 about **nine and a half** (S4) — which also notes this repository has never kept session accounts, so every figure is a first estimate.

What the first estimate of three missed, verified on `main` unless marked: **`diff.py`**, 1 459 lines, where the version weights, the reweighting flag, the range import, the sweep's reading of retractions and the ranked list's reading of `series` die or change; **the browser**, budgeted at zero — three rendering readers of the reweighting flag (`graph/diff/noChange.ts:52`, `components/Inspector.tsx:248` and `:385`), its mapper (`apiSource.ts:325`) and its *"worlds under each"* sentence (`apiSource.ts:228`), all on `feat-04b-evals`; plus the retraction badge whose height is baked into the tile's geometry; **34 of `test_propagation.py`'s 46** tests (46 confirmed by count); **the locality oracle**, rewritten and stricter; and **every decimal in the two multiverse chapters** — on `feat-04b-evals`, 259 in `propagation.md` and 189 in `diff.md`, counted as a decimal point followed by one or more digits; on `main` today the same command gives 239 and 166. For calibration, `d9c853e` (#38) fixed **one** defect class and cost **1 335 insertions across 12 files**.

## Open for Kent

**1. What to do about the budget, now that the benchmark with states is over it.** Every millisecond above is a prototype's, not the product's.

* **(A) Recommended — make the budget the gate on the flip, not on this record.** The staging already builds the new core beside the old behind a flag and flips in a pull request of its own. This record then names **one benchmark** — twenty claims, up to three causes each, **five states feeding `sustain` arrows**, **three arrows that hold a claim back**, 2 000 versions, 24 slices — and **one number, 600 ms**; the flip does not happen unless the product's own core meets it there, and if it cannot, Kent is told with the numbers. *Cost:* the design is accepted with its cost unproven on the hard case, and the three unmeasured optimisations above become the first work of the core pull request. *Why first:* a prototype's milliseconds are not the product's, and a gate belongs where the real code is.
* **(B) Another spike round before acceptance** — measure the three optimisations in scratch. *Cost:* about a session, and this record waits for it.
* **(C) Raise the budget to a named larger value.** What has actually been measured needs about **700 ms** to carry the 644 ms benchmark with the same margin 600 ms gave the all-event case; the states-plus-holding-back-arrows combination is unmeasured and would need more. *Cost:* a slower branch edit on large maps. For scale, today's engine takes **61.1 ms** on its own seven-claim map at 2 000 versions × 8 worlds (61.1–66.4 ms across three runs), and **nobody has measured today's engine at twenty claims**, so there is no like-for-like to compare a relaxation against.

**2. What the screen says about *This happened*.** The sampler is seeded and reproducible and no measured number is off by more than `.005`, but it is a sample, and the reader is entitled to know which verb is answered by one.

* *Recommended:* nothing on the ordinary screen, and one sentence in the Inspector on an observation branch — *"learning moves numbers upstream; this one is worked out by a seeded sample of 50 000 worlds and is within `.005` of the exact answer on maps this size."*
* Alternative: say it on the honesty line for every world — cheaper, and it puts a caveat on screens the caveat is not about. Or say nothing anywhere, which is the traceability veto.

## More Information

* **Kent's decisions, 2026-09-21**, recorded in the dated decisions note kept locally under `plans/notes/`: **R1** (an exact core with a sampler on top, the time model kept and made sound, a spike with a kill criterion first), **R18** (causes add as independent routes), **R19** (the budget is 600 ms for one world with its range at 2 000 versions) and **R22** (the remedy for causes that share a route is the map — two prompt paragraphs at the freeze, no engine code). *(Those are the decisions note's words for his choices, not a transcript of his own.)*
* **The evidence.** The stack-05 spike's two rounds, the composition analysis, and the engine digest and adversarial pass that preceded them, all 2026-09-21, kept locally under `plans/analysis/` with their scripts. Every measurement here is quoted from one of those reports with its script named, or was re-run on 2026-09-21 by this record's author.
* **Related.** ADR-0005 and ADR-0014 (amended, not superseded) · ADR-0015 (intact) · proposed ADR-0017, ADR-0021, ADR-0022. Chapters rewritten: `spec/multiverse/propagation.md`, `spec/multiverse/diff.md`.
