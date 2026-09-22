"""One pass over the map, causes before effects, that works out when every claim happens.

Decision record 0016 is what this file implements.

What this module is for
-----------------------
Working the map through has two halves. This is the first: **when**. One pass, in
an order that puts every cause before the effects it feeds, turns the stated
chances into rates, adds each cause's push into its target's rate, and comes out
with, for every claim, how much of the chance falls in each slice of the window.

The second half is **whether**, and it lives in `solving.py`. It reads the small
yes/no table this pass builds for each claim and solves the map exactly.

**Because the rates add, the average is taken one cause at a time** rather than
over every combination of arrival days. That is exact — not an approximation — and
it is most of why a twenty-claim map is worked out in a fraction of a second. The
one exception is the arrows that **hold a claim back**, whose arrival days really
must be multiplied out; three of those cost about twice a plain pass and ten cost
about seventy times it.

**There is no separate table object.** `Forward` is what the solve reads.

The shape conventions — the version axis first, then the cause axes in the claim's
arrow order, then the claim's own axis last — are written out once in `rates.py`.
"""

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.link import Link
from katalyst.domain.proposition import Persistence, Proposition
from katalyst.domain.rates import (
    AddedUp,
    ClaimShapes,
    Drawn,
    Pin,
    Rates,
    Window,
    added_up,
    rates_of,
    shapes_of,
)
from katalyst.domain.states import (
    Times,
    as_joint,
    chance_of_each_reading,
    holding_under_each_truth,
    is_true_on_its_deadline,
    needs_the_joint,
    on_and_off,
)

NOTHING_PINNED: Mapping[PropositionId, Pin] = MappingProxyType({})
"""No claim has a value fixed on it. The ordinary case, and the default below.

A frozen mapping rather than an empty dictionary, so that a default cannot be
written into by accident and quietly outlive the call that did it.
"""

_NOT_ZERO: Final = 1e-12
"""A floor under a divisor that can honestly come out at nought.

A cause that is certainly false in some version has no distribution over *when it
happened given it happened*. Rather than divide by nothing, such a version is given
the flat spread across the times that were open to it — which is then multiplied by
a chance of nought in the solve, so it reaches no reader.
"""


@dataclass(frozen=True)
class Forward:
    """Everything one forward pass worked out, and everything the exact solve reads.

    A version is one coherent set of the numbers a person stated, and every array
    in here has the version axis first.
    """

    order: tuple[PropositionId, ...]
    """Every claim on the map, causes before the effects they feed."""

    causes: Mapping[PropositionId, tuple[PropositionId, ...]]
    """Claim -> its causes, in the order its cause axes are laid out in.

    The same order as the claim's own `ClaimShapes.arrows`, read as the claim each
    arrow comes from. Empty for a claim *Suppose this is true* was said of, whose
    arrows are cut.
    """

    times: Mapping[PropositionId, Times]
    """Claim -> when it happened: the slice an event landed in, or a state's pair of slices."""

    table: Mapping[PropositionId, NDArray[numpy.float64]]
    """Claim -> its small yes/no table, `(versions,) + (2,) * how many causes + (2,)`.

    The claim's **own** axis is last and the table adds to one along it. Index 1 on
    that axis means *the claim happened by its deadline*, or for a state *the claim
    is holding on its deadline*. Every earlier axis is one cause being false then
    true, in the order `causes` gives.
    """

    shapes: Mapping[PropositionId, ClaimShapes]
    """Claim -> the parts of its arrows that no version changes. Kept so the assembly
    can warn about an arrow that could not hold its claim back, without redoing the pass."""

    rates: Mapping[PropositionId, Rates]
    """Claim -> its rates, one column per version."""

    added: Mapping[PropositionId, AddedUp]
    """Claim -> those rates added up across the window, which the sampler reuses."""


def _causes_before_effects(graph: Graph) -> tuple[PropositionId, ...]:
    """Put the claims in an order where nothing comes before a cause of it.

    Ties are broken by the claim's own identifier, so one map always gives one
    order and two runs of the engine can be compared.

    Args:
        graph: The map.

    Returns:
        Every claim on it, causes first.

    Raises:
        ValueError: If some claims can never be reached — a loop, or an arrow
            starting at a claim that is not on the map. Either way the map cannot be
            worked through causes first, and which claims were left is said out loud.
    """
    waiting = {
        one.id: {arrow.source for arrow in graph.links if arrow.target == one.id}
        for one in graph.propositions
    }
    settled: list[PropositionId] = []
    while waiting:
        ready = sorted(name for name, causes in waiting.items() if causes <= set(settled))
        if not ready:
            raise ValueError(
                "this map cannot be worked through causes before effects; "
                f"{sorted(waiting)} are each waiting on one another or on a claim that is "
                "not on the map"
            )
        for name in ready:
            settled.append(name)
            del waiting[name]
    return tuple(settled)


def _shared_out(
    mass: NDArray[numpy.float64], open_to_it: NDArray[numpy.float64]
) -> NDArray[numpy.float64]:
    """Turn unshared chance into a spread that adds to one, with a flat fallback.

    Args:
        mass: `(versions, readings)` how much chance sits on each reading.
        open_to_it: `(readings,)` one where a reading was open to the claim at all,
            nought where it was not.

    Returns:
        `(versions, readings)` adding to one along the second axis. Where a version
        put no chance at all on any of these readings, the flat spread across the
        ones that were open to it, because *given something that cannot happen* has
        no answer and a made-up one must at least be even-handed.
    """
    total = mass.sum(axis=-1, keepdims=True)
    flat = open_to_it / open_to_it.sum()
    shared: NDArray[numpy.float64] = numpy.where(
        total > 0.0, mass / numpy.maximum(total, _NOT_ZERO), flat[None, :]
    )
    return shared


def _holding_from_the_pairs(square: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """The chance a state is holding at the end of each slice, read off its pair of times.

    Args:
        square: `(versions, slices + 1, slices + 1)` the chance of each pair *(the
            slice it came on in, the slice it went off in)*.

    Returns:
        `(versions, slices)` the chance it was on by the end of each slice and had
        not gone off by then.
    """
    slices = square.shape[1] - 1
    ends = numpy.arange(slices)
    already_on = numpy.arange(slices + 1)[None, :] <= ends[:, None]
    not_yet_off = numpy.arange(slices + 1)[None, :] > ends[:, None]
    holding: NDArray[numpy.float64] = numpy.einsum(
        "vab,ka,kb->vk", square, already_on.astype(float), not_yet_off.astype(float)
    )
    return holding


def _told_twice(times: Times) -> tuple[Times, Times]:
    """One cause's times, told twice: once given it is false, once given it is true.

    A claim's yes/no table says what the claim's chance is with each of its causes
    false and true, so each cause's timing has to be re-read under both. For an
    **event**, true means it happened at some point in the window and false means it
    never did. For a **state**, true means it is holding on its deadline — on by
    then, and not yet off — because that is what a state's tile says, and false is
    everything else, including *came on and then stopped*.

    Args:
        times: The cause's times as the pass worked them out.

    Returns:
        The same times twice over: given the cause is false, then given it is true.
    """
    slices = times.spread.shape[1] - 1
    if times.persistence == "event":
        happened = numpy.concatenate([numpy.ones(slices), numpy.zeros(1)])
        never = 1.0 - happened
        return (
            _an_events_times(times.claim, _shared_out(times.spread * never, never), slices),
            _an_events_times(times.claim, _shared_out(times.spread * happened, happened), slices),
        )

    square = as_joint(times)
    came_on = numpy.arange(slices + 1)[:, None] < slices
    still_holding = numpy.arange(slices + 1)[None, :] == slices
    holds = (came_on & still_holding).astype(float).reshape(-1)
    stopped_or_never = 1.0 - holds
    flat = square.reshape(square.shape[0], -1)
    return (
        _a_states_times(times.claim, _shared_out(flat * stopped_or_never, stopped_or_never)),
        _a_states_times(times.claim, _shared_out(flat * holds, holds)),
    )


def _an_events_times(claim: PropositionId, spread: NDArray[numpy.float64], slices: int) -> Times:
    """Wrap one event's slice-by-slice chance of happening as a whole set of times."""
    return Times(
        claim=claim,
        persistence="event",
        spread=spread,
        holding=numpy.cumsum(spread[:, :slices], axis=1),
        pairs=None,
    )


def _a_states_times(claim: PropositionId, flat: NDArray[numpy.float64]) -> Times:
    """Wrap one state's flattened pair of times as a whole set of times."""
    side = round(flat.shape[1] ** 0.5)
    square = flat.reshape(flat.shape[0], side, side)
    return Times(
        claim=claim,
        persistence="state",
        spread=square.sum(axis=2),
        holding=_holding_from_the_pairs(square),
        pairs=flat,
    )


def _pinned_times(
    claim: PropositionId, pin: Pin, kind: Persistence, slices: int, versions: int
) -> Times:
    """The times of a claim *Suppose this is true* fixed a value on.

    A claim supposed **true** came on at the very start of the window and, if it is
    a state, never goes off — which is what supposing a state says: it holds from
    its date onwards. A claim supposed **false** never came on at all. Every version
    says the same thing, because a supposition is not a number anybody drew.

    Args:
        claim: The claim.
        pin: What the edit fixed and which verb fixed it.
        kind: Which kind of truth the claim is.
        slices: How many slices the window is cut into.
        versions: How many versions were drawn.

    Returns:
        Times with the whole of the chance on that one reading, in every version.
    """
    came_on = 0 if pin.value else slices
    spread = numpy.zeros((versions, slices + 1))
    spread[:, came_on] = 1.0
    if kind == "event":
        return _an_events_times(claim, spread, slices)
    square = numpy.zeros((versions, slices + 1, slices + 1))
    square[:, came_on, slices] = 1.0
    return _a_states_times(claim, square.reshape(versions, -1))


def _an_events_table(
    shapes: ClaimShapes,
    added: AddedUp,
    under_each_truth: Sequence[tuple[NDArray[numpy.float64], NDArray[numpy.float64]]],
) -> NDArray[numpy.float64]:
    """One event's chance of happening by its deadline, for every combination of its causes.

    **The expensive part is done once.** Turning the added-up rates into survival is
    one exponential over the whole of the working; what changes from one combination
    of truths to the next is only which spread each cause's timing is read with, and
    only the end of the last slice is looked at. That is why a claim with three
    causes costs one pass rather than eight.

    Args:
        shapes: The claim's shapes, for its arrow order and what each arrow does.
        added: The claim's rates already added up across the window.
        under_each_truth: For each arrow, how much chance sits on each of the
            **different** pushes it carries — given its cause is false and given it is
            true, in the arrow order of `shapes`. That is what
            `states.chance_of_each_reading` hands back.

    Returns:
        `(versions,) + (2,) * how many arrows` the chance the claim happened by its
        deadline under each combination of its causes' truths.
    """
    versions = int(added.leak.shape[0])
    how_many = len(shapes.arrows)
    survived_leak = numpy.exp(-added.leak[:, :, -1])
    survived_help = {
        position: numpy.exp(-added.helps[position].over_the_window()) for position in shapes.helps
    }

    table = numpy.zeros((versions,) + (2,) * how_many)
    for truths in itertools.product((0, 1), repeat=how_many):
        chance_of_combination = numpy.ones((versions, 1))
        for position in shapes.holds_back:
            reading = under_each_truth[position][truths[position]]
            paired = chance_of_combination[:, :, None] * reading[:, None, :]
            chance_of_combination = paired.reshape(versions, -1)
        not_yet = survived_leak * chance_of_combination
        for position in shapes.helps:
            reading = under_each_truth[position][truths[position]]
            not_yet = not_yet * numpy.einsum("vd,vcd->vc", reading, survived_help[position])
        where: tuple[slice | int, ...] = (slice(None), *truths)
        table[where] = 1.0 - not_yet.sum(axis=1)
    return table


def forward_pass(
    graph: Graph,
    window: Window,
    drawn: Drawn,
    *,
    pinned: Mapping[PropositionId, Pin] = NOTHING_PINNED,
) -> Forward:
    """Work out, in one pass over the map, when every claim happens and its small yes/no table.

    **A supposition is honoured here, not patched afterwards.** *Suppose this is
    true* pins the claim to its day, cuts the arrows into it, and the whole pass is
    redone with it pinned — never a finished table edited after the fact. *This
    happened* is not honoured here at all: it is a narrowing of the answer, and it
    belongs to the solve.

    **A state that anything on the map reads is worked out with its pair of times.**
    A claim's yes/no table says what its chance is with each cause false and true,
    and a state's truth is *it is holding on its deadline* — a fact about the whole
    stretch and not about the moment it came on. So the pair is asked for whenever a
    state has any arrow leaving it, and the cheap path is what a state nothing reads
    takes.

    Args:
        graph: The map. Must have no loops, because the claims have to be worked
            through causes before effects.
        window: The map's window, already cut into slices.
        drawn: One draw per version of every number a person stated.
        pinned: The claims an edit fixed a value on, and which verb fixed it. Only
            the *Suppose this is true* entries change this pass.

    Returns:
        The finished pass: the order, each claim's causes, its times, its yes/no
        table, and the working the solve and the sampler both read.

    Raises:
        ValueError: If the map cannot be worked through causes before effects.
    """
    claims: Mapping[PropositionId, Proposition] = {one.id: one for one in graph.propositions}
    order = _causes_before_effects(graph)
    into: Mapping[PropositionId, tuple[Link, ...]] = {
        name: tuple(sorted((a for a in graph.links if a.target == name), key=lambda a: a.id))
        for name in order
    }
    anything_leaves = {arrow.source for arrow in graph.links}

    causes: dict[PropositionId, tuple[PropositionId, ...]] = {}
    times: dict[PropositionId, Times] = {}
    tables: dict[PropositionId, NDArray[numpy.float64]] = {}
    every_shape: dict[PropositionId, ClaimShapes] = {}
    every_rate: dict[PropositionId, Rates] = {}
    every_total: dict[PropositionId, AddedUp] = {}

    day_of = {
        one.id: max(0, (one.resolution.by - window.day_zero).days) for one in graph.propositions
    }

    for name in order:
        claim = claims[name]
        fixed = pinned.get(name)
        supposed = fixed if fixed is not None and fixed.kind == "do" else None
        arrows = () if supposed is not None else into[name]
        kind = claim.persistence

        with_this_cause = {
            position: drawn.with_this_cause[arrow.id] for position, arrow in enumerate(arrows)
        }
        shapes = shapes_of(
            claim,
            arrows,
            {arrow.id: claims[arrow.source].persistence for arrow in arrows},
            {arrow.id: day_of[arrow.source] for arrow in arrows},
            window,
            persistence=kind,
        )
        rates = rates_of(shapes, drawn.own_chance[name], with_this_cause, persistence=kind)
        added = added_up(shapes, rates)

        cause_times = [times[arrow.source] for arrow in arrows]
        under_each_truth = [_told_twice(one) for one in cause_times]

        if supposed is not None:
            settled = _pinned_times(name, supposed, kind, window.slices, drawn.versions)
            times[name] = settled
            held = is_true_on_its_deadline(settled)
            tables[name] = numpy.stack([1.0 - held, held], axis=-1)
        else:
            # A state's truth is a fact about its whole stretch, so anything that reads
            # it at all needs the pair of times, not only a `sustain` child.
            wants_pairs = needs_the_joint(graph, claim, kind) or (
                kind == "state" and name in anything_leaves
            )
            times[name] = on_and_off(
                shapes,
                rates,
                added,
                cause_times,
                persistence=kind,
                joint=wants_pairs,
            )
            # A state nothing on the map can end never goes off, so *holding on its
            # deadline* and *came on by its deadline* are the same question, and it
            # takes the event's own table rather than a second arithmetic that
            # answers the same thing. That is decision record 0017's sentence — such
            # a state is identical to the same claim written as an event — made a
            # property of the code rather than of two routes happening to agree.
            if kind == "state" and shapes.ends:
                happened = holding_under_each_truth(shapes, rates, added, under_each_truth)
            else:
                happened = _an_events_table(
                    shapes,
                    added,
                    [
                        (
                            chance_of_each_reading(shapes.carried[position], pair[0]),
                            chance_of_each_reading(shapes.carried[position], pair[1]),
                        )
                        for position, pair in enumerate(under_each_truth)
                    ],
                )
            tables[name] = numpy.stack([1.0 - happened, happened], axis=-1)

        causes[name] = tuple(arrow.source for arrow in arrows)
        every_shape[name] = shapes
        every_rate[name] = rates
        every_total[name] = added

    return Forward(
        order=order,
        causes=causes,
        times=times,
        table=tables,
        shapes=every_shape,
        rates=every_rate,
        added=every_total,
    )
