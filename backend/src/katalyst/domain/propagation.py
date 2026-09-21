"""Working the likelihoods through a map: what a world is, and how it is computed.

A branch is a list of edits; a world is what those edits do to the numbers. This
file is the arithmetic in between. It takes the map a fold left behind, the
values that fold fixed, a day to start from and a seed, and gives back one
`World`: a likelihood for every claim on the day that claim is judged, a
likelihood for every day in between, a named state for every one of those days,
and a plain sentence for anything the reader should be told.

**Two loops, because there are two kinds of not-knowing.**

* *How the dice fall.* The strait either opens or it does not. That is already
  inside the likelihood: it is the share of worlds in which the claim came out
  true.
* *How sure we are of the numbers we put in.* Every prior on the map was
  elicited, and **every arrow's push was written down by somebody with more or
  less to go on**. A different but equally defensible set of those numbers would
  give a different answer. **That** is the range.

So the outer loop draws 2 000 **versions of the map** — each one a coherent set
of numbers this model would have stood behind — and the inner loop runs 8
**worlds** under each. The range is the middle 80% across versions once the
coin-flip noise has been subtracted out. A wide range means "we are not sure what
number to give you; more homework would move it", never "the event is more
volatile".

**What this file must never do**

- Never report the spread of the coin flips as the range. Run more worlds and
  that number shrinks, which makes it a statement about the machine rather than
  about the map. The inner noise is subtracted with the law of total variance,
  and a test freezes every prior at a point and demands a band of no width.
- Never let the stream that picks the versions depend on the branch. A base world
  and a branch world built from one seed must try the *same* 2 000 versions, or
  every comparison between them is the user's edit plus a wash of noise. Each
  claim's prior and each arrow's push get a stream of their own, keyed by the seed
  and by that thing's own identifier, so adding a claim or an arrow cannot shift
  what any other one drew.
- Never let a drawn push change the *shape* of the map. Which arrows oppose a
  supposition, and the day one of them undermines it, are read off the strength
  the map states — the same answer in every version, because a retraction is one
  record on one world and cannot be true in version 7 and false in version 8.
  A drawn push decides only how hard that arrow shoves inside its own version.
- Never store how wide an arrow's push is. It is derived from where the arrow came
  from, every time, and there is no `strength_lo` and no `strength_hi`.
- Never model a supposition as a large baseline the arrows argue with. While a
  supposition holds the claim is true in **every** draw, and the tile shows a word
  where a number would mislead.
- Never fit a stated likelihood and its range on the probability scale. The two
  halves are fitted separately on the log-odds scale — the scale the pushes add
  on — which honours all three stated numbers exactly and can never leave 0 to 1.
- No clock, no network, no global random state. Every random number comes from
  the one `seed` argument, so the same map, branch and seed give the same world
  on any machine.
- Never unroll a feedback arrow. A market feeding back on the world is carried as
  data and set aside here exactly as the map's own loop check sets it aside; a
  later stack works it through over time.
"""

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from types import MappingProxyType
from typing import Literal

import networkx
import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.belief import Belief
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, LinkId, PropositionId
from katalyst.domain.link import Link, Provenance
from katalyst.domain.patch import Assignment
from katalyst.domain.proposition import Proposition
from katalyst.domain.validity import _name_of

Numbers = NDArray[numpy.float64]
"""An array of ordinary numbers. Written down once because it appears everywhere below."""

Flags = NDArray[numpy.bool_]
"""An array of true-or-false values: which draws a claim came out true in."""

Draws = NDArray[numpy.float32]
"""One number per draw, kept to about seven digits rather than about sixteen.

Sixteen thousand draws times a claim times a day is a great many numbers, and
holding each to seven digits rather than sixteen runs about three times quicker
and takes half the memory. Nothing visible changes: every number this product
shows is rounded to two significant figures, and every average, spread and
percentile below is still worked out to the full sixteen.
"""

DRAWING = numpy.float32
"""How much precision one draw is kept to. See `Draws`."""


SeriesState = Literal["sampled", "supposed", "withdrawn", "pushed"]
"""What a claim's day is, in one word.

`sampled` — the ordinary case: no supposition has ever touched this claim.
`supposed` — a supposition is holding; the claim is true in every draw and the
tile shows a word rather than a number.
`withdrawn` — the supposition has been undermined and no opposing push has
arrived yet, so the claim reads its own prior again.
`pushed` — an opposing push is live.
"""

PARAMS_STREAM = 1
"""Which stream of random numbers picks each claim's prior. Never sees the branch."""

WORLDS_STREAM = 2
"""Which stream of random numbers rolls the dice inside one version."""

STRENGTHS_STREAM = 3
"""Which stream of random numbers picks each arrow's push. Never sees the branch.

A stream of its own, keyed by the arrow's own identifier, for the same reason the
priors have one: adding an arrow must not shift what any other arrow drew, or two
worlds of one map would stop agreeing about a claim neither of them touched.
"""

PROVENANCE_SPREAD: Mapping[Provenance, float] = MappingProxyType(
    {
        "documented": 0.15,
        "historical": 0.15,
        "market_implied": 0.15,
        "argued": 0.40,
        "user": 0.40,
        "simulated": 0.50,
        "asserted": 0.60,
    }
)
"""How unsure we are of an arrow's push, read off where that arrow came from.

**"How well-backed is this" becomes "how wide is this", with nobody asked a second
question.** An arrow's `provenance` is a receipt our own pipeline writes, never
something a model claims for itself, so it is the one thing on an arrow that
already says how much there was to go on. Each of the versions of the map draws
every arrow's push from a bell curve centred on the push the map states, this wide
— measured in the same log-odds the push itself is written in, so a spread of
`0.40` on a push of `1.6` is four tenths of a log-odds unit and not four tenths of
the push.

The three words that mean *somebody fetched something* are narrow and equal:
`documented` (the search tool returned a page this arrow cites), `historical` (a
study of past cases), `market_implied` (read off a live price). `argued` and
`user` are a stated mechanism and a person's own judgement. `simulated` is a
probe's output. `asserted` is a sentence with no mechanism in it, and it is the
widest for exactly that reason.

**A generated map's arrows are only ever `documented` or `argued`.** The accept
step writes `documented` when the search returned an address the arrow cites and
`argued` otherwise, and the map's own rules refuse an arrow with no mechanism at
all — so no arrow a generation produces is ever `asserted`. The other four words
are written by somebody else: a stored example, a person, a price adapter, a
probe.

**There is no `strength_lo` and no `strength_hi`, now or ever** (Kent, decision
record 0014). The spread is derived from the receipt every time it is needed; a
stored width would be a second number about one arrow, and the two would drift.

Not to be confused with `PROVENANCE_WEIGHT` in `diff.py`, which turns the same
receipt into *how well-backed a route is* for the change list's ranking. Two
questions, two tables: one widens a band, the other ranks a row. Merging them
would make a well-backed arrow's rank depend on how sure we are of its number.
"""

NO_SPREAD: Mapping[Provenance, float] = MappingProxyType(dict.fromkeys(PROVENANCE_SPREAD, 0.0))
"""Every arrow's push held at exactly what the map states.

Not how the engine runs, and not reachable through `propagate`. It exists so that
"the band is not the coin flips" can be **checked** rather than asserted: freeze
every prior at a point, hold every push at its stated value, and a band of any
width at all is the machine talking about itself.
"""

NINETIETH_PERCENTILE = 1.2816
"""How many standard deviations out a bell curve's 10th and 90th percentiles sit."""

SERIES_CAP = 180
"""The most **evenly spaced** points a series is drawn at, however long the window is.

A cap on the evenly spaced points alone, and on both counts it is not a ceiling:
**every claim's resolve-by day is kept whatever the cap says**, because a tile's
headline is read on that day and it has to be a point of the line drawn beneath
it. A map with more than 180 claims judged on 180 different days therefore sends
one point per judged day and no more — more than this number, and every one of
them earning its place. See `_days_to_send`.

It bounds what is **worked out** as well, because the days worked out are the
days sent plus the handful the arithmetic must land on exactly. What it must
never do is decide the *timing* of anything: every day a push fires on is on the
grid exactly, whatever this number is and however long the window runs.
"""

LOWEST_SURVIVAL = 0.02
"""Below this share of worlds surviving an observation, the world warns loudly."""

NOTHING_ADDED: Mapping[LinkId, int] = MappingProxyType({})
"""What "nobody said which edit added which arrow" looks like: an empty, unchangeable map."""

LOUD_STRENGTH = 5.0
"""A push beyond this is roughly 1% to 99% on a coin flip, and is worth a second look."""

RANGE_BINS = 20
"""How many groups the versions are sorted into when working out where a band's width comes from."""

TINY = 1e-9
"""How close to 0 or 1 a likelihood may get before the log-odds scale is asked for a number.

A stated 0 or 1 has no log-odds — the scale runs to infinity there — so it is read
as "as close to certain as this arithmetic can say". Far finer than the two
significant figures anything on screen ever shows.
"""


class Retraction(BaseModel):
    """The end of a supposition: which claim, which day, and what undermined it.

    A claim the user supposed true, and which a later edit has pushed back down,
    is never drawn as plainly true. This is what the tile's *Retracted · date · by
    "…"* badge is written from.

    It records the day the **cause** became true, never that day plus the arrow's
    delay. Tying the end of a supposition to the arrival of the push would tie
    "do I still take your word for this" to a delay parameter — change a lag from
    three days to thirty and the supposition would silently outlive the news.
    """

    model_config = ConfigDict(frozen=True)

    target: PropositionId = Field(description="The claim whose supposition ended.")
    at: date = Field(
        description=(
            "The day it ended: the day the opposing arrow's source was settled, never "
            "that day plus the arrow's delay."
        )
    )
    by_link: LinkId = Field(description="The arrow that undermined the supposition.")
    by_claim: PropositionId = Field(
        description="That arrow's source — the claim the tile names in its badge."
    )
    by: int = Field(
        ge=0,
        description=(
            "Which edit introduced the arrow, as its position in the branch, counting "
            "from 0. Always known, and that is a theorem rather than a convention: "
            "supposing a claim cuts every arrow pointing at it at that moment, so any "
            "arrow that later pushes against it was added afterwards, by an edit."
        ),
    )


class World(BaseModel):
    """One finished answer: a map, the values its edits fixed, and every number worked through.

    A world is a **computed result, never a source of truth**. It can always be
    thrown away and rebuilt from three things — the base map, the branch and the
    seed — and if a stored world ever disagrees with what those three produce, the
    stored world is the one that is wrong.

    Every likelihood in `beliefs` is owned by the model and is read on that claim's
    own resolve-by day, which is the day the claim is judged and the date its tile
    already shows. `series` carries one likelihood per day so the spike and the
    fade are visible rather than hidden, and `states` says, for each of those days,
    whether the number is the ordinary sampled one, a supposition holding, a
    supposition withdrawn with no push yet, or a push that has landed.

    **A claim whose supposition is holding reads 1 — exactly 1, range and all, or
    0 when it was supposed false.** That number is there so that a chain of claims
    multiplied together has a factor for it, and for nothing else: **no surface may
    print it.** Every reader looks at `states` first and prints the word *Supposed*
    where the number would go, because "suppose this is true" answered with a
    likelihood is a tool arguing with the person using it.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(description="The map this world was built from.")
    branch_id: BranchId | None = Field(
        default=None,
        description=(
            "The branch that was folded on. None means the base world, the empty branch. "
            "Working the numbers through takes a map and the values its edits fixed, and "
            "never the branch itself, so whatever asked for the world writes this in."
        ),
    )
    seed: int = Field(description="The one number every random draw in here came from.")
    versions: int = Field(
        description="The outer loop: how many versions of the map were tried — how sure we are "
        "of the numbers we put in."
    )
    worlds: int = Field(
        description="The inner loop: how many worlds were run under each version — how the "
        "dice fall."
    )
    day_zero: date = Field(description="The day the window starts on.")
    days: int = Field(
        description=(
            "How long the window is, in whole days. Not the number of points in a series: "
            "past 180 days a series is drawn at 180 evenly spaced points, plus every claim's "
            "own resolve-by day, which is always kept."
        )
    )
    graph: Graph = Field(description="The map the branch's edits left behind.")
    assignments: tuple[Assignment, ...] = Field(
        description="Every value an edit fixed, in the order the edits were made."
    )
    retractions: tuple[Retraction, ...] = Field(
        description="Every supposition that a later edit undermined, and what undermined it."
    )
    beliefs: Mapping[PropositionId, Belief] = Field(
        description=(
            "The model's likelihood for each claim, read on that claim's own resolve-by "
            "day, with the range that says how sure we are of it."
        )
    )
    series_days: tuple[int, ...] = Field(
        description=(
            "Which day of the window each point of every series stands for, counting from "
            "zero. Ordinarily every day. Past 180 days the series is drawn at fewer, "
            "unevenly spaced days — every claim's own resolve-by day is always among them, "
            "so a tile's headline number is always a point of the line drawn beneath it — "
            "and then this is the only thing that says where those points sit."
        )
    )
    series: Mapping[PropositionId, tuple[float, ...]] = Field(
        description=("One likelihood for each of the days above, for the scrubbable time axis.")
    )
    states: Mapping[PropositionId, tuple[SeriesState, ...]] = Field(
        description="One named state per day, the same length as the series."
    )
    conditionals: Mapping[LinkId, Belief] = Field(
        default_factory=dict,
        description=(
            "The likelihood of an arrow's target with that arrow's source **supposed** "
            "true — never how often the two show up together. Empty on a freshly built "
            "world: it costs a whole extra run per arrow, so it is fetched one arrow at "
            "a time when something asks."
        ),
    )
    range_shares: Mapping[PropositionId, Mapping[PropositionId, float]] = Field(
        default_factory=dict,
        description=(
            "How much of each claim's band comes from not being sure of each claim's "
            "prior: range_shares[target][source]. Nothing on screen reads it yet; it is "
            "carried because the sample it comes from is thrown away otherwise."
        ),
    )
    warnings: tuple[str, ...] = Field(
        default=(),
        description="Plain sentences the reader should see under the map.",
    )


@dataclass(frozen=True)
class Versions:
    """The version-by-version numbers behind a world, which never go on the wire.

    Comparing two worlds means subtracting them **version by version** — version 7
    of one against version 7 of the other — because both were built from the same
    2 000 sets of numbers, so that subtraction cancels the elicitation noise and
    leaves the edit. That needs one number per version per day per claim, which is
    millions of numbers on a map of any size, and no browser should ever be sent
    them.

    So they are not a field on `World`. They are recomputed from the world's own
    three inputs by `versions_of`, which is exact: the same map, assignments and
    seed give the same numbers every time, so a recomputed version is the version
    the world was built from.

    This is a plain frozen record rather than one of the data shapes, because it
    holds arrays rather than values and never crosses to the browser.
    """

    days: tuple[int, ...]
    """Which day of the window each column is."""

    weights: Mapping[PropositionId, Numbers]
    """How much each version counts, **per claim**: one vector of one number per version.

    Every version counts the same unless something was observed, in which case a
    version counts by the share of its worlds that survived — and it survives the
    observations that are evidence about **that claim**, never every observation on
    the branch. Two observations in pieces of the map that share no arrow and no
    cause are independent under the model the engine draws from, so one pooled
    share would let an observation weigh a claim it says nothing about.
    """

    reweighted: frozenset[PropositionId]
    """The claims some observation is evidence about, and so counts the versions of.

    Every other claim is read with every version counting the same, because an
    observation joined to it by no chain of arrows and sharing no cause with it
    changes nothing about it at all. Which observations reach which claim is what
    `weights` above is worked out from; this is the set of claims any of them
    reaches, for a reader who only wants to know whether a claim was weighed.
    """

    priors: Mapping[PropositionId, Numbers]
    """The likelihood each version drew for each claim's prior, one per version."""

    likelihood: Mapping[PropositionId, Numbers]
    """Each version's answer for each claim, one row per version and one column per day."""

    inner_spread: Mapping[PropositionId, Numbers]
    """How much the worlds inside each version disagreed, per version and per day.

    What the noise correction needs. With this and the likelihoods above, a reader
    can rebuild any day's band exactly as the world reports it — which is how a
    difference between two worlds gets each world's band on whichever day it wants
    to read the change on, without a world carrying millions of numbers itself.
    """

    def counting_for(self, claim_id: PropositionId) -> Numbers:
        """Say how much each version counts when this claim's own number is read.

        **The one rule, named once here because everything that reads a number or
        its direction has to obey the same one.** Every version counts the same,
        unless what was observed is evidence about this claim — the claims in
        `reweighted` — and then each version counts by the share of its worlds that
        survived **the observations that are evidence about this claim**, and no
        others. The likelihood, the band, the width a change list reports on
        another day and the direction of a move are all read with the vector this
        gives back, so none of them can be counted one way and another of them
        another way.

        **And a world that kept nothing at all counts every version the same
        again.** Nothing survived what was observed anywhere, so there is no
        surviving share to weigh anything by; counting evenly at least reports the
        map rather than dividing by nothing, and the world carries a loud warning
        saying the reader is looking at the map rather than at an answer. That
        fallback lives here and nowhere else, so every reader gets it.

        Args:
            claim_id: The claim whose number is being read.

        Returns:
            How much each version counts, one number per version. Never all
            zeroes, so anything dividing by its total is safe.
        """
        counting = self.weights[claim_id]
        evenly: Numbers = numpy.ones_like(counting)
        if claim_id not in self.reweighted:
            return evenly
        return counting if counting.sum() > 0.0 else evenly


def propagate(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    versions: int = 2_000,
    worlds: int = 8,
    introduced_by: Mapping[LinkId, int] = NOTHING_ADDED,
) -> World:
    """Work every likelihood on a map through time, and say how sure we are of each.

    Pure: no clock, no network, no global random state. The same map, values and
    seed give a byte-identical world on any machine, which is what makes a
    three-day-old screenshot reproducible from three values.

    The map must already be one the validity rules accept. In particular it must
    have no loops once feedback arrows are set aside, because the claims have to
    be worked through causes-before-effects and a map that runs round in circles
    has no such order.

    Args:
        graph: The map a fold left behind. Never changed.
        assignments: Every value that fold fixed, in the order the edits were made.
            When a claim has more than one, the last is the one in force and the
            earlier ones stay for the record.
        as_of: Day zero — the day the window starts on. This layer reads no clock,
            so the day is always passed in.
        seed: The one number every random draw comes from.
        versions: The outer loop — how many versions of the map to try. Each one is
            a coherent set of numbers this model would have stood behind.
        worlds: The inner loop — how many worlds to run under each version. At
            least two, or there is no inner spread to subtract.
        introduced_by: Which edit added each arrow, by position in the branch, so a
            supposition something undermined can name the edit responsible. Leaving
            it out is only safe when no supposition can be undermined; when one is,
            and its arrow is not in here, that is a broken promise between our own
            two pieces of code and it is said out loud rather than guessed at.

    Returns:
        One world: a likelihood and a range for every claim on the day it is
        judged, a likelihood and a named state for every day the series is drawn
        at — every day of the window until the window outruns the cap, and then
        the days `series_days` names — every supposition that was undermined, and
        a sentence for anything the reader should be told.

    Raises:
        ValueError: If a supposition was undermined by an arrow that `introduced_by`
            does not account for. The one thing this file raises for, and why is in
            `_retractions`.
    """
    return _propagated(
        graph,
        assignments,
        as_of=as_of,
        seed=seed,
        versions=versions,
        worlds=worlds,
        introduced_by=introduced_by,
        spreads=PROVENANCE_SPREAD,
    )


def _propagated(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    versions: int,
    worlds: int,
    introduced_by: Mapping[LinkId, int],
    spreads: Mapping[Provenance, float],
) -> World:
    """Work a map through, with the spread on the arrows' pushes handed in.

    The body of `propagate`, with the one thing `propagate` never lets a caller
    choose. Nothing that ships calls this; `_propagate_with_no_spread` below does,
    and says why.

    Args:
        graph: The map a fold left behind.
        assignments: Every value that fold fixed, in order.
        as_of: Day zero.
        seed: The one number every draw comes from.
        versions: The outer loop.
        worlds: The inner loop.
        introduced_by: Which edit added each arrow.
        spreads: How wide each kind of arrow's push is drawn.

    Returns:
        One world.
    """
    setup = _prepare(graph, assignments, as_of)
    sample = _draw(setup, seed=seed, versions=versions, worlds=worlds, spreads=spreads)
    return _world_from(
        graph,
        assignments,
        setup,
        sample,
        _retractions(setup, introduced_by),
        seed=seed,
        versions=versions,
        worlds=worlds,
    )


def _propagate_with_no_spread(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    versions: int,
    worlds: int,
) -> World:
    """The same world with every arrow's push held at exactly what the map states.

    Not how the engine runs and not reachable through `propagate`, for the same
    reason `_versions_on_every_day` is not: it exists so that a promise can be
    **checked** rather than asserted. Hold every push at its stated value, freeze
    every prior at a point, and there is nothing uncertain anywhere on the map —
    so any band left is the machine reporting its own wobble, which is the single
    most likely way to get this engine wrong.

    It is deliberately **not** an argument on `propagate`. A world carries only the
    map, the branch and the seed, and `versions_of` rebuilds its version-by-version
    numbers from those three — so a world built with a different spread table could
    not be rebuilt, and every comparison against it would be quietly wrong.
    `test_band_is_not_sampling_noise` and `test_range_matches_analytic_first_order_on_fixture`
    are the only callers.

    Args:
        graph: The map to work through.
        assignments: Every value the branch's edits fixed.
        as_of: Day zero.
        seed: The one number every draw comes from.
        versions: The outer loop.
        worlds: The inner loop.

    Returns:
        One world, in which no arrow's push varies between versions.
    """
    return _propagated(
        graph,
        assignments,
        as_of=as_of,
        seed=seed,
        versions=versions,
        worlds=worlds,
        introduced_by=NOTHING_ADDED,
        spreads=NO_SPREAD,
    )


def versions_of(world: World) -> Versions:
    """Give back the version-by-version numbers behind a world, for comparing two of them.

    A world carries the three inputs it was built from, and the arithmetic is
    exact, so this recomputes the same 2 000 versions the world was built from
    rather than storing them. The cost is one more run of the engine; the saving
    is that a world stays small enough to send to a browser.

    Args:
        world: The world to look behind.

    Returns:
        The day each column stands for, how much each version counts, the prior
        each version drew for each claim, and each version's answer for each claim
        on each day.
    """
    setup = _prepare(world.graph, world.assignments, world.day_zero)
    sample = _draw(
        setup,
        seed=world.seed,
        versions=world.versions,
        worlds=world.worlds,
        spreads=PROVENANCE_SPREAD,
    )
    return _versions_from(setup, sample)


def _versions_on_every_day(world: World) -> Versions:
    """The same world's numbers, worked out on **every** day of the window.

    Not how the engine runs and not reachable through `propagate`: the days worked
    out are ordinarily the days sent plus the handful the arithmetic must land on
    exactly, which past 180 days is far fewer than the window has. This exists so
    that the licence for working out fewer days can be **checked** rather than
    asserted — work a map out both ways and require the days they share to agree to
    the bit. `test_a_days_answer_does_not_depend_on_which_other_days_were_worked_out`
    is the only caller, and it is private because nothing that ships should want it.

    Args:
        world: The world to work out again, on every day.

    Returns:
        The version-by-version numbers, one column per day of the window.
    """
    setup = _prepare(world.graph, world.assignments, world.day_zero, every_day=True)
    sample = _draw(
        setup,
        seed=world.seed,
        versions=world.versions,
        worlds=world.worlds,
        spreads=PROVENANCE_SPREAD,
    )
    return _versions_from(setup, sample)


def _sent_days(setup: "_Setup") -> NDArray[numpy.int64]:
    """Where the days a reader is given sit among the days worked out.

    The days worked out are the days sent plus the handful the arithmetic must land
    on exactly, so every sent day is among them and this is a lookup rather than a
    search for a near miss. Worked out once, when the map is prepared, because a
    world asks for it twice.
    """
    return numpy.searchsorted(setup.points, setup.sent).astype(numpy.int64)


def _versions_from(setup: "_Setup", sample: "_Sample") -> Versions:
    """Gather the version-by-version numbers a run produced into one record.

    Written once and used twice: by `versions_of`, which recomputes a world's
    versions for a comparison, and by the step that turns a run into a world,
    which needs the same record to ask how much each version counts. Two copies of
    this would be two chances for a world and the difference between two worlds to
    disagree about what a version is.

    Args:
        setup: Everything chance had no say in.
        sample: What the two loops produced.

    Returns:
        One record of the version-by-version numbers.
    """
    # Thinned to the days a reader is given, so that a difference between two
    # worlds compares exactly the days the two of them show and nothing else.
    sent = _sent_days(setup)
    return Versions(
        days=tuple(int(setup.points[one]) for one in sent),
        weights=sample.weights,
        reweighted=frozenset().union(*setup.observation_reach.values())
        if setup.observation_reach
        else frozenset(),
        priors=sample.priors,
        likelihood={one: row[:, sent] for one, row in sample.likelihood.items()},
        inner_spread={one: row[:, sent] for one, row in sample.inner_spread.items()},
    )


# --- Everything that is decided before a single random number is drawn -----


@dataclass(frozen=True)
class _Spell:
    """One stretch of days over which one edit's fixed value holds on one claim.

    A claim can be fixed more than once — supposed, then reported, then supposed
    again — and each edit's word holds from its own day until the next edit on the
    same claim has something to say. A supposition also stops holding early, on the
    day something undermined it, and the claim is worked out like any other from
    then until the stretch ends.
    """

    kind: Literal["do", "observe"]
    value: bool
    starts: int
    ends: int | None
    """The first day this stretch no longer holds. None means it runs to the end."""
    undermined_on: int | None
    """The day a supposition was undermined, inside this stretch. None means it was not."""
    undermined_by: Link | None
    """The arrow that undermined it, if one did."""


@dataclass(frozen=True)
class _Setup:
    """The whole of a world that does not depend on chance: who causes whom, and when."""

    claims: Mapping[PropositionId, Proposition]
    order: tuple[PropositionId, ...]
    arrows_into: Mapping[PropositionId, tuple[Link, ...]]
    spells: Mapping[PropositionId, tuple[_Spell, ...]]
    settled: Mapping[PropositionId, int]
    day_zero: date
    days: int
    points: NDArray[numpy.int64]
    sent: NDArray[numpy.int64]
    read_at: Mapping[PropositionId, int]
    shape_rows: Mapping[LinkId, Numbers]
    observation_reach: Mapping[PropositionId, frozenset[PropositionId]]
    states: Mapping[PropositionId, tuple[SeriesState, ...]]
    warnings: tuple[str, ...]


def _prepare(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    as_of: date,
    every_day: bool = False,
) -> _Setup:
    """Work out everything about a world that chance has no say in.

    The window, the order claims are worked through in, the day each claim's clock
    starts, which stretch of days each fixed value holds over, which suppositions
    something undermined and on which day, and what the reader should be warned
    about. All of it is the same in every one of the sixteen thousand draws, which
    is exactly why it is computed once.

    Args:
        graph: The map a fold left behind.
        assignments: Every value that fold fixed, in order.
        as_of: Day zero.
        every_day: Work every day of the window out rather than the days a
            reader is sent plus the ones the arithmetic must land on exactly.
            Nothing that ships passes this; `_versions_on_every_day` does, so that
            working out fewer days can be checked against working out all of them.

    Returns:
        Everything the draw below needs and nothing that depends on a seed.
    """
    claims = {one.id: one for one in graph.propositions}
    ordinary = _ordinary_arrows(graph, claims)
    order = _causes_before_effects(claims, ordinary)
    arrows_into: dict[PropositionId, tuple[Link, ...]] = {
        claim_id: tuple(one for one in ordinary if one.target == claim_id) for claim_id in claims
    }

    fixed_on: dict[PropositionId, list[Assignment]] = {claim_id: [] for claim_id in claims}
    for one in assignments:
        if one.target in fixed_on:
            fixed_on[one.target].append(one)
    settled = _settled_days(order, arrows_into, fixed_on, as_of)

    days = _window_length(graph, as_of)
    spells = {
        claim_id: _spells_on(fixed_on[claim_id], arrows_into[claim_id], settled, as_of)
        for claim_id in claims
    }

    # **The days the numbers are worked out on.** Two kinds, and the difference is
    # the whole of what makes an edit local.
    #
    # The days a reader is *sent* — at most 180 of them, evenly spaced, with every
    # claim's resolve-by day always among them. These move when the window's length
    # moves, and that is allowed: they decide where a line is *drawn*, nothing more.
    #
    # And the days the arithmetic must land on **exactly**: the day each claim's
    # clock starts, because a one-off push fires then, and the day each observation
    # speaks, because that is when worlds are thrown away. Reading either off the
    # nearest drawn day is what used to let the window's length re-time a push, so
    # that an inserted claim at one end of a map moved a claim at the other by
    # `.096`. They are put on the grid instead, and every lookup is then exact.
    #
    # Adding them cannot move anything, and that is why this is safe rather than
    # merely cheaper: a claim's answer on a given day is a function of that day and
    # of the map's own timings, never of which *other* days happen to be worked
    # out. So the grid decides only where the series is evaluated.
    sent = (
        numpy.arange(days + 1, dtype=numpy.int64)
        if every_day
        else _days_to_send(claims, as_of, days)
    )
    must_be_exact = {min(max(0, one), days) for one in settled.values()}
    # An observation carries no date today — `Observe` has no `at`, so it always
    # speaks on day zero, which is already on the grid as the first sent day. This
    # term is therefore dead, and it is written anyway: the day an observation
    # speaks is a day the arithmetic reads by name, and the moment `Observe` grows
    # a date the grid must already be landing on it. Adding it later, after the
    # field existed, would be a defect waiting to be found twice.
    for stretches in spells.values():
        must_be_exact |= {
            min(max(0, one.starts), days) for one in stretches if one.kind == "observe"
        }
    points = numpy.union1d(sent, numpy.array(sorted(must_be_exact), dtype=numpy.int64))
    read_at = {
        claim_id: _point_of(points, _day_index(one.resolution.by, as_of, days))
        for claim_id, one in claims.items()
    }

    shape_rows = {one.id: _shape_row(one, settled[one.source], points) for one in ordinary}

    return _Setup(
        claims=claims,
        order=order,
        arrows_into=arrows_into,
        spells=spells,
        settled=settled,
        day_zero=as_of,
        days=days,
        points=points,
        sent=sent,
        read_at=read_at,
        shape_rows=shape_rows,
        observation_reach=_observation_reach(claims, ordinary, spells),
        states=_states(claims, spells, shape_rows, points),
        warnings=_warnings_about(graph, claims, days),
    )


def _ordinary_arrows(graph: Graph, claims: Mapping[PropositionId, Proposition]) -> tuple[Link, ...]:
    """List the arrows the arithmetic actually uses, **in the order the map carries them**.

    A feedback arrow — a market changing the world it is measuring — is left out:
    it is carried as data in this version and worked through by a later stack, the
    same way the map's own loop check leaves it out. An arrow with an end that is
    not on the map is left out too; it already has its own complaint.

    The order is the map's own, and that order means something: folding a branch
    appends each `insert`'s arrows after the ones already there, so an arrow's
    place on the map is the order it arrived in. That is both a settled order to
    add the pushes on a claim up in — so two runs agree to the last digit — and
    the tie-break when two arrows undermine a supposition on the very same day.

    Args:
        graph: The map to read.
        claims: Every claim on it, by identifier.

    Returns:
        The ordinary arrows, in the order the map carries them.
    """
    return tuple(
        one
        for one in graph.links
        if not one.reflexive and one.source in claims and one.target in claims
    )


def _causes_before_effects(
    claims: Mapping[PropositionId, Proposition], arrows: Sequence[Link]
) -> tuple[PropositionId, ...]:
    """Put the claims in an order that always works out a cause before its effects.

    Ties — claims that no arrow orders relative to one another — are broken by
    identifier, so the order depends on the map and never on the order the claims
    happen to be written down in.

    Args:
        claims: Every claim on the map, by identifier.
        arrows: The ordinary arrows.

    Returns:
        Every claim's identifier, causes first.

    Raises:
        networkx.NetworkXUnfeasible: If the map runs round in circles once feedback
            arrows are set aside. Such a map has no causes-before-effects order at
            all, and the validity rules refuse it long before it reaches here.
    """
    walkable: networkx.DiGraph[PropositionId] = networkx.DiGraph()
    walkable.add_nodes_from(sorted(claims))
    walkable.add_edges_from((one.source, one.target) for one in arrows)
    return tuple(networkx.lexicographical_topological_sort(walkable))


def _day_index(when: date | None, day_zero: date, cap: int | None = None) -> int:
    """Turn a date into a whole number of days after day zero.

    Nothing before day zero: a value fixed from a day already gone holds from the
    beginning of the window.

    Args:
        when: The date, or nothing at all, which means day zero.
        day_zero: The day the window starts on.
        cap: The last day of the window, when the answer must sit inside it.

    Returns:
        The day's number, counting from zero.
    """
    if when is None:
        return 0
    index = max(0, (when - day_zero).days)
    return index if cap is None else min(index, cap)


def _window_length(graph: Graph, day_zero: date) -> int:
    """Say how many days the window runs for: day zero to the last day anything is judged."""
    return max(_day_index(one.resolution.by, day_zero) for one in graph.propositions)


def _days_to_send(
    claims: Mapping[PropositionId, Proposition], day_zero: date, days: int
) -> NDArray[numpy.int64]:
    """Choose which days of the window a claim's series carries to the reader.

    **A cap on the evenly spaced points alone**, and never a decision about timing.
    Ordinarily every day of the window. Past 180 days that is more points than
    anybody scrubs through, so a series is drawn at 180 evenly spaced days instead
    — **and every claim's own resolve-by day is kept whatever the cap says**, so a
    map judged on more than 180 different days sends one point per judged day,
    which is more than the cap and is the honest answer. That is not a nicety: a
    tile's headline number is read on the claim's own resolve-by day, and if that
    day were not on the claim's own series the number on the tile would not be a
    point of the line drawn beneath it.

    These days are not, by themselves, the days the engine works out: `_prepare`
    adds to them every day the arithmetic must land on exactly. So the cap does
    bound the work — the days worked out are these plus that handful — but it is
    never what decides when a push fires.

    It was once the whole grid the engine worked on, and that was a defect. A push
    fires on the day its cause is settled, read off the days worked out — so
    thinning them made that day depend on how long the window was, and an edit at
    one end of a map could re-time a claim at the other end that nothing connected
    it to. Measured before it was separated: an inserted claim that stretched a
    window from 31 days to 365 moved a claim in a wholly separate piece of the map
    by `.096`.

    Args:
        claims: Every claim on the map, by identifier.
        day_zero: The day the window starts on.
        days: How long the window is.

    Returns:
        The days to send, in order.
    """
    judged = numpy.array(
        sorted({_day_index(one.resolution.by, day_zero, days) for one in claims.values()}),
        dtype=numpy.int64,
    )
    if days + 1 <= SERIES_CAP:
        return numpy.arange(days + 1, dtype=numpy.int64)
    spare = max(2, SERIES_CAP - len(judged))
    evenly = numpy.rint(numpy.linspace(0, days, spare)).astype(numpy.int64)
    return numpy.union1d(judged, evenly).astype(numpy.int64)


def _settled_days(
    order: Sequence[PropositionId],
    arrows_into: Mapping[PropositionId, Sequence[Link]],
    fixed_on: Mapping[PropositionId, Sequence[Assignment]],
    day_zero: date,
) -> dict[PropositionId, int]:
    """Say which day each claim's clock starts on — the day it is *settled*.

    Three rules, in order. If an edit fixed the claim's value, its clock starts on
    the earliest day any of them holds from. Otherwise it starts on the earliest
    day a live incoming arrow reaches it: the day that arrow's cause was settled,
    plus the arrow's delay, rounded up to a whole day. A claim with neither is
    settled on day zero, because the map carries no timing information about it at
    all.

    **Being settled is not being true.** A claim with nothing fixing it is sampled
    from its own prior in every draw; its clock starting says only when the arrows
    leaving it begin to measure their delays from. Conflating the two is the
    mistake this paragraph exists to prevent.

    Args:
        order: Every claim, causes first.
        arrows_into: The ordinary arrows pointing at each claim.
        fixed_on: Every value fixed on each claim, in the order the edits were made.
        day_zero: The day the window starts on.

    Returns:
        The day each claim's clock starts on.
    """
    settled: dict[PropositionId, int] = {}
    for claim_id in order:
        fixed = fixed_on[claim_id]
        if fixed:
            settled[claim_id] = min(_day_index(one.at, day_zero) for one in fixed)
            continue
        arrivals = [math.ceil(settled[one.source] + one.lag) for one in arrows_into[claim_id]]
        settled[claim_id] = min(arrivals) if arrivals else 0
    return settled


def _shape_row(link: Link, settled: int, points: NDArray[numpy.int64]) -> Numbers:
    """Work out how big one arrow's push is on each day, as a fraction of its full size.

    A plain function of elapsed days, and zero before the cause was settled. A
    **spike** is nothing through the delay, then full size, halving every half-life
    afterwards. A **step** is nothing through the delay, then full size, held. A
    **ramp** climbs from nothing to full size across the delay, then holds.

    A ramp with no delay at all needs no special case: the days at or past the
    delay are settled first, which for a delay of nothing is every day from the
    cause onwards, and the climb is then left with no days to climb over. Such a
    ramp behaves as a step, as a consequence of the shape rather than as a rule.

    A spike always says how fast it fades — a spike that does not is a fault in the
    map, refused by its own rules before it ever reaches here. The line below is
    the net under a map that arrived some other way, and it holds the push rather
    than dividing by nothing.

    Args:
        link: The arrow.
        settled: The day the arrow's cause was settled.
        points: The days to work out.

    Returns:
        One number per day, between 0 and 1.
    """
    elapsed = points.astype(numpy.float64) - settled
    landed = elapsed >= link.lag
    row = numpy.zeros_like(elapsed)
    row[landed] = 1.0
    if link.shape == "step":
        return row
    if link.shape == "ramp":
        climbing = (elapsed >= 0.0) & ~landed
        row[climbing] = elapsed[climbing] / link.lag
        return row
    if link.half_life is None or link.half_life <= 0.0:
        return row
    row[landed] = 2.0 ** (-(elapsed[landed] - link.lag) / link.half_life)
    return row


def _opposing(arrows: Sequence[Link], supposed: bool) -> list[Link]:
    """List the arrows pushing against a supposed value, in the order they were given.

    An arrow opposes a claim supposed **true** when its push is negative, and one
    supposed **false** when its push is positive. An arrow of no strength pushes
    neither way and opposes nothing.
    """
    return [one for one in arrows if (one.strength < 0.0) == supposed and one.strength != 0.0]


def _spells_on(
    fixed: Sequence[Assignment],
    arrows: Sequence[Link],
    settled: Mapping[PropositionId, int],
    day_zero: date,
) -> tuple[_Spell, ...]:
    """Work out which stretch of days each edit's word holds over, on one claim.

    Each edit's word holds from its own day until the next edit on the same claim
    has something to say, because a later assignment overrides an earlier one. A
    supposition also stops early, on the day the **cause** of the first arrow
    pushing against it was settled — not the day that arrow's push reaches full
    size, because tying the end of a supposition to the arrival would tie "do I
    still take your word for this" to a delay parameter.

    A user may suppose a claim again after it was undermined. The second
    supposition holds from its own day until something undermines it again, and the
    series then reads supposed, withdrawn, pushed, supposed — which falls straight
    out of "a later assignment overrides an earlier one" rather than needing a rule
    of its own.

    When two arrows undermine a supposition on the very same day, the one that
    arrived on the map first wins. That is the arrow's own place on the map, which
    is the order the edits added them in: the base map's arrows, then each `insert`'s
    arrows in the order it listed them. Some settled answer is needed or the badge
    would name a different arrow on different runs and a world would stop replaying.

    Args:
        fixed: Every value fixed on this claim, in the order the edits were made.
        arrows: The ordinary arrows pointing at it, in the order the map carries them.
        settled: The day each claim's clock starts on.
        day_zero: The day the window starts on.

    Returns:
        One stretch per edit, in the order the edits were made.
    """
    where = {one.id: index for index, one in enumerate(arrows)}
    days = [_day_index(one.at, day_zero) for one in fixed]
    spells: list[_Spell] = []
    for index, one in enumerate(fixed):
        starts = days[index]
        ends = days[index + 1] if index + 1 < len(days) else None
        undermined_on, undermined_by = None, None
        if one.kind == "do":
            against = [
                (max(starts, settled[arrow.source]), where[arrow.id], arrow)
                for arrow in _opposing(arrows, one.value)
            ]
            live = [entry for entry in against if ends is None or entry[0] < ends]
            if live:
                undermined_on, _, undermined_by = min(live, key=lambda entry: entry[:2])
        spells.append(
            _Spell(
                kind=one.kind,
                value=one.value,
                starts=starts,
                ends=ends,
                undermined_on=undermined_on,
                undermined_by=undermined_by,
            )
        )
    return tuple(spells)


def _retractions(setup: _Setup, introduced_by: Mapping[LinkId, int]) -> tuple[Retraction, ...]:
    """Write down every supposition something undermined, and which edit is to blame.

    **Which edit added the undermining arrow is always known**, and that is a
    theorem rather than a convention: supposing a claim cuts every arrow pointing
    at it at that moment, so any arrow that later pushes against it was added
    afterwards, by an edit with a position in the branch.

    Args:
        setup: Everything chance has no say in.
        introduced_by: Which edit added each arrow, by position in the branch.

    Returns:
        One retraction per supposition that ended, claim by claim.

    Raises:
        ValueError: If an arrow that undermined a supposition is not in the list of
            which edit added what. That is the one thing this file raises for, and
            it is a broken promise between our own two pieces of code rather than
            anything a user did: whoever asked for this world folded a branch onto
            the map and then did not say which edit added which arrow.
    """
    found: list[Retraction] = []
    for claim_id in sorted(setup.spells):
        for spell in setup.spells[claim_id]:
            if spell.undermined_on is None or spell.undermined_by is None:
                continue
            arrow = spell.undermined_by
            if arrow.id not in introduced_by:
                raise ValueError(
                    "A supposition was undermined by an arrow that nothing says was added "
                    "by an edit. Every arrow that can undermine a supposition was added "
                    "after it, so the branch's edits have to be passed in alongside the "
                    "values they fixed."
                )
            found.append(
                Retraction(
                    target=claim_id,
                    at=setup.day_zero + timedelta(days=spell.undermined_on),
                    by_link=arrow.id,
                    by_claim=arrow.source,
                    by=introduced_by[arrow.id],
                )
            )
    return tuple(found)


def _states(
    claims: Mapping[PropositionId, Proposition],
    spells: Mapping[PropositionId, Sequence[_Spell]],
    shape_rows: Mapping[LinkId, Numbers],
    points: NDArray[numpy.int64],
) -> dict[PropositionId, tuple[SeriesState, ...]]:
    """Name what each claim's every day is, so the canvas knows when a number would mislead.

    On a claim no supposition ever touched, and on any day before one takes effect,
    the day is `sampled`. While a supposition holds it is `supposed`, and the tile
    shows the word rather than a likelihood. Once something has undermined it the
    day is `withdrawn` until an opposing push is actually live, and `pushed` after
    that. The gap between the two — the day the world changed and the day the push
    arrives — is the honest shape of the answer, not a bug to hide, which is the
    whole reason these words exist.

    A claim reported to have happened is `sampled` throughout: an observation is
    news rather than a lever, so there is no word standing in for a number.

    Args:
        claims: Every claim on the map, by identifier.
        spells: Which stretch of days each fixed value holds over, per claim.
        shape_rows: How big each arrow's push is on each day.
        points: The days to work out.

    Returns:
        One word per day, per claim.
    """
    named: dict[PropositionId, tuple[SeriesState, ...]] = {}
    untouched: SeriesState = "sampled"
    for claim_id in claims:
        suppositions = [one for one in spells[claim_id] if one.kind == "do"]
        if not suppositions:
            named[claim_id] = (untouched,) * len(points)
            continue
        days: list[SeriesState] = [untouched] * len(points)
        for spell in suppositions:
            pushing = (
                shape_rows[spell.undermined_by.id] > 0.0
                if spell.undermined_by is not None
                else numpy.zeros(len(points), dtype=bool)
            )
            for index, day in enumerate(int(one) for one in points):
                if day < spell.starts or (spell.ends is not None and day >= spell.ends):
                    continue
                if spell.undermined_on is None or day < spell.undermined_on:
                    days[index] = "supposed"
                else:
                    days[index] = "pushed" if pushing[index] else "withdrawn"
        named[claim_id] = tuple(days)
    return named


def _observation_reach(
    claims: Mapping[PropositionId, Proposition],
    arrows: Sequence[Link],
    spells: Mapping[PropositionId, Sequence[_Spell]],
) -> Mapping[PropositionId, frozenset[PropositionId]]:
    """List, for **each** observed claim, the claims that one observation is evidence about.

    Observing something is done by throwing away the worlds it did not happen in,
    and that changes what the survivors say about the claim's **causes** as much as
    about what it causes — which is why observing reaches upstream and supposing
    does not. One observation reaches the observed claim, everything it leads to,
    everything that leads to it, and everything those causes lead to.

    **And nothing else, on purpose.** A claim joined to the observed one by no
    chain of arrows in either direction, and sharing no cause with it, is
    independent of what was observed: the right answer for such a claim is the
    answer it already had. Reading it off the surviving worlds only would let a
    coin flip somewhere else move a number nobody touched — the locality rule
    failing by sampling noise rather than by intent — so those claims are read off
    every world instead.

    **One reach per observation, never the pool of them all.** Two observations in
    pieces of the map that share no arrow and no cause are independent under the
    very model the engine draws from — nothing in the map ties a draw for one piece
    to a draw for the other — so conditioning on one of them says nothing whatever
    about the other's piece. Pooling the reaches would say otherwise: a claim that
    *some* observation is evidence about would be read through *every*
    observation's surviving worlds, and an observation at one end of a map would
    move a claim at the other end that nothing connects it to, by a wash of
    sampling noise. Measured before this was separated: on a map in two pieces,
    observing a claim in one piece moved a claim in the other by **`.083`**.

    Args:
        claims: Every claim on the map, by identifier.
        arrows: The ordinary arrows.
        spells: Which stretch of days each fixed value holds over, per claim.

    Returns:
        For each observed claim, the claims that observation is evidence about.
        Empty when nothing was observed.
    """
    observed = [
        claim_id
        for claim_id, stretches in spells.items()
        if any(one.kind == "observe" and _still_holds(one) for one in stretches)
    ]
    if not observed:
        return MappingProxyType({})
    walkable: networkx.DiGraph[PropositionId] = networkx.DiGraph()
    walkable.add_nodes_from(sorted(claims))
    walkable.add_edges_from((one.source, one.target) for one in arrows)
    each: dict[PropositionId, frozenset[PropositionId]] = {}
    for claim_id in sorted(observed):
        causes = networkx.ancestors(walkable, claim_id)
        reached = {claim_id} | networkx.descendants(walkable, claim_id) | causes
        for cause in causes:
            reached |= networkx.descendants(walkable, cause)
        each[claim_id] = frozenset(reached)
    return MappingProxyType(each)


def _evidence_about(
    reach: Mapping[PropositionId, frozenset[PropositionId]], claim_id: PropositionId
) -> tuple[PropositionId, ...]:
    """Name the observations that are evidence about one claim, in a settled order."""
    return tuple(observed for observed in sorted(reach) if claim_id in reach[observed])


def _warnings_about(
    graph: Graph, claims: Mapping[PropositionId, Proposition], days: int
) -> tuple[str, ...]:
    """Say, in plain sentences, what the reader should be told about this map.

    Args:
        graph: The map to read.
        claims: Every claim on it, by identifier.
        days: How long the window is.

    Returns:
        One sentence per thing worth saying, in a settled order.
    """
    said: list[str] = []
    named = dict(claims)
    for link in sorted(graph.links, key=lambda one: one.id):
        ends = f"from {_name_of(named, link.source)} to {_name_of(named, link.target)}"
        if abs(link.strength) > LOUD_STRENGTH:
            said.append(
                f"The arrow {ends} pushes by {link.strength}, which is past the point where a "
                "coin flip becomes a near certainty. The map is still legal; the number is "
                "worth a second look."
            )
    if days + 1 > SERIES_CAP:
        said.append(
            f"This map runs for {days} days, so each claim's series is drawn at {SERIES_CAP} "
            "evenly spaced points rather than one for every day. Every day a push fires or "
            "a claim is judged is worked out exactly; the days between are not needed."
        )
    return tuple(said)


# --- The two loops --------------------------------------------------------


@dataclass(frozen=True)
class _Sample:
    """What the two loops produced, before any of it is turned into a world."""

    priors: Mapping[PropositionId, Numbers]
    strengths: Mapping[LinkId, Numbers]
    likelihood: Mapping[PropositionId, Numbers]
    inner_spread: Mapping[PropositionId, Numbers]
    weights: Mapping[PropositionId, Numbers]
    survival: float


def _stream_key(identifier: str) -> int:
    """Turn one thing's identifier into a number, the same one on every machine.

    Used for a claim and for an arrow alike: each gets a stream of random numbers
    of its own, and this is what picks which stream.

    Python's own hashing is stirred differently in every process, which would make
    a world depend on when it was computed. This does not: the same identifier
    always gives the same number, today and next week, here and in a container.

    Args:
        identifier: The claim's or the arrow's identifier.

    Returns:
        A number standing for that identifier.
    """
    digest = hashlib.blake2b(identifier.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _standard_normal_quantile(share: Numbers) -> Numbers:
    """Turn "how far along a bell curve" into "how many standard deviations out".

    A published rational approximation (Peter Acklam's), accurate to about one part
    in a billion, which is millions of times finer than the two significant figures
    anything on screen ever shows. It is written out because the only library that
    ships this function is one this project deliberately does not depend on.

    Args:
        share: How far along the curve, strictly between 0 and 1.

    Returns:
        How many standard deviations out that is: 0 in the middle, about 1.28 at
        nine-tenths of the way along.
    """
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    edge = 0.02425

    u = numpy.clip(share, TINY, 1.0 - TINY)
    out = numpy.empty_like(u)

    low, high = u < edge, u > 1.0 - edge
    middle = ~(low | high)

    q = u[middle] - 0.5
    r = q * q
    out[middle] = (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )
    for side, tail in ((low, u[low]), (high, 1.0 - u[high])):
        q = numpy.sqrt(-2.0 * numpy.log(tail))
        value = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
        out[side] = value if side is low else -value
    return out


def _log_odds(likelihood: Numbers) -> Numbers:
    """Turn a likelihood into log-odds: the scale on which separate pushes add up."""
    kept = numpy.clip(likelihood, TINY, 1.0 - TINY)
    return numpy.log(kept / (1.0 - kept))


def _likelihood_of(log_odds: Numbers) -> Numbers:
    """Turn log-odds back into a likelihood between 0 and 1."""
    turned: Numbers = 1.0 / (1.0 + numpy.exp(-log_odds))
    return turned


def _draw_likelihood_of(log_odds: Draws) -> Draws:
    """Turn log-odds back into a likelihood, at the precision one draw is kept to.

    The same turn as `_likelihood_of`, written out again because the arrays inside
    the two loops carry seven digits rather than sixteen and the type checker is
    told which is which.
    """
    return numpy.asarray(1.0 / (1.0 + numpy.exp(-log_odds)), dtype=DRAWING)


def _fitted_halves(belief: Belief) -> tuple[float, float]:
    """Fit the two halves of a stated likelihood and its range, on the log-odds scale.

    A stated `{p, lo, hi}` is read as a bell curve on the log-odds scale with its
    two halves fitted separately: the middle at `p`, a tenth of the curve below
    `lo` and a tenth above `hi`. The halves are fitted apart because real elicited
    ranges are lopsided, and fitting on log-odds rather than on probability honours
    all three stated numbers exactly and can never leave 0 to 1.

    Args:
        belief: The stated likelihood with its range.

    Returns:
        How wide the curve is below the middle, and how wide above.
    """
    middle = float(_log_odds(numpy.array(belief.p)))
    bottom = float(_log_odds(numpy.array(belief.lo)))
    top = float(_log_odds(numpy.array(belief.hi)))
    return (
        max(0.0, (middle - bottom) / NINETIETH_PERCENTILE),
        max(0.0, (top - middle) / NINETIETH_PERCENTILE),
    )


def _version_priors(claim: Proposition, seed: int, versions: int) -> Numbers:
    """Draw one likelihood per version for one claim's prior.

    The draws are spread evenly over the curve rather than left to clump — a Latin
    hypercube, which here is one stratified column per claim. Each claim's column
    comes from the seed and the claim's own identifier and from nothing else, which
    is what makes a base world and a branch world share their versions: adding a
    claim to the map cannot shift the numbers drawn for any other.

    Args:
        claim: The claim whose prior is being drawn.
        seed: The one number every draw comes from.
        versions: How many versions to draw.

    Returns:
        One likelihood per version.
    """
    drawer = numpy.random.default_rng([seed, PARAMS_STREAM, _stream_key(claim.id)])
    strata = (drawer.permutation(versions) + drawer.random(versions)) / versions
    steps = _standard_normal_quantile(strata)
    below, above = _fitted_halves(claim.prior)
    middle = float(_log_odds(numpy.array(claim.prior.p)))
    return _likelihood_of(middle + steps * numpy.where(steps < 0.0, below, above))


def _version_strengths(
    arrow: Link, seed: int, versions: int, spreads: Mapping[Provenance, float]
) -> Numbers:
    """Draw one push per version for one arrow, as wide as where it came from says.

    The same stratified draw the priors get — spread evenly over the curve rather
    than left to clump — and, like theirs, the numbers come from the seed and the
    arrow's **own** identifier and from nothing else. So adding an arrow cannot
    shift what another arrow drew, and version 7 of a base world and version 7 of
    a branch world push exactly as hard as each other along every arrow the two
    maps share.

    The draw is on the log-odds scale, because that is the scale a push is already
    written in: a spread of four tenths is four tenths of a log-odds unit, whatever
    the push itself happens to be. A weakly-backed push can therefore come out the
    other way round in some versions, and that is the honest reading — *we do not
    know which way this one goes* is most of what `asserted` means.

    Args:
        arrow: The arrow whose push is being drawn.
        seed: The one number every draw comes from.
        versions: How many versions to draw.
        spreads: How wide each kind of arrow's push is drawn.

    Returns:
        One push per version.
    """
    drawer = numpy.random.default_rng([seed, STRENGTHS_STREAM, _stream_key(arrow.id)])
    strata = (drawer.permutation(versions) + drawer.random(versions)) / versions
    steps = _standard_normal_quantile(strata)
    drawn: Numbers = arrow.strength + steps * spreads[arrow.provenance]
    return drawn


def _draw(
    setup: _Setup,
    *,
    seed: int,
    versions: int,
    worlds: int,
    spreads: Mapping[Provenance, float],
) -> _Sample:
    """Run the two loops: every version of the map, and every world under each.

    Each claim is worked out causes-first, for every draw and every day at once.
    A claim whose value an edit fixed is that value while the fixing holds, and is
    sampled from its own likelihood otherwise. What is kept from each world is the
    **likelihood** the claim came out true with, not the coin flip that came out of
    it — free accuracy, because the number was already worked out.

    When something was observed, the worlds it did not happen in are thrown away
    and each version then counts by the share of its worlds that survived. That
    takes two passes over the map: which worlds survive is only known once every
    observed claim has been reached, and a claim worked out before then would
    otherwise be averaged over worlds that are about to be discarded.

    Args:
        setup: Everything chance has no say in.
        seed: The one number every draw comes from.
        versions: The outer loop.
        worlds: The inner loop.
        spreads: How wide each kind of arrow's push is drawn.

    Returns:
        What each version drew for each prior and for each arrow's push, what each
        version answered for each claim on each day, how much the worlds inside a
        version disagreed, how much each version counts, and what share of worlds
        survived.
    """
    priors = {
        claim_id: _version_priors(setup.claims[claim_id], seed, versions)
        for claim_id in setup.order
    }
    strengths = {
        arrow.id: _version_strengths(arrow, seed, versions, spreads)
        for arrows in setup.arrows_into.values()
        for arrow in arrows
    }
    coins = {
        claim_id: numpy.random.default_rng([seed, WORLDS_STREAM, _stream_key(claim_id)])
        .random((versions, worlds))
        .astype(DRAWING)
        for claim_id in setup.order
    }

    alive: Mapping[PropositionId, Flags] = {}
    if setup.observation_reach:
        _, _, alive = _one_pass(
            setup, priors, strengths, coins, versions, worlds, alive, reduce=False
        )
    likelihood, inner, _ = _one_pass(
        setup, priors, strengths, coins, versions, worlds, alive, reduce=True
    )

    # How much each version counts, **per claim**: the share of its worlds that
    # survived the observations that are evidence about that claim, and no others.
    # One pooled share would let an observation weigh a claim it says nothing about.
    counting: dict[PropositionId, Numbers] = {}
    survived_all = numpy.ones((versions, worlds), dtype=bool)
    for observed in sorted(alive):
        survived_all = survived_all & alive[observed]
    for claim_id in setup.order:
        about = _evidence_about(setup.observation_reach, claim_id)
        kept = _surviving_both(alive, about, versions, worlds).sum(axis=1)
        counting[claim_id] = kept.astype(numpy.float64) / worlds
    return _Sample(
        priors=priors,
        strengths=MappingProxyType(strengths),
        likelihood=likelihood,
        inner_spread=inner,
        weights=MappingProxyType(counting),
        survival=float(survived_all.sum()) / float(versions * worlds),
    )


def _one_pass(
    setup: _Setup,
    priors: Mapping[PropositionId, Numbers],
    strengths: Mapping[LinkId, Numbers],
    coins: Mapping[PropositionId, Draws],
    versions: int,
    worlds: int,
    alive: Mapping[PropositionId, Flags],
    *,
    reduce: bool,
) -> tuple[dict[PropositionId, Numbers], dict[PropositionId, Numbers], dict[PropositionId, Flags]]:
    """Walk every claim once, causes first, working out its likelihood in every draw.

    Args:
        setup: Everything chance has no say in.
        priors: What each version drew for each claim's prior.
        strengths: What each version drew for each arrow's push.
        coins: One number per claim per world, held the same on every day. It is
            also the same in a base world and a branch world, so the two can be
            compared draw by draw and the dice cancel out of the comparison.
        versions: The outer loop.
        worlds: The inner loop.
        alive: Which worlds are still consistent with what was observed.
        reduce: Whether to average each claim down to one number per version. The
            first of two passes does not, because it is only there to find out
            which worlds survive.

    Returns:
        Each claim's answer per version and day, how much the worlds inside a
        version disagreed, and which worlds survived.
    """
    points = len(setup.points)
    shape = (versions, worlds, points)
    truth: dict[PropositionId, Flags] = {}
    fired: dict[PropositionId, Flags] = {}
    answered: dict[PropositionId, Numbers] = {}
    spread: dict[PropositionId, Numbers] = {}
    surviving: dict[PropositionId, Flags] = dict(alive)

    for claim_id in setup.order:
        baseline = _log_odds(priors[claim_id]).astype(DRAWING)
        total = numpy.broadcast_to(baseline[:, None, None], shape).astype(DRAWING)
        for arrow in setup.arrows_into[claim_id]:
            # One push per version per day: each version drew its own strength for
            # this arrow, as wide as where the arrow came from says, and the shape
            # row says how much of that push has arrived on each day.
            push = (strengths[arrow.id][:, None] * setup.shape_rows[arrow.id][None, :]).astype(
                DRAWING
            )
            if arrow.mode == "sustain":
                total += push[:, None, :] * truth[arrow.source]
            else:
                total += push[:, None, :] * fired[arrow.source][:, :, None]
        answer = _draw_likelihood_of(total)
        # One number per claim per world, held the same on every day of the
        # window. A world is one coherent draw, and a claim that flickered true,
        # false and true again from one day to the next inside a single world
        # would be nobody's idea of a world; it would also make a sustaining
        # arrow's push flicker with it. So the day a claim becomes true is the
        # day its likelihood rises past this one number, and it stays true while
        # it does. The chapter does not settle this; the alternative — a fresh
        # number every day — is the only other reading and it is the noisy one.
        came_true = coins[claim_id][:, :, None] < answer

        starts = _point_of(setup.points, setup.settled[claim_id])
        for spell in setup.spells[claim_id]:
            if spell.kind == "observe" and _still_holds(spell):
                at = _point_of(setup.points, spell.starts)
                # This observation's own worlds, kept apart from every other
                # observation's. Pooling them is what let an observation in one
                # piece of a map move a claim in another.
                kept = came_true[:, :, at] == spell.value
                surviving[claim_id] = (
                    kept if claim_id not in surviving else surviving[claim_id] & kept
                )
        held, word = _fixed_days(setup, claim_id)
        if held.any():
            answer = numpy.where(held[None, None, :], word[None, None, :], answer)
            came_true = numpy.where(held[None, None, :], word[None, None, :] > 0.5, came_true)

        truth[claim_id] = came_true
        fired[claim_id] = came_true[:, :, starts]
        if reduce:
            # Read through the worlds that survived **the observations this claim
            # is evidence of**, and no others. A claim no observation is evidence
            # about is read off every world, which is both exact and what keeps a
            # coin flip somewhere else from moving a number nobody touched.
            about = _evidence_about(setup.observation_reach, claim_id)
            answered[claim_id], spread[claim_id] = _per_version(
                answer, _surviving_both(surviving, about, versions, worlds), bool(about)
            )

    return answered, spread, surviving


def _still_holds(spell: _Spell) -> bool:
    """Say whether a stretch of days is one this edit's word actually covers.

    A later edit on the same claim ends an earlier one's stretch, and where the
    later edit lands on the very same day the earlier stretch covers no day at all.
    **An observation no longer in force throws no world away**: the user said "this
    happened" and then said "suppose it did not", and the second word is the one in
    force. Discarding worlds for the first would be reading news the user has
    withdrawn — and it leaked, because the worlds an observation discards are how
    much every version it is evidence about counts.
    """
    return spell.ends is None or spell.ends > spell.starts


def _surviving_both(
    surviving: Mapping[PropositionId, Flags],
    about: Sequence[PropositionId],
    versions: int,
    worlds: int,
) -> Flags:
    """Which worlds survived **every** observation that is evidence about one claim.

    A claim two observations are both evidence about is read through the worlds
    that survived both of them: each one really is news about it, and a world that
    contradicts either is not a world this claim can be read in. A claim only one
    of them reaches is read through that one alone. A claim neither reaches is read
    through every world there is.

    Args:
        surviving: Which worlds survived each observation, by the claim observed.
        about: The observations that are evidence about the claim being read.
        versions: The outer loop.
        worlds: The inner loop.

    Returns:
        One flag per version per world.
    """
    kept = numpy.ones((versions, worlds), dtype=bool)
    for observed in about:
        kept = kept & surviving[observed]
    return kept


def _point_of(points: NDArray[numpy.int64], day: int) -> int:
    """Find where one day of the window sits among the days actually worked out.

    **Exact, and it has to be.** Every day the arithmetic reads by name — the day a
    claim's clock starts, so a one-off push fires then, and the day an observation
    speaks — is put on the grid when the grid is built, precisely so that this can
    never round. Rounding here to the next drawn day along is what once let the
    length of the window decide the timing of a push, and so let an edit at one end
    of a map move a claim at the other; see `_days_to_send` and `_prepare`.

    A day past the end of the window is read at the last one, which only a claim
    whose clock starts outside the window can be, and such a claim is not doing
    anything inside it.

    Args:
        points: The days worked out, in order.
        day: The day wanted.

    Returns:
        Where that day sits among them.
    """
    if day >= points[-1]:
        return len(points) - 1
    return int(numpy.searchsorted(points, max(0, day)))


def _fixed_days(setup: _Setup, claim_id: PropositionId) -> tuple[Flags, Draws]:
    """Say which of the worked-out days a fixed value holds on, and what it was fixed to.

    Each edit's word holds from its own day until the next edit on the same claim
    has something to say. A supposition also stops on the day something undermined
    it, after which the claim is worked out like any other — its own prior plus
    every live arrow, each arriving on its own delay — until that stretch runs out.
    An observation is never undermined: it is news, not a lever.

    Args:
        setup: Everything chance has no say in.
        claim_id: The claim.

    Returns:
        Which days a value holds on, and the value itself on each of them.
    """
    days = setup.points
    held = numpy.zeros(len(days), dtype=bool)
    word = numpy.zeros(len(days), dtype=DRAWING)
    for spell in setup.spells[claim_id]:
        stop = spell.undermined_on if spell.undermined_on is not None else spell.ends
        covered = days >= spell.starts
        if stop is not None:
            covered &= days < stop
        held |= covered
        word[covered] = 1.0 if spell.value else 0.0
    return held, word


def _per_version(answer: Draws, surviving: Flags, weighted: bool) -> tuple[Numbers, Numbers]:
    """Average each version's worlds down to one number per day, and say how much they differed.

    A claim an observation is evidence about is read off the surviving worlds only.
    A claim it is not evidence about — no chain of arrows either way, no shared
    cause — is read off every world, because for such a claim the observation
    changes nothing and reading a subset would only add noise.

    Args:
        answer: Every draw's likelihood, by version, world and day.
        surviving: Which worlds are still consistent with what was observed.
        weighted: Whether this claim is one the observation is evidence about.

    Returns:
        One number per version per day, and how much the worlds inside each version
        disagreed.
    """
    if not weighted:
        return (
            answer.mean(axis=1, dtype=numpy.float64),
            answer.var(axis=1, ddof=1, dtype=numpy.float64),
        )
    kept = surviving[:, :, None]
    counted = surviving.sum(axis=1)[:, None].astype(numpy.float64)
    safe = numpy.where(counted > 0.0, counted, 1.0)
    middle = (answer * kept).sum(axis=1, dtype=numpy.float64) / safe
    spread = ((answer - middle[:, None, :]) ** 2 * kept).sum(
        axis=1, dtype=numpy.float64
    ) / numpy.maximum(safe - 1.0, 1.0)
    return middle, spread


# --- Turning the sample into numbers a person reads ------------------------


def _weighted_mean(values: Numbers, weights: Numbers) -> Numbers:
    """Average one number per version, counting each version by how much it survived.

    **Added up along the versions, which is the axis laid out end to end**, so that
    the order the numbers are added in depends on how many versions there are and
    on nothing else. Adding along the other axis lets the array library pick its
    order by the shape of the block, and floating-point addition is not
    associative: the same sixteen numbers then total `11.689481994806576` in an
    array one day wide and `11.689481994806577` in a wider one. That is nothing a
    reader could see, and it is enough to stop two worlds of one map agreeing to
    the bit about a claim neither of them touched — which is the sharpest way there
    is to state locality, so it is worth one transpose to keep.
    """
    along_versions = numpy.ascontiguousarray(values.T)
    return (along_versions * weights[None, :]).sum(axis=1) / weights.sum()


def _weighted_percentiles(
    values: Numbers, weights: Numbers, shares: tuple[float, ...]
) -> tuple[Numbers, ...]:
    """Find the values a given share of the versions sit below, counting each by its weight.

    Written out rather than taken from a library because the library that has it is
    the dependency this project does without, and because a weighted percentile is
    a dozen lines. Several shares are asked for at once because putting the
    versions in order is the expensive part and doing it twice is waste.

    Args:
        values: One number per version, per day.
        weights: How much each version counts.
        shares: How far along, each from 0 to 1.

    Returns:
        One row of numbers per share asked for, a number per day.
    """
    order = numpy.argsort(values, axis=0)
    sorted_values = numpy.take_along_axis(values, order, axis=0)
    running = numpy.cumsum(weights[order], axis=0)
    running /= running[-1]
    found: list[Numbers] = []
    for share in shares:
        picked = (running >= share).argmax(axis=0)
        found.append(numpy.take_along_axis(sorted_values, picked[None, :], axis=0)[0])
    return tuple(found)


def _band(
    values: Numbers, spread: Numbers, weights: Numbers, worlds: int
) -> tuple[Numbers, Numbers, Numbers]:
    """Work out the likelihood and the range around it, with the coin-flip noise taken out.

    The spread we measure across versions is the spread we actually want *plus* the
    wobble of having run only a handful of worlds under each. Those two add, so the
    second is subtracted and the band shrunk by what is left — the law of total
    variance. A claim whose apparent spread was all coin flips then reports a band
    of no width rather than an imaginary one.

    Args:
        values: One number per version, per day.
        spread: How much the worlds inside each version disagreed.
        weights: How much each version counts, which must be the vector
            `Versions.counting_for` gives for this claim and nothing else. That is
            what makes the band and the number on the tile the same reading, and it
            is also what guarantees these weights are never all zeroes — the
            "nothing survived anywhere" fallback lives there, so there is no second
            copy of it here to drift from it.
        worlds: How many worlds ran under each version.

    Returns:
        The likelihood, the bottom of the range, and the top.
    """
    middle = _weighted_mean(values, weights)
    across = _weighted_mean((values - middle[None, :]) ** 2, weights)
    within = _weighted_mean(spread, weights) / worlds
    shrink = numpy.sqrt(
        numpy.clip(
            1.0 - numpy.divide(within, across, out=numpy.ones_like(across), where=across > 0.0),
            0.0,
            1.0,
        )
    )
    corrected = middle[None, :] + (values - middle[None, :]) * shrink[None, :]
    bottom, top = _weighted_percentiles(corrected, weights, (0.1, 0.9))
    return middle, numpy.minimum(bottom, middle), numpy.maximum(top, middle)


def _range_shares(
    setup: _Setup, sample: _Sample
) -> dict[PropositionId, dict[PropositionId, float]]:
    """Work out how much of each claim's band comes from not being sure of each prior.

    Sort the versions into groups by the number one prior drew, average each group's
    answer for the claim in question, and see how much of the claim's own spread
    those group averages explain. That share is what a later stack turns into
    "where would more homework pay?" — it is worked out here because the sample it
    comes from is thrown away otherwise.

    Args:
        setup: Everything chance has no say in.
        sample: What the two loops produced.

    Returns:
        For each claim, how much of its band each claim's prior explains.
    """
    order = list(setup.order)
    if not order:  # pragma: no cover - a map always has at least one claim
        return {}
    read = numpy.array([sample.likelihood[one][:, setup.read_at[one]] for one in order])
    middle = read.mean(axis=1)
    total = ((read - middle[:, None]) ** 2).mean(axis=1)
    groups = min(RANGE_BINS, read.shape[1])
    edges = numpy.linspace(0, read.shape[1], groups + 1).astype(int)[:-1]
    sizes = numpy.diff(numpy.append(edges, read.shape[1])).astype(numpy.float64)

    shares: dict[PropositionId, dict[PropositionId, float]] = {one: {} for one in order}
    for source in order:
        by_prior = numpy.argsort(sample.priors[source], kind="stable")
        grouped = numpy.add.reduceat(read[:, by_prior], edges, axis=1) / sizes[None, :]
        explained = ((grouped - middle[:, None]) ** 2 * sizes[None, :]).sum(axis=1) / read.shape[1]
        for index, target in enumerate(order):
            share = 0.0 if total[index] <= 0.0 else float(explained[index] / total[index])
            shares[target][source] = min(1.0, max(0.0, share))
    return shares


def _world_from(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    setup: _Setup,
    sample: _Sample,
    retractions: tuple[Retraction, ...],
    *,
    seed: int,
    versions: int,
    worlds: int,
) -> World:
    """Assemble the finished world: a number per claim, a series per claim, and the sentences.

    Args:
        graph: The map the branch's edits left behind.
        assignments: Every value those edits fixed, in the order they were made.
        setup: Everything chance had no say in.
        sample: What the two loops produced.
        retractions: Every supposition something undermined.
        seed: The one number every draw came from.
        versions: The outer loop.
        worlds: The inner loop.

    Returns:
        One world.
    """
    beliefs: dict[PropositionId, Belief] = {}
    series: dict[PropositionId, tuple[float, ...]] = {}
    drawn: dict[PropositionId, tuple[SeriesState, ...]] = {}
    # How much each version counts, asked of the one place that knows. A world's
    # own numbers and the difference between two worlds then count the versions
    # the same way by construction rather than by two copies of one line agreeing.
    behind = _versions_from(setup, sample)
    sent = _sent_days(setup)
    for claim_id in setup.order:
        counting = behind.counting_for(claim_id)
        middle, bottom, top = _band(
            sample.likelihood[claim_id], sample.inner_spread[claim_id], counting, worlds
        )
        read = setup.read_at[claim_id]
        beliefs[claim_id] = Belief(
            p=float(numpy.clip(middle[read], 0.0, 1.0)),
            lo=float(numpy.clip(bottom[read], 0.0, 1.0)),
            hi=float(numpy.clip(top[read], 0.0, 1.0)),
            owner="model",
        )
        series[claim_id] = tuple(float(middle[one]) for one in sent)
        drawn[claim_id] = tuple(setup.states[claim_id][one] for one in sent)

    said = list(setup.warnings)
    # **The warning is about a claim's reading, not about the map.** Each claim is
    # read through the worlds that survived the observations that are evidence
    # about *it*, so how thin that reading is differs from claim to claim: two
    # observations can each keep plenty of worlds while almost none survive both,
    # and a claim in a piece of the map neither of them touches is read off every
    # world and is perfectly well supported. Saying "x per cent of the worlds
    # survived" about the whole map would be true of no claim in particular.
    starved = sorted(
        (float(sample.weights[claim_id].mean()), claim_id)
        for claim_id in setup.order
        if _evidence_about(setup.observation_reach, claim_id)
        and float(sample.weights[claim_id].mean()) < LOWEST_SURVIVAL
    )
    if starved:
        thinnest, claim_id = starved[0]
        others = (
            ""
            if len(starved) == 1
            else f", and {len(starved) - 1} other claim{'' if len(starved) == 2 else 's'} "
            "{is_are} as thinly supported".format(is_are="is" if len(starved) == 2 else "are")
        )
        numbers = "that number" if len(starved) == 1 else "those numbers"
        said.append(
            f"Only {thinnest * 100:.1f} per cent of the simulated worlds match everything "
            f"observed about {_name_of(setup.claims, claim_id)}{others}, so the range on "
            f"{numbers} is unreliable — not just the number itself."
        )

    return World(
        base_id=graph.id,
        branch_id=None,
        seed=seed,
        versions=versions,
        worlds=worlds,
        day_zero=setup.day_zero,
        days=setup.days,
        series_days=tuple(int(setup.points[one]) for one in sent),
        graph=graph,
        assignments=assignments,
        retractions=retractions,
        beliefs=beliefs,
        series=series,
        states=drawn,
        conditionals={},
        range_shares=_range_shares(setup, sample),
        warnings=tuple(said),
    )
