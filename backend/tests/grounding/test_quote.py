"""What a quote is allowed to be, and what a venue's price becomes on a tile.

Four rules are checked here, and each of them is a way this product could have
printed a number nobody can trace to an input, a rule or a source.

* **A venue publishes no range.** Its bid and its offer differ because dealing
  costs something, not because the venue is unsure. An earlier draft of this
  product turned a two-point spread into a seven-point range and wrote it on the
  tile. The market's likelihood is a point.
* **Only a venue's own number fills the market slot.** A price the reader typed is
  their report of what they could deal at; it never becomes the market's voice.
* **A quote read from a venue carries the venue's facts, and a typed one carries
  none of them.** An absent field stays absent rather than being filled in with
  something plausible.
* **The midpoint is worked out from the two prices**, so it can never disagree
  with them.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from katalyst.grounding import Quote, market_belief
from katalyst.grounding.quote import (
    ALWAYS_FROM_A_VENUE,
    SOMETIMES_FROM_A_VENUE,
    VENUE_FIELDS,
)
from tests.strategies import quotes

THE_FOUR_FLAGS = ("active", "closed", "archived", "accepting_orders")
"""The four words the venue says about whether one of its markets can be traded."""

many = settings(max_examples=50, deadline=None)


@given(quote=quotes(source="recorded"))
@many
def test_a_market_belief_has_no_invented_range(quote: Quote) -> None:
    """A likelihood built from a venue's price is a point: its low, middle and high agree."""
    belief = market_belief(quote)

    assert belief.owner == "market"
    assert belief.lo == belief.p == belief.hi
    assert belief.p == quote.midpoint


@given(quote=quotes(source="user"))
@many
def test_a_reader_entered_price_never_fills_the_market_belief(quote: Quote) -> None:
    """A price the reader typed is refused by name, rather than quietly becoming the market's."""
    with pytest.raises(ValueError, match="never fills the market's likelihood"):
        market_belief(quote)


@given(quote=quotes())
@many
def test_the_midpoint_sits_between_the_two_prices(quote: Quote) -> None:
    """The number shown to a reader is worked out from the two prices and lies between them."""
    assert quote.bid <= quote.midpoint <= quote.offer
    assert quote.midpoint == (quote.bid + quote.offer) / 2.0


@given(quote=quotes(source="fetched"))
@many
def test_a_venue_quote_carries_what_a_venue_always_gives(quote: Quote) -> None:
    """Nothing read from a venue is missing a fact every venue answer carries.

    Twelve of them, measured over the 1,693 real market records this repository
    saved: the venue, its three identifiers, the side priced, its own question and
    rules, a web address and its four state flags. The five it sometimes leaves out
    are a different list and are not demanded here.
    """
    for named in ALWAYS_FROM_A_VENUE:
        assert getattr(quote, named) is not None, named
    assert quote.side in ("yes", "no")


@given(quote=quotes(source="user"))
@many
def test_a_typed_price_carries_none_of_them(quote: Quote) -> None:
    """A reader knows a price, not a contract's on-chain identifier, so those stay absent."""
    for named in VENUE_FIELDS:
        assert getattr(quote, named) is None, named


@given(quote=quotes(source="user"))
@many
def test_a_typed_price_is_live_because_that_is_what_typing_one_means(quote: Quote) -> None:
    """A reader reporting what they can get now is reporting something they can deal at.

    They are not asked about the venue's own bookkeeping and it is not invented for
    them, so the four flags stay absent and this is read from what a typed price
    means rather than from a flag nobody set.
    """
    assert quote.live is True
    assert quote.active is None and quote.closed is None


@given(quote=quotes(source="recorded"), named=st.sampled_from(ALWAYS_FROM_A_VENUE))
@many
def test_a_venue_quote_missing_a_venue_fact_is_refused(quote: Quote, named: str) -> None:
    """Taking away any one fact every venue answer carries is refused, and it is named."""
    with pytest.raises(ValueError, match=f"missing.*{named}"):
        Quote(**{**quote.model_dump(), named: None})


@given(quote=quotes(source="recorded"), named=st.sampled_from(SOMETIMES_FROM_A_VENUE))
@many
def test_a_venue_quote_without_a_field_the_venue_omits_still_reads(
    quote: Quote, named: str
) -> None:
    """A venue leaving out a size, a volume, an end date or a dealing amount is ordinary.

    154 of the 1,693 saved market records carry no resting size, 189 no traded
    volume and 24 no end date. Demanding them would refuse working markets.
    """
    without = Quote(**{**quote.model_dump(), named: None})

    assert getattr(without, named) is None
    assert without.venue == quote.venue


@given(quote=quotes(source="user"), venue=...)
@many
def test_a_typed_price_wearing_a_venues_facts_is_refused(quote: Quote, venue: str) -> None:
    """A price the reader typed cannot be dressed up as a venue's by naming one."""
    with pytest.raises(ValueError, match="nothing a venue would have told us"):
        Quote(**{**quote.model_dump(), "venue": venue})


@given(quote=quotes(source="recorded"))
@many
def test_a_crossed_book_is_refused(quote: Quote) -> None:
    """A bid above its offer is not a price anybody could deal at, so it is not a quote."""
    with pytest.raises(ValueError, match="must not be above its best offer"):
        Quote(**{**quote.model_dump(), "bid": 1.0, "offer": 0.0})


@given(quote=quotes(source="recorded", live=True))
@many
def test_a_market_an_order_could_be_placed_on_reads_live(quote: Quote) -> None:
    """All four of the venue's own words have to agree before a market counts as tradeable."""
    assert quote.live is True
    assert (quote.active, quote.closed, quote.archived, quote.accepting_orders) == (
        True,
        False,
        False,
        True,
    )


@given(quote=quotes(source="recorded", live=False))
@many
def test_a_market_no_order_could_be_placed_on_reads_settled(quote: Quote) -> None:
    """And one the venue has closed, put away or stopped calling active reads settled.

    Whatever its two prices happen to be: a finished market keeps serving a
    plausible book, and the one this repository saved reads .999 against 1.00.
    """
    assert quote.live is False


@given(quote=quotes(source="recorded", live=True), named=st.sampled_from(THE_FOUR_FLAGS))
@many
def test_every_one_of_the_four_flags_can_stop_a_market_being_live(quote: Quote, named: str) -> None:
    """Turn any one of the four the other way and the market is no longer tradeable.

    Two flags is what the chapter first named and what 226 of the 1,693 real market
    records saved here get wrong: they say they are open and taking orders while
    also saying they are not active.
    """
    turned = Quote(**{**quote.model_dump(), named: not getattr(quote, named)})

    assert turned.live is False
