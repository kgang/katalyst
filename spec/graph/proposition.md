# Proposition — a claim that can be checked

## Purpose

A thesis usually lives in a sentence: *"if Hormuz opens, oil falls."* You cannot check a sentence, you cannot put a number on it, and you certainly cannot trade it. A **proposition** is the unit that fixes this: a claim that will be true or false **by a date**, judged by a **named source**. Everything else in Katalyst is built on that promise — a likelihood means something because someone will eventually settle the claim; a chain of claims can end in an instrument because the last claim names one; and a map can be audited because every box in it is a bet somebody could win or lose. What a user can do that they could not before: hand over a hunch and get back a list of claims, each one of which a named judge will settle on a named date.

---

## Data model

These are the shapes exactly as pull request 2 of this stack writes them, in `backend/src/katalyst/domain/proposition.py`. Pydantic is the Python library that defines and validates our data shapes. Every class is **frozen** — once built, it cannot be changed. A change to a proposition is never an edit; it is an intervention recorded on a branch (see [`../multiverse/interventions.md`](../multiverse/interventions.md)).

Every collection is a `tuple`, not a `list`, because a frozen object holding a list is only half frozen. Every field carries a plain-words `description` rather than a comment, for one reason: descriptions travel into the generated browser types, so the same sentence explains the field in Python and in TypeScript.

`Belief` and `Beliefs` are defined in [`belief.md`](belief.md) and imported here.

```python
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalyst.domain.belief import Belief, Beliefs
```

```python
PropositionId = str
"""The identifier of one proposition: a plain string, unique within its map.

Our code mints it and the model never invents one (decision record 0003).
Minting needs a clock and randomness, so it happens outside the domain, in
`engine/ids.py`, and the finished identifier is passed in; the domain never
checks its format. The Hormuz fixture uses readable ones: H, C, B, R, S, M1,
M2, N1. Identifier rules live in `validity.md`.
"""
```

```python
class Resolution(BaseModel):
    """How a claim gets settled: the test, who applies it, and by when.

    Every proposition has one. A claim with no resolution is a vibe, and a
    likelihood attached to a vibe can never be scored, right or wrong.
    """

    model_config = ConfigDict(frozen=True)

    criteria: str = Field(
        description=(
            "The test, written so that two people reading it would agree on the "
            "answer. 'At least 14 consecutive days of unrestricted commercial "
            "transit', not 'shipping returns to normal'."
        )
    )
    source: str = Field(
        description=(
            "Who or what applies the test: a named publication, exchange, agency "
            "or venue. 'Lloyd's List transit counts', not 'the news'."
        )
    )
    by: date = Field(
        description=(
            "The date by which the test has been applied. After this date the "
            "claim is true or false — never still open."
        )
    )
```

```python
class BaseRate(BaseModel):
    """How often this kind of thing has happened before: k times out of n.

    The outside view — the anchor a likelihood starts from before anything
    specific to this case is considered. Optional, because some claims have no
    honest reference class, and absent is better than invented.
    """

    model_config = ConfigDict(frozen=True)

    reference_class: str = Field(
        description=(
            "The set of past cases being counted, stated precisely enough that "
            "someone else could recount them: 'Hormuz closure or disruption "
            "episodes since 1980 that ended within 90 days'."
        )
    )
    k: int = Field(ge=0, description="How many cases in that set came out true.")
    n: int = Field(gt=0, description="How many cases are in that set altogether.")
    sources: tuple[str, ...] = Field(
        default=(),
        description=(
            "Web addresses where the count can be checked. Empty means the count "
            "is the model's own recollection, and nothing downstream of it may "
            "claim to be documented."
        ),
    )

    @model_validator(mode="after")
    def _k_within_n(self) -> "BaseRate":
        """You cannot count 7 cases out of 5."""
        if self.k > self.n:
            raise ValueError(
                f"a base rate counts {self.k} cases out of {self.n}; k must not exceed n"
            )
        return self
```

```python
class Evidence(BaseModel):
    """One published item that supports or undercuts a claim.

    Evidence moves no number by itself in this version. It is what the Inspector
    shows when the user asks why a likelihood is what it is, and it is what lets
    the panel say "two for, one against" without re-reading the sources.
    """

    model_config = ConfigDict(frozen=True)

    claim: str = Field(description="What the source says, in one sentence, in our words.")
    url: str = Field(description="Where to read it, so the reader can check us.")
    direction: Literal[1, -1] = Field(
        description=(
            "1 if this supports the proposition, -1 if it cuts against it. There "
            "is no 0: an item that points neither way is not attached at all."
        )
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How much this item counts, from 0 (barely) to 1 (decisive). Elicited "
            "and unitless; shown as a bar, never as a decimal."
        ),
    )
```

```python
class ContractPayoff(BaseModel):
    """A position in one named contract on one named venue: the yes side, or the no side.

    Used when a real venue already quotes this exact claim, which is the happy
    case: a Polymarket contract on Brent below $70 settles on the same fact the
    proposition does.

    The boundary this class sits on: **the domain names what you would trade;
    the grounding layer names what it costs.** So there is a venue, a contract
    and a side here, and no price. What the contract trades at, how wide the
    bid-offer spread is, and the moment we looked are a market belief, fetched
    live from the venue when the thesis card needs it (decision record 0010). A
    price written into this class would be stale the moment it was written, and
    the domain reads no clock (decision record 0003).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["contract"]
    venue: str = Field(
        description=(
            "Where the contract trades, named as the venue names itself: "
            "'Polymarket'. This is what tells the grounding layer whom to ask."
        )
    )
    contract_id: str = Field(
        description=(
            "The venue's own identifier for the contract, so a quote can be "
            "fetched later without guessing from the title."
        )
    )
    title: str = Field(
        description=(
            "The contract's title in the venue's words, so a reader recognises "
            "it on the venue's own page: 'Brent below $70 on 2026-10-31'."
        )
    )
    side: Literal["yes", "no"] = Field(
        description=(
            "'yes' if the position pays out when the claim comes true, 'no' if "
            "it pays out when the claim fails."
        )
    )


class PricePayoff(BaseModel):
    """A position in something with a price: which way, and how far it moves.

    Used when no venue quotes the claim itself but something whose price the
    claim moves can be bought or sold — a fund, a ticker, a futures contract, or
    one traded against another.

    The same boundary as `ContractPayoff`: **the domain names what you would
    trade; the grounding layer names what it costs.** The instrument and the
    expected move are written here; the price you would pay for it, the spread,
    and the moment we looked are a market belief (decision record 0010).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["price"]
    instrument: str = Field(
        description=(
            "What you would buy or sell, named the way its venue names it: a "
            "ticker, a futures contract, or one traded against another written "
            "out in full — 'XLE against SPY'."
        )
    )
    direction: Literal["long", "short"] = Field(
        description=(
            "'long' if the position makes money when the claim comes true, "
            "'short' if it makes money when the claim fails."
        )
    )
    move: float = Field(
        ge=0.0,
        description=(
            "How far the instrument's price is expected to move if the claim "
            "comes out true, as a fraction of that price: 0.03 is three per "
            "cent. Which way it moves is carried by `direction`, so this number "
            "is never negative. It is not a return on a position: a return needs "
            "an entry price, and prices are not kept here."
        ),
    )


Payoff = Annotated[ContractPayoff | PricePayoff, Field(discriminator="kind")]
"""What you would trade on a `market` terminal: a contract, or a price.

Read the `kind` field to know which of the two it is — `"contract"` or
`"price"`. That makes this a *discriminated union*: a reader, and the TypeScript
types generated for the browser, can tell the two shapes apart from one field
without guessing from which others happen to be present. It is the same pattern
the six interventions use (`../multiverse/interventions.md`).

**Neither `kind` has a default, and that is the point.** A default would keep the
field out of the schema's list of required fields, and that schema is what the
model is asked to fill — so the one field that says which of the two shapes was
meant would become the one field the model could leave out. Then a price payoff
with no `kind` would read as a contract payoff missing its venue, and the refusal
would name the wrong thing. Required in both shapes, the discriminator is always
there to discriminate on.

Neither shape carries a price. That is the rule stated in both docstrings above
and settled in decision record 0013.
"""
```

```python
class Proposition(BaseModel):
    """A claim that will be true or false by a date, judged by a named source.

    The unit the whole map is built from. Never a vibe ("tensions ease"); always
    a check ("at least 14 consecutive days of unrestricted commercial transit
    through the Strait of Hormuz per Lloyd's List, by 2026-11-01").

    Frozen. A proposition is never edited in place; a change to one is an
    intervention recorded on a branch.
    """

    model_config = ConfigDict(frozen=True)

    id: PropositionId = Field(
        description="This proposition's identifier, minted by our code before the proposition is built."
    )
    claim: str = Field(
        description=(
            "The claim in one sentence, as a person would say it out loud. The "
            "precise, settleable version lives in `resolution.criteria`."
        )
    )
    kind: Literal["hypothesis", "event", "market", "not_tradeable"] = Field(
        description=(
            "What this proposition is for: `hypothesis` is the user's root input, "
            "`event` a step in the middle, `market` an ending that names an "
            "instrument, `not_tradeable` an ending that names why there is none."
        )
    )
    resolution: Resolution = Field(
        description="How and when this claim gets settled, and by whom."
    )
    prior: Belief = Field(
        description=(
            "The model's likelihood for this claim before its causes are taken "
            "into account. Always owned by `model`."
        )
    )
    beliefs: Beliefs = Field(
        description=(
            "The three likelihoods shown side by side: the model's (causes taken "
            "into account), the user's, and the market's. Never merged."
        )
    )
    base_rate: BaseRate | None = Field(
        default=None,
        description=(
            "How often this kind of thing has happened before, when there is an "
            "honest reference class. None means there is not one."
        ),
    )
    evidence: tuple[Evidence, ...] = Field(
        default=(),
        description=(
            "Published items for and against, each with a direction and a weight. "
            "Empty is honest; invented sources are not."
        ),
    )
    payoff: Payoff | None = Field(
        default=None,
        description=(
            "What you would trade: a contract on a venue, or a position in "
            "something with a price. Required when `kind` is `market` — required "
            "by `validate`, not by this class. See `validity.md`."
        ),
    )
    not_tradeable_reason: str | None = Field(
        default=None,
        description=(
            "Why this chain ends without an instrument, in one plain sentence. "
            "Required when `kind` is `not_tradeable` — again by `validate`."
        ),
    )

    @model_validator(mode="after")
    def _prior_is_the_models(self) -> "Proposition":
        """The prior is the model's own number; any other owner is a bug in our code."""
        if self.prior.owner != "model":
            raise ValueError(
                f"a proposition's prior must be owned by 'model'; got '{self.prior.owner}'"
            )
        return self
```

### The four kinds

| `kind` | What it is | Must come with | Who makes it |
|--------|------------|----------------|--------------|
| `hypothesis` | The user's root input, asserted as true. Exactly one per graph | — | The user's typed sentence, turned into a settleable claim by the model |
| `event` | A step in the middle of the chain | — | The model, proposing |
| `market` | An ending that names something you can trade | `payoff` | The model, then checked against a real venue (decision record 0010) |
| `not_tradeable` | An ending that says, in words, why this chain cannot be traded | `not_tradeable_reason` | The model, when no instrument exists |

`market` and `not_tradeable` are the two **terminals**. A graph must contain at least one of them (INV-9): a map that stops at "and so oil is cheaper" is an essay.

### Which rule is checked where, and why

Two places, one principle. **A rule only our own code could break is a pydantic validator and raises an exception. A rule a well-formed model proposal could plausibly break is a `Violation` — a stable code, the subject's identifier, and a plain sentence the user reads.** A proposal that is refused is shown to the user, so its message is interface text, not a stack trace.

| Rule | Checked by | Why there |
|------|------------|-----------|
| `low ≤ likelihood ≤ high` on any belief | pydantic, at construction | Only our own arithmetic can produce one; see [`belief.md`](belief.md) |
| `prior.owner` is `model` | pydantic | The engine builds the belief; a wrong owner is our bug |
| `k` does not exceed `n` on a base rate | pydantic | Same |
| `resolution.criteria` and `resolution.source` are not blank | `validate` | A model can easily hand back an empty string, and the user must be told which claim it was. Code `missing_resolution` |
| A `market` proposition has a `payoff` | `validate` | The model proposes terminals; this is the commonest thing it gets wrong. Code `market_without_payoff` |
| A `not_tradeable` proposition has a reason | `validate` | Same. Code `not_tradeable_without_reason` |
| Exactly one `hypothesis`; at least one terminal | `validate` | No single proposition can know what the rest of the graph contains. Codes `no_hypothesis`, `multiple_hypotheses`, `no_terminal` |

`validate(graph) -> list[Violation]` returns **every** violation at once and repairs nothing. [`validity.md`](validity.md) owns the codes, the message wording, and the argument for rejecting rather than repairing.

### `prior` versus `beliefs.model`

`prior` is what the model thinks about this claim **on its own**; `beliefs.model` is what it thinks **after its causes have been taken into account**. Both are numbers owned by `model`, and for the hypothesis — which has no causes — they are the same. [`belief.md`](belief.md) tells the whole story, including who computes `beliefs.model` and when.

---

## Behaviour

### B1 — A claim is written so that it can be checked

The user types *"The Strait of Hormuz is going to open next week."* That is a topic, not a claim. The model turns it into a proposition, and the shape of the data forces the turn: there is nowhere to put a vibe.

| | |
|---|---|
| **Not a proposition** | "Tensions in the Gulf ease." |
| **Why not** | Nobody can say on which day it became true, and no publication will ever rule on it. Two readers would score it differently. |
| **A proposition** | `claim`: "The Strait of Hormuz reopens to unrestricted commercial transit." `resolution.criteria`: "At least 14 consecutive days of unrestricted commercial transit through the Strait of Hormuz." `resolution.source`: "Lloyd's List transit counts." `resolution.by`: `2026-11-01`. |

The test is mechanical: *can you name the person who settles this, and the day they settle it by?* If not, it is not a proposition, and `validate` says so in those words.

### B2 — A terminal names an instrument, or says why it cannot

Every chain has to land somewhere you could put money, or admit that it does not. Hormuz lands twice:

```
H ──▶ C ──▶ B ──┬──▶ M1   market   a Polymarket contract "Brent below $70 on
│           ▲   │                  2026-10-31" resolves YES
└───────────┘   │                  payoff: contract — Polymarket, side yes
                │
                ├──▶ M2   market   the energy fund XLE underperforms the S&P 500
                │                  fund SPY by more than 3% over 20 days
                │                  payoff: price — short XLE against SPY, move 0.03
                │
                └──▶ R ──▶ B       OPEC+ announces output restraint, and restraint
                                   props the price back up
```

H reaches B twice: directly, along the arrow that loops beneath `C`, and the long way through `C` itself. The `B → R → B` in the last row is one loop drawn flat — the same `B` twice — and it is legal only because `B → R` is the market feeding back on the world, marked reflexive and carrying a delay. [`link.md`](link.md) owns all of that.

The two payoffs read under **one** rule, and it is the rule the two shapes exist to enforce: *the domain names what you would trade; the grounding layer names what it costs.* M1 is a **contract payoff** — a real venue quotes this exact claim, so the terminal names the venue (Polymarket), the venue's identifier for the contract, its title, and the side you would take (yes). What the contract costs is deliberately absent: it is fetched live as a market belief when the thesis card is built, which is why the old `1.08` — a return on a position, which silently assumed an entry price no field ever held — has gone. M2 is a **price payoff** — no venue quotes "XLE underperforms SPY by 3%", so the terminal names the instrument (XLE against SPY), the direction (short), and how far the price is expected to move if the claim comes out true (`move` of 0.03, three per cent). Decision record 0013 has the argument.

A different assignment example lands in the other state. *"Photonic chips get adopted faster than expected"* runs into a wall: no venue quotes datacentre transceiver share, and the listed pure-plays are too thin to trade honestly.

```
P ──▶ … ──▶ N1  not_tradeable
                not_tradeable_reason: "No venue quotes photonic transceiver share
                of datacentre interconnect, and the two listed pure-plays trade
                under $40m a day — too thin to express this at size."
```

That is a real answer, and the product says it out loud. What it must never do is end the chain in a sentence with no `kind` of its own. If the model proposes a `market` terminal with no `payoff`, `validate` returns `market_without_payoff` naming the claim — *"the tradeable claim 'a Polymarket contract on Brent below $70 on 2026-10-31 resolves YES' does not say what you would trade"* — and the proposal is refused, not patched.

### B3 — Evidence attaches to a claim with a direction and a weight

While the chain is being built, the retrieval step reads the web and attaches what it found to the claim it bears on. Each item says which way it points and how much it counts. On the Hormuz hypothesis (numbers illustrative, from research report 02 §3):

| Item | `direction` | `weight` |
|------|-------------|----------|
| "Omani mediation round reported, both sides attending" | `+1` | 0.3 |
| "Three tankers remain held; no release announced" | `-1` | 0.4 |

The Inspector shows these as two bars under the claim, one each way, each a click from its source. Nothing here moves a number automatically in this version — the model's likelihood is its own, and the evidence is the audit trail beside it. An item with no `url` is not evidence and is not attached; a link that claims to be `documented` with no sources behind it is a violation (INV-2, owned by [`link.md`](link.md)).

### B4 — A base rate anchors the prior

Before asking what the model thinks, ask what usually happens. The Hormuz hypothesis carries a reference class: *"closure or disruption episodes in the Strait of Hormuz since 1980 that ended within 90 days"*, 7 out of 9. That is where the prior of about `.35` starts from, adjusted down for the specifics of this episode. The Inspector shows the count, the class, and the sources, so a reader who disputes the number can dispute the class instead of arguing about a feeling.

A claim with no honest reference class carries `base_rate = None`. That is a visible state in the Inspector — "no reference class" — not a blank.

---

## INVARIANTS

Each is written *for all inputs drawn from generator S, statement P holds*, and names the automated test that checks it.

Generators live in `backend/tests/strategies.py`: `propositions()` and `graphs()` produce random propositions and maps that are **valid by construction**, and `broken_graphs(rule)` produces the same maps with exactly one named rule broken. Local numbers are unique across the whole of `spec/graph/`: this chapter uses `INV-graph.9`–`INV-graph.11`, [`belief.md`](belief.md) uses `INV-graph.12`–`INV-graph.14`, and the lower numbers belong to [`link.md`](link.md) and [`validity.md`](validity.md).

### INV-graph.9 — Checkable *(refines INV-1)*

- For every proposition drawn from `backend/tests/strategies.py::propositions()`: `resolution.criteria` and `resolution.source` are non-empty once surrounding whitespace is stripped, and `resolution.by` is a `date`.
- For every graph drawn from `broken_graphs("missing_resolution")` — a valid map with exactly one proposition's criteria or source blanked: `validate(graph)` returns exactly one violation, code `missing_resolution`, whose `subject` is that proposition's identifier.
- **Test:** `test_validate_rejects_unresolvable_proposition` — named in decision record 0003. **Stack 02.**

### INV-graph.10 — Ends somewhere *(refines the proposition half of INV-9)*

- For every graph drawn from `graphs()`: at least one proposition has `kind` of `market` or `not_tradeable`.
- For every graph drawn from `broken_graphs("no_terminal")` — every terminal's `kind` changed to `event`: `validate(graph)` returns exactly one violation, code `no_terminal`.
- **Test:** `test_validate_requires_terminal` — named in decision record 0003. **Stack 02.**

### INV-graph.11 — A terminal names an instrument or a reason *(refines the other half of INV-9)*

- For every proposition drawn from `propositions()` with `kind == "market"`: `payoff` is not `None`. For every one with `kind == "not_tradeable"`: `not_tradeable_reason` is not `None` and is non-blank.
- For every graph drawn from `broken_graphs("market_without_payoff")`: `validate(graph)` returns exactly one violation with that code. For every graph from `broken_graphs("not_tradeable_without_reason")`: exactly one `not_tradeable_without_reason`.
- **Tests:** `test_validate_requires_payoff_on_market`, `test_validate_requires_reason_on_not_tradeable` — both listed in [`validity.md`](validity.md)'s rule table, which owns the codes and the wording of the messages. **Stack 02.**

---

## ANTI-PATTERNS

1. **Do not write a vibe where a claim belongs.** "Tensions ease", "sentiment improves", "the market reacts" — because nothing can ever settle them, so the likelihood on them can never be scored and the whole audit trail dead-ends. **Instead:** name the test, name who applies it, name the date. If you cannot, the claim is not ready to be on the map.

2. **Do not pack two claims into one proposition.** "Hormuz opens and Brent falls" — because no single source settles a conjunction on a single date, and because the relationship between the two halves is exactly the thing the map exists to show. **Instead:** two propositions and a link between them, with the mechanism written on the link.

3. **Do not let the model mint identifiers.** Because identifiers invented per generation collide the moment two branches fork from the same base. **Instead:** the model refers to propositions by claim text and by position within its own proposal, and our code mints the identifier and passes it in — see [`validity.md`](validity.md), which owns identifiers.

4. **Do not let a chain end in prose.** Because a map that finishes with "and therefore oil is cheaper" is an essay with boxes drawn on it. **Instead:** every ending is `market` with a `payoff`, or `not_tradeable` with a sentence saying why (INV-9).

5. **Do not silently repair a broken proposal** — dropping a blank resolution, inventing a payoff, downgrading a terminal to an event — because the user can then no longer tell what the model said from what we quietly fixed. **Instead:** return the violations and show them; [`validity.md`](validity.md) owns this argument and the re-prompt that follows.

---

## Open questions

*Raised 2026-09-16.*

1. **`Payoff.magnitude` units.** Currently "the expected move as a fraction". Is that (a) a move in the instrument's price, (b) a return on the position, or (c) a position size? The thesis card's `legs` (stack 05) need one answer, and B2 above has to use two different readings to describe two ordinary terminals.
   **Decided 2026-09-17:** none of the three, because the field is gone. `Payoff` becomes two shapes — a contract payoff and a price payoff, told apart by `kind`. A price payoff carries `move`, which is reading (a): a fractional move in the instrument's price. Reading (b) needs an entry price, and prices belong to the grounding layer, not the domain. A contract payoff carries no size at all: its side is `yes` or `no`, and what it costs is the live quote. See decision record 0013.
2. **Should `Payoff` name its venue?** Decision record 0010 puts venue, `as_of` and a link on the grounding layer's quote, not on the domain. A terminal that names "a Polymarket contract" without saying which one is weaker than INV-9 implies.
   **Decided 2026-09-17:** yes, for a contract. `ContractPayoff` carries `venue`, `contract_id` and `title` — which contract you would trade is *identity*, and identity is what the domain is for. `as_of`, the price and the spread stay on the grounding layer's market belief, exactly as decision record 0010 has them. See decision record 0013.
3. **A `Source` type.** A link's sources are a named `Source` type ([`link.md`](link.md) owns it). Here, `BaseRate.sources` and `Evidence.url` are plain web-address strings. If `Source` becomes a record — title, publisher, date retrieved — do these two adopt it?
4. **A resolve-by date in the past.** Checkable in principle, but the domain reads no clock (decision record 0003), so `validate` cannot see "today". Does the check live in `engine/`, and is a stale date a violation or a warning?
5. **A payoff on a non-market proposition.** There is no violation code for it, so it is currently legal and meaningless. Add `payoff_on_non_market`, or leave it alone?
6. **"Falsified if".** The Inspector requirement (FR-10 in `PRODUCT_REQUIREMENTS.md` §6) promises a "falsified if" line, and there is no field for it. Is it derived from `resolution.criteria` (no new field), or does the model write it?
