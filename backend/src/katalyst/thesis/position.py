"""The reader's position and their exit, and how often each end of it is reached first.

A trade needs something bought or sold, a size, and a point at which the reader
gets out. **None of those is derivable from a map of claims**, so the stop, the
target and the horizon are numbers the reader types. What this file computes
beside them is how often each is reached first, and what their own risk budget
implies about size.

That is a reversal, and a deliberate one. The roadmap promised a *derived* stop —
the flip that damages an ending most and resolves before it. On this product's own
worked example that derivation leaves one claim, and it is the causal step the
trade rests on, so the derived stop reads *get out if the thing you are betting on
stops being true*: a restatement of the position, not a warning about it. A stop
is a price the reader owns.

**First touch** means walking each drawn world's path day by day and recording
which of the stop and the target is reached first, counting a level as reached the
moment the path touches it. A stop hit on day three is hit even if the price
finishes the month above it, and any method that reads only the end of the window
understates being stopped out — in the flattering direction.

**Two honesty rules travel with the number.**

*A daily check misses touches between closes.* So the standard correction is
applied: the **barrier shift** moves each level a little way toward the price the
reader entered at, by an amount growing with the instrument's variability and the
length of the step, so that a daily count matches what watching continuously would
have found. The distance is a known constant times the daily variability, and the
constant is named and cited below.

*When a day's step crosses both levels, the stop is taken as first.* It is the
only reading that cannot flatter the trade.

**A contract ending has no first touch here.** A probability does not follow a
price-path model: a random walk leaves the zero-to-one range, the contract's truth
in a drawn world is already known from the draw, and the reader has no day-to-day
variability to give for one. A contract is held to resolution and the question is
refused by name.

What this file must never do
----------------------------
- Never derive a stop, a target or a horizon. They arrive on a `Position` the
  reader filled in, and nothing here invents one.
- Never recommend a size. What the reader's own risk budget implies is arithmetic
  on two numbers they typed; the greyed ceiling beside it is a ceiling and not a
  size.
- Never answer a path question with an end-of-window distribution, and never read
  a daily count as if it were continuous.
- Never report a first-touch number without naming the sample its days came from.
- Never put a contract on a price path.
- Never repair a form quietly. A refusal names the field and says one plain
  sentence.
"""

import math
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal

import numpy

from katalyst.domain import ContractPayoff, Proposition, PropositionId
from katalyst.thesis.draws import NEVER, Days, SampleFrom, effective_draws, weighted_share
from katalyst.thesis.paths import Paths

ZETA_HALF: Final = -1.4603545088095868
"""The Riemann zeta function at one half, which is where the barrier shift comes from.

Written down with its name rather than computed, because computing it needs a
library this program does not carry and a series that converges too slowly to be
worth a page of code. Source: the value is standard and is quoted to sixteen
digits in the literature on discretely monitored barriers, from which the shift
below is taken (Broadie, Glasserman and Kou, *A continuity correction for discrete
barrier options*, Mathematical Finance 7(4), 1997).
"""

BARRIER_SHIFT: Final = -ZETA_HALF / math.sqrt(2.0 * math.pi)
"""How far to move a level toward the entry price, per unit of a day's variability.

About four days in ten, a price that is going to cross a level crosses it and comes
back between two closes, so a daily check misses the touch. The standard
correction is to move the level toward where the price started by this constant
times one day's variability: a daily count against the moved level then matches
what watching continuously would have found against the level the reader typed.

It is not a fudge factor. It is `-zeta(1/2) / sqrt(2 * pi)`, computed here from the
one number above rather than typed, and it is the same constant in every treatment
of discretely monitored barriers.
"""

Side = Literal["long", "short"]
"""Which way the trade is pointed. A long position makes money when the price rises."""

Trades = Literal["instrument", "contract"]
"""What the ending names: something traded whose price moves, or a contract on the claim itself."""

RefusalCode = Literal[
    "stop_on_the_wrong_side",
    "target_not_beyond_entry",
    "horizon_after_the_claim",
    "risk_budget_out_of_range",
    "price_outside_the_contract",
    "first_touch_on_a_contract",
]
"""Every reason this file refuses, as a closed list.

The first five are things a reader can fix on the form. The last is not a mistake
at all: it is the honest answer to a question that does not apply to a contract.
"""

REFUSALS: Final[dict[str, str]] = {
    "stop_on_the_wrong_side": (
        "A stop protects you; this one is where the trade is already working."
    ),
    "target_not_beyond_entry": "A target you are already at is not a target.",
    "horizon_after_the_claim": (
        "This claim is settled before your horizon; the trade cannot still be open."
    ),
    "risk_budget_out_of_range": (
        "A risk budget is the share of your capital you are willing to lose."
    ),
    "price_outside_the_contract": "A contract's price is between nothing and everything.",
    "first_touch_on_a_contract": ("A contract is held to resolution; there is no path to touch."),
}
"""What each refusal says, in plain words the reader can act on.

Written here, once, so that the form, the card and the export all print the same
sentence and nobody writes a sixth wording of the same rule.
"""


@dataclass(frozen=True)
class Refusal:
    """One thing the form will not accept, the field at fault, and what it says.

    A refusal is a value, not an exception, and never a blank: it names a stable
    code a screen can branch on, the field the reader should look at, and one plain
    sentence. Nothing is silently repaired.

    Attributes:
        code: Which rule this is, from the closed list above.
        field: The field on the form at fault, named as the reader sees it.
        sentence: What the screen prints.
    """

    code: RefusalCode
    field: str
    sentence: str


@dataclass(frozen=True)
class Position:
    """What the reader typed, and the two things taken from the map so they cannot disagree.

    Every number here is the reader's own except `instrument`, `side` and `trades`,
    which come from the ending's own payoff — so the position cannot name a trade
    the map does not.

    A position is **not an edit to the map**: nothing moves on the canvas and it
    appears on no branch.

    Attributes:
        ending: The ending being traded.
        instrument: What is bought or sold, named the way its venue names it, or
            the contract's own identifier where the ending names a contract.
        side: Which way the trade is pointed, taken from the ending's payoff.
        trades: Whether the ending names something traded or a contract on the
            claim itself. A contract gets no price path and no first touch.
        entry: The price the reader entered at, in the instrument's own units.
        stop: The price at which they get out for a loss. Theirs, never derived.
        target: The price at which they get out for a gain. Theirs, never derived.
        horizon: The day by which they expect to be out.
        risk_budget: The share of their capital they are prepared to lose on this
            trade, between nothing and one.
        daily_move: How far the instrument moves in a day, in price units — one
            standard deviation of a day's change. The reader's own number today.
    """

    ending: PropositionId
    instrument: str
    side: Side
    trades: Trades
    entry: float
    stop: float
    target: float
    horizon: date
    risk_budget: float
    daily_move: float


@dataclass(frozen=True)
class FirstTouch:
    """How often each end of the reader's exit is reached first, and what the number rests on.

    Attributes:
        stop_first: The weighted share of drawn worlds where the stop was touched
            before the target.
        target_first: The weighted share where the target was touched first.
        neither: The weighted share where the window closed with neither touched.
            The three always sum to one.
        stop_touched: The weighted share where the stop was touched at **any**
            time, whether or not the target went first. Never less than the share
            that finished beyond it.
        finished_beyond_the_stop: The weighted share whose last price was past the
            stop the reader typed. Read against the reader's own level, not the
            shifted one.
        stop_at: The level actually checked for the stop, after the barrier shift.
        target_at: The level actually checked for the target, after the shift.
        shift: How far each level was moved toward the entry price.
        effective_draws: How many equally-weighted worlds this rests on.
        stop_first_on: For each drawn world, the day the stop was touched first, or
            `NEVER` where it was not. This is what lift reads.
        sample: Which sampler the days came from, so no screen can print these
            shares without saying.
    """

    stop_first: float
    target_first: float
    neither: float
    stop_touched: float
    finished_beyond_the_stop: float
    stop_at: float
    target_at: float
    shift: float
    effective_draws: float
    stop_first_on: Days
    sample: SampleFrom


def position_on(
    ending: Proposition,
    *,
    entry: float,
    stop: float,
    target: float,
    horizon: date,
    risk_budget: float,
    daily_move: float,
) -> Position | tuple[Refusal, ...]:
    """Build a position on an ending, or say everything wrong with the form at once.

    **The one place a position's instrument and side are read from the map.** They
    come from the ending's own payoff, so a position cannot name a trade the map
    does not, and the reader is shown them rather than asked for them.

    Every fault is returned together, the way the rules layer returns every
    complaint about a map at once, because a form that reveals one mistake at a
    time is a form nobody finishes.

    Args:
        ending: The claim being traded. Its payoff says what is traded and which
            way.
        entry: The price the reader entered at.
        stop: The price at which they get out for a loss.
        target: The price at which they get out for a gain.
        horizon: The day by which they expect to be out.
        risk_budget: The share of capital they are prepared to lose here.
        daily_move: How far the instrument moves in a day, in price units.

    Returns:
        The position, or every refusal the form has, in a fixed order.

    Raises:
        ValueError: If the ending names no trade at all. That is not something the
            reader did: whatever offered this claim as tradeable offered the wrong
            claim.
    """
    payoff = ending.payoff
    if payoff is None:
        raise ValueError(
            f"'{ending.id}' names no trade, so there is no position to take on it; whatever "
            "offered it as tradeable offered the wrong claim"
        )
    traded: Trades = "contract" if isinstance(payoff, ContractPayoff) else "instrument"
    if isinstance(payoff, ContractPayoff):
        named, side = payoff.contract_id, payoff.side == "yes"
    else:
        named, side = payoff.instrument, payoff.direction == "long"

    wanted = Position(
        ending=ending.id,
        instrument=named,
        side="long" if side else "short",
        trades=traded,
        entry=entry,
        stop=stop,
        target=target,
        horizon=horizon,
        risk_budget=risk_budget,
        daily_move=daily_move,
    )
    refused = what_the_form_refuses(wanted, ending)
    return refused if refused else wanted


def what_the_form_refuses(position: Position, ending: Proposition) -> tuple[Refusal, ...]:
    """List everything wrong with a position, in a fixed order.

    Five rules, each with one plain sentence:

    | Rule | Why |
    |---|---|
    | The stop is on the losing side of the entry | A stop where the trade works is not one |
    | The target is beyond the entry, the other way | A target you are already at is not one |
    | The horizon is after the day the claim is judged | The trade cannot still be open then |
    | The risk budget is above nothing and at most one | It is a share of capital, not an amount |
    | A contract's prices are between nothing and one | A contract cannot trade outside its range |

    Args:
        position: What the reader typed.
        ending: The claim being traded, which carries the day it is settled.

    Returns:
        Every refusal, in the order of the table above. Empty when the form is
        good.
    """
    losing = -1.0 if position.side == "long" else 1.0
    found: list[Refusal] = []
    if losing * (position.stop - position.entry) <= 0.0:
        found.append(_refusing("stop_on_the_wrong_side", "stop"))
    if losing * (position.target - position.entry) >= 0.0:
        found.append(_refusing("target_not_beyond_entry", "target"))
    if position.horizon > ending.resolution.by:
        found.append(_refusing("horizon_after_the_claim", "horizon"))
    if not 0.0 < position.risk_budget <= 1.0:
        found.append(_refusing("risk_budget_out_of_range", "risk budget"))
    if position.trades == "contract" and not all(
        0.0 <= one <= 1.0 for one in (position.entry, position.stop, position.target)
    ):
        found.append(_refusing("price_outside_the_contract", "entry"))
    return tuple(found)


def _refusing(code: RefusalCode, field: str) -> Refusal:
    """One refusal, with the sentence written once for every screen that prints it."""
    return Refusal(code=code, field=field, sentence=REFUSALS[code])


def first_touch(paths: Paths, position: Position) -> FirstTouch | Refusal:
    """Say how often the stop and the target are each reached first, or refuse by name.

    Each drawn world's path is walked day by day from the day after entry. A level
    counts as reached the moment the path touches it; when one day's step crosses
    both, the stop is taken as first. Both levels are moved toward the entry price
    by the barrier shift before they are checked, so that a daily count says what
    continuous watching would have found.

    Args:
        paths: A daily price path through every drawn world.
        position: The reader's entry, stop, target and side.

    Returns:
        The three shares and what they rest on; or a refusal, by name, where the
        ending names a contract rather than something traded.

    Raises:
        ValueError: If the paths were not walked from this position's entry price,
            or at its own day-to-day variability. Checking a stop against a path
            that started somewhere else answers a question nobody asked, and one
            walked at another variability would be corrected by the wrong amount.
    """
    if position.trades == "contract":
        return _refusing("first_touch_on_a_contract", "ending")
    if paths.entry != position.entry or paths.daily_move != position.daily_move:
        raise ValueError(
            "a stop is checked against the path the reader's own position was walked "
            f"through; these paths started at {paths.entry} and stepped at "
            f"{paths.daily_move}, and the position says {position.entry} and "
            f"{position.daily_move}"
        )

    # Each level moves toward the entry price by the shift, and never past it: a
    # level nearer the entry than the shift is touched on the first day either way.
    shift = BARRIER_SHIFT * position.daily_move
    losing = -1.0 if position.side == "long" else 1.0
    stop_at = position.entry + losing * max(0.0, abs(position.stop - position.entry) - shift)
    target_at = position.entry - losing * max(0.0, abs(position.target - position.entry) - shift)

    walked = paths.level[:, 1:]
    beyond = (walked <= stop_at) if position.side == "long" else (walked >= stop_at)
    reached = (walked >= target_at) if position.side == "long" else (walked <= target_at)
    never = walked.shape[1] + 1
    stop_on = numpy.where(beyond.any(axis=1), beyond.argmax(axis=1), never)
    target_on = numpy.where(reached.any(axis=1), reached.argmax(axis=1), never)
    stop_won = (stop_on <= target_on) & (stop_on < never)
    target_won = target_on < stop_on

    last = paths.level[:, -1]
    past_the_readers_stop = (
        (last < position.stop) if position.side == "long" else (last > position.stop)
    )
    return FirstTouch(
        stop_first=weighted_share(stop_won, paths.weight),
        target_first=weighted_share(target_won, paths.weight),
        neither=weighted_share(~stop_won & ~target_won, paths.weight),
        stop_touched=weighted_share(beyond.any(axis=1), paths.weight),
        finished_beyond_the_stop=weighted_share(past_the_readers_stop, paths.weight),
        stop_at=stop_at,
        target_at=target_at,
        shift=shift,
        effective_draws=effective_draws(paths.weight),
        stop_first_on=numpy.where(stop_won, stop_on + 1, NEVER).astype(numpy.int32),
        sample=paths.sample,
    )


def what_your_risk_budget_implies(position: Position) -> float:
    """The share of capital whose loss from entry to stop is exactly the risk budget.

    Arithmetic on two numbers the reader typed and nothing else: the share of
    capital to put in so that a move from the entry price to the stop loses exactly
    the share of capital they said they were prepared to lose.

    **It is what their own rule implies, never a recommendation**, and it is not
    capped: a stop close to the entry implies more than all of their capital, and
    saying so is more useful than quietly clipping it to one.

    Args:
        position: The reader's entry, stop and risk budget.

    Returns:
        A share of capital. Above one where the stop is nearer the entry than the
        risk budget is to the whole.

    Raises:
        ValueError: If the stop is the entry price, where the arithmetic has
            nothing to divide by and the position has no loss to size against.
    """
    away = abs(position.entry - position.stop)
    if away == 0.0:
        raise ValueError(
            "a stop at the entry price is not a loss to size against, so there is nothing "
            "here for a risk budget to imply"
        )
    return position.risk_budget * position.entry / away
