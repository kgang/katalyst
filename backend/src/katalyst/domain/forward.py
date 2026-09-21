"""One pass over the map, causes before effects, that works out when every claim happens.

**Stubs.** Every function below raises `NotImplementedError`. Decision record 0016
is what this file implements.

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

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.rates import AddedUp, ClaimShapes, Drawn, Pin, Rates, Window
from katalyst.domain.states import Times

NOTHING_PINNED: Mapping[PropositionId, Pin] = MappingProxyType({})
"""No claim has a value fixed on it. The ordinary case, and the default below.

A frozen mapping rather than an empty dictionary, so that a default cannot be
written into by accident and quietly outlive the call that did it.
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
    arrow comes from.
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
    """
    raise NotImplementedError
