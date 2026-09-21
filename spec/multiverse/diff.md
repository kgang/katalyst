# Diff — what moved between two worlds

## Purpose

The user supposes the strait reopens, then adds a strike the next day, and asks the only question that matters: *what changed?* Before this chapter the answer is two full maps side by side and a reader squinting at fourteen numbers. After it, the answer is a short, ordered list — the Brent contract went from `.50` to `.42`, this claim is out of the picture, this one did not move — with the biggest, best-backed change at the top and a single sentence anybody can read aloud. A **diff** is that list. It is not an approximation and it is not a guess: because both worlds are built from the same untouched base map and the same random seed, every difference in it can be traced to an edit the user made.

This chapter owns the four per-claim states, how a change is decided, how much each version of the map counts when a direction is read, how the changes are ranked and dated, the one-line summary, the one-at-a-time sensitivity sweep, and the three routes that serve them. It rests on decision record **0014 (accepted 2026-09-17, amended in place the same day)** — *a supposition ends when something pushes back; a range says how sure we are of the number, not how the dice fall* — which settles how a change is ranked, which day a number is read on, and that the direction is read with the same weights the number was read with. A **world**, a **version of the map**, the two seed streams and the **range** on a computed likelihood are defined in [`propagation.md`](propagation.md); this chapter uses those words and does not redefine them.

---

## Data model

**A difference is read off two worlds, never off two maps.** `diff` takes two finished worlds — each one a base map with a branch folded onto it and the likelihoods worked through — and compares them claim by claim. Both must carry the same `base_id`, the same `seed`, the same `versions` count and the same `worlds` count. Anything else is refused, because the comparison below is only meaningful when the two worlds were built from the same raw material (see B1).

```python
def diff(world_a: World, world_b: World, *, edit_in_words: str) -> Diff | list[Violation]
# edit_in_words fills the summary's first slot. A world carries its branch's identifier, not
# its label, and that slot is never written fresh — so the caller hands the words in (B6).
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
    agreement: float | None          # share of the versions that count which moved the same
                                     # way; None when the claim is `added`, and when no
                                     # version of the map counted in both numbers
    moved_only_by_reweighting: bool  # the move is nothing but the observation changing how
                                     # much each version counts. See B3
```

`agreement` is carried on **every** claim present in both worlds, not only the shifted ones, so a reader — or a test — can check the rule that decided a claim's state without recomputing anything. It is `None` in exactly two cases, and both mean *there is no direction to report*: an `added` claim, which has no world A to be compared against; and a claim no version of the map counted in **both** numbers, so the paired difference has no pair left (B3). Otherwise it is read with **the same weights the two numbers beside it were read with** — B3 states that rule once.

`moved_only_by_reweighting` is `true` **exactly when the claim is in both worlds, it moved by `0.005` or more, and every version that counts gives it the identical number in both worlds** — not one paired difference among them is anything but zero. Then nothing about the map's arithmetic moved the number; all that moved is how much each version counts. It is `false` everywhere else, including on an `added` claim. Only an observation can make it `true`: under every other edit both worlds count every version the same, so identical version-by-version answers give an identical number and the move is exactly nothing, which is below the floor. The Inspector turns it into one sentence, and there is no fifth state — B3.

`before` and `after` are read on **the claim's own resolve-by day** — the day the claim is judged, which every claim has (INV-1, the product rule that a claim without resolution criteria, a named judge and a date is not a claim). That is the number the claim's tile shows, so it is the number its state has to be about. When a claim is still `supposed` on its own resolve-by day, `before` and `after` carry the stored `1.0` (or `0.0` for a claim supposed false) so that `delta` stays ordinary arithmetic — but any surface showing that row reads `states` first and prints the word, *Supposed · date*, never `1.0`, because no surface except a path product may print that number ([`propagation.md`](propagation.md)).

### The ranked change list

```python
class DeltaRow(BaseModel):
    target: PropositionId
    before: float          # at at_day
    after: float           # at at_day
    peak_delta: float      # signed; the largest divergence over the days the series
                           # carries — not necessarily over every day (see B4's second wart)
    at_day: date           # the day that divergence is largest, among those days
    range_width: float     # a column in the delta rail; never multiplied into rank
    agreement: float       # share of the versions that count which moved the same way;
                           # a column, never a factor
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

Worked on the Strait of Hormuz map and its strike branch. The claims, quoted from the fixture: **H** *"The Strait of Hormuz reopens to unrestricted commercial transit."* (the hypothesis, prior `.35`, judged by 2026-11-01) · **C** *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%."* (prior `.30`, by 2026-10-31) · **B** *"Brent crude settles below $68 for five sessions."* (prior `.28`, by 2026-10-15) · **R** *"OPEC+ announces output restraint."* (prior `.18`, by 2026-11-30) · **M1** *"A Polymarket contract 'Brent below $70 on 2026-10-31' resolves YES."* (a terminal, by 2026-10-31) · **M2** *"The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days."* (a terminal, by 2026-11-15) · **N1** *"Omani-mediated United States-Iran talks resume publicly."* (a terminal nobody quotes, by 2026-11-30). The branch `br_hormuz_then_strike`, labelled **"Hormuz opens, then Iran is struck"**, adds **S** *"A confirmed military strike on Iranian territory."* with three arrows and supposes it true on 2026-10-02. Day zero is 2026-10-01.

**Every number below is the engine's own**, measured on the shipped fixture at seed `20261001` and the full budget of 2 000 versions × 8 worlds. None of them is typed by hand. The example map is a curated one whose illustrative inputs may be tuned — B's resolve-by day and one half-life were, in this stack — so the golden test asserts **directions and orderings, never values**, and re-running the engine is what keeps this page honest rather than re-reading it.

### B1 — Two worlds, one base, one seed

`diff` compares the world of branch A with the world of branch B. Both are built by folding a branch onto the *same* untouched base map and working the likelihoods through with the *same* seed. The versions stream — the one that picks which 2 000 versions of the map to try — never depends on the branch, so version 7 of world A and version 7 of world B were built from the same underlying numbers and differ only by the edit. That is what makes the paired comparison in B3 possible.

Two worlds that disagree on `base_id`, `seed`, `versions` or `worlds` are refused with a violation naming the mismatch, under its own code, `worlds_not_comparable` — nothing here is anybody's edit, so it borrows none of the four codes a refused edit carries. There is no repair: a difference computed across two seeds is the user's change plus a wash of sampling noise, and a number nobody can trace to an edit is exactly the state this product refuses to show.

For the Hormuz walkthrough, world A is the base world (the empty branch) and world B is `br_hormuz_then_strike`, three edits in order: suppose H true on the 1st, insert S with its three arrows, suppose S true on the 2nd.

### B2 — The four states, and exactly what puts a claim in each

The checks run in this order, and the first that matches wins.

1. **`added`** — the claim is in world B and not in world A. `S` is added: the base map has never heard of it.
2. **`killed`** — the claim is in both, and in world B it is **assigned false** by a `do` or an `observe`. That is the whole rule (Kent, 2026-09-17). A claim whose likelihood fell to `.02` is a claim that moved a long way; it is `shifted`, and calling it `killed` would tell the user their argument was cut when it was merely losing.
3. **`shifted`** — the claim is in both, it moved by 0.005 or more on its own resolve-by day, **and** it moved the same way in at least 90% of the versions of the map. Both halves, always. B3 says why.
4. **`unchanged`** — the claim is in both and fails either half.

A claim present in world A and missing from world B cannot happen: there is no delete operation, and "this is out of the picture" is expressed as `do(n, false)`, which forces the claim false ([`interventions.md`](interventions.md) anti-pattern 5).

**On the Hormuz branch.** `S` is `added`. Six claims are `shifted`, each read on its own resolve-by day, base world to strike world: `H` `.36` → `.08`, `C` `.40` → `.07`, `B` `.40` → `.30`, `M1` `.46` → `.41`, `M2` `.43` → `.36`, and `N1` `.28` → `.37`. Every one of those moves clears the 0.005 floor with room to spare, and every one clears the 90% same-direction bar — which is what the golden test pins, rather than a particular share. `N1` going **up** is not a slip: `H → N1` is a trigger, H was true on day 0 in every world, so that push fired everywhere and stays fired after the strike withdraws H.

`R` is `unchanged` — `.19 (.08–.32)` in both worlds, byte for byte — and for a reason worth reading: R's only incoming arrow is `B → R`, the feedback arrow from the market back onto the world, and *the map the engine works through is the map with feedback arrows set aside* — [`interventions.md`](interventions.md)'s named rule, which every chapter cites rather than re-deciding, and which `test_a_feedback_arrow_never_carries_a_change` pins. So R reads its own prior in both worlds. Nothing on this branch is `killed`.

**`killed`, shown.** Add `Do(target="C", value=False)` to a branch and C is `killed` — forced false, its tile struck through, still on the map and still in the record.

**Why `killed` is not also "cut off from the hypothesis".** That second half was tried and dropped (Kent, 2026-09-17), and the fixture shows why. `Do(target="B", value=True)` cuts B's incoming arrows, which removes `H → B`, so no path of arrows runs from the hypothesis H to M1, M2 or R any more — and under the dropped rule all three would have read *killed* while B, supposed true, was pushing M1 and M2 harder than anything else on the map. Two unrelated facts were wearing one word. Losing the last path is a fact about the **path**, not about the claim's value, so it is reported where paths are reported: the Inspector's path bar says *"no path from the hypothesis reaches this claim any more"* in those words (`spec/workbench/inspector.md`).

### B3 — How `shifted` is decided: the paired difference, never band overlap

Subtract world A's version *k* from world B's version *k*, for all 2 000 versions. Because the versions stream does not depend on the branch, the elicitation noise cancels and what is left is the edit — this is *common random numbers*, the standard trick for comparing two runs of the same simulation. Two numbers come out of those 2 000 paired differences:

* **the move** — the average paired difference, which is what `delta` and `peak_delta` report;
* **agreement** — the share of versions whose paired difference has the same sign as that average, **each version counted by as much as it counted for the two numbers** (the rule is stated once just below). It is the vocabulary's word for a number the machine computes rather than one anything self-reports. Here it means the share of versions of the map that moved the same way; a run-to-run agreement across independent generations would be the other sense — decision record 0015 says stack 04 builds none — and the vocabulary asks us to say which.

A claim is `shifted` when the move is at least `0.005` in size **and** agreement is at least `90%`.

#### The one rule: the direction is read with the same weights the number was read with

*(Kent, 2026-09-17 — G2. This closes open question 7, below.)*

A world does not always count every version equally. When something was **observed**, the worlds it did not happen in are thrown away, and each version then counts by **the share of its worlds that survived** — but a claim is weighted only by the observations that are evidence about *that claim*, each with its own surviving worlds, never by one pooled mask over all of them ([`propagation.md`](propagation.md) B6). Every claim no observation is evidence about, and every claim under every other edit, is read with each version counting the same.

The direction is counted the same way as the number, in one sentence: **a version counts for the move by as much as it counted for the two numbers — the smaller of the two weights it carried — so a version with no surviving world counts for nothing and does not vote.** A version can only speak about a difference as far as it counted in *both* numbers.

Three situations fall out of that one sentence, and not one of them is a special case:

| Which world observed something | How much version *k* counts for the direction |
|---|---|
| Only world B | the weight world B read that claim with |
| Both worlds | the smaller of the two weights |
| Neither — or the claim is one the observation is not evidence about | 1, the same as every other version |

**Each world's own weights are worked out first, one world at a time, and only then are the two put together.** That matters in the corner: a world in which nothing at all survived what was observed reads every version the same again — there is no surviving share left to weigh anything by, so counting evenly at least reports the map rather than dividing by nothing, and the world carries a loud warning saying the reader is looking at the map rather than at an answer. **That fallback belongs to that world**, because it is what that world's own number was read with. Take the smaller of the two worlds' weights *before* letting either fall back and the world that did keep survivors loses its weights too — the direction is then read with weights neither number was read with, which is the one sentence above broken in the one place nobody looks. It is reachable only branch against branch, because a base world on one side is unweighted anyway.

**And when no version counted in both numbers, there is no direction at all.** Two branches that each observed something can keep disjoint sets of versions alive: every version then counted in one of the two numbers or the other and in neither pair, so the paired difference this chapter is built on has no pair left. The share comes back as **nothing** — `agreement` is `None` — and the claim cannot be `shifted`, because nothing can be said about which way it moved. Counting every version equally instead would report a direction read off versions that contributed to neither reading, which is a number nobody computed. `before`, `after` and `delta` are still true statements about the two worlds' own numbers and are still carried; it is only the *direction* that is unreadable, and it says so rather than guessing.

**Why it had to change, measured.** Hormuz, seed `20261001`, the shipped 2 000 versions × 8 worlds, `observe(B, true)` — *Brent settled below $68*: **209 of the 2 000 versions have no surviving world at all**. Such a version reports nothing to the number and nothing to the band, because its weight is zero — and yet, counted as one vote each, all 209 voted **against** the direction. M1 and M2 both came out at `89.05%`, a hair under the 90% bar, so both read `unchanged`, the rail was empty, and **This happened** looked like a button that does nothing. Counted with the weights, both read `98.66%` (`99.44%` among the versions that survived, counted one vote each), both are `shifted`, and both are on the rail. Nothing else moved: under the five edits that are not an observation every weight is 1, so every number this chapter quotes for the strike branch and for `do(H)` is what it was, bit for bit. Worlds per version stays 8 and the 90% bar is untouched.

#### A claim moved only by reweighting

*(Kent, 2026-09-17 — G3.)*

A claim with **no causes** — the hypothesis, usually — is its own prior in every world of a version, so throwing worlds away cannot change what a version *says* about it. Inside every version that counts, the two worlds give it the identical number and the paired difference is exactly zero. Its same-direction share is therefore `0`, by construction and not by disagreement, and it can never be `shifted`. But its reported number does move, because the versions are now counted differently: on Hormuz, `observe(C, true)` — *the war-risk premium printed below 0.4%* — moves H from `.356` to `.365`, nearly twice the `0.005` floor.

**The four states stay as they are.** A fifth state would put two unrelated facts under one word, exactly as `killed` nearly did (B2). Instead the claim's row carries `moved_only_by_reweighting`, true under the rule in the Data model above, and the Inspector prints one sentence, word for word:

> **this claim moved only because the observation made some versions count more.**

That is the same shape as the path bar's sentence in B2: a fact about how the number was *read* lives in the Inspector, beside the number, and not in the claim's state. Such a claim never appears on the rail — the rail holds `shifted` endings, and a same-direction share of zero cannot clear the bar — so the field lives on `ClaimDiff` and not on `DeltaRow`.

**On screen the rail heads this column *same direction*, and the range-width column beside it *how firm*** (Kent, 2026-09-17). The field names stay `agreement` and `range_width`; the headings say in the reader's words what each column answers, and keeping *agreement* off the screen here leaves the word free for a run-to-run number, if one is ever earned (decision record 0015 says not in stack 04).

**Why never band overlap, measured on this fixture.** Supposing the strait opens and reading B on its own resolve-by day, 2026-10-15: the base world says `.40 (.25–.55)` and the supposed world says `.58 (.42–.73)`. Those two bands **overlap by 44% of the narrower one** — `.129` of `.296` — and yet **99.9% of versions move the same way**: `+.19`, with a 10-to-90 band on the difference itself of `+.10` to `+.27`. Reading the overlap would report "no change" about the single clearest change on the map. The two bands overlap because each one is wide for its own reason — we are unsure what number to give you — while the *difference* between them is tight, because both were computed from the same numbers.

A second measured warning from the same fixture, so nobody builds a demo on it: supposing the strait opens **widens** B's band, `.296` to `.318`, because the curve that turns log-odds into a likelihood is steeper near `.45`. A supposition collapses its own target's band and does not reliably narrow anything downstream. The honest thing to show is the **share** of B's band that H's own range explains, which goes from 6.1% to 0.4% — that is FR-21's "where to spend modeling budget" number, carried on the world and first read on screen in stack 06.

### B4 — The ranked change list: two factors, and only two

```
rank = |peak_delta| × min(provenance weight of each arrow on the best-backed route
                          from a differing edit's subject to this terminal)
```

How big the move is, times what the weakest arrow behind it is worth. That is FR-16's "the size of the move × the weakest backing on the best-backed route", made arithmetic.

**`range_width` and `agreement` are columns and never factors.** They answer two different questions — *how unsure are we of this number* and *how sure are we of its direction* — and a trader weighs them separately from *how big is it*. Blend any of the three into one score and the reader can no longer tell which one is talking. Worse, multiplying width in would push down exactly the claims FR-21 floats: a wide band is the signal that says *go and research this*, and a ranking that buries wide claims gives the opposite advice.

**Which route the weakest arrow is read along** (Kent, 2026-09-17). Over every path from **any** differing edit's subject to the terminal — the subjects of the edits branch B has and branch A does not — take the one whose weakest arrow is strongest. That is the **widest bottleneck**: the route whose narrowest point is as wide as possible, the way a lorry driver picks the road with the highest low bridge rather than the shortest one. It is a ten-line variant of the usual shortest-path walk. Neither "shortest" nor "which subject" survives in the rule: a change that could have reached a terminal along a well-backed route is ranked by that route, whichever edit started it, because that route is the best case the reader is entitled to.

The route is read over **the same map the affected set is computed over** — *the map the engine works through is the map with feedback arrows set aside*, [`interventions.md`](interventions.md)'s named rule. So for five of the six operations the route simply follows the arrows, and for `observe`, the one edit that may move a claim *upstream* of its subject, the affected set already reaches upstream and so does the route. There is no second direction rule to remember and no exception to carve out.

**On the Hormuz branch.** World A is the base world, so all three edits count and the differing subjects are H (supposed) and S (inserted, then supposed). Every route from either of them to M1 or M2 ends in `B → M1` or `B → M2` and passes only through `argued` arrows, so the best-backed route's weakest arrow is worth `0.6`. Every route to N1 must end in `H → N1`, which is the only arrow into N1 and is `asserted`, so the bottleneck is `0.3` however well-backed the rest of the route is.

The rail the engine actually produces, base world against the strike branch:

| | Ending | `at_day` | before → after | `peak_delta` | same direction | weakest weight | `rank` |
|---|---|---|---|---|---|---|---|
| 1 | M1, the Polymarket contract | day 3, 2026-10-04 | `.50` → `.42` | `−.079` | 96.5% | 0.6 | `.047` |
| 2 | M2, energy shares against the market | day 5, 2026-10-06 | `.43` → `.36` | `−.069` | 95.5% | 0.6 | `.041` |
| 3 | N1, talks resume | day 10, 2026-10-11 | `.28` → `.37` | `+.088` | 99.9% | 0.3 | `.026` |

**N1 has the biggest move on the map and ranks last**, and that is the second factor earning its place. `+.088` is larger than either market's move and the direction is all but unanimous, but the only way into N1 is `H → N1`, an arrow whose own rationale admits it cannot say which way the causality runs — quiet talks may be what reopened the lane rather than the other way about. The rail does not hide the move; it puts the two claims somebody can actually trade above it.

**And the rail under an observation**, base world against `observe(B, true)` — *Brent settled below $68* — which is what **This happened** produces on the same map. Both endings rise, because cheap Brent is evidence for both, and both peak within days of the news:

| | Ending | `at_day` | before → after | `peak_delta` | same direction | weakest weight | `rank` |
|---|---|---|---|---|---|---|---|
| 1 | M1, the Polymarket contract | day 1, 2026-10-02 | `.41` → `.62` | `+.21` | 100% | 0.6 | `.13` |
| 2 | M2, energy shares against the market | day 3, 2026-10-04 | `.38` → `.54` | `+.16` | 100% | 0.6 | `.095` |

N1 is reachable — the observation climbs from B to H and runs forward down `H → N1` — but it is absent, and for the ordinary reason: its move is `+.0004`, well under the `0.005` floor, and its same-direction share is `41%`, well under the bar. Read both rows above with every version counted as one vote instead and each reads `89.05%`, each falls under the bar, and this table is empty — which was open question 7, and B3's one rule is the answer.

**The Inspector's path-product bar walks this same route** and names its steps. One path-choosing rule, used twice, so the bar and the rail can never point at two different chains through the same map. When two routes are equally well-backed the **shorter** one is taken, and if they are still level, the one whose first differing arrow comes earlier in the map's own list of arrows *(proposed here)* — the rank does not care, because tied routes give the same weight, but the bar names its steps, so the choice has to be the same every time. On the Hormuz map every arrow into M1 is `argued`, so `H → B → M1` wins over `H → C → B → M1` by being shorter.

### B5 — Which day a number is read on

Two surfaces want two different days, and saying so out loud is cheaper than a reader guessing.

| Surface | Day | Why |
|---|---|---|
| A tile's headline likelihood, and therefore a claim's state | The claim's **own resolve-by day** | Every claim has one (INV-1, the rule that a claim names its criteria, its judge and its date), and it is the day the claim is judged. The number on the tile is the number the tile's own date refers to |
| A delta rail row | The **day of largest divergence** between the two worlds | A change that shows up for a fortnight and then unwinds is the thing a trader acts on. The row carries `at_day` and `peak_delta`, and names the date on screen |

**Why the second row is not pedantry**, measured on the fixture as it stands. The two worlds are furthest apart soon after the edit and then drift back together: all three endings peak within ten days of the strike. M1 is the clean case. Its row reads `−.079` on day 3, while the same claim's headline move on its own resolve-by day, 2026-10-31, is only `−.05` — read the row there and you show about two thirds of the move and call it the answer. So M1's row names 2026-10-04.

Fading pushes are part of why. A claim's clock starts on the day it is *settled* — for B that is day 2, the earliest day a live arrow reaches it, through `H → B`'s two-day lag ([`propagation.md`](propagation.md) B1) — and a spike is measured in elapsed days from there. B is now judged on day 14, close enough to the strike that `H → B` is still at 0.76 of full size when the tile reads; M1 is judged on day 30, by which time `B → M1` has fallen to 0.54. Tuning B's window down from forty-five days to fourteen is exactly what moved the tile's number back inside the interesting part of the story — and it changed nothing about how the rail picks its day.

**A second known wart: a row's day and its rank are read off the *drawn* series, and an unrelated edit can move them** *(added 2026-09-21)*. `at_day` is the largest divergence over the days **both worlds drew**, and past 180 days those days are spread evenly over the window ([`propagation.md`](propagation.md) B5). The window runs to the last day anything is judged, so an `insert` anywhere on the map — in a piece nothing connects to this claim — re-spaces them. Measured on a two-piece map: a push on `cause` moves its ending by `+.27` on **day 3** on a 31-day window, drawn day by day; add an unrelated claim judged a year out and the same push, on the same map with the same seed, reports `+.21` on **day 4**, because the 365-day window is drawn every other day and day 3 is not among them. `rank` is `|peak_delta|` times a weight, so the rank moves with it.

Nothing about the arithmetic moved: on every day the two windows share, every version's answer for that claim is identical bit for bit, and the tile's headline — read on the claim's own resolve-by day, which is **always** drawn — is the same number either way. What moved is which day the rail is looking at.

**And it cannot be fixed by choosing better days.** The divergence between two worlds is a continuous curve; its peak can fall anywhere between two drawn days, so finding it truly would mean working out **every** day of the window, which is the 5.9-gigabyte ceiling `propagation.md` B5 exists to avoid. Days could be *added* — every arrow's firing day, `settled(source) + lag`, is a property of the map and not of the window — which would catch the common case of a spike, and that is now safe in a way it once was not, since the arithmetic no longer depends on which days are worked out. It would still be a heuristic and not a guarantee, and it changes what a reader is sent, so it is recorded here as an option and not taken. **What the rail promises is the largest divergence among the days it drew, not the largest there is.**

**A known wart, written down rather than hidden.** INV-8 — the rule that any displayed path shows the product of its likelihoods beside the headline, so a chain cannot be sold as more certain than the product of its steps — multiplies numbers each read on that claim's own resolve-by day, so it is a product across different days and not a joint likelihood at one instant. (`PRODUCT_REQUIREMENTS.md` §9 writes INV-8 as the product of the path's link probabilities; the number actually shown is the product of the claims' likelihoods on the path, each read on its own resolve-by day — decision record 0014.) It is still the most honest single number available for a chain, and the interface says this beside it rather than letting a reader assume otherwise.

### B6 — The one-line summary is a template, filled in

```
"<edit in the user's words> moves <terminal> from <before> to <after> by <date>
 and leaves <n> claims untouched."          (`claim`, singular, when <n> is 1)
```

`<terminal>` is the top row of the rail, `<before>`, `<after>` and `<date>` are that row's `before`, `after` and `at_day`, and `<n>` is the count of claims whose state is `unchanged`. Two significant figures, like every number this product shows.

**The two numbers in this sentence are likelihoods, so they carry the guards** *(Kent, 2026-09-20 — G10)*. The rule in one sentence: **round to two significant figures, then use a guard word exactly when it is true of the rounded number** — `<.01` below a hundredth, `>.99` above ninety-nine hundredths, the figures themselves otherwise. `.010` and `.99` print, because neither is below or above its own guard; `.0099` and `.995` do not. The reason the boundary sits exactly there is that **the guard's words have to mean what they say**: `<.01` beside a likelihood of `.0035` is true, and beside `.010` it would not be. [`../graph/belief.md`](../graph/belief.md) B5 owns the rule and works it; [`../workbench/keyboard-and-access.md`](../workbench/keyboard-and-access.md) B6 owns the table of awkward cases; `_two_figures` in `domain/diff.py` writes this sentence and `toTwoFigures` in `BeliefChip.tsx` writes every chip, and the two are one rule that moves in one pull request.

**A move is not a likelihood and is never guarded.** It keeps two significant figures however small it is, because a move of `.0090` is a quantity the reader acts on while a likelihood of `.0090` is one this product declines to state that precisely. So every number in this chapter that is a *move* — the `0.005` floor, `peak_delta`, `+.0004` under an observation, `−.0002` on H, a `rank` — is written at two figures with no guard anywhere near it, and nothing writes a move through the likelihood formatter.

**`<edit in the user's words>` is the branch's `label`** when branch B holds more than one edit, because the branch is the thing the user named and no single edit of three is the change they made. A branch of exactly one edit may use that edit's own words instead; the rule the test pins is that the slot is filled from the branch or the edit, never written fresh.

**The Hormuz instance.** Diffing the base world against `br_hormuz_then_strike`:

```
"Hormuz opens, then Iran is struck" moves A Polymarket contract "Brent below $70 on
2026-10-31" resolves YES from .50 to .42 by 2026-10-04 and leaves 1 claim untouched.
```

`<terminal>` is filled with the claim's own words, exactly as the map stores them, minus the full stop the claim ends in — the sentence supplies its own. The one untouched claim is R, for the reason in B2. Every number here is the engine's at seed `20261001`; none was typed.

Note which numbers these are. `.50` and `.42` are M1 on **2026-10-04**, the day the two worlds are furthest apart, not on M1's own resolve-by day, where the move is the smaller `−.05`. The summary quotes the top row of the rail, so it quotes the rail's day, and it names that day rather than leaving the reader to assume otherwise (B5).

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

This chapter uses the local numbers `INV-multiverse.18` through `.33`. `.1`–`.5` belong to [`interventions.md`](interventions.md), `.6`–`.8` to [`branches-and-worlds.md`](branches-and-worlds.md), and `.9`–`.17` to [`propagation.md`](propagation.md).

**INV-multiverse.18 — a difference comes from two worlds, one base and one seed.** For all maps `g` from `graphs()`, all pairs of branches `a`, `b` from `branches(g)` and all seeds `s` from `seeds()`: `diff` over the two worlds built from `(g, a, s)` and `(g, b, s)` returns a `Diff`; over two worlds differing in `base_id`, `seed`, `versions` or `worlds` it returns a list of violations and never a number. Test: `test_diff_refuses_mismatched_worlds`.

**INV-multiverse.19 — every claim gets exactly one state.** For all such world pairs: every claim in either world appears exactly once in `claims`, its state is one of the four, and the four states partition the union of the two worlds' claims. Test: `test_every_claim_has_exactly_one_state`.

**INV-multiverse.20 — `shifted` is exactly the two halves.** For all such world pairs and all claims present in both and not `killed`: the state is `shifted` if and only if `agreement` is a number at all **and** `delta` is at least `0.005` in size **and** `agreement` is at least `0.90`. A claim whose direction could not be read is never `shifted`, because nothing can be said about which way it went. Both numbers are carried on every such claim, so the rule can be read straight off the `Diff`. A pair whose bands overlap heavily but which moves the same way in every version comes out `shifted`; a pair that moved far but inconsistently in direction does not. Test: `test_shifted_needs_agreement`.

**INV-multiverse.21 — `killed` means forced false.** For all such world pairs: a claim's state is `killed` if and only if world B assigns it false, by a `do` or an `observe`. So, for any threshold, a claim whose `after` falls below it is never `killed` unless it was assigned false; and a claim that lost its last path from the hypothesis but was not assigned false is not `killed` either — that fact belongs to the path, not to the state. Test: `test_killed_means_forced_false`.

**INV-multiverse.22 — the rank has two factors and no more.** For all such world pairs and all rows: `rank` equals the size of `peak_delta` times the weakest provenance weight on the **best-backed route** — over every path from any differing edit's subject to that row's claim, in the map with feedback arrows set aside, the route whose weakest arrow is strongest. No other route to that claim has a stronger weakest arrow. Rebuilding the same diff with every `range_width` and every `agreement` replaced by any other number leaves every `rank` and the whole ordering unchanged. Test: `test_rank_has_two_factors`.

**INV-multiverse.23 — the rail holds ranked terminals and nothing else.** For all such world pairs: `rows` contains exactly the claims of kind `market` or `not_tradeable` whose state is `shifted`, ordered by `rank` from largest to smallest. Test: `test_delta_rail_holds_ranked_terminals`.

**INV-multiverse.24 — a row is read on the day of largest divergence.** For all such world pairs and all rows: no day **the two worlds' series both carry** has a divergence larger in size between them for that claim than `at_day` does — which is what a row can honestly name, because the day is shown on screen and has to be a point of the line drawn beneath it; `peak_delta` is the signed divergence on that day, and `before` and `after` are the two worlds' likelihoods on that same day. `at_day` is always one of the days the series actually carries — which matters when a window longer than 180 days has had its **series** sampled down, because the peak is then chosen among those points and no other. The days a claim is *worked out* on are a different set and a larger one ([`propagation.md`](propagation.md) B5); a change list reads the days it can name. Test: `test_delta_row_reads_the_peak_day`.

**INV-multiverse.25 — locality shows up in the difference.** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s`: every claim outside the branch's affected set — the claims an edit is allowed to move, which INV-4, the product's locality rule, defines as those still connected to the edit's subject in the map the edit leaves behind, with feedback arrows set aside ([`interventions.md`](interventions.md)'s named rule) — comes out `unchanged`. The test computes the affected set itself from the shape of the map and never asks the engine what it touched. Test: `test_diff_states_respect_locality`.

**INV-multiverse.26 — a difference replays.** For all maps `g`, all branch pairs `a`, `b` and all seeds `s`: two independently computed diffs from `(g, a, b, s)` serialize to identical bytes (INV-5 and NFR-2, the rules that a world is replayable from its base map, its branch and its seed). Test: `test_diff_replays_from_base_branches_seed`.

**INV-multiverse.27 — the summary is one of two fixed sentences, filled in.** For all such world pairs: `summary` matches one of the two sentences in B6 exactly — the first when `rows` is not empty, the second when it is. Both take the branch's `label` (or, for a branch of one edit, that edit's words) and the count of `unchanged` claims, with *claim* written in the singular when that count is 1; the first also takes the top row's claim, `before`, `after` and `at_day`. Neither contains a number that is not already in the `Diff`. Test: `test_summary_matches_the_template`.

**INV-multiverse.28 — a sensitivity row names its budget.** For all maps `g`, branches `b` and seeds `s`: `sensitivity` returns one row per claim in the world, each carrying the budget it was produced at — `versions` 250 and `worlds` 8 — and each row's `deltas` covers every terminal on the map. Test: `test_sensitivity_rows_name_their_budget`.

**INV-multiverse.29 — a rejected edit is a 422 with violations.** For all maps `g` and all branches drawn from `branches(g2)` for an independently drawn map `g2`, so that subjects usually do not match: `POST /api/worlds` and `POST /api/worlds/diff` answer either with a body or with status 422 carrying the list of violations, each with its code, its subject and its plain sentence. Never a 500, never a silently repaired branch. Test: `test_worlds_routes_reject_with_422`, in `backend/tests/api/test_worlds.py`.

**INV-multiverse.30 — the diff route builds both worlds from one versions stream.** For all maps `g`, branch pairs and seeds: the `Diff` returned by `POST /api/worlds/diff` is byte-identical to the one `diff` gives for the two worlds `POST /api/worlds` returns for the same base, branches and seed. Test: `test_diff_route_matches_two_world_calls`, in `backend/tests/api/test_worlds.py`.

**INV-multiverse.31 — a version with no surviving world does not vote.** On the worked example under `observe(B, true)`: for every claim, the versions that count for the direction are exactly the versions that counted for both numbers, so every version an observation left with no surviving world counts zero. Make every one of those versions point the opposite way and not one `agreement` in the answer changes. The same-direction share is read with the weights each world read that claim's own number with — the test rebuilds each number from the version-by-version answers to find out which weights those were, rather than being told. Tests: `test_a_dead_version_does_not_vote`, `test_direction_is_read_with_the_numbers_own_weights`, and `test_an_observation_puts_a_row_on_the_rail`, which is the visible consequence: both tradeable endings come out `shifted`, both are on the rail, and the summary is the first sentence.

**INV-multiverse.32 — the weights change nothing under any edit that is not an observation.** For the strike branch and for `do(H, true)` on the worked example: no version is weighted, and the whole `Diff` computed as the code computes it serializes to exactly the bytes of the same `Diff` computed with every version forced to count the same. Nothing is compared against a number anybody typed — the difference is compared with itself. Test: `test_an_edit_that_is_not_an_observation_is_unchanged_by_the_weights`.

**INV-multiverse.32b — each world's weights fall back on their own, and a direction nobody can read says so.** Branch against branch, which is the only way to reach either corner. When one world kept no surviving world anywhere and the other kept some: the starved world counts every version the same — what its own number was read with — and the surviving world's weights are carried through rather than thrown away with it, so `agreement` is a number. When the two worlds kept **disjoint** sets of versions alive: no version counted in both numbers, `agreement` is `None` on every claim, nothing is `shifted`, the rail is empty and the summary is the second sentence. Tests: `test_a_world_that_kept_nothing_does_not_erase_the_other_worlds_weights` and `test_no_direction_at_all_when_no_version_counted_in_both_numbers`.

**INV-multiverse.33 — a claim moved only by reweighting says so, and keeps its state.** On the worked example under `observe(C, true)`: the hypothesis, which nothing on the map causes, carries `moved_only_by_reweighting` true, a `delta` at or past the `0.005` floor, an `agreement` of exactly zero, and the state it would have had anyway — `unchanged`, not a fifth word. It is the only claim on that map in that position, and under an edit that is not an observation no claim is. Test: `test_a_claim_moved_only_by_reweighting_says_so`.

---

## ANTI-PATTERNS

**1. Do not decide `shifted` by whether the two ranges overlap.** *Because* each range says how sure we are of that world's own number, and two wide ranges can overlap while the difference between them is tight and one-directional — measured on this fixture, B's two ranges overlap by 44% of the narrower one while 99.9% of versions move the same way. Overlap would report no change about the clearest change on the map. **Do** subtract version by version and read the move and the agreement off the paired differences.

**2. Do not fold range width or agreement into the rank.** *Because* "this moved a lot", "we are unsure how much" and "we are sure which way" are three separate facts a trader weighs separately, and one blended score hides which is talking; multiplying width in would also sink exactly the wide claims FR-21 is trying to float as the ones worth researching. **Do** rank on two factors — the size of the move times the weakest backing on the path — and show width and agreement as their own columns.

**3. Do not call a small number `killed`, and do not call a lost path `killed` either.** *Because* `killed` means one thing — the claim was forced false — and stretching it to cover "the likelihood got low" tells the user their argument was severed when it is merely losing, while stretching it to cover "no path reaches this from the hypothesis" puts one word on two unrelated facts: on the fixture a claim can lose its last path and still be the biggest mover on the map. **Do** report a large move as `shifted` with its before and after, reserve `killed` for an assignment to false, and let the Inspector's path bar say *"no path from the hypothesis reaches this claim any more"* where that is what happened.

**4. Do not infer a difference by matching two maps.** *Because* a difference reconstructed after the fact cannot tell "the user supposed this" from "the model happened to number it differently this run", cannot recover the order the edits were made in, and turns a free, exact answer into a guess — the same reason [`branches-and-worlds.md`](branches-and-worlds.md) refuses to derive a branch by diffing two maps. **Do** build both worlds from one base map, one seed and two branches, and read the difference off the two results.

**5. Do not write the summary as free prose.** *Because* a sentence a model wrote is a fourth place a number can come from, with nothing to trace it to, and it will eventually disagree with the rail sitting beside it. **Do** fill in the fixed template from fields that are already in the `Diff`, so the sentence and the list cannot drift apart and neither needs a model key.

**6. Do not read a delta row on the claim's distant resolve-by day.** *Because* two worlds are furthest apart soon after the edit and then drift back together — on this fixture all three endings peak within ten days of the strike, and M1's row reads `−.079` on day 3 against a headline move of `−.05` on its own resolve-by day three weeks later — so a row read there shows two thirds of the move and calls it the answer. **Do** read the row at the day of largest divergence, carry that day as `at_day`, and name it on screen.

**7. Do not count the versions one way for the number and another way for the direction.** *Because* a version an observation left with no surviving world reports nothing to the number and nothing to the band — its weight is zero — so letting it cast a full vote on the direction lets a version that contributed to neither answer argue about which way they moved. Measured: 209 of Hormuz's 2 000 versions die under `observe(B, true)`, and counted as one vote each they dragged both tradeable endings from `98.66%` to `89.05%`, under the 90% bar, and emptied the rail. **Do** count a version for the move by as much as it counted for the two numbers, which under every edit but an observation is 1 for every version and changes not a bit.

**8. Do not add a fifth state for a claim moved only by reweighting.** *Because* the four states answer one question — what happened to this claim — and a word that instead answers *how was this number read* puts two unrelated facts under one heading, which is the mistake `killed` nearly made (B2, anti-pattern 3). **Do** leave the state alone, carry `moved_only_by_reweighting` on the claim's row, and let the Inspector say *"this claim moved only because the observation made some versions count more"* beside the number.

**9. Do not build the two worlds of a difference from different seeds, or different loop sizes.** *Because* the whole comparison rests on version *k* of both worlds having been built from the same numbers; break that and every difference is the user's edit plus a wash of sampling noise, which is unreadable and untraceable. **Do** take one seed for the pair, refuse two worlds that disagree about it, and keep the versions stream free of any dependence on the branch.

---

## Open questions

Raised 2026-09-17. The first four were settled the same day and their answers are recorded in place below. The seventh was raised by the engine itself and was settled the same day; its answer is recorded in place too. The fifth and sixth stay open and name who owns them.

1. **Which subject the path starts from, when a branch holds several edits.** The ranking was defined from "the edit's subject", and the showcase branch has three edits. The draft proposed the nearest subject.
   **Decided 2026-09-17:** the question disappears, because "shortest" and "which subject" both leave the rule. The rank reads the **best-backed route** — over every path from *any* differing edit's subject to the terminal, the one whose weakest arrow is strongest. See B4.

2. **Whether that path is read with or against the arrows.** `observe` is the one operation allowed to move a claim *upstream* of its subject, so a terminal could shift with no forward path from the subject to it, leaving the rank without its second factor.
   **Decided 2026-09-17:** the route is read over **the same map the affected set is computed over**, so the question answers itself — five operations follow the arrows, and `observe`'s affected set already reaches upstream, so its routes do too. Feedback arrows are set aside in both, by [`interventions.md`](interventions.md)'s named rule. See B4.

3. **What `range_width` measures.** The draft proposed the width of the paired difference's own band.
   **Decided 2026-09-17:** the width of **world B's own 10-to-90 band on that claim at `at_day`** — the same quantity the tile shows, so the rail and the tile cannot disagree. On screen the column is headed *how firm*. See the Data model and B3.

4. **A claim cut off from the hypothesis can still move.** Losing the last path from the hypothesis was going to be the second half of `killed`, and on the fixture such a claim can be the biggest mover on the map — the state would have said it left the argument while the rail showed it moving hardest.
   **Decided 2026-09-17:** it is not a diff state at all. `killed` means forced false, full stop. Losing the path is a fact about the **path**, reported by the Inspector's path bar — *"no path from the hypothesis reaches this claim any more"* (`spec/workbench/inspector.md`). See B2.

5. **Whether the rail should ever show an unshifted terminal.**
   **Decided 2026-09-17 (stack 04a), and nothing changes on this side.** `rows` still holds only the terminals that came out `shifted`; a terminal that did not move is not missing, it is in `claims` with the state `unchanged`, and the delta rail draws it as a greyed row reading *no change* rather than leaving it out (`spec/workbench/diff-view.md` B5). The interface reads that state rather than re-running the shifted test on two numbers, so there is only ever one answer to *did this move*.

6. **Diffing more than two worlds.** The interface shows up to four branches at once, and `diff` takes exactly two worlds. Three pairwise diffs against a common base world is the obvious reading and nothing here forbids it, but nothing names it either, and the delta rail's ranking across three lists is undesigned. `spec/workbench/` owns how four branches are compared on screen.

7. **An observation rarely puts a row on the rail at eight worlds per version.** *Raised 2026-09-17, when the engine first ran it.* Under a `do` the dice cancel out of the paired difference, because both worlds roll the same dice. Under an `observe` they do not: *which* of a version's eight worlds survive the observation is itself a coin flip, and a version can lose all eight. Measured on Hormuz at seed `20261001` and the shipped 2 000 × 8: learning that B happened moves M1 by `+.063` and M2 by `+.107`, and with every version counted as one vote both came out at **`89.05%`** — a hair under the 90% bar — so both read `unchanged`, the rail was empty, the summary was the second sentence, and **This happened** looked like a button that does nothing.

   **Decided 2026-09-17 (Kent, G2): count only the versions that survived, each by how much it survived.** The cause is not the coin flip; it is that **209 of the 2 000 versions have no surviving world at all**, weigh nothing in the number and the band, and were each casting a full vote against the direction anyway. One rule, stated once in B3 and obeyed everywhere: *the direction is read with the same weights the number was read with.* Both endings then read **`98.66%`** (`99.44%` among the versions that survived, one vote each), both are `shifted`, and both are on the rail. **Worlds per version stays 8** — the candidate repair of running more worlds under an observation was not taken, because it buys steadiness with time and does not fix the arithmetic — **and the 90% bar is untouched.** Under the five edits that are not an observation every weight is 1, so no other number in this chapter moved by a bit, which `test_an_edit_that_is_not_an_observation_is_unchanged_by_the_weights` pins by computing one such difference both ways and asking for the same bytes.

   **Decided 2026-09-17 (Kent, G3), the related fact that came with it.** A claim with **no causes** moves under an observation only through the version weights, because within one version such a claim's answer is its prior in every world: observing B moves H by `−0.0002`, and observing C moves H from `.356` to `.365`. Its same-direction share is zero by construction, so it can never be `shifted`. There is no fifth state; the claim's row carries `moved_only_by_reweighting` and the Inspector says *"this claim moved only because the observation made some versions count more."* See B3 and the Data model.

   *Recorded as a dated amendment to decision record **0014**, which owns the two loops and the `observe` weighting; nothing in that decision changed.*
