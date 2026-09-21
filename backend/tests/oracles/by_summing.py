"""The first oracle: add up the whole joint by brute force, over somebody else's tables.

**What it is given.** One yes/no table per claim. A claim's table says how likely
that claim is to come true for each combination of its causes' truths: an array
whose first axes are its causes, in a stated order, and whose **last axis is the
claim's own** and runs `[it did not, it did]`, so the last axis adds up to one.
A table may carry a leading **version** axis — the same map with the numbers
redrawn, 2 000 times over — and then every answer carries it too.

**What it does.** It multiplies every table into one array over every claim at
once — two to the power of the number of claims — and then adds that array up.
No elimination, no ordering, no cleverness: the point of this oracle is that a
reader can see at a glance that it is the definition of the thing rather than a
method for working it out.

**The two verbs.**

* *Suppose this is true* (`kind="do"`) — the user pulls a lever. The claim's own
  table is thrown away, **which is what cuts its incoming arrows**, and replaced
  by a certainty on the supposed value. Nothing upstream may move.
* *This happened* (`kind="observe"`) — the user reports news. Every table stays
  where it is; the joint is multiplied by a one-or-nothing mask that keeps only
  the worlds agreeing with what was seen, and what is left is scaled back up to
  add to one. This is the one verb allowed to move a cause.

**What this oracle cannot see.** It never asks where a table came from, so a
table built from the wrong arithmetic — the wrong day, the wrong rate, a cause
read before it arrived — passes here without a murmur. That is not a shortcoming
to be repaired; it is why record 0016 asks for a second oracle, `by_integrating`,
which is forbidden these tables entirely. One oracle alone could not have caught
the error that record found in its own first design.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

MOST_CLAIMS = 12
"""The largest map this will take on.

The joint is two to the power of the number of claims, times the versions. At
twelve claims and 2 000 versions that is about sixty-five megabytes, which is the
most a test should ask a machine for. A larger map is refused by name rather than
run until it runs out of memory.
"""


class ImpossibleEvidence(ValueError):
    """What was reported cannot happen on this map, so there is nothing to renormalise.

    Raised rather than answered, because dividing by nothing and calling the
    result a likelihood is exactly the untraceable number this repository vetoes.
    """


@dataclass(frozen=True)
class Pin:
    """One claim held to a value, and which of the two verbs did it.

    `kind` is `"do"` for *Suppose this is true* and `"observe"` for *This
    happened*. They are not the same operation and this oracle keeps them apart:
    that is invariant INV-3, *assert is not observe*.
    """

    value: bool
    kind: Literal["do", "observe"]


@dataclass(frozen=True)
class Tables:
    """Every claim's yes/no table, and the axis order each one was written in."""

    order: tuple[str, ...]
    """Every claim, causes before effects. Any order works; this one reads best."""

    causes: Mapping[str, tuple[str, ...]]
    """Which claims are a claim's causes, in the order its table's axes are in."""

    table: Mapping[str, np.ndarray]
    """Claim -> its table, shaped (versions,) + (2,) per cause + (2,) for itself.

    The leading version axis is optional; leave it off and every answer comes back
    as a plain number rather than a column.
    """

    pinned: Mapping[str, Pin] = field(default_factory=dict)
    """Left empty by callers who pass their pins to `by_summing` instead."""


def by_summing(tables: Tables, pinned: Mapping[str, Pin] | None = None) -> dict[str, np.ndarray]:
    """Work out every claim's chance of being true, by adding up the whole joint.

    Args:
        tables: One yes/no table per claim, with the axis order each was written
            in.
        pinned: Which claims are held to a value, and by which verb. Left out, it
            is read from the tables themselves.

    Returns:
        One answer per claim: the chance it is true. Each answer has whatever
        leading version axis the tables carried — a column of 2 000 numbers if
        they carried 2 000 versions, and a single number if they carried none.

    Raises:
        ValueError: If the map is larger than this oracle will take on, if a
            table is not the shape its causes say it should be, or if a table's
            last axis does not add up to one.
        ImpossibleEvidence: If what was reported cannot happen on this map.
    """
    held = dict(tables.pinned if pinned is None else pinned)
    names = tuple(tables.order)
    if len(names) > MOST_CLAIMS:
        raise ValueError(
            f"This oracle adds up the whole joint, so it takes at most {MOST_CLAIMS} "
            f"claims; it was handed {len(names)}."
        )

    versions = _version_axis(tables)
    lead = () if versions is None else (versions,)
    first = len(lead)
    axis_of = {name: first + index for index, name in enumerate(names)}

    joint = np.ones(lead + (2,) * len(names), dtype=np.float64)
    for name in names:
        pin = held.get(name)
        if pin is not None and pin.kind == "do":
            # *Suppose this is true*: the claim's own table goes, and with it every
            # arrow into the claim, because those arrows are what the table is
            # written over. A certainty on the supposed value takes its place.
            joint = joint * _spread(_certainly(pin.value, lead), lead, (axis_of[name],), len(names))
            continue
        joint = joint * _spread(
            _checked(name, tables),
            lead,
            (*(axis_of[cause] for cause in tables.causes[name]), axis_of[name]),
            len(names),
        )

    for name, pin in held.items():
        if pin.kind != "observe":
            continue
        # *This happened*: keep only the worlds that agree with the news.
        joint = joint * _spread(_certainly(pin.value, lead), lead, (axis_of[name],), len(names))

    every = tuple(range(first, first + len(names)))
    total = joint.sum(axis=every)
    if np.any(total <= 0.0):
        raise ImpossibleEvidence(
            "Nothing on this map can happen alongside what was reported, so there is "
            "no world left to read a likelihood off."
        )

    answers: dict[str, np.ndarray] = {}
    for name in names:
        rest = tuple(axis for axis in every if axis != axis_of[name])
        answers[name] = joint.sum(axis=rest)[..., 1] / total
    return answers


def _certainly(value: bool, lead: tuple[int, ...]) -> np.ndarray:
    """A one-claim table holding it to a value: all the weight on one of the two.

    It is built carrying whatever version axis the tables carry, because a pinned
    claim is pinned in every version — the same lever, the same news — and every
    other table laid over the joint has that axis in front of it.
    """
    row = np.zeros((*lead, 2), dtype=np.float64)
    row[..., int(value)] = 1.0
    return row


def _version_axis(tables: Tables) -> int | None:
    """How many versions the tables carry, or None if they carry no version axis.

    A claim's table has one axis per cause plus one of its own. Anything left over
    at the front is the version axis, and every table has to agree about it.
    """
    seen: set[int | None] = set()
    for name in tables.order:
        shape = tables.table[name].shape
        wanted = len(tables.causes[name]) + 1
        spare = len(shape) - wanted
        if spare == 0:
            seen.add(None)
        elif spare == 1:
            seen.add(int(shape[0]))
        else:
            raise ValueError(
                f"The table for {name!r} has {len(shape)} axes, where its "
                f"{len(tables.causes[name])} causes and its own truth want {wanted}, "
                "or one more for a version axis."
            )
    if len(seen) != 1:
        raise ValueError(f"The tables disagree about how many versions they carry: {seen}.")
    return seen.pop()


def _checked(name: str, tables: Tables) -> np.ndarray:
    """One claim's table, with the two things a table must be checked for.

    Every axis but the last is two wide, and the last axis adds up to one. Both
    are questions about the table's *shape* rather than about its numbers: this
    oracle takes the numbers entirely on trust, which is the whole of what it
    cannot see.
    """
    arr = np.asarray(tables.table[name], dtype=np.float64)
    if any(size != 2 for size in arr.shape[arr.ndim - len(tables.causes[name]) - 1 :]):
        raise ValueError(f"The table for {name!r} has an axis that is not two wide: {arr.shape}.")
    if not np.allclose(arr.sum(axis=-1), 1.0):
        raise ValueError(
            f"The table for {name!r} does not add up to one along its own axis, so it "
            "is not a table of chances."
        )
    return arr


def _spread(
    arr: np.ndarray, lead: tuple[int, ...], axes: tuple[int, ...], claims: int
) -> np.ndarray:
    """Lay one claim's table out over every claim's axis, ready to be multiplied in.

    The table's own axes go where `axes` says and every other claim's axis is left
    one wide, which is how numpy broadcasts it across the whole joint without ever
    building a copy of it.
    """
    wide = arr.reshape(lead + (2,) * len(axes) + (1,) * (claims - len(axes)))
    came_from = range(len(lead), len(lead) + len(axes))
    return np.moveaxis(wide, tuple(came_from), axes)
