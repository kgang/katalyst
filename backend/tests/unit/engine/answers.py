"""Answers written out by hand, in the same types the service returns.

Decision record 0008 warns about hand-written stand-ins for a client library:
they encode our assumptions about the library rather than its behaviour, and rot
silently. Two things keep that warning answered here.

**These are not stand-ins for the library.** Every answer below is built out of
the library's own response types — the same classes it hands back over the wire —
so a change to those classes breaks these tests immediately rather than quietly.
What is hand-written is the *content* of an answer, not its shape.

**They do not replace the recorded exchanges.** The boundary tests still run
against real answers recorded to disk. What these buy is the other half: a
refusal, a run that spends its ceiling, three refusals in a row on one claim — none
of which a live model will produce on demand, and all of which are rules the
product rests on.

Nothing here talks to a network, and nothing here needs a key.
"""

from datetime import date
from threading import Lock

from anthropic.types import ParsedMessage, Usage, WebSearchResultBlock, WebSearchToolResultBlock
from anthropic.types.parsed_message import ParsedTextBlock
from anthropic.types.refusal_stop_details import RefusalStopDetails
from anthropic.types.server_tool_usage import ServerToolUsage

from katalyst.domain import BaseRate, ContractPayoff, Resolution
from katalyst.engine.proposal import (
    ClaimProposal,
    LinkDraft,
    LinkProposal,
    Proposal,
    Ranged,
    SourceDraft,
    StartingClaim,
    Stop,
)

FROM_THE_QUESTION = "<the claim this question is about>"
"""What a story writes where a real answer would copy a short name out of the question.

The prompt hands out the short names and a model points back at one of them. A
story written by hand cannot know them in advance — they are minted while the run
is happening — so it writes this instead, and `Storyteller` puts the real one in
before answering, exactly as a model reading the question would have.
"""

SETTLED_BY = date(2026, 11, 1)
"""One resolve-by date, used everywhere so no test is about a date."""

THE_DAY_THE_RUN_HAPPENED = date(2026, 9, 17)
"""The day every test run pretends to be happening on.

Passed in rather than read from a clock, which is the whole reason the pipeline
takes it as an argument.
"""


# --- The things a model may answer with ------------------------------------


def a_claim(
    claim: str,
    *,
    cause: str,
    kind: str = "event",
    cites: tuple[str, ...] = (),
    rationale: str = "The cause moves the effect, and here is how.",
    criteria: str = "A test two people reading it would agree on.",
    counted: BaseRate | None = None,
    names_a_trade: bool = True,
) -> ClaimProposal:
    """Write out one claim proposal, with the arrow that reaches it."""
    payoff = (
        ContractPayoff(venue="Somewhere", contract_id="c-1", title="Does it?", side="yes")
        if kind == "market" and names_a_trade
        else None
    )
    return ClaimProposal(
        kind="claim",
        claim=claim,
        claim_kind=kind,  # type: ignore[arg-type]
        resolution=Resolution(criteria=criteria, source="A named judge.", by=SETTLED_BY),
        prior=Ranged(p=0.4, lo=0.2, hi=0.6),
        base_rate=counted,
        payoff=payoff,
        not_tradeable_reason="No venue quotes this claim." if kind == "not_tradeable" else None,
        cause=cause,
        link=an_arrow(rationale=rationale, cites=cites),
    )


def an_arrow(
    *, rationale: str = "The cause moves the effect, and here is how.", cites: tuple[str, ...] = ()
) -> LinkDraft:
    """Write out one arrow draft."""
    return LinkDraft(
        mode="sustain",
        strength=0.5,
        lag=1,
        shape="step",
        half_life=None,
        rationale=rationale,
        sources=tuple(SourceDraft(url=url, title="What the model says it read") for url in cites),
    )


def a_link(source: str, target: str, **arrow: object) -> LinkProposal:
    """Write out one arrow between two claims already on the map."""
    return LinkProposal(kind="link", source=source, target=target, link=an_arrow(**arrow))  # type: ignore[arg-type]


def a_stop(why: str = "This part of the story is finished.") -> Stop:
    """Write out the answer that says there is nothing more here."""
    return Stop(kind="stop", why=why)


def a_starting_claim(claim: str = "The thing the person expects happens.") -> StartingClaim:
    """Write out a person's own sentence, turned into a claim."""
    return StartingClaim(
        claim=claim,
        resolution=Resolution(
            criteria="A test two people reading it would agree on.",
            source="A named judge.",
            by=SETTLED_BY,
        ),
        prior=Ranged(p=0.3, lo=0.1, hi=0.5),
    )


# --- The answers those arrive inside ---------------------------------------


def an_answer(
    said: object,
    *,
    found: tuple[str, ...] = (),
    searches: int = 0,
    read_fresh: int = 200,
    written: int = 100,
    read_from_cache: int = 0,
    written_to_cache: int = 0,
    stopped: str = "end_turn",
) -> ParsedMessage[Proposal]:
    """Build one answer the way the service builds one.

    Args:
        said: The proposal, already checked against its shape, as the library
            would have handed it over.
        found: Addresses the search tool returned during this call.
        searches: How many searches the service says it ran.
        read_fresh: Tokens of question read at full price.
        written: Tokens of answer.
        read_from_cache: Tokens recognised from an earlier call.
        written_to_cache: Tokens written into the cache.
        stopped: Why the model stopped writing.

    Returns:
        One answer, in the library's own types.
    """
    content: list[object] = (
        [
            WebSearchToolResultBlock(
                type="web_search_tool_result",
                tool_use_id="a-search",
                content=[
                    WebSearchResultBlock(
                        type="web_search_result",
                        url=url,
                        title=f"What is at {url}",
                        encrypted_content="",
                        page_age=None,
                    )
                    for url in found
                ],
            )
        ]
        if found
        else []
    )
    content.append(_a_block(said))
    return ParsedMessage[type(said)](  # type: ignore[misc,valid-type,no-any-return]
        id="an-answer",
        content=content,  # type: ignore[arg-type]
        model="claude-opus-5",
        role="assistant",
        stop_reason=stopped,  # type: ignore[arg-type]
        type="message",
        usage=_usage(read_fresh, written, read_from_cache, written_to_cache, searches),
    )


def a_declined_answer(explanation: str | None = None) -> ParsedMessage[Proposal]:
    """Build the answer the service returns when its own safety check declines a call."""
    return ParsedMessage[Proposal](
        id="declined",
        content=[],
        model="claude-opus-5",
        role="assistant",
        stop_reason="refusal",
        stop_details=RefusalStopDetails(type="refusal", category=None, explanation=explanation),
        type="message",
        usage=_usage(200, 0, 0, 0, 0),
    )


def a_search_that_failed(said: object) -> ParsedMessage[Proposal]:
    """Build an answer whose search came back as an error rather than as results."""
    return ParsedMessage[type(said)](  # type: ignore[misc,valid-type,no-any-return]
        id="search-failed",
        content=[  # type: ignore[arg-type]
            WebSearchToolResultBlock(
                type="web_search_tool_result",
                tool_use_id="a-search",
                content={"type": "web_search_tool_result_error", "error_code": "max_uses_exceeded"},  # type: ignore[arg-type]
            ),
            _a_block(said),
        ],
        model="claude-opus-5",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=_usage(200, 100, 0, 0, 1),
    )


def _a_block(said: object) -> ParsedTextBlock[object]:
    """Wrap one already-checked answer the way the library wraps one.

    The block is parameterised by the shape that was actually answered with,
    because the library checks what it is holding: a claim proposal goes in a
    block that expects one.
    """
    return ParsedTextBlock[type(said)](  # type: ignore[misc,valid-type]
        type="text", text="{}", citations=None, parsed_output=said
    )


def _usage(fresh: int, written: int, cached: int, into_cache: int, searches: int) -> Usage:
    """Build the counters the service reports on every answer."""
    return Usage(
        input_tokens=fresh,
        output_tokens=written,
        cache_read_input_tokens=cached,
        cache_creation_input_tokens=into_cache,
        server_tool_use=ServerToolUsage(web_search_requests=searches, web_fetch_requests=0),
    )


# --- Something to ask ------------------------------------------------------


class Scripted:
    """An answerer that hands back answers written in advance, and remembers the questions.

    It is what the pipeline is handed instead of a live client. It never talks to
    anything, and it keeps every question it was asked so a test can check that a
    call after a refusal is the same call, word for word.

    Answers run out on purpose: once the list is empty, the last answer repeats.
    A test that wants a run to stop says so with a cap, never by running the
    answers out.
    """

    def __init__(
        self,
        proposals: list[ParsedMessage[Proposal]] | None = None,
        *,
        starting: list[ParsedMessage[Proposal]] | None = None,
        raises: Exception | None = None,
    ) -> None:
        """Set out what this answerer will say.

        Args:
            proposals: The answers to hand back, in order, to the questions that
                grow a map.
            starting: The answers to hand back to the questions that turn a
                person's own sentence into a claim.
            raises: Something to raise instead of answering, for the case where
                an answer does not fit the shape we asked for.
        """
        self._proposals = list(proposals or [])
        self._starting = list(starting or [])
        self._raises = raises
        self._lock = Lock()
        self.asked: list[str] = []
        self.searched: list[bool] = []

    def starting_claim(self, question: str) -> list[ParsedMessage[Proposal]]:
        """Answer the question that turns one typed sentence into a claim."""
        with self._lock:
            self.asked.append(question)
            if self._raises is not None:
                raise self._raises
            return [self._next(self._starting)]

    def proposal(self, question: str, *, may_search: bool) -> list[ParsedMessage[Proposal]]:
        """Answer the question that asks for the one next piece of the map."""
        with self._lock:
            self.asked.append(question)
            self.searched.append(may_search)
            if self._raises is not None:
                raise self._raises
            return [self._next(self._proposals)]

    def _next(self, waiting: list[ParsedMessage[Proposal]]) -> ParsedMessage[Proposal]:
        """Take the next answer, or repeat the last one once they have run out."""
        if not waiting:
            return an_answer(a_starting_claim())
        if len(waiting) > 1:
            return waiting.pop(0)
        return waiting[0]


ASKING_ABOUT = "We are asking about this claim: "
"""The line in a question that names the claim it is about."""


class Storyteller:
    """An answerer that answers by *which claim* the question is about.

    A walk asks three questions at once, so an answerer handing answers out of one
    queue would give them to whichever thread got there first, and a test written
    against it would pass or fail by the weather. This one reads the question,
    finds the claim it is about, and answers from that claim's own list — so the
    same story always produces the same map.

    A claim the story says nothing about gets the same answer every time: there is
    nothing more here.
    """

    def __init__(
        self,
        story: dict[str, list[ParsedMessage[Proposal]]] | None = None,
        *,
        starting: list[ParsedMessage[Proposal]] | None = None,
        otherwise: ParsedMessage[Proposal] | None = None,
    ) -> None:
        """Set out the story this answerer tells.

        Args:
            story: For each claim's own words, the answers to give when asked
                about it, in order. Once they run out, that claim is answered the
                way a claim the story never mentioned is answered.
            starting: The answers to the questions that turn a person's own
                sentences into claims, in order.
            otherwise: What to say about a claim the story does not mention.
        """
        self._story = {claim: list(said) for claim, said in (story or {}).items()}
        self._starting = list(starting or [])
        self._otherwise = otherwise or an_answer(a_stop())
        self._lock = Lock()
        self.asked: list[str] = []
        self.asked_about: list[str] = []
        self.searched: list[bool] = []

    def starting_claim(self, question: str) -> list[ParsedMessage[Proposal]]:
        """Answer the question that turns one typed sentence into a claim."""
        with self._lock:
            self.asked.append(question)
            if not self._starting:
                return [an_answer(a_starting_claim())]
            if len(self._starting) > 1:
                return [self._starting.pop(0)]
            return [self._starting[0]]

    def proposal(self, question: str, *, may_search: bool) -> list[ParsedMessage[Proposal]]:
        """Answer the question that asks for the one next piece of the map."""
        with self._lock:
            about = question.split(ASKING_ABOUT, 1)[1].splitlines()[0]
            self.asked.append(question)
            self.asked_about.append(about)
            self.searched.append(may_search)
            waiting = self._story.get(about)
            said = waiting.pop(0) if waiting else self._otherwise
            return [_pointing_at(said, question, about)]


def _pointing_at(
    answer: ParsedMessage[Proposal], question: str, about: str
) -> ParsedMessage[Proposal]:
    """Put the short name the question handed out where the story left a placeholder.

    A real model copies a short name out of the question it was asked. A story
    written by hand cannot, because the names are minted while the run is
    happening — so this does it, and only for answers that asked for it.
    """
    said = answer.parsed_output
    if isinstance(said, ClaimProposal) and said.cause == FROM_THE_QUESTION:
        named = _name_for(question, about)
        return answer.model_copy(
            update={"content": [_a_block(said.model_copy(update={"cause": named}))]}
        )
    if isinstance(said, LinkProposal):
        # A story writes an arrow by naming the two claims' own words; the short
        # names are minted while the run is happening, so they are put in here.
        return answer.model_copy(
            update={
                "content": [
                    _a_block(
                        said.model_copy(
                            update={
                                "source": _name_for(question, about)
                                if said.source == FROM_THE_QUESTION
                                else _name_for(question, said.source),
                                "target": _name_for(question, said.target),
                            }
                        )
                    )
                ]
            }
        )
    return answer


def _name_for(question: str, about: str) -> str:
    """Find the short name the question gave the claim it is asking about.

    The map block writes one line per claim: two spaces, the short name, two more
    spaces, the claim's own words, and — on the one the map started from — a note
    saying so.
    """
    for line in question.splitlines():
        if not line.startswith("  "):
            continue
        parts = line.strip().split("  ", 1)
        if len(parts) == 2 and parts[1].startswith(about):
            return parts[0]
    raise AssertionError(f"the question never listed a claim reading {about!r}")
