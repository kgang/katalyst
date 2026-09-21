"""Whether each claim is true, solved exactly over the map's small yes/no tables.

Decision record 0016 is what this file implements.

What this module is for
-----------------------
The forward pass works out **when** each claim happens and leaves a small yes/no
table for each one. This module answers **whether**, exactly: it multiplies those
tables together and sums out one claim at a time until only the claim being asked
about is left. The standard name for that procedure is *variable elimination*, and
on the maps this product builds it is a few milliseconds of work.

Exactly means exactly. No sampling, no iteration, no tolerance. The only thing
between the answer and arithmetic truth is the tables themselves.

The two verbs
-------------
* ***Suppose this is true*** pins the claim to its day and **redoes the forward
  pass** with it pinned, then solves. A finished table is never patched afterwards.
  That is why this module takes what the fixed values were: it must know which
  claims were supposed, but it does not apply them itself. Here the supposed
  claim's own table is replaced by a certainty on the supposed value — which is
  what cuts the arrows into it, since those arrows are the axes that table is
  written over.
* ***This happened*** multiplies in a mask that keeps only what agrees with what was
  seen, then makes the result add back up to one.

**Locality is a theorem here, not a hope.** A claim joined to the evidence by no
chain of arrows and sharing no cause with it has a factor that already adds to one,
so summing it out leaves the answer untouched — **bit for bit**, not merely close.
That is the strictest promise in this stack, and it is kept by never multiplying
such a factor in at all: each claim is answered over the claims that can reach it,
and nothing else is touched. Multiplying by a number that ought to be one and
dividing it out again is not bit for bit, because neither step is exact in floating
point.

**One version or two thousand, it is one pass.** A version is one coherent draw of
every number a person stated. Every array in here carries the versions as its
first axis and every step is elementwise along it, so two thousand versions cost
one pass over slightly larger arrays rather than two thousand passes.

**There is no share-of-the-range working here.** Splitting a claim's range across
the claims that caused it would cost one more solve per claim, and the assembly
reads it off the exact per-version numbers instead.
"""

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy
from numpy.typing import NDArray

from katalyst.domain.forward import Forward
from katalyst.domain.ids import PropositionId
from katalyst.domain.rates import Pin


class ImpossibleObservation(ValueError):
    """What was reported cannot happen on this map, so there is nothing to scale back up.

    Raised rather than answered with a number, because dividing by nothing and
    calling the result a chance is exactly the untraceable state this repository
    refuses. The caller turns it into a refusal the reader can see, naming the
    claims in `claims`.
    """

    def __init__(self, claims: tuple[PropositionId, ...]) -> None:
        """Say which claims were reported, and that no world on the map agrees with them.

        Args:
            claims: The claims *This happened* was used on, in the map's own order.
        """
        self.claims = claims
        super().__init__(
            "Nothing this map can produce agrees with what was reported on "
            f"{', '.join(claims)}, so there is no world left to read a chance off."
        )


@dataclass(frozen=True)
class _Factor:
    """One array in the elimination, and which claims its axes stand for.

    A factor starts life as a claim's yes/no table and becomes, as claims are
    summed out, a table over whatever claims are left. `values` is shaped
    `(versions,) + (2,) * len(over)`: the versions first, then one two-wide axis
    per claim in `over`, in that order, running `[it did not, it did]`.
    """

    over: tuple[PropositionId, ...]
    """The claims this factor's axes stand for, after the leading version axis."""

    values: NDArray[numpy.float64]
    """`(versions,) + (2,) * len(over)` — the numbers themselves."""


def solve(
    forward: Forward, pinned: Mapping[PropositionId, Pin]
) -> Mapping[PropositionId, NDArray[numpy.float64]]:
    """Answer, for every claim, the chance it is true, given everything that was fixed.

    True means what the claim's own tile says: for an event, that it happened by its
    deadline; for a state, that it is holding on its deadline.

    An observation nothing on the map can produce — one whose mask leaves no chance
    at all — is **answered**, with a violation-shaped refusal from the caller, and
    never divided through by zero. This function raises `ImpossibleObservation`
    naming the claims, and the caller shapes the refusal the reader sees.

    Args:
        forward: The finished forward pass, whose tables this solves over. Every
            claim in its order carries a table, including one an edit fixed.
        pinned: The claims an edit fixed a value on. The *Suppose this is true*
            entries were already honoured by the pass; the *This happened* entries
            are applied here as a mask.

    Returns:
        Claim -> `(versions,)` the chance it is true.

    Raises:
        ImpossibleObservation: If nothing the map can produce agrees with what
            *This happened* reported.
    """
    order = elimination_order(forward)
    reported = tuple(claim for claim in forward.order if _verb(pinned, claim) == "observe")
    if reported:
        _refuse_if_nothing_agrees(forward, pinned, reported, order)
    return {claim: _chance_of(forward, pinned, claim, order) for claim in forward.order}


def all_marginals(
    forward: Forward, pinned: Mapping[PropositionId, Pin]
) -> Mapping[PropositionId, NDArray[numpy.float64]]:
    """Every claim's number, in the one call the whole assembly makes.

    **One elimination pass per claim in this pull request**, which is what `solve`
    already does, so today this call is exactly that call. The faster arrangement —
    one tree built once and passed over twice — is a change behind this signature
    and nothing else: the assembly asks this question and never asks how it was
    answered. It is not built here because it replaces twenty elimination passes
    rather than the pass itself, which is about a tenth of the cost of a hard map,
    and nothing now asks for twenty in one request.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.

    Returns:
        Claim -> `(versions,)` the chance it is true.

    Raises:
        ImpossibleObservation: If nothing the map can produce agrees with what
            *This happened* reported.
    """
    return solve(forward, pinned)


def elimination_order(forward: Forward) -> tuple[PropositionId, ...]:
    """Choose the order claims are summed out in, so the tables stay small.

    Two standard steps. First the map is made **moral**: every arrow loses its
    direction, and any two causes of the same claim are joined to each other,
    because summing that claim out would join them anyway. Then claims are taken in
    **minimum-fill** order: at each step, the one whose removal would add the fewest
    new joins.

    The order changes how much work the solve does and **never** changes the answer.
    It is read off the map alone: what an edit fixed does not enter, because an
    order that is merely a good one stays a good one when an arrow is cut.

    Args:
        forward: The finished forward pass, for which claim causes which.

    Returns:
        Every claim, in the order they are summed out.
    """
    return _fewest_new_joins(_moral(forward.order, forward.causes), forward.order)


def _chance_of(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    claim: PropositionId,
    order: Sequence[PropositionId],
) -> NDArray[numpy.float64]:
    """Work out one claim's chance of being true, over the claims that can reach it.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.
        claim: The claim being asked about.
        order: The whole map's elimination order, which this filters down.

    Returns:
        `(versions,)` the chance the claim is true.
    """
    inside = _can_reach(forward, pinned, claim)
    factors = _factors(forward, pinned, inside)
    summing = tuple(other for other in order if other in inside and other != claim)
    left = _eliminate(factors, summing).values
    return left[..., 1] / left.sum(axis=-1)


def _refuse_if_nothing_agrees(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    reported: tuple[PropositionId, ...],
    order: Sequence[PropositionId],
) -> None:
    """Refuse an observation no world on the map agrees with, before any answer is read.

    The check is made once for the whole map rather than per claim, because a claim
    cut off from the evidence never meets it: its answer would come out perfectly
    reasonable while the map as a whole says something impossible happened.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.
        reported: The claims *This happened* was used on, in the map's own order.
        order: The whole map's elimination order, which this filters down.

    Raises:
        ImpossibleObservation: If any version leaves no world agreeing with what
            was reported.
    """
    inside = _every_cause_of(forward, pinned, reported)
    factors = _factors(forward, pinned, inside)
    summing = tuple(claim for claim in order if claim in inside)
    agreeing = _eliminate(factors, summing).values
    if bool(numpy.any(agreeing <= 0.0)):
        raise ImpossibleObservation(reported)


def _verb(pinned: Mapping[PropositionId, Pin], claim: PropositionId) -> str | None:
    """Which verb fixed this claim's value, or nothing if no edit fixed it.

    Args:
        pinned: The claims an edit fixed a value on.
        claim: The claim being asked about.

    Returns:
        `"do"` for *Suppose this is true*, `"observe"` for *This happened*, or
        `None`.
    """
    pin = pinned.get(claim)
    return None if pin is None else pin.kind


def _can_reach(
    forward: Forward, pinned: Mapping[PropositionId, Pin], claim: PropositionId
) -> set[PropositionId]:
    """Which claims can move this one, and which therefore have to be worked through.

    Two standard prunings, and between them they are what makes locality a theorem.
    First, only the claim's causes, its causes' causes and so on can move it, along
    with the same for anything *This happened* reported — everything else has a
    table that adds to one and would multiply the answer by exactly nothing.
    Second, of those, only the ones joined to this claim once the map is made moral:
    a claim the evidence cannot reach by any chain of arrows or any shared cause is
    left out of the working entirely, so its answer is the arithmetic it would have
    been given no evidence at all, bit for bit.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.
        claim: The claim being asked about.

    Returns:
        The claims whose tables this claim's answer is worked out over.
    """
    reported = tuple(other for other in forward.order if _verb(pinned, other) == "observe")
    ancestry = _every_cause_of(forward, pinned, (claim, *reported))
    causes = {
        other: () if _verb(pinned, other) == "do" else forward.causes[other] for other in ancestry
    }
    return _joined_to(claim, _moral(ancestry, causes))


def _every_cause_of(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    seeds: tuple[PropositionId, ...],
) -> set[PropositionId]:
    """The claims themselves, their causes, their causes' causes, and so on.

    A claim *Suppose this is true* fixed has no causes any more: the supposition
    cuts the arrows into it, so the walk stops there.

    Args:
        forward: The finished forward pass, for which claim causes which.
        pinned: The claims an edit fixed a value on.
        seeds: The claims to walk back from.

    Returns:
        The seeds and everything upstream of them.
    """
    seen: set[PropositionId] = set()
    waiting = deque(seeds)
    while waiting:
        claim = waiting.popleft()
        if claim in seen:
            continue
        seen.add(claim)
        if _verb(pinned, claim) != "do":
            waiting.extend(forward.causes[claim])
    return seen


def _moral(
    claims: Iterable[PropositionId],
    causes: Mapping[PropositionId, tuple[PropositionId, ...]],
) -> dict[PropositionId, set[PropositionId]]:
    """Make the map moral: drop the arrow directions, and join every claim's causes.

    Two causes of the same claim are joined because summing that claim out would
    join them anyway — the table it leaves behind is written over both of them.

    Args:
        claims: The claims to build the graph over. Every cause named below is one
            of them.
        causes: Claim -> its causes.

    Returns:
        Claim -> the claims it is joined to.
    """
    joined: dict[PropositionId, set[PropositionId]] = {claim: set() for claim in claims}
    for claim in joined:
        for cause in causes[claim]:
            joined[claim].add(cause)
            joined[cause].add(claim)
        for one, other in combinations(causes[claim], 2):
            joined[one].add(other)
            joined[other].add(one)
    return joined


def _joined_to(
    start: PropositionId, joined: Mapping[PropositionId, set[PropositionId]]
) -> set[PropositionId]:
    """Everything reachable from one claim once the map is moral, including itself.

    Args:
        start: The claim to walk out from.
        joined: Claim -> the claims it is joined to.

    Returns:
        The claims in the same piece of the graph as `start`.
    """
    seen = {start}
    waiting = deque([start])
    while waiting:
        for other in joined[waiting.popleft()]:
            if other not in seen:
                seen.add(other)
                waiting.append(other)
    return seen


def _fewest_new_joins(
    joined: Mapping[PropositionId, set[PropositionId]], sequence: Sequence[PropositionId]
) -> tuple[PropositionId, ...]:
    """Take claims in the order that adds the fewest new joins as each one goes.

    Summing a claim out joins everything it was joined to. This counts, for every
    claim still standing, how many pairs of its neighbours are not joined already,
    and takes the smallest count. Ties go to whichever claim the map names first,
    so the order is the same on every machine and every run.

    Args:
        joined: Claim -> the claims it is joined to.
        sequence: The map's own order, used to break ties.

    Returns:
        Every claim, in the order they are summed out.
    """
    left = {claim: set(friends) for claim, friends in joined.items()}
    place = {claim: index for index, claim in enumerate(sequence)}
    out: list[PropositionId] = []
    while left:
        claim = min(left, key=lambda one: (_new_joins(left, one), place[one]))
        friends = left.pop(claim)
        for friend in friends:
            left[friend] = (left[friend] | friends) - {claim, friend}
        out.append(claim)
    return tuple(out)


def _new_joins(left: Mapping[PropositionId, set[PropositionId]], claim: PropositionId) -> int:
    """How many pairs of one claim's neighbours are not joined to each other yet.

    Args:
        left: Claim -> the claims it is joined to, among those still standing.
        claim: The claim being costed.

    Returns:
        The number of joins summing this claim out would add.
    """
    return sum(1 for one, other in combinations(sorted(left[claim]), 2) if other not in left[one])


def _factors(
    forward: Forward, pinned: Mapping[PropositionId, Pin], inside: set[PropositionId]
) -> list[_Factor]:
    """Gather the arrays the elimination multiplies, one or two per claim.

    A claim *Suppose this is true* fixed does not contribute its table: it
    contributes a certainty on the supposed value, over its own axis alone, and
    **that is what cuts the arrows into it**, because those arrows are the other
    axes its table was written over. A claim *This happened* reported contributes
    its table as usual **and** a mask keeping only the worlds that agree.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.
        inside: The claims to gather factors for.

    Returns:
        The factors, in the map's own order, so that the arithmetic below is the
        same on every run.
    """
    out: list[_Factor] = []
    for claim in forward.order:
        if claim not in inside:
            continue
        verb = _verb(pinned, claim)
        versions = int(forward.table[claim].shape[0])
        if verb == "do":
            out.append(_Factor((claim,), _held_at(pinned[claim].value, versions)))
        else:
            out.append(_Factor((*forward.causes[claim], claim), forward.table[claim]))
        if verb == "observe":
            out.append(_Factor((claim,), _held_at(pinned[claim].value, versions)))
    return out


def _held_at(value: bool, versions: int) -> NDArray[numpy.float64]:
    """A one-claim factor holding it at a value: all the weight on one of the two.

    Args:
        value: What the edit fixed the claim to.
        versions: How many versions the map is being worked out at. The same
            certainty stands in every one of them.

    Returns:
        `(versions, 2)` — a one where the claim takes the fixed value, a zero
        where it does not.
    """
    held = numpy.zeros((versions, 2), dtype=numpy.float64)
    held[:, int(value)] = 1.0
    return held


def _eliminate(factors: Sequence[_Factor], summing: Sequence[PropositionId]) -> _Factor:
    """Sum out the named claims one at a time, and multiply out what is left.

    The whole of variable elimination, in five lines: to sum a claim out, take
    every factor that mentions it, multiply just those together, and add up along
    that claim's axis. The result goes back into the pool over whatever claims it
    still mentions. Every claim named in `summing` must be mentioned by at least
    one factor, which is true of every order this module builds.

    Args:
        factors: The arrays to work over.
        summing: The claims to sum out, in the order to take them.

    Returns:
        One factor over whatever claims were not summed out.
    """
    pool = list(factors)
    for claim in summing:
        touching = [factor for factor in pool if claim in factor.over]
        pool = [factor for factor in pool if claim not in factor.over]
        pool.append(_summed_out(touching, claim))
    return _multiplied(pool)


def _summed_out(factors: Sequence[_Factor], claim: PropositionId) -> _Factor:
    """Multiply factors together and add the result up along one claim's axis.

    Args:
        factors: Every factor that mentions the claim.
        claim: The claim to sum out.

    Returns:
        One factor over the other claims those factors mentioned.
    """
    others = tuple(other for other in _every_claim_in(factors) if other != claim)
    return _Factor(others, _laid_out_together(factors, (*others, claim)).sum(axis=-1))


def _multiplied(factors: Sequence[_Factor]) -> _Factor:
    """Multiply factors together over every claim any of them mentions.

    Args:
        factors: The factors to multiply. At least one.

    Returns:
        One factor over every claim they mention between them.
    """
    over = _every_claim_in(factors)
    return _Factor(over, _laid_out_together(factors, over))


def _every_claim_in(factors: Sequence[_Factor]) -> tuple[PropositionId, ...]:
    """Every claim the given factors mention, each once, in the order first met.

    Args:
        factors: The factors to read.

    Returns:
        The claims, in a fixed order, so the arithmetic below is the same on every
        run.
    """
    out: list[PropositionId] = []
    for factor in factors:
        for claim in factor.over:
            if claim not in out:
                out.append(claim)
    return tuple(out)


def _laid_out_together(
    factors: Sequence[_Factor], over: tuple[PropositionId, ...]
) -> NDArray[numpy.float64]:
    """Multiply factors together, each laid out over the same list of claims.

    Args:
        factors: The factors to multiply. At least one.
        over: The claims to lay every one of them out over.

    Returns:
        `(versions,) + (2,) * len(over)` — the product.
    """
    out = _laid_out(factors[0], over)
    for factor in factors[1:]:
        out = out * _laid_out(factor, over)
    return out


def _laid_out(factor: _Factor, over: tuple[PropositionId, ...]) -> NDArray[numpy.float64]:
    """Lay one factor out over a longer list of claims, ready to be multiplied.

    The factor's own axes go where `over` says, and every other claim's axis is
    left one wide, which is how the arithmetic spreads it across the whole without
    ever building a copy of it.

    Args:
        factor: The factor to lay out.
        over: The claims to lay it out over. Every claim the factor mentions is one
            of them.

    Returns:
        `(versions,) + (2 or 1,) * len(over)` — the same numbers, ready to
        multiply.
    """
    mine = len(factor.over)
    wide = factor.values.reshape(factor.values.shape[:1] + (2,) * mine + (1,) * (len(over) - mine))
    lands = tuple(1 + over.index(claim) for claim in factor.over)
    return numpy.moveaxis(wide, tuple(range(1, 1 + mine)), lands)
