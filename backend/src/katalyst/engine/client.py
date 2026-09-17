"""The one place this program talks to a model, and the one place its types appear.

Everything else in the pipeline is arithmetic and rules over values already in
hand. This file is the seam. On one side a question written as plain text; on the
other a `Said` — our own small shape holding what was answered, what the search
returned, whether the model declined, and what the call cost. **The library's own
types are named here and nowhere else in this program**, and a test reads the
layer's source to keep it so.

Why a seam and not a function
-----------------------------
`expand.py` takes an *answerer* as an argument rather than reaching for a client
itself. Three things follow, and each of them is the point:

* The tests are fast and exact. A test that wants a refusal writes a refusal; it
  does not hope one turns up in a recording.
* Nothing below this line can start calling a model by accident.
* Playing back a recorded run plugs in where the live answerer does, with no
  second path through the pipeline.

`what_it_said` is the translation, and it is a pure function of an answer. The
tests build answers in the library's own types and put them through this same
function, so what they exercise is what a real call exercises.

The search tool, and the two states it has
-------------------------------------------
The tool, its version and its per-call limit were re-read from the `claude-api`
reference bundle on 2026-09-17. Three things about it are decisions rather than
defaults: one search per call, nothing declared alongside it, and no fetching of
a page of our own choosing.

Once a run has spent its whole budget of searches, the tool stays declared and is
**forbidden** for the rest of the run rather than removed from the list. The two
look the same to the model and cost very differently: the tool list is written at
the very front of a request, so removing it would stop the service recognising
the prefix it has been reading back at a tenth of the price all run, while
forbidding it leaves that prefix untouched.

What this file must never do
----------------------------
- Never decide anything about a map. It asks, it translates, it hands back.
- Never read an environment variable itself; `katalyst.settings` is the one place
  that does.
- Never hide a refusal or a part-finished answer. Both come back for the pipeline
  to report.
- Never declare a place to run code beside the search tool, and never declare a
  tool that fetches a page of our choosing.
"""

import time
from collections.abc import Sequence
from typing import Any, Literal, Protocol

import anthropic
from anthropic import Omit, omit

# A private path into the client library, used in exactly one place and never to
# build a request: `wire_schema` below looks at what the library *would* send, so
# a test can check it before a call is made. If the library ever moves it, the
# import fails loudly at start-up rather than the product failing quietly.
from anthropic.lib._parse._transform import transform_schema
from anthropic.types import (
    MessageParam,
    OutputConfigParam,
    ParsedMessage,
    TextBlockParam,
    ToolChoiceParam,
    WebSearchTool20260209Param,
)
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from katalyst.engine.outcome import FoundPage, Said
from katalyst.engine.pricing import MODEL
from katalyst.engine.prompt import STANDING_TEXT
from katalyst.engine.proposal import Proposal, StartingClaim
from katalyst.settings import get_settings

ROOM_FOR_AN_ANSWER = 16_000
"""How many tokens one answer may take, thinking included.

A proposal is a few hundred words, but the model thinks before it writes and that
thinking is counted here too. The figure is the one the `claude-api` reference
bundle gives for a request that is not streamed: large enough that an answer is
never cut off in the middle, small enough that the request cannot sit past the
client library's own patience.
"""

SEARCHES_INSIDE_ONE_CALL = 1
"""How many web searches the model may run while answering one question.

One proposal per call, one search per proposal. One answer is one claim and the
one arrow that reaches it, so it is checking one mechanism, and a budget of one
look keeps the bill in step with the work. It is raised only when a measurement
says it should be, never because a run felt thin.

Fixed for the whole of a run, on purpose. A figure that counted down per call
would change the tool list, and the tool list is the very front of the request.
"""

TIMES_A_PART_FINISHED_ANSWER_IS_SENT_BACK = 3
"""How often a part-finished answer is handed straight back to be continued.

A question that uses the search tool can come back with the search half done and
no answer yet. The service expects exactly one thing in reply: the same
conversation with its own part-finished turn on the end, and no new instruction —
it picks up where it left off. This is how many times we will do that before
treating the answer as one we never got.
"""

SEARCH_TOOL: WebSearchTool20260209Param = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": SEARCHES_INSIDE_ONE_CALL,
}
"""The search tool, as it is declared. Declared on every call, without exception.

The name and the version are the ones the `claude-api` reference bundle gives,
read on 2026-09-17. This version filters what it finds before the results reach
the model, which is why nothing here declares a place to run code alongside it: a
second one would only confuse matters. Nothing declares a tool that fetches a
page either — a document the search never offered is a document we went looking
for to support a conclusion we already had.

A search that fails does not raise. The answer comes back normally and the result
block holds one error instead of a list of results, which reads as nothing found.
"""

HOW_HARD_TO_TRY: Literal["low", "medium", "high", "xhigh", "max"] | None = None
"""How hard the model tries, pinned for the whole program rather than per call.

`None` means the setting is not sent at all, which is where it stands today: the
service's own default is `high`, and naming a value here — even the same one —
puts a field in the request that was not there before. The request is what a
recorded exchange is matched on, so changing this re-records every cassette and
every demo recording, and that is a decision with a bill attached rather than a
tuning knob.

**It is a constant on purpose.** Changing how hard the model tries between calls
would throw away the remembered prefix the whole run is reading back at a tenth
of the price, so this may be edited but never varied.

The reason to reach for it: the first five recorded calls spent **half to
two-thirds of their written tokens thinking**, and took about a minute each.
`medium` is the first thing to measure against the default, and the transcript
now carries the thinking tokens and the seconds per call so that measurement
needs no second experiment.
"""

MAY_SEARCH: ToolChoiceParam = {"type": "auto"}
"""The model decides for itself whether this question needs a look at the web."""

MAY_NOT_SEARCH: ToolChoiceParam = {"type": "none"}
"""The tool is there and may not be used, which is how a run spends its last search.

Changing this between calls leaves the remembered prefix — the tools and the
standing text — intact, which is the whole reason it is done this way rather than
by taking the tool out of the list.
"""

STANDING_BLOCK: list[TextBlockParam] = [
    {
        "type": "text",
        "text": STANDING_TEXT,
        # Mark the end of the part that never changes. Everything up to here —
        # the tools and this text — is recognised on the next call and charged at
        # a tenth of the price. A run whose answers report nothing read back is a
        # bug in how this request is put together, not a slow day.
        "cache_control": {"type": "ephemeral"},
    }
]
"""The standing half of every request, marked as the part worth remembering."""


class OneProposal(BaseModel):
    """The envelope a proposal travels in, and the one thing in this layer the wire forced.

    A proposal is one of three shapes told apart by a `kind` field. Written out as
    a description of what an answer must look like, that is a choice at the very
    top — and **the service refuses a top-level choice that also names shapes by
    reference**: *"output_config.format.schema: For 'anyOf', '$defs' is not
    supported"* (2026-09-17, the first live call). Put the same choice one field
    down and the top is an ordinary object, which it accepts.

    So this exists for the wire and for nothing else. It is put on at the moment
    the question goes out and taken off at the moment the answer comes back, both
    inside this file. **No field of any proposal is renamed, and nothing outside
    this file knows the envelope exists** — `expand.py` is handed a plain
    proposal, exactly as before.

    A single shape such as a starting claim is already an object at the top, so it
    needs no envelope and does not get one.
    """

    model_config = ConfigDict(frozen=True)

    proposal: Proposal = Field(description="The one thing this answer is.")


def wire_schema(shape: Any) -> dict[str, Any]:
    """Return the exact description of an answer that the library will send.

    The library builds this from the shape and then tidies it — dropping what the
    service does not support and validating those parts on this side instead — so
    reading the shape's own description would not tell you what actually goes out.
    This is the thing to make assertions about.

    Args:
        shape: A shape an answer must fit.

    Returns:
        The description as the service will receive it.
    """
    schema: dict[str, Any] = TypeAdapter(shape).json_schema()
    tidied: dict[str, Any] = transform_schema(schema)
    return tidied


class AnswerWeCouldNotRead(Exception):
    """The model wrote something that did not fit the shape the call asked for.

    Carried across the seam as one of ours rather than as the library's own
    complaint, so that nothing past this file has to know whose complaint it was.
    Its sentence is written for a person.
    """

    def __init__(self, why: str) -> None:
        """Hold the plain sentence of what went wrong."""
        super().__init__(why)
        self.why = why


class Answerer(Protocol):
    """Whatever the pipeline asks its questions of.

    Two questions, because a run asks two kinds. Before anything is expanded, a
    sentence a person typed is turned into a claim anybody could settle. After
    that, every call asks for the one next piece of the map.

    Both hand back one `Said`. A question that came back part finished and was
    sent back to be continued is still one answer; every trip it took is on its
    counters, and a bill that quietly missed one would make the spending cap a
    lie.

    Both raise `AnswerWeCouldNotRead` when the model wrote something that did not
    fit the shape.
    """

    def starting_claim(self, question: str) -> Said:
        """Ask for one typed sentence, written as a claim anybody could settle."""
        ...

    def proposal(self, question: str, *, may_search: bool) -> Said:
        """Ask for the one next piece of the map, searching or not."""
        ...


class Model:
    """The live answerer: the vendor's own client, and nothing added to it.

    Built around an already-made client so that a caller can hand in one with a
    different patience or a different address without this file growing a second
    way to be configured.

    This class must never look at what was *said*. It asks, it sends a
    part-finished answer back to be continued, and it translates. Reading an
    answer — accepting it, refusing it, saying it made no sense — belongs to
    `expand.py`, which can be tested without spending a penny.
    """

    def __init__(self, client: anthropic.Anthropic, *, model: str = MODEL) -> None:
        """Wrap a client.

        Args:
            client: The vendor's client, already built and already holding
                whatever credentials it needs.
            model: Which model to ask. The default is the one decision record
                0006 chose and `pricing.py` prices.
        """
        self._client = client
        self._model = model

    def starting_claim(self, question: str) -> Said:
        """Ask for one typed sentence, written as a claim anybody could settle.

        Searching is forbidden on this call. The question is what the person
        meant, and the web has nothing to say about that.

        Args:
            question: The varying half of the request, from `prompt.py`.

        Returns:
            The answer, in our own words.
        """
        return self._ask(question, StartingClaim, may_search=False)

    def proposal(self, question: str, *, may_search: bool) -> Said:
        """Ask for the one next piece of the map.

        Args:
            question: The varying half of the request, from `prompt.py`.
            may_search: Whether this run still has searches left. False forbids
                the tool for this call and leaves it in the list.

        Returns:
            The answer, in our own words.
        """
        return self._ask(question, OneProposal, may_search=may_search)

    def _ask(self, question: str, shape: Any, *, may_search: bool) -> Said:
        """Put one question, sending a part-finished answer back until it finishes.

        The shape is handed to the client library, which turns it into the
        description of what an answer must look like, sends it with the request,
        and checks what comes back against it before returning.

        The shape goes on `output_format`, which is what `messages.parse` takes;
        the reference bundle's note that `output_format` is deprecated is about
        `messages.create`, where the same thing is spelled `output_config.format`.
        `messages.parse` merges the two itself. Do not "fix" this to the other
        spelling — decision record 0006 names this call.

        Args:
            question: The varying half of the request.
            shape: What an answer must fit — a starting claim, or a proposal.
            may_search: Whether the search tool may be used on this call.

        Returns:
            The answer, in our own words.

        Raises:
            AnswerWeCouldNotRead: If what came back did not fit the shape.
        """
        # Sent only when somebody has decided to send it; see `HOW_HARD_TO_TRY`.
        trying: OutputConfigParam | Omit = (
            {"effort": HOW_HARD_TO_TRY} if HOW_HARD_TO_TRY is not None else omit
        )
        conversation: list[MessageParam] = [{"role": "user", "content": question}]
        rounds: list[ParsedMessage[Any]] = []
        started = time.monotonic()
        for _ in range(TIMES_A_PART_FINISHED_ANSWER_IS_SENT_BACK + 1):
            try:
                answer = self._client.messages.parse(
                    model=self._model,
                    max_tokens=ROOM_FOR_AN_ANSWER,
                    # The model decides for itself how long to think. How hard it
                    # tries is left at the service's own default, which is the
                    # setting we want; naming it would add a knob that changes
                    # nothing and a second place for two settings to disagree.
                    thinking={"type": "adaptive"},
                    system=STANDING_BLOCK,
                    tools=[SEARCH_TOOL],
                    tool_choice=MAY_SEARCH if may_search else MAY_NOT_SEARCH,
                    messages=conversation,
                    output_format=shape,
                    output_config=trying,
                )
            except ValidationError as did_not_fit:
                raise AnswerWeCouldNotRead(_did_not_fit_the_shape(did_not_fit)) from did_not_fit
            rounds.append(answer)
            if answer.stop_reason != "pause_turn":
                return what_it_said(rounds, seconds=time.monotonic() - started)
            # Part finished. The service picks up from its own turn, and adding a
            # "carry on" of our own would only confuse it.
            conversation = [*conversation, {"role": "assistant", "content": answer.content}]
        return what_it_said(rounds, seconds=time.monotonic() - started)


def what_it_said(rounds: Sequence[ParsedMessage[Any]], *, seconds: float = 0.0) -> Said:
    """Turn every round trip of one question into one answer in our own words.

    The only place a reply of the library's becomes a shape of ours. Pure: it
    reads what it is given and asks nothing of anybody, which is what lets the
    tests put hand-written replies through the very same translation a live call
    goes through.

    What the model wrote and what the search returned come out in **two different
    fields**, because the whole grounding rule rests on never confusing them.

    A proposal arrives inside the envelope the wire forced on it, and leaves
    without one.

    Args:
        rounds: Every round trip the question took, oldest first. The last one
            holds the answer.
        seconds: How long the whole question took, measured by the caller that
            made it. Passed in rather than read here, so this stays a pure
            function of an answer and a test can hand it a fixed number.

    Returns:
        The answer, its search results, whether the model declined, and the sum of
        what every trip cost.
    """
    last = rounds[-1]
    answered = last.parsed_output
    if isinstance(answered, OneProposal):
        # The envelope comes off here, so nothing past this file ever sees it.
        answered = answered.proposal
    return Said(
        answered=answered,
        found=_pages_the_search_returned(rounds),
        declined=_declined(last),
        calls=len(rounds),
        searches=sum(
            one.usage.server_tool_use.web_search_requests if one.usage.server_tool_use else 0
            for one in rounds
        ),
        input_tokens=sum(one.usage.input_tokens for one in rounds),
        output_tokens=sum(one.usage.output_tokens for one in rounds),
        cache_read_tokens=sum(one.usage.cache_read_input_tokens or 0 for one in rounds),
        cache_write_tokens=sum(one.usage.cache_creation_input_tokens or 0 for one in rounds),
        thinking_tokens=sum(
            one.usage.output_tokens_details.thinking_tokens
            if one.usage.output_tokens_details
            else 0
            for one in rounds
        ),
        seconds=seconds,
    )


def _pages_the_search_returned(rounds: Sequence[ParsedMessage[Any]]) -> tuple[FoundPage, ...]:
    """Read the search tool's own results out of an answer, and nothing else.

    A question sent back to be continued can search on either trip, so the results
    are the whole question's rather than the last trip's. A page returned twice is
    kept once, in the order it first arrived.

    A search that failed comes back as one error object where a list of results
    would be, which reads here as nothing found.

    Args:
        rounds: Every round trip the question took, oldest first.

    Returns:
        One page per result, in the order the tool returned them.
    """
    found: list[FoundPage] = []
    seen: set[str] = set()
    for one in rounds:
        for block in one.content:
            if block.type != "web_search_tool_result":
                continue
            results = block.content
            if not isinstance(results, list):
                continue  # The tool reported an error instead of results.
            for result in results:
                if result.type != "web_search_result" or result.url in seen:
                    continue
                seen.add(result.url)
                found.append(FoundPage(url=result.url, title=result.title))
    return tuple(found)


def _declined(answer: ParsedMessage[Any]) -> str | None:
    """Say, in plain words, that the model declined the question — or that it did not.

    The vendor's own safety check can turn a call down. That comes back as an
    ordinary answer with a stop reason saying so, and sometimes with an
    explanation. It is surfaced as a refusal a person sees, never hidden and never
    quietly re-routed to a different model — decision record 0006 declines the
    server-side rerouting the reference bundle offers, for exactly that reason.

    Args:
        answer: The last round trip's answer.

    Returns:
        One plain sentence, or nothing at all when the model did not decline.
    """
    if answer.stop_reason != "refusal":
        return None
    details = answer.stop_details
    if details is not None and details.explanation:
        return f"The model declined to answer this question. It said: {details.explanation}"
    return "The model declined to answer this question."


def _did_not_fit_the_shape(problem: ValidationError) -> str:
    """Say, in plain words, that the answer did not fit the shape we asked for.

    Nothing technical reaches a screen. The field names are the same words this
    spec uses for those fields, so naming them helps rather than mystifies.

    Args:
        problem: What the shape check objected to.

    Returns:
        One plain sentence.
    """
    fields = sorted(
        {
            ".".join(str(step) for step in fault["loc"] if not str(step).startswith("function-"))
            for fault in problem.errors()
        }
    )
    named = ", ".join(field for field in fields if field)
    if not named:
        return "The model's answer did not fit the shape this call asked for."
    return f"The model's answer did not fit the shape this call asked for, at: {named}."


def live_answerer() -> Model | None:
    """Build the live answerer, or say plainly that there is no key for one.

    The one function that knows whether this program can call a model at all.
    Nothing here raises and nothing here prints: a missing key is an ordinary fact
    about how the program was started, and the screen says so rather than failing.

    Returns:
        A live answerer, or nothing at all when no key is configured.
    """
    key = get_settings().ANTHROPIC_API_KEY
    if not key:
        return None
    return Model(anthropic.Anthropic(api_key=key))
