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

**Which number.** A claim's likelihood is *the chance the claim comes true*. An
ending whose payoff takes the **no** side makes money when the claim **fails**,
and the venue's no outcome is a separate contract that pays out in exactly that
case. So a no-side ending is priced on *one minus* the claim's number, with its
range turned over with it — the low end of *false* is one minus the high end of
*true*. One function works that out, `what_this_side_pays_on`, and everything
downstream reads its answer: both edges, the break-even, the band and the rule
about the model's own range. Four places each remembering to turn a number over
is four places one of them can forget.

**Which price.** A venue shows a best bid, what somebody will pay you, and a best
offer, what somebody will sell to you for. **You buy at the offer and sell at the
bid**, so there are two edges, and the venue's fee is the only cost term:

> edge of buying = what this side pays on, minus the offer, minus the fee
>
> edge of selling = the bid, minus what this side pays on, minus the fee

There is no half-the-spread term anywhere: the spread is already inside the two
prices, and subtracting it again counts it twice. The midpoint between them is
shown because it is the number a reader recognises, and it is never traded
against. When neither edge is positive that is a complete answer rather than a
gap: the number sits inside the venue's own bid and offer, fees included.

**Which contract.** The prices have to be *this ending's* prices. A quote read
from a venue is checked against the payoff — same venue, same market, same side —
and a mismatch is said out loud rather than priced, because it is a broken promise
between our own pieces of code and not anything a reader did. A price the reader
typed carries no venue and no identifiers, so there is nothing to match: it is
taken to be for this ending's own side, which is the side they were looking at
when they typed it.

**The break-even** is that same number moved by the fee, one step each way: worth
buying below it less the fee, worth selling above it plus the fee. Those two bound
the price you would actually pay or receive, not the midpoint. The stretch between
them is the **no-trade band**, and more fee makes it *wider*. It needs no quote,
which is why it is what a card prints when there is none.

**The fee is a price, not a rate.** It is in the same units as a price — a fee of
`0.01` is one cent per contract — and it is subtracted flat from both sides. And
it may be **unknown**, which is not the same as nothing: nobody has read the
venue's schedule, so a caller says `None` out loud and every answer this file
builds carries that absence as a field, so a card cannot print a number without
its caveat.

**A refusal is a value, not an exception.** Every case this file can meet has a
defined answer: an edge, or a named refusal carrying the sentence the card prints
and a break-even where one exists.

What this file must never do
----------------------------
- Never read the compared number from anywhere but `base`, and never rebuild it
  from the mixture below.
- Never compute an edge against the midpoint, and never subtract the spread twice.
- Never price a claim against a quote for another contract, another venue or the
  other side of the same contract.
- Never set a no-side price against the chance the claim comes true. That is two
  different questions differenced, one layer below the trap the two required
  worlds exist to close.
- Never treat an unknown fee as a fee of nothing without saying so.
- Never blank or zero a card because there is no quote, and never treat a negative
  edge as a failure: *the venue is paying more for this than we think it is worth*
  is a complete answer whose other side is a trade.
- Never call the gap between the model's number and the reader's own an edge. That
  is the argument the reader is having with the tool.
- Never read a stored number for a claim an edit has pinned. The rules layer says
  no surface may print one, and the mixture below looks at a world's own record of
  what it pinned before it reads anything.
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Assignment, Belief, BranchId, ContractPayoff, PropositionId, World
from katalyst.grounding import Quote

FEE = (
    "What the venue charges on one filled trade, in the same units as a price: a fee of "
    "0.01 is one cent per contract, subtracted flat from both sides. **None means nobody "
    "has read the venue's fee schedule**, so the arithmetic here is before fees and "
    "whatever reads this must say so rather than printing a number that looks net."
)
"""What the fee means, written once because three shapes carry it and must agree.

It is a **price**, not a rate. A rate would be a share of the amount and would
have to be multiplied by something before it could be subtracted; this is
subtracted as it stands. Whoever reads the venue's schedule next passes cents,
not a percentage, and the three descriptions below say so in the same words.
"""


def what_this_side_pays_on(model: Belief, side: str) -> Belief:
    """The likelihood the side of the trade actually pays on, with its range.

    **The one place a side is turned over.** A claim's likelihood is the chance the
    claim comes **true**. An ending whose payoff takes the `no` side makes money
    when the claim **fails**, and the venue's no outcome is a separate contract
    paying out in exactly that case, so its price stands against *one minus* the
    claim's number. The range turns over with it: the low end of *false* is one
    minus the high end of *true*.

    Everything that needs that number asks here — both edges, the break-even, the
    band, and the rule about the model's own range — because four places each
    remembering to turn a number over is four places one of them can forget.

    Args:
        model: The model's likelihood for the claim, read from the world with
            nothing fixed by an edit.
        side: Which side of the contract the ending takes: `yes` pays when the
            claim comes true, `no` when it fails.

    Returns:
        The same likelihood on a yes side, and one minus it with its range turned
        over on a no side. Owned by the model either way, because it is the model's
        own number read the other way round and not somebody else's.
    """
    if side == "yes":
        return model
    return Belief(p=1.0 - model.p, lo=1.0 - model.hi, hi=1.0 - model.lo, owner=model.owner)


class BreakEven(BaseModel):
    """The two prices this side's own number sets, once the venue's fee is paid.

    Below the first it is worth buying; above the second it is worth selling. The
    stretch between them is the **no-trade band** — the prices at which neither
    side is worth taking — and paying more in fees makes it wider, never narrower.

    These bound the price you would **actually pay or receive** — the offer if you
    are buying, the bid if you are selling — and never the midpoint between them.

    On an ending that takes the **no** side the number they are built from is one
    minus the claim's, because that is what a no contract pays on.
    """

    model_config = ConfigDict(frozen=True)

    buy_below: float = Field(
        description="Worth buying at any offer below this: what this side pays on, less the fee."
    )
    sell_above: float = Field(
        description="Worth selling at any bid above this: what this side pays on, plus the fee."
    )
    fee: float | None = Field(description=FEE)


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

    **The two readings are ordinary stored likelihoods, so they mean something only
    for a claim no edit has pinned.** A claim a supposition is holding over reads
    exactly 1, or exactly 0 when it was supposed false — a number that is there so
    a chain has a factor for it and that no surface may print. Ask for a mixture on
    the very claim the reader supposed and the two terms weigh to the unsupposed
    number **exactly**, by arithmetic and not by explanation, which would make this
    shape claim the one thing the paragraph above says it never claims. So there is
    no mixture in that case at all.
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
            "Which branch the first reading came from, as whoever built that world wrote "
            "it in. None means nobody wrote one in."
        )
    )
    world_otherwise: BranchId | None = Field(
        description="Which branch the second reading came from."
    )


class Edge(BaseModel):
    """The number this side of a trade pays on, against the two prices a venue is showing.

    Built by `priced` and by nothing else, which is what makes *which world the
    number came from* a fact about the type rather than a rule a caller has to
    remember.

    The two edges are the ones worth taking on each side. The card shows whichever
    is positive; when neither is, the number sits inside the venue's own bid and
    offer with fees paid, and *no edge at this price* is the whole answer.

    Two numbers, not one, and they differ on a no-side ending: `model` is the
    claim's own likelihood — the chance it comes **true**, which is what the tile
    shows — and `pays_on` is what this side of the contract actually pays on. On a
    yes side they are the same number; on a no side `pays_on` is one minus it, with
    its range turned over.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim this edge is about.")
    model: Belief = Field(
        description=(
            "The claim's own likelihood — the chance it comes true — read from the world "
            "with nothing fixed by an edit, range and all. Never from the world on screen."
        )
    )
    pays_on: Belief = Field(
        description=(
            "The likelihood this side of the contract pays on, which is what the prices "
            "below are set against. The same as the claim's number on a yes-side ending; "
            "one minus it, range turned over, on a no-side one."
        )
    )
    quote: Quote = Field(description="The venue's two prices, and everything they came with.")
    fee: float | None = Field(description=FEE)
    buying: float = Field(
        description=(
            "What buying is worth: what this side pays on, less the offer you would buy at, "
            "less the fee. Negative means buying is not worth it at this price."
        )
    )
    selling: float = Field(
        description=(
            "What selling is worth: the bid you would sell at, less what this side pays on, "
            "less the fee. Negative means selling is not worth it at this price."
        )
    )
    break_even: BreakEven = Field(
        description="The two prices this side's own number sets, and the band between them."
    )
    inside_the_model_range: bool = Field(
        description=(
            "True when an edge is worth taking at one end of the model's own stated range "
            "and not at the other — the gap is smaller than how unsure the model is of its "
            "own number. Such an edge is shown with its reason, and neither headlined nor "
            "ranked."
        )
    )
    base_branch: BranchId | None = Field(
        description=(
            "The branch the compared number's world was built from. None means the "
            "untouched map. Anything else means the reader has edited the map — no value "
            "was fixed, which is refused, but an arrow may have been retuned or a claim "
            "added — and the card says the number comes from an edited map."
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
    fee: float | None = Field(description=FEE)
    break_even: BreakEven | None = Field(
        default=None,
        description=(
            "The two prices this side's own number sets, where the claim names a contract. "
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
    "instead: the number this side pays on, moved by the fee."
)
"""What the card prints on a contract ending with no quote in hand."""

MARKET_HAS_SETTLED = (
    "This market is not open to orders, so there is nothing to trade on it. Here is the "
    "break-even instead: the number this side pays on, moved by the fee."
)
"""What the card prints when the venue's own flags say no order could be placed.

Read from the flags — all four of them — and never from the price: a settled
market keeps serving a plausible book, and the one this repository saved reads
0.999 against 1.00.
"""

A_QUOTE_FOR_SOMETHING_ELSE = (
    "this claim's ending names {wanted}, and the quote handed in is for {got}. A price is "
    "only an edge against the contract and the side it was read for, so the two have to be "
    "the same thing before they can be differenced."
)
"""What is said when a quote is not the quote for this ending.

A broken promise between our own pieces of code rather than anything a reader
did — whatever fetched the quote fetched the wrong one — so it is raised, the way
a claim that is not on the map is, and never turned into a refusal a reader cannot
act on.
"""


def priced(
    base: World,
    shown: World,
    claim: PropositionId,
    quote: Quote | None,
    *,
    fee: float | None,
    otherwise: World | None = None,
) -> Edge | NotComparable:
    """Set the number one side of a trade pays on against a venue's prices, or say why not.

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
    | The same, with a quote no order could be placed on | `settled_market`, and the break-even |
    | An ending naming a contract, a live quote, `base` clean | an **edge** |

    A branch that only *adds* a claim, or retunes an arrow, fixes no value, so it
    passes the first row: nothing is pinned and the map is merely larger or
    differently drawn. The edge that comes back says which branch its number was
    read from, so a card can tell the reader the map was edited.

    **Which side.** A yes-side ending is priced on the chance the claim comes true;
    a no-side ending on one minus it, range turned over. A quote read from a venue
    must be for this ending's venue, market and side, and is refused out loud when
    it is not. A price the reader typed names no venue, so there is nothing to
    match: it is taken to be for this ending's own side.

    Args:
        base: The world with nothing fixed by an edit. The number is read from here
            and from nowhere else.
        shown: The world the reader is looking at, which may be a branch world. Read
            only for the mixture below; never for the compared number.
        claim: The claim to price.
        quote: The venue's two prices for it, or nothing at all when none has been
            read.
        fee: What the venue charges on one filled trade, in the same units as a
            price, or **None** when nobody has read the venue's schedule. Required,
            with no default, so that an unknown fee is said rather than assumed; it
            is carried through to everything this returns.
        otherwise: The world in which the reader's supposition goes the **other**
            way, when a card wants the mixture that explains the supposed reading.
            Leaving it out leaves the mixture out.

    Returns:
        One edge, or one named refusal carrying the sentence the card prints and a
        break-even where the claim names a contract.

    Raises:
        ValueError: If the claim is not on the base world's map, if a venue's quote
            is not for this ending's contract and side, or if `otherwise` is not the
            world where the one thing `shown` supposes goes the other way. All three
            are broken promises between our own pieces of code rather than anything
            a reader did, so they are said out loud rather than turned into a
            refusal a reader cannot act on.
    """
    if base.assignments:
        return NotComparable(
            claim=claim, reason="conditional_world", sentence=A_VALUE_IS_FIXED, fee=fee
        )

    proposition = next((one for one in base.graph.propositions if one.id == claim), None)
    if proposition is None:
        raise ValueError(
            f"the claim '{claim}' is not on this map, so there is nothing here to price"
        )

    payoff = proposition.payoff
    if proposition.kind == "not_tradeable":
        said = proposition.not_tradeable_reason or NO_TRADE_NAMED
        return NotComparable(claim=claim, reason="no_contract", sentence=said, fee=fee)
    if payoff is None:
        return NotComparable(claim=claim, reason="no_contract", sentence=NO_TRADE_NAMED, fee=fee)
    if not isinstance(payoff, ContractPayoff):
        return NotComparable(
            claim=claim, reason="no_contract", sentence=NO_CONTRACT_QUOTES_IT, fee=fee
        )

    model = base.beliefs[claim]
    pays_on = what_this_side_pays_on(model, payoff.side)
    paid = fee or 0.0
    break_even = BreakEven(buy_below=pays_on.p - paid, sell_above=pays_on.p + paid, fee=fee)
    if quote is None:
        return NotComparable(
            claim=claim,
            reason="no_quote",
            sentence=NO_PRICE_READ,
            fee=fee,
            break_even=break_even,
        )
    _the_quote_is_for_this_ending(payoff, quote)
    if not quote.live:
        return NotComparable(
            claim=claim,
            reason="settled_market",
            sentence=MARKET_HAS_SETTLED,
            fee=fee,
            break_even=break_even,
        )

    return Edge(
        claim=claim,
        model=model,
        pays_on=pays_on,
        quote=quote,
        fee=fee,
        buying=pays_on.p - quote.offer - paid,
        selling=quote.bid - pays_on.p - paid,
        break_even=break_even,
        inside_the_model_range=_sign_changes_across_the_range(pays_on, quote, paid),
        base_branch=base.branch_id,
        tick=quote.tick,
        mixture=_mixture_of(base, shown, claim, otherwise),
    )


def _the_quote_is_for_this_ending(payoff: ContractPayoff, quote: Quote) -> None:
    """Check that a venue's quote is the price of the very contract and side this ending names.

    Three things have to agree — the venue, the venue's own identifier for the
    market, and which of the contract's two outcomes was priced — because a
    contract's yes and its no are separate order books and two markets at one venue
    are two different questions. A price that does not belong to this ending is a
    number on a card that cannot be traced to its source.

    A price the reader typed carries none of the three, so there is nothing to
    check: it is their report of what they can get on the ending they were looking
    at, and it is taken as being for that ending's own side.

    Args:
        payoff: What the ending says you would trade.
        quote: The price handed in.

    Raises:
        ValueError: If a venue's quote names a different venue, a different market
            or the other side of the contract.
    """
    if quote.source == "user":
        return
    wanted = (payoff.venue, payoff.contract_id, payoff.side)
    got = (quote.venue, quote.market_id, quote.side)
    if wanted != got:
        raise ValueError(
            A_QUOTE_FOR_SOMETHING_ELSE.format(
                wanted=f"{wanted[0]} market {wanted[1]}, {wanted[2]} side",
                got=f"{got[0]} market {got[1]}, {got[2]} side",
            )
        )


def _sign_changes_across_the_range(pays_on: Belief, quote: Quote, fee: float) -> bool:
    """Say whether an edge is worth taking at one end of the model's own range and not the other.

    Every claim carries the range the model stated — how unsure it is of its own
    number. Work the two edges out at the bottom of that range and again at the
    top: if either of them is worth taking at one end and not at the other, the gap
    being called an edge is smaller than the model's own uncertainty about the
    number it is made from. A product that policed a one-cent tick and ignored a
    twenty-point band would be policing what was easy.

    **Worth taking means strictly better than nothing**, so an edge of exactly
    nothing at one end and something at the other is marked. A gap you would not
    cross the spread for is not one to lead with.

    Args:
        pays_on: The likelihood this side of the trade pays on, with its range —
            already turned over on a no-side ending, so this reads one rule.
        quote: The venue's two prices.
        fee: What the venue charges on a filled trade, in the same units as a
            price, with an unknown fee already read as nothing.

    Returns:
        True when buying, or selling, is worth it at one end of the range and not
        at the other.
    """
    buying = (pays_on.lo - quote.offer - fee, pays_on.hi - quote.offer - fee)
    selling = (quote.bid - pays_on.lo - fee, quote.bid - pays_on.hi - fee)
    return _changes_sign(buying) or _changes_sign(selling)


def _changes_sign(ends: tuple[float, float]) -> bool:
    """Say whether one of two edges is worth taking and the other is not.

    Worth taking is **strictly** more than nothing: an edge of exactly nothing pays
    for nothing, so an end that reads nought sits with the ends that are not worth
    crossing the spread for rather than with the ones that are.
    """
    return (ends[0] > 0.0) != (ends[1] > 0.0)


def _mixture_of(
    base: World, shown: World, claim: PropositionId, otherwise: World | None
) -> Mixture | None:
    """Work out the terms that relate a supposed reading to the unsupposed one.

    Built only when a caller hands in the world where the supposition goes the other
    way, because there is no honest way to read that number off the two worlds an
    edge already has: working it back out of the unsupposed number would be
    assuming the very equality this explanation does not claim.

    **And only when the ending's number in both worlds is one that may be read at
    all.** The two readings come out of each world's stored likelihoods, and the
    rules layer is explicit that a claim a supposition is holding over reads exactly
    1 — or exactly 0 when it was supposed false — and that no surface may print
    that. Every reader looks at a world's own record of what it pinned first, and
    this one does too. The case it catches is an ordinary thing for a reader to do:
    suppose the very ending being priced. The mixture would then carry 1 and 0, the
    two terms would weigh to the unsupposed number **exactly**, and a card would
    show a perfect agreement that is arithmetic rather than explanation — the one
    claim this shape must never make. A mixture of *the ending supposed true*
    against *the ending supposed false* explains nothing about the ending anyway.

    Args:
        base: The world with nothing fixed. The weight is read from here.
        shown: The world the reader is looking at, which supposes exactly one thing.
        claim: The ending being explained.
        otherwise: The world where that same one thing goes the other way.

    Returns:
        The four terms and the two worlds they were read from; or nothing at all
        when no other world was handed in, or when either world has the ending
        itself pinned.

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
    # One check, not two: the pair rule above has already settled that both worlds
    # pin the same claim, so a reading the other world may not show is one this
    # world may not show either.
    if not _a_number_that_may_be_read(shown, claim):
        return None
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


def _a_number_that_may_be_read(world: World, claim: PropositionId) -> bool:
    """Say whether a world's stored likelihood for a claim is one a surface may show.

    A world names what each of a claim's days is, in one word, and only `sampled`
    means the number was worked out rather than put there. While a supposition
    holds the claim reads exactly 1 or exactly 0, and the rules layer says in as
    many words that no surface may print it; the two words a withdrawn supposition
    leaves behind are the same kind of thing. So a claim whose days are not all
    ordinary is one this file does not read a number for.

    Args:
        world: The world to read.
        claim: The claim whose number is wanted.

    Returns:
        True when every day of that claim's series is an ordinary, worked-out one.
    """
    return all(one == "sampled" for one in world.states[claim])


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
