"""Working the likelihoods through a map: what a world is, and how it is computed.

A branch is a list of edits; a world is what those edits do to the numbers. This
file is the arithmetic in between. It takes the map a fold left behind, the
values that fold fixed, a day to start from and a seed, and gives back one
`World`: a likelihood for every claim on the day that claim is judged, a
likelihood for every day in between, a named state for every one of those days,
and a plain sentence for anything the reader should be told.

**One likelihood per claim, computed once.** A claim's number is *the chance it
happens by its deadline* — or, for a claim that holds over a stretch of time,
*the chance it is still holding on its deadline*. There is one reading of the map
and no range around any number (decision records 0016 and 0028). What a number
carries is the arithmetic of the map itself; it says nothing about how sure
anybody is of the numbers that went in, because that was a second number per
claim that no reader could use and it has been cut.

**Four steps and nothing else.**

1. **Read the numbers a person stated.** Every claim's own chance and every
   arrow's push, exactly as the map states them.
2. **Work out when.** One pass over the map, causes before effects, turning those
   chances into rates and adding each cause's push into its target's rate
   (`forward.py`).
3. **Solve whether, exactly.** One elimination over the small yes/no tables the
   pass built (`solving.py`). No sampling, no iteration.
4. **Correct for what was seen.** Where an edit said *This happened*, worlds are
   drawn forward and weighted by how well they match, and the difference between
   the sampled answer and the answer the solve already knows is added back
   (`sampling.py`). One correction per claim.

**What this file must never do**

- Never draw a range. There is one reading of the map, and `lo`, `p` and `hi` are
  the same number until those two fields leave the wire.
- Never model a supposition as a large baseline the arrows argue with. While a
  supposition holds the claim is true, and the tile shows a word where a number
  would mislead.
- Never let a claim's line and the number on its tile disagree. A day of a series
  is the share of the claim's whole chance that has arrived by then times the
  solved number, so the line ends on the tile's own number exactly. `_lines_of`
  is where that is done and why.
- Never retract anything by calendar. Nothing on this product undermines a
  supposition: a claim that happened stays happened, and what a later event pushes
  back on is a *state*, which falls on its own terms (decision record 0017).
- No clock, no network, no global random state. Every random number comes from
  the one `seed` argument, so the same map, branch and seed give the same world
  on any machine.
- Never unroll a feedback arrow. A market feeding back on the world it measures is
  carried as data and set aside here exactly as the map's own loop check sets it
  aside; a later stack works it through over time.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Final, Literal

import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.belief import Belief, two_figures
from katalyst.domain.forward import Forward, forward_pass
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, LinkId, PropositionId
from katalyst.domain.link import Link
from katalyst.domain.patch import Assignment
from katalyst.domain.proposition import Proposition
from katalyst.domain.rates import (
    SLICES,
    Drawn,
    Pin,
    Window,
    clamped,
    stated_chance_with,
    window_of,
)
from katalyst.domain.sampling import sample_forward
from katalyst.domain.solving import ImpossibleObservation, all_marginals
from katalyst.domain.validity import _name_of

Numbers = NDArray[numpy.float64]
"""An array of ordinary numbers. Written down once because it appears everywhere below."""


SeriesState = Literal["sampled", "supposed"]
"""What a claim's day is, in one word.

`sampled` — the ordinary case: no supposition has ever touched this claim.
`supposed` — a supposition is holding; the claim is true and the tile shows a word
rather than a likelihood.

There were two more words once — `withdrawn` and `pushed` — for a supposition a
later edit had undermined. Nothing undermines a supposition any more (decision
record 0017): what a later event pushes back on is a state, and a state falls by
its own arithmetic rather than by a badge.
"""

ONE_VERSION: Final = 1
"""How many versions of the map the engine works out: one.

A *version* is one coherent set of the numbers a person stated. This engine works
out exactly one of them — the numbers as stated — and reports one likelihood per
claim (decision record 0028, Kent's row R48). The arrays underneath keep a version
axis all the same, running at length one, because a version enters the arithmetic
as a single number multiplying arrays built once: at length one the axis costs
nothing, and it keeps every shape below saying what each of its numbers is about.
"""

SAMPLED_WORLDS: Final = 50_000
"""How many worlds are drawn when something has been observed.

Nothing is thrown away: every one of them is kept and weighted by how well it
matches what was seen.
"""

NOTHING_ADDED: Mapping[LinkId, int] = MappingProxyType({})
"""What "nobody said which edit added which arrow" looks like: an empty, unchangeable map."""

LOUD_STRENGTH = 5.0
"""A push beyond this is roughly 1% to 99% on a coin flip, and is worth a second look."""

SERIES_CAP = 180
"""The most **evenly spaced** points a series is drawn at, however long the window is.

A cap on the evenly spaced points alone, and on both counts it is not a ceiling:
**every claim's resolve-by day is kept whatever the cap says**, because a tile's
headline is read on that day and it has to be a point of the line drawn beneath
it. A map with more than 180 claims judged on 180 different days therefore sends
one point per judged day and no more — more than this number, and every one of
them earning its place. See `_days_to_send`.

What it must never do is decide the *timing* of anything. It cannot: every claim
is worked out on its own window, cut into slices from its own resolve-by day, and
this number decides only where the finished line is read.
"""


def _push_as_written(strength: float) -> str:
    """Write how hard an arrow pushes, the way this product writes every push.

    One place after the point, and always with its sign, because a push's sign is
    half of what it says: `+0.9` takes the claim at the arrow's head toward coming
    true and `-2.4` takes it away. Both figures are printed even when the second is
    a nought, so `+2.0` does not read as a number somebody measured more loosely
    than its neighbours.

    This is deliberately **not** the rule for a likelihood. A likelihood runs from
    0 to 1 and is written `.40` or `<.01`; a push runs from minus infinity to plus
    infinity on the log-odds scale and has no such bounds, so sending one through
    the likelihood rule would print `>.99` for a push of 5.2 — a sentence that says
    the opposite of the truth. Two quantities, two rules, and each says what it
    means.

    Args:
        strength: How hard an arrow pushes, on the log-odds scale.

    Returns:
        The push as text: `+0.9`, `-2.4`, `+5.2`.
    """
    return f"{strength:+.1f}"


class World(BaseModel):
    """One finished answer: a map, the values its edits fixed, and every number worked through.

    A world is a **computed result, never a source of truth**. It can always be
    thrown away and rebuilt from three things — the base map, the branch and the
    seed — and if a stored world ever disagrees with what those three produce, the
    stored world is the one that is wrong.

    Every likelihood in `beliefs` is owned by the model and is read on that claim's
    own resolve-by day, which is the day the claim is judged and the date its tile
    already shows. `series` carries one likelihood per day so the way the chance
    arrives is visible rather than hidden, and `states` says, for each of those
    days, whether the number is the ordinary computed one or a supposition holding.

    **A claim whose supposition is holding reads 1 — exactly 1, or 0 where it was
    supposed false.** That number is there so that a chain of claims multiplied
    together has a factor for it, and for nothing else: **no surface may print
    it.** Every reader looks at `states` first and prints the word *Supposed* where
    the number would go, because "suppose this is true" answered with a likelihood
    is a tool arguing with the person using it.
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
        description=(
            "How many versions of the map were worked out. Always 1: one likelihood per "
            "claim, computed once. Kept on the wire, always the same number, until the "
            "browser round closes (decision record 0028; dated 2026-09-22)."
        )
    )
    worlds: int = Field(
        description=(
            "How many worlds ran inside each version. Always 0, meaning there is no inner "
            "loop at all. Kept on the wire, always the same number, until the browser "
            "round closes (decision record 0016; dated 2026-09-22)."
        )
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
    retractions: tuple[str, ...] = Field(
        description=(
            "Always empty. Nothing on this product undermines a supposition any more "
            "(decision record 0017): a claim that happened stays happened, and what a "
            "later event pushes back on is a state. Kept on the wire, always empty, until "
            "the browser round closes (dated 2026-09-22)."
        )
    )
    beliefs: Mapping[PropositionId, Belief] = Field(
        description=(
            "The model's likelihood for each claim, read on that claim's own resolve-by "
            "day. One number: `lo`, `p` and `hi` are all the same."
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
            "Always empty. It said how much of each claim's range came from not being "
            "sure of each claim's own stated number, and there is no range (decision "
            "record 0028). Kept on the wire, always empty, until the browser round closes "
            "(dated 2026-09-22)."
        ),
    )
    warnings: tuple[str, ...] = Field(
        default=(),
        description="Plain sentences the reader should see under the map.",
    )


def propagate(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    versions: int = ONE_VERSION,
    worlds: int = 0,
    introduced_by: Mapping[LinkId, int] = NOTHING_ADDED,
    slices: int = SLICES,
    sampled_worlds: int = SAMPLED_WORLDS,
) -> World:
    """Work every likelihood on a map through time, on the day each claim is judged.

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
        versions: **Accepted and ignored.** There is one version of the map and one
            likelihood per claim (decision record 0028). The argument stays so that
            callers written against the old engine keep working; it goes with the
            two empty fields when the browser round closes. Dated 2026-09-22.
        worlds: **Accepted and ignored.** There is no inner loop. The same dated
            note as `versions` above.
        introduced_by: **Accepted and ignored.** It named which edit added each
            arrow, so that a supposition something had undermined could name the
            edit responsible; nothing undermines a supposition any more (decision
            record 0017). The same dated note as `versions` above.
        slices: How many equal pieces to cut each claim's window into.
        sampled_worlds: How many worlds to draw where something has been observed.

    Returns:
        One world: a likelihood for every claim on the day it is judged, a
        likelihood and a named state for every day the series is drawn at — every
        day of the window until the window outruns the cap, and then the days
        `series_days` names — and a sentence for anything the reader should be
        told.
    """
    claims: Mapping[PropositionId, Proposition] = {one.id: one for one in graph.propositions}
    worked = _worked_out(
        graph,
        assignments,
        as_of=as_of,
        seed=seed,
        slices=slices,
        sampled_worlds=sampled_worlds,
    )
    window, drawn, pinned, forward = worked.window, worked.drawn, worked.pinned, worked.forward
    answers, refusals = worked.answers, worked.refusals

    sent = _days_to_send(claims, as_of, window.days)
    beliefs: dict[PropositionId, Belief] = {}
    series: dict[PropositionId, tuple[float, ...]] = {}
    named_days: dict[PropositionId, tuple[SeriesState, ...]] = {}
    for claim_id in forward.order:
        # One reading of the map, so the three numbers of a belief are one number.
        # Dated 2026-09-22, decision record 0028: `lo` and `hi` stay on the wire,
        # equal to `p`, until one follow-up after the browser round takes the two
        # fields off it. A field that is always equal to another field is a field
        # somebody will eventually believe, which is why they go together and soon.
        read = float(numpy.clip(answers[claim_id][0], 0.0, 1.0))
        beliefs[claim_id] = Belief(p=read, lo=read, hi=read, owner="model")
        held = pinned.get(claim_id)
        supposed = held is not None and held.kind == "do"
        lines = _lines_of(forward, claim_id, sent, _at_day_zero(held), answers[claim_id])
        series[claim_id] = tuple(float(one) for one in lines[0])
        named_days[claim_id] = (("supposed" if supposed else "sampled"),) * len(sent)

    said = [
        *_warnings_about(graph, claims, window.days),
        *_clamps_said_out_loud(forward, drawn, claims),
        *refusals,
    ]
    return World(
        base_id=graph.id,
        branch_id=None,
        seed=seed,
        # One version, no inner loop, nothing retracted, no range to take apart.
        # Four constants with one dated reason between them: records 0016, 0017 and
        # 0028, and they leave the wire together when the browser round closes.
        versions=ONE_VERSION,
        worlds=0,
        day_zero=as_of,
        days=window.days,
        series_days=tuple(int(one) for one in sent),
        graph=graph,
        assignments=assignments,
        retractions=(),
        beliefs=beliefs,
        series=series,
        states=named_days,
        conditionals={},
        range_shares={},
        warnings=tuple(said),
    )


# --- Everything the assembly owns -------------------------------------------


@dataclass(frozen=True)
class _WorkedOut:
    """Everything the core works out from a map, a branch and a seed."""

    window: Window
    drawn: Drawn
    pinned: Mapping[PropositionId, Pin]
    forward: Forward
    answers: Mapping[PropositionId, Numbers]
    refusals: tuple[str, ...]


def _worked_out(
    graph: Graph,
    assignments: tuple[Assignment, ...],
    *,
    as_of: date,
    seed: int,
    slices: int,
    sampled_worlds: int,
) -> _WorkedOut:
    """Read the numbers, work out when, and solve whether — the whole of the arithmetic.

    Args:
        graph: The map a fold left behind.
        assignments: Every value that fold fixed, in order.
        as_of: Day zero — the day the window starts on.
        seed: The one number every random draw comes from.
        slices: How many equal pieces to cut each claim's window into.
        sampled_worlds: How many worlds to draw where something was observed.

    Returns:
        The window, the stated numbers, what each edit fixed, the finished pass,
        every claim's solved number, and any sentence the reader is owed.
    """
    claims: Mapping[PropositionId, Proposition] = {one.id: one for one in graph.propositions}
    ordinary = _ordinary_arrows(graph, claims)
    # A feedback arrow is carried as data and set aside, exactly as the map's own
    # loop check sets it aside, so the pass below is handed a map it can walk
    # causes-before-effects. The world still reports the map it was given.
    walkable = graph.model_copy(update={"links": ordinary})

    window = window_of(graph, as_of, slices=slices)
    drawn = _as_stated(claims, ordinary)
    pinned = _pinned_from(assignments, claims)
    forward = forward_pass(walkable, window, drawn, pinned=pinned)
    answers, refusals = _answers_from(
        forward, pinned, window=window, seed=seed, worlds=sampled_worlds
    )
    return _WorkedOut(
        window=window,
        drawn=drawn,
        pinned=pinned,
        forward=forward,
        answers=answers,
        refusals=refusals,
    )


def _as_stated(claims: Mapping[PropositionId, Proposition], arrows: Sequence[Link]) -> Drawn:
    """Read every number a person stated, exactly as the map states it.

    **Nothing is drawn here any more.** The engine used to run two thousand
    versions of the map, each one taking every claim's likelihood from that claim's
    own stated range and every arrow's push from a spread read off where the arrow
    came from. Kent cut all of it on 2026-09-22 (decision record 0028): one
    likelihood per claim, computed once, and no range anywhere. So a claim's number
    is its stated `p` and an arrow's is its stated `strength`, each as a single row.

    **The bridge is what is left, and it is temporary.** An arrow's stated push is
    in log-odds, and the core wants *the chance this claim reaches its deadline
    with that one cause on and no other*. `stated_chance_with` converts one to the
    other, and its own docstring says plainly that this is a conversion rather than
    an identity. The one shape freeze asks the model for the number directly and
    the bridge goes with it.

    Args:
        claims: Every claim on the map, by identifier.
        arrows: The arrows the arithmetic uses, feedback arrows already set aside.

    Returns:
        Every claim's own stated chance and the chance with each one cause on, each
        as one row.
    """
    own = {
        claim_id: numpy.array([one.prior.p], dtype=numpy.float64)
        for claim_id, one in claims.items()
    }
    return Drawn(
        versions=ONE_VERSION,
        own_chance=own,
        with_this_cause={
            arrow.id: stated_chance_with(
                own[arrow.target], numpy.array([arrow.strength], dtype=numpy.float64)
            )
            for arrow in arrows
        },
    )


def _pinned_from(
    assignments: Sequence[Assignment], claims: Mapping[PropositionId, Proposition]
) -> dict[PropositionId, Pin]:
    """Read the values a branch's edits fixed as one pin per claim.

    **The last edit on a claim is the one in force**, which is what `propagate`
    promises its caller. A claim's number is about its own deadline rather than
    about a day, so what is in force is a single value and there is no calendar of
    stretches to keep.

    An edit naming a claim the map does not carry is passed over: the fold already
    answered for it.

    Args:
        assignments: Every value the edits fixed, in the order they were made.
        claims: Every claim on the map, by identifier.

    Returns:
        Claim -> the value fixed on it and which verb fixed it.
    """
    return {
        one.target: Pin(value=one.value, kind=one.kind)
        for one in assignments
        if one.target in claims
    }


def _answers_from(
    forward: Forward,
    pinned: Mapping[PropositionId, Pin],
    *,
    window: Window,
    seed: int,
    worlds: int,
) -> tuple[Mapping[PropositionId, Numbers], tuple[str, ...]]:
    """Work out every claim's number, and say so plainly if the news cannot have happened.

    Three cases. With nothing reported, the exact solve is the whole answer. With
    something reported, the exact solve answers **whether** and a weighted sample of
    worlds corrects it for the fact that learning a claim happened moves *when* its
    causes happened as well as whether they did.

    **A claim the evidence cannot reach keeps its exact answer, untouched.** The
    solve makes locality a theorem — a claim joined to the evidence by no chain of
    arrows and sharing no cause with it comes out **bit for bit** as it would have
    with nothing reported at all — and a sampled correction, however small, would
    throw that away. So the map is solved a second time with the report set aside,
    and a correction is added **only where those two answers differ**. That test is
    the promise itself rather than a stand-in for it: the numbers compared are the
    very numbers the promise is about.

    **And when nothing the map can produce agrees with what was reported**, there is
    no answer to condition on. It answers with **the map's own numbers, worked out
    as though nothing had been reported**, and says exactly that in a sentence
    naming the claims. Nothing raises, and nothing shows a number that is not a
    number.

    Args:
        forward: The finished forward pass.
        pinned: The value fixed on each claim, and which verb fixed it.
        window: The map's window, which the sample draws its days on.
        seed: The one number every draw comes from.
        worlds: How many worlds to draw where something was reported.

    Returns:
        Claim -> its number, and any sentence the reader must be told.
    """
    reported = tuple(one for one in forward.order if _pin_kind(pinned, one) == "observe")
    if not reported:
        return all_marginals(forward, pinned), ()
    levers = {one: pin for one, pin in pinned.items() if pin.kind == "do"}
    with_it_set_aside = all_marginals(forward, levers)
    try:
        exact = all_marginals(forward, pinned)
        corrected = sample_forward(
            forward,
            pinned,
            window=window,
            version=0,
            seed=seed,
            worlds=worlds,
            exact=exact,
        ).correction
    except ImpossibleObservation:
        return with_it_set_aside, (_nothing_agrees_with(reported),)
    return (
        {
            one: row
            if numpy.array_equal(row, with_it_set_aside[one])
            else numpy.clip(row + corrected[one], 0.0, 1.0)
            for one, row in exact.items()
        },
        (),
    )


def _pin_kind(pinned: Mapping[PropositionId, Pin], claim_id: PropositionId) -> str | None:
    """Say which verb fixed a claim's value, or nothing at all if no edit fixed it."""
    pin = pinned.get(claim_id)
    return None if pin is None else pin.kind


def _nothing_agrees_with(reported: Sequence[PropositionId]) -> str:
    """Say, in one sentence, that no world this map can produce matches what was reported.

    Args:
        reported: The claims *This happened* was used on, in the map's own order.

    Returns:
        One sentence for the reader, naming them.
    """
    which = ", ".join(reported)
    return (
        f"Nothing this map can produce agrees with what was reported about {which}, so "
        "there is no world left to read a number off. Every number below is the map's "
        "own, worked out as though nothing had been reported — the report itself has "
        "moved nothing."
    )


def _at_day_zero(held: Pin | None) -> float:
    """What a claim's line reads on the first day of the window.

    Nought for an ordinary claim: nothing has happened yet. **A claim a supposition
    holds reads that supposition**, day zero included, because what the reader typed
    is a hard fact from the moment they typed it rather than something that arrives
    partway through the first slice. A claim something was reported about reads
    nought like any other: an observation is news about the whole window, not a value
    fixed on a day.

    Args:
        held: The value an edit fixed on the claim, if one did.

    Returns:
        The claim's number on day zero.
    """
    if held is None or held.kind != "do":
        return 0.0
    return float(held.value)


def _lines_of(
    forward: Forward,
    claim_id: PropositionId,
    sent: NDArray[numpy.int64],
    at_day_zero: float,
    answer: Numbers,
) -> Numbers:
    """Read one claim's chance of having happened at each day the reader is sent.

    **A shape from the pass, a size from the solve.** The forward pass leaves, for
    every claim, the chance it is holding at the end of each slice of **its own**
    window. Read at the days the reader is given — straight-lining between slice
    ends, and holding the last value past the claim's own deadline, because an event
    that has happened never un-happens and a claim is not judged twice — that curve
    says **what share** of the claim's whole chance has arrived by each day. The
    exact solve says **how much** that whole chance is. A day of the line is the
    share times the whole.

    **Why the two have to be married here.** The pass and the solve answer the same
    question by different routes, and on a claim reached two ways at once they do not
    give the same number: the pass averages each cause's timing one cause at a time,
    so it treats two causes' arrival days as independent even when both descend from
    one claim, and the solve does not. Left as they were, a tile read `.51` above a
    chart that ended at `.50` — two numbers for one claim on one day, different at the
    two figures the product prints, with no edit in force
    (`plans/analysis/2026-09-22-review-05-core.md`, must-fix 1). Dividing the curve by
    its own last value throws away exactly the quantity the two disagree about and
    keeps the only thing the pass is the authority on, which is the *order* the chance
    arrives in. The last day then reads the solved number **exactly**: the share on
    that day is a number divided by itself, which is one.

    A claim whose whole chance is nought has no shape to speak of — its curve is flat
    along the bottom — and its solved number is nought too, because a claim the timing
    model can never bring about is a claim no solve over those same tables can either.
    Such a line is left on the floor rather than dividing nought by nought.

    The line is held between nought and one. That binds on a **state** and only a
    state: a state's curve can fall as well as rise, so its share of the whole can
    read above one on a day it was more likely to be holding than it is on its
    deadline. It never binds on the last day, which is the solved number itself.

    Args:
        forward: The finished forward pass.
        claim_id: The claim whose line is wanted.
        sent: The days of the window the reader is given.
        at_day_zero: What the claim reads on the first day of the window.
        answer: The claim's solved number — the very number the tile is read off, so
            that the line and the tile cannot part.

    Returns:
        `(1, days sent)` the chance the claim has happened by each of them, ending
        on `answer`.
    """
    curves = forward.times[claim_id].holding
    edges = forward.shapes[claim_id].edges
    days = sent.astype(numpy.float64)
    start = numpy.full((curves.shape[0], 1), at_day_zero)
    whole = numpy.concatenate([start, curves], axis=1)
    arrived = numpy.array([numpy.interp(days, edges, row) for row in whole])
    by_the_end = arrived[:, [-1]]
    share = numpy.divide(arrived, by_the_end, out=numpy.zeros_like(arrived), where=by_the_end > 0.0)
    lines: Numbers = numpy.clip(share * answer[:, None], 0.0, 1.0)
    return lines


def _clamps_said_out_loud(
    forward: Forward, drawn: Drawn, claims: Mapping[PropositionId, Proposition]
) -> tuple[str, ...]:
    """Name every arrow that could not hold its claim back as far as its number asks.

    An arrow whose push covers only part of a claim's window cannot hold that claim
    to the number stated for it, even with the claim's rate suppressed entirely
    while the cause is on. The claim then comes out **above** the stated number, and
    the reader is told which arrow, what it asked for and what it delivered, rather
    than being shown a number that quietly disagrees with the arrow beside it.

    In the same shape as the warning about a loud push, and sorted by the arrow's
    own identifier for the same reason: two runs of one map say the same things in
    the same order.

    Args:
        forward: The finished forward pass, whose shapes and rates this reads.
        drawn: The stated numbers, for what each arrow asked of its claim.
        claims: Every claim on the map, by identifier.

    Returns:
        One sentence per arrow that fell short, in arrow order.
    """
    named = dict(claims)
    found: list[tuple[LinkId, str]] = []
    for claim_id in forward.order:
        shapes = forward.shapes[claim_id]
        asked_for = {
            position: drawn.with_this_cause[arrow_id]
            for position, arrow_id in enumerate(shapes.arrows)
        }
        for clamp in clamped(shapes, forward.rates[claim_id], asked_for):
            found.append(
                (
                    clamp.arrow,
                    f"The arrow {clamp.arrow} into {_name_of(named, claim_id)} is stated to "
                    f"hold that claim to {two_figures(clamp.asked)} by its deadline, and the "
                    f"most it can hold it to is {two_figures(clamp.delivered)}, because its "
                    "push covers only part of the window. The map is still legal; the "
                    "claim's own number comes out above the one stated for the arrow.",
                )
            )
    return tuple(said for _arrow, said in sorted(found))


# --- Reading the map itself --------------------------------------------------


def _ordinary_arrows(graph: Graph, claims: Mapping[PropositionId, Proposition]) -> tuple[Link, ...]:
    """List the arrows the arithmetic actually uses, **in the order the map carries them**.

    A feedback arrow — a market changing the world it is measuring — is left out:
    it is carried as data in this version and worked through by a later stack, the
    same way the map's own loop check leaves it out. An arrow with an end that is
    not on the map is left out too; it already has its own complaint.

    The order is the map's own, and that order means something: folding a branch
    appends each `insert`'s arrows after the ones already there, so an arrow's
    place on the map is the order it arrived in.

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


def _day_index(when: date, day_zero: date, cap: int) -> int:
    """Turn a claim's resolve-by date into a whole number of days after day zero.

    Nothing before day zero and nothing past the end of the window: a claim judged
    on a day already gone is judged on the first day this engine works out, and one
    judged past the map's own last day is read on that last day.

    Args:
        when: The date.
        day_zero: The day the window starts on.
        cap: The last day of the window.

    Returns:
        The day's number, counting from zero.
    """
    return min(max(0, (when - day_zero).days), cap)


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

    These days decide only where a finished line is **read**. They decided when a
    push fired once, and that was a defect: thinning them made the day a push
    landed on depend on how long the window was, so an edit at one end of a map
    could re-time a claim at the other end that nothing connected it to. Measured
    before it was separated: an inserted claim that stretched a window from 31 days
    to 365 moved a claim in a wholly separate piece of the map by `.096`. Every
    claim is now worked out on its own window, cut into slices from its own
    resolve-by day, so the cap cannot reach the arithmetic at all.

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
                f"The arrow {ends} pushes by {_push_as_written(link.strength)}, which is past "
                "the point where a coin flip becomes a near certainty. The map is still "
                "legal; the number is worth a second look."
            )
    if days + 1 > SERIES_CAP:
        said.append(
            f"This map runs for {days} days, so each claim's series is drawn at {SERIES_CAP} "
            "evenly spaced points rather than one for every day. Every claim is still "
            "worked out on its own window, cut into slices from its own resolve-by day; "
            "these are the days the line is drawn at."
        )
    return tuple(said)
