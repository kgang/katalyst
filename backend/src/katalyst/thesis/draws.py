"""Draws: the one thing the trade asks of the engine, and the only thing.

Everything above this file is pure arithmetic over a sample of worlds. This file
says what that sample looks like, so that the trade layer can be built, tested and
read without an engine anywhere near it.

**What a set of draws is.** A window — the day it starts and how many days it runs
— a fixed list of claims, and, for each drawn world and each claim, **the day it
came on** and **the day it went off**. Plus one **weight** per drawn world, and
how many equally-weighted worlds those weights are worth.

Field for field, that is the engine's own forward sample. Whatever adapts one to
the other renames, and never computes.

**Two days, not one, because a claim is an event or a state.** An event never
un-happens, so its off day is always *still holding*. A state can stop, and with a
single day a state that held for three days would be indistinguishable from one
still running when the window closed. Every reader of this shape would inherit
that hole, so the shape closes it once.

**Why there is a weight.** The engine draws worlds forward and sets an observed
claim to what was observed, weighting each world by how likely that observation
was in it. So the worlds are not equally likely and a plain average over them
would be wrong. Every count taken from a set of draws is weighted, everywhere
above this file. Where nothing was observed the weights are all the same number,
and the arithmetic is unchanged.

**How many worlds a weighted sample is really worth** is fewer than were drawn,
and `effective` says how many — measured on the engine's own sampler at about
nineteen worlds in twenty on average and two in five at worst. That is the count
the floor under a lift row is measured against: two hundred **effective** worlds,
not two hundred drawn ones.

**Days come on a coarse grid, not on every day.** The engine cuts the window into
a fixed number of time slices and puts an arrival in the middle of its slice, so
over a two-month window every arrival lands on one of about two dozen days, two
and a half days apart. Nothing here may assume a claim can come on any day: a
daily price path steps sixty times and takes a surprise on at most two dozen of
them, and a histogram of arrival days is coarse by construction.

What this file must never do
----------------------------
- Never import the engine, reach the network, read a clock or draw a random
  number. It is a shape and a handful of checks on it.
- Never assume a claim can come on any day of the window. Arrivals land on the
  middles of the engine's time slices and nowhere else.
- Never let a day outside the window in. A day that is neither inside the window
  nor one of the two markers is a number nobody can read, and every count above
  would quietly inherit it.
- Never treat a claim that never came on as one whose off day means anything.
- Never average over the drawn worlds without their weights.
"""

from dataclasses import dataclass
from datetime import date
from typing import Final, Literal

import numpy
from numpy.typing import NDArray

from katalyst.domain import PropositionId

Days = NDArray[numpy.int32]
"""Whole days, counted from the first day of the window, which is day zero."""

Weights = NDArray[numpy.float64]
"""How much each drawn world counts. Never negative, and never all zero."""

Flags = NDArray[numpy.bool_]
"""True or false, one per drawn world, or one per drawn world and claim."""

SampleFrom = Literal["weighted_forward_sample", "built_by_hand"]
"""Where a set of drawn worlds came from, as a closed list.

`weighted_forward_sample` — the engine's own sampler: worlds drawn forward
carrying the day each claim came on, with an observed claim set to what was
observed and each world weighted by how likely that was. `built_by_hand` — worlds
somebody wrote down, which is what a test does and what a worked example may do.

It is a field rather than a comment because **no first-touch number may be
reported without naming the sample its days came from**: under *This happened*
those days come from a weighted sample with a measured error, and this is the
number the reader acts on. Carrying it on the draws means an answer cannot be
built without it.
"""

THE_SAMPLE_SAYS: Final[dict[str, str]] = {
    "weighted_forward_sample": "the engine's weighted forward sample",
    "built_by_hand": "a set of worlds built by hand",
}
"""What each sample is called on screen, in the same sentence as the number."""

NEVER: Final = -1
"""This claim never came on in this drawn world.

In `on_day` it is the whole story. In `off_day` it appears on exactly the claims
whose `on_day` is `NEVER` too, because a claim that never started cannot have
stopped, and a marker that means *it ended* would be a lie about it.
"""

STILL_HOLDING: Final = -2
"""In `off_day`: this claim had not stopped holding by the last day of the window.

Always this for a claim that is an event, because an event never un-happens. Often
this for a state as well — a state that is still running when the window closes is
the ordinary case, not a special one.

A different number from `NEVER` on purpose. *It never started* and *it started and
has not stopped* are opposite facts, and a reader that had to tell them apart by
looking at the other array would be a reader that could forget to.
"""


@dataclass(frozen=True)
class Draws:
    """A sample of worlds carrying, for each claim, the day it came on and the day it went off.

    The one contract between the trade layer and the engine. Built by whatever
    samples worlds; read by the daily path, by first touch and by lift, and by
    nothing else.

    A plain frozen record rather than one of the shapes that cross to the browser,
    because it holds arrays rather than values: fifty thousand worlds by twenty
    claims is a million numbers, and no browser should ever be sent them. The same
    reason `Versions` in the rules layer is a plain record.

    Attributes:
        day_zero: The first day of the window, which is day zero.
        days: How many days the window runs for, after day zero. So the days a
            claim may come on or go off are 0 through `days`, and a path drawn
            through this window has `days + 1` points.
        claims: The claims, in a fixed order. The columns of the two arrays below
            stand for these claims, in this order.
        on_day: For each drawn world and each claim, the day that claim came on, or
            `NEVER`. Day zero means it was already on when the window opened.
        off_day: For each drawn world and each claim, the day that claim stopped
            holding; `STILL_HOLDING` where it had not stopped by the end of the
            window, and `NEVER` where it never came on at all. Never before the day
            it came on, and equal to it where the engine's grid is coarse enough
            that a state came on and went off inside one day.
        weight: How much each drawn world counts. Never negative, and not all zero.
        effective: How many equally-weighted worlds those weights are worth, which
            is what the floor under a lift row is measured against. Checked here
            against the weights, so it cannot be some other sample's count.
        sample: Which sampler these worlds came from, named so that no number built
            on them can be reported without saying where its days came from.
    """

    day_zero: date
    days: int
    claims: tuple[PropositionId, ...]
    on_day: Days
    off_day: Days
    weight: Weights
    effective: float
    sample: SampleFrom

    def __post_init__(self) -> None:
        """Check the shape hangs together, and say plainly which part does not.

        Seven things are checked: the window is at least one day long; the claims
        are named once each; the two day arrays are one row per drawn world and one
        column per claim, and agree with each other; every day is inside the window
        or is one of the two markers; a claim that never came on never went off,
        and one that came on never went off before it; the weights are one per
        world, none negative and not all zero; and the effective count is the one
        those weights imply.

        Raises:
            ValueError: If any of those seven does not hold. A set of draws that
                does not is a broken promise between our own pieces of code —
                whatever built it built it wrongly — so it is said out loud here
                rather than read as a number somewhere above.
        """
        if self.days < 1:
            raise ValueError(f"a window has to run for at least one day; got {self.days}")
        if len(set(self.claims)) != len(self.claims):
            raise ValueError("a claim may name only one column, and one of these names two")
        _two_dimensions_of_whole_days(self.on_day, "on_day")
        _two_dimensions_of_whole_days(self.off_day, "off_day")
        if self.on_day.shape != self.off_day.shape:
            raise ValueError(
                "the day a claim came on and the day it went off are one array each of the "
                f"same shape; got {self.on_day.shape} against {self.off_day.shape}"
            )
        if self.on_day.shape[1] != len(self.claims):
            raise ValueError(
                f"there are {len(self.claims)} claims, so each array has that many columns; "
                f"got {self.on_day.shape[1]}"
            )
        if self.on_day.shape[0] < 1:
            raise ValueError("a set of draws with no worlds in it answers nothing")
        self._the_days_are_readable()
        self._the_weights_are_usable()

    def _the_days_are_readable(self) -> None:
        """Check every day is inside the window or is one of the two markers.

        And that the two arrays tell the same story: a claim that never came on
        never went off, and a claim that came on did not go off before it did.

        Raises:
            ValueError: If a day is outside the window and is not a marker, if one
                array says a claim never came on where the other says it ended, or
                if a claim went off before it came on.
        """
        came_on = self.on_day != NEVER
        if bool(((self.on_day < 0) & (self.on_day != NEVER)).any()) or bool(
            (self.on_day > self.days).any()
        ):
            raise ValueError(
                f"the day a claim came on is 0 to {self.days}, or {NEVER} for never; "
                f"got days from {int(self.on_day.min())} to {int(self.on_day.max())}"
            )
        marked = (self.off_day == NEVER) | (self.off_day == STILL_HOLDING)
        if bool(((self.off_day < 0) & ~marked).any()) or bool((self.off_day > self.days).any()):
            raise ValueError(
                f"the day a claim went off is 0 to {self.days}, {STILL_HOLDING} for still "
                f"holding, or {NEVER} where it never came on; got days from "
                f"{int(self.off_day.min())} to {int(self.off_day.max())}"
            )
        if bool((came_on != (self.off_day != NEVER)).any()):
            raise ValueError(
                "a claim that never came on never went off, and one that came on did not "
                f"never come on; {NEVER} has to stand in both arrays or in neither"
            )
        ended = came_on & (self.off_day != STILL_HOLDING)
        if bool((self.off_day[ended] < self.on_day[ended]).any()):
            raise ValueError("a claim cannot go off before the day it came on")

    def _the_weights_are_usable(self) -> None:
        """Check the weights are one per world, none negative, not all zero, and counted right.

        Raises:
            ValueError: If the weights are not one per drawn world, if any is
                negative or not a real number, if no world carries any weight, or
                if the effective count is not the one these weights imply.
        """
        if self.weight.ndim != 1 or not numpy.issubdtype(self.weight.dtype, numpy.floating):
            raise ValueError(
                f"the weights are one ordinary number per drawn world; got a {self.weight.ndim}"
                f"-dimensional array of {self.weight.dtype}"
            )
        if self.weight.shape[0] != self.on_day.shape[0]:
            raise ValueError(
                f"there are {self.on_day.shape[0]} drawn worlds and {self.weight.shape[0]} "
                "weights, and there has to be one weight for each world"
            )
        if not bool(numpy.isfinite(self.weight).all()) or bool((self.weight < 0.0).any()):
            raise ValueError("a world's weight is a real number and is never below nothing")
        counted = effective_draws(self.weight)
        if counted <= 0.0:
            raise ValueError("no drawn world carries any weight, so there is nothing to count")
        if abs(self.effective - counted) > 1e-9 * counted:
            raise ValueError(
                f"these weights are worth {counted} equally-weighted worlds, and the count "
                f"handed in says {self.effective}; it is some other sample's count"
            )

    @property
    def worlds(self) -> int:
        """How many worlds were drawn."""
        return int(self.on_day.shape[0])

    def column(self, claim: PropositionId) -> int:
        """Which column of the two day arrays stands for a claim.

        Args:
            claim: The claim to find.

        Returns:
            Its position in `claims`.

        Raises:
            KeyError: If the claim is not in this set of draws at all.
        """
        try:
            return self.claims.index(claim)
        except ValueError:
            raise KeyError(
                f"'{claim}' is not one of the claims these worlds were drawn for"
            ) from None

    def holding_on(self, day: int) -> Flags:
        """Which claims were holding, in which worlds, on a given day.

        A claim is holding on a day when it came on that day or earlier and had not
        gone off by then. A claim that went off **on** that day is not holding on
        it: the day it went off is the first day it is no longer true. So a state
        whose two days are the same day held for no whole day at all, which the
        engine's coarse grid can produce and which this reading handles without a
        special case.

        Args:
            day: A day of the window, counted from zero.

        Returns:
            One true-or-false value per drawn world and claim.
        """
        return _holding(self.on_day, self.off_day, day)

    def came_on_by(self, day: int) -> Flags:
        """Which claims had come on at all by a given day, in which worlds.

        Unlike `holding_on`, this does not care whether the claim later stopped. It
        is what lift reads: *had this claim already happened before the stop was
        touched?* — and a state that came on and then stopped had still happened.

        Args:
            day: A day of the window, counted from zero.

        Returns:
            One true-or-false value per drawn world and claim.
        """
        return _came_on_by(self.on_day, day)

    def holding_each_day(self, claim: PropositionId, grid: Days) -> Flags:
        """Whether one claim was holding, per drawn world, on each day of a grid at once.

        The same rule as `holding_on`, read for one claim over many days instead of
        for many claims on one day — the two share their one expression below, so
        the day a claim stops holding cannot mean one thing to a price path and
        another to everything else.

        Args:
            claim: Which claim.
            grid: The days to read, as a row of whole numbers.

        Returns:
            One true-or-false value per drawn world and day.

        Raises:
            KeyError: If the claim is not in this set of draws at all.
        """
        column = self.column(claim)
        return _holding(self.on_day[:, column, None], self.off_day[:, column, None], grid[None, :])

    def came_on_each_day(self, claim: PropositionId, grid: Days) -> Flags:
        """Whether one claim had come on at all, per drawn world, on each day of a grid.

        Args:
            claim: Which claim.
            grid: The days to read, as a row of whole numbers.

        Returns:
            One true-or-false value per drawn world and day.

        Raises:
            KeyError: If the claim is not in this set of draws at all.
        """
        return _came_on_by(self.on_day[:, self.column(claim), None], grid[None, :])


def _came_on_by(on_day: Days, day: Days | int) -> Flags:
    """Had a claim come on by a day — the one expression, written once.

    Read with a single day it answers for every claim at once; read with a row of
    days it answers for one claim across the window. One expression rather than
    two, because two would be two places the marker for *never* could be forgotten.
    """
    came: Flags = (on_day != NEVER) & (on_day <= day)
    return came


def _holding(on_day: Days, off_day: Days, day: Days | int) -> Flags:
    """Was a claim holding on a day — the one expression, written once.

    Holding means it came on that day or earlier and had not gone off by then. The
    day it went off is the first day it is no longer true, so a state whose two days
    are the same day held for no whole day at all.
    """
    running: Flags = (off_day == STILL_HOLDING) | (off_day > day)
    return _came_on_by(on_day, day) & running


def _two_dimensions_of_whole_days(days: Days, called: str) -> None:
    """Check one of the two day arrays is a grid of whole days.

    Args:
        days: The array to check.
        called: Which of the two it is, so a reader of the failure knows.

    Raises:
        ValueError: If it is not two-dimensional, or does not hold whole numbers.
    """
    if days.ndim != 2 or not numpy.issubdtype(days.dtype, numpy.integer):
        raise ValueError(
            f"`{called}` is a whole day per drawn world per claim; got a {days.ndim}"
            f"-dimensional array of {days.dtype}"
        )


def effective_draws(weight: Weights) -> float:
    """How many equally-weighted worlds a weighted sample is worth.

    The sum of the weights, squared, divided by the sum of their squares. Where
    every world counts the same this is exactly the number of worlds drawn; where
    one world carries most of the weight it is close to one. It is the standard
    count for a weighted sample, and it is the number the two-hundred floor under a
    lift row is measured against, because two hundred worlds of which one carries
    nine tenths of the weight is not two hundred worlds.

    Args:
        weight: One weight per drawn world. None negative, and not all zero.

    Returns:
        The effective count, which is never more than the number of worlds handed
        in. Nothing at all where no world carries any weight.
    """
    total = float(weight.sum())
    squared = float((weight * weight).sum())
    if squared <= 0.0:
        return 0.0
    return total * total / squared


def weighted_share(flags: Flags, weight: Weights) -> float:
    """What share of the drawn worlds a true-or-false answer came out true in.

    Weighted, because the worlds are not equally likely. Written once here because
    every count in this layer is this arithmetic.

    Args:
        flags: One true-or-false value per drawn world.
        weight: One weight per drawn world.

    Returns:
        A share between nothing and one.

    Raises:
        ValueError: If the two do not have one entry each per drawn world, or if no
            world carries any weight.
    """
    if flags.shape != weight.shape:
        raise ValueError(
            "a share is counted over one answer per drawn world; got "
            f"{flags.shape} answers against {weight.shape} weights"
        )
    total = float(weight.sum())
    if total <= 0.0:
        raise ValueError("no drawn world carries any weight, so there is no share to take")
    return float(weight[flags].sum()) / total
