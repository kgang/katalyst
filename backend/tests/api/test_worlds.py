"""The three routes that work a branch through a map and say what it did.

The point of these tests is the crossing. A world leaves the program as JSON —
eight claims, a likelihood and a range each, a likelihood for every day of the
window and a named word beside it — and has to arrive as the same world. A
refused branch has to arrive as a list of sentences and a status that says whose
fault it was, never as a stack trace.

These run at a **small budget** unless the test is about the budget itself: the
shipped run is two thousand versions of the map times eight worlds each, and a
difference costs four runs of the engine. Nothing about what the routes answer
changes with the budget, only how steady the numbers are.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from katalyst.api.main import app
from katalyst.domain import Belief, Diff, World, diff
from katalyst.engine import worlds as engine
from katalyst.engine.transcript import Transcript, held
from katalyst.fixtures import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE
from tests.strategies import branches, graphs

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

SMALL: dict[str, int] = {"versions": 16, "worlds": 4}
"""Sixty-four draws rather than sixteen thousand. See this file's own note."""

STRIKE: dict[str, Any] = HORMUZ_THEN_STRIKE.model_dump(mode="json")
"""The shipped branch as the browser would send it: a whole branch, not a name."""

no_wandering = settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


def _asked(client: TestClient, route: str, **body: Any) -> Any:
    """Ask one route a question and give back its answer, whatever the status."""
    return client.post(f"/api/{route}", json={"base_id": "hormuz", "seed": SEED, **SMALL, **body})


def test_a_base_world_answers_with_every_claim_on_the_map() -> None:
    """Asking with no branch gives the map as it stands, with a number for every claim.

    That is what the browser asks for first. The route that hands out the stored
    examples still hands out a map and its branches and nothing computed, because
    a map is written by hand and a world never is — so the world arrives here, from
    the engine, rather than being typed into the example.
    """
    with TestClient(app) as client:
        answer = _asked(client, "worlds")

    assert answer.status_code == 200
    world = World.model_validate(answer.json())
    assert world.branch_id is None
    assert world.base_id == "hormuz"
    assert {one.id for one in world.graph.propositions} == set(world.beliefs)
    for claim_id, belief in world.beliefs.items():
        assert 0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0, claim_id
        assert belief.owner == "model"
    assert world.conditionals == {}, "a freshly built world holds no arrow numbers"


def test_the_strike_branch_answers_with_a_world_that_names_its_branch() -> None:
    """A branch sent whole comes back worked through, saying which branch it was.

    The branch travels in the request because there is nowhere to keep one yet.
    Which branch a world came from is written in by the layer that knows, because
    working the numbers through takes a map and the values its edits fixed and
    never the branch itself.
    """
    with TestClient(app) as client:
        answer = _asked(client, "worlds", branch=STRIKE)

    assert answer.status_code == 200
    world = World.model_validate(answer.json())
    assert world.branch_id == HORMUZ_THEN_STRIKE.id
    assert "S" in world.beliefs, "the branch adds a claim the base map has never heard of"
    assert world.retractions == (), "nothing retracts itself any more (decision record 0017)"
    assert set(world.states["H"]) == {"supposed"}
    assert len(world.series["H"]) == len(world.series_days)


def test_the_budget_a_request_may_still_ask_for_reaches_no_arithmetic() -> None:
    """Whatever a request asks for, a world says one version of the map and no inner loop.

    Both fields are **accepted and ignored** (decision records 0028 and 0016): the
    engine works out one version and reports one likelihood per claim, and there is
    no inner loop for a world to run inside. They stay on the wire, with their own
    ceilings, until the browser round closes and the empty fields go together — so
    this asks the route twice, once saying nothing and once asking for the largest
    run the ceilings allow, and requires the same two constants back both times.
    """
    with TestClient(app) as client:
        silent = client.post("/api/worlds", json={"base_id": "hormuz", "seed": SEED})
        asked = client.post(
            "/api/worlds",
            json={
                "base_id": "hormuz",
                "seed": SEED,
                "versions": engine.MOST_VERSIONS,
                "worlds": engine.MOST_WORLDS,
            },
        )

    for answer in (silent, asked):
        world = World.model_validate(answer.json())
        assert (world.versions, world.worlds) == (1, 0)


def test_the_diff_route_ranks_the_endings_and_says_so_in_a_sentence() -> None:
    """Comparing the base map with the strike branch lists the endings that moved, ranked."""
    with TestClient(app) as client:
        answer = _asked(client, "worlds/diff", branch_b=STRIKE)

    assert answer.status_code == 200
    difference = Diff.model_validate(answer.json())
    assert difference.branch_a is None
    assert difference.branch_b == HORMUZ_THEN_STRIKE.id
    assert difference.claims["S"].state == "added"
    assert [one.rank for one in difference.rows] == sorted(
        (one.rank for one in difference.rows), reverse=True
    )
    assert HORMUZ_THEN_STRIKE.label in difference.summary
    assert difference.summary.endswith("untouched.")


def test_diff_route_matches_two_world_calls() -> None:
    """The difference the route gives is exactly the two worlds compared, to the byte.

    The route exists because the comparison needs both worlds at once, and sending
    two whole worlds to the browser so that it can subtract them would be sending
    it work it has no way to check. It must not be a second, slightly different
    answer.
    """
    with TestClient(app) as client:
        before = _asked(client, "worlds")
        after = _asked(client, "worlds", branch=STRIKE)
        route = _asked(client, "worlds/diff", branch_b=STRIKE)

    by_hand = diff(
        World.model_validate(before.json()),
        World.model_validate(after.json()),
        edit_in_words=HORMUZ_THEN_STRIKE.label,
    )
    assert not isinstance(by_hand, list), by_hand
    assert route.json() == by_hand.model_dump(mode="json")


def test_the_conditional_route_supposes_rather_than_observes() -> None:
    """An arrow's number is its target with its source **supposed** true, never observed.

    The two are different numbers and the difference is the whole point. Supposing
    the premium falls cuts it loose from what would have caused it, so nothing is
    learned about the strait. Observing that it fell keeps only the worlds in which
    it did, and those are the worlds where the strait was more often open — cheap
    insurance is evidence the lane really is open — so the oil price reads higher.
    Putting the observed number on a wire that claims a mechanism would be a quiet
    lie, because a reader would have no way to tell which they were looking at.
    """
    supposing = {"kind": "do", "target": "C", "value": True}
    observing = {
        "id": "br-observed",
        "label": "The premium has already fallen",
        "interventions": [{"kind": "observe", "target": "C", "value": True}],
    }
    with TestClient(app) as client:
        arrow = _asked(client, "worlds/conditional", link_id="C->B")
        supposed = _asked(
            client,
            "worlds",
            branch={
                "id": "br-supposed",
                "label": "Suppose the premium falls",
                "interventions": [supposing],
            },
        )
        observed = _asked(client, "worlds", branch=observing)

    assert arrow.status_code == 200
    number = Belief.model_validate(arrow.json())
    assert number.owner == "model"
    assert 0.0 <= number.lo <= number.p <= number.hi <= 1.0

    from_supposing = World.model_validate(supposed.json()).beliefs["B"]
    from_observing = World.model_validate(observed.json()).beliefs["B"]
    assert number == from_supposing, "the arrow's number is the supposed one, exactly"
    assert number.p != from_observing.p, "and observing the same claim gives a different number"


def test_worlds_routes_reject_with_422() -> None:
    """A branch that does not fit the map comes back as 422 with every reason at once.

    Never a server error, never a half-applied branch, never a silent repair. Each
    reason carries a stable code for the interface, the identifier of the thing at
    fault so the right tile can be highlighted, and one plain sentence for the
    person — which names the claim or the arrow by its words and never by its
    identifier.
    """
    nowhere = {
        "id": "br-unknown",
        "label": "Names a claim nobody has",
        "interventions": [{"kind": "do", "target": "not-on-this-map", "value": True}],
    }
    orphan = {
        "id": "br-orphan",
        "label": "Continues from a branch nobody stored",
        "parent": "br-never-written",
        "interventions": [],
    }
    with TestClient(app) as client:
        refusals = [
            _asked(client, "worlds", branch=nowhere),
            _asked(client, "worlds", branch=orphan),
            _asked(client, "worlds/diff", branch_b=nowhere),
            _asked(client, "worlds/conditional", link_id="H->nowhere"),
        ]

    for answer in refusals:
        assert answer.status_code == 422, answer.text
        listed = answer.json()["detail"]
        assert listed, "a refusal says at least one thing"
        for one in listed:
            assert set(one) == {"code", "subject", "message"}
            assert one["code"] in {"unknown_target", "unknown_link", "edit_not_applicable"}
            assert one["message"].endswith(".")
            assert one["subject"] not in one["message"]
            assert len(one["message"].split()) >= 8, "a sentence, not a code"


@given(st.data())
@no_wandering
def test_a_branch_written_for_another_map_is_answered_or_refused_and_never_breaks(
    data: st.DataObject,
) -> None:
    """Send a branch built for a different map and the answer is a world or a refusal.

    Never a server error. The subjects of a branch drawn against some other map
    usually name nothing on this one, so most of these are refused — but a few land
    on a claim that happens to share a name, and those are answered like any other.
    """
    elsewhere = data.draw(graphs())
    branch = data.draw(branches(elsewhere))

    with TestClient(app) as client:
        answer = _asked(client, "worlds", branch=branch.model_dump(mode="json"))

    assert answer.status_code in {200, 422}, answer.text
    if answer.status_code == 422:
        for one in answer.json()["detail"]:
            assert one["code"] and one["subject"] is not None and one["message"]


def test_asking_for_an_example_that_does_not_exist_answers_in_words() -> None:
    """An unknown example name is a 404 with a sentence naming the ones that do exist."""
    with TestClient(app) as client:
        answers = [
            _asked(client, "worlds", base_id="photonics"),
            _asked(client, "worlds/diff", base_id="photonics", branch_b=STRIKE),
            _asked(client, "worlds/conditional", base_id="photonics", link_id="H->B"),
        ]

    for answer in answers:
        assert answer.status_code == 404
        message = answer.json()["detail"]
        assert "photonics" in message
        assert "hormuz" in message
        assert len(message.split()) >= 8


A_GENERATED_MAP = "01JGENERATEDMAP0000000000"
"""A map identifier of the shape the engine mints, so nothing here reads as a stored name."""


@pytest.fixture
def a_generation_this_process_is_holding() -> Iterator[str]:
    """Fold one stand-in generation into this process and give back its map's own name.

    A finished generation is kept in memory, under the identifier of the map it
    built, for the life of the process — which is what lets a reviewer who has just
    watched a map draw itself suppose something on it. Nothing here calls a model:
    what stands in for the generated map is the stored one under a minted name,
    which is exactly what a generated map is to every route below — a map that
    answers to no stored name.

    Yields:
        The map's own identifier, which is what a request sends as its `base_id`.
    """
    held.forget_everything()
    held.remember(
        Transcript(
            generation_id="01JGENERATIONTHATBUILTIT0",
            hypothesis="The Strait of Hormuz is going to open next week.",
            seed=SEED,
            # The day the run happened, which is its map's day zero. The stored
            # example's own date is used so that the two worlds below differ by
            # the name of the map and by nothing else.
            on=FIXTURE_DATE,
            mode="replay",
        ),
        HORMUZ.model_copy(update={"id": A_GENERATED_MAP}),
        in_flight=False,
    )
    yield A_GENERATED_MAP
    held.forget_everything()


def test_a_world_is_built_on_a_generated_map_held_by_its_id(
    a_generation_this_process_is_holding: str,
) -> None:
    """A map this process generated answers here under its own name, like any stored one.

    This is the whole of what lets a reader edit a map they have just watched
    build itself: the six edits, a branch, the two worlds and the change list all
    go through these routes with the generated map's identifier as the base, and
    nothing about them knows or cares where the map came from.

    The proof is the comparison rather than any number written down here: the same
    map under a minted name gives the same world, to the byte, apart from the name
    itself.
    """
    generated = a_generation_this_process_is_holding
    with TestClient(app) as client:
        answer = _asked(client, "worlds", base_id=generated)
        stored = _asked(client, "worlds")

    assert answer.status_code == 200, answer.text
    world = World.model_validate(answer.json())
    assert world.base_id == generated
    assert world.branch_id is None
    assert {one.id for one in world.graph.propositions} == set(world.beliefs)
    for claim_id, belief in world.beliefs.items():
        assert 0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0, claim_id
        assert belief.owner == "model"

    from_the_stored_one = World.model_validate(stored.json())
    assert world.beliefs == from_the_stored_one.beliefs
    assert world.series == from_the_stored_one.series
    assert world.model_dump(mode="json", exclude={"base_id", "graph"}) == (
        from_the_stored_one.model_dump(mode="json", exclude={"base_id", "graph"})
    )


def test_a_branch_folded_onto_a_generated_map_moves_the_same_endings(
    a_generation_this_process_is_holding: str,
) -> None:
    """Supposing something on a generated map gives two worlds and a ranked change list.

    The browser's *Change this claim* is this pair of requests and nothing else: a
    world with the branch folded on, and the difference between that world and the
    one before it. Both have to answer on a generated base, or the panel beside a
    map somebody just watched build itself has nothing to draw.
    """
    generated = a_generation_this_process_is_holding
    with TestClient(app) as client:
        after = _asked(client, "worlds", base_id=generated, branch=STRIKE)
        change = _asked(client, "worlds/diff", base_id=generated, branch_b=STRIKE)
        on_the_stored_one = _asked(client, "worlds/diff", branch_b=STRIKE)

    assert after.status_code == 200, after.text
    assert World.model_validate(after.json()).branch_id == HORMUZ_THEN_STRIKE.id

    assert change.status_code == 200, change.text
    difference = Diff.model_validate(change.json())
    assert difference.base_id == generated
    assert difference.branch_b == HORMUZ_THEN_STRIKE.id
    assert difference.claims["S"].state == "added"
    assert [one.rank for one in difference.rows] == sorted(
        (one.rank for one in difference.rows), reverse=True
    )
    # The same edit on the same map under its stored name says the same thing
    # about every claim, in the same words — which is the one thing worth
    # asserting about the numbers, and the reason no number is written down here.
    also = Diff.model_validate(on_the_stored_one.json())
    assert difference.claims == also.claims
    assert [one.target for one in difference.rows] == [one.target for one in also.rows]
    assert difference.summary == also.summary


def test_a_generation_this_process_no_longer_holds_says_so() -> None:
    """A generated map is held for the life of the process, and the refusal says that.

    A restarted server has forgotten every map it generated, and a reader who
    refreshes on one then asks for a world under an identifier nothing answers to.
    Naming the stored examples alone would leave them thinking they had mistyped a
    name; what is true is that the map was real and this process no longer has it.
    """
    with TestClient(app) as client:
        answer = _asked(client, "worlds", base_id="01JGENERATEDMAPLONGGONE00")

    assert answer.status_code == 404
    message = answer.json()["detail"]
    assert "01JGENERATEDMAPLONGGONE00" in message
    assert "hormuz" in message
    assert "life of the process" in message
    assert len(message.split()) >= 8


def test_a_world_needs_no_key_of_any_kind() -> None:
    """Nothing here asks a language model anything, so nothing here needs a key.

    The whole engine is arithmetic over a map somebody wrote down. A route that
    quietly needed a key would make the tests need one too, and the checks that run
    on every change are given none.
    """
    with TestClient(app) as client:
        answer = _asked(client, "worlds", branch=STRIKE)

    assert answer.status_code == 200
    assert "key" not in answer.text.lower()
