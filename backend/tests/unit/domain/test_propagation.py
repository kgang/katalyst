"""What the engine does with a map, over maps nobody wrote by hand.

`propagate` turns a map and the values its edits fixed into a world: one
likelihood for every claim on the day it is judged, one likelihood for every day
in between, and a named word for each of those days.

**One likelihood per claim, computed once.** There is no range around any number
and no second loop underneath one (decision records 0016 and 0028), so the four
things this file used to guard — that a band was not the coin flips, that the
versions never saw the branch, that a stated range was fitted half by half, and
that a second method gave the same band — are no longer statements about
anything. What is left is sharper, and most of it is an identity rather than a
tolerance: a claim an edit cannot reach comes back **byte-identical**, a
supposition is true rather than nearly true, and every belief's two ends are its
own middle.

**The arithmetic itself is tested next door.** `test_rates.py`, `test_states.py`,
`test_forward.py`, `test_solving.py` and `test_sampling.py` are about the five
modules the answer is worked out in, and `test_by_deadline.py` checks the whole
of it against two enumerators that share none of its code. This file is about
what `propagate` assembles out of them: the world a reader is handed.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from katalyst.domain import (
    Assignment,
    Belief,
    Beliefs,
    Believe,
    Branch,
    ContractPayoff,
    Do,
    Graph,
    Insert,
    Link,
    Observe,
    Proposition,
    Resolution,
    Retune,
    World,
    apply,
    propagate,
    validate,
)
from katalyst.domain.propagation import SERIES_CAP
from tests.comparisons import every_version_answered_the_same
from tests.strategies import branches, graphs, interventions, seeds, uncertain_beliefs

many = settings(max_examples=25, deadline=None)
a_few = settings(max_examples=12, deadline=None)

DAY_ZERO = date(2026, 1, 1)
"""Day zero for the generated maps, which carry resolve-by dates from 2026 onwards."""

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

DOMAIN = Path(__file__).resolve().parents[3] / "src" / "katalyst" / "domain"
"""The engine's own source, for the two checks that read it rather than run it."""


def judged_no_later_than(graph: Graph, target: str) -> set[str]:
    """Name the claims judged on or before the day this one is judged.

    A claim's number is the chance it happens by **its own** deadline, so a cause
    judged long after its effect is answering a question about a different stretch
    of time; see `_a_claim_something_really_pushes`.
    """
    judged = {one.id: one.resolution.by for one in graph.propositions}
    return {one for one, day in judged.items() if day <= judged[target]}


A_REAL_PUSH = 0.5
"""How hard an arrow has to push before a test treats it as a cause at all.

Half a unit of log-odds, which takes a coin flip to about `.62`. The generated
maps draw pushes from the whole range a map may carry, `2.2e-16` included, and an
arrow that pushes by that is a cause in name only — it leaves its target's number
where it was, so learning the target says nothing about it.
"""


# --- Small maps the example tests build by hand ----------------------------


def _claim(
    identifier: str,
    kind: str = "event",
    prior: tuple[float, float, float] = (0.3, 0.2, 0.45),
    days: int = 30,
) -> Proposition:
    """One plain claim, an event, with the chance it comes true on its own."""
    low, middle, high = prior[1], prior[0], prior[2]
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


def _arrow(
    source: str,
    target: str,
    *,
    strength: float = 1.0,
    mode: str = "trigger",
    shape: str = "step",
    lag: float = 0.0,
    half_life: float | None = None,
    reflexive: bool = False,
) -> Link:
    """One plain arrow, with every field a test might want to vary."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode=mode,  # type: ignore[arg-type]
        strength=strength,
        lag=lag,
        shape=shape,  # type: ignore[arg-type]
        half_life=half_life,
        rationale="The first claim makes the second one more likely, for a stated reason.",
        provenance="argued",
        reflexive=reflexive,
    )


def _map(
    claims: tuple[Proposition, ...], arrows: tuple[Link, ...], identifier: str = "small"
) -> Graph:
    """A whole small map, with the first claim as the one it started from."""
    return Graph(id=identifier, propositions=claims, links=arrows, hypothesis_id=claims[0].id)


def _two_step_map() -> Graph:
    """A cause, an effect and an ending: `top` pushes `middle`, which pushes `ending`."""
    return _map(
        (
            _claim("top", kind="hypothesis"),
            _claim("middle"),
            _claim("ending", kind="market"),
        ),
        (_arrow("top", "middle", strength=1.5), _arrow("middle", "ending", strength=1.2)),
    )


def _folded(graph: Graph, *edits: object) -> World:
    """Fold a branch onto a map and work the numbers through, in one line."""
    branch = Branch(id="branch-under-test", label="A branch a test wrote", interventions=edits)  # type: ignore[arg-type]
    result = apply(graph, branch)
    assert not isinstance(result, list), result
    left_behind, fixed = result
    return propagate(left_behind, fixed, as_of=DAY_ZERO, seed=SEED)


def _folded_if_it_applies(graph: Graph, branch: Branch) -> World:
    """The same, for a generated branch, which may hold an edit that cannot be applied.

    Splitting a claim is not built yet and an insert can reuse an identifier, so a
    branch nobody wrote by hand is sometimes refused. Those are discarded rather
    than quietly passed: what is being checked here is what the engine does with
    the branches that *do* apply.
    """
    result = apply(graph, branch)
    assume(not isinstance(result, list))
    assert not isinstance(result, list)
    left_behind, fixed = result
    return propagate(left_behind, fixed, as_of=DAY_ZERO, seed=SEED)


def _a_claim_with_causes(data: st.DataObject, graph: Graph) -> str:
    """Pick a claim to observe from the ones the map actually gives causes to."""
    with_causes = [one.id for one in graph.propositions if _causes_of(graph, one.id)]
    assert with_causes, "graphs() gives every claim but the first at least one cause"
    return str(data.draw(st.sampled_from(with_causes)))


def _pushing_nothing(graph: Graph) -> Graph:
    """The same map with every arrow's push set to exactly nothing.

    The arrows stay where they are — what a claim's causes *are* is a fact about the
    shape of the map, and none of them moves — so this leaves every question of
    which claims are connected to which alone and takes away only the push.
    """
    return graph.model_copy(
        update={"links": tuple(one.model_copy(update={"strength": 0.0}) for one in graph.links)}
    )


def _causes_of(graph: Graph, claim_id: str) -> set[str]:
    """List every claim a chain of ordinary arrows reaches this one from."""
    reached: set[str] = set()
    growing = True
    while growing:
        growing = False
        for one in graph.links:
            reaches = one.target == claim_id or one.target in reached
            if one.reflexive or not reaches or one.source in reached:
                continue
            reached.add(one.source)
            growing = True
    return reached


def _a_claim_something_really_pushes(data: st.DataObject, graph: Graph) -> str:
    """Pick a claim to observe from the ones an arrow that really pushes points at.

    Two things are asked of the claim, and each rules out a map on which the
    question has no answer rather than a map on which the engine is wrong.

    **An arrow of strength nought is a cause in name only.** It leaves its target's
    rate exactly where it was, so the two claims are independent and learning one
    says nothing about the other — which is the subject of
    `test_an_observation_moves_nothing_no_arrow_reaches`, the other side of this
    same coin.

    **And a claim judged on day zero has a window of no width.** However large its
    rate, nothing has time to happen in no time at all, so such a claim reads
    nought and nothing anybody learns can move it (`rates.py`, `_NOT_ZERO`). A
    generated map can carry a whole row of them.

    **A cause judged long after its effect is a third such case**, and it is the
    one that reads least obviously. A claim's number is the chance it happens by
    **its own** deadline, so a cause judged a year out is answering a question
    about a year, while the effect it feeds is answering one about a day: learning
    the effect happened on day one says almost nothing about a year-long window,
    and *almost nothing* can round to nothing. So the target is picked from the
    claims whose causes are judged no later than they are.

    `A_REAL_PUSH` is what "really pushes" means here, said as a number rather than
    left to `!= 0`: the generator will happily draw a push of `2.2e-16`, which is a
    cause in name only just as surely as a push of nought is.
    """
    judged = {one.id: one.resolution.by for one in graph.propositions}
    pushed = sorted(
        {
            one.target
            for one in graph.links
            if not one.reflexive
            and abs(one.strength) >= A_REAL_PUSH
            and judged[one.target] > DAY_ZERO
            and DAY_ZERO < judged[one.source] <= judged[one.target]
        }
    )
    assume(pushed)
    return str(data.draw(st.sampled_from(pushed)))


# --- One number per claim, and both its ends are that number ----------------


@given(st.data())
@many
def test_probability_bounds(data: st.DataObject) -> None:
    """Every number a world reports is a likelihood, and no number carries a range.

    Nothing between 0 and 1 is optional here: a likelihood outside that is not a
    likelihood. And `lo`, `p` and `hi` are one number, because this product ships
    one reading of the map (decision record 0028, Kent's row R48).
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    world = _folded_if_it_applies(graph, branch)

    for claim_id, belief in world.beliefs.items():
        assert 0.0 <= belief.p <= 1.0, claim_id
        assert belief.owner == "model"
    for claim_id, drawn in world.series.items():
        assert all(0.0 <= one <= 1.0 for one in drawn), claim_id
        assert len(drawn) == len(world.states[claim_id])


@given(st.data())
@many
def test_a_computed_belief_has_no_range(data: st.DataObject) -> None:
    """Every belief a world carries satisfies `lo == p == hi`, on maps nobody wrote by hand.

    Decision record 0028 names this test. No number on this product carries a
    range — not on a tile, not in the panel, not on the change list — and the two
    fields that used to hold one are on the wire only until the follow-up after
    the browser round takes them off. A field that is always equal to another
    field is a field somebody will eventually believe, so while they are there
    this says out loud what they hold.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    world = _folded_if_it_applies(graph, branch)

    for claim_id, belief in world.beliefs.items():
        assert belief.lo == belief.p == belief.hi, claim_id


@given(st.data())
@many
def test_belief_bounds_after_any_sequence(data: st.DataObject) -> None:
    """A run of edits, one after another, never produces a number outside 0 to 1.

    The same statement as the bounds above, made about a *sequence* rather than a
    single edit, because that is how a user actually works: suppose this, add
    that, change this number, and see what comes out.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    folded = apply(graph, branch)
    assume(not isinstance(folded, list))
    assert not isinstance(folded, list)
    left_behind, fixed = folded

    world = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=data.draw(seeds()))

    for belief in world.beliefs.values():
        assert 0.0 <= belief.p <= 1.0
    for drawn in world.series.values():
        assert all(0.0 <= one <= 1.0 for one in drawn)


def test_nothing_draws_a_version() -> None:
    """The engine's own source holds no machinery for two thousand versions of the map.

    Decision record 0028 names this test, and it reads the source rather than
    running it, because what it is about is machinery that is **gone** rather than
    a number that came out small. A Latin hypercube, a per-version draw of a
    claim's likelihood or an arrow's push, and the spread that decided how wide an
    arrow was drawn would each produce a range nothing on screen could account
    for — the state this product refuses.
    """
    written = "\n".join(one.read_text(encoding="utf-8") for one in sorted(DOMAIN.glob("*.py")))

    for gone in (
        "PROVENANCE_SPREAD",
        "_version_priors",
        "_version_strengths",
        "_fitted_halves",
        "_standard_normal_quantile",
        "_weighted_percentiles",
        "range_shares[",
    ):
        assert gone not in written, f"{gone} is still in the engine's source"


def test_the_engine_carries_no_retraction() -> None:
    """The names the undermining machinery went by are gone from the engine's source.

    Decision record 0017: nothing on this product undermines a supposition. A
    claim that happened stays happened, and what a later event pushes back on is a
    state, which falls by its own arithmetic. This names symbols rather than
    English words, so it cannot be satisfied by rewording a docstring.
    """
    written = "\n".join(one.read_text(encoding="utf-8") for one in sorted(DOMAIN.glob("*.py")))

    for gone in (
        "class Retraction",
        "_retractions",
        "_opposing",
        "_spells_on",
        '"withdrawn"',
        '"pushed"',
        "undermined_on",
        "_multiplied_out",
    ):
        assert gone not in written, f"{gone} is still in the engine's source"


# --- The same three inputs always give the same world ----------------------


@given(st.data())
@many
def test_propagation_idempotent(data: st.DataObject) -> None:
    """Working the same numbers through twice gives the same world, to the byte."""
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))

    once = _folded_if_it_applies(graph, branch)
    twice = _folded_if_it_applies(graph, branch)

    assert once.model_dump_json() == twice.model_dump_json()


@given(st.data())
@many
def test_propagation_order_independent(data: st.DataObject) -> None:
    """Writing the claims down in a different order changes nothing.

    Causes are worked out before effects, and claims no arrow orders relative to
    one another are put in a settled order of their own rather than the order they
    happened to be written down in.
    """
    graph = data.draw(graphs())
    shuffled = graph.model_copy(update={"propositions": tuple(reversed(graph.propositions))})

    plain = _folded(graph)
    reordered = _folded(shuffled)

    assert plain.beliefs == reordered.beliefs
    assert plain.series == reordered.series
    assert plain.states == reordered.states


@given(st.data())
@many
def test_world_replays_from_base_branch_seed(data: st.DataObject) -> None:
    """A map, a branch and a seed are the whole of a world: nothing else is allowed to matter.

    A screenshot from three days ago is reproducible from three values, and if it
    ever is not, exactly one of three things is at fault — the base map changed,
    the branch changed, or the engine read something other than its seed.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    seed = data.draw(seeds())
    folded = apply(graph, branch)
    assume(not isinstance(folded, list))
    assert not isinstance(folded, list)
    left_behind, fixed = folded

    first = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=seed)
    second = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=seed)

    assert first.model_dump_json() == second.model_dump_json()


def test_a_world_says_which_map_branch_and_seed_it_came_from() -> None:
    """A world carries its three inputs, because it is a result and never a source of truth.

    And it says what the four fields that carry nothing hold: one version of the
    map, no inner loop, nothing retracted, no range taken apart. Each is a
    constant with a dated reason beside it in `propagation.py`, and all four leave
    the wire together when the browser round closes.
    """
    graph = _two_step_map()

    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))

    assert world.base_id == graph.id
    assert world.branch_id is None
    assert world.seed == SEED
    assert (world.versions, world.worlds) == (1, 0)
    assert world.retractions == ()
    assert world.range_shares == {}
    assert world.conditionals == {}
    assert world.day_zero == DAY_ZERO
    assert world.assignments[0].target == "top"
    assert World.model_validate_json(world.model_dump_json()) == world


# --- The two kinds of arrow --------------------------------------------------


def test_an_event_a_later_strike_pushes_against_still_stands() -> None:
    """A domino that has fallen stays fallen, whatever happens to the one before it.

    The cause is supposed true, a later edit inserts a claim with a hard negative
    arrow into it, and the supposition still holds: an event that happened cannot
    un-happen, so nothing undermines it and the claim it pushed is byte-identical
    to the world in which the strike was never inserted. Decision record 0017 —
    what a strike lowers is a *state*, and there is no state on this map.
    """
    graph = _two_step_map()
    upset = Insert(proposition=_claim("strike"), links=(_arrow("strike", "top", strength=-3.0),))

    undisturbed = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    struck = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        upset,
        Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=1)),
    )

    assert set(undisturbed.states["top"]) == {"supposed"}
    assert set(struck.states["top"]) == {"supposed"}
    assert struck.retractions == ()
    assert struck.series["middle"] == undisturbed.series["middle"]
    assert struck.beliefs["middle"] == undisturbed.beliefs["middle"]


def test_a_cause_forced_false_pushes_nothing() -> None:
    """A cause held false is worth exactly as much to its effect as no arrow at all.

    Not nearly — to the byte. The arrow is on the map either way; what has gone is
    the chance its source is ever true, and an arrow out of a claim that never
    happens adds nothing to anything.
    """
    held = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0),),
    )
    alone = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (),
    )

    without_its_cause = _folded(held, Do(target="top", value=False, at=DAY_ZERO))
    without_the_arrow = _folded(alone, Do(target="top", value=False, at=DAY_ZERO))
    with_its_cause = _folded(held, Do(target="top", value=True, at=DAY_ZERO))

    assert without_its_cause.series["ending"] == without_the_arrow.series["ending"]
    assert with_its_cause.beliefs["ending"].p > without_its_cause.beliefs["ending"].p


# --- Suppose is not observe ---------------------------------------------------


@given(st.data())
@many
def test_do_leaves_ancestors_unchanged(data: st.DataObject) -> None:
    """Supposing something moves nothing that could have caused it.

    Supposing the strait opens must not quietly raise the odds that a diplomatic
    settlement happened. That is the difference between pulling a lever and
    reporting news, and it is the reason the product offers two verbs.

    Read to the last bit rather than to the byte, and `tests/comparisons.py` says
    why: a supposition cuts the arrows into its target, the exact solve reads its
    elimination order off the shape of the map, and a different order multiplies
    the same factors in a different sequence.
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="do"))

    base = _folded(graph)
    supposed = _folded(graph, edit)

    every_version_answered_the_same(base, supposed, _causes_of(graph, edit.target))


@given(st.data())
@a_few
def test_observe_may_update_ancestors(data: st.DataObject) -> None:
    """Learning something reaches back into what caused it, which supposing never does.

    Conditioning on the claim having come out as observed changes what the map
    says about its causes just as much as about what it causes. The claim to
    observe is picked from the ones that actually have causes, read off the shape
    of the map, and every prior comes from `uncertain_beliefs()` so that nothing
    on the map is settled before the engine starts.
    """
    graph = data.draw(graphs(priors=uncertain_beliefs()))
    target = _a_claim_something_really_pushes(data, graph)
    causes = {
        one.source
        for one in graph.links
        if one.target == target
        and not one.reflexive
        and abs(one.strength) >= A_REAL_PUSH
        and one.source in judged_no_later_than(graph, target)
    }

    base = _folded(graph)
    learned = _folded(graph, Observe(target=target, value=True))

    assert any(learned.beliefs[one] != base.beliefs[one] for one in causes)


@given(st.data())
@a_few
def test_an_observation_moves_nothing_no_arrow_reaches(data: st.DataObject) -> None:
    """With every arrow flattened to nothing, an observation moves nothing but itself.

    The sharpest statement of what a piece of news is allowed to do. An arrow of
    strength nought and no arrow at all are the same thing to the arithmetic, so a
    map whose every arrow pushes nothing is a heap of claims that have nothing to
    do with one another. Learning one of them is news about that one claim and
    about nothing else, and every other claim has to come back **bit for bit**.

    This test failed by design for as long as the old engine ran, and it was
    marked so: observing something threw away the worlds it did not happen in,
    each version of the map was then counted by the share of its worlds that
    survived, and counting the versions differently moved every number those
    versions averaged. Decision record 0016 deleted that mechanism.

    **The tolerance is `1e-12`, and what it stands for is named rather than
    guessed.** An arrow with no push adds exactly nothing to its target's rate —
    both sides of that comparison are read through the same conversion, so a push
    of nought lands on the claim's own number and the rate it adds comes out at
    nought — and the claim's yes/no table is then constant along that cause's axis.
    But the arrows are still on the map, so the elimination still multiplies that
    factor in and renormalises, and multiplying and dividing by one number is not
    bit-exact in floating point: the upstream claim came back one last bit away,
    `1.1e-16`, on the map `plans/analysis/scripts/stack-05-flip/no_push.py` prints.
    **Byte-identity is claimed for a claim the map does not join to the evidence at
    all**, and `test_a_claim_cut_off_from_the_evidence_is_bit_for_bit` in
    `test_patches.py` is where that promise lives.
    """
    graph = _pushing_nothing(data.draw(graphs(priors=uncertain_beliefs())))
    assert all(one.strength == 0.0 for one in graph.links), "every arrow pushes nothing"
    target = _a_claim_with_causes(data, graph)
    others = [one.id for one in graph.propositions if one.id != target]

    base = _folded(graph)
    learned = _folded(graph, Observe(target=target, value=True))

    moved = {
        one: learned.beliefs[one].p - base.beliefs[one].p
        for one in others
        if abs(learned.beliefs[one].p - base.beliefs[one].p) > 1e-12
    }
    assert not moved, (
        "every arrow on this map pushes nothing, so an observation reaches nothing but "
        f"the claim observed — and yet these moved: {moved}"
    )


def _two_pieces() -> Graph:
    """A map in two halves with nothing joining them: `near -> far`, and `other -> beyond`."""
    return _map(
        (
            _claim("near", kind="hypothesis", prior=(0.5, 0.25, 0.75)),
            _claim("far", kind="market", prior=(0.4, 0.2, 0.6)),
            _claim("other", kind="event", prior=(0.5, 0.25, 0.75)),
            _claim("beyond", kind="market", prior=(0.4, 0.2, 0.6)),
        ),
        (_arrow("near", "far", strength=1.4), _arrow("other", "beyond", strength=1.4)),
    )


def test_an_observation_in_one_piece_moves_nothing_in_another() -> None:
    """Observing something in one half of a map moves nothing in the other half.

    Two halves, no arrow and no cause between them, so conditioning on one of them
    says nothing whatever about the other's piece.

    It used to say something. The worlds thrown away were pooled across **every**
    observation on the branch, so a claim that *some* observation was evidence
    about was read through *all* of them; measured before that was fixed, a claim
    in the far piece moved by `.083`, sixteen times the floor at which this
    product calls anything a move. There are no worlds to pool now, and the answer
    is byte-identical rather than merely close.

    The order the two observations are made in must not matter either, and the
    test says so: an edit that changes nothing cannot change something by being
    made second.
    """
    graph = _two_pieces()
    alone = _folded(graph, Observe(target="near", value=True))
    with_the_other = _folded(
        graph, Observe(target="near", value=True), Observe(target="other", value=True)
    )
    other_first = _folded(
        graph, Observe(target="other", value=True), Observe(target="near", value=True)
    )

    for claim_id in ("near", "far"):
        assert with_the_other.beliefs[claim_id] == alone.beliefs[claim_id], claim_id
        assert other_first.beliefs[claim_id] == alone.beliefs[claim_id], claim_id
    only_other = _folded(graph, Observe(target="other", value=True))
    for claim_id in ("other", "beyond"):
        assert with_the_other.beliefs[claim_id] == only_other.beliefs[claim_id], claim_id


def test_two_observations_on_one_chain_are_both_evidence_about_it() -> None:
    """A claim both observations reach is read through both of them.

    The mirror of the test above, and the reason keeping observations apart is not
    merely convenient: where two observations really are both evidence about a
    claim, both must still count.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.5, 0.25, 0.75)),
            _claim("middle", prior=(0.5, 0.25, 0.75)),
            _claim("ending", kind="market", prior=(0.4, 0.2, 0.6)),
        ),
        (_arrow("top", "middle", strength=1.5), _arrow("middle", "ending", strength=1.5)),
    )
    one = _folded(graph, Observe(target="top", value=True))
    both = _folded(graph, Observe(target="top", value=True), Observe(target="middle", value=True))

    assert both.beliefs["ending"] != one.beliefs["ending"], "the second observation is evidence too"
    assert 0.0 <= both.beliefs["ending"].p <= 1.0


def test_an_observation_a_later_supposition_cuts_off_stops_being_evidence() -> None:
    """Supposing a claim cuts its causes off, and an observation upstream stops reaching past it.

    A `do` cuts every arrow into its target, so what was upstream of the observed
    claim is no longer joined to it — and an observation reaches along the arrows
    of the map the edits leave behind, not along the map as written. So the claim
    above the supposition comes back **byte-identical** to the untouched world.
    """
    graph = _map(
        (
            _claim("cause", kind="hypothesis", prior=(0.5, 0.25, 0.75)),
            _claim("seen", prior=(0.5, 0.25, 0.75)),
            _claim("ending", kind="market", prior=(0.4, 0.2, 0.6)),
        ),
        (_arrow("cause", "seen", strength=1.5), _arrow("seen", "ending", strength=1.5)),
    )
    base = _folded(graph)
    reaching = _folded(graph, Observe(target="seen", value=True))
    cut = _folded(graph, Observe(target="seen", value=True), Do(target="seen", value=True, at=None))

    assert reaching.beliefs["cause"] != base.beliefs["cause"]
    assert cut.beliefs["cause"] == base.beliefs["cause"]


def test_a_claim_one_observation_reaches_is_read_through_that_one_alone() -> None:
    """A claim in one piece of a map is untouched by an observation in another piece.

    The case that looks as though it should be pooled and must not be. `only_a`
    hangs off `seen`, which the first observation names; `also_seen` is in a piece
    of its own. Adding the second observation leaves the first piece where it was.

    **The tolerance is `0.001`, and it is the honest one.** *This happened* is
    answered in two halves: the exact solve, which is local to the last bit, and a
    sampled correction for the way learning a claim happened moves *when* its
    causes happened. The sample is **one** weighted draw of fifty thousand worlds
    over the whole map, so adding an observation anywhere redraws it, and a claim
    in another piece moves by that much sampling noise. Measured on this very map
    by `plans/analysis/scripts/stack-05-flip/two_pieces.py`: the largest move in
    the first piece is `2.7e-4`, against the `0.005` floor at which this product
    calls anything a move at all, and against the `.083` the old engine leaked here
    for a reason that was not sampling noise but a pooled set of surviving worlds.
    """
    graph = _map(
        (
            _claim("shared", kind="hypothesis", prior=(0.5, 0.25, 0.75)),
            _claim("seen", prior=(0.5, 0.25, 0.75)),
            _claim("only_a", kind="market", prior=(0.4, 0.2, 0.6)),
            _claim("apart", prior=(0.5, 0.25, 0.75)),
            _claim("also_seen", kind="market", prior=(0.4, 0.2, 0.6)),
        ),
        (
            _arrow("shared", "seen", strength=1.5),
            _arrow("seen", "only_a", strength=1.5),
            _arrow("apart", "also_seen", strength=1.5),
        ),
    )
    one = _folded(graph, Observe(target="seen", value=True))
    two = _folded(
        graph, Observe(target="seen", value=True), Observe(target="also_seen", value=True)
    )

    for claim_id in ("shared", "seen", "only_a"):
        assert abs(two.beliefs[claim_id].p - one.beliefs[claim_id].p) < 0.001, claim_id
    assert two.beliefs["also_seen"] != one.beliefs["also_seen"]


def test_an_observation_a_later_supposition_overrode_is_not_read() -> None:
    """ "This happened", then "suppose it did not": the second word is the one in force.

    A later edit on the same claim overrides an earlier one, so an observation a
    supposition has overridden is not news any more. The check is the sharp one:
    every number the world reports is byte-identical to the one the supposition
    alone produces. The two differ in `assignments` alone, and rightly — that is
    the record of what the user did, and they did make two edits.
    """
    graph = _two_pieces()
    withdrawn = _folded(
        graph,
        Observe(target="near", value=True),
        Do(target="near", value=False, at=None),
    )
    only_supposed = _folded(graph, Do(target="near", value=False, at=None))

    answers = {"exclude": {"assignments"}}
    assert withdrawn.model_dump_json(**answers) == only_supposed.model_dump_json(**answers)


# --- How a supposition holds -------------------------------------------------


@given(st.data())
@many
def test_a_supposition_is_true_and_stays_true(data: st.DataObject) -> None:
    """While a supposition holds, the claim is true. Not .98, not .999.

    "Suppose this is true" is a hard fact, not a strong push, and a tool that
    answered it with a number would be lying about what the user asked for. Every
    day of the claim's series is named `supposed`, which is what lets the tile show
    a word where a likelihood would mislead. Nothing ends it: there is no
    retraction on this product any more (decision record 0017).
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="do")).model_copy(update={"at": None})

    world = _folded(graph, edit)

    expected = 1.0 if edit.value else 0.0
    assert set(world.states[edit.target]) == {"supposed"}
    assert set(world.series[edit.target]) == {expected}
    assert world.beliefs[edit.target] == Belief(p=expected, lo=expected, hi=expected, owner="model")
    assert world.retractions == ()


def test_a_claim_supposed_twice_reads_the_last_word() -> None:
    """Supposing a claim a second time works, and the second word is the one in force.

    A user who supposed something true and then changed their mind simply says it
    again. The last edit on a claim is the one the engine reads — there is no
    calendar of stretches, because a claim's number is about its own deadline
    rather than about a day.
    """
    graph = _two_step_map()

    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Do(target="top", value=False, at=DAY_ZERO + timedelta(days=5)),
    )
    plainly_false = _folded(graph, Do(target="top", value=False, at=None))

    assert set(world.states["top"]) == {"supposed"}
    assert set(world.series["top"]) == {0.0}
    assert world.beliefs == plainly_false.beliefs


def test_supposing_a_claim_cuts_the_arrows_pointing_at_it() -> None:
    """Supposing a claim cuts every arrow into it, so what pushed at it is gone from the map.

    This is the fold's doing rather than the engine's, and it is worth a test of
    its own because it is what makes *Suppose this is true* mean what it says: the
    claim is held at the value the reader typed and nothing argues with it.
    """
    graph = _two_step_map()

    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Insert(
            proposition=_claim("strike"),
            links=(_arrow("strike", "top", strength=-3.0),),
        ),
        Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=1)),
        Do(target="top", value=True, at=DAY_ZERO + timedelta(days=5)),
    )

    assert set(world.states["top"]) == {"supposed"}
    assert "strike->top" not in {one.id for one in world.graph.links}


def test_the_day_a_supposition_names_is_not_read() -> None:
    """A value fixed on a claim holds for the whole window, whatever day the edit names.

    **This is a change the by-deadline engine made, and it is said out loud rather
    than left for a reader to find.** The old engine read a likelihood on each day
    and so had a calendar of stretches: a supposition dated day five held from day
    five. A claim's number is now *the chance it is true by its deadline*, which is
    one question about the whole window, so there is no day for a stretch to start
    on. The date a `do` carries is kept in `assignments`, because it is the record
    of what the reader did, and the arithmetic does not read it.
    """
    graph = _two_step_map()

    at_the_start = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    part_way = _folded(graph, Do(target="top", value=True, at=DAY_ZERO + timedelta(days=12)))
    past_the_end = _folded(graph, Do(target="top", value=True, at=DAY_ZERO + timedelta(days=400)))

    answers = {"exclude": {"assignments"}}
    assert part_way.model_dump_json(**answers) == at_the_start.model_dump_json(**answers)
    assert past_the_end.model_dump_json(**answers) == at_the_start.model_dump_json(**answers)


@pytest.mark.parametrize("value", (True, False))
def test_an_observation_forces_the_claim_it_names(value: bool) -> None:
    """A claim reported to have happened reads as having happened, on the day it is judged.

    An observation is news rather than a lever, so the tile shows a number rather
    than a word — and that number is the certainty the reader reported.
    """
    graph = _two_step_map()

    world = _folded(graph, Observe(target="middle", value=value))

    assert world.beliefs["middle"].p == (1.0 if value else 0.0)
    assert set(world.states["middle"]) == {"sampled"}


# --- The time axis, the shapes, and the sentences under the map --------------


def test_a_long_window_is_drawn_at_a_manageable_number_of_points() -> None:
    """A window of years is drawn at about 180 days rather than one point per day.

    Nobody scrubs a two-year axis a day at a time. The world says which day each
    point stands for, because past the cap they are no longer one a day.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis", days=5),
            _claim("ending", kind="market", days=900),
        ),
        (_arrow("top", "ending"),),
    )

    world = _folded(graph)

    assert world.days == 900
    assert len(world.series["ending"]) < 190
    assert len(world.series_days) == len(world.series["ending"])
    assert world.series_days[0] == 0
    assert world.series_days[-1] == 900
    assert any("180" in one for one in world.warnings), world.warnings


def test_the_long_window_warning_says_what_the_engine_actually_does() -> None:
    """The sentence a reader is shown about a long window has to be true of the engine.

    This one is drawn verbatim in the browser, so it is the whole of what a reader
    is ever told about the thinning, and it has already been wrong once: it used to
    say *every day is still worked out*, which stopped being true the moment the
    engine started working out only the days it sends. A number the reader can see
    is a promise, and so is a sentence.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis", days=5),
            _claim("ending", kind="market", days=900),
        ),
        (_arrow("top", "ending"),),
    )

    world = _folded(graph)
    about_the_window = [one for one in world.warnings if str(SERIES_CAP) in one]

    assert about_the_window == [
        f"This map runs for {world.days} days, so each claim's series is drawn at "
        f"{SERIES_CAP} evenly spaced points rather than one for every day. Every claim is "
        "still worked out on its own window, cut into slices from its own resolve-by day; "
        "these are the days the line is drawn at."
    ], world.warnings
    assert len(world.series_days) < world.days + 1


@given(st.data())
@a_few
def test_a_long_window_still_keeps_every_resolve_by_day(data: st.DataObject) -> None:
    """Whatever the cap drops, it never drops a day a claim is judged on.

    A tile's headline number is read on the claim's own resolve-by day. If that day
    were not one of the points its series carries, the number on the tile would not
    be a point of the line drawn underneath it — and a reader scrubbing to the
    claim's own date would land somewhere near it and read something else.
    """
    graph = data.draw(graphs())
    world = _folded(graph)
    assume(world.days + 1 > 180)

    judged = {
        min((one.resolution.by - world.day_zero).days, world.days) for one in graph.propositions
    }
    assert judged <= {max(0, one) for one in world.series_days}


def test_an_arrow_that_pushes_harder_than_a_near_certainty_is_called_out() -> None:
    """A push past ±5 is roughly 1% to 99% on a coin flip, and the reader is told.

    A warning, not a refusal: the map is still legal and the rules layer puts no
    ceiling on a push, because an unbounded number is the honest type. But a model
    that writes twelve has asserted certainty while looking like it gave a number.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=7.5),),
    )

    world = _folded(graph)

    assert any("second look" in one for one in world.warnings), world.warnings


def test_the_warning_writes_the_push_the_way_the_product_does() -> None:
    """The sentence quotes the push to one place, with its sign, and never sixteen digits.

    This warning is read by a person, beside the map. A push arithmetic worked out
    rather than a person typed is held by the computer as 5.199999999999999, and a
    number nobody wrote and nobody could act on is exactly the state this product
    refuses to put on screen.

    A push is **not** a likelihood and is deliberately not written as one. It runs
    from minus infinity to plus infinity on the log-odds scale, so the likelihood
    rule — two significant figures with a guard at each end — would answer `>.99`
    for this push, which says the opposite of what the sentence means.
    """
    worked_out = 0.1 + 5.1
    assert repr(worked_out) == "5.199999999999999"

    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=worked_out),),
    )

    world = _folded(graph)

    loud = [one for one in world.warnings if "second look" in one]
    assert len(loud) == 1, world.warnings
    assert "5.199999999999999" not in loud[0], loud[0]
    assert "pushes by +5.2," in loud[0], loud[0]


def test_a_ramp_with_no_rise_time_arrives_at_once() -> None:
    """A ramp climbs across its delay, and a ramp with no delay has nothing to climb.

    Reading it as "full size on the day itself" is the only answer that is not a
    division by nothing, and it makes such an arrow behave as a step — byte for
    byte, which is what makes it a consequence of the shape rather than a rule.
    """
    climbing = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, shape="ramp", lag=0.0),),
    )
    stepping = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, shape="step", lag=0.0),),
    )

    ramped = _folded(climbing, Do(target="top", value=True, at=DAY_ZERO))
    stepped = _folded(stepping, Do(target="top", value=True, at=DAY_ZERO))

    assert ramped.series["ending"] == stepped.series["ending"]
    assert ramped.beliefs["ending"] == stepped.beliefs["ending"]


def test_a_shape_decides_when_the_chance_arrives_and_not_how_much_of_it_does() -> None:
    """Two shapes, one stated number: the tile agrees and the line does not.

    This is the sharpest thing the by-deadline engine changed about an arrow's
    shape. A number on an arrow is now *the chance its target reaches its deadline
    with that one cause on*, and the rate is calibrated so that the whole window
    delivers exactly that — whatever shape the push has. So a ramp and a step with
    the same push and the same delay land within a thousandth of each other on the
    tile, and where they differ is **when** the chance arrives: the step is at full
    size the day it lands and the ramp is still climbing, so the two lines part
    company inside the delay. The ramp is the one **ahead** there, which is worth
    reading twice: a ramp starts climbing from the day its cause is settled while a
    step does nothing at all until the delay is out, and the calibration then gives
    the ramp the larger rate to make the same total arrive over a smaller shape.
    """

    def one_shaped(shape: str) -> World:
        graph = _map(
            (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
            (_arrow("top", "ending", strength=2.0, shape=shape, lag=10.0),),
        )
        return _folded(graph, Do(target="top", value=True, at=DAY_ZERO))

    ramped, stepped = one_shaped("ramp"), one_shaped("step")

    assert abs(ramped.beliefs["ending"].p - stepped.beliefs["ending"].p) < 0.005
    assert ramped.series["ending"][10] > stepped.series["ending"][10]


def test_an_edit_that_writes_a_users_own_number_moves_nothing() -> None:
    """The user's own number sits beside the model's and is not pushed through the map.

    Propagating a user's whole worldview is a real feature with its own design and
    its own stack. Until then the honest thing is to show the two numbers side by
    side rather than half-mixing them.
    """
    graph = _two_step_map()
    mine = Believe(target="top", belief=Belief(p=0.9, lo=0.8, hi=0.95, owner="user"))

    plain = _folded(graph)
    with_my_number = _folded(graph, mine)

    assert with_my_number.beliefs == plain.beliefs
    assert with_my_number.series == plain.series


def test_changing_one_push_moves_what_is_downstream_of_it() -> None:
    """Retuning an arrow reaches the claim it points at, and everything that claim leads to."""
    graph = _two_step_map()

    plain = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    softened = _folded(
        graph, Do(target="top", value=True, at=DAY_ZERO), Retune(link="top->middle", strength=0.1)
    )

    assert softened.beliefs["middle"].p < plain.beliefs["middle"].p
    assert softened.beliefs["ending"].p < plain.beliefs["ending"].p


@pytest.mark.parametrize("half_life", (None, 0.0))
def test_a_spike_with_nothing_to_fade_by_is_a_fault_in_the_map(half_life: float | None) -> None:
    """A spike that never says how fast it fades is refused by the map's own rules.

    Neither nothing at all nor nought says how fast a spike fades, so neither can
    be evaluated, and no default is invented anywhere — reject, never repair. The
    engine still answers for a map that arrived some other way rather than
    dividing by nothing; but such a map never reaches the engine through this
    product, because `validate` refuses it.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, shape="impulse", lag=0.0, half_life=half_life),),
    )

    if half_life is None:
        assert [one.code for one in validate(graph)] == ["impulse_without_half_life"]
    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    assert 0.0 <= world.beliefs["ending"].p <= 1.0


def test_a_value_fixed_on_a_claim_that_is_not_on_the_map_is_ignored() -> None:
    """The engine works out the map it was given, and a stray value fixes nothing.

    Refusing an edit that names a claim the map does not have is the fold's job,
    and it does refuse one, in words. By the time the numbers are worked through,
    the map and the values fixed on it agree — and if a caller ever hands over a
    value about a claim that is not there, it changes nothing rather than crashing
    half way through a world.
    """
    graph = _two_step_map()
    plain = propagate(graph, (), as_of=DAY_ZERO, seed=SEED)
    stray = propagate(
        graph,
        (Assignment(target="not-on-this-map", value=True, at=None, by=0, kind="observe"),),
        as_of=DAY_ZERO,
        seed=SEED,
    )

    assert stray.beliefs == plain.beliefs
    assert stray.series == plain.series
