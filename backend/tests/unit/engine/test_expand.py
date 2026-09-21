"""One call, one proposal, and the three things that can happen to it.

Every test here hands the pipeline an answer written out by hand, in the
library's own types, and checks what our own code did with it. No key, no
network, no money.
"""

import pytest
from pydantic import TypeAdapter, ValidationError

from katalyst.domain import validate
from katalyst.engine.client import AnswerWeCouldNotRead, _did_not_fit_the_shape
from katalyst.engine.expand import expand
from katalyst.engine.outcome import Accepted, Refused, Stopped
from katalyst.engine.proposal import Proposal
from katalyst.fixtures import HORMUZ
from tests.unit.engine.answers import (
    THE_DAY_THE_RUN_HAPPENED,
    Scripted,
    a_claim,
    a_declined_answer,
    a_link,
    a_stop,
    an_answer,
)


def ask(answerer: Scripted, frontier: str = "C", **rest: object) -> object:
    """Put one question about the stored example's map."""
    return expand(
        HORMUZ,
        frontier,
        target=None,
        answerer=answerer,  # type: ignore[arg-type]
        on=THE_DAY_THE_RUN_HAPPENED,
        **rest,  # type: ignore[arg-type]
    )


def test_an_accepted_claim_is_minted_by_us_and_never_by_the_model() -> None:
    """The identifiers and the name on the number are ours; the numbers are the model's."""
    proposed = a_claim("Something the strait opening causes.", cause="C")
    outcome = ask(Scripted([an_answer(proposed)]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    claim = accepted.proposition
    assert claim is not None
    assert claim.claim == proposed.claim
    assert claim.id not in {one.id for one in HORMUZ.propositions}
    assert claim.prior.owner == "model"
    assert (claim.prior.p, claim.prior.lo, claim.prior.hi) == (
        proposed.prior.p,
        proposed.prior.lo,
        proposed.prior.hi,
    )
    assert len(accepted.links) == 1
    assert accepted.links[0].source == "C"
    assert accepted.links[0].target == claim.id


def test_the_map_the_question_was_asked_about_is_never_changed() -> None:
    """A proposal is a candidate map that wins or loses. The map a person sees is untouched."""
    before = HORMUZ.model_dump_json()
    ask(Scripted([an_answer(a_claim("Anything at all.", cause="C"))]))
    ask(Scripted([an_answer(a_link("B", "H"))]))
    assert HORMUZ.model_dump_json() == before


def test_a_proposal_that_would_close_a_loop_is_refused_with_the_rules_own_sentence() -> None:
    """The rule is the map's, and so are the words a person reads."""
    outcome = ask(Scripted([an_answer(a_link("B", "H"))]), frontier="B")

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert [one.code for one in refused.violations] == ["cycle"]
    assert "loop" in refused.violations[0].message


def test_a_claim_with_a_blank_test_is_refused() -> None:
    """A claim nobody can settle is not a claim, and the map's own rules say so."""
    outcome = ask(Scripted([an_answer(a_claim("A mood, not a claim.", cause="C", criteria="  "))]))

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert [one.code for one in refused.violations] == ["missing_resolution"]


def test_every_reason_comes_back_at_once_and_never_the_first() -> None:
    """A proposal with two faults comes back with two, so a person fixes both."""
    nothing_to_trade = a_claim(
        "A tradeable ending with nothing to trade.",
        cause="C",
        kind="market",
        criteria=" ",
        names_a_trade=False,
    )
    outcome = ask(Scripted([an_answer(nothing_to_trade)]))

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert set(one.code for one in refused.violations) == {
        "missing_resolution",
        "market_without_payoff",
    }


def test_a_fault_the_map_already_had_is_not_blamed_on_the_proposal() -> None:
    """Only what the proposal introduced counts, or every proposal would be refused."""
    half_built = HORMUZ.model_copy(
        update={
            "propositions": tuple(
                one for one in HORMUZ.propositions if one.kind not in ("market", "not_tradeable")
            ),
            "links": (),
        }
    )
    assert any(one.code == "no_terminal" for one in validate(half_built))

    outcome = expand(
        half_built,
        "C",
        target=None,
        answerer=Scripted([an_answer(a_claim("A step in the middle.", cause="C"))]),  # type: ignore[arg-type]
        on=THE_DAY_THE_RUN_HAPPENED,
    )
    assert isinstance(outcome.result, Accepted)


def test_a_proposal_naming_a_claim_that_is_not_on_the_map_is_refused() -> None:
    """Pointing at a name we never handed out needs no check of its own."""
    outcome = ask(Scripted([an_answer(a_claim("Caused by nothing here.", cause="not-a-claim"))]))

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert [one.code for one in refused.violations] == ["dangling_link"]


def test_a_stop_is_not_a_failure() -> None:
    """A line that is finished says so, and the sentence is kept."""
    outcome = ask(Scripted([an_answer(a_stop("Nothing honest follows from this."))]))

    stopped = outcome.result  # type: ignore[union-attr]
    assert isinstance(stopped, Stopped)
    assert stopped.why == "Nothing honest follows from this."


def test_expand_surfaces_a_refusal_as_a_rejected_proposal() -> None:
    """The vendor's own safety check declining a call is shown, never hidden."""
    outcome = ask(Scripted([a_declined_answer("It looked like something I should not help with.")]))

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert refused.violations == ()
    assert "declined" in refused.claim_in_words
    assert "It looked like something I should not help with." in refused.claim_in_words
    assert outcome.input_tokens > 0  # type: ignore[union-attr]


def test_expand_reports_a_malformed_answer_and_does_not_crash() -> None:
    """An answer that did not fit the shape is one more refusal, with a plain sentence.

    The seam turns the library's own complaint into one of ours on the way out,
    so nothing past it has to know whose complaint it was.
    """
    with pytest.raises(ValidationError) as caught:
        TypeAdapter(Proposal).validate_json('{"kind": "claim"}')
    did_not_fit = AnswerWeCouldNotRead(_did_not_fit_the_shape(caught.value))

    outcome = ask(Scripted(raises=did_not_fit))

    refused = outcome.result  # type: ignore[union-attr]
    assert isinstance(refused, Refused)
    assert refused.violations == ()
    assert refused.claim_in_words.startswith("The model's answer did not fit the shape")
    assert outcome.calls == 1  # type: ignore[union-attr]


def test_a_refused_claim_is_asked_again_without_being_told_why() -> None:
    """The second question is the first question, byte for byte, and names no fault."""
    answerer = Scripted([an_answer(a_link("B", "H"))])

    first = ask(answerer, frontier="B")
    second = ask(answerer, frontier="B")

    assert isinstance(first.result, Refused)  # type: ignore[union-attr]
    assert isinstance(second.result, Refused)  # type: ignore[union-attr]
    assert answerer.asked[0] == answerer.asked[1]
    for said in answerer.asked:
        for violation in first.result.violations:  # type: ignore[union-attr]
            assert violation.code not in said
            assert violation.message not in said
        assert "loop" not in said


def test_the_last_call_asks_only_for_an_ending() -> None:
    """The one call a run makes when it has run out of room says so, and only then."""
    answerer = Scripted([an_answer(a_stop())])
    ask(answerer)
    ask(answerer, ending_only=True)

    ordinary, last = answerer.asked
    assert "answer only with an ending" not in ordinary
    assert "answer only with an ending" in last
