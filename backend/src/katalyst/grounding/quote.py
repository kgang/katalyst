"""A quote: what one venue is charging for one claim, and how we came to know it.

A price on this screen has to say where it came from, when it was true, and how
we got it. This file holds the one shape allowed to carry a price, and the one
function that turns a venue's price into the market's likelihood on a claim.

**Store what the venue returned; derive the rest.** The best bid — what somebody
will pay you — and the best offer — what somebody will sell to you for — are kept
exactly as they were read. The **midpoint** halfway between them is worked out
from those two, never the other way round, and it is the number a reader
recognises and nobody actually trades at.

**A venue publishes no range.** The gap between its bid and its offer is what it
costs to deal, not how unsure the venue is, so the market's likelihood on a claim
is a **point**: its low and high ends equal its middle. Turning a spread into a
range, as an earlier draft of this product did, produces a number nobody can
trace to an input, a rule or a source.

**Identity takes three names and a side.** A prediction-market contract has an
on-chain condition identifier, the venue's own market identifier, and one
*outcome token* identifier per side — and only the token identifier buys a price,
because a contract's yes and its no are two separate order books. The same
contract reads `.07` on one side and `.93` on the other, so a quote says which
side it priced.

**Where a quote comes from is one of three things**, and the screen says which:
read from the venue a moment ago (`fetched`), read from a committed dated file
(`recorded`), or typed by the reader (`user`). A reader's own price is their
report of a price they could deal at — not what they think the claim is worth,
which is a different quantity that lives on the claim's tile.

What this file must never do
----------------------------
- Never invent a field a reader did not report. A price somebody typed carries a
  price, the moment it was true and nothing else; the venue's fields stay absent.
- Never let a price that is not a venue's own fill the market's likelihood.
- Never decide from a price whether a market is still trading. A settled market
  keeps serving a plausible book — 0.999 against 1.00 — so that is read from the
  venue's own flags, **all** of them, and from nowhere else.
- Never demand of a venue a field the venue does not always send. Two different
  lists are kept below for two different things: what **only** a venue can tell
  us, which a typed price therefore never carries, and what a venue **always**
  tells us, which a venue's quote must have. Measured over the 1 693 real market
  records this repository has saved: twelve fields are on every one of them, and
  five are missing from between 24 and 189 of them.
- Never reach over a network. Fetching is `polymarket.py`'s business; this file
  is the shape and the arithmetic on it.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalyst.domain import Belief

QuoteSource = Literal["fetched", "recorded", "user"]
"""The three ways a price reaches this program, in the words the screen uses.

`fetched` — read from the venue just now. `recorded` — read from the committed,
dated file the demo and the build run on. `user` — typed by the reader, as their
report of a price they could deal at.
"""

ALWAYS_FROM_A_VENUE: tuple[str, ...] = (
    "venue",
    "condition_id",
    "market_id",
    "token_id",
    "side",
    "question",
    "rules",
    "url",
    "active",
    "closed",
    "archived",
    "accepting_orders",
)
"""What a venue always tells us, so a quote read from one must carry every one.

Measured, not assumed: all twelve are on every one of the 1 693 distinct market
records this repository has saved from the venue. A venue's quote missing one of
them is refused by name, because identity, the venue's own question and whether
the market is still trading are what make a price checkable at all.
"""

SOMETIMES_FROM_A_VENUE: tuple[str, ...] = (
    "ends",
    "tick",
    "minimum_order",
    "resting",
    "traded",
)
"""What a venue tells us most of the time, and sometimes simply leaves out.

Measured over the same 1 693 records: 154 carry no resting size, 189 no traded
volume and 24 no end date. An absent one stays **absent** — never nought, which
would read as an empty book or a market that settles today. Demanding them would
refuse ordinary, well-formed venue answers.
"""

VENUE_FIELDS: tuple[str, ...] = (*ALWAYS_FROM_A_VENUE, *SOMETIMES_FROM_A_VENUE)
"""Everything only a venue can tell us, listed once so one rule can check them all.

A price the reader typed carries none of them: the reader knows a price, not a
contract's on-chain identifier, not the venue's resolution rules, and not whether
the venue has archived the market. An absent field stays absent rather than being
filled with a plausible stand-in.
"""


class Quote(BaseModel):
    """One price for one claim, with everything needed to check it and to date it.

    Frozen, like the map's own shapes: a quote is what was true at one instant, so
    a changed quote is a new quote rather than an edited one.

    The two prices are stored as they were read and everything else about the
    price is worked out from them. `midpoint` is for display; `live` is read from
    the venue's own flags and never from the numbers.
    """

    model_config = ConfigDict(frozen=True)

    bid: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "The best bid, as read: the most anybody is offering to pay for this claim, "
            "between 0 and 1. This is the price you would sell at."
        ),
    )
    offer: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "The best offer, as read: the least anybody will sell this claim for, "
            "between 0 and 1. This is the price you would buy at."
        ),
    )
    as_of: datetime = Field(
        description=(
            "The instant this price was true, to the millisecond the venue gave. The "
            "book moves within a day, so the instant is stored and the day is printed."
        )
    )
    source: QuoteSource = Field(
        description="How this price reached us: read now, read from a committed file, or typed."
    )
    active: bool | None = Field(
        default=None,
        description=(
            "Whether the venue says this market is one of its live ones. Absent on a price "
            "the reader typed, who knows a price and not the venue's own bookkeeping."
        ),
    )
    closed: bool | None = Field(
        default=None,
        description="Whether the venue says this market has closed. Absent on a typed price.",
    )
    archived: bool | None = Field(
        default=None,
        description="Whether the venue says it has put this market away. Absent on a typed price.",
    )
    accepting_orders: bool | None = Field(
        default=None,
        description=(
            "Whether the venue says it is still taking orders on this market. Absent on a "
            "typed price."
        ),
    )
    venue: str | None = Field(
        default=None,
        description=(
            "Where it trades, by the venue's own name: 'Polymarket'. Absent on a typed price."
        ),
    )
    condition_id: str | None = Field(
        default=None,
        description=(
            "The contract's on-chain identifier, which is how the venue's order books "
            "name the market they belong to."
        ),
    )
    market_id: str | None = Field(
        default=None,
        description=(
            "The venue's own identifier for this market — the short number a person can "
            "paste into the site, and the name the committed quote file is given."
        ),
    )
    token_id: str | None = Field(
        default=None,
        description=(
            "The identifier of the one outcome this price is for. A contract's yes and no "
            "are separate order books, and only this identifier buys a price."
        ),
    )
    side: Literal["yes", "no"] | None = Field(
        default=None,
        description=(
            "Which outcome was priced: 'yes' pays when the claim comes true, 'no' when it "
            "fails. The same contract reads .07 on one side and .93 on the other."
        ),
    )
    question: str | None = Field(
        default=None,
        description=(
            "The venue's own question, word for word, so a reader can check with no "
            "network that the venue is asking what the claim asks."
        ),
    )
    rules: str | None = Field(
        default=None,
        description="The venue's own resolution rules, word for word, for the same reason.",
    )
    ends: date | None = Field(
        default=None,
        description="The day the venue settles this market, so the deadlines can be compared.",
    )
    tick: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "The smallest price step the venue trades in. A gap narrower than this cannot "
            "be traded, so it is not an edge anybody could take."
        ),
    )
    minimum_order: float | None = Field(
        default=None,
        gt=0.0,
        description="The smallest order the venue accepts, in the venue's own units.",
    )
    resting: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "How much money is resting in orders on this market. A midpoint over an empty "
            "book is a different claim from one over a hundred thousand dollars."
        ),
    )
    traded: float | None = Field(
        default=None,
        ge=0.0,
        description="How much has been traded on this market altogether, for the same reason.",
    )
    url: str | None = Field(
        default=None, description="A web address that opens this market, so a reader can check us."
    )

    @model_validator(mode="after")
    def _a_venue_quote_names_its_venue(self) -> "Quote":
        """Check that a venue's quote carries a venue's facts and a typed price carries none.

        The rule this makes mechanical: only a venue's own number about this claim
        may fill the market's likelihood. A price with no venue, no identifiers and
        no rules cannot be one, and a typed price carrying an on-chain identifier
        the reader never saw would be a stand-in dressed as a fact.

        Returns:
            This same quote, once both halves have been checked.

        Raises:
            ValueError: If a venue's quote is missing one of the facts a venue
                always gives, or a typed price carries any fact only a venue could
                have given.
        """
        if self.source == "user":
            present = sorted(one for one in VENUE_FIELDS if getattr(self, one) is not None)
            if present:
                raise ValueError(
                    "a price the reader typed carries a price and the moment it was true, "
                    f"and nothing a venue would have told us; this one carries {present}"
                )
        else:
            missing = sorted(one for one in ALWAYS_FROM_A_VENUE if getattr(self, one) is None)
            if missing:
                raise ValueError(
                    "a quote read from a venue carries the facts every venue answer has — "
                    "its venue, its three identifiers, the side priced, the venue's own "
                    "question and rules, a web address and its four state flags; this one "
                    f"is missing {missing}"
                )
        if self.bid > self.offer:
            raise ValueError(
                f"a quote's best bid must not be above its best offer; got bid={self.bid}, "
                f"offer={self.offer}. A crossed book is not a price anybody can deal at."
            )
        return self

    @property
    def midpoint(self) -> float:
        """The number halfway between the two prices — shown to a reader, never traded at.

        Worked out from the bid and the offer every time it is asked for, so it can
        never disagree with them.

        Returns:
            The midpoint, between 0 and 1.
        """
        return (self.bid + self.offer) / 2.0

    @property
    def live(self) -> bool:
        """Whether an order could be put in right now, read from the venue's flags alone.

        Never from the price. A settled market keeps serving a plausible book — the
        one this repository saved reads 0.999 against 1.00 — so a reader who decided
        from the numbers would show a finished market as a live one at nearly
        certain odds.

        **All four flags, not two.** The venue publishes *active*, *closed*,
        *archived* and *accepting orders*, and they disagree more often than one
        would guess: of the 1 693 real market records this repository has saved,
        **226** say they are open and taking orders while also saying they are not
        active, and one of those says it is archived as well. Reading two flags
        calls all 226 tradeable.

        A price the reader typed is live by what it means: they are reporting what
        they can get now. They are not asked about the venue's bookkeeping and it
        is not invented for them.

        Returns:
            True when an order could be placed: the venue says the market is
            active, is not closed, is not archived and is taking orders — or the
            reader typed the price themselves.
        """
        if self.source == "user":
            return True
        return bool(self.active and self.accepting_orders and not self.closed and not self.archived)


def market_belief(quote: Quote) -> Belief:
    """Turn a venue's quote into the market's likelihood on a claim: a point, never a range.

    The low and high ends equal the middle, because the venue publishes no interval
    at all. What its two prices differ by is what dealing costs, and that shows up
    where it belongs — in the two edges, one for buying and one for selling.

    Args:
        quote: The venue's quote. Read from the venue or from the committed file;
            never a price the reader typed.

    Returns:
        One likelihood owned by `market`, whose low end, middle and high end are
        all the quote's midpoint.

    Raises:
        ValueError: If the quote is a price the reader typed. That is their report
            of what they could deal at, not a venue's number about this claim, and
            the two are never shown in the same place.
    """
    if quote.source == "user":
        raise ValueError(
            "a price the reader typed is their report of what they could deal at, not a "
            "venue's number about this claim, so it never fills the market's likelihood"
        )
    middle = quote.midpoint
    return Belief(p=middle, lo=middle, hi=middle, owner="market")
