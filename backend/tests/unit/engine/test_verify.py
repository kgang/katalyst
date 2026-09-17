"""The Verify door: a graded route to the place the person asked about, or none.

A person can ask *does this get me there?* The only two honest answers are a
route, graded, and a plain statement that there is no route. Making one up is the
state this product exists to refuse.
"""

from katalyst.domain import Belief, Beliefs, Link, Proposition, Resolution
from katalyst.engine.expand import verdict
from katalyst.fixtures import FIXTURE_DATE, HORMUZ

SOMEWHERE_ELSE = "Iranian crude exports return to pre-sanction levels."


def a_claim_nobody_reaches(claim: str = SOMEWHERE_ELSE) -> Proposition:
    """Build a claim to stand on the map as a destination."""
    stated = Belief(p=0.2, lo=0.1, hi=0.4, owner="model")
    return Proposition(
        id="WANTED",
        claim=claim,
        kind="event",
        resolution=Resolution(
            criteria="A test two people reading it would agree on.",
            source="A named judge.",
            by=FIXTURE_DATE,
        ),
        prior=stated,
        beliefs=Beliefs(model=stated),
    )


def test_a_route_that_exists_is_graded_and_its_steps_are_named() -> None:
    """The route starts at the claim the map started from and ends at the destination."""
    answer = verdict(HORMUZ, "M1")

    assert answer.kind == "reached"
    assert answer.path[0] == HORMUZ.hypothesis_id
    assert answer.path[-1] == "M1"
    assert "reaches" in answer.why


def test_the_route_shown_is_the_best_backed_one_and_not_the_shortest() -> None:
    """The road with the highest low bridge, rather than the road with fewest bridges."""
    straight_but_weak = Link(
        id="H->WANTED",
        source=HORMUZ.hypothesis_id,
        target="WANTED",
        mode="sustain",
        strength=0.2,
        lag=1.0,
        shape="step",
        rationale="A story rather than a mechanism.",
        provenance="asserted",
    )
    long_but_strong = Link(
        id="B->WANTED",
        source="B",
        target="WANTED",
        mode="sustain",
        strength=0.2,
        lag=1.0,
        shape="step",
        rationale="A mechanism with a document behind it.",
        sources=(HORMUZ.links[0].sources[0] if HORMUZ.links[0].sources else None,),  # type: ignore[arg-type]
        provenance="documented",
    )
    both_ways = HORMUZ.model_copy(
        update={
            "propositions": (*HORMUZ.propositions, a_claim_nobody_reaches()),
            "links": (*HORMUZ.links, straight_but_weak, long_but_strong),
        }
    )

    answer = verdict(both_ways, "WANTED")

    assert answer.kind == "reached"
    assert answer.path[-2] == "B"
    assert len(answer.path) > 2


def test_the_multiplied_out_likelihood_is_absent_until_the_numbers_are_run() -> None:
    """A number nobody computed is never shown, and never invented to fill a slot."""
    assert verdict(HORMUZ, "M1").product is None


def test_the_multiplied_out_likelihood_leaves_out_the_claim_we_are_supposing() -> None:
    """The person is supposing the first claim happens, so it is not a step that must go right."""
    numbers = {one.id: Belief(p=0.5, lo=0.4, hi=0.6, owner="model") for one in HORMUZ.propositions}
    answer = verdict(HORMUZ, "M1", beliefs=numbers)

    assert answer.product is not None
    steps_that_must_go_right = len(answer.path) - 1
    assert answer.product == 0.5**steps_that_must_go_right


def test_verify_returns_no_path_rather_than_a_bridge() -> None:
    """Nothing adds an arrow to make a route exist, so the honest answer is the only one."""
    with_a_destination = HORMUZ.model_copy(
        update={"propositions": (*HORMUZ.propositions, a_claim_nobody_reaches())}
    )

    answer = verdict(with_a_destination, "WANTED")

    assert answer.kind == "no_path"
    assert answer.path == ()
    assert len(with_a_destination.links) == len(HORMUZ.links)
    assert SOMEWHERE_ELSE in answer.why


def test_when_nothing_touches_the_destination_the_verdict_says_how_far_the_story_got() -> None:
    """Closest has no meaning on that map, so a computed answer to a real question is given."""
    with_a_destination = HORMUZ.model_copy(
        update={"propositions": (*HORMUZ.propositions, a_claim_nobody_reaches())}
    )

    answer = verdict(with_a_destination, "WANTED")

    assert answer.nearest in {one.id for one in HORMUZ.propositions}
    assert answer.nearest != HORMUZ.hypothesis_id
    assert "no arrow on it touches that claim at all" in answer.why
    assert "got as far as" in answer.why


def test_when_something_does_touch_the_destination_the_nearest_claim_is_a_real_distance() -> None:
    """Arrows are walked either way here: the question is how close the map came."""
    pointing_at_it = Link(
        id="WANTED->B",
        source="WANTED",
        target="B",
        mode="sustain",
        strength=0.2,
        lag=1.0,
        shape="step",
        rationale="More barrels reaching the market hold the price down.",
        provenance="argued",
    )
    with_a_destination = HORMUZ.model_copy(
        update={
            "propositions": (*HORMUZ.propositions, a_claim_nobody_reaches()),
            "links": (*HORMUZ.links, pointing_at_it),
        }
    )

    answer = verdict(with_a_destination, "WANTED")

    assert answer.kind == "no_path"
    assert answer.nearest == "B"
    assert "closest claim the story does reach" in answer.why
