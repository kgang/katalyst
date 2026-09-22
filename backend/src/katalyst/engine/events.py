"""The eight things a generation is made of, one that is only ever live, and their framing.

One request builds a whole map, and this is what comes back along it while that
happens. **The stream is the loading state**: a generation takes minutes and
returns one whole proposal every few seconds, so there is no honest way to show
it as a single answer that arrives at the end — and a spinner followed by a
finished map is a veto condition rather than a design choice.

Eight names that are written down
---------------------------------
The map starts · a proposal landed · a proposal was refused · the likelihoods ·
whether the destination was reached · what it cost · why it stopped · what broke.

**These eight are the generation.** Each one is a decision somebody took — the
model, the rules, the walk — and a recording is exactly these, line for line.

Two things that close a claim make **no event of their own**: the model saying
this part of the story is finished, and a claim's third failure in a row. Neither
adds anything to the map, and the browser does not need to be told — it reads the
next growth event's `frontier`, which no longer names that claim, and on
`beliefs_propagated` every skeleton goes at once because the frontier is empty by
definition. An event whose only job is to say that nothing happened is an event
somebody will one day draw.

And one that never is
---------------------
`activity` says what a model call is doing **right now** — the search it just
issued, one thing that search returned, the sentence it is thinking. It is not a
decision and it changes nothing, so it is not part of the generation: it is sent
on a live run and **never written to a recording, a transcript or a kept run,
never replayed, never invented by a replay, never billed and never counted by
`at`**. That is why it is not in `NAMES` and not in `Event` — the eight are what
a recording holds, and the ninth is what a live run additionally says out loud
(record 0027, Kent's R44 and R47, 2026-09-22; it amends record 0023's *no ninth
event*).

Four of these shapes are not defined here, on purpose
------------------------------------------------------
`Verdict` is the Verify door's own answer and `Done.reason` is the walk's own
list of reasons; both are imported rather than restated, because a shape written
out twice is two shapes that eventually disagree. `Proposition`, `Link`,
`Violation` and `World` are the rules layer's, carried whole, so what the browser
draws is what `domain/` computed.

What this file must never do
----------------------------
- Never gain another event for something a client can already read off the eight.
- Never carry a fact that is already on another event. `no_path` lives on the
  verdict; the mode, the recording's date and the prompt's fingerprint live on
  the receipt. Two places to read one fact eventually disagree.
- Never write a stack trace, an exception's name or an identifier into `Failed`.
  It is interface text.
- Never put `activity` in `NAMES`, in `BY_NAME` or in `Event`. Those three are
  what a recording is read and written through, and the moment `activity` is in
  one of them a recording can hold one.
- Never emit a heartbeat, a comment line or anything else that is not one of the
  eight or `activity`. A recording is the eight line for line, and a line
  carrying no event is a line somebody eventually parses as one.
"""

import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Link, Proposition, PropositionId, Violation, World
from katalyst.engine.grow import StoppingReason
from katalyst.engine.outcome import (
    WHAT_THE_SERVICE_DEFAULTS_TO,
    Accepted,
    Outcome,
    Refused,
)
from katalyst.engine.verify import Verdict


class GenerationStarted(BaseModel):
    """The generation has an identifier and a seed. Nothing has been proposed yet.

    It goes out before the first model call has returned, which is what the first
    screen draws its reserved rectangle from: the first thing a person sees is the
    map beginning, not a word of the model's.
    """

    model_config = ConfigDict(frozen=True)

    generation_id: str = Field(description="Minted by `engine/ids.py`, never by the model.")
    seed: int = Field(
        description=(
            "The one number the rules layer will work every likelihood through with. "
            "Always a number here, even when the request left it out — the server "
            "mints one and says which, so the run is reproducible from its first event."
        )
    )
    hypothesis: str = Field(description="The sentence the person typed, unaltered.")
    target: str | None = Field(
        default=None, description="The Verify door's destination, in their own words."
    )


class ProposalAccepted(BaseModel):
    """One proposal passed the rules. The map is now bigger by this much.

    Two different proposals arrive through it. One that adds a claim carries the
    claim and its one incoming arrow; one that only joins two claims already on
    the map carries no claim at all and one new arrow. From the browser's side
    both are the same fact — the map got bigger — and splitting them would be a
    ninth event whose only difference is a field that is already optional.

    The claim a person's own sentence became arrives this way too, with no arrows,
    because it has no cause. Turning a sentence into something checkable is
    exactly the step a reader wants to audit.
    """

    model_config = ConfigDict(frozen=True)

    at: int = Field(
        description=(
            "Where this sits in the transcript, counting from 0. It rises by one on "
            "every accepted and every refused proposal, because both are things that "
            "were proposed. It is not a time."
        )
    )
    proposition: Proposition | None = Field(
        default=None,
        description="The new claim, with the identifier minted here. Absent for an arrow alone.",
    )
    links: tuple[Link, ...] = Field(
        default=(), description="Its incoming arrows, with the identifiers minted here."
    )
    frontier: tuple[PropositionId, ...] = Field(
        default=(), description="The claims still open to expand, once this had been folded in."
    )


class ProposalRejected(BaseModel):
    """One proposal was refused. Every reason at once, never the first one only.

    It is an event, not an error: the answer stays 200 and the stream carries on.
    Watching the rules refuse the model is half of what this product is for, and a
    generation that hides its misses has deleted that half.
    """

    model_config = ConfigDict(frozen=True)

    at: int = Field(description="The same transcript counter the accepted proposals use.")
    claim_in_words: str = Field(
        description=(
            "What the model wrote, or the plain sentence of what happened when it "
            "wrote nothing we could read. Never minted, never drawn as a tile."
        )
    )
    violations: tuple[Violation, ...] = Field(
        default=(),
        description=(
            "Every reason the map's own rules gave, in their words. Empty when no map "
            "was proposed at all — when the model declined, or its answer did not fit."
        ),
    )
    frontier: tuple[PropositionId, ...] = Field(
        default=(),
        description=(
            "The claims still open. **Both** growth events carry it, so a claim closed "
            "by its third failure loses its reserved rectangle at once rather than "
            "leaving one standing where nothing will arrive."
        ),
    )


class BeliefsPropagated(BaseModel):
    """Every likelihood, worked through the finished map. Exactly once, at the end.

    Never during the growing. A chip that changes four times as its causes arrive
    has shown four numbers nobody computed, and only the last of them is the
    engine's answer.
    """

    model_config = ConfigDict(frozen=True)

    world: World = Field(description="The whole thing, straight from the rules layer.")


class Receipt(BaseModel):
    """What this run cost. The second-to-last event of every stream.

    Second-to-last in both endings — before the run finished and before it broke.
    A run that broke after ten calls still cost ten calls, and a run that broke
    before its first emits a receipt of zeroes, which is also true.

    It is not the same shape as the running total `engine/receipt.py` keeps. That
    one counts what the bill is made of, cache writes included; this one is what a
    person is shown, and it carries the three facts about the run that live here
    and nowhere else: whether it was live or played back, the day the recording
    was made, and the fingerprint of the prompt behind it.
    """

    model_config = ConfigDict(frozen=True)

    model: str = Field(description="Which model wrote this map.")
    calls: int = Field(description="How many round trips the run made.")
    input_tokens: int = Field(description="Tokens of question read fresh.")
    output_tokens: int = Field(description="Tokens of answer written, thinking included.")
    cache_read_tokens: int = Field(
        description=(
            "Tokens the service recognised from an earlier call. A run where this "
            "stays at nothing is a bug in how the request is put together."
        )
    )
    searches: int = Field(
        description=(
            "Web searches this run made. Billed apart from tokens, so the dollars "
            "below cannot be worked out again without it."
        )
    )
    dollars: float = Field(description="What all of that came to, at the shipped price table.")
    seconds: float = Field(description="How long the run took, wall clock.")
    mode: Literal["live", "replay"] = Field(
        description="Whether this run called a model or played a recording back."
    )
    recording_date: date | None = Field(
        default=None, description="The day the recording was made. Nothing at all when live."
    )
    effort: str = Field(
        default=WHAT_THE_SERVICE_DEFAULTS_TO,
        description=(
            "How hard the model was asked to try, as a plain word — `default` "
            "when nothing was sent and the service's own applied, otherwise "
            "`low`, `medium`, `high`, `xhigh` or `max`. One setting with two "
            "pinned defaults behind it: a recording is made rich and a live run "
            "is made fast, and a reader of a map is entitled to know which this "
            "was (Kent, G13, 2026-09-21)."
        ),
    )
    prompt_hash: str = Field(description="The fingerprint of the prompt this run was made against.")


class Done(BaseModel):
    """The generation finished. One reason, and the size of what was built."""

    model_config = ConfigDict(frozen=True)

    reason: StoppingReason = Field(
        description=(
            "Why the generation stopped. One reason, picked by the walk's own rule: it "
            "names what closed the last claim that was still open, with the money "
            "running out and a map that ends nowhere as the two overrides above it."
        )
    )
    claims: int = Field(description="How many claims the map ended up with.")
    links: int = Field(description="How many arrows.")
    rejected: int = Field(description="How many proposals were refused along the way.")


class Failed(BaseModel):
    """Something on our side broke. One plain sentence, never a stack trace.

    Stopping because the money ran out is **not** this: that is a decision, and it
    arrives as `done` with its own reason. This is for the things nobody chose.
    """

    model_config = ConfigDict(frozen=True)

    message: str = Field(
        description=(
            "One plain sentence a person can act on. Never an exception's name, never "
            "an identifier, never a stack trace — those go in the server's own log."
        )
    )


class Activity(BaseModel):
    """What one model call is doing this second. Live only, and never written down.

    The one thing on the wire that is **not** a decision. Nothing on the map
    changes because of it, nothing is spent because of it, and a run that never
    sent one is the same run. It exists because a model call takes minutes and a
    person watching an empty screen has no way to tell a working program from a
    stopped one (Kent, 2026-09-22).

    Every word in `text` is the model's own or the search tool's own, verbatim.
    Nothing here is composed by us, and nothing here is an estimate of progress:
    there is no percentage, no count of what is left and no guess at how long.

    What it must never do
    ---------------------
    - Never be written to a recording, a transcript or a kept run.
    - Never be sent by a replay, and never be invented by one.
    - Never be billed, and never counted by the `at` counter.
    - Never be folded into the map, and never drawn on it.
    - Never be the reason a run fails. Whatever goes wrong raising one is
      swallowed and logged, and the run carries on.
    """

    model_config = ConfigDict(frozen=True)

    about: PropositionId | None = Field(
        default=None,
        description=(
            "The open claim this call is working on — one of the identifiers the "
            "latest `frontier` names — or nothing at all when the call is not "
            "about one claim, which is what the opening call is."
        ),
    )
    kind: Literal["searching", "found", "thinking"] = Field(
        description=(
            "Which of the three this is. `searching`: the model just issued a web "
            "search. `found`: one thing that search returned. `thinking`: the "
            "model's own summarised thinking."
        )
    )
    text: str = Field(
        description=(
            "The words themselves, never paraphrased by us. For `searching`, the "
            "query the model wrote. For `found`, the title of one page the search "
            "returned, followed by ` · <host>` when a host is known. For "
            "`thinking`, the most recent whole sentence of the model's own "
            "summarised thinking."
        )
    )


ACTIVITY = "activity"
"""The name the ninth travels under.

**Deliberately not in `NAMES`.** That table is the eight a recording is written
and read through, and a name in it is a name a recording may hold.
"""


Event = (
    GenerationStarted
    | ProposalAccepted
    | ProposalRejected
    | BeliefsPropagated
    | Verdict
    | Receipt
    | Done
    | Failed
)
"""Any one of the eight. The wire's `event:` line carries the name; `data:` carries the payload.

`Activity` is **not** one of them, on purpose: this is the type a recording, a
transcript and a replay are written in terms of.
"""

OnTheWire = Event | Activity
"""Anything a live stream may write out: the eight, plus the one that is never recorded."""

NAMES: dict[type[Event], str] = {
    GenerationStarted: "generation_started",
    ProposalAccepted: "proposal_accepted",
    ProposalRejected: "proposal_rejected",
    BeliefsPropagated: "beliefs_propagated",
    Verdict: "verdict",
    Receipt: "receipt",
    Done: "done",
    Failed: "failed",
}
"""Every event and the name it travels under. **The one place the eight are listed.**

Written as a table rather than as a field on each shape, because one of the eight
— the Verify door's answer — is defined where that door lives, and a shape should
not grow a field in order to be streamable.
"""

BY_NAME: dict[str, type[Event]] = {said: shape for shape, said in NAMES.items()}
"""The same table read the other way, for whatever reads a stream back."""


def framed(event: OnTheWire) -> str:
    """Write one event the way it goes on the wire: two lines and a blank one.

    The payload is **one line of JSON** — never pretty-printed, never wrapped — so
    a reader never has to join two `data:` lines back together and a recording can
    be one event per line.

    Args:
        event: The event to write. One of the eight, or the live-only ninth.

    Returns:
        The `event:` line, the `data:` line and the blank line that ends them.
    """
    return f"event: {name_of(event)}\ndata: {payload_of(event)}\n\n"


def name_of(event: OnTheWire) -> str:
    """Say which name this event travels under: one of the eight, or `activity`."""
    if isinstance(event, Activity):
        return ACTIVITY
    return NAMES[type(event)]


def payload_of(event: OnTheWire) -> str:
    """Write one event's payload as the single line of JSON the wire carries.

    Sorted and tightly spaced, so the same event is always the same bytes and a
    recording can be compared with a live run without either being re-read.
    """
    return json.dumps(json.loads(event.model_dump_json()), separators=(",", ":"), sort_keys=True)


def growth_event(outcome: Outcome, at: int) -> ProposalAccepted | ProposalRejected:
    """Turn one folded outcome into the event that says what happened to it.

    The one place an outcome becomes something on the wire, so the stream and the
    recorder cannot drift into saying it two ways.

    Args:
        outcome: What happened to one proposal, and what it cost.
        at: Where it sits in the transcript, counting from 0.

    Returns:
        The growth event. A model that had nothing more to say makes none of
        these, and the caller checks that before asking.
    """
    result = outcome.result
    if isinstance(result, Accepted):
        return ProposalAccepted(
            at=at, proposition=result.proposition, links=result.links, frontier=outcome.frontier
        )
    if not isinstance(result, Refused):  # pragma: no cover - `makes_an_event` decided this
        raise TypeError(
            "growth_event was handed an answer that makes no event. `makes_an_event` "
            "says which do, and the caller asks it first."
        )
    return ProposalRejected(
        at=at,
        claim_in_words=result.claim_in_words,
        violations=result.violations,
        frontier=outcome.frontier,
    )
