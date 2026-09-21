"""Reading the venue's real answers, saved once and never fetched again.

Every answer read here was saved from the live venue on 2026-09-21 and is in this
repository word for word: the Strait of Hormuz market and its order book, in
`backend/recordings/quotes/`, and a handful of whole market records in
`responses/` beside this file, each kept because it is a shape the parser has to
survive. Nothing is a hand-written imitation of an interface, because the
surprising parts of this one all give a plausible wrong number rather than an
error:

* the two sides of a book arrive worst-price-first, so the first bid in the saved
  answer is `.01` where the best bid is `.06`;
* the outcomes, their identifiers and the displayed prices are strings holding
  more JSON;
* a finished market keeps serving a book, and that book reads almost certain;
* the displayed price is rounded and is not the midpoint;
* and a venue answer is allowed to leave fields out — 154 of the 1,693 markets
  saved here carry no resting size, 189 no traded volume, 24 no end date — so a
  parser that indexes them refuses ordinary, working markets.

**The order book a market record implies.** The venue gives the two prices on the
market record and the instant only on an order book, and this repository saved one
book. So a test that has to reach a market whose book was never read builds the
book that market's own best bid and best offer imply, borrowing the instant and
the two smallest dealing amounts from the book that *was* read. Every number a
test asserts on comes from the market record; nothing asserted here depends on the
borrowed instant.

No test in this file opens a connection. The fixture in `conftest.py` makes that
mechanical rather than a promise.
"""

import json
import random
from pathlib import Path
from typing import Any

import pytest

from katalyst.grounding import Quote, quote_from, read_book, recorded_quote, refresh
from katalyst.grounding.polymarket import MARKET_PAGE, VENUE, _slug_of

SAVED = Path(__file__).parent / "responses"
HORMUZ_MARKET = "3501950"
RECORDINGS = Path(__file__).resolve().parents[2] / "recordings" / "quotes"


def committed() -> dict[str, Any]:
    """Read the committed quote file back as it sits on disk: the venue's own two answers."""
    found = sorted(RECORDINGS.glob(f"{HORMUZ_MARKET}-*.json"))
    assert found, "the committed quote for the Hormuz contract is missing"
    parsed: dict[str, Any] = json.loads(found[-1].read_text(encoding="utf-8"))
    return parsed


def settled_market() -> dict[str, Any]:
    """Read the saved answer for a market the venue says has finished."""
    held: dict[str, Any] = json.loads((SAVED / "settled-market.json").read_text(encoding="utf-8"))
    market: dict[str, Any] = held["market"]
    return market


def saved_market_records() -> list[dict[str, Any]]:
    """Every whole market record saved beside this file, with the note saying why it is here."""
    held = json.loads((SAVED / "market-records.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = list(held["records"])
    return records


def a_book_for(market: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    """The order book a market record's own two best prices imply.

    The venue gives the prices on the market record and the instant only on a book,
    so the instant, the smallest price step and the smallest order are borrowed
    from the one real book this repository saved. Nothing any test asserts on
    depends on them.

    Args:
        market: One whole market record, as the venue sent it.
        token: Which outcome to price. The first one by default.

    Returns:
        An order-book answer in the venue's own shape.
    """
    real = committed()["book"]
    identifiers = json.loads(str(market["clobTokenIds"]))
    return {
        "market": market["conditionId"],
        "asset_id": token or identifiers[0],
        "timestamp": real["timestamp"],
        "bids": [{"price": str(market["bestBid"]), "size": "10"}],
        "asks": [{"price": str(market["bestAsk"]), "size": "10"}],
        "tick_size": str(market.get("orderPriceMinTickSize") or real["tick_size"]),
        "min_order_size": str(market.get("orderMinSize") or real["min_order_size"]),
    }


def an_event_around(record: dict[str, Any]) -> dict[str, Any]:
    """The smallest event record that carries one saved market: its slug and that market."""
    return {"id": "event", "slug": record["event_slug"], "markets": [record["market"]]}


def recorded_live_quote() -> Quote:
    """The committed Hormuz quote, which the venue's own flags say is still trading."""
    quote = recorded_quote(HORMUZ_MARKET)
    assert quote is not None
    return quote


def _market_in(held: dict[str, Any]) -> dict[str, Any]:
    """Find the market in a committed file that the saved order book belongs to."""
    market: dict[str, Any] = next(
        one for one in held["event"]["markets"] if one["conditionId"] == held["book"]["market"]
    )
    return market


# --- Reading a book --------------------------------------------------------


def test_the_best_bid_is_not_the_first_bid() -> None:
    """The best of each side is its best price, wherever in the answer that price sits.

    Two mutations have to fail here and only one of them used to. Reading the
    **first** line of a side takes the worst price in it — `.01` against a best bid
    of `.06` in this real answer. Reading the **last** happens to be right on
    today's ordering and is a rule about the venue's habits rather than about what
    *best* means, so the sides are shuffled and the same answer demanded: with the
    book stirred, the last line is not the best one either.
    """
    book = committed()["book"]
    bids = [float(one["price"]) for one in book["bids"]]
    offers = [float(one["price"]) for one in book["asks"]]

    read = read_book(book)

    assert read.bid == max(bids) != bids[0]
    assert read.offer == min(offers) != offers[0]

    stirred = random.Random(6).sample  # one settled order, so a failure reads the same twice
    shuffled = {
        **book,
        "bids": stirred(book["bids"], len(book["bids"])),
        "asks": stirred(book["asks"], len(book["asks"])),
    }
    # The stirring really did move the best price off the end of each side, so the
    # assertions below are about the rule and not about the ordering.
    assert float(shuffled["bids"][-1]["price"]) != read.bid
    assert float(shuffled["asks"][-1]["price"]) != read.offer

    again = read_book(shuffled)

    assert (again.bid, again.offer) == (read.bid, read.offer)


def test_a_book_with_an_empty_side_is_refused() -> None:
    """A side with nothing on it has no best price, so it is refused rather than patched."""
    held = committed()

    with pytest.raises(ValueError, match="nothing on its bids side"):
        read_book({**held["book"], "bids": []})


def test_a_book_missing_a_number_is_refused_by_name() -> None:
    """A book without its smallest price step says so, rather than raising something bare."""
    held = committed()

    with pytest.raises(ValueError, match="no readable 'tick_size'"):
        read_book({key: value for key, value in held["book"].items() if key != "tick_size"})


def test_an_instant_in_seconds_is_refused_rather_than_dating_a_price_to_1970() -> None:
    """The venue sends milliseconds; the same number as seconds silently reads as 1970."""
    held = committed()
    as_seconds = str(int(held["book"]["timestamp"]) // 1000)

    with pytest.raises(ValueError, match="prediction markets existed"):
        read_book({**held["book"], "timestamp": as_seconds})


# --- Reading a market record -----------------------------------------------


def test_a_settled_market_is_read_from_its_flags() -> None:
    """A finished market reads finished although its book still reads almost certain.

    The whole of it goes through the parser: the venue's own saved answer for a
    market it says has closed, with the book that answer's own two prices imply. No
    quote is assembled by hand here, because the row of the decision table this
    feeds exists precisely for answers like this one.
    """
    market = settled_market()
    step = float(market["orderPriceMinTickSize"])
    still_trading = recorded_live_quote()

    finished = quote_from(
        {"id": "event", "slug": "what-price-will-wti-hit-in-september-2026", "markets": [market]},
        a_book_for(market),
        source="recorded",
    )

    assert finished.live is False
    assert finished.closed is True
    assert finished.accepting_orders is False
    # Its book sits within one price step of certainty and reads far more confident
    # than the market that really is still trading, so a reader deciding from the
    # numbers would have the two exactly the wrong way round.
    assert 1.0 - finished.midpoint < step
    assert finished.midpoint > still_trading.midpoint
    assert still_trading.live is True


def test_a_market_the_venue_says_is_not_active_is_not_live() -> None:
    """All four flags are read, because two of them call 226 real markets tradeable.

    Of the 1,693 market records saved here, 226 say they are open and taking orders
    while also saying they are not active, and one of those says it is archived as
    well. The record below is one of them, word for word.
    """
    for record in saved_market_records():
        market = record["market"]
        if market.get("active") is not False:
            continue
        quote = quote_from(an_event_around(record), a_book_for(market), source="recorded")

        assert quote.closed is False
        assert quote.accepting_orders is True
        assert quote.active is False
        assert quote.live is False, record["why"]
        return
    raise AssertionError("no saved record shows a market the venue says is not active")


def test_a_market_the_venue_has_archived_is_not_live() -> None:
    """Archived is the fourth flag, and it is read too."""
    for record in saved_market_records():
        market = record["market"]
        if market.get("archived") is not True:
            continue
        quote = quote_from(an_event_around(record), a_book_for(market), source="recorded")

        assert quote.archived is True
        assert quote.live is False, record["why"]
        return
    raise AssertionError("no saved record shows a market the venue has archived")


def test_a_venue_answer_that_leaves_a_field_out_still_reads() -> None:
    """A venue leaving out a size, a volume or an end date is an ordinary answer.

    Absent stays absent: never nought, which would read as an empty book or a
    market settling today. Each record below is a real one, kept because the venue
    left exactly one of those out of it.
    """
    absent = {
        "liquidityNum": "resting",
        "volumeNum": "traded",
        "endDateIso": "ends",
    }
    seen: set[str] = set()
    for record in saved_market_records():
        market = record["market"]
        for sent, called in absent.items():
            if sent in market:
                continue
            quote = quote_from(an_event_around(record), a_book_for(market), source="recorded")

            assert getattr(quote, called) is None, record["why"]
            assert quote.venue == VENUE
            seen.add(sent)
    assert seen == set(absent), f"no saved record is missing {sorted(set(absent) - seen)}"


def test_every_saved_market_record_reads_or_says_why() -> None:
    """The parser survives every real answer saved here, or refuses it with a sentence.

    Nothing may come out of it but a quote or a `ValueError` carrying words a person
    can act on. A bare `KeyError` on a field the venue simply omitted is the defect
    this test exists to keep out: it reports the venue as unreadable when the venue
    answered perfectly well.
    """
    records = saved_market_records()
    assert len(records) >= 5, "too few saved shapes for this to be checking anything"
    quotes, refusals = 0, 0
    for record in records:
        try:
            quote_from(an_event_around(record), a_book_for(record["market"]), source="recorded")
            quotes += 1
        except ValueError as refused:
            assert str(refused).strip(), record["why"]
            refusals += 1
    assert quotes >= 4
    assert refusals >= 1, "one saved record has outcomes that are not yes and no"


def test_a_market_whose_outcomes_are_not_yes_and_no_is_refused() -> None:
    """Six of the saved markets name their outcomes Up and Down; this program prices neither."""
    for record in saved_market_records():
        if "Up" not in str(record["market"].get("outcomes", "")):
            continue
        with pytest.raises(ValueError, match="calls this outcome"):
            quote_from(an_event_around(record), a_book_for(record["market"]), source="recorded")
        return
    raise AssertionError("no saved record has outcomes that are not yes and no")


def test_a_market_record_missing_something_every_answer_has_is_refused() -> None:
    """The twelve fields on every one of the 1,693 saved records are demanded, and named."""
    held = committed()
    market = _market_in(held)

    for named in ("question", "description", "id"):
        without = {key: value for key, value in market.items() if key != named}
        with pytest.raises(ValueError, match=f"no '{named}'"):
            quote_from({**held["event"], "markets": [without]}, held["book"], source="recorded")

    # And the event's own name for itself, which the web address is built from.
    with pytest.raises(ValueError, match="no 'slug'"):
        quote_from(
            {key: value for key, value in held["event"].items() if key != "slug"},
            held["book"],
            source="recorded",
        )

    for flag in ("active", "closed", "archived", "acceptingOrders"):
        without = {key: value for key, value in market.items() if key != flag}
        with pytest.raises(ValueError, match=f"whether it is '{flag}'"):
            quote_from({**held["event"], "markets": [without]}, held["book"], source="recorded")


# --- Identity --------------------------------------------------------------


def test_a_quote_reads_the_side_it_priced_off_the_market_record() -> None:
    """Which outcome a price is for is worked out by matching identifiers, never assumed."""
    held = committed()
    market = _market_in(held)
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


def test_an_order_book_for_another_contract_is_refused() -> None:
    """Two answers that should describe one contract and do not are named, never guessed past."""
    held = committed()
    elsewhere = {**held["book"], "market": "0xnot-this-contract"}

    with pytest.raises(ValueError, match="not one of the markets"):
        quote_from(held["event"], elsewhere, source="recorded")


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


def test_the_web_address_carries_the_venues_own_name_for_the_event() -> None:
    """The address a reader clicks is the event page plus the venue's slug, and back again.

    The event's, not the market's — an event can hold many markets, and the address
    this repository has a real answer for is the event's. The quote carries the
    venue's own question word for word, which is how a reader finds the market on a
    page holding several.
    """
    held = committed()

    quote = quote_from(held["event"], held["book"], source="recorded")

    assert quote.url == MARKET_PAGE + held["event"]["slug"]
    assert quote.url is not None
    assert _slug_of(quote.url) == held["event"]["slug"]


# --- Asking the venue again ------------------------------------------------


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
    assert "could not be reached" in again.refresh_failed
    assert "TimeoutError" in again.refresh_failed


def test_an_answer_this_program_cannot_read_does_not_blame_the_venue() -> None:
    """A venue that answered and a venue that is down are two different facts about two parties."""
    recorded = recorded_live_quote()
    held = committed()

    def an_answer_in_another_shape(address: str) -> Any:
        return [held["event"]] if "events" in address else {"not": "a book"}

    again = refresh(recorded, ask=an_answer_in_another_shape)

    assert again.quote == recorded
    assert again.refresh_failed is not None
    assert "answered, but this program could not read the answer" in again.refresh_failed
    assert "could not be reached" not in again.refresh_failed


def test_a_refresh_of_a_typed_price_has_nothing_to_ask() -> None:
    """A price the reader typed names no market, so there is nowhere to read it again from."""
    typed = Quote(
        bid=0.41,
        offer=0.41,
        as_of=recorded_live_quote().as_of,
        source="user",
    )

    def never_called(address: str) -> Any:  # pragma: no cover - the point is that it is not
        raise AssertionError(f"nothing should have been asked, but {address} was")

    again = refresh(typed, ask=never_called)

    assert again.quote == typed
    assert again.refresh_failed is not None
    assert "typed" in again.refresh_failed
