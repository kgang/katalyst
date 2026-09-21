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

**Which `p`, exactly, and over which worlds.** `p` is the share of drawn worlds in
which the claim comes true inside the window, **among the worlds where it was not
already true when the window opened** — the same number `the_sample_s_own_chance`
works out. Worlds where the claim was already on sit outside the statement
altogether: the claim is in today's price there, it moves nothing, and they
contribute nothing either way. So on a sample where a share `a` of the weight has
the claim already on, the window's expected move is `m x (1 - a) x (p - q)`, and it
is still nothing when the model and the market agree.

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

**What it prices, and what it does not.** The rule prices **the chance a claim
comes true**. It does not price *the chance it stops*, because nothing asks the
model for that number yet — it is one line of the one shape freeze. So the path is
exact for an **event**, which once it comes on holds to the end of the window, and
on a **state** it carries a known gap: a state already on when the window opened
sits in the entry price and the whole level gap falls away on the day it stops,
with nothing having been priced in against that. Two tests say exactly what that
costs, and the chapter states it as the antecedent of the no-drift rule rather
than leaving it to be discovered.

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
- Never refuse a market chance of one. It is a chance the layer's own neutral
  assumption reaches, and the honest answer there is that the claim moves the
  price by nothing — not an error a reader cannot act on.
- Never draw without a seed handed in.
- Never work out for itself whether a claim is holding. `Draws` fixes what an off
  day means and this file reads it, because two copies of that comparison are two
  answers to one question.
- Never put a contract on a price path. A random walk leaves the zero-to-one range
  and the contract's truth in that world is already known from the draw. That
  refusal is in `position.py`, by name.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy
from numpy.typing import NDArray

from katalyst.domain import PropositionId
from katalyst.thesis.draws import NEVER, Days, Draws, SampleFrom, Weights

Levels = NDArray[numpy.float64]
"""Prices: one row per drawn world, one column per day of the window."""

Schedule = NDArray[numpy.float64]
"""The share of a claim's move the price still carries on each day, while it has not happened.

One number per day of the window, starting at the market's chance of the claim and
reaching nothing on the last day, because a claim that has not happened by the end
of the window never will.
"""

MarketChanceFrom = Literal["venue_quote", "sample_share", "base_world", "reader"]
"""Where the market's chance of a claim came from, as a closed list.

`venue_quote` — a venue quotes a contract asking this claim's own resolution test,
and its price is the market's own chance.

`sample_share` — nobody quotes it, so the neutral assumption is used: **the market
believes what the model believes**. The number is then the share of the drawn
worlds in which the claim comes true inside the trade's window, worked out from
the draws by `the_sample_s_own_chance` rather than handed in. It is the **only**
reading under which the path carries no drift at all.

`base_world` — the model's printed likelihood for the claim, read from the world
with nothing fixed by an edit. It is the right fallback where the sample carries no
arrivals inside the window, and it is **not** the number the no-drift rule holds
for: the claim's own resolve-by day and the trade's window are two different
questions, and the gap between them is drift. A screen using it owes the reader
that sentence.

`reader` — they typed one over the top, which they may always do and never must.

**The screen names this in the same sentence as the number.** The two model
readings are separate entries here rather than one, because a card that could not
tell them apart could not say whether the number it is showing carries drift.
"""

DecayShape = Literal["arrival_days", "straight_line", "nothing_given_back"]
"""Which shape the giveback followed, as a closed list.

`arrival_days` — the model's own distribution of the day the claim arrives, read
from the drawn worlds and rescaled to the market's chance. The only schedule
measured fair on every day. `straight_line` — a straight run down to nothing, used
where no drawn world has the claim arriving inside the window, so there is no
histogram to borrow. It is fair over the window and quietly unfair within it.
`nothing_given_back` — the market is **certain** of the claim, so the whole move is
already in today's price, there is no surprise to apply and nothing is ever given
back. The claim moves the price by nothing at all, which is the honest answer to a
certainty rather than a refusal.
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
        market_chance: The market's own chance of the claim, from nothing to one.
            One means the market is certain, so the claim moves the price by
            nothing at all. **Nothing at all** means *read it off the drawn worlds*
            — the neutral assumption — and the walk fills it in.
        market_chance_from: Where that chance came from, which the screen names in
            the same sentence as any number built on it. It is `sample_share` when,
            and only when, no chance was handed in.
    """

    claim: PropositionId
    move: float
    market_chance: float | None
    market_chance_from: MarketChanceFrom

    def __post_init__(self) -> None:
        """Check the move is a real number, and that the chance and its source agree.

        A **negative** move is ordinary: it is a claim whose coming true pushes the
        instrument down rather than up, and the level gap carries its own sign.

        **A chance of one is a chance**, and it is one the layer's own neutral
        assumption reaches: a claim that comes true in every drawn world the
        question arises for. The market is certain, so the whole move is already in
        today's price, the claim moves nothing, and the schedule is flat at one
        rather than dividing by nothing on the last day.

        Raises:
            ValueError: If the move is not a real number; if a chance is handed in
                and is outside nothing to one; or if the chance and its source
                disagree about whether this layer worked it out.
        """
        if not math.isfinite(self.move):
            raise ValueError(
                f"a claim's move is a level gap in price units; got {self.move} for '{self.claim}'"
            )
        if (self.market_chance is None) != (self.market_chance_from == "sample_share"):
            raise ValueError(
                "a chance read off the drawn worlds is the one this layer works out, so "
                "'sample_share' is said when and only when no chance is handed in; got "
                f"{self.market_chance} from '{self.market_chance_from}' for '{self.claim}'"
            )
        if self.market_chance is not None and not 0.0 <= self.market_chance <= 1.0:
            raise ValueError(
                "the market's chance of a claim is a chance, from nothing to one; got "
                f"{self.market_chance} for '{self.claim}'"
            )


@dataclass(frozen=True)
class ChanceUsed:
    """The market's chance the walk actually applied to one claim, and where it came from.

    Carried because record 0019 requires the source in the same sentence as the
    number, and because the chance may have been **worked out here** rather than
    handed in: a card cannot name what it cannot read.

    Attributes:
        value: The chance, from nothing to one.
        came_from: Which of the four sources it is.
    """

    value: float
    came_from: MarketChanceFrom


def the_chance_applied(draws: Draws, move: "ClaimMove") -> "ChanceUsed":
    """The market's chance this claim's move is scaled by, and where it came from.

    One place, so the schedule and the number a card prints beside it can never be
    two different chances. A chance handed in is taken as it stands; a move that
    hands in none is read off the drawn worlds under the neutral assumption.

    Args:
        draws: The drawn worlds.
        move: What the claim does to the price, and what is already in it.

    Returns:
        The chance and its source.

    Raises:
        KeyError: If the claim is not among the drawn worlds' claims.
    """
    if move.market_chance is not None:
        return ChanceUsed(value=move.market_chance, came_from=move.market_chance_from)
    return ChanceUsed(value=the_sample_s_own_chance(draws, move.claim), came_from="sample_share")


def the_sample_s_own_chance(draws: Draws, claim: PropositionId) -> float:
    """The market's chance of a claim under the neutral assumption, read off the drawn worlds.

    **The market believes what the model believes**, except where a venue says
    otherwise. Read straight off the sample, that chance is the weighted share of
    the drawn worlds in which the claim **comes true inside the trade's window** —
    among the worlds where it was not already true when the window opened, because
    a claim already true is in today's price and the question does not arise for
    it.

    It is this number rather than the claim's printed likelihood, which is read on
    the claim's own resolve-by day and answers a different question. The difference
    is not cosmetic: with this number the weighted mean price is the entry price on
    **every** day, exactly, which is the promise record 0019 makes about the base
    world's path and the sentence the whole supposed-screen demonstration rests on.

    Args:
        draws: The drawn worlds.
        claim: Which claim.

    Returns:
        A chance from nothing to one. **One** where every world the question arises
        for has the claim coming true — a certainty, and a legitimate answer.
        Nothing where the claim is already true in every drawn world, so the
        question arises nowhere.

    Raises:
        KeyError: If the claim is not among the drawn worlds' claims.
    """
    came_on = draws.on_day[:, draws.column(claim)]
    arises = float(draws.weight[came_on != 0].sum())
    inside = float(draws.weight[(came_on != NEVER) & (came_on > 0)].sum())
    return inside / arises if arises > 0.0 else 0.0


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
        daily_move: How far the instrument moves in a day, in price units, which
            these paths were stepped at. Carried because the correction a daily
            check needs is built from it, and a stop checked against a path walked
            at some other variability would be corrected by the wrong amount.
        level: The price in each drawn world on each day, day zero first.
        weight: How much each drawn world counts, carried from the draws so that
            whoever reads these paths does not have to hold both.
        sample: Which sampler the days came from, carried through so that no
            first-touch number can be reported without naming it.
        decay_shape: For each claim that moves the price, which shape its giveback
            followed. Carried because the shape is an assumption and the Inspector
            says which one was used.
        market_chance: For each of those claims, the chance the walk applied and
            where it came from — which may be a number this file worked out rather
            than one handed in.
    """

    day_zero: date
    days: int
    entry: float
    daily_move: float
    level: Levels
    weight: Weights
    sample: SampleFrom
    decay_shape: Mapping[PropositionId, DecayShape]
    market_chance: Mapping[PropositionId, ChanceUsed]


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
    chance = the_chance_applied(draws, move).value
    grid = numpy.arange(draws.days + 1, dtype=numpy.int32)
    if chance >= 1.0:
        return numpy.ones(draws.days + 1), "nothing_given_back"
    came_on = draws.on_day[:, draws.column(move.claim)]
    inside = (came_on != NEVER) & (came_on > 0)
    arriving = float(draws.weight[inside].sum())
    if arriving <= 0.0:
        return chance * (draws.days - grid) / draws.days, "straight_line"

    by = numpy.array(
        [float(draws.weight[inside & (came_on <= day)].sum()) / arriving for day in grid]
    )
    after = 1.0 - by
    return chance * after / (1.0 - chance * by), "arrival_days"


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
    named = [one.claim for one in moves]
    if len(set(named)) != len(named):
        raise ValueError(
            "a claim moves the price by one level gap, and two of these name the same claim"
        )
    if not math.isfinite(daily_move) or daily_move < 0.0:
        raise ValueError(
            f"a day's variability is a distance in price units, never below nothing; "
            f"got {daily_move}"
        )
    if not math.isfinite(entry) or entry <= 0.0:
        raise ValueError(f"an entry price is above nothing; got {entry}")

    grid = numpy.arange(draws.days + 1, dtype=numpy.int32)
    steps = numpy.random.default_rng(seed).standard_normal((draws.worlds, draws.days))
    level = entry + numpy.concatenate(
        [numpy.zeros((draws.worlds, 1)), numpy.cumsum(daily_move * steps, axis=1)], axis=1
    )

    shapes: dict[PropositionId, DecayShape] = {}
    applied: dict[PropositionId, ChanceUsed] = {}
    for one in moves:
        schedule, shapes[one.claim] = giveback_schedule(draws, one)
        applied[one.claim] = the_chance_applied(draws, one)
        carried = _carried(draws, one.claim, schedule, grid)
        level = level + one.move * (carried - carried[:, :1])

    return Paths(
        day_zero=draws.day_zero,
        days=draws.days,
        entry=entry,
        daily_move=daily_move,
        level=level,
        weight=draws.weight,
        sample=draws.sample,
        decay_shape=shapes,
        market_chance=applied,
    )


def _carried(draws: Draws, claim: PropositionId, schedule: Schedule, grid: Days) -> Levels:
    """How much of one claim's move the price carries, per drawn world and per day.

    Three states and no fourth. **Holding** — the claim came on and has not gone off
    — carries the whole move, because the move is the level gap between a world
    where the claim is true and one where it is false. **Gone off** carries nothing,
    because the level gap goes when the claim does; an event never goes off, so this
    only ever touches a state. **Not yet** carries the schedule's share, which is the
    part the market has already priced and gives back day by day.

    The walk subtracts each world's own day-zero amount, so every path starts at the
    entry price whatever state its claims were in when the window opened. A claim
    already on at day zero therefore moves the price by nothing at all — which is
    not a special case but the surprise rule read at a market chance of one: a claim
    that has already happened is in today's price, so there is no surprise to apply
    and nothing left to give back.

    Args:
        draws: The drawn worlds.
        claim: Which claim's move this is.
        schedule: The share of the move the price carries on each day while the
            claim has not happened.
        grid: The days of the window, from zero.

    Returns:
        A share of the move per drawn world per day.
    """
    holding = draws.holding_each_day(claim, grid)
    gone = draws.came_on_each_day(claim, grid) & ~holding
    carried: Levels = numpy.where(
        holding, 1.0, numpy.where(gone, 0.0, numpy.broadcast_to(schedule, holding.shape))
    )
    return carried
