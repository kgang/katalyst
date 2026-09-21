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

from katalyst.grounding import Quote, market_belief
from tests.strategies import quotes

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
def test_a_venue_quote_carries_the_venues_own_facts(quote: Quote) -> None:
    """Nothing read from a venue is missing the venue's name, its identifiers or its rules."""
    assert quote.venue is not None
    assert quote.condition_id is not None
    assert quote.market_id is not None
    assert quote.token_id is not None
    assert quote.side in ("yes", "no")
    assert quote.question and quote.rules
    assert quote.ends is not None
    assert quote.tick is not None and quote.tick > 0.0
    assert quote.url is not None


@given(quote=quotes(source="user"))
@many
def test_a_typed_price_carries_none_of_them(quote: Quote) -> None:
    """A reader knows a price, not a contract's on-chain identifier, so those stay absent."""
    assert quote.venue is None
    assert quote.condition_id is None
    assert quote.market_id is None
    assert quote.token_id is None
    assert quote.side is None
    assert quote.question is None
    assert quote.rules is None
    assert quote.ends is None
    assert quote.tick is None
    assert quote.url is None


@given(quote=quotes(source="recorded"))
@many
def test_a_venue_quote_missing_a_venue_fact_is_refused(quote: Quote) -> None:
    """Taking one of the venue's own facts off a venue's quote is refused, and it is named."""
    with pytest.raises(ValueError, match="missing"):
        Quote(**{**quote.model_dump(), "condition_id": None})


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


@given(quote=quotes(live=True))
@many
def test_a_market_the_venue_says_is_open_reads_live(quote: Quote) -> None:
    """Whether a market is still trading is read from the venue's two flags and nothing else."""
    assert quote.live is True
    assert quote.closed is False
    assert quote.accepting_orders is True


@given(quote=quotes(live=False))
@many
def test_a_market_the_venue_says_has_finished_reads_settled(quote: Quote) -> None:
    """And a finished one reads finished whatever its two prices happen to be."""
    assert quote.live is False
