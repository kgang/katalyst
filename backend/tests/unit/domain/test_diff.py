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

import re
from datetime import date, timedelta
from itertools import pairwise

import networkx
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
    Refine,
    Resolution,
    Retune,
    World,
    apply,
    diff,
    introduced_by,
    propagate,
    sensitivity,
)
from katalyst.domain.diff import PROVENANCE_WEIGHT, SWEEP_VERSIONS, SWEEP_WORLDS
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE
from tests.strategies import branches, graphs

many = settings(max_examples=20, deadline=None)
a_few = settings(max_examples=8, deadline=None)

SMALL = {"versions": 16, "worlds": 4}
"""The budget the tests over generated maps run at, and why it is not the shipped one.

Sixteen versions of the map and four worlds under each is sixty-four draws rather
than sixteen thousand, and a difference costs four runs of the engine. Every rule
these tests check — which word a claim gets, which endings are listed and in what
order, what the sentence says — is true at any budget; only how steady the
numbers are depends on it.
"""

FULL = {"versions": 2_000, "worlds": 8}
"""The shipped budget, for the handful of tests that are about a measured number."""

DAY_ZERO = date(2026, 1, 1)
"""Day zero for the generated maps, which carry resolve-by dates from 2026 onwards."""

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

FIRST_SENTENCE = re.compile(
    r'^".+" moves .+ from [<>]?\.\d+ to [<>]?\.\d+ by \d{4}-\d{2}-\d{2} '
    r"and leaves \d+ claims? untouched\.$"
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


def _world(graph: Graph, branch: Branch, **budget: int) -> World:
    """Fold a branch onto a map, work the numbers through, and say which branch it was."""
    folded = apply(graph, branch)
    if isinstance(folded, list):
        # A branch nobody wrote by hand sometimes cannot be folded: splitting a
        # claim is not built yet, and an insert can reuse an identifier. Those
        # are discarded rather than quietly passed.
        assume(False)
    assert not isinstance(folded, list)
    left_behind, fixed = folded
    world = propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        **(budget or SMALL),
    )
    return world.model_copy(update={"branch_id": branch.id})


def _hormuz_world(branch: Branch | None, **budget: int) -> World:
    """The same, on the shipped worked example and its own day zero."""
    folded = apply(HORMUZ, branch or _branch())
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    world = propagate(
        left_behind,
        fixed,
        as_of=FIXTURE_DATE,
        seed=SEED,
        introduced_by=introduced_by(branch or _branch()),
        **(budget or FULL),
    )
    return world.model_copy(update={"branch_id": branch.id if branch is not None else None})


def _compared(graph: Graph, first: Branch, second: Branch, **budget: int) -> Diff:
    """Two worlds from one map and one seed, and the difference between them."""
    answer = diff(
        _world(graph, first, **budget),
        _world(graph, second, **budget),
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
        refused = diff(first, second.model_copy(update=wrong), edit_in_words="a name")
        assert isinstance(refused, list), wrong
        assert len(refused) == 1
        assert refused[0].message.endswith(".")
        assert refused[0].subject not in refused[0].message


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


def test_shifted_needs_agreement() -> None:
    """Two ranges can overlap across half their width while every version moves the same way.

    This is the single most likely way to get a difference wrong, and it is
    measured here on the shipped example rather than argued. Supposing the strait
    opens moves Brent-below-$68 on its own resolve-by day, and the two ranges
    overlap heavily — because each one is wide for its own reason, which is that
    we are unsure what number to give you. The *difference* between them is tight
    and all one way, because both worlds were worked out from the same numbers.
    An engine that compared the two ranges would report no change about the
    clearest change on the map.
    """
    base = _hormuz_world(None)
    supposed = _hormuz_world(_branch(Do(target="H", value=True, at=FIXTURE_DATE)))
    answer = diff(base, supposed, edit_in_words="Hormuz opens")
    assert not isinstance(answer, list), answer

    before, after = base.beliefs["B"], supposed.beliefs["B"]
    overlap = min(before.hi, after.hi) - max(before.lo, after.lo)
    narrower = min(before.hi - before.lo, after.hi - after.lo)
    assert overlap > 0.3 * narrower, "the two ranges were expected to overlap heavily"

    moved = answer.claims["B"]
    assert moved.state == "shifted"
    assert moved.agreement is not None and moved.agreement > 0.9
    assert moved.delta is not None and moved.delta > 0.0


@given(st.data())
@many
def test_shifted_is_exactly_the_two_halves(data: st.DataObject) -> None:
    """A claim is `shifted` exactly when it moved far enough **and** the versions agreed.

    Both numbers are carried on every claim both worlds hold, so the rule that
    decided the word can be read straight off the answer without recomputing
    anything — which is the whole reason they are carried.
    """
    graph = data.draw(graphs())
    answer = _compared(graph, data.draw(branches(graph)), data.draw(branches(graph)))

    for one in answer.claims.values():
        if one.state in {"added", "killed"} or one.delta is None or one.agreement is None:
            continue
        both_halves = abs(one.delta) >= 0.005 and one.agreement >= 0.90
        assert (one.state == "shifted") == both_halves, one


def test_killed_means_forced_false() -> None:
    """`killed` is the claim being forced false, and a claim that merely fell a long way is not.

    Stretching the word to cover "the likelihood got low" would tell the user
    their argument was cut when it was merely losing. On the strike branch the
    strait's own claim falls from about a third to under a tenth and is `shifted`;
    add one edit forcing the premium claim false and that one, and only that one,
    is `killed`.
    """
    base = _hormuz_world(None, **SMALL)
    strike = _hormuz_world(HORMUZ_THEN_STRIKE, **SMALL)
    falling = diff(base, strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(falling, list), falling

    assert falling.claims["H"].state == "shifted"
    assert falling.claims["H"].after is not None and falling.claims["H"].after < 0.2
    assert all(one.state != "killed" for one in falling.claims.values())

    cut = _hormuz_world(_branch(Do(target="C", value=False, at=FIXTURE_DATE)), **SMALL)
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
        _hormuz_world(None, **SMALL),
        _hormuz_world(HORMUZ_THEN_STRIKE, **SMALL),
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
        assert abs(row.peak_delta) >= max(gaps) - 1e-12
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
        graph, _branch(identifier="base"), _branch(Observe(target="seen", value=True)), **FULL
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
    answer = _compared(graph, _branch(identifier="base"), branch)

    for claim_id, one in answer.claims.items():
        if claim_id in reach:
            continue
        assert one.state == "unchanged", claim_id
        assert one.delta == 0.0, claim_id


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

    Four sentences a person can check, and not one number among them. The two
    tradeable endings fall and the one nobody quotes rises; the one that rises
    moves furthest and still ranks last, because the only arrow into it is the
    weakest on the map and the rank's second factor says so; the claim reached only
    through a feedback arrow is identical to the byte; and the strike itself is a
    claim the base map has never heard of.

    Values are deliberately absent. The example is a curated one whose illustrative
    inputs may be tuned, so a test that pinned numbers would break every time
    somebody made the example read better — which is exactly what tuning is for.
    """
    base = _hormuz_world(None)
    strike = _hormuz_world(HORMUZ_THEN_STRIKE)
    answer = diff(base, strike, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(answer, list), answer

    assert [one.target for one in answer.rows] == ["M1", "M2", "N1"]
    by_name = {one.target: one for one in answer.rows}
    assert by_name["M1"].peak_delta < 0.0
    assert by_name["M2"].peak_delta < 0.0
    assert by_name["N1"].peak_delta > 0.0
    assert abs(by_name["N1"].peak_delta) == max(abs(one.peak_delta) for one in answer.rows)
    assert by_name["N1"].rank == min(one.rank for one in answer.rows)

    assert answer.claims["R"].state == "unchanged"
    assert base.series["R"] == strike.series["R"]
    assert base.beliefs["R"] == strike.beliefs["R"]
    assert answer.claims["S"].state == "added"

    contract = next(one for one in HORMUZ.propositions if one.id == "M1")
    assert contract.claim.rstrip(".") in answer.summary
    assert HORMUZ_THEN_STRIKE.label in answer.summary
    assert "leaves 1 claim untouched" in answer.summary


# --- One claim at a time ---------------------------------------------------


def test_sensitivity_rows_name_their_budget() -> None:
    """A sweep gives one row per claim, every ending on every row, and says what it ran at.

    A sweep is one whole run of the engine per claim, so it runs at a quarter of
    the versions the shipped budget uses — and every row carries that budget, so
    nobody lays a swept number beside a full-budget one without noticing. The rows
    come back unranked on purpose: which direction hurts depends on the trade, and
    this has no idea which trade is being run.
    """
    world = _hormuz_world(None)

    swept = sensitivity(world)

    assert [one.flipped for one in swept] == [one.id for one in HORMUZ.propositions]
    endings = {one.id for one in HORMUZ.propositions if one.kind in {"market", "not_tradeable"}}
    for row in swept:
        assert (row.versions, row.worlds) == (SWEEP_VERSIONS, SWEEP_WORLDS)
        assert (row.versions, row.worlds) == (250, 8)
        assert set(row.deltas) == endings
        assert row.to is (world.beliefs[row.flipped].p < 0.5)
    assert any(abs(value) > 0.01 for row in swept for value in row.deltas.values())


@given(st.data())
@a_few
def test_a_sweep_covers_every_claim_of_any_map(data: st.DataObject) -> None:
    """One row per claim, every ending on every row, over maps nobody wrote by hand.

    Run at a reduced budget, like every other test over generated maps here: a
    sweep is a run of the engine per claim, and the statement being checked is
    which rows exist rather than how steady their numbers are.
    """
    graph = data.draw(graphs())
    world = _world(graph, data.draw(branches(graph)))

    swept = sensitivity(world, **SMALL)

    assert [one.flipped for one in swept] == [one.id for one in world.graph.propositions]
    endings = {
        one.id for one in world.graph.propositions if one.kind in {"market", "not_tradeable"}
    }
    for row in swept:
        assert (row.versions, row.worlds) == (SMALL["versions"], SMALL["worlds"])
        assert set(row.deltas) == endings
        assert row.to is (world.beliefs[row.flipped].p < 0.5)
        assert all(-1.0 <= value <= 1.0 for value in row.deltas.values())


def test_a_sweep_leaves_the_world_it_was_given_alone() -> None:
    """Sweeping a world changes nothing about it: every map here is frozen."""
    world = _hormuz_world(None, **SMALL)
    before = world.model_dump_json()

    sensitivity(world, **SMALL)

    assert world.model_dump_json() == before


def test_a_sweep_works_from_a_world_that_already_holds_a_branch() -> None:
    """A world with a supposition already undermined can still be swept.

    The sweep works the same map through again, and a supposition that something
    undermined has to be able to name the edit responsible. The world already
    knows: it carries one record per supposition that ended, and each names both
    the arrow and the edit.
    """
    world = _hormuz_world(HORMUZ_THEN_STRIKE, **SMALL)
    assert world.retractions, "the strike branch is the one that undermines a supposition"

    swept = sensitivity(world, **SMALL)

    assert [one.flipped for one in swept] == [one.id for one in world.graph.propositions]
