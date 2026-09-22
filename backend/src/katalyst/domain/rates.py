"""How a claim's window is cut up, and what each arrow does to the claim's rate.

Decision record 0016 is what this file implements.

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

import itertools
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

_LIKELIHOOD_FLOOR: Final = 1e-9
"""How close to nought or to one a stated chance is allowed to get.

The same value, for the same reason, as the floor the engine on `main` puts under
a likelihood before it takes its logarithm (`propagation.py`, `_log_odds`). A
chance of exactly nought or exactly one has no logarithm, and a map is allowed to
carry both. Keeping the two floors the same is what makes `stated_chance_with`
below the very arithmetic today's engine does, rather than a second version of it.
"""

_NOT_ZERO: Final = 1e-12
"""A floor under a divisor that can honestly come out at nought.

An arrow whose push lands entirely after its target's deadline has no push at all
over the window, and a claim whose deadline is day zero has no window. Dividing by
either is a fault in the map, not in the arithmetic; the floor answers with a very
large rate instead of with `inf`.

**What the claim's own number then comes out at is nought, and that is the honest
answer.** A rate is turned into a chance by multiplying it by the width of the
window it runs over, and a claim judged on day zero has a window of no width at
all: however large the rate, nothing has time to happen. So the claim reads
nought, not one. (This passage used to say the opposite. Measured and corrected on
2026-09-22 — `plans/analysis/scripts/stack-05-core/review/edges.py`, which reads
exactly `0.0`; `test_an_impossible_observation_answers_rather_than_dividing_by
_nothing` is the test that rests on it.)
"""


@dataclass(frozen=True)
class Window:
    """A stretch of days from day zero to a resolve-by day, cut into equal slices.

    **Every claim is worked out on its own window, cut from its own resolve-by
    day** — never on a grid the rest of the map decides. That is what makes a claim
    an edit cannot reach come out byte for byte the same: inserting a claim judged
    six months later changes the map's longest window, and if every claim were cut
    from that, every slice boundary on the map would move and claims the insertion
    cannot reach would move with them. The repository has been bitten by exactly
    that once already, when thinning a series' drawn days re-timed a claim in a
    wholly separate piece of the map.

    `window_of` gives the **map's** window, which is the longest of them and is what
    the reader is shown; `shapes_of` cuts each claim's own.
    """

    day_zero: date
    """The day the window starts on. Passed in, never read off a clock."""

    days: int
    """How many whole days from day zero to the resolve-by day this window ends at."""

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
class Carried:
    """One arrow's push, carried onto its target's reading days, with the repeats folded together.

    **A *reading* is one thing the arrow's cause might have done** — the slice it came
    on in, or, for an arrow that reads a state's whole stretch, the pair *(the slice
    it came on in, the slice it went off in)*. The arrow's push over its target's
    window is a different array of numbers for each of those.

    **Except that it very often is not.** A cause judged long after its target has
    slices that start after the target's own deadline, and an arrow whose cause
    arrives then pushes **nothing at all** over the target's window — the same array
    of noughts, over and over. So does the reading that means *the cause never came*.
    On the committed Hormuz strike branch the two arrows that hold the oil price back
    carry twenty-five readings each and only five and twenty-five different arrays of
    numbers between them, so the combinations the arithmetic must work through fall
    from six hundred and twenty-five to a hundred and twenty-five.

    **The fold changes no answer.** Two readings whose pushes are the same array of
    numbers give the same everything downstream, entry for entry, so averaging over
    the readings and averaging over the different pushes with the readings' chances
    added up first are the same sum written in a different order.
    """

    push: NDArray[numpy.float64]
    """`(different, slices, POINTS_IN_A_SLICE)` each **different** push, once each.

    `different` counts the arrays of numbers that are not equal to one another, not
    the readings. `for_each_reading` writes them back out one per reading.
    """

    of_each_reading: NDArray[numpy.int64]
    """`(readings,)` which row of `push` each reading takes.

    The readings are flattened in the order the arrow's cause-time axes are written —
    for an arrow that reads a whole stretch, the slice the cause came on in changing
    slowest — which is the very layout a claim's times are held in
    (`states.Times.spread` and `states.Times.pairs`).
    """

    whole_stretch: bool
    """Whether a reading is a **pair** *(came on, went off)* rather than one slice.

    True only for a `sustain` arrow out of a claim that holds over a stretch of time.
    It is what says how many readings there are — `slices + 1` when false and that
    squared when true — and which of a cause's two arrays of times to read.
    """

    @property
    def readings(self) -> int:
        """How many different *when its cause happened* this arrow's push is held for."""
        return int(self.of_each_reading.shape[0])

    @property
    def different(self) -> int:
        """How many of those readings carry arrays of numbers that are not all equal."""
        return int(self.push.shape[0])

    def fold(self, chance: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
        """Add a chance spread over every reading up into one number per different push.

        Args:
            chance: `(versions, readings)` how much chance sits on each reading, in
                the flattened order `of_each_reading` is written in.

        Returns:
            `(versions, different)` the same chance, with the readings that carry the
            same push added together.
        """
        together = numpy.argsort(self.of_each_reading, kind="stable")
        starts = numpy.searchsorted(self.of_each_reading[together], numpy.arange(self.different))
        folded: NDArray[numpy.float64] = numpy.add.reduceat(chance[:, together], starts, axis=1)
        return folded

    def for_each_reading(self) -> NDArray[numpy.float64]:
        """This arrow's push written back out once per reading, repeats and all.

        The shape the fold was taken from: `(slices + 1, slices, POINTS_IN_A_SLICE)`
        for an arrow that reads the moment its cause came on, and `(slices + 1,
        slices + 1, slices, POINTS_IN_A_SLICE)` for one that reads a whole stretch.

        Nothing in the arithmetic calls this; it is how a reader, or a test, sees the
        push the fold was taken from.
        """
        whole: NDArray[numpy.float64] = self.push[self.of_each_reading]
        if not self.whole_stretch:
            return whole
        side = round(self.readings**0.5)
        return whole.reshape(side, side, *whole.shape[1:])


def _folded(pushed: NDArray[numpy.float64], *, whole_stretch: bool) -> Carried:
    """Put an arrow's push away with the readings that carry identical numbers folded together.

    Args:
        pushed: The push at every reading day, for everything the cause might have
            done: `(…cause-time axes…, slices, POINTS_IN_A_SLICE)`.
        whole_stretch: Whether a reading is a pair *(came on, went off)*.

    Returns:
        The same push, each different array of numbers kept once.
    """
    slices, points = pushed.shape[-2], pushed.shape[-1]
    flat = pushed.reshape(-1, slices * points)
    kept, which = numpy.unique(flat, axis=0, return_inverse=True)
    return Carried(
        push=kept.reshape(-1, slices, points),
        of_each_reading=which.reshape(-1).astype(numpy.int64),
        whole_stretch=whole_stretch,
    )


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
    """How many whole days from day zero to this claim's own resolve-by day."""

    edges: NDArray[numpy.float64]
    """`(slices + 1,)` the day each of **this claim's** slice boundaries falls on.

    Cut from day zero to this claim's own deadline and from nothing else, so that
    nothing else on the map can move them.
    """

    middle_day: NDArray[numpy.float64]
    """`(slices + 1,)` the day that stands for this claim happening in each of its slices.

    The middle of the slice, never its end. The last entry is positive infinity and
    means *the claim never happened*.
    """

    width: NDArray[numpy.float64]
    """`(slices,)` how many days of this claim's window fall in each of its slices.

    Every slice is the same width, because the window is cut from the claim's own
    deadline: the last slice ends exactly on it, and nothing is ever counted past it.
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

    carried: Mapping[int, Carried]
    """Arrow -> the arrow's push carried to this claim's reading days, for each time its cause came.

    Two layouts, and which one an arrow has is decided by the kind of truth its
    **source** is and by the arrow's mode:

    * `slices + 1` readings — a `trigger` arrow, which reads only the day its cause
      came on and keeps pushing afterwards. The reading is the slice the cause
      arrived in, its last index meaning *the cause never came*.
    * `(slices + 1) * (slices + 1)` readings — a `sustain` arrow out of a **state**,
      which reads its cause's whole stretch and is dead once the cause stops holding.
      The reading is the pair *(the slice it came on in, the slice it went off in)*,
      flattened with the on-slice changing slowest.

    The second layout is slices **squared** readings, and it is the cost
    `needs_the_joint` exists so that a state nobody reads the stretch of never pays.

    **That flattened order is the very layout a claim's times are held in**
    (`states.Times.spread` and `states.Times.pairs`), so a cause's times and the push
    its arrow carries are contracted against each other with no unpacking on either
    side — after `Carried.fold` has added the chances of the readings that carry the
    same push together.
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

    One entry per arrow that holds its claim back, and none for any other kind:
    a helping arrow and an ending arrow are both fitted with nothing clamped.
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


MOST_NUMBERS_AT_ONCE: Final = 16_000_000
"""How many numbers one working array may hold while a helping arrow's total is read.

Sixteen million of them is a hundred and twenty-eight megabytes. The array being
bounded is *versions by combinations by readings by slices*, and on a map with two
arrows holding one claim back it would otherwise be gigabytes. Versions are read in
blocks small enough to stay under this, which changes no number: every version is
worked out from the same arrays, and a version enters only as a scalar multiplying
them.
"""


@dataclass(frozen=True)
class Spread:
    """One helping arrow's rate added up across the window, kept as the pieces it is a sum of.

    **Why this is not one array.** What a reader wants is *versions by combinations
    by readings by slices*: for each version of the stated numbers, for each
    combination of the arrival times of the arrows that hold the claim back, for each
    time this arrow's own cause might have come, a running total to the end of each
    slice. On a map where two arrows hold one claim back that array is six hundred
    and twenty-five combinations wide and runs to gigabytes — the committed Hormuz
    strike branch needed 12.53 gigabytes of them, and the product did not run.

    **It does not have to be one array**, because a version enters only as a number
    multiplying arrays nothing about a version changes. The claim's rate is expanded
    into one term per *subset* of the arrows that hold it back; each term is a
    version-free block, and each carries one number per version. So what is stored is
    small, and the big array is built only for as many versions at a time as
    `MOST_NUMBERS_AT_ONCE` allows.

    A reader asks for what it needs: `over_the_window` for the total on the claim's
    deadline, `between` for a block of versions, `whole` for all of them, and
    indexing with a version number for one version.
    """

    rate: NDArray[numpy.float64]
    """`(versions,)` how much this arrow adds to the claim's rate while it is pushing."""

    coefficients: NDArray[numpy.float64]
    """`(versions, terms)` what each term of the expansion is multiplied by, per version."""

    blocks: tuple[NDArray[numpy.float64], ...]
    """One per term: `(rows, readings, slices)` that term's push, which no version changes.

    `rows` is however many combinations of the **different** pushes the arrows in
    **that term** have between them — one for the term that names no arrow at all.

    **Already a running total from day zero to the end of each slice.** Adding up
    across the slices is a sum, and a sum can be taken before the version's number is
    multiplied through as well as after; taking it here means it is taken over a block
    of a few hundred numbers rather than over the same block repeated once per
    version, which on the Hormuz strike branch was a quarter of the whole run.
    """

    rows: tuple[NDArray[numpy.int64], ...]
    """One per term: `(combos,)` which row of that term's block each combination takes."""

    versions: int
    """How many versions were drawn."""

    combos: int
    """How many combinations of the holding-back arrows' arrival times there are."""

    readings: int
    """How many **different** pushes this arrow carries: `Carried.different`.

    Not how many readings the arrow has. Readings whose push is the same array of
    numbers are folded together by `Carried.fold`, which is exact, and it is the
    folded count that every array here is built at. The entries where the cause never
    came hold nought, so the exponential of minus them is one and such a cause pushes
    nothing.
    """

    slices: int
    """How many slices the claim's window is cut into."""

    @property
    def shape(self) -> tuple[int, int, int, int]:
        """The shape the whole thing would have, without building it."""
        return (self.versions, self.combos, self.readings, self.slices)

    def versions_at_once(self) -> int:
        """How many versions can be built at a time under `MOST_NUMBERS_AT_ONCE`."""
        per_version = max(self.combos * self.readings * self.slices, 1)
        return max(1, MOST_NUMBERS_AT_ONCE // per_version)

    def version_blocks(self) -> list[tuple[int, int]]:
        """The version ranges to read this in, each small enough to build at once."""
        step = self.versions_at_once()
        return [
            (first, min(first + step, self.versions)) for first in range(0, self.versions, step)
        ]

    def between(self, first: int, last: int) -> NDArray[numpy.float64]:
        """Build the running totals for the versions from `first` up to but not including `last`.

        Args:
            first: The first version to build.
            last: One past the last version to build.

        Returns:
            `(last - first, combos, readings, slices)` a running total from day zero
            to the end of each slice, the rate already multiplied through.
        """
        total = numpy.zeros((last - first, self.combos, self.readings, self.slices))
        for term, (block, row) in enumerate(zip(self.blocks, self.rows, strict=True)):
            total += self.coefficients[first:last, term][:, None, None, None] * block[row][None]
        built: NDArray[numpy.float64] = self.rate[first:last, None, None, None] * total
        return built

    def whole(self) -> NDArray[numpy.float64]:
        """Build every version at once. Only for a claim small enough that it fits."""
        return self.between(0, self.versions)

    def over_the_window(self) -> NDArray[numpy.float64]:
        """The running total on the claim's deadline, which is the end of its last slice.

        Read straight off the pieces rather than off the whole: every block is already
        a running total, so the total on the deadline is its last slice, and nothing
        per slice is ever built. Every version is done at once.

        Returns:
            `(versions, combos, readings)`.
        """
        ends = numpy.zeros((self.versions, self.combos, self.readings))
        for term, (block, row) in enumerate(zip(self.blocks, self.rows, strict=True)):
            ends += self.coefficients[:, term][:, None, None] * block[..., -1][row][None]
        whole: NDArray[numpy.float64] = self.rate[:, None, None] * ends
        return whole

    def __getitem__(self, version: int) -> NDArray[numpy.float64]:
        """One version's running totals, `(combos, readings, slices)`."""
        one: NDArray[numpy.float64] = self.between(version, version + 1)[0]
        return one


@dataclass(frozen=True)
class AddedUp:
    """Each rate added up across the window, ready to be turned into survival by one exponential.

    **A running total from day zero to the end of each slice**, with every entry a
    rate already multiplied through — so the chance a claim has not happened by the
    end of a slice is the exponential of minus the entries added together, and
    nothing that reads this has to take a running total or multiply by a rate first.

    `combos` counts the combinations of the **different** pushes the arrows that
    **hold the claim back** carry — readings whose push is the same array of numbers
    having been folded together first by `Carried`. Those combinations are the one
    place the cost still multiplies out: three arrows cost about twice a plain pass
    and ten cost about seventy times it. Every other kind of arrow is averaged one
    cause at a time, which is exact because the rates add.
    """

    leak: NDArray[numpy.float64]
    """`(versions, combos, slices)` the no-cause rate, added up to the end of each slice."""

    helps: Mapping[int, Spread]
    """Arrow -> a helping cause's rate added up, held as the pieces it is a sum of.

    It is not one array, because on a map with two arrows holding one claim back one
    array would run to gigabytes. `Spread` says how to read it.
    """


def _log_odds(likelihood: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """Turn a chance into log-odds: the scale on which separate pushes add up.

    The same two lines, and the same floor, as the engine on `main`. Log-odds is
    the logarithm of the ratio of a chance to its opposite.
    """
    kept = numpy.clip(likelihood, _LIKELIHOOD_FLOOR, 1.0 - _LIKELIHOOD_FLOOR)
    turned: NDArray[numpy.float64] = numpy.log(kept / (1.0 - kept))
    return turned


def _likelihood_of(log_odds: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """Turn log-odds back into a chance between nought and one."""
    turned: NDArray[numpy.float64] = 1.0 / (1.0 + numpy.exp(-log_odds))
    return turned


def _push_at(arrow: Link, elapsed: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """How big one arrow's push is, as a share of its full size, some days after its cause.

    The same three shapes, with the same meanings, that the engine on `main` reads
    (`propagation.py`, `_shape_row`), so one arrow means one thing whichever engine
    is running. A **step** is nothing through the delay, then full size, held. A
    **spike** is nothing through the delay, then full size, halving every half-life.
    A **ramp** climbs from nothing to full size across the delay, then holds.

    A ramp with no delay needs no rule of its own: with the delay at nothing there
    are no days left to climb over, and the shape is a step as a consequence rather
    than as a special case. A spike that does not say how fast it fades is a fault
    in the map, refused by the map's own rules long before this; the line that holds
    the push rather than dividing by nothing is the net under a map that arrived
    some other way.

    Args:
        arrow: The arrow.
        elapsed: How many days after its cause became true each reading day is.
            Negative infinity where the cause never became true, which lands in
            *before the delay* and so pushes nothing.

    Returns:
        One share between nought and one for each reading day.
    """
    landed = elapsed >= arrow.lag
    held: NDArray[numpy.float64] = numpy.where(landed, 1.0, 0.0)
    if arrow.shape == "step":
        return held
    if arrow.shape == "ramp":
        climbing = (elapsed >= 0.0) & ~landed
        climbed: NDArray[numpy.float64] = numpy.where(
            climbing, elapsed / max(arrow.lag, _NOT_ZERO), held
        )
        return climbed
    half_life = arrow.half_life
    if half_life is None or half_life <= 0.0:
        return held
    # The exponent is read as nought on the days the push has not landed on, so that
    # a cause that never came — whose elapsed days are negative infinity — raises two
    # to the power of nothing rather than to the power of infinity. Either way the
    # line below throws the answer away on those days.
    since = numpy.where(landed, elapsed - arrow.lag, 0.0)
    faded: NDArray[numpy.float64] = numpy.where(landed, 2.0 ** (-since / half_life), 0.0)
    return faded


def window_cut_to(day_zero: date, days: int, slices: int) -> Window:
    """Cut one stretch of days, from day zero to a resolve-by day, into equal slices.

    Args:
        day_zero: The day the stretch starts on. This layer reads no clock.
        days: How many whole days it runs for.
        slices: How many equal pieces to cut it into.

    Returns:
        The window, with the day each slice boundary falls on and the day that
        stands for an arrival in each slice.
    """
    edges = numpy.linspace(0.0, float(days), slices + 1)
    middles = 0.5 * (edges[:-1] + edges[1:])
    return Window(
        day_zero=day_zero,
        days=days,
        slices=slices,
        edges=edges,
        middle_day=numpy.append(middles, numpy.inf),
    )


def window_of(graph: Graph, day_zero: date, *, slices: int = SLICES) -> Window:
    """Cut the map's own window — day zero to the last day anything on it is judged.

    **This is the window the reader is shown, not the grid any claim is worked out
    on.** Each claim is cut from its own resolve-by day by `shapes_of`, so that
    inserting a claim judged long after everything else cannot move a claim the
    insertion has no arrow to.

    Args:
        graph: The map. Its latest resolve-by day is where the window ends.
        day_zero: The day the window starts on. This layer reads no clock.
        slices: How many equal pieces to cut it into.

    Returns:
        The map's window.
    """
    days = max(max(0, (one.resolution.by - day_zero).days) for one in graph.propositions)
    return window_cut_to(day_zero, days, slices)


def shapes_of(
    claim: Proposition,
    arrows: Sequence[Link],
    source_persistence: Mapping[LinkId, Persistence],
    source_deadline: Mapping[LinkId, int],
    window: Window,
    *,
    persistence: Persistence,
) -> ClaimShapes:
    """Work out everything about one claim's arrows that no version can change.

    **What an arrow does is settled here, once, from the numbers as they were
    stated** — the claim's own chance and, through `stated_chance_with`, the chance
    with that one cause on. A version redraws both, and a redraw can put a helping
    arrow's chance below the claim's own; the calibration below answers that with a
    push of nothing rather than by moving the arrow into another list, because an
    arrow that changes what it is from version to version is not one arrow.

    **The claim is cut from its own deadline**, and each arrow's cause from that
    cause's own deadline. Nothing else on the map touches either grid, which is what
    makes a claim an edit cannot reach come out byte for byte the same when a claim
    judged much later is inserted somewhere else.

    Args:
        claim: The claim being worked out. Its own stated chance is what each
            arrow's number is compared against to decide what that arrow does, and
            its own resolve-by day is where its window ends.
        arrows: The arrows into this claim, which become the cause axes in the order
            given here.
        source_persistence: For each of those arrows, which kind of truth its
            **source** is. A `sustain` arrow out of a state is the one case that
            needs its cause's whole stretch rather than the moment it came on.
        source_deadline: For each of those arrows, how many whole days from day zero
            to its **source's** resolve-by day. It is what says which day a cause
            arriving in one of its own slices actually arrived on.
        window: Any window on this map, read only for the day it starts on and how
            many slices to cut into. The claim's own window is cut here.
        persistence: Which kind of truth **this** claim is. It is what tells a
            holding-back arrow from an ending one: an arrow stated below the claim's
            own chance scales down an event's rate and adds to a state's stopping
            rate. Passed in rather than read off the claim, because the field that
            carries it arrives with the flip.

    Returns:
        This claim's shapes: its own grid, the arrow order, which arrow does what,
        each arrow's push carried to the claim's own reading days, and each arrow's
        area.
    """
    deadline = max(0, (claim.resolution.by - window.day_zero).days)
    mine = window_cut_to(window.day_zero, deadline, window.slices)
    starts = mine.edges[:-1]
    width = mine.edges[1:] - starts
    inside = (numpy.arange(POINTS_IN_A_SLICE) + 0.5) / POINTS_IN_A_SLICE
    points = starts[:, None] + inside[None, :] * width[:, None]

    own = numpy.array([float(claim.prior.p)])
    # Both sides of the comparison below are read through the same bridge. An
    # arrow's number comes from `stated_chance_with`, which runs the claim's own
    # chance through the log-odds scale and so cannot return exactly nought or
    # exactly one; the claim's raw number can be either. Compared against the raw
    # number, a map that calls a claim **certain** files every arrow that helps it
    # under `holds_back` — the one axis whose cost multiplies, three such arrows
    # costing 15 625 combinations instead of one — and a map that calls a claim
    # **impossible** files every arrow that holds it back under `helps`. The map is
    # legal either way: a stated chance of one or nought breaks no rule. So the
    # claim's own chance is read the same way the arrow's is, and the sign of the
    # push decides rather than a floor. (Review of 2026-09-22, should-fix 5.)
    as_the_arrows_are_read = float(stated_chance_with(own, numpy.zeros(1))[0])
    helps: list[int] = []
    holds_back: list[int] = []
    ends: list[int] = []
    carried: dict[int, Carried] = {}
    area: dict[int, float] = {}
    for position, arrow in enumerate(arrows):
        with_it = stated_chance_with(own, numpy.array([float(arrow.strength)]))
        if float(with_it[0]) >= as_the_arrows_are_read:
            helps.append(position)
        elif persistence == "state":
            ends.append(position)
        else:
            holds_back.append(position)

        theirs = window_cut_to(window.day_zero, source_deadline[arrow.id], window.slices)
        pushed = _push_at(arrow, points[None, :, :] - theirs.middle_day[:, None, None])
        whole_stretch = arrow.mode == "sustain" and source_persistence[arrow.id] == "state"
        if whole_stretch:
            # The push is dead once its cause stops holding, so it is read for every
            # pair of *came on in this slice, went off in that one*. The last index of
            # the off axis is *still holding*, whose day is positive infinity, and a
            # reading day is always before that.
            still_on = points[None, None, :, :] < theirs.middle_day[None, :, None, None]
            pushed = pushed[:, None, :, :] * still_on
        carried[position] = _folded(pushed, whole_stretch=whole_stretch)
        area[position] = float((width * _push_at(arrow, points).mean(axis=1)).sum())

    return ClaimShapes(
        claim=claim.id,
        deadline=deadline,
        edges=mine.edges,
        middle_day=mine.middle_day,
        width=width,
        points=points,
        arrows=tuple(arrow.id for arrow in arrows),
        helps=tuple(helps),
        holds_back=tuple(holds_back),
        ends=tuple(ends),
        carried=carried,
        area=area,
    )


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

    **A version that redraws a number the wrong side of the claim's own gets a push
    of nothing**, not a push the other way: a helping arrow's rate stops at nought,
    a holding-back arrow's share stops at the whole of the rate, and an ending
    arrow's chance of stopping stops at nought. What each arrow *is* was settled by
    `shapes_of` from the numbers as stated, and no draw moves it.

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

    Raises:
        ValueError: If the shapes were worked out for the other kind of truth —
            an event with an arrow that ends it, or a state with one that holds it
            back. The two lists are filled by `shapes_of` from this same word, so a
            mismatch means two callers disagreed about one claim.
    """
    misplaced = shapes.ends if persistence == "event" else shapes.holds_back
    if misplaced:
        raise ValueError(
            f"claim '{shapes.claim}' was worked out as a {persistence} but carries "
            f"{len(misplaced)} arrow(s) of the other kind; the shapes and the rates must be "
            f"asked for with the same kind of truth"
        )

    window_days = max(float(shapes.width.sum()), _NOT_ZERO)
    own = numpy.clip(own_chance, 0.0, 1.0 - _LIKELIHOOD_FLOOR)
    leak = -numpy.log1p(-own) / window_days

    helps: dict[int, NDArray[numpy.float64]] = {}
    leaves: dict[int, NDArray[numpy.float64]] = {}
    ends: dict[int, NDArray[numpy.float64]] = {}
    saturated: dict[int, NDArray[numpy.bool_]] = {}

    for position in shapes.helps:
        area = max(shapes.area[position], _NOT_ZERO)
        with_it = numpy.clip(with_this_cause[position], 0.0, 1.0 - _LIKELIHOOD_FLOOR)
        helps[position] = numpy.maximum((numpy.log1p(-own) - numpy.log1p(-with_it)) / area, 0.0)

    for position in shapes.holds_back:
        area = max(shapes.area[position], _NOT_ZERO)
        with_it = numpy.clip(with_this_cause[position], 0.0, 1.0 - _LIKELIHOOD_FLOOR)
        gap = (window_days + numpy.log1p(-with_it) / numpy.maximum(leak, _NOT_ZERO)) / area
        saturated[position] = gap > 1.0
        leaves[position] = numpy.clip(1.0 - gap, 0.0, 1.0)

    for position in shapes.ends:
        area = max(shapes.area[position], _NOT_ZERO)
        with_it = numpy.clip(with_this_cause[position], 0.0, 1.0 - _LIKELIHOOD_FLOOR)
        stops = numpy.clip(
            1.0 - with_it / numpy.maximum(own, _NOT_ZERO), 0.0, 1.0 - _LIKELIHOOD_FLOOR
        )
        ends[position] = -numpy.log1p(-stops) / area

    return Rates(leak=leak, helps=helps, leaves=leaves, ends=ends, saturated=saturated)


def added_up(shapes: ClaimShapes, rates: Rates) -> AddedUp:
    """Add each rate up across the window, once, so the forward pass is gathers and products.

    **Why the arrows that hold a claim back are the expensive ones.** The rate is
    the share those arrows leave, multiplied by the leak plus the helping arrows'
    pushes. Multiplying that out turns the share they leave into a sum over every
    *subset* of them, and each term is a product of pushes that no version changes —
    so a version enters as one number multiplying arrays built once. What does not
    collapse is *when* each of those arrows' causes happened: every combination of
    their arrival times is carried through, which is where the cost of three of them
    (about twice a plain pass) and of ten (about seventy times it) comes from.

    **What does partly collapse is the arrival times that push the same.** A cause
    judged long after this claim, or one that never came at all, pushes nothing over
    this claim's window, so many of its arrival times are the same array of noughts;
    `Carried` folds those together before any combination is formed, which is exact
    and on the Hormuz strike branch takes the combinations from 625 to 125.

    Args:
        shapes: This claim's shapes.
        rates: This claim's rates, one column per version.

    Returns:
        The added-up rates, with the arrows that hold the claim back multiplied out
        over their arrival times and every other kind of arrow left one at a time.
    """
    versions = int(rates.leak.shape[0])
    slices = int(shapes.width.shape[0])
    held = shapes.holds_back
    per_held = tuple(shapes.carried[position].different for position in held)
    combos = int(numpy.prod(per_held)) if held else 1

    # Which of its different pushes each holding-back arrow has in each combination:
    # one row per arrow, one column per combination.
    every = (
        numpy.indices(per_held).reshape(len(held), -1)
        if held
        else numpy.zeros((0, 1), dtype=numpy.int64)
    )

    flat = {position: one.push for position, one in shapes.carried.items()}

    leak_total = numpy.zeros((versions, combos, slices))
    coefficients: list[NDArray[numpy.float64]] = []
    help_blocks: dict[int, list[NDArray[numpy.float64]]] = {
        position: [] for position in shapes.helps
    }
    help_rows: list[NDArray[numpy.int64]] = []

    for size in range(len(held) + 1):
        for term in itertools.combinations(range(len(held)), size):
            coefficient = numpy.ones(versions)
            product = numpy.ones((1, slices, POINTS_IN_A_SLICE))
            for slot in term:
                coefficient = coefficient * -(1.0 - rates.leaves[held[slot]])
                block = flat[held[slot]]
                product = (product[:, None, :, :] * block[None, :, :, :]).reshape(
                    -1, slices, POINTS_IN_A_SLICE
                )
            here = (
                numpy.ravel_multi_index(
                    tuple(every[slot] for slot in term), tuple(per_held[slot] for slot in term)
                )
                if term
                else numpy.zeros(combos, dtype=numpy.int64)
            )
            # **Added up across the slices here, where the block is small.** A running
            # total is a sum, and a version enters as one number multiplying it, so
            # taking the total before the version rather than after is the same
            # arithmetic over a few hundred numbers instead of over millions.
            spread = numpy.cumsum(shapes.width[None, :] * product.mean(axis=2), axis=-1)
            leak_total += coefficient[:, None, None] * spread[here][None, :, :]
            # **The version axis stops here.** Each helping arrow's block is kept as
            # it is — nothing about a version changes it — beside the one number per
            # version it is multiplied by. Multiplying the two out now would be the
            # array that does not fit.
            coefficients.append(coefficient)
            help_rows.append(here)
            for position in shapes.helps:
                together = product[:, None, :, :] * flat[position][None, :, :, :]
                help_blocks[position].append(
                    numpy.cumsum(shapes.width[None, None, :] * together.mean(axis=3), axis=-1)
                )

    stacked = numpy.stack(coefficients, axis=1) if coefficients else numpy.ones((versions, 0))
    return AddedUp(
        leak=rates.leak[:, None, None] * leak_total,
        helps={
            position: Spread(
                rate=rates.helps[position],
                coefficients=stacked,
                blocks=tuple(blocks),
                rows=tuple(help_rows),
                versions=versions,
                combos=combos,
                readings=shapes.carried[position].different,
                slices=slices,
            )
            for position, blocks in help_blocks.items()
        },
    )


def clamped(
    shapes: ClaimShapes, rates: Rates, with_this_cause: Mapping[int, NDArray[numpy.float64]]
) -> tuple[Clamp, ...]:
    """List the arrows that could not hold this claim back as far as their numbers ask.

    One entry per arrow that fell short, with both numbers, so the assembly can put
    a sentence naming the arrow on the world's warnings. An arrow that fell short in
    no version is not listed.

    **Both numbers are read at the version where the miss is largest**, because a
    warning names the worst of what it is warning about. The version is chosen by
    that rule rather than fixed, so nothing here is a number somebody picked.

    Args:
        shapes: This claim's shapes.
        rates: This claim's rates, whose `saturated` entries are what this reads.
        with_this_cause: Arrow position -> `(versions,)` the chance stated for this
            claim with that one cause on. It is what the arrow **asked** for, and it
            cannot be read back out of a rate that has already been clamped.

    Returns:
        One entry per arrow that fell short, in the arrow order of `shapes`.
    """
    window_days = max(float(shapes.width.sum()), _NOT_ZERO)
    fell_short: list[Clamp] = []
    for position in shapes.holds_back:
        short = rates.saturated[position]
        if not bool(short.any()):
            continue
        asked = numpy.clip(with_this_cause[position], 0.0, 1.0 - _LIKELIHOOD_FLOOR)
        left = window_days - (1.0 - rates.leaves[position]) * shapes.area[position]
        delivered = 1.0 - numpy.exp(-rates.leak * left)
        worst = int(numpy.argmax(numpy.where(short, delivered - asked, -numpy.inf)))
        fell_short.append(
            Clamp(
                arrow=shapes.arrows[position],
                asked=float(asked[worst]),
                delivered=float(delivered[worst]),
            )
        )
    return tuple(fell_short)


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
    return _likelihood_of(_log_odds(claim_prior) + strength)
