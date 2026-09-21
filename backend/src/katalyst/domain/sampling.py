"""Worlds drawn forward with weights: what *This happened* needs, and the days stack 06 reads.

Decision record 0016 is what this file implements.

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
standard name is a *control variate*. Where the two models cannot disagree about a
claim — a claim with no causes, or one every cause of which an edit has pinned —
the same random number settles both draws the same way and the difference is
exactly nought, so the exact answer comes back untouched.

**One draw serves every version.** The draw is made at **version 0** — the first
row of the evenly spread draw — and the correction it produces is one number per
claim, added to every version's exact answer. Which version to draw at is a choice
nothing measured, so it is named rather than assumed. What bounds the error of
sharing it is measured, and lives in the stack's own notes.

**Every claim draws from its own stream of random numbers**, taken from the one
seed and the claim's own name. Two consequences, both wanted: how many worlds are
held in memory at once changes nothing about the answer, and a claim an edit
cannot reach is **drawn the very same worlds** whatever else happens on the map,
because nothing else touches its stream. Its weights are still the whole map's,
so its correction is not yet bit for bit across an edit; what would make it so is
dropping the weights for a claim the evidence cannot reach, and the rule for which
claims those are belongs to the solve.

What this module must never do
------------------------------
- Never read a clock, reach the network, or touch a global source of random
  numbers. The one seed handed in is where every draw comes from.
- Never return a correction that would take a version's number outside nought
  and one. One scalar serves every version, so it is held to what every one of
  them can take.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

import numpy
from numpy.typing import NDArray

from katalyst.domain.forward import Forward
from katalyst.domain.ids import PropositionId
from katalyst.domain.rates import AddedUp, ClaimShapes, Pin, Rates, Window
from katalyst.domain.solving import ImpossibleObservation
from katalyst.domain.states import NEVER, STILL_HOLDING

_NOT_ZERO: Final = 1e-300
"""A floor under a total of chances that can honestly come out at nought.

A world in which a claim was certain not to happen has no spread over *when it
happened*. Rather than divide by nothing, such a world is given the last reading,
which the line that reads it then throws away.
"""


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

    `combos` counts the combinations of the **different** pushes the arrows that hold
    the claim back carry — the one place the work still multiplies out. Arrival slices
    whose push is the same array of numbers count once between them.
    """

    helps: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(combos, different pushes, slices)` surviving that helping cause.

    The middle axis is the row of the arrow's push a world takes: its cause's arrival
    slice for an arrow that reads only the moment its cause came on, and the pair
    *(on-slice, off-slice)* for one that reads its cause's whole stretch, each turned
    into a row by `Carried.of_each_reading`. The row a cause that never came takes
    holds nothing, so such a cause pushes nothing.
    """

    stops: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(different pushes, on-slice, slices)` surviving that ending cause.

    Only a **state** has these, one per arrow that can end it. The entry says the
    chance the state has not stopped by the end of a slice, given it came on in a
    slice and given what its ending cause did. One wherever the slice ends before
    the state came on, because a state cannot stop before it starts.

    A state's stopping rate accrues from the moment it came on — the middle of its
    own slice, never the start of it — which is why the on-slice is an axis here
    rather than something the reader adds afterwards.
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


@dataclass(frozen=True)
class _Chunk:
    """One block of drawn worlds, while their times are still slices rather than days.

    Held for exactly as long as it takes to add its weighted counts up and turn its
    slices into days. Nothing outside this file ever sees one.
    """

    on_slice: Mapping[PropositionId, NDArray[numpy.int64]]
    """Claim -> `(worlds in this block,)` the slice it came on in; `slices` means never."""

    off_slice: Mapping[PropositionId, NDArray[numpy.int64]]
    """Claim -> `(worlds in this block,)` the slice it went off in; `slices` means still holding."""

    happened: Mapping[PropositionId, NDArray[numpy.bool_]]
    """Claim -> whether it is true in each world under the **full time model**."""

    agreed: Mapping[PropositionId, NDArray[numpy.bool_]]
    """Claim -> whether it is true in each world under the **plain yes/no model**."""

    weight: NDArray[numpy.float64]
    """`(worlds in this block,)` how much each world counts under the full time model."""

    yes_no_weight: NDArray[numpy.float64]
    """`(worlds in this block,)` how much each world counts under the plain yes/no model."""


def ready_to_sample(shapes: ClaimShapes, rates: Rates, added: AddedUp, *, version: int) -> Ready:
    """Take the exponential of one claim's added-up rates, once, at one version.

    Every entry of `AddedUp` is a running total of a rate already multiplied
    through, so the chance a claim has not come on by the end of a slice is the
    exponential of minus those entries added together. Doing the exponential here,
    once per claim, is what turns drawing a world into gathers and multiplications.

    A **state** also needs the rate it stops at, which `AddedUp` does not carry
    because nothing else needs it added up: it is built here from the claim's own
    shapes and rates, by the same arithmetic `states.py` uses for the whole map at
    once, and a test pins the two together.

    Args:
        shapes: The claim's shapes, for its arrow order, the days of its window in
            each slice, and each ending arrow's push.
        rates: The claim's rates, of which one column is used.
        added: Those rates added up across the window.
        version: Which column of the rates to draw at.

    Returns:
        The claim's survival factors, with no version axis left.
    """
    slices = int(shapes.width.shape[0])
    at_or_after_the_middle = shapes.middle_day[:slices, None] <= shapes.points
    ends_of = numpy.arange(slices)
    at_or_after = ends_of[None, :] >= ends_of[:, None]

    stops: dict[int, NDArray[numpy.float64]] = {}
    for position in shapes.ends:
        by_reading = shapes.carried[position].push
        whole = shapes.width * by_reading.mean(axis=2)
        from_the_middle = shapes.width * numpy.where(at_or_after_the_middle, by_reading, 0.0).mean(
            axis=2
        )
        running = numpy.cumsum(whole, axis=1)
        stretch = from_the_middle[:, :, None] + (running[:, None, :] - running[:, :, None])
        stops[position] = numpy.exp(
            -float(rates.ends[position][version]) * numpy.where(at_or_after[None], stretch, 0.0)
        )

    return Ready(
        leak=numpy.exp(-added.leak[version]),
        helps={position: numpy.exp(-total[version]) for position, total in added.helps.items()},
        stops=stops,
    )


def sample_forward(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    *,
    window: Window,
    version: int,
    seed: int,
    worlds: int = 50_000,
    chunk: int = 50_000,
    exact: Mapping[PropositionId, NDArray[numpy.float64]],
) -> Sample:
    """Draw worlds forward, weight them by the evidence, and correct the exact answer.

    Every world is drawn twice from one stream of random numbers per claim: once
    under the full time model, where a claim's chance depends on the **days** its
    causes arrived, and once under the plain yes/no model, where it depends only on
    whether they did. The solve knows the second model's answer exactly, so only the
    difference between the two is sampled, and that difference is this function's
    whole output beyond the days.

    Args:
        forward: The finished forward pass, whose rates and tables the worlds are
            drawn from.
        pinned: The claims an edit fixed a value on. A *Suppose this is true* entry
            holds its claim on from its day; a *This happened* entry is what the
            weights are worked out against.
        window: The map's window, read for the day it starts on, how many days it
            runs and how many slices it is cut into.
        version: Which version to draw at. Version 0 unless a test says otherwise.
        seed: The one number every draw comes from.
        worlds: How many worlds to draw.
        chunk: How many worlds to hold in memory at once. Purely about memory: the
            days and weights do not depend on it.
        exact: Claim -> `(versions,)` the exact answer the solve gave. It is what
            holds the correction to a step every version can take without its
            number leaving nought and one.

    Returns:
        The drawn worlds, their weights, the days, and one correction per claim.

    Raises:
        ValueError: If fewer than one world, or fewer than one world at a time, was
            asked for.
        ImpossibleObservation: If no drawn world agrees with what was reported, so
            there is no weighted answer to read. The solve refuses the same map for
            the same reason and by the same name.
    """
    if worlds < 1 or chunk < 1:
        raise ValueError(
            f"a sample is at least one world drawn at least one at a time; got {worlds} "
            f"worlds in blocks of {chunk}"
        )

    order = forward.order
    slices = int(window.slices)
    ready = {
        name: ready_to_sample(
            forward.shapes[name], forward.rates[name], forward.added[name], version=version
        )
        for name in order
    }
    streams = [_stream_for(seed, name) for name in order]

    counted = 0.0
    yes_no_counted = 0.0
    true_here = {name: 0.0 for name in order}
    true_under_yes_no = {name: 0.0 for name in order}
    on_days: list[NDArray[numpy.int32]] = []
    off_days: list[NDArray[numpy.int32]] = []
    weights: list[NDArray[numpy.float64]] = []

    drawn_so_far = 0
    while drawn_so_far < worlds:
        size = min(chunk, worlds - drawn_so_far)
        drawn_so_far += size
        block = _draw_one_chunk(
            forward, pinned, ready, streams, version=version, slices=slices, size=size
        )
        counted += float(block.weight.sum())
        yes_no_counted += float(block.yes_no_weight.sum())
        for name in order:
            true_here[name] += float((block.weight * block.happened[name]).sum())
            true_under_yes_no[name] += float((block.yes_no_weight * block.agreed[name]).sum())
        came, went = _days_of(forward, block, slices)
        on_days.append(came)
        off_days.append(went)
        weights.append(block.weight)

    if counted <= 0.0 or yes_no_counted <= 0.0:
        raise ImpossibleObservation(tuple(name for name in order if _is_news(pinned.get(name))))

    # Read off the finished weights rather than off the block-by-block running
    # totals, so that a reader who recomputes it from `weight` gets the very same
    # number rather than one a few bits away.
    every_weight = numpy.concatenate(weights)
    total = float(every_weight.sum())

    return Sample(
        seed=seed,
        worlds=worlds,
        version=version,
        day_zero=window.day_zero,
        days=window.days,
        claims=order,
        on_day=numpy.concatenate(on_days),
        off_day=numpy.concatenate(off_days),
        weight=every_weight,
        effective=total * total / float((every_weight * every_weight).sum()),
        correction={
            name: _a_step_every_version_can_take(
                true_here[name] / counted - true_under_yes_no[name] / yes_no_counted,
                exact[name],
            )
            for name in order
        },
    )


def _stream_for(seed: int, claim: PropositionId) -> numpy.random.Generator:
    """One claim's own stream of random numbers, taken from the seed and the claim's name.

    A stream per claim rather than one for the whole map, for two reasons. How many
    worlds are held in memory at once then changes nothing about the answer, because
    each claim's numbers come off its own stream in world order however the blocks
    are cut. And a claim an edit cannot reach draws the very same worlds whatever
    else happens elsewhere on the map, because nothing else touches its stream.

    Args:
        seed: The one number the whole sample comes from.
        claim: The claim whose stream this is.

    Returns:
        A generator of random numbers, owing nothing to any global state.
    """
    return numpy.random.default_rng(
        numpy.random.SeedSequence(entropy=seed, spawn_key=tuple(claim.encode()))
    )


def _is_news(fixed: Pin | None) -> bool:
    """Whether an edit reported this claim happened, as opposed to supposing it or nothing."""
    return fixed is not None and fixed.kind == "observe"


def _a_step_every_version_can_take(moved: float, answers: NDArray[numpy.float64]) -> float:
    """Hold one claim's correction to a step that leaves every version's number a chance.

    The correction is one number added to two thousand exact answers, so a step big
    enough for the middle of the range can still push the top of it above one. The
    step is cut back to what the whole range can take, and never past nought, so a
    claim the map already calls certain is never moved.

    **The whole range moves together, and keeps its width.** Cutting each version's
    answer back to nought or one *after* the step had been added would flatten the
    top of a range onto one and report a narrower range than the numbers deserve —
    a width that moved because of the sample is exactly the noise this engine was
    rebuilt to remove.

    Args:
        moved: How far the sample says the claim moved.
        answers: `(versions,)` the exact answer the step will be added to.

    Returns:
        The step to add to every version.
    """
    lowest = min(-float(answers.min()), 0.0)
    highest = max(1.0 - float(answers.max()), 0.0)
    return float(numpy.clip(moved, lowest, highest))


def _draw_one_chunk(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    ready: Mapping[PropositionId, Ready],
    streams: Sequence[numpy.random.Generator],
    *,
    version: int,
    slices: int,
    size: int,
) -> _Chunk:
    """Draw one block of worlds forward, causes before effects.

    Three random numbers are taken per claim per world, from that claim's own
    stream: one settles whether the claim is true, one which slice it came on in,
    and one which slice it went off in. The first is used **twice** — once against
    the chance the full time model gives and once against the chance the plain
    yes/no table gives — and that shared number is the whole of the control
    variate.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.
        ready: Each claim's survival factors at the drawn version.
        streams: One stream of random numbers per claim, in the pass's own order.
        version: Which version is being drawn at.
        slices: How many slices a window is cut into.
        size: How many worlds are in this block.

    Returns:
        The block: every claim's times and truth under both models, and the two
        sets of weights.
    """
    on_slice: dict[PropositionId, NDArray[numpy.int64]] = {}
    off_slice: dict[PropositionId, NDArray[numpy.int64]] = {}
    happened: dict[PropositionId, NDArray[numpy.bool_]] = {}
    agreed: dict[PropositionId, NDArray[numpy.bool_]] = {}
    weight = numpy.ones(size, dtype=numpy.float64)
    yes_no_weight = numpy.ones(size, dtype=numpy.float64)

    for position, name in enumerate(forward.order):
        dice = streams[position].random((size, 3))
        fixed = pinned.get(name)
        if fixed is not None and fixed.kind == "do":
            # A supposed claim came on at the very start of the window, or never,
            # and never goes off — which is what the forward pass pinned it to.
            on_slice[name] = numpy.full(size, 0 if fixed.value else slices, dtype=numpy.int64)
            off_slice[name] = numpy.full(size, slices, dtype=numpy.int64)
            happened[name] = numpy.full(size, fixed.value, dtype=numpy.bool_)
            agreed[name] = happened[name]
            continue

        shapes = forward.shapes[name]
        a_state = forward.times[name].persistence == "state"
        readings = _readings(shapes, forward.causes[name], on_slice, off_slice, slices)
        not_yet = _not_yet(ready[name], shapes, readings, size)
        came_on = _came_on(not_yet)
        still_on = (
            _still_on_at_the_end(ready[name], shapes, readings, size, slices) if a_state else None
        )
        chance = (
            1.0 - not_yet[:, -1]
            if still_on is None
            else (came_on[:, :slices] * still_on).sum(axis=1)
        )
        from_the_table = _from_the_table(forward, name, agreed, version, size)

        if fixed is None:
            true_in_this_world = dice[:, 0] < chance
            agreed[name] = dice[:, 0] < from_the_table
        else:
            true_in_this_world = numpy.full(size, fixed.value, dtype=numpy.bool_)
            agreed[name] = true_in_this_world
            weight = weight * (chance if fixed.value else 1.0 - chance)
            yes_no_weight = yes_no_weight * (
                from_the_table if fixed.value else 1.0 - from_the_table
            )

        happened[name] = true_in_this_world
        came = _when_it_came_on(came_on, still_on, true_in_this_world, dice[:, 1], slices)
        on_slice[name] = came
        off_slice[name] = (
            _when_it_stopped(
                ready[name], shapes, readings, came, true_in_this_world, dice[:, 2], slices
            )
            if a_state
            else numpy.full(size, slices, dtype=numpy.int64)
        )

    return _Chunk(
        on_slice=on_slice,
        off_slice=off_slice,
        happened=happened,
        agreed=agreed,
        weight=weight,
        yes_no_weight=yes_no_weight,
    )


def _readings(
    shapes: ClaimShapes,
    causes: tuple[PropositionId, ...],
    on_slice: Mapping[PropositionId, NDArray[numpy.int64]],
    off_slice: Mapping[PropositionId, NDArray[numpy.int64]],
    slices: int,
) -> dict[int, NDArray[numpy.int64]]:
    """Which of the different pushes each arrow carries this world calls for.

    An arrow that reads only the moment its cause came on is read by the slice that
    happened in. An arrow that reads its cause's whole stretch is read by the pair
    *(on-slice, off-slice)*, flattened with the on-slice changing slowest — the same
    layout the forward pass lays a cause's times out in.

    That reading is then turned into the row of the arrow's push it takes. Readings
    whose push is the same array of numbers share one row, which is what the whole
    pass is built at, so this is where a world stops counting readings and starts
    counting pushes.

    Args:
        shapes: The claim's shapes, whose carried push says which of the two it is
            and which readings carry the same numbers.
        causes: The claims each arrow comes from, in the claim's arrow order.
        on_slice: Every claim already drawn -> the slice it came on in.
        off_slice: Every claim already drawn -> the slice it went off in.
        slices: How many slices a window is cut into.

    Returns:
        Arrow position -> one row of that arrow's push per world.
    """
    out: dict[int, NDArray[numpy.int64]] = {}
    for position, source in enumerate(causes):
        carried = shapes.carried[position]
        if carried.whole_stretch:
            reading = on_slice[source] * (slices + 1) + off_slice[source]
        else:
            reading = on_slice[source]
        out[position] = carried.of_each_reading[reading]
    return out


def _not_yet(
    ready: Ready,
    shapes: ClaimShapes,
    readings: Mapping[int, NDArray[numpy.int64]],
    size: int,
) -> NDArray[numpy.float64]:
    """The chance a claim has not come on by the end of each slice, world by world.

    Because the rates add, the chance is a product of one factor per cause, and each
    factor is a gather out of an array that was exponentiated once. No table over
    combinations of causes is ever built — except for the arrows that **hold the
    claim back**, which `AddedUp` has already multiplied out along its `combos`
    axis, and which this picks a row out of.

    Args:
        ready: The claim's survival factors at the drawn version.
        shapes: The claim's shapes, for which arrows hold it back.
        readings: Arrow position -> one reading per world.
        size: How many worlds are in this block.

    Returns:
        `(worlds in this block, slices)`.
    """
    if shapes.holds_back:
        each = tuple(shapes.carried[position].different for position in shapes.holds_back)
        combination = numpy.ravel_multi_index(
            tuple(readings[position] for position in shapes.holds_back), each
        ).astype(numpy.int64)
    else:
        combination = numpy.zeros(size, dtype=numpy.int64)

    not_yet: NDArray[numpy.float64] = ready.leak[combination]
    for position, block in ready.helps.items():
        not_yet = not_yet * block[combination, readings[position]]
    return not_yet


def _came_on(not_yet: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """Turn *not on yet by the end of each slice* into *came on in this slice*.

    Args:
        not_yet: `(worlds, slices)` the chance it has not come on by each slice end.

    Returns:
        `(worlds, slices + 1)` the slice it came on in, the last entry meaning it
        never came on at all.
    """
    size, slices = not_yet.shape
    step = numpy.concatenate([numpy.ones((size, 1)), not_yet], axis=1)
    came_on = numpy.empty((size, slices + 1), dtype=numpy.float64)
    came_on[:, :slices] = step[:, :-1] - step[:, 1:]
    came_on[:, slices] = not_yet[:, -1]
    return came_on


def _still_on_at_the_end(
    ready: Ready,
    shapes: ClaimShapes,
    readings: Mapping[int, NDArray[numpy.int64]],
    size: int,
    slices: int,
) -> NDArray[numpy.float64]:
    """The chance a state is still holding on its deadline, given the slice it came on in.

    Args:
        ready: The claim's survival factors at the drawn version.
        shapes: The claim's shapes, for which arrows can end it.
        readings: Arrow position -> one reading per world.
        size: How many worlds are in this block.
        slices: How many slices a window is cut into.

    Returns:
        `(worlds in this block, slices)` — one column per slice the state might have
        come on in. All ones for a state nothing on the map can end, which is what
        makes such a state identical to the same claim written as an event.
    """
    still_on = numpy.ones((size, slices), dtype=numpy.float64)
    for position in shapes.ends:
        still_on = still_on * ready.stops[position][readings[position], :, slices - 1]
    return still_on


def _from_the_table(
    forward: Forward,
    claim: PropositionId,
    agreed: Mapping[PropositionId, NDArray[numpy.bool_]],
    version: int,
    size: int,
) -> NDArray[numpy.float64]:
    """The plain yes/no model's chance for one claim, read off its own small table.

    This is the other half of the control variate: the same claim's chance worked
    out from **whether** its causes are true and from nothing about when they
    happened. The solve knows what this model answers exactly, which is why sampling
    it as well costs nothing and cancels most of the noise.

    Args:
        forward: The finished forward pass, for the claim's table and cause order.
        claim: The claim being drawn.
        agreed: Every claim already drawn -> whether it is true under this model.
        version: Which version is being drawn at.
        size: How many worlds are in this block.

    Returns:
        `(worlds in this block,)` the chance the claim is true in each world.
    """
    causes = forward.causes[claim]
    row = forward.table[claim][version].reshape(-1, 2)
    if not causes:
        return numpy.full(size, float(row[0, 1]), dtype=numpy.float64)
    flat = numpy.ravel_multi_index(
        tuple(agreed[cause].astype(numpy.int64) for cause in causes), (2,) * len(causes)
    )
    chance: NDArray[numpy.float64] = row[flat, 1]
    return chance


def _when_it_came_on(
    came_on: NDArray[numpy.float64],
    still_on: NDArray[numpy.float64] | None,
    true_in_this_world: NDArray[numpy.bool_],
    dice: NDArray[numpy.float64],
    slices: int,
) -> NDArray[numpy.int64]:
    """Draw which slice a claim came on in, given whether it came out true.

    Drawing the truth first and the day second is what keeps the two models in
    step: both read the same random number for the truth, so they part company only
    where they disagree about the chance itself.

    For an **event**, true means it happened, so the slice is drawn from the slices
    it could have happened in, and false means it never came on. For a **state**,
    true means it is holding on its deadline, so the slice is drawn from the slices
    it could have come on in **and still be holding**; false covers both *it never
    came on* and *it came on and stopped*.

    Args:
        came_on: `(worlds, slices + 1)` the slice it came on in, before any truth is
            known.
        still_on: `(worlds, slices)` for a state, the chance it is still holding on
            its deadline given each on-slice; nothing at all for an event.
        true_in_this_world: Whether the claim came out true in each world.
        dice: One random number per world.
        slices: How many slices a window is cut into.

    Returns:
        `(worlds,)` the slice it came on in; `slices` means it never came on.
    """
    if still_on is None:
        untrue = numpy.full(came_on.shape[0], slices, dtype=numpy.int64)
        holding = came_on[:, :slices]
    else:
        holding = came_on[:, :slices] * still_on
        untrue = _drawn_from(
            numpy.concatenate(
                [came_on[:, :slices] * (1.0 - still_on), came_on[:, slices:]], axis=1
            ),
            dice,
        )
    return numpy.where(true_in_this_world, _drawn_from(holding, dice), untrue)


def _when_it_stopped(
    ready: Ready,
    shapes: ClaimShapes,
    readings: Mapping[int, NDArray[numpy.int64]],
    came: NDArray[numpy.int64],
    true_in_this_world: NDArray[numpy.bool_],
    dice: NDArray[numpy.float64],
    slices: int,
) -> NDArray[numpy.int64]:
    """Draw which slice a state went off in, given the slice it came on in.

    A state that is holding on its deadline has not gone off, and a state that never
    came on has nothing to stop. Every other world draws an off-slice from the
    chance it stopped in each slice, which is nought before the slice it came on in
    — so a state's off day is never before its on day, by construction rather than
    by a check afterwards.

    Args:
        ready: The claim's survival factors at the drawn version.
        shapes: The claim's shapes, for which arrows can end it.
        readings: Arrow position -> one reading per world.
        came: `(worlds,)` the slice it came on in.
        true_in_this_world: Whether it is holding on its deadline in each world.
        dice: One random number per world.
        slices: How many slices a window is cut into.

    Returns:
        `(worlds,)` the slice it went off in; `slices` means it is still holding.
    """
    still_holding = numpy.full(came.shape[0], slices, dtype=numpy.int64)
    if not shapes.ends:
        return still_holding

    on_at = numpy.minimum(came, slices - 1)
    surviving = numpy.ones((came.shape[0], slices), dtype=numpy.float64)
    for position in shapes.ends:
        surviving = surviving * ready.stops[position][readings[position], on_at]
    step = numpy.concatenate([numpy.ones((came.shape[0], 1)), surviving], axis=1)
    stopped = _drawn_from(step[:, :-1] - step[:, 1:], dice)
    return numpy.where(true_in_this_world | (came >= slices), still_holding, stopped)


def _drawn_from(mass: NDArray[numpy.float64], dice: NDArray[numpy.float64]) -> NDArray[numpy.int64]:
    """Pick one reading per world, with each reading's chance in proportion to its mass.

    The masses need not add to one: each world's row is scaled by its own total,
    which is how a conditional draw — *given the claim came out true* — is taken
    from the same array as an unconditional one. A world whose row is all nought
    gets the last reading, and every caller throws that world's answer away.

    Args:
        mass: `(worlds, readings)` how much chance sits on each reading.
        dice: One random number per world.

    Returns:
        `(worlds,)` which reading was drawn.
    """
    total = mass.sum(axis=1, keepdims=True)
    reached = numpy.cumsum(mass / numpy.maximum(total, _NOT_ZERO), axis=1)
    drawn: NDArray[numpy.int64] = (dice[:, None] >= reached).sum(axis=1).astype(numpy.int64)
    return numpy.clip(drawn, 0, mass.shape[1] - 1)


def _days_of(
    forward: Forward, block: _Chunk, slices: int
) -> tuple[NDArray[numpy.int32], NDArray[numpy.int32]]:
    """Turn one block's slices into the two day tables stack 06 reads.

    A day is the **middle of the slice, rounded to a whole day**, read off the
    claim's **own** grid — a claim judged in a fortnight and one judged in a year do
    not share slice boundaries. A claim that never came on carries the never marker
    in both tables; one that has not gone off carries the still-holding marker,
    which is every event and a state whose stretch outlasted the window.

    Args:
        forward: The finished forward pass, for each claim's own grid.
        block: One block of drawn worlds.
        slices: How many slices a window is cut into.

    Returns:
        `(worlds in this block, claims)` twice: the day each claim came on and the
        day it went off.
    """
    came: list[NDArray[numpy.int32]] = []
    went: list[NDArray[numpy.int32]] = []
    for name in forward.order:
        middles = forward.shapes[name].middle_day
        on_slice = block.on_slice[name]
        off_slice = block.off_slice[name]
        never = on_slice >= slices
        came.append(
            numpy.where(never, NEVER, _rounded(middles, on_slice, slices)).astype(numpy.int32)
        )
        went.append(
            numpy.where(
                never,
                NEVER,
                numpy.where(
                    off_slice >= slices, STILL_HOLDING, _rounded(middles, off_slice, slices)
                ),
            ).astype(numpy.int32)
        )
    return numpy.stack(came, axis=1), numpy.stack(went, axis=1)


def _rounded(
    middles: NDArray[numpy.float64], which: NDArray[numpy.int64], slices: int
) -> NDArray[numpy.int64]:
    """The whole day a slice's middle falls on, for each world.

    Args:
        middles: `(slices + 1,)` the day that stands for an arrival in each slice.
            Its last entry is positive infinity and means *never*, so it is never
            read here.
        which: `(worlds,)` which slice each world is asking about.
        slices: How many slices a window is cut into.

    Returns:
        `(worlds,)` the whole day.
    """
    day: NDArray[numpy.int64] = numpy.rint(middles[numpy.minimum(which, slices - 1)]).astype(
        numpy.int64
    )
    return day
