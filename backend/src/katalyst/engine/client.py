"""The one place this program talks to a model, and the one place its types appear.

Everything else in the pipeline is arithmetic and rules over values already in
hand. This file is the seam: a question as plain text on one side, a `Said` on
the other — our own small shape holding what was answered, what the search
returned, whether the model declined, and what the call cost. **The library's own
types are named here and nowhere else**, and a test reads the layer's source to
keep it so.

`expand.py` takes an *answerer* as an argument rather than reaching for a client,
which is what lets a test write the refusal it wants instead of hoping one turns
up, stops anything below this line calling a model by accident, and lets a
recording plug in where the live answerer does. `what_it_said` is the
translation and it is pure, so a test's hand-written answer goes through exactly
what a real one does.

What this file must never do
----------------------------
- Never decide anything about a map. It asks, it translates, it hands back.
- Never read an environment variable itself; `katalyst.settings` does that.
- Never hide a refusal or a part-finished answer. Both come back for the
  pipeline to report.
- Never declare a place to run code beside the search tool, and never declare a
  tool that fetches a page of our choosing. Both were decided in record 0006.
- Never let saying what a call is doing change what a call is. `on_activity` is
  optional, the recorder and every recorded exchange leave it out — so their
  requests are byte for byte what they have always been — and anything that goes
  wrong while saying it is swallowed and logged. A run must be able to finish
  with nobody listening and with a listener that throws.
- Never take the search tool **out** of the list to stop a run searching. The
  tool list is the very front of a request, so removing it throws away the
  prefix the service has been reading back at a tenth of the price; forbidding
  it with `tool_choice` leaves that prefix untouched. The two look identical
  from here and cost very differently.

Everything the service can do to a call — declining, pausing part-finished,
rate-limiting, falling over, not answering — comes back through here as one of
our own shapes with a plain sentence on it. Nothing above this file should ever
have to know whose exception it was.
"""

import logging
import time
from collections.abc import Sequence
from importlib import import_module
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

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
    ThinkingConfigParam,
    ToolChoiceParam,
    WebSearchTool20260209Param,
)
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from katalyst.engine.outcome import WHAT_THE_SERVICE_DEFAULTS_TO, FoundPage, Said
from katalyst.engine.prompt import STANDING_TEXT
from katalyst.engine.proposal import Proposal, StartingClaim
from katalyst.engine.receipt import Receipt, fold, nothing_spent_yet, over_the_cap
from katalyst.settings import get_settings

ROOM_FOR_AN_ANSWER = 16_000
"""How many tokens one answer may take, thinking included.

A proposal is a few hundred words, but the model thinks before it writes and that
thinking is counted here too. The figure is the one the `claude-api` reference
bundle gives for a request that is not streamed: large enough that an answer is
never cut off in the middle, small enough that the request cannot sit past the
client library's own patience.
"""

SEARCHES_INSIDE_ONE_CALL = 25
"""How many web searches the model may run while answering one question.

One search was enough to check an arrow's mechanism and nowhere near enough to
**count a reference class**. The first measured run proved it: eight of ten
claims came back with a count like "12 of 15" and not one source behind it,
because the one search had gone to the arrow. Counting how often something has
happened before means finding the cases, and finding cases takes looking.

Fixed for the whole of a run, on purpose. A figure that counted down per call
would change the tool list, and the tool list is the very front of the request —
so the whole remembered prefix would be thrown away mid-run.
"""

ROUNDS_OF_RESEARCH = 5
"""How many passes one question may make — **passes, not continuations**.

A *round* is one pass in which the model searches, reads what came back, and
decides whether to search again, which is what `grounding.md` counts. The first
request is the first round, so five rounds is five requests and four hand-backs.
It was written as five hand-backs once, which made six rounds of a chapter that
says five (2026-09-20).

The service runs the search tool in a loop of its own and stops after a while,
handing back a part-finished answer. Sending it straight back — the same
conversation with its own turn on the end and no new instruction — lets it carry
on where it left off. Each of those is a round: search, read, decide whether to
look again.

**At the cap the answer is taken as it stands.** Whatever the model has by then
is what we read: if it found a countable class it says so, and if it did not, the
claim arrives without a base rate and the transcript says why. Nothing is retried
and nothing is asked a second time, because both would be paying twice for the
same question.
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

MAY_SEARCH: ToolChoiceParam = {"type": "auto"}
"""The model decides for itself whether this question needs a look at the web."""

MAY_NOT_SEARCH: ToolChoiceParam = {"type": "none"}
"""The tool is there and may not be used, which is how a run spends its last search.

Changing this between calls leaves the remembered prefix — the tools and the
standing text — intact, which is the whole reason it is done this way rather than
by taking the tool out of the list.
"""

THINKING_OUT_LOUD: ThinkingConfigParam = {"type": "adaptive", "display": "summarized"}
"""How the model is asked to think **on a live call that somebody is watching**.

The same adaptive thinking every other call asks for, plus one field: `display`,
set to `summarized`. Left alone, this model returns its thinking blocks with the
text emptied out, so a stream carries the shape of the thinking and none of the
words; asked for a summary, it writes a readable one. The raw chain of thought is
never returned by anything, at any setting, and nothing here asks for it.

**Live calls only.** The recorder sends `{"type": "adaptive"}` and nothing else,
which is what every committed recording and every recorded exchange under
`tests/cassettes/` was made with, and those are matched on the whole request
body. Asking for the summary there would rewrite nine of them for a line nobody
would ever read back (record 0027; R34 is the precedent for the live request
differing from the recorder's).

Read off the `claude-api` reference bundle on 2026-09-22, for this model at this
effort. **Never verified against the service** — no live call has been made since
this line was written.
"""

HOW_MANY_RESULTS_ARE_WORTH_SAYING = 1
"""How many of a search's results are said out loud: the first one.

A search returns ten pages and the strip shows one line. Saying all ten would put
nine of them straight in the bin, because only the newest line of each kind
survives the pace below.
"""


WhatOneCallIsDoing = Literal["searching", "found", "thinking"]
"""The three things a live call can be caught doing, as the stream's own words for them."""


class WhatItIsDoing(BaseModel):
    """One thing a live call is doing this second, on its way to the stream.

    Ours, not the library's, so nothing above this file meets a vendor type — and
    deliberately **not** the stream's own `activity` event: this file must not
    import `engine/events.py`, which reads the walk, which reads this file.

    It carries the question the call was put with, because that is the only thing
    this file knows about *which* claim is being worked on. Whoever built the
    callback decides what to do with it.
    """

    model_config = ConfigDict(frozen=True)

    kind: WhatOneCallIsDoing = Field(description="Which of the three this is.")
    text: str = Field(description="The model's own words, or the search tool's own, verbatim.")
    question: str = Field(
        description="The varying half of the request this call was put with. Identifies the call."
    )


class SayWhatItIsDoing(Protocol):
    """Whatever wants to be told what a call is doing while it is happening.

    Optional everywhere. The recorder, the cassette tests and every hand-written
    answerer pass nothing, which is what keeps their requests byte for byte what
    they have always been.

    It must never raise and must never block: it is called from the thread making
    the model call, between two chunks of the answer.
    """

    def __call__(self, doing: WhatItIsDoing) -> None:
        """Take one thing a call is doing. Return at once, whatever happens."""
        ...


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


# NOTE: **this class's docstring goes over the wire.** A shape's docstring is its
# description in the request body, so editing one changes the bytes the service
# sees, invalidates every cassette and changes the prompt's fingerprint. Found on
# 2026-09-20 by adding one paragraph to it and watching four recordings stop
# matching. Say things about a shape in a comment like this one, not in its
# docstring, unless the model is meant to read them.


def what_goes_out() -> dict[str, dict[str, Any]]:
    """Every description of an answer this program sends, as the library sends them.

    Here rather than in `prompt.py`, which needs them for the prompt's
    fingerprint: the envelope a proposal travels in is this file's business and
    nothing outside it names one. A caller asks what goes out and is told. That
    is what keeps `OneProposal`'s "nothing outside this file knows the envelope
    exists" true — `prompt.py` used to import it by name (2026-09-20).

    Returns:
        One entry per question this program asks, keyed by what it asks for.
    """
    return {
        "proposal": wire_schema(OneProposal),
        "starting_claim": wire_schema(StartingClaim),
    }


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


EFFORT_WHEN_RECORDING = ""
"""What the recorder sends when nothing says otherwise: nothing at all.

**Record rich** (Kent, G13, 2026-09-21). A recording is made once and played back
by everybody, so it is worth the service's own default — its best — and the
request is byte for byte what it was before anybody had an opinion.
"""

EFFORT_WHEN_LIVE = "medium"
"""What every run but a recording sends when nothing says otherwise.

**Run live fast** (Kent, G13, 2026-09-21). Somebody watching a map arrive is
waiting; the measured difference is 27 seconds a call against 79, for a map of
nine claims against twenty. `KATALYST_EFFORT` overrides this and the line above.

**And develop at the same effort** (Kent, 2026-09-21, later the same day): the
scorecard, `make eval`, asks for this too. It used to take the recorder's
effort, and one case took the best part of an hour — long enough that nobody
would run it while working on a prompt. So the rule is one rule: **only the
recorder sends nothing.** `make eval EFFORT=as-recorded` still scores the effort
the recordings are made at.
"""

HOW_LONG_TO_WAIT = 300.0
"""How long one request may take before it is given up on, in seconds.

The library's own default is ten minutes. Measured on 2026-09-17 and again on
2026-09-20, a whole question — every round of research it takes — runs about two
hundred seconds, and one round of it is well inside that. Ten minutes is
therefore not a timeout, it is a hang: three attempts of it is half an hour of
somebody watching a stream that will never move. Five minutes is comfortably
above anything measured and bounds a whole question, retries and all, at fifteen.
"""

HOW_OFTEN_TO_TRY_AGAIN = 2
"""How many times the library tries a failed request again by itself.

The library's own default, written down rather than inherited. It retries 408,
409, 429, every 5xx and every connection failure, with a wait between — which is
exactly the set of failures that go away on their own, and exactly the set this
program has no better answer to. A failed request is not billed, so trying again
is free; what it costs is time, which the figure above bounds.
"""


class TheModelDidNotAnswer(Exception):
    """The service could not be reached, or would not answer, after the library gave up.

    The vendor's own exception classes stop here, as `AnswerWeCouldNotRead` stops
    the library's validation errors here: nothing past this file knows whose
    complaint it was. Carries one plain sentence a person could read.
    """

    def __init__(self, why: str) -> None:
        """Hold the plain sentence of what went wrong."""
        super().__init__(why)
        self.why = why


def _in_plain_words(failure: anthropic.APIError) -> str:
    """Say what went wrong with a call, in words a person reads.

    Never the exception's class, never a status code, never a stack trace: those
    belong in the server's own log. What a reader needs is whether to wait, to
    try a smaller run, or to tell somebody.

    Args:
        failure: Whatever the library raised.

    Returns:
        One plain sentence.
    """
    if isinstance(failure, anthropic.APITimeoutError):
        return "The model did not answer in time, twice over, so this question was given up on."
    if isinstance(failure, anthropic.APIConnectionError):
        return "The model could not be reached. The connection failed, twice over."
    if isinstance(failure, anthropic.RateLimitError):
        return "This run has asked too much of the model too quickly, and was turned away."
    if isinstance(failure, anthropic.APIStatusError) and failure.status_code >= 500:
        return "The model is busy and turned this question away, twice over."
    if isinstance(failure, anthropic.APIStatusError) and failure.status_code in (401, 403):
        return "The key this run was started with is not allowed to ask this model."
    if isinstance(failure, anthropic.APIStatusError) and failure.status_code == 402:
        return "This account cannot pay for another question."
    return "The model would not answer this question, and did not say why in words we can pass on."


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

    effort_used: str
    """Which effort this answerer asks with, as the plain word a receipt shows."""

    def watching(self, spent: Receipt, cap: float) -> None:
        """Say what the run has spent and what it may spend, before the next question.

        Called before every question. An answerer that cannot go over a budget —
        every fake in the tests — may do nothing with it.
        """
        ...

    def starting_claim(self, question: str, *, may_search: bool = True) -> Said:
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

    def __init__(
        self,
        client: anthropic.Anthropic,
        *,
        model: str | None = None,
        effort: str | None = None,
        on_activity: SayWhatItIsDoing | None = None,
    ) -> None:
        """Wrap a client.

        Args:
            client: The vendor's client, already built and already holding
                whatever credentials it needs.
            model: Which model to ask. The one the settings name when not said.
            effort: How hard it should try. The one the settings name when not
                said, and nothing at all when neither says — which leaves the
                service's own default and puts no field in the request.
            on_activity: Somewhere to say what each call is doing while it is
                doing it. **Nothing at all is the default, and it is what the
                recorder and every recorded exchange use**: with nothing here the
                request is byte for byte the one this program has always sent.
                Given one, the call is streamed and asks for summarised thinking,
                which is a live-only difference (record 0027).
        """
        self._client = client
        self._on_activity = on_activity
        settings = get_settings()
        self._model = model or settings.KATALYST_MODEL
        chosen: Any = effort if effort is not None else settings.KATALYST_EFFORT
        # Pinned for the whole run and never varied between calls: changing it
        # mid-run would throw away the remembered prefix the run is reading back
        # at a tenth of the price. Left empty it is not sent at all, so the
        # request is byte for byte what it was before anybody had an opinion.
        self._trying: OutputConfigParam | Omit = (
            OutputConfigParam(effort=chosen) if chosen else omit
        )
        self.effort_used = str(chosen) if chosen else WHAT_THE_SERVICE_DEFAULTS_TO
        self._spent = nothing_spent_yet(self._model)
        self._cap = float("inf")

    def watching(self, spent: Receipt, cap: float) -> None:
        """Take note of what the run has spent and what it may spend.

        Args:
            spent: What the run had spent before this question was put.
            cap: What the whole run may spend, in dollars.
        """
        self._spent = spent
        self._cap = cap

    def starting_claim(self, question: str, *, may_search: bool = True) -> Said:
        """Ask for one typed sentence, written as a claim anybody could settle.

        **Searching is allowed here**, which it was not at first: how often this
        kind of thing has happened before is exactly what the web is for, and
        this is the claim every number below it hangs off.

        Args:
            question: The varying half of the request, from `prompt.py`.
            may_search: Whether this run still has searches left.

        Returns:
            The answer, in our own words.
        """
        return self._ask(question, StartingClaim, may_search=may_search)

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

        The shape goes on `output_format`, which is what `messages.parse` takes.
        The reference bundle's note that `output_format` is deprecated is about
        `messages.create`, where the same thing is spelled `output_config.format`;
        `messages.parse` merges the two itself. **Do not "fix" this to the other
        spelling** — record 0006 names this call.

        **Two ways of putting the same question, and the difference is one
        argument.** With nowhere to say what it is doing, the question is put the
        way it has always been put and the whole answer arrives at the end. With
        somewhere to say it, the same question is put through the streaming
        helper — which takes the same `output_format` and hands back the same
        validated answer — and every block is read out loud as it lands. Nothing
        else about the request moves except the summarised thinking that makes
        the third line possible, and neither reaches the recorder.

        Args:
            question: The varying half of the request.
            shape: What an answer must fit — a starting claim, or a proposal.
            may_search: Whether the search tool may be used on this call.

        Returns:
            The answer, in our own words.

        Raises:
            AnswerWeCouldNotRead: If what came back did not fit the shape.
            TheModelDidNotAnswer: If the service could not be reached, or would
                not answer, after the library had tried again as often as it may.
        """
        conversation: list[MessageParam] = [{"role": "user", "content": question}]
        rounds: list[ParsedMessage[Any]] = []
        started = time.monotonic()
        for _ in range(ROUNDS_OF_RESEARCH):
            try:
                answer = (
                    self._streamed(conversation, shape, question, may_search=may_search)
                    if self._on_activity is not None
                    else self._client.messages.parse(
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
                        output_config=self._trying,
                    )
                )
            except ValidationError as did_not_fit:
                raise AnswerWeCouldNotRead(_did_not_fit_the_shape(did_not_fit)) from did_not_fit
            except anthropic.APIError as did_not_answer:
                # Everything the library raises stops here. The pipeline folds a
                # sentence, never an exception class (Kent, 2026-09-20).
                raise TheModelDidNotAnswer(_in_plain_words(did_not_answer)) from did_not_answer
            rounds.append(answer)
            if answer.stop_reason != "pause_turn":
                return what_it_said(rounds, seconds=time.monotonic() - started)
            if self._out_of_money(rounds):
                # The rounds already paid for are kept and read as they stand.
                return what_it_said(rounds, seconds=time.monotonic() - started)
            # Part finished. The service picks up from its own turn, and adding a
            # "carry on" of our own would only confuse it.
            conversation = [*conversation, {"role": "assistant", "content": answer.content}]
        return what_it_said(rounds, seconds=time.monotonic() - started)

    def _streamed(
        self,
        conversation: list[MessageParam],
        shape: Any,
        question: str,
        *,
        may_search: bool,
    ) -> ParsedMessage[Any]:
        """Put one round of a question, reading it out loud as the answer arrives.

        The same request as the one above with two live-only differences: it is
        streamed, and it asks for the thinking to be summarised so there is
        something to read out. The shape still goes on `output_format` and the
        answer that comes back is the same validated shape, which is what lets
        one translation serve both ways of asking (`sdk-upgrade.md` in the
        `claude-api` reference bundle, read 2026-09-22).

        Args:
            conversation: The turns so far, which is one turn on the first round
                and grows by the service's own turn on every hand-back.
            shape: What an answer must fit.
            question: The varying half of the request, passed on unchanged so
                whoever is listening can tell one call from another.
            may_search: Whether the search tool may be used on this call.

        Returns:
            The whole answer, once it has finished arriving.
        """
        with self._client.messages.stream(
            model=self._model,
            max_tokens=ROOM_FOR_AN_ANSWER,
            thinking=THINKING_OUT_LOUD,
            system=STANDING_BLOCK,
            tools=[SEARCH_TOOL],
            tool_choice=MAY_SEARCH if may_search else MAY_NOT_SEARCH,
            messages=conversation,
            output_format=shape,
            output_config=self._trying,
        ) as arriving:
            said = ""
            for happening in arriving:
                said = self._say(happening, question, said)
            return arriving.get_final_message()

    def _say(self, happening: Any, question: str, said: str) -> str:
        """Hand on what one piece of an arriving answer is doing, if anything.

        The reading itself is `what_it_is_doing`, which is pure. This is only the
        part that talks to whoever is listening — and it never lets either half
        stop the call.

        Args:
            happening: One thing the streaming helper handed over.
            question: The varying half of the request this call was put with.
            said: The last line of thinking this call has already said, so the
                same sentence is not said twice.

        Returns:
            The last line of thinking said so far, for the next piece to compare
            against.
        """
        try:
            reading = what_it_is_doing(happening, said)
        except Exception:
            # Saying what a call is doing may never stop the call. The run goes
            # on and the screen simply says one thing less.
            logging.getLogger(__name__).exception("reading what a call was doing went wrong")
            return said
        if reading is None:
            return said
        kind, text = reading
        self._tell(kind, text, question)
        return text if kind == "thinking" else said

    def _tell(self, kind: WhatOneCallIsDoing, text: str, question: str) -> None:
        """Hand one line to whoever is listening, and never let it fail the call.

        Args:
            kind: Which of the three this is.
            text: The words themselves, already the model's or the tool's own.
            question: The varying half of the request this call was put with.
        """
        listening = self._on_activity
        if listening is None:  # pragma: no cover - only reached if called wrongly
            return
        try:
            listening(WhatItIsDoing(kind=kind, text=text, question=question))
        except Exception:
            logging.getLogger(__name__).exception("saying what a call was doing went wrong")

    def _out_of_money(self, rounds: Sequence[ParsedMessage[Any]]) -> bool:
        """Say whether the rounds so far have taken the run past what it may spend.

        Priced through the same receipt the run itself is priced through, so the
        figure that stops a question mid-flight and the figure on the bill are
        worked out by one piece of code.

        Args:
            rounds: Every round trip this question has made so far.

        Returns:
            True once this question's rounds have carried the run over its cap.
        """
        return over_the_cap(fold(self._spent, what_it_said(rounds)), self._cap)


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


def what_it_is_doing(happening: Any, said: str) -> tuple[WhatOneCallIsDoing, str] | None:
    """Read one piece of an arriving answer and say what it is doing, if anything.

    The other half of the translation, and pure for the same reason `what_it_said`
    is: a test hands it the library's own blocks and they go through exactly what
    a real call's go through.

    **A piece this does not recognise says nothing at all.** Nothing above cares
    whether a line was said, so the safe answer to anything unexpected is silence
    rather than a guess. That matters more here than usual: the blocks themselves
    are documented but the shape they arrive in has never met the service from
    this program, so the reading is written to shrug.

    Three things are worth saying, and each is somebody else's words:

    * a search the model just issued — the query it wrote, verbatim;
    * one thing that search returned — the title the tool gave, with its host;
    * the model's own summarised thinking — its most recent whole sentence.

    Args:
        happening: One thing the streaming helper handed over.
        said: The last line of thinking this call has already said, so that the
            same sentence is not said twice while it is still the newest one.

    Returns:
        Which of the three and the words, or nothing at all.
    """
    if happening.type == "thinking":
        return _a_new_thought(happening.snapshot, said, ended=False)
    if happening.type != "content_block_stop":
        return None
    block = happening.content_block
    if block.type == "thinking":
        return _a_new_thought(block.thinking, said, ended=True)
    if block.type == "server_tool_use" and block.name == "web_search":
        asked = block.input.get("query")
        if isinstance(asked, str) and asked.strip():
            return ("searching", asked.strip())
        return None
    if block.type == "web_search_tool_result" and isinstance(block.content, list):
        # A search that failed comes back as one error object where a list of
        # results would be, which reads here as nothing found — the same reading
        # `_pages_the_search_returned` gives it.
        for result in block.content[:HOW_MANY_RESULTS_ARE_WORTH_SAYING]:
            if result.type == "web_search_result":
                return ("found", _one_page(result.title, result.url))
    return None


def _a_new_thought(so_far: str, said: str, *, ended: bool) -> tuple[WhatOneCallIsDoing, str] | None:
    """The model's newest whole sentence of thinking, when there is a new one.

    Args:
        so_far: The summarised thinking of this block as it stands.
        said: The last line of thinking already said on this call.
        ended: True once the block has finished, which is when a sentence that
            never got its full stop is worth saying anyway.

    Returns:
        The line to say, or nothing at all.
    """
    line = _a_line_of_thinking(so_far, ended=ended)
    return ("thinking", line) if line and line != said else None


AS_MUCH_THINKING_AS_FITS = 160
"""How many characters of the model's thinking one line may carry.

One line of a strip at the foot of a map. A sentence longer than this is shown
from its end rather than its start, because the end is the part that just
arrived. The figure is the shapes sheet's, agreed with the browser before either
half was built (record 0027).
"""

ENDS_A_SENTENCE = (".", "!", "?")
"""What the end of a sentence looks like, for the purpose of showing the last whole one."""


def _a_line_of_thinking(so_far: str, *, ended: bool) -> str:
    """Pick the one line of the model's thinking worth showing right now.

    The most recent **whole** sentence, so nothing is shown half written. Until
    the first full stop there is nothing whole to show and this says nothing —
    unless the thinking has finished without one, at which point its tail is the
    truest thing there is.

    Args:
        so_far: The summarised thinking as it stands.
        ended: True once no more of it is coming.

    Returns:
        The line, or nothing at all when there is nothing whole to say.
    """
    text = so_far.strip()
    if not text:
        return ""
    ends_at = max(text.rfind(one) for one in ENDS_A_SENTENCE)
    if ends_at < 0:
        return _the_last_of_it(text) if ended else ""
    before = text[:ends_at]
    starts_after = max(before.rfind(one) for one in ENDS_A_SENTENCE)
    return _the_last_of_it(text[starts_after + 1 : ends_at + 1])


def _the_last_of_it(text: str) -> str:
    """Cut a run of words down to what one line holds, keeping the end of it.

    Cut at a space, so no word is shown in halves.

    Args:
        text: Whatever the model wrote.

    Returns:
        The last words of it, at most one line's worth.
    """
    trimmed = text.strip()
    if len(trimmed) <= AS_MUCH_THINKING_AS_FITS:
        return trimmed
    last = trimmed[-AS_MUCH_THINKING_AS_FITS:]
    at_a_space = last.find(" ")
    return (last[at_a_space + 1 :] if at_a_space >= 0 else last).strip()


def _one_page(title: str, url: str) -> str:
    """Name one thing a search returned: its own title, and where it came from.

    Both are the search tool's, neither is ours. The host is worth saying because
    a title alone does not say whether it came from a wire service or a forum.

    Args:
        title: The page's title, as the tool gave it.
        url: The page's address, as the tool gave it.

    Returns:
        The title, with the host after it when the address has one.
    """
    host = (urlsplit(url).hostname or "").removeprefix("www.")
    return f"{title} · {host}" if host else title


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


def a_stand_in_answerer() -> Any | None:
    """Build the stand-in `KATALYST_ANSWERER` names, when it names one.

    **Only the recorder ever asks for this**, and it asks by name. It used to sit
    inside `live_answerer`, which the stream route calls — so a deployed server
    with the setting on would have answered every reader from a list in a test
    file, unlabelled, and the map would have looked generated. That was a veto
    (Kent, 2026-09-20), and this is how it is not one: the seam is reachable from
    one program, which refuses to call a run answered this way a recording.

    Returns:
        The stand-in, or nothing at all when the setting is empty — which it is
        everywhere but a test that starts the recorder as a program.
    """
    named = get_settings().KATALYST_ANSWERER
    return _named(named) if named else None


def _named(path: str) -> Any:
    """Build whatever `module:name` names, by calling it.

    Args:
        path: An import path of the form `module:name`, naming something that
            can be called with no arguments and hands back an answerer.

    Returns:
        Whatever that factory built.

    Raises:
        ValueError: If the path does not name a module and something in it.
    """
    module, _, name = path.partition(":")
    if not module or not name:
        raise ValueError(
            f"KATALYST_ANSWERER is {path!r}, which does not name anything. It wants "
            "'module:name', where the name can be called with no arguments."
        )
    return getattr(import_module(module), name)()


def live_answerer(
    *,
    effort: str | None = None,
    model: str | None = None,
    when_nothing_is_said: str = EFFORT_WHEN_RECORDING,
    on_activity: SayWhatItIsDoing | None = None,
) -> Model | None:
    """Build the live answerer, or say plainly that there is no key for one.

    The one function that knows whether this program can call a model at all.
    Nothing here raises and nothing here prints: a missing key is an ordinary fact
    about how the program was started, and the screen says so rather than failing.

    Args:
        effort: How hard the model should try on this run, when a measurement run
            has said. The settings decide when it has not.
        model: Which model to ask, when a measurement run has said. The settings
            decide when it has not.
        when_nothing_is_said: The effort to use when neither the caller nor the
            settings name one. One setting, two pinned defaults: the recorder
            sends nothing and takes the service's own; a live run and the
            scorecard ask for `medium` (Kent, G13 and its extension,
            2026-09-21).
        on_activity: Somewhere to say what each call is doing while it is doing
            it, or nothing at all. **The recorder passes nothing**, which is what
            keeps its request byte for byte the one every recording was made
            with; the stream route passes one, which is a live-only difference
            (record 0027, R34's precedent).

    Returns:
        A live answerer, or nothing at all when no key is configured.
    """
    key = get_settings().ANTHROPIC_API_KEY
    if not key:
        return None
    return Model(
        anthropic.Anthropic(
            api_key=key,
            timeout=HOW_LONG_TO_WAIT,
            max_retries=HOW_OFTEN_TO_TRY_AGAIN,
        ),
        effort=effort or get_settings().KATALYST_EFFORT or when_nothing_is_said,
        model=model,
        on_activity=on_activity,
    )
