"""The greyed ceiling: quartered Kelly at the unfavourable end, and the two ways it is not a number.

Every ceiling here is worked out by hand in the docstring that asserts it, and no
number an engine computed is typed anywhere in this file.

The edges are **written out rather than priced**, because a ceiling reads four
numbers off an edge — the model's range, the venue's two prices and the fee — and
this file is about the arithmetic on those four. Whether `priced` fills them
correctly, and whether it marks an edge whose sign changes across the model's
range, is what `test_edge.py` is for; here that mark is an input the test chose.

Three things these tests exist to catch:

* **A ceiling built at the flattering end of the model's range.** The range is the
  model's own statement of how unsure it is, and a ceiling that ignores it is a
  ceiling of a number nobody stated. Widening the range about the same point never
  raises the answer, and a test checks that in both directions.
* **A blank.** Zero and absent are different answers — the arithmetic ran and came
  out at nothing, against there being no arithmetic to run — and each carries its
  own sentence.
* **A number that looks like a size.** The warning travels on the value, so no
  screen and no export can print the fraction without it.
"""

from datetime import UTC, datetime

import pytest

from katalyst.domain import Belief
from katalyst.grounding import Quote
from katalyst.thesis.ceiling import (
    A_CEILING_NEEDS_AN_EDGE,
    NEVER_SIZE_TO_THIS,
    NOTHING_WORTH_TAKING,
    QUARTER,
    THE_RANGE_DISAGREES,
    Ceiling,
    ceiling_of,
)
from katalyst.thesis.edge import BreakEven, Edge, NotComparable

SOME_INSTANT = datetime(2026, 9, 21, 14, 48, 27, tzinfo=UTC)
"""One instant a price was true. Every quote must carry one; nothing here reads it."""

CLAIM = "the-claim"


def a_quote(bid: float, offer: float) -> Quote:
    """A venue's two prices for the contract this file prices against."""
    return Quote(
        bid=bid,
        offer=offer,
        as_of=SOME_INSTANT,
        source="user",
    )


def an_edge(
    *,
    model: Belief,
    bid: float,
    offer: float,
    fee: float | None = 0.0,
    straddles: bool = False,
) -> Edge:
    """One edge on a yes-side contract, so the ceiling has something to work from.

    Built here rather than through a world, because a ceiling reads four numbers
    off an edge — the model's range, the two prices and the fee — and what this
    file is about is the arithmetic on those four.
    """
    paid = fee or 0.0
    return Edge(
        claim=CLAIM,
        model=model,
        pays_on=model,
        quote=a_quote(bid, offer),
        fee=fee,
        buying=model.p - offer - paid,
        selling=bid - model.p - paid,
        break_even=BreakEven(buy_below=model.p - paid, sell_above=model.p + paid, fee=fee),
        inside_the_model_range=straddles,
        base_branch=None,
        tick=None,
    )


def a_refusal(reason: str = "no_contract") -> NotComparable:
    """One named refusal, standing where an edge could not be built."""
    return NotComparable(
        claim=CLAIM,
        reason=reason,  # type: ignore[arg-type]
        sentence="No contract quotes this claim — edge not calculable.",
        fee=None,
    )


# --- The arithmetic ---------------------------------------------------------


def test_the_ceiling_is_a_quartered_kelly_at_the_unfavourable_end() -> None:
    """Worked out by hand: the model says a half, low end four tenths, and the offer is a fifth.

    Buying a contract that pays one costs the offer. The Kelly rule at a likelihood
    `p` and a cost `c` puts on `(p - c) / (1 - c)` of capital. At the **low** end of
    the model's range — the end that makes buying worth least — that is
    `(0.4 - 0.2) / (1 - 0.2) = 0.25`, and a quarter of that is **one sixteenth**.
    """
    edge = an_edge(model=Belief(p=0.5, lo=0.4, hi=0.6, owner="model"), bid=0.1, offer=0.2)

    ceiling = ceiling_of(edge)

    assert ceiling.taken_by == "buying"
    assert ceiling.at == pytest.approx(0.4)
    assert ceiling.fraction == pytest.approx(0.25 / QUARTER)


def test_selling_is_worked_out_at_the_top_of_the_range() -> None:
    """The mirror: the venue bids eight tenths for something the model's top end calls a half.

    Selling a contract for `r` and paying one if it comes good puts on
    `(r - p) / r` of capital, at the **high** end of the range because a higher
    likelihood makes selling worth less: `(0.8 - 0.5) / 0.8 = 0.375`, quartered to
    three thirty-seconds.
    """
    edge = an_edge(model=Belief(p=0.4, lo=0.3, hi=0.5, owner="model"), bid=0.8, offer=0.9)

    ceiling = ceiling_of(edge)

    assert ceiling.taken_by == "selling"
    assert ceiling.at == pytest.approx(0.5)
    assert ceiling.fraction == pytest.approx(0.375 / QUARTER)


def test_the_fee_makes_the_ceiling_smaller_and_never_larger() -> None:
    """Buying costs the offer plus the fee, so paying to deal puts less on, never more."""
    model = Belief(p=0.5, lo=0.4, hi=0.6, owner="model")

    free = ceiling_of(an_edge(model=model, bid=0.1, offer=0.2, fee=0.0))
    charged = ceiling_of(an_edge(model=model, bid=0.1, offer=0.2, fee=0.05))

    assert charged.fraction is not None and free.fraction is not None
    assert charged.fraction < free.fraction


def test_the_fee_makes_a_seller_s_ceiling_smaller_too() -> None:
    """Selling is paid the bid **less** the fee, so paying to deal puts less on, never more.

    The buying side has its own test above; without this one the fee's sign on the
    selling side is free, and a fee that helped the seller would go unnoticed.
    """
    model = Belief(p=0.4, lo=0.3, hi=0.5, owner="model")

    free = ceiling_of(an_edge(model=model, bid=0.8, offer=0.9, fee=0.0))
    charged = ceiling_of(an_edge(model=model, bid=0.8, offer=0.9, fee=0.05))

    assert free.taken_by == "selling" and charged.taken_by == "selling"
    assert charged.fraction is not None and free.fraction is not None
    assert charged.fraction < free.fraction


def test_an_unknown_fee_is_read_as_nothing_and_the_edge_says_it_is_unknown() -> None:
    """The ceiling cannot invent a fee; the edge it came from carries the absence."""
    model = Belief(p=0.5, lo=0.4, hi=0.6, owner="model")

    unknown = ceiling_of(an_edge(model=model, bid=0.1, offer=0.2, fee=None))
    free = ceiling_of(an_edge(model=model, bid=0.1, offer=0.2, fee=0.0))

    assert unknown.fraction == free.fraction


def test_a_wider_range_about_the_same_point_never_raises_the_ceiling() -> None:
    """The range is the model's own statement of how unsure it is, so widening it costs."""
    narrow = ceiling_of(
        an_edge(model=Belief(p=0.5, lo=0.45, hi=0.55, owner="model"), bid=0.1, offer=0.2)
    )
    wide = ceiling_of(
        an_edge(model=Belief(p=0.5, lo=0.3, hi=0.7, owner="model"), bid=0.1, offer=0.2)
    )

    assert narrow.fraction is not None and wide.fraction is not None
    assert wide.fraction <= narrow.fraction


def test_the_ceiling_is_never_the_one_the_middle_of_the_range_would_give() -> None:
    """A ceiling at the middle is a ceiling that ignores what the model said about itself."""
    model = Belief(p=0.5, lo=0.4, hi=0.6, owner="model")

    honest = ceiling_of(an_edge(model=model, bid=0.1, offer=0.2))
    flattering = (model.p - 0.2) / (1.0 - 0.2) / QUARTER

    assert honest.fraction is not None
    assert honest.fraction < flattering


# --- Zero, and absent -------------------------------------------------------


def test_agreeing_with_the_market_gives_a_ceiling_of_exactly_zero() -> None:
    """Bid and offer both the model's own number, no fee, no range: nothing to put on.

    Built from the world the same way its twin for the edge is: the prices are the
    model's own number, so buying and selling are each worth exactly nothing, and
    the ceiling is zero to the last bit rather than nearly zero.
    """
    agreed = Belief(p=0.42, lo=0.42, hi=0.42, owner="model")

    ceiling = ceiling_of(an_edge(model=agreed, bid=agreed.p, offer=agreed.p, fee=0.0))

    assert ceiling.fraction == 0.0
    assert ceiling.sentence == NOTHING_WORTH_TAKING
    assert ceiling.taken_by is None


def test_a_price_inside_the_no_trade_band_gives_zero_with_its_reason() -> None:
    """The model's number sits inside the venue's own two prices, so neither side is worth it."""
    edge = an_edge(model=Belief(p=0.5, lo=0.5, hi=0.5, owner="model"), bid=0.45, offer=0.55)

    ceiling = ceiling_of(edge)

    assert ceiling.fraction == 0.0
    assert ceiling.sentence == NOTHING_WORTH_TAKING


def test_a_range_that_does_not_agree_which_side_to_be_gives_zero_with_its_own_reason() -> None:
    """A different zero from the one above, and the card says which.

    Where the edge is worth taking at one end of the model's range and not at the
    other, the model's own range does not agree which side of this price to be. The
    edge already works that out; the ceiling reads it and refuses to name a size.
    """
    edge = an_edge(
        model=Belief(p=0.5, lo=0.1, hi=0.9, owner="model"),
        bid=0.45,
        offer=0.55,
        straddles=True,
    )

    ceiling = ceiling_of(edge)

    assert ceiling.fraction == 0.0
    assert ceiling.sentence == THE_RANGE_DISAGREES
    assert ceiling.sentence != NOTHING_WORTH_TAKING


def test_a_refused_edge_leaves_the_ceiling_absent_and_not_zero() -> None:
    """Absent means there was no arithmetic to run. It is never a blank and never a nought."""
    ceiling = ceiling_of(a_refusal())

    assert ceiling.fraction is None
    assert ceiling.sentence is not None
    assert ceiling.sentence.startswith(A_CEILING_NEEDS_AN_EDGE)
    assert "No contract quotes this claim" in ceiling.sentence


@pytest.mark.parametrize(
    "reason", ["conditional_world", "no_contract", "no_quote", "settled_market"]
)
def test_every_refusal_carries_its_own_sentence_into_the_ceiling(reason: str) -> None:
    """One rule, not four: whichever way the edge was refused, the ceiling says that reason."""
    refused = a_refusal(reason)

    ceiling = ceiling_of(refused)

    assert ceiling.fraction is None
    assert ceiling.sentence == f"{A_CEILING_NEEDS_AN_EDGE} {refused.sentence}"


def test_a_price_at_everything_leaves_nothing_to_buy() -> None:
    """An offer of one for something that pays one at most cannot be worth buying."""
    edge = an_edge(model=Belief(p=1.0, lo=1.0, hi=1.0, owner="model"), bid=1.0, offer=1.0, fee=0.0)

    ceiling = ceiling_of(edge)

    assert ceiling.fraction == 0.0


def test_a_bid_of_nothing_leaves_nothing_to_sell() -> None:
    """Being paid nothing to take on a liability is not a trade at any size."""
    edge = an_edge(model=Belief(p=0.0, lo=0.0, hi=0.0, owner="model"), bid=0.0, offer=0.0, fee=0.0)

    ceiling = ceiling_of(edge)

    assert ceiling.fraction == 0.0


# --- What it always carries -------------------------------------------------


@pytest.mark.parametrize(
    "ceiling",
    [
        ceiling_of(an_edge(model=Belief(p=0.5, lo=0.4, hi=0.6, owner="model"), bid=0.1, offer=0.2)),
        ceiling_of(
            an_edge(model=Belief(p=0.5, lo=0.5, hi=0.5, owner="model"), bid=0.45, offer=0.55)
        ),
        ceiling_of(a_refusal()),
    ],
)
def test_the_warning_travels_on_the_value(ceiling: Ceiling) -> None:
    """A warning written into a screen is a warning one screen has.

    Carried on the value, every screen and the export have the same one and none of
    them can print the number without it.
    """
    assert ceiling.warning == NEVER_SIZE_TO_THIS
    assert ceiling.warning == "never size to this"
