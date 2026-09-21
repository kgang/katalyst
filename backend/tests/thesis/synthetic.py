"""Worlds built by hand, so the trade layer can be checked without an engine anywhere near it.

Everything above `Draws` is pure arithmetic over a sample of worlds, and this file
writes those samples down. Two reasons that is the right way round:

* **No engine number is typed into a test.** A set of draws written here is an
  input the test chose, so every answer worked out from it can be worked out on
  paper in the test's own docstring. The engine's numbers move at the flip, and
  nothing here moves with them.
* **The real sample is coarse and weighted, and a hand-made one must be too.** The
  engine cuts the window into a fixed number of time slices and puts an arrival in
  the middle of its slice, so over a two-month window arrivals land on about two
  dozen days, two and a half days apart — never on an arbitrary day. And the
  weights are real. A generator that drew a day uniformly and a weight of one
  would test arithmetic nobody will ever run.

`worlds_of` builds a small set by hand from a readable table. `draws()` and
`positions()` generate them by the hundred for the property tests.
"""

from collections.abc import Sequence
from datetime import date
from typing import Any

import numpy
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy, composite

from katalyst.domain import PropositionId
from katalyst.thesis.draws import NEVER, STILL_HOLDING, Draws, effective_draws
from katalyst.thesis.position import Position

DAY_ZERO = date(2026, 10, 1)
"""The day every window in these tests opens on. Nothing reads it for its own sake."""

SLICES = 24
"""How many time slices the engine cuts a window into, which is what makes arrivals coarse."""


def slice_middles(days: int, slices: int = SLICES) -> tuple[int, ...]:
    """The days an arrival can land on: the middle of each time slice, rounded to a whole day.

    The engine takes an arrival at the middle of its slice, so over a sixty-day
    window cut into twenty-four slices every arrival lands on one of about
    twenty-four days, two and a half days apart. Over a window shorter than the
    number of slices two middles round to the same day, which is allowed and is
    why a claim may come on and go off on one day.

    Args:
        days: How long the window runs for.
        slices: How many slices it is cut into.

    Returns:
        The days an arrival may land on, in order, without repeats.
    """
    middles = sorted({round((half + 0.5) * days / slices) for half in range(slices)})
    return tuple(day for day in middles if 0 <= day <= days)


def worlds_of(
    *,
    claims: Sequence[str],
    on: Sequence[Sequence[int]],
    off: Sequence[Sequence[int]] | None = None,
    weight: Sequence[float] | None = None,
    days: int = 30,
    day_zero: date = DAY_ZERO,
) -> Draws:
    """Write a small set of drawn worlds down as a table.

    One row per drawn world, one column per claim, holding the day that claim came
    on or `NEVER`. Where no off days are given every claim that came on is still
    holding, which is what an event always is.

    Args:
        claims: The claims, in the order the columns stand for.
        on: The day each claim came on in each drawn world.
        off: The day each claim went off, if any of them did.
        weight: How much each drawn world counts. All the same where not given.
        days: How long the window runs for.
        day_zero: The day it opens on.

    Returns:
        The drawn worlds, with the effective count their weights imply.
    """
    came = numpy.array(on, dtype=numpy.int32).reshape(len(on), len(claims))
    went = (
        numpy.where(came == NEVER, NEVER, STILL_HOLDING).astype(numpy.int32)
        if off is None
        else numpy.array(off, dtype=numpy.int32).reshape(len(on), len(claims))
    )
    counts = numpy.ones(len(on)) if weight is None else numpy.array(weight, dtype=numpy.float64)
    return Draws(
        day_zero=day_zero,
        days=days,
        claims=tuple(PropositionId(one) for one in claims),
        on_day=came,
        off_day=went,
        weight=counts,
        effective=effective_draws(counts),
        sample="built_by_hand",
    )


@composite
def draws(
    draw: Any,
    *,
    claims: int | None = None,
    worlds: int | None = None,
    days: int | None = None,
    even_weights: bool = False,
    already_on: bool = True,
    events_only: bool = False,
) -> Draws:
    """Generate a set of drawn worlds with coarse arrival days and real weights.

    Arrivals land on the middles of the engine's time slices and nowhere else, and
    a state may go off on any later middle. Weights are drawn above nothing, so
    the effective count is genuinely below the number of worlds unless the test
    asks for even ones.

    Args:
        draw: Hypothesis's own drawing function.
        claims: How many claims, or nothing to let it choose.
        worlds: How many drawn worlds, or nothing to let it choose.
        days: How long the window runs for, or nothing to let it choose.
        even_weights: True to weight every world the same, for a test about
            something other than weighting.
        already_on: False to leave out claims that were already on when the window
            opened.
        events_only: True to make every claim an event — once it comes on it holds
            to the end of the window. **The path prices the chance a claim comes
            true and not the chance it stops**, because nothing asks the model for
            that second number yet, so a test about the path inventing no advantage
            has to say so and leave states out.

    Returns:
        One set of drawn worlds.
    """
    how_many_claims = claims if claims is not None else draw(st.integers(1, 4))
    how_many_worlds = worlds if worlds is not None else draw(st.integers(4, 40))
    how_long = days if days is not None else draw(st.integers(8, 60))
    grid = slice_middles(how_long)
    if not already_on:
        grid = tuple(day for day in grid if day > 0) or (1,)

    came = numpy.full((how_many_worlds, how_many_claims), NEVER, dtype=numpy.int32)
    went = numpy.full((how_many_worlds, how_many_claims), NEVER, dtype=numpy.int32)
    for world in range(how_many_worlds):
        for claim in range(how_many_claims):
            if not draw(st.booleans()):
                continue
            came[world, claim] = draw(st.sampled_from(grid))
            later = [day for day in grid if day >= came[world, claim]]
            went[world, claim] = (
                STILL_HOLDING
                if events_only or draw(st.booleans())
                else draw(st.sampled_from(later))
            )

    counts = (
        numpy.ones(how_many_worlds)
        if even_weights
        else numpy.array(
            [
                draw(st.floats(0.05, 4.0, allow_nan=False, allow_infinity=False))
                for _ in range(how_many_worlds)
            ]
        )
    )
    return Draws(
        day_zero=DAY_ZERO,
        days=how_long,
        claims=tuple(PropositionId(f"claim-{one}") for one in range(how_many_claims)),
        on_day=came,
        off_day=went,
        weight=counts,
        effective=effective_draws(counts),
        sample="built_by_hand",
    )


@composite
def positions(draw: Any, *, trades: str = "instrument", ending: str = "ending-0") -> Position:
    """Generate a position whose stop and target are on the right sides of the entry.

    The form's own rules are checked elsewhere; a position from here is one that
    passed them, so a test about first touch is about first touch.

    Args:
        draw: Hypothesis's own drawing function.
        trades: Whether the ending names something traded or a contract.
        ending: What the ending is called.

    Returns:
        One position.
    """
    entry = draw(st.floats(20.0, 200.0, allow_nan=False, allow_infinity=False))
    side = draw(st.sampled_from(["long", "short"]))
    away = draw(st.floats(0.01, 0.2, allow_nan=False, allow_infinity=False))
    toward = draw(st.floats(0.01, 0.4, allow_nan=False, allow_infinity=False))
    losing = -1.0 if side == "long" else 1.0
    return Position(
        ending=PropositionId(ending),
        instrument="the instrument",
        side=side,
        trades=trades,  # type: ignore[arg-type]
        entry=entry,
        stop=entry * (1.0 + losing * away),
        target=entry * (1.0 - losing * toward),
        horizon=date(2026, 10, 31),
        risk_budget=draw(st.floats(0.001, 0.5, allow_nan=False, allow_infinity=False)),
        daily_move=entry * draw(st.floats(0.002, 0.03, allow_nan=False, allow_infinity=False)),
    )


def whole_days(draws_from: Draws) -> SearchStrategy[int]:
    """Every day of a window, as something to draw one of."""
    return st.integers(0, draws_from.days)
