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
* **An arrow's arrival readings are whatever its carried push is read by.** An
  arrow's entry in `ClaimShapes.carried` is read by the slice its cause came on in
  when it reads only that moment, and by the pair *(came on, went off)* when it reads
  its cause's whole stretch. Flattened in the order they are written — the on-slice
  changing slowest — they line up entry for entry with the cause's own times, which
  is how a push is averaged over the times of the claim that caused it. **Readings
  whose push is the same array of numbers are folded together first**, which is the
  same sum in a different order; `chance_of_each_reading` is the one place that fold
  is taken, and every axis below it is the folded count.
* **Combinations of the arrows that hold a claim back run in the arrow order of
  `ClaimShapes.holds_back`, the last arrow changing fastest.** That is the axis
  `AddedUp` calls `combos`, and the chance of each combination is the product of the
  folded arrival chances of the arrows that make it up.

Nothing here searches for a number by trial. There is no loop that narrows a
bracket, and nothing is clipped into range: every rate arrives already worked out
in closed form by `rates.py`, and this file only adds rates up and exponentiates
them.
"""

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.proposition import Persistence, Proposition
from katalyst.domain.rates import AddedUp, Carried, ClaimShapes, Rates, Spread

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
    that nothing on the map reads the whole stretch of — see `needs_the_joint`. It
    is a square of chances per version where the holding curve is a row, and an arrow
    that reads a whole stretch is indexed by a square of readings rather than a row
    of them, so everything downstream of it grows with it.
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


def chance_of_each_reading(carried: Carried, when: Times) -> NDArray[numpy.float64]:
    """How much of the chance sits on each **different** push one arrow carries.

    An arrow that reads only the moment its cause came on is read by the slice that
    happened in, so its chances are the cause's own `spread`. An arrow that reads its
    cause's whole stretch is read by the pair *(on-slice, off-slice)*, so its chances
    are that cause's pair of times, flattened the same way.

    Either way the answer is then **folded**: readings whose push is the same array of
    numbers have their chances added together, because everything downstream of them
    is the same array of numbers too. That is the same sum written in a different
    order, and it is what keeps a cause judged long after this claim — whose late
    arrival slices all push nothing at all — from costing a reading each.

    Args:
        carried: That one arrow's push carried to the claim's reading days, which
            says which of the two readings the arrow is read by and which of them
            carry the same numbers.
        when: The times of the claim that arrow comes from.

    Returns:
        `(versions, different)` adding to one along the second axis.
    """
    if not carried.whole_stretch:
        return carried.fold(when.spread)
    square = as_joint(when)
    return carried.fold(square.reshape(square.shape[0], -1))


def _chance_of_each_combination(
    shapes: ClaimShapes, cause_times: Sequence[Times], versions: int
) -> NDArray[numpy.float64]:
    """How likely each combination of the holding-back arrows' arrival times was.

    The arrows that hold a claim back scale its rate rather than adding to it, so
    `AddedUp` has already multiplied them out along its `combos` axis; this is the
    weight each of those combinations carries. A claim no arrow holds back has one
    combination, of weight one — and a **state** is always such a claim, because an
    arrow stated below a state's own chance ends it rather than holding it back.

    Args:
        shapes: The claim's shapes, for which arrows hold it back and in what order.
        cause_times: The times of each cause, in the arrow order of `shapes`.
        versions: How many versions were drawn.

    Returns:
        `(versions, combos)`, the last arrow of `ClaimShapes.holds_back` changing
        fastest.
    """
    chance = numpy.ones((versions, 1), dtype=numpy.float64)
    for index in shapes.holds_back:
        arrival = chance_of_each_reading(shapes.carried[index], cause_times[index])
        paired = chance[:, :, None] * arrival[:, None, :]
        chance = paired.reshape(versions, -1)
    return chance


def _a_helping_arrows_factors(
    added_help: Spread, arrivals: Sequence[NDArray[numpy.float64]]
) -> list[NDArray[numpy.float64]]:
    """One helping arrow's share of *the claim has not come on yet*, under each reading asked for.

    **This is the one costly line in a claim's on-process**, and the reason it is a
    function of its own. Three things keep it in bounds. The exponential is taken
    **once** and every reading asked for is averaged against the same one — a yes/no
    table asks for the arrow's cause false and true, and both come out of one pass.
    It is worked out **once per reading**, never once per combination of every cause's
    truth. And it is worked out **a block of versions at a time**, because the array
    it exponentiates is versions by combinations by readings by slices, which on a map
    with two arrows holding one claim back would otherwise be gigabytes.

    Args:
        added_help: That arrow's rate added up to the end of each slice, for each
            thing its cause might have done.
        arrivals: One `(versions, readings)` array per reading asked for: how likely
            each of those things was.

    Returns:
        One `(versions, combos, slices)` array per reading asked for — the share this
        arrow leaves of the chance the claim has not come on by the end of each slice.
    """
    averaged = [
        numpy.empty((added_help.versions, added_help.combos, added_help.slices)) for _ in arrivals
    ]
    for first, last in added_help.version_blocks():
        survived = numpy.exp(-added_help.between(first, last))
        for one, arrival in zip(averaged, arrivals, strict=True):
            one[first:last] = numpy.einsum(
                "vd,vcds->vcs", arrival[first:last], survived, optimize=True
            )
    return averaged


def _not_yet_on(
    survived_leak: NDArray[numpy.float64], factors: Sequence[NDArray[numpy.float64]]
) -> NDArray[numpy.float64]:
    """The chance the claim has not come on by the end of each slice.

    Because rates add, this is a product of one factor per cause, and each factor
    was averaged over that cause's own times on its own. That is why a claim with
    many causes is one pass and not a pass per combination of arrival days.

    Args:
        survived_leak: `(versions, combos, slices)` what the claim's own rate alone
            leaves — the exponential of minus its added-up leak.
        factors: One entry per helping arrow, in the arrow order of the claim's
            shapes, each `(versions, combos, slices)`.

    Returns:
        `(versions, combos, slices)`.
    """
    not_yet = survived_leak
    for factor in factors:
        not_yet = not_yet * factor
    return not_yet


def _spread_of_arrivals(
    not_yet: NDArray[numpy.float64], chance_of_combination: NDArray[numpy.float64]
) -> NDArray[numpy.float64]:
    """Difference *not yet on* into the slice the claim came on in.

    Every entry of `AddedUp` is a **running total from day zero to the end of each
    slice**, so the chance of coming on inside a slice is the drop across it, and
    what is left at the end of the last slice is the chance of never coming on.
    Nothing here adds anything up a second time.

    Args:
        not_yet: `(versions, combos, slices)` the chance the claim has not come on by
            the end of each slice.
        chance_of_combination: `(versions, combos)` how likely each combination was.

    Returns:
        `(versions, slices + 1)` the slice the claim came on in, the last index
        meaning it never came on.
    """
    versions, combos, slices = not_yet.shape
    step = numpy.concatenate([numpy.ones((versions, combos, 1)), not_yet], axis=2)
    by_combination = numpy.empty((versions, combos, slices + 1), dtype=numpy.float64)
    by_combination[:, :, :slices] = step[:, :, :-1] - step[:, :, 1:]
    by_combination[:, :, slices] = not_yet[:, :, -1]
    came_on: NDArray[numpy.float64] = numpy.einsum(
        "vc,vcs->vs", chance_of_combination, by_combination
    )
    return came_on


def _came_on(
    shapes: ClaimShapes,
    added: AddedUp,
    cause_times: Sequence[Times],
) -> NDArray[numpy.float64]:
    """The slice the claim came on in, averaged over everything its causes might have done.

    Args:
        shapes: The claim's shapes, for its arrow order and what each arrow does.
        added: The claim's rates already added up across the window.
        cause_times: The times of each cause, in the arrow order of `shapes`.

    Returns:
        `(versions, slices + 1)` the slice the claim came on in, the last index
        meaning it never came on.
    """
    versions = int(added.leak.shape[0])
    return _spread_of_arrivals(
        _not_yet_on(
            numpy.exp(-added.leak),
            [
                _a_helping_arrows_factors(
                    added.helps[index],
                    [chance_of_each_reading(shapes.carried[index], cause_times[index])],
                )[0]
                for index in shapes.helps
            ],
        ),
        _chance_of_each_combination(shapes, cause_times, versions),
    )


@dataclass(frozen=True)
class _EndingPush:
    """One ending arrow's push, added up per slice, ready to be exponentiated.

    A state's off-rate starts accruing the moment the state switched **on**, which is
    the middle of its own slice and not the start of it. That is why there are two
    totals and not one.

    Nothing in here depends on what any cause was held true or false at, so one of
    these is worked out once per ending arrow and read under every combination of
    the claim's causes' truths.
    """

    rate: NDArray[numpy.float64]
    """`(versions,)` how much this arrow adds to the rate the state stops at."""

    from_the_middle: NDArray[numpy.float64]
    """`(readings, slices)` the push over the part of each slice from its middle onwards."""

    running: NDArray[numpy.float64]
    """`(readings, slices)` the push over whole slices, as a running total from day zero."""


def _ending_pushes(shapes: ClaimShapes, rates: Rates) -> list[_EndingPush]:
    """Each ending arrow's push added up per slice, for each thing its cause might have done.

    Two totals per arrow: the whole of each slice, kept as a running total, and the
    part of a slice from its middle onwards. Getting the second wrong is worth about
    a hundredth on a state's number.

    Args:
        shapes: The claim's shapes, for each ending arrow's carried push and the
            days of its own window in each slice.
        rates: The claim's rates, for how much each ending arrow adds.

    Returns:
        One entry per ending arrow, in the order `ClaimShapes.ends` lists them.
    """
    slices = shapes.width.shape[0]
    at_or_after_the_middle = shapes.middle_day[:slices, None] <= shapes.points
    pushes = []
    for index in shapes.ends:
        by_reading = shapes.carried[index].push
        whole = shapes.width * by_reading.mean(axis=2)
        part = shapes.width * numpy.where(at_or_after_the_middle, by_reading, 0.0).mean(axis=2)
        pushes.append(
            _EndingPush(
                rate=rates.ends[index],
                from_the_middle=part,
                running=numpy.cumsum(whole, axis=1),
            )
        )
    return pushes


def _ending_arrivals(
    shapes: ClaimShapes, cause_times: Sequence[Times]
) -> list[NDArray[numpy.float64]]:
    """How likely each reading of each ending arrow's cause was, in the order `ends` lists them."""
    return [
        chance_of_each_reading(shapes.carried[index], cause_times[index]) for index in shapes.ends
    ]


def _split_the_stretch(
    push: _EndingPush,
) -> tuple[NDArray[numpy.float64], NDArray[numpy.float64]]:
    """One ending arrow's survival, split into an on-slice part and an end-of-slice part.

    **This split is what makes a state affordable, and it is exact.** The push an
    ending arrow has laid down between the middle of the slice the state came on in
    and the end of some later slice is

        from the middle of the on-slice, plus the running total to the end,
        less the running total to the on-slice

    — one term that depends only on the slice the state came on in, and one that
    depends only on the slice being asked about. The exponential of a sum is a
    product, so the survival is a product of two arrays of *a row per version across
    a reading and a slice*, rather than one array across a reading and a slice
    **squared**. On a map where an ending arrow reads a state's whole stretch that is
    six hundred and twenty-five readings, and writing the square out directly asked
    for versions by readings by slices by slices exponentials — gigabytes of them.

    Args:
        push: One ending arrow's added-up push.

    Returns:
        Two arrays, both `(versions, readings, slices)`. Multiply the first at the
        slice the state came on in by the second at the end of a later slice to get
        the chance this arrow alone has not ended it by then.
    """
    leaving = push.from_the_middle - push.running
    on_slice: NDArray[numpy.float64] = numpy.exp(-push.rate[:, None, None] * leaving[None])
    to_the_end: NDArray[numpy.float64] = numpy.exp(-push.rate[:, None, None] * push.running[None])
    return on_slice, to_the_end


def _survival_on_the_deadline(push: _EndingPush) -> NDArray[numpy.float64]:
    """The chance one ending arrow alone has not ended a state by its deadline.

    The end of the last slice **is** the claim's deadline, because every claim is cut
    from its own resolve-by day, so this is the split above read at that one end
    rather than at all of them: `(versions, readings, slices)` and not a slice
    squared. It is all a claim's yes/no table ever needs, and the table is asked for
    once per combination of the claim's causes' truths.

    Args:
        push: One ending arrow's added-up push.

    Returns:
        `(versions, readings, slices)`, indexed by the slice the state came on in.
    """
    tail = push.from_the_middle + push.running[:, -1][:, None] - push.running
    survived: NDArray[numpy.float64] = numpy.exp(-push.rate[:, None, None] * tail[None])
    return survived


def _still_on_at_each_slice(
    pushes: Sequence[_EndingPush],
    arrivals: Sequence[NDArray[numpy.float64]],
    versions: int,
    slices: int,
) -> NDArray[numpy.float64]:
    """The chance a state that came on in one slice is still holding at the end of another.

    The whole square at once, which is what the pair of times is differenced out of.
    It is built from the split above, so the largest thing in hand is a row per
    version across a reading and a slice, and the square itself — a row per version
    across a slice and a slice — is small.

    Args:
        pushes: What `_ending_pushes` worked out, one entry per ending arrow.
        arrivals: How likely each reading of each of those arrows' causes was, in the
            same order.
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
    for push, arrival in zip(pushes, arrivals, strict=True):
        on_slice, to_the_end = _split_the_stretch(push)
        weighed = arrival[:, :, None] * on_slice
        both = numpy.einsum("vda,vdk->vak", weighed, to_the_end, optimize=True)
        # Before the state came on there is nothing for this arrow to have ended, so
        # every reading of its cause leaves the state standing and the readings add
        # up to the whole of the chance.
        anything = arrival.sum(axis=1)[:, None, None]
        still_on = still_on * numpy.where(at_or_after[None], both, anything)
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
    arrivals: Sequence[NDArray[numpy.float64]],
    versions: int,
    slices: int,
) -> NDArray[numpy.float64]:
    """The holding curve, one slice end at a time, without ever holding the whole square.

    **The cheap path's arithmetic.** The answer is the same as reading the curve off
    the square — the two agree to twelve decimal places, and a test says so — but no
    square of *still holding* chances is ever built, which is what a state nobody
    reads the stretch of is spared. The split is done once, outside the loop, so
    nothing here works out an exponential at all.

    Args:
        came_on: `(versions, slices + 1)` the slice the state came on in.
        pushes: What `_ending_pushes` worked out, one entry per ending arrow.
        arrivals: How likely each reading of each of those arrows' causes was, in the
            same order.
        versions: How many versions were drawn.
        slices: How many slices the window is cut into.

    Returns:
        `(versions, slices)` the chance it is holding at the end of each slice.
    """
    split = []
    for push, arrival in zip(pushes, arrivals, strict=True):
        on_slice, to_the_end = _split_the_stretch(push)
        split.append((arrival[:, :, None] * on_slice, to_the_end))

    holding = numpy.empty((versions, slices), dtype=numpy.float64)
    for end_of in range(slices):
        reached = end_of + 1
        still_on = numpy.ones((versions, reached), dtype=numpy.float64)
        for weighed, to_the_end in split:
            still_on = still_on * numpy.einsum(
                "vda,vd->va", weighed[:, :, :reached], to_the_end[:, :, end_of], optimize=True
            )
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
        cause_times: The times of each cause, in the arrow order of `shapes`. A
            claim is cut into slices over its **own** window, so a cause's slices are
            not this claim's; `ClaimShapes.carried` has already carried each cause's
            push onto this claim's own reading days.
        persistence: Which kind of truth this claim is. Passed in rather than read
            off the claim, because the field that carries it arrives with the flip.
        joint: True to build the whole pair of times, false to build only enough for
            the holding curve. `needs_the_joint` is what decides this, and building
            the pair when nothing reads it is a square of chances per version that no
            reader wants.

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

    pushes = _ending_pushes(shapes, rates)
    arrivals = _ending_arrivals(shapes, cause_times)
    still_on = _still_on_at_each_slice(pushes, arrivals, versions, slices) if joint else None

    if not shapes.ends:
        holding = numpy.cumsum(came_on[:, :slices], axis=1)
    elif still_on is not None:
        holding = _holding_from_the_square(came_on, still_on, slices)
    else:
        holding = _holding_without_the_square(came_on, pushes, arrivals, versions, slices)

    return Times(
        claim=shapes.claim,
        persistence=persistence,
        spread=came_on,
        holding=holding,
        pairs=None if still_on is None else _pairs_of_times(came_on, still_on, slices),
    )


def holding_under_each_truth(
    shapes: ClaimShapes,
    rates: Rates,
    added: AddedUp,
    under_each_truth: Sequence[tuple[Times, Times]],
) -> NDArray[numpy.float64]:
    """The chance a state is holding on its deadline, for every combination of its causes' truths.

    A claim's yes/no table says what its chance is with each of its causes false and
    then true, and a state's truth is *it is holding on its deadline*. That is a fact
    about its whole stretch, so it cannot be read off the on-process alone: which
    causes are held true changes both when the state came on and how fast it is being
    ended.

    **What the combinations change, and what they do not.** They change only two
    things: how likely each reading of each cause was, and — through that — the slice
    the state came on in. They change nothing about the arrows themselves. So every
    exponential is worked out **once for the claim**, and each arrow's contribution is
    worked out **twice** — once with its cause false and once with it true — and then
    read under every combination. Redoing the whole pass once per combination instead
    is what made a twenty-claim map with five states take a minute rather than a
    second; a combination costs a handful of small products here.

    Args:
        shapes: The claim's shapes, for its arrow order and what each arrow does.
        rates: The claim's rates, one column per version.
        added: Those rates already added up across the window.
        under_each_truth: For each arrow, its cause's times given the cause is false
            and given the cause is true, in the arrow order of `shapes`.

    Returns:
        `(versions,) + (2,) * how many arrows` the chance the state is holding on its
        deadline under each combination of its causes' truths.
    """
    versions, _, slices = added.leak.shape
    how_many = len(shapes.arrows)

    survived_leak = numpy.exp(-added.leak)
    helping = {
        index: _a_helping_arrows_factors(
            added.helps[index],
            [
                chance_of_each_reading(shapes.carried[index], when)
                for when in under_each_truth[index]
            ],
        )
        for index in shapes.helps
    }
    ending = {}
    for index, push in zip(shapes.ends, _ending_pushes(shapes, rates), strict=True):
        left = _survival_on_the_deadline(push)
        ending[index] = tuple(
            numpy.einsum(
                "vd,vda->va",
                chance_of_each_reading(shapes.carried[index], when),
                left,
                optimize=True,
            )
            for when in under_each_truth[index]
        )

    table = numpy.zeros((versions,) + (2,) * how_many)
    for truths in itertools.product((0, 1), repeat=how_many):
        held = [under_each_truth[index][truths[index]] for index in range(how_many)]
        came_on = _spread_of_arrivals(
            _not_yet_on(survived_leak, [helping[index][truths[index]] for index in shapes.helps]),
            _chance_of_each_combination(shapes, held, versions),
        )
        still_on = numpy.ones((versions, slices), dtype=numpy.float64)
        for index in shapes.ends:
            still_on = still_on * ending[index][truths[index]]
        where: tuple[slice | int, ...] = (slice(None), *truths)
        table[where] = (came_on[:, :slices] * still_on).sum(axis=1)
    return table


def needs_the_joint(graph: Graph, claim: Proposition, persistence: Persistence) -> bool:
    """Say whether anything on this map reads a state's whole stretch rather than one moment of it.

    **The cheap path.** Only a `sustain` child reads a state's whole stretch, and it
    is read as a pair of times — a square of chances per version, where the holding
    curve is a row of them. Every arrow out of such a state is then indexed by that
    square rather than by a single slice, which is twenty-five times as many readings
    at twenty-four slices, and every piece of arithmetic that touches the arrow grows
    with it.

    **No measured saving is claimed for this.** The forward-pass timing decision
    record 0017 quotes already skipped the pair of times for the states no `sustain`
    arrow left. This exists so that a map full of states nobody reads the stretch of
    does not pay for work no reader wants — not as an improvement on a number already
    measured.

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
