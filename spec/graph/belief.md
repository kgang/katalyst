# Belief — a likelihood with a range and an owner

## Purpose

A bare number on a box is a claim from nowhere. A **belief** is a likelihood that says whose it is and how sure it is: a value between 0 and 1, an honest range around it, and an **owner** — the model, the user, or a market. Every claim on the map carries up to three of them side by side, and they are never combined into one. That is the whole product in one design choice: the model's `.61`, the market's `.48` and your own `.30` on the same claim are not three attempts at one true number to be averaged away, they are the disagreement you are about to trade. What a user can do that they could not before: see, on any step of an argument, where their own view differs from a model's and from a live price — and put their own number on the map without the model overwriting it.

---

## Data model

Written by pull request 2 of this stack in `backend/src/katalyst/domain/belief.py`. Frozen, like everything else in the domain. Field descriptions rather than comments, so the same sentences reach the generated browser types.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
```

```python
class Belief(BaseModel):
    """A likelihood with an honest range and a name on it.

    `p` is the likelihood, `lo` and `hi` are the range around it, and `owner`
    says whose number this is. There are exactly three owners and no code path
    ever combines two of them into one number.

    A belief is a number, never text. The domain does not round it and does not
    store it as a string; rounding happens once, at the moment of display.
    """

    model_config = ConfigDict(frozen=True)

    p: float = Field(
        ge=0.0, le=1.0,
        description="How likely the claim is to come out true, from 0 (certainly not) to 1 (certainly yes).",
    )
    lo: float = Field(
        ge=0.0, le=1.0,
        description="The bottom of the honest range around `p`. Never above `p`.",
    )
    hi: float = Field(
        ge=0.0, le=1.0,
        description="The top of the honest range around `p`. Never below `p`.",
    )
    owner: Literal["model", "user", "market"] = Field(
        description="Whose number this is: the model's estimate, the user's own, or a live price at a venue.",
    )

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Belief":
        """`0 <= lo <= p <= hi <= 1`. The field bounds cover 0 and 1; this covers the order."""
        if not (self.lo <= self.p <= self.hi):
            raise ValueError(
                "a belief must satisfy low <= likelihood <= high; got "
                f"low={self.lo}, likelihood={self.p}, high={self.hi}"
            )
        return self
```

```python
class Beliefs(BaseModel):
    """The three voices on one claim: the model's, the user's, and a market's.

    Three named slots, deliberately not a dictionary, so that nothing can loop
    over them and average them by accident. `model` is always present. `user` is
    absent until the user says what they think. `market` is absent when no venue
    quotes this claim — and absent means the words "no market", never a blank
    and never a stand-in number.
    """

    model_config = ConfigDict(frozen=True)

    model: Belief = Field(
        description="What the model thinks, with this claim's causes taken into account. Always present.",
    )
    user: Belief | None = Field(
        default=None,
        description="What the user thinks. Written only by the `believe` intervention. None means the user has not said.",
    )
    market: Belief | None = Field(
        default=None,
        description="What a venue is currently pricing, read live and read-only. None means no venue quotes this claim.",
    )

    @model_validator(mode="after")
    def _owners_match_slots(self) -> "Beliefs":
        """A belief sitting in the wrong slot would make the never-merge rule unenforceable."""
        for slot, belief in (("model", self.model), ("user", self.user), ("market", self.market)):
            if belief is not None and belief.owner != slot:
                raise ValueError(f"the '{slot}' slot holds a belief owned by '{belief.owner}'")
        return self
```

**On the field named `model`.** It is legal. Pydantic protects names beginning with `model_` (so `model_config` and `model_dump` are reserved); plain `model` is not one of them. It stays `model` because that is the word the vocabulary uses, on the canvas and in the code alike.

### Two rules, two places

The range rule `0 ≤ lo ≤ p ≤ hi ≤ 1` is a **pydantic validator**: an out-of-range belief cannot be constructed at all. That is different from the "a `market` terminal needs a payoff" rules in [`proposition.md`](proposition.md), which are checked by `validate` and come back as messages the user reads. The line between them: *a rule that only our own arithmetic could break raises; a rule a well-formed model proposal could plausibly break becomes a violation with a plain sentence.*

There is still a violation code `belief_out_of_range` — rule 11 in [`validity.md`](validity.md) — and it is not redundant. It exists so that (a) the engine can catch a malformed proposal and report it alongside the other violations as interface text rather than as a stack trace, and (b) a graph that arrived some other way — a stored fixture, or the output of the propagation pass in stack 03a — is re-checked rather than trusted. Belt and braces, on purpose.

### Why the three owners are never merged

Averaging them destroys the only thing the map is for. If the model says `.61`, the market says `.48` and you say `.30`, the average `.46` is a number nobody holds, describing nobody's view, and it deletes the two gaps that are the actual output: **model minus market is the edge you might trade; user minus model is the argument you are having with the tool.** This is invariant INV-11, and it is enforced by a test that inspects our own source code rather than by good intentions — see INV-graph.13 below.

The rule is narrow and absolute: **no function in `domain/` takes beliefs of two different owners and returns one number.** Showing them next to each other is encouraged. Subtracting one from the other for display — the thesis card's `edge` column — happens outside the domain and is labelled as a difference, not as a belief.

### `prior` versus `beliefs.model`

Both are the model's number. They differ in what has been taken into account.

| | `prior` | `beliefs.model` |
|---|---|---|
| Plain meaning | What the model thinks about this claim **on its own**, before looking at what causes it | What the model thinks **after** the claim's causes have pushed on it |
| Where it comes from | Elicited once, anchored on a base rate where there is one (see [`proposition.md`](proposition.md)) | Computed: start from the prior, add one push per active incoming link, on a scale where pushes add up (decision record 0005) |
| When it is computed | At generation | By propagation, in stack 03a. Until then the Hormuz fixture stores an illustrative value and says so |
| For the hypothesis | The same number — the root has no causes, so there is nothing to add | The same number |
| Owner | `model` | `model` |

Keeping both is what lets the Inspector answer "why is this `.71` when the base rate says `.20`?" with a list: the prior, then each incoming link and the push it contributed. The audit trail *is* the arithmetic.

### The market voice

A `market` belief is a live, read-only price at a real venue — Polymarket first, the Federal Reserve's FRED economic-data service second (decision record 0010). The mid-price of a contract on Polymarket — halfway between the best bid and the best offer — becomes `p`; where the venue publishes a spread, that becomes `lo` and `hi`; its provenance is `market_implied`, meaning "this came from a price, not from an argument".

Two things follow. **Absent is a state, not a gap.** `beliefs.market is None` renders as the words *"no market"* with the reason beside it, never as a blank chip and never as a placeholder number. Many honest hypotheses have no contract — that is the path to a `not_tradeable` terminal, and it is information. **Two venues are two rows.** If Polymarket and Kalshi both quote a claim, both are shown and the spread between them is called out as a signal. They are not averaged into a single market number, for the same reason the three owners are not.

### The user voice

A `user` belief is written by exactly one thing: the `believe` intervention, recorded on a branch like every other change (see [`../multiverse/interventions.md`](../multiverse/interventions.md)). The model never writes it, never reads it in order to adjust itself, and never overwrites it. In this version it is also not pushed through the graph — the user's number sits beside the model's rather than replacing it and re-propagating. Propagating a user's whole world is deferred to the last stack of the roadmap (decision record 0004).

The first `user` belief usually arrives before the map exists: the likelihood slider on the input screen, with its explicit "I don't know" state, is stored as a `user` belief on the hypothesis.

### The domain never rounds, and never stores a string

Beliefs are rendered at **two significant figures with the range**: `.35 (.2–.5)`, never `.347`. Precision beyond two figures on an elicited number is a lie about how much we know — the honesty requirement, NFR-1 in `PRODUCT_REQUIREMENTS.md` §8.

That is a rendering rule, and the rendering lives in the workbench spec. What belongs here is the half of it the domain must obey:

- **Never round before storing.** `p` keeps the full float it was computed with; two worlds must stay byte-identical on replay, and rounding at rest would make that depend on display choices.
- **Never store the rendered form.** There is no `p_display` field and no string anywhere in `Belief`. A number formatted into text is a number that can no longer be compared, summed, or diffed.
- **Never compare rendered forms.** A diff between two worlds compares floats; two beliefs that both display `.35` may genuinely differ, and the delta rail must be able to say so.

---

## Behaviour

### B1 — Three numbers, side by side, on one claim

The Hormuz map reaches terminal M1, *a Polymarket contract "Brent below $70 on 2026-10-31" resolves YES*. Its tile shows three chips (numbers illustrative, from research report 02 §3, marked in the fixture as `argued`, never `documented`):

| Owner | Shown | Where it came from |
|-------|-------|--------------------|
| model | `.61 (.45–.75)` | Propagated: prior `.30`, plus the push from *Brent crude settles below $68 for five sessions* |
| market | `.48 (.46–.50)` | The contract's mid-price, read minutes ago from Polymarket, `market_implied` |
| user | `.30 (.20–.45)` | What you typed on the slider |

Nothing on this tile is an average. The thesis card later reports `model − market = +.13` as an **edge**, computed outside the domain and labelled a difference. The gap is the point of the screen.

### B2 — "I think that is less likely than that"

You drag the user chip on the Hormuz hypothesis from nothing to `.20 (.10–.35)`. What happens: a `believe` intervention is appended to the current branch, carrying a `Belief` with owner `user`. The `model` and `market` chips do not move, now or ever, on account of it. Because the change is a patch on a branch, it replays, it diffs, and it can be undone by dropping the intervention — there is no hidden "user override" flag anywhere in the graph.

What does **not** happen in this version: your `.20` does not flow downstream. The map still shows the model's propagated numbers; yours sits beside them on the claims you have touched.

### B3 — No market is a sentence, not a blank

*"Photonic chips get adopted faster than expected"* produces a chain whose most interesting claim — datacentre transceiver share crossing a threshold — has no contract anywhere. The tile shows two chips and one sentence:

```
model   .42 (.25–.60)
user    —
market  no market · "no venue quotes datacentre photonic transceiver share"
```

The empty `user` slot renders as a dash inviting you to say what you think. The empty `market` slot renders as words, with the reason, and it is the thing that pushes this chain toward a `not_tradeable` terminal.

### B4 — A number that can say why

Click the model chip on *"Brent crude settles below $68 for five sessions"* and the Inspector unrolls it (illustrative):

```
prior                            .20 (.10–.35)   base rate: 4 of 19 months since 2022 in which
                                                 Brent crude settled below $68 for five sessions
+ H, the strait opens (trigger)  +1.6 push       "the war-risk premium in the price unwinds"
+ C, the Lloyd's war-risk
  premium for Gulf transits
  falls below 0.4% (sustain)     +0.7 push       "cheaper insurance lowers delivered cost"
= model                          .71 (.55–.83)
```

A *push* is decision record 0005's link strength: a signed amount added on the log-odds scale — the scale on which independent influences add up instead of multiplying. Two pushes of `+1.6` and `+0.7` on a prior of `.20` land on `.71`; the propagation chapter of the multiverse part (stack 03a) spells out the arithmetic and where the range comes from. The rule this chapter enforces is narrower: no line of that list may be a number whose owner cannot be named.

### B5 — Two significant figures, always, and only at the last moment

`p = 0.6134` is what the domain stores, sends over the wire, and replays. `.61` is what the chip shows. `p = 0.6134, lo = 0.4471, hi = 0.7522` displays as `.61 (.45–.75)`. A chip is never permitted to show `.6134`; the rendering test in the frontend checks exactly that, and that the range is never omitted.

---

## INVARIANTS

Each is written *for all inputs drawn from generator S, statement P holds*, and names the automated test that checks it.

Generators live in `backend/tests/strategies.py`: `beliefs()`, `propositions()` and `graphs()` produce random beliefs, propositions and maps that are **valid by construction**. Local numbers are unique across the whole of `spec/graph/`: this chapter uses `INV-graph.12`–`INV-graph.14`, [`proposition.md`](proposition.md) uses `INV-graph.9`–`INV-graph.11`, and the lower numbers belong to [`link.md`](link.md) and [`validity.md`](validity.md).

### INV-graph.12 — Honest numbers *(refines INV-7)*

- For every belief drawn from `backend/tests/strategies.py::beliefs()`: `0 ≤ lo ≤ p ≤ hi ≤ 1`.
- For every three floats drawn from the `hypothesis` property-testing library's own `floats()` and every owner drawn from its `sampled_from(("model", "user", "market"))` — that pair is `backend/tests/strategies.py::raw_belief_fields()`: constructing a `Belief` from them either produces one satisfying that chain of inequalities, or raises. There is no third outcome, and no silent clamping to fit.
- For every graph drawn from `backend/tests/strategies.py::graphs()` driven through a random sequence of interventions by the state machine `GraphEditMachine`: after **every** step, every belief on every proposition still satisfies it.
- **Tests:** `test_belief_bounds_at_construction` — introduced by this chapter, **stack 02**. And `test_belief_bounds_after_any_sequence` — named in decision record 0008's invariant table, driven by `GraphEditMachine`, **stack 03a**, because nothing applies an intervention until then.

### INV-graph.13 — Three voices, never merged *(refines INV-11)*

Two checks, one test name.

- **Over our own source code.** Here the thing quantified over is not generated data but every module under `backend/src/katalyst/domain/`, walked at test time — a static check with a fixed, finite input, which is why it names no generator. For every function defined in any of those modules: none takes beliefs of two different owners — two or more `Belief` parameters, or one `Beliefs` — and returns a `float`, a `Belief`, or a structure containing either. Checked by walking the syntax tree of every module under `domain/` and reading its type annotations, the same technique as the import-boundary test `test_domain_imports_nothing_impure`. **Stack 02.**
- **Over generated data.** For every proposition drawn from `propositions()` that has all three slots filled, and every belief drawn from `beliefs()` re-owned to `user`: applying a `believe` intervention with that belief leaves `beliefs.model` and `beliefs.market` byte-identical, and changes only `beliefs.user`. **Stack 03a**, since applying an intervention is stack 03a's work; [`../multiverse/interventions.md`](../multiverse/interventions.md) states the same guarantee from the other side as `test_believe_touches_only_user_belief`.
- **Test:** `test_beliefs_never_merged` — named in decision record 0004's confirmation list. Decision record 0010 adds its outward-facing twin, `test_market_belief_never_merged`, which extends the source-code check to `api/` and to the thesis-card builder.

### INV-graph.14 — Every belief sits in the slot that matches its owner

- For every proposition drawn from `propositions()`: `prior.owner` and `beliefs.model.owner` are `"model"`; `beliefs.user.owner`, where the slot is filled, is `"user"`; `beliefs.market.owner`, where filled, is `"market"`.
- For every belief drawn from `beliefs()` whose owner is not `"user"`: constructing a `Beliefs` with it in the `user` slot raises. Likewise for the other two slots.
- **Test:** `test_owner_matches_slot` — introduced by this chapter. **Stack 02.** Without it, INV-graph.13's source-code check could be satisfied while a user's number sat in the model's chip.

---

## ANTI-PATTERNS

1. **Do not average the three owners, weight them, or reconcile them.** Because the average is a number nobody holds, and it deletes the two gaps that are the product's entire output — model against market is the edge, user against model is the argument. **Instead:** store three slots, render three chips, and where a single number is genuinely needed (the thesis card's `edge`), compute it outside the domain, label it a *difference*, and show both sides of it.

2. **Do not store a display string on a belief.** No `p_display`, no `".35 (.2–.5)"` field, no pre-rounded `p`. Because a number turned into text can no longer be compared, diffed or replayed, and a rounded stored value makes two worlds differ on replay for a display reason. **Instead:** store the full float; format once, in the component that draws the chip.

3. **Do not ship a bare point with no range.** `.35` on its own claims a precision that an elicited number does not have, and it hides the one thing that tells you where to spend more effort: the width. **Instead:** `lo` and `hi` are required fields, and the chip always draws the range. If the range is honestly unknown, that is a question for the model, not a reason to drop the field.

4. **Do not say "confidence" when you mean probability.** Because the word has been retired: as of 2026-09-17 nothing in the product carries a field called `confidence` — the one that lived on a link was dropped (see [`link.md`](link.md), Open questions 1) — and reintroducing it as a loose synonym for a likelihood puts two ideas under one word and makes both unreadable. **Instead:** say *likelihood* or *probability* for the number and *range* for `lo`–`hi`. How well-founded a mechanism is, say with `provenance` and the rationale; how much independent runs of the model agreed, say *agreement*, and only where something has actually computed it.

5. **Do not fill an absent market quote with a stand-in** — not 0.5, not the model's number, not a blank chip. Because "no venue prices this" is a finding, and it is the finding that drives a chain to a `not_tradeable` ending. **Instead:** `None` in the slot, the words "no market" on the chip, and the reason beside them.

---

## Open questions

*Raised 2026-09-16.*

1. **A belief has no provenance field.** Invariants INV-2 and INV-12 say provenance is encoded on every chip. Owner implies it for two of the three (`user`, and `market_implied` for a market), but a `model` belief anchored on a documented base rate and one asserted from nothing look identical. Add `provenance` to `Belief`, carry it on the proposition, or derive it from whether `base_rate.sources` is empty?
2. **Where do a quote's `as_of`, venue and link live?** Decision record 0010's grounding-layer quote carries them; the domain `Belief` has four fields and no clock. Does the domain gain a small `MarketQuote` wrapper, or does the Inspector read them from the grounding cache alongside the belief?
3. **What does the range actually mean?** Decision record 0005 says the Inspector labels it "model interval, uncalibrated" and that it mixes simulation noise with the elicited spread. Is `lo`–`hi` an 80 per cent band, a plausible minimum and maximum, or "the model's honest spread"? Nothing tests it today, and no calibration claim can be made until it is pinned down.
4. **Is a zero-width range legal?** `.35 (.35–.35)` satisfies every rule and claims certainty the model does not have. Leave it, or have `validate` warn?
5. **Two significant figures, precisely.** The honesty requirement's own example, `.35 (.2–.5)`, renders the point at two figures and the bounds at one. Deliberate — a coarser range is the honest one — or shorthand? And what is two significant figures for `p = 0.035` or `p = 0.9962`? One worked table in the workbench chapter settles it; the domain stores the full float either way.
