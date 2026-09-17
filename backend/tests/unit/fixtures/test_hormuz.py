"""The Hormuz example is valid, complete, and says what it is.

This example is not decoration. Stack 03a measures its arithmetic against it and
stack 03b draws it, so anything that silently changed in it would change answers
elsewhere with nothing to say why. These tests pin down the things later stacks
rely on: that the map is valid, that it still exercises every shape the model
layer defines, that every number is a range rather than a point, that no arrow
claims evidence it does not cite, and that the two arrows making up the
trigger-versus-sustain showcase are still the way round they are supposed to be.
"""

import json

import pytest

from katalyst.domain import (
    Belief,
    Branch,
    ContractPayoff,
    Graph,
    Insert,
    Link,
    PricePayoff,
    validate,
)
from katalyst.fixtures import EXAMPLES, find
from katalyst.fixtures.hormuz import (
    FIXTURE_DATE,
    HORMUZ,
    HORMUZ_THEN_STRIKE,
    _checked,
)
from tests.unit.test_import_boundary import (
    DOMAIN_PACKAGE,
    DOMAIN_ROOT,
    find_forbidden_imports,
)

TERMINAL_KINDS = ("market", "not_tradeable")

# The four provenance values that claim no outside evidence. An arrow marked
# with anything else is saying a document or a price is behind it, and then it
# has to cite one.
CLAIMS_NO_EVIDENCE = ("asserted", "argued", "user", "simulated")


def inserted_links() -> tuple[Link, ...]:
    """Every arrow the strike branch adds to the map."""
    return tuple(
        link
        for edit in HORMUZ_THEN_STRIKE.interventions
        if isinstance(edit, Insert)
        for link in edit.links
    )


def every_link() -> tuple[Link, ...]:
    """Every arrow in the example, the base map's and the branch's together."""
    return HORMUZ.links + inserted_links()


def every_belief() -> list[tuple[str, Belief]]:
    """Every likelihood in the example, with the claim it sits on, for naming a failure."""
    found: list[tuple[str, Belief]] = []
    inserted = [
        edit.proposition for edit in HORMUZ_THEN_STRIKE.interventions if isinstance(edit, Insert)
    ]
    for proposition in [*HORMUZ.propositions, *inserted]:
        slots = (
            proposition.prior,
            proposition.beliefs.model,
            proposition.beliefs.user,
            proposition.beliefs.market,
        )
        found.extend((proposition.id, belief) for belief in slots if belief is not None)
    return found


def test_the_rules_layer_never_reads_the_examples() -> None:
    """Whether a map is valid may not depend on which examples we happen to ship.

    The arrow between these two points one way: an example reads the rules layer
    and is checked by it, and the rules layer has never heard of the examples. If
    that ever reversed, a rule could be quietly written to suit this one map. The
    checker is the one the other import-boundary test uses, pointed at a
    different package.
    """
    offenders = find_forbidden_imports(DOMAIN_ROOT, DOMAIN_PACKAGE, ("katalyst.fixtures",))

    assert not offenders, "\n".join(one.describe() for one in offenders)


def test_the_hormuz_map_breaks_no_rule() -> None:
    """The example passes every check, and says which one it failed if it ever stops."""
    violations = validate(HORMUZ)

    assert violations == [], "\n".join(f"{one.code}: {one.message}" for one in violations)


def test_an_invalid_example_refuses_to_load_at_all() -> None:
    """The guard that runs when the example loads actually refuses a broken map.

    A test that only ever sees the good case would pass whether or not the guard
    worked, so this hands it a map with an arrow pointing at a claim that is not
    there and checks that loading is refused with the fault named.
    """
    dangling = HORMUZ.links[0].model_copy(update={"id": "H->NOWHERE", "target": "NOWHERE"})
    broken = HORMUZ.model_copy(update={"links": (*HORMUZ.links, dangling)})

    with pytest.raises(ValueError, match="not a valid map") as refusal:
        _checked(broken)

    assert "not on this map" in str(refusal.value)


def test_the_map_has_one_starting_claim_and_both_kinds_of_ending() -> None:
    """One hypothesis, at least one tradeable ending, at least one that says why it is not."""
    kinds = [proposition.kind for proposition in HORMUZ.propositions]

    assert kinds.count("hypothesis") == 1
    assert HORMUZ.hypothesis_id == "H"
    assert kinds.count("market") >= 1
    assert kinds.count("not_tradeable") >= 1


def test_every_tradeable_ending_names_something_to_trade() -> None:
    """A market ending names a contract to take a side of, or an instrument to move on."""
    tradeable = [one for one in HORMUZ.propositions if one.kind == "market"]

    assert tradeable
    for proposition in tradeable:
        payoff = proposition.payoff
        assert payoff is not None
        if isinstance(payoff, ContractPayoff):
            assert payoff.venue.strip()
            assert payoff.contract_id.strip()
            assert payoff.title.strip()
        else:
            assert payoff.instrument.strip()
            assert payoff.move > 0


def test_the_two_endings_use_the_two_payoff_shapes() -> None:
    """M1 names a contract somebody sells; M2 names an instrument that moves. Both shapes.

    They are genuinely different endings, which is why there are two shapes
    rather than one with fields that mean different things in each case. Neither
    one names a price: what a contract costs is a live quote, and the map is not
    where a live quote lives.
    """
    contract = next(one for one in HORMUZ.propositions if one.id == "M1").payoff
    price = next(one for one in HORMUZ.propositions if one.id == "M2").payoff

    assert isinstance(contract, ContractPayoff)
    assert contract.kind == "contract"
    assert contract.venue == "Polymarket"
    assert contract.side == "yes"

    assert isinstance(price, PricePayoff)
    assert price.kind == "price"
    assert price.direction == "short"
    # A fraction of the instrument's own price: three per cent, read straight
    # off the claim, not a return on a position whose entry nobody wrote down.
    assert price.move == pytest.approx(0.03)


def test_the_ending_that_cannot_be_traded_says_why() -> None:
    """The not-tradeable ending gives a reason a reader can weigh, not a blank."""
    untradeable = [one for one in HORMUZ.propositions if one.kind == "not_tradeable"]

    assert untradeable
    for proposition in untradeable:
        assert proposition.not_tradeable_reason is not None
        assert len(proposition.not_tradeable_reason.split()) >= 5


def test_the_map_has_a_feedback_arrow_and_it_takes_time() -> None:
    """At least one arrow is a market feeding back on the world, and it has a delay.

    The delay is what makes the loop honest: a price outcome cannot change the
    world it is measuring in zero time.
    """
    feedback = [link for link in every_link() if link.reflexive]

    assert feedback
    for link in feedback:
        assert link.lag > 0


def test_no_arrow_claims_evidence_it_does_not_cite() -> None:
    """Every arrow is either honest about being the model talking, or cites a source.

    The example had no retrieval step behind it, so its arrows say `argued` or
    `asserted`. One carries a source a person attached by hand, which is allowed
    and does not change the receipt.
    """
    for link in every_link():
        assert link.provenance in CLAIMS_NO_EVIDENCE or link.sources, (
            f"the arrow {link.id} is marked {link.provenance} and cites nothing"
        )


def test_every_likelihood_is_a_range_and_never_a_point() -> None:
    """No number in the example pretends to a precision nobody has.

    A belief whose low and high are the same number is a point estimate wearing a
    range's clothes, which is the dishonesty this shape exists to prevent.
    """
    for claim_id, belief in every_belief():
        assert belief.lo < belief.hi, f"the {belief.owner} number on {claim_id} is a point"
        assert belief.lo <= belief.p <= belief.hi


def test_the_starting_claim_carries_the_users_own_number() -> None:
    """The hypothesis holds a user belief, which is where one comes from on the input screen."""
    hypothesis = next(one for one in HORMUZ.propositions if one.id == "H")

    assert hypothesis.beliefs.user is not None
    assert hypothesis.beliefs.user.owner == "user"
    # The whole point of keeping the slots apart: these two are allowed to
    # disagree, and the gap between them is the argument the user is having.
    assert hypothesis.beliefs.user.p != hypothesis.beliefs.model.p


def test_the_quoted_contract_carries_a_market_number() -> None:
    """The Polymarket terminal holds a market belief beside the model's, unmerged."""
    contract = next(one for one in HORMUZ.propositions if one.id == "M1")

    assert contract.beliefs.market is not None
    assert contract.beliefs.market.owner == "market"
    assert contract.beliefs.model.owner == "model"
    assert contract.beliefs.market.p != contract.beliefs.model.p


def test_the_starting_claim_is_anchored_on_a_reference_class() -> None:
    """The hypothesis says how often this kind of thing has happened before: 7 of 9."""
    hypothesis = next(one for one in HORMUZ.propositions if one.id == "H")

    assert hypothesis.base_rate is not None
    assert (hypothesis.base_rate.k, hypothesis.base_rate.n) == (7, 9)
    # Nothing has checked that count, and the empty source list is how the
    # example says so rather than implying a document that does not exist.
    assert hypothesis.base_rate.sources == ()
    assert len(hypothesis.evidence) >= 2
    assert {item.direction for item in hypothesis.evidence} == {1, -1}


def test_the_map_carries_a_tail() -> None:
    """At least one claim is unlikely and, if it happened, would turn the answer over.

    The tail strip needs something to draw before any branch exists, so the tail
    is in the base map rather than only on the branch.
    """
    unlikely = [one for one in HORMUZ.propositions if one.prior.p <= 0.20]

    assert unlikely, "no claim in the base map is unlikely enough to be a tail"
    heavy = [
        link
        for link in HORMUZ.links
        if link.source in {one.id for one in unlikely} and abs(link.strength) >= 1.0
    ]
    assert heavy, "the unlikely claims push on nothing hard enough to matter"


def test_the_example_exercises_every_shape_the_model_layer_defines() -> None:
    """Every kind, mode, signal shape and belief owner appears somewhere in the example.

    This is what makes the example worth having: a later stack that handles only
    the shapes it happened to see here would pass its tests and fail on a real
    map. If a new value is added to one of these lists, this test fails until the
    example covers it.
    """
    inserted = [
        edit.proposition for edit in HORMUZ_THEN_STRIKE.interventions if isinstance(edit, Insert)
    ]
    propositions = [*HORMUZ.propositions, *inserted]

    assert {one.kind for one in propositions} == {
        "hypothesis",
        "event",
        "market",
        "not_tradeable",
    }
    assert {link.mode for link in every_link()} == {"trigger", "sustain"}
    assert {link.shape for link in every_link()} == {"impulse", "step", "ramp"}
    assert {owner for _, belief in every_belief() for owner in [belief.owner]} == {
        "model",
        "user",
        "market",
    }
    assert any(link.half_life is not None for link in every_link())
    assert any(link.strength < 0 for link in every_link())
    assert any(link.sources for link in every_link())
    assert {one.payoff.kind for one in propositions if one.payoff is not None} == {
        "contract",
        "price",
    }


def test_every_arrow_is_named_after_its_two_ends() -> None:
    """An arrow's identifier is its cause and its effect joined by an arrow drawn in text.

    The convention is settled in the example itself, and the spec's worked
    branch already writes identifiers this way, so a test keeps the two agreeing.
    """
    for link in every_link():
        assert link.id == f"{link.source}->{link.target}"


def test_every_resolve_by_date_falls_after_the_day_the_example_is_set_on() -> None:
    """Dates in the example are spans from one fixed day, so the example never goes stale."""
    inserted = [
        edit.proposition for edit in HORMUZ_THEN_STRIKE.interventions if isinstance(edit, Insert)
    ]
    for proposition in [*HORMUZ.propositions, *inserted]:
        assert proposition.resolution.by > FIXTURE_DATE
        assert proposition.resolution.criteria.strip()
        assert proposition.resolution.source.strip()


def test_the_strike_branch_is_three_edits_in_the_order_that_makes_it_work() -> None:
    """Suppose the strait opens, add the strike, then suppose the strike lands.

    The order is load-bearing. Supposing a claim cuts the arrows that exist at
    that moment, so the arrow from the strike back onto the strait has to be
    added *after* the strait was supposed open — otherwise it would be cut and
    the showcase would not happen.
    """
    edits = HORMUZ_THEN_STRIKE.interventions

    assert [edit.kind for edit in edits] == ["do", "insert", "do"]
    assert edits[0].target == "H"
    assert edits[0].value is True
    assert edits[0].at == FIXTURE_DATE
    assert edits[1].proposition.id == "S"
    assert edits[2].target == "S"
    assert edits[2].at is not None
    assert (edits[2].at - FIXTURE_DATE).days == 1
    assert HORMUZ_THEN_STRIKE.parent is None
    assert HORMUZ_THEN_STRIKE.label.strip()


def test_the_showcase_is_a_sustain_arrow_pulling_against_a_trigger_that_already_fired() -> None:
    """S → H is a sustain and H → B is a trigger. Both, together, are the whole idea.

    The strike withdraws what was holding the strait open, so the openness
    retracts even though the user asserted it — a sustain arrow, the apple and
    the desk. The push into the oil price already fired and does not un-fire — a
    trigger arrow, the toppled domino. If either of these two ever flips, the
    example stops demonstrating the thing it exists to demonstrate.
    """
    strike_to_hormuz = next(link for link in inserted_links() if link.id == "S->H")
    hormuz_to_brent = next(link for link in HORMUZ.links if link.id == "H->B")

    assert strike_to_hormuz.mode == "sustain"
    assert strike_to_hormuz.strength < 0
    assert hormuz_to_brent.mode == "trigger"
    assert hormuz_to_brent.strength > 0
    # A trigger that fades needs to say how fast it fades, or there is nothing
    # left for it to keep doing after its cause is retracted.
    assert hormuz_to_brent.shape == "impulse"
    assert hormuz_to_brent.half_life is not None


def test_the_signs_on_the_map_read_the_way_the_claims_are_written() -> None:
    """A strength's sign says which way the arrow pushes the claim at its head toward true.

    The two that are easiest to get backwards, pinned: an open strait makes
    "Brent settles below $68" *more* likely, so that arrow is positive even
    though the price is falling; announced restraint makes the same claim *less*
    likely, so that one is negative.
    """
    by_id = {link.id: link for link in every_link()}

    assert by_id["H->B"].strength == pytest.approx(1.6)
    assert by_id["H->C"].strength == pytest.approx(1.1)
    assert by_id["C->B"].strength == pytest.approx(0.7)
    assert by_id["R->B"].strength == pytest.approx(-1.2)
    assert by_id["S->B"].strength == pytest.approx(-2.4)
    assert by_id["S->C"].strength == pytest.approx(-2.0)
    assert by_id["S->H"].strength == pytest.approx(-1.9)


def test_the_branch_lands_on_a_map_that_is_still_valid() -> None:
    """Adding the strike and its three arrows leaves a map that breaks no rule.

    The fold is done by hand here because nothing folds a branch onto a map yet —
    that arrives with the propagation stack. What this checks is the part that
    does not depend on how the fold is written: the claim and the arrows the
    branch carries are well-formed against this map, and none of them closes a
    loop.
    """
    edit = HORMUZ_THEN_STRIKE.interventions[1]
    assert isinstance(edit, Insert)

    folded = Graph(
        id="hormuz-with-the-strike",
        propositions=(*HORMUZ.propositions, edit.proposition),
        links=(*HORMUZ.links, *edit.links),
        hypothesis_id=HORMUZ.hypothesis_id,
    )

    assert validate(folded) == []


def test_the_whole_example_survives_a_round_trip_through_json() -> None:
    """Written out as JSON and read back, the map and the branch are unchanged.

    This is the trip the example makes on its way to the browser, so anything it
    loses on the way — a tuple becoming a list, a date becoming a string that
    does not parse back — would be a bug the canvas would find first.
    """
    written = HORMUZ.model_dump_json()
    assert Graph.model_validate_json(written) == HORMUZ
    assert Graph.model_validate(json.loads(written)) == HORMUZ

    written_branch = HORMUZ_THEN_STRIKE.model_dump_json()
    assert Branch.model_validate_json(written_branch) == HORMUZ_THEN_STRIKE


def test_the_example_is_listed_and_can_be_found_by_name() -> None:
    """The catalogue offers the example under the name the routes ask for it by."""
    assert [one.id for one in EXAMPLES] == ["hormuz"]

    found = find("hormuz")
    assert found is not None
    assert found.graph is HORMUZ
    assert found.branches == (HORMUZ_THEN_STRIKE,)
    assert found.fixture_date == FIXTURE_DATE
    assert found.title.strip()
    assert found.one_line.strip()

    assert find("not-an-example") is None
