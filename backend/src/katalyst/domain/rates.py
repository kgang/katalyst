"""How a claim's window is cut up, and what each arrow does to the claim's rate.

**Stubs.** Every function below raises `NotImplementedError`. The shapes, the names
and the plain-words meaning are settled here so that the four people writing the
arithmetic can import each other's work from the first minute. Decision record 0016
is what this file implements.

What a rate is
--------------
A **rate** is how likely a claim is to happen on a given day, supposing it has not
happened yet. Add the rate up across a claim's window and you get the chance it has
happened by the end of it — the number every tile shows. Nothing here is a
likelihood read on one day; the answer is always *by the deadline*.

**Causes add.** Each arrow into a claim is an independent route to it, so each adds
its own amount to the claim's rate. Two causes that each alone take a claim from a
tenth to four tenths give **just under six tenths** together, not nine tenths.

Three kinds of arrow, told apart by the number stated for them
-------------------------------------------------------------
Every arrow carries the chance its target reaches its deadline with that one cause
on and nothing else on. Compare it with the claim's own no-cause chance:

* **above** it — the arrow **helps**: it adds to the rate at which the claim happens.
* **below** it, on a claim that happens once and stays happened — the arrow
  **holds the claim back**: it scales the rate down while the cause is on.
* **below** it, on a claim that holds over a stretch of time and can stop — the
  arrow **ends** it: it adds to the rate at which the claim stops. Decision
  record 0017.

The conventions every array in the new engine obeys
---------------------------------------------------
* **The version axis comes first.** A version is one coherent set of the numbers a
  person stated. Every array is shaped `(versions, …)`. A version enters the
  arithmetic as a single number multiplying arrays that were built once, which is
  why two thousand versions cost one pass rather than two thousand passes.
* **Then the cause axes**, in the order the arrows appear on the claim — the map's
  arrows sorted by target and then by the arrow's own identifier — and **the
  claim's own axis last**.
* **Twenty-four slices.** A window is cut into `SLICES` equal pieces, and the rate
  inside a piece is read at `POINTS_IN_A_SLICE` evenly spaced days. Twelve slices
  halve the cost and miss the accuracy record 0016 states; thirty-two points inside
  a slice has never been measured and is not built.
* **An arrival inside a slice is taken at the slice's middle**, never at its end.
* **Every number is a full-precision `float64`.** The old engine's half-precision
  drawing type does not come over: an exact answer is sold on being exact.
* **The last index of a slice axis means *never*.** On the axis that says when a
  state stopped, it means *still holding*.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final, Literal

import numpy
from numpy.typing import NDArray

from katalyst.domain.graph import Graph
from katalyst.domain.ids import LinkId, PropositionId
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition

SLICES: Final = 24
"""How many equal pieces a claim's window is cut into.

Twenty-four is what decision record 0016 measured its accuracy at. Twelve halves
the cost and fails that record's stated distance to the enumerator it is checked
against.
"""

POINTS_IN_A_SLICE: Final = 8
"""How many evenly spaced days inside each slice the rate is read at.

Eight is what every measurement in record 0016 was taken with. Thirty-two would be
more accurate and nobody has costed it, so it is not built.
"""

Persistence = Literal["event", "state"]
"""Which kind of truth a claim is.

`event` — it happens once and stays happened, such as *the strait reopens*.
`state` — it holds over a stretch of time and can stop, such as *the strait stays
open to commercial transit through 1 November*.

Written here as a plain pair of words rather than read off a claim, because the
field that carries it on a claim arrives with the flip (decision record 0017,
`persistence` required on every claim) and this file lands before that.
"""


@dataclass(frozen=True)
class Window:
    """The stretch of days every claim on one map is worked out over, cut into slices.

    One window is built per map, not per claim. Claims differ only in where their
    own deadline falls inside it.
    """

    day_zero: date
    """The day the window starts on. Passed in, never read off a clock."""

    days: int
    """How many whole days from day zero to the latest resolve-by day on the map."""

    slices: int
    """How many equal pieces the window is cut into. `SLICES` unless a test says otherwise."""

    edges: NDArray[numpy.float64]
    """`(slices + 1,)` the day each slice boundary falls on, the first being day zero."""

    middle_day: NDArray[numpy.float64]
    """`(slices + 1,)` the day that stands for an arrival in each slice.

    Entry `k` is the middle of slice `k` — never its end, which is worth about three
    hundredths of a point on a claim's number at twenty-four slices. The last entry
    is positive infinity, and it means *the claim never happened*.
    """


@dataclass(frozen=True)
class Pin:
    """A value an edit fixed on one claim, and which of the two verbs fixed it.

    It lives in this file rather than beside the solve because the forward pass
    takes it, and the forward pass sits below the solve in the import order.
    """

    value: bool
    """What the edit fixed the claim to: true or false."""

    kind: Literal["do", "observe"]
    """Which verb fixed it.

    `do` is *Suppose this is true*: the claim is cut loose from whatever would have
    caused it and held at the fixed value. `observe` is *This happened*: the claim
    keeps its causes and the answer is narrowed to the worlds that agree with what
    was seen.
    """


@dataclass(frozen=True)
class Drawn:
    """One draw of every number a person stated, one row per version.

    Built by the two draws that survive the change of engine whole — the split
    curve fitted to a stated range, the evenly spread draw across it, and the width
    that comes from where a number was said to have come from. Decision record 0016
    replaces what the engine does with these numbers, not how they are drawn.
    """

    versions: int
    """How many versions were drawn: how sure we are of the numbers put in."""

    own_chance: Mapping[PropositionId, NDArray[numpy.float64]]
    """Claim -> `(versions,)` the chance it reaches its deadline with no cause on."""

    with_this_cause: Mapping[LinkId, NDArray[numpy.float64]]
    """Arrow -> `(versions,)` the chance its target reaches its deadline with that one cause on."""


@dataclass(frozen=True)
class ClaimShapes:
    """One claim's arrows worked out as far as the map's shape alone allows.

    Nothing in here depends on a version. A version redraws the chances a person
    stated and never a lag, an arrow's shape over time, or a half-life — so all of
    this is built once and every version multiplies through it.
    """

    claim: PropositionId
    """The claim these shapes belong to."""

    deadline: int
    """Which day of the window this claim's own resolve-by day is."""

    width: NDArray[numpy.float64]
    """`(slices,)` how many days of **this** claim's window fall in each slice.

    Clipped at the claim's deadline, so a slice past the deadline is zero days wide
    and a slice the deadline falls inside counts only the part before it.
    """

    points: NDArray[numpy.float64]
    """`(slices, POINTS_IN_A_SLICE)` the days inside each slice the rate is read at."""

    arrows: tuple[LinkId, ...]
    """The order of the cause axes: the arrows into this claim, sorted by identifier.

    Every other module reads its cause axes in this order and in no other. An
    index into any of the mappings below is a position in this tuple.
    """

    helps: tuple[int, ...]
    """Which arrows were stated above the claim's own chance: they add to its rate."""

    holds_back: tuple[int, ...]
    """Which arrows were stated below it on an **event**: they scale its rate down."""

    ends: tuple[int, ...]
    """Which arrows were stated below it on a **state**: they add to the rate it stops at.

    Decision record 0017: a state's stopping rate starts at zero and is the sum of
    its ending causes, so a state nothing on the map can end does not end.
    """

    carried: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> the arrow's push carried to this claim's reading days, for each time its cause came.

    Two shapes, and which one an arrow has is decided by the kind of truth its
    **source** is and by the arrow's mode:

    * `(slices + 1, slices, POINTS_IN_A_SLICE)` — a `trigger` arrow, which reads only
      the day its cause came on and keeps pushing afterwards. The first axis is the
      slice the cause arrived in, its last index meaning *the cause never came*.
    * `(slices + 1, slices + 1, slices, POINTS_IN_A_SLICE)` — a `sustain` arrow out
      of a **state**, which reads its cause's whole stretch and is dead once the
      cause stops holding. Its first two axes are the slice the cause came on in and
      the slice it went off in.

    The second shape is slices **cubed**, and it is the cost `needs_the_joint`
    exists so that a state nobody reads the stretch of never pays.
    """

    area: Mapping[int, float]
    """Arrow -> its push added up over this claim's whole window, with the cause on from day zero.

    One number per arrow. It is what every calibration below divides by.
    """


@dataclass(frozen=True)
class Rates:
    """One claim's rates, one column per version, worked out in closed form.

    Nothing in here is searched for by trial: every entry comes out of one formula.
    Every entry is a rate or a plain multiplier, never a chance.
    """

    leak: NDArray[numpy.float64]
    """`(versions,)` the claim's rate with no cause on — what its own stated chance alone gives."""

    helps: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(versions,)` how much that cause adds to the rate while it is pushing."""

    leaves: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(versions,)` the share of the rate a holding-back cause leaves, between 0 and 1.

    Zero means it suppresses the rate entirely while it is on; one means it does
    nothing.
    """

    ends: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(versions,)` how much an ending cause adds to a state's stopping rate."""

    saturated: Mapping[int, NDArray[numpy.bool_]]
    """Arrow -> `(versions,)` true where the arrow could not hold the claim back as far as asked.

    An arrow whose push covers only part of the window cannot hold a claim back to
    the number stated for it, even with the rate suppressed entirely while the cause
    is on. Where this is true the claim comes out **above** the number stated, and
    `clamped` turns that into a sentence the reader sees.
    """


@dataclass(frozen=True)
class Clamp:
    """One arrow that could not hold its claim back as far as the number stated for it asks.

    Kept so the reader is told, by name and with both numbers, rather than shown a
    number that quietly disagrees with the one on the arrow.
    """

    arrow: LinkId
    """The arrow that fell short."""

    asked: float
    """The chance stated for the claim with this cause on."""

    delivered: float
    """What suppressing the claim's rate entirely while the cause is on actually gives."""


@dataclass(frozen=True)
class AddedUp:
    """Each rate added up across the window, ready to be turned into survival by one exponential.

    `combos` counts the combinations of arrival slices of the arrows that **hold the
    claim back**. Those are the one place the cost still multiplies out: three of
    them cost about twice a plain pass and ten cost about seventy times it. Every
    other kind of arrow is averaged one cause at a time, which is exact because the
    rates add.
    """

    leak: NDArray[numpy.float64]
    """`(versions, combos, slices)` the no-cause rate added up over each slice."""

    helps: Mapping[int, NDArray[numpy.float64]]
    """Arrow -> `(versions, combos, slices + 1, slices)` a helping cause's rate added up per slice.

    The third axis is the slice its cause arrived in; its last index means the cause
    never came, and the added-up rate there is zero.
    """


def window_of(graph: Graph, day_zero: date, *, slices: int = SLICES) -> Window:
    """Cut one window, covering every claim on the map, into equal slices.

    Args:
        graph: The map. Its latest resolve-by day is where the window ends.
        day_zero: The day the window starts on. This layer reads no clock.
        slices: How many equal pieces to cut it into.

    Returns:
        The window, with the day each slice boundary falls on and the day that
        stands for an arrival in each slice.
    """
    raise NotImplementedError


def shapes_of(
    claim: Proposition,
    arrows: Sequence[Link],
    source_persistence: Mapping[LinkId, Persistence],
    window: Window,
    *,
    persistence: Persistence,
) -> ClaimShapes:
    """Work out everything about one claim's arrows that no version can change.

    Args:
        claim: The claim being worked out. Its own stated chance is what each
            arrow's number is compared against to decide what that arrow does.
        arrows: The arrows into this claim, which become the cause axes in the order
            given here.
        source_persistence: For each of those arrows, which kind of truth its
            **source** is. A `sustain` arrow out of a state is the one case that
            needs its cause's whole stretch rather than the moment it came on.
        window: The map's window, already cut into slices.
        persistence: Which kind of truth **this** claim is. It is what tells a
            holding-back arrow from an ending one: an arrow stated below the claim's
            own chance scales down an event's rate and adds to a state's stopping
            rate. Passed in rather than read off the claim, because the field that
            carries it arrives with the flip.

    Returns:
        This claim's shapes: the arrow order, which arrow does what, each arrow's
        push carried to the claim's own reading days, and each arrow's area.
    """
    raise NotImplementedError


def rates_of(
    shapes: ClaimShapes,
    own_chance: NDArray[numpy.float64],
    with_this_cause: Mapping[int, NDArray[numpy.float64]],
    *,
    persistence: Persistence,
) -> Rates:
    """Turn the chances a person stated into rates, in closed form and with nothing searched for.

    Three calibrations, one per kind of arrow, each written so that the claim comes
    back out at exactly the chance that was stated for it. Writing `own` for the
    claim's own chance and `with_it` for the chance stated with one cause on:

    * a **helping** arrow: `rate * area = ln(1 - own) - ln(1 - with_it)`
    * a **holding-back** arrow: `leak * (window - (1 - leaves) * area) = -ln(1 - with_it)`
    * an **ending** arrow: `rate * area = -ln(1 - stops)`, where `stops` is
      `1 - with_it / own` — the chance the state stops, which decision record 0017
      says is what an ending arrow is asked for.

    `ln` is the natural logarithm, and `area` is the arrow's push added up over the
    claim's whole window with its cause on from day zero.

    An arrow whose push covers only part of the window cannot always hold a claim
    back as far as its number asks. Where it cannot, `leaves` stops at zero — the
    rate suppressed entirely while the cause is on — the claim comes out above the
    number stated, and the arrow is marked in `Rates.saturated`.

    Args:
        shapes: This claim's shapes, which say what each arrow does and how big its
            push is over the window.
        own_chance: `(versions,)` the chance this claim reaches its deadline with no
            cause on.
        with_this_cause: Arrow position -> `(versions,)` the chance stated for this
            claim with that one cause on and no other.
        persistence: Which kind of truth this claim is.

    Returns:
        The claim's rates, one column per version.
    """
    raise NotImplementedError


def added_up(shapes: ClaimShapes, rates: Rates) -> AddedUp:
    """Add each rate up across the window, once, so the forward pass is gathers and products.

    Args:
        shapes: This claim's shapes.
        rates: This claim's rates, one column per version.

    Returns:
        The added-up rates, with the arrows that hold the claim back multiplied out
        over their arrival slices and every other kind of arrow left one at a time.
    """
    raise NotImplementedError


def clamped(shapes: ClaimShapes, rates: Rates) -> tuple[Clamp, ...]:
    """List the arrows that could not hold this claim back as far as their numbers ask.

    One entry per arrow that fell short, with both numbers, so the assembly can put
    a sentence naming the arrow on the world's warnings. An arrow that fell short in
    no version is not listed.

    Args:
        shapes: This claim's shapes.
        rates: This claim's rates, whose `saturated` entries are what this reads.

    Returns:
        One entry per arrow that fell short, in the arrow order of `shapes`.
    """
    raise NotImplementedError


def stated_chance_with(
    claim_prior: NDArray[numpy.float64], strength: NDArray[numpy.float64]
) -> NDArray[numpy.float64]:
    """The chance a claim reaches its deadline with one cause on and no other.

    **Dated 2026-09-22 and temporary.** The one shape freeze asks the model for this
    number directly, and this function is deleted the day it does. Until then the
    number is derived from the push the old engine elicited.

    **That is a conversion, not an identity.** The old `strength` is an increment in
    log-odds — the logarithm of the ratio of a chance to its opposite — applied to a
    likelihood read on one day, at whatever size the arrow's push had reached that
    day. The number wanted here is a chance by a deadline with the arrow's whole
    push counted. The two agree for an arrow that reaches full size at once and
    holds, and they diverge for every other shape.

    **The claim's own number is converted too, and silently:** its prior is read as
    the chance it reaches its deadline with no cause on, where today it is a
    likelihood read on one day. Both moves are what record 0016 means by *every
    number on the map changes once*, and `make numbers-check` is what makes each one
    a build failure rather than a silent drift.

    Args:
        claim_prior: `(versions,)` the claim's own stated chance.
        strength: `(versions,)` the arrow's elicited push, in log-odds.

    Returns:
        `(versions,)` the chance the claim reaches its deadline with that one cause on.
    """
    raise NotImplementedError
