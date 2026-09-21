"""Reading Polymarket: what its answers look like, and how one becomes a quote.

Polymarket is a prediction market — a venue where people buy and sell contracts
that pay one dollar if a stated question comes out yes and nothing if it comes
out no, so the price of a contract reads directly as a likelihood. Two of its
addresses are used here, both public and neither needing a key:

* **the market record** — `gamma-api.polymarket.com/events?slug=…` — which carries
  the identifiers, the venue's own question and resolution rules, the end date,
  how much is resting and traded, and the flags saying whether the market is
  still open;
* **the order book** — `clob.polymarket.com/book?token_id=…` — which carries the
  two sides of the book and, uniquely, the instant the book was true.

Everything below was written against answers this repository actually saved on
2026-09-21, not against a memory of the interface, because four things about it
are surprising and every one of them would produce a plausible wrong number:

* **`outcomes`, `outcomePrices` and `clobTokenIds` are strings holding JSON**, not
  lists. They are parsed a second time.
* **Every price and size in the order book is a string**, and the book's instant is
  a string of milliseconds.
* **The bids come back ascending and the offers descending**, so the first line of
  each side is the *worst* price: in the answer this repository saved, the first
  bid is `0.01` against a best bid of `0.06`. The best of each side is taken by
  value here — the largest bid and the smallest offer — which is what *best* means
  and does not depend on the venue's ordering staying what it is today.
* **A market's displayed price is rounded and is not the midpoint.** It reads
  `0.07` where the book says six against eight, and snaps to `1` and `0` on a
  settled market whose book still reads `0.999` against `1.00`. It is never read.

**Recorded first, fetched second.** Nothing in the demo, the tests or the build
calls out: they read the committed dated file, parsed by the very same functions
below, so a replay is the real thing played back. Asking the venue again is
something a reader opts into, and when it fails the recorded quote stays and the
card says the refresh failed. On the machine this was written on it *will* fail —
the local resolver returns no address for the venue's hosts — which is why
recorded-first is the rule here rather than a fallback.

What this file must never do
----------------------------
- Never call out unless a reader asked for it. The parsing below is pure; the one
  function that opens a connection is named for what it does and is handed in.
- Never read a price off the displayed figure or off the first line of a side.
- Never decide from a price whether a market is still trading.
- Never let a failed read take the recorded price with it.
"""

import json
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.grounding.quote import Quote, QuoteSource

VENUE = "Polymarket"
"""The venue's own name, as a reader should see it written."""

MARKET_RECORDS = "https://gamma-api.polymarket.com/events"
"""Where a market's identifiers, question, rules, state and size are read from."""

ORDER_BOOKS = "https://clob.polymarket.com/book"
"""Where the two sides of the book, and the instant they were true, are read from."""

MARKET_PAGE = "https://polymarket.com/event/"
"""What a market's public web address starts with. The venue's own slug follows."""

HOW_LONG_TO_WAIT = 10.0
"""How many seconds an opt-in read waits before giving up and keeping the recorded price."""

Ask = Callable[[str], Any]
"""Something that takes a web address and gives back the answer, already parsed.

Handed in rather than reached for, so that the one function here that can open a
connection is visible at every call site and a test can hand in something that
never leaves the machine.
"""


@dataclass(frozen=True)
class Book:
    """The two sides of one order book, and the instant they were true.

    A plain record rather than one of the data shapes: it never crosses to the
    browser and never gets stored. It exists because both the committed file and
    an opt-in read produce one, and the arithmetic on it must be written once.
    """

    token_id: str
    """Which outcome this book is for. A contract's yes and no are separate books."""

    bid: float
    """The best bid: the largest price anybody is offering to pay."""

    offer: float
    """The best offer: the smallest price anybody will sell at."""

    as_of: datetime
    """The instant the venue stamped this book with, to the millisecond."""

    tick: float
    """The smallest price step this market trades in."""

    minimum_order: float
    """The smallest order this market accepts."""


class Refreshed(BaseModel):
    """What came back from asking the venue for a price again.

    Two fields rather than one, because a refresh that failed must not look like a
    refresh that worked: the price is still the recorded one and the card has to
    say so.
    """

    model_config = ConfigDict(frozen=True)

    quote: Quote = Field(
        description=(
            "The price to show: the venue's new one if the read worked, and the one "
            "that was handed in if it did not."
        )
    )
    refresh_failed: str | None = Field(
        default=None,
        description=(
            "One plain sentence saying the read did not happen and the price on screen "
            "is the one it already had. None means the read worked."
        ),
    )


def read_book(answer: Mapping[str, Any]) -> Book:
    """Read one order-book answer: the best of each side, and the instant it was true.

    The best bid is the **largest** price anybody is bidding and the best offer the
    **smallest** price anybody is asking, which is what *best* means from the point
    of view of somebody crossing the spread. Taking them by value rather than by
    position is deliberate: the venue happens to send bids ascending and offers
    descending today, so the first line of each side is the worst price in it, and
    a reader of the first line would have got `0.01` where the best bid was `0.06`.

    Args:
        answer: One answer from the venue's order-book address, already parsed.

    Returns:
        The two prices, the instant, and the two smallest amounts the venue deals in.

    Raises:
        ValueError: If either side of the book is empty, because a side with nothing
            on it has no best price and a quote with half a book is not a price
            anybody could deal at.
    """
    bids = _sides(answer, "bids")
    offers = _sides(answer, "asks")
    return Book(
        token_id=str(answer["asset_id"]),
        bid=max(bids),
        offer=min(offers),
        as_of=datetime.fromtimestamp(int(answer["timestamp"]) / 1000.0, tz=UTC),
        tick=float(answer["tick_size"]),
        minimum_order=float(answer["min_order_size"]),
    )


def quote_from(
    event: Mapping[str, Any], book_answer: Mapping[str, Any], *, source: QuoteSource
) -> Quote:
    """Turn one market record and one order book into a quote, deriving everything derivable.

    Which of the event's markets the book belongs to, and which side of that market
    it prices, are both worked out rather than said: the book names the contract's
    on-chain identifier and the outcome it is for, and the market record lists its
    outcomes and their identifiers index for index.

    Args:
        event: One event from the venue's market-record address, already parsed —
            the single object, not the list it arrives inside.
        book_answer: The matching order-book answer, already parsed.
        source: How this pair reached us: `fetched` from the venue just now, or
            `recorded` from the committed dated file.

    Returns:
        One quote carrying both prices as read, the instant, the identifiers, the
        venue's own question and rules, its end date, its state and its size.

    Raises:
        ValueError: If no market in the event has the book's contract identifier, if
            the market does not list the outcome the book prices, or if that outcome
            is named anything but yes or no. Each is a mismatch between two answers
            that should describe the same contract, and guessing past one would
            price the wrong thing.
    """
    book = read_book(book_answer)
    market = _market_for(event, str(book_answer["market"]))
    return Quote(
        bid=book.bid,
        offer=book.offer,
        as_of=book.as_of,
        source=source,
        closed=bool(market["closed"]),
        accepting_orders=bool(market["acceptingOrders"]),
        venue=VENUE,
        condition_id=str(market["conditionId"]),
        market_id=str(market["id"]),
        token_id=book.token_id,
        side=_side_of(market, book.token_id),
        question=str(market["question"]),
        rules=str(market["description"]),
        ends=date.fromisoformat(str(market["endDateIso"])),
        tick=book.tick,
        minimum_order=book.minimum_order,
        resting=float(market["liquidityNum"]),
        traded=float(market["volumeNum"]),
        url=MARKET_PAGE + str(event["slug"]),
    )


def refresh(recorded: Quote, ask: Ask | None = None) -> Refreshed:
    """Ask the venue for this contract's price again, and keep the old one if it cannot be asked.

    **This is the only thing in the program that reaches the venue**, and nothing
    calls it unless a reader asked: not a page as it loads, not a test, not the
    build. Two reads, both public and neither needing a key — the market record for
    the state and the size, the order book for the prices and the instant — and the
    answers go through the very same parsing the committed file does, so a refreshed
    quote and a recorded one are the same shape and can be compared field by field.

    Anything at all going wrong — no answer, a slow answer, an answer in a shape
    this program does not recognise — keeps the recorded price on screen with a
    sentence saying the read did not happen. A stale price that says it is stale is
    worth more than a blank.

    Args:
        recorded: The quote to read again. It supplies the outcome identifier and,
            through its web address, the venue's own name for the market.
        ask: What actually fetches an address, for a test that must not leave the
            machine. Left out, the real one is used and this function opens a
            connection.

    Returns:
        The venue's new price, or the one handed in with a sentence saying why.
    """
    if recorded.source == "user" or recorded.token_id is None or recorded.url is None:
        return Refreshed(
            quote=recorded,
            refresh_failed=(
                "This price was typed rather than read from a venue, so there is no "
                "market to read it from again."
            ),
        )
    fetch = _ask_the_venue if ask is None else ask
    named = urllib.parse.urlencode({"slug": _slug_of(recorded.url)})
    outcome = urllib.parse.urlencode({"token_id": recorded.token_id})
    try:
        events = fetch(f"{MARKET_RECORDS}?{named}")
        book = fetch(f"{ORDER_BOOKS}?{outcome}")
        return Refreshed(quote=quote_from(events[0], book, source="fetched"))
    except Exception as trouble:
        return Refreshed(
            quote=recorded,
            refresh_failed=(
                f"{VENUE} could not be read just now ({type(trouble).__name__}), so the "
                "price shown is the one already on file and the day beside it is still true."
            ),
        )


def _ask_the_venue(address: str) -> Any:
    """Fetch one public address from the venue and parse the answer.

    The one function in this program that opens a connection to a venue. It is
    never called by a test and never by the build.

    Args:
        address: The full web address, query included.

    Returns:
        The answer, parsed from JSON.
    """
    with urllib.request.urlopen(address, timeout=HOW_LONG_TO_WAIT) as answer:
        return json.loads(answer.read().decode("utf-8"))


def _slug_of(url: str) -> str:
    """Take the venue's own name for a market off the end of its public web address.

    The address is built here, in `quote_from`, as the market page followed by the
    venue's slug, so this is exactly the inverse of that and nothing is guessed.

    Args:
        url: A market's public web address.

    Returns:
        The venue's own name for the market.
    """
    return url.rstrip("/").rsplit("/", 1)[-1]


def _sides(answer: Mapping[str, Any], named: str) -> list[float]:
    """Read every price on one side of a book, as numbers.

    Args:
        answer: One order-book answer, already parsed.
        named: Which side to read: the bids or the asks.

    Returns:
        Every price on that side.

    Raises:
        ValueError: If that side is empty.
    """
    lines: Sequence[Mapping[str, Any]] = answer.get(named) or ()
    if not lines:
        raise ValueError(
            f"this order book has nothing on its {named} side, so there is no best price "
            "on it and no price anybody could deal at"
        )
    return [float(one["price"]) for one in lines]


def _market_for(event: Mapping[str, Any], condition_id: str) -> Mapping[str, Any]:
    """Find the market in an event that the book's contract identifier names.

    Args:
        event: One event from the venue, already parsed.
        condition_id: The contract identifier the order book carries.

    Returns:
        That event's market record for this contract.

    Raises:
        ValueError: If the event has no market under that identifier.
    """
    markets: Sequence[Mapping[str, Any]] = event.get("markets") or ()
    found = next((one for one in markets if str(one.get("conditionId")) == condition_id), None)
    if found is None:
        raise ValueError(
            f"this order book is for contract {condition_id}, which is not one of the "
            f"markets in the record for '{event.get('slug')}'"
        )
    return found


def _side_of(market: Mapping[str, Any], token_id: str) -> Literal["yes", "no"]:
    """Say which outcome a price is for, by matching the book's outcome identifier.

    The market lists its outcomes and their identifiers as two JSON strings that
    line up index for index, so the side is read off rather than assumed.

    Args:
        market: One market record from the venue, already parsed.
        token_id: The outcome identifier the order book is for.

    Returns:
        'yes' or 'no'.

    Raises:
        ValueError: If the market does not list that outcome, or names it something
            other than yes or no.
    """
    identifiers: list[str] = [str(one) for one in json.loads(str(market["clobTokenIds"]))]
    outcomes: list[str] = [str(one) for one in json.loads(str(market["outcomes"]))]
    if token_id not in identifiers:
        raise ValueError(
            f"outcome {token_id} is not one of the outcomes market {market.get('id')} lists"
        )
    named = outcomes[identifiers.index(token_id)].strip().lower()
    if named == "yes":
        return "yes"
    if named == "no":
        return "no"
    raise ValueError(
        f"market {market.get('id')} calls this outcome '{named}'; this program only "
        "prices a contract whose two outcomes are yes and no"
    )
