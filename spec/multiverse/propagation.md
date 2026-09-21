# Propagation — how a change travels

## Purpose

A branch is a list of edits; a world is what those edits do to the numbers. This chapter is the arithmetic in between. After it, the user can suppose the strait opens, insert a strike the next day, and watch one claim after another move — and click any number to see the chance it started from and the causes that were added to it.

**A claim's number is the chance it comes out true by its own deadline.** That is the sentence already printed beside it: *Brent crude settles below $68 for five sessions, by 15 October*. Not a snapshot of how things look on one day. Two kinds of truth are told apart, because they end differently:

* an **event** happens once and stays happened — *the strait reopens*. Its number only rises as its deadline approaches.
* a **state** holds over a stretch of time and can stop — *the strait stays open to commercial transit through 1 November*. Its number is the chance it is **holding on its deadline**, so it can rise and then fall.

Every claim says which it is, in a field called `persistence`, and no code can work it out from the sentence (decision record 0017).

The chapter settles five things: how an arrow bends a claim's **rate** rather than a likelihood read on one day; how two causes of the same claim combine; how *Suppose this is true* and *This happened* are answered; where the **range** under a computed number comes from; and what the engine costs.

### Every number on the map moves twice, and this is the first move

*(2026-09-22.)* Until now an arrow carried a `strength`: a push on the log-odds scale, added to a likelihood read on one day. A claim's number is now the chance it happens by its deadline, so an arrow is calibrated from **the chance the claim reaches its deadline with that one cause on and no other** — written `q1` below, against the claim's own no-cause chance `q0`.

Nobody has been asked for `q1` yet. Until the model is asked directly, one dated function converts the stated `strength` into it, and **that is a conversion, not an identity**: `strength` was an odds increment read on a single day at whatever size the arrow's shape had reached by then, where `q1` counts the arrow's whole push over the window. The two agree for a `step` arrow with no lag and part company for every other shape. The claim's own number is converted too, and quietly: what was a snapshot prior is read as `q0`.

So **every computed number on the map moves once at this flip, and once more at the shape freeze** that asks the model for `q1` directly and deletes the conversion. Neither move is a sweep anybody has to review by eye: the generated numbers file below is what makes each one a single reviewable diff.

**Every engine-computed figure this chapter mentions is cited from one generated file and never typed here.** [`docs/worked-numbers.txt`](../../docs/worked-numbers.txt) is written by `make numbers` from the shipped engine on the Strait of Hormuz map, at that example's own seed and the shipped loop sizes, and the build fails when it goes stale. Every line in it starts with a name a passage can cite — `B · base · reading` — and the numbers a person typed into the example are kept in a part of their own, apart from the numbers the engine worked out. The day the arithmetic changes, the diff of that one file is the whole list of what moved.

Everything here rests on decision records **0016** (a claim's number is the chance it happens by its deadline; *whether* is solved exactly, *when* is sampled) and **0017** (a claim is an event or a state; nothing retracts itself). Both amend record 0005, which named `trigger` and `sustain`, and record 0014, which owns what the range means — **and `lo` and `hi` keep exactly the meaning 0014 gave them.**

---

## Data model

The shapes, and the module that defines each. Frozen, like everything else in `backend/src/katalyst/domain/`: no clock, no network, no global state.

### What `apply` hands to `propagate`

`apply` (`domain/patch.py`) folds a branch's edits onto a base map, in order, and returns **the map it leaves behind together with every value an edit fixed**. Each fixed value is an `Assignment`: which claim, what it was fixed to, the day it holds from (day zero when none is given), which edit in the branch did it, and which of the two verbs — *Suppose this is true* or *This happened* — the user chose.

**`Proposition` grows no "fixed value" field, and never will.** A fixed value is a fact about a *world*, not about a claim. Written onto the claim, the same claim would mean different things in different branches and the base map would stop being the one thing every branch agrees on ([`branches-and-worlds.md`](branches-and-worlds.md), open question 1, decided 2026-09-17). The pair — map and assignments — is also what a further `apply` takes, which is what keeps the concatenation law type-checking (INV-5: applying two branches in a row equals applying the two joined). The list stays **ordered**, so a later assignment reads as overriding an earlier one rather than silently replacing it.

### What a claim's day looks like

Two states, one per claim per day, in `domain/propagation.py`:

* **`sampled`** — the ordinary case. The number is worked out.
* **`supposed`** — a *Suppose this is true* is holding. The claim is true in every version, and the tile shows the word where a likelihood would go.

There used to be two more, `withdrawn` and `pushed`, for a supposition the engine ended on a calendar. **Nothing retracts itself any more** (record 0017): a supposition holds until another edit changes it, so there is no third or fourth state to be in.

### What a world is

`World` (`domain/propagation.py`) carries, for one map, one branch and one seed:

| Field | What it is for |
|---|---|
| `base_id`, `branch_id`, `seed` | the replay triple — these three rebuild this world byte for byte on any machine |
| `versions` | how many versions of the map were drawn; the range is the spread across them |
| `graph`, `assignments` | the map `apply` left behind, and every value an edit fixed |
| `beliefs` | one number per claim, owner `model`, read on that claim's own resolve-by day |
| `series`, `series_days` | how that number stands on each day drawn, and which day of the window each point sits on |
| `states` | one of the two day-states above, per claim per day, the same length as the series |
| `conditionals` | one number per arrow: its target, with its source **supposed** true. Empty until asked for |
| `range_shares` | whose stated chance explains whose range. No route reads it until stack 06 |
| `warnings` | plain sentences: a series sampled down, an arrow stated beyond ±5, an arrow that could not hold its claim back as far as its number asks (B4) |

`series` is what makes the scrubbable time axis possible (UX-3). **An event's series only rises** — it is the chance the claim has happened by that day, and a thing that has happened does not un-happen. **A state's series may fall**, because it is the chance the claim is still holding.

Three fields are on the wire and always empty, each with a dated comment saying so, because their readers in the browser move in a later pull request: `retractions` (nothing retracts itself), `worlds` (there is no inner loop, so it is `0`), and `ClaimDiff.moved_only_by_reweighting` in [`diff.md`](diff.md) (every version now counts the same). They go together, when those readers do. <!-- VERIFY AT FLIP: that all three are present and empty rather than deleted, and that each carries its dated comment. -->

**`conditionals` means *supposed*, not *observed*, and it is empty on a freshly built world.** The number on a wire's midpoint chip is the target's likelihood **with that arrow's source supposed true** — the interventional number. It is never "how often do these two show up together", which is the correlational quantity [`../graph/link.md`](../graph/link.md)'s anti-pattern 3 refuses; putting that on a wire claiming a mechanism would be the worst kind of quiet lie. Computing it costs an extra solve per arrow, for a number most users never open, so it is fetched **lazily**, one arrow at a time, through `POST /api/worlds/conditional`. Laziness costs nothing in honesty: the number is a pure function of the same three inputs plus the arrow, so a lazily fetched number is byte-identical to an eagerly computed one.

### The six modules that do the arithmetic

They import in one direction only — each reads the one above it and never the other way round.

| Module | What it holds |
|---|---|
| `domain/rates.py` | the window and its slices; one claim's arrows worked out as far as the map's shape allows; the calibration from stated chances to rates; the arrows that could not hold a claim back |
| `domain/states.py` | a claim's times — one for an event, a pair for a state — and the cheap path that skips the pair when nothing reads it |
| `domain/forward.py` | one pass over the map, causes before effects, producing every claim's times and its small yes/no table |
| `domain/solving.py` | the exact solve over those tables: summing claims out in an order chosen to keep the tables small |
| `domain/sampling.py` | the weighted forward sample that answers *This happened*, and the arrival days stack 06 reads |
| `domain/propagation.py` | the one entry point, which assembles a `World` from the five above |

### The one entry point

```python
def propagate(graph, assignments, *, as_of, seed,
              versions=2_000, worlds=0, introduced_by=NOTHING_ADDED,
              slices=24, sampled_worlds=50_000) -> World
```

`as_of` is day zero, passed in by `engine/worlds.py` from the stored example's own date; this layer reads no clock. `worlds` and `introduced_by` are the two arguments nothing reads any more, kept until their callers move. <!-- VERIFY AT FLIP: the exact signature — whether `introduced_by` survives the deletion of retraction, and whether the `engine=` flag that stood the two cores side by side is deleted here or kept with its default changed. -->

---

## Behaviour

Worked on the Strait of Hormuz map. Its claims and their stated chances are the lines named `H · prior`, `C · prior`, `B · prior`, `R · prior`, `M1 · prior`, `M2 · prior`, `N1 · prior` and `S · prior` in the numbers file, and each claim's deadline is the line named `… · resolve by`. Day zero is the line named `run · day zero`, and the seed `run · seed`.

| | The claim | Kind of truth |
|---|---|---|
| **H** | *The Strait of Hormuz reopens to unrestricted commercial transit.* — the hypothesis | event |
| **O** | *The strait stays open to commercial transit through 1 November.* | **state** |
| **C** | *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.* | event |
| **B** | *Brent crude settles below $68 for five sessions.* | event |
| **R** | *OPEC+ announces output restraint.* — the tail | event |
| **M1** | *A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.* — tradeable | event |
| **M2** | *The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days.* — tradeable | event |
| **N1** | *Omani-mediated United States-Iran talks resume publicly.* — real, and no venue prices it | event |
| **S** | *A confirmed military strike on Iranian territory.* — on the branch only | event |

<!-- VERIFY AT FLIP: the state claim O's identifier, its exact wording, its deadline and its arrows, all of which the fixture gains in the flip. Every line name below of the form `O · … ` depends on it. -->

Every number fed into that map is **illustrative**, exactly as the fixture says of its own, and the flip may tune it to make the example richer — each tuned value carrying a comment saying what it was, what it is and why. So the tests that guard this example assert **directions and orderings**, never values.

### B1 — The window, its slices, and where inside a slice an arrival is taken

The window runs from day zero to the latest resolve-by day on the map, in whole days. Every date becomes an integer day index at the edge of `propagate` and stays an integer inside it.

**The window is cut into 24 equal slices**, and inside each slice the rate is read at 8 evenly spaced days. One window is cut per map; claims differ only in where their own deadline falls inside it, and a slice past a claim's deadline counts zero days of that claim's window. Both counts are constants in `domain/rates.py`, and both were chosen by measurement (record 0016):

* **Twelve slices halves the cost and is not built.** Its grid error alone puts 2.50% of *This happened* numbers further than `.005` from a fine reference, where 24 slices with the middle-of-slice convention below puts 0.00% — both measured over the same adversarially generated four-claim maps under the additive rate.
* **An arrival inside a slice is taken at the slice's middle, never its end.** At 24 slices, against the same fine reference, that one line moves the worst gap from `.0290` to `.0027`. The last-day convention at 60 slices is worse than the middle-day one at 12.

**What that grid costs, said plainly, because every tolerance in this chapter is smaller than it.** At 24 slices with 8 points inside each, against a dense integral of the rate itself, the calibration reproduces a stated chance to `1.8e-2` and the machinery reproduces the rate to `1.9e-2`. Thirty-two points inside a slice brings both to about `5e-3`, and **nobody has costed 32**, so it is not built. The `.005` the oracles below are judged at is the distance to an enumerator **running on the same grid**, where the grid error cancels on both sides — it is not the distance to the truth. A reader who takes it for the second has been misled by the number rather than by the sentence around it.

**The settled day stops doing two jobs.** The old engine read *when a cause arrived* off the grid it drew the series on, which tied the timing of a push to how long the window happened to be — so a claim added at one end of the map could re-time a claim at the other end that nothing connected it to. That reading is gone: **when a cause arrived now comes out of the forward pass in B2**, as a chance spread over the slices, and the drawn grid is only where a line is drawn. Past 180 days the series handed to a reader is sampled down to 180 points, with every claim's own resolve-by day kept among them and a sentence in `warnings` saying so; `series_days` says which day each point sits on, because evenly spacing unevenly spaced points would misplace every date on the axis.

**The slice edges are still a property of the whole map**, and that is the one place this hazard can come back: stretching the window by inserting a claim judged far out makes every slice wider, and a short-deadline claim is then worked out on a coarser grid. `test_a_longer_window_moves_nothing_it_cannot_reach` is what says whether that moves a number it cannot reach, and INV-4 below is the sharper form. <!-- VERIFY AT FLIP: whether a map-wide slice grid keeps `test_a_longer_window_moves_nothing_it_cannot_reach` and INV-4's byte-identity green; if it does not, this passage states the remedy instead of the hazard. -->

### B2 — What a number means, and how an arrow bends a rate

Each claim has a **rate**: how fast it is coming about, per day. With nothing causing it, that rate is whatever reproduces the claim's own stated chance of reaching its deadline. The chance it has *not* happened by some day is the rate added up over the days before that, run through the exponential — and the chance it *has* happened is one minus that.

**Causes add to the rate. Each arrow is a separate way for the claim to come about** (Kent, decision R18, record 0016). The chance none of them brings it about is the product of the chances that none severally does, so two causes that each alone would take a claim from 10% to 40% by the same deadline give **59%** together — not 91%, which is what multiplying the likelihoods would say. *(Those three figures are the record's own worked identity on a bare two-cause map, not a reading of the Hormuz example.)*

Three consequences worth stating, because each is otherwise a surprise:

* **Causes never amplify one another.** *Hormuz reopens* and *OPEC+ restraint holds* may be worth more together than apart; here they are not. Nobody stated the amplification — one number per arrow, plus the claim's own, and neither is about two causes coinciding.
* **Because the rate adds, the average over *when* each cause arrived is taken one cause at a time**, rather than over every combination of arrival days. That is the whole of the cost result, and it is exact: one cause at a time equals averaging the full table to `4.4e-16`.
* **Two arrows running through one mechanism count the same route twice.** The remedy is the map, not the arithmetic (Kent, R22): draw the arrow into the step the map already names, and write two things that only matter together as their own claim. Two paragraphs asking the model for exactly that ride the shape freeze.

**A warning above ±5.** `validate` puts no ceiling on a stated push; an unbounded number is the honest type. But ±5 is roughly 1% to 99% on a coin flip, so `propagate` adds a plain sentence to `warnings` naming any arrow beyond it. A warning, not a rejection: the map is still legal, and the user should be told. A push in such a sentence is written to one place after the point, always with its sign, by `_push_as_written` in `domain/propagation.py` — a different rule from the one that writes a likelihood, because a likelihood runs from 0 to 1 and a push runs from minus infinity to plus infinity.

### B3 — The three shapes, and the calibration with nothing searched for

An arrow carries a `shape`, a `lag` and — for a spike — a `half_life`, all unchanged in name and meaning. They now say how the arrow's push is spread over the days rather than how big it is on one day. Writing `u` for the days since the cause arrived and `L` for the lag:

```
impulse(u) = 0                            for u < L      zero through the lag, then a spike
             2 ** (−(u − L) / half_life)  for u ≥ L      that halves every half_life days

step(u)    = 0                            for u < L      zero through the lag, then
             1                            for u ≥ L      full size, held

ramp(u)    = 1                            for u ≥ L      full size, held — tested first
             u / L                        for 0 ≤ u < L  climbing from 0 to 1 across the lag
```

**Two edge cases that need no special case.** A `ramp` whose `lag` is zero has no rise time, and because the `u ≥ L` branch is tested first the climbing branch is never reached: it behaves as a `step`, with no division by zero. And an `impulse` with no `half_life` never arrives, because a map carrying one is refused by `validate` before `propagate` sees it (`impulse_without_half_life`, [`../graph/validity.md`](../graph/validity.md)). Reject, never repair. **`lag` is the ramp's rise time**, and there is no `rise_time` field; a `half_life` on a `step` or a `ramp` is a violation, not an ignored field.

**A whole shape's area now counts, which removes a wart record 0014 admitted.** The old arithmetic read an arrow on one day, so a spike that had mostly faded before a deadline still delivered whatever it happened to be worth that morning, and the answer depended on where the deadline fell against the half-life. Now the arrow's push is added up across the claim's window. Attacked with half-lives of one and two days landing four days before a deadline, the gaps were `.0000` to `.0001`.

**The calibration is closed form: three lines, no searching, no clamping of a root.** Writing `own` for the claim's own chance of reaching its deadline with nothing on, `with_it` for the chance stated with one cause on and no other, `area` for the arrow's shape added up over the claim's window, and `ln` for the natural logarithm:

```
a helping arrow       rate × area  = ln(1 − own) − ln(1 − with_it)
a holding-back arrow  leak × (window − (1 − leaves) × area) = −ln(1 − with_it)
an ending arrow       rate × area  = −ln(1 − stops),   stops = 1 − with_it / own
```

**The sign of an arrow decides which of those three it is, and no field is added to the arrow.** Stated above the claim's own chance, it helps. Stated below it, on an **event**, it holds the claim back. Stated below it, on a **state**, it ends the state. Record 0017 settled that; `domain/rates.py` is where it is written down.

**An ending arrow is asked a different question, and only an ending arrow** (Kent, R26): *if this cause happens, how likely is it that the state has stopped holding by its deadline?* Asking the usual question of it — how likely the state is to *hold* while stripping away the cause that turned it on — has no honest answer, and the old form needed a numerical search to fit one. `stops` is closed form, and that is measured: over the adversarial set it fits every arrow with **zero** searches and **zero** clamps, where the old wording needed a search for each and clamped 2.6% of them.

**One honest wrinkle, said here so a reader does not find it.** `stops = 1 − with_it / own` is not invariant to the state's own stated chance the way an odds increment is: on the bridge from today's `strength`, one push of `−0.5` gives four different values of `stops` as the state's own number runs from `.10` to `.90`. It is survivable only because **no state exists on any map until the flip creates one by hand** — the code that mints claims from a recorded proposal makes every one an event until the freeze — so the one state on the map carries hand-written numbers a reader can check, and the freeze then asks the model for *the chance it stops* directly.

### B4 — An arrow that holds a claim back, and when it cannot hold it back enough

A holding-back arrow does not add a rate. It **scales the claim's own rate down** while its cause is on, and `leaves` above is the share of the rate it leaves running — zero meaning the rate is suppressed entirely.

That is a hard floor, and it has a consequence the reader is told about rather than left to discover. **An arrow whose shape covers only part of the claim's window cannot hold the claim back as far as its number asks.** A spike with a half-life of ten days into a fortnight-long window is on for a fraction of that window; even suppressing the rate entirely while it is on leaves the rest of the window running, and the claim comes out **above** the number stated for it.

**Where that happens, the arrow says so.** `propagate` puts a sentence on `World.warnings` naming the arrow in the map's own words, the chance it asked for and the chance the engine could deliver — the same shape as the loud-push warning in B2. Nothing is silently repaired and nothing is refused: the map is legal, the number is honest, and the reader can see which arrow is asking for more than its shape can give. On the shipped fixture this fires on the strike branch; the line named `strike · warnings` in the numbers file carries the sentences word for word, and `base · warnings` carries the base world's. Across the adversarially generated maps record 0016 measured, 30.0% of holding-back arrows fall short this way.

<!-- VERIFY AT FLIP: which arrows on the shipped fixture clamp, and whether the numbers file names them on `strike · warnings` and `base · warnings` or on new lines of their own. The plan expects `S->B` and `R->B`; the flip re-examines `S->B`'s shape and number, so it may no longer. -->

### B5 — Events and states

A **state** carries two times: the day it came on and the day it went off. Both come from rates.

* Its **on-rate** is bent by its causes exactly as an event's rate is.
* Its **off-rate starts at zero** and is the sum of its ending causes. So a state with nothing on the map that can end it does not end — and it is then **identical to the same claim written as an event**, measured to `1.4e-16`. **No second number is elicited** for the off-rate; the ending arrows are all of it.
* It switches on at most once and off at most once, and its number is the chance it is **holding on its deadline**: on by then, and not yet off.

**The two arrow modes are now told apart by which of the source's times the arrow reads.** This is record 0005's domino and apple, made arithmetic:

* A **`trigger`** arrow reads the day its cause came on, and keeps pushing afterwards whatever the cause does. The domino stays fallen.
* A **`sustain`** arrow reads its cause's **whole stretch**, and is dead once the cause stops holding. The desk is gone; the apple falls.

A `sustain` arrow may therefore leave only a state, because only a state can stop. That rule is refused by name — `sustain_without_state` — **from the shape freeze**, together with the prompt sentence that asks the model for `persistence`; until then the code that mints claims from a recorded proposal makes every one an event, and a `sustain` arrow out of an event measures identical to a `trigger`.

**What a state costs.** In the exact solve, nothing: on a twenty-claim map with five states the largest table, the entries built and the elimination time are the same as on the same maps with no state at all. Its **pair of times is the one expensive piece**, and only a `sustain` child ever reads it — the pair costs versions times slices **cubed** where the on-curve alone costs versions times slices squared, about twenty times the work per state at 2 000 versions and 24 slices. So `needs_the_joint` in `domain/states.py` builds the pair only for a state some `sustain` arrow leaves. **No measured saving is claimed for that**: record 0017's own forward-pass timing already skipped the pair for the states nothing sustained. It exists so a map full of states nobody reads the stretch of does not pay slices cubed for work no reader wants.

**And a state is no less accurate than an event**: over 82 map skeletons run once with states and once with every claim an event, both sides put 99.8% of numbers within `.005` of the enumerator, with worst gaps of `.00835` and `.00794` — the same maps, the same seeds, the additive rate, measured at 12 slices and re-measured at 24 before the tolerance goes into a test.

**What nobody has measured: what a state does to the range.** Every version draws each claim's stated chance from its stated range; a state has two rates and the second is fitted from its ending arrows rather than drawn. Record 0017 names this as a real gap, and the core pull request measures it and writes the answer into `docs/measurements.md`.

> **On the Hormuz map.** *Hormuz opens, then Iran is struck* leaves **both events standing**: H is supposed true and S is supposed true, and neither is withdrawn, retracted or dated out. What falls is the state O — it was held up by the reopening and is ended by the strike — and what falls with it is C, which O sustains. The lines are `H · strike · reading`, `S · strike · reading`, `O · base · reading`, `O · strike · reading` and `C · strike · reading`. Nothing consults a calendar, nothing un-trues a claim, and the word *retracted* appears nowhere in the answer.

### B6 — *Suppose this is true*, and *This happened*

*Whether* each claim is true is solved **exactly**, by summing claims out of the map's small yes/no tables one at a time in an order chosen to keep those tables small (`domain/solving.py`). The order changes how much work the solve does and never changes the answer. The versions ride as an extra axis on every array, so a whole range is one pass rather than two thousand.

**A supposition is a hard fact until another edit changes it.** While it holds, the claim is simply true in every version — not a large finite baseline that arrows can argue with. There is no number at all: the tile shows the word *Supposed* and its date. A tool that answered "suppose this is true" with `.98` would be lying about what the user asked for.

**The two verbs are answered differently, and that difference is the product.**

* ***Suppose this is true*** pins the claim to its day, **redoes the forward pass** with it pinned, and solves. It is never a factor patched after the fact. A `do` also cuts every arrow into its target that is present when it is applied, so nothing upstream of the claim moves — INV-3.
* ***This happened*** leaves every arrow where it is and multiplies in a mask keeping only what agrees with what was seen, then renormalises. Because nothing is cut, the evidence reaches the claim's **causes** as well as what it causes: cheap insurance is evidence the lane really is open.

**Nothing is thrown away, so nothing can starve.** The old engine answered *This happened* by keeping only the draws in which the claim came out as observed, which meant a version could lose every draw it had and contribute nothing. It could then also warn that it had. Both are gone: an exact solve conditions rather than discards, every version counts the same under every edit, and the starvation warning has nothing left to report. An observation nothing on the map can produce is **answered**, with a refusal the caller turns into a violation the user can read, and never divided through by zero.

**Locality is now a theorem rather than a hope.** A claim cut off from the evidence — no path to it, no shared cause — has a factor that sums to one, so it drops out of the solve untouched and comes out **bit for bit** identical to the world without the evidence. That is the strictest assertion in this stack, and it replaces a property test that could only ever say *close enough*.

**Observations stay undated in version one.** *This happened* carries a claim and a value and no date: *this happened on day 5* would need the yes/no question re-cut for each possible evidence day, and nothing asks for it.

> **On the Hormuz map.** *This happened: the war-risk premium printed below 0.4%* keeps the answer for C at certainty and lifts H, because the surviving explanations are the ones in which the strait is open — the lines `C · observed C · reading` and `H · observed C · reading`, against `H · base · reading`. *Suppose this is true* on the same claim leaves H exactly where it was, at `H · base · reading` to the bit.

### B7 — The weighted sample, and the days it hands on

The exact solve above answers *whether*. It is built from timing worked out **before** the evidence, and evidence moves *when* a cause happened as well as *whether* it did — which is the one place the tables alone are not enough. So *This happened* is corrected by a sample.

**The correction, in one sentence.** Worlds are drawn forward with arrival days; at the observed claim the world is not thrown away, but set to what was seen with its weight multiplied by how likely that was; and **the same world is drawn twice with the same random numbers** — once under the full time model and once under the yes/no model whose answer is already known exactly — so only the *difference* between them is sampled and added to an answer already known exactly. *(A control variate, which is the textbook name for sampling only a difference from something exact.)*

Fifty thousand worlds, seeded, and **one sample serves a whole range and both its readers** — the numbers on screen, and the arrival days stack 06 reads to walk a position through time. The sample is drawn at **one** version, not at each of the two thousand, and its correction is a single number per claim added to every version's exact answer. That is why it is a fixed cost rather than a per-version one, and what bounds the error of sharing it is measured: under the rate model this engine uses the correction is `.0020` and moves `.0020` across versions, where under the multiplicative rate the old engine used it was `.1172` and moved `.0805`. Redone per version, 2 000 versions would cost 110 seconds.

**Which version the one sample is drawn at is named rather than assumed**: version 0, the first row of the spread. Nothing measured a better choice, and a rule a reader can check beats one nobody wrote down.

**What it hands stack 06**, as a fixed contract: the day the window starts and how many days it runs; the claims in a fixed order; for each drawn world and each claim, the day it came on and the day it went off, with markers for *never* and *still holding*; and a weight per drawn world. Three things a consumer must know: the days are **slice middles rounded to whole days**, so on a sixty-day window at 24 slices every arrival lands on one of twenty-four days about two and a half apart; the weights are **real**, not all ones, so every count is weighted and any floor counts *effective* draws rather than rows; and an event's off day is always *still holding*, where a state's may not be.

**How accurate that makes *This happened*** (Kent, R25): on the four-claim maps the enumerator can check, no number was further than `.005` from it. That is what the Inspector is allowed to say, and it must not be widened to *on maps this size* — the accuracy was measured on four-claim maps and the cost on twenty-claim ones, and the two sets never meet.

### B8 — Versions, and where the range comes from

Read this before any formula, because it is the idea the whole design rests on.

* **How the dice fall.** The strait either opens or it does not. That is already inside the number: it is the chance the claim comes out true.
* **How sure we are of the numbers we put in.** Every chance on the map was elicited, and every arrow's number was written down by somebody with more or less to go on. A different but equally defensible set of those numbers would give a different answer. **That** is the range.

So a wide range means *"we are not sure what number to give you; more homework would move it"* — never *"the event is more volatile"*. That is the one sentence a trader has to be able to repeat, and the chip says it: **model interval, uncalibrated · how sure we are of this number — not how much the world can move.**

**What a stated `{p, lo, hi}` means: a split logit-normal** — a bell curve on the log-odds scale with its two halves fitted separately, so that the middle is `p`, the 10th percentile is `lo` and the 90th is `hi`. "Eight times in ten" is the phrase. The halves are fitted separately because real elicited ranges are lopsided: over the seven base-map claims the fixture's own ranges are near-symmetric on log-odds and clearly skewed on probability. This honours all three stated numbers exactly, stays inside 0 and 1 with no clamping, and needs no new field on `Belief`.

**How wide an arrow's number is drawn comes from its receipt, and nobody is asked a second question.** An arrow carries a `provenance` — a receipt our own pipeline writes from what actually happened, never something a model claims for itself — and each version draws the arrow's number from a bell curve centred on what the map states, this wide, in log-odds:

| Where the arrow came from | How wide |
|---|---|
| `documented` · `historical` · `market_implied` — somebody fetched something | `0.15` |
| `argued` · `user` — a stated mechanism, or a person's own judgement | `0.40` |
| `simulated` — a probe's output | `0.50` |
| `asserted` — a sentence with no mechanism in it | `0.60` |

A weakly-backed arrow can come out the other way round in some versions, and that is the honest reading: *we cannot vouch for which way this one goes* is most of what `asserted` means. **There is no `strength_lo` and no `strength_hi`, now or ever** (Kent, record 0014): the width is derived from the receipt every time it is needed, so there is one number about an arrow and it cannot drift from a second. Not to be confused with the *other* table that reads the same receipt — [`diff.md`](diff.md)'s provenance **weight**, which turns it into how well-backed a *route* is for ranking. Two questions, two tables.

**The loop is now one loop.**

1. Draw **2 000 versions** of the map — a chance for every claim and a number for every arrow, spread evenly by a Latin hypercube, which is a way of spreading draws evenly instead of letting them clump. A version is **one coherent set of numbers this model would have stood behind**, never "every low end at once".
2. Solve every version **exactly**, on one array axis.
3. The reported number is the mean across versions; `lo` and `hi` are the 10th and 90th percentiles across versions.

There is no inner loop, no coin flip to keep, and **no noise correction**, because there is no noise left to subtract. That makes the statement that the range is not sampling noise exact rather than approximate: freeze every stated chance to a point and freeze every arrow's number at what the map states, and the range comes out **zero wide, exactly**.

**Two thousand versions, and why not two hundred.** At 2 000, a range's end wanders `.0086` on a wide range and `.0046` on a narrow one across seeds; at 200 it wanders `.0275`, which is a tenth of the range's own width. What 2 000 buys is a *narrow* range's two ends to two significant figures — a range a quarter of the scale across needs about 6 000 by the square-root rule that measurement obeys, and this chapter does not claim otherwise. *(Measured at 12 slices under the multiplicative rate and not re-run under the additive one, so it could move.)*

**Where the width comes from, free.** Sorting the same versions into bins by the value each stated chance drew, and comparing the bins' averages, gives each claim's **share of another claim's range** — how much of the width comes from not being sure of *this* claim. Six lines, nothing run twice, now read off the exact per-version answers rather than a sampled average. It is carried as `range_shares[target][source]` and no route reads it until stack 06, where it becomes FR-21's *where to spend modeling budget* ranking.

**The shares do not add up to the whole range, and are not meant to.** They answer whose stated *chance* explains this width, and a version draws the arrows' numbers too; what the arrows explain is in no entry. On the Hormuz map the lines are named `B · base · band from B`, `B · base · band from H` and so on, against the range on `B · base · reading`. Pin B's own chance down and most of that width goes with it — which is the ranking FR-21 asks for, in one number per claim.

**Two counter-intuitive warnings, both measured on this fixture.** A *Suppose* does not reliably narrow what is downstream: it collapses the target's own range, and the width of a claim below it can go *up*, because the curve is steeper where the answer lands. The honest thing to show is the **share**, not the width. And a terminal's range is dominated by its own stated chance: an upstream range reaches it multiplied by a factor that is at most a quarter, so *widen the hypothesis and watch the ending widen* is not a demo, it is a rounding error. <!-- VERIFY AT FLIP: both of these were measured on the old engine; re-measure under the exact core and cite the line names, or cut the passage. -->

### B9 — Three seed streams, and replay

Everything comes from the one `seed` argument, through random generators built from it and nothing else. **No module-level generator, no clock, no global state, ever.** The same map, branch and seed give byte-identical worlds on any machine — NFR-2 — which is what makes a three-day-old screenshot reproducible from three values.

| Stream | Drives | Rule |
|---|---|---|
| `params` | which chance each of the 2 000 versions gives each claim | **Must not depend on the branch.** A base world and a branch world from one seed use the *same* 2 000 versions |
| `strengths` | which number each of those versions gives each arrow | the same rule, for the same reason |
| `worlds` | the worlds the forward sample of B7 draws | ordinary; may depend on anything |

The first two keep the jobs they had. The third has changed jobs rather than gone: it used to drive the coin flips inside each version, and there are no coin flips inside a version any more, so it drives the forward sample instead.

**Every stream is derived per thing**, from the seed and the claim's or arrow's **own** identifier. So adding a claim cannot shift another claim's draws and adding an arrow cannot shift another arrow's — which is what makes the dice cancel out of a paired comparison: version *k* of the base world and version *k* of the branch world drew the same numbers for everything they share. That is *common random numbers*, and without it every comparison is the user's change plus a wash of sampling noise. [`diff.md`](diff.md) spends the whole of it: a change is read off the paired difference, never off whether two ranges overlap.

### B10 — What the user ends up looking at

| What the interface reads | Where it comes from |
|---|---|
| The number on a tile | `beliefs[claim]`, read on that claim's own resolve-by day, at two significant figures with its range (NFR-1) |
| The sparkline and the scrubber | `series[claim]` against `series_days` — rising for an event, able to fall for a state (UX-3) |
| *Supposed · date* | `states[claim]`, the same length as the series |
| The number on a wire's midpoint chip | `conditionals[link]`, fetched one arrow at a time, always the *supposed* number |
| Sentences under the map | `warnings` — an arrow that cannot hold its claim back, a push beyond ±5, a series sampled down |

**What the map reads**, engine's own numbers, each on the claim's own resolve-by day, are the lines named `… · base · reading` and `… · strike · reading` in the numbers file, one pair per claim; the two observation worlds are `… · observed B · reading` and `… · observed C · reading`. Three rows repay a second look, and each is a sentence rather than a value:

* **R is identical to the byte** between the two worlds, because the only arrow into it is a feedback arrow, which the engine sets aside. That is the feedback rule doing its work rather than a coincidence.
* **N1 goes up** on the branch that makes everything else worse. `H → N1` is a `trigger`: the reopening was supposed true, the arrow fired, and a `trigger` keeps pushing whatever its cause does afterwards. What already rose stays risen.
* **N1's range is the widest on the map**, because the only arrow into it is the fixture's one `asserted` arrow — the spread saying, in the one place on this map where it is entitled to, *we cannot vouch for this arrow*.

### What it costs, and the target it is read against

**Recalculating a branch has a target proportional to the size of the map, not a fixed number, and it is a target rather than a gate** (Kent, R24, superseding the fixed 600 ms of R19). The reference point is 600 ms for one world with its range on a **twenty-claim** map at 2 000 versions — 30 ms a claim by plain division — and what it protects is that an edit feels responsive. **No test gates on the clock.**

Where the design stood against that when record 0016 was written, on one benchmark — twenty claims, up to three causes each, 2 000 versions, 24 slices — the prototype measured 538–568 ms with three arrows holding claims back, and **644 ms with five states feeding `sustain` arrows**, which is over the target and the record says so. The engine's own measured figures are recorded beside the old engine's in `ARCHITECTURE.md` §10 and in `docs/measurements.md`; the old engine's figures are not overwritten, because they were measured. <!-- VERIFY AT FLIP: the shipped engine's own benchmark, which the core pull request records; these are the prototype's. -->

**One arrangement that is deliberately not built.** One tree built once and passed over twice would replace twenty elimination passes rather than the solve itself — about a tenth of the cost of a hard map, and nothing now asks for twenty passes in one request. The seam for it is the signature of `all_marginals` and nothing else.

---

## INVARIANTS

Each statement is true for every input a named generator can produce, and each names the test that checks it. Generators live in `backend/tests/strategies.py`: `graphs()` yields random **valid** maps, `interventions(graph)` yields edits whose subjects exist in that map, `branches(graph)` yields branches of such edits, `seeds()` draws integer seeds, and `separated_pair(graph)` picks two claims joined by no path and sharing no ancestor. Tests live in `backend/tests/unit/domain/test_propagation.py` unless noted.

This chapter uses the local numbers `INV-multiverse.9` through `.17`. `.1`–`.5` belong to [`interventions.md`](interventions.md), `.6`–`.8` to [`branches-and-worlds.md`](branches-and-worlds.md), and `.18` onward to [`diff.md`](diff.md).

**INV-7 — honest numbers (product invariant: `0 ≤ lo ≤ p ≤ hi ≤ 1` on every belief, always).** For all maps, branches and seeds: every belief and every series point lies between 0 and 1 and satisfies that chain. Tests: `test_probability_bounds`, `test_belief_bounds_after_any_sequence`.

**INV-3 — assert is not observe (product invariant: `do` moves nothing upstream of its target; `observe` may).** For all maps and all `Do` edits: every ancestor of the target is byte-identical between base and branch. For all maps with a claim having at least one cause strictly between 0 and 1, an `Observe` on that claim changes at least one ancestor. Tests: `test_do_leaves_ancestors_unchanged`, `test_observe_may_update_ancestors`.

**INV-4 — locality (product invariant: an edit changes only what is still connected to its subject in the map the edit leaves behind).** For all maps and all edits: every claim outside the edit's affected set is byte-identical between the base world and the branch world, for all six operations, each pinning at least one fully separated claim. The test computes the affected set itself from the shape of the map — over the map with feedback arrows set aside — and never calls the code it is testing. Test: `test_intervention_locality`, in `test_patches.py`, re-checked after every step of `GraphEditMachine`.

**INV-multiverse.9 — the versions do not depend on the branch.** For all maps, branches and seeds: the 2 000 versions drawn for a base world and for a branch world from one seed are element-for-element identical. Without this, every comparison is the user's edit plus a wash of sampling noise. Test: `test_versions_do_not_depend_on_the_branch`. *Catches:* deciding that something moved by comparing two ranges.

**INV-multiverse.10 — a supposition is true in every version.** For all maps and all `Do` edits: the target comes out true in **every** version, and its state on every day is `supposed`. Not `.98`, not `.999`. Nothing ends it but another edit, so there is no condition on the statement. Test: `test_supposition_is_true_in_every_world_until_undermined`. *Catches:* an implementation that models a supposition as a large finite baseline.

**INV-multiverse.11 — the elimination is exact.** For all maps of four claims or fewer from `graphs()`, all edits and all seeds: the answer agrees with an enumerator that sums the joint by hand **over the core's own tables** to `1e-9`. Test: `test_the_elimination_is_exact`, in `test_solving.py`. That enumerator is blind to a wrong table, which is why `.13` exists beside it. *Catches:* a wrong elimination order, a factor patched after the fact instead of the pass redone, a renormalisation that divides by zero.

**INV-multiverse.12 — the range is not sampling noise, and is zero wide exactly.** For all maps rewritten so every stated chance is a point, **and worked through with every arrow's number held at exactly what the map states**, and all seeds: every computed range comes out **zero width**, exactly and not within a tolerance. Test: `test_band_is_not_sampling_noise`. Both freezes are needed: a version draws an arrow's number as well as a claim's chance, so freezing the chances alone leaves a range that is perfectly real, and `test_freezing_the_priors_alone_leaves_the_arrows_talking` is the other half. *Catches:* reporting the engine's own wobble as uncertainty, which is the single most likely way to get this chapter wrong.

**INV-multiverse.13 — the tables agree with integrating over time.** For all maps of four claims or fewer from `graphs()`, carrying **states as well as events** and including at least one impulse and one diamond: every claim's number is within `.005` of an enumerator built from the arrow parameters alone — forbidden the core's tables — on at least 99% of the generated set, with failing cases named. Seeded, sample size stated, and run at the **same 24 slices and the same middle-of-slice convention as the core**, so what it measures is the arithmetic and not the grid (B1 says what the grid itself costs). Test: `test_the_tables_agree_with_integrating_over_time`, in `test_by_deadline.py`. *Catches:* the defect the first design of this core shipped with, where the arithmetic was exact and the table it ran on was built from timing worked out before the evidence.

**INV-multiverse.13b — how wide an arrow's number is drawn comes from where it came from, and from nothing else.** Two arrows sharing a `provenance` and differing in every other field draw numbers that agree to the bit; each word's draws are centred on what the map states and spread by B8's table; on a map whose every stated chance is a point, the claim an arrow points at has a wider range where that arrow is `asserted` than `argued`, and wider there than `documented`. Adding an arrow leaves every other arrow's draws untouched. Tests: `test_link_spread_comes_only_from_provenance`, `test_a_documented_arrow_gives_a_narrower_band_than_an_asserted_one`, `test_adding_an_arrow_does_not_move_another_arrows_draws`.

**INV-multiverse.14 — the domino stays fallen and the apple falls.** For all maps containing a `trigger` arrow out of a claim that later stops holding: the target's series afterwards is byte-identical to the series in which the source never stopped. For all maps containing a `sustain` arrow out of a **state**: the arrow contributes exactly nothing from the moment its source stops holding. Tests: `test_a_sustain_arrow_reads_the_whole_interval_and_a_trigger_only_the_on_day`, `test_trigger_persists_after_parent_reset`.

**INV-multiverse.15 — a state with nothing to end it is an event.** For all maps and all seeds: a claim written as a state with no ending arrow is **byte-identical** to the same claim written as an event. And propagation is idempotent and order-independent — propagating twice over the same inputs, or shuffling the claims no arrow orders relative to one another, gives a byte-identical world. Tests: `test_a_state_with_nothing_to_end_it_is_an_event`, `test_propagation_idempotent`, `test_propagation_order_independent`.

**INV-multiverse.16 — a claim cut off from the evidence is bit for bit.** For all maps, all `Observe` edits and all separated pairs: a claim with no path to the observed claim and no ancestor in common with it serializes to **identical bytes** in the world with the observation and the world without it. Not *close*: identical. It is a theorem about the solve rather than a hope about a sample, which is why it is stated this strongly. Test: `test_a_claim_cut_off_from_the_evidence_is_bit_for_bit`, in `test_patches.py`.

**INV-multiverse.17 — the Hormuz map reads the way the story reads.** Not a generated statement: pinned to the shipped fixture at its own seed. Five assertions, each a sentence a person can check, replacing the four the old engine's golden test carried.

| # | Assertion |
|---|---|
| 1 | **Both events stand through the strike.** H and S each read as supposed on every day of the strike branch; neither is withdrawn and the world carries no retraction, because the machinery no longer exists |
| 2 | **The state is what falls.** O's number and every claim it sustains are lower on the strike branch than in the base world |
| 3 | **The strike keeps the war-risk premium up.** C is the claim *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%"* and the arrow from S to C is negative, so the strike makes C **less** likely. The roadmap's shorthand *raises the premium claim* means the premium stays high, which is C going **down**. Read the wording before writing the assertion |
| 4 | **A supposition survives a claim nobody believes.** Insert a claim at a stated chance of `.001` with a weak arrow pushing against a supposed claim, and the supposed claim reads as supposed on every day — written as an event and as a state alike |
| 5 | **The strike lowers Brent-below-$68 on the day Brent is judged.** A comparison between the two branches on **one** day: `B · strike · reading` against `B · base · reading`, both on B's own resolve-by day |

Assertion 5 is a comparison **between branches on one day**, where the old golden test compared one branch's series across two days and asked it to rise. Under *the chance it has happened by day t* an event's series can only rise, so that assertion could no longer fail and had to be restated. Directions and orderings, never values.

<!-- VERIFY AT FLIP: the five test names record 0017 lists, and that assertion 2's claim O exists on the fixture with the arrows the story needs. -->

---

## ANTI-PATTERNS

**1. Do not report the spread of a sampler as the range.** *Because* it measures the machine rather than the map: run more of it and the "uncertainty" shrinks, which means a number that moves when you buy computer time is being passed off as a statement about the world. **Do** take the percentiles across versions of exactly solved answers, and keep `test_band_is_not_sampling_noise`, which freezes every stated chance to a point **and** holds every arrow's number at what the map states and demands a range of zero width. *(This anti-pattern kept its rule and lost its mechanism: there is no inner loop left to subtract, and the law of total variance that used to do the subtracting is gone with it.)*

**2. Do not let the `params` or the `strengths` stream see the branch.** *Because* the base world and the branch world then run on different underlying numbers, and every comparison becomes the user's edit plus a wash of elicitation noise, with no way to separate them. **Do** derive both from the seed alone, and each thing's own stream from its own identifier.

**3. Do not model a supposition as a big finite baseline.** *Because* ±4.0 is an arbitrary constant with no source, it contradicts the user in about two per cent of versions, and it makes "suppose this is true" mean "assume ninety-eight per cent", which is not what the button says. **Do** make the claim true in every version while the supposition holds, and show a word where a number would go.

**4. Do not fit `{p, lo, hi}` on the probability scale.** *Because* elicited ranges are lopsided there, so a symmetric fit has to clamp at 0 and 1 and silently stops honouring the three numbers the model stated. **Do** fit the two halves separately on the log-odds scale, which honours all three exactly and can never leave 0–1.

**5. Do not decide that something moved by comparing two ranges.** *Because* the ranges answer a different question: two worlds can overlap across more than half the narrower of them while nearly every version moves the same way. **Do** subtract version by version and read the paired difference; [`diff.md`](diff.md) states the rule.

**6. Do not reach for a module-level random generator, a global seed, or the clock.** *Because* a world would then depend on how many other worlds had been computed before it, which quietly destroys replay and with it every reproducible screenshot. **Do** pass the seed as an argument and build every generator from it.

**7. Do not type a computed number by hand.** *Because* a hand-written number cannot say why it is what it is, which is the traceability veto exactly. **Do** set the fixture's `beliefs.model` equal to its stated chance — the truthful statement *nothing has been computed yet* — and serve the engine's world beside the map.

**8. Do not put "how often these two show up together" on a wire.** *Because* that is a correlation, and a wire claims a mechanism; the two disagree whenever a third thing caused both, and the reader has no way to tell. **Do** compute `conditionals` with the arrow's source **supposed** true.

**9. Do not add `strength_lo` and `strength_hi` to make arrows uncertain.** *Because* a second elicited number per arrow is exactly the budget record 0005 refused, and two numbers about one arrow's width would eventually drift apart. **Do** derive the width from the arrow's `provenance` every time it is needed.

**10. Do not read when a cause arrived off a grid the map's shape chose.** *Because* that grid is a property of the **whole map** — how far out the furthest deadline happens to sit — so a claim inserted at one end of the map re-times a claim at the other end that nothing connects it to, and locality fails through the sampling rather than along the arrows. **Do** take *when* out of the forward pass, which reads each claim's own window and its own arrows and nothing else.

**11. Do not print a number worked out from a table built before the evidence without saying its tolerance.** *Because* the exactness is in the elimination, not in the table the elimination runs on, and a reader shown a number to five places will believe all five. **Do** say what the number was checked against and at what distance — and say, where the grid is the thing being measured, that the check ran on the same grid and so cannot see the grid's own error (B1).

---

## Open questions

**Nothing is open in this chapter.** The four questions it carried from 2026-09-17 were all answered the same day, and each answer now lives in the Behaviour section that owns it: an `impulse` with no `half_life` and a `ramp` with a zero `lag` are in B3, and the two about how a supposition ended died with the calendar that ended it (record 0017). The dated history of how this chapter's arithmetic was chosen lives in decision records 0005, 0014, 0016 and 0017 rather than here.
