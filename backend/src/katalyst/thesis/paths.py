"""A daily price path through each drawn world, which invents no advantage of its own.

A stop is path-dependent: a stop touched on day three is touched even if the price
finishes the month well above it. A distribution of end-of-window outcomes cannot
answer a question about the way there, so this file walks each drawn world day by
day.

**The walk.** A random walk with no built-in upward or downward tendency, stepping
at the instrument's own day-to-day variability, starting at the price the reader
entered at. On top of it, each claim's move is carried while that claim is holding.

**The surprise, not the whole move.** Today's price already reflects the market's
own chance of a claim, so applying the whole stated move on top of today's price
counts that move twice, in the reader's favour. Write `q` for the market's chance
of the claim and `m` for the stated move:

> when the claim comes true the price moves by the **surprise**, `m x (1 - q)`;
>
> while it has not happened the price **gives back** the priced-in part, `m x q`
> in total.

Under the model's own chance `p` the window's expected move is then `m x (p - q)`
— the edge, and **nothing at all when the model and the market agree**. The rule
this replaced gave the path `m x p` points of free drift and read *the target is
reached first* far too high.

**The giveback is paid day by day, not on the deadline.** Every schedule that
starts at `q` and runs down to nothing has the same total, so the total cannot
choose between them — and a first touch is about the way there, not the total. The
one chosen here leaves the price fair *on every day*: the priced-in part still
carried on day `t` is

> `q x` (the share of arrivals after `t`) `/ (1 - q x` the share of arrivals by
> `t)`

where the shares are read from the drawn worlds themselves. That histogram **is**
the model's own arrival-day distribution, rescaled to the market's level `q`; it
needs no new input and no new data source, and it is the same neutral assumption
the level already makes — the market believes what the model believes, except
where a venue says otherwise. Where no drawn world has the claim arriving inside
the window there is no histogram to borrow, and the fallback is a straight line
down to nothing. Which of the two was used is carried on the answer, because four
to five points of *the stop is reached first* ride on that shape.

**Three conditions this rule needs, and one of them is not ours to enforce.** The
stated move must be a **level gap** — the level in a world where the claim is true
against the level in a world where it is false, both read at the same moment — and
not the reaction on the announcement day, which is already the surprise and would
be discounted twice. Moves must be **additive, in price units**, because two
correlated claims then need only their own chances and no joint between them; the
same arithmetic on a percentage move puts free drift back. And the market's chance
must be a chance of **this** claim's own resolution test. The first is a sentence
the model is asked for and does not yet say; the second this file requires by
taking its moves in price units and refusing a share; the third belongs to
whoever curates a venue contract.

What this file must never do
----------------------------
- Never apply a claim's whole stated move to a path that starts from today's
  price. That is the double count this file exists to close.
- Never pay the giveback in one step on the deadline. It leaves the path drifting
  one way for the whole window and dumps a cliff on the last day, and a first
  touch is most sensitive to exactly that.
- Never take a move as a share of the price. A percentage move compounds, the
  surprise rule's arithmetic is additive, and the gap between them is free drift
  in the reader's favour.
- Never use a market chance of one. A claim the market is certain of has no
  surprise to apply and nothing left to give back, and the schedule's arithmetic
  divides by nothing.
- Never draw without a seed handed in.
- Never put a contract on a price path. A random walk leaves the zero-to-one range
  and the contract's truth in that world is already known from the draw. That
  refusal is in `position.py`, by name.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy
from numpy.typing import NDArray

from katalyst.domain import PropositionId
from katalyst.thesis.draws import Draws, Weights

Levels = NDArray[numpy.float64]
"""Prices: one row per drawn world, one column per day of the window."""

Schedule = NDArray[numpy.float64]
"""The share of a claim's move the price still carries on each day, while it has not happened.

One number per day of the window, starting at the market's chance of the claim and
reaching nothing on the last day, because a claim that has not happened by the end
of the window never will.
"""

MarketChanceFrom = Literal["venue_quote", "model", "reader"]
"""Where the market's chance of a claim came from, as a closed list.

`venue_quote` — a venue quotes a contract asking this claim's own resolution test.
`model` — nobody quotes it, so the neutral assumption is used: the market believes
what the model believes, read from the world with nothing fixed by an edit.
`reader` — the reader typed one over the top, which they may always do and never
must. **The screen names this in the same sentence as the number**, because a path
built on the model's own chance carries no drift at all and one built on a venue's
does.
"""

DecayShape = Literal["arrival_days", "straight_line"]
"""Which shape the giveback followed, as a closed list.

`arrival_days` — the model's own distribution of the day the claim arrives, read
from the drawn worlds and rescaled to the market's chance. The only schedule
measured fair on every day. `straight_line` — a straight run down to nothing, used
where no drawn world has the claim arriving inside the window, so there is no
histogram to borrow. It is fair over the window and quietly unfair within it.
"""


@dataclass(frozen=True)
class ClaimMove:
    """What one claim does to the traded instrument's price, and what is already in it.

    Attributes:
        claim: Which claim this is about. It must be one of the claims the draws
            carry.
        move: The **level gap**, in price units: how much higher the instrument
            stands in a world where this claim is true than in one where it is
            false, both read at the same moment. Never a share of the price, and
            never the reaction on the announcement day.
        market_chance: The market's own chance of the claim, between nothing and
            one, and never one exactly.
        market_chance_from: Where that chance came from, which the screen names in
            the same sentence as any number built on it.
    """

    claim: PropositionId
    move: float
    market_chance: float
    market_chance_from: MarketChanceFrom

    def __post_init__(self) -> None:
        """Check the move is in price units and the market's chance is usable.

        Raises:
            ValueError: If the market's chance is below nothing, or is one or more.
                A chance of one says the market is already certain: there is no
                surprise to apply, nothing left to give back, and the schedule's
                arithmetic has nothing to divide by.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class Paths:
    """A daily price path through every drawn world, and what shaped each claim's giveback.

    A plain frozen record, like `Draws`, because it holds arrays: fifty thousand
    worlds by thirty-one days is a million and a half numbers.

    Attributes:
        day_zero: The first day of the window, carried from the draws.
        days: How many days the window runs for. The levels below have one more
            column than this, because day zero is a column too.
        entry: The price the reader entered at, which every path starts from.
        level: The price in each drawn world on each day, day zero first.
        weight: How much each drawn world counts, carried from the draws so that
            whoever reads these paths does not have to hold both.
        decay_shape: For each claim that moves the price, which shape its giveback
            followed. Carried because the shape is an assumption and the Inspector
            says which one was used.
    """

    day_zero: date
    days: int
    entry: float
    level: Levels
    weight: Weights
    decay_shape: dict[PropositionId, DecayShape]


def giveback_schedule(draws: Draws, move: ClaimMove) -> tuple[Schedule, DecayShape]:
    """Work out how much of a claim's move the price still carries on each day.

    The priced-in part still carried on day `t` is the market's chance that the
    claim still happens in the days after `t`, given it has not happened by `t`:

    > `q x` (the share of arrivals after `t`) `/ (1 - q x` the share by `t)`

    with the shares read from the drawn worlds themselves — a histogram of the days
    this claim came on, over the worlds where it came on inside the window at all,
    rescaled from the model's own chance to the market's level `q`. It starts at
    `q` on day zero and reaches nothing on the last day, because a claim that has
    not happened by the end of the window never will.

    Where no drawn world has the claim coming on inside the window there is no
    histogram to borrow, and the schedule falls back to a straight line from `q`
    down to nothing. That is fair over the window and unfair within it, so which
    shape was used comes back with it.

    Args:
        draws: The drawn worlds, which carry the arrival days.
        move: The claim, its level gap and the market's chance of it.

    Returns:
        One share per day of the window, and which of the two shapes it followed.

    Raises:
        KeyError: If the claim is not among the drawn worlds' claims.
    """
    raise NotImplementedError


def walk(
    draws: Draws,
    moves: tuple[ClaimMove, ...],
    *,
    entry: float,
    daily_move: float,
    seed: int,
) -> Paths:
    """Walk a daily price path through every drawn world.

    Each path starts at the price the reader entered at and steps with no built-in
    tendency either way, at the instrument's own day-to-day variability. On top of
    that walk, each claim carries its **surprise** while it is holding, and gives
    the priced-in part back day by day while it has not happened.

    **A claim already on when the window opened is already in today's price**, so
    it moves nothing. That is not a special case: the market's chance of a claim
    that has already happened is one, its surprise is nothing, and there is nothing
    left to give back. Such a world is left out of the histogram that shapes the
    giveback for the same reason.

    **A claim that stops holding gives its move back**, because the move is a level
    gap: the instrument stands higher while the claim is true and returns when it
    is not. An event never un-happens, so this only ever touches a state.

    Args:
        draws: The drawn worlds and their arrival days.
        moves: What each claim does to this instrument's price, and what the market
            already prices of it. A claim with no entry here moves the price by
            nothing, which is what an ending's map says about a claim its payoff
            does not mention.
        entry: The price the reader entered at, in the instrument's own units.
        daily_move: How far the instrument moves in a day, in price units — one
            standard deviation of a day's change. The reader's own number today.
        seed: The one number every random step comes from. Required, with no
            default, because a path nobody can redraw is a number nobody can check.

    Returns:
        One price per drawn world per day, with the weights carried through and the
        shape each claim's giveback followed.

    Raises:
        ValueError: If two entries in `moves` name the same claim, if the daily
            variability is negative, or if the entry price is not above nothing.
        KeyError: If a move names a claim the drawn worlds do not carry.
    """
    raise NotImplementedError
