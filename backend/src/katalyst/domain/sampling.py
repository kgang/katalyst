"""Worlds drawn forward with weights: what *This happened* needs, and the days stack 06 reads.

**Stubs.** Every function below raises `NotImplementedError`. Decision record 0016
is what this file implements.

What this module is for
-----------------------
The exact solve answers **whether** each claim is true. It cannot say **when**,
once something has been observed, because seeing that a claim happened moves the
day its causes happened as well as whether they did. So worlds are drawn forward
under the full time model, each kept and weighted by how well it matches what was
seen rather than thrown away — the standard name for that is *likelihood
weighting*.

**One sampler, two readers.** The same draw answers *This happened* and hands
stack 06 the event days a path needs.

**The trick that makes it cheap and accurate.** Each world is drawn twice from the
**same** random numbers: once under the full time model, and once under the plain
yes/no model whose answer the solve already knows exactly. Only the *difference*
between the two is sampled, and that difference is added to the exact answer. The
standard name is a *control variate*. Where the evidence moves nothing, the
difference is zero and the exact answer is left exactly where it was.

**One draw serves every version.** The draw is made at **version 0** — the first
row of the evenly spread draw — and the correction it produces is one number per
claim, added to every version's exact answer. Which version to draw at is a choice
nothing measured, so it is named rather than assumed. What bounds the error of
sharing it is measured, and lives in the stack's own notes.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import numpy
from numpy.typing import NDArray

from katalyst.domain.forward import Forward
from katalyst.domain.ids import PropositionId
from katalyst.domain.rates import AddedUp, ClaimShapes, Pin, Rates


@dataclass(frozen=True)
class Ready:
    """One claim's survival factors, worked out once, so drawing a world is gathers and products.

    *Survival* here means the chance a claim has **not** happened yet by the end of
    a slice. Taking the exponential of an added-up rate is the expensive part of
    drawing a world, so it is done once per claim before any world is drawn rather
    than once per world.

    There is no version axis in here: the draw is made at one version, named by
    `Sample.version`.
    """

    leak: NDArray[numpy.float64]
    """`(combos, slices)` surviving the no-cause rate through each slice.

    `combos` counts the combinations of arrival slices of the arrows that hold the
    claim back — the one place the work still multiplies out.
    """

    helps: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(combos, slices + 1, slices)` surviving that helping cause through each slice.

    The middle axis is the slice its cause arrived in; its last index means the
    cause never came.
    """


@dataclass(frozen=True)
class Sample:
    """Worlds drawn forward, each with a weight, and the day every claim came on and went off.

    This is the whole of what stack 06 reads from the engine: the window, the claims
    in a fixed order, a day per claim per drawn world, and a weight per drawn world.
    """

    seed: int
    """The one number every draw in here came from.

    The same seed gives the same days and the same weights, on any machine.
    """

    worlds: int
    """How many worlds were drawn."""

    version: int
    """Which version the draw was made at. Version 0, the first row of the evenly spread draw."""

    day_zero: date
    """The day the window starts on."""

    days: int
    """How many whole days the window runs for."""

    claims: tuple[PropositionId, ...]
    """Every claim, in a fixed order. This is the column order of the two day tables."""

    on_day: NDArray[numpy.int32]
    """`(worlds, claims)` which day of the window each claim came on, or `NEVER`.

    Every arrival is the middle of a slice rounded to a whole day, so at twenty-four
    slices over a sixty-day window every arrival lands on one of twenty-four days,
    about two and a half days apart. A reader that steps a day at a time will see a
    surprise on at most twenty-four of them.
    """

    off_day: NDArray[numpy.int32]
    """`(worlds, claims)` which day each claim went off, or `STILL_HOLDING`, or `NEVER`.

    **An event's is always `STILL_HOLDING`**, because an event never goes off. A
    state's may be too, when its stretch was still running at the end of the window.
    A claim that never came on carries `NEVER` in both tables.
    """

    weight: NDArray[numpy.float64]
    """`(worlds,)` how much each drawn world counts.

    **These are real numbers, not all ones.** Every count taken off this sample is a
    weighted one.
    """

    effective: float
    """How many draws the weights are really worth.

    The square of their sum, divided by the sum of their squares. A floor on how
    many draws an answer may rest on counts **this**, never the number of rows drawn.
    """

    correction: Mapping[PropositionId, float]
    """Claim -> one number, added to that claim's exact answer in **every** version.

    A single number per claim rather than one per version, because the draw is made
    at one version. That is what makes the sample a fixed cost rather than one paid
    two thousand times over.
    """


def ready_to_sample(shapes: ClaimShapes, rates: Rates, added: AddedUp, *, version: int) -> Ready:
    """Take the exponential of one claim's added-up rates, once, at one version.

    Args:
        shapes: The claim's shapes, for its arrow order.
        rates: The claim's rates, of which one column is used.
        added: Those rates added up across the window.
        version: Which column of the rates to draw at.

    Returns:
        The claim's survival factors, with no version axis left.
    """
    raise NotImplementedError


def sample_forward(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    *,
    version: int,
    seed: int,
    worlds: int = 50_000,
    chunk: int = 50_000,
    exact: Mapping[PropositionId, NDArray[numpy.float64]],
) -> Sample:
    """Draw worlds forward, weight them by the evidence, and correct the exact answer.

    Args:
        forward: The finished forward pass, whose rates and tables the worlds are
            drawn from.
        pinned: The claims an edit fixed a value on. A *Suppose this is true* entry
            holds its claim on from its day; a *This happened* entry is what the
            weights are worked out against.
        version: Which version to draw at. Version 0 unless a test says otherwise.
        seed: The one number every draw comes from.
        worlds: How many worlds to draw.
        chunk: How many worlds to hold in memory at once. Purely about memory: the
            days and weights do not depend on it.
        exact: Claim -> `(versions,)` the exact answer the solve gave, which the
            correction is measured against and added back to.

    Returns:
        The drawn worlds, their weights, the days, and one correction per claim.
    """
    raise NotImplementedError
