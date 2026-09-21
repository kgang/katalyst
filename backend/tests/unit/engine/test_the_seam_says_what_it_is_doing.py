"""The seam reads a call out loud as it happens — and only when somebody is listening.

Two halves, and they are tested apart because they fail apart.

**What goes out.** With nowhere to say what it is doing, the seam puts the
question exactly the way it has always put it: not streamed, and thinking left
where it was. That is what keeps every recorded exchange under
`tests/cassettes/` matching, since those are matched on the whole request body.
Given somewhere to say it, the same question is streamed and asks for the
thinking to be summarised — a live-only difference (record 0027, R34's
precedent).

**What comes back.** `what_it_is_doing` is pure, like `what_it_said` beside it,
so the blocks here are the library's own types and go through exactly what a real
call's go through. Decision record 0008's warning about hand-written stand-ins is
answered the same way it is in `answers.py`: what is written by hand is the
*content*, never the shape.

Nothing here talks to a network, and nothing here needs a key.
"""

from types import TracebackType
from typing import Any

import pytest
from anthropic.lib.streaming import ContentBlockStopEvent

# The one event this file needs that the library does not export by name. It is
# the library's own class either way: importing it is how these tests break
# loudly if it ever moves, rather than quietly agreeing with a copy of ours.
from anthropic.lib.streaming._types import ThinkingEvent
from anthropic.types import (
    ServerToolUseBlock,
    ThinkingBlock,
    WebSearchResultBlock,
    WebSearchToolResultBlock,
)

from katalyst.engine.client import (
    AS_MUCH_THINKING_AS_FITS,
    THINKING_OUT_LOUD,
    Model,
    WhatItIsDoing,
    what_it_is_doing,
)
from tests.unit.engine.answers import a_claim, an_answer

A_QUERY = "Lloyd's JWC Hormuz premium 2026"
A_TITLE = "Joint War Committee reviews Gulf listed areas"
A_PAGE = "https://www.lloyds.com/market/war-committee/2026-review"


# --- Two ways of putting one question ----------------------------------------


class Wire:
    """Stands in for the library, both ways round, and remembers what was asked."""

    def __init__(self, happenings: list[Any] | None = None) -> None:
        """Set out what a streamed call hands over, piece by piece."""
        self.parsed: list[dict[str, Any]] = []
        self.streamed: list[dict[str, Any]] = []
        self._happenings = happenings or []
        self.messages = self

    def parse(self, **request: Any) -> Any:
        """The way this program has always asked."""
        self.parsed.append(request)
        return an_answer(a_claim("Anything at all.", cause="C"))

    def stream(self, **request: Any) -> "Wire":
        """The way it asks when somebody is listening."""
        self.streamed.append(request)
        return self

    def __enter__(self) -> "Wire":
        """Hand back the arriving answer."""
        return self

    def __exit__(self, kind: Any, what: Any, where: TracebackType | None) -> None:
        """Close it, as the library's own does."""

    def __iter__(self) -> Any:
        """Hand over each piece of the answer in turn."""
        return iter(self._happenings)

    def get_final_message(self) -> Any:
        """The whole answer, once it has finished arriving."""
        return an_answer(a_claim("Anything at all.", cause="C"))


def test_a_call_with_nobody_listening_is_the_request_it_has_always_been() -> None:
    """The recorder's request, byte for byte — which is why nine cassettes still match."""
    wire = Wire()

    Model(wire).proposal("one question", may_search=True)  # type: ignore[arg-type]

    assert wire.streamed == []
    assert len(wire.parsed) == 1
    assert wire.parsed[0]["thinking"] == {"type": "adaptive"}
    assert "stream" not in wire.parsed[0]


def test_a_call_somebody_is_listening_to_is_streamed_and_thinks_out_loud() -> None:
    """The same question, two live-only differences, and nothing else moved."""
    plain, listened_to = Wire(), Wire()
    said: list[WhatItIsDoing] = []

    Model(plain).proposal("one question", may_search=True)  # type: ignore[arg-type]
    Model(listened_to, on_activity=said.append).proposal(  # type: ignore[arg-type]
        "one question", may_search=True
    )

    assert plain.streamed == [] and listened_to.parsed == []
    asked, also_asked = plain.parsed[0], listened_to.streamed[0]
    assert also_asked["thinking"] == THINKING_OUT_LOUD
    assert also_asked["thinking"]["display"] == "summarized"
    # Everything a request is made of besides the thinking is the same request.
    assert {one: also_asked[one] for one in asked if one != "thinking"} == {
        one: asked[one] for one in asked if one != "thinking"
    }


def test_a_streamed_call_says_each_thing_it_does_as_it_does_it() -> None:
    """Three blocks, three lines, each carrying somebody else's words."""
    said: list[WhatItIsDoing] = []
    wire = Wire([_a_search(A_QUERY), _what_came_back(), _the_end_of_a_thought("So it falls.")])

    Model(wire, on_activity=said.append).proposal("q", may_search=True)  # type: ignore[arg-type]

    assert [one.kind for one in said] == ["searching", "found", "thinking"]
    assert said[0].text == A_QUERY
    assert all(one.question == "q" for one in said)


def test_a_listener_that_throws_never_stops_a_call() -> None:
    """A line on a strip may not take a paid call with it."""

    def throws(doing: WhatItIsDoing) -> None:
        raise RuntimeError("the reader went away in the rudest possible way")

    wire = Wire([_a_search(A_QUERY)])

    answered = Model(wire, on_activity=throws).proposal("q", may_search=True)  # type: ignore[arg-type]

    assert answered.answered is not None


# --- Reading one piece of an arriving answer ---------------------------------


def test_a_search_says_the_query_the_model_wrote_verbatim() -> None:
    """Not summarised, not tidied, not put in our words. The query, as written."""
    assert what_it_is_doing(_a_search(A_QUERY), "") == ("searching", A_QUERY)


def test_a_search_with_nothing_to_show_says_nothing() -> None:
    """A tool call whose input never named a query is not a line anybody can read."""
    assert what_it_is_doing(_a_search(""), "") is None


def test_what_came_back_is_named_by_its_own_title_and_its_host() -> None:
    """A title alone does not say whether it came from a wire service or a forum."""
    reading = what_it_is_doing(_what_came_back(), "")

    assert reading == ("found", f"{A_TITLE} · lloyds.com")


def test_a_search_that_failed_says_nothing() -> None:
    """It comes back as one error object where a list would be, and reads as nothing found."""
    failed = ContentBlockStopEvent(
        type="content_block_stop",
        index=0,
        content_block=WebSearchToolResultBlock(
            type="web_search_tool_result",
            tool_use_id="srvtoolu_1",
            content={"type": "web_search_tool_result_error", "error_code": "max_uses_exceeded"},
        ),
    )

    assert what_it_is_doing(failed, "") is None


def test_thinking_is_the_most_recent_whole_sentence() -> None:
    """Never half a sentence: a line that reads as unfinished reads as broken."""
    so_far = "The premium matters first. Then the rate follows. And then"

    assert what_it_is_doing(_thinking(so_far), "") == ("thinking", "Then the rate follows.")


def test_thinking_with_no_whole_sentence_yet_says_nothing() -> None:
    """Until the first full stop there is nothing whole to show."""
    assert what_it_is_doing(_thinking("The premium matters"), "") is None


def test_thinking_that_stopped_without_a_full_stop_is_shown_from_its_end() -> None:
    """Once no more is coming, its tail is the truest thing there is."""
    reading = what_it_is_doing(_the_end_of_a_thought("The premium matters"), "")

    assert reading == ("thinking", "The premium matters")


def test_a_long_thought_is_cut_at_a_word_and_keeps_its_end() -> None:
    """The end is the part that just arrived, and no word is shown in halves."""
    long = ("word " * 200).strip() + " last."

    reading = what_it_is_doing(_thinking(long), "")

    assert reading is not None
    _, line = reading
    assert len(line) <= AS_MUCH_THINKING_AS_FITS
    assert line.endswith("last.")
    assert not line.startswith("ord")


def test_the_same_sentence_is_not_said_twice() -> None:
    """Every delta of a block carries the whole of it so far, and most of it is old news."""
    so_far = "The premium matters first."

    assert what_it_is_doing(_thinking(so_far), "The premium matters first.") is None


def test_a_piece_this_does_not_recognise_says_nothing_at_all() -> None:
    """The blocks are documented; the shape they arrive in has never met the service."""

    class SomethingNew:
        type = "something_nobody_has_seen"

    assert what_it_is_doing(SomethingNew(), "") is None


# --- The library's own blocks, with words written by hand --------------------


def _a_search(query: str) -> ContentBlockStopEvent:
    """One finished web search, as the library hands it over."""
    return ContentBlockStopEvent(
        type="content_block_stop",
        index=0,
        content_block=ServerToolUseBlock(
            type="server_tool_use",
            id="srvtoolu_1",
            name="web_search",
            input={"query": query} if query else {},
        ),
    )


def _what_came_back() -> ContentBlockStopEvent:
    """One finished search result, as the library hands it over."""
    return ContentBlockStopEvent(
        type="content_block_stop",
        index=1,
        content_block=WebSearchToolResultBlock(
            type="web_search_tool_result",
            tool_use_id="srvtoolu_1",
            content=[
                WebSearchResultBlock(
                    type="web_search_result",
                    title=A_TITLE,
                    url=A_PAGE,
                    encrypted_content="whatever the service wrapped it in",
                )
            ],
        ),
    )


def _thinking(so_far: str) -> ThinkingEvent:
    """One more piece of summarised thinking, with everything said so far beside it."""
    return ThinkingEvent(type="thinking", thinking=so_far[-10:], snapshot=so_far)


def _the_end_of_a_thought(whole: str) -> ContentBlockStopEvent:
    """A finished block of summarised thinking."""
    return ContentBlockStopEvent(
        type="content_block_stop",
        index=2,
        content_block=ThinkingBlock(type="thinking", thinking=whole, signature="signed"),
    )


@pytest.fixture(autouse=True)
def _no_key_anywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing here may reach a network even by accident."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
