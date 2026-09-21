# Position — the reader's trade, their exit, and the one thing this layer asks of the engine

## Purpose

A trade needs something bought or sold, a size, and a point at which the reader gets out. None of those is derivable from a map of claims, so **the stop, the target and the horizon are numbers the reader types**, and what the map computes beside them is how often each is reached first. A reader can now say *I am short this at today's price, out at 3% against me, target 6% for me, by the end of October*, and be told how often each of those happens first.

---

## Data model

Five modules in `backend/src/katalyst/thesis/`, all outside `domain/`, which gains nothing from this part.

**`position.py` — `Position`.** What the reader types: which ending it trades; the instrument or contract, taken from the claim's own payoff so it cannot disagree with the map; the side; the entry price; the **stop**; the **target**; the **horizon**; a **risk budget**, the share of their capital they are prepared to lose on this trade; and how far the instrument moves in a day. Every number is theirs. **`position_on` is the one place a position is built**, and it reads the instrument, the side and which of the two kinds of ending this is off the payoff, so the form cannot name a trade the map does not. The side is read one way for both kinds: **long** means the position makes money when the claim comes true. An ending naming an **instrument** trades in that instrument's own price; an ending naming a **contract** trades in the claim's own probability, and gets no path and no first touch in version one (B3).

**`draws.py` — `Draws`**, the only thing this part asks of the engine: the day the window starts and how many days it runs; the claims in a fixed order; for each drawn world and each claim, the day it **came on** (`on_day`) and the day it **went off** (`off_day`); a **weight** per drawn world; how many equally-weighted worlds those weights are worth; and which sampler they came from. Field for field, that is the engine's own forward sample, so the adapter between them renames and never computes.

Two days, not one, because a claim is an event or a state. An event never un-happens, so its off-day is always *still holding*; a state can stop, and with one day a state that held three days would be indistinguishable from one still running. Every consumer would otherwise inherit that hole.

**Two markers, not one.** *It never came on* and *it came on and has not stopped* are opposite facts, so they are different numbers — a reader that had to tell them apart by looking at the other array is a reader that can forget to. A claim that never came on never went off, and the shape refuses a set of draws that says otherwise.

**Days are coarse.** The engine cuts the window into a fixed number of time slices and takes an arrival at the **middle** of its slice, so over a two-month window every arrival lands on one of about two dozen days, two and a half days apart. A daily path steps sixty times and takes a surprise on at most two dozen of them. Nothing above may assume a claim can come on any day, and over a window shorter than the number of slices two middles round to one day — which is why a state may come on and go off on the same day.

**Where the days come from.** The engine's own **weighted forward sample**: worlds drawn forward carrying event days, with an observed claim set to what was observed and the world weighted by how likely that was — one sampler, two readers. **So the weight is real, not all ones**, and every count here is weighted. Record 0019 carries the measurement, the script and the caveats. The sampler's name is a **field on the draws**, carried through the path to the first-touch answer, so a number cannot be reported without it.

**`paths.py` — a daily path.** For each drawn world, a price path for the traded instrument: a **random walk with no built-in upward or downward tendency**, stepping at the instrument's own day-to-day variability, with each claim's **surprise** applied on the day it came on. A path exists for one reason: a stop is path-dependent, and a distribution of end-of-window outcomes cannot answer a question about the way there.

**The surprise, not the whole move.** Today's price already reflects the market's own chance of a claim, so applying the whole stated move on top of it counts that move twice, in the reader's favour. Write `q` for the market's chance and `m` for the stated move: the price moves by `m × (1 − q)` when the claim comes true and gives back `m × q` while it has not — paid day by day on the shape of the model's own arrival days, never dropped whole on the deadline. The window's expected move is then `m × (p − q)`, the edge, and **nothing at all where the model and the market agree**. `q` comes from a venue quote on that claim where one exists, else the model's own number from the world with no fixed value in force; the reader may override it and never must, and **the screen names the source used**. Record 0019 carries the arithmetic and the measurement.

**Every path starts at the entry price.** Each claim's carried amount is measured from its own day-zero value, which makes two rules fall out rather than needing to be written. A claim **already on when the window opened** is in today's price and moves it by nothing — the surprise rule read at a market chance of one. A claim that **stops holding** gives its level gap back, because the gap is what the claim was worth.

**Where there are no arrival days there is no histogram**, so the giveback falls back to a straight line down to nothing — fair over the window and quietly unfair within it. The answer says which of the two shapes each claim followed, because four to five points of *the stop is reached first* ride on that choice.

**What the path does not price.** It prices the chance a claim **comes true**, and not *the chance it stops*, because nothing asks the model for that second number yet — it is one line of the one shape freeze. So the path invents nothing on an **event**; on a **state** it carries a known gap, stated in INV-thesis.16 and in the open questions below.

**`ceiling.py` — the greyed size ceiling.** A **quartered Kelly** fraction at the **unfavourable** end of the model's stated range: the bottom of the range when buying, because a lower likelihood makes buying worth less, and the top when selling. It is shown greyed beside the reader's own arithmetic, under the words *never size to this*, which the value carries as a field rather than a screen carrying as copy. Three answers and never a blank: a fraction; **zero** where the arithmetic ran and came out at nothing, with its reason; and **absent** where there was no edge to run it on, carrying that refusal's own sentence after one fixed clause. `card-and-export.md` says where it sits on the card.

---

## Behaviour

### B1 — The reader types a position

On the Hormuz map they select the ending they want to trade and fill in the form; instrument and side come from the claim's payoff and are shown, not typed. A position is not an edit to the map: nothing moves on the canvas, and it appears on no branch.

### B2 — First touch

**First touch** means walking each drawn world's path day by day and recording which of the stop and the target is reached first, counting a level as reached the moment the path touches it. A stop hit on day three is hit even if the price finishes the month above it, and any method that looks only at the end of the window understates being stopped out — in the flattering direction.

Two honesty rules travel with the number. A **daily** check misses touches between closes, so the method applies the standard correction, the **barrier shift**: the stop moves a little way toward the starting price, by an amount growing with the instrument's variability and the step, so a daily count matches what continuous watching would have found. And when a day's step crosses **both** levels the **stop** is taken as first — the only reading that cannot flatter the trade.

**How far, exactly.** The distance is `−ζ(½) / √(2π)` — the Riemann zeta function at one half, the constant in every treatment of discretely monitored barriers — times one day's variability. It is computed from that one cited number rather than typed as a rounded factor, and it never moves a level past the entry price: a stop nearer the entry than the correction is touched on the first day either way. **Measured** on forty thousand worlds walked at a hundred steps a day, a stop three points below a hundred with a variability of one point a day: watching continuously the stop is touched in `.5786` of worlds, checking only at the close in `.5149`, and checking the corrected level in `.5874`. The uncorrected daily count is short by `.0637`; the corrected one overshoots by `.0088`. Script and saved output: `plans/analysis/scripts/T2a/check_the_path.py`.

**The number is read against the reader's own stop where that is what is being asked.** The share that *finished beyond* the stop is measured at the price they typed; the shift is a correction to a count of touches, not a change to their price.

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

Given a risk budget and the distance from entry to stop, the size that loses exactly that budget is arithmetic on two numbers the reader typed — the share of capital to put in is the budget times the entry price, over the distance to the stop. The card shows it as what their own rule implies, **never as a recommendation**, and it is **not capped**: a stop nearer the entry than the budget is to the whole implies more than all their capital, and saying so is more useful than quietly clipping it. Beside it sits the greyed **quartered-Kelly ceiling** of `ceiling.py`, labelled *never size to this*. On getting out the card says one thing and no more: *a stop order's trigger is not its fill price.*

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. `positions()` and `draws()` are added by the pull request that builds this chapter, in `backend/tests/thesis/synthetic.py` beside a `worlds_of` that writes a small set of drawn worlds down as a table. This chapter owns `INV-thesis.7`–`INV-thesis.9`.

**INV-thesis.7 — A stop is never derived.** Over every module under `backend/src/katalyst/thesis/`, walked at test time: nothing assigns to a name called `stop`, `target` or `horizon`; a `Position` is built in exactly one place; and that place takes all three as keyword arguments with no default — a static check with a fixed, finite input, in the manner of `test_beliefs_never_merged`. The checker is shown catching each of those on a throwaway file, so it cannot pass because nothing is there. **Tests:** `test_a_stop_is_never_derived`, `test_a_position_is_built_in_exactly_one_place`, `test_the_one_builder_takes_the_reader_s_three_numbers_and_defaults_none_of_them`.

**INV-thesis.8 — Touching is at least as likely as finishing beyond.** For every position from `positions()` over every set of draws from `draws()`: the weighted share of worlds in which the stop is touched at any time is at least the share in which the outcome finishes beyond it. True by containment, whatever the path model. **Test:** `test_the_stop_is_at_least_as_likely_as_finishing_beyond_it`.

**INV-thesis.9 — A fixed claim comes on when the edit says.** For every map from `graphs()` and every branch supposing a claim true at a date: in every drawn world that claim's on-day is the day the edit fixed and never anything else. **Test:** `test_a_supposed_claim_comes_on_its_own_day`.

**INV-thesis.16 — A path invents no advantage.** For every set of draws from `draws()` **in which each claim is an event** — once it comes on it holds to the end of the window — with each claim's market chance read off those same worlds, so nothing is typed in: the weighted mean price is the entry price on **every** day, exactly rather than within a sampling error; and the price in a world where the claim came true, less the price in one where it never did, is its stated move. **Tests:** `test_a_path_has_no_drift_when_the_model_agrees_with_the_market`, `test_agreeing_with_the_market_leaves_the_mean_price_where_it_started`, `test_the_move_applied_and_the_giveback_sum_to_the_stated_move`, and `test_the_old_rule_fails_the_same_assertion`, which shows the rule this replaced failing it.

**The antecedent is the gap, and it is named rather than left to be found.** The path prices the chance a claim comes true and not *the chance it stops*. So a **state** already on when the window opened gives up its whole level gap on the day it stops, with nothing having been priced in against that; and a state that comes on and stops within one day — reachable, because the engine's arrival days are coarse — is never carried at all. Two tests pin both, and the symmetric rule waits on the one number nobody is asked for yet.

---

## ANTI-PATTERNS

1. **Do not derive the reader's stop, and do not recommend a size.** Because on this product's own worked example the derivation names the claim the trade rests on — *get out if the thing you are betting on stops being true* — and a recommended size is advice resting on an uncalibrated probability. **Instead:** take the stop as typed, compute *what takes you out* and *what to watch* beside it, and show what their own risk budget implies, with the greyed ceiling where nobody can mistake it for a recommendation.

2. **Do not report a first-touch number without naming the sample its days came from.** Because under *This happened* those days come from a weighted sample with a measured error, and this is the number the reader acts on. **Instead:** name the engine's weighted forward sample in the same sentence as the number.

3. **Do not answer a path question with an end-of-window distribution, and do not read a daily count as if it were continuous.** Because a stop touched on day three is touched, and a daily count misses touches between closes — both errors run in the flattering direction. **Instead:** walk the path, and apply the barrier shift.

4. **Do not put a contract on a price path.** Because a random walk leaves the zero-to-one range and the contract's truth in that world is already known. **Instead:** refuse the question by name and hold the contract to resolution.

5. **Do not apply a claim's whole stated move to a path that starts from today's price.** Because today's price already reflects the market's own chance of that claim, so the whole move counts it twice — measured at twelve points of *the target is reached first* on a plain example. **Instead:** apply the surprise, give the priced-in part back day by day, and name where the market's chance came from.

---

## Open questions

*Raised 2026-09-21.*

1. **Is a claim's stated move a level gap or a reaction?** The surprise rule needs the first — the level where the claim is true against the level where it is false — and the model answers with the second unless asked precisely. One sentence in the one shape freeze; until it lands the rule can discount twice. The map states a move as a **share of the price** today, and this layer takes one in **price units**, so whatever adapts the two converts; a percentage move compounds and the additive arithmetic puts free drift back above about a twenty per cent move.
2. **How much of the giveback's shape is noise?** The engine's arrivals land on about two dozen days, so the histogram behind the schedule has at most that many bars. How few arrivals it takes before that shape is noise is unmeasured.
3. **Which number is the market's chance, exactly?** The neutral assumption is the model's own, and there are two candidates: the base world's likelihood for the claim, read on its own resolve-by day, and the share of the **drawn worlds** in which it comes on inside the trade's window. They agree only where the window is the claim's own horizon. The path has no drift at all under the second — that is what makes the invariant above an identity — so a supplier handing in the first should expect a little drift and say so.
4. **How many drawn worlds, and where does the instrument's day-to-day variability come from?** The first is a measurement to be made; the second is the reader's own number today, and measuring it needs a third data source. The walk also steps at one fixed variability for the whole window, where a real instrument's moves most around the event.
5. **Does a position survive a branch change?** It is not an edit, so it lives on no branch — but a reader who supposes something new and comes back expects their numbers to still be there.

*(The question this chapter raised first — that the path double-counts what the spot already prices — was answered on 2026-09-21 by Kent's decision R28, above.)*
