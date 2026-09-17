"""What happens when a branch is folded onto a map, over maps nobody wrote by hand.

A branch is an ordered list of edits sitting beside a map nobody touches, and
`apply` is what folds one onto the other. Almost everything the product promises
rests on three laws about that fold — applying nothing changes nothing, two
branches in a row equal the two joined, and the original is never written to —
and on one rule about each edit: it may move what is still connected to its
subject in the map it leaves behind, and nothing else.

The maps come from `tests/strategies.py`. `graphs()` builds them valid by
construction; `graphs(separated=True)` builds them in two pieces with no arrow
running between them, which is what gives the locality test a claim it can pin.

**The locality test works the affected set out for itself**, from the shape of
the map, with the same graph library the rules layer uses but its own code. It
never calls `affected_set` and it never asks the fold what it touched: a test
that agrees with the code it is testing is not a test.
"""

from datetime import date

import networkx
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from katalyst.domain import (
    Belief,
    Beliefs,
    Believe,
    Branch,
    ContractPayoff,
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
    Violation,
    World,
    affected_set,
    apply,
    flatten,
    introduced_by,
    propagate,
)
from katalyst.fixtures.hormuz import (
    FIXTURE_DATE,
    HORMUZ,
    HORMUZ_THEN_STRIKE,
    STRIKE_ON_IRAN,
    STRIKE_TO_BRENT,
    STRIKE_TO_HORMUZ,
    STRIKE_TO_PREMIUM,
)
from tests.strategies import beliefs, branches, graphs, interventions, separated_pair

# Building a whole random map is slow enough that a per-example time limit would
# flake on a loaded machine without telling us anything true.
many = settings(max_examples=40, deadline=None)
a_few = settings(max_examples=20, deadline=None)

SIX_OPERATIONS: tuple[str, ...] = ("do", "observe", "insert", "retune", "refine", "believe")
"""Every way of changing a map. The locality rule is checked against each of them."""

DAY_ZERO = date(2026, 1, 1)
"""The day the windows below start on. The generated maps carry dates from 2026 onwards."""

SEED = 20261001
"""One seed, so that two worlds in a test differ by the edit between them and nothing else."""

TINY_BUDGET = {"versions": 8, "worlds": 2}
"""How many versions of the map and worlds under each these tests run at, and why so few.

The shipped engine runs two thousand versions times eight worlds, which is about
seventy milliseconds a world — far too slow to run twice per edit over hundreds of
generated maps. Locality is not a statement about how steady a number is: a claim
outside an edit's reach comes out **byte-identical** at any budget, because every
claim's random numbers come from its own identifier and an edit it cannot reach
cannot change them. Two worlds run at eight versions prove that as squarely as two
run at two thousand, and in a thousandth of the time.
"""


# --- Small things the tests below build by hand ----------------------------


def _branch(*edits: Intervention, identifier: str = "branch-under-test") -> Branch:
    """Wrap a few edits in a branch, since that is what `apply` takes."""
    return Branch(id=identifier, label="A branch written by a test", interventions=edits)


def _claim_text(graph: Graph) -> dict[str, str]:
    """Write down every claim on a map as bytes, so two maps can be compared claim by claim."""
    return {one.id: one.model_dump_json() for one in graph.propositions}


def _example_claim(identifier: str, kind: str = "event") -> Proposition:
    """One plain claim, for the small maps the example tests build by hand."""
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind=kind,  # type: ignore[arg-type]
        resolution=Resolution(
            criteria="Two readers of this sentence would agree on the answer.",
            source="The publication that would carry it.",
            by=date(2026, 12, 31),
        ),
        prior=Belief(p=0.3, lo=0.2, hi=0.4, owner="model"),
        beliefs=Beliefs(model=Belief(p=0.3, lo=0.2, hi=0.4, owner="model")),
        payoff=(
            ContractPayoff(
                venue="Polymarket",
                contract_id="something-tradeable",
                title="Will the claim written down under this name come true?",
                side="yes",
            )
            if kind == "market"
            else None
        ),
    )


def _example_arrow(source: str, target: str, reflexive: bool = False) -> Link:
    """One plain arrow, for the small maps the example tests build by hand."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="trigger",
        strength=0.5,
        lag=1.0 if reflexive else 0.0,
        shape="step",
        rationale="The first claim makes the second one more likely, for a stated reason.",
        provenance="argued",
        reflexive=reflexive,
    )


def _two_piece_map() -> Graph:
    """A small map in two pieces, written out so the affected-set table can be read off it.

    One piece is a chain — `first` to `second` to `third` to `ending` — and the
    other is `apart` to `apart-ending`. No arrow joins the two pieces, so a claim
    in one is fully separated from every claim in the other.
    """
    return Graph(
        id="map-in-two-pieces",
        propositions=(
            _example_claim("first", kind="hypothesis"),
            _example_claim("second"),
            _example_claim("third"),
            _example_claim("ending", kind="market"),
            _example_claim("apart"),
            _example_claim("apart-ending", kind="market"),
        ),
        links=(
            _example_arrow("first", "second"),
            _example_arrow("second", "third"),
            _example_arrow("third", "ending"),
            _example_arrow("apart", "apart-ending"),
        ),
        hypothesis_id="first",
    )


def _affected_from_the_shape(graph: Graph, edit: Intervention) -> set[str]:
    """Work out, from the shape of the map alone, which claims this edit may move.

    This is the affected-set table written out a second time, from the chapter
    rather than from the code, using the same graph library and none of the same
    lines. It must never call `affected_set` and must never ask the fold which
    claims it changed — a test that agrees with the code it is checking passes by
    agreeing with itself.

    The map handed in is the one the edit **leaves behind**, because that is the
    map the locality rule is about: `do` cuts the arrows into its target, and what
    was on the far side of a cut arrow is no longer connected to anything.
    """
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in graph.propositions)
    # Feedback arrows are left out, the same way the map's own loop check leaves
    # them out: nothing is worked through one in this version, so nothing an edit
    # does can travel along it.
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


def _edit_of_kind(data: st.DataObject, graph: Graph, kind: str, subject: str) -> Intervention:
    """Build one edit of the named kind whose subject is the named claim.

    For five of the six the subject is the claim the edit names. For `retune`,
    whose subject is an arrow, it is an arrow pointing at that claim — maps
    offering none are discarded rather than quietly passed.
    """
    if kind == "do":
        return Do(target=subject, value=data.draw(st.booleans()), at=None)
    if kind == "observe":
        return Observe(target=subject, value=data.draw(st.booleans()))
    if kind == "believe":
        return Believe(target=subject, belief=data.draw(beliefs(owner="user")))
    if kind == "refine":
        return Refine(
            target=subject,
            into=(_example_claim("claim-finer-0"), _example_claim("claim-finer-1")),
        )
    if kind == "insert":
        newcomer = _example_claim("claim-newcomer")
        return Insert(proposition=newcomer, links=(_example_arrow(subject, newcomer.id),))
    pointing_at_it = [one for one in graph.links if one.target == subject]
    assume(pointing_at_it)
    return Retune(
        link=data.draw(st.sampled_from(pointing_at_it)).id,
        strength=data.draw(st.floats(min_value=-4.0, max_value=4.0, allow_nan=False)),
    )


# --- The three laws a branch obeys -----------------------------------------


@given(graphs())
@many
def test_apply_empty_is_identity(graph: Graph) -> None:
    """A branch with no edits gives the map back, byte for byte.

    The base world is exactly this: the empty branch. So "the original is always
    there" is true by construction rather than by care.
    """
    folded = apply(graph, _branch())

    assert not isinstance(folded, list)
    left_behind, fixed = folded
    assert left_behind.model_dump_json() == graph.model_dump_json()
    assert fixed == ()


@given(st.data())
@many
def test_patch_concat_equals_sequential_apply(data: st.DataObject) -> None:
    """Two branches in a row give the same map as the single branch holding both lists.

    This is why continuing from a parent branch needs no machinery of its own, and
    why a difference between two worlds is free: the patch *is* the difference.

    The positions the assignments carry are checked too, because that is the one
    thing the two forms can disagree about. Folding the whole branch at once
    numbers the edits by where they sit in it. Folding it in two calls carries on
    from one past the last position already recorded, which is all a list of
    assignments can say about how many edits came before it — only a `do` and an
    `observe` record one. The two forms therefore agree exactly when the first
    branch ends on an edit that fixed a value, and otherwise the second branch's
    positions are shifted down by however many edits at the end of the first fixed
    nothing. This test pins that shift rather than looking the other way.
    """
    graph = data.draw(graphs())
    first = data.draw(branches(graph))
    second = data.draw(branches(graph))

    joined = apply(graph, _branch(*first.interventions, *second.interventions))
    one_at_a_time = apply(graph, first)

    if isinstance(one_at_a_time, list):
        assert joined == one_at_a_time
        return

    part_way, carried = one_at_a_time
    rest = apply(part_way, second, carried)
    if isinstance(rest, list):
        assert joined == rest
        return

    assert not isinstance(joined, list)
    all_at_once, fixed_at_once = joined
    step_by_step, fixed_step_by_step = rest

    assert step_by_step.model_dump_json() == all_at_once.model_dump_json()
    assert [(one.target, one.value, one.at, one.kind) for one in fixed_step_by_step] == [
        (one.target, one.value, one.at, one.kind) for one in fixed_at_once
    ]

    shift = len(first.interventions) - (max((one.by for one in carried), default=-1) + 1)
    for index, (stepped, at_once) in enumerate(zip(fixed_step_by_step, fixed_at_once, strict=True)):
        assert stepped.by == at_once.by - (0 if index < len(carried) else shift)


@given(st.data())
@many
def test_base_graph_unchanged_after_apply(data: st.DataObject) -> None:
    """The map a branch was folded onto is the same bytes after the call as before it.

    The models are frozen, so this cannot fail quietly — it fails loudly, which is
    the point of keeping the test. Every branch is computed against this map and
    every replay starts from it; change it and every stored world becomes a lie.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    before = graph.model_dump_json()

    apply(graph, branch)

    assert graph.model_dump_json() == before


@given(st.data())
@many
def test_child_branch_applies_parent_first(data: st.DataObject) -> None:
    """A chain of branches comes out as one list of edits, the oldest ancestor's first.

    Order is load-bearing: a child's edit can name an arrow that only exists
    because its parent added one, so the parent's edits have to have happened
    first. There is no merge and no rebase — it is concatenation.
    """
    graph = data.draw(graphs())
    grandparent = data.draw(branches(graph)).model_copy(
        update={"id": "branch-grandparent", "parent": None}
    )
    parent = data.draw(branches(graph)).model_copy(
        update={"id": "branch-parent", "parent": grandparent.id}
    )
    child = data.draw(branches(graph)).model_copy(
        update={"id": "branch-child", "parent": parent.id}
    )
    stored = {one.id: one for one in (grandparent, parent, child)}

    in_order = flatten(stored, child.id)

    assert in_order == (
        *grandparent.interventions,
        *parent.interventions,
        *child.interventions,
    )
    assert flatten(stored, grandparent.id) == grandparent.interventions


# --- What each edit may touch, and what it must leave alone ----------------


@given(st.data())
@many
def test_apply_rejects_unknown_subject(data: st.DataObject) -> None:
    """An edit naming a claim that is not there is refused, in words, and applies nothing.

    The edits are drawn from one map and folded onto another, so their subjects
    usually do not match. Never a raised exception, never a half-applied branch,
    and never a map handed back with the subject still missing.
    """
    graph = data.draw(graphs())
    somewhere_else = data.draw(graphs())
    edit = data.draw(interventions(somewhere_else))
    before = graph.model_dump_json()

    folded = apply(graph, _branch(edit))

    assert graph.model_dump_json() == before
    here = {one.id for one in graph.propositions}
    names_a_claim = edit.kind in ("do", "observe", "believe", "refine")

    if names_a_claim and edit.target not in here:
        assert isinstance(folded, list)
        assert any(one.code == "unknown_target" and one.subject == edit.target for one in folded)
    if isinstance(folded, list):
        assert folded
        assert all(one.message.strip() for one in folded)


@given(st.data())
@many
def test_retune_changes_only_strength(data: st.DataObject) -> None:
    """Changing one arrow's push reaches one field of one arrow and nothing else.

    Not the mechanism, not the delay, not the shape, not the half-life, not the
    sources, not the receipt, not which two claims it joins. Not another arrow,
    and not a claim anywhere.
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="retune"))

    folded = apply(graph, _branch(edit))

    assert not isinstance(folded, list)
    after, fixed = folded
    assert fixed == ()
    assert _claim_text(after) == _claim_text(graph)

    was = {one.id: one for one in graph.links}
    for arrow in after.links:
        if arrow.id != edit.link:
            assert arrow.model_dump_json() == was[arrow.id].model_dump_json()
            continue
        assert arrow.strength == edit.strength
        assert arrow.model_copy(update={"strength": was[arrow.id].strength}) == was[arrow.id]


@given(st.data())
@many
def test_believe_touches_only_user_belief(data: st.DataObject) -> None:
    """The user's own number is written to the user's own slot and nowhere else.

    The model's number and the market's price stay exactly where they were, on
    that claim and on every other. The gap between the three is what the user came
    to look at, so nothing ever averages them or writes one over another.
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="believe"))

    folded = apply(graph, _branch(edit))

    assert not isinstance(folded, list)
    after, fixed = folded
    assert fixed == ()
    assert [one.model_dump_json() for one in after.links] == [
        one.model_dump_json() for one in graph.links
    ]

    was = {one.id: one for one in graph.propositions}
    for claim in after.propositions:
        if claim.id != edit.target:
            assert claim.model_dump_json() == was[claim.id].model_dump_json()
            continue
        assert claim.beliefs.user == edit.belief
        assert claim.beliefs.model == was[claim.id].beliefs.model
        assert claim.beliefs.market == was[claim.id].beliefs.market
        assert claim.model_copy(update={"beliefs": was[claim.id].beliefs}) == was[claim.id]


@given(st.data())
@many
def test_apply_preserves_dag(data: st.DataObject) -> None:
    """After any run of edits the map still has no loops, once feedback arrows are set aside.

    A feedback arrow — a market changing the world it is measuring — is allowed to
    close a loop and takes time to do it, so it is set aside here exactly as the
    map's own rules set it aside.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))

    folded = apply(graph, branch)
    assume(not isinstance(folded, list))
    assert not isinstance(folded, list)
    after, _ = folded

    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in after.propositions)
    walk.add_edges_from((one.source, one.target) for one in after.links if not one.reflexive)
    assert networkx.is_directed_acyclic_graph(walk)


@pytest.mark.parametrize("kind", SIX_OPERATIONS)
@given(st.data())
@many
def test_apply_touches_only_the_affected_set(kind: str, data: st.DataObject) -> None:
    """Every claim outside an edit's affected set is byte-identical in the two maps.

    This is the structural half of the locality rule: it compares the two **maps**.
    The other half — every likelihood outside the set identical in the two worlds —
    needs numbers, and numbers arrive with propagation.

    For each of the six operations the test pins a claim **fully separated** from
    the subject: nothing leads from one to the other either way, and no claim is a
    cause of both. Without that, the `observe` case would pass while checking
    nothing, because on a small map its affected set can swallow every claim there
    is and an assertion over an empty set is always true.
    """
    graph = data.draw(graphs(separated=True))
    subject, pinned = data.draw(separated_pair(graph))
    edit = _edit_of_kind(data, graph, kind, subject)
    before = _claim_text(graph)

    folded = apply(graph, _branch(edit))

    if isinstance(folded, list):
        # Splitting a claim is not built yet, so it moves nothing whatever.
        assert kind == "refine"
        assert _claim_text(graph) == before
        assert before[pinned] == _claim_text(graph)[pinned]
        return

    after, _ = folded
    may_move = _affected_from_the_shape(after, edit)
    now = _claim_text(after)

    assert pinned not in may_move
    assert now[pinned] == before[pinned]
    for identifier, text in now.items():
        if identifier in may_move:
            continue
        assert identifier in before, "an edit added a claim outside its own affected set"
        assert text == before[identifier]
    for identifier in before:
        assert identifier in now, "no edit removes a claim; there is no such operation"


# --- The affected set, read straight off the table -------------------------


def test_affected_set_matches_the_table() -> None:
    """One case per row of the affected-set table, on a map small enough to check by eye.

    The map is two pieces: a chain of four claims, and a pair off on its own. The
    pair is what makes each row worth asserting — it is outside every one of them.
    """
    graph = _two_piece_map()
    newcomer = _example_claim("newcomer")
    added = Insert(proposition=newcomer, links=(_example_arrow("third", "newcomer"),))
    folded = apply(graph, _branch(added))
    assert not isinstance(folded, list)
    with_newcomer, _ = folded

    assert affected_set(graph, Do(target="second", value=True)) == frozenset(
        {"second", "third", "ending"}
    )
    assert affected_set(graph, Observe(target="second", value=True)) == frozenset(
        {"first", "second", "third", "ending"}
    )
    assert affected_set(with_newcomer, added) == frozenset({"newcomer"})
    assert affected_set(graph, Retune(link="second->third", strength=0.1)) == frozenset(
        {"third", "ending"}
    )
    assert affected_set(
        graph,
        Refine(
            target="second",
            into=(_example_claim("finer-one"), _example_claim("finer-two")),
        ),
    ) == frozenset({"finer-one", "finer-two"})
    assert affected_set(
        graph,
        Believe(target="second", belief=Belief(p=0.5, lo=0.4, hi=0.6, owner="user")),
    ) == frozenset({"second"})


def test_affected_set_is_empty_when_the_map_has_no_such_subject() -> None:
    """An edit that cannot be applied moves nothing, so it is allowed to move nothing."""
    graph = _two_piece_map()

    assert affected_set(graph, Do(target="not-on-this-map", value=True)) == frozenset()
    assert affected_set(graph, Retune(link="no-such-arrow", strength=0.1)) == frozenset()


def test_an_arrow_with_an_end_off_the_map_moves_nothing() -> None:
    """A claim that does not exist cannot move, so an arrow reaching one is left out.

    Such an arrow already has its own complaint from the map's own rules. Counting
    it here would widen the answer around a claim nobody can see.
    """
    graph = _two_piece_map()
    with_a_dangling_arrow = graph.model_copy(
        update={"links": (*graph.links, _example_arrow("third", "nowhere"))}
    )

    assert affected_set(with_a_dangling_arrow, Do(target="third", value=True)) == frozenset(
        {"third", "ending"}
    )


@given(st.data())
@a_few
def test_a_feedback_arrow_never_carries_a_change(data: st.DataObject) -> None:
    """A claim reachable only through a feedback arrow is byte-identical in the two worlds.

    A feedback arrow is a market changing the world it is measuring. In this
    version it is **carried as data and never worked through** — a later stack
    unrolls it over time — so nothing an edit does can travel along one, and a
    claim on the far side of one provably cannot move. That is the rule Kent named
    on 2026-09-17, and it is what lets the product point at a claim and say *your
    change could not reach this*; on the worked example that claim is OPEC+
    restraint, whose only incoming arrow is the feedback arrow out of Brent.

    **The day a later stack unrolls feedback arrows, this test fails**, and the one
    sentence to change is in `spec/multiverse/interventions.md`, where the rule is
    written down once and every other chapter cites it. It is not a bug in this
    test; it is this test doing its job.

    The map is a generated one in two pieces, with a feedback arrow added from the
    edit's subject across to the other piece, so that arrow is the only route
    between them.
    """
    graph = data.draw(graphs(separated=True))
    subject, pinned = data.draw(separated_pair(graph))
    joined = graph.model_copy(
        update={
            "links": (
                *graph.links,
                _example_arrow(subject, pinned, reflexive=True),
            )
        }
    )
    edit = Do(target=subject, value=data.draw(st.booleans()), at=None)

    base = _world_of(joined)
    supposed = _world_of(joined, edit)

    assert pinned not in affected_set(joined, edit)
    assert supposed.beliefs[pinned] == base.beliefs[pinned]
    assert supposed.series[pinned] == base.series[pinned]
    assert supposed.states[pinned] == base.states[pinned]


def test_the_strike_branch_cannot_reach_opec_on_the_worked_example() -> None:
    """The same rule on the shipped example: OPEC+ restraint is outside every edit's reach.

    R's only incoming arrow is `B -> R`, the market feeding back on the world, so
    none of the strike branch's three edits can reach it — and it is the claim the
    interface can show as untouched with something behind the word.
    """
    for edit in HORMUZ_THEN_STRIKE.interventions:
        assert "R" not in affected_set(HORMUZ, edit)


# --- The refusals, one per way an edit can fail to fit ---------------------


def test_supposing_or_reporting_a_claim_that_is_not_there_is_refused() -> None:
    """Neither verb invents the claim it was asked about."""
    graph = _two_piece_map()

    supposed = apply(graph, _branch(Do(target="missing", value=True)))
    reported = apply(graph, _branch(Observe(target="missing", value=True)))

    assert supposed == [
        Violation(
            code="unknown_target",
            subject="missing",
            message=(
                "This edit supposes a claim that is not on this map, so there is nothing "
                "here to suppose."
            ),
        )
    ]
    assert isinstance(reported, list)
    assert [one.code for one in reported] == ["unknown_target"]
    assert "reports a claim that is not on this map" in reported[0].message


def test_putting_your_own_number_on_a_claim_that_is_not_there_is_refused() -> None:
    """The user's number needs a claim to sit beside."""
    graph = _two_piece_map()

    folded = apply(
        graph,
        _branch(Believe(target="missing", belief=Belief(p=0.5, lo=0.4, hi=0.6, owner="user"))),
    )

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["unknown_target"]
    assert "your own number" in folded[0].message


def test_changing_the_push_on_an_arrow_that_is_not_there_is_refused() -> None:
    """There is no arrow to change, and none is invented to receive the number."""
    graph = _two_piece_map()

    folded = apply(graph, _branch(Retune(link="no-such-arrow", strength=1.0)))

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["unknown_link"]
    assert folded[0].subject == "no-such-arrow"


def test_splitting_a_claim_says_it_is_not_built_yet() -> None:
    """`refine` has a shape and no behaviour, and says so rather than half-doing it.

    Refusing out loud is the point: a silently dropped edit is exactly the state
    the user cannot account for. The two refusals are different faults and carry
    different codes — a claim that is not there is `unknown_target`, and a claim
    that is there but cannot be split yet is `edit_not_applicable`, which means
    "this edit cannot be folded onto this map as written".
    """
    graph = _two_piece_map()
    finer = (_example_claim("finer-one"), _example_claim("finer-two"))

    on_the_map = apply(graph, _branch(Refine(target="second", into=finer)))
    not_on_the_map = apply(graph, _branch(Refine(target="missing", into=finer)))

    assert isinstance(on_the_map, list)
    assert [one.code for one in on_the_map] == ["edit_not_applicable"]
    assert "not built yet" in on_the_map[0].message
    assert isinstance(not_on_the_map, list)
    assert [one.code for one in not_on_the_map] == ["unknown_target"]
    assert "splits a claim that is not on this map" in not_on_the_map[0].message


def test_adding_a_claim_under_an_identifier_already_in_use_is_refused() -> None:
    """Two claims under one name would make every arrow between them ambiguous."""
    graph = _two_piece_map()
    clash = Insert(
        proposition=_example_claim("second"),
        links=(_example_arrow("first", "second"),),
    )

    folded = apply(graph, _branch(clash))

    assert isinstance(folded, list)
    assert sorted(one.code for one in folded) == ["duplicate_id", "duplicate_id"]
    assert {one.subject for one in folded} == {"second", "first->second"}
    assert all("already has" in one.message for one in folded)


def test_adding_two_arrows_under_one_identifier_is_refused() -> None:
    """The clash is caught between the arrows arriving together, not only against the map."""
    newcomer = _example_claim("newcomer")
    twice = Insert(
        proposition=newcomer,
        links=(
            _example_arrow("first", "newcomer"),
            _example_arrow("first", "newcomer").model_copy(update={"source": "second"}),
        ),
    )

    folded = apply(_two_piece_map(), _branch(twice))

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["duplicate_id"]


def test_adding_a_claim_whose_arrow_reaches_off_the_map_is_refused() -> None:
    """An arrow has to join the new claim to a claim that is actually there."""
    newcomer = _example_claim("newcomer")
    dangling = Insert(
        proposition=newcomer,
        links=(_example_arrow("nowhere", "newcomer"),),
    )

    folded = apply(_two_piece_map(), _branch(dangling))

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["unknown_target"]
    assert folded[0].subject == "nowhere"
    assert "not on this map" in folded[0].message


def test_adding_a_claim_with_an_arrow_that_does_not_touch_it_is_refused() -> None:
    """An `insert` adds one claim and the arrows that attach *it*.

    An arrow between two claims that are already on the map is not part of that
    edit: it would move a claim that is nowhere near the one being added, which
    is how the locality rule quietly stops being true. Both claims it names are on
    the map, so nothing is missing — the edit simply cannot be folded on as
    written, which is what `edit_not_applicable` says.
    """
    newcomer = _example_claim("newcomer")
    elsewhere = Insert(
        proposition=newcomer,
        links=(_example_arrow("first", "third"),),
    )

    folded = apply(_two_piece_map(), _branch(elsewhere))

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["edit_not_applicable"]
    assert folded[0].subject == "newcomer"
    assert "does not name the claim this edit adds" in folded[0].message


def test_adding_a_claim_that_closes_a_loop_is_refused() -> None:
    """A map that runs round in circles with no delay cannot be worked through at all.

    The complaint is the map's own `cycle`, in the same words a rejected proposal
    would get, because it is the same fault.
    """
    newcomer = _example_claim("newcomer")
    closing = Insert(
        proposition=newcomer,
        links=(_example_arrow("third", "newcomer"), _example_arrow("newcomer", "second")),
    )

    folded = apply(_two_piece_map(), _branch(closing))

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["cycle"]
    assert "form a loop with no delay in it" in folded[0].message


def test_a_newly_added_claim_is_left_to_the_maps_own_rules() -> None:
    """Folding an edit is not the moment to re-check everything a map must satisfy.

    A tradeable ending that forgets to say what you would trade is a fault in the
    map, reported when the map is checked and fixable in place. Answering the
    user's edit with it would be answering a question they did not ask.
    """
    unpriced = _example_claim("newcomer", kind="market").model_copy(update={"payoff": None})
    added = Insert(proposition=unpriced, links=(_example_arrow("third", "newcomer"),))

    folded = apply(_two_piece_map(), _branch(added))

    assert not isinstance(folded, list)
    after, _ = folded
    assert "newcomer" in {one.id for one in after.propositions}


def test_one_refused_edit_refuses_the_whole_branch() -> None:
    """A branch is all or nothing: no map comes back with only some of the edits on it."""
    graph = _two_piece_map()
    folded = apply(
        graph,
        _branch(
            Believe(target="second", belief=Belief(p=0.5, lo=0.4, hi=0.6, owner="user")),
            Retune(link="no-such-arrow", strength=1.0),
        ),
    )

    assert isinstance(folded, list)
    assert [one.code for one in folded] == ["unknown_link"]


@given(st.data())
@a_few
def test_a_refusal_never_names_an_identifier(data: st.DataObject) -> None:
    """A refused edit is read by a person, so it names a claim by its words.

    "No such link 01J8Z…" tells the user nothing. The identifier is already in
    `subject`, where the interface uses it to highlight the right tile or wire.
    """
    graph = data.draw(graphs())
    somewhere_else = data.draw(graphs())
    edit = data.draw(interventions(somewhere_else))

    folded = apply(graph, _branch(edit))
    assume(isinstance(folded, list))
    assert isinstance(folded, list)

    identifiers = (
        {one.id for one in graph.propositions} | {one.id for one in graph.links} | {graph.id}
    )
    for refusal in folded:
        for identifier in identifiers:
            assert identifier not in refusal.message


# --- Chains of branches ----------------------------------------------------


def test_a_chain_of_branches_that_loops_is_refused_rather_than_walked() -> None:
    """A branch that is its own ancestor would hang the walk, so it is refused instead.

    Storing branches so that this cannot happen belongs to whatever keeps them.
    This is only the walk refusing to go round for ever.
    """
    first = Branch(id="branch-one", label="The first branch", parent="branch-two")
    second = Branch(id="branch-two", label="The second branch", parent="branch-one")

    walked = flatten({first.id: first, second.id: second}, first.id)

    assert isinstance(walked, list)
    assert [one.code for one in walked] == ["edit_not_applicable"]
    assert walked[0].subject == "branch-one"
    assert "continues from itself" in walked[0].message
    assert "The first branch" in walked[0].message


def test_a_chain_of_branches_with_one_missing_is_refused() -> None:
    """A parent that is not here, and a branch that is not here, each say so plainly."""
    child = Branch(id="branch-child", label="The child branch", parent="branch-gone")

    without_parent = flatten({child.id: child}, child.id)
    without_anything = flatten({}, "branch-gone")

    assert isinstance(without_parent, list)
    assert [one.code for one in without_parent] == ["edit_not_applicable"]
    assert "The child branch" in without_parent[0].message
    assert isinstance(without_anything, list)
    assert "no branch stored under the name" in without_anything[0].message


# --- The worked example ----------------------------------------------------


def test_the_strike_branch_folds_onto_the_hormuz_map() -> None:
    """The example's three edits apply cleanly and fix the two values they say they do.

    Suppose the strait opens on the 1st; add the strike and its three arrows;
    suppose the strike lands on the 2nd. The positions are 0 and 2, because the
    edit in between added a claim rather than fixing a value.
    """
    folded = apply(HORMUZ, HORMUZ_THEN_STRIKE)

    assert not isinstance(folded, list)
    after, fixed = folded

    assert {one.id for one in after.propositions} == {"H", "C", "B", "R", "M1", "M2", "N1", "S"}
    assert [(one.target, one.value, one.at, one.by, one.kind) for one in fixed] == [
        ("H", True, FIXTURE_DATE, 0, "do"),
        ("S", True, date(2026, 10, 2), 2, "do"),
    ]
    assert HORMUZ.model_dump_json() == apply(HORMUZ, _branch())[0].model_dump_json()  # type: ignore[index]


def test_an_arrow_inserted_after_a_supposition_is_live() -> None:
    """Supposing a claim cuts the arrows pointing at it *now*, not the ones added later.

    This is the whole showcase in one assertion. The branch supposes the strait
    open first and adds the strike second, so the strike's arrow against the strait
    survives and can push the supposition back down. Reverse the two edits and the
    same arrow is cut, and the branch demonstrates nothing — which is why the order
    the user made their edits in is part of the record.
    """
    in_the_example_order = apply(HORMUZ, HORMUZ_THEN_STRIKE)
    the_other_way_round = apply(
        HORMUZ,
        _branch(
            Insert(
                proposition=STRIKE_ON_IRAN,
                links=(STRIKE_TO_BRENT, STRIKE_TO_PREMIUM, STRIKE_TO_HORMUZ),
            ),
            Do(target="H", value=True, at=FIXTURE_DATE),
            Do(target="S", value=True, at=date(2026, 10, 2)),
        ),
    )

    assert not isinstance(in_the_example_order, list)
    assert not isinstance(the_other_way_round, list)
    live, _ = in_the_example_order
    cut, _ = the_other_way_round

    assert "S->H" in {one.id for one in live.links}
    assert "S->H" not in {one.id for one in cut.links}
    assert "S->B" in {one.id for one in cut.links}
    assert "S->C" in {one.id for one in cut.links}


# --- Locality, in full: over two worlds rather than two maps -----------------


def _world_of(graph: Graph, *edits: Intervention) -> World:
    """Fold a branch onto a map and work the numbers through, at the small budget above."""
    branch = _branch(*edits)
    folded = apply(graph, branch)
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    return propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        **TINY_BUDGET,
    )


def _same_on_the_days_they_share(base: World, branched: World, claim_id: str) -> None:
    """Check one claim reads the same in two worlds, on every day both of them carry.

    Two worlds of the same map are drawn at the same days. Two worlds a claim was
    added between can be drawn at slightly different ones, because past the
    180-point cap every claim's own resolve-by day is kept among the points and a
    new claim brings a new one. Comparing the days they share is the whole of what
    can be compared, and it is every day the two would be shown side by side on.
    """
    where = {day: index for index, day in enumerate(base.series_days)}
    for index, day in enumerate(branched.series_days):
        if day not in where:
            continue
        assert branched.series[claim_id][index] == base.series[claim_id][where[day]], day
        assert branched.states[claim_id][index] == base.states[claim_id][where[day]], day


def _has_no_loops(graph: Graph) -> bool:
    """Say whether a map runs round in circles once its feedback arrows are set aside."""
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in graph.propositions)
    walk.add_edges_from((one.source, one.target) for one in graph.links if not one.reflexive)
    return bool(networkx.is_directed_acyclic_graph(walk))


@pytest.mark.parametrize("kind", SIX_OPERATIONS)
@given(st.data())
@a_few
def test_intervention_locality(kind: str, data: st.DataObject) -> None:
    """Every claim outside an edit's reach is byte-identical in the two **worlds**.

    This is the product's central correctness claim, and the full form of it: not
    only that the two maps agree about a claim the edit cannot reach, but that the
    two *answers* do — the likelihood, its range, and every day of its series.

    For each of the six operations the test pins a claim **fully separated** from
    the subject: no chain of arrows runs between them in either direction and no
    claim is a cause of both. Without that, the `observe` case would pass while
    checking nothing, because its reach can swallow every claim on a small map and
    an assertion over an empty set is always true. Maps offering no such claim are
    discarded rather than quietly passed.

    The reach is worked out here, from the shape of the map, and never asked of the
    engine.
    """
    graph = data.draw(graphs(separated=True))
    subject, pinned = data.draw(separated_pair(graph))
    edit = _edit_of_kind(data, graph, kind, subject)
    base = _world_of(graph)

    folded = apply(graph, _branch(edit))
    if isinstance(folded, list):
        # Splitting a claim is not built yet, so it moves nothing whatever.
        assert kind == "refine"
        assert _world_of(graph).beliefs[pinned] == base.beliefs[pinned]
        return

    after, _ = folded
    branched = _world_of(graph, edit)
    may_move = _affected_from_the_shape(after, edit)

    assert pinned not in may_move
    assert branched.beliefs[pinned] == base.beliefs[pinned]
    for claim_id, belief in branched.beliefs.items():
        if claim_id in may_move:
            continue
        assert claim_id in base.beliefs, "an edit added a claim outside its own reach"
        assert belief == base.beliefs[claim_id], claim_id
    # A claim added by an `insert` brings its own resolve-by day, and past the
    # 180-point cap that day joins the points every series is drawn at — so the two
    # worlds can be drawn at slightly different days. They are compared on the days
    # they share, which is every day either of them would show side by side.
    _same_on_the_days_they_share(base, branched, pinned)


def _in_force(fixed: tuple[object, ...]) -> dict[str, tuple[str, bool]]:
    """Which value is in force on each claim, and which verb fixed it.

    A later assignment overrides an earlier one on the same claim, so the last is
    the one that counts and the earlier ones stay for the record.
    """
    return {one.target: (one.kind, one.value) for one in fixed}  # type: ignore[attr-defined]


def _observation_reach(graph: Graph, fixed: tuple[object, ...]) -> set[str]:
    """Which claims the observations in force are evidence about, on this map.

    An observation reaches the claim it names, everything that claim leads to,
    everything that leads to it, and everything those causes lead to — the widest
    of the six reaches, and the same one `observe` has in the affected-set table.
    """
    reached: set[str] = set()
    for target, (kind, value) in _in_force(fixed).items():
        if kind == "observe":
            reached |= _affected_from_the_shape(graph, Observe(target=target, value=value))
    return reached


def _evidence_moved(
    before: Graph, before_fixed: tuple[object, ...], after: Graph, after_fixed: tuple[object, ...]
) -> set[str]:
    """Which claims an edit may move by changing what the evidence on the map is about.

    The affected-set table says what one edit does to a map on its own. It does
    not cover one thing a *run* of edits can do: change what an earlier
    observation is evidence about.

    Two ways that happens, and both are honest rather than a hole in the rule.
    Putting a lever on a claim somebody had reported — a `do` over an earlier
    `observe` — **takes the evidence off the map**, and the claims that evidence
    reached go back to what they said before it arrived. And attaching a new claim
    to one that was reported widens what the evidence is about, because the new
    arrows carry it further. Evidence is the one thing on a map that is not local,
    which is exactly why observing and supposing are two different verbs.

    So when the evidence in force changes, or the claims it reaches change, those
    claims are allowed to move as well — and when neither changes, they are not.
    """
    was, now = _in_force(before_fixed), _in_force(after_fixed)
    was_evidence = {one: was[one] for one in was if was[one][0] == "observe"}
    now_evidence = {one: now[one] for one in now if now[one][0] == "observe"}
    reached_before = _observation_reach(before, before_fixed)
    reached_after = _observation_reach(after, after_fixed)
    if was_evidence == now_evidence and reached_before == reached_after:
        return set()
    return reached_before | reached_after


class GraphEditMachine(RuleBasedStateMachine):
    """A run of edits made one after another, the way a user actually works.

    Rather than one random edit on one random map, this makes a *sequence* of them
    — suppose this, add that, change this number — and re-checks three things after
    **every** step: the map still has no loops once feedback arrows are set aside,
    every likelihood is still a likelihood inside its own range, and the step just
    taken moved nothing outside its own reach.

    A failing sequence is shrunk to the shortest one that still breaks, so a
    failure reads as "these two edits, in this order" rather than as a wall of
    generated data. That is the whole reason this is a state machine and not
    another property test.
    """

    @initialize(graph=graphs(separated=True))
    def start_from(self, graph: Graph) -> None:
        """Begin with a map in two pieces and the base world it produces."""
        self.graph = graph
        self.fixed: tuple[object, ...] = ()
        self.world = propagate(graph, (), as_of=DAY_ZERO, seed=SEED, **TINY_BUDGET)

    @rule(data=st.data())
    def make_one_more_edit(self, data: st.DataObject) -> None:
        """Apply one more edit, and re-check the three rules against the step just taken."""
        offered = [one for one in SIX_OPERATIONS if one != "retune" or self.graph.links]
        edit = data.draw(interventions(self.graph, kind=data.draw(st.sampled_from(offered))))
        outcome = apply(self.graph, _branch(edit), self.fixed)  # type: ignore[arg-type]
        if isinstance(outcome, list):
            # A refused edit changes nothing at all; what it says is tested above.
            return
        after, fixed = outcome
        world = propagate(after, fixed, as_of=DAY_ZERO, seed=SEED, **TINY_BUDGET)

        assert _has_no_loops(after)
        for belief in world.beliefs.values():
            assert 0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0
        may_move = _affected_from_the_shape(after, edit) | _evidence_moved(
            self.graph, self.fixed, after, fixed
        )
        for claim_id, belief in world.beliefs.items():
            if claim_id in may_move:
                continue
            assert belief == self.world.beliefs[claim_id], claim_id

        self.graph, self.fixed, self.world = after, fixed, world


GraphEditMachine.TestCase.settings = settings(max_examples=15, stateful_step_count=4, deadline=None)
TestGraphEditMachine = GraphEditMachine.TestCase
