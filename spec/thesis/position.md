# Position — the reader's trade, their exit, and the one thing this layer asks of the engine

## Purpose

A trade needs something bought or sold, a size, and a point at which the reader gets out. None of those is derivable from a map of claims, so **the stop, the target and the horizon are numbers the reader types**, and what the map computes beside them is how often each is reached first. A reader can now say *I am short this at today's price, out at 3% against me, target 6% for me, by the end of October*, and be told how often each of those happens first.

---

## Data model

Three modules in `backend/src/katalyst/thesis/`, all outside `domain/`, which gains nothing from this part.

**`position.py` — `Position`.** What the reader types: which ending it trades; the instrument or contract, taken from the claim's own payoff so it cannot disagree with the map; the side; the entry price; the **stop**; the **target**; the **horizon**; and a **risk budget**, the share of their capital they are prepared to lose on this trade. Every field is theirs. An ending naming an **instrument** trades in that instrument's own price, anchored on a dated spot reading; an ending naming a **contract** trades in probability, and gets no path and no first touch in version one (B3).

**`draws.py` — `Draws`**, the only thing this part asks of the engine: the day the window starts and how many days it runs; the claims in a fixed order; for each drawn world and each claim, the day it **came on** and the day it **went off**, with markers for *never* and *still holding*; and a **weight** per drawn world.

Two days, not one, because a claim is an event or a state. An event that has happened never un-happens, so its off-day is always *still holding*; a state can stop, and with one day a state that held three days and stopped would be indistinguishable from one still running. That is the whole of what a state needs from the sample, and every consumer would otherwise inherit the hole. *(The states work is being re-run under the engine's new rate; this shape does not depend on the outcome, because a state needs an on day and an off day either way.)*

**Where the days come from.** They are the engine's own **weighted forward sample**: worlds drawn forward carrying event days, with an observed claim set to what was observed and the world weighted by how likely that was — one sampler, two readers. Measured against an exact answer, each claim's day-it-happened spread is `.0023` away on average and `.0064` at worst, and a median day moves by at most two and a half days, where the design that drew days from tables built before the evidence moved one by ten. **So the weight is real, not all ones**, and every count here is a weighted one. Record 0019 carries the table, the script and the caveats; every first-touch number on screen names the sample it rests on.

**`paths.py` — a daily path.** For each drawn world, a price path for the traded instrument: a **random walk with no built-in upward or downward tendency**, stepping at the instrument's own day-to-day variability, with each claim's stated move applied on the day it came on. A path exists for one reason: a stop is path-dependent, and a distribution of end-of-window outcomes cannot answer a question about the way there.

---

## Behaviour

### B1 — The reader types a position

On the Hormuz map they select the ending they want to trade and fill in the form; instrument and side come from the claim's payoff and are shown, not typed. A position is not an edit to the map: nothing moves on the canvas, and it appears on no branch.

### B2 — First touch

**First touch** means walking each drawn world's path day by day and recording which of the stop and the target is reached first, counting a level as reached the moment the path touches it. A stop hit on day three is hit even if the price finishes the month above it, and any method that looks only at the end of the window understates being stopped out — in the flattering direction.

Two honesty rules travel with the number. A **daily** check misses touches between closes, so the stated method applies the standard discrete-monitoring correction, the **barrier shift**: the stop is moved a little way toward the starting price, by an amount growing with the instrument's variability and the step, so a daily count matches what continuous watching would have found. And when a day's step crosses **both** levels the **stop** is taken as first — the only reading that cannot flatter the trade.

### B3 — A contract ending has no first touch

A probability does not follow a price-path model: a random walk leaves the zero-to-one range, the contract's truth in a drawn world is already known from the draw, and the reader has no day-to-day variability to give for it. **A contract is held to resolution**, and the card refuses the question by name rather than answering it badly.

### B4 — An ending that names an instrument is a trade too

The recorded Hormuz map — the one the walk opens, committed at `backend/recordings/hormuz.jsonl` — has eleven tradeable endings and **every one names an instrument**. So one gets a position, a daily path, first touch, and the break-even an entry price makes computable, beside the honest line that no contract quotes the claim.

### B5 — What the form refuses, and what it implies

Refusals read like the map's own validity rules: a stable code, the field at fault, one plain sentence, nothing silently repaired.

| Code | The sentence |
|---|---|
| `stop_on_the_wrong_side` | "A stop protects you; this one is where the trade is already working." |
| `target_not_beyond_entry` | "A target you are already at is not a target." |
| `horizon_after_the_claim` | "This claim is settled before your horizon; the trade cannot still be open." |
| `risk_budget_out_of_range` | "A risk budget is the share of your capital you are willing to lose." |
| `price_outside_the_contract` | "A contract's price is between nothing and everything." |
| `first_touch_on_a_contract` | "A contract is held to resolution; there is no path to touch." |

Given a risk budget and the distance from entry to stop, the size that loses exactly that budget is arithmetic on two numbers the reader typed; the card shows it as what their own rule implies, **never as a recommendation**. On getting out it says one thing and no more: *a stop order's trigger is not its fill price.*

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. `positions()` and `draws()` are added by the pull request that builds this chapter. This chapter owns `INV-thesis.7`–`INV-thesis.9`.

**INV-thesis.7 — A stop is never derived.** Over every module under `backend/src/katalyst/thesis/`, walked at test time: no function returns a stop, a target or a horizon it did not receive from a `Position` the reader built — a static check with a fixed, finite input, in the manner of `test_beliefs_never_merged`. **Test:** `test_a_stop_is_never_derived`.

**INV-thesis.8 — Touching is at least as likely as finishing beyond.** For every position from `positions()` over every set of draws from `draws()`: the weighted share of worlds in which the stop is touched at any time is at least the share in which the outcome finishes beyond it. True by containment, whatever the path model. **Test:** `test_the_stop_is_at_least_as_likely_as_finishing_beyond_it`.

**INV-thesis.9 — A fixed claim comes on when the edit says.** For every map from `graphs()` and every branch supposing a claim true at a date: in every drawn world that claim's on-day is the day the edit fixed and never anything else. **Test:** `test_a_supposed_claim_comes_on_its_own_day`.

---

## ANTI-PATTERNS

1. **Do not derive the reader's stop, and do not size the trade for them.** Because on this product's own worked example the derivation names the claim the trade rests on — *get out if the thing you are betting on stops being true* — and a recommended size is advice resting on an uncalibrated probability. **Instead:** take the stop as typed, compute *what takes you out* and *what to watch* beside it, and show only what their own risk budget implies.

2. **Do not report a first-touch number without naming the sample its days came from.** Because under *This happened* those days come from a weighted sample with a measured error, and this is the number the reader acts on. **Instead:** name the engine's weighted forward sample in the same sentence as the number.

3. **Do not answer a path question with an end-of-window distribution, and do not read a daily count as if it were continuous.** Because a stop touched on day three is touched, and a daily count misses touches between closes — both errors run in the flattering direction. **Instead:** walk the path, and apply the barrier shift.

4. **Do not put a contract on a price path.** Because a random walk leaves the zero-to-one range and the contract's truth in that world is already known. **Instead:** refuse the question by name and hold the contract to resolution.

---

## Open questions

*Raised 2026-09-21.*

1. **The path double-counts what the spot already prices.** Today's price already reflects the market's own chance of the claim, so applying the claim's full move on top of a tendency-free walk manufactures a favourable drift — and it lands on the chance of the target being reached first. On Kent's list in record 0019.
2. **How many drawn worlds, and where does the instrument's day-to-day variability come from?** The first is a measurement to be made; the second is the reader's own number today, and measuring it needs a third data source.
3. **Does a position survive a branch change?** It is not an edit, so it lives on no branch — but a reader who supposes something new and comes back expects their numbers to still be there.
