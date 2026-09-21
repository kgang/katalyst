"""A state's two times: the day it switches on and the day it switches off.

**Stubs.** Every function below raises `NotImplementedError`. Decision record 0017
is what this file implements.

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
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.proposition import Proposition
from katalyst.domain.rates import AddedUp, ClaimShapes, Persistence, Rates

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

    An event's times and a state's are held in the same field, in different shapes,
    told apart by `persistence`. `as_joint` and `holding_curve` are how a reader
    gets at a state's two times without unpacking the flattened row by hand.
    """

    claim: PropositionId
    """The claim these times belong to."""

    persistence: Persistence
    """Which kind of truth the claim is, and so which of the two shapes `spread` has."""

    spread: NDArray[numpy.float64]
    """How much of the chance falls where, one row per version. Each row adds to one.

    * an **event**: `(versions, slices + 1)` — the slice it happened in. The last
      index means it never happened.
    * a **state**: `(versions, (slices + 1) * (slices + 1))` — the pair *(the slice
      it came on in, the slice it went off in)*, flattened with the on-slice
      changing slowest. On-slice at the last index means it never came on; off-slice
      at the last index means it is still holding.
    """


def as_joint(times: Times) -> NDArray[numpy.float64]:
    """Unflatten a state's two times into the square they came from.

    Args:
        times: One claim's times. Must be a state's.

    Returns:
        `(versions, slices + 1, slices + 1)` the chance of each pair *(on-slice,
        off-slice)*.

    Raises:
        ValueError: If the claim is an event. An event has one time and no pair, and
            answering with a square that pretends otherwise would be a number nobody
            can account for.
    """
    raise NotImplementedError


def holding_curve(times: Times) -> NDArray[numpy.float64]:
    """The chance a claim is holding at the end of each slice.

    This is the cheap reading of a state: it costs versions times slices squared,
    where the whole pair of times costs versions times slices cubed. It is all a
    `trigger` child and all the exact solve ever need.

    Args:
        times: One claim's times.

    Returns:
        `(versions, slices)` the chance the claim is holding at the end of each
        slice. For an event this rises and never falls; for a state it can fall.
    """
    raise NotImplementedError


def is_true_on_its_deadline(times: Times) -> NDArray[numpy.float64]:
    """The one bit the exact solve carries: the claim's number as its tile states it.

    For an event, the chance it happened by its deadline. For a state, the chance it
    is holding on its deadline — on by then, and not yet off.

    Args:
        times: One claim's times.

    Returns:
        `(versions,)` that chance, one number per version.
    """
    raise NotImplementedError


def on_and_off(
    shapes: ClaimShapes,
    rates: Rates,
    added: AddedUp,
    cause_times: Sequence[Times],
    *,
    joint: bool,
) -> Times:
    """Work out when one claim came on, and — for a state — when it went off.

    The causes are already done, so their own times are passed in; this adds their
    pushes to the claim's rates and turns the total into the chance the claim came
    on in each slice, and went off in each later one.

    Args:
        shapes: The claim's shapes, in whose arrow order `cause_times` is read.
        rates: The claim's rates, one column per version.
        added: Those rates already added up across the window.
        cause_times: The times of each cause, in the arrow order of `shapes`.
        joint: True to build the whole pair of times, false to build only enough for
            the holding curve. `needs_the_joint` is what decides this, and building
            the pair when nothing reads it costs slices cubed for nothing.

    Returns:
        This claim's times.
    """
    raise NotImplementedError


def needs_the_joint(graph: Graph, claim: Proposition, persistence: Persistence) -> bool:
    """Say whether anything on this map reads a state's whole stretch rather than one moment of it.

    **The cheap path.** Only a `sustain` child reads a state's whole stretch, and
    building that costs versions times slices **cubed** where the holding curve
    alone costs versions times slices squared — about twenty times the work per
    state at two thousand versions and twenty-four slices.

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
    raise NotImplementedError
