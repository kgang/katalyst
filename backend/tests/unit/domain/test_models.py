"""The data shapes: what they refuse to be built out of, and what survives a round trip.

These are example-based tests, one small hand-written case per rule, because the
rules here are about a single object rather than about a whole map. The
property-based tests over thousands of generated maps arrive with the validity
rules.

Two ideas are checked over and over below.

*Frozen* means an instance cannot be changed once it is built. A change to a
claim is never an edit in place; it is a new instance, recorded as an edit on a
branch. If a model could be changed in place, the untouched original every branch
is computed against would stop being untouched.

*Round trip* means: build the object, turn it into the text we send over the
wire, read that text back, and get something equal to what we started with. The
whole product is replayable only if that holds.
"""

from collections.abc import Callable
from datetime import date

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from katalyst.domain import (
    BaseRate,
    Belief,
    Beliefs,
    Believe,
    Branch,
    Do,
    Evidence,
    Graph,
    Insert,
    Intervention,
    Link,
    Observe,
    Payoff,
    Proposition,
    Refine,
    Resolution,
    Retune,
    Source,
)

# --- Small builders, so each test says only what it is about ---------------


def a_belief(owner: str = "model", p: float = 0.35, lo: float = 0.2, hi: float = 0.5) -> Belief:
    """One likelihood, owned by whoever the test needs."""
    return Belief(p=p, lo=lo, hi=hi, owner=owner)  # type: ignore[arg-type]


def a_resolution() -> Resolution:
    """One way of settling a claim: the test, the judge, and the date."""
    return Resolution(
        criteria="At least 14 consecutive days of unrestricted commercial transit.",
        source="Lloyd's List transit counts",
        by=date(2026, 11, 1),
    )


def a_proposition(
    identifier: str = "H",
    kind: str = "hypothesis",
    claim: str = "The Strait of Hormuz reopens to unrestricted commercial transit.",
) -> Proposition:
    """One claim, with the model's number on it and nothing else filled in."""
    return Proposition(
        id=identifier,
        claim=claim,
        kind=kind,  # type: ignore[arg-type]
        resolution=a_resolution(),
        prior=a_belief(),
        beliefs=Beliefs(model=a_belief()),
    )


def a_link(identifier: str = "H->B", source: str = "H", target: str = "B") -> Link:
    """One arrow, with a mechanism written on it."""
    return Link(
        id=identifier,
        source=source,
        target=target,
        mode="trigger",
        strength=1.6,
        lag=2.0,
        shape="impulse",
        half_life=30.0,
        rationale="The war-risk premium priced into crude unwinds once transit data confirms it.",
        confidence="argued",
        provenance="argued",
    )


def a_graph() -> Graph:
    """Two claims and the arrow between them, the smallest map worth looking at."""
    return Graph(
        id="g1",
        propositions=(
            a_proposition(),
            a_proposition(
                identifier="B",
                kind="market",
                claim="Brent crude settles below $68 for five sessions.",
            ),
        ),
        links=(a_link(),),
        hypothesis_id="H",
    )


def a_payoff() -> Payoff:
    """What one tradeable ending is worth."""
    return Payoff(instrument="Brent below $70 on 2026-10-31", direction="long", magnitude=0.03)


# --- One test per rule the classes check while they are being built --------


def test_belief_bounds_at_construction() -> None:
    """A likelihood must sit inside its own range, and the range inside 0 and 1.

    There is no third outcome: either the belief that comes back satisfies
    low <= likelihood <= high, or nothing comes back at all. Nothing is quietly
    clamped to fit.
    """
    ordered = a_belief(p=0.35, lo=0.2, hi=0.5)
    assert ordered.lo <= ordered.p <= ordered.hi

    with pytest.raises(ValidationError, match="low <= likelihood <= high"):
        a_belief(p=0.1, lo=0.2, hi=0.5)
    with pytest.raises(ValidationError, match="low <= likelihood <= high"):
        a_belief(p=0.9, lo=0.2, hi=0.5)
    with pytest.raises(ValidationError):
        a_belief(p=1.4, lo=0.2, hi=1.5)
    with pytest.raises(ValidationError):
        a_belief(p=-0.1, lo=-0.2, hi=0.5)


def test_owner_matches_slot() -> None:
    """Each of the three slots holds a number owned by the voice it is named for.

    A belief sitting in the wrong slot would make the never-merge rule
    unenforceable: a user's number could sit in the model's chip and nothing
    anywhere would notice.
    """
    both_ways = Beliefs(model=a_belief("model"), user=a_belief("user"), market=a_belief("market"))
    assert both_ways.model.owner == "model"

    with pytest.raises(ValidationError, match="'model' slot holds a belief owned by 'user'"):
        Beliefs(model=a_belief("user"))
    with pytest.raises(ValidationError, match="'user' slot holds a belief owned by 'model'"):
        Beliefs(model=a_belief("model"), user=a_belief("model"))
    with pytest.raises(ValidationError, match="'market' slot holds a belief owned by 'user'"):
        Beliefs(model=a_belief("model"), market=a_belief("user"))


def test_believe_requires_user_owner() -> None:
    """A `believe` edit carries the user's own number and nobody else's.

    There is no valid map in which the model's number arrives dressed as the
    user's, so this fails at the door rather than later, over a whole map.
    """
    mine = Believe(target="M1", belief=a_belief("user", p=0.3, lo=0.2, hi=0.45))
    assert mine.belief.owner == "user"

    for impostor in ("model", "market"):
        with pytest.raises(ValidationError, match="carries the user's own belief"):
            Believe(target="M1", belief=a_belief(impostor))


def test_prior_is_owned_by_the_model() -> None:
    """A claim's prior is the model's own number; any other owner is a bug in our code."""
    with pytest.raises(ValidationError, match="prior must be owned by 'model'"):
        Proposition(
            id="H",
            claim="The Strait of Hormuz reopens.",
            kind="hypothesis",
            resolution=a_resolution(),
            prior=a_belief("user"),
            beliefs=Beliefs(model=a_belief("model")),
        )


def test_hypothesis_id_names_a_claim_on_the_map() -> None:
    """A map's starting claim has to be one of the claims on it."""
    with pytest.raises(ValidationError, match="must name a proposition on the same map"):
        Graph(
            id="g1",
            propositions=(a_proposition(),),
            links=(),
            hypothesis_id="not-on-this-map",
        )


@pytest.mark.parametrize(
    ("rule", "build"),
    [
        (
            "a base rate cannot count more true cases than it has cases",
            lambda: BaseRate(reference_class="Hormuz disruptions since 1980", k=7, n=5),
        ),
        (
            "a base rate cannot count a negative number of true cases",
            lambda: BaseRate(reference_class="Hormuz disruptions since 1980", k=-1, n=5),
        ),
        (
            "a base rate over an empty set of cases says nothing",
            lambda: BaseRate(reference_class="Hormuz disruptions since 1980", k=0, n=0),
        ),
        (
            "a piece of evidence counts between 0 and 1, and no more",
            lambda: Evidence(
                claim="Omani mediation reported.", url="http://x", direction=1, weight=1.4
            ),
        ),
        (
            "a piece of evidence counts between 0 and 1, and no less",
            lambda: Evidence(
                claim="Omani mediation reported.", url="http://x", direction=1, weight=-0.1
            ),
        ),
        (
            "a piece of evidence points one way or the other, never neither",
            lambda: Evidence(
                claim="Omani mediation reported.", url="http://x", direction=0, weight=0.3
            ),
        ),
        (
            "a payoff's size of move is never negative; the side is carried by its direction",
            lambda: Payoff(instrument="Brent below $70", direction="long", magnitude=-0.03),
        ),
        (
            "a payoff is taken from one of two sides",
            lambda: Payoff(instrument="Brent below $70", direction="sideways", magnitude=0.03),
        ),
        (
            "a claim is one of the four kinds and no other",
            lambda: a_proposition(kind="vibe"),
        ),
        (
            "an arrow is a one-time shove or a continuous hold, and nothing else",
            lambda: Link.model_validate({**a_link().model_dump(), "mode": "maybe"}),
        ),
        (
            "an arrow's push has one of three shapes over time",
            lambda: Link.model_validate({**a_link().model_dump(), "shape": "wobble"}),
        ),
        (
            "where a number came from is one of seven recorded answers",
            lambda: Link.model_validate({**a_link().model_dump(), "provenance": "vibes"}),
        ),
    ],
)
def test_construction_refuses_what_it_cannot_honestly_accept(
    rule: str, build: Callable[[], object]
) -> None:
    """Each rule a class checks for itself rejects the case it exists to reject.

    Args:
        rule: The rule in plain words, so a failure reads as a sentence.
        build: A way of building the object that breaks it.
    """
    with pytest.raises(ValidationError):
        build()


# --- Frozen, round trip, and the discriminator -----------------------------


def every_model() -> list[tuple[str, BaseModel]]:
    """One filled-in instance of every shape in the rules layer, named for the report."""
    return [
        ("Belief", a_belief()),
        ("Beliefs", Beliefs(model=a_belief(), user=a_belief("user"), market=a_belief("market"))),
        ("Resolution", a_resolution()),
        ("BaseRate", BaseRate(reference_class="Hormuz disruptions since 1980", k=7, n=9)),
        (
            "Evidence",
            Evidence(
                claim="Omani mediation round reported, both sides attending.",
                url="https://example.test/mediation",
                direction=1,
                weight=0.3,
            ),
        ),
        ("Payoff", a_payoff()),
        ("Proposition", a_proposition()),
        ("Source", Source(url="https://example.test/war-risk", title="War risk rates")),
        ("Link", a_link()),
        ("Graph", a_graph()),
        ("Do", Do(target="H", value=True, at=date(2026, 10, 1))),
        ("Observe", Observe(target="C", value=True)),
        ("Insert", Insert(proposition=a_proposition("S", "event", "Iran is struck."), links=())),
        ("Retune", Retune(link="C->B", strength=0.3)),
        ("Refine", Refine(target="H", into=(a_proposition("H1", "event"),))),
        ("Believe", Believe(target="M1", belief=a_belief("user"))),
        (
            "Branch",
            Branch(
                id="br1",
                label="Hormuz opens, then Iran is struck",
                parent=None,
                interventions=(Do(target="H", value=True), Retune(link="C->B", strength=0.3)),
            ),
        ),
    ]


@pytest.mark.parametrize(("name", "instance"), every_model(), ids=lambda value: str(value))
def test_models_are_frozen(name: str, instance: BaseModel) -> None:
    """Nothing in the rules layer can be changed after it is built.

    Every branch is computed against an original that nobody touches. If one of
    these could be written to, that original would stop being original and every
    stored result would quietly become a lie.
    """
    first_field = next(iter(type(instance).model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, first_field, "anything at all")


@pytest.mark.parametrize(("name", "instance"), every_model(), ids=lambda value: str(value))
def test_models_round_trip_json(name: str, instance: BaseModel) -> None:
    """Every shape survives being written out as text and read back in."""
    written = instance.model_dump_json()
    read_back = type(instance).model_validate_json(written)
    assert read_back == instance


def test_collections_are_tuples_not_lists() -> None:
    """Collections are tuples, because a frozen object holding a list is only half frozen."""
    graph = a_graph()
    assert isinstance(graph.propositions, tuple)
    assert isinstance(graph.links, tuple)
    assert isinstance(graph.links[0].sources, tuple)
    assert isinstance(graph.propositions[0].evidence, tuple)


@pytest.mark.parametrize(
    ("kind", "edit"),
    [
        ("do", Do(target="H", value=True, at=date(2026, 10, 1))),
        ("observe", Observe(target="C", value=True)),
        ("insert", Insert(proposition=a_proposition("S", "event", "Iran is struck."), links=())),
        ("retune", Retune(link="C->B", strength=0.3)),
        ("refine", Refine(target="H", into=(a_proposition("H1", "event"),))),
        ("believe", Believe(target="M1", belief=a_belief("user"))),
    ],
)
def test_intervention_discriminator(kind: str, edit: BaseModel) -> None:
    """Reading `kind` alone is enough to know which of the six edits this is.

    Nothing guesses from which fields happen to be present, and an edit named by
    a word that is not one of the six is refused rather than squeezed into
    whichever shape it nearly fits.
    """
    reader: TypeAdapter[Intervention] = TypeAdapter(Intervention)

    parsed = reader.validate_json(edit.model_dump_json())

    assert parsed.kind == kind
    assert type(parsed) is type(edit)
    assert parsed == edit


def test_intervention_rejects_an_unknown_kind() -> None:
    """An edit whose `kind` is not one of the six is refused, and the message says so."""
    reader: TypeAdapter[Intervention] = TypeAdapter(Intervention)

    with pytest.raises(ValidationError, match="kind"):
        reader.validate_python({"kind": "delete", "target": "H"})
