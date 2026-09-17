"""What the seam actually sends, and what it hands back.

The other tests hand the pipeline an answer and check what our code did with it.
These check the other direction: what leaves the machine. Two of this stack's
rules live entirely in the shape of a request and can be checked nowhere else —
that the part the service remembers is byte-identical on every call, and that a
run which has spent its searches **forbids** the tool rather than removing it.

The stand-in below records what it was asked and hands back an answer built in
the library's own types. Decision record 0008 warns that a hand-written stand-in
encodes our assumptions about a library rather than its behaviour; that warning
is about what comes *back*, which the recorded exchanges cover. What goes *out*
is ours, and this is the only way to look at it without spending money.
"""

from typing import Any

import pytest

from katalyst.engine.client import (
    MAY_NOT_SEARCH,
    MAY_SEARCH,
    SEARCH_TOOL,
    AnswerWeCouldNotRead,
    Model,
)
from katalyst.engine.pricing import MODEL
from katalyst.engine.prompt import STANDING_TEXT
from tests.unit.engine.answers import a_claim, a_starting_claim, an_answer


class Wire:
    """Records every request the seam builds, and answers each one."""

    def __init__(self, answers: list[Any] | None = None) -> None:
        """Set out what to answer with, and start with nothing recorded."""
        self.sent: list[dict[str, Any]] = []
        self._answers = answers or []
        self.messages = self

    def parse(self, **request: Any) -> Any:
        """Stand in for the library's own call, and remember what was asked."""
        self.sent.append(request)
        if self._answers:
            return self._answers.pop(0)
        return an_answer(a_claim("Anything at all.", cause="C"))


def test_the_part_the_service_remembers_is_the_same_bytes_on_every_call() -> None:
    """A run whose answers report nothing read back is a bug, not a slow day."""
    wire = Wire()
    model = Model(wire)  # type: ignore[arg-type]

    model.proposal("one question", may_search=True)
    model.proposal("a different question", may_search=False)

    first, second = wire.sent
    assert first["system"] == second["system"]
    assert first["system"][0]["text"] == STANDING_TEXT
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert first["tools"] == second["tools"] == [SEARCH_TOOL]
    assert first["model"] == second["model"] == MODEL


def test_a_run_that_has_spent_its_searches_forbids_the_tool_rather_than_removing_it() -> None:
    """The tools sit at the very front of a request, so removing one costs the whole prefix."""
    wire = Wire()
    model = Model(wire)  # type: ignore[arg-type]

    model.proposal("with searches left", may_search=True)
    model.proposal("with none left", may_search=False)

    with_some, with_none = wire.sent
    assert with_some["tool_choice"] == MAY_SEARCH
    assert with_none["tool_choice"] == MAY_NOT_SEARCH
    assert with_none["tools"] == [SEARCH_TOOL]


def test_the_question_about_what_somebody_meant_never_searches() -> None:
    """The web has nothing to say about what a person meant by their own sentence."""
    wire = Wire([an_answer(a_starting_claim())])
    Model(wire).starting_claim("what did they mean")  # type: ignore[arg-type]

    assert wire.sent[0]["tool_choice"] == MAY_NOT_SEARCH


def test_the_model_thinks_for_itself_and_nothing_pins_how_long() -> None:
    """Adaptive thinking, and no sampling settings: both are what record 0006 chose."""
    wire = Wire()
    Model(wire).proposal("a question", may_search=True)  # type: ignore[arg-type]

    sent = wire.sent[0]
    assert sent["thinking"] == {"type": "adaptive"}
    assert "temperature" not in sent
    assert "top_p" not in sent


def test_a_part_finished_answer_is_sent_straight_back_with_nothing_added() -> None:
    """The service picks up from its own turn; a "carry on" of ours would confuse it."""
    paused = an_answer(a_claim("Half an answer.", cause="C"), stopped="pause_turn")
    finished = an_answer(a_claim("The whole of it.", cause="C"))
    wire = Wire([paused, finished])

    said = Model(wire).proposal("a question", may_search=True)  # type: ignore[arg-type]

    assert said.calls == 2
    carried_on = wire.sent[1]["messages"]
    assert carried_on[0] == wire.sent[0]["messages"][0]
    assert carried_on[-1]["role"] == "assistant"
    assert len(carried_on) == 2


def test_every_round_trip_is_on_the_bill() -> None:
    """A call that cost money and is not counted is money the receipt cannot account for."""
    paused = an_answer(a_claim("Half.", cause="C"), stopped="pause_turn", read_fresh=11, written=7)
    finished = an_answer(a_claim("Whole.", cause="C"), read_fresh=13, written=5)

    said = Model(Wire([paused, finished])).proposal("q", may_search=True)  # type: ignore[arg-type]

    assert said.input_tokens == 11 + 13
    assert said.output_tokens == 7 + 5


def test_what_the_model_wrote_and_what_the_search_returned_arrive_apart() -> None:
    """Two fields, so no code downstream could mistake one for the other."""
    found = "https://example.test/returned"
    answered = a_claim("Backed by one page.", cause="C", cites=(found, "https://example.test/not"))
    wire = Wire([an_answer(answered, found=(found,), searches=1)])

    said = Model(wire).proposal("q", may_search=True)  # type: ignore[arg-type]

    assert [one.url for one in said.found] == [found]
    assert said.answered is not None
    assert said.searches == 1


def test_an_answer_that_did_not_fit_the_shape_crosses_the_seam_as_one_of_ours() -> None:
    """Nothing past this file has to know whose complaint it was."""
    from pydantic import TypeAdapter, ValidationError

    from katalyst.engine.proposal import Proposal

    class Broken(Wire):
        def parse(self, **request: Any) -> Any:
            self.sent.append(request)
            return TypeAdapter(Proposal).validate_json('{"kind": "claim"}')

    with pytest.raises(AnswerWeCouldNotRead) as caught:
        Model(Broken()).proposal("q", may_search=True)  # type: ignore[arg-type]

    assert "did not fit the shape" in caught.value.why
    assert not isinstance(caught.value, ValidationError)
