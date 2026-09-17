# Diff — what moved between two worlds

## Purpose

The user supposes the strait reopens, then adds a strike the next day, and asks the only question that matters: *what changed?* Before this chapter the answer is two full maps side by side and a reader squinting at fourteen numbers. After it, the answer is a short, ordered list — this claim went from `.44` to `.21`, this one is out of the picture, these three did not move — with the biggest, best-backed change at the top and a single sentence anybody can read aloud. A **diff** is that list. It is not an approximation and it is not a guess: because both worlds are built from the same untouched base map and the same random seed, every difference in it can be traced to an edit the user made.

This chapter owns the four per-claim states, how a change is decided, how the changes are ranked and dated, the one-line summary, the one-at-a-time sensitivity sweep, and the three routes that serve them. It rests on decision record **0014 (accepted 2026-09-17)** — *a supposition ends when something pushes back; a range says how sure we are of the number, not how the dice fall* — which settles how a change is ranked and which day a number is read on. A **world**, a **version of the map**, the two seed streams and the **range** on a computed likelihood are defined in [`propagation.md`](propagation.md); this chapter uses those words and does not redefine them.

---

## Data model

**A difference is read off two worlds, never off two maps.** `diff` takes two finished worlds — each one a base map with a branch folded onto it and the likelihoods worked through — and compares them claim by claim. Both must carry the same `base_id`, the same `seed`, the same `versions` count and the same `worlds` count. Anything else is refused, because the comparison below is only meaningful when the two worlds were built from the same raw material (see B1).

```python
def diff(world_a: World, world_b: World) -> Diff | list[Violation]
```

`World`, `Belief`, `PropositionId`, `LinkId` and `BranchId` are defined in [`propagation.md`](propagation.md), [`../graph/belief.md`](../graph/belief.md) and [`../graph/proposition.md`](../graph/proposition.md). `Violation` — a stable code, the identifier of the thing at fault, and one plain sentence for the reader — is defined in [`../graph/validity.md`](../graph/validity.md). Every model below is frozen: once built it cannot be altered, so a stored difference is a record rather than a working buffer.

### Per claim: one of four states

```python
ClaimState = Literal["unchanged", "shifted", "added", "killed"]
# unchanged — present in both worlds, and it fails either half of the shifted test
# shifted   — present in both, moved by 0.005 or more, and moved the same way in
#             at least 90% of the versions of the map
# added     — present in world B and not in world A
# killed    — present in both, and assigned false in world B. Never "its number got
#             small", and never "it lost its path from the hypothesis" (see B2)


class ClaimDiff(BaseModel):          # proposed here — the plan names the four states, not this shape
    target: PropositionId            # the claim
    state: ClaimState
    before: float | None             # world A's likelihood on this claim's own resolve-by day; None when added
    after: float | None              # world B's likelihood on the same day
    delta: float | None              # signed, after minus before; None when added
    agreement: float | None          # share of versions that moved the same way;
                                     # `None` only when the claim is `added`
```

`agreement` is carried on **every** claim present in both worlds, not only the shifted ones, so a reader — or a test — can check the rule that decided a claim's state without recomputing anything. It is `None` only for an `added` claim, which has no world A to be compared against.

`before` and `after` are read on **the claim's own resolve-by day** — the day the claim is judged, which every claim has (INV-1, the product rule that a claim without resolution criteria, a named judge and a date is not a claim). That is the number the claim's tile shows, so it is the number its state has to be about. When a claim is still `supposed` on its own resolve-by day, `before` and `after` carry the stored `1.0` (or `0.0` for a claim supposed false) so that `delta` stays ordinary arithmetic — but any surface showing that row reads `states` first and prints the word, *Supposed · date*, never `1.0`, because no surface except a path product may print that number ([`propagation.md`](propagation.md)).

### The ranked change list

```python
class DeltaRow(BaseModel):
    target: PropositionId
    before: float          # at at_day
    after: float           # at at_day
    peak_delta: float      # signed; the largest divergence over the window
    at_day: date           # the day that divergence is largest
    range_width: float     # a column in the delta rail; never multiplied into rank
    agreement: float       # share of versions that moved the same way; a column, never a factor
    rank: float            # |peak_delta| × weakest provenance weight on the path. Two factors
```

One row per **terminal** — a claim of kind `market` (it names an instrument) or `not_tradeable` (it names the reason there is nothing to trade) — that came out `shifted`. Ordered by `rank`, largest first. The **delta rail** is the interface's name for this list beside a diff.

`range_width` is **the width of world B's own 10-to-90 band on that claim at `at_day`** — `hi` minus `lo`, the same quantity the claim's tile shows (Kent, 2026-09-17). Taking it from the tile rather than from the difference is what keeps the rail and the tile from ever disagreeing about how firm a number is.

### The whole difference

```python
class Diff(BaseModel):                              # proposed here — the plan names DeltaRow, not this wrapper
    base_id: str                                    # the one base map both worlds were built from
    branch_a: BranchId | None                       # None means the base world, the empty branch
    branch_b: BranchId | None
    seed: int                                       # the one seed both worlds were built from
    versions: int                                   # the outer loop both worlds ran
    worlds: int                                     # the inner loop both worlds ran
    claims: Mapping[PropositionId, ClaimDiff]       # every claim in either world, exactly once
    rows: tuple[DeltaRow, ...]                      # the terminals that shifted, ranked
    summary: str                                    # the fixed sentence of B6, filled in
    warnings: tuple[str, ...]                       # plain sentences, carried over from either world
```

### The sensitivity sweep

```python
class SensitivityRow(BaseModel):                    # proposed here — the plan names the function, not this shape
    flipped: PropositionId                          # the claim that was flipped
    to: bool                                        # the value it was flipped to: the opposite of how it more often comes out
    deltas: Mapping[PropositionId, float]           # signed change on each terminal
    versions: int                                   # the reduced outer loop this row was produced at: 250
    worlds: int                                     # the inner loop: 8


def sensitivity(world: World) -> tuple[SensitivityRow, ...]
```

### How well-backed an arrow is, as a number

Each arrow carries a `provenance` — a receipt our own pipeline writes, never something the model claims for itself (see [`../graph/link.md`](../graph/link.md)). The ranking turns that receipt into a weight:

| Provenance | Weight | What it means |
|---|---|---|
| `documented` | 1.0 | The retrieval step attached at least one real source |
| `historical` | 0.9 | The number came from a study of past cases |
| `market_implied` | 0.9 | The number was read off a live price |
| `argued` | 0.6 | A mechanism was stated and nothing was fetched to back it |
| `user` | 0.6 | A person typed it |
| `simulated` | 0.5 | A probe produced it |
| `asserted` | 0.3 | A story rather than a mechanism, and no sources |

Every arrow in the Hormuz example is `argued` (0.6) except `` `H->N1` ``, which is `asserted` (0.3) — so on that map the second factor is one of exactly two numbers, and the weak arrow is the one reaching the ending nobody can trade.

---

## Behaviour

Worked on the Strait of Hormuz map and its strike branch. The claims, quoted from the fixture: **H** *"The Strait of Hormuz reopens to unrestricted commercial transit."* (the hypothesis, prior `.35`, judged by 2026-11-01) · **C** *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%."* (prior `.30`, by 2026-10-31) · **B** *"Brent crude settles below $68 for five sessions."* (prior `.28`, by 2026-11-15) · **R** *"OPEC+ announces output restraint."* (prior `.18`, by 2026-11-30) · **M1** *"A Polymarket contract 'Brent below $70 on 2026-10-31' resolves YES."* (a terminal, by 2026-10-31) · **M2** *"The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days."* (a terminal, by 2026-11-15) · **N1** *"Omani-mediated United States-Iran talks resume publicly."* (a terminal nobody quotes, by 2026-11-30). The branch `br_hormuz_then_strike`, labelled **"Hormuz opens, then Iran is struck"**, adds **S** *"A confirmed military strike on Iranian territory."* with three arrows and supposes it true on 2026-10-02. Day zero is 2026-10-01.

Every likelihood written below is illustrative. The engine arrives with the code in this stack, the example map is a curated one whose inputs may be tuned, and its golden test asserts **directions and orderings, never values**. What this chapter settles is the arithmetic and the shape of the answer.

### B1 — Two worlds, one base, one seed

`diff` compares the world of branch A with the world of branch B. Both are built by folding a branch onto the *same* untouched base map and working the likelihoods through with the *same* seed. The versions stream — the one that picks which 2 000 versions of the map to try — never depends on the branch, so version 7 of world A and version 7 of world B were built from the same underlying numbers and differ only by the edit. That is what makes the paired comparison in B3 possible.

Two worlds that disagree on `base_id`, `seed`, `versions` or `worlds` are refused with a violation naming the mismatch. There is no repair: a difference computed across two seeds is the user's change plus a wash of sampling noise, and a number nobody can trace to an edit is exactly the state this product refuses to show.

For the Hormuz walkthrough, world A is the base world (the empty branch) and world B is `br_hormuz_then_strike`, three edits in order: suppose H true on the 1st, insert S with its three arrows, suppose S true on the 2nd.

### B2 — The four states, and exactly what puts a claim in each

The checks run in this order, and the first that matches wins.

1. **`added`** — the claim is in world B and not in world A. `S` is added: the base map has never heard of it.
2. **`killed`** — the claim is in both, and in world B it is **assigned false** by a `do` or an `observe`. That is the whole rule (Kent, 2026-09-17). A claim whose likelihood fell to `.02` is a claim that moved a long way; it is `shifted`, and calling it `killed` would tell the user their argument was cut when it was merely losing.
3. **`shifted`** — the claim is in both, it moved by 0.005 or more on its own resolve-by day, **and** it moved the same way in at least 90% of the versions of the map. Both halves, always. B3 says why.
4. **`unchanged`** — the claim is in both and fails either half.

A claim present in world A and missing from world B cannot happen: there is no delete operation, and "this is out of the picture" is expressed as `do(n, false)`, which forces the claim false ([`interventions.md`](interventions.md) anti-pattern 5).

**On the Hormuz branch.** `S` is `added`. `H`, `C`, `B`, `M1`, `M2` and `N1` are `shifted` — every one of them is downstream of H or of S. `R` is `unchanged`, and for a reason worth reading: R's only incoming arrow is `B → R`, the feedback arrow from the market back onto the world, and *the map the engine works through is the map with feedback arrows set aside* — [`interventions.md`](interventions.md)'s named rule, which every chapter cites rather than re-deciding, and which `test_a_feedback_arrow_never_carries_a_change` pins. So R reads its own prior in both worlds. Nothing on this branch is `killed`.

**`killed`, shown.** Add `Do(target="C", value=False)` to a branch and C is `killed` — forced false, its tile struck through, still on the map and still in the record.

**Why `killed` is not also "cut off from the hypothesis".** That second half was tried and dropped (Kent, 2026-09-17), and the fixture shows why. `Do(target="B", value=True)` cuts B's incoming arrows, which removes `H → B`, so no path of arrows runs from the hypothesis H to M1, M2 or R any more — and under the dropped rule all three would have read *killed* while B, supposed true, was pushing M1 and M2 harder than anything else on the map. Two unrelated facts were wearing one word. Losing the last path is a fact about the **path**, not about the claim's value, so it is reported where paths are reported: the Inspector's path bar says *"no path from the hypothesis reaches this claim any more"* in those words (`spec/workbench/inspector.md`).

### B3 — How `shifted` is decided: the paired difference, never band overlap

Subtract world A's version *k* from world B's version *k*, for all 2 000 versions. Because the versions stream does not depend on the branch, the elicitation noise cancels and what is left is the edit — this is *common random numbers*, the standard trick for comparing two runs of the same simulation. Two numbers come out of those 2 000 paired differences:

* **the move** — the average paired difference, which is what `delta` and `peak_delta` report;
* **agreement** — the share of versions whose paired difference has the same sign as that average. It is the vocabulary's word for a number the machine computes rather than one anything self-reports. Here it means the share of versions of the map that moved the same way; stack 04's run-to-run agreement across generations is the other sense, and the vocabulary asks us to say which.

A claim is `shifted` when the move is at least `0.005` in size **and** agreement is at least `90%`.

**On screen the rail heads this column *same direction*, and the range-width column beside it *how firm*** (Kent, 2026-09-17). The field names stay `agreement` and `range_width`; the headings say in the reader's words what each column answers, and keeping *agreement* off the screen here leaves the word free for stack 04's run-to-run number.

**Why never band overlap, measured on this fixture.** Supposing the strait opens, B's band in the base world and B's band in the branch world **overlap by a third**, and yet **100% of versions move the same way**: `+.10`, with a 10-to-90 band on the difference itself of `+.07` to `+.13`. Reading the overlap would report "no change" about the single clearest change on the map. The two bands overlap because each one is wide for its own reason — we are unsure what number to give you — while the *difference* between them is tight, because both were computed from the same numbers.

A second measured warning from the same fixture, so nobody builds a demo on it: supposing the strait opens **widens** B's band, `.292` to `.323`, because the curve that turns log-odds into a likelihood is steeper near `.45`. A supposition collapses its own target's band and does not reliably narrow anything downstream. The honest thing to show is the **share** of B's band that H's own range explains, which goes from 2.6% to 0% — that is FR-21's "where to spend modeling budget" number, carried on the world and first read on screen in stack 06.

### B4 — The ranked change list: two factors, and only two

```
rank = |peak_delta| × min(provenance weight of each arrow on the best-backed route
                          from a differing edit's subject to this terminal)
```

How big the move is, times what the weakest arrow behind it is worth. That is FR-16's "the size of the move × the weakest backing on the best-backed route", made arithmetic.

**`range_width` and `agreement` are columns and never factors.** They answer two different questions — *how unsure are we of this number* and *how sure are we of its direction* — and a trader weighs them separately from *how big is it*. Blend any of the three into one score and the reader can no longer tell which one is talking. Worse, multiplying width in would push down exactly the claims FR-21 floats: a wide band is the signal that says *go and research this*, and a ranking that buries wide claims gives the opposite advice.

**Which route the weakest arrow is read along** (Kent, 2026-09-17). Over every path from **any** differing edit's subject to the terminal — the subjects of the edits branch B has and branch A does not — take the one whose weakest arrow is strongest. That is the **widest bottleneck**: the route whose narrowest point is as wide as possible, the way a lorry driver picks the road with the highest low bridge rather than the shortest one. It is a ten-line variant of the usual shortest-path walk. Neither "shortest" nor "which subject" survives in the rule: a change that could have reached a terminal along a well-backed route is ranked by that route, whichever edit started it, because that route is the best case the reader is entitled to.

The route is read over **the same map the affected set is computed over** — *the map the engine works through is the map with feedback arrows set aside*, [`interventions.md`](interventions.md)'s named rule. So for five of the six operations the route simply follows the arrows, and for `observe`, the one edit that may move a claim *upstream* of its subject, the affected set already reaches upstream and so does the route. There is no second direction rule to remember and no exception to carve out.

**On the Hormuz branch.** World A is the base world, so all three edits count and the differing subjects are H (supposed) and S (inserted, then supposed). Every route from either of them to M1 or M2 ends in `B → M1` or `B → M2` and passes only through `argued` arrows, so the best-backed route's weakest arrow is worth `0.6`. Every route to N1 must end in `H → N1`, which is the only arrow into N1 and is `asserted`, so the bottleneck is `0.3` however well-backed the rest of the route is. If M2 and N1 had moved by the same amount, M2 would rank twice as high — which is the whole point: the arrow into N1 is a story about which way the causality runs, and the rail says so by putting it lower.

**The Inspector's path-product bar walks this same route** and names its steps. One path-choosing rule, used twice, so the bar and the rail can never point at two different chains through the same map. When two routes are equally well-backed the **shorter** one is taken, and if they are still level, the one whose first differing arrow comes earlier in the map's own list of arrows *(proposed here)* — the rank does not care, because tied routes give the same weight, but the bar names its steps, so the choice has to be the same every time. On the Hormuz map every arrow into M1 is `argued`, so `H → B → M1` wins over `H → C → B → M1` by being shorter.

### B5 — Which day a number is read on

Two surfaces want two different days, and saying so out loud is cheaper than a reader guessing.

| Surface | Day | Why |
|---|---|---|
| A tile's headline likelihood, and therefore a claim's state | The claim's **own resolve-by day** | Every claim has one (INV-1, the rule that a claim names its criteria, its judge and its date), and it is the day the claim is judged. The number on the tile is the number the tile's own date refers to |
| A delta rail row | The **day of largest divergence** between the two worlds | A change that shows up for a fortnight and then unwinds is the thing a trader acts on. The row carries `at_day` and `peak_delta`, and names the date on screen |

**Why the second row is not pedantry**, measured on the fixture as it stands. A claim's clock starts on the day it is *settled* — for B that is day 2, the earliest day a live arrow reaches it, through `H → B`'s two-day lag ([`propagation.md`](propagation.md) B1) — and a spike is measured in elapsed days from there. So `H → B` has decayed to 0.37 of full size by day 45, which is B's resolve-by day, and `B → M1` to 0.26 of full size by day 30, which is M1's. Read a delta row on a distant resolve-by day and you show a quarter of the move and call it the answer. So M1's row on the strike branch names a date in early October, days after the strike, not 2026-10-31.

**A known wart, written down rather than hidden.** INV-8 — the rule that any displayed path shows the product of its likelihoods beside the headline, so a chain cannot be sold as more certain than the product of its steps — multiplies numbers each read on that claim's own resolve-by day, so it is a product across different days and not a joint likelihood at one instant. (`PRODUCT_REQUIREMENTS.md` §9 writes INV-8 as the product of the path's link probabilities; the number actually shown is the product of the claims' likelihoods on the path, each read on its own resolve-by day — decision record 0014.) It is still the most honest single number available for a chain, and the interface says this beside it rather than letting a reader assume otherwise.

### B6 — The one-line summary is a template, filled in

```
"<edit in the user's words> moves <terminal> from <before> to <after> by <date>
 and leaves <n> claims untouched."          (`claim`, singular, when <n> is 1)
```

`<terminal>` is the top row of the rail, `<before>`, `<after>` and `<date>` are that row's `before`, `after` and `at_day`, and `<n>` is the count of claims whose state is `unchanged`. Two significant figures, like every number this product shows.

**`<edit in the user's words>` is the branch's `label`** when branch B holds more than one edit, because the branch is the thing the user named and no single edit of three is the change they made. A branch of exactly one edit may use that edit's own words instead; the rule the test pins is that the slot is filled from the branch or the edit, never written fresh.

**The Hormuz instance.** Diffing the base world against `br_hormuz_then_strike`:

```
"Hormuz opens, then Iran is struck" moves a Polymarket contract "Brent below $70
on 2026-10-31" from .62 to .41 by 2026-10-09 and leaves 1 claim untouched.
```

The one untouched claim is R, for the reason in B2. The three numbers are illustrative — the sentence is what is settled here, not the values.

**When no ending shifted, there is a second fixed sentence:**

```
"<edit in the user's words> moves no ending and leaves <n> claims untouched."
```

It is used whenever the rail is empty — after a `believe`, because the user's own number is not pushed through the map in this version, or after a `retune` whose effect lands below the 0.005 floor. That is a real answer and not an error: *you changed something and nothing at the endings moved* is exactly what the user needs to hear, and an empty rail with no sentence beside it reads as a bug.

Nothing about either sentence is written by a language model, and the diff route needs no model key to answer. Free prose would be a fourth place for a number to come from, with nothing to trace it to.

### B7 — The sensitivity sweep

`sensitivity(world)` flips each claim in turn — a `do` to the opposite of whichever way it more often comes out in that world — re-propagates, and records the signed change on every terminal. One re-propagation per claim, so it runs at a **reduced budget of 250 versions × 8 worlds**, about 2 000 worlds per flip rather than the full 16 000, and **every row says which budget produced it** so nobody compares a swept number with a full-budget one without noticing.

**The rows come back unranked.** The ranking FR-19 asks for is *per terminal* and is applied by whoever reads them — stack 05's stop-loss, stack 06's "spend here" ranking — because the adverse direction depends on the terminal: the flip that hurts a long position helps a short one, and this function has no idea which trade is being run.

On the Hormuz map that is seven flips in the base world, eight on the strike branch. It answers FR-19 — one-at-a-time flips of every claim, with the change recorded on each terminal — and it feeds stack 05's derived stop-loss (the claim whose flip most damages a terminal *and* resolves before it *and* is publicly observable) and stack 06's ranking.

**No route reads it in this stack**, because nothing on screen shows it yet. It is written now because the engine it needs is written now, and bolting it on later would mean a second pass over the same arithmetic.

### B8 — The three routes

All under the `/api/` prefix, in `backend/src/katalyst/api/worlds.py`.

| Route | Body | Answer |
|---|---|---|
| `POST /api/worlds` | `{base_id, branch, seed, versions?, worlds?}` — `branch` is a whole branch sent by the browser, not a stored identifier; there is no store until stack 05 | One `World` |
| `POST /api/worlds/diff` | `{base_id, branch_a, branch_b, seed, versions?, worlds?}` | One `Diff` |
| `POST /api/worlds/conditional` | `{base_id, branch, seed, link_id}` | One `Belief`: the arrow's target with the arrow's source **supposed** true — a `do`, never an observation |

**Both worlds of a diff are built with the same versions stream**, from the one seed in the body. That is not an optimisation; it is what makes the paired difference in B3 mean anything, and it is why the route takes one seed rather than two.

`engine/worlds.py` sits between the routes and the pure core: it finds the base map among the stored examples, walks the parent chain of a branch and concatenates the edits, reads day zero from the stored example's own fixture date, mints identifiers and passes the seed through. It is the only place any of that happens, because the pure core reads no clock and knows no store.

**A rejected edit comes back as 422 with the list of violations** — each with its stable code, the identifier of the thing at fault and one plain sentence naming the claim or the arrow by its words. Never a 500, never a half-applied branch, never a silent repair. An edit naming a claim the map does not have is a sentence the user can act on, not a stack trace.

---

## INVARIANTS

Each statement is true for every input a named generator can produce, and each names the automated test that checks it. Generators live in `backend/tests/strategies.py`: `graphs()` yields random valid maps, `branches(graph)` yields branches of edits whose subjects exist in that map, and `seeds()` draws integer seeds. Tests live in `backend/tests/unit/domain/test_diff.py` unless noted; the route tests live in `backend/tests/api/test_worlds.py`. All of them land in **stack 03a**.

This chapter uses the local numbers `INV-multiverse.18` through `.30`. `.1`–`.5` belong to [`interventions.md`](interventions.md), `.6`–`.8` to [`branches-and-worlds.md`](branches-and-worlds.md), and `.9`–`.17` to [`propagation.md`](propagation.md).

**INV-multiverse.18 — a difference comes from two worlds, one base and one seed.** For all maps `g` from `graphs()`, all pairs of branches `a`, `b` from `branches(g)` and all seeds `s` from `seeds()`: `diff` over the two worlds built from `(g, a, s)` and `(g, b, s)` returns a `Diff`; over two worlds differing in `base_id`, `seed`, `versions` or `worlds` it returns a list of violations and never a number. Test: `test_diff_refuses_mismatched_worlds`.

**INV-multiverse.19 — every claim gets exactly one state.** For all such world pairs: every claim in either world appears exactly once in `claims`, its state is one of the four, and the four states partition the union of the two worlds' claims. Test: `test_every_claim_has_exactly_one_state`.

**INV-multiverse.20 — `shifted` is exactly the two halves.** For all such world pairs and all claims present in both and not `killed`: the state is `shifted` if and only if `delta` is at least `0.005` in size **and** `agreement` is at least `0.90`. Both numbers are carried on every such claim, so the rule can be read straight off the `Diff`. A pair whose bands overlap heavily but which moves the same way in every version comes out `shifted`; a pair that moved far but inconsistently in direction does not. Test: `test_shifted_needs_agreement`.

**INV-multiverse.21 — `killed` means forced false.** For all such world pairs: a claim's state is `killed` if and only if world B assigns it false, by a `do` or an `observe`. So, for any threshold, a claim whose `after` falls below it is never `killed` unless it was assigned false; and a claim that lost its last path from the hypothesis but was not assigned false is not `killed` either — that fact belongs to the path, not to the state. Test: `test_killed_means_forced_false`.

**INV-multiverse.22 — the rank has two factors and no more.** For all such world pairs and all rows: `rank` equals the size of `peak_delta` times the weakest provenance weight on the **best-backed route** — over every path from any differing edit's subject to that row's claim, in the map with feedback arrows set aside, the route whose weakest arrow is strongest. No other route to that claim has a stronger weakest arrow. Rebuilding the same diff with every `range_width` and every `agreement` replaced by any other number leaves every `rank` and the whole ordering unchanged. Test: `test_rank_has_two_factors`.

**INV-multiverse.23 — the rail holds ranked terminals and nothing else.** For all such world pairs: `rows` contains exactly the claims of kind `market` or `not_tradeable` whose state is `shifted`, ordered by `rank` from largest to smallest. Test: `test_delta_rail_holds_ranked_terminals`.

**INV-multiverse.24 — a row is read on the day of largest divergence.** For all such world pairs and all rows: no day in the window has a divergence **larger in size** between the two worlds' series for that claim than `at_day` does; `peak_delta` is the signed divergence on that day, and `before` and `after` are the two worlds' likelihoods on that same day. `at_day` is always one of the days the series actually carries — which matters when a window longer than 180 days has been sampled down to 180 points, because the peak is then chosen among those points and no other. Test: `test_delta_row_reads_the_peak_day`.

**INV-multiverse.25 — locality shows up in the difference.** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s`: every claim outside the branch's affected set — the claims an edit is allowed to move, which INV-4, the product's locality rule, defines as those still connected to the edit's subject in the map the edit leaves behind, with feedback arrows set aside ([`interventions.md`](interventions.md)'s named rule) — comes out `unchanged`. The test computes the affected set itself from the shape of the map and never asks the engine what it touched. Test: `test_diff_states_respect_locality`.

**INV-multiverse.26 — a difference replays.** For all maps `g`, all branch pairs `a`, `b` and all seeds `s`: two independently computed diffs from `(g, a, b, s)` serialize to identical bytes (INV-5 and NFR-2, the rules that a world is replayable from its base map, its branch and its seed). Test: `test_diff_replays_from_base_branches_seed`.

**INV-multiverse.27 — the summary is one of two fixed sentences, filled in.** For all such world pairs: `summary` matches one of the two sentences in B6 exactly — the first when `rows` is not empty, the second when it is. Both take the branch's `label` (or, for a branch of one edit, that edit's words) and the count of `unchanged` claims, with *claim* written in the singular when that count is 1; the first also takes the top row's claim, `before`, `after` and `at_day`. Neither contains a number that is not already in the `Diff`. Test: `test_summary_matches_the_template`.

**INV-multiverse.28 — a sensitivity row names its budget.** For all maps `g`, branches `b` and seeds `s`: `sensitivity` returns one row per claim in the world, each carrying the budget it was produced at — `versions` 250 and `worlds` 8 — and each row's `deltas` covers every terminal on the map. Test: `test_sensitivity_rows_name_their_budget`.

**INV-multiverse.29 — a rejected edit is a 422 with violations.** For all maps `g` and all branches drawn from `branches(g2)` for an independently drawn map `g2`, so that subjects usually do not match: `POST /api/worlds` and `POST /api/worlds/diff` answer either with a body or with status 422 carrying the list of violations, each with its code, its subject and its plain sentence. Never a 500, never a silently repaired branch. Test: `test_worlds_routes_reject_with_422`, in `backend/tests/api/test_worlds.py`.

**INV-multiverse.30 — the diff route builds both worlds from one versions stream.** For all maps `g`, branch pairs and seeds: the `Diff` returned by `POST /api/worlds/diff` is byte-identical to the one `diff` gives for the two worlds `POST /api/worlds` returns for the same base, branches and seed. Test: `test_diff_route_matches_two_world_calls`, in `backend/tests/api/test_worlds.py`.

---

## ANTI-PATTERNS

**1. Do not decide `shifted` by whether the two ranges overlap.** *Because* each range says how sure we are of that world's own number, and two wide ranges can overlap while the difference between them is tight and one-directional — measured on this fixture, B's two ranges overlap by a third while 100% of versions move the same way. Overlap would report no change about the clearest change on the map. **Do** subtract version by version and read the move and the agreement off the paired differences.

**2. Do not fold range width or agreement into the rank.** *Because* "this moved a lot", "we are unsure how much" and "we are sure which way" are three separate facts a trader weighs separately, and one blended score hides which is talking; multiplying width in would also sink exactly the wide claims FR-21 is trying to float as the ones worth researching. **Do** rank on two factors — the size of the move times the weakest backing on the path — and show width and agreement as their own columns.

**3. Do not call a small number `killed`, and do not call a lost path `killed` either.** *Because* `killed` means one thing — the claim was forced false — and stretching it to cover "the likelihood got low" tells the user their argument was severed when it is merely losing, while stretching it to cover "no path reaches this from the hypothesis" puts one word on two unrelated facts: on the fixture a claim can lose its last path and still be the biggest mover on the map. **Do** report a large move as `shifted` with its before and after, reserve `killed` for an assignment to false, and let the Inspector's path bar say *"no path from the hypothesis reaches this claim any more"* where that is what happened.

**4. Do not infer a difference by matching two maps.** *Because* a difference reconstructed after the fact cannot tell "the user supposed this" from "the model happened to number it differently this run", cannot recover the order the edits were made in, and turns a free, exact answer into a guess — the same reason [`branches-and-worlds.md`](branches-and-worlds.md) refuses to derive a branch by diffing two maps. **Do** build both worlds from one base map, one seed and two branches, and read the difference off the two results.

**5. Do not write the summary as free prose.** *Because* a sentence a model wrote is a fourth place a number can come from, with nothing to trace it to, and it will eventually disagree with the rail sitting beside it. **Do** fill in the fixed template from fields that are already in the `Diff`, so the sentence and the list cannot drift apart and neither needs a model key.

**6. Do not read a delta row on the claim's distant resolve-by day.** *Because* pushes fade — on this fixture `H → B` is at 0.37 of full size by B's resolve-by day and `B → M1` at 0.26 by M1's — so a row read there shows a quarter of the move and calls it the answer. **Do** read the row at the day of largest divergence, carry that day as `at_day`, and name it on screen.

**7. Do not build the two worlds of a difference from different seeds, or different loop sizes.** *Because* the whole comparison rests on version *k* of both worlds having been built from the same numbers; break that and every difference is the user's edit plus a wash of sampling noise, which is unreadable and untraceable. **Do** take one seed for the pair, refuse two worlds that disagree about it, and keep the versions stream free of any dependence on the branch.

---

## Open questions

Raised 2026-09-17. The first four were settled the same day and their answers are recorded in place below. The last two stay open and name who owns them.

1. **Which subject the path starts from, when a branch holds several edits.** The ranking was defined from "the edit's subject", and the showcase branch has three edits. The draft proposed the nearest subject.
   **Decided 2026-09-17:** the question disappears, because "shortest" and "which subject" both leave the rule. The rank reads the **best-backed route** — over every path from *any* differing edit's subject to the terminal, the one whose weakest arrow is strongest. See B4.

2. **Whether that path is read with or against the arrows.** `observe` is the one operation allowed to move a claim *upstream* of its subject, so a terminal could shift with no forward path from the subject to it, leaving the rank without its second factor.
   **Decided 2026-09-17:** the route is read over **the same map the affected set is computed over**, so the question answers itself — five operations follow the arrows, and `observe`'s affected set already reaches upstream, so its routes do too. Feedback arrows are set aside in both, by [`interventions.md`](interventions.md)'s named rule. See B4.

3. **What `range_width` measures.** The draft proposed the width of the paired difference's own band.
   **Decided 2026-09-17:** the width of **world B's own 10-to-90 band on that claim at `at_day`** — the same quantity the tile shows, so the rail and the tile cannot disagree. On screen the column is headed *how firm*. See the Data model and B3.

4. **A claim cut off from the hypothesis can still move.** Losing the last path from the hypothesis was going to be the second half of `killed`, and on the fixture such a claim can be the biggest mover on the map — the state would have said it left the argument while the rail showed it moving hardest.
   **Decided 2026-09-17:** it is not a diff state at all. `killed` means forced false, full stop. Losing the path is a fact about the **path**, reported by the Inspector's path bar — *"no path from the hypothesis reaches this claim any more"* (`spec/workbench/inspector.md`). See B2.

5. **Whether the rail should ever show an unshifted terminal.** Today a terminal that failed either half of the test is absent from `rows`, so a reader cannot tell "it did not move" from "it is not on this map". A greyed row saying *no change* may be better than silence; that is an interface question and `spec/workbench/` owns it.

6. **Diffing more than two worlds.** The interface shows up to four branches at once, and `diff` takes exactly two worlds. Three pairwise diffs against a common base world is the obvious reading and nothing here forbids it, but nothing names it either, and the delta rail's ranking across three lists is undesigned. `spec/workbench/` owns how four branches are compared on screen.
