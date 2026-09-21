"""The edge: the model's number for a claim against the price you would actually trade at.

The reader's first finance question is *what is already priced in?* This file
answers it, or says exactly why it cannot.

**Which world.** The product's central gesture changes the question. *Suppose this
is true* pins a claim and re-works the map, so the number on a tile becomes *the
chance of this ending in a world where the strait has been made to open*. A
venue's price is not that; it is the price in the world as it stands. Subtract one
from the other and you have the difference between two questions, printed as
money. So `priced` takes **two** worlds and both are required: `base`, the world
with nothing fixed by an edit, and `shown`, the world the reader is looking at.
The compared number is always read from `base`. A caller holding only a branch
world cannot build an edge at all — that is checked by the type of the function
rather than by the caller's care — and a `base` that does carry a fixed value is
refused by name.

**Which price.** A venue shows a best bid, what somebody will pay you, and a best
offer, what somebody will sell to you for. **You buy at the offer and sell at the
bid**, so there are two edges, and the venue's fee is the only cost term:

> edge of buying = model minus offer minus fee
>
> edge of selling = bid minus model minus fee

There is no half-the-spread term anywhere: the spread is already inside the two
prices, and subtracting it again counts it twice. The midpoint between them is
shown because it is the number a reader recognises, and it is never traded
against. When neither edge is positive that is a complete answer rather than a
gap: the model's number sits inside the venue's own bid and offer, fees included.

**The break-even** is the model's own number moved by the fee, one step each way:
worth buying below *the model's number less the fee*, worth selling above *the
model's number plus the fee*. Those two bound the price you would actually pay or
receive, not the midpoint. The stretch between them is the **no-trade band**, and
more fee makes it *wider*. It needs no quote, which is why it is what a card
prints when there is none.

**A refusal is a value, not an exception.** Every case this file can meet has a
defined answer: an edge, or a named refusal carrying the sentence the card prints
and a break-even where one exists.

What this file must never do
----------------------------
- Never read the compared number from anywhere but `base`, and never rebuild it
  from the mixture below.
- Never compute an edge against the midpoint, and never subtract the spread twice.
- Never blank or zero a card because there is no quote, and never treat a negative
  edge as a failure: *the venue is paying more for this than we think it is worth*
  is a complete answer whose other side is a trade.
- Never call the gap between the model's number and the reader's own an edge. That
  is the argument the reader is having with the tool.
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Assignment, Belief, BranchId, ContractPayoff, PropositionId, World
from katalyst.grounding import Quote

UNKNOWN_FEE = 0.0
"""What a venue charges on a filled trade, as a share of the amount — until somebody reads it.

Nobody has read the venue's fee schedule, so the fee every card runs on today is
**nothing**, and the card says the fee is unknown rather than saying it is zero.
That makes today's no-trade band zero-width and the break-even the model's own
number. It is honest, it is one afternoon's reading away from being better, and it
is written down here rather than buried in a default.
"""


class BreakEven(BaseModel):
    """The two prices the model's own number sets, once the venue's fee is paid.

    Below the first it is worth buying; above the second it is worth selling. The
    stretch between them is the **no-trade band** — the prices at which neither
    side is worth taking — and paying more in fees makes it wider, never narrower.

    These bound the price you would **actually pay or receive** — the offer if you
    are buying, the bid if you are selling — and never the midpoint between them.
    """

    model_config = ConfigDict(frozen=True)

    buy_below: float = Field(
        description=("Worth buying at any offer below this: the model's likelihood less the fee.")
    )
    sell_above: float = Field(
        description=("Worth selling at any bid above this: the model's likelihood plus the fee.")
    )


class Mixture(BaseModel):
    """How the supposed reading relates to the unsupposed one — an explanation, never a sum.

    After *Suppose this is true*, a reader sees the ending's number re-worked in a
    world where the supposition holds, beside an edge computed from the world where
    nothing was supposed. These are the terms that relate the two: the map's own
    chance of the supposition times the reading where it holds, plus one minus that
    chance times the reading where it does not.

    **The two terms do not add up to the unsupposed number, and nothing here claims
    they do.** Two things break the equality, and a reader needs both: a cause of
    the supposed claim may reach the ending by another route, and *Suppose this is
    true* pins a **date** as well as a truth while the unsupposed world averages
    over the days the claim might have happened. Decision record 0018 carries the
    measured size of the gap and names the script that measured it.

    So these four numbers are shown term by term as an explanation. Nothing
    computes an edge from them.
    """

    model_config = ConfigDict(frozen=True)

    supposed: PropositionId = Field(description="The claim the reader supposed.")
    weight_supposed: float = Field(
        description=(
            "How much the reader's supposition weighs: the map's own chance of that claim "
            "coming out the way they supposed it, read from the world with nothing fixed."
        )
    )
    weight_otherwise: float = Field(
        description="One minus the weight above. The two always sum to one."
    )
    reading_supposed: float = Field(
        description="The ending's likelihood in the world the reader is looking at."
    )
    reading_otherwise: float = Field(
        description="The ending's likelihood in the world where the same claim goes the other way."
    )
    world_supposed: BranchId | None = Field(
        description=(
            "Which branch the first reading came from. None means the untouched map, "
            "which cannot happen here: a supposition is an edit."
        )
    )
    world_otherwise: BranchId | None = Field(
        description="Which branch the second reading came from."
    )


class Edge(BaseModel):
    """The model's number for one claim against the two prices a venue is really showing.

    Built by `priced` and by nothing else, which is what makes *which world the
    number came from* a fact about the type rather than a rule a caller has to
    remember.

    The two edges are the ones worth taking on each side. The card shows whichever
    is positive; when neither is, the model's number sits inside the venue's own
    bid and offer with fees paid, and *no edge at this price* is the whole answer.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim this edge is about.")
    model: Belief = Field(
        description=(
            "The model's likelihood for that claim, read from the world with nothing fixed "
            "by an edit, range and all. Never from the world on screen."
        )
    )
    quote: Quote = Field(description="The venue's two prices, and everything they came with.")
    fee: float = Field(
        description=(
            "What the venue charges on a filled trade, as a share of the amount. Nothing "
            "today, because the schedule has not been read, and the card says so."
        )
    )
    buying: float = Field(
        description=(
            "What buying is worth: the model's likelihood, less the offer you would buy at, "
            "less the fee. Negative means buying is not worth it at this price."
        )
    )
    selling: float = Field(
        description=(
            "What selling is worth: the bid you would sell at, less the model's likelihood, "
            "less the fee. Negative means selling is not worth it at this price."
        )
    )
    break_even: BreakEven = Field(
        description="The two prices the model's own number sets, and the band between them."
    )
    inside_the_model_range: bool = Field(
        description=(
            "True when an edge changes sign between the two ends of the model's own stated "
            "range — the gap is smaller than how unsure the model is of its own number. "
            "Such an edge is shown with its reason and is neither headlined nor ranked."
        )
    )
    tick: float | None = Field(
        description=(
            "The smallest price step the venue trades in, carried so a card can refuse to "
            "call a gap narrower than one step an edge."
        )
    )
    mixture: Mixture | None = Field(
        default=None,
        description=(
            "The terms relating the supposed reading to this one, when the reader has "
            "supposed something and the other world was worked out. An explanation that "
            "never computes the edge. None otherwise."
        ),
    )


NotComparableReason = Literal["conditional_world", "no_contract", "no_quote", "settled_market"]
"""Every reason an edge cannot be built, as a closed list.

`conditional_world` — a value on the map was fixed by an edit, so the model's
number answers a different question from the venue's price. `no_contract` —
nothing on this claim names a contract somebody quotes. `no_quote` — it names one
and no price has been read. `settled_market` — it names one and that market has
finished.
"""


class NotComparable(BaseModel):
    """Why an edge could not be built here, and the most useful thing to say instead.

    A refusal is a value rather than an error, and it is never a blank row: it
    carries the sentence the card prints and, where the claim names a contract, the
    break-even — which needs no quote and is the honest answer when there is none.

    A claim that names **no** contract gets no break-even. The price at which a
    position in an instrument is worth nothing needs an entry price, and the entry
    price is on the reader's own position, which arrives later.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim there is no edge for.")
    reason: NotComparableReason = Field(description="Which of the four cases this is.")
    sentence: str = Field(description="What the card prints, in plain words a reader can act on.")
    break_even: BreakEven | None = Field(
        default=None,
        description=(
            "The two prices the model's own number sets, where the claim names a contract. "
            "None where it names no contract at all."
        ),
    )


NO_TRADE_NAMED = "Nothing on this claim names a trade, so there is no price to compare it with."
"""What the card prints on the claim the map starts from, or on a step in the middle."""

NO_CONTRACT_QUOTES_IT = "No contract quotes this claim — edge not calculable."
"""What the card prints on an ending that names an instrument rather than a contract.

Something traded moves when the claim's answer changes, but no venue asks the
claim's own question, so there is no price on *this claim* to compare the model's
number with. The break-even for a trade like that is a price rather than a
likelihood, and it needs the entry price on the reader's own position.
"""

A_VALUE_IS_FIXED = (
    "A value on this map has been fixed — by Suppose this is true, or by This happened — so "
    "the number on this claim answers a different question from the venue's price. An edge is "
    "read from the map with nothing fixed."
)
"""What the card prints when the wrong world was handed in.

One rule, not two: **either** button makes the world unfit to price against. The
cost, accepted deliberately: a reader who records a real, public fact loses the
edge on that map until they start again from one without it, even though a quote
taken afterwards already reflects that fact.
"""

NO_PRICE_READ = (
    "No price has been read for this contract, so there is no edge. Here is the break-even "
    "instead: the model's own number, moved by the fee."
)
"""What the card prints on a contract ending with no quote in hand."""

MARKET_HAS_SETTLED = (
    "This market has settled, so there is nothing left to trade on it. Here is the break-even "
    "instead: the model's own number, moved by the fee."
)
"""What the card prints when the venue's own flags say the market has finished.

Read from the flags and never from the price: a settled market keeps serving a
plausible book, and the one this repository saved reads 0.999 against 1.00.
"""


def priced(
    base: World,
    shown: World,
    claim: PropositionId,
    quote: Quote | None,
    *,
    fee: float = UNKNOWN_FEE,
    otherwise: World | None = None,
) -> Edge | NotComparable:
    """Set the model's number for one claim against a venue's prices, or say why it cannot be.

    **The only way an edge is built.** Both worlds are required, so a caller holding
    only the world on screen has to go and work out the world with nothing fixed
    first; and the compared number is always read from that first world, never from
    the second.

    Every case has a defined answer:

    | The case | What comes back |
    |---|---|
    | `base` carries any value fixed by an edit | `conditional_world` |
    | The claim names no trade — the map's starting claim, a step in the middle | `no_contract` |
    | An ending that says it cannot be traded | `no_contract`, printing its own reason |
    | An ending naming an instrument, quote or no quote | `no_contract`, and **no** break-even |
    | An ending naming a contract, no quote in hand | `no_quote`, **and** the break-even |
    | The same, with a quote whose market has finished | `settled_market`, and the break-even |
    | An ending naming a contract, a live quote, `base` clean | an **edge** |

    A branch that only *adds* a claim fixes no value, so it passes the first row:
    nothing is pinned, the map is merely larger.

    Args:
        base: The world with nothing fixed by an edit. The model's number is read
            from here and from nowhere else.
        shown: The world the reader is looking at, which may be a branch world. Read
            only for the mixture below; never for the compared number.
        claim: The claim to price.
        quote: The venue's two prices for it, or nothing at all when none has been
            read.
        fee: What the venue charges on a filled trade, as a share of the amount.
            Nothing by default, because nobody has read the schedule.
        otherwise: The world in which the reader's supposition goes the **other**
            way, when a card wants the mixture that explains the supposed reading.
            Leaving it out leaves the mixture out.

    Returns:
        One edge, or one named refusal carrying the sentence the card prints and a
        break-even where the claim names a contract.

    Raises:
        ValueError: If the claim is not on the base world's map, or if `otherwise`
            is not the world where the one thing `shown` supposes goes the other
            way. Both are broken promises between our own pieces of code rather
            than anything a reader did, so they are said out loud rather than
            turned into a refusal a reader cannot act on.
    """
    if base.assignments:
        return NotComparable(claim=claim, reason="conditional_world", sentence=A_VALUE_IS_FIXED)

    proposition = next((one for one in base.graph.propositions if one.id == claim), None)
    if proposition is None:
        raise ValueError(
            f"the claim '{claim}' is not on this map, so there is nothing here to price"
        )

    payoff = proposition.payoff
    if proposition.kind == "not_tradeable":
        said = proposition.not_tradeable_reason or NO_TRADE_NAMED
        return NotComparable(claim=claim, reason="no_contract", sentence=said)
    if payoff is None:
        return NotComparable(claim=claim, reason="no_contract", sentence=NO_TRADE_NAMED)
    if not isinstance(payoff, ContractPayoff):
        return NotComparable(claim=claim, reason="no_contract", sentence=NO_CONTRACT_QUOTES_IT)

    model = base.beliefs[claim]
    break_even = BreakEven(buy_below=model.p - fee, sell_above=model.p + fee)
    if quote is None:
        return NotComparable(
            claim=claim, reason="no_quote", sentence=NO_PRICE_READ, break_even=break_even
        )
    if not quote.live:
        return NotComparable(
            claim=claim, reason="settled_market", sentence=MARKET_HAS_SETTLED, break_even=break_even
        )

    return Edge(
        claim=claim,
        model=model,
        quote=quote,
        fee=fee,
        buying=model.p - quote.offer - fee,
        selling=quote.bid - model.p - fee,
        break_even=break_even,
        inside_the_model_range=_sign_changes_across_the_range(model, quote, fee),
        tick=quote.tick,
        mixture=_mixture_of(base, shown, claim, otherwise),
    )


def _sign_changes_across_the_range(model: Belief, quote: Quote, fee: float) -> bool:
    """Say whether an edge changes sign between the two ends of the model's own range.

    Every claim carries the range the model stated — how unsure it is of its own
    number. Work the two edges out at the bottom of that range and again at the
    top: if either of them is worth taking at one end and not at the other, the gap
    being called an edge is smaller than the model's own uncertainty about the
    number it is made from. A product that policed a one-cent tick and ignored a
    twenty-point band would be policing what was easy.

    Args:
        model: The model's likelihood with its range, read from the base world.
        quote: The venue's two prices.
        fee: What the venue charges on a filled trade.

    Returns:
        True when buying, or selling, is worth it at one end of the range and not
        at the other.
    """
    buying = (model.lo - quote.offer - fee, model.hi - quote.offer - fee)
    selling = (quote.bid - model.lo - fee, quote.bid - model.hi - fee)
    return _changes_sign(buying) or _changes_sign(selling)


def _changes_sign(ends: tuple[float, float]) -> bool:
    """Say whether one of two numbers is below zero and the other is not."""
    return (ends[0] < 0.0) != (ends[1] < 0.0)


def _mixture_of(
    base: World, shown: World, claim: PropositionId, otherwise: World | None
) -> Mixture | None:
    """Work out the terms that relate a supposed reading to the unsupposed one.

    Built only when a caller hands in the world where the supposition goes the other
    way, because there is no honest way to read that number off the two worlds an
    edge already has: working it back out of the unsupposed number would be
    assuming the very equality this explanation does not claim.

    Args:
        base: The world with nothing fixed. The weight is read from here.
        shown: The world the reader is looking at, which supposes exactly one thing.
        claim: The ending being explained.
        otherwise: The world where that same one thing goes the other way.

    Returns:
        The four terms and the two worlds they were read from, or nothing at all
        when no other world was handed in.

    Raises:
        ValueError: If the two worlds are not a pair: one supposition each, on the
            same claim, one true and one false.
    """
    if otherwise is None:
        return None
    here = _the_one_supposition(shown, "the world on screen")
    there = _the_one_supposition(otherwise, "the world handed in as the other way round")
    if here.target != there.target or here.value == there.value:
        raise ValueError(
            "the mixture explains one supposition going both ways, so the two worlds must "
            f"suppose the same claim in opposite directions; got '{here.target}' "
            f"supposed {here.value} against '{there.target}' supposed {there.value}"
        )
    chance = base.beliefs[here.target].p
    weight = chance if here.value else 1.0 - chance
    return Mixture(
        supposed=here.target,
        weight_supposed=weight,
        weight_otherwise=1.0 - weight,
        reading_supposed=shown.beliefs[claim].p,
        reading_otherwise=otherwise.beliefs[claim].p,
        world_supposed=shown.branch_id,
        world_otherwise=otherwise.branch_id,
    )


def _the_one_supposition(world: World, called: str) -> Assignment:
    """Find the single supposition a world holds, and refuse anything else.

    Args:
        world: The world to read.
        called: What to call it in the complaint, so a reader of the failure knows
            which of the two worlds was wrong.

    Returns:
        The one value that world's edits fixed.

    Raises:
        ValueError: If it fixed no value, more than one, or one by *This happened*
            rather than by *Suppose this is true*. The mixture has two terms, so it
            explains one supposition and not a branch full of them.
    """
    fixed: Sequence[Assignment] = world.assignments
    if len(fixed) != 1 or fixed[0].kind != "do":
        raise ValueError(
            f"the mixture explains one supposition, so {called} must fix exactly one value "
            f"and fix it by supposing; this one fixed {len(fixed)}"
        )
    return fixed[0]
