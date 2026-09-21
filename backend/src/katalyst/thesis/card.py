"""The card: the thesis a reader carries away, with an owner on every number.

The last step of the walk is a thesis the reader can take with them — what
carries it, what is priced in, what takes them out, what to watch, what they
typed, and what it does not know. This file builds that as data. `export.py`
turns it into a document a program can read and a page a person can read.

**The card assembles; it computes nothing another module owns.** Every number on
it was worked out by the module whose subject it is — the edge by `edge.py`, the
first-touch shares by `position.py`, the rail by `lift.py`, the greyed ceiling by
`ceiling.py`, the shift by whatever owns the map's own verdict — and handed in.
One rule, and it is what keeps a card from becoming a second place any of that
arithmetic lives.

**Every number says who it belongs to.** A card holds no bare numbers at all: each
one is a `Figure` carrying its value, its owner — the reader, the model, a venue,
or a computation over the drawn worlds — what it is in plain words, and where it
came from. That is a shape rather than a rule to remember, so no screen and no
document can print a figure from this card without being handed its owner at the
same time.

**No array ever reaches a card.** The shapes underneath carry one row per drawn
world: fifty thousand worlds by twenty claims is a million numbers, and a card is
something a person reads. Whatever this file needs out of a sample of worlds it
reads as a share, a count or a day, and leaves the arrays where they are.

**Two kinds of ending are ranked by two rules, said out loud.** An ending a venue
quotes is ranked by the size of its edge, whichever side it favours; an ending
naming an instrument is ranked by the shift the hypothesis makes to it, times the
move its payoff names. An edge in cents and a move in per cent are not the same
quantity and there is no honest exchange rate between them, so there are two
ranked lists and every row says which rule put it where.

**A price ending is a first-class trade.** The recorded map the walk opens has
eleven tradeable endings and every one names an instrument rather than a venue
contract. If a card only worked on contracts the walk's last three steps would
have to change maps halfway through, so an instrument ending carries a position,
first touch, both computed lists, the break-even its own entry price makes
computable, and the honest line *no contract quotes this claim — edge not
calculable*.

What this file must never do
----------------------------
- Never compute a number another module owns. It is handed the edge, the shares,
  the rail, the ceiling and the shift, and it arranges them.
- Never put a number on a card without its owner. There is no way to: a card
  holds `Figure`s, and a `Figure` cannot be built without one.
- Never merge the model's number, the reader's and a venue's. They sit in
  different figures, and the card never subtracts one from another — the one
  difference this product draws is the edge, and `edge.py` draws it.
- Never rank a contract ending against an instrument ending on one number.
- Never headline an average outcome. The tails are rows of their own, ranked by
  what they would do to the position, and an average is exactly what hides them.
- Never attach a probability to a shock the reader placed. They supposed it; that
  is not a forecast, and the shape here has no field one could go in.
- Never let an array or a whole world onto the card.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import (
    Belief,
    BranchId,
    ContractPayoff,
    Payoff,
    PricePayoff,
    Proposition,
    PropositionId,
    World,
)
from katalyst.thesis.ceiling import Ceiling
from katalyst.thesis.draws import THE_SAMPLE_SAYS, SampleFrom
from katalyst.thesis.edge import Edge, Mixture, NotComparable, NotComparableReason
from katalyst.thesis.lift import WhatTakesYouOut
from katalyst.thesis.paths import MarketChanceFrom
from katalyst.thesis.position import FirstTouch, Position, Refusal, Side, Trades

Owner = Literal["reader", "model", "venue", "computed"]
"""Who a number on the card belongs to, as a closed list of four.

`reader` — they typed it. `model` — the language model stated it, and nobody has
calibrated it. `venue` — a market published it. `computed` — this program worked
it out over the drawn worlds or from numbers above. Every figure on a card names
exactly one of the four, and no two are ever merged into a third.
"""

OWNER_SAYS: Mapping[Owner, str] = {
    "reader": "yours",
    "model": "the model's",
    "venue": "the venue's",
    "computed": "computed",
}
"""What each owner is called on screen, written once so two renderings agree."""

THE_CHANCE_CAME_FROM: Mapping[MarketChanceFrom, str] = {
    "venue_quote": "a venue's quote on that claim",
    "model": "the model's own number",
    "reader": "a chance the reader typed",
}
"""What each source of the market's chance of a claim is called, in plain words.

A first-touch number is read off a price path, and the path applies only what the
market has not already priced. How much that is depends on where the market's
chance came from, so the words appear in the same sentence as the number.
"""

NOT_ADVICE = "Educational, not investment advice, and not a recommendation."
"""The one line that says what this document is not.

Carried as a field rather than printed in a footer, because a footer is dropped by
whatever reads the document next and a field has to be read.
"""

EXECUTION = "A stop order's trigger is not its fill price."
"""The one thing this product will say about getting out, and nothing else.

This is not an execution layer: it names no order type, routes nothing, and
guarantees no fill. The sentence is here because a reader who types a stop and
believes it is a price they will get has been misled by our silence.
"""

REFUSES: tuple[str, ...] = (
    "This document names no order type and guarantees no fill price.",
    "The stop is the reader's own price rule, never derived by this tool.",
    "No size here is a recommendation, and the greyed ceiling is a limit nobody may size to.",
    "Every probability is the model's, uncalibrated, under the stated map and seed.",
    "Impact sizes are the model's statements, not measured from data.",
    (
        "The path applies only what the market has not already priced, at a market chance "
        "whose source is named on each claim."
    ),
    "Quotes are as of the dates shown and were not refreshed.",
    "The map is not exhaustive, and risks outside it are not represented.",
)
"""What this card does not know, in full sentences, carried as data.

Eight limits, each one a thing a reader could otherwise take the card to be
claiming. They are a field on the card and a field in the export, so a program
that ingests the document ingests them with it.
"""

TWO_RULES = (
    "Two kinds of ending are ranked by two rules, never blended into one number: an ending "
    "a venue quotes is ranked by the size of its edge, whichever side it favours; an ending "
    "naming an instrument is ranked by the shift the hypothesis makes to it, times the move "
    "its payoff names. An edge in cents and a move in per cent are not the same quantity."
)
"""Why there are two ranked lists rather than one, said on the card itself."""

A_SHOCK_HAS_NO_PROBABILITY = (
    "You supposed this, and supposing something is not a statement about how likely it is. "
    "The change to the position is shown; how likely it is remains yours to judge."
)
"""What is printed beside a shock the reader placed, in place of a probability."""

A_PRICE_YOU_ENTERED = "against a price you entered"
"""What stands where a venue's name would, on an edge against a price the reader typed.

Their price is their report of what they believe they could deal at. It is not a
venue's number, it never fills the market's slot, and the card says so on the same
line rather than letting a typed price read as a published one.
"""

THE_MIXTURE_EXPLAINS = (
    "These four terms explain how the reading you are looking at relates to the one the edge "
    "was computed from. They are an explanation with a measured residual: they do not add up "
    "to the unsupposed number, and nothing here claims they do."
)
"""What the mixture is, and what it is not, printed with it."""

NO_EDGE_AT_THIS_PRICE = (
    "No edge at this price: the number this side pays on sits inside the venue's own bid "
    "and offer, fees included."
)
"""What is printed when neither side of the trade is worth taking."""

NARROWER_THAN_A_TICK = (
    "The gap is smaller than the smallest price step the venue trades in, so it is not a "
    "gap anybody could take."
)
"""Why an edge is ranked but not led with."""

INSIDE_THE_MODEL_RANGE = (
    "The edge is worth taking at one end of the model's own stated range and not at the "
    "other, so the gap is smaller than the model's own uncertainty about the number it is "
    "made from."
)
"""Why an ending is left out of the ranking altogether."""

NO_SHIFT_WAS_WORKED_OUT = (
    "Nothing has worked out how much the hypothesis moves this ending, so there is no "
    "number to rank it by."
)
"""Why an instrument ending is left out of the ranking."""

NOTHING_WAS_PRICED = (
    "Nothing was priced for this ending, so there is no edge to rank it by and no refusal "
    "to explain why."
)
"""Why a contract ending nobody asked about is left out of the ranking.

Different from a refusal: a refusal is an answer about this ending, and this is
the absence of one. A reader can act on the difference — ask for a price — so it
is said rather than left as a gap in a list.
"""

THE_BARRIER_SHIFT = (
    "First touch is read by walking a daily path through each drawn world. A daily check "
    "misses touches between closes, so each level is moved toward the entry price by the "
    "standard barrier shift, and a daily count then says what watching continuously would "
    "have found."
)
"""How the two first-touch shares were arrived at, printed wherever they are."""


class Figure(BaseModel):
    """One number on the card, with who it belongs to and where it came from.

    The card holds no bare numbers. A figure cannot be built without an owner, so
    no screen and no document can print one without being handed the owner in the
    same breath — which is the shape this repository prefers to a rule a renderer
    has to remember.

    `lo` and `hi` are the range around the number where one exists: the model's
    own stated range on a likelihood, or the interval on a measured share. They
    are absent where no range was stated, which is different from a range of zero
    width.
    """

    model_config = ConfigDict(frozen=True)

    value: float = Field(description="The number itself, at full precision. A rendering rounds.")
    owner: Owner = Field(
        description=(
            "Whose number this is: the reader's, the model's, a venue's, or a computation "
            "over the drawn worlds. Exactly one of the four, and never a merge."
        )
    )
    about: str = Field(
        description="What the number is, in plain words a reader needs no other page to follow."
    )
    source: str | None = Field(
        default=None,
        description=(
            "Where it came from, where that is not obvious from the owner: the venue and "
            "the day a price was read, the sample a share was taken over, the rule a "
            "ranking used. Nothing at all for a number the reader typed."
        ),
    )
    lo: float | None = Field(
        default=None,
        description="The bottom of the range around this number, where one was stated.",
    )
    hi: float | None = Field(
        default=None, description="The top of that range. Absent together with `lo`."
    )


def readers(value: float, about: str) -> Figure:
    """Build a figure the reader typed.

    Args:
        value: The number they typed.
        about: What it is, in plain words.

    Returns:
        A figure owned by the reader, with no source: they are the source.
    """
    return Figure(value=value, owner="reader", about=about)


def models(belief: Belief, about: str, source: str | None = None) -> Figure:
    """Build a figure from one of the model's own likelihoods, range and all.

    Args:
        belief: The model's likelihood, which carries its own range.
        about: What the number is, in plain words.
        source: Where it was read from, where that needs saying.

    Returns:
        A figure owned by the model, carrying the range the model stated.

    Raises:
        ValueError: If the belief is not the model's. The three voices are never
            merged, and a card that labelled a venue's number as the model's would
            be doing exactly that.
    """
    if belief.owner != "model":
        raise ValueError(
            f"a card reads the model's own number here; this one is owned by '{belief.owner}'"
        )
    return Figure(
        value=belief.p, owner="model", about=about, source=source, lo=belief.lo, hi=belief.hi
    )


def venues(value: float, about: str, source: str) -> Figure:
    """Build a figure a venue published.

    Args:
        value: The number the venue gave.
        about: What it is, in plain words.
        source: The venue and the day, which a venue's number always names.

    Returns:
        A figure owned by a venue.
    """
    return Figure(value=value, owner="venue", about=about, source=source)


def computed(
    value: float,
    about: str,
    source: str | None = None,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> Figure:
    """Build a figure this program worked out.

    Args:
        value: The number worked out.
        about: What it is, in plain words.
        source: What it was worked out over — the sample, the rule — where that
            needs saying.
        lo: The bottom of the interval around it, where one was measured.
        hi: The top of that interval.

    Returns:
        A figure owned by a computation over the drawn worlds.
    """
    return Figure(value=value, owner="computed", about=about, source=source, lo=lo, hi=hi)


# --- What the card is handed -------------------------------------------------


class Carried(BaseModel):
    """How much of the hypothesis's effect on this ending one claim's arrows carry.

    Worked out by whatever owns the map's own verdict — the shift the hypothesis
    makes to a destination, and which arrows carry most of it — and handed in. The
    card arranges it and never re-derives it.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim whose arrows carry part of the effect.")
    points: float = Field(
        description=(
            "How much of the shift this claim accounts for, as a difference of two "
            "likelihoods: the ending's chance with the hypothesis supposed true against its "
            "chance with it supposed false, attributed to this claim."
        )
    )
    share: float = Field(
        description="What part of the whole shift that is, between nothing and one."
    )


class Shift(BaseModel):
    """How much the hypothesis moves one ending, as a difference of two likelihoods.

    The ending's chance with the hypothesis supposed true, minus its chance with it
    supposed false. It is one of the three worked-out quantities that replaced the
    multiplied-out path likelihood, and the card reads it for one job only: ranking
    the endings a venue does not quote.

    It arrives as a value rather than being computed here, because the exact core
    that works it out is a separate piece of work. This shape is the whole of what
    the card needs from it, so the two can be built in either order.
    """

    model_config = ConfigDict(frozen=True)

    ending: PropositionId = Field(description="The ending the hypothesis moves.")
    points: float = Field(
        description=(
            "The size of the move, as a difference of two likelihoods. Positive where "
            "supposing the hypothesis true raises the ending, negative where it lowers it."
        )
    )
    worked_out_by: str = Field(
        description=(
            "What worked this out, named so the card can say where the number came from: "
            "the map's own verdict over the drawn worlds, or a set of worlds built by hand."
        )
    )


class Watched(BaseModel):
    """One adverse turn worth watching: it hurts, it resolves in time, anybody can see it.

    Handed in by whatever sweeps the map both ways and applies the two filters. The
    card carries it and never calls it a stop.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim to watch.")
    resolves: date = Field(
        description="The day it is judged, which is strictly before the ending's own day."
    )
    observed_by: str = Field(
        description="Who publishes the answer, so a reader knows where to look."
    )
    hurts_by: float = Field(
        description=(
            "How far this turn moves the ending against the reader's side, as a difference "
            "of two likelihoods."
        )
    )


class Unhedgeable(BaseModel):
    """One adverse turn that cannot be watched for, and the reason.

    A claim that would damage the ending but resolves on the same day or later, or
    whose answer nobody publishes. It is listed with its reason and never used as a
    stop, because *this would hurt and you cannot see it coming* is one of the most
    useful sentences this product can say.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim that cannot be watched for.")
    why: str = Field(description="Why it cannot, in one plain sentence.")
    resolves: date = Field(description="The day it is judged.")
    can_be_seen: bool = Field(
        description="Whether anybody publishes the answer at all, which is one of the two filters."
    )


class Tail(BaseModel):
    """One claim that is unlikely and would hurt a lot.

    A tail gets a row of its own and is **never averaged into an expected value**,
    because an average hides the case that wipes the reader out — which is the case
    they most need to see.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The unlikely claim.")
    likelihood: Belief = Field(
        description="The model's own chance of it, range and all. Never merged with anything."
    )
    harm: float = Field(
        description=(
            "What it would do to the position, in the instrument's own price units. Stated "
            "as a loss, so a larger number is a worse case."
        )
    )
    what_could_be_done: str = Field(
        description="What a reader could do about it, in one plain sentence, or why nothing can."
    )


class Shocked(BaseModel):
    """A supposition the reader placed on the map, and what it did to the position.

    **No probability, ever.** They supposed it; that is not a forecast, and the
    map's own number for a claim an edit has just fixed is not one either. This
    shape has no field a probability could go in, so none can be attached by
    accident.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="What they supposed, in their own words.")
    change_to_the_position: float = Field(
        description=(
            "What the position is worth on that branch less what it is worth without it, "
            "in the instrument's own price units."
        )
    )


# --- The sections ------------------------------------------------------------


class TheTrade(BaseModel):
    """What is being traded, where, and which way."""

    model_config = ConfigDict(frozen=True)

    ending: PropositionId = Field(description="The ending the position is on.")
    says: str = Field(description="That ending's claim, in one sentence.")
    trades: Trades = Field(
        description="Whether it names something traded whose price moves, or a contract."
    )
    instrument: str = Field(description="What is bought or sold, named the way its venue names it.")
    side: Side = Field(description="Which way the trade is pointed.")
    venue: str | None = Field(
        default=None, description="The venue, where the ending names a contract."
    )
    contract_id: str | None = Field(
        default=None, description="The venue's own identifier for that contract."
    )
    contract_side: Literal["yes", "no"] | None = Field(
        default=None,
        description=(
            "Which outcome of the contract the ending takes: yes pays when the claim comes true."
        ),
    )
    resolves: date = Field(description="The day the ending's own claim is judged.")
    resolution_test: str = Field(description="The test that settles it, word for word.")
    resolved_by: str = Field(description="Who applies that test.")


class WhatCarriesIt(BaseModel):
    """One row of *what carries it*: a claim, and how much of the effect its arrows carry."""

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim.")
    says: str = Field(description="Its claim, in one sentence.")
    points: Figure = Field(description="How much of the shift this claim accounts for.")
    share: Figure = Field(description="What part of the whole shift that is.")


class QuotedPrices(BaseModel):
    """What a venue is showing, and when it was read.

    A price the reader typed is **theirs**, not a venue's: it is their report of a
    price they believe they could deal at, and it never fills the market's slot. So
    the three figures below are owned by a venue on a quote a venue gave and by the
    reader on one they typed, and the card says which on the same line as the
    number.
    """

    model_config = ConfigDict(frozen=True)

    bid: Figure = Field(description="The best bid: the price you would sell at.")
    offer: Figure = Field(description="The best offer: the price you would buy at.")
    midpoint: Figure = Field(
        description=(
            "Halfway between the two, shown because a reader recognises it and never traded at."
        )
    )
    venue: str = Field(description="Which venue published it, or that the reader entered it.")
    read_on: date = Field(description="The day it was read.")
    how: str = Field(
        description="How it reached us: read now, read from a committed file, or typed."
    )


class MixtureShown(BaseModel):
    """How a supposed reading relates to the unsupposed one — an explanation, never a sum.

    After *Suppose this is true* the reader sees the ending's number re-worked in a
    world where the supposition holds, beside an edge computed from the world where
    nothing was supposed. These are the terms relating the two: the map's own
    chance of the supposition times the reading where it holds, plus one minus that
    chance times the reading where it does not.

    **The two terms do not add up to the unsupposed number and nothing here claims
    they do.** A cause of the supposed claim may reach the ending another way, and
    supposing something pins a **date** as well as a truth while the unsupposed
    world averages over the days it might have happened. So these are four numbers
    shown term by term, and nothing computes an edge from them.
    """

    model_config = ConfigDict(frozen=True)

    supposed: PropositionId = Field(description="The claim the reader supposed.")
    weight_supposed: Figure = Field(
        description="The map's own chance of that claim coming out the way they supposed it."
    )
    weight_otherwise: Figure = Field(description="One minus it. The two always sum to one.")
    reading_supposed: Figure = Field(
        description="The ending's likelihood in the world the reader is looking at."
    )
    reading_otherwise: Figure = Field(
        description="The ending's likelihood where that same claim goes the other way."
    )
    says: str = Field(description="What these terms are, and what they are not.")


class PricedIn(BaseModel):
    """What is priced in, where a venue quotes this claim and an edge could be built.

    The card shows whichever side is worth taking. When neither is, that is a
    complete answer rather than a gap: the number this side pays on sits inside the
    venue's own bid and offer with fees paid.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["priced"] = "priced"
    model: Figure = Field(
        description=(
            "The claim's own likelihood — the chance it comes true — read from the map with "
            "nothing fixed by an edit."
        )
    )
    pays_on: Figure = Field(
        description=(
            "The likelihood this side of the contract actually pays on. The same number on a "
            "yes side; one minus it, range turned over, on a no side."
        )
    )
    quote: QuotedPrices = Field(description="The venue's two prices and the day they were read.")
    fee: Figure | None = Field(
        description=(
            "What the venue charges on one filled trade, in the same units as a price. "
            "Nothing at all means nobody has read the venue's schedule, which is not the "
            "same as a fee of nothing."
        )
    )
    fee_is_unknown: str | None = Field(
        description="Said out loud where nobody has read the fee schedule; nothing otherwise."
    )
    buying: Figure = Field(description="What buying is worth, at the offer, after the fee.")
    selling: Figure = Field(description="What selling is worth, at the bid, after the fee.")
    headline: Literal["buying", "selling", "no_edge_at_this_price"] = Field(
        description="Which side the card leads with, or that neither is worth taking."
    )
    not_headlined_because: str | None = Field(
        description=(
            "Why a positive edge is not led with: the gap is narrower than the venue's "
            "smallest price step, or it is inside the model's own stated range."
        )
    )
    buy_below: Figure = Field(description="Worth buying at any offer below this.")
    sell_above: Figure = Field(description="Worth selling at any bid above this.")
    mixture: MixtureShown | None = Field(
        description=(
            "The terms relating a supposed reading to this one, where the reader supposed "
            "something and the other world was worked out. An explanation that never "
            "computes the edge. Nothing at all otherwise."
        )
    )


class NotPriced(BaseModel):
    """What is priced in, where an edge could not be built — a named refusal and a break-even.

    A refusal is a value and never a blank. Where the ending names a contract, the
    break-even comes with it, because it needs no quote and is the honest answer
    when there is none. Where the ending names an instrument, the break-even is a
    **price** rather than a likelihood, and the reader's own entry price is what
    makes it computable.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["not_priced"] = "not_priced"
    because: NotComparableReason = Field(description="Which of the four refusals this is.")
    sentence: str = Field(description="What the card prints, in plain words a reader can act on.")
    fee: Figure | None = Field(
        description="The venue's fee, where anybody has read it. Nothing at all where nobody has."
    )
    fee_is_unknown: str | None = Field(
        description="Said out loud where nobody has read the fee schedule; nothing otherwise."
    )
    buy_below: Figure | None = Field(
        description="Worth buying below this, where the ending names a contract."
    )
    sell_above: Figure | None = Field(
        description="Worth selling above this, where the ending names a contract."
    )
    price_break_even: Figure | None = Field(
        description=(
            "The price at which a position in an instrument is worth nothing: the reader's "
            "own entry price moved by what it costs to get in and out. Nothing at all where "
            "the ending names a contract, which has a break-even in likelihoods instead."
        )
    )
    costs_are_unknown: str | None = Field(
        description=(
            "Said out loud where nobody has stated what it costs to get in and out of the "
            "instrument, so the price above is the entry price itself."
        )
    )


WhatIsPricedIn = Annotated[PricedIn | NotPriced, Field(discriminator="kind")]
"""Either an edge against a venue's two prices, or a named refusal and a break-even.

Two shapes rather than one because the two are genuinely different answers, and a
single shape with half its fields empty would make a reader guess which case they
are in. Read `kind` to know.
"""


class TakesYouOutRow(BaseModel):
    """One claim over-represented in the worlds where the stop went first.

    **Company, not cause.** A claim can be over-represented in the worlds that
    stopped the reader out because it shares a cause with whatever did. The map
    beside the card is where the mechanism lives.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim.")
    says: str = Field(description="Its claim, in one sentence.")
    lift: Figure = Field(
        description=(
            "How much more often this claim had already come on where the stop went first "
            "than it came on across all the drawn worlds. Three means three times as often; "
            "one means it tells you nothing. No interval, because no coverage is claimed for "
            "a ratio of two shares over overlapping sets."
        )
    )
    came_on_first: Figure = Field(
        description=(
            "The share of the stop-first worlds where this claim had already come on before "
            "the stop was touched, with the interval on that share."
        )
    )
    came_on: Figure = Field(
        description="The share of all the drawn worlds where it came on at all."
    )
    draws: Figure = Field(description="How many equally-weighted worlds the share above is worth.")
    days_before_the_stop: Figure = Field(
        description="The typical days between this claim coming on and the stop being touched."
    )


class WhatTakesYouOutShown(BaseModel):
    """The rail: the rows, what was left off it, and what the numbers rest on."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[TakesYouOutRow, ...] = Field(
        description="The claims, ranked by lift, highest first. Empty where the draws are too few."
    )
    left_off: tuple[str, ...] = Field(
        description="Every claim the rail leaves off, with its reason, in full sentences."
    )
    too_few_draws: str | None = Field(
        description=(
            "Why the rail is empty, where it is empty because the draws behind it are too "
            "few. An empty rail without this reads as *nothing takes you out*."
        )
    )
    draws: Figure = Field(description="How many equally-weighted worlds the whole rail rests on.")


class WhatToWatch(BaseModel):
    """One adverse turn to keep an eye on — and never a stop."""

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim to watch.")
    says: str = Field(description="Its claim, in one sentence.")
    resolves: date = Field(description="The day it is judged, which is before the ending's own.")
    observed_by: str = Field(description="Who publishes the answer.")
    hurts_by: Figure = Field(description="How far it moves the ending against the reader's side.")


class UnhedgeableShown(BaseModel):
    """One adverse turn nothing can warn the reader about, with the reason."""

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim.")
    says: str = Field(description="Its claim, in one sentence.")
    why: str = Field(description="Why it cannot be watched for.")
    resolves: date = Field(description="The day it is judged.")
    can_be_seen: bool = Field(description="Whether anybody publishes the answer at all.")


class CeilingShown(BaseModel):
    """The greyed quartered-Kelly ceiling, and the words it is always shown under.

    A ceiling, never a size. The only number that sets a size is the reader's own
    risk budget. **Zero and absent are different answers** and this shape says
    which: a fraction of zero means the arithmetic ran and came out at nothing to
    put on; nothing at all means there was no edge to run it on.
    """

    model_config = ConfigDict(frozen=True)

    fraction: Figure | None = Field(
        description="The share of capital, quartered, at the unfavourable end of the model's range."
    )
    taken_by: Literal["buying", "selling"] | None = Field(
        description="Which side of the venue's book it was worked out for."
    )
    at: Figure | None = Field(
        description=(
            "The likelihood it was worked out at: the unfavourable end of the model's range."
        )
    )
    warning: str = Field(description="The words the number is always shown under.")
    sentence: str | None = Field(
        description=(
            "Why the answer is zero, or why it is absent. Nothing where a fraction came out."
        )
    )


class YourExit(BaseModel):
    """What the reader typed, what their own rule implies, and how often each end is reached first.

    Every number here is the reader's own except the first-touch shares and the
    greyed ceiling. The size is what their own risk budget implies, which is
    arithmetic on two numbers they typed and is never a recommendation.
    """

    model_config = ConfigDict(frozen=True)

    entry: Figure = Field(description="The price they entered at.")
    stop: Figure = Field(description="The price at which they get out for a loss. Never derived.")
    target: Figure = Field(description="The price at which they get out for a gain. Never derived.")
    horizon: date = Field(description="The day by which they expect to be out.")
    risk_budget: Figure = Field(description="The share of capital they are prepared to lose here.")
    implied_size: Figure = Field(
        description=(
            "The share of capital whose loss from entry to stop is exactly that risk budget. "
            "Their own rule's arithmetic, and never a recommendation."
        )
    )
    ceiling: CeilingShown = Field(description="The greyed ceiling, beside their own arithmetic.")
    stop_first: Figure | None = Field(
        description="How often the stop is touched before the target, over the drawn worlds."
    )
    target_first: Figure | None = Field(description="How often the target is touched first.")
    neither: Figure | None = Field(
        description="How often the window closes with neither touched. The three sum to one."
    )
    stop_at: Figure | None = Field(
        description="The level actually checked, after the barrier shift."
    )
    target_at: Figure | None = Field(description="The same, for the target.")
    first_touch_refused: str | None = Field(
        description=(
            "Why there is no first touch here: a contract is held to resolution and there is "
            "no path to touch. Nothing at all where the shares were worked out."
        )
    )
    method: str | None = Field(
        description="How the shares were arrived at, printed wherever they are."
    )


class TailRow(BaseModel):
    """One tail: unlikely, and enough to hurt. Never averaged into anything."""

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The unlikely claim.")
    says: str = Field(description="Its claim, in one sentence.")
    likelihood: Figure = Field(description="The model's own chance of it, range and all.")
    harm: Figure = Field(description="What it would do to the position, as a loss.")
    what_could_be_done: str = Field(
        description="What a reader could do about it, or why nothing can."
    )


class ShockRow(BaseModel):
    """A supposition the reader placed, and what it did to the position — with no probability."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="What they supposed, in their own words.")
    placed_by: Literal["reader"] = Field(
        default="reader",
        description="Who placed it. Always the reader: nothing else places a shock.",
    )
    change_to_the_position: Figure = Field(
        description="What the position is worth on that branch less what it is worth without it."
    )
    says: str = Field(description="Why there is no probability here, in the reader's own terms.")


class RankedEnding(BaseModel):
    """One tradeable ending in the ranking, and which rule put it there."""

    model_config = ConfigDict(frozen=True)

    ending: PropositionId = Field(description="The ending.")
    says: str = Field(description="Its claim, in one sentence.")
    trades: Trades = Field(description="Whether it names something traded or a contract.")
    instrument: str = Field(
        description="What would be bought or sold, or the contract's identifier."
    )
    ranked_by: Literal["the_size_of_its_edge", "the_shift_times_the_move"] = Field(
        description="Which of the two rules ranked this row. Never a blend of the two."
    )
    key: Figure = Field(description="The number that rule ranked it on.")
    made_of: tuple[Figure, ...] = Field(
        description="The numbers the key is made of, so it can say why it is what it is."
    )
    headline: bool = Field(description="Whether this row may be led with, or only listed.")
    not_headlined_because: str | None = Field(
        description="Why it may not be led with. Nothing where it may."
    )


class NotRanked(BaseModel):
    """One tradeable ending the ranking leaves out, and why.

    Said out loud rather than quietly missing, because *this ending is not ranked*
    and *this ending was never considered* are different facts and a reader can act
    on only one of them.
    """

    model_config = ConfigDict(frozen=True)

    ending: PropositionId = Field(description="The ending left out.")
    says: str = Field(description="Its claim, in one sentence.")
    because: Literal["inside_the_model_range", "no_edge", "no_shift"] = Field(
        description="Which of the three reasons it was."
    )
    sentence: str = Field(description="What the card prints beside it.")


class WhatElseCanITrade(BaseModel):
    """Every tradeable ending on the map, ranked — by two rules, kept apart.

    Two lists rather than one because an edge in cents and a move in per cent are
    not the same quantity and there is no honest exchange rate between them. Each
    list is ordered within itself; no row is ever ordered against a row in the
    other.
    """

    model_config = ConfigDict(frozen=True)

    by_the_size_of_its_edge: tuple[RankedEnding, ...] = Field(
        description="Endings a venue quotes, best edge first, whichever side it favours."
    )
    by_the_shift_times_the_move: tuple[RankedEnding, ...] = Field(
        description="Endings naming an instrument, largest shift times move first."
    )
    not_ranked: tuple[NotRanked, ...] = Field(
        description="Tradeable endings neither rule could rank, each with its reason."
    )
    two_rules: str = Field(description="Why there are two lists, said on the card itself.")


class WhatThisDoesNotKnow(BaseModel):
    """The limits, carried as data rather than as a footer.

    A footer is dropped by whatever reads the document next; a field has to be
    read. So the refusals are a list of full sentences, the not-advice line is a
    field, and the one thing this product says about getting out is a field too.
    """

    model_config = ConfigDict(frozen=True)

    refuses: tuple[str, ...] = Field(description="Every limit, in full sentences.")
    not_advice: str = Field(description="What this document is not, in one line.")
    execution: str = Field(description="The one thing said about getting out, and nothing else.")


class Card(BaseModel):
    """The whole thesis the reader carries away, stamped with what produced it.

    A card is a **state of the panel, never a dialog**, and it can always be thrown
    away and rebuilt: the map it came from, the branch and the seed are on it, and
    the same three produce the same card.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(description="The map this card was built from.")
    branch_id: BranchId | None = Field(
        description="The branch folded on, or nothing at all for the untouched map."
    )
    seed: int = Field(description="The one number every random draw behind this card came from.")
    as_of: date = Field(description="The first day of the window the numbers were worked out over.")
    hypothesis: PropositionId = Field(description="The claim the map starts from.")
    hypothesis_says: str = Field(description="That claim, in one sentence.")
    the_trade: TheTrade = Field(description="What is being traded, where, and which way.")
    carried_by: tuple[WhatCarriesIt, ...] = Field(
        description="The claims whose arrows carry most of the hypothesis's effect on this ending."
    )
    priced_in: WhatIsPricedIn = Field(
        description=(
            "The edge against a venue's two prices, or the named refusal and the break-even."
        )
    )
    takes_you_out: WhatTakesYouOutShown = Field(
        description="The claims over-represented where the stop went first."
    )
    watch: tuple[WhatToWatch, ...] = Field(
        description="What is adverse, resolves in time, and can be seen."
    )
    unhedgeable: tuple[UnhedgeableShown, ...] = Field(
        description="What is adverse and cannot be watched for, with the reason."
    )
    your_exit: YourExit = Field(description="What the reader typed, and how often each end is hit.")
    tails: tuple[TailRow, ...] = Field(
        description="Claims that are unlikely and would hurt, ranked by harm, never averaged."
    )
    shocks: tuple[ShockRow, ...] = Field(
        description="Suppositions the reader placed, with no probability attached."
    )
    what_else: WhatElseCanITrade = Field(
        description="Every tradeable ending on the map, ranked by two rules kept apart."
    )
    does_not_know: WhatThisDoesNotKnow = Field(
        description="The refusals, the not-advice line and the one execution sentence."
    )


# --- Building one ------------------------------------------------------------


def where_the_numbers_came_from(
    sample: SampleFrom, market_chance_from: Mapping[PropositionId, MarketChanceFrom]
) -> str:
    """Name, in one sentence, the sample the days came from and where each market chance came from.

    Two things have to be said wherever a first-touch number appears. The days each
    claim came on are drawn from a sample of worlds, and which sample that is
    decides how much the number can be trusted. And the path applies only what the
    market has not already priced, so how much that is depends on where the
    market's chance of each claim came from — a venue's quote, the model's own
    number, or a chance the reader typed.

    Args:
        sample: Which sampler the drawn worlds came from.
        market_chance_from: Where the market's chance of each claim that moves the
            price came from.

    Returns:
        One sentence naming both, with the claims in a fixed order so two runs
        produce the same words.
    """
    said = THE_SAMPLE_SAYS[sample]
    if not market_chance_from:
        return f"{said}; no claim on this map moves the price, so no market chance was needed"
    each = ", ".join(
        f"{claim} — {THE_CHANCE_CAME_FROM[market_chance_from[claim]]}"
        for claim in sorted(market_chance_from)
    )
    return f"{said}, with the market's chance of each claim from: {each}"


def _the_claim(base: World, claim: PropositionId) -> Proposition:
    """Find a claim on the map, or say plainly that it is not there.

    Args:
        base: The world whose map to look in.
        claim: The claim wanted.

    Returns:
        That claim.

    Raises:
        ValueError: If the map does not carry it. A card row about a claim nobody
            drew is a number that cannot be traced to an input, so it is said out
            loud rather than left to a renderer.
    """
    found = next((one for one in base.graph.propositions if one.id == claim), None)
    if found is None:
        raise ValueError(f"the claim '{claim}' is not on this map, so no card row can name it")
    return found


def _tradeable(base: World) -> tuple[tuple[Proposition, Payoff], ...]:
    """Every ending on the map that names something you could trade, beside what it names.

    The pair is returned rather than the ending alone so that what it names travels
    with it: the two ranking rules are chosen by which of the two payoffs it is,
    and an ending carried without its payoff would have to be asked again.

    Args:
        base: The world whose map to read.

    Returns:
        The endings naming a contract or an instrument, each with its payoff, in
        the map's own order. An ending that names why there is no trade is not one
        of them.
    """
    return tuple((one, one.payoff) for one in base.graph.propositions if one.payoff is not None)


def what_else_can_i_trade(
    base: World,
    priced: Mapping[PropositionId, Edge | NotComparable],
    shifts: Mapping[PropositionId, Shift],
) -> WhatElseCanITrade:
    """Rank every tradeable ending on the map, by two rules that are never blended.

    | The ending | The rule | The key |
    |---|---|---|
    | A venue quotes it, an edge was built | the size of its edge | the better of the two edges |
    | It names an instrument | the shift times the move | the shift, times its payoff's move |

    An ending whose edge is worth taking at one end of the model's own stated range
    and not at the other is **not ranked at all** and says so; an edge narrower than
    the venue's smallest price step is ranked but not led with. An ending a venue
    does not quote, and an instrument ending nothing has worked out a shift for,
    are listed with their reasons rather than dropped.

    Args:
        base: The world with nothing fixed by an edit, whose map holds the endings.
        priced: What `edge.py` returned for each ending — an edge, or the refusal
            that stands where one could not be built.
        shifts: How much the hypothesis moves each ending, for the endings a venue
            does not quote.

    Returns:
        Two ordered lists and everything neither could rank.

    Raises:
        ValueError: If `priced` carries an answer about a claim that is not on this
            map, which would mean two different maps had been mixed.
    """
    for claim in priced:
        _the_claim(base, claim)
    by_edge: list[RankedEnding] = []
    by_shift: list[RankedEnding] = []
    left_out: list[NotRanked] = []
    for ending, payoff in _tradeable(base):
        answer = priced.get(ending.id)
        if isinstance(payoff, ContractPayoff):
            if not isinstance(answer, Edge):
                left_out.append(
                    NotRanked(
                        ending=ending.id,
                        says=ending.claim,
                        because="no_edge",
                        sentence=answer.sentence if answer is not None else NOTHING_WAS_PRICED,
                    )
                )
            elif answer.inside_the_model_range:
                left_out.append(
                    NotRanked(
                        ending=ending.id,
                        says=ending.claim,
                        because="inside_the_model_range",
                        sentence=INSIDE_THE_MODEL_RANGE,
                    )
                )
            else:
                by_edge.append(_ranked_by_edge(ending, answer))
            continue
        shift = shifts.get(ending.id)
        if shift is None:
            left_out.append(
                NotRanked(
                    ending=ending.id,
                    says=ending.claim,
                    because="no_shift",
                    sentence=NO_SHIFT_WAS_WORKED_OUT,
                )
            )
            continue
        by_shift.append(_ranked_by_shift(ending, payoff, shift))
    by_edge.sort(key=lambda one: (-one.key.value, one.ending))
    by_shift.sort(key=lambda one: (-one.key.value, one.ending))
    return WhatElseCanITrade(
        by_the_size_of_its_edge=tuple(by_edge),
        by_the_shift_times_the_move=tuple(by_shift),
        not_ranked=tuple(left_out),
        two_rules=TWO_RULES,
    )


def _ranked_by_edge(ending: Proposition, edge: Edge) -> RankedEnding:
    """Rank one ending by the size of its edge, whichever side it favours.

    The key is the better of the two edges, and it may be negative: an ending a
    venue prices out of reach is still an ending the reader asked about, and it
    ranks last rather than disappearing.

    Args:
        ending: The ending.
        edge: The edge built against the venue's two prices, which its caller has
            already found is not inside the model's own stated range.

    Returns:
        The row.
    """
    best = max(edge.buying, edge.selling)
    side = "buying" if edge.buying >= edge.selling else "selling"
    narrow = edge.tick is not None and abs(best) < edge.tick
    return RankedEnding(
        ending=ending.id,
        says=ending.claim,
        trades="contract",
        instrument=edge.quote.market_id or ending.id,
        ranked_by="the_size_of_its_edge",
        key=computed(
            best,
            f"the better of the two edges, which is the edge of {side}",
            "the size of its edge, whichever side it favours",
        ),
        made_of=(
            computed(edge.buying, "what buying is worth, at the offer, after the fee"),
            computed(edge.selling, "what selling is worth, at the bid, after the fee"),
        ),
        headline=not narrow,
        not_headlined_because=NARROWER_THAN_A_TICK if narrow else None,
    )


def _ranked_by_shift(ending: Proposition, payoff: PricePayoff, shift: Shift) -> RankedEnding:
    """Rank one ending by the shift the hypothesis makes to it, times the move its payoff names.

    The shift may point either way, and the payoff's own direction says which way
    makes money, so the key is the size of the product and the two numbers it is
    made of sit beside it.

    Args:
        ending: The ending being ranked.
        payoff: What it names: the instrument, and how far the model says that
            instrument moves if the claim comes true.
        shift: How far the hypothesis moves it.

    Returns:
        The row.
    """
    return RankedEnding(
        ending=ending.id,
        says=ending.claim,
        trades="instrument",
        instrument=payoff.instrument,
        ranked_by="the_shift_times_the_move",
        key=computed(
            abs(shift.points) * payoff.move,
            "how far the hypothesis moves this ending, times the move its payoff names",
            "the shift times the move",
        ),
        made_of=(
            computed(
                shift.points,
                "how far the hypothesis moves this ending, as a difference of two likelihoods",
                shift.worked_out_by,
            ),
            Figure(
                value=payoff.move,
                owner="model",
                about=(
                    "how far the instrument moves if the claim comes true, as the model stated it"
                ),
            ),
        ),
        headline=True,
        not_headlined_because=None,
    )


def card_of(
    base: World,
    *,
    position: Position,
    priced: Mapping[PropositionId, Edge | NotComparable],
    shifts: Mapping[PropositionId, Shift],
    carried_by: Sequence[Carried],
    ceiling: Ceiling,
    touch: FirstTouch | Refusal,
    takes_you_out: WhatTakesYouOut,
    market_chance_from: Mapping[PropositionId, MarketChanceFrom],
    watch: Sequence[Watched],
    unhedgeable: Sequence[Unhedgeable],
    tails: Sequence[Tail],
    shocks: Sequence[Shocked],
    implied_size: float,
    costs: float | None,
) -> Card:
    """Assemble one card out of what every other module worked out.

    Nothing here is computed that another module owns: the edge arrives built, the
    first-touch shares arrive measured, the rail arrives ranked, the ceiling
    arrives quartered, and the shift arrives from whatever works out the map's own
    verdict. What this does is arrange them, attach an owner to every number, and
    rank two things nobody else ranks — the tradeable endings, by two rules kept
    apart, and the tails, by what they would do to the position.

    Args:
        base: The world with nothing fixed by an edit. The map, the branch, the
            seed and the first day of the window are read from it.
        position: What the reader typed, and the trade the map's own payoff names.
        priced: What `edge.py` returned for each tradeable ending, including the
            one being traded.
        shifts: How far the hypothesis moves each ending, for ranking the ones a
            venue does not quote.
        carried_by: The claims whose arrows carry most of that shift.
        ceiling: The greyed quartered-Kelly ceiling, or the reason there is none.
        touch: How often each end of the exit is reached first, or the refusal a
            contract gets.
        takes_you_out: The rail of claims over-represented where the stop went first.
        market_chance_from: Where the market's chance of each claim that moves the
            price came from, which every first-touch number names in its own
            sentence.
        watch: The adverse turns that resolve in time and can be seen.
        unhedgeable: The adverse turns that cannot be watched for, with reasons.
        tails: The claims that are unlikely and would hurt.
        shocks: The suppositions the reader placed, and what each did to the position.
        implied_size: The share of capital the reader's own risk budget implies,
            worked out by `position.py` and handed in rather than re-derived here.
        costs: What it costs to get in and out of the instrument, in its own price
            units, or nothing at all where nobody has stated them.

    Returns:
        The card.

    Raises:
        ValueError: If the position's ending is not on the map, if no answer was
            priced for it, or if any row names a claim the map does not carry. All
            are broken promises between our own pieces of code rather than anything
            a reader did.
    """
    ending = _the_claim(base, position.ending)
    answer = priced.get(position.ending)
    if answer is None:
        raise ValueError(
            f"the ending '{position.ending}' is being traded, so the card needs what was "
            "priced for it, and nothing was handed in"
        )
    hypothesis = _the_claim(base, base.graph.hypothesis_id)
    return Card(
        base_id=base.base_id,
        branch_id=base.branch_id,
        seed=base.seed,
        as_of=base.day_zero,
        hypothesis=hypothesis.id,
        hypothesis_says=hypothesis.claim,
        the_trade=_the_trade(ending, position),
        carried_by=tuple(_carries(base, one) for one in carried_by),
        priced_in=_priced_in(answer, position, costs),
        takes_you_out=_rail(base, takes_you_out, market_chance_from),
        watch=tuple(_watch(base, one) for one in watch),
        unhedgeable=tuple(_unhedgeable(base, one) for one in unhedgeable),
        your_exit=_your_exit(position, ceiling, touch, market_chance_from, implied_size),
        tails=_tails(base, tails),
        shocks=tuple(_shock(one) for one in shocks),
        what_else=what_else_can_i_trade(base, priced, shifts),
        does_not_know=WhatThisDoesNotKnow(
            refuses=REFUSES, not_advice=NOT_ADVICE, execution=EXECUTION
        ),
    )


def _the_trade(ending: Proposition, position: Position) -> TheTrade:
    """Say what is traded, where and which way, reading the venue's facts off the payoff.

    Args:
        ending: The ending being traded.
        position: What the reader typed, which took its instrument and side from
            that same payoff.

    Returns:
        The trade section.
    """
    payoff = ending.payoff
    contract = payoff if isinstance(payoff, ContractPayoff) else None
    return TheTrade(
        ending=ending.id,
        says=ending.claim,
        trades=position.trades,
        instrument=position.instrument,
        side=position.side,
        venue=contract.venue if contract is not None else None,
        contract_id=contract.contract_id if contract is not None else None,
        contract_side=contract.side if contract is not None else None,
        resolves=ending.resolution.by,
        resolution_test=ending.resolution.criteria,
        resolved_by=ending.resolution.source,
    )


def _carries(base: World, carried: Carried) -> WhatCarriesIt:
    """Turn one carried-effect row into a card row, with an owner on both numbers.

    Args:
        base: The world whose map names the claim.
        carried: What was handed in.

    Returns:
        The row.
    """
    claim = _the_claim(base, carried.claim)
    return WhatCarriesIt(
        claim=claim.id,
        says=claim.claim,
        points=computed(
            carried.points,
            "how much of the hypothesis's effect on this ending this claim's arrows carry",
        ),
        share=computed(carried.share, "what part of the whole shift that is"),
    )


def _priced_in(
    answer: Edge | NotComparable, position: Position, costs: float | None
) -> WhatIsPricedIn:
    """Turn an edge, or the refusal that stands where one could not be built, into a card section.

    An instrument ending gets the break-even its own entry price makes computable:
    the price at which the position is worth nothing, which is the entry price moved
    by what it costs to get in and out. Where nobody has stated those costs the
    price is the entry price itself, and the card says so rather than printing a
    number that looks net.

    Args:
        answer: What `edge.py` returned.
        position: What the reader typed, whose entry price and side the price
            break-even needs.
        costs: What it costs to get in and out, or nothing at all.

    Returns:
        Either the priced section or the refused one.
    """
    unknown_fee = (
        "Nobody has read this venue's fee schedule, so these are before fees."
        if answer.fee is None
        else None
    )
    fee = (
        venues(answer.fee, "what the venue charges on one filled trade", "the venue's schedule")
        if answer.fee is not None
        else None
    )
    if isinstance(answer, NotComparable):
        price_break_even = None
        unknown_costs = None
        if position.trades == "instrument":
            paid = costs or 0.0
            away = paid if position.side == "long" else -paid
            price_break_even = computed(
                position.entry + away,
                "the price at which this position is worth nothing",
                "the entry price you typed, moved by what it costs to get in and out",
            )
            unknown_costs = (
                "Nobody has stated what it costs to get in and out of this instrument, so "
                "this is the entry price itself."
                if costs is None
                else None
            )
        return NotPriced(
            because=answer.reason,
            sentence=answer.sentence,
            fee=fee,
            fee_is_unknown=unknown_fee,
            buy_below=(
                computed(answer.break_even.buy_below, "worth buying at any offer below this")
                if answer.break_even is not None
                else None
            ),
            sell_above=(
                computed(answer.break_even.sell_above, "worth selling at any bid above this")
                if answer.break_even is not None
                else None
            ),
            price_break_even=price_break_even,
            costs_are_unknown=unknown_costs,
        )
    best = max(answer.buying, answer.selling)
    headline: Literal["buying", "selling", "no_edge_at_this_price"]
    if best <= 0.0:
        headline = "no_edge_at_this_price"
    else:
        headline = "buying" if answer.buying >= answer.selling else "selling"
    narrow = answer.tick is not None and abs(best) < answer.tick
    read_on = answer.quote.as_of.date()
    typed = answer.quote.source == "user"
    said = (
        A_PRICE_YOU_ENTERED
        if typed
        else f"{answer.quote.venue}, {answer.quote.source} {read_on.isoformat()}"
    )

    def price(value: float, about: str) -> Figure:
        """Build a price figure, owned by whoever gave the price."""
        return readers(value, about) if typed else venues(value, about, said)

    return PricedIn(
        model=models(answer.model, "the chance this claim comes true"),
        pays_on=models(answer.pays_on, "the chance this side of the trade pays on"),
        quote=QuotedPrices(
            bid=price(answer.quote.bid, "the best bid: the price you would sell at"),
            offer=price(answer.quote.offer, "the best offer: the price you would buy at"),
            midpoint=price(answer.quote.midpoint, "halfway between the two, and never traded at"),
            venue=A_PRICE_YOU_ENTERED if typed else (answer.quote.venue or A_PRICE_YOU_ENTERED),
            read_on=read_on,
            how=answer.quote.source,
        ),
        fee=fee,
        fee_is_unknown=unknown_fee,
        buying=computed(answer.buying, "what buying is worth, at the offer, after the fee"),
        selling=computed(answer.selling, "what selling is worth, at the bid, after the fee"),
        headline=headline,
        not_headlined_because=(
            NO_EDGE_AT_THIS_PRICE
            if headline == "no_edge_at_this_price"
            else NARROWER_THAN_A_TICK
            if narrow
            else None
        ),
        buy_below=computed(answer.break_even.buy_below, "worth buying at any offer below this"),
        sell_above=computed(answer.break_even.sell_above, "worth selling at any bid above this"),
        mixture=_mixture(answer.mixture),
    )


def _mixture(mixture: Mixture | None) -> MixtureShown | None:
    """Put the four terms that explain a supposed reading on the card, and claim nothing by it.

    Args:
        mixture: The terms `edge.py` worked out, or nothing at all where the reader
            supposed nothing or no second world was handed in.

    Returns:
        The four terms with an owner on each, or nothing at all.
    """
    if mixture is None:
        return None
    return MixtureShown(
        supposed=mixture.supposed,
        weight_supposed=Figure(
            value=mixture.weight_supposed,
            owner="model",
            about="the map's own chance of the claim you supposed coming out that way",
        ),
        weight_otherwise=Figure(
            value=mixture.weight_otherwise,
            owner="model",
            about="one minus it, which is the chance it comes out the other way",
        ),
        reading_supposed=Figure(
            value=mixture.reading_supposed,
            owner="model",
            about="this ending's likelihood in the world you are looking at",
        ),
        reading_otherwise=Figure(
            value=mixture.reading_otherwise,
            owner="model",
            about="this ending's likelihood where that same claim goes the other way",
        ),
        says=THE_MIXTURE_EXPLAINS,
    )


def _rail(
    base: World,
    rail: WhatTakesYouOut,
    market_chance_from: Mapping[PropositionId, MarketChanceFrom],
) -> WhatTakesYouOutShown:
    """Turn the lift rail into card rows, naming the sample every share was taken over.

    Args:
        base: The world whose map names each claim.
        rail: The rail as `lift.py` ranked it.
        market_chance_from: Where each claim's market chance came from, for the
            sentence that names it beside the sample.

    Returns:
        The rail as the card shows it, with what was left off in full sentences.
    """
    said = where_the_numbers_came_from(rail.sample, market_chance_from)
    rows = tuple(
        TakesYouOutRow(
            claim=one.claim,
            says=_the_claim(base, one.claim).claim,
            lift=computed(
                one.lift,
                "how much more often this claim had already come on where the stop went first",
                said,
            ),
            came_on_first=computed(
                one.came_on_first,
                "the share of the stop-first worlds where it had already come on",
                f"{said}; the interval covers this share {one.coverage:.0%} of the time",
                lo=one.came_on_first_lo,
                hi=one.came_on_first_hi,
            ),
            came_on=computed(
                one.came_on, "the share of all the drawn worlds where it came on at all", said
            ),
            draws=computed(
                one.effective_draws,
                "how many equally-weighted worlds this row rests on",
                said,
            ),
            days_before_the_stop=computed(
                one.days_before_the_stop,
                "the typical days between this claim coming on and the stop being touched",
                said,
            ),
        )
        for one in rail.rows
    )
    return WhatTakesYouOutShown(
        rows=rows,
        left_off=tuple(f"{one.claim}: {one.sentence}" for one in rail.dropped),
        too_few_draws=rail.too_few_draws,
        draws=computed(
            rail.effective_draws,
            "how many equally-weighted worlds the whole rail rests on",
            f"{said}; {rail.stop_first_worlds} worlds ended with the stop touched first, and no "
            f"row may rest on fewer than {rail.floor} equally-weighted ones",
        ),
    )


def _watch(base: World, watched: Watched) -> WhatToWatch:
    """Turn one watchlist row into a card row.

    Args:
        base: The world whose map names the claim.
        watched: What was handed in.

    Returns:
        The row.
    """
    claim = _the_claim(base, watched.claim)
    return WhatToWatch(
        claim=claim.id,
        says=claim.claim,
        resolves=watched.resolves,
        observed_by=watched.observed_by,
        hurts_by=computed(watched.hurts_by, "how far this turn moves the ending against your side"),
    )


def _unhedgeable(base: World, one: Unhedgeable) -> UnhedgeableShown:
    """Turn one unhedgeable row into a card row.

    Args:
        base: The world whose map names the claim.
        one: What was handed in.

    Returns:
        The row.
    """
    claim = _the_claim(base, one.claim)
    return UnhedgeableShown(
        claim=claim.id,
        says=claim.claim,
        why=one.why,
        resolves=one.resolves,
        can_be_seen=one.can_be_seen,
    )


def _your_exit(
    position: Position,
    ceiling: Ceiling,
    touch: FirstTouch | Refusal,
    market_chance_from: Mapping[PropositionId, MarketChanceFrom],
    implied_size: float,
) -> YourExit:
    """Arrange what the reader typed, what it implies, and how often each end is reached first.

    Args:
        position: What they typed.
        ceiling: The greyed ceiling, or the reason there is none.
        touch: The three shares, or the refusal a contract gets.
        market_chance_from: Where each claim's market chance came from, for the
            sentence naming it beside the sample.
        implied_size: What their own risk budget implies, worked out elsewhere.

    Returns:
        The exit section.
    """
    shown = _ceiling(ceiling)
    if isinstance(touch, Refusal):
        return YourExit(
            entry=readers(position.entry, "the price you entered at"),
            stop=readers(position.stop, "the price at which you get out for a loss"),
            target=readers(position.target, "the price at which you get out for a gain"),
            horizon=position.horizon,
            risk_budget=readers(
                position.risk_budget, "the share of your capital you are prepared to lose here"
            ),
            implied_size=readers(implied_size, "the share of capital your own risk budget implies"),
            ceiling=shown,
            stop_first=None,
            target_first=None,
            neither=None,
            stop_at=None,
            target_at=None,
            first_touch_refused=touch.sentence,
            method=None,
        )
    said = where_the_numbers_came_from(touch.sample, market_chance_from)
    return YourExit(
        entry=readers(position.entry, "the price you entered at"),
        stop=readers(position.stop, "the price at which you get out for a loss"),
        target=readers(position.target, "the price at which you get out for a gain"),
        horizon=position.horizon,
        risk_budget=readers(
            position.risk_budget, "the share of your capital you are prepared to lose here"
        ),
        implied_size=readers(implied_size, "the share of capital your own risk budget implies"),
        ceiling=shown,
        stop_first=computed(
            touch.stop_first, "how often your stop is touched before your target", said
        ),
        target_first=computed(touch.target_first, "how often your target is touched first", said),
        neither=computed(touch.neither, "how often the window closes with neither touched", said),
        stop_at=computed(
            touch.stop_at,
            "the level actually checked for the stop, after the barrier shift",
            said,
        ),
        target_at=computed(
            touch.target_at,
            "the level actually checked for the target, after the barrier shift",
            said,
        ),
        first_touch_refused=None,
        method=THE_BARRIER_SHIFT,
    )


def _ceiling(ceiling: Ceiling) -> CeilingShown:
    """Put the greyed ceiling on the card, keeping zero and absent apart.

    Args:
        ceiling: What `ceiling.py` worked out.

    Returns:
        The ceiling as the card shows it, always under its own words.
    """
    return CeilingShown(
        fraction=(
            computed(
                ceiling.fraction,
                "the most of your capital the Kelly rule would put on, quartered",
                "worked out at the unfavourable end of the model's own stated range",
            )
            if ceiling.fraction is not None
            else None
        ),
        taken_by=ceiling.taken_by,
        at=(
            computed(
                ceiling.at,
                "the likelihood it was worked out at: the unfavourable end of the model's range",
            )
            if ceiling.at is not None
            else None
        ),
        warning=ceiling.warning,
        sentence=ceiling.sentence,
    )


def _tails(base: World, tails: Sequence[Tail]) -> tuple[TailRow, ...]:
    """Rank the tails by what they would do to the position, and never by an average.

    Ranked by **harm alone**, with the likelihood beside it and never multiplied
    into it: likelihood times harm is an expected loss by another name, and an
    expected value is the one thing a tail row exists to avoid headlining.

    Args:
        base: The world whose map names each claim.
        tails: The claims that are unlikely and would hurt.

    Returns:
        The rows, worst harm first.
    """
    rows = [
        TailRow(
            claim=one.claim,
            says=_the_claim(base, one.claim).claim,
            likelihood=models(one.likelihood, "the model's own chance of this claim"),
            harm=computed(one.harm, "what this would do to the position, as a loss in price units"),
            what_could_be_done=one.what_could_be_done,
        )
        for one in tails
    ]
    rows.sort(key=lambda one: (-one.harm.value, one.claim))
    return tuple(rows)


def _shock(shocked: Shocked) -> ShockRow:
    """Put a shock the reader placed on the card, with no probability anywhere near it.

    Args:
        shocked: What they supposed, and what it did to the position.

    Returns:
        The row, carrying the sentence that says why there is no probability.
    """
    return ShockRow(
        name=shocked.name,
        change_to_the_position=computed(
            shocked.change_to_the_position,
            "what the position is worth on that branch less what it is worth without it",
        ),
        says=A_SHOCK_HAS_NO_PROBABILITY,
    )
