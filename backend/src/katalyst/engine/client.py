"""The one place this program talks to a model over the network.

Everything else in the pipeline is arithmetic and rules over values that are
already in hand. This file is the seam: on one side a question written as plain
text, on the other an answer already checked against the shape we asked for. It
exists so that every rule the pipeline enforces — accept and mint, refuse with
every reason, ask again without saying why, stop at a cap — can be shown to work
against answers written out by hand, in the same types the service returns, with
no key, no network and no money.

Why a seam and not a function
-----------------------------
`expand.py` takes an *answerer* as an argument rather than reaching for a client
itself. Three things follow, and each of them is the point:

* The tests are fast and exact. A test that wants a refusal writes a refusal; it
  does not hope one turns up in a recording.
* Nothing below this line can start calling a model by accident. There is one
  import of the vendor's library in the whole program, and it is here.
* Playing back a recorded run plugs in where the live answerer does, with no
  second path through the pipeline.

The search tool, and the one place it is declared
--------------------------------------------------
The tool, its version and its per-call limit were re-read from the `claude-api`
reference bundle on 2026-09-17. Three things about it are decisions rather than
defaults, and each has its reason beside it below: only one search per call,
nothing declared alongside it, and no fetching of our own.

Once a run has spent its whole budget of searches, later calls are made with **no
search tool declared at all**, so there is nothing to half-use and nothing to
explain away. That costs one thing worth knowing about: the tools are written out
at the very front of a request, so the call where the tool disappears cannot
recognise the prefix it has been reading back cheaply all run, and is charged in
full once before the new prefix settles. It is one call in a run of dozens, and
it buys a rule a reader can check by looking at the request.

What this file must never do
----------------------------
- Never decide anything about a map. It asks and it hands back the answer.
- Never read an environment variable itself; `katalyst.settings` is the one place
  that does.
- Never hide a refusal or a part-finished answer. Both are handed straight back
  for the pipeline to report.
- Never declare a place to run code beside the search tool, and never declare a
  tool that fetches a page of our choosing.
"""

from collections.abc import Sequence
from typing import Any, Protocol

import anthropic
from anthropic.types import MessageParam, ParsedMessage, TextBlockParam

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
"""

TIMES_A_PART_FINISHED_ANSWER_IS_SENT_BACK = 3
"""How often a part-finished answer is handed straight back to be continued.

A question that uses the search tool can come back with the search half done and
no answer yet. The service expects exactly one thing in reply: the same
conversation with its own part-finished turn on the end, and no new instruction —
it picks up where it left off. This is how many times we will do that before
treating the answer as one we never got.
"""

SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": SEARCHES_INSIDE_ONE_CALL,
}
"""The search tool, as it is declared.

The name and the version are the ones the `claude-api` reference bundle gives,
read on 2026-09-17. This version filters what it finds before the results reach
the model, which is why nothing here declares a place to run code alongside it: a
second one would only confuse matters. Nothing declares a tool that fetches a
page either — a document the search never offered is a document we went looking
for to support a conclusion we already had.

A search that fails does not raise. The answer comes back normally and the
result block holds one error instead of a list of results, which is read as
nothing found.
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


class Answerer(Protocol):
    """Whatever the pipeline asks its questions of.

    Two questions, because a run asks two kinds. Before anything is expanded, a
    sentence a person typed is turned into a claim anybody could settle. After
    that, every call asks for the one next piece of the map.

    Both hand back **every round trip the question took**, oldest first, because
    a question that searched can come back part-finished and be sent straight
    back. The last one holds the answer; all of them are on the bill, and a bill
    that quietly missed one would make the spending cap a lie.
    """

    def starting_claim(self, question: str) -> Sequence[ParsedMessage[StartingClaim]]:
        """Ask for one typed sentence, written as a claim anybody could settle."""
        ...

    def proposal(self, question: str, *, may_search: bool) -> Sequence[ParsedMessage[Proposal]]:
        """Ask for the one next piece of the map, with or without the search tool."""
        ...


class Model:
    """The live answerer: the vendor's own client, and nothing added to it.

    Built around an already-made client so that a caller can hand in one with a
    different patience or a different address without this file growing a second
    way to be configured.

    This class must never look at what came back. It asks, it sends a
    part-finished answer back to be continued, and it hands over everything it
    received. Reading an answer — accepting it, refusing it, saying it made no
    sense — belongs to `expand.py`, which can be tested without spending a penny.
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

    def starting_claim(self, question: str) -> Sequence[ParsedMessage[StartingClaim]]:
        """Ask for one typed sentence, written as a claim anybody could settle.

        No search tool on this call. The question is what the person meant, and
        the web has nothing to say about that.

        Args:
            question: The varying half of the request, from `prompt.py`.

        Returns:
            Every round trip the question took, oldest first.
        """
        return self._ask(question, StartingClaim, may_search=False)

    def proposal(self, question: str, *, may_search: bool) -> Sequence[ParsedMessage[Proposal]]:
        """Ask for the one next piece of the map.

        Args:
            question: The varying half of the request, from `prompt.py`.
            may_search: Whether this run still has searches left. False declares
                no search tool at all, so there is nothing to half-use.

        Returns:
            Every round trip the question took, oldest first.
        """
        return self._ask(question, Proposal, may_search=may_search)

    def _ask(self, question: str, shape: Any, *, may_search: bool) -> Sequence[ParsedMessage[Any]]:
        """Put one question, sending a part-finished answer back until it finishes.

        The shape is handed to the client library, which turns it into the
        description of what an answer must look like, sends it with the request,
        and checks what comes back against it before returning. An answer that
        does not fit raises, and `expand.py` catches that and reports it as an
        answer we could not read.

        Args:
            question: The varying half of the request.
            shape: What an answer must fit — a starting claim, or a proposal.
            may_search: Whether the search tool is declared at all.

        Returns:
            Every round trip, oldest first. The last one holds the answer.
        """
        conversation: list[MessageParam] = [{"role": "user", "content": question}]
        rounds: list[ParsedMessage[Any]] = []
        for _ in range(TIMES_A_PART_FINISHED_ANSWER_IS_SENT_BACK + 1):
            answer = self._client.messages.parse(
                model=self._model,
                max_tokens=ROOM_FOR_AN_ANSWER,
                # The model decides for itself how long to think. How hard it
                # tries is left at the service's own default, which is the
                # setting we want; naming it would add a knob that changes
                # nothing and a second place for two settings to disagree.
                thinking={"type": "adaptive"},
                system=STANDING_BLOCK,
                tools=[SEARCH_TOOL] if may_search else [],
                messages=conversation,
                output_format=shape,
            )
            rounds.append(answer)
            if answer.stop_reason != "pause_turn":
                return rounds
            # Part finished. The service picks up from its own turn, and adding a
            # "carry on" of our own would only confuse it.
            conversation = [*conversation, {"role": "assistant", "content": answer.content}]
        return rounds


def live_answerer() -> Model | None:
    """Build the live answerer, or say plainly that there is no key for one.

    The one function that knows whether this program can call a model at all.
    Nothing here raises and nothing here prints: a missing key is an ordinary
    fact about how the program was started, and the screen says so rather than
    failing.

    Returns:
        A live answerer, or nothing at all when no key is configured.
    """
    key = get_settings().ANTHROPIC_API_KEY
    if not key:
        return None
    return Model(anthropic.Anthropic(api_key=key))
