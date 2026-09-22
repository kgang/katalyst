"""The Verify door: a graded route to the place the person asked about, or none.

A person can ask *does this get me there?* The only two honest answers are a
route, graded, and a plain statement that there is no route. Making one up is the
state this product exists to refuse.

**Not one number an engine worked out is written down here.** Every test asserts
an identity, a direction or an ordering, on maps this file builds, or compares a
number with the same number reached a different way.

Three words, used throughout, and each is one of the three quantities decision
record 0022 puts beside a route in place of the multiplied-out number it deleted.
*The shift* — how far apart the destination sits in two worlds, one with the map's
starting claim supposed true and one with it supposed false. *The joint* — the
chance every step on the route is true at once. *The weakest arrow* — the single
arrow on the route whose removal leaves the smallest shift behind.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest

from katalyst.domain import Belief, Beliefs, Graph, Link, Proposition, Resolution
from katalyst.domain.branch import Branch
from katalyst.domain.intervention import Do
from katalyst.domain.patch import apply
from katalyst.domain.propagation import World, propagate
from katalyst.engine.verify import verdict
from katalyst.fixtures import FIXTURE_DATE, HORMUZ

SOMEWHERE_ELSE = "Iranian crude exports return to pre-sanction levels."

DAY_ZERO = date(2026, 10, 1)
"""Day zero for every map this file builds. No test here reads a clock."""

SEED = 20260922
"""The one number every draw in this file comes from, so a failure repeats exactly."""

ROUND_OFF = 1e-12
"""How far two orderings of the same arithmetic may sit apart.

Never a tolerance on an answer: it is only used where this file works the same
quantity out in a different order from the code under test, and double-precision
addition is not associative.
"""


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


# --- Small maps this file builds, and the worlds they make ------------------


def a_claim(name: str, *, prior: float = 0.3) -> Proposition:
    """One plain claim, with the chance it comes true on its own and the day it is judged."""
    stated = Belief(p=prior, lo=max(0.0, prior - 0.1), hi=min(1.0, prior + 0.1), owner="model")
    return Proposition(
        id=name,
        claim=f"The claim written down under the name {name}.",
        kind="event",
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=60),
        ),
        prior=stated,
        beliefs=Beliefs(model=stated),
    )


def an_arrow(source: str, target: str) -> Link:
    """One plain arrow, every one of them as well-backed as every other.

    They are all the same strength and all the same provenance on purpose: which
    route the map's own rule picks is then settled by its stated tie-breaks — the
    shorter route, and then the arrow the map lists first — rather than by a number
    a test chose.
    """
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="trigger",
        strength=1.5,
        lag=0.0,
        shape="step",
        rationale="The first claim moves the second one, for a stated reason.",
        provenance="argued",
    )


def a_map(name: str, claims: tuple[str, ...], arrows: tuple[tuple[str, str], ...]) -> Graph:
    """A whole small map, with the first claim named as the one it started from."""
    return Graph(
        id=name,
        propositions=tuple(a_claim(one) for one in claims),
        links=tuple(an_arrow(source, target) for source, target in arrows),
        hypothesis_id=claims[0],
    )


def a_world(graph: Graph) -> World:
    """Work a map through the exact core, at one version of it.

    One version because decision record 0022's three numbers carry no range of
    their own: a claim has one likelihood, and this is the map worked through once.
    """
    return propagate(
        graph,
        (),
        as_of=DAY_ZERO,
        seed=SEED,
        versions=1,
        # The flip makes this the default.
        engine="by_deadline",
    )


def supposing(graph: Graph, *, value: bool) -> World:
    """The same map worked through with its starting claim supposed true, or false.

    Built through the ordinary fold every edit goes through, so this is the same
    supposition the Verify door makes, reached by the front door rather than by
    calling the door's own working.
    """
    folded = apply(
        graph,
        Branch(
            id="test",
            label="The starting claim, supposed",
            interventions=(Do(target=graph.hypothesis_id, value=value, at=None),),
        ),
    )
    assert not isinstance(folded, list), folded
    supposed, fixed = folded
    return propagate(
        supposed,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        versions=1,
        # The flip makes this the default.
        engine="by_deadline",
    )


A_CHAIN = a_map("chain", ("H", "A", "D"), (("H", "A"), ("A", "D")))
"""The starting claim, one step, and the destination."""

SHARING_A_CAUSE = a_map(
    "shared",
    ("H", "S", "C", "D"),
    (("H", "C"), ("S", "C"), ("S", "D"), ("C", "D")),
)
"""Both steps of the route are caused by S as well, so the two are not independent.

This is the map decision record 0022 is about: multiplying the two steps' own
numbers together would claim they are independent, and here they are not.
"""

A_HUB = a_map(
    "hub",
    ("H", "A", "C", "D"),
    (("H", "A"), ("A", "D"), ("A", "C"), ("C", "D")),
)
"""Everything reaches the destination through A, but only one arrow out of A is on the route.

Taking the arrow into A away leaves the destination with nothing from the starting
claim at all; taking the route's other arrow away still leaves the way round
through C. So the two arrows on the route are worth different amounts.
"""

TWO_WAYS_ROUND = a_map(
    "two ways round",
    ("H", "A", "B", "D"),
    (("H", "A"), ("A", "D"), ("H", "B"), ("B", "D")),
)
"""Two routes of the same length and the same backing, so the map's own tie-break picks.

Taking an arrow off the named route leaves the other route standing, so the shift
falls by part of itself rather than to nothing — which is what the weakest arrow's
share has to be checked against.
"""


# --- The route, and the honest refusal to invent one ------------------------


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


def test_when_nothing_touches_the_destination_the_verdict_says_what_it_did_reach() -> None:
    """Closest has no meaning on that map, so a computed answer to a real question is given.

    It names what the story reaches along its **best-backed** route, and says so:
    the sentence used to say "got as far as", which reads as furthest and is not
    what is ranked (2026-09-20).
    """
    with_a_destination = HORMUZ.model_copy(
        update={"propositions": (*HORMUZ.propositions, a_claim_nobody_reaches())}
    )

    answer = verdict(with_a_destination, "WANTED")

    assert answer.nearest in {one.id for one in HORMUZ.propositions}
    assert answer.nearest != HORMUZ.hypothesis_id
    assert "no arrow on it touches that claim at all" in answer.why
    assert "best-backed thing the story does reach" in answer.why


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


# --- Chains are worked out, not multiplied (decision record 0022) -----------


def test_nothing_multiplies_a_route_out_anywhere_on_the_server() -> None:
    """The multiplication is gone from the source, not merely gone from the answer.

    A number that is not the probability of anything must not be reachable by any
    caller, so this reads the shipped code rather than one function's output.
    """
    shipped = Path(__file__).resolve().parents[3] / "src"
    assert shipped.is_dir()
    multiplying = [
        one.relative_to(shipped)
        for one in sorted(shipped.rglob("*.py"))
        if "_multiplied_out" in one.read_text(encoding="utf-8")
    ]
    assert multiplying == []


def test_the_multiplied_out_likelihood_is_absent_however_the_door_is_asked() -> None:
    """A number nobody computed is never shown, and never invented to fill a slot."""
    assert verdict(HORMUZ, "M1").product is None
    assert verdict(A_CHAIN, "D", world=a_world(A_CHAIN)).product is None


def test_the_three_numbers_are_absent_until_a_world_is_handed_in() -> None:
    """Without the numbers, the route is graded structurally and nothing is guessed at."""
    answer = verdict(A_CHAIN, "D")

    assert answer.kind == "reached"
    assert answer.shift is None
    assert answer.joint is None
    assert answer.weakest_arrow is None
    assert answer.share_of_the_shift is None


def test_the_shift_is_the_difference_between_two_supposed_worlds() -> None:
    """The shift, worked out a second way: two whole worlds, subtracted at the destination.

    The door works this out from the two passes it makes; this test builds the two
    worlds through the ordinary fold and reads the destination's own likelihood off
    each. Same number, two roads.
    """
    answer = verdict(A_CHAIN, "D", world=a_world(A_CHAIN))

    both_ways_round = supposing(A_CHAIN, value=True).beliefs["D"].p - (
        supposing(A_CHAIN, value=False).beliefs["D"].p
    )
    assert answer.shift == both_ways_round
    assert answer.shift > 0.0


def test_the_shift_is_nought_when_no_route_reaches_the_destination() -> None:
    """Supposing a claim cuts the arrows into it, so it moves nothing it cannot reach.

    Exactly nought, not nearly nought: the exact solve leaves a claim the
    supposition cannot reach bit for bit where it was, under either supposition, so
    the two numbers subtract to zero rather than to a rounding error.
    """
    unreachable = a_map("apart", ("H", "A", "Z"), (("H", "A"),))

    answer = verdict(unreachable, "Z", world=a_world(unreachable))

    assert answer.kind == "no_path"
    assert answer.shift == 0.0
    assert answer.joint is None
    assert answer.weakest_arrow is None


def test_the_joint_of_a_route_of_one_step_is_that_steps_own_number() -> None:
    """One step has to go right, so the joint is that one step's likelihood."""
    answer = verdict(A_CHAIN, "A", world=a_world(A_CHAIN))

    assert answer.path == ("H", "A")
    assert answer.joint == supposing(A_CHAIN, value=True).beliefs["A"].p


def test_the_joint_is_not_the_product() -> None:
    """Two steps that share a cause are not independent, so multiplying them is wrong.

    The map is built so that both steps of the route are caused by the same claim.
    Multiplying the two steps' own likelihoods together claims they are
    independent; the joint does not, and the two answers differ.
    """
    answer = verdict(SHARING_A_CAUSE, "D", world=a_world(SHARING_A_CAUSE))
    each = supposing(SHARING_A_CAUSE, value=True).beliefs

    assert answer.path == ("H", "C", "D")
    assert answer.joint is not None
    assert answer.joint != each["C"].p * each["D"].p


def test_the_joint_is_never_more_than_any_step_it_is_made_of() -> None:
    """Everything going right is at most as likely as any one thing going right."""
    for graph, destination in ((SHARING_A_CAUSE, "D"), (A_HUB, "D"), (TWO_WAYS_ROUND, "D")):
        answer = verdict(graph, destination, world=a_world(graph))
        each = supposing(graph, value=True).beliefs
        assert answer.joint is not None
        for step in answer.path[1:]:
            assert answer.joint <= each[step].p + ROUND_OFF, f"{graph.id}, {step}"


def test_the_weakest_arrow_is_the_one_whose_removal_loses_the_most() -> None:
    """On a map with a way round, the arrow with no way round it carries the most.

    Both arrows named are on the route. Taking the first away leaves the
    destination nothing at all from the starting claim; taking the second away
    still leaves the way round. So the first is the one that carries the shift, and
    the door must name it rather than the other.
    """
    answer = verdict(A_HUB, "D", world=a_world(A_HUB))

    assert answer.path == ("H", "A", "D")
    assert answer.weakest_arrow == "H->A"


def test_deleting_the_weakest_arrow_costs_the_share_it_claims() -> None:
    """Take the named arrow off the map, work the shift out again, and check the sum.

    The share is what the verdict promises the arrow is worth. Removing the arrow
    and asking the same door again is the only way to hold it to that promise: what
    is left must be the shift less the share it claimed.
    """
    world = a_world(TWO_WAYS_ROUND)
    answer = verdict(TWO_WAYS_ROUND, "D", world=world)

    assert answer.shift is not None
    assert answer.weakest_arrow is not None
    assert answer.share_of_the_shift is not None
    assert 0.0 < answer.share_of_the_shift < 1.0

    without = TWO_WAYS_ROUND.model_copy(
        update={
            "links": tuple(one for one in TWO_WAYS_ROUND.links if one.id != answer.weakest_arrow)
        }
    )

    left = verdict(without, "D", world=world).shift

    assert left is not None
    assert left == pytest.approx(answer.shift * (1.0 - answer.share_of_the_shift), rel=ROUND_OFF)
