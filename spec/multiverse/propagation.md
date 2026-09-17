# Propagation — how a change travels

## Purpose

A branch is a list of edits; a world is what those edits do to the numbers. This chapter is the arithmetic in between. After it, the user can suppose the strait opens, insert a strike the next day, and watch one claim after another move on the days they actually move — and click any number to see the prior it started from and the pushes that were added to it. It settles four things the rest of the product has been deferring: **when** each claim's clock starts, **how** a likelihood is computed on a given day, **how a supposition ends** when a later edit undermines it, and **what the range under a computed number means**. The last one is the reason the range stopped being decoration: it says *how sure we are of the number*, not how much the world can move, and it no longer shrinks when the machine is given more computer time.

Everything here rests on decision record **0014** (accepted 2026-09-17) — *a supposition ends when something pushes back; a range says how sure we are of the number, not how the dice fall* — and on record 0005 (log-odds pushes, trigger and sustain, seeded simulation), which 0014 amends in three places without superseding.

---

## Data model

Written by pull requests 2 and 3 of this stack, in `backend/src/katalyst/domain/patch.py` and `backend/src/katalyst/domain/propagation.py`. Frozen, like everything else in `domain/`: no clock, no network, no global state.

### What `apply` hands to `propagate`

`apply` folds a branch's edits onto a base map, in order, and returns **the map it leaves behind together with every value an edit fixed**:

```python
def apply(
    graph: Graph,
    branch: Branch,
    assignments: tuple[Assignment, ...] = (),
) -> tuple[Graph, tuple[Assignment, ...]] | list[Violation]
```

```python
class Assignment(BaseModel):          # frozen, like everything in domain/
    target: PropositionId             # the claim an edit fixed
    value: bool                       # what it was fixed to
    at: date | None                   # the day it holds from; None means day zero
    by: int                           # which edit did it: its position in the branch, counting from 0
    kind: Literal["do", "observe"]    # which of the two verbs the user chose
```

**`Proposition` grows no "fixed value" field, and never will.** A fixed value is a fact about a *world*, not about a claim. Written onto the claim, the same claim would mean different things in different branches and the base map would stop being the one thing every branch agrees on ([`branches-and-worlds.md`](branches-and-worlds.md), open question 1, decided 2026-09-17). The pair — map and assignments — is also what a further `apply` takes, which is what keeps the concatenation law type-checking (INV-5: applying two branches in a row equals applying the two joined).

The list stays **ordered** so a later assignment reads as overriding an earlier one rather than silently replacing it. That ordering is what the tile's *Supposed · Oct 1 → Retracted · Oct 2* line is drawn from (UX-14 in `PRODUCT_REQUIREMENTS.md` §7).

### What a claim's day looks like

```python
SeriesState = Literal["sampled", "supposed", "withdrawn", "pushed"]
# sampled   — the ordinary case: no supposition has ever touched this claim
# supposed  — a `do` is holding; the claim is true in every draw and the tile shows a word
# withdrawn — the supposition has been undermined and no opposing push has arrived yet
# pushed    — an opposing push is live
```

```python
class Retraction(BaseModel):
    target: PropositionId    # the claim whose supposition ended
    at: date                 # the day it ended — the day the opposing arrow's SOURCE became true
    by_link: LinkId          # the arrow that undermined it
    by_claim: PropositionId  # that arrow's source — the claim the tile names in its badge
    by: int                  # the edit that introduced the arrow, by position in the branch
```

**`by` is a required `int`, never `None`** (decided 2026-09-17), and that is a small theorem rather than a convention. A `do` cuts every arrow into its target that is present **when it is applied**. So any arrow that later undermines that supposition cannot have been on the map at the time — it was added afterwards, by an edit, and every edit has a position in the branch. There is no case left over, so there is no `None` to represent it, and the badge can always name the edit responsible.

`propagate` is told those positions through a keyword-only argument, `introduced_by: Mapping[LinkId, int]`, defaulting to `NOTHING_ADDED` — an empty mapping that cannot be written to — and computed from the branch by a pure helper in `domain/patch.py`. **This is one of the two additions to the shapes the plan wrote** (`World.series_days` is the other), and it is here because a `Graph` records what a map contains, not which edit put it there: that history lives in the branch, and `propagate` is handed it rather than guessing.

If an arrow undermines a supposition and is **not** in that mapping, `propagate` raises `ValueError`. It is the one place in the whole function that raises, and deliberately so: every other failure is a user's map or a user's edit and comes back as a `Violation` they can read, but this one is our own caller handing the engine an incomplete answer to a question only our code asks. That is a contract breach in our code, not a mistake a user can make, and it should stop the program rather than produce a world with a badge that cannot name anything.

### What a world is

```python
class World(BaseModel):                                   # frozen
    base_id: str
    branch_id: BranchId | None
    seed: int
    versions: int                                         # the outer loop — how sure we are of the inputs
    worlds: int                                           # the inner loop — how the dice fall
    day_zero: date
    days: int                                             # the window's length in whole days, not the number of series points
    graph: Graph                                          # the map apply left behind
    assignments: tuple[Assignment, ...]
    retractions: tuple[Retraction, ...]
    beliefs: Mapping[PropositionId, Belief]               # owner "model", read on each claim's resolve-by day
    series_days: tuple[int, ...]                          # which day of the window each point of every series
                                                          # sits on; evenly spaced unless the 180-point cap
                                                          # fired, which keeps every claim's resolve-by day
    series: Mapping[PropositionId, tuple[float, ...]]     # one likelihood per day above, for the time axis
    states: Mapping[PropositionId, tuple[SeriesState, ...]]  # one named state per day, same length as the series
    conditionals: Mapping[LinkId, Belief]                 # empty by default — see below
    range_shares: Mapping[PropositionId, Mapping[PropositionId, float]]
                                                          # whose prior explains whose band; no route reads it until stack 06
    warnings: tuple[str, ...]                             # plain sentences; the low-survival warning lives here
```

`series` is what makes the scrubbable time axis possible (UX-3), and `states` is what lets the canvas say *Supposed* where a number would mislead and *withdrawn — no live push yet* where a number would confuse. Every entry in `beliefs` is owned by `model` and is read on that claim's own resolve-by day — INV-1 guarantees every claim has one, so there is always such a day, and it is the day the claim is judged. Which day a *change list* row is read on is a different question and belongs to [`diff.md`](diff.md).

**`conditionals` means *supposed*, not *observed*, and it is empty on a freshly built world.** The number on a wire's midpoint chip is the target's likelihood **with that arrow's source supposed true** — a `do`, the interventional number. It is never "how often do these two show up together", which is the correlational quantity [`../graph/link.md`](../graph/link.md)'s anti-pattern 3 refuses; putting that on a wire claiming a mechanism would be the worst kind of quiet lie. Computing it costs a whole extra propagation per arrow — eight on the Hormuz map, about eighty on a sixty-claim one — for a number most users never open, so it is fetched **lazily**, one arrow at a time, through `POST /api/worlds/conditional`. Laziness costs nothing in honesty: the number is a pure function of the same three inputs plus the arrow, so a lazily fetched number is byte-identical to an eagerly computed one.

### The one entry point

```python
def propagate(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    versions: int = 2_000,   # the outer loop: versions of the map (how sure we are of the inputs)
    worlds: int = 8,         # the inner loop: worlds per version (how the dice fall)
    introduced_by: Mapping[LinkId, int] = NOTHING_ADDED,  # which edit added each arrow; see Retraction above
) -> World
```

Sixteen thousand worlds in total, and the two numbers are not interchangeable: they measure two different kinds of not-knowing, and B5 below says which is which.

**What it costs, measured on the shipped engine.** The Hormuz strike branch — eight claims over a sixty-one-day window — takes **67 milliseconds**. A sixty-claim map read on a single day takes **41 milliseconds**; over a sixty-one-day window, **544 milliseconds**; over a year capped at 180 points, **1.4 seconds**. The cost is claims × days × 16 000 worlds, so the window is the term that grows, not the map. (The plan's "about ten milliseconds at sixty claims" measured one day in a prototype and is not what the shipped engine does over a window.)

**Three things that are deliberately absent.** There is no `strength_lo` and no `strength_hi`, now or ever: link strengths are **fixed numbers in stack 03a** and only priors vary between versions. Widening an arrow is derived from its `provenance` — "how well-backed" becomes "how wide" — and that ships in stack 04, where arrows finally differ from one another; every arrow in today's fixture is hand-written `argued` or `asserted`, so doing it now would widen everything by the same amount and teach nobody anything. There is no `scipy`: the Latin hypercube — a way of spreading draws evenly instead of letting them clump — is three lines of `numpy`, and the percentiles are one. And there is no module-level random generator — see B7.

---

## Behaviour

Worked on the Strait of Hormuz map. Its claims, quoted from the fixture word for word:

| | The claim | `prior` | Judged on |
|---|---|---|---|
| **H** | *The Strait of Hormuz reopens to unrestricted commercial transit.* — the hypothesis | `.35 (.22–.50)` | day 31 |
| **C** | *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.* | `.30 (.18–.45)` | day 30 |
| **B** | *Brent crude settles below $68 for five sessions.* | `.28 (.15–.42)` | day 14 |
| **R** | *OPEC+ announces output restraint.* — the tail | `.18 (.08–.32)` | day 60 |
| **M1** | *A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.* — tradeable | `.40 (.28–.55)` | day 30 |
| **M2** | *The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days.* — tradeable | `.35 (.22–.50)` | day 45 |
| **N1** | *Omani-mediated United States-Iran talks resume publicly.* — real, and no venue prices it | `.22 (.12–.36)` | day 60 |
| **S** | *A confirmed military strike on Iranian territory.* — on the branch only | `.06 (.02–.14)` | day 1 |

"Judged on" is the claim's own `resolution.by`, counted from day zero — the day the claim is settled by, and therefore the day its tile's headline is read on. B's is a **fortnight**: five settlements below $68 is about a fortnight of sessions, and the fixture was tuned to say so (it used to read day 45, by which time both pushes on B had faded to nothing much and the tile read almost exactly B's own prior).

Day zero is 2026-10-01.

Every number below is **illustrative**, exactly as the fixture's are, and pull request 3 may tune the fixture's inputs to make the example richer (each tuned value carrying a comment saying what it was, what it is and why). The golden test therefore asserts **directions and orderings**, never these values.

### B1 — The time axis: day zero, the window, and the day a claim is settled

**Day zero is `as_of`**, passed in by `engine/worlds.py` from the stored example's `fixture_date`. `Graph` grows no date field. The window runs from day zero to the latest `resolution.by` date on the map, in whole days. Every date becomes an integer day index at the edge of `propagate` and stays an integer inside it.

**Every claim gets a day on which it is *settled*** — the day its clock starts, so that any arrow leaving it measures elapsed days from there. Three rules, in order:

1. If an assignment fixes it, that day is the assignment's `at` (day zero when `at` is `None`).
2. Otherwise it is the earliest day any live incoming arrow reaches it: the day that arrow's source was settled, plus the arrow's `lag`.
3. A claim with neither an assignment nor a live incoming arrow is settled on **day zero** — the map carries no timing information about it, so its clock starts at the beginning of the window.

**Being settled is not being true.** A claim with no assignment is sampled from its own `prior`, every draw, exactly as always; nothing is ever forced true because its clock started. The two ideas are separate and conflating them is the mistake this paragraph exists to prevent. It follows that the settled day — call it `t_source` — is **one schedule, computed once from the shape of the map**, the same in every draw, while **truth is per draw**: an arrow's term is non-zero only in those draws where its source came out true. One schedule, sixteen thousand different worlds running along it.

**The window is capped at 180 points.** If the window is longer than 180 days the series is sampled down to 180 points and a sentence in `warnings` says so. The sampling is not blindly even: **every claim's resolve-by day is kept among the points**, and the rest are spread evenly around them. A tile's headline is read on the claim's own resolve-by day, so without that guarantee the headline could be a number that appears nowhere on the sparkline underneath it — the same guarantee [`diff.md`](diff.md) gives a delta row's `at_day`.

Which is why the world carries **`series_days`**: one entry per point, saying which day of the window that point stands for. On a window of 180 days or fewer it is simply every day, and reading it is the same as counting. Past that the points are unevenly spaced, and `series_days` is then the only thing that says where they sit — a sparkline drawn as though they were evenly spaced would quietly misplace every date on the axis. `states` and every claim's `series` are always the same length as `series_days`.

> **On the Hormuz map.** The longest resolve-by date is R's and N1's, sixty days out, so the window runs day 0 to day 60 — sixty-one points — and the cap never bites: `series_days` is `(0, 1, 2, … 60)`. On the strike branch, H is settled on day 0 by `Do(target="H", at=2026-10-01)` and S on day 1 by `Do(target="S", at=2026-10-02)`. C is settled on day 0, because `H → C` carries `lag=0.0`. B is settled on **day 1**: `S → B` carries `lag=0.0` and S was settled on day 1, so that arrow reaches B the same day — earlier than `H → B`'s two-day lag (day 2), `R → B`'s five (day 5) or `C → B`'s seven (day 7). In the base world, where there is no S, B is settled on day 2 via `H → B`. B's own clock is what the arrows *leaving* B measure from, so on the branch M1 is settled on day 2 (`B → M1`, one-day lag) and M2 on day 4 (`B → M2`, three-day lag), each a day earlier than in the base world. R is settled on **day zero**: its only incoming arrow is `B → R`, a feedback arrow, which the engine sets aside ([`interventions.md`](interventions.md), *the map the engine works through is the map with feedback arrows set aside*), so R has no live incoming arrow and rule 3 applies. It is also why R is `unchanged` on the strike branch.

### B2 — One claim's log-odds on one day

At day *t*, for each claim, in an order that always puts causes before effects — a topological order over **the map the engine works through**, which is the map with feedback arrows set aside; that rule is stated once in [`interventions.md`](interventions.md) and cited here. There is always such an order, because INV-6 (a map has no loops once feedback arrows are removed) guarantees it.

```
log-odds(claim, t) = baseline(claim) + Σ over live incoming arrows: strength × shape(t − t_source)
```

`baseline(claim)` is the log-odds of the claim's own `prior` — its likelihood before anything causes it. *Log-odds* is the natural logarithm of the chance a claim is true divided by the chance it is false; it is the scale on which independent pushes **add** instead of multiplying, which is why a claim with three parents gets three numbers added together rather than a table of eight combinations. Where a formula below needs it by name, the log-odds of a likelihood `x` is written `logit x`, and the way back — log-odds to a likelihood between 0 and 1 — is written `sigmoid`.

`shape` is a plain function of **elapsed days**, and it is zero before the cause is settled. Writing `u` for `t − t_source` and `L` for the arrow's `lag`:

```
impulse(u) = 0                          for u < L        zero through the lag, then a spike
             2 ** (−(u − L) / half_life)    for u ≥ L    that halves every half_life days

step(u)    = 0                          for u < L        zero through the lag, then
             1                          for u ≥ L        full size, held

ramp(u)    = 1                          for u ≥ L        full size, held — this branch is tested first
             u / L                      for 0 ≤ u < L    climbing from 0 to 1 across the lag
```

**Two edge cases that need no special case.** A `ramp` whose `lag` is `0.0` has no rise time, and because the `u ≥ L` branch is tested first, the climbing branch is never reached and the arrow behaves as a `step` — full size on the same day. That is a *consequence* of the order the branches are written in, not a rule anyone has to remember, and there is no division by zero. And an `impulse` with no `half_life` never arrives: a spike that fades must say how fast, so a map carrying one is refused by `validate` before `propagate` ever sees it (`impulse_without_half_life`, [`../graph/validity.md`](../graph/validity.md) rule 13, decided 2026-09-17). Reject, never repair — the alternatives were to read it as no decay, which silently turns the arrow into a `step` and overrides the author's choice of shape, or to invent a number and attribute it to the model.

**`lag` is the ramp's rise time**, and there is no `rise_time` field in version 1. That settles [`../graph/link.md`](../graph/link.md)'s open question 5. A `half_life` on a `step` or a `ramp` is a **violation**, not an ignored field — `half_life_without_impulse`, already on `main`; this stack cites it and does not add it again.

**A warning above ±5.** `validate` is untouched and puts no ceiling on `strength`; an unbounded number is the honest type. But ±5 is roughly 1% to 99% on a coin flip, so `propagate` adds a plain sentence to `warnings` naming any arrow beyond it. A warning, not a rejection: the map is still legal, and the user should be told.

> **On the Hormuz map.** B's prior is `.28`, whose log-odds is `−0.94`. On the strike branch, day 1: `S → B` is an impulse with `lag=0.0`, so it is already at full size — `−2.4`. `H → B` has not arrived (two-day lag); `C → B` has not arrived (seven-day lag); `R → B` has not arrived (five days from R's day zero). Total `−0.94 − 2.4 = −3.34`, about **`.03`**. Day 2: `H → B` arrives at full size, `+1.6`, and `S → B` has faded by one day of its ten-day half-life to `−2.24`. Total `−1.58`, about **`.17`**. B *rises* between day 1 and day 2, and that rise is golden assertion 4.

### B3 — Trigger and sustain, as arithmetic

Both kinds of arrow use the same formula. They differ in one clause, and it is the whole domino-and-apple distinction:

* A **sustain** arrow's term is **zero on any day its source is not true**. The desk is gone; the apple falls.
* A **trigger** arrow's term **keeps running on its own schedule once fired**, whatever the source does afterwards. The domino stays fallen.

Nothing else differs. The two behave identically for as long as the cause holds, and part company the day it stops. [`../graph/link.md`](../graph/link.md) draws it:

```
                   t0                      t1
                   │                       │
trigger (domino)   ▼                       ▼
push on effect ────█████▇▇▆▆▅▅▄▄▃▃▂▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
                   └ fires once, then fades on its own;
                     t1 changes nothing — the domino stays fallen.

sustain (apple on desk)
push on effect ────████████████████████████▁▁▁▁▁▁▁▁▁
                   └ holds while the cause holds …
                                           └ … and is gone at t1.

t0 = the cause becomes true.    t1 = the cause stops being true.
The cause is the link's `source`; the effect is its `target`. Elsewhere
these two are also called the parent and the child.
```

And the three shapes, so the two pictures can be read together:

```
                   cause true             lag ends
                   │                      │
impulse  push  ────┴──────────────────────█▇▆▅▄▃▂▁▁▁▁▁   spike, then halves every half_life
step     push  ────┴──────────────────────██████████████   switches on and holds
ramp     push  ────┴▁▁▁▂▂▂▃▃▃▄▄▄▅▅▅▆▆▆▇▇▇▇██████████████   climbs across the lag, then holds
```

> **On the Hormuz map.** `H → B` is a trigger that fired on day 0, so on day 2 it delivers `+1.6` to B even though H's supposition was withdrawn on day 1 — that domino is down. `H → C` is a sustain, so from day 1 its `+1.1` is present only in the draws where H still came out true, which after day 4 is about eight in a hundred. Same cause, two honest behaviours, one branch.
>
> The clearest reading of the difference is **N1**, *Omani-mediated talks resume publicly*. `H → N1` is a trigger, and H was supposed true on day 0, so it fired in **every** world. The strike then withdraws H — and N1 still comes out **higher** on the strike branch than in the base world, `.37` against `.28`, because that domino cannot be stood back up. Meanwhile C, held by a sustain arrow from the same claim, collapses from `.40` to `.07`. One cause, one branch, two claims moving in opposite directions, and the only difference between them is a single field on the arrow.

### B4 — How a supposition ends

**A supposition is a hard fact until something undermines it.** While a `do` holds, the claim is simply **true in every draw** — not a large log-odds baseline that arrows can argue with. There is no ±4.0, no `.98`, no number at all: the tile shows the word *Supposed* and its date where a likelihood would go. That is what "suppose this is true" means in English, and a tool that answered "suppose this is true" with `.98` would be lying about what the user asked for.

**It stops holding on the day the *cause* of the first live opposing arrow becomes true.** Not the day that arrow's push reaches full size — the day the world changed. An arrow into the target is *opposing* when its push runs against the value that was supposed: negative strength against a claim supposed true, positive against one supposed false. In code: `Retraction.at = t_source` of that arrow's source, and the arrow's own `lag` then does its ordinary work afterwards. From that day the claim is computed like any other claim: its own prior, plus every live arrow, each arriving on its own schedule.

Tying the end of a supposition to the *arrival* instead would tie "do I still take your word for this" to a delay parameter — change a lag from three days to thirty and the supposition silently outlives the news.

**When two opposing arrows land on the same day, the badge names one, and which one is fixed** (decided 2026-09-17). Take the arrow whose introducing edit came **first in the branch**; within one edit, its position in `Insert.links`; for an arrow that was on the base map all along, its position in `graph.links`. All three orderings already exist and are already load-bearing, so nothing new has to be remembered and replay still holds: the same map, branch and seed name the same arrow on the badge every time.

**A retracted claim can be supposed again** (decided 2026-09-17), and what happens then is a consequence of the settled rule that **a `do` cuts every arrow pointing at its target at the moment it is applied**. A second `do` cuts them all — *including the arrow that undermined the first supposition* — and a cut is not timed: the arrow is gone from the map the branch leaves behind, not merely suspended. So the second supposition holds from its own date, and the thing that ended the first one can never end it again.

That rules out the series people expect. **`supposed · withdrawn · pushed · supposed` cannot occur**: suppose H, let `S → H` withdraw it, then suppose H again — the second `do` cuts `S → H`, so nothing ever undermines the first supposition either, and H reads `supposed` on every day of the window. The undermining is not replayed and then reversed; it never happens.

What *can* happen is a second supposition undermined by an arrow added **after** it: suppose H, insert `S` with `S → H`, suppose H again (cutting `S → H`), then insert a further claim with a new arrow into H. That series reads `supposed · withdrawn · pushed`, with **one** `Retraction` — one per ending, always, so a claim carries as many retractions as suppositions that actually ended.

Two tests hold the pair up: `test_a_claim_can_be_supposed_again_after_it_was_undermined` and `test_supposing_a_claim_again_cuts_what_undermined_it`.

**What a supposed claim's `Belief` holds.** While a supposition holds the claim is true in every draw, so its `Belief` is `p = lo = hi = 1.0` — or `0.0` where it was supposed false. That exists for exactly one reader: the path product (INV-8, the rule that a chain's multiplied-out likelihood is reported honestly), which needs a factor to multiply. **No other surface may read it.** Every other reader checks `states` first and prints the word *Supposed*, because a tile showing `1.00` claims a certainty about the world that the user never asserted — they asserted a supposition.

> **On the Hormuz strike branch, with day zero at 2026-10-01:**
>
> | Days | What `H` reads | Why |
> |---|---|---|
> | Oct 1 | **Supposed · Oct 1** — a word, not a number | The `do` holds; `H` is true in every draw |
> | Oct 2 – Oct 4 | **`.36`**, the series marked *withdrawn — no live push yet* | `S` became true on Oct 2, so the supposition is withdrawn that day. `S → H` carries `lag=3`, so nothing is pushing yet and `H` falls back to its own prior, `.35` |
> | Oct 5 onward | **about `.08`**, the series marked *pushed* | `S → H`'s step reaches full size — `−1.9` on a log-odds baseline of `−0.62` — and pushes `H` down |
>
> The tile reads *Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"* — UX-14's badge, with the claim named in the fixture's own words — and the world carries one `Retraction` with `at=2026-10-02`, `by_link="S->H"`, `by_claim="S"`. The three-day gap between the date on the badge and the day the number moves is **not a bug to hide**. It is the honest shape of the answer, and the series has to be able to say so — which is exactly why every day carries a named state.
>
> The engine's own figures, seed `20261001`: `.356` on the withdrawn days and `.081` from Oct 5. Do the two sums by hand and you get `.35` and `sigmoid(−2.52) = .074` — both right as hand arithmetic. The reported numbers sit a hair above because each is a mean across two thousand versions, and that mean sits above the middle whenever the likelihood is below `.5`; B5 explains it. Where this chapter quotes a number the engine reported, it is the engine's.

**The rejected alternatives**, one line each, kept for the record. *A permanent seal* — the user's first edit would silently veto their third; [`interventions.md`](interventions.md) rejected it on 2026-09-17, and it deletes the showcase. *A large finite baseline the arrows argue with* — at ±4.0 an arrow of `−1.9` moves the claim from `.98` to `.89`, which is not a retraction, and it makes "suppose" mean "assume ninety-eight per cent", which is not what the button says. *Hold until the push lands* — that is the delay-parameter trap above, and it is a cliff with no state in between.

### B5 — The two kinds of not-knowing, and where the range comes from

Read this before any formula, because it is the idea the whole design rests on.

* **How the dice fall.** The strait either opens or it does not. That is already inside `p`: `p` is the share of worlds in which the claim came out true.
* **How sure we are of the numbers we put in.** Every prior on the map was elicited, and a different but equally defensible set of priors would give a different `p`. **That** is the range.

So a wide band means *"we are not sure what number to give you; more homework would move it"* — never *"the event is more volatile"*. That is the one sentence a trader has to be able to repeat, and the chip says it: **model interval, uncalibrated · how sure we are of `.35` — not how much the world can move.** The formal name for two loops of this shape — one for how sure we are of the inputs, one for how the dice fall — is a second-order, or two-dimensional, Monte Carlo.

**What a stated `{p, lo, hi}` means: a split logit-normal** — a bell curve on the log-odds scale with its two halves fitted separately: middle `p`, 10th percentile `lo`, 90th percentile `hi`. "Eight times in ten" is the phrase. The halves are fitted **on the log-odds scale**, the scale the pushes add on:

```
s_lo = (logit(p) − logit(lo)) / 1.2816        # 1.2816 is the 90th percentile of a standard normal
s_hi = (logit(hi) − logit(p)) / 1.2816
```

`logit x` is the log-odds of `x`, defined in B2; `sigmoid` is the way back — it turns log-odds into a likelihood between 0 and 1.

Version *k* draws one standard-normal number `z` per stated range and reads the prior back as `sigmoid(logit(p) + z × s_lo)` when `z` is negative and `sigmoid(logit(p) + z × s_hi)` when it is positive. Separately, because real elicited ranges are lopsided: over the seven base-map claims the fixture's own ranges are near-symmetric on log-odds (mean gap ratio 0.94) and clearly skewed on probability (1.24). This honours all three stated numbers exactly, stays inside 0 and 1 with no clamping, and needs no new field on `Belief`.

**One consequence, written here rather than left for a reader to trip over.** The mean of a split logit-normal sits slightly above its median when `p < .5`. So a claim's `prior.p` and its computed `beliefs.model.p` differ by a hair *even for the hypothesis, which has no causes*: H is `.35` as a prior and `.36` as a computed belief. Both are right. [`../graph/belief.md`](../graph/belief.md)'s `prior` versus `beliefs.model` table says so too.

**The loop.**

1. Draw **2 000 versions** of the map with a Latin hypercube over every prior's fitted shape. `numpy` only, three lines. A version is **one coherent set of numbers this model would have stood behind**, never "every low end at once".
2. Inside each version, run **8 worlds**.
3. **Keep the likelihood, not the coin flip**: for each claim keep the likelihood it came out true in that world. Free variance reduction — the number is already computed. (The textbook name for this is Rao-Blackwellisation.)
4. **Correct for inner noise** with the law of total variance (the rule that a total spread is the spread of the averages plus the average of the spreads — so subtract the second), so that what is left is the spread across versions and not the spread across eight coin flips. Writing `q` for the 2 000 version-level answers and `inner_var` for the spread of the eight likelihoods inside a version — measured the unbiased way, dividing by one fewer than the number of worlds, because eight numbers give only seven independent comparisons and dividing by eight would understate the noise and leave the band a shade too wide:

```
f = sqrt(max(0, 1 − mean(inner_var / worlds) / var(q)))
q_corrected = mean(q) + (q − mean(q)) · f
```

5. `p` is the mean over both loops. With no `observe` on the branch that is the same number as `mean(q)`, because every version runs the same number of worlds; with an `observe` it is the survival-weighted mean of B6, and the recentring above uses that same weighted mean. `lo` and `hi` are the 10th and 90th percentiles of the corrected version-level values. `f` is clamped at 0, so a claim whose apparent spread was all noise reports a zero-width band rather than an imaginary number.

**Four designs, measured on 2026-09-17** — on Hormuz claim B read at **day 45**, against the exact answer by enumeration, `.35 (.20–.49)`. This is a dated comparison of four *designs*, so it is kept as it was measured; B's resolve-by day has since moved to day 14, and the shipped engine still reports `.35 (.20–.49)` for B at day 45.

| Design | Reports | Wobble of the band edges across seeds |
|---|---|---|
| Three runs: all lows, then all highs | `.19–.50`, and it is not a bound — `R → B` is negative, so the true corner is `.158–.567` | none |
| 20 batches of 500 | `.25–.46` — a quarter of that width is coin-flip noise, and the band is 28% too narrow | ±.021 |
| The analytic delta method — calculus instead of sampling: work out how much each stated range moves the answer, and add those up | `.22–.52`, accurate to .004, but fifty times slower and first-order only | none |
| **2 000 × 8, likelihoods kept, noise-corrected** | **`.20–.50`** | **±.002 to ±.003** |

The delta method is kept — not as the engine, but as a **cross-check in a test**. On the shipped engine, B in the base world on its own resolve-by day: the sampler reports `.2495–.5451` and the analytic answer is `.2459–.5455`. Two independent methods, agreeing to two significant figures.

**Where the width comes from, free.** From the same outer sample, sorting the versions into bins by the value each prior drew, and comparing the bins' averages, gives each claim's **share of another claim's band** — how much of the width comes from not being sure of *this* claim. Six lines of `numpy`, nothing run twice. It is carried as `range_shares[target][source]` — the share of `target`'s band explained by `source`'s prior — and **no route reads it until stack 06**, where it becomes FR-21's "where to spend modeling budget" ranking. It is computed and carried now because the sample it comes from is thrown away otherwise.

On the shipped fixture, B in the base world read on its own resolve-by day: **65% of B's band is B's own prior**, then H at 6.1% and C at 4.2%. Pin B's prior down — freeze it at a point — and the band goes from `.25–.55` to `.34–.46`: **from 30 points wide to 12**. That is the ranking FR-21 asks for, in one number per claim. (FR-21 and record 0014 say "its own base rate"; the thing that varies between versions is the claim's `prior`, which is the word used here.)

**Two counter-intuitive warnings, both measured.**

* **A `do` does not reliably narrow what is downstream.** It collapses the target's own band, but B's width goes *up* under `do(H)` — `.296` to `.318`, measured — because the logistic curve is steeper where the answer lands. The honest thing to show is the **share**, not the width: H's contribution to B's band falls from **6.1% to 0.4%**, which is the sentence a reader can act on.
* **A terminal's band is dominated by its own prior.** An upstream range reaches it multiplied by `p(1−p)`, which is at most a quarter. Do not build the demo around "widen H and watch B widen"; it moves about 4%.

### B6 — `observe`: keep only the consistent draws

`observe` records that a claim actually came true or false. Unlike `do` it cuts nothing, and it is handled in the **inner** loop: inside each version, keep only the worlds in which the claim came out as observed, then **weight that version by its survival share** when the two loops are pooled. Five lines of importance weighting — a version under which the observation was likely counts for more than one under which it was a fluke.

**This is why observing reaches upstream and supposing does not.** Throwing worlds away changes what the survivors say about the claim's *causes* just as much as what it *causes* — which is exactly why `observe`'s affected set under INV-4 (locality: an edit changes only what is still connected to its subject in the map the edit leaves behind) includes its ancestors and their descendants, while `do`'s does not. INV-3 (assert is not observe) is the product-level statement of the same thing, and the two operations are never merged into one "set this value" control.

**The weighting reaches only what the observation is evidence about.** Survival-weighting every claim on the map would be wrong, and the property tests caught it: an observation is evidence about the claim observed, about what that claim causes, about its own causes, and about what those causes go on to cause — and about nothing else. A claim with no connection to the observation is read off **every** world, unweighted, which is both exact and what keeps INV-4 true (locality: an edit changes only what is still connected to its subject in the map the edit leaves behind). Weighting it would have moved it by a wash of sampling noise and called that an effect.

**Below about two per cent survival the world carries a loud warning, and the warning says the *range* is unreliable, not merely the point.** A version that survived twice out of eight is contributing a very noisy number to the band, and the noise correction can only subtract what it can measure.

> **On the Hormuz map.** `Observe(target="C", value=True)` — the premium printed below 0.4% this morning — keeps only the worlds in which C came out true. C's own cause is H, and the surviving worlds are the ones where H more often came out true, so H rises: cheap insurance is evidence the lane really is open. `Do(target="C", value=True)` on the same claim leaves H exactly where it was. That difference is the product.

### B7 — Two seed streams, and replay

Everything comes from the one `seed` argument, through `numpy.random.Generator` objects built from it and nothing else. **No module-level generator, no clock, no global state, ever.** The same `(map, branch, seed)` gives byte-identical worlds on any machine — NFR-2, the determinism requirement — which is what makes a three-day-old screenshot reproducible from three values.

There are **two streams**, and keeping them apart is load-bearing:

| Stream | Drives | Rule |
|---|---|---|
| `params` | The outer loop — which 2 000 versions of the map we try | **Must not depend on the branch.** A base world and a branch world built from the same seed use the *same* 2 000 versions |
| `worlds` | The inner loop — how the dice fall inside one version | Ordinary; may depend on anything |

**Both streams are derived per claim**, from the seed and a hash of the claim's own identifier. So adding a claim to the map cannot shift any other claim's draws — a claim's numbers depend on its own name and the seed, and on nothing about how many neighbours it has or what order they were written in. That is what makes `test_versions_do_not_depend_on_the_branch` hold *exactly* rather than approximately, and it is also what makes the dice cancel out of a paired comparison: version *k* of the base world and version *k* of the branch world drew the same numbers for every claim they share.

The `params` rule is what makes a difference between two worlds readable. Compare a base world and a branch world version by version and the only thing that changed is the edit — the numbers underneath were held fixed. That is *common random numbers*, and without it every comparison is the user's change plus a wash of sampling noise, which is exactly the failure [`branches-and-worlds.md`](branches-and-worlds.md)'s anti-pattern 4 describes. [`diff.md`](diff.md) spends the whole of it: a change is read off the paired difference, never off whether two bands overlap.

> **On the Hormuz map.** Supposing the strait opens moves B, on its own resolve-by day, from `.40 (.25–.55)` to `.58 (.42–.73)`. The two bands **overlap from `.42` to `.55`** — about two fifths of each — and a reader comparing bands would call that inconclusive. Compare the same versions against each other instead and **99.9% of them move the same way**, by `+.19` (`+.10` to `+.27` eight times in ten); [`diff.md`](diff.md) owns that number and the rule that reads it. Band overlap would report "no change" about the single clearest change on the map.

### B8 — What the user ends up looking at

One `propagate` call fills every field of `World`. On the Hormuz strike branch, with the fixture's seed `20261001`:

| What the interface reads | Where it comes from |
|---|---|
| The number on a tile | `beliefs[claim]`, read on that claim's own resolve-by day, rendered at two significant figures with its range (NFR-1) |
| The sparkline and the scrubber | `series[claim]` against `series_days`, one point per day, so the spike and the fade are visible rather than hidden (UX-3) |
| *Supposed* / *withdrawn — no live push yet* / *pushed* | `states[claim]`, the same length as the series |
| The **Retracted · date · by "…"** badge | `retractions`, which names the day, the arrow and the claim (UX-14) |
| The number on a wire's midpoint chip | `conditionals[link]`, fetched one arrow at a time, and always the *supposed* number |
| Sentences under the map | `warnings` — low survival, a sampled-down series, a strength beyond ±5 |

**What the map actually reads**, engine's own numbers, each on the claim's own resolve-by day:

| | Base world | Strike branch | |
|---|---|---|---|
| **H** the strait reopens | `.36 (.22–.50)` | `.08 (.04–.13)` | the supposition is withdrawn and then pushed down |
| **C** the premium falls below 0.4% | `.40 (.25–.55)` | `.07 (.03–.11)` | `S → C` holds the premium up |
| **B** Brent below $68 | `.40 (.25–.55)` | `.30 (.17–.44)` | the strike puts the risk premium back in the price |
| **R** OPEC+ restraint | `.19 (.08–.32)` | `.19 (.08–.32)` | **byte-identical** — reached only by a feedback arrow |
| **M1** the Polymarket contract | `.46 (.32–.60)` | `.41 (.28–.55)` | tradeable |
| **M2** XLE against SPY | `.43 (.28–.58)` | `.36 (.23–.51)` | tradeable |
| **N1** talks resume | `.28 (.15–.42)` | `.37 (.22–.53)` | **up** — see B3 |

Two rows repay a second look. **R is identical to the byte**, which is the feedback rule doing its work rather than a coincidence. And **N1 goes up** on the branch that makes everything else worse: `H → N1` is a trigger, H was true in every world on day 0, so that push fired everywhere and stays fired after the strike withdraws H. What already fell stays fallen, and here what already rose stays risen.

Four things are what the golden test checks, and each is a sentence a person can read back: the strike lowers B; the strike makes **C less likely** (`C` is the claim *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%"* and `S → C` is `−2.0`, so the shorthand "the premium stays high" means C goes **down** — getting this backwards silently inverts the test); H is *supposed*, then *withdrawn*, then *pushed*; and B **rises** between day 1 and day 2, because what already fell stays fallen.

---

## INVARIANTS

Each statement is true for every input a named generator can produce, and each names the test that checks it. Generators live in `backend/tests/strategies.py`: `graphs()` yields random **valid** maps, `interventions(graph)` yields edits whose subjects exist in that map, `branches(graph)` yields branches of such edits, `beliefs()` yields likelihoods with their ranges, `seeds()` draws integer seeds, and `separated_pair(graph)` picks two claims joined by no path and sharing no ancestor. Tests live in `backend/tests/unit/domain/test_propagation.py` unless noted. Everything here lands in **stack 03a**, because nothing propagates before it.

This chapter uses the local numbers `INV-multiverse.9` through `.17`. `.1`–`.5` belong to [`interventions.md`](interventions.md) and `.6`–`.8` to [`branches-and-worlds.md`](branches-and-worlds.md); `.18` onward belongs to [`diff.md`](diff.md).

Two of them, `.13` and `.17`, are pinned to the shipped Hormuz fixture at the fixed seed rather than to a generator, and say so. The rest quantify over generated maps.

**INV-7 — honest numbers (product invariant: `0 ≤ lo ≤ p ≤ hi ≤ 1` on every belief, always).** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s` from `seeds()`: every belief and every series point in the world built from `(g, b, s)` lies between 0 and 1 and satisfies that chain. Tests: `test_probability_bounds`, and `test_belief_bounds_after_any_sequence` driven by `GraphEditMachine`.

**INV-3 — assert is not observe (product invariant: `do` moves nothing upstream of its target; `observe` may).** For all maps `g` from `graphs()` and all `Do` edits from `interventions(g)`: every ancestor of the target is byte-identical in the base world and the branch world. For all maps containing a claim with at least one parent strictly between 0 and 1, an `Observe` on that claim changes at least one ancestor. Tests: `test_do_leaves_ancestors_unchanged`, `test_observe_may_update_ancestors`.

**INV-4 — locality (product invariant: an edit changes only what is still connected to its subject in the map the edit leaves behind).** For all maps `g` from `graphs()` and all edits from `interventions(g)`: every claim outside the edit's affected set is byte-identical in the **base world** and the **branch world** — the full statement, over propagated worlds, for all six operations, each pinning at least one fully separated claim from `separated_pair(graph)`. The test computes the affected set itself from the shape of the map with `networkx` — over the map with feedback arrows set aside, by [`interventions.md`](interventions.md)'s rule — and never calls `domain.patch.affected_set`; a test that agrees with the code it is testing is not a test. The companion `test_a_feedback_arrow_never_carries_a_change`, in the same file, holds the other half: a claim reachable only through a feedback arrow is byte-identical in the two worlds, which is why R is untouched on the Hormuz strike branch. Test: `test_intervention_locality`, in `backend/tests/unit/domain/test_patches.py`. Re-checked after every step of `GraphEditMachine`, in the same file, which also re-checks the no-loops rule (INV-6) and the 0-to-1 bounds (INV-7) and shrinks any failing sequence to the shortest one that still breaks.

**INV-5 with NFR-2 — every world replays from base, branch and seed.** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s` from `seeds()`: two independently computed worlds from `(g, b, s)` serialize to identical bytes. Tests: `test_world_replays_from_base_branch_seed`, and `test_same_seed_same_world`, which must cover **both** streams — the same 2 000 versions and the same coin flips inside them.

**INV-multiverse.9 — the versions do not depend on the branch.** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s` from `seeds()`: the 2 000 versions drawn for a base world and for a branch world from one seed are element-for-element identical. Without this, every comparison is the user's edit plus a wash of sampling noise. Test: `test_versions_do_not_depend_on_the_branch`. Replay across both streams is `test_same_seed_same_world`, above, which compares two runs of the *same* inputs and so cannot see this. Checked from the other side in `backend/tests/unit/domain/test_diff.py` by `test_shifted_needs_agreement` ([`diff.md`](diff.md) owns that statement). *Catches:* deciding that something moved by comparing two bands — a pair of worlds whose bands overlap heavily but which move the same way in every version must come out `shifted`, not `unchanged`.

**INV-multiverse.10 — a supposition is true in every world until it is undermined.** For all maps `g` from `graphs()` and all `Do` edits from `interventions(g)` against which no live opposing arrow exists: the target comes out true in **every** one of the 16 000 worlds, and its state on every day is `supposed`. Not `.98`, not `.999`. Test: `test_supposition_is_true_in_every_world_until_undermined`. *Catches:* an implementation that models a supposition as a large finite baseline.

**INV-multiverse.11 — a retraction dates from the cause, not from the push.** For all maps `g` from `graphs()` and all branches from `branches(g)` that undermine a supposition: each `Retraction.at` equals the day the opposing arrow's **source** was settled, and never that day plus the arrow's `lag`. Test: `test_retraction_dates_from_the_cause_not_the_push`. *Catches:* tying "do I still take your word for this" to a delay parameter.

**INV-multiverse.12 — the band is not sampling noise.** For all maps `g` from `graphs()` rewritten so that every prior is a point — `lo = p = hi` — and all seeds `s`: every computed band comes out **essentially zero width**, within tolerance. Test: `test_band_is_not_sampling_noise`. *Catches:* reporting coin-flip spread as uncertainty, which is the single most likely way to get this chapter wrong.

**INV-multiverse.13 — the band agrees with an independent method.** Not a generated statement: it is pinned to the shipped Hormuz fixture at the fixed seed. The sampled band agrees with the analytic first-order (delta-method) band to two significant figures — measured, on B in the base world on its own resolve-by day: `.2495–.5451` sampled against `.2459–.5455` analytic. Two independent methods, one answer; it is what keeps the delta method useful after it was rejected as the engine. Test: `test_range_matches_analytic_first_order_on_fixture`. *Catches:* a band that is the right shape and the wrong size.

**INV-multiverse.14 — the domino stays fallen and the apple falls.** For all maps `g` from `graphs()` containing a `trigger` arrow whose source is later reset: the target's series after the reset is byte-identical to the series in which the source was never reset. For all maps containing a `sustain` arrow: on every day its source is not true, its term is exactly zero. Tests: `test_trigger_persists_after_parent_reset`, `test_sustain_retracts_when_parent_removed`.

**INV-multiverse.15 — propagation is idempotent and order-independent.** For all maps `g` from `graphs()`, all assignment lists and all seeds `s`: propagating a second time over the same inputs gives a byte-identical world; and shuffling the ties in the causes-before-effects ordering — the claims no arrow orders relative to one another — gives a byte-identical world. Tests: `test_propagation_idempotent`, `test_propagation_order_independent`.

**INV-multiverse.16 — a starved observation warns, and says the range is unreliable.** For all maps `g` from `graphs()` and all `Observe` edits from `interventions(g)` under which fewer than two per cent of worlds survive: the world carries a warning whose sentence says the **range** is unreliable, not merely the point. Test: `test_observe_warns_below_two_percent_survival`.

**INV-multiverse.17 — the Hormuz map reads the way the story reads.** Not a generated statement: it is pinned to the shipped fixture at the fixed seed `20261001`, four assertions, each one a sentence a person can check. Test: `test_hormuz_strike_branch_reads_the_way_the_story_reads`, in `backend/tests/unit/fixtures/test_hormuz_golden.py`.

| # | Assertion |
|---|---|
| 1 | **The strike lowers Brent-below-$68.** `B`'s likelihood on its resolve-by day is lower in the strike branch than in the base world |
| 2 | **The strike keeps the war-risk premium up.** `C` is the claim *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%"* and `S → C` is `−2.0`, so the strike makes `C` **less** likely. The roadmap's shorthand "raises the premium claim" means the premium stays high, which is `C` going **down**. Read the wording before writing the assertion |
| 3 | **The strait's standing is withdrawn, and the push lands three days later.** `H`'s state is `supposed` on day 0, `withdrawn` on days 1 to 3 with a series reading about `.36` — H's own prior, `.35`, read back — and `pushed` from day 4 with a series below `.10`. The world carries one `Retraction` for `H` with `at` = 2026-10-02, `by_link` = `S->H`, `by_claim` = `S` |
| 4 | **What already fell stays fallen.** `B`'s series **rises** between day 1 and day 2 — the strike has already hit it, and then `H → B`'s trigger arrives on its two-day lag and pushes back the other way. A world in which `B` only ever falls has lost the domino |

Directions and orderings, never values: research report 02 §3 reports `P(M1)` going from about `.61` to about `.18` and `P(M2)` from about `.54` to about `.09`; the engine reports `.46 → .41` and `.43 → .36`. The directions match and the sizes do not, which is what "illustrative" meant — and it is why the assertions are written the way they are, so tuning the fixture cannot break them. The same report writes `H → B` as `−1.6` because it was thinking about the oil *price*; the fixture writes `+1.6` because `B` is the *claim* "Brent settles below $68", and the sign is on the claim. The fixture is right.

---

## ANTI-PATTERNS

**1. Do not report the spread of the coin flips as the band.** *Because* it measures the machine rather than the map: run more worlds and the "uncertainty" shrinks, which means a number that moves when you buy computer time is being passed off as a statement about the world. **Do** run two loops, subtract the inner noise with the law of total variance, and take the percentiles across versions — and keep `test_band_is_not_sampling_noise`, which freezes every prior at a point and demands a zero-width band.

**2. Do not let the `params` stream see the branch.** *Because* the base world and the branch world then run on different underlying numbers, and every comparison becomes the user's edit plus a wash of elicitation noise, with no way to separate them. **Do** derive `params` from the seed alone, so version *k* of both worlds was built from the same numbers and the difference is the edit.

**3. Do not model a supposition as a big finite baseline.** *Because* ±4.0 is an arbitrary constant with no source; it contradicts the user in about two per cent of worlds; an opposing arrow of `−1.9` moves the claim from `.98` to `.89`, which is not a retraction; and it makes "suppose this is true" mean "assume ninety-eight per cent", which is not what the button says. **Do** make the claim true in every draw while the supposition holds, show a word where a number would go, and end it on the day the opposing cause becomes true.

**4. Do not fit `{p, lo, hi}` on the probability scale.** *Because* elicited ranges are lopsided there — over the seven base-map claims the fixture's are skewed 1.24 on probability and near-symmetric 0.94 on log-odds — so a symmetric fit has to clamp at 0 and 1 and silently stops honouring the three numbers the model actually stated. **Do** fit the two halves separately on the log-odds scale, which honours all three exactly and can never leave 0–1.

**5. Do not decide that something moved by comparing two bands.** *Because* the bands answer a different question. Under `do(H)` on the fixture, B's two bands overlap across about two fifths of their width — `.25–.55` against `.42–.73` — while 99.9% of versions agree on the direction; band overlap would report "no change" about the clearest change on the map. **Do** subtract version by version and read the paired difference; [`diff.md`](diff.md) states the rule and `test_shifted_needs_agreement` pins it.

**6. Do not reach for a module-level random generator, a global seed, or the clock.** *Because* a world would then depend on how many other worlds had been computed before it, which quietly destroys replay (NFR-2: the same map, branch and seed give byte-identical worlds) and with it every reproducible screenshot. **Do** pass the seed as an argument, build every `numpy.random.Generator` from it, and let `test_world_replays_from_base_branch_seed` fail loudly if anyone slips.

**7. Do not type a computed number by hand.** *Because* a hand-written `beliefs.model` cannot say why it is what it is, which is the traceability veto exactly. **Do** set the fixture's `beliefs.model` equal to its `prior` — the truthful statement "nothing has been computed yet" — and serve the engine's world beside the map. Every number in a demo comes from the engine or from a recording of the engine.

**8. Do not put "how often these two show up together" on a wire.** *Because* that is a correlation, and a wire claims a mechanism; the two disagree whenever a third thing caused both, and the reader has no way to tell. **Do** compute `conditionals` with the arrow's source **supposed** true — a `do` — exactly as [`../graph/link.md`](../graph/link.md)'s anti-pattern 3 requires.

**9. Do not add `strength_lo` and `strength_hi` to make arrows uncertain.** *Because* every arrow in today's fixture is hand-written `argued` or `asserted`, so spreading them now would widen everything by the same amount and teach nobody anything — and a second elicited pair per arrow is exactly the budget record 0005 refused. **Do** keep strengths fixed in 03a and derive the spread from `provenance` in stack 04, where "how well-backed" becomes "how wide" at no extra elicitation cost.

---

## Open questions

Raised 2026-09-17, and all four **decided the same day**. Each answer now lives in Behaviour, where a reader meets it in the arithmetic rather than in a footnote; the questions are kept here, closed, so the chapter shows its working.

1. **An `impulse` that names no `half_life`.** [`../graph/link.md`](../graph/link.md)'s open question 4 settled one direction — a half-life on a `step` or a `ramp` is a violation — and left this one open: what should `propagate` do with a spike that has no decay to evaluate?
   **Decided 2026-09-17: nothing, because it never sees one.** It is a map fault, `impulse_without_half_life`, checked by `validate` ([`../graph/validity.md`](../graph/validity.md) rule 13). The shape and its parameters must agree, checked both ways. Reject, never repair: reading it as no decay would silently turn the arrow into a `step`, and any other default would be a number we invented and attributed to the model. See B2.

2. **Which arrow the badge names when two undermine a supposition on the same day.**
   **Decided 2026-09-17:** the arrow whose introducing edit came first in the branch; within one edit, its position in `Insert.links`; for a base-map arrow, its position in `graph.links`. Three orderings that already exist and are already load-bearing, so replay holds. See B4.

3. **A `ramp` with `lag = 0.0`.**
   **Decided 2026-09-17: nothing to decide.** The `u ≥ L` branch is tested first, so the climbing branch is never reached and a zero-lag ramp behaves as a `step`. A consequence of how the shape is written, not a special case, and no division by zero. See B2.

4. **A second `do` on a claim whose supposition has already been withdrawn.**
   **Decided 2026-09-17: allowed.** The second supposition holds from its own date until undermined again; the world carries one `Retraction` per ending, so a claim may have several; the series reads `supposed · withdrawn · pushed · supposed` and the tile shows the last pair. It falls out of "a later assignment overrides an earlier one" and needed nothing new. See B4.

Nothing is open in this chapter today.
