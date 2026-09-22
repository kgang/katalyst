"""What a difference between two worlds says, over maps nobody wrote by hand.

`diff` takes two finished worlds built from one map and one seed and says what
moved: a word for every claim, a ranked list of the endings that moved, and one
fixed sentence. Four things are easy to get wrong here and each has a test whose
whole job is to catch exactly one of them.

* **A move must be read off the paired difference, never off whether two ranges
  overlap.** On the worked example two ranges overlap across nearly half their
  width while every version moves the same way; overlap would report "no change"
  about the clearest change on the map. `test_shifted_needs_agreement` is that
  measurement.
* **`killed` means forced false, and nothing else.** A claim whose number fell a
  long way is `shifted`. `test_killed_means_forced_false`.
* **The rank has two factors and no more.** How big the move is, times how
  well-backed the weakest arrow on the best-backed route behind it is. Neither how
  wide the range is nor how much the versions agreed is ever multiplied in.
  `test_rank_has_two_factors`.
* **A row is read on the day the two worlds are furthest apart**, not on the
  claim's own distant resolve-by day. `test_delta_row_reads_the_peak_day`.

**Budgets.** The shipped run is two thousand versions of the map times eight
worlds each, and a difference costs four runs of the engine: two worlds, and the
version-by-version numbers behind each of them worked out again. That is far too
slow to run hundreds of times, so the tests over generated maps use a much
smaller budget and say so. Nothing about the arithmetic changes with the budget;
only how steady the numbers are, and these tests are about what the arithmetic
*is*. The handful of tests that are about a measured number run at the shipped
budget on the worked example.
"""

import importlib
import re
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise

import networkx
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from katalyst.domain import (
    Belief,
    Beliefs,
    Believe,
    Branch,
    ContractPayoff,
    Diff,
    Do,
    Graph,
    Insert,
    Intervention,
    Link,
    Observe,
    Proposition,
    PropositionId,
    Refine,
    Resolution,
    Retune,
    Source,
    World,
    apply,
    diff,
    propagate,
    sensitivity,
)
from katalyst.domain.belief import two_figures
from katalyst.domain.diff import (
    MOVED_AT_LEAST,
    NO_ARROW_TO_WEAKEN,
    PROVENANCE_WEIGHT,
    _ordinary_arrows,
    best_backed_routes,
)
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE
from tests.comparisons import every_version_answered_the_same
from tests.strategies import branches, graphs

# The package re-exports the `diff` function under the name of the file it lives
# in, so plain `import katalyst.domain.diff` hands back the function rather than
# the file. One test replaces something inside that file, so it asks for the file
# by name.
diff_module = importlib.import_module("katalyst.domain.diff")

many = settings(max_examples=20, deadline=None)
a_few = settings(max_examples=8, deadline=None)

DAY_ZERO = date(2026, 1, 1)
"""Day zero for the generated maps, which carry resolve-by dates from 2026 onwards."""

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

A_LIKELIHOOD = r"[<>]?\.\d+"
"""How this product writes a likelihood, as a pattern: a point, then digits.

Either of the two guard words, `<.01` and `>.99`, or a plain decimal with the
nought before the point dropped. Never an exponent, never a digit before the
point. The sentence pattern below is built out of this one so that the two cannot
drift, and `test_a_likelihood_is_written_as_a_plain_decimal` checks it on its own
over every likelihood there is.
"""

WRITTEN_LIKELIHOOD = re.compile(f"^{A_LIKELIHOOD}$")
"""The same pattern, anchored, for checking one written likelihood by itself."""

FIRST_SENTENCE = re.compile(
    rf'^".+" moves .+ from {A_LIKELIHOOD} to {A_LIKELIHOOD} by '
    r"\d{4}-\d{2}-\d{2} and leaves \d+ claims? untouched\.$"
)
"""The sentence a difference uses when something at an ending moved."""

SECOND_SENTENCE = re.compile(r'^".+" moves no ending and leaves \d+ claims? untouched\.$')
"""The sentence a difference uses when nothing at an ending moved."""


# --- Small maps and small helpers ------------------------------------------


def _claim(
    identifier: str,
    kind: str = "event",
    prior: tuple[float, float, float] = (0.3, 0.2, 0.45),
    days: int = 30,
) -> Proposition:
    """One plain claim with a stated likelihood and range."""
    middle, low, high = prior
    belief = Belief(p=middle, lo=low, hi=high, owner="model")
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind=kind,  # type: ignore[arg-type]
        persistence="event",
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=days),
        ),
        prior=belief,
        beliefs=Beliefs(model=belief),
        payoff=(
            ContractPayoff(
                venue="Polymarket",
                contract_id="something-tradeable",
                title="Will the claim under this name come true?",
                side="yes",
            )
            if kind == "market"
            else None
        ),
    )


def _arrow(source: str, target: str, *, strength: float = 1.0, provenance: str = "argued") -> Link:
    """One plain arrow that switches on the day its cause is settled and holds."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="trigger",
        strength=strength,
        lag=0.0,
        shape="step",
        rationale="The first claim makes the second one more likely, for a stated reason.",
        provenance=provenance,  # type: ignore[arg-type]
    )


def _map(claims: tuple[Proposition, ...], arrows: tuple[Link, ...]) -> Graph:
    """A whole small map, with the first claim as the one it started from."""
    return Graph(id="small", propositions=claims, links=arrows, hypothesis_id=claims[0].id)


def _branch(*edits: Intervention, identifier: str = "branch-under-test") -> Branch:
    """A branch holding the edits given, named the way a user would name one."""
    return Branch(id=identifier, label="A branch a test wrote", interventions=edits)


def _world(graph: Graph, branch: Branch) -> World:
    """Fold a branch onto a map, work the numbers through, and say which branch it was."""
    folded = apply(graph, branch)
    if isinstance(folded, list):
        # A branch nobody wrote by hand sometimes cannot be folded: splitting a
        # claim is not built yet, and an insert can reuse an identifier. Those
        # are discarded rather than quietly passed.
        assume(False)
    assert not isinstance(folded, list)
    left_behind, fixed = folded
    world = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=SEED)
    return world.model_copy(update={"branch_id": branch.id})


def _hormuz_world(branch: Branch | None) -> World:
    """The same, on the shipped worked example and its own day zero."""
    folded = apply(HORMUZ, branch or _branch())
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    world = propagate(left_behind, fixed, as_of=FIXTURE_DATE, seed=SEED)
    return world.model_copy(update={"branch_id": branch.id if branch is not None else None})


def _compared(graph: Graph, first: Branch, second: Branch) -> Diff:
    """Two worlds from one map and one seed, and the difference between them."""
    answer = diff(
        _world(graph, first),
        _world(graph, second),
        edit_in_words=second.label,
    )
    assert not isinstance(answer, list), answer
    return answer


def _affected_from_the_shape(graph: Graph, edit: Intervention) -> set[str]:
    """Work out, from the shape of the map alone, which claims this edit may move.

    The affected-set table written out from the chapter rather than from the code.
    It must never call `affected_set` and must never ask the engine which claims it
    changed — a test that agrees with the code it is checking passes by agreeing
    with itself.
    """
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in graph.propositions)
    # Feedback arrows are left out, the same way the map's own loop check leaves
    # them out: nothing is worked through one in this version.
    walk.add_edges_from((one.source, one.target) for one in graph.links if not one.reflexive)

    if isinstance(edit, Refine):
        return {one.id for one in edit.into}
    if isinstance(edit, Insert):
        subject = edit.proposition.id
    elif isinstance(edit, Retune):
        subject = next(one.target for one in graph.links if one.id == edit.link)
    else:
        subject = edit.target
    if isinstance(edit, Believe):
        return {subject}

    reached = {subject} | networkx.descendants(walk, subject)
    if isinstance(edit, Observe):
        for cause in networkx.ancestors(walk, subject):
            reached |= {cause} | networkx.descendants(walk, cause)
    return reached


def _may_move(graph: Graph, branch: Branch) -> set[str] | None:
    """Every claim any edit of a branch is allowed to move, worked out edit by edit.

    Each edit's reach is read off the map **that edit** leaves behind, because that
    is the map the locality rule is about, and the branch's reach is the union.
    Nothing here asks the engine what it touched.
    """
    reached: set[str] = set()
    here = graph
    for edit in branch.interventions:
        folded = apply(here, _branch(edit, identifier="one-step"))
        if isinstance(folded, list):
            return None
        here, _ = folded
        reached |= _affected_from_the_shape(here, edit)
    return reached


def _weakest_on_the_best_route(graph: Graph, subjects: set[str], target: str) -> float:
    """Walk every route from any subject to the target and take the strongest weakest arrow.

    Written out with the graph library's own path enumeration rather than with the
    search the code uses, so the two agree by arithmetic rather than by sharing a
    line. Feedback arrows are set aside, by the rule the whole engine reads the map
    under.
    """
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in graph.propositions)
    worth: dict[tuple[str, str], float] = {}
    for one in graph.links:
        if one.reflexive:
            continue
        walk.add_edge(one.source, one.target)
        worth[(one.source, one.target)] = max(
            worth.get((one.source, one.target), 0.0), PROVENANCE_WEIGHT[one.provenance]
        )
    widest = 0.0
    for subject in subjects:
        if subject == target:
            widest = max(widest, 1.0)
            continue
        for route in networkx.all_simple_paths(walk, subject, target):
            widest = max(widest, min(worth[step] for step in pairwise(route)))
    return widest


# --- A difference comes from two worlds, one base and one seed -------------


@given(st.data())
@many
def test_diff_refuses_mismatched_worlds(data: st.DataObject) -> None:
    """Two worlds built from the same raw material compare; anything else is refused.

    The comparison rests on version 7 of both worlds having been built from the
    same numbers. Break that — a different map, a different seed, a different
    number of versions or worlds — and every difference is the user's edit plus a
    wash of sampling noise. There is no repair: rebuilding one world to match the
    other would answer a question nobody asked.
    """
    graph = data.draw(graphs())
    first = _world(graph, data.draw(branches(graph)))
    second = _world(graph, data.draw(branches(graph)))

    assert not isinstance(diff(first, second, edit_in_words="a name"), list)

    for wrong in (
        {"base_id": "a-different-map"},
        {"seed": first.seed + 1},
        {"versions": first.versions + 1},
        {"worlds": first.worlds + 1},
    ):
        doctored = second.model_copy(update=wrong)
        refused = diff(first, doctored, edit_in_words="a name")
        assert isinstance(refused, list), wrong
        assert len(refused) == 1
        # Its own code, not one of the four that refuse an edit: nothing here is
        # anybody's edit, and a code has to mean what it says.
        assert refused[0].code == "worlds_not_comparable"
        assert refused[0].subject == doctored.base_id
        assert refused[0].message.endswith(".")
        assert refused[0].subject not in refused[0].message
        assert len(refused[0].message.split()) >= 8, "a sentence, not a code"


@given(st.data())
@many
def test_every_claim_has_exactly_one_state(data: st.DataObject) -> None:
    """Every claim either world holds appears exactly once, with one of the four words."""
    graph = data.draw(graphs())
    answer = _compared(graph, data.draw(branches(graph)), data.draw(branches(graph)))

    assert set(answer.claims) == {one.target for one in answer.claims.values()}
    for claim_id, one in answer.claims.items():
        assert one.target == claim_id
        assert one.state in {"unchanged", "shifted", "added", "killed"}


@given(st.data())
@many
def test_diff_replays_from_base_branches_seed(data: st.DataObject) -> None:
    """Two differences worked out independently from the same three inputs are identical bytes."""
    graph = data.draw(graphs())
    first, second = data.draw(branches(graph)), data.draw(branches(graph))

    once = _compared(graph, first, second)
    twice = _compared(graph, first, second)

    assert once.model_dump_json() == twice.model_dump_json()


# --- What puts a claim in each of the four states --------------------------


@given(st.data())
@many
def test_shifted_is_the_floor_alone(data: st.DataObject) -> None:
    """A claim is `shifted` exactly when it moved by the floor or more, and on nothing else.

    Decision record 0028 names this test. The word used to need a second thing —
    that at least nine versions of the map in ten moved the same way — and that
    went with the versions: there is one reading of the map, so a share of them is
    a share of one thing. The move is carried on every claim both worlds hold, so
    the rule that decided the word can be read straight off the answer without
    recomputing anything, which is the whole reason it is carried.
    """
    graph = data.draw(graphs())
    answer = _compared(graph, data.draw(branches(graph)), data.draw(branches(graph)))

    for one in answer.claims.values():
        assert one.agreement is None, one
        assert one.moved_only_by_reweighting is False, one
        if one.state in {"added", "killed"} or one.delta is None:
            continue
        assert (one.state == "shifted") == (abs(one.delta) >= MOVED_AT_LEAST), one


def test_killed_means_forced_false() -> None:
    """`killed` is the claim being forced false, and a claim that merely fell a long way is not.

    Stretching the word to cover "the likelihood got low" would tell the user
    their argument was cut when it was merely losing. On the strike branch the
    state everything downstream rests on — *the strait stays open to commercial
    transit through 1 November* — falls a long way and is `shifted`, and nothing on
    that branch is `killed` at all: the strike is an insert and a supposition, and
    neither forces anything false. Add one edit forcing the premium claim false and
    that one, and only that one, is `killed`.
    """
    base = _hormuz_world(None)
    strike = _hormuz_world(HORMUZ_THEN_STRIKE)
    falling = diff(base, strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(falling, list), falling

    fell = falling.claims["O"]
    assert fell.state == "shifted"
    assert fell.before is not None and fell.after is not None and fell.after < fell.before
    assert all(one.state != "killed" for one in falling.claims.values())

    cut = _hormuz_world(_branch(Do(target="C", value=False, at=FIXTURE_DATE)))
    forced = diff(base, cut, edit_in_words="The premium never falls")
    assert not isinstance(forced, list), forced

    assert forced.claims["C"].state == "killed"
    assert [one for one, said in forced.claims.items() if said.state == "killed"] == ["C"]


@given(st.data())
@many
def test_killed_is_exactly_what_the_second_world_forces_false(data: st.DataObject) -> None:
    """A claim is `killed` exactly when the last word any edit had on it fixed it false."""
    graph = data.draw(graphs())
    first, second = data.draw(branches(graph)), data.draw(branches(graph))
    world = _world(graph, second)
    answer = _compared(graph, first, second)

    for claim_id, one in answer.claims.items():
        if one.state == "added":
            continue
        said = [each for each in world.assignments if each.target == claim_id]
        assert (one.state == "killed") == (bool(said) and not said[-1].value), claim_id


def test_a_claim_only_the_first_world_holds_reads_as_untouched() -> None:
    """A claim one branch added and the other did not is left alone, with no second number.

    The product cannot produce this — there is no delete, and "this is out of the
    picture" is said by forcing a claim false — but two branches that forked apart
    could, and a difference has to have a word for every claim either world holds.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending"),),
    )
    newcomer = Insert(proposition=_claim("extra"), links=(_arrow("top", "extra"),))

    answer = _compared(graph, _branch(newcomer), _branch())

    assert answer.claims["extra"].state == "unchanged"
    assert answer.claims["extra"].before is not None
    assert answer.claims["extra"].after is None
    assert answer.claims["extra"].delta is None


def test_a_claim_the_second_world_adds_reads_as_added() -> None:
    """A claim the second branch put on the map is `added`, and carries the number it has there."""
    strike = diff(
        _hormuz_world(None),
        _hormuz_world(HORMUZ_THEN_STRIKE),
        edit_in_words=HORMUZ_THEN_STRIKE.label,
    )
    assert not isinstance(strike, list), strike

    added = strike.claims["S"]
    assert added.state == "added"
    assert added.before is None
    assert added.delta is None
    assert added.agreement is None
    assert added.after == 1.0


# --- The ranked list of endings that moved ---------------------------------


def test_rank_has_two_factors() -> None:
    """The rank is the size of the move times the weakest arrow on the best-backed route.

    Two factors, and the test works the second one out for itself: it walks every
    route from either edit's subject to the ending and takes the one whose weakest
    arrow is strongest. Neither how wide the range is nor how much the versions
    agreed may be multiplied in, so replacing both with any other numbers leaves
    every rank and the whole order exactly as it was.
    """
    strike = _hormuz_world(HORMUZ_THEN_STRIKE)
    answer = diff(_hormuz_world(None), strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(answer, list), answer

    # The two edits of this branch work from the strait's own claim and from the
    # strike it inserts, and the test names them rather than asking the code.
    subjects = {"H", "S"}
    for row in answer.rows:
        weakest = _weakest_on_the_best_route(strike.graph, subjects, row.target)
        assert weakest in set(PROVENANCE_WEIGHT.values())
        assert row.rank == abs(row.peak_delta) * weakest, row.target

    rewritten = [
        one.model_copy(update={"range_width": 0.99, "agreement": 0.5}) for one in answer.rows
    ]
    assert [one.rank for one in rewritten] == [one.rank for one in answer.rows]
    assert sorted(rewritten, key=lambda one: (-one.rank, one.target)) == rewritten


@given(st.data())
@many
def test_delta_rail_holds_ranked_terminals(data: st.DataObject) -> None:
    """The list holds exactly the endings that moved, largest rank first, and nothing else."""
    graph = data.draw(graphs())
    second = data.draw(branches(graph))
    answer = _compared(graph, data.draw(branches(graph)), second)
    endings = {
        one.id
        for one in _world(graph, second).graph.propositions
        if one.kind in {"market", "not_tradeable"}
    }

    listed = [one.target for one in answer.rows]
    assert len(listed) == len(set(listed)), "an ending is listed at most once"
    assert set(listed) == {
        claim_id
        for claim_id, one in answer.claims.items()
        if one.state == "shifted" and claim_id in endings
    }
    assert [one.rank for one in answer.rows] == sorted(
        (one.rank for one in answer.rows), reverse=True
    )


@given(st.data())
@many
def test_delta_row_reads_the_peak_day(data: st.DataObject) -> None:
    """No day in the window divides the two worlds more than the day the row names.

    A change that shows up for a fortnight and then unwinds is the thing a trader
    acts on, so a row is read where the two worlds are furthest apart — and the day
    it names is always one of the days the series actually carries, which matters
    once a long window has been drawn at fewer points.
    """
    graph = data.draw(graphs())
    first, second = data.draw(branches(graph)), data.draw(branches(graph))
    before, after = _world(graph, first), _world(graph, second)
    answer = diff(before, after, edit_in_words=second.label)
    assert not isinstance(answer, list), answer

    in_a = {day: index for index, day in enumerate(before.series_days)}
    in_b = {day: index for index, day in enumerate(after.series_days)}
    for row in answer.rows:
        named = (row.at_day - after.day_zero).days
        assert named in in_a and named in in_b
        gaps = [
            abs(after.series[row.target][in_b[day]] - before.series[row.target][in_a[day]])
            for day in in_b
            if day in in_a
        ]
        assert abs(row.peak_delta) >= max(gaps)
        assert row.before == before.series[row.target][in_a[named]]
        assert row.after == after.series[row.target][in_b[named]]
        assert row.peak_delta == row.after - row.before
        assert 0.0 <= row.range_width <= 1.0
        assert 0.0 <= row.agreement <= 1.0


def test_an_observation_carries_a_change_upstream_and_the_route_climbs_with_it() -> None:
    """A route out of an observed claim may climb against the arrows before it descends.

    Observing something is done by throwing away the worlds it did not happen in,
    and that changes what the survivors say about the claim's **causes** as much as
    about what it causes. So the route the rank is read along reaches upstream
    exactly as far as an observation's own reach does. On the map below the only
    way from the claim that was observed to the other ending is back up through
    their shared cause and down the far side — and the far side is the weak arrow,
    so that is what the second factor reads. Refuse to climb and there would be no
    route at all, and the ending would rank at nothing.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.5, 0.35, 0.65)),
            _claim("seen", kind="market", prior=(0.05, 0.02, 0.10)),
            _claim("far", kind="market", prior=(0.3, 0.2, 0.45)),
        ),
        (
            _arrow("top", "seen", strength=4.5),
            _arrow("top", "far", strength=3.0, provenance="asserted"),
        ),
    )

    answer = _compared(
        graph,
        _branch(identifier="base"),
        _branch(Observe(target="seen", value=True)),
    )

    listed = {one.target: one for one in answer.rows}
    assert set(listed) == {"seen", "far"}
    assert listed["far"].peak_delta > 0.0, "the worlds that survive are the ones where top held"
    assert listed["far"].rank == abs(listed["far"].peak_delta) * PROVENANCE_WEIGHT["asserted"]
    # The observed claim is the edit's own subject, so no arrow stands between the
    # edit and it and there is nothing for the second factor to discount.
    assert listed["seen"].rank == abs(listed["seen"].peak_delta)


def test_a_supposed_ending_is_written_as_nearly_certain_rather_than_as_one() -> None:
    """A number that rounds to nothing or to everything is written `<.01` or `>.99`.

    A sentence that prints `1.0` claims a certainty nobody asserted. A claim
    somebody supposed true reads exactly 1 inside the arithmetic, and the sentence
    says so in words that do not overstate it.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending"),),
    )
    supposed = _branch(Do(target="ending", value=True, at=DAY_ZERO))
    ruled_out = _branch(Do(target="ending", value=False, at=DAY_ZERO))

    assert ">.99" in _compared(graph, _branch(), supposed).summary
    assert "<.01" in _compared(graph, ruled_out, _branch()).summary


# --- The direction is read with the number's own weights -------------------


def _observing(target: str) -> Branch:
    """A branch of one edit: this claim actually came true."""
    return _branch(Observe(target=target, value=True), identifier=f"br_observe_{target.lower()}")


def test_an_observation_puts_a_row_on_the_rail() -> None:
    """Saying Brent settled below $68 puts the two tradeable endings on the change list.

    This is the button that used to look as if it did nothing. It looked that way
    for a reason that no longer exists: an observation was made by throwing away
    the worlds it did not happen in, some versions of the map lost every one of
    their eight worlds, and counting those empty versions in the direction dragged
    both endings a hair under the ninety-per-cent bar and emptied the rail. There
    are no versions and no bar now — a change-list row needs a move of `.005` and
    nothing else (decision record 0028) — and both endings are on the rail, rising,
    with the fixed sentence beside them.

    Directions and orderings only. The example map is a curated one whose
    illustrative inputs may be tuned, so nothing here pins a value.
    """
    base = _hormuz_world(None)
    learned = _hormuz_world(_observing("B"))
    answer = diff(base, learned, edit_in_words="Brent settled below $68")
    assert not isinstance(answer, list), answer

    listed = {one.target: one for one in answer.rows}
    assert {"M1", "M2"} <= set(listed), listed
    for target in ("M1", "M2"):
        assert answer.claims[target].state == "shifted"
        assert listed[target].peak_delta > 0.0, "cheap Brent is evidence for both market claims"
    assert FIRST_SENTENCE.match(answer.summary), answer.summary


# --- Two corners where the weights run out ---------------------------------


# --- Which half of the test an unchanged claim failed ----------------------


@given(st.data())
@many
def test_an_unchanged_claim_says_why(data: st.DataObject) -> None:
    """The word on the row is the rule applied to the number beside it.

    The floor lives in the engine and reaches no reader, so *unchanged* on its own
    cannot say that the claim moved at all. There is one reason left —
    `under_the_floor` — because the other was about the two thousand versions of
    the map (decision record 0028), and this says so: no row ever carries the
    other word.
    """
    graph = data.draw(graphs())
    answer = _compared(graph, data.draw(branches(graph)), data.draw(branches(graph)))

    for claim_id, one in answer.claims.items():
        assert one.unchanged_because != "versions_disagree", claim_id
        if one.state != "unchanged" or one.delta is None:
            assert one.unchanged_because is None, claim_id
        else:
            assert one.unchanged_because == "under_the_floor", claim_id


def test_only_an_unchanged_claim_says_why() -> None:
    """Every other word means the claim moved, so there is nothing to explain.

    On the worked example's strike branch: claims that moved, the claim the
    branch added, and a claim forced false all carry nothing at all, and the
    claims that held still all carry a word.
    """
    base = _hormuz_world(None)
    strike = _hormuz_world(HORMUZ_THEN_STRIKE)
    answer = diff(base, strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(answer, list), answer

    held_still = [one for one in answer.claims.values() if one.state == "unchanged"]
    moved = [one for one in answer.claims.values() if one.state != "unchanged"]
    assert held_still and moved, "the worked example was expected to show both"
    assert all(one.unchanged_because is not None for one in held_still), held_still
    assert all(one.unchanged_because is None for one in moved), moved

    cut = _hormuz_world(_branch(Do(target="C", value=False, at=FIXTURE_DATE)))
    forced = diff(_hormuz_world(None), cut, edit_in_words="The premium never falls")
    assert not isinstance(forced, list), forced
    assert forced.claims["C"].state == "killed"
    assert forced.claims["C"].unchanged_because is None


# --- Locality, seen from the difference ------------------------------------


@given(st.data())
@a_few
def test_diff_states_respect_locality(data: st.DataObject) -> None:
    """Every claim outside a branch's reach comes out `unchanged`.

    The reach is worked out here, from the shape of the map, edit by edit, and is
    never asked of the engine. The maps are drawn in two pieces so that there is
    always something outside the reach to check: on a map that is all of one piece
    the first claim is a cause of every other, and an assertion over an empty set
    is always true.
    """
    graph = data.draw(graphs(separated=True))
    branch = data.draw(branches(graph))
    reach = _may_move(graph, branch)
    assume(reach is not None)
    assert reach is not None
    base = _world(graph, _branch(identifier="base"))
    branched = _world(graph, branch)
    answer = diff(base, branched, edit_in_words=branch.label)
    assert not isinstance(answer, list), answer

    # What the engine worked out about each unreachable claim, exactly: every
    # version of the map, on every day both worlds drew. `tests/comparisons.py`
    # says why the reported average is not the thing to ask for to the bit.
    every_version_answered_the_same(
        base, branched, [one for one in answer.claims if one not in reach]
    )
    for claim_id, one in answer.claims.items():
        if claim_id in reach:
            continue
        assert one.state == "unchanged", claim_id
        # And the reported number itself, exactly. Nothing about how the numbers
        # are worked out depends on how long the window is any more, so this is
        # bit-for-bit whatever the edit did to the window.
        assert one.delta == 0.0, claim_id


def test_a_longer_window_moves_nothing_it_cannot_reach() -> None:
    """Inserting a claim at one end of a map moves nothing at the other end.

    Two pieces with nothing joining them. In the second piece `cause` triggers
    `effect` through an arrow with a three-day delay, so `effect`'s clock starts on
    day 3, and `effect` in turn pushes `ending`. The edit inserts a claim in the
    **first** piece, judged a year out, which stretches the window from a month to a
    year. Nothing on the second piece is connected to what was inserted.

    But past 180 days a series is drawn at evenly spaced points instead of every
    day, and a day between two of them is read at the next one along — so day 3 is
    drawn on the short window and is not on the long one, and the push into `ending`
    starts reading `effect` on day 4 instead. `ending` moves, and no edit reached it.

    It used to. Measured before the fix: `.096` on the version-by-version answers,
    a tenth of a likelihood, because the push into `ending` started reading `effect`
    on day 4 instead of day 3. That was the product's central correctness claim
    (INV-4, locality: an edit changes only what is still connected to its subject)
    failing through the sampling grid rather than along the arrows.

    The fix is the one rule in `propagation.md` B5: **the day cap decides where a
    series is drawn, never when a push fires.** Every day the arithmetic reads by
    name — the day each claim's clock starts, the day each observation speaks — is
    on the grid exactly, so a push fires on the true day its cause settles.
    Re-spacing the drawn points by lengthening a window then re-times nothing,
    because nothing that fires was ever read off them.

    **The repair that looks obvious is not the repair**, and was tried: keeping
    every settled day among the days a reader is *sent* makes the drawn points
    depend on the settled days, so a supposition — which cuts arrows and so moves
    them — re-spaces the series and shifts a claim's own ancestors, breaking INV-3,
    assert is not observe.

    *(Amended 2026-09-21. This docstring first said every day of the window is
    worked out, which was true of the engine that shipped the repair. Two sets of
    days have to be told apart and were not: the days a reader is **drawn** a line
    through, which move when the window's length moves and may, and the days the
    numbers are **computed** on, which must land exactly on every day the
    arithmetic names and must not. The first repair made both sets every day of
    the window, which was correct and cost 5 892 MB on a five-year map; the grid
    is now the sent days plus the named ones, at 958 MB, and the narrow difference
    from the rejected repair above is which of the two sets the settled days join.)*
    """
    far_side = (
        _claim("cause", kind="event", prior=(0.5, 0.25, 0.75), days=0),
        _claim("effect", kind="event", prior=(0.5, 0.25, 0.75), days=0),
        _claim("ending", kind="market", prior=(0.3, 0.2, 0.45), days=0),
    )
    near_side = (_claim("start", kind="hypothesis", prior=(0.4, 0.2, 0.6), days=31),)
    delayed = _arrow("cause", "effect").model_copy(
        update={"lag": 3.0, "shape": "impulse", "half_life": 1.0}
    )
    graph = _map(near_side + far_side, (delayed, _arrow("effect", "ending", strength=1.5)))

    a_year_out = _claim("claim-newcomer", kind="event", prior=(0.3, 0.2, 0.45), days=365)
    stretches_the_window = _branch(
        Insert(proposition=a_year_out, links=(_arrow("start", "claim-newcomer", strength=0.0),)),
        identifier="a-year-out",
    )

    base = _world(graph, _branch(identifier="base"))
    stretched = _world(graph, stretches_the_window)
    assert len(base.series_days) != len(stretched.series_days), "the window was meant to grow"

    # `ending` is in the other piece; nothing the edit did can reach it.
    every_version_answered_the_same(base, stretched, ["cause", "effect", "ending"])


# --- How a likelihood is written ------------------------------------------


WRITTEN_BY_THE_RULE: tuple[tuple[float, str], ...] = (
    (0.0, "<.01"),
    (1e-09, "<.01"),
    (0.00012, "<.01"),
    (0.0035, "<.01"),
    (0.0099, "<.01"),
    (0.00995, ".010"),
    (0.01, ".010"),
    (0.0105, ".011"),
    (0.0999, ".10"),
    (0.06, ".060"),
    (0.35, ".35"),
    (0.99, ".99"),
    (0.994, ".99"),
    (0.995, ">.99"),
    (1.0, ">.99"),
)
"""The rule, written out on the cases that decide it.

The right-hand column is not a measurement and nothing computed it: it is the
rule's own definition — *round to two significant figures, then use a guard word
exactly when it is true of the rounded number* (Kent, 2026-09-20) — worked out by
hand for each input on the left. Every awkward case is here on purpose:

* **both guards' own numbers print**, because neither `.010` nor `.99` is below or
  above its own guard, which is the whole of where the boundary sits;
* **both guards catch a rounding that carries across them** — `.00995` rounds up
  to `.010` and prints, `.0099` does not and is guarded; `.994` rounds to `.99`
  and prints, `.995` rounds to one and is guarded;
* `.0999`, whose rounding carries into the next place and gives `.10`, not `.100`;
* `.060`, which keeps the trailing nought it earned;
* a billionth and a ten-thousandth, which are now guarded and which used to print
  `1.0e-09` and `.00012` — the first put an exponent in a sentence, and the second
  stated a likelihood more precisely than this product is willing to;
* nothing at all and one, the two values the guards exist for.

**The browser writes this same rule as `toTwoFigures` in
`frontend/src/components/BeliefChip.tsx`**, and the two are one rule written
twice. When the two stacks meet, run this table through both and require the same
answer for every row — that cross-check is the thing that keeps one number from
reading two ways on one screen, and a table stated from the rule cannot do it
alone.
"""


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=500, deadline=None)
def test_a_likelihood_is_written_as_a_plain_decimal(likelihood: float) -> None:
    """However small it is, a likelihood is written as a decimal a person can read aloud.

    Four things at once, for every likelihood there is. It never carries an
    exponent — *"moves this claim from `>.99` to `1.0e-09`"* is not a sentence
    anybody can read aloud, and it is what this function used to produce below a
    ten thousandth. It always matches the shape the summary sentence's own pattern
    expects, which is the same pattern this checks against, so the two cannot
    drift. Where it is not one of the two guards it reads back within half a unit
    of its second figure — which is what *two significant figures* means, and is
    worked out from the answer rather than typed in — and it lands between the two
    guards' own numbers, which is where the rule says the figures live.

    **The two guards are checked by what their words claim**, which is the whole
    reason the boundary sits where it does (Kent, 2026-09-20): `<.01` is written
    only for a likelihood that really is below a hundredth, and `>.99` only for one
    that really is above ninety-nine hundredths. A guard beside a number those
    words are false of would be the product lying in two characters.
    """
    written = two_figures(likelihood)

    assert "e" not in written.lower(), written
    assert WRITTEN_LIKELIHOOD.match(written), written

    if written == "<.01":
        assert likelihood < 0.01, "the words say it is below a hundredth, so it has to be"
    elif written == ">.99":
        assert likelihood > 0.99, (
            "the words say it is above ninety-nine hundredths, so it has to be"
        )
    else:
        # Half a unit of the second figure: the most that rounding to two of them
        # can move a number. Both sides are read as exact decimals so that the
        # comparison needs no slack of its own.
        half_the_second_figure = Decimal(1).scaleb(Decimal(written).adjusted() - 1) / 2
        assert abs(Decimal(repr(likelihood)) - Decimal(written)) <= half_the_second_figure, written
        # And the printed figures always land between the two guards' own numbers,
        # because anything below rounds under `<.01` and anything above rounds to
        # one. Read off the guard words themselves so the bounds cannot drift.
        assert Decimal("0.01") <= Decimal(written) <= Decimal("0.99"), written


def test_a_likelihood_is_written_by_the_rule_on_the_cases_that_decide_it() -> None:
    """The boundary, pinned on every case that decides where it sits.

    *Round to two significant figures, then use a guard word exactly when it is
    true of the rounded number.* Everything a careless reading of that sentence
    gets wrong is in the table: whether the guards' own numbers print, what happens
    when rounding carries across a guard, what happens when it carries into the
    next place, and the two ends of the scale.

    The browser writes the same rule as `toTwoFigures` in
    `frontend/src/components/BeliefChip.tsx`. This table states the rule, so it
    catches the engine drifting from it — it cannot catch the two implementations
    drifting from each other, and running the same rows through both is still owed
    where the two stacks meet.
    """
    for likelihood, expected in WRITTEN_BY_THE_RULE:
        assert two_figures(likelihood) == expected, likelihood


def test_a_likelihood_that_is_not_a_number_is_refused_rather_than_written() -> None:
    """ "Not a number" and the infinities raise; they are never quietly written `<.01`.

    Neither can be rounded to two significant figures, and writing a modest `<.01`
    for one would put a likelihood on screen that nothing computed — the one state
    this product refuses to show, arrived at by repairing rather than rejecting.
    Neither can reach here from a world either: a likelihood that is not a real
    number between 0 and 1 cannot be built into a `Belief` at all. So one arriving
    is a broken promise between two pieces of our own code, and it is said out loud.
    """
    for not_a_number in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="real number"):
            two_figures(not_a_number)


# --- The one sentence beside the list --------------------------------------


@given(st.data())
@many
def test_summary_matches_the_template(data: st.DataObject) -> None:
    """The sentence is one of two fixed templates with its blanks filled in, and never prose."""
    graph = data.draw(graphs())
    second = data.draw(branches(graph))
    answer = _compared(graph, data.draw(branches(graph)), second)

    pattern = FIRST_SENTENCE if answer.rows else SECOND_SENTENCE
    assert pattern.match(answer.summary), answer.summary
    assert second.label in answer.summary

    untouched = sum(1 for one in answer.claims.values() if one.state == "unchanged")
    assert f"{untouched} {'claim' if untouched == 1 else 'claims'} untouched" in answer.summary


def test_the_summary_says_so_when_no_ending_moved() -> None:
    """Changing something and moving no ending is a real answer, and gets its own sentence.

    The user's own number is not pushed through the map, so writing one down moves
    nothing at all. An empty list with no sentence beside it reads as a bug; a
    sentence saying nothing at an ending moved is what actually happened.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending"),),
    )
    mine = Believe(target="top", belief=Belief(p=0.9, lo=0.8, hi=0.95, owner="user"))

    answer = _compared(graph, _branch(identifier="base"), _branch(mine))

    assert SECOND_SENTENCE.match(answer.summary), answer.summary
    assert answer.rows == ()


def test_a_warning_either_world_carried_is_said_once() -> None:
    """Both worlds are built from one map, so most warnings would otherwise be said twice."""
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=7.5),),
    )

    answer = _compared(graph, _branch(identifier="base"), _branch(Do(target="top", value=True)))

    assert len(answer.warnings) == 1
    assert "second look" in answer.warnings[0]


# --- The worked example, as a rail -----------------------------------------


def test_the_hormuz_rail_reads_the_way_the_story_reads() -> None:
    """The shipped example's change list, pinned by its directions and its order.

    Four sentences a person can check, and not one number among them. The rail is
    exactly the endings that shifted, in rank order. Both endings that hang off the
    Brent claim fall, because the strike ends the state the whole chain rests on.
    The claim reached only through a feedback arrow is identical to the byte, and
    the strike itself is a claim the base map has never heard of.

    Values are deliberately absent, and so are counts of rows. The example is a
    curated one whose illustrative inputs may be tuned, so a test that pinned
    numbers — or pinned how many endings the branch happens to reach — would break
    every time somebody made the example read better, which is exactly what tuning
    is for.
    """
    base = _hormuz_world(None)
    strike = _hormuz_world(HORMUZ_THEN_STRIKE)
    answer = diff(base, strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(answer, list), answer

    endings = {one.id for one in HORMUZ.propositions if one.kind in {"market", "not_tradeable"}}
    listed = [one.target for one in answer.rows]
    assert set(listed) <= endings, listed
    assert set(listed) == {one for one in endings if answer.claims[one].state == "shifted"}, listed
    assert listed == sorted(
        listed, key=lambda one: -next(row.rank for row in answer.rows if row.target == one)
    ), "the rail is not in rank order"

    by_name = {one.target: one for one in answer.rows}
    assert by_name["M1"].peak_delta < 0.0
    assert by_name["M2"].peak_delta < 0.0

    assert answer.claims["R"].state == "unchanged"
    assert base.series["R"] == strike.series["R"]
    assert base.beliefs["R"] == strike.beliefs["R"]
    assert answer.claims["S"].state == "added"

    top = next(one for one in HORMUZ.propositions if one.id == answer.rows[0].target)
    assert top.claim.rstrip(".") in answer.summary
    assert HORMUZ_THEN_STRIKE.label in answer.summary


# --- One claim at a time ---------------------------------------------------


@given(st.data())
@a_few
def test_a_sweep_covers_every_claim_of_any_map(data: st.DataObject) -> None:
    """One row per claim, every ending on every row, over maps nobody wrote by hand.

    A sweep is one whole run of the engine per claim, and the statement being
    checked is which rows exist rather than what their numbers are.
    """
    graph = data.draw(graphs())
    world = _world(graph, data.draw(branches(graph)))

    swept = sensitivity(world)

    assert [one.flipped for one in swept] == [one.id for one in world.graph.propositions]
    endings = {
        one.id for one in world.graph.propositions if one.kind in {"market", "not_tradeable"}
    }
    for row in swept:
        assert set(row.deltas) == endings
        assert row.to is (world.beliefs[row.flipped].p < 0.5)
        assert all(-1.0 <= value <= 1.0 for value in row.deltas.values())


def test_a_sweep_leaves_the_world_it_was_given_alone() -> None:
    """Sweeping a world changes nothing about it: every map here is frozen."""
    world = _hormuz_world(None)
    before = world.model_dump_json()

    sensitivity(world)

    assert world.model_dump_json() == before


def test_a_sweep_works_from_a_world_that_already_holds_a_branch() -> None:
    """A world a branch was folded onto can still be swept, one claim at a time.

    The sweep works from what the branch left behind — the map, the values its
    edits fixed, day zero and the seed — and a world carries all four. It needs
    nothing else: there is no record of a supposition something undermined to hand
    back, because nothing undermines a supposition (decision record 0017).
    """
    world = _hormuz_world(HORMUZ_THEN_STRIKE)
    assert world.branch_id == HORMUZ_THEN_STRIKE.id
    assert world.retractions == ()

    swept = sensitivity(world)

    assert [one.flipped for one in swept] == [one.id for one in world.graph.propositions]


# --- The one rule for choosing a route, and the walk that applies it -------


def a_route_map(arrows: list[tuple[str, str, str]]) -> Graph:
    """Build a small map from `(cause, effect, provenance)` triples, in that order."""
    names = []
    for cause, effect, _ in arrows:
        for one in (cause, effect):
            if one not in names:
                names.append(one)
    claims = tuple(
        Proposition(
            id=name,
            claim=f"Claim {name}.",
            kind="hypothesis" if index == 0 else ("market" if name == "T" else "event"),
            persistence="event",
            resolution=Resolution(
                criteria="A test two people reading it would agree on.",
                source="A named judge.",
                by=date(2026, 11, 1),
            ),
            prior=Belief(p=0.4, lo=0.2, hi=0.6, owner="model"),
            beliefs=Beliefs(model=Belief(p=0.4, lo=0.2, hi=0.6, owner="model")),
            payoff=(
                ContractPayoff(venue="Somewhere", contract_id="c-1", title="Does it?", side="yes")
                if name == "T"
                else None
            ),
        )
        for index, name in enumerate(names)
    )
    links = tuple(
        Link(
            id=f"arrow-{position}",
            source=cause,
            target=effect,
            mode="sustain",
            strength=0.5,
            lag=1.0,
            shape="step",
            rationale="The cause moves the effect, and here is how.",
            sources=(Source(url="https://example.test/page", title="A page"),)
            if provenance in ("documented", "historical", "market_implied")
            else (),
            provenance=provenance,  # type: ignore[arg-type]
        )
        for position, (cause, effect, provenance) in enumerate(arrows)
    )
    return Graph(id="a-route-map", propositions=claims, links=links, hypothesis_id=names[0])


def test_a_routes_width_is_always_the_weakest_arrow_on_that_very_route() -> None:
    """The invariant a stale entry in the walk's own queue could break (2026-09-20).

    The search pushes a claim onto its queue each time it finds a better route to
    it, and an entry that has since been beaten still comes off. Read without a
    check, that pairs one route's width with another route's path — two halves of
    two different answers, handed out as one. The guard is the ordinary one: an
    entry that is no longer the best route to its claim is dropped where it is
    popped.
    """
    graph = a_route_map(
        [
            ("S", "X", "asserted"),
            ("S", "Y", "documented"),
            ("X", "A", "documented"),
            ("Y", "A", "asserted"),
            ("A", "T", "documented"),
            ("X", "T", "argued"),
        ]
    )

    routes = best_backed_routes(graph, frozenset({"S"}))

    for claim_id, route in routes.items():
        along = [
            PROVENANCE_WEIGHT[one.provenance]
            for step, next_step in pairwise(route.path)
            for one in graph.links
            if one.source == step and one.target == next_step
        ]
        assert route.path[-1] == claim_id
        assert route.path[0] == "S"
        assert route.width == (min(along) if along else NO_ARROW_TO_WEAKEN)


def test_two_equally_backed_routes_are_separated_by_the_shorter_one() -> None:
    """The rule's own second clause, and the reproducer that found it missing.

    Three routes reach C. `S -> C` is asserted and worth 0.3. `S -> B -> C` and
    `S -> A -> B -> C` are both worth 0.5, because both run through the same
    weakest arrow, so the shorter of the two wins under the rule this function's
    own docstring states.

    A one-pass walk hands back the longer one: B is reached by `S -> B` worth 0.5
    and then improved to `S -> A -> B` worth 0.9, and the narrower route to B —
    the one that would have given the *shorter* route to C — is gone by the time
    C is reached. Keeping one best state per claim cannot work, because a claim
    reached by a wider route can be a worse place to continue from than the same
    claim reached by a narrower one. Fixed 2026-09-21 with the two-pass walk.
    """
    graph = a_route_map(
        [
            ("S", "A", "historical"),
            ("B", "C", "simulated"),
            ("S", "T", "simulated"),
            ("S", "C", "asserted"),
            ("B", "T", "asserted"),
            ("A", "B", "documented"),
            ("S", "B", "simulated"),
        ]
    )

    routes = best_backed_routes(graph, frozenset({"S"}))

    assert routes["C"].width == 0.5
    assert routes["C"].path == ("S", "B", "C")


def test_two_equally_backed_routes_of_one_length_take_the_earlier_arrow() -> None:
    """And the rule's third clause, so nothing is left to whichever the search reached."""
    graph = a_route_map(
        [
            ("S", "X", "documented"),
            ("S", "Y", "documented"),
            ("X", "A", "documented"),
            ("Y", "A", "documented"),
        ]
    )

    routes = best_backed_routes(graph, frozenset({"S"}))

    assert routes["A"].width == 1.0
    assert routes["A"].path == ("S", "X", "A")


# --- The route rule, read literally, as the oracle -------------------------
#
# The fast walk is two passes and a proof; the rule itself is one sentence.
# These check the first against the second over maps the strategies build, which
# is the only way to know the proof was right. Designed by the domain's owner
# with a reference implementation and a brute-force oracle; brought in here and
# applied to `best_backed_routes` on 2026-09-21.


def every_route_from(
    graph: Graph, subject: PropositionId, climbing: bool
) -> list[tuple[tuple[PropositionId, ...], tuple[int, ...], float]]:
    """Walk every route out of one claim, with no cleverness at all.

    A route is a walk over **states** — a claim together with whether it is still
    climbing against the arrows — and no state is visited twice, which is what
    stops a route going round in circles. A claim can appear twice only by being
    climbed through and then descended through, which is the one shape an
    observation's two halves allow.

    Args:
        graph: The map to walk.
        subject: Where every route starts.
        climbing: Whether it starts by climbing against the arrows.

    Returns:
        One entry per route: the claims it passes through, the arrows it walks
        along in order, and what its weakest arrow is worth.
    """
    at = {arrow.id: position for position, arrow in enumerate(graph.links)}
    arrows = [
        (one.source, one.target, PROVENANCE_WEIGHT[one.provenance], at[one.id])
        for one in _ordinary_arrows(graph)
    ]
    found: list[tuple[tuple[PropositionId, ...], tuple[int, ...], float]] = []

    def walk(
        here: PropositionId,
        still_climbing: bool,
        seen: frozenset[tuple[PropositionId, bool]],
        claims: tuple[PropositionId, ...],
        used: tuple[int, ...],
        narrowest: float,
    ) -> None:
        found.append((claims, used, narrowest))
        if still_climbing and (here, False) not in seen:
            walk(here, False, seen | {(here, False)}, claims, used, narrowest)
        for source, target, worth, position in arrows:
            if still_climbing and target == here:
                there = source
            elif not still_climbing and source == here:
                there = target
            else:
                continue
            if (there, still_climbing) in seen:
                continue
            walk(
                there,
                still_climbing,
                seen | {(there, still_climbing)},
                (*claims, there),
                (*used, position),
                min(narrowest, worth),
            )

    walk(subject, climbing, frozenset({(subject, climbing)}), (subject,), (), NO_ARROW_TO_WEAKEN)
    return found


def the_rule_read_literally(
    graph: Graph,
    subjects: frozenset[PropositionId],
    observed: frozenset[PropositionId] = frozenset(),
) -> dict[PropositionId, tuple[float, tuple[PropositionId, ...]]]:
    """The documented rule over every route there is: widest, then shortest, then earliest.

    Written as one sort key so that the three clauses are unmistakably in that
    order and nothing else is in it.
    """
    on_the_map = {one.id for one in graph.propositions}
    best: dict[PropositionId, tuple[float, int, tuple[int, ...], tuple[PropositionId, ...]]] = {}
    for subject in sorted(subjects):
        if subject not in on_the_map:
            continue
        for walked, used, narrowest in every_route_from(graph, subject, subject in observed):
            here = walked[-1]
            offered = (min(NO_ARROW_TO_WEAKEN, narrowest), len(used), used, walked)
            standing = best.get(here)
            if standing is None or (-offered[0], offered[1], offered[2]) < (
                -standing[0],
                standing[1],
                standing[2],
            ):
                best[here] = offered
    return {here: (one[0], one[3]) for here, one in best.items()}


@given(graphs(), st.data())
@many
def test_the_fast_walk_agrees_with_the_rule_read_literally(
    graph: Graph, data: st.DataObject
) -> None:
    """Two passes and a proof against one sentence and no cleverness.

    The proof: a route reaches a claim with bottleneck `W` if and only if every
    arrow on it is worth at least `W`, so the best routes are exactly the routes
    of the map with every thinner arrow set aside. This is what says the proof
    was right — and the same maps catch the one-pass walk that was here before.
    """
    subject = data.draw(st.sampled_from([one.id for one in graph.propositions]))
    climbing = data.draw(st.booleans())
    subjects = frozenset({subject})
    observed = subjects if climbing else frozenset()

    fast = best_backed_routes(graph, subjects, observed)
    slow = the_rule_read_literally(graph, subjects, observed)

    assert set(fast) == set(slow)
    for claim_id, route in fast.items():
        width, path = slow[claim_id]
        assert route.width == pytest.approx(width), claim_id
        assert route.path == path, claim_id
