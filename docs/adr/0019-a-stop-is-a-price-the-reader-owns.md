---
# ADR-0019: A stop is a price the reader owns; what the map derives is what takes you out and what to watch
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted: Kent's decision of 2026-09-21 (row R10 of plans/notes/2026-09-21-decisions-after-review.md); plans/analysis/2026-09-21-digest-finance.md §2.2; plans/analysis/2026-09-21-red-team.md items S2 and S6; plans/analysis/2026-09-21-review-adr-06.md, whose measurements corrected this record's first draft; both midpoint reviews, which named the same defect independently
informed: agents working in backend/src/katalyst/thesis; whoever writes the thesis dock and the export; whoever rewrites domain/diff.py's sweep
supersedes: none
superseded-by: none
spec-impact: spec/thesis/position.md (new), spec/thesis/what-takes-you-out.md (new), spec/thesis/README.md (the landing page's "derived, not guessed"), PRODUCT_REQUIREMENTS.md INV-14, FR-19, FR-22, FR-23, FR-24, FR-25 and anti-pattern 11
---

# ADR-0019: A stop is a price the reader owns; what the map derives is what takes you out and what to watch

## Context and Problem Statement

The roadmap has always promised a **derived stop-loss**: `spec/thesis/README.md` said the flip that damages an ending most, and resolves before it, and can be seen publicly, *"is the stop-loss, and it is derived, not guessed"*, and `PRODUCT_REQUIREMENTS.md` says the same in INV-14, FR-23 and anti-pattern 11 — *"do not type the stop-loss by hand."*

On this project's own worked example that derivation produces nothing a trader could use, for two measured reasons below. Behind them sits a plainer problem: **four different things are called "the stop-loss"** — what would prove the argument wrong, what would hurt the position badly, the price at which the reader gets out, and the order that gets them out. So: **what does this product derive, what does the reader type, and what do we stop calling a stop?**

## What was measured, and how to re-run it

Script: `plans/analysis/scripts/finance/check_stop_claims.py`, against `main` at `48eb562` with the shipped seed.

**1. The dates leave one claim, and it is the step the trade rests on.** Day zero is 2026-10-01; the contract ending **M1** resolves 2026-10-31; the only claim resolving *strictly before* it is **B**, *Brent crude settles below $68 for five sessions*, on 2026-10-15 — the causal step the thesis rests on. Everything else resolves on the same day or later. So the derived "stop" reads *get out if the thing you are betting on stops being true*: a restatement of the position, not a warning about it. (The second ending has four claims before it, so the filter is not always empty — the defect is structural.)

**2. The sweep only flips one way.** `sensitivity()` in `backend/src/katalyst/domain/diff.py` flips each claim *"to the opposite of whichever way it more often comes out"* — one direction per claim, chosen by which side of one half it sits on. Measured: all seven claims sit below one half, so all seven rows flip the claim **to true**. For a reader who is long, the damaging direction of **the claims the thesis rests on** — the strait not opening, Brent not falling — is never computed. (Not every claim: the OPEC+ arrow pushes the oil claim *down*, so flipping that one to true is already adverse. The rule is the defect, not the numbers: the reader's side is never consulted.)

## Decision Drivers

* **Every number can say why.** A derived stop is a price nobody computed, standing where the reader's own risk rule belongs.
* **Kent's decision, 2026-09-21 (row R10 of the decisions note):** the reader's own price, plus two computed lists. This record writes that down rather than re-arguing it.
* **Do not name a thing after something it is not.** A ranking of flips is a watchlist; the brief's most distinctive sentence — *what events could lead to stop losses* — deserves an answer by arithmetic instead.
* **Only build what the inputs support.** Expected shortfall, drawdown and ruin need a capital base and a portfolio this product does not have.

## Considered Options

| | Option | Verdict |
|---|---|---|
| **A** | **Four things, kept apart on the card: what takes you out · what to watch · your exit · execution** | **Chosen.** Each gets its own name, owner and arithmetic |
| B | Keep the wording; derive a stop from the sweep as written | It names the trade's own supporting claim on the flagship ending, and the sweep behind it never computes the reader's adverse direction |
| C | Derive only where the filter leaves an independent claim | Half the cases print nothing, the reader still has no stop, and the word still means four things |

## Decision Outcome

Chosen option: **A**.

| On the card | What it is | Who owns it | How it is worked out |
|---|---|---|---|
| **What takes you out** | The claims over-represented in the worlds where the reader's stop was touched **first** | computed | **Lift** — see below. Ranked, each row carrying an interval, the number of drawn worlds behind it, and the typical days between the claim happening and the stop being touched |
| **What to watch** | The adverse flip that damages the ending most, **and** resolves before it, **and** can be seen publicly | computed | The sweep, flipped **both** ways, keeping the adverse row for the reader's side, then INV-14's two filters. A watchlist, not a stop |
| **Your exit** | The stop, the target and the horizon | **the reader types them** | Never derived |
| **Execution** | The one thing we will say about getting out | ours | One sentence on the card and nothing else: *a stop order's trigger is not its fill price.* This is not an execution layer |

**Unhedgeable stays.** A claim that damages the ending but resolves after it, or cannot be seen, is listed under that word with its reason and never used as a stop — which is what INV-14 was reaching for.

### Lift, exactly

Among the worlds where the stop was touched first, how often had this claim **already happened before the stop was touched**? Divide by how often the claim happened across all drawn worlds. Three means three times as often; one means it tells you nothing.

*Before the stop* is load-bearing: a claim that happened afterwards cannot have contributed, and counting it inflates the rail in the flattering direction. Both shares are **weighted**, because the sample below is a weighted one. The interval is a **Wilson interval** — the standard interval for a share, sensible at small counts — **on the numerator share only**, and no coverage is claimed for the ratio itself. A claim an edit holds true has lift one by construction and is dropped. **The 200-draw floor is chosen, not measured**, carried over from the finance analysis because some floor is needed; it counts **effective** draws, and what would replace it is the count at which the top rows stop changing order between seeds.

### First touch, and what it is honest about

The chance of the stop or the target being reached first is read by walking a **daily** path through each drawn world. Two things are said wherever that number appears. **A daily check misses touches between closes**, so a naive daily count understates being stopped out; the stated method is the standard discrete-monitoring correction, the **barrier shift** — move the stop a little way toward the starting price, by an amount growing with the volatility and the step, so a daily count matches what continuous watching would have found. And **a contract ending has no first touch in version one**: a probability does not follow a price-path model, and the reader has no volatility to give for one. A contract is held to resolution, and the card refuses the question on it by name.

The inequality that *is* always true — the stop is touched at least as often as the outcome finishes beyond it — is what the test asserts. The first draft also asserted a ratio of two, from the reflection principle; that is a continuous-monitoring result, it fails at every draw count above the floor (`plans/analysis/scripts/finance/review/first_touch_reflection.py`), and it is withdrawn.

### What changes in the requirements

**INV-14** becomes a rule about the *watchlist*, and no claim is presented as a stop. **FR-19** gains one clause: the sweep flips each claim **both** ways. **FR-22** keeps the tail strip and adds the reader-placed shock, reported as the change to the position with **no probability attached**. **FR-23** is rewritten: the exit is typed, and the two lists are computed beside it. **FR-24** keeps the percentile outcomes and the two first-touch chances; expected shortfall, maximum drawdown and probability of ruin are **cut**. **FR-25**'s card fields lose *invalidation* and *take-profit* and gain **six** sections: the four above, plus *what carries it* and *what is priced in* from record 0018. **Anti-pattern 11 is reversed**: do not derive the reader's stop.

Exact replacement wording is held in `plans/notes/2026-09-21-stack-06-docs-owed.md` and lands once the branches editing `PRODUCT_REQUIREMENTS.md` have merged.

### What is cut here

**Expected shortfall** — the average loss in the worst few per cent of outcomes — needs a capital base and reads as theatre beside an uncalibrated model number. **Maximum drawdown** needs a path through a portfolio, not through one position, so the number would be an artefact of the draw count. **Probability of ruin**, with one position, is the chance of the stop renamed. Three further cuts belong to the record listing what version one does not build: a fifth, price-valued kind of claim; two-sided payoffs; automatic sizing.

### Where the event days come from, and how good they are

**The first-touch and lift numbers read event *days* from a sample of worlds** — the `Draws` shape in `spec/thesis/position.md`, which carries, per drawn world, the day each claim **came on** and the day it **went off**, because Kent's decision R2 makes a claim an event or a state and a state can stop holding.

The spike answered which sample that is. **They come from the engine's own weighted forward sample**: worlds drawn forward carrying event days, with an observed claim set to what was observed and each world weighted by how likely that was. **One sampler, two readers** — the engine reads it for *This happened*, and this layer reads the same worlds for first touch and lift.

**Measured** (`plans/analysis/scripts/spike-05/observe/when_table.py`: 40 maps, every *This happened* on every claim, 24 slices, 200 000 worlds, against a judge that holds the whole joint over days and is therefore exact):

| Each claim's day-it-happened spread against the exact one | mean | worst |
|---|---|---|
| **the weighted forward sample** | **.0023** | **.0064** |
| the alternative: truths from the exact solve, days drawn forward under the prior | .0104 | .2143 |

The measure is total variation distance — half the summed absolute difference between two distributions over days — so `.0064` means under one world in a hundred would have to move. **A median day moves by at most one slice, two and a half days**, where the alternative moved one by **ten days**, and a stop-versus-target number would have been wrong by whatever ten days of path is worth.

**The spike's own caveats.** The day table was measured on **four-claim maps** under the engine's **first, multiplicative** rate. Round two confirms the weighted sample still wins under the additive rate Kent chose (R18), at 50 000 worlds rather than 200 000, but **did not re-run the day table**. The states half of the spike is being re-run under that rate too; the `Draws` shape does not depend on the outcome, because a state needs an on day and an off day either way.

So **`Draws.weight` is real, not all ones**, and **the 200-draw floor counts *effective* draws** — how many equally-weighted worlds the weighted sample is worth, measured at **96.7% of those drawn on average and 41.8% at worst** across 1 120 observations.

**What this record still waits for.** It stays `proposed` until **proposed record 0016 is accepted**, because that record owns the sampler these numbers come from. Independent of it either way: the four things and their names; that the stop is typed; the two-way sweep and the watchlist, which read each claim's number on its own resolve-by day and no days at all; every cut above; and every requirement amendment.

### Open for Kent

**1. The simulated path double-counts what the spot already prices.** Applying a claim's full stated move whenever it fires, on a path starting from today's price, counts the move twice — the starting price already reflects the market's own chance of that claim — so the simulation manufactures a favourable drift, and it lands on the chance of the target being reached first.

* **Recommended: the reader states how much of the claim the spot already prices** — one number on the position form, theirs like the stop, and the path applies only the remainder. Cost: one more field, and a reader who leaves it at zero gets the flattering answer. It is the only option both honest and computable from what we have.
* Alternative: the card states the assumption in one sentence and the arithmetic does nothing — the headline number is then known to be optimistic with only a footnote saying so.
* Settled when 06-2 is planned either way, because it moves with whatever the spike says about event times.

**2. A greyed sizing ceiling, or nothing?** The finance analysis proposed showing, beside the reader's risk-budget arithmetic, a **quarter-Kelly ceiling** — the Kelly rule is the bet size that grows capital fastest given an edge, notoriously aggressive, so a quarter of it is a common working limit — computed at the pessimistic end of the model's stated range and labelled *never size to this*.

* **Recommended: leave it out of version one.** Cost: a reviewer looking for a sizing discipline finds only arithmetic on the reader's own numbers. Reason: a number nobody may act on still has to say why, and this one would rest on an uncalibrated probability.
* Alternative: show it, greyed, with the label. About fifteen lines and one more number to defend.

### Consequences

* Good, because the brief's most distinctive question gets an answer by computation, and the one indefensible claim in the product is gone; the reader's stop needs no model and no calibration to be right.
* Bad, because the product no longer answers *"where should my stop be?"* at all, and four sections where there was one is more screen.
* Neutral, because almost none of this is code: the renaming is copy, the two-way sweep is about fifteen lines inside the existing sweep, and the lift query about forty.

### Confirmation

* `grep -rn "derived stop-loss\|the stop-loss is derived\|derive it from sensitivity"` over `spec/`, `PRODUCT_REQUIREMENTS.md` and `docs/adr/`, **excluding `docs/research/` and the two records that mention it as history, 0005 and 0012**, returns nothing outside this record's quotations of the old wording.
* `test_a_stop_is_never_derived` — a walk over our own source: nothing outside the position form writes a stop, a target or a horizon.
* `test_the_sweep_flips_both_ways` — every claim gets a row in each direction, and the adverse row for a long position is the one where the ending falls.
* `test_a_claim_held_true_by_an_edit_has_lift_one`, `test_a_lift_row_says_how_many_draws_it_rests_on` — lift one is dropped; no row below the floor; every row carries its count and interval.
* `test_the_stop_is_at_least_as_likely_as_finishing_beyond_it` — the pathwise inequality, which always holds — and `test_a_contract_ending_refuses_first_touch`, by name, with the sentence.
* Review item: every first-touch number on screen names the sample its days came from — *the engine's weighted forward sample* — in the same sentence, and the export carries the same words.

## More Information

* **Kent's decision, 2026-09-21, row R10:** the reader's own price, plus two computed lists — *what takes you out* by lift, *what to watch* as the honest remnant of INV-14, and *your exit* typed and never derived.
* `plans/analysis/2026-09-21-digest-finance.md` §2.2 (the table, the lift definition, the draw floor) · `plans/analysis/2026-09-21-red-team.md` S2 and S6 · `plans/analysis/2026-09-21-review-adr-06.md` (the reflection measurement and the lift correction).
* Related: **0013** (a payoff names the trade), **0018** (the edge, and why a supposed world prices nothing), **0020** (where a quote comes from). **Records 0016 and 0017 are forthcoming**; nothing here depends on a number either will state.
* Measurement scripts: `plans/analysis/scripts/finance/check_stop_claims.py`, and the review's `first_touch_reflection.py` beside it.
