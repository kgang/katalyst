"""What moved between two worlds, and what one claim at a time would move.

The user supposes the strait reopens, adds a strike the next day, and asks the
only question that matters: *what changed?* This file answers it. It takes two
finished worlds — the same untouched map, the same seed, two branches folded on —
and gives back a short ordered list: this ending went from `.50` to `.42`, this
claim is out of the picture, this one did not move, and one sentence anybody can
read aloud.

Two functions live here.

* `diff` compares two worlds claim by claim and ranks the endings that moved.
* `sensitivity` flips each claim in one world, one at a time, and records what
  each flip does to every ending. Nothing on screen reads it yet; it is written
  now because the engine it needs is written now.

**Why a difference is read off two worlds and never off two maps.** Both worlds
were built from one base map and one seed, so every difference between them can
be traced to an edit the user made. A difference reconstructed afterwards by
matching two maps could not tell "the user supposed this" from "the numbers came
out differently this run", and a number nobody can trace to an input is the one
state this product refuses to show.

What this file must never do
----------------------------
- Never decide that something moved by asking whether two ranges overlap. The
  ranges answer a different question — how sure we are of each world's own
  number — and two wide ranges can overlap while the difference between them is
  tight and all one way. The move is read off the **paired** difference: version
  7 of one world against version 7 of the other, which cancels the elicitation
  noise because both versions were built from the same numbers.
- Never count the versions one way for the number and another way for the
  direction. **The direction is read with the same weights the number was read
  with.** When something was observed, a version counts by the share of its
  worlds that survived, so a version with no surviving world counts for nothing
  in the number and must not vote on the direction either. Let it vote and a
  version that contributed nothing to either number argues about which way they
  moved.
- Never fold how wide a range is, or how much the versions agreed, into the
  rank. "This moved a lot", "we are unsure how much" and "we are sure which way"
  are three separate facts a trader weighs separately, and one blended score
  hides which of them is talking.
- Never call a small number `killed`. `killed` means the claim was forced false,
  and nothing else. A claim whose likelihood fell to `.02` moved a long way; it
  is `shifted`, and saying it was cut would tell the user their argument was
  severed when it was merely losing.
- Never write the summary as free prose. It is one of two fixed sentences with
  the blanks filled in from numbers already in the answer, so the sentence and
  the list beside it cannot drift apart, and neither needs a language model.
- No clock, no network, no global random state. Everything here is worked out
  from the two worlds it was handed and the seed they both carry.
"""

import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from heapq import heappop, heappush
from types import MappingProxyType
from typing import Literal

import numpy
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.branch import Branch
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, PropositionId
from katalyst.domain.intervention import Do
from katalyst.domain.link import Link, Provenance
from katalyst.domain.patch import apply

# `_band` is borrowed from the file that works the likelihoods through, so that
# the width this file reports on a given day and the width a tile shows on that
# day are produced by the very same arithmetic. The noise correction inside it is
# subtle enough that a second copy would drift, and the two numbers disagreeing
# would be a state no reader could account for.
from katalyst.domain.propagation import (
    Numbers,
    Versions,
    World,
    _band,
    propagate,
    versions_of,
)
from katalyst.domain.proposition import Proposition

# `_quoted` is borrowed from the file that decides whether a map is valid, so
# that a name this product puts in quotation marks looks the same wherever it
# appears. Two copies of that wording would drift apart and the user would be
# reading two slightly different voices from one product.
from katalyst.domain.validity import TERMINAL_KINDS, Violation, _quoted

ClaimState = Literal["unchanged", "shifted", "added", "killed"]
"""What happened to one claim between two worlds, in one word.

`unchanged` — it is in both worlds and it fails either half of the test below.
`shifted` — it is in both, it moved by at least 0.005 on its own resolve-by day,
and it moved the same way in at least 90% of the versions of the map.
`added` — it is in the second world and not in the first.
`killed` — it is in both, and the second world forces it false. Never "its number
got small", and never "nothing reaches it from the hypothesis any more", which is
a fact about the path rather than about the claim.
"""

MOVED_AT_LEAST = 0.005
"""How far a claim has to move before the move counts as a move at all."""

AGREEING_AT_LEAST = 0.90
"""How many of the versions have to move the same way before the move counts."""

SWEEP_VERSIONS = 250
"""The outer loop a one-at-a-time sweep runs at.

A sweep is one whole run of the engine per claim, which at the shipped budget
would be sixteen thousand worlds per flip. A quarter of the versions is enough to
say which way each flip pushes each ending, and every row says so.
"""

SWEEP_WORLDS = 8
"""The inner loop a one-at-a-time sweep runs at, which is the shipped one."""

PROVENANCE_WEIGHT: Mapping[Provenance, float] = MappingProxyType(
    {
        "documented": 1.0,
        "historical": 0.9,
        "market_implied": 0.9,
        "argued": 0.6,
        "user": 0.6,
        "simulated": 0.5,
        "asserted": 0.3,
    }
)
"""How well-backed each kind of arrow is, as a number between 0 and 1.

An arrow's `provenance` is a receipt our own pipeline writes, never something a
model claims for itself: `documented` means the retrieval step attached a real
source, `historical` that the number came from a study of past cases,
`market_implied` that it was read off a live price, `argued` that a mechanism was
stated and nothing was fetched to back it, `user` that a person typed it,
`simulated` that a probe produced it, and `asserted` that the sentence is a story
rather than a mechanism. This turns that receipt into the second of the ranking's
two factors.
"""

NO_ARROW_TO_WEAKEN = 1.0
"""What the second factor is worth when no arrow stands between an edit and an ending.

A user who supposes an ending itself has moved it with no arrow in between, so
there is no weak arrow for the ranking to discount — the move is exactly as
well-founded as the user's own supposition, which is the strongest the second
factor goes.
"""


class ClaimDiff(BaseModel):
    """What happened to one claim between two worlds, with the numbers behind it.

    `before` and `after` are read on **the claim's own resolve-by day** — the day
    the claim is judged, which every claim has, and the day its tile's number
    already refers to. So a claim's state is about the number the reader is
    looking at, and not about some other day.

    `agreement` is carried on every claim both worlds hold, not only the ones
    that moved, so a reader — or a test — can check the rule that decided the
    state without recomputing anything. It is read with the same weights the two
    numbers above were read with, so a version that counted for nothing in them
    does not vote on which way they moved.

    A claim still supposed on its own resolve-by day carries the stored 1 (or 0,
    where it was supposed false) so that the arithmetic stays ordinary. **No
    surface prints that number**: every reader looks at the world's `states`
    first and writes the word *Supposed* where the number would go.
    """

    model_config = ConfigDict(frozen=True)

    target: PropositionId = Field(description="The claim this is about.")
    state: ClaimState = Field(description="What happened to it, in one word.")
    before: float | None = Field(
        description=(
            "The first world's likelihood for it, on the claim's own resolve-by day. "
            "Nothing at all when the second world added the claim, because there is no "
            "first-world number to read."
        )
    )
    after: float | None = Field(
        description=(
            "The second world's likelihood for it, on the same day. Nothing at all in "
            "the one case the product cannot produce: a claim the first world holds and "
            "the second does not."
        )
    )
    delta: float | None = Field(
        description=(
            "The move, signed: the second world's number minus the first world's. "
            "Nothing at all when one of the two worlds has no number to read."
        )
    )
    agreement: float | None = Field(
        description=(
            "The share of versions of the map that moved the same way as the move above, "
            "each version counted by as much as it counted for the two numbers. Nothing at "
            "all when only one of the two worlds holds the claim. On screen this column is "
            "headed 'same direction'."
        )
    )
    moved_only_by_reweighting: bool = Field(
        description=(
            "True when the move above came from nothing but the observation changing how "
            "much each version counts: the claim is in both worlds, it moved by at least "
            "0.005, and not one version that counts moved at all. Only an observation can "
            "produce it, and the Inspector says so in one sentence."
        )
    )


class DeltaRow(BaseModel):
    """One ending that moved, with everything a reader needs to weigh the move.

    A row is read on the **day of largest divergence**, not on the claim's own
    resolve-by day, because a change that shows up for a fortnight and then
    unwinds is the thing a trader acts on — and on this product's own worked
    example reading a row on its distant resolve-by day shows about two thirds of
    the move and calls it the answer.

    `range_width` and `agreement` are **columns, never factors**. They answer two
    different questions — how unsure are we of this number, and how sure are we of
    its direction — and a trader weighs them separately from how big the move is.
    Multiplying either into the rank would bury exactly the wide claims that are
    worth researching, and would hide which of the three facts is talking.
    """

    model_config = ConfigDict(frozen=True)

    target: PropositionId = Field(description="The ending that moved.")
    before: float = Field(description="The first world's likelihood on the day below.")
    after: float = Field(description="The second world's likelihood on the day below.")
    peak_delta: float = Field(
        description="The move on that day, signed: the largest the two worlds ever differ."
    )
    at_day: date = Field(
        description=(
            "The day the two worlds are furthest apart. Always one of the days the series "
            "actually carries, which matters once a window longer than 180 days has been "
            "drawn at fewer points."
        )
    )
    range_width: float = Field(
        description=(
            "How wide the second world's own range on this claim is on that day — the same "
            "width its tile shows, so the list and the tile can never disagree about how "
            "firm a number is. On screen this column is headed 'how firm'."
        )
    )
    agreement: float = Field(
        description=(
            "The share of versions of the map that moved the same way on that day, each "
            "version counted by as much as it counted for the two numbers. A column, never "
            "a factor. On screen it is headed 'same direction'."
        )
    )
    rank: float = Field(
        description=(
            "How big the move is times how well-backed the route behind it is: the size of "
            "the move, times the weakest arrow on the best-backed route from a differing "
            "edit's subject to this ending. Two factors, and only two."
        )
    )


class Diff(BaseModel):
    """The whole difference between two worlds: every claim, the endings that moved, one sentence.

    Frozen, like everything in this layer, so a stored difference is a record
    rather than a working buffer. It can always be thrown away and rebuilt from
    the base map, the two branches and the seed, and if a stored one ever
    disagrees with what those produce, the stored one is the one that is wrong.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(description="The one map both worlds were built from.")
    branch_a: BranchId | None = Field(
        description="The first world's branch. Nothing at all means the base world."
    )
    branch_b: BranchId | None = Field(
        description="The second world's branch. Nothing at all means the base world."
    )
    seed: int = Field(description="The one seed both worlds were built from.")
    versions: int = Field(description="The outer loop both worlds ran: versions of the map.")
    worlds: int = Field(description="The inner loop both worlds ran: worlds per version.")
    claims: Mapping[PropositionId, ClaimDiff] = Field(
        description="Every claim either world holds, exactly once."
    )
    rows: tuple[DeltaRow, ...] = Field(
        description=(
            "The endings that moved, largest rank first. An ending is a claim that names "
            "an instrument or one that says why there is nothing to trade."
        )
    )
    summary: str = Field(
        description=(
            "One of two fixed sentences with its blanks filled in from the numbers above. "
            "Never written by a language model, and never free prose."
        )
    )
    warnings: tuple[str, ...] = Field(
        description="Plain sentences either world wanted the reader to see, each said once."
    )


class SensitivityRow(BaseModel):
    """What flipping one claim does to every ending, and the budget that answer came from.

    The rows come back **unranked**. The ranking is per ending and is applied by
    whoever reads them, because which direction hurts depends on the trade: the
    flip that damages a long position helps a short one, and this file has no idea
    which trade is being run.
    """

    model_config = ConfigDict(frozen=True)

    flipped: PropositionId = Field(description="The claim that was flipped.")
    to: bool = Field(
        description=(
            "What it was flipped to: the opposite of whichever way it more often comes out "
            "in the world being swept."
        )
    )
    deltas: Mapping[PropositionId, float] = Field(
        description="The signed change the flip made to each ending."
    )
    versions: int = Field(
        description=(
            "The outer loop this row was produced at. A sweep is one whole run per claim, so "
            "it runs at a reduced budget and says so, and nobody compares a swept number "
            "with a full-budget one without noticing."
        )
    )
    worlds: int = Field(description="The inner loop this row was produced at.")


def diff(world_a: World, world_b: World, *, edit_in_words: str) -> Diff | list[Violation]:
    """Say what moved between two worlds, and rank the endings that moved.

    Pure: no clock, no network, no global random state. The two worlds carry the
    three things they were built from, so the version-by-version numbers behind
    each of them are recomputed here rather than carried on the wire — millions of
    numbers no browser should ever be sent.

    Both worlds must have been built from the same map, the same seed and the same
    two loop sizes. Anything else is refused with a plain sentence, because a
    difference computed across two seeds is the user's change plus a wash of
    sampling noise, and a number nobody can trace to an edit is exactly the state
    this product refuses to show.

    Args:
        world_a: The world to compare from — usually the base world.
        world_b: The world to compare to — usually a branch folded onto the same
            map.
        edit_in_words: What to call the change in the summary sentence: the second
            branch's own name, or the words of its single edit when it holds only
            one. It is filled in from the branch or the edit and is never written
            fresh, which is why it is handed in rather than invented here — a
            world carries the identifier of its branch and not the name the user
            gave it.

    Returns:
        One difference: every claim either world holds with what happened to it,
        the endings that moved in ranked order, one fixed sentence, and every
        warning either world carried. Or a list of violations saying why the two
        worlds cannot be compared.
    """
    refused = _worlds_do_not_match(world_a, world_b)
    if refused:
        return refused

    behind_a, behind_b = versions_of(world_a), versions_of(world_b)
    days, where_a, where_b = _days_both_worlds_drew(world_a, world_b)
    claims = _states(world_a, world_b, behind_a, behind_b)
    rows = _ranked_endings(world_a, world_b, behind_a, behind_b, claims, days, where_a, where_b)
    named = {one.id: one for one in world_b.graph.propositions}

    return Diff(
        base_id=world_b.base_id,
        branch_a=world_a.branch_id,
        branch_b=world_b.branch_id,
        seed=world_b.seed,
        versions=world_b.versions,
        worlds=world_b.worlds,
        claims=claims,
        rows=rows,
        summary=_summary(edit_in_words, rows, claims, named),
        warnings=_said_once(world_a.warnings, world_b.warnings),
    )


def sensitivity(
    world: World, *, versions: int = SWEEP_VERSIONS, worlds: int = SWEEP_WORLDS
) -> tuple[SensitivityRow, ...]:
    """Flip each claim in turn and record what the flip does to every ending.

    One claim at a time, to the opposite of whichever way it more often comes out
    in this world, with the map worked through again from scratch each time. That
    is one whole run of the engine per claim, so the sweep runs at a **reduced
    budget** — 250 versions of the map rather than 2 000 — and **every row says
    which budget produced it**, so nobody lays a swept number beside a
    full-budget one without noticing.

    The world it starts from is worked out again at that same reduced budget, so
    that the difference each row reports is the flip and nothing else. Comparing a
    reduced-budget flip against a full-budget starting point would report part of
    the budget change as an effect.

    Nothing on screen reads this yet. It is written now because the engine it
    needs is written now, and bolting it on later would mean a second pass over
    the same arithmetic.

    Args:
        world: The world to sweep. Its map, the values its edits fixed, its day
            zero and its seed are all read from it.
        versions: The outer loop to sweep at. The default is the reduced budget.
        worlds: The inner loop to sweep at. The default is the shipped one.

    Returns:
        One row per claim on the map, in the map's own order, each naming the
        claim it flipped, what it flipped it to, the signed change on every
        ending, and the budget it was produced at. Unranked, on purpose.
    """
    endings = tuple(one.id for one in world.graph.propositions if one.kind in TERMINAL_KINDS)
    # Which edit added each arrow that ever undermined a supposition. A world
    # already knows: it carries one retraction per supposition that ended, and
    # each of those names both the arrow and the edit. So a sweep can work the
    # same map through again without being handed the branch a second time.
    told = {one.by_link: one.by for one in world.retractions}
    budget = {"versions": versions, "worlds": worlds}

    start = propagate(
        world.graph,
        world.assignments,
        as_of=world.day_zero,
        seed=world.seed,
        introduced_by=told,
        **budget,
    )

    swept: list[SensitivityRow] = []
    for claim in world.graph.propositions:
        # The opposite of whichever way it more often comes out **in the world
        # handed in**, which is the world the reader is looking at, rather than in
        # the reduced-budget run below it. A claim sitting exactly on the fence
        # comes out neither way more often, so it is flipped false — as good an
        # answer as its mirror, and always the same one.
        to = bool(world.beliefs[claim.id].p < 0.5)
        flip = Branch(
            id="sweep",
            label="One claim flipped, to see what it moves",
            interventions=(Do(target=claim.id, value=to, at=None),),
        )
        folded = apply(world.graph, flip, world.assignments)
        if isinstance(folded, list):  # pragma: no cover
            # Unreachable: the only thing a supposition can be refused for is
            # naming a claim that is not on the map, and this one was read off
            # the map a line ago. Kept so that a wrong assumption here leaves the
            # claim out of the sweep rather than crashing it.
            continue
        left_behind, fixed = folded
        flipped = propagate(
            left_behind,
            fixed,
            as_of=world.day_zero,
            seed=world.seed,
            introduced_by=told,
            **budget,
        )
        swept.append(
            SensitivityRow(
                flipped=claim.id,
                to=to,
                deltas={one: flipped.beliefs[one].p - start.beliefs[one].p for one in endings},
                versions=versions,
                worlds=worlds,
            )
        )
    return tuple(swept)


# --- Refusing a comparison that cannot mean anything -----------------------


def _worlds_do_not_match(world_a: World, world_b: World) -> list[Violation]:
    """List every reason these two worlds cannot be compared, or nothing at all.

    A difference is only meaningful when both worlds were built from the same raw
    material: the same untouched map, the same seed, and the same two loop sizes.
    Then version 7 of one and version 7 of the other were built from the same
    underlying numbers and differ only by the edit. Break any of those and every
    difference is the user's change plus a wash of sampling noise.

    There is no repair. Rebuilding one of the worlds to match the other would
    answer a question nobody asked, with a number nobody could trace.

    Every one of these carries the code `worlds_not_comparable`, which is its own
    code rather than one borrowed from the four that refuse an *edit*. Nothing
    here is anybody's edit: the two worlds are each perfectly good on their own,
    and what cannot be done is setting them side by side. A code has to mean what
    it says, or the interface reading it is reading a guess.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.

    Returns:
        One violation per mismatch, naming the map both worlds should have come
        from, or an empty list when the two agree.
    """
    disagreements = (
        (
            world_a.base_id != world_b.base_id,
            "These two worlds were built from different maps, so there is nothing to "
            "compare. A difference is only meaningful between two branches of one "
            "untouched map.",
        ),
        (
            world_a.seed != world_b.seed,
            "These two worlds were built from different seeds, so the numbers underneath "
            "them were never held fixed. Every difference between them would be the edit "
            "plus a wash of sampling noise, with no way to tell the two apart.",
        ),
        (
            world_a.versions != world_b.versions,
            "These two worlds tried a different number of versions of the map, so there "
            "is no version of one to set against the matching version of the other.",
        ),
        (
            world_a.worlds != world_b.worlds,
            "These two worlds ran a different number of worlds under each version of the "
            "map, so the two are not measured on the same footing.",
        ),
    )
    return [
        Violation(code="worlds_not_comparable", subject=world_b.base_id, message=said)
        for wrong, said in disagreements
        if wrong
    ]


# --- What happened to each claim -------------------------------------------


def _days_both_worlds_drew(
    world_a: World, world_b: World
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Find the days both worlds drew, and where each day sits in each world's own series.

    The two are almost always the same days. They can differ by a day or two when
    a branch adds a claim whose own resolve-by day joins the points a long window
    is drawn at — a window past 180 days is drawn at fewer, unevenly spaced days,
    and every claim's resolve-by day is always kept among them. Comparing the days
    they share is every day either of them would show side by side.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.

    Returns:
        The days both drew, in order, and the position of each of those days in
        the first world's series and in the second world's.
    """
    in_a = {day: index for index, day in enumerate(world_a.series_days)}
    in_b = {day: index for index, day in enumerate(world_b.series_days)}
    shared = tuple(day for day in world_b.series_days if day in in_a)
    return shared, tuple(in_a[day] for day in shared), tuple(in_b[day] for day in shared)


def _read_on(world: World, claim: Proposition) -> int:
    """Find where a claim's own resolve-by day sits among the days its series carries.

    That day is the day the claim is judged, and it is the day its tile's number is
    read on, so it is the day this file reads a claim's state on. It is always one
    of the days the series carries: a window longer than 180 days is drawn at fewer
    points, and every claim's resolve-by day is kept among them precisely so that a
    tile's number is always a point of the line drawn beneath it.

    Args:
        world: The world to read.
        claim: The claim whose day is wanted.

    Returns:
        The position of that day in the world's list of drawn days.
    """
    day = min(max(0, (claim.resolution.by - world.day_zero).days), world.days)
    return min(int(numpy.searchsorted(world.series_days, day)), len(world.series_days) - 1)


def _counting_for(behind_a: Versions, behind_b: Versions, claim_id: PropositionId) -> Numbers:
    """Say how much each version of the map counts when one claim's move is read.

    **One rule: the direction is read with the same weights the number was read
    with.** A world reads a claim's number off every version equally — unless an
    observation is evidence about that claim, in which case each version counts by
    the share of its worlds that survived what was observed. The two worlds of a
    difference can each answer that differently, so a version counts for the move
    by **the smaller of the two weights it carried**: a version can only speak
    about a difference as far as it counted in both numbers. A version with no
    surviving world therefore counts for nothing and does not vote.

    Three cases fall out of that one sentence, and none of them is a special case.
    Only the second world observed something: the version weights that world read
    the claim with. Both observed something: the smaller of the two. The claim is
    one the observation is not evidence about — it is joined to what was observed
    by no chain of arrows and shares no cause with it — so both worlds read it off
    every world equally, and every version counts the same here too.

    Under every edit that is not an observation neither world weights anything, so
    every version counts 1 and nothing this file reports can move by a bit.

    Args:
        behind_a: The version-by-version numbers behind the first world.
        behind_b: The same behind the second.
        claim_id: The claim whose move is being read.

    Returns:
        How much each version counts, one number per version.
    """
    in_a = (
        behind_a.weights if claim_id in behind_a.reweighted else numpy.ones_like(behind_a.weights)
    )
    in_b = (
        behind_b.weights if claim_id in behind_b.reweighted else numpy.ones_like(behind_b.weights)
    )
    together: Numbers = numpy.minimum(in_a, in_b)
    # Nothing at all survived what was observed, anywhere. Then every version
    # counts the same again — which is exactly what the band does in the same
    # corner, so the number and its direction stay read the same way. The world
    # carries a loud warning saying the reader is looking at the map rather than
    # at an answer.
    if together.sum() <= 0.0:
        return numpy.ones_like(together)
    return together


def _agreement_on(before: Numbers, after: Numbers, move: float, counting: Numbers) -> float:
    """Say what share of the versions of the map moved the way the reported move says.

    Subtract the first world's version *k* from the second world's version *k*, for
    every version. Because the stream that picks the versions never depends on the
    branch, both versions were built from the same underlying numbers, so the
    elicitation noise cancels and what is left is the edit. This counts how many of
    those paired differences point the same way as the move being reported, **each
    version counted by as much as it counted for the two numbers** — which is what
    `_counting_for` works out, and is why a version with no surviving world says
    nothing here.

    A claim that did not move at all in any version that counts comes out at 0
    unless the move is itself nothing: no paired difference points the reported
    way, because none of them points any way at all. That is the claim an
    observation moved through the version weights alone, and `_states` names it.

    Args:
        before: The first world's answer for one claim on one day, per version.
        after: The second world's answer for the same claim and day, per version.
        move: The move being reported, whose direction the versions are counted
            against.
        counting: How much each version counts, one number per version.

    Returns:
        The share of the counted versions that moved that way, between 0 and 1.
    """
    paired = after - before
    agreeing = numpy.sign(paired) == numpy.sign(move)
    return float((counting * agreeing).sum() / counting.sum())


def _moved_only_by_reweighting(
    before: Numbers, after: Numbers, move: float, counting: Numbers
) -> bool:
    """Say whether a claim's whole move came from how much each version counts.

    True when the claim moved far enough for the move to count at all and **not one
    version that counts moved by so much as a bit**: every paired difference among
    them is exactly zero. Then the two worlds' version-by-version answers are the
    same numbers, and the only thing left that can have moved the reported number is
    how much each of those versions counts.

    Only an observation can produce it. Under every other edit both worlds count
    every version the same, so identical version-by-version answers give identical
    numbers and the move is exactly nothing, which is below the floor.

    The claim it happens to is a claim with **no causes** — the hypothesis, usually.
    Inside one version such a claim is its own prior in every world, so throwing
    worlds away cannot change what that version says about it, and only the version
    weights are left to move it.

    Args:
        before: The first world's answer for one claim on one day, per version.
        after: The second world's answer for the same claim and day, per version.
        move: The move being reported.
        counting: How much each version counts, one number per version.

    Returns:
        True when the move is at least the floor and no counted version moved.
    """
    if abs(move) < MOVED_AT_LEAST:
        return False
    return not bool(numpy.any((after != before) & (counting > 0.0)))


def _forced_false_in(world: World, claim_id: PropositionId) -> bool:
    """Say whether the last word any edit had on this claim fixed it false.

    `killed` means forced false, full stop — by a supposition or by an
    observation, the two verbs that fix a value. A later edit overrides an earlier
    one, so the last assignment on the claim is the one in force.

    Args:
        world: The world to read.
        claim_id: The claim.

    Returns:
        True when the claim's last assignment fixed it false.
    """
    said = [one for one in world.assignments if one.target == claim_id]
    return bool(said) and not said[-1].value


def _states(
    world_a: World,
    world_b: World,
    behind_a: Versions,
    behind_b: Versions,
) -> dict[PropositionId, ClaimDiff]:
    """Work out what happened to every claim either world holds.

    Four checks, in order, and the first that matches wins: added, then killed,
    then shifted, then unchanged. Each claim is read on **its own resolve-by day**
    — the day it is judged, and the day its tile's number already refers to.

    `shifted` needs **both** halves: the claim moved by at least 0.005, and it
    moved the same way in at least 90% of the versions of the map. Reading the
    second half off whether the two ranges overlap would be badly wrong — on this
    product's own worked example two ranges overlap across two fifths of their
    width while 99.9% of versions move the same way, so overlap would report "no
    change" about the clearest change on the map.

    Each claim's direction is read with the same weights its two numbers were read
    with, so a version an observation left with no surviving world does not vote.
    A claim whose whole move came from those weights — every version that counts
    says exactly the same thing in both worlds — keeps whichever of the four words
    it had and says so in one field of its own, which the Inspector turns into one
    sentence.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.
        behind_a: The version-by-version numbers behind the first world.
        behind_b: The same behind the second.

    Returns:
        One entry per claim either world holds, by identifier.
    """
    in_a = {one.id: one for one in world_a.graph.propositions}
    in_b = {one.id: one for one in world_b.graph.propositions}
    found: dict[PropositionId, ClaimDiff] = {}

    for claim_id in sorted(set(in_a) | set(in_b)):
        if claim_id not in in_a:
            found[claim_id] = ClaimDiff(
                target=claim_id,
                state="added",
                before=None,
                after=world_b.beliefs[claim_id].p,
                delta=None,
                agreement=None,
                moved_only_by_reweighting=False,
            )
            continue
        if claim_id not in in_b:
            # A claim the first world holds and the second does not. The product
            # cannot produce this — there is no delete, and "this is out of the
            # picture" is said by forcing a claim false — but two branches that
            # forked apart could. Nothing in the second world moved it, because
            # there is nothing there to move, so it reads unchanged with no
            # second number beside it.
            found[claim_id] = ClaimDiff(
                target=claim_id,
                state="unchanged",
                before=world_a.beliefs[claim_id].p,
                after=None,
                delta=None,
                agreement=None,
                moved_only_by_reweighting=False,
            )
            continue

        before = world_a.beliefs[claim_id].p
        after = world_b.beliefs[claim_id].p
        move = after - before
        each_version = behind_a.likelihood[claim_id][:, _read_on(world_a, in_a[claim_id])]
        each_version_after = behind_b.likelihood[claim_id][:, _read_on(world_b, in_b[claim_id])]
        counting = _counting_for(behind_a, behind_b, claim_id)
        agreement = _agreement_on(each_version, each_version_after, move, counting)
        state: ClaimState = "unchanged"
        if _forced_false_in(world_b, claim_id):
            state = "killed"
        elif abs(move) >= MOVED_AT_LEAST and agreement >= AGREEING_AT_LEAST:
            state = "shifted"
        found[claim_id] = ClaimDiff(
            target=claim_id,
            state=state,
            before=before,
            after=after,
            delta=move,
            agreement=agreement,
            moved_only_by_reweighting=_moved_only_by_reweighting(
                each_version, each_version_after, move, counting
            ),
        )
    return found


# --- Which route a move travelled along, and how well-backed it is ---------


def _subjects_that_differ(
    world_a: World, world_b: World
) -> tuple[frozenset[PropositionId], frozenset[PropositionId]]:
    """Name the claims the two worlds' edits part company over, and which were observed.

    A world does not carry the branch that made it; it carries what that branch
    left behind. That is enough: the six edits can each change exactly one of four
    things, and all four are visible here. A `do` or an `observe` fixes a value, so
    it shows up as an assignment one world has and the other does not. An `insert`
    adds a claim. A `retune` changes one arrow's push. A `believe` writes the
    user's own number on one claim.

    An observation is named separately because it is the one edit allowed to move
    a claim **upstream** of its subject: throwing away the worlds it did not happen
    in changes what the survivors say about the claim's causes as much as about
    what it causes. So a route out of an observed claim is allowed to climb before
    it descends, exactly as far as that edit's reach allows.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.

    Returns:
        Every claim an edit of one world and not the other works from, and the
        ones among them that an observation named.
    """
    fixed_a = {(one.target, one.value, one.at, one.kind) for one in world_a.assignments}
    fixed_b = {(one.target, one.value, one.at, one.kind) for one in world_b.assignments}
    differing = fixed_a ^ fixed_b
    subjects = {one[0] for one in differing}
    observed = {one[0] for one in differing if one[3] == "observe"}

    claims_a = {one.id: one for one in world_a.graph.propositions}
    claims_b = {one.id: one for one in world_b.graph.propositions}
    for claim_id in set(claims_a) ^ set(claims_b):
        subjects.add(claim_id)
    for claim_id in set(claims_a) & set(claims_b):
        if claims_a[claim_id].beliefs.user != claims_b[claim_id].beliefs.user:
            subjects.add(claim_id)

    arrows_a = {one.id: one for one in world_a.graph.links}
    arrows_b = {one.id: one for one in world_b.graph.links}
    for arrow_id in set(arrows_a) | set(arrows_b):
        here, there = arrows_a.get(arrow_id), arrows_b.get(arrow_id)
        if here is not None and there is not None and here.strength == there.strength:
            continue
        # A retune works from the claim the arrow points at, because that is the
        # earliest thing a change to the arrow can reach.
        subjects.add((here or there).target)  # type: ignore[union-attr]

    return frozenset(subjects), frozenset(observed)


def _ordinary_arrows(graph: Graph) -> tuple[Link, ...]:
    """List the arrows a change is allowed to travel along.

    A feedback arrow — a market changing the world it is measuring — is left out,
    exactly as the map's own loop check and the engine's own arithmetic leave it
    out: nothing is worked through one in this version, so nothing an edit does can
    travel along it. An arrow with an end that is not on the map is left out too,
    because a claim that does not exist cannot carry a change.

    This is the same map the affected set is read over, which is what keeps the
    route behind a ranking and the claims an edit is allowed to move in step. The
    two change together, on the day a later stack works a feedback arrow through
    time.

    Args:
        graph: The map to read.

    Returns:
        The ordinary arrows, in the order the map carries them.
    """
    present = {one.id for one in graph.propositions}
    return tuple(
        one
        for one in graph.links
        if not one.reflexive and one.source in present and one.target in present
    )


def _best_backed_routes(
    graph: Graph, subjects: frozenset[PropositionId], observed: frozenset[PropositionId]
) -> dict[PropositionId, float]:
    """Find, for each claim, the strongest weak arrow any route from an edit reaches it by.

    Over every route from any of the subjects to a claim, take the one whose
    **weakest** arrow is strongest. That is the widest bottleneck: the road with
    the highest low bridge rather than the shortest one. A change that could have
    reached an ending along a well-backed route is ranked by that route, whichever
    edit started it, because that route is the best case the reader is entitled to.

    A route out of an observed claim may climb against the arrows first and then
    descend, once — that is exactly the reach an observation has, and the two rules
    are the same rule. Every other edit's routes simply follow the arrows.

    Routes are compared by their weakest arrow alone, so two routes that are
    equally well-backed give the same answer and the search need not choose
    between them. The interface's path bar, which draws one of them, breaks that
    tie by taking the shorter route and then the one whose first differing arrow
    comes earlier in the map's own list.

    Args:
        graph: The map the routes run over — the one the second world's edits left
            behind.
        subjects: The claims the edits work from.
        observed: Which of those an observation named, and may therefore climb
            from.

    Returns:
        For each claim a route reaches, how much its best-backed route's weakest
        arrow is worth. A claim that is itself a subject is worth the most a route
        can be worth, because no arrow stands between the edit and it.
    """
    arrows = _ordinary_arrows(graph)
    onward: dict[PropositionId, list[tuple[PropositionId, float]]] = {}
    backward: dict[PropositionId, list[tuple[PropositionId, float]]] = {}
    for claim in graph.propositions:
        onward[claim.id], backward[claim.id] = [], []
    for arrow in arrows:
        onward[arrow.source].append((arrow.target, PROVENANCE_WEIGHT[arrow.provenance]))
        backward[arrow.target].append((arrow.source, PROVENANCE_WEIGHT[arrow.provenance]))

    # Two states per claim, because a route out of an observed claim has two
    # halves: climbing against the arrows, and then running with them. Dropping
    # from the first half to the second is free and can happen anywhere, and there
    # is no way back, which is what stops a route from zigzagging.
    best: dict[tuple[PropositionId, bool], float] = {}
    waiting: list[tuple[float, PropositionId, bool]] = []
    for subject in sorted(subjects):
        if subject not in onward:
            continue
        climbing = subject in observed
        best[(subject, climbing)] = math.inf
        heappush(waiting, (-math.inf, subject, climbing))

    while waiting:
        reached, here, climbing = heappop(waiting)
        width = -reached
        steps = [
            ((there, climbing), min(width, worth))
            for there, worth in (backward if climbing else onward)[here]
        ]
        if climbing:
            steps.append(((here, False), width))
        for state, along in steps:
            if along > best.get(state, -1.0):
                best[state] = along
                heappush(waiting, (-along, state[0], state[1]))

    widest: dict[PropositionId, float] = {}
    for (claim_id, _), width in best.items():
        widest[claim_id] = max(widest.get(claim_id, 0.0), min(NO_ARROW_TO_WEAKEN, width))
    return widest


# --- The endings that moved, ranked ----------------------------------------


def _ranked_endings(
    world_a: World,
    world_b: World,
    behind_a: Versions,
    behind_b: Versions,
    claims: Mapping[PropositionId, ClaimDiff],
    days: Sequence[int],
    where_a: Sequence[int],
    where_b: Sequence[int],
) -> tuple[DeltaRow, ...]:
    """Build one row per ending that moved, read on the day the two worlds are furthest apart.

    An ending is a claim that names an instrument, or one that says why there is
    nothing to trade. Only endings that came out `shifted` get a row; ordering is
    by rank, largest first, and ties are broken by identifier so that the same
    difference always lists them the same way.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.
        behind_a: The version-by-version numbers behind the first world.
        behind_b: The same behind the second.
        claims: What happened to each claim.
        days: The days both worlds drew.
        where_a: Where each of those days sits in the first world's series.
        where_b: Where each sits in the second world's.

    Returns:
        The rows, largest rank first.
    """
    subjects, observed = _subjects_that_differ(world_a, world_b)
    widest = _best_backed_routes(world_b.graph, subjects, observed)
    rows: list[DeltaRow] = []

    for claim in world_b.graph.propositions:
        if claim.kind not in TERMINAL_KINDS or claims[claim.id].state != "shifted":
            continue
        before = numpy.array([world_a.series[claim.id][one] for one in where_a])
        after = numpy.array([world_b.series[claim.id][one] for one in where_b])
        gap = after - before
        at = int(numpy.argmax(numpy.abs(gap)))
        column = where_b[at]
        peak = float(gap[at])
        rows.append(
            DeltaRow(
                target=claim.id,
                before=float(before[at]),
                after=float(after[at]),
                peak_delta=peak,
                at_day=world_b.day_zero + timedelta(days=int(days[at])),
                range_width=_width_of_the_band(world_b, behind_b, claim.id, column),
                agreement=_agreement_on(
                    behind_a.likelihood[claim.id][:, where_a[at]],
                    behind_b.likelihood[claim.id][:, column],
                    peak,
                    _counting_for(behind_a, behind_b, claim.id),
                ),
                rank=abs(peak) * widest.get(claim.id, 0.0),
            )
        )
    return tuple(sorted(rows, key=lambda one: (-one.rank, one.target)))


def _width_of_the_band(
    world: World, behind: Versions, claim_id: PropositionId, column: int
) -> float:
    """Work out how wide one claim's range is on one day of the window.

    A world carries its range only on each claim's own resolve-by day, because that
    is the day the tile reads. A change list reads a different day — the day the
    two worlds are furthest apart — so the range for that day is worked out again
    here, from the same version-by-version numbers the world itself was built from
    and through the same arithmetic, which is what stops the list and the tile ever
    disagreeing about how firm a number is.

    Args:
        world: The world whose range is wanted.
        behind: The version-by-version numbers behind it.
        claim_id: The claim.
        column: Which of the drawn days to read.

    Returns:
        The distance between the bottom and the top of the range, on that day.
    """
    counting = behind.weights if claim_id in behind.reweighted else numpy.ones_like(behind.weights)
    _, bottom, top = _band(
        behind.likelihood[claim_id][:, [column]],
        behind.inner_spread[claim_id][:, [column]],
        counting,
        world.worlds,
    )
    return float(numpy.clip(top[0], 0.0, 1.0) - numpy.clip(bottom[0], 0.0, 1.0))


# --- The one sentence beside the list --------------------------------------


def _two_figures(likelihood: float) -> str:
    """Write a likelihood the way this product writes every likelihood.

    Two significant figures, with the nought before the point dropped, so `.50`
    and `.42` and `.060` — both figures always printed, because dropping a
    trailing nought would claim less precision than we have.

    **Never a certainty.** Rounding to two figures turns `.995` into `1.0` and
    nothing at all into `.0`, and both are claims nobody on this map is entitled
    to make: one says the thing cannot fail, the other that it cannot happen. So
    those print as `>.99` and `<.01`. The upper guard catches everything from
    `.995` up, including 1 itself. The lower one is rarer than it looks: two
    figures keeps two digits however small the number gets, so `.0035` prints
    `.0035` and a billionth prints `.0000000010`, and the only value that prints
    as `<.01` is nothing at all.

    **Never scientific notation.** A sentence that reads *"moves this claim from
    `>.99` to `1.0e-09`"* is not a sentence anybody can read aloud, and asking
    Python for two significant figures directly produces exactly that below a ten
    thousandth. So the rounding is done on the number's own decimal digits: the
    shortest decimal that reads back as this exact number, its point shifted by
    counting rather than by multiplying, rounded half-up, and written out with as
    many noughts after the point as it takes. That is also what stops `.995`
    printing `.99` — a computer stores it as `0.99499999999999999556`, so asking
    for two figures directly gives a number under the guard, and the sentence
    would print the one thing this rule forbids.

    **This rule is written twice and the two must move together.** The browser
    writes it as `toTwoFigures` in `frontend/src/components/BeliefChip.tsx`, and
    this function says the same thing for every input it can be given, carry
    cases included. Change one and change the other in the same pull request, or
    the same number reads two ways on one screen. Where the lower guard should
    *begin* — whether a likelihood under `.01` ought to print `<.01` rather than
    its own two figures — is a question for Kent and is deliberately not settled
    here; whatever he says lands in both places at once.

    Args:
        likelihood: The number, between 0 and 1.

    Returns:
        The number as it is written on screen: `.35`, or `<.01`, or `>.99`.
    """
    if not math.isfinite(likelihood) or likelihood <= 0.0:
        return "<.01"
    if likelihood >= 1.0:
        return ">.99"
    # The shortest decimal that reads back as this exact number, and where its
    # point sits: `.995` becomes the digits 995 with its leading digit at the
    # first place after the point.
    shortest = Decimal(repr(likelihood))
    place = shortest.adjusted()
    # The two figures, as a whole number from 10 to 99. Shifting the point by
    # counting places rather than by multiplying is what keeps `.995` at exactly
    # 99.5 rather than a hair under it, so it rounds up the way a reader would.
    figures = int(shortest.scaleb(1 - place).to_integral_value(rounding=ROUND_HALF_UP))
    if figures >= 100:
        # Rounding up carried into the next place: `.0999` is `.10`, not `.100`.
        figures, place = 10, place + 1
    if place >= 0:
        return ">.99"
    return f".{'0' * (-place - 1)}{figures}"


def _without_full_stop(claim: str) -> str:
    """Give a claim's own words with the full stop it ends in removed.

    The sentence around it supplies its own, and a claim quoted mid-sentence with
    two full stops in a row reads as a typing mistake rather than as a quotation.
    """
    return " ".join(claim.split()).rstrip(".")


def _summary(
    edit_in_words: str,
    rows: Sequence[DeltaRow],
    claims: Mapping[PropositionId, ClaimDiff],
    named: Mapping[PropositionId, Proposition],
) -> str:
    """Fill in one of two fixed sentences from numbers that are already in the answer.

    Two sentences, because there are two things that can have happened. When
    something at an ending moved, the sentence names the biggest, best-backed one
    and the day it moved on. When nothing at an ending moved, it says so — after a
    `believe`, whose number is not pushed through the map, or after a `retune`
    whose effect lands below the floor. *You changed something and nothing at the
    endings moved* is a real answer, and an empty list with no sentence beside it
    reads as a bug.

    Neither sentence is written by a language model. Free prose would be a fourth
    place for a number to come from, with nothing to trace it to, and it would
    eventually disagree with the list sitting beside it.

    Args:
        edit_in_words: What to call the change: the branch's own name, or the words
            of its single edit.
        rows: The endings that moved, largest rank first.
        claims: What happened to each claim.
        named: Every claim on the second world's map, by identifier, for its words.

    Returns:
        The sentence, with every blank filled in.
    """
    untouched = sum(1 for one in claims.values() if one.state == "unchanged")
    counted = f"{untouched} {'claim' if untouched == 1 else 'claims'}"
    called = _quoted(edit_in_words)
    if not rows:
        return f"{called} moves no ending and leaves {counted} untouched."
    top = rows[0]
    return (
        f"{called} moves {_without_full_stop(named[top.target].claim)} from "
        f"{_two_figures(top.before)} to {_two_figures(top.after)} by "
        f"{top.at_day.isoformat()} and leaves {counted} untouched."
    )


def _said_once(first: Sequence[str], second: Sequence[str]) -> tuple[str, ...]:
    """Join the two worlds' warnings, keeping the order and saying nothing twice.

    Both worlds are built from one map, so most of what either wants the reader to
    know it wants twice. A reader told the same thing twice reasonably wonders
    what the difference between the two was.
    """
    kept: list[str] = []
    for said in (*first, *second):
        if said not in kept:
            kept.append(said)
    return tuple(kept)
