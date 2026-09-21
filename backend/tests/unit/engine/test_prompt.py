"""What the varying half of a request says, and when it says it.

The standing half is fixed and its fingerprint is checked elsewhere. This is
about the other half: the map written out, the claim pointed at, and the one
thing the question asks for that depends on where in the story that claim sits.
"""

from datetime import date

from katalyst.domain import Graph, Link, Proposition, Resolution
from katalyst.domain.belief import Belief, Beliefs
from katalyst.engine.prompt import ASK_FOR_A_STEP_FIRST, expanding_question

TODAY = date(2026, 9, 17)
"""One day, so no test here is about a date."""


def a_claim(name: str, kind: str) -> Proposition:
    """One claim, with everything the shapes require and nothing a test reads."""
    return Proposition(
        id=name,
        claim=f"Claim {name}.",
        kind=kind,  # type: ignore[arg-type]
        resolution=Resolution(
            criteria="A test two people reading it would agree on.",
            source="A named judge.",
            by=date(2026, 11, 1),
        ),
        prior=Belief(p=0.4, lo=0.2, hi=0.6, owner="model"),
        beliefs=Beliefs(model=Belief(p=0.4, lo=0.2, hi=0.6, owner="model")),
        not_tradeable_reason="Nothing quotes this." if kind == "not_tradeable" else None,
    )


def an_arrow(name: str, source: str, target: str) -> Link:
    """One arrow, with everything the shapes require and nothing a test reads."""
    return Link(
        id=name,
        source=source,
        target=target,
        mode="sustain",
        strength=0.5,
        lag=1.0,
        shape="step",
        rationale="The cause moves the effect, and here is how.",
        provenance="argued",
    )


def a_map(claims: dict[str, str], arrows: list[tuple[str, str]]) -> Graph:
    """Build a small map from claim kinds and the arrows between them."""
    return Graph(
        id="a-map",
        propositions=tuple(a_claim(name, kind) for name, kind in claims.items()),
        links=tuple(
            an_arrow(f"arrow-{index}", source, target)
            for index, (source, target) in enumerate(arrows)
        ),
        hypothesis_id=next(iter(claims)),
    )


def asking(graph: Graph, frontier: str, **rest: object) -> str:
    """Put one expanding question about that map."""
    return expanding_question(
        graph,
        frontier,
        target=None,
        ending_only=False,
        today=TODAY,
        **rest,  # type: ignore[arg-type]
    )


# --- Asking for a step while the story has not started -------------------
#
# Measured on 2026-09-20: a run answered the hypothesis three times running with
# a tradeable ending, the frontier emptied — an ending never joins it — and the
# map stopped at four claims and one layer.


def test_the_first_claim_with_nothing_after_it_is_asked_for_a_step() -> None:
    """The hypothesis, before anything leads on from it."""
    graph = a_map({"H": "hypothesis"}, [])

    assert ASK_FOR_A_STEP_FIRST in asking(graph, "H")


def test_a_claim_one_arrow_from_the_first_is_asked_for_a_step_too() -> None:
    """One layer down is still the very start of a story."""
    graph = a_map({"H": "hypothesis", "A": "event"}, [("H", "A")])

    assert ASK_FOR_A_STEP_FIRST in asking(graph, "A")


def test_a_claim_that_already_has_a_step_after_it_is_asked_for_anything() -> None:
    """Once the story carries on from a claim, an ending off it is welcome.

    This is the half that keeps it a preference rather than a rule: the first
    Opus run's arrow straight from the strait opening to Brent was a good arrow,
    and nothing here or in `expand.py` refuses one.
    """
    graph = a_map({"H": "hypothesis", "A": "event"}, [("H", "A")])

    assert ASK_FOR_A_STEP_FIRST not in asking(graph, "H")


def test_an_ending_is_not_a_step_and_does_not_satisfy_the_preference() -> None:
    """The whole point: an ending closes a line rather than carrying it on."""
    graph = a_map({"H": "hypothesis", "M1": "market"}, [("H", "M1")])

    assert ASK_FOR_A_STEP_FIRST in asking(graph, "H")


def test_a_claim_deeper_in_the_story_is_asked_for_anything() -> None:
    """Two layers down the argument has been made, so an ending is the point."""
    graph = a_map(
        {"H": "hypothesis", "A": "event", "B": "event"},
        [("H", "A"), ("A", "B")],
    )

    assert ASK_FOR_A_STEP_FIRST not in asking(graph, "B")


def test_the_last_ending_seeking_call_is_never_asked_for_a_step() -> None:
    """That call asks for an ending and nothing else; asking for both would be nonsense."""
    graph = a_map({"H": "hypothesis"}, [])

    question = expanding_question(graph, "H", target=None, ending_only=True, today=TODAY)

    assert ASK_FOR_A_STEP_FIRST not in question
    assert "answer only with an ending" in question


def test_the_preference_names_no_claim_and_no_violation() -> None:
    """It is about where a claim sits, so it is the same bytes for every claim there.

    Which keeps the promise the next call is never told why the last one was
    refused: a refused claim is asked again with these same bytes.
    """
    graph = a_map({"H": "hypothesis", "A": "event"}, [("H", "A")])

    assert asking(graph, "H") == asking(graph, "H")
    assert "refused" not in ASK_FOR_A_STEP_FIRST
    assert "violation" not in ASK_FOR_A_STEP_FIRST
