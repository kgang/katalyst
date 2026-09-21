"""What the engine does with a map, over maps nobody wrote by hand.

`propagate` turns a map and the values its edits fixed into a world: a likelihood
and a range for every claim on the day it is judged, a likelihood for every day
in between, and a named word for each of those days. Four things are easy to get
wrong here and each has a test whose whole job is to catch exactly one of them.

* **The range must not be the coin flips.** Freeze every prior at a point and the
  band has to collapse. An engine that reports how much its own sampling wobbled
  would pass everything else in this file and fail `test_band_is_not_sampling_noise`.
* **The versions must not see the branch.** A base world and a branch world built
  from one seed have to try the same versions of the map, or every comparison
  between them is the user's edit plus a wash of noise.
* **A supposition is true in every world**, not at ninety-eight per cent.
* **A stated likelihood and its range are fitted on the log-odds scale**, half by
  half, which is what `test_range_matches_analytic_first_order_on_fixture` checks
  from the other side: a second, independent method has to give the same band.

**Budgets.** The shipped default is two thousand versions of the map times eight
worlds each. That is about seventy milliseconds a world on the worked example and
far too slow to run hundreds of times, so the tests over generated maps use a
much smaller budget and say so. Nothing about the arithmetic changes with the
budget; only how steady the numbers are, and these tests are about what the
arithmetic *is*.
"""

import math
from datetime import date, timedelta
from itertools import pairwise

import networkx
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
    introduced_by,
    propagate,
    validate,
    versions_of,
)
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ
from tests.strategies import branches, graphs, interventions, seeds, uncertain_beliefs

many = settings(max_examples=25, deadline=None)
a_few = settings(max_examples=12, deadline=None)

SMALL = {"versions": 16, "worlds": 4}
"""The budget the tests over generated maps run at, and why it is not the shipped one.

Sixteen versions of the map and four worlds under each is sixty-four draws rather
than sixteen thousand. Every rule these tests check — the bounds, replay, what a
supposition does, which claims an edit may move — is true at any budget; only how
steady the numbers are depends on it, and a test that took seventy milliseconds a
world could not be run over hundreds of maps.
"""

FULL = {"versions": 2_000, "worlds": 8}
"""The shipped budget, for the handful of tests that are about how steady a number is."""

DAY_ZERO = date(2026, 1, 1)
"""Day zero for the generated maps, which carry resolve-by dates from 2026 onwards."""

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""


# --- Small maps the example tests build by hand ----------------------------


def _claim(
    identifier: str,
    kind: str = "event",
    prior: tuple[float, float, float] = (0.3, 0.2, 0.45),
    days: int = 30,
) -> Proposition:
    """One plain claim with a stated likelihood and range."""
    low, middle, high = prior[1], prior[0], prior[2]
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


def _folded(graph: Graph, *edits: object, **budget: int) -> World:
    """Fold a branch onto a map and work the numbers through, in one line."""
    branch = Branch(id="branch-under-test", label="A branch a test wrote", interventions=edits)  # type: ignore[arg-type]
    result = apply(graph, branch)
    assert not isinstance(result, list), result
    left_behind, fixed = result
    return propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        **(budget or SMALL),
    )


def _folded_if_it_applies(graph: Graph, branch: Branch, **budget: int) -> World:
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
    return propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        **(budget or SMALL),
    )


def _a_claim_with_causes(data: st.DataObject, graph: Graph) -> str:
    """Pick a claim to observe from the ones the map actually gives causes to.

    Read off the shape of the map rather than drawn and then discarded. Every claim
    but the first on a map that is all of one piece is given at least one cause by
    `graphs()` itself, so the list is never empty; that guarantee is asserted rather
    than assumed, so the day it stops holding this says so out loud instead of
    quietly checking fewer maps.
    """
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
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(one.id for one in graph.propositions)
    walk.add_edges_from((one.source, one.target) for one in graph.links if not one.reflexive)
    return set(networkx.ancestors(walk, claim_id))


def _log_odds(likelihood: float) -> float:
    """The log-odds of a likelihood, for the arithmetic a test checks by hand."""
    return math.log(likelihood / (1.0 - likelihood))


def _likelihood(log_odds: float) -> float:
    """A likelihood from log-odds, for the arithmetic a test checks by hand."""
    return 1.0 / (1.0 + math.exp(-log_odds))


# --- Honest numbers --------------------------------------------------------


@given(st.data())
@many
def test_probability_bounds(data: st.DataObject) -> None:
    """Every number a world reports is a likelihood, and every range is around its own number.

    Nothing between 0 and 1 is optional here: a likelihood outside that is not a
    likelihood, and a range that does not contain the number it is a range around
    is not a range.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))
    world = _folded_if_it_applies(graph, branch)

    for claim_id, belief in world.beliefs.items():
        assert 0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0, claim_id
        assert belief.owner == "model"
    for claim_id, drawn in world.series.items():
        assert all(0.0 <= one <= 1.0 for one in drawn), claim_id
        assert len(drawn) == len(world.states[claim_id])


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

    world = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=data.draw(seeds()), **SMALL)

    for belief in world.beliefs.values():
        assert 0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0
    for drawn in world.series.values():
        assert all(0.0 <= one <= 1.0 for one in drawn)


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
    happened to be written down in. Each claim's random numbers come from its own
    identifier for the same reason.

    The **arrows** are not shuffled here, and that is deliberate: an arrow's place
    on the map is the order it arrived in — folding a branch appends each new
    arrow after the ones already there — and that order decides which arrow a badge
    names when two undermine a supposition on the same day. Shuffling the arrows
    would be shuffling a record of what happened, not a tie nobody has broken.
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
def test_same_seed_same_world(data: st.DataObject) -> None:
    """One seed gives one world — the same versions of the map and the same dice inside them.

    Both streams are checked, because a world that replayed its dice but not its
    versions would look right until two worlds were compared.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))

    first = _folded_if_it_applies(graph, branch)
    second = _folded_if_it_applies(graph, branch)

    assert first.model_dump_json() == second.model_dump_json()
    before, after = versions_of(first), versions_of(second)
    assert before.days == after.days
    for claim_id, drawn in before.priors.items():
        assert (drawn == after.priors[claim_id]).all(), claim_id
        assert (before.likelihood[claim_id] == after.likelihood[claim_id]).all(), claim_id


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

    first = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=seed, **SMALL)
    second = propagate(left_behind, fixed, as_of=DAY_ZERO, seed=seed, **SMALL)

    assert first.model_dump_json() == second.model_dump_json()


@given(st.data())
@many
def test_versions_do_not_depend_on_the_branch(data: st.DataObject) -> None:
    """A base world and a branch world from one seed try the very same versions of the map.

    This is what makes a difference between two worlds readable. Compare them
    version by version and the only thing that changed is the edit, because the
    numbers underneath were held fixed. Without it every comparison is the user's
    change plus a wash of sampling noise — and a run of the same inputs twice
    cannot see the difference, which is why this is its own test.
    """
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))

    base = versions_of(_folded(graph))
    branched = versions_of(_folded_if_it_applies(graph, branch))

    for claim_id, drawn in base.priors.items():
        assert claim_id in branched.priors, "an edit removed a claim; there is no such operation"
        assert (drawn == branched.priors[claim_id]).all(), claim_id


# --- The two kinds of arrow --------------------------------------------------


def test_trigger_persists_after_parent_reset() -> None:
    """A domino that has fallen stays fallen, whatever happens to the one before it.

    The cause is supposed true, a later edit undermines the supposition, and the
    claim the cause pushed is byte-identical to the world in which nothing ever
    undermined it. That is what `trigger` means, and it is half of the worked
    example: the war-risk premium came out of the oil price once and does not go
    back in because the strait's standing was withdrawn.
    """
    graph = _two_step_map()
    strike = _claim("strike")
    upset = Insert(proposition=strike, links=(_arrow("strike", "top", strength=-3.0),))

    undisturbed = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    reset = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        upset,
        Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=1)),
    )

    assert undisturbed.states["top"][3] == "supposed"
    assert reset.states["top"][3] == "pushed"
    assert reset.series["middle"] == undisturbed.series["middle"]
    assert reset.beliefs["middle"] == undisturbed.beliefs["middle"]


def test_sustain_retracts_when_parent_removed() -> None:
    """An apple falls the moment the desk goes: a sustain push is zero when its cause is not true.

    Forced false, the cause holds nothing up, and the claim below reads exactly
    what it would read if the arrow were not on the map at all — not nearly, but
    to the byte.
    """
    held = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, mode="sustain"),),
    )
    alone = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (),
    )

    without_its_cause = _folded(held, Do(target="top", value=False, at=DAY_ZERO))
    without_the_arrow = _folded(alone, Do(target="top", value=False, at=DAY_ZERO))
    with_its_cause = _folded(held, Do(target="top", value=True, at=DAY_ZERO))

    assert without_its_cause.series["ending"] == without_the_arrow.series["ending"]
    assert with_its_cause.series["ending"][0] > without_its_cause.series["ending"][0]


# --- Assert is not observe ---------------------------------------------------


@given(st.data())
@many
def test_do_leaves_ancestors_unchanged(data: st.DataObject) -> None:
    """Supposing something moves nothing that could have caused it.

    Supposing the strait opens must not quietly raise the odds that a diplomatic
    settlement happened. That is the difference between pulling a lever and
    reporting news, and it is the reason the product offers two verbs.
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="do"))

    base = _folded(graph)
    supposed = _folded(graph, edit)

    for cause in _causes_of(graph, edit.target):
        assert supposed.beliefs[cause] == base.beliefs[cause], cause
        assert supposed.series[cause] == base.series[cause], cause


@given(st.data())
@a_few
def test_observe_may_update_ancestors(data: st.DataObject) -> None:
    """Learning something reaches back into what caused it, which supposing never does.

    Keeping only the worlds in which the claim came out as observed changes what
    the survivors say about the claim's causes just as much as about what it
    causes.

    **The map is built to be one a cause can move on, never filtered down to one.**
    Every claim's prior comes from `uncertain_beliefs()` — a likelihood this product
    would be willing to print, with a range of real width around it — so nothing on
    the map is settled before the engine starts and the versions really do draw
    different numbers for each claim. The claim to observe is picked from the ones
    that actually have causes, read off the shape of the map.

    Asking instead for *any* likelihood above nought, as this test once did, lets
    through a number like `3.4e-289`: a cause that comes out false in every world,
    so nothing upstream can move, and the test fails on a rare seed rather than on a
    real fault. A generator that builds what a test needs cannot have that hole, and
    it throws nothing away to get there.

    **And this one runs at the shipped budget, not the small one.** The thing it is
    about is the weight an observation gives each version — the share of that
    version's worlds that survived — and at four worlds per version that share is
    one of five numbers. A map whose observed claim is nearly certain then discards
    no world at all in any version, every weight is 1, and the two worlds come out
    identical: the test would be reporting how coarse its own budget is rather than
    anything about the engine. The propagation chapter's section B6 says the same
    thing about the size of the move. Measured over four hundred generated maps:
    sixteen of them could not show the effect at sixteen versions of four worlds,
    and every single one showed it at the shipped two thousand of eight.

    **What the map does *not* need is an arrow that pushes.** How hard the arrows
    push is left free here on purpose, and about a fifth of the maps this test
    draws have nothing but arrows of strength nought into the observed claim. The
    test below says why that is fine and pins it.
    """
    graph = data.draw(graphs(priors=uncertain_beliefs()))
    target = _a_claim_with_causes(data, graph)
    causes = _causes_of(graph, target)

    base = _folded(graph, **FULL)
    learned = _folded(graph, Observe(target=target, value=True), **FULL)

    assert any(learned.beliefs[one] != base.beliefs[one] for one in causes)


@given(st.data())
@a_few
def test_an_observation_moves_a_cause_even_when_no_arrow_pushes(data: st.DataObject) -> None:
    """An observation reaches a cause through the version weights, not along the arrows.

    This is the one worth stating plainly, because the arrows look as though they
    must be what carries it. They are not. Observing something throws away the
    worlds it did not happen in, and each version is then counted by the share of
    its worlds that survived. A cause's number is the average of what each version
    said about it — so counting the versions differently moves that average, and it
    moves it whether or not a single arrow on the map pushes by anything at all.

    So this takes a whole generated map and sets **every** arrow's push to exactly
    nothing, which is the strongest form of the worry, and requires a cause to move
    anyway. What it needs instead is that the versions disagree about the cause,
    which is what `uncertain_beliefs()` builds: a range of real width, so every
    version draws a different number and a different weighting gives a different
    average.

    It is the same mechanism as a claim with **no causes at all** moving under an
    observation — an arrow of strength nought and no arrow are the same thing to
    the arithmetic — which `domain/diff.py` reports as `moved_only_by_reweighting`
    and `spec/multiverse/diff.md` B3 spells out.

    Measured before it was written: over nine hundred generated maps with every
    arrow flattened to nought, a cause moved in every one.
    """
    graph = _pushing_nothing(data.draw(graphs(priors=uncertain_beliefs())))
    assert all(one.strength == 0.0 for one in graph.links), "every arrow pushes nothing"
    target = _a_claim_with_causes(data, graph)
    causes = _causes_of(graph, target)

    base = _folded(graph, **FULL)
    learned = _folded(graph, Observe(target=target, value=True), **FULL)

    assert any(learned.beliefs[one] != base.beliefs[one] for one in causes)


def test_observe_warns_below_two_percent_survival() -> None:
    """When almost no world survives an observation, the world says the *range* is unreliable.

    A version that survived twice out of eight contributes a very noisy number to
    the band, and the noise correction can only subtract what it can measure. So
    the warning is about the range and not merely about the number.
    """
    unlikely = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.005, 0.005, 0.005)),
            _claim("ending", kind="market"),
        ),
        (_arrow("top", "ending"),),
    )

    world = _folded(unlikely, Observe(target="top", value=True), **FULL)

    assert any("range" in one for one in world.warnings), world.warnings
    assert any("unreliable" in one for one in world.warnings), world.warnings


def test_an_observation_nothing_survives_still_answers() -> None:
    """An observation no world at all matches still gives back a world, loudly warned.

    Refusing to answer would be worse: the reader would be left with a spinning
    wheel instead of a sentence saying the map cannot produce what they said they
    saw.
    """
    impossible = _map(
        (
            _claim("top", kind="hypothesis", prior=(0.0, 0.0, 0.0)),
            _claim("ending", kind="market"),
        ),
        (_arrow("top", "ending"),),
    )

    world = _folded(impossible, Observe(target="top", value=True))

    assert any("unreliable" in one for one in world.warnings), world.warnings
    assert 0.0 <= world.beliefs["ending"].p <= 1.0


# --- How a supposition holds, and how it ends --------------------------------


@given(st.data())
@many
def test_supposition_is_true_in_every_world_until_undermined(data: st.DataObject) -> None:
    """While a supposition holds, the claim is true in **every** world. Not .98, not .999.

    "Suppose this is true" is a hard fact, not a strong push, and a tool that
    answered it with a number would be lying about what the user asked for. Every
    day of the claim's series is named `supposed`, which is what lets the tile show
    a word where a likelihood would mislead.
    """
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph, kind="do")).model_copy(update={"at": None})

    world = _folded(graph, edit)

    expected = 1.0 if edit.value else 0.0
    assert set(world.states[edit.target]) == {"supposed"}
    assert set(world.series[edit.target]) == {expected}
    assert world.beliefs[edit.target] == Belief(p=expected, lo=expected, hi=expected, owner="model")
    assert world.retractions == ()


def test_retraction_dates_from_the_cause_not_the_push() -> None:
    """A supposition ends the day the world changed, never the day the push arrives.

    Tying it to the arrival would tie "do I still take your word for this" to a
    delay parameter: change a lag from three days to thirty and the supposition
    would silently outlive the news. So the same branch with a thirty-day lag ends
    the supposition on exactly the same day.
    """
    graph = _two_step_map()
    strike = _claim("strike")

    def undermined(lag: float) -> World:
        return _folded(
            graph,
            Do(target="top", value=True, at=DAY_ZERO),
            Insert(
                proposition=strike,
                links=(_arrow("strike", "top", strength=-3.0, mode="sustain", lag=lag),),
            ),
            Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=2)),
        )

    quick, slow = undermined(3.0), undermined(30.0)

    assert [one.at for one in quick.retractions] == [DAY_ZERO + timedelta(days=2)]
    assert [one.at for one in slow.retractions] == [DAY_ZERO + timedelta(days=2)]
    assert quick.retractions[0].by_claim == "strike"
    assert quick.retractions[0].by_link == "strike->top"
    assert quick.retractions[0].by == 1
    # The day the push lands is a different day, and the states say which is which.
    assert quick.states["top"][2:6] == ("withdrawn", "withdrawn", "withdrawn", "pushed")
    assert set(slow.states["top"][2:]) == {"withdrawn"}


def test_a_retraction_always_names_the_edit_that_added_the_arrow() -> None:
    """Which edit added an undermining arrow is always known, and the engine says so loudly.

    It is a theorem rather than a convention: supposing a claim cuts every arrow
    pointing at it at that moment, so any arrow that later pushes against it must
    have been added afterwards, by an edit with a position in the branch. An engine
    that shrugged and left the badge blank would be hiding a broken promise between
    two pieces of our own code — so it is the one thing this file raises for.
    """
    graph = _two_step_map()
    strike = _claim("strike")
    branch = Branch(
        id="branch-undermining",
        label="Suppose the first, then knock it over",
        interventions=(
            Do(target="top", value=True, at=DAY_ZERO),
            Insert(
                proposition=strike,
                links=(_arrow("strike", "top", strength=-3.0, mode="sustain", lag=1.0),),
            ),
            Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=2)),
        ),
    )
    folded = apply(graph, branch)
    assert not isinstance(folded, list)
    left_behind, fixed = folded

    told = propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        **SMALL,
    )
    assert [one.by for one in told.retractions] == [1]

    with pytest.raises(ValueError, match="added by an edit"):
        propagate(left_behind, fixed, as_of=DAY_ZERO, seed=SEED, **SMALL)


def test_a_claim_can_be_supposed_again_after_it_was_undermined() -> None:
    """Supposing a claim a second time works, and the second word holds from its own day.

    A later edit overrides an earlier one, so a user who watched their supposition
    withdrawn can simply say it again. The second one holds from its own day until
    something undermines it again — a **new** arrow, because supposing a claim
    cuts every arrow pointing at it at that moment, including the one that
    undermined the first supposition. One retraction per ending.
    """
    graph = _two_step_map()
    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Insert(
            proposition=_claim("first-strike"),
            links=(_arrow("first-strike", "top", strength=-3.0, mode="sustain", lag=1.0),),
        ),
        Do(target="first-strike", value=True, at=DAY_ZERO + timedelta(days=1)),
        Do(target="top", value=True, at=DAY_ZERO + timedelta(days=5)),
        Insert(
            proposition=_claim("second-strike"),
            links=(_arrow("second-strike", "top", strength=-3.0, mode="sustain", lag=1.0),),
        ),
        Do(target="second-strike", value=True, at=DAY_ZERO + timedelta(days=7)),
    )

    assert world.states["top"][:10] == (
        "supposed",
        "supposed",
        "supposed",
        "supposed",
        "supposed",
        "supposed",
        "supposed",
        "withdrawn",
        "pushed",
        "pushed",
    )
    assert [(one.target, one.at, one.by_claim) for one in world.retractions] == [
        ("top", DAY_ZERO + timedelta(days=7), "second-strike")
    ]


def test_supposing_a_claim_again_cuts_what_undermined_it() -> None:
    """Saying it again cuts the arrow that knocked it down, exactly as saying it the first time did.

    This is the one consequence of re-supposing worth reading twice. Supposing a
    claim cuts every arrow pointing at it **at that moment** — that is what the
    first supposition did, and the second one does the same thing to the arrow that
    undermined the first. The arrow is gone from the map the fold leaves behind, so
    the world worked out from that map has nothing that ever pushed against the
    claim, and the series reads `supposed` throughout with no retraction at all.

    It is not a number the reader cannot account for: the branch still lists all
    four edits in order, and the arrow's removal is the third edit doing exactly
    what the second verb on the box says it does.
    """
    graph = _two_step_map()
    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Insert(
            proposition=_claim("strike"),
            links=(_arrow("strike", "top", strength=-3.0, mode="sustain", lag=1.0),),
        ),
        Do(target="strike", value=True, at=DAY_ZERO + timedelta(days=1)),
        Do(target="top", value=True, at=DAY_ZERO + timedelta(days=5)),
    )

    assert set(world.states["top"]) == {"supposed"}
    assert world.retractions == ()
    assert "strike->top" not in {one.id for one in world.graph.links}


def test_two_arrows_on_the_same_day_are_broken_by_which_arrived_first() -> None:
    """When two arrows undermine a supposition on one day, the one added first names the badge.

    Some settled answer is needed or the badge would name a different arrow on
    different runs and a world would stop replaying. The answer is the order the
    arrows arrived on the map: the base map's first, then each `insert`'s in the
    order it listed them — which is exactly the order a map carries them in.
    """
    graph = _two_step_map()
    both = _claim("both")
    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Insert(
            proposition=both,
            links=(
                _arrow("both", "top", strength=-3.0, mode="sustain", lag=1.0),
                _arrow("both", "top", strength=-4.0, mode="sustain", lag=5.0).model_copy(
                    update={"id": "both->top-again"}
                ),
            ),
        ),
        Do(target="both", value=True, at=DAY_ZERO + timedelta(days=1)),
    )

    assert [one.by_link for one in world.retractions] == ["both->top"]


# --- The range is how sure we are of the numbers, not how the dice fell ------


def test_band_is_not_sampling_noise() -> None:
    """Freeze every prior at a point and the band collapses: it is not the coin flips.

    This is the single most likely way to get the engine wrong. An implementation
    that reported how much its own sampling wobbled would pass every other test in
    this file and fail here, loudly: with no stated range left anywhere on the map
    there is nothing for a band to be about, so there must be no band.
    """
    real = propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED, **FULL)
    flat = propagate(_frozen(HORMUZ), (), as_of=FIXTURE_DATE, seed=SEED, **FULL)

    for claim_id, belief in flat.beliefs.items():
        width = belief.hi - belief.lo
        assert width < 0.02, f"{claim_id} still reports a band of {width:.3f}"
        assert width < 0.1 * (real.beliefs[claim_id].hi - real.beliefs[claim_id].lo)


def test_range_matches_analytic_first_order_on_fixture() -> None:
    """Two independent methods, one answer: the sampled band agrees with the calculus.

    The other method is the delta method — work out how much each stated range
    moves the answer, and add those up — which was measured and rejected as the
    engine because it is fifty times slower and produces no worlds. It is kept as
    a cross-check, and this is that check: a band that came out the right shape and
    the wrong size would pass everything else and fail here.

    The sums are done on the log-odds scale, half by half, because that is the
    scale the pushes add on and the scale the stated ranges were fitted on.
    """
    sampled = propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED, **FULL)
    middles = propagate(_frozen(HORMUZ), (), as_of=FIXTURE_DATE, seed=SEED, **FULL)
    claims = [one.id for one in HORMUZ.propositions]
    halves = {
        one.id: (
            (_log_odds(one.prior.p) - _log_odds(one.prior.lo)) / 1.2816,
            (_log_odds(one.prior.hi) - _log_odds(one.prior.p)) / 1.2816,
        )
        for one in HORMUZ.propositions
    }

    step = 0.05
    slope: dict[str, dict[str, float]] = {one: {} for one in claims}
    for source in claims:
        up = propagate(_frozen(HORMUZ, source, step), (), as_of=FIXTURE_DATE, seed=SEED, **FULL)
        down = propagate(_frozen(HORMUZ, source, -step), (), as_of=FIXTURE_DATE, seed=SEED, **FULL)
        for target in claims:
            slope[target][source] = (
                _log_odds(up.beliefs[target].p) - _log_odds(down.beliefs[target].p)
            ) / (2.0 * step)

    for target in claims:
        below = math.sqrt(
            sum(
                (slope[target][one] * halves[one][0 if slope[target][one] > 0 else 1]) ** 2
                for one in claims
            )
        )
        above = math.sqrt(
            sum(
                (slope[target][one] * halves[one][1 if slope[target][one] > 0 else 0]) ** 2
                for one in claims
            )
        )
        middle = _log_odds(middles.beliefs[target].p)
        assert abs(_likelihood(middle - 1.2816 * below) - sampled.beliefs[target].lo) < 0.02
        assert abs(_likelihood(middle + 1.2816 * above) - sampled.beliefs[target].hi) < 0.02


def _frozen(graph: Graph, moved: str | None = None, step: float = 0.0) -> Graph:
    """Rewrite every prior as a point, optionally nudging one of them along the log-odds scale.

    With no stated range anywhere, every version of the map is the same map, which
    is what lets the two tests above ask "what is left when the ranges are gone?"
    and "how much does one range move the answer?" without the two questions
    getting in each other's way.
    """
    rewritten = []
    for one in graph.propositions:
        middle = one.prior.p if moved != one.id else _likelihood(_log_odds(one.prior.p) + step)
        point = Belief(p=middle, lo=middle, hi=middle, owner="model")
        rewritten.append(
            one.model_copy(
                update={
                    "prior": point,
                    "beliefs": one.beliefs.model_copy(update={"model": point}),
                }
            )
        )
    return graph.model_copy(update={"propositions": tuple(rewritten)})


def test_where_a_bands_width_comes_from_is_carried_but_shown_to_nobody() -> None:
    """Each claim's band is broken down by whose prior explains it, and no route reads it yet.

    It falls out of the same sample the band does, so working it out costs nothing
    and throwing it away would mean running the whole thing twice later. On the
    worked example most of Brent's band is Brent's own prior — pin that down and
    the band would shrink to a fraction of its width.
    """
    world = propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED, **FULL)

    shares = world.range_shares["B"]
    assert set(shares) == {one.id for one in HORMUZ.propositions}
    assert all(0.0 <= one <= 1.0 for one in shares.values())
    assert shares["B"] > 0.5
    assert shares["B"] == max(shares.values())
    assert world.conditionals == {}


# --- The time axis, the shapes, and the sentences under the map --------------


def test_the_series_reads_the_arithmetic_written_in_the_chapter() -> None:
    """One claim, worked out by hand, against the engine.

    A step arrow with no delay is at full size the day its cause is settled, and a
    spike halves every half-life from there. Two days of arithmetic anybody can
    check on paper, against sixteen thousand simulated worlds.
    """
    graph = _map(
        (
            _claim("top", kind="hypothesis"),
            _claim("ending", kind="market", prior=(0.28, 0.15, 0.42)),
        ),
        (_arrow("top", "ending", strength=-2.4, shape="impulse", lag=0.0, half_life=10.0),),
    )

    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO), **FULL)

    by_hand_day_zero = _likelihood(_log_odds(0.28) - 2.4)
    by_hand_day_ten = _likelihood(_log_odds(0.28) - 1.2)
    assert abs(world.series["ending"][0] - by_hand_day_zero) < 0.01
    assert abs(world.series["ending"][10] - by_hand_day_ten) < 0.01


def test_a_claim_with_no_cause_and_no_assignment_starts_its_clock_at_day_zero() -> None:
    """A claim the map says nothing about in time is settled on the first day of the window.

    Being settled is not being true: the claim is still sampled from its own prior
    in every draw. Its clock starting only says when the arrows leaving it begin to
    measure their delays from.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=1.0, lag=2.0),),
    )

    world = _folded(graph, **FULL)

    assert abs(world.series["top"][0] - world.series["top"][-1]) < 0.01
    assert world.series["ending"][0] < world.series["ending"][5]


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


def test_a_ramp_with_no_rise_time_arrives_at_once() -> None:
    """A ramp climbs across its delay, and a ramp with no delay has nothing to climb.

    Reading it as "full size on the day itself" is the only answer that is not a
    division by nothing, and it makes such an arrow behave as a step — which the
    chapter raises as something nobody has said out loud before now.
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


def test_a_ramp_climbs_across_its_delay() -> None:
    """Where a ramp does have a rise time, it arrives a little at a time."""
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, shape="ramp", lag=10.0),),
    )

    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO), **FULL)

    climbing = world.series["ending"][:11]
    assert all(earlier < later for earlier, later in pairwise(climbing))
    assert abs(world.series["ending"][10] - world.series["ending"][20]) < 0.01


def test_a_supposition_dated_past_the_end_of_the_window_never_takes_hold() -> None:
    """A value fixed from a day past the end of the window changes nothing inside it."""
    graph = _map(
        (_claim("top", kind="hypothesis", days=10), _claim("ending", kind="market", days=10)),
        (_arrow("top", "ending", strength=2.0),),
    )

    late = _folded(graph, Do(target="top", value=True, at=DAY_ZERO + timedelta(days=400)))

    assert set(late.states["top"]) == {"sampled"}


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

    assert softened.series["middle"][0] < plain.series["middle"][0]
    assert softened.beliefs["ending"].p < plain.beliefs["ending"].p


def test_a_world_says_which_map_branch_and_seed_it_came_from() -> None:
    """A world carries its three inputs, because it is a result and never a source of truth."""
    graph = _two_step_map()

    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))

    assert world.base_id == graph.id
    assert world.branch_id is None
    assert world.seed == SEED
    assert (world.versions, world.worlds) == (SMALL["versions"], SMALL["worlds"])
    assert world.day_zero == DAY_ZERO
    assert world.assignments[0].target == "top"
    assert World.model_validate_json(world.model_dump_json()) == world


@pytest.mark.parametrize("value", (True, False))
def test_an_observation_forces_the_claim_it_names(value: bool) -> None:
    """A claim reported to have happened reads as having happened, every day of the window."""
    graph = _two_step_map()

    world = _folded(graph, Observe(target="middle", value=value), **FULL)

    assert set(world.series["middle"]) == {1.0 if value else 0.0}
    assert set(world.states["middle"]) == {"sampled"}


def test_an_arrow_that_pushes_neither_way_undermines_nothing() -> None:
    """An arrow of no strength is not an opposing arrow, so it ends no supposition.

    Opposing means pushing against the value that was supposed — negative against
    a claim supposed true, positive against one supposed false. Nought is neither,
    and a supposition that ended because of an arrow doing nothing would name an
    edit that changed no number.
    """
    graph = _two_step_map()
    idle = _claim("idle")

    world = _folded(
        graph,
        Do(target="top", value=True, at=DAY_ZERO),
        Insert(proposition=idle, links=(_arrow("idle", "top", strength=0.0, mode="sustain"),)),
        Do(target="idle", value=True, at=DAY_ZERO + timedelta(days=1)),
    )

    assert world.retractions == ()
    assert set(world.states["top"]) == {"supposed"}


@pytest.mark.parametrize("half_life", (None, 0.0))
def test_a_spike_with_nothing_to_fade_by_is_a_fault_in_the_map(half_life: float | None) -> None:
    """A spike that never says how fast it fades is refused by the map's own rules.

    Neither nothing at all nor nought says how fast a spike fades, so neither can
    be evaluated, and no default is invented anywhere — reject, never repair. The
    engine still has a net under it for a map that arrived some other way, and the
    net holds the push at full size rather than dividing by nothing; but such a map
    never reaches the engine through this product, because `validate` refuses it.
    """
    graph = _map(
        (_claim("top", kind="hypothesis"), _claim("ending", kind="market")),
        (_arrow("top", "ending", strength=2.0, shape="impulse", lag=0.0, half_life=half_life),),
    )

    if half_life is None:
        assert [one.code for one in validate(graph)] == ["impulse_without_half_life"]
    world = _folded(graph, Do(target="top", value=True, at=DAY_ZERO))
    assert world.series["ending"][0] == world.series["ending"][20]


def test_a_value_fixed_on_a_claim_that_is_not_on_the_map_is_ignored() -> None:
    """The engine works out the map it was given, and a stray value fixes nothing.

    Refusing an edit that names a claim the map does not have is the fold's job,
    and it does refuse one, in words. By the time the numbers are worked through,
    the map and the values fixed on it agree — and if a caller ever hands over a
    value about a claim that is not there, it changes nothing rather than crashing
    half way through a world.
    """
    graph = _two_step_map()
    plain = propagate(graph, (), as_of=DAY_ZERO, seed=SEED, **SMALL)

    stray = propagate(
        graph,
        (Assignment(target="not-on-this-map", value=True, at=None, by=0, kind="observe"),),
        as_of=DAY_ZERO,
        seed=SEED,
        **SMALL,
    )

    assert stray.beliefs == plain.beliefs
    assert stray.warnings == plain.warnings
