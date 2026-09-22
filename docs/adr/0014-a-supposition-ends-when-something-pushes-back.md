---
# ADR-0014: A supposition ends when something pushes back; a range says how sure we are of the number, not how the dice fall
status: accepted
date: 2026-09-17
decision-makers: Kent Gang
consulted: two independent Opus reviews (2026-09-17); `plans/notes/2026-09-17-range-on-computed-beliefs-research.md`; `spec/graph/belief.md` open questions 3 and 4; `spec/multiverse/interventions.md` B2
informed: agents working in `backend/src/katalyst/domain` and on stacks 03a, 03b, 04 and 06
supersedes: none
superseded-by: none
spec-impact: spec/graph/belief.md (what the range means; open questions 3 and 4), spec/multiverse/propagation.md and spec/multiverse/diff.md (both written in stack 03a and both bound by this record), spec/multiverse/interventions.md (B2), PRODUCT_REQUIREMENTS.md FR-16 and FR-21
---

# ADR-0014: A supposition ends when something pushes back; a range says how sure we are of the number, not how the dice fall

> **Amended in place on 2026-09-17** — see *Amendment (2026-09-17) — the direction is read with the number's own weights*, at the end. It says how the versions are counted while section D decides that something moved. Nothing in the decision changed, and no measurement below was rewritten.
>
> **Second amendment 2026-09-21, and this one reverses something** — see *Second amendment (2026-09-21) — decision A is reversed, and the band's machinery changes while its meaning does not*, at the end. **Decision A below — how a supposition ends — is reversed by record 0017**, and section B's machinery is replaced by record 0016. Both are **in force from 2026-09-21**, when Kent accepted those records. What `lo` and `hi` mean does not change. No measurement below was rewritten.

## Context and Problem Statement

Stack 03a is about to write the engine, and two rules it cannot be written without are unsettled. The first: the showcase branch supposes the strait is open on 1 October, then inserts a strike on the 2nd that pushes against it. What happens to the supposed claim, and on which day does it stop being taken as given? The second: every claim shows a range — `.35 (.20–.49)` — and nothing says what that range *is*. Record 0005 called it "a standard interval for such a share" and admitted in the same breath that it mixes simulation noise with the elicited spread, which means the width shrinks by running the machine longer. A number that moves when you buy more computer time is not telling you anything about the world. So: **when does a supposition end, and what does the range under a computed likelihood mean?**

## Decision Drivers

* **INV-3, assert is not observe** — whatever ends a supposition must move nothing upstream of it.
* **INV-4, locality** — base and branch must be comparable claim by claim, so they must be built from the same raw material.
* **INV-7, honest numbers** — `0 ≤ lo ≤ p ≤ hi ≤ 1` after any sequence of edits.
* **NFR-1, honesty** — two significant figures and a range, always.
* **NFR-2, determinism** — the same map, branch and seed give byte-identical worlds.
* **UX-14** — the tile must be able to draw the states a supposition passes through, in order, with dates.
* **FR-16** — a ranked list of the terminals that moved. **FR-21** — a ranking that says which claim to go and research.
* **FR-24** — percentile outcomes, the average loss in the worst five per cent of runs, and the chance of being wiped out: all need many worlds.
* **The traceability veto (D5-ii)** — no state that cannot be traced to an input, a rule or a cited source. A range nobody can define is that state.

## Considered Options

**How a supposition ends** — four options:

* **S1.** A hard fact in every simulated world while it holds; it stops holding on the day the **cause** of the first live arrow pushing against it becomes true, and from that day the claim reads its own prior plus every live arrow.
* **S2.** A large finite push — add ±4 on the log-odds scale and let the arithmetic fight it out.
* **S3.** Hold the claim true until the opposing push lands, that is, until that arrow's delay has run.
* **S4.** A plain push with no retraction: once supposed, always supposed.

**What the range under a computed likelihood means** — five options:

* **R1.** Two nested loops: **two thousand versions of the map**, each drawing every claim's likelihood from its own stated range, **eight worlds under each version**; the band is the middle 80% across versions once the sampling noise has been subtracted.
* **R2.** Three runs: every low end at once, every high end at once, and the middle.
* **R3.** Twenty batches of five hundred worlds, the band read off the spread between batches — record 0005's "standard interval for such a share", made concrete.
* **R4.** Analytic first-order arithmetic (the delta method) as the engine: one extra propagation per stated range, combined by calculus.
* **R5.** No range on a computed number; a point, and the words "range unknown".

Four whole formalisms were read and set aside before these five were measured; see the end of *Pros and Cons of the Options*.

## Decision Outcome

Chosen option: **"S1 — a supposition is a hard fact in every simulated world, and it ends on the day the cause of the first live arrow pushing against it becomes true"**, because it is the only option under which "suppose this is true" and "this happened" agree about the claim itself (INV-3), under which the user's word is withdrawn by an *event* rather than by a delay parameter, and which leaves UX-14 a state to draw on the days in between.

Chosen option: **"R1 — two thousand versions of the map, eight worlds under each, the band read as the middle 80% across versions once the sampling noise has been subtracted"**, because it is the only measured design that keeps how sure we are of our numbers apart from how the dice fall, reproduces to ±.002 across seeds in about ten milliseconds (NFR-2), and pays for FR-21, FR-24 and the diff out of one sample.

**This record amends ADR-0005 without superseding it**, in three places: the interval on a belief is no longer the sampling interval of a share; `observe` keeps its reject-the-inconsistent-worlds rule and gains a reweighting of the outer loop; and the diff's "shifted" is decided by paired comparison, not by overlapping bands. That record's link fields, log-odds aggregation and trigger-versus-sustain rule stand untouched.

### A. How a supposition ends

While a `do` holds, the claim is **true in every simulated world** — a hard fact, not a strong push. The tile shows the words **Supposed · date**, never a number; a number would invite the reader to wonder about the other two per cent.

It stops holding on the day the **cause** of the first live arrow pushing against it becomes true — not the day that arrow's push lands. From that day the claim reads its own prior plus every live arrow, each arriving on its own delay. Three named states, in this order:

| State | Hormuz H, the strait is open | What the tile shows | Why |
|---|---|---|---|
| **supposed** | 1 October | **Supposed · Oct 1** | The user pulled a lever; H is true in every world |
| **withdrawn** | 2–4 October, `.35` | **Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"**, with "withdrawn — no live push yet" beside the number | The strike became true on the 2nd, so we stop taking the user's word; H falls back to its own prior `.35`, and S → H's three-day delay has not run |
| **pushed** | from 5 October, about `.07` | the number, same badge | The delay has run; S → H's −1.9 push lands on the prior and `.35` becomes `.07` |

The warrant is **ADR-0004's amendment: a `do` is a timed assertion.** `Do(H, true, at=1 October)` says *H holds from the 1st*, not *H is sealed for ever against whatever you tell me next*. Do **not** cite Pearl's do-operator as the warrant; that operator has no clock in it, and the clock is the whole of this rule.

### B. What the range under a computed likelihood means

Two kinds of not-knowing, kept apart:

| | Lives where | Plain statement |
|---|---|---|
| **How the dice fall** | inside `p` | The event may happen or not; `p` already says how often |
| **How sure we are of the numbers we put in** | in `lo` and `hi` | We are not certain what number to give you; more homework would move it |

`lo` and `hi` are the **10th and 90th percentiles of the likelihood itself**. `.35 (.20–.49)` reads: *our number is .35; if we somehow learned the true likelihoods, about 8 times in 10 the answer would land between .20 and .49.* A wide range never means the event is more volatile.

**What a stated `{p, lo, hi}` defines.** A bell curve on the **log-odds scale** — the scale the pushes add on — with its two halves fitted separately: middle `p`, 10th percentile `lo`, 90th percentile `hi`. The half-widths are `(logit p − logit lo) / 1.2816` and `(logit hi − logit p) / 1.2816`, where `logit x` is the log-odds of `x` and `1.2816` is how many standard deviations out a bell curve's 10th and 90th percentiles sit. It honours all three stated numbers exactly, takes a lopsided range without complaint, and can never leave 0–1.

**How it is computed.**

1. Draw **two thousand versions of the map** by Latin hypercube sampling — a way of spreading draws evenly instead of letting them clump; three lines of `numpy`, no new dependency. Each version draws every claim's likelihood from that claim's own stated range. A version is **one coherent set of numbers this model would have stood behind**, never "every low end at once".
2. Run **eight worlds under each version**, and on the last step keep each claim's **computed probability** rather than only the coin flip that came out of it — eight worlds then carry far more than eight coin flips.
3. The band is the **middle 80% across versions, after the sampling noise has been subtracted**. `p` is the average over every version and every world.

**The noise correction, in words.** The spread we measure across versions is the real spread we want *plus* the wobble of having run only eight worlds each. Those two add, so subtract the second and shrink the band by what is left — the law of total variance. In symbols:

```
f    = square root of  max( 0 , 1 − ( mean over versions of v_k / m ) / V )
low  = p̄ + (q10 − p̄) × f
high = p̄ + (q90 − p̄) × f
```

* `m` — worlds run under each version; here 8. At least 2, or `v_k` does not exist.
* `q_k` — version `k`'s own answer for this claim: the average of its `m` computed probabilities.
* `v_k` — the spread (variance) of those `m` computed probabilities within version `k`; `v_k / m` is how much version `k`'s answer wobbles for sampling reasons alone.
* `V` — the spread (variance) of `q_1 … q_2000` across versions. This is the quantity that is too wide.
* `f` — the shrink factor, 0 to 1. Clamped at 0, so a claim whose apparent spread was all noise reports a zero-width band rather than an imaginary number.
* `p̄` — the average of every computed probability over all versions and all worlds; the reported `p`.
* `q10`, `q90` — the 10th and 90th percentiles of `q_1 … q_2000`; the uncorrected band edges.

**Two seed streams, derived from the one seed** — one for the versions, one for the worlds. The versions stream **never depends on the branch**, so base and branch see the same two thousand versions and can be compared version by version. Both are byte-identical on repeat (NFR-2).

**Link strengths are fixed numbers in stack 03a**, and the propagation chapter says so in those words. Only the claims' likelihoods vary between versions. Spreading the strengths too is decision G.

**The measured evidence.** All on Hormuz claim B, *Brent crude settles below $68 for five sessions*, read at day 45, where the truth is known by exact enumeration: **.35 (.20–.49)**.

| Design | Reports | Seed wobble of the band edges | Verdict |
|---|---|---|---|
| **R1** two loops, 2 000 × 8, noise-corrected | **.20–.50** | **±.002 / ±.003**, about 10 ms over 60 claims | **Chosen** |
| R2 every low end / every high end | .19–.50 | none | Not even a bound: R → B is negative, so the true corner of the box is .158–.567 |
| R3 twenty batches of five hundred | .25–.46 | ±.02 | A quarter of that width is coin-flip noise; the band is 28% too narrow |
| R4 analytic first-order arithmetic | .22–.52 | none | Accurate to .004, but 50× slower — one propagation per stated range — and it produces no worlds, so no payoff distribution |

R4 is **kept as a test**, not as the engine: the simulation must agree with the analytic answer to two figures on the fixture.

### C. Where the width comes from — for free

From the same two thousand versions, compute **each stated range's share of each claim's band** — a first-order variance share, obtained by binning the versions by the drawn value and comparing group averages; six lines of `numpy`, nothing run twice. Hormuz: **92 per cent of B's band is B's own prior**; pin that down and B's band goes from 29 points wide to 8. Everything else contributes under half a point. *(Corrected 2026-09-17: read "base rate"; the Brent claim has none — the number that varies is its `prior`. `PRODUCT_REQUIREMENTS.md` FR-21 carries the same repair. Re-measured 2026-09-17 by the shipped engine after B's resolve-by day moved to day 14: read there, B is `.40 (.25–.55)`, 65% of its band is its own prior, and pinning that prior takes the band from 30 points to 12; read on day 45 the engine still gives `.35 (.20–.49)`. The design conclusions are unchanged, and the measurements above stand as taken.)*

This **replaces FR-21's "sensitivity × width of interval"** as the ranking for where to spend modelling effort. Carried on the world in stack 03a; first read by the interface in stack 06.

### D. When a change counts as shifted

Compare base and branch **version by version** — the same versions, because that stream does not depend on the branch. Never by whether two bands overlap.

A claim is **`shifted`** when it moved by **0.005 or more** *and* moved in the **same direction in at least 90 per cent of versions**. That share is reported as **agreement**, the word the vocabulary already reserves for a computed number.

Hormuz, supposing the strait opens: B's two bands **overlap by a third**, and yet **every version moves the same way** — +.10, middle 80% from +.07 to +.13. Band overlap would have called that unchanged. It is the clearest change on the map.

### E. How the change list is ranked and dated

**Rank = size of the move × the weakest provenance weight on the shortest path from the edit to that terminal.** Two factors, and only two. **Range width and agreement are shown as their own columns and never multiplied in** — multiplying width in would sink exactly the claims FR-21 floats, which is the opposite of the advice the user wants.

**Which day a number is read on.** A tile's headline is read on the claim's **own resolve-by day**. A change-list row is read on the **day of largest divergence**, and the row names that day.

**A known wart, stated rather than hidden.** A path's multiplied-out likelihood (INV-8, the conjunctive honesty bar) multiplies numbers each read on a different day. It is still the most honest single number available for a chain, and it is not a joint probability. Say so beside it.

### F. `observe` under two loops

**Inner loop:** reject the worlds inconsistent with what was observed, exactly as record 0005 says. **Outer loop:** weight each version by its own survival share, so a version under which the observation was likely counts for more than one under which it was a fluke.

**Warn loudly when fewer than about 2 per cent of worlds survive**, and say in the warning that the *range* is then unreliable, not merely the point.

### G. Deferred, and said so

* **A spread on link strengths derived from provenance** — a cited arrow narrow, a bare story wide, at no extra elicitation cost. **Stack 04**, when the backing is real; in 03a every fixture arrow is hand-written `argued` or `asserted`, so the spread would be uniform and teach nobody anything. **There are no `strength_lo` / `strength_hi` fields, ever** — record 0005's "one number and one sentence per link" stands.
* **Whether a claim's starting range should come from measured disagreement across several independent model runs.** Kent: decide in stack 04. The research finding that stated ranges from language models are reliably too narrow is recorded under *More Information* as **input to that decision, not as a decision**.

### Consequences

* Good, because the range answers a question at last — *how sure are we of this number* — and no longer shrinks when the machine runs longer, so it can be argued with.
* Good, because FR-21, the diff, the payoff distribution and the range come out of one sample: nothing is computed twice and no two of them can disagree.
* Good, because base and branch are built from the same versions, so a change reads as a paired difference: more sensitive than comparing bands, and easier to explain.
* Bad, because **the mean sits a hair above the middle for `p < .5`**: the hypothesis's `prior.p` of `.35` shows as a `beliefs.model.p` of `.36` although nothing pushes on it. Both are right, and the `prior` versus `beliefs.model` table now says so.
* Bad, because **a terminal's band is dominated by its own prior's band** — an upstream range reaches a terminal through a factor of at most one quarter times the arrow's effect, so widening an upstream range barely widens a terminal (about 4 per cent on Hormuz). Do not build a demo around "widen this, watch that widen".
* Bad, because **`do` collapses the target's own band but does not reliably narrow the bands downstream**: supposing the strait opens moves B's width from .292 to .323, the curve being steeper near .45. Show instead the target's **share** of the downstream band falling to zero — H's share of B's band goes 2.6% → 0%.
* Bad, because **nothing here is calibrated**. No claim on any map has resolved, so the 8-in-10 has never been checked. The chip says **"model interval, uncalibrated"**.
* Neutral, because record 0005's flat ten thousand draws become 2 000 versions × 8 worlds = 16 000 propagations — still about ten milliseconds over sixty claims.
* Neutral, because a tile read on the claim's own resolve-by day meets spike-shaped pushes that have mostly faded, so computed numbers land near their priors. **The stored example map may therefore be curated:** its illustrative resolve-by dates, half-lives and strengths may be tuned so the example is rich and interesting, each tuned value carrying a comment saying why. A computed number may never be tuned — **every number shown in a demo comes from the engine itself or from a recording of the engine, never typed by hand** (Kent, 2026-09-17).

### Confirmation

* `test_same_seed_same_world` — covers **both** streams: the same map, branch and seed give byte-identical versions and byte-identical worlds (NFR-2).
* `test_range_matches_analytic_first_order_on_fixture` — the simulated band agrees with the analytic first-order band to two significant figures on the Hormuz fixture. This is what keeps R4 useful after rejecting it as the engine.
* `test_band_is_not_sampling_noise` — freeze every prior at its point value, leaving no stated range anywhere, and the band collapses to zero width within tolerance. A band that survived this would be measuring the machine, not the map.
* `test_shifted_needs_agreement` — a claim that moved ≥ .005 but inconsistently in direction is **not** `shifted`; a claim whose bands overlap but whose agreement is ≥ 90% **is**.
* `test_supposition_is_true_in_every_world_until_undermined` — while a `do` holds and nothing live pushes against the target, the target comes out true in every one of the 16 000 worlds.
* `test_retraction_dates_from_the_cause_not_the_push` — on the Hormuz branch the retraction date is 2 October, the day S becomes true, and **not** 5 October, when S → H's three-day delay has run.
* The **Hormuz golden series** — H reads *supposed* on 1 October, `.35` and *withdrawn* on 2–4 October, about `.07` from 5 October. Directions asserted exactly; values to two significant figures.

## Pros and Cons of the Options

### S1. A hard fact until its cause is undermined (chosen)

* Good, because "suppose this is true" and "this happened" then agree about the target itself and differ only in what they do to its causes — exactly INV-3.
* Good, because the day the user's word is withdrawn is an **event on the map**, with a name and a date, so UX-14's badge writes itself.
* Bad, because three states must be rendered rather than two, and the middle one needs a sentence on the tile or it reads as a bug.

### S2. A large finite push of ±4 log-odds

* Good, because a supposition becomes just another arrow; no new machinery.
* Bad, because ±4 is an arbitrary constant with no source, it contradicts the user in about 2 per cent of worlds, and it makes "suppose" and "this happened" disagree about the target itself — the one thing they must agree on.

### S3. Hold until the opposing push lands

* Good, because the claim never shows a number nobody asked for.
* Bad, because it ties "do I still take your word for this" to a **delay parameter**: change a lag from three days to thirty and the supposition outlives the news. And it is a cliff — true, then `.07`, with no state in between.

### S4. A plain push with no retraction

* Good, because it is the simplest rule to state and to build.
* Bad, because the showcase cannot happen: the strait stays open through the strike, and the one branch that demonstrates sustaining causality demonstrates nothing.

### R1. Two nested loops, noise-corrected (chosen)

* Good, because it separates the two kinds of not-knowing by construction, and the width shares, the diff and the payoff distribution fall out of the same sample.
* Good, because it reproduces to ±.002 across seeds in about ten milliseconds, on `numpy` alone.
* Bad, because two loops are more to explain than one, and `m ≥ 2` is a real constraint a future performance tweak could quietly break.

### R2. Three runs — every low end, every high end

* Good, because it is three propagations and needs nothing new.
* Bad, because it is **not even a bound**: with one negative arrow on the map, R → B, the extreme corner is neither the all-low nor the all-high corner — the true box runs .158–.567 against this design's .19–.50. And no version it reports is one anybody believes.

### R3. Twenty batches of five hundred

* Good, because it is record 0005's own reading, and it is one loop.
* Bad, because it measures the machine: a quarter of its width is coin-flip noise, the band is 28 per cent too narrow, and it wobbles ±.02 between seeds.

### R4. Analytic first-order arithmetic as the engine

* Good, because it is accurate to .004 on the fixture and has no seed wobble at all.
* Bad, because it costs one propagation per stated range — 50× slower here — and produces no worlds, so FR-24's payoff distribution, the tail rows and the wipe-out chance have nothing to read. Kept as a test.

### R5. No range on a computed number

* Good, because it claims nothing it cannot defend.
* Bad, because it breaks INV-7 and NFR-1 outright and deletes the one signal that says where more homework would pay, which is FR-21's whole job.

### Four formalisms considered and set aside

* **Subjective logic** — the most attractive presentation of "wider means less sure", but its deduction is unsound where two claims share an ancestor, which is the normal case here.
* **Credal networks** — exact and principled, and NP-hard beyond binary polytrees; our maps are neither.
* **Probability boxes** — rigorous only while each quantity appears once; a shared ancestor appears twice and the guarantee is gone.
* **Dempster–Shafer belief functions** — combining them is #P-complete, and the extra power buys nothing a range does not already say.

## More Information

* **Kent's decisions, 2026-09-17**, taken in a structured question-and-answer after two independent Opus reviews; recorded in `plans/STATUS.md` under *2026-09-17 (evening)* and its follow-up.
* **Kent, 2026-09-17, on the example map:** *"Anything canned or predetermined can be fudged a little. The demo should actually use the system or recordings of the system."* Record 0012 applies the same rule to generation transcripts.
* **`plans/notes/2026-09-17-range-on-computed-beliefs-research.md`** — the measured comparison against exact enumeration, the curve fit, the noise-correction identity, the variance shares, and the chip wording this record adopts.
* **Second-order Monte Carlo** is the standard name for two loops of this shape: Cullen & Frey, *Probabilistic Techniques in Exposure Assessment* (1999); Vose, *Risk Analysis* (2000); the United States Environmental Protection Agency's *Guiding Principles for Monte Carlo Analysis* (1997); Der Kiureghian & Ditlevsen, "Aleatory or epistemic? Does it matter?" (2009).
* **Input to a stack 04 decision, not a decision here — stated ranges from language models are reliably too narrow.** FermiEval (2025): a nominal 90 per cent range covered the truth 28 per cent of the time; QuantSightBench (2026) reproduced it; Paleka et al. (ICLR 2025) found stated ranges incoherent under rewording; Farquhar et al. (*Nature*, 2024) found measured disagreement across runs beats self-report; Halawi (2024) and the AIA Forecaster (2025) both ensemble. The likely shape: a trimmed mean for the point, and the wider of the stated range and the measured spread for the range, the measured number being *agreement*.
* **Related records.** ADR-0004 (a `do` is a timed assertion — the warrant for decision A) and its 2026-09-17 amendment; ADR-0005 (amended here in three places, not superseded); ADR-0008 (which owns test names); ADR-0012 (recordings of the system stand in for the system).
* **Chapters bound by this record.** `spec/multiverse/propagation.md` and `spec/multiverse/diff.md` are written in stack 03a and cite this record; they are not written here.

## Amendment (2026-09-17) — the direction is read with the number's own weights

Section **F** already says that under an `observe` each version is weighted by its own survival share. Section **D** said how a change counts as shifted without saying how the versions are counted while that happens, and the engine read the direction with every version counted as one vote. This amendment says how they are counted. **Nothing in the decision changed** — the two loops, the band, the noise correction, the 90% bar and the eight worlds per version are all as they were, and every measurement above stands exactly as it was taken. Amended in place, as record 0008 was, rather than superseded.

**What was measured.** Hormuz, seed `20261001`, the shipped **2 000 versions × 8 worlds**, comparing the base world with `Observe(target="B", value=True)`. Re-run by the coordinator on 2026-09-17 and re-measured on the same day by the agent who made the change:

| | |
|---|---|
| Versions with **no surviving world** at all | **209 of 2 000** |
| M1 and M2, every version counted as one vote | **89.05%** — a hair under the 90% bar, so both read `unchanged` and the change list was empty |
| M1 and M2, each version counted by how much it survived | **98.66%** — both `shifted`, both on the change list |
| M1 and M2, among the versions that survived, one vote each | **99.44%** |

A version with no surviving world reports nothing to the number and nothing to the band, because its weight is zero. Counted as one vote each, all 209 of them voted against the direction.

**The rule (Kent, 2026-09-17).** *Read the direction with the same weights the number was read with.* A version counts for a move by as much as it counted for the two numbers — the smaller of the two weights it carried — so a version with no surviving world counts for nothing and does not vote. A claim the observation is not evidence about is read with every version counting the same, on both sides, exactly as its number is. If nothing survived anywhere, every version counts the same again, which is what section B's band already does in that corner.

**What it does not change.** **Worlds per version stays 8**, and the **90% bar of section D is untouched**. Under the five edits that are not an observation every weight is 1, so nothing else moves by a bit — pinned by computing one such difference both ways and requiring identical bytes, never by comparing against a typed-in number.

**Kent chose this on 2026-09-17** over the alternative of **running more worlds under each version while an observation is in force**. The noise does fall as the survivors grow, but that buys steadiness with time and leaves the arithmetic wrong: a version that contributed to neither number would still be voting on the direction. The cheaper rule is also the correct one.

**A consequence, decided the same day.** A claim with **no causes** is its own prior in every world of a version, so throwing worlds away cannot change what a version says about it: every version that counts gives it the identical number in both worlds, and its same-direction share is zero by construction rather than by disagreement. Its reported number still moves, because the versions are counted differently — `Observe(target="C", value=True)` moves the hypothesis H from `.356` to `.365`, nearly twice the `0.005` floor. **The four states of section D stay as they are**; the claim's row carries one field saying the move was nothing but the reweighting, and the Inspector prints one sentence: *"this claim moved only because the observation made some versions count more."*

**Confirmation.** `test_an_observation_puts_a_row_on_the_rail` · `test_a_dead_version_does_not_vote` · `test_direction_is_read_with_the_numbers_own_weights` · `test_an_edit_that_is_not_an_observation_is_unchanged_by_the_weights` · `test_a_claim_moved_only_by_reweighting_says_so`, all in `backend/tests/unit/domain/test_diff.py`. `spec/multiverse/diff.md` states the rule once, in B3, and closes its open question 7 with it.

## Second amendment (2026-09-21) — decision A is reversed, and the band's machinery changes while its meaning does not

**In force from 2026-09-21**, when Kent accepted records 0016 and 0017 (decisions note, row R32). It is the first amendment to this record that **reverses** part of it, so it is written here rather than as a quiet edit: a reader who knew decision A must be told it is gone and why.

**Nothing measured for this record was rewritten.** The figures in sections B and C were taken on the engine of 2026-09-17 and stand as taken. Every one of them moves when the new engine's default is flipped, and the diff of one generated numbers file is what states the new ones.

### Decision A is reversed by record 0017

Gone: the rule that a supposition *"stops holding on the day the cause of the first live arrow pushing against it becomes true"*; the three-state table of **supposed · withdrawn · pushed** and the sentences that go with it; the `Retracted · date · by "…"` badge; the `withdrawn` and `pushed` day-states; and the two confirmation tests `test_retraction_dates_from_the_cause_not_the_push` and the Hormuz golden series that pins the retraction date.

**Why.** The rule as written is coherent. What shipped is not: it ends a supposition on a **calendar** worked out from the shape of the map, without ever asking whether the thing pushing back happened or how hard it pushes. Measured on 2026-09-21: insert a claim the map gives one chance in a thousand, carrying an arrow of `−0.01`, into a supposed claim, and the tile **never reads *Supposed* on any day** — its day-states run `withdrawn, withdrawn, pushed, …` from day zero.

**What stands.** *"While a `do` holds, the claim is true in every simulated world — a hard fact, not a strong push"*, and *"the tile shows the words **Supposed · date**, never a number"*. Both are unchanged. What record 0017 changes is that **nothing ends a supposition but another edit**: the strike no longer un-happens the opening, and what falls instead is a **state** — *the strait stays open to commercial transit through 1 November* — which is the claim everything downstream was resting on.

### Section B's machinery is replaced by record 0016; its meaning is not

**What `lo` and `hi` mean does not change**, and that is the whole point of this record: they stay the 10th and 90th percentiles of the likelihood itself, a wide range still never means the event is more volatile, and a stated `{p, lo, hi}` still defines a bell curve on the log-odds scale with its two halves fitted separately. The **two kinds of not-knowing kept apart** is the decision, and it survives intact.

What is replaced is how the band is worked out:

* **The inner loop goes.** *"Run eight worlds under each version"*, and with it the whole of **the noise correction** — the `f = square root of max(0, 1 − …)` block and its glossary of `m`, `q_k`, `v_k`, `V`, `f`, `p̄`, `q10`, `q90`. Under an exact core a version has one exact answer, so there is no sampling wobble to subtract and nothing to clamp. The band becomes the 10th and 90th percentiles of the exact answers across versions, with no correction.
* **`m ≥ 2` disappears** as a constraint, and so does the *"Bad, because … a future performance tweak could quietly break it"* consequence it earned.
* **How many versions stays at two thousand.** It was chosen for a sampler that no longer exists, so the spike re-measured it from first principles and it comes out the same: at 2 000 a band end wanders `.0086` on a wide band, where at 200 — the count the engine digest proposed — it wanders `.0275`, a tenth of the band's own width. Two conditions travel with that measurement and record 0016 carries both: it was taken **at 12 slices and under the rate model record 0016 has since replaced**, so the number could move; and what 2 000 buys is a *narrow* band's ends to two significant figures — a band `.25` across needs about 6 000.
* **What a version varies is unchanged, and what it varies is now a rate.** A version still draws every claim's likelihood from its own stated range and never a lag, a shape or a half-life. Under record 0016 those numbers calibrate an **additive** rate — causes add to it, each an independent route — rather than a log-odds push read on one day, so the shape integrals are computed once for a whole range and a version enters as a scalar.
* **Two seed streams stay two.** The versions stream still never depends on the branch, so base and branch still see the same versions and can be compared version by version — which is what decision D rests on. The worlds stream stops being part of the answer and becomes the stream the forward sample of event times is drawn from, for the trade.
* **Section F goes entirely** — *"reject the worlds inconsistent with what was observed"*, the weighting of each version by its survival share, and *"warn loudly when fewer than about 2 per cent of worlds survive"*. Nothing is thrown away, so nothing starves and there is nothing to warn about. With it, the **2026-09-17 amendment above becomes vacuous**: every version carries weight 1 under every edit, so *"read the direction with the same weights the number was read with"* is satisfied trivially, and `moved_only_by_reweighting` is always false and is deleted at the flip. Its rule was right and the reason it was needed is gone.
* **Section C keeps its quantity and changes its method.** Each stated range's share of a claim's band is still the thing FR-21 ranks by; it is computed by re-solving with one range frozen — one extra exact solve each — rather than by binning versions. Its measured Hormuz figures move at the flip.
* **Section D's two thresholds stand**: `.005` of movement, and the same direction in at least 90% of versions. Nothing about what counts as *shifted* changes.

### The two warts this record admitted are both removed

1. **Section E's wart** — *"A path's multiplied-out likelihood (INV-8, the conjunctive honesty bar) multiplies numbers each read on a different day. It is still the most honest single number available for a chain, and it is not a joint probability."* Record 0016 stops computing it. INV-8 becomes *"chains are worked out, not multiplied"*, and the Verify door reports the shift the hypothesis makes, the chance every step on the route goes right as a true joint, and which arrow carries most of the shift. Section E's rank — size of the move times the weakest backing on the best-backed route — is untouched.
2. **The consequence bullet** beginning *"Neutral, because a tile read on the claim's own resolve-by day meets spike-shaped pushes that have mostly faded, so computed numbers land near their priors."* Under record 0016 an impulse's whole area counts, so the answer no longer depends on where a deadline falls against a half-life. Attacked deliberately with short impulses landing just before a deadline, the gap between this design and an exact answer was `.0000` to `.0001` (the adversarial pass of 2026-09-21). **The permission that bullet carries stands and is not weakened**: the example map may still be curated, each tuned value saying why, and its closing rule is untouched — *"every number shown in a demo comes from the engine itself or from a recording of the engine, never typed by hand"* (Kent, 2026-09-17, quoted from the bullet above).

One more bullet is restated rather than removed: *"the mean sits a hair above the middle for `p < .5`"*. Its cause changes — it was the extra averaging over eight worlds, and under an exact core what is left is the curvature of the map across versions. Whether the Hormuz figure `.35 → .36` survives is a fact the flip's generated numbers file will state; this amendment does not assert it.

### What is untouched

Decision **D** (how a change counts as shifted, and *agreement*), decision **E** (the rank, and which day a number is read on — a tile's headline is still read on the claim's own resolve-by day, which under record 0016 is the only day it could be read on), and decision **G** (the provenance-derived spread, landing in stack 04; and *"there are no `strength_lo` / `strength_hi` fields, ever"*). The *Pros and Cons* of all nine options, and the four formalisms set aside, stand as written: they were the reasons for a decision whose meaning this amendment preserves.

---

## Third amendment, 2026-09-22 — the range itself is cut, by decision record 0028

**In force from 2026-09-22** (Kent, decisions note row R48). Appended, like the two amendments above, so the record still reads as it was decided.

**The second amendment kept this record's meaning and replaced its machinery.** This one removes the meaning as well. **Decision B — what a range on a computed number means — is reversed.** There is no range on any number this product shows: not on a tile, not in the panel, not on the change list, not in a footer sentence and not in a hover note. `lo` and `hi` cease to be percentiles of anything; they stay on the wire equal to `p` until one follow-up pull request takes them out. Kent's reason, in his own words, is quoted in record 0028.

**What goes with decision B:**

* **The two thousand versions of the map**, and everything that made them differ — a claim's likelihood drawn from its stated range, the split fitting of `{p, lo, hi}` on the log-odds scale, and the even spreading of the draws.
* **Decision C, the variance shares** — whose stated number explains whose width. There is no width. FR-21 is not built in version one.
* **Decision G's provenance-derived spread** — *how well-backed an arrow is becomes how wide it is drawn*. It existed only to make versions differ. **The other half of G stands and is now permanent: there are no `strength_lo` / `strength_hi` fields, ever.**
* **The second half of decision D.** A claim counted as `shifted` when it moved by `.005` **and** at least 90% of versions moved the same way. The second half was a share **of versions** and goes with them; the `.005` floor is now the whole test, and an `unchanged` claim has one reason where it had two.

**What stands.** Decision A's surviving half — a supposition is a hard fact in every reading while it holds, and the tile shows **Supposed · date**, never a number (its other half was reversed by record 0017). Decision E in full: the ranking is the size of the move times the weakest backing on the best-backed route, and a tile's headline is read on the claim's own resolve-by day. **Two significant figures and both guards.** And this record's own closing rule, untouched: *every number shown in a demo comes from the engine itself or from a recording of the engine, never typed by hand.*
