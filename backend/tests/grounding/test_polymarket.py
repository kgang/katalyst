"""Reading the venue's real answers, saved once and never fetched again.

Every answer read here was saved from the live venue on 2026-09-21 and is in this
repository word for word: the Strait of Hormuz market and its order book, in
`backend/recordings/quotes/`, and one finished market from the September WTI event
in `responses/` beside this file. Nothing is a hand-written imitation of an
interface, because four things about this one are surprising and each would give
a plausible wrong number:

* the two sides of a book arrive worst-price-first, so the first bid in the saved
  answer is `.01` where the best bid is `.06`;
* the outcomes, their identifiers and the displayed prices are strings holding
  more JSON;
* a finished market keeps serving a book, and that book reads almost certain;
* the displayed price is rounded and is not the midpoint.

No test in this file opens a connection. The fixture in `conftest.py` makes that
mechanical rather than a promise.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from katalyst.grounding import Quote, quote_from, read_book, recorded_quote, refresh
from katalyst.grounding.polymarket import MARKET_PAGE, VENUE, _slug_of

SAVED = Path(__file__).parent / "responses"
HORMUZ_MARKET = "3501950"


def committed() -> dict[str, Any]:
    """Read the committed quote file back as it sits on disk: the venue's own two answers."""
    found = sorted(
        (Path(__file__).resolve().parents[2] / "recordings" / "quotes").glob(
            f"{HORMUZ_MARKET}-*.json"
        )
    )
    assert found, "the committed quote for the Hormuz contract is missing"
    parsed: dict[str, Any] = json.loads(found[-1].read_text(encoding="utf-8"))
    return parsed


def settled_market() -> dict[str, Any]:
    """Read the saved answer for a market the venue says has finished."""
    held: dict[str, Any] = json.loads((SAVED / "settled-market.json").read_text(encoding="utf-8"))
    market: dict[str, Any] = held["market"]
    return market


def test_the_best_bid_is_the_last_bid() -> None:
    """The best of each side is its best price, which in this saved answer is not its first.

    A reader of the first line of each side would have taken the *worst* price in
    the book. The numbers below are all read out of the saved answer, so the gap
    between the first bid and the best bid is the venue's own and not one typed
    here.
    """
    book = committed()["book"]
    bids = [float(one["price"]) for one in book["bids"]]
    offers = [float(one["price"]) for one in book["asks"]]

    read = read_book(book)

    assert read.bid == max(bids)
    assert read.offer == min(offers)
    # The two things that make reading by position a trap, in this real answer.
    assert read.bid == bids[-1] != bids[0]
    assert read.offer == offers[-1] != offers[0]
    assert read.bid > bids[0]


def test_a_settled_market_is_read_from_its_flags() -> None:
    """A finished market reads finished although its book still reads almost certain.

    Two halves. First, the saved answer really is the trap: the venue's own flags
    say the market has closed and is taking no orders, while its book sits within
    one price step of certainty — so anyone deciding from the numbers would show it
    as a live market at nearly even money against nothing. Second, a quote carrying
    those flags and those prices reads settled.
    """
    market = settled_market()
    step = float(market["orderPriceMinTickSize"])
    book_says = (float(market["bestBid"]) + float(market["bestAsk"])) / 2.0
    still_trading = recorded_live_quote()

    assert market["closed"] is True
    assert market["acceptingOrders"] is False
    # Its book sits within one price step of certainty, and reads far more confident
    # than the market that really is still trading — so a reader who decided from
    # the numbers would have it exactly the wrong way round.
    assert 1.0 - book_says < step
    assert book_says > still_trading.midpoint

    # A quote carrying that market's flags and its two prices. Everything else is
    # the committed Hormuz quote's, so that nothing here is typed by hand.
    finished = recorded_live_quote().model_copy(
        update={
            "closed": bool(market["closed"]),
            "accepting_orders": bool(market["acceptingOrders"]),
            "bid": float(market["bestBid"]),
            "offer": float(market["bestAsk"]),
        }
    )

    assert finished.live is False
    assert finished.midpoint > 0.99


def recorded_live_quote() -> Quote:
    """The committed Hormuz quote, which the venue's own flags say is still trading."""
    quote = recorded_quote(HORMUZ_MARKET)
    assert quote is not None
    return quote


def test_a_quote_reads_the_side_it_priced_off_the_market_record() -> None:
    """Which outcome a price is for is worked out by matching identifiers, never assumed."""
    held = committed()
    market = next(
        one for one in held["event"]["markets"] if one["conditionId"] == held["book"]["market"]
    )
    identifiers = json.loads(market["clobTokenIds"])
    outcomes = json.loads(market["outcomes"])
    priced_side = outcomes[identifiers.index(held["book"]["asset_id"])].strip().lower()

    quote = quote_from(held["event"], held["book"], source="recorded")

    assert quote.side == priced_side
    assert quote.token_id == held["book"]["asset_id"]
    assert quote.condition_id == held["book"]["market"]
    assert quote.venue == VENUE


def test_the_other_side_of_the_same_contract_reads_as_the_other_side() -> None:
    """One contract, two outcomes, two books: the side is matched, never assumed to be yes."""
    held = committed()
    identifiers = json.loads(_market_in(held)["clobTokenIds"])
    outcomes = [one.strip().lower() for one in json.loads(_market_in(held)["outcomes"])]
    yes_side = quote_from(held["event"], held["book"], source="recorded")

    other = quote_from(
        held["event"],
        {**held["book"], "asset_id": identifiers[1 - identifiers.index(yes_side.token_id)]},
        source="recorded",
    )

    assert {yes_side.side, other.side} == set(outcomes)
    assert other.condition_id == yes_side.condition_id
    assert other.token_id != yes_side.token_id


def test_an_outcome_the_market_does_not_list_is_refused() -> None:
    """A book for an outcome this market does not have is named, never priced anyway."""
    held = committed()

    with pytest.raises(ValueError, match="not one of the outcomes"):
        quote_from(
            held["event"],
            {**held["book"], "asset_id": "an-outcome-nobody-issued"},
            source="recorded",
        )


def test_an_outcome_that_is_not_yes_or_no_is_refused() -> None:
    """This program prices a contract with two outcomes, so a third is refused by name."""
    held = committed()
    market = _market_in(held)
    renamed = {
        **held["event"],
        "markets": [{**market, "outcomes": json.dumps(["Maybe", "No"])}],
    }

    with pytest.raises(ValueError, match="calls this outcome 'maybe'"):
        quote_from(renamed, held["book"], source="recorded")


def test_a_quote_never_reads_the_displayed_price() -> None:
    """The venue's own displayed figure is rounded, so the midpoint is worked out instead.

    On this saved answer the two happen to round to the same two figures; what the
    test pins is that the midpoint comes from the book, not from the display, by
    comparing it with the book's own two sides.
    """
    held = committed()
    displayed = [float(one) for one in json.loads(_market_in(held)["outcomePrices"])]

    quote = quote_from(held["event"], held["book"], source="recorded")
    book = read_book(held["book"])

    assert quote.midpoint == (book.bid + book.offer) / 2.0
    assert quote.midpoint != displayed[0] or quote.bid != quote.offer


def _market_in(held: dict[str, Any]) -> dict[str, Any]:
    """Find the market in a committed file that the saved order book belongs to."""
    market: dict[str, Any] = next(
        one for one in held["event"]["markets"] if one["conditionId"] == held["book"]["market"]
    )
    return market


def test_a_book_with_an_empty_side_is_refused() -> None:
    """A side with nothing on it has no best price, so it is refused rather than patched."""
    held = committed()

    with pytest.raises(ValueError, match="nothing on its bids side"):
        read_book({**held["book"], "bids": []})


def test_an_order_book_for_another_contract_is_refused() -> None:
    """Two answers that should describe one contract and do not are named, never guessed past."""
    held = committed()
    elsewhere = {**held["book"], "market": "0xnot-this-contract"}

    with pytest.raises(ValueError, match="not one of the markets"):
        quote_from(held["event"], elsewhere, source="recorded")


def test_the_web_address_carries_the_venues_own_name_for_the_market() -> None:
    """The address a reader clicks is the market page plus the venue's slug, and back again."""
    held = committed()

    quote = quote_from(held["event"], held["book"], source="recorded")

    assert quote.url == MARKET_PAGE + held["event"]["slug"]
    assert quote.url is not None
    assert _slug_of(quote.url) == held["event"]["slug"]


def test_a_refresh_reads_the_venue_into_exactly_the_shape_a_recording_has() -> None:
    """Asking the venue again gives back the same shape, differing only in how it got here.

    The reader's own machine never leaves the room in this test: the thing that
    would fetch an address is handed in, and it serves the very answers the
    committed file holds. That is the point of recorded-first — the recorded path
    and the live path are one piece of parsing, so a replay is the real thing
    played back.
    """
    held = committed()
    asked: list[str] = []

    def saved_answers(address: str) -> Any:
        asked.append(address)
        return [held["event"]] if "events" in address else held["book"]

    recorded = recorded_live_quote()
    again = refresh(recorded, ask=saved_answers)

    assert again.refresh_failed is None
    assert again.quote.source == "fetched"
    assert again.quote.model_dump(exclude={"source"}) == recorded.model_dump(exclude={"source"})
    assert len(asked) == 2
    assert recorded.token_id is not None and recorded.token_id in asked[1]


def test_a_refresh_that_cannot_reach_the_venue_keeps_the_recorded_price() -> None:
    """A failed read keeps the price already on file and says, in one sentence, that it failed."""
    recorded = recorded_live_quote()

    def nothing_answers(address: str) -> Any:
        raise TimeoutError(address)

    again = refresh(recorded, ask=nothing_answers)

    assert again.quote == recorded
    assert again.refresh_failed is not None
    assert VENUE in again.refresh_failed
    assert "TimeoutError" in again.refresh_failed


def test_a_refresh_of_a_typed_price_has_nothing_to_ask() -> None:
    """A price the reader typed names no market, so there is nowhere to read it again from."""
    typed = Quote(
        bid=0.41,
        offer=0.41,
        as_of=recorded_live_quote().as_of,
        source="user",
        closed=False,
        accepting_orders=True,
    )

    def never_called(address: str) -> Any:  # pragma: no cover - the point is that it is not
        raise AssertionError(f"nothing should have been asked, but {address} was")

    again = refresh(typed, ask=never_called)

    assert again.quote == typed
    assert again.refresh_failed is not None
    assert "typed" in again.refresh_failed
