"""A live run says what it is doing while it waits, and the waiting is the point.

**This is the suite's first meeting with a live wait.** Every other test here
answers instantly, which is exactly why nobody saw what Kent saw: he pressed
*Watch it build*, the first model call took minutes, and the screen had no way to
say anything at all. So the answerer below says what it is doing and then
**stops**, on a latch the test opens when it has seen enough — never on a sleep,
because a test that waits is a test nobody runs.

What is proved here: something reaches the reader before the first proposal does
and well inside five seconds; the newest line of each call wins and at most about
one a second leaves it; a line names the claim its call is working on; and none
of it reaches the transcript, the bill or a replay.

No key, no network, no money: the seam is handed a script.
"""

import json
import threading
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from katalyst.api import generate
from katalyst.api.generate import ASKING_ABOUT, AT_MOST_ONE_A_SECOND, WhatTheCallsAreDoing
from katalyst.api.main import app
from katalyst.domain import Graph
from katalyst.engine import prompt, replay
from katalyst.engine.client import WhatItIsDoing
from katalyst.engine.events import ProposalAccepted
from katalyst.engine.outcome import Said
from katalyst.engine.transcript import held
from katalyst.settings import get_settings
from tests.unit.engine.a_recording import a_claim, written_to
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Storyteller,
    a_starting_claim,
    a_stop,
    an_answer,
)
from tests.unit.engine.answers import a_claim as an_answered_claim

STARTED_AT = "Something a person expects."
A_STEP = "A step in the middle of the story."
AN_ENDING = "Something you could put money on."
SMALL: dict[str, int] = {"versions": 16, "worlds": 4}

A_QUERY = "Lloyd's JWC Hormuz premium 2026"
"""The model's own search, verbatim. Nothing rewrites it on the way out."""

ANOTHER_QUERY = "war risk premium Gulf transits November 2026"
A_THOUGHT = "The premium has to fall before the shipping rate does."

LONG_ENOUGH_TO_SEE_SOMETHING = 5.0
"""How long a reader may be shown nothing at all before this test fails.

Kent's ask, in his words: *"there should only be a few seconds between things
happening for real on the UI if possible."* Five is a ceiling with room in it, not
a target: the pace below sends the first line of a call the moment it exists.
"""

BEFORE_WE_GIVE_UP = 30.0
"""How long the stand-in waits to be let go before it answers anyway.

A latch that is never opened would hang a suite, so it opens itself. Nothing in a
passing run ever reaches this.
"""


def a_story() -> Storyteller:
    """One short generation, told to the seam instead of asked of a model."""
    return Storyteller(
        {
            STARTED_AT: [
                an_answer(an_answered_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(an_answered_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
        },
        starting=[an_answer(a_starting_claim(STARTED_AT))],
    )


class SaysWhatItIsDoingThenWaits:
    """A stand-in that says three things at once and then stops until it is let go.

    It is the shape of the wait Kent met: everything interesting about a call
    happens in its first second, and then nothing happens for minutes. The
    `Storyteller` underneath answers exactly as it does everywhere else, so the
    map this builds is the map every other test builds.
    """

    def __init__(
        self,
        telling: Storyteller,
        on_activity: Any,
        said_them: threading.Event,
        let_go: threading.Event,
    ) -> None:
        """Set out what it says, where it says it, and what it waits on.

        Args:
            telling: The story to answer with, once it is let go.
            on_activity: Where to say what it is doing.
            said_them: Opened by this, the moment all three lines are out.
            let_go: Opened by the test, to let the answer come back.
        """
        self._telling = telling
        self._say = on_activity
        self._said_them = said_them
        self._let_go = let_go
        self.effort_used = telling.effort_used

    def watching(self, spent: Any, cap: float) -> None:
        """Take note of the purse, exactly as the story does."""
        self._telling.watching(spent, cap)

    def starting_claim(self, question: str, *, may_search: bool = True) -> Said:
        """Say what this call is doing, wait to be let go, then answer."""
        for kind, text in (
            ("searching", A_QUERY),
            ("searching", ANOTHER_QUERY),
            ("thinking", A_THOUGHT),
        ):
            self._say(WhatItIsDoing(kind=kind, text=text, question=question))
        self._said_them.set()
        self._let_go.wait(timeout=BEFORE_WE_GIVE_UP)
        return self._telling.starting_claim(question, may_search=may_search)

    def proposal(self, question: str, *, may_search: bool) -> Said:
        """Answer the ordinary way. The wait this test is about is the first call's."""
        return self._telling.proposal(question, may_search=may_search)


@pytest.fixture(autouse=True)
def a_copy_with_recordings_and_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Run every test against a program with recordings on disk and nothing configured."""
    folder = tmp_path / "recordings"
    written_to(folder)
    monkeypatch.setattr(replay, "RECORDINGS", folder)
    monkeypatch.setenv("KATALYST_REPLAY_PACE", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    held.forget_everything()
    yield
    get_settings.cache_clear()
    held.forget_everything()


# --- Through the real route, against a call that goes quiet ------------------


def test_something_reaches_the_reader_inside_five_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The test that would have caught what Kent saw.

    The first model call says what it is doing and then **goes quiet**, and it
    is let go again only when a line of what it said has been written out to the
    reader. So the run finishes quickly if and only if something reached the
    reader while the call was still waiting: take the writing out away and this
    test sits on the stand-in's own give-up timer and fails on the clock.

    **What the test client can and cannot see**, the same limit
    `test_the_stream_is_not_buffered.py` writes down: it collects a response
    before handing it back, so every line reads as having arrived at one instant
    however the server behaved. What is visible is the **order** the server wrote
    them in and the **clock** the whole request ran against, and between them
    they say the thing that matters: a line about the call went out before the
    call's answer did.
    """
    said_them, let_go = threading.Event(), threading.Event()
    _let_go_when_something_is_written_out(monkeypatch, let_go)
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **how: SaysWhatItIsDoingThenWaits(a_story(), how["on_activity"], said_them, let_go),
    )

    started = time.monotonic()
    seen = _whole_live_run()
    took = time.monotonic() - started

    heard = [payload for name, payload in seen if name == "activity"]
    assert heard, "a live call went quiet and the reader was told nothing"
    assert took < LONG_ENOUGH_TO_SEE_SOMETHING, (
        f"the run took {took:.1f}s, which is the stand-in giving up rather than "
        "anything being said: nothing about the call reached the reader while it waited"
    )
    assert said_them.is_set()

    # Before the proposal, which is the whole point: the wait is what is being
    # reported on, so a line that arrived with the answer would report nothing.
    names = [name for name, _ in seen]
    assert names.index("activity") < names.index("proposal_accepted")
    assert names[0] == "generation_started"
    assert names[-2:] == ["receipt", "done"]

    # The model's own words, not ours. Each of the three is verbatim or absent.
    assert heard[0]["text"] in (A_QUERY, ANOTHER_QUERY, A_THOUGHT)
    assert heard[0]["kind"] in ("searching", "thinking")


def _let_go_when_something_is_written_out(
    monkeypatch: pytest.MonkeyPatch, let_go: threading.Event
) -> None:
    """Open the latch the moment a line of activity is handed to the wire.

    This is what makes the clock above mean something. The stand-in is released
    by the product doing its job, so a build where nothing is written out never
    releases it and the test fails on time rather than on a guess.

    Args:
        monkeypatch: pytest's own patcher.
        let_go: The latch the stand-in is waiting on.
    """
    writing_out = WhatTheCallsAreDoing.whatever_is_new

    def watched(self: WhatTheCallsAreDoing, now: float) -> Any:
        said = writing_out(self, now)
        if said:
            let_go.set()
        return said

    monkeypatch.setattr(WhatTheCallsAreDoing, "whatever_is_new", watched)


def test_nothing_is_said_after_the_run_starts_paying_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activity sits between the first event and the ending, and nowhere else.

    The ending is the likelihoods, the verdict, the receipt and why it stopped. A
    line saying a call is searching, arriving after the bill, would be about work
    that has already been paid for.
    """
    said_them, let_go = threading.Event(), threading.Event()
    let_go.set()
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **how: SaysWhatItIsDoingThenWaits(a_story(), how["on_activity"], said_them, let_go),
    )

    names = [name for name, _ in _whole_live_run()]

    ending = min(
        names.index(one) for one in ("beliefs_propagated", "receipt", "done") if one in names
    )
    assert "activity" not in names[ending:]


def test_an_activity_line_never_reaches_the_transcript_or_the_bill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never written down, never billed, never counted by `at`."""
    said_them, let_go = threading.Event(), threading.Event()
    let_go.set()
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **how: SaysWhatItIsDoingThenWaits(a_story(), how["on_activity"], said_them, let_go),
    )

    read = _whole_live_run()

    generation = next(payload for name, payload in read if name == "generation_started")
    working = TestClient(app).get(f"/api/generate/{generation['generation_id']}/transcript")
    assert working.status_code == 200
    lines = working.json()["lines"]
    assert lines
    # Three kinds of line, and none of them is a thing a call was doing.
    assert all(one["what"] in ("accepted", "refused", "stopped") for one in lines)
    assert not [one for one in lines if A_QUERY in json.dumps(one)]

    # The transcript counter counts proposals, and activity is not one.
    counted = [payload["at"] for name, payload in read if name.startswith("proposal_")]
    assert counted == list(range(len(counted)))

    # And the bill is the calls, which activity is no part of.
    receipt = next(payload for name, payload in read if name == "receipt")
    assert receipt["calls"] == len(lines)


def test_a_replay_says_nothing_about_what_it_is_doing() -> None:
    """A replay is not working: it is showing. There is nothing of activity to show."""
    from tests.unit.engine.a_recording import THE_SENTENCE

    with TestClient(app).stream(
        "POST", "/api/generate", json={"hypothesis": THE_SENTENCE, **SMALL}
    ) as answer:
        names = [name for name, _ in _read(answer)]

    assert names
    assert "activity" not in names


# --- The pace, with no clock of anybody's but this test's --------------------


def test_the_newest_line_of_a_call_wins_and_at_most_one_a_second_leaves_it() -> None:
    """Three things said in one second leave as one: the newest. Nothing queues."""
    doing = WhatTheCallsAreDoing()
    for kind, text in (("searching", A_QUERY), ("searching", ANOTHER_QUERY)):
        doing.put(WhatItIsDoing(kind=kind, text=text, question="one call"))

    at_once = doing.whatever_is_new(100.0)
    doing.put(WhatItIsDoing(kind="thinking", text=A_THOUGHT, question="one call"))
    too_soon = doing.whatever_is_new(100.0 + AT_MOST_ONE_A_SECOND / 2)
    later = doing.whatever_is_new(100.0 + AT_MOST_ONE_A_SECOND)

    assert [one.text for one in at_once] == [ANOTHER_QUERY]
    assert too_soon == []
    assert [one.text for one in later] == [A_THOUGHT]


def test_two_calls_at_once_are_paced_apart_from_each_other() -> None:
    """Three questions go out together, and one of them talking must not silence the rest."""
    doing = WhatTheCallsAreDoing()
    doing.put(WhatItIsDoing(kind="searching", text=A_QUERY, question="first call"))
    doing.put(WhatItIsDoing(kind="searching", text=ANOTHER_QUERY, question="second call"))

    out = doing.whatever_is_new(100.0)

    assert sorted(one.text for one in out) == sorted([A_QUERY, ANOTHER_QUERY])


def test_nothing_is_said_once_the_run_has_started_ending() -> None:
    """The channel closes on the first event of the ending, and stays closed."""
    doing = WhatTheCallsAreDoing()
    doing.note(_a_receipt())
    doing.put(WhatItIsDoing(kind="searching", text=A_QUERY, question="one call"))

    assert doing.whatever_is_new(100.0) == []


# --- Which claim a call is working on ---------------------------------------


def test_a_line_names_the_claim_its_call_is_working_on() -> None:
    """`about` is one of the identifiers the latest frontier names, or nothing at all."""
    claim = a_claim("C", "War-risk cover for Gulf transits gets cheap again.")
    doing = WhatTheCallsAreDoing()
    doing.note(ProposalAccepted(at=0, proposition=claim, frontier=("C",)))
    doing.put(
        WhatItIsDoing(
            kind="searching", text=A_QUERY, question=f"{ASKING_ABOUT}{claim.claim}\nand so on"
        )
    )

    said = doing.whatever_is_new(100.0)

    assert [one.about for one in said] == ["C"]


def test_a_call_that_is_not_about_one_claim_says_so_with_nothing() -> None:
    """The opening call turns a person's sentence into a claim. It expands nothing."""
    doing = WhatTheCallsAreDoing()
    doing.put(WhatItIsDoing(kind="thinking", text=A_THOUGHT, question="What did this person mean?"))

    assert [one.about for one in doing.whatever_is_new(100.0)] == [None]


def test_the_line_the_question_names_the_claim_with_is_still_there() -> None:
    """The route reads a prompt it does not own, so the reading is pinned here.

    `api/generate.py` finds the claim a call is about by the one line
    `engine/prompt.py` writes before it. Nothing else in a request names it. The
    day that wording changes this test fails, which is the whole reason it
    exists — the alternative is every activity line quietly losing its claim.
    """
    claim = a_claim("C", "War-risk cover for Gulf transits gets cheap again.")
    graph = Graph(id="a-map", propositions=(claim,), links=(), hypothesis_id="C")
    question = prompt.expanding_question(
        graph, "C", target=None, ending_only=False, today=date(2026, 9, 22)
    )

    doing = WhatTheCallsAreDoing()
    doing.note(ProposalAccepted(at=0, proposition=claim, frontier=("C",)))
    doing.put(WhatItIsDoing(kind="searching", text=A_QUERY, question=question))

    assert [one.about for one in doing.whatever_is_new(100.0)] == ["C"]


# --- Reading the wire --------------------------------------------------------


def _the_stream() -> Any:
    """Open a live generation and hand back the answer to read as it arrives."""
    return TestClient(app).stream(
        "POST",
        "/api/generate",
        json={"hypothesis": STARTED_AT, "start": "live", **SMALL},
    )


def _whole_live_run() -> list[tuple[str, dict[str, Any]]]:
    """Read a whole live generation off the wire."""
    with _the_stream() as answer:
        return list(_read(answer))


def _read(answer: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """Read the two lines of each event the way a browser does."""
    name: str | None = None
    for line in answer.iter_lines():
        if line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            assert name is not None
            yield name, json.loads(line.removeprefix("data: "))
            name = None


def _a_receipt() -> Any:
    """One receipt event, which is the ending this test cares about."""
    from katalyst.engine.events import Receipt

    return Receipt(
        model="claude-sonnet-5",
        calls=1,
        input_tokens=1,
        output_tokens=1,
        cache_read_tokens=0,
        searches=0,
        dollars=0.0,
        seconds=0.0,
        mode="live",
        prompt_hash="whatever",
    )
