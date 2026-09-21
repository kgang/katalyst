"""What a run cost, added up as it goes, and the sentence it says when it stops.

Every call to a model spends money. A run that could not say how much would be a
number nobody computed sitting on the screen, which is the one thing this product
refuses to show — so the counters come back with every answer, they are folded in
here, and the total is checked against the run's ceiling **after every call**.

Where each number comes from
----------------------------
The service reports, on every answer, how many tokens it read fresh, how many it
read back out of its cache, how many it wrote into the cache, how many it wrote
as an answer, and how many web searches it ran. Those five, times the prices in
`pricing.py`, are the whole bill. Nothing here estimates and nothing here rounds
until the moment a person reads it.

Two of the five are easy to leave out and expensive to leave out. **Cache writes**
are charged at more than a fresh token, not less, and a run pays them on its very
first call. **Searches** are charged per search, not per token. A receipt missing
either would be smaller than the truth, and a ceiling checked against a number
smaller than the truth is not a ceiling.

What this file must never do
----------------------------
- Never hold a price. They live in `pricing.py`, with the day they were read.
- Never guess at a counter the service did not report. A call whose answer we
  could not read is counted as a call and its tokens are left at nothing, because
  nothing is what we know.
- Never talk to a model, read a clock, or decide whether a run should carry on.
  It adds up and it says what the total is; the stopping is the walk's own.
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from katalyst.engine.pricing import (
    A_MILLION,
    A_THOUSAND,
    DOLLARS_PER_THOUSAND_SEARCHES,
    prices_for,
)
from katalyst.settings import get_settings


class Counted(Protocol):
    """Anything that knows what one question cost.

    Written as a shape rather than as a named type so that this file depends on
    nothing above it: the thing a run actually folds in is the outcome of one
    call, which lives with the pipeline, and a receipt has no business importing
    the pipeline to add five numbers up.
    """

    calls: int
    searches: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int


class Receipt(BaseModel):
    """What one run has spent so far, and on what.

    Frozen, like everything else on this map: folding a call in returns a new
    receipt rather than changing this one, so a receipt handed to somebody cannot
    quietly grow behind their back.

    `dollars` is worked out from the counters and the price table every time the
    receipt changes, so it can never drift away from the numbers beside it.
    """

    model_config = ConfigDict(frozen=True)

    model: str = Field(description="Which model the run asked. Priced by `pricing.py`.")
    calls: int = Field(
        default=0,
        description=(
            "How many round trips this run has made. A question whose answer came "
            "back part finished and was sent back to be continued counts each "
            "trip, because each trip is on the bill."
        ),
    )
    searches: int = Field(
        default=0, description="How many web searches the model ran across the whole run."
    )
    input_tokens: int = Field(
        default=0,
        description=(
            "Tokens of question read fresh. It is the remainder only: the ones "
            "read back out of the cache are counted separately below."
        ),
    )
    output_tokens: int = Field(
        default=0, description="Tokens of answer written, the model's thinking included."
    )
    cache_read_tokens: int = Field(
        default=0,
        description=(
            "Tokens the service recognised from an earlier call and charged a "
            "tenth of the usual price for. A run where this stays at nothing is a "
            "bug in how the request is put together, not a slow day."
        ),
    )
    cache_write_tokens: int = Field(
        default=0,
        description=(
            "Tokens written into the cache as they were read, charged at more than "
            "a fresh one. A run pays these on its first call and rarely again."
        ),
    )
    dollars: float = Field(
        default=0.0, description="What all of the above comes to, at the prices in `pricing.py`."
    )


def nothing_spent_yet(model: str | None = None) -> Receipt:
    """Start a run's receipt at zero.

    Args:
        model: Which model the run will ask. The one the settings name when not
            said, because which model this is is a fact about how the program was
            started rather than something a caller decides per run.

    Returns:
        A receipt with every counter at nothing.
    """
    return Receipt(model=model or get_settings().KATALYST_MODEL)


def fold(receipt: Receipt, call: Counted) -> Receipt:
    """Add what one call cost to what the run has spent, and re-price the total.

    Args:
        receipt: What the run had spent before this call.
        call: What this call cost — the five counters and how many round trips it
            took.

    Returns:
        A new receipt. The one passed in is unchanged.
    """
    added = receipt.model_copy(
        update={
            "calls": receipt.calls + call.calls,
            "searches": receipt.searches + call.searches,
            "input_tokens": receipt.input_tokens + call.input_tokens,
            "output_tokens": receipt.output_tokens + call.output_tokens,
            "cache_read_tokens": receipt.cache_read_tokens + call.cache_read_tokens,
            "cache_write_tokens": receipt.cache_write_tokens + call.cache_write_tokens,
        }
    )
    return added.model_copy(update={"dollars": dollars_for(added)})


def dollars_for(receipt: Receipt) -> float:
    """Work out what a set of counters comes to, at the prices in `pricing.py`.

    Args:
        receipt: The counters to price, and the model that charged for them. Its
            own `dollars` is ignored.

    Returns:
        The total in dollars.

    Raises:
        KeyError: If nobody has read that model's prices.
    """
    prices = prices_for(receipt.model)
    tokens = (
        receipt.input_tokens * prices.input_tokens
        + receipt.output_tokens * prices.output_tokens
        + receipt.cache_read_tokens * prices.cache_read_tokens
        + receipt.cache_write_tokens * prices.cache_write_tokens
    ) / A_MILLION
    searching = receipt.searches * DOLLARS_PER_THOUSAND_SEARCHES / A_THOUSAND
    return tokens + searching


def over_the_cap(receipt: Receipt, cap: float) -> bool:
    """Say whether this run has spent what it was allowed to spend.

    Args:
        receipt: What the run has spent so far.
        cap: What it was allowed to spend, in dollars.

    Returns:
        True once the total has reached the ceiling.
    """
    return receipt.dollars >= cap


def what_it_spent_and_got(receipt: Receipt, cap: float, claims: int, links: int) -> str:
    """Say, in one plain sentence, that the run stopped for money and what it bought.

    What was built is kept rather than thrown away: a partial map with a visible
    reason beats a blank screen with a silent one, so the sentence names both
    halves — what went out and what came back.

    Args:
        receipt: What the run spent.
        cap: What it was allowed to spend.
        claims: How many claims the map ended up with.
        links: How many arrows.

    Returns:
        One sentence for a person to read. Never a code and never a stack trace.
    """
    return (
        f"This run reached its spending limit of {_money(cap)}. "
        f"It spent {_money(receipt.dollars)} and built {claims} claims and {links} arrows."
    )


def _money(dollars: float) -> str:
    """Write an amount the way a person reads one: a dollar sign and two decimals."""
    return f"${dollars:.2f}"
