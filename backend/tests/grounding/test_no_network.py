"""No test that touches a price touches the network, and that is checked rather than promised.

A test that passes because nothing tried to dial out would pass just as happily on
the day something did and the connection happened to succeed. So this file does
two things: it shows that the guard every test in these two directories runs under
really refuses a connection, and it then runs the whole of the price path under
that guard — reading the committed file, working a quote out of the venue's own
answers, turning it into the market's likelihood, and pricing a claim against it.

If somebody later puts a live read on any of those paths, this test is where it
fails, by name, on the line that reached out.
"""

import socket
from datetime import date

import pytest

from katalyst.domain import (
    Belief,
    Beliefs,
    ContractPayoff,
    Graph,
    Proposition,
    Resolution,
    World,
    propagate,
)
from katalyst.grounding import Quote, every_recorded_quote, market_belief, recorded_quote
from katalyst.thesis import Edge, priced
from tests.outbound import WentOutbound

HORMUZ_MARKET = "3501950"
DAY_ZERO = date(2026, 9, 21)


def test_the_guard_really_refuses_a_connection() -> None:
    """Opening a connection under the guard raises, so the test below is not passing vacuously."""
    with pytest.raises(WentOutbound):
        socket.create_connection(("example.invalid", 443), timeout=1)

    with pytest.raises(WentOutbound), socket.socket() as one:
        one.connect(("example.invalid", 443))


def test_no_quote_test_touches_the_network() -> None:
    """The whole price path runs with every outbound connection refused."""
    quote = recorded_quote(HORMUZ_MARKET)
    assert quote is not None
    assert every_recorded_quote() != ()

    belief = market_belief(quote)
    assert belief.owner == "market"

    world = _a_world_whose_ending_names(quote)
    answer = priced(world, world, "ending", quote, fee=None)

    assert isinstance(answer, Edge)
    assert answer.quote is quote
    assert answer.fee is None


def _a_world_whose_ending_names(quote: Quote) -> World:
    """Build the smallest map with an ending that names this quote's contract, and work it out."""
    assert quote.venue is not None and quote.market_id is not None and quote.side is not None
    resolution = Resolution(criteria=quote.rules or "", source=quote.venue, by=date(2026, 11, 1))
    prior = Belief(p=0.35, lo=0.22, hi=0.5, owner="model")
    graph = Graph(
        id="one-ending",
        hypothesis_id="start",
        propositions=(
            Proposition(
                id="start",
                claim="The strait returns to normal traffic.",
                kind="hypothesis",
                resolution=resolution,
                prior=prior,
                beliefs=Beliefs(model=prior),
            ),
            Proposition(
                id="ending",
                claim="The contract the venue quotes on that question pays out.",
                kind="market",
                resolution=resolution,
                prior=prior,
                beliefs=Beliefs(model=prior),
                payoff=ContractPayoff(
                    venue=quote.venue,
                    contract_id=quote.market_id,
                    title=quote.question or "",
                    side=quote.side,
                ),
            ),
        ),
        links=(),
    )
    return propagate(graph, (), as_of=DAY_ZERO, seed=1, versions=8, worlds=2)
