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
import numpy
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
    Refine,
    Resolution,
    Retune,
    World,
    apply,
    diff,
    introduced_by,
    propagate,
    sensitivity,
    versions_of,
)
from katalyst.domain.diff import (
    AGREEING_AT_LEAST,
    MOVED_AT_LEAST,
    PROVENANCE_WEIGHT,
    SWEEP_VERSIONS,
    SWEEP_WORLDS,
    _agreement_on,
    _counting_for,
    _read_on,
    _two_figures,
)
from katalyst.domain.propagation import Numbers, Versions
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


def _weights_the_number_was_read_with(behind: Versions, claim_id: str) -> Numbers:
    """How much each version counted when this world read this claim's own number.

    Written out from the chapter rather than taken from the code, so the two agree
    by arithmetic and not by sharing a line. Every version counts the same, unless
    what was observed is evidence about this claim — then each version counts by
    the share of its worlds that survived what was observed.
    """
    if claim_id in behind.reweighted:
        return behind.weights
    return numpy.ones_like(behind.weights)


def _one_number(per_version: Numbers, counting: Numbers) -> float:
    """Average one claim's version-by-version answers the way a world reads its number."""
    return float(numpy.clip((per_version * counting).sum() / counting.sum(), 0.0, 1.0))


def _count_every_version_the_same(behind_a: Versions, behind_b: Versions, claim_id: str) -> Numbers:
    """Stand in for the weights so that every version counts 1, whatever was observed."""
    del behind_b, claim_id
    return numpy.ones_like(behind_a.weights)


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


# --- The direction is read with the number's own weights -------------------


def _observing(target: str) -> Branch:
    """A branch of one edit: this claim actually came true."""
    return _branch(Observe(target=target, value=True), identifier=f"br_observe_{target.lower()}")


def test_an_observation_puts_a_row_on_the_rail() -> None:
    """Saying Brent settled below $68 puts the two tradeable endings on the change list.

    This is the button that used to look as if it did nothing. An observation is
    made by throwing away the worlds it did not happen in, and on the worked
    example some versions of the map lose every one of their eight worlds. Such a
    version weighs nothing in the number, so it must weigh nothing in the
    direction; counting it anyway dragged both endings a hair under the 90% bar and
    emptied the rail. Read the direction with the weights the number was read with
    and both endings are on the rail, rising, with the fixed sentence beside them.

    Directions and orderings only. The example map is a curated one whose
    illustrative inputs may be tuned, so nothing here pins a value.
    """
    base = _hormuz_world(None)
    learned = _hormuz_world(_observing("B"))
    answer = diff(base, learned, edit_in_words="Brent settled below $68")
    assert not isinstance(answer, list), answer

    behind = versions_of(learned)
    assert bool((behind.weights == 0.0).any()), "this observation empties some versions"

    assert [one.target for one in answer.rows] == ["M1", "M2"]
    for row in answer.rows:
        assert answer.claims[row.target].state == "shifted"
        assert row.peak_delta > 0.0, "cheap Brent is evidence for both market claims"
        assert row.agreement >= AGREEING_AT_LEAST
    assert FIRST_SENTENCE.match(answer.summary), answer.summary


def test_a_dead_version_does_not_vote() -> None:
    """A version left with no surviving world weighs nothing, so it says nothing about direction.

    Such a version reports no number at all, and its weight is zero, so letting it
    argue about which way the number moved would let a version that contributed
    nothing to either answer outvote the ones that did. The test hands every dead
    version the loudest opinion it could have — each one made to point the opposite
    way — and the answer does not move by a bit.
    """
    base = _hormuz_world(None)
    learned = _hormuz_world(_observing("B"))
    behind_a, behind_b = versions_of(base), versions_of(learned)
    dead = behind_b.weights == 0.0
    assert bool(dead.any()), "this observation empties some versions"

    for claim in learned.graph.propositions:
        before = behind_a.likelihood[claim.id][:, _read_on(base, claim)]
        after = behind_b.likelihood[claim.id][:, _read_on(learned, claim)]
        move = learned.beliefs[claim.id].p - base.beliefs[claim.id].p
        counting = _counting_for(behind_a, behind_b, claim.id)
        assert bool((counting[dead] == 0.0).all()), claim.id

        shouting = after.copy()
        shouting[dead] = before[dead] - move
        assert _agreement_on(before, shouting, move, counting) == _agreement_on(
            before, after, move, counting
        ), claim.id

    # And the corner where nothing at all survived anywhere: every version counts
    # the same again, which is exactly what the band does in the same corner, so
    # the number and its direction stay read the same way and nothing is divided
    # by nothing. The world already carries a loud warning about it.
    impossible = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.0, 0.0, 0.0)),
            _claim("ending", kind="market"),
        ),
        (_arrow("top", "ending"),),
    )
    gone = _compared(impossible, _branch(identifier="base"), _observing("top"))
    assert all(
        one.agreement is None or 0.0 <= one.agreement <= 1.0 for one in gone.claims.values()
    ), gone.claims


def test_direction_is_read_with_the_numbers_own_weights() -> None:
    """One rule: the direction is read with the same weights the number was read with.

    The test finds out from the engine which weights each number was read with,
    rather than being told: it rebuilds each world's own likelihood for each claim
    from that world's version-by-version answers — every version counting the same
    for a claim the observation is not evidence about, each version counting by the
    share of its worlds that survived for a claim it is — and checks the world's own
    number comes back. Then it checks the same-direction share is counted with those
    very weights, a version counting for the move by as much as it counted in both
    numbers. The last line is the teeth: on this observation at least one claim has
    to read differently when every version is counted the same, or the rule would
    be about nothing.
    """
    base = _hormuz_world(None)
    learned = _hormuz_world(_observing("B"))
    answer = diff(base, learned, edit_in_words="Brent settled below $68")
    assert not isinstance(answer, list), answer
    behind_a, behind_b = versions_of(base), versions_of(learned)

    read_another_way = 0
    for claim in learned.graph.propositions:
        before = behind_a.likelihood[claim.id][:, _read_on(base, claim)]
        after = behind_b.likelihood[claim.id][:, _read_on(learned, claim)]
        in_a = _weights_the_number_was_read_with(behind_a, claim.id)
        in_b = _weights_the_number_was_read_with(behind_b, claim.id)
        assert _one_number(before, in_a) == pytest.approx(base.beliefs[claim.id].p), claim.id
        assert _one_number(after, in_b) == pytest.approx(learned.beliefs[claim.id].p), claim.id

        counting = _counting_for(behind_a, behind_b, claim.id)
        assert bool((counting == numpy.minimum(in_a, in_b)).all()), claim.id

        move = learned.beliefs[claim.id].p - base.beliefs[claim.id].p
        assert answer.claims[claim.id].agreement == _agreement_on(before, after, move, counting)
        evenly = _agreement_on(before, after, move, numpy.ones_like(counting))
        read_another_way += evenly != answer.claims[claim.id].agreement

    assert read_another_way, "counting every version the same has to give a different answer here"


def test_an_edit_that_is_not_an_observation_is_unchanged_by_the_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Five of the six edits weight nothing, so the difference is the same read either way.

    Only an observation makes a version count for less than another, so under every
    other edit reading the direction with the weights has to be the very same
    arithmetic as reading it without them — not close, the same bytes. Nothing here
    is compared against a number somebody typed: the whole difference is computed
    twice, once as the code does it and once with every version forced to count the
    same, and the two are asked to serialize identically.
    """
    base = _hormuz_world(None)
    for branch in (HORMUZ_THEN_STRIKE, _branch(Do(target="H", value=True, at=FIXTURE_DATE))):
        second = _hormuz_world(branch)
        behind = versions_of(second)
        assert not behind.reweighted, "nothing on this branch was observed"
        assert bool((behind.weights == 1.0).all())

        as_built = diff(base, second, edit_in_words=branch.label)
        assert not isinstance(as_built, list), as_built

        with monkeypatch.context() as forced:
            forced.setattr(diff_module, "_counting_for", _count_every_version_the_same)
            evenly = diff(base, second, edit_in_words=branch.label)
        assert not isinstance(evenly, list), evenly
        assert evenly.model_dump_json() == as_built.model_dump_json(), branch.label


def test_a_claim_moved_only_by_reweighting_says_so() -> None:
    """A claim with no causes moves under an observation only by how much each version counts.

    Learning that the insurance premium fell moves the strait's own claim — the
    hypothesis, which nothing on this map causes. Inside one version that claim is
    its own prior in every world, so throwing worlds away cannot change what the
    version says about it, and every version that counts gives exactly the same
    number in both worlds. The whole move is the reweighting; the same-direction
    share is zero by construction, not by disagreement. The four states are left
    alone and the difference says so in one field of its own, which the Inspector
    turns into one sentence.
    """
    base = _hormuz_world(None)
    learned = _hormuz_world(_observing("C"))
    answer = diff(base, learned, edit_in_words="the premium fell")
    assert not isinstance(answer, list), answer

    strait = answer.claims["H"]
    assert strait.moved_only_by_reweighting
    assert strait.state == "unchanged", "the four states are untouched"
    assert strait.delta is not None and abs(strait.delta) >= MOVED_AT_LEAST
    assert strait.agreement == 0.0, "no version that counts moved at all, either way"

    # It is a claim with no causes, read off the map rather than asserted, and it
    # is the only claim on this map in that position.
    into_it = [one for one in learned.graph.links if one.target == "H" and not one.reflexive]
    assert not into_it, "the strait's own claim has no causes on this map"
    assert [one for one in answer.claims.values() if one.moved_only_by_reweighting] == [strait]

    # No edit that is not an observation can ever set it: with every version
    # counting the same, identical version-by-version answers give identical
    # numbers, so the move is exactly nothing and lands below the floor.
    struck = diff(base, _hormuz_world(HORMUZ_THEN_STRIKE), edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(struck, list), struck
    assert not any(one.moved_only_by_reweighting for one in struck.claims.values())


# --- Two corners where the weights run out ---------------------------------


def test_a_world_that_kept_nothing_does_not_erase_the_other_worlds_weights() -> None:
    """Each world falls back on its own, and only then are the two counted together.

    A world in which nothing at all survived what was observed reads every version
    the same, because there is no surviving share left to weigh anything by. That
    fallback belongs to **that world**. Take the smaller of the two worlds' weights
    before letting either of them fall back, and the one that did keep survivors
    has its weights thrown away too — every version counts the same, which is what
    *neither* of the two numbers was read with, and the one sentence this whole
    rule rests on is broken in a corner.

    Reachable only branch against branch, which is why it went unseen: with a base
    world on one side that world is unweighted anyway, so the two readings happen
    to agree. Here one branch observes something that keeps some worlds and the
    other observes something that can keep none.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.5, 0.25, 0.75)),
            _claim("seen", kind="market", prior=(0.4, 0.2, 0.6)),
            _claim("impossible", kind="market", prior=(0.0, 0.0, 0.0)),
        ),
        (_arrow("top", "seen"), _arrow("top", "impossible")),
    )
    kept_some = _world(graph, _branch(Observe(target="seen", value=True), identifier="kept-some"))
    kept_none = _world(
        graph, _branch(Observe(target="impossible", value=True), identifier="kept-none")
    )
    behind_a, behind_b = versions_of(kept_some), versions_of(kept_none)

    # The corner is only the corner if one world really kept nothing, the other
    # really is weighted, and the claim is one both observations are evidence about.
    assert behind_b.weights.sum() == 0.0, "this observation was meant to keep nothing"
    assert behind_a.weights.sum() > 0.0
    assert not bool((behind_a.weights == 1.0).all()), "this observation was meant to weigh"
    assert "top" in behind_a.reweighted and "top" in behind_b.reweighted

    # The starved world counts every version the same — on its own, which is what
    # its own number was read with — and never hands back nothing at all.
    assert bool((behind_b.counting_for("top") == 1.0).all())
    assert behind_a.counting_for("top").sum() > 0.0

    # So the direction keeps the surviving world's own weights instead of losing
    # them, which is what taking the smaller of the two first would have done.
    counting = _counting_for(behind_a, behind_b, "top")
    assert bool((counting == behind_a.counting_for("top")).all())
    assert not bool((counting == 1.0).all()), "the weights of the world that kept some survived"

    answer = diff(kept_some, kept_none, edit_in_words="what cannot have happened")
    assert not isinstance(answer, list), answer
    assert answer.claims["top"].agreement is not None


def test_no_direction_at_all_when_no_version_counted_in_both_numbers() -> None:
    """Two branches can keep disjoint versions alive, and then there is no direction.

    Every version counted in one of the two numbers or the other and in neither
    pair, so the paired difference this whole file is built on has no pair left.
    Counting every version equally instead would report a direction read off
    versions that contributed to neither reading — a number nobody computed, which
    is the one state this product refuses to show. So the share comes back as
    nothing at all and no claim can be `shifted`. Reject, never repair.

    The map is built for it rather than waited for: one claim whose stated range
    spans nearly the whole scale, so that at two versions of two worlds each
    version draws a prior near one end or the other and comes out the same way in
    both of its worlds. Observing it true then keeps one version and observing it
    false keeps the other. Nothing here is typed in but the shape of the map; which
    version survives which observation is the engine's own answer, and the test
    asserts the disjointness it found rather than a number.
    """
    graph = _map(
        (
            _claim("either-way", kind="hypothesis", prior=(0.5, 1e-9, 1.0 - 1e-9)),
            _claim("ending", kind="market", prior=(0.5, 0.25, 0.75)),
        ),
        (_arrow("either-way", "ending", strength=0.5),),
    )
    two_of_two = {"versions": 2, "worlds": 2}
    said_true = _world(
        graph, _branch(Observe(target="either-way", value=True), identifier="yes"), **two_of_two
    )
    said_false = _world(
        graph, _branch(Observe(target="either-way", value=False), identifier="no"), **two_of_two
    )
    behind_a, behind_b = versions_of(said_true), versions_of(said_false)

    # Each world kept something of its own, and between them they kept nothing in
    # common. Without all three of those this is not the corner being tested.
    assert behind_a.counting_for("either-way").sum() > 0.0
    assert behind_b.counting_for("either-way").sum() > 0.0
    assert _counting_for(behind_a, behind_b, "either-way").sum() == 0.0

    answer = diff(said_true, said_false, edit_in_words="the other way round")
    assert not isinstance(answer, list), answer
    for claim_id, one in answer.claims.items():
        assert one.agreement is None, claim_id
        assert one.state != "shifted", claim_id
        assert not one.moved_only_by_reweighting, claim_id
    assert answer.rows == (), "no ending can be listed as moved when no direction can be read"
    assert SECOND_SENTENCE.match(answer.summary), answer.summary


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
    on_one_grid = every_version_answered_the_same(
        base, branched, [one for one in answer.claims if one not in reach]
    )
    for claim_id, one in answer.claims.items():
        if claim_id in reach:
            continue
        assert one.state == "unchanged", claim_id
        # And the reported number itself, exactly — but only where exactly is a
        # thing that can be asked. On one grid every reduction behind it is over
        # arrays of the same shape, so it is identical to the bit.
        if on_one_grid:
            assert one.delta == 0.0, claim_id


@pytest.mark.xfail(
    reason=(
        "known defect: a one-off push fires on the day its cause is settled, read off "
        "the days actually drawn. Past the 180-point cap those days are spaced out, so "
        "an edit that lengthens the window re-spaces the grid for the whole map and a "
        "push anywhere on it can start reading its cause a day later — moving a claim "
        "the edit cannot reach. Reported to the coordinator with this reproducer."
    ),
    strict=True,
)
def test_a_longer_window_moves_a_claim_it_cannot_reach() -> None:
    """Inserting a claim at one end of a map moves a claim at the other end. It must not.

    Two pieces with nothing joining them. In the second piece `cause` triggers
    `effect` through an arrow with a three-day delay, so `effect`'s clock starts on
    day 3, and `effect` in turn pushes `ending`. The edit inserts a claim in the
    **first** piece, judged a year out, which stretches the window from a month to a
    year. Nothing on the second piece is connected to what was inserted.

    But past 180 days a series is drawn at evenly spaced points instead of every
    day, and a day between two of them is read at the next one along — so day 3 is
    drawn on the short window and is not on the long one, and the push into `ending`
    starts reading `effect` on day 4 instead. `ending` moves, and no edit reached it.

    Measured when this was written: `.096` on the version-by-version answers, a
    tenth of a likelihood. That is the product's central correctness claim (INV-4,
    locality: an edit changes only what is still connected to its subject) failing
    through the sampling grid rather than along the arrows.

    **The obvious repair is not the repair.** Keeping every settled day among the
    drawn points was tried: it makes the grid depend on the settled days, so a
    supposition — which cuts arrows and so moves settled days — then re-spaces the
    grid and shifts a claim's own ancestors. That breaks INV-3, assert is not
    observe, which is worse than what it cures. The fix has to read a push's firing
    day somewhere other than off the drawn grid, and that is a design decision about
    `propagation.md`'s 180-point cap rather than a patch.
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
    assert len(base.series_days) != len(stretched.series_days), "the grid was meant to move"

    # `ending` is in the other piece; nothing the edit did can reach it.
    every_version_answered_the_same(base, stretched, ["cause", "effect", "ending"])
    behind_base, behind_stretched = versions_of(base), versions_of(stretched)
    where = {day: index for index, day in enumerate(behind_base.days)}
    for index, day in enumerate(behind_stretched.days):
        if day not in where:
            continue
        assert numpy.array_equal(
            behind_stretched.likelihood["ending"][:, index],
            behind_base.likelihood["ending"][:, where[day]],
        ), day


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
    written = _two_figures(likelihood)

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
        assert _two_figures(likelihood) == expected, likelihood


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
            _two_figures(not_a_number)


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
