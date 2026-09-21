"""A state's two times: the day it switches on and the day it switches off.

Decision record 0017 is what this file implements.

What this module is for
-----------------------
A claim is one of two kinds of truth. An **event** happens once and stays happened,
so it has one time: the day it happened. A **state** holds over a stretch of time
and can stop, so it has two: the day it switched on and the day it switched off.
Both come out of the same arithmetic — a rate, added up over the claim's own
window.

The rules this module holds
---------------------------
* **The sign of an arrow picks which rate it bends.** An arrow whose stated chance
  is above the claim's own bends the rate at which the claim comes **on**; one
  below it bends the rate at which the claim goes **off**.
* **A state's off-rate starts at zero** and is the sum of its ending causes, so a
  state that nothing on the map can end does not end — and it is then identical to
  the same claim written as an event. No second number is ever elicited for it.
* **One stretch only.** A state switches on at most once and off at most once. A
  thing that comes back is a second claim.
* **The number a state's tile shows is the chance it is holding on its deadline** —
  on by that day, and not yet off. An event's is the chance it happened by that day.
* **A `trigger` arrow reads its source's on time alone** and keeps pushing
  afterwards. **A `sustain` arrow reads its source's whole stretch** and is dead
  once the source stops holding.

The shape conventions — the version axis first, twenty-four slices, an arrival
taken at the middle of its slice, and the last index of a slice axis meaning
*never* — are written out once in `rates.py` and obeyed here.

Two conventions this file settles, which the rest of the engine must match
--------------------------------------------------------------------------
* **An arrow's arrival readings are whatever its carried push is indexed by.** An
  arrow's entry in `ClaimShapes.carried` carries one leading axis when it reads only
  the moment its cause came on, and two when it reads its cause's whole stretch.
  Flattened in the order they are written — the on-slice changing slowest — they
  line up entry for entry with the cause's own times, which is how a push is
  averaged over the times of the claim that caused it.
* **Combinations of the arrows that hold a claim back run in the arrow order of
  `ClaimShapes.holds_back`, the last arrow changing fastest.** That is the axis
  `AddedUp` calls `combos`, and the chance of each combination is the product of the
  arrival readings of the arrows that make it up.

Nothing here searches for a number by trial. There is no loop that narrows a
bracket, and nothing is clipped into range: every rate arrives already worked out
in closed form by `rates.py`, and this file only adds rates up and exponentiates
them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.proposition import Proposition
from katalyst.domain.rates import AddedUp, ClaimShapes, Persistence, Rates, Window

NEVER: Final = -1
"""The marker for *this claim never came on*, where a day index is expected."""

STILL_HOLDING: Final = -2
"""The marker for *this claim has not gone off*.

Every event carries it on its off day, because an event never goes off. A state
carries it when its stretch was still running at the end of the window.
"""


@dataclass(frozen=True)
class Times:
    """When one claim happened, spread across the slices of the window, one row per version.

    An event's times and a state's are held in the same three fields. `as_joint`,
    `holding_curve` and `is_true_on_its_deadline` are how a reader gets at them
    without unpacking a flattened row by hand.
    """

    claim: PropositionId
    """The claim these times belong to."""

    persistence: Persistence
    """Which kind of truth the claim is."""

    spread: NDArray[numpy.float64]
    """`(versions, slices + 1)` the slice the claim came on in. Each row adds to one.

    For an event this is the slice it happened in. For a state it is the slice it
    switched on in. In both cases the last index means it never came on at all.
    """

    holding: NDArray[numpy.float64]
    """`(versions, slices)` the chance the claim is holding at the end of each slice.

    For an event this is the running total of `spread` and can only rise. For a
    state it can fall, because a state that has switched on can switch off again.
    """

    pairs: NDArray[numpy.float64] | None
    """`(versions, (slices + 1) * (slices + 1))` the pair *(on-slice, off-slice)*, or nothing.

    Flattened with the on-slice changing slowest. An on-slice at the last index
    means the claim never came on; an off-slice at the last index means it is still
    holding at the end of the window.

    It is **nothing** for an event, which has no off time, and nothing for a state
    that nothing on the map reads the whole stretch of — see `needs_the_joint`.
    Building it costs the slices-cubed work that path exists to avoid.
    """


def as_joint(times: Times) -> NDArray[numpy.float64]:
    """Unflatten a state's two times into the square they came from.

    Args:
        times: One claim's times. Must be a state's, and must be one whose pair of
            times was built.

    Returns:
        `(versions, slices + 1, slices + 1)` the chance of each pair *(on-slice,
        off-slice)*.

    Raises:
        ValueError: If the claim is an event. An event has one time and no pair, and
            answering with a square that pretends otherwise would be a number nobody
            can account for.
        ValueError: If the claim is a state whose pair of times was not built,
            because nothing on the map reads its whole stretch. Asking for it after
            the fact would silently pay the cost the cheap path exists to avoid.
    """
    if times.persistence == "event":
        raise ValueError(
            f"{times.claim} is an event: it has one time, the moment it happened, "
            "and no pair of times to unflatten."
        )
    if times.pairs is None:
        raise ValueError(
            f"{times.claim} is a state whose pair of times was not worked out, because "
            "no arrow out of it reads its whole stretch. Ask for the pair when the "
            "times are built, not afterwards."
        )
    side = times.spread.shape[1]
    square: NDArray[numpy.float64] = times.pairs.reshape(times.pairs.shape[0], side, side)
    return square


def holding_curve(times: Times) -> NDArray[numpy.float64]:
    """The chance a claim is holding at the end of each slice.

    This is the cheap reading of a state: it is a row per version across the slices,
    where the whole pair of times is a square per version. It is all a `trigger`
    child and all the exact solve ever need.

    Args:
        times: One claim's times.

    Returns:
        `(versions, slices)` the chance the claim is holding at the end of each
        slice. For an event this rises and never falls; for a state it can fall.
    """
    return times.holding


def is_true_on_its_deadline(times: Times) -> NDArray[numpy.float64]:
    """The one bit the exact solve carries: the claim's number as its tile states it.

    For an event, the chance it happened by its deadline. For a state, the chance it
    is holding on its deadline — on by then, and not yet off.

    Every slice past the claim's own deadline is nought days wide, so the end of the
    last slice is the deadline, and this is the last entry of the holding curve.

    Args:
        times: One claim's times.

    Returns:
        `(versions,)` that chance, one number per version.
    """
    last: NDArray[numpy.float64] = times.holding[:, -1]
    return last


def _arrival_weight(
    shapes: ClaimShapes, index: int, cause_times: Sequence[Times]
) -> NDArray[numpy.float64]:
    """How much of the chance sits in each reading one arrow's carried push is indexed by.

    An arrow that reads only the moment its cause came on is indexed by the slice
    that happened in, so its weights are the cause's own `spread`. An arrow that
    reads its cause's whole stretch is indexed by the pair *(on-slice, off-slice)*,
    so its weights are that cause's pair of times, flattened the same way.

    Args:
        shapes: The claim's shapes, whose carried push says which of the two it is.
        index: Which arrow, as a position in `shapes.arrows`.
        cause_times: The times of each cause, in that same arrow order.

    Returns:
        `(versions, readings)` adding to one along the second axis.
    """
    carried = shapes.carried[index]
    when = cause_times[index]
    if carried.ndim == 3:
        return when.spread
    square = as_joint(when)
    flat: NDArray[numpy.float64] = square.reshape(square.shape[0], -1)
    return flat


def _came_on(
    shapes: ClaimShapes,
    added: AddedUp,
    cause_times: Sequence[Times],
) -> NDArray[numpy.float64]:
    """The slice the claim came on in, averaged over everything its causes might have done.

    Because rates add, the chance the claim has not come on yet is a product of one
    factor per cause, and each factor can be averaged over that cause's own times on
    its own. That is why a claim with many causes is one pass and not a pass per
    combination of arrival days. The arrows that **hold** the claim back are the
    exception: they scale the rate rather than adding to it, so `AddedUp` has
    already multiplied them out along its `combos` axis, and all that is left here
    is to weigh each combination by how likely it was.

    Every entry of `AddedUp` is a **running total from day zero to the end of each
    slice**, already multiplied by its rate, so the chance the claim has not come on
    by the end of a slice is the exponential of minus those entries added together.
    Nothing here adds them up a second time.

    Args:
        shapes: The claim's shapes, for its arrow order and what each arrow does.
        added: The claim's rates already added up across the window.
        cause_times: The times of each cause, in the arrow order of `shapes`.

    Returns:
        `(versions, slices + 1)` the slice the claim came on in, the last index
        meaning it never came on.
    """
    versions, combos, slices = added.leak.shape

    chance_of_combination = numpy.ones((versions, 1), dtype=numpy.float64)
    for index in shapes.holds_back:
        arrival = _arrival_weight(shapes, index, cause_times)
        paired = chance_of_combination[:, :, None] * arrival[:, None, :]
        chance_of_combination = paired.reshape(versions, -1)

    not_yet: NDArray[numpy.float64] = numpy.exp(-added.leak)
    for index in shapes.helps:
        arrival = _arrival_weight(shapes, index, cause_times)
        pushed = added.helps[index].reshape(versions, combos, arrival.shape[1], slices)
        not_yet = not_yet * numpy.einsum("vd,vcds->vcs", arrival, numpy.exp(-pushed))

    step = numpy.concatenate([numpy.ones((versions, combos, 1)), not_yet], axis=2)
    by_combination = numpy.empty((versions, combos, slices + 1), dtype=numpy.float64)
    by_combination[:, :, :slices] = step[:, :, :-1] - step[:, :, 1:]
    by_combination[:, :, slices] = not_yet[:, :, -1]
    came_on: NDArray[numpy.float64] = numpy.einsum(
        "vc,vcs->vs", chance_of_combination, by_combination
    )
    return came_on


@dataclass(frozen=True)
class _EndingPush:
    """One ending arrow's push, added up per slice, ready to be exponentiated.

    A state's off-rate starts accruing the moment the state switched **on**, which is
    the middle of its own slice and not the start of it. That is why there are two
    totals and not one.
    """

    rate: NDArray[numpy.float64]
    """`(versions,)` how much this arrow adds to the rate the state stops at."""

    arrival: NDArray[numpy.float64]
    """`(versions, readings)` how likely each reading of this arrow's cause was."""

    from_the_middle: NDArray[numpy.float64]
    """`(readings, slices)` the push over the part of each slice from its middle onwards."""

    running: NDArray[numpy.float64]
    """`(readings, slices)` the push over whole slices, as a running total from day zero."""


def _ending_pushes(
    shapes: ClaimShapes,
    rates: Rates,
    cause_times: Sequence[Times],
    window: Window,
) -> list[_EndingPush]:
    """Each ending arrow's push added up per slice, for each thing its cause might have done.

    Two totals per arrow: the whole of each slice, kept as a running total, and the
    part of a slice from its middle onwards. Getting the second wrong is worth about
    a hundredth on a state's number.

    Args:
        shapes: The claim's shapes, for each ending arrow's carried push and the
            days of its own window in each slice.
        rates: The claim's rates, for how much each ending arrow adds.
        cause_times: The times of each cause, in the arrow order of `shapes`.
        window: The map's window, for the day that stands for an arrival in a slice.

    Returns:
        One entry per ending arrow, in the order `ClaimShapes.ends` lists them.
    """
    slices = shapes.width.shape[0]
    at_or_after_the_middle = window.middle_day[:slices, None] <= shapes.points
    pushes = []
    for index in shapes.ends:
        carried = shapes.carried[index]
        by_reading = carried.reshape(-1, carried.shape[-2], carried.shape[-1])
        whole = shapes.width * by_reading.mean(axis=2)
        part = shapes.width * numpy.where(at_or_after_the_middle, by_reading, 0.0).mean(axis=2)
        pushes.append(
            _EndingPush(
                rate=rates.ends[index],
                arrival=_arrival_weight(shapes, index, cause_times),
                from_the_middle=part,
                running=numpy.cumsum(whole, axis=1),
            )
        )
    return pushes


def _still_on_at_each_slice(
    pushes: Sequence[_EndingPush],
    versions: int,
    slices: int,
) -> NDArray[numpy.float64]:
    """The chance a state that came on in one slice is still holding at the end of another.

    The whole square at once, which is what the pair of times is differenced out of.
    This is the reading that costs versions times slices **cubed**, and it is the one
    `needs_the_joint` exists so that a state nobody reads the stretch of never pays.

    Args:
        pushes: What `_ending_pushes` worked out, one entry per ending arrow.
        versions: How many versions were drawn.
        slices: How many slices the window is cut into.

    Returns:
        `(versions, slices, slices)` the chance it is still holding at the end of
        each slice, given it came on in each slice. One, by construction, wherever
        the end of the slice is before the state came on.
    """
    positions = numpy.arange(slices)
    at_or_after = positions[None, :] >= positions[:, None]
    still_on = numpy.ones((versions, slices, slices), dtype=numpy.float64)
    for push in pushes:
        running = push.running
        stretch = push.from_the_middle[:, :, None] + (running[:, None, :] - running[:, :, None])
        stretch = numpy.where(at_or_after[None], stretch, 0.0)
        survived = numpy.exp(-push.rate[:, None, None, None] * stretch[None])
        still_on = still_on * numpy.einsum("vd,vdak->vak", push.arrival, survived)
    return still_on


def _holding_from_the_square(
    came_on: NDArray[numpy.float64],
    still_on: NDArray[numpy.float64],
    slices: int,
) -> NDArray[numpy.float64]:
    """Read the holding curve off the whole square of *came on then still on*.

    Args:
        came_on: `(versions, slices + 1)` the slice the state came on in.
        still_on: `(versions, slices, slices)` what `_still_on_at_each_slice` gave.
        slices: How many slices the window is cut into.

    Returns:
        `(versions, slices)` the chance it is holding at the end of each slice.
    """
    positions = numpy.arange(slices)
    at_or_after = positions[None, :] >= positions[:, None]
    holding: NDArray[numpy.float64] = numpy.einsum(
        "va,vak->vk", came_on[:, :slices], numpy.where(at_or_after, still_on, 0.0)
    )
    return holding


def _holding_without_the_square(
    came_on: NDArray[numpy.float64],
    pushes: Sequence[_EndingPush],
    versions: int,
    slices: int,
) -> NDArray[numpy.float64]:
    """The holding curve, one slice end at a time, without ever holding the whole square.

    **The cheap path's arithmetic.** The answer is the same as reading the curve off
    the square — the two agree to twelve decimal places, and a test says so — but the
    biggest thing in hand at any moment is a row per version across the readings of
    one ending arrow, never a square per version.

    Args:
        came_on: `(versions, slices + 1)` the slice the state came on in.
        pushes: What `_ending_pushes` worked out, one entry per ending arrow.
        versions: How many versions were drawn.
        slices: How many slices the window is cut into.

    Returns:
        `(versions, slices)` the chance it is holding at the end of each slice.
    """
    holding = numpy.empty((versions, slices), dtype=numpy.float64)
    for end_of in range(slices):
        reached = end_of + 1
        still_on = numpy.ones((versions, reached), dtype=numpy.float64)
        for push in pushes:
            running = push.running
            stretch = push.from_the_middle[:, :reached] + (
                running[:, end_of][:, None] - running[:, :reached]
            )
            survived = numpy.exp(-push.rate[:, None, None] * stretch[None])
            still_on = still_on * numpy.einsum("vd,vda->va", push.arrival, survived)
        holding[:, end_of] = (came_on[:, :reached] * still_on).sum(axis=1)
    return holding


def _pairs_of_times(
    came_on: NDArray[numpy.float64],
    still_on: NDArray[numpy.float64],
    slices: int,
) -> NDArray[numpy.float64]:
    """Difference *still holding* into the chance of each pair *(on-slice, off-slice)*.

    Args:
        came_on: `(versions, slices + 1)` the slice the state came on in.
        still_on: `(versions, slices, slices)` what `_still_on_at_each_slice` gave.
        slices: How many slices the window is cut into.

    Returns:
        `(versions, (slices + 1) * (slices + 1))` flattened with the on-slice
        changing slowest.
    """
    versions = came_on.shape[0]
    square = numpy.zeros((versions, slices + 1, slices + 1), dtype=numpy.float64)
    step = numpy.concatenate([numpy.ones((versions, slices, 1)), still_on], axis=2)
    square[:, :slices, :slices] = came_on[:, :slices, None] * (step[:, :, :-1] - step[:, :, 1:])
    square[:, :slices, slices] = came_on[:, :slices] * still_on[:, :, -1]
    square[:, slices, slices] = came_on[:, slices]
    flat: NDArray[numpy.float64] = square.reshape(versions, -1)
    return flat


def on_and_off(
    shapes: ClaimShapes,
    rates: Rates,
    added: AddedUp,
    cause_times: Sequence[Times],
    *,
    window: Window,
    persistence: Persistence,
    joint: bool,
) -> Times:
    """Work out when one claim came on, and — for a state — when it went off.

    The causes are already done, so their own times are passed in; this adds their
    pushes to the claim's rates and turns the total into the chance the claim came
    on in each slice, and went off in each later one.

    An event has one time, so for an event this is the moment it happened and
    nothing else. A state whose map holds nothing that can end it has an off-rate of
    nought, so it never goes off, and its times come out identical to the same claim
    written as an event.

    Args:
        shapes: The claim's shapes, in whose arrow order `cause_times` is read.
        rates: The claim's rates, one column per version.
        added: Those rates already added up across the window.
        cause_times: The times of each cause, in the arrow order of `shapes`.
        window: The map's window, for the day that stands for an arrival in a slice.
            A state's off-rate starts accruing at that day, not at the start of the
            slice, and only this object says where it falls.
        persistence: Which kind of truth this claim is. Passed in rather than read
            off the claim, because the field that carries it arrives with the flip.
        joint: True to build the whole pair of times, false to build only enough for
            the holding curve. `needs_the_joint` is what decides this, and building
            the pair when nothing reads it costs slices cubed for nothing.

    Returns:
        This claim's times.
    """
    versions, _, slices = added.leak.shape
    came_on = _came_on(shapes, added, cause_times)

    if persistence == "event":
        return Times(
            claim=shapes.claim,
            persistence=persistence,
            spread=came_on,
            holding=numpy.cumsum(came_on[:, :slices], axis=1),
            pairs=None,
        )

    pushes = _ending_pushes(shapes, rates, cause_times, window)
    still_on = _still_on_at_each_slice(pushes, versions, slices) if joint else None

    if not shapes.ends:
        holding = numpy.cumsum(came_on[:, :slices], axis=1)
    elif still_on is not None:
        holding = _holding_from_the_square(came_on, still_on, slices)
    else:
        holding = _holding_without_the_square(came_on, pushes, versions, slices)

    return Times(
        claim=shapes.claim,
        persistence=persistence,
        spread=came_on,
        holding=holding,
        pairs=None if still_on is None else _pairs_of_times(came_on, still_on, slices),
    )


def needs_the_joint(graph: Graph, claim: Proposition, persistence: Persistence) -> bool:
    """Say whether anything on this map reads a state's whole stretch rather than one moment of it.

    **The cheap path.** Only a `sustain` child reads a state's whole stretch, and
    building that costs versions times slices **cubed** where the holding curve
    alone never holds more than a row per version across one arrow's readings.

    **No measured saving is claimed for this.** The forward-pass timing decision
    record 0017 quotes already skipped the pair of times for the states no `sustain`
    arrow left. This exists so that a map full of states nobody reads the stretch of
    does not pay slices cubed for work no reader wants — not as an improvement on a
    number already measured.

    The check on the kind of truth is load-bearing between the flip and the shape
    freeze: the rule that a `sustain` arrow may only leave a state rides the freeze,
    and until then the code that mints a claim from a recorded proposal makes every
    one an event. Without the check this would ask for the pair of times of a claim
    that has no off time at all.

    Args:
        graph: The map, for its arrows.
        claim: The claim being asked about.
        persistence: Which kind of truth that claim is. Passed in rather than read
            off the claim, because the field that carries it arrives with the flip.

    Returns:
        True when the claim is a state and some `sustain` arrow leaves it.
    """
    return persistence == "state" and any(
        arrow.mode == "sustain" and arrow.source == claim.id for arrow in graph.links
    )
