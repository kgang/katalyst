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
- Never decide that something moved by anything but the move. A claim is
  `shifted` when the second world's number is at least `0.005` away from the
  first world's on the claim's own resolve-by day, and on nothing else. There
  used to be a second half to that test — did at least nine versions in ten of
  the map move the same way — and it went with the versions (decision record
  0028, Kent's row R48): there is one reading of the map now, so a share of the
  versions is a share of one thing.
- Never fold anything but the size of the move and the backing behind it into
  the rank. "This moved a lot" and "the route it travelled is well-backed" are
  the two factors, and there are only two.
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
from heapq import heappop, heappush
from types import MappingProxyType
from typing import Literal

import numpy
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.belief import two_figures
from katalyst.domain.branch import Branch
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, PropositionId
from katalyst.domain.intervention import Do
from katalyst.domain.link import Link, Provenance
from katalyst.domain.patch import apply
from katalyst.domain.propagation import World, propagate
from katalyst.domain.proposition import Proposition

# `_quoted` is borrowed from the file that decides whether a map is valid, so
# that a name this product puts in quotation marks looks the same wherever it
# appears. Two copies of that wording would drift apart and the user would be
# reading two slightly different voices from one product.
from katalyst.domain.validity import TERMINAL_KINDS, Violation, _quoted

ClaimState = Literal["unchanged", "shifted", "added", "killed"]
"""What happened to one claim between two worlds, in one word.

`unchanged` — it is in both worlds and it moved by less than 0.005.
`shifted` — it is in both, and it moved by at least 0.005 on its own resolve-by day.
`added` — it is in the second world and not in the first.
`killed` — it is in both, and the second world forces it false. Never "its number
got small", and never "nothing reaches it from the hypothesis any more", which is
a fact about the path rather than about the claim.
"""

MOVED_AT_LEAST = 0.005
"""How far a claim has to move before the move counts as a move at all."""

UnchangedBecause = Literal["under_the_floor", "versions_disagree"]
"""Why a claim reads `unchanged`, in one word.

`under_the_floor` — the claim did move, but by less than `MOVED_AT_LEAST`. **It is
the only answer this engine can give.**
`versions_disagree` — the move cleared the floor and fewer than nine versions of
the map in ten moved that way. **Never written.** The versions were cut on
2026-09-22 (decision record 0028), and a share of them is a share of nothing; the
word stays on the wire, unreachable, until one follow-up after the browser round
takes it off with the two range fields.

The floor lives in this file and on no wire, so without this word a reader is told
only that the engine says nothing moved. It is a fact about how the number was
**read**, and it never becomes a fifth state.
"""

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

    A claim still supposed on its own resolve-by day carries the stored 1 (or 0,
    where it was supposed false) so that the arithmetic stays ordinary. **No
    surface prints that number**: every reader looks at the world's `states`
    first and writes the word *Supposed* where the number would go.

    `unchanged_because` says why an `unchanged` claim is unchanged. It is here
    because the floor is a constant inside this file and appears on no wire, so a
    reader who is only told *unchanged* cannot tell "it barely moved" from
    anything else — and working it out at the other end would mean a second copy
    of the floor, disagreeing with this one.

    **Two fields on this shape are now always the same value**, and both say so
    in their own description: `agreement` is always nothing at all, and
    `moved_only_by_reweighting` is always false. Both were about the two thousand
    versions of the map, which were cut on 2026-09-22 (decision records 0028 and
    0016). They stay on the wire until one follow-up after the browser round,
    because their readers are that round's files.
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
            "Always nothing at all. It was the share of the versions of the map that "
            "moved the same way as the move above, and there is one version (decision "
            "record 0028). Kept on the wire, always absent, until the browser round "
            "closes."
        )
    )
    moved_only_by_reweighting: bool = Field(
        description=(
            "Always false. It was true when a claim's whole move came from an observation "
            "changing how much each version of the map counted, and no version counts for "
            "anything any more (decision record 0016: there is no inner loop for a world "
            "to survive). Kept on the wire, always false, until the browser round closes."
        )
    )
    unchanged_because: UnchangedBecause | None = Field(
        description=(
            "Why this claim is unchanged, in one word: 'under_the_floor', because the "
            "move is smaller than the floor, which is the only answer this engine gives. "
            "The other word, 'versions_disagree', is never written — it was about the two "
            "thousand versions of the map, and there is one. Nothing at all unless the "
            "claim is 'unchanged', and nothing where there is no move to measure: a claim "
            "only one of the two worlds holds."
        )
    )


class DeltaRow(BaseModel):
    """One ending that moved, with everything a reader needs to weigh the move.

    A row is read on the **day of largest divergence**, not on the claim's own
    resolve-by day, because a change that shows up for a fortnight and then
    unwinds is the thing a trader acts on — and on this product's own worked
    example reading a row on its distant resolve-by day shows about two thirds of
    the move and calls it the answer.

    **`range_width` and `agreement` are both always nought**, and each says so in
    its own description. They were the width of a range and a share of the two
    thousand versions of the map, and Kent cut both on 2026-09-22 (decision record
    0028). They stay on the wire until one follow-up after the browser round,
    because their readers are that round's files.
    """

    model_config = ConfigDict(frozen=True)

    target: PropositionId = Field(description="The ending that moved.")
    before: float = Field(description="The first world's likelihood on the day below.")
    after: float = Field(description="The second world's likelihood on the day below.")
    peak_delta: float = Field(
        description=(
            "The move on that day, signed: the largest the two worlds differ on any day "
            "the series carries — which past 180 days is not every day there is."
        )
    )
    at_day: date = Field(
        description=(
            "The day the two worlds are furthest apart. Always one of the days the series "
            "actually carries, which matters once a window longer than 180 days has been "
            "drawn at fewer points: the peak of a continuous curve can fall between two "
            "drawn days, so an edit that lengthens the window can move this date and the "
            "rank with it, without moving the claim's numbers at all. `diff.md` B4."
        )
    )
    range_width: float = Field(
        description=(
            "Always nought, and truthfully so: no number on this product carries a range "
            "any more, so every range is nought wide (decision record 0028). Kept on the "
            "wire until the browser round closes."
        )
    )
    agreement: float = Field(
        description=(
            "Always nought. It was the share of the versions of the map that moved the "
            "same way on that day; there is one version, so there is no share of them to "
            "report, and nought is what a field that counts nothing carries. Kept on the "
            "wire until the browser round closes (decision record 0028)."
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
    versions: int = Field(
        description=(
            "How many versions of the map both worlds worked out. Always 1 (decision "
            "record 0028). Kept on the wire until the browser round closes."
        )
    )
    worlds: int = Field(
        description=(
            "How many worlds ran inside each version. Always 0 — there is no inner loop "
            "(decision record 0016). Kept on the wire until the browser round closes."
        )
    )
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

    A row used to carry the budget it was produced at, because a sweep ran the
    engine at a quarter of the versions the shipped world used and nobody should
    lay a cheap number beside a dear one without noticing. There is one version of
    the map now (decision record 0028), so every run is the same run and there is
    no budget to report.
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


def diff(world_a: World, world_b: World, *, edit_in_words: str) -> Diff | list[Violation]:
    """Say what moved between two worlds, and rank the endings that moved.

    Pure: no clock, no network, no global random state. Everything is read off the
    two finished worlds: their beliefs for what each claim came out at, and their
    series for the day the two are furthest apart.

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

    days, where_a, where_b = _days_both_worlds_drew(world_a, world_b)
    claims = _states(world_a, world_b)
    rows = _ranked_endings(world_a, world_b, claims, days, where_a, where_b)
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


def sensitivity(world: World) -> tuple[SensitivityRow, ...]:
    """Flip each claim in turn and record what the flip does to every ending.

    One claim at a time, to the opposite of whichever way it more often comes out
    in this world, with the map worked through again from scratch each time. That
    is one whole run of the engine per claim, and there is nothing to choose about
    how big a run is: the engine works out one version of the map (decision record
    0028), so a sweep costs what it costs and every row is produced the same way as
    every other.

    This used to take a budget, because the engine ran two thousand versions of the
    map and a sweep could not afford twenty of those. It also used to be handed the
    arithmetic that built the world, because two engines stood side by side. Both
    are gone: one engine, one version, one kind of run.

    Nothing on screen reads this yet. It is written now because the engine it
    needs is written now, and bolting it on later would mean a second pass over
    the same arithmetic.

    Args:
        world: The world to sweep. Its map, the values its edits fixed, its day
            zero and its seed are all read from it.

    Returns:
        One row per claim on the map, in the map's own order, each naming the
        claim it flipped, what it flipped it to, and the signed change on every
        ending. Unranked, on purpose.
    """
    endings = tuple(one.id for one in world.graph.propositions if one.kind in TERMINAL_KINDS)
    start = propagate(
        world.graph,
        world.assignments,
        as_of=world.day_zero,
        seed=world.seed,
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
        )
        swept.append(
            SensitivityRow(
                flipped=claim.id,
                to=to,
                deltas={one: flipped.beliefs[one].p - start.beliefs[one].p for one in endings},
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

    The two are the same days whenever the two worlds' windows are, which is every
    edit but one. An `insert` can make the window longer — the window runs to the
    last day anything is judged — and past 180 days a series is drawn at evenly
    spaced points, so **the two can then share very few days indeed**: measured on
    the two-piece map of `test_a_longer_window_moves_nothing_it_cannot_reach`, a
    31-day window drawn at 32 points and a 365-day one drawn at 178 share 18. How
    few depends entirely on the map's own dates, so that figure is an illustration
    of the shape of the problem and not a property of the engine.

    Both worlds are still worked out on every day their own arithmetic reads by
    name; it is the *drawing* that parts company. Comparing the days they share is
    every day either of them would show side by side, and it is the whole of what a
    change list can honestly read.

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


def _why_it_is_unchanged(state: ClaimState, move: float | None) -> UnchangedBecause | None:
    """Say why an `unchanged` claim is unchanged.

    One answer, because there is one test: a claim is `shifted` when it moved by
    at least the floor, and `unchanged` when it did not. The floor lives in this
    file and is never put on a wire, so a reader who is only told *unchanged*
    could not otherwise tell that the claim moved at all.

    Nothing at all where there is no test to fail: every state but `unchanged`,
    and a claim only one of the two worlds holds, where there is no move to
    measure.

    Args:
        state: The word this claim came out with.
        move: The move, or nothing at all where one of the worlds has no number.

    Returns:
        The word, or nothing at all.
    """
    if state != "unchanged" or move is None:
        return None
    return "under_the_floor"


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


def _states(world_a: World, world_b: World) -> dict[PropositionId, ClaimDiff]:
    """Work out what happened to every claim either world holds.

    Four checks, in order, and the first that matches wins: added, then killed,
    then shifted, then unchanged. Each claim is read on **its own resolve-by day**
    — the day it is judged, and the day its tile's number already refers to.

    `shifted` needs one thing: the claim moved by at least 0.005. It needed a
    second thing once — that at least nine versions of the map in ten moved the
    same way — and that went with the versions on 2026-09-22 (decision record
    0028, Kent's row R48). There is one reading of the map, so there is nothing
    for a share of it to be a share of.

    An `unchanged` claim also says **why**, in `unchanged_because`, because the
    floor lives in this file and never reaches a reader.

    Args:
        world_a: The world to compare from.
        world_b: The world to compare to.

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
                unchanged_because=None,
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
                unchanged_because=None,
            )
            continue

        before = world_a.beliefs[claim_id].p
        after = world_b.beliefs[claim_id].p
        move = after - before
        state: ClaimState = "unchanged"
        if _forced_false_in(world_b, claim_id):
            state = "killed"
        elif abs(move) >= MOVED_AT_LEAST:
            state = "shifted"
        found[claim_id] = ClaimDiff(
            target=claim_id,
            state=state,
            before=before,
            after=after,
            delta=move,
            # Two fields, one dated reason: there is one version of the map, so
            # there is no share of the versions to agree and nothing for an
            # observation to reweight. 2026-09-22, records 0028 and 0016; both
            # leave the wire in one follow-up when the browser round closes.
            agreement=None,
            moved_only_by_reweighting=False,
            unchanged_because=_why_it_is_unchanged(state, move),
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


class Route(BaseModel):
    """One way through the map from an edit's subject to a claim, and how firm it is.

    `width` is what the route's **weakest** arrow is worth — the low bridge on
    that road. `path` is the claims it runs through, the subject first and the
    claim it reaches last; a subject reaches itself by a route of one claim and no
    arrows.

    A route may run against the arrows before it runs with them, once, when it
    starts at a claim somebody observed. That is exactly the reach an observation
    has, and it is why a route is worth reading rather than just counting.
    """

    model_config = ConfigDict(frozen=True)

    width: float = Field(
        description=(
            "What this route's weakest arrow is worth, between 0 and 1. A claim "
            "reached with no arrow in between is worth the most a route can be."
        )
    )
    path: tuple[PropositionId, ...] = Field(
        description="The claims this route runs through, the subject first."
    )


def best_backed_routes(
    graph: Graph,
    subjects: frozenset[PropositionId],
    observed: frozenset[PropositionId] = frozenset(),
) -> dict[PropositionId, "Route"]:
    """Find, for each claim, the route to it whose weakest arrow is strongest.

    **One rule for choosing a route, and this is it.** The change list ranks an
    ending by the route that reaches it; the Inspector's path bar draws one; and
    the Verify door grades the one that reaches the place a person asked about.
    Three readers, one rule, so nobody can be shown two different "best" routes
    for the same map.

    Over every route from any of the subjects to a claim, take the one whose
    **weakest** arrow is strongest. That is the widest bottleneck: the road with
    the highest low bridge rather than the shortest one. A change that could have
    reached an ending along a well-backed route is ranked by that route, whichever
    edit started it, because that route is the best case the reader is entitled to.

    A route out of an observed claim may climb against the arrows first and then
    descend, once — that is exactly the reach an observation has, and the two rules
    are the same rule. Every other edit's routes simply follow the arrows.

    **Two routes that are equally well-backed are separated** by taking the
    shorter one, and then the one whose first differing arrow comes earlier in the
    map's own list. Something has to choose, and a rule anybody can re-run beats
    whichever the search happened to reach first.

    Args:
        graph: The map the routes run over.
        subjects: The claims the routes work from.
        observed: Which of those an observation named, and may therefore climb
            from. Empty when nothing was observed, which is every caller but the
            change list.

    Returns:
        For each claim a route reaches, that route. A claim nothing reaches is
        absent.
    """
    arrows = tuple(_ordinary_arrows(graph))
    # Where each arrow sits in the map's own list, which is what separates two
    # routes that are equally well-backed and equally short.
    position_of = {arrow.id: position for position, arrow in enumerate(graph.links)}

    widest = _widths(graph, arrows, subjects, observed)
    by_floor: dict[float, list[PropositionId]] = {}
    for claim_id, width in widest.items():
        by_floor.setdefault(width, []).append(claim_id)

    found: dict[PropositionId, Route] = {}
    for floor, wanted in by_floor.items():
        over = _shortest_over(graph, arrows, position_of, subjects, observed, floor)
        for claim_id in wanted:
            if claim_id in subjects:
                # A subject is reached by no arrow at all, so its route is itself.
                found[claim_id] = Route(width=widest[claim_id], path=(claim_id,))
                continue
            walked = over.get(claim_id)
            if walked is None:  # pragma: no cover - the width says it is reachable
                continue
            found[claim_id] = Route(width=widest[claim_id], path=walked)
    return found


def _widths(
    graph: Graph,
    arrows: tuple[Link, ...],
    subjects: frozenset[PropositionId],
    observed: frozenset[PropositionId],
) -> dict[PropositionId, float]:
    """The widest bottleneck any route reaches each claim by.

    The max-min walk, which is the right way to find a widest bottleneck and
    always was. Two states per claim, because a route out of an observed claim
    has two halves: climbing against the arrows, then running with them. Dropping
    from the first to the second is free and can happen anywhere, and there is no
    way back, which is what stops a route zigzagging.

    Args:
        graph: The map the routes run over.
        arrows: Its ordinary arrows.
        subjects: The claims the routes work from.
        observed: Which of those an observation named.

    Returns:
        For each claim a route reaches, how wide the widest route to it is.
    """
    onward: dict[PropositionId, list[tuple[PropositionId, float]]] = {}
    backward: dict[PropositionId, list[tuple[PropositionId, float]]] = {}
    for claim in graph.propositions:
        onward[claim.id], backward[claim.id] = [], []
    for arrow in arrows:
        worth = PROVENANCE_WEIGHT[arrow.provenance]
        onward[arrow.source].append((arrow.target, worth))
        backward[arrow.target].append((arrow.source, worth))

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
        if width < best.get((here, climbing), -1.0):
            continue
        onwards: list[tuple[tuple[PropositionId, bool], float]] = [
            ((there, climbing), min(width, worth))
            for there, worth in (backward if climbing else onward)[here]
        ]
        if climbing:
            onwards.append(((here, False), width))
        for state, along in onwards:
            if along > best.get(state, -1.0):
                best[state] = along
                heappush(waiting, (-along, state[0], state[1]))

    widest: dict[PropositionId, float] = {}
    for (claim_id, _), width in best.items():
        widest[claim_id] = max(widest.get(claim_id, 0.0), min(NO_ARROW_TO_WEAKEN, width))
    return widest


def _shortest_over(
    graph: Graph,
    arrows: tuple[Link, ...],
    position_of: dict[str, int],
    subjects: frozenset[PropositionId],
    observed: frozenset[PropositionId],
    floor: float,
) -> dict[PropositionId, tuple[PropositionId, ...]]:
    """The shortest route to each claim over the arrows worth at least `floor`.

    **Why this is the whole of the second half of the rule.** A route reaches a
    claim with bottleneck `W` if and only if every arrow on it is worth at least
    `W`: a route whose bottleneck is `W` cannot hold an arrow worth less, and a
    route made only of arrows worth at least `W` has a bottleneck of at least
    `W`, which cannot exceed the widest there is. So the best routes to a claim
    are exactly the routes of the map with every thinner arrow set aside, and the
    shortest of those — ties by the arrows' own order — is what the rule names.

    Ties are broken by comparing `(how many arrows, their positions)` left to
    right, which is "the first differing arrow comes earlier" written out.

    Args:
        graph: The map the routes run over.
        arrows: Its ordinary arrows.
        position_of: Where each arrow sits in the map's own list.
        subjects: The claims the routes work from.
        observed: Which of those an observation named.
        floor: The width every arrow on a route must be worth at least.

    Returns:
        For each claim reached, the claims its best route runs through.
    """
    onward: dict[PropositionId, list[tuple[PropositionId, int]]] = {}
    backward: dict[PropositionId, list[tuple[PropositionId, int]]] = {}
    for claim in graph.propositions:
        onward[claim.id], backward[claim.id] = [], []
    for arrow in arrows:
        if PROVENANCE_WEIGHT[arrow.provenance] < floor:
            continue
        onward[arrow.source].append((arrow.target, position_of[arrow.id]))
        backward[arrow.target].append((arrow.source, position_of[arrow.id]))

    waiting: list[tuple[int, tuple[int, ...], PropositionId, bool, tuple[PropositionId, ...]]] = []
    seen: dict[tuple[PropositionId, bool], tuple[int, tuple[int, ...]]] = {}
    for subject in sorted(subjects):
        if subject not in onward:
            continue
        climbing = subject in observed
        seen[(subject, climbing)] = (0, ())
        heappush(waiting, (0, (), subject, climbing, (subject,)))

    reached: dict[PropositionId, tuple[int, tuple[int, ...], tuple[PropositionId, ...]]] = {}
    while waiting:
        steps, order, here, climbing, walked = heappop(waiting)
        if (steps, order) > seen.get((here, climbing), (steps, order)):
            continue
        best = reached.get(here)
        if best is None or (steps, order) < (best[0], best[1]):
            reached[here] = (steps, order, walked)

        moves: list[tuple[PropositionId, bool, int, tuple[PropositionId, ...], int]] = [
            (there, climbing, steps + 1, (*walked, there), at)
            for there, at in (backward if climbing else onward)[here]
        ]
        if climbing:
            # The drop from climbing to descending is free and is not an arrow,
            # so it adds neither a step nor a position.
            moves.append((here, False, steps, walked, -1))

        for there, still_climbing, cost, path, at in moves:
            key = (cost, order if at < 0 else (*order, at))
            state = (there, still_climbing)
            if state not in seen or key < seen[state]:
                seen[state] = key
                heappush(waiting, (key[0], key[1], there, still_climbing, path))
    return {claim_id: one[2] for claim_id, one in reached.items()}


def _best_backed_routes(
    graph: Graph, subjects: frozenset[PropositionId], observed: frozenset[PropositionId]
) -> dict[PropositionId, float]:
    """Read only how firm each claim's best-backed route is, for the ranking.

    The ranking multiplies the size of a move by how well-backed the route that
    carried it is, and never draws the route itself. This is that one number, off
    the one rule above.

    Args:
        graph: The map the routes run over — the one the second world's edits left
            behind.
        subjects: The claims the edits work from.
        observed: Which of those an observation named.

    Returns:
        For each claim a route reaches, how much its best-backed route's weakest
        arrow is worth.
    """
    return {
        claim_id: route.width
        for claim_id, route in best_backed_routes(graph, subjects, observed).items()
    }


# --- The endings that moved, ranked ----------------------------------------


def _ranked_endings(
    world_a: World,
    world_b: World,
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
        peak = float(gap[at])
        rows.append(
            DeltaRow(
                target=claim.id,
                before=float(before[at]),
                after=float(after[at]),
                peak_delta=peak,
                at_day=world_b.day_zero + timedelta(days=int(days[at])),
                # Both nought, for one dated reason: no number carries a range, so
                # every range is nought wide, and there is one version of the map,
                # so there is no share of the versions to report. 2026-09-22,
                # decision record 0028; both leave the wire with the follow-up.
                range_width=0.0,
                agreement=0.0,
                rank=abs(peak) * widest.get(claim.id, 0.0),
            )
        )
    return tuple(sorted(rows, key=lambda one: (-one.rank, one.target)))


# --- The one sentence beside the list --------------------------------------


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
        f"{two_figures(top.before)} to {two_figures(top.after)} by "
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
