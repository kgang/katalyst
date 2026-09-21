---
# ADR-0019: A stop is a price the reader owns; what the map derives is what takes you out and what to watch
status: accepted
date: 2026-09-21
decision-makers: Kent Gang
consulted: Kent's decisions of 2026-09-21 (rows R10, R28 and R29 of plans/notes/2026-09-21-decisions-after-review.md); plans/analysis/2026-09-21-digest-finance.md §2.2 and §2.3; plans/analysis/2026-09-21-red-team.md items S2 and S6; plans/analysis/2026-09-21-review-adr-06.md, whose measurements corrected this record's first draft and whose must-fix 8 named the double count; plans/analysis/2026-09-21-priced-in.md, the simulation behind R28; both midpoint reviews, which named the same defect independently
informed: agents working in backend/src/katalyst/thesis; whoever writes the thesis dock and the export; whoever rewrites domain/diff.py's sweep; whoever writes the one shape freeze's prompt, which this record gives one sentence
supersedes: none
superseded-by: none
spec-impact: spec/thesis/position.md (new), spec/thesis/what-takes-you-out.md (new), spec/thesis/card-and-export.md (new), spec/thesis/README.md (the landing page's "derived, not guessed"), PRODUCT_REQUIREMENTS.md INV-14, FR-19, FR-22, FR-23, FR-24, FR-25 and anti-pattern 11
---

# ADR-0019: A stop is a price the reader owns; what the map derives is what takes you out and what to watch

> **Accepted by Kent on 2026-09-21** (decisions note, row R32). His decision R10 settles what this record is about; R28 and R29, taken the same day, are written into it below.

> **In short.** The stop, the target and the horizon are numbers **the reader types**. What the map computes beside them is **what takes you out** — the claims over-represented in the worlds where that stop was touched first, ranked by *lift* — and **what to watch**, the one adverse turn that hurts most, resolves in time, and anybody can see. The simulated price path applies a claim's **surprise** rather than its whole stated move, so it manufactures no advantage of its own (R28). A **quartered Kelly ceiling** at the unfavourable end of the model's range sits greyed beside the reader's own arithmetic, labelled *never size to this* (R29).
>
> **On screen.** Four sections where there was one, plus a form. Measured: today's path reads *the target is reached first* at `.3794` where the honest rule reads `.2594`.
>
> **What it costs.** The product stops answering *"where should my stop be?"* at all. About seventy lines of new arithmetic; the renaming is copy.
>
> **Open for Kent.** Nothing — R10, R28 and R29 are all written in, and he accepted the record with them.

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

### What the path applies, now that today's price already carries part of it

A claim's **whole** stated move, applied to a path that starts from today's price, counts that move twice: today's price already reflects the market's own chance of the claim. Kent declined to fix that by asking the reader. **His words (R28):** *"I'm not sure that the reader can be relied upon to state how much is priced in. Can this be a quantitative analysis component that's assisted or handled by katalyst itself?"*

**The rule.** Write `q` for the market's chance of the claim and `m` for its stated move. When the claim comes true the price moves by the **surprise**, `m × (1 − q)`; while it has not happened, the price gives back the priced-in part, `m × q` in total. Under the model's chance `p` the window's expected move is then `m × (p − q)` — the edge, and **zero when the model and the market agree**, which the old rule never was.

**The giveback is paid day by day, not on the deadline.** Every schedule from `q` down to nothing has the same total, so the total cannot choose between them, and a first touch is about the way there. The one chosen leaves the price fair *on every day*: it follows **the model's own distribution of the day the claim arrives**, which `Draws` already carries, rescaled to `q`. One histogram, no new input.

**Where `q` comes from, in order.** A **venue quote on that claim**, where the contract asks the claim's own resolution test (record 0020's curation rule). Otherwise **the model's own number from the world with no fixed value in force** — the neutral assumption that the market believes what the model believes. The reader **may** override it, never must. **The card names the source used, in the same sentence as the number.** With `q` from the model the base world's path carries no drift at all, so every point of advantage on a supposed screen came from what the reader supposed or observed.

**Measured** (`plans/analysis/scripts/finance/priced-in/priced_in.py`, seed `20260921`, 200 000 worlds, thirty days, a claim worth eight points, stop three below and target six above, model agreeing with market, variants sharing their random numbers):

| | expected move | *target first* | *stop first* |
|---|---|---|---|
| today's rule — the whole move, nothing given back | `+2.789 ± 0.015` points | `.3794` | `.4411` |
| the surprise rule | `−0.011 ± 0.015` points | `.2594` | `.5750` |

Today's rule inflates *target first* by `+.1200 ± .0007`, **46% in relative terms**. The surprise rule's expected move matches `m × (p − q)` within 1.8 standard errors at five model-and-market pairs; paying the giveback in one step on the deadline instead reads *stop first* `.0818` low.

**What it still gets wrong.** The stated move must be a **level gap** between a world where the claim is true and one where it is false — not the reaction on the announcement day, which is already the surprise and would be discounted twice, `2.80` points short at `q = .35`. That is one sentence in the one shape freeze. Moves must be **additive, in price units**: two correlated claims then need only their marginal chances (`−0.010 ± 0.018` points, zero within 0.55 standard errors, so no joint reaches this layer), where the same arithmetic on a percentage move puts back `+1.9%` of drift at 40%. And the decay's **shape is an assumption** — early rather than late arrivals move *stop first* by `.0456` — so the Inspector says which was used. The measurement checks a price path, not the engine: its event days are drawn from a simple distribution, and record 0016's caveat about the day table stands.

**Kent asked for this in R28; it was worked out and measured here, and he accepted it with the record (R32).** Acceptance softens none of the three conditions above — the level gap, additive moves in price units, and a named decay shape.

### The size ceiling the card greys out

**R29 overturns this record's own recommendation and the drafting agent's:** show it. The **Kelly rule** is the bet size that makes capital grow fastest in the long run given a stated edge; it is notoriously aggressive, so dividing it by four is a common working limit among the people who use it at all.

**What is shown:** a **quartered Kelly** worked out at the **unfavourable end of the model's stated range** — the end that makes the edge smallest, never the middle and never the flattering end — greyed, beside the arithmetic on the reader's own risk budget, under the words *never size to this*. It is a ceiling, not a size; the risk budget stays the only number that sets one.

**When it appears.** Kelly needs an edge, and under record 0018 an edge exists only for an ending naming a **venue contract**, with a **live quote**, in a world with **no fixed value in force**. So:

| The case | The ceiling |
|---|---|
| A contract ending, a live quote, nothing fixed by an edit | the number, greyed, labelled |
| The edge's sign differs at the two ends of the model's range (record 0018's second threshold) | **zero**: *the model's own range does not agree which side of this price to be* |
| Any refusal from `priced` — supposed or observed base world, no quote, no contract, settled market | **absent**, printing that refusal's own sentence |
| An ending naming an instrument | **absent**: *a ceiling needs an edge, and no contract quotes this claim* |

Zero and absent are different answers and the card says which. Neither is ever a blank.

### What changes in the requirements

**INV-14** becomes a rule about the *watchlist*, and no claim is presented as a stop. **FR-19** gains one clause: the sweep flips each claim **both** ways. **FR-22** keeps the tail strip and adds the reader-placed shock, reported as the change to the position with **no probability attached**. **FR-23** is rewritten: the exit is typed, and the two lists are computed beside it. **FR-24** keeps the percentile outcomes and the two first-touch chances; expected shortfall, maximum drawdown and probability of ruin are **cut**. **FR-25**'s card fields lose *invalidation* and *take-profit* and gain **six** sections: the four above, plus *what carries it* and *what is priced in* from record 0018. **Anti-pattern 11 is reversed**: do not derive the reader's stop.

Exact replacement wording is held in `plans/notes/2026-09-21-stack-06-docs-owed.md` and lands once the branches editing `PRODUCT_REQUIREMENTS.md` have merged.

### What is cut here

**Expected shortfall** — the average loss in the worst few per cent of outcomes — needs a capital base and reads as theatre beside an uncalibrated model number. **Maximum drawdown** needs a path through a portfolio, not through one position, so the number would be an artefact of the draw count. **Probability of ruin**, with one position, is the chance of the stop renamed. Two further cuts belong to the record listing what version one does not build: a fifth, price-valued kind of claim; two-sided payoffs. **The greyed ceiling is no longer among the cuts** — R29 puts it on the card. A *recommended* size still is: the ceiling recommends nothing, and the only number that sets a size is the reader's own risk budget.

### Where the event days come from, and how good they are

**First touch, lift and the giveback's schedule all read event *days* from a sample of worlds** — the `Draws` shape in `spec/thesis/position.md`, which carries, per drawn world, the day each claim **came on** and the day it **went off**, because Kent's decision R2 makes a claim an event or a state and a state can stop holding.

The spike answered which sample that is: **the engine's own weighted forward sample**, worlds drawn forward carrying event days, with an observed claim set to what was observed and each world weighted by how likely that was. **One sampler, two readers** — the engine reads it for *This happened*, this layer for first touch, lift and the schedule.

**Measured** (`plans/analysis/scripts/spike-05/observe/when_table.py`: 40 maps, every *This happened* on every claim, 24 slices, 200 000 worlds, against a judge that holds the whole joint over days and is therefore exact):

| Each claim's day-it-happened spread against the exact one | mean | worst |
|---|---|---|
| **the weighted forward sample** | **.0023** | **.0064** |
| the alternative: truths from the exact solve, days drawn forward under the prior | .0104 | .2143 |

The measure is total variation distance — half the summed absolute difference between two distributions over days — so `.0064` means under one world in a hundred would have to move. **A median day moves by at most two and a half days**, where the alternative moved one by **ten days**, and a stop-versus-target number would have been wrong by whatever ten days of path is worth.

**The spike's own caveats**, which record 0016 carries in full: the day table was measured on **four-claim maps** under the engine's **first, multiplicative** rate, and round two, which confirmed the weighted sample still wins under the additive rate Kent chose (R18), **did not re-run it**. The `Draws` shape does not depend on the outcome, because a state needs an on day and an off day either way.

So **`Draws.weight` is real, not all ones**, and **the 200-draw floor counts *effective* draws** — how many equally-weighted worlds the weighted sample is worth, measured at **96.7% of those drawn on average and 41.8% at worst** across 1 120 observations.

**Where these numbers come from.** **Record 0016**, accepted the same day, owns the sampler they are drawn from. Independent of it either way: the four things and their names; that the stop is typed; the two-way sweep and the watchlist, which read each claim's number on its own resolve-by day and no days at all; every cut above; and every requirement amendment.

### Open for Kent

**Nothing open.** Both questions this record held are answered: **R28** closed the double count — the path applies the surprise, and Katalyst works out what is priced in rather than asking the reader — and **R29** put the greyed ceiling on the card, overturning this record's own recommendation. Both are written above, and Kent accepted the record with them on 2026-09-21 (**R32**). Declined along the way: asking the reader to state how much is priced in, which was this record's first recommendation and which R28 rules out by name.

### Consequences

* Good, because the brief's most distinctive question gets an answer by computation, and the one indefensible claim in the product is gone; the reader's stop needs no model and no calibration to be right.
* Bad, because the product no longer answers *"where should my stop be?"* at all, and four sections where there was one is more screen.
* Bad, because the greyed ceiling rests on a probability nobody has calibrated, and a reader who ignores the label has been handed a size — the cost Kent took knowingly (R29), bearable because of the unfavourable end and the greying.
* Neutral, because almost none of this is code: the renaming is copy, the two-way sweep about fifteen lines, the lift query forty, the ceiling fifteen, and the surprise rule a different multiplier on a line that was being written anyway.

### Confirmation

* `grep -rn "derived stop-loss\|the stop-loss is derived\|derive it from sensitivity"` over `spec/`, `PRODUCT_REQUIREMENTS.md` and `docs/adr/`, **excluding `docs/research/` and the two records that mention it as history, 0005 and 0012**, returns nothing outside this record's quotations of the old wording.
* `test_a_stop_is_never_derived` — a walk over our own source: nothing outside the position form writes a stop, a target or a horizon.
* `test_the_sweep_flips_both_ways` — every claim gets a row in each direction, and the adverse row for a long position is the one where the ending falls.
* `test_a_claim_held_true_by_an_edit_has_lift_one`, `test_a_lift_row_says_how_many_draws_it_rests_on` — lift one is dropped; no row below the floor; every row carries its count and interval.
* `test_the_stop_is_at_least_as_likely_as_finishing_beyond_it` — the pathwise inequality, which always holds — and `test_a_contract_ending_refuses_first_touch`, by name, with the sentence.
* `test_a_path_has_no_drift_when_the_model_agrees_with_the_market` — the market's chance built from the base world's own number, so nothing is typed in; the window's mean move is zero within the sample's error and the old rule fails the same assertion. With `test_the_applied_move_and_the_giveback_sum_to_the_stated_move`.
* `test_agreeing_with_the_market_gives_a_ceiling_of_exactly_zero` — bid and offer both the base world's own number, zero fee, ceiling `0.0` exactly; built from the world, like its twin in record 0018. And `test_a_wider_model_range_never_raises_the_ceiling` — widening the stated range about the same point never raises it; where the edge's sign differs at the two ends it is zero with its reason; where `priced` refuses, it is absent with that refusal's sentence.
* Review item: every first-touch number on screen names the sample its days came from — *the engine's weighted forward sample* — and which source the market's chance came from; the export carries the same words.

## More Information

* **Accepted by Kent on 2026-09-21** (decisions note, row R32), with records 0016–0022.
* **Kent's decision, 2026-09-21, row R10:** the reader's own price, plus two computed lists — *what takes you out* by lift, *what to watch* as the honest remnant of INV-14, and *your exit* typed and never derived. **Row R28:** Katalyst works out what is priced in; the reader is not relied on. **Row R29:** the greyed ceiling is shown, quartered Kelly at the unfavourable end of the model's range, labelled *never size to this*.
* `plans/analysis/2026-09-21-digest-finance.md` §2.2 (lift, the draw floor) and §2.3 (the ceiling as first proposed) · `plans/analysis/2026-09-21-red-team.md` S2 and S6 · `plans/analysis/2026-09-21-review-adr-06.md` (the reflection measurement, the lift correction, and must-fix 8, which named the double count) · `plans/analysis/2026-09-21-priced-in.md` (the simulation behind R28).
* Related: **0013** (a payoff names the trade), **0018** (the edge, why a supposed world prices nothing, and the model-range threshold the ceiling reuses), **0020** (where a quote comes from, and the rule that a contract must ask the claim's own question), **0016** (the engine, whose weighted forward sample supplies the arrival days the giveback's schedule reads) and **0017** (a claim is an event or a state). Nothing else here depends on a number either of the last two states.
* Measurement scripts: `plans/analysis/scripts/finance/check_stop_claims.py`, the review's `first_touch_reflection.py` beside it, and `plans/analysis/scripts/finance/priced-in/priced_in.py` with its saved output.
