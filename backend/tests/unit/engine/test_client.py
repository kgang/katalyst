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
from katalyst.engine.prompt import STANDING_TEXT
from katalyst.engine.receipt import nothing_spent_yet
from katalyst.settings import get_settings
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
    assert first["model"] == second["model"] == get_settings().KATALYST_MODEL


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


def test_the_first_claim_of_a_map_may_research_like_any_other() -> None:
    """It was the one claim nobody could look anything up for, and it showed.

    The question is partly what the person meant, which the web cannot answer,
    and partly how often this kind of thing has happened before, which is exactly
    what the web is for. A run that could not search here produced a first claim
    with a two-character test and no reference class (2026-09-17).
    """
    wire = Wire([an_answer(a_starting_claim())])
    Model(wire).starting_claim("what did they mean")  # type: ignore[arg-type]

    assert wire.sent[0]["tool_choice"] == MAY_SEARCH
    assert wire.sent[0]["tools"] == [SEARCH_TOOL]


def test_a_run_with_no_searches_left_forbids_them_on_the_first_claim_too() -> None:
    """One budget, and the first claim spends from it like any other."""
    wire = Wire([an_answer(a_starting_claim())])
    Model(wire).starting_claim("what did they mean", may_search=False)  # type: ignore[arg-type]

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


def test_a_question_stops_between_its_own_rounds_when_the_money_runs_out() -> None:
    """Kent, 2026-09-20: twenty-five searches over five rounds can cost a dollar.

    A ceiling checked only between calls is a ceiling the dearest thing in the
    program steps over. The walk says what is left in the purse; this stops.
    """
    paused = an_answer(a_claim("Half.", cause="C"), stopped="pause_turn", written=1_000_000)
    asking = Model(Wire([paused, paused, paused]))  # type: ignore[arg-type]
    asking.watching(nothing_spent_yet("claude-sonnet-5"), 5.0)

    said = asking.proposal("q", may_search=True)

    # One round of a million written tokens is $10 on Sonnet 5, so the second
    # never goes out, and what the first one cost is still on the bill.
    assert said.calls == 1
    assert said.output_tokens == 1_000_000


def test_a_question_with_money_left_runs_its_rounds_out() -> None:
    """The same check, from the other side: a cheap round is not interrupted."""
    paused = an_answer(a_claim("Half.", cause="C"), stopped="pause_turn", written=100)
    finished = an_answer(a_claim("Whole.", cause="C"), written=100)
    asking = Model(Wire([paused, finished]))  # type: ignore[arg-type]
    asking.watching(nothing_spent_yet("claude-sonnet-5"), 15.0)

    assert asking.proposal("q", may_search=True).calls == 2


def test_a_question_nobody_told_about_a_purse_is_not_stopped() -> None:
    """A seam built and asked directly — every request test above — spends freely."""
    paused = an_answer(a_claim("Half.", cause="C"), stopped="pause_turn", written=1_000_000)
    finished = an_answer(a_claim("Whole.", cause="C"))

    assert Model(Wire([paused, finished])).proposal("q", may_search=True).calls == 2  # type: ignore[arg-type]


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
