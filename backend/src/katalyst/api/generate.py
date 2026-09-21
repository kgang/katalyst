"""The three routes a generation is asked for, watched and read back through.

**The stream is the loading state.** A generation takes minutes and returns one
whole proposal every few seconds, so there is no honest way to show it as a
single answer that arrives at the end — and a spinner followed by a finished map
is a veto condition rather than a design choice. One request opens, and the map
arrives down it, claim by claim, with every refusal beside it.

Three routes and nothing else
------------------------------
`POST /api/generate` builds a map and writes the eight events out as they happen.
`POST /api/generate/insert` drafts one claim a person asked for — the single edit
that needs a model. `GET /api/generate/{id}/transcript` hands back the working of
a generation this process is still holding.

The same route serves a live run and a replay
----------------------------------------------
With a key it calls a model; with none it plays a committed recording back
through the same events, the same framing and the same canvas. The only
substitution anywhere is where the bytes came from. There is **no fallback
between them**: a live run that fails is a live run that failed and says so,
because showing somebody a recorded map labelled as an answer to their question
is worse than showing them nothing.

What this file must never do
----------------------------
- Never send a heartbeat, a comment line or anything that is not one of the eight
  events. A recording is this stream line for line, and a line carrying no event
  is a line somebody eventually parses as one.
- Never turn a refused proposal into an error. It is an event, the answer stays
  200, and the run carries on.
- Never keep calling a model for a client that has gone away.
- Never quietly reduce a request that asks for more than the ceiling allows.
- Never put a stack trace or an identifier in the sentence a person reads.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Generator
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from katalyst.domain import Belief, Branch, Graph, Insert, Violation, apply, validate
from katalyst.engine import events, replay
from katalyst.engine import worlds as engine
from katalyst.engine.client import Answerer, live_answerer
from katalyst.engine.events import (
    BeliefsPropagated,
    Done,
    Event,
    Failed,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
)
from katalyst.engine.expand import add_a_claim
from katalyst.engine.following import WENT_WRONG, Following, receipt_event
from katalyst.engine.grow import grow
from katalyst.engine.ids import BIGGEST_SEED, mint_id, mint_seed
from katalyst.engine.outcome import Caps, Outcome
from katalyst.engine.receipt import Receipt as Spent
from katalyst.engine.receipt import fold, nothing_spent_yet
from katalyst.engine.transcript import (
    Transcript,
    TranscriptLine,
    held,
    line_for,
)
from katalyst.engine.verify import Verdict, verdict
from katalyst.settings import Settings, get_settings

router = APIRouter(tags=["generate"])

NO_KEY_FOR_A_NEW_CLAIM = "drafting a new claim needs a model key."
"""What the insert route says when it cannot draft, word for word.

Not an error, not a stack trace, not a button that does nothing without saying
why. It is the one thing in a replayed flow that genuinely needs a key.
"""

STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
"""What the answer carries besides its media type.

Nothing between here and the browser may hold the body back: a proxy that buffers
delivers the whole growing map at once, which is the spinner-then-dump this
product forbids — silently, and only in the packaged build where nobody develops.
`X-Accel-Buffering: no` is the header nginx reads to turn its own buffering off
for one answer; `docker/nginx.conf` says the same thing for the whole location, so
the rule holds whether or not a future proxy reads the header.
"""


class GenerateRequest(BaseModel):
    """What it takes to build a map: a sentence, and a few things that are optional."""

    hypothesis: str = Field(
        min_length=1, description="The sentence the person typed. The map starts here."
    )
    target: str | None = Field(
        default=None,
        description=(
            "The place they want to know whether the story reaches, in their own "
            "words. Leave it out on the Explore door; supply it and the run is graded "
            "against it and says plainly when there is no route."
        ),
    )
    user_belief: Belief | None = Field(
        default=None,
        description=(
            "How likely the person thinks their own sentence is. Kept as theirs, "
            "never overwritten and never merged with the model's."
        ),
    )
    seed: int | None = Field(
        default=None,
        ge=0,
        le=BIGGEST_SEED,
        description=(
            "The one number every likelihood is worked out from. **Leave it out and "
            "the server mints one**, and the first event says which, so the run is "
            "reproducible from the moment it starts. Send one only to reproduce a run "
            "you were handed: a number invented by whoever is asking is a number "
            "nobody computed sitting inside the reproducibility of the answer. It "
            "is bounded by the largest whole number a browser holds exactly, "
            "because a seed that comes back rounded is a seed nobody ran."
        ),
    )
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description="How many versions of the map to try. Bounded at both ends.",
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description="How many worlds to run under each version. Bounded at both ends.",
    )


class DraftedInsert(BaseModel):
    """What the insert route answers with: the edit, and what drafting it cost.

    An insert is not one call — a drafting call, then one call per arrow — so it
    spends real money, and NFR-6 (every generation records model, tokens, cache
    reads, searches and dollars) has no exception for money spent outside a
    stream. The route used to answer a bare `Insert` and drop what it cost on the
    floor (`streaming.md`, settled 2026-09-20).
    """

    model_config = ConfigDict(frozen=True)

    insert: Insert = Field(description="The claim and its arrows, already validated.")
    receipt: Receipt = Field(
        description="What drafting it cost, in the shape the stream's receipt event carries."
    )


class InsertRequest(BaseModel):
    """What it takes to draft one claim a person asked for."""

    base_id: str = Field(
        description=(
            "The map the new claim is going onto, by **the map's own identifier** — "
            "the one a world carries as its `base_id`, and the one the stored "
            "examples answer to. Not the generation's identifier: a generation is "
            "a run and a map is a thing it built, and one run can hand its map to "
            "any number of later questions."
        )
    )
    branch: Branch | None = Field(default=None, description="The branch built so far, sent whole.")
    claim_in_words: str = Field(
        min_length=1, description='What the person typed: "…but Iran is struck the next day".'
    )
    position: int = Field(
        default=0,
        ge=0,
        description=(
            "Where in the branch the new edit goes. It is `position` and not `at`: "
            "`at` already means a place in a transcript and a date on an edit, and a "
            "third meaning is how a field stops meaning what it says."
        ),
    )


@router.post(
    "/generate",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "The eight events, in the order the grammar allows, one `event:` line "
                "and one `data:` line each. A refusal is one of them, never an error."
            ),
        }
    },
)
async def generate(
    request: Request,
    asked: GenerateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Build a map from one sentence, and write it out as it is built.

    With a key this calls a model; with none it plays a committed recording back
    through the same events. Either way the answer is one long response the
    browser reads as it arrives.

    Args:
        request: The request itself, so the run can stop when the client goes.
        asked: The sentence, and everything optional beside it.
        settings: The program's settings, which say whether a key is configured.

    Returns:
        The stream.
    """
    del settings  # Read through `live_answerer`, which is the one place that looks.
    return StreamingResponse(
        _written_out(request, asked),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )


@router.post("/generate/insert")
def draft_a_claim(asked: InsertRequest) -> DraftedInsert:
    """Draft one claim a person asked for, and check it like any other proposal.

    The one edit that needs a model. The other five — *Suppose this is true*,
    *This happened*, *Change this push*, *Split this claim* and *My own number* —
    are pure arithmetic in the rules layer, which is why a reviewer with no key
    still gets the whole multiverse at full fidelity.

    With no key this answers the one scripted intervention each recording carries,
    and declines anything else in plain words.

    Args:
        asked: The map, the branch, the sentence and where it goes.

    Returns:
        The claim and its arrows, already checked.

    Raises:
        HTTPException: 404 when no map answers to that name; 422 with every reason
            at once when the draft does not fit the map; 501 with one plain
            sentence when there is no key and no recording holds that sentence.
    """
    stored = engine.example_named(asked.base_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=_no_such_map(asked.base_id))

    # **The map the reader is looking at**, which is the base with their branch
    # folded onto it — not the bare base. Drafting against the base let the same
    # claim be added twice, and the reader first heard of it when a world route
    # refused the branch with `duplicate_id` (Kent, 2026-09-20).
    onto = _as_the_reader_sees_it(stored.graph, asked.branch)
    if isinstance(onto, list):
        raise HTTPException(status_code=422, detail=[one.model_dump() for one in onto])

    spent = nothing_spent_yet()
    answerer = live_answerer()
    if answerer is None:
        drafted = _scripted_insert(asked.claim_in_words)
        if drafted is None:
            raise HTTPException(status_code=501, detail=NO_KEY_FOR_A_NEW_CLAIM)
    else:
        started = time.monotonic()
        drafted, its_calls = add_a_claim(
            onto,
            asked.claim_in_words,
            answerer=answerer,
            on=_today(),
            width=Caps().width,
        )
        for one in its_calls:
            spent = fold(spent, one)
        _remember_what_the_insert_cost(asked, spent, its_calls, time.monotonic() - started)
        if drafted is None:
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "code": "edit_not_applicable",
                        "subject": asked.base_id,
                        "message": (
                            "That sentence could not be written as a claim this map "
                            "could carry, or nothing on the map turned out to join it."
                        ),
                    }
                ],
            )

    refused = _what_it_would_break(onto, drafted)
    if refused:
        raise HTTPException(status_code=422, detail=[one.model_dump() for one in refused])
    return DraftedInsert(
        insert=drafted,
        receipt=receipt_event(
            spent, seconds=0.0, mode="live" if answerer is not None else "replay"
        ),
    )


def _as_the_reader_sees_it(base: Graph, branch: Branch | None) -> Graph | list[Violation]:
    """Fold the reader's branch onto the stored map, or say why it will not fold.

    Args:
        base: The stored map, untouched.
        branch: What the reader has done to it so far, or nothing at all.

    Returns:
        The map as the reader is looking at it, or every reason the branch does
        not fit the map it names.
    """
    if branch is None:
        return base
    folded = apply(base, branch)
    if isinstance(folded, list):
        return folded
    return folded[0]


def _remember_what_the_insert_cost(
    asked: InsertRequest, spent: Spent, its_calls: tuple[Outcome, ...], seconds: float
) -> None:
    """Put an insert's calls on a transcript of their own, so the money is readable.

    NFR-6 has no exception for money spent outside a stream, and an insert is not
    one call: a drafting call, then one call per arrow (Kent, 2026-09-20).
    """
    working = Transcript(
        generation_id=mint_id(),
        hypothesis=asked.claim_in_words,
        target=None,
        seed=0,
        on=_today(),
        mode="live",
    )
    for at, one in enumerate(its_calls):
        working = working.plus(line_for(one, at))
    held.remember(working.model_copy(update={"receipt": spent, "why": None}), None)


@router.get("/generate/{generation_id}/transcript")
def transcript_of(generation_id: str) -> Transcript:
    """Hand back the working of a generation this process is still holding.

    Args:
        generation_id: The identifier the stream's first event carried.

    Returns:
        Every proposal, in order, with what each one cost.

    Raises:
        HTTPException: 404 with one plain sentence when the generation is no
            longer held — which a restart is enough to cause.
    """
    working = held.working(generation_id)
    if working is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "This program is no longer holding that generation. A transcript lives "
                "for the life of the process that made it, and nothing is written to "
                "disk yet."
            ),
        )
    return working


# --- Writing the stream out -------------------------------------------------


async def _written_out(request: Request, asked: GenerateRequest) -> AsyncIterator[str]:
    """Write one generation out as the bytes of a stream.

    The one place the two paths meet: a live run and a replay produce the same
    events, and this turns either into lines. It stops the moment the client goes
    away — **before the next model call**, which is the whole reason the behaviour
    is written down rather than left to chance.

    Args:
        request: The request, which knows whether the client is still there.
        asked: What was asked for.

    Yields:
        The wire's lines, one event at a time.
    """
    answerer = live_answerer()
    stepping = _replayed(asked) if answerer is None else _lived(asked, answerer)
    try:
        while True:
            if await request.is_disconnected():
                # Nothing already in flight is retried and nothing further is
                # asked. The transcript keeps what was built, as far as it got.
                return
            event = await run_in_threadpool(_next_or_nothing, stepping)
            if event is None:
                return
            yield events.framed(event)
            if events.name_of(event) not in (events.NAMES[Done], events.NAMES[Failed]):
                await _pause(answerer is None)
    finally:
        stepping.close()


def _next_or_nothing(stepping: Generator[Event, None, None]) -> Event | None:
    """Take the next event, or nothing at all when there are no more."""
    return next(stepping, None)


async def _pause(replaying: bool) -> None:
    """Wait between two events of a replay, and not at all during a live run.

    Pacing is presentation: a live run is already paced by how long a model takes
    to answer, and a replay that raced would teach a reviewer the product is
    faster than it is.
    """
    if not replaying:
        return
    waiting = replay.seconds_between()
    if waiting > 0:
        await asyncio.sleep(waiting)


def _lived(asked: GenerateRequest, answerer: Answerer) -> Generator[Event, None, None]:
    """Run a generation against a model, writing the transcript as it goes."""
    generation_id = mint_id()
    seed = asked.seed if asked.seed is not None else mint_seed()
    today = _today()
    working = Transcript(
        generation_id=generation_id,
        hypothesis=asked.hypothesis,
        target=asked.target,
        seed=seed,
        on=today,
        mode="live",
    )
    held.remember(working, None, in_flight=True)
    yield GenerationStarted(
        generation_id=generation_id, seed=seed, hypothesis=asked.hypothesis, target=asked.target
    )

    watching = Following(working)
    walking = grow(
        asked.hypothesis,
        target=asked.target,
        answerer=answerer,
        on=today,
        caps=Caps(),
        user_belief=asked.user_belief,
        never_seen=watching.never_seen,
    )
    try:
        for event in watching.follow(walking):
            held.remember(watching.working, None)
            yield event
    finally:
        # The reader may have gone away. Whatever this run paid for is on the
        # working before it is let go of, which is what makes "a run that broke
        # after ten calls still cost ten calls" true of every ending there is.
        walking.close()
        held.remember(watching.ended(), None, in_flight=False)

    finished, broke = watching.finished, watching.broke
    if finished is None or finished.graph is None:
        yield watching.receipt()
        if broke is None and finished is not None and finished.reason == "spend_cap":
            # **Stopping because the money ran out is a decision, not a fault**,
            # whether it runs out on call forty or call one — `events.py` says so
            # in as many words, and `proposals.md` INV-generation.6 promises the
            # stream ends in `done` for it. A run that emptied the purse before it
            # had a map used to end in `failed`, which reads as "something broke"
            # for the one ending nobody should read that way (2026-09-20).
            #
            # Everything else that leaves no map still ends in `failed`: a run the
            # model would not answer, or would not start, is not a decision
            # anybody took and should not read like one.
            yield Done(
                reason=finished.reason,
                claims=finished.claims,
                links=finished.links,
                rejected=finished.refused,
            )
            return
        # The walk's own sentence, because it knows what happened and this does
        # not: a run the model never answered must not tell a person to go and
        # rewrite a sentence that was never the problem (Kent, 2026-09-20).
        yield Failed(message=broke or (finished.why if finished is not None else WENT_WRONG))
        return

    held.remember(watching.working, finished.graph, in_flight=False)
    world = engine.build_world(
        finished.graph.id, None, seed, versions=asked.versions, worlds=asked.worlds
    )
    if world is None or isinstance(world, list):  # pragma: no cover - our own map, just built
        yield watching.receipt()
        yield Failed(message="The map was built but its likelihoods could not be worked through.")
        return
    yield BeliefsPropagated(world=world)
    if finished.destination is not None:
        yield verdict(finished.graph, finished.destination, beliefs=world.beliefs)
    yield watching.receipt()
    yield Done(
        reason=finished.reason,
        claims=finished.claims,
        links=finished.links,
        rejected=finished.refused,
    )


def _replayed(asked: GenerateRequest) -> Generator[Event, None, None]:
    """Play a committed recording back, matched on the person's own sentence."""
    started = time.monotonic()
    recording = replay.find(asked.hypothesis)
    if recording is None:
        # A receipt comes before every ending, this one included: the grammar
        # puts it second to last in **both** endings, and a receipt of zeroes is
        # the truth here. A stream with no receipt at all says nothing, and a
        # reader cannot tell it from one that forgot (2026-09-20).
        yield _nothing_spent(time.monotonic() - started)
        yield Failed(
            message=(
                "This copy of Katalyst has no model key and no recording of that "
                "sentence, so there is nothing it can honestly show you. The examples "
                "it can replay are listed on the first screen."
            )
        )
        return

    # **One identifier per viewing, minted here.** The recording's own is a
    # constant in a committed file, so two people opening the same card shared
    # one entry in the store and overwrote each other's working — and whichever
    # finished last decided what both of them read afterwards (2026-09-20). The
    # recording's own identifier is kept as a field, because it is what says
    # which file this was.
    announced = mint_id()
    played_from = next(
        (
            payload["generation_id"]
            for name, payload in recording.lines
            if name == events.NAMES[GenerationStarted]
        ),
        recording.header.base_id,
    )
    working = Transcript(
        generation_id=announced,
        played_from=played_from,
        hypothesis=recording.hypothesis,
        target=None,
        seed=recording.header.seed,
        on=recording.header.recording_date,
        mode="replay",
    )
    at = 0
    worked_through = False
    try:
        # Building the map from the file is as much "reading the recording" as
        # playing it is, so it sits inside the same guard.
        graph = replay.map_of(recording)
        held.remember(working, graph, in_flight=True)
        for event in replay.play(recording):
            if isinstance(event, GenerationStarted):
                # The reader is handed **this** viewing's identifier, which is
                # what their transcript is filed under.
                yield event.model_copy(update={"generation_id": announced})
                continue
            if isinstance(event, ProposalAccepted | ProposalRejected):
                working = working.plus(_line_from(event, at))
                held.remember(working, graph)
                at += 1
                yield event
                continue
            # The likelihoods are the one event a recording never holds: they are
            # recomputed here, and the grammar puts them straight after the growing
            # and before the two events that read them — the verdict, whose
            # multiplied-out number comes off the world, and the receipt.
            if not worked_through and isinstance(event, Verdict | Receipt):
                worked_through = True
                yield replay.beliefs_of(recording, (asked.versions, asked.worlds))
            if isinstance(event, Receipt):
                yield event.model_copy(update={"seconds": time.monotonic() - started})
                continue
            yield event
        held.remember(working, graph, in_flight=False)
    except replay.CannotBeRead as unreadable:
        # Half a map and an open connection is the worst of both worlds. This
        # ends where it is, with what it spent — nothing — and one plain sentence
        # naming the file (Kent, 2026-09-20).
        yield _nothing_spent(time.monotonic() - started)
        yield Failed(message=unreadable.why)
    except Exception:
        # The same treatment for a bug of our own, because the one thing that
        # must never reach the wire is a stack trace.
        logging.getLogger(__name__).exception("a replay stopped where it should not have")
        yield _nothing_spent(time.monotonic() - started)
        yield Failed(message=WENT_WRONG)


def _line_from(event: ProposalAccepted | ProposalRejected, at: int) -> TranscriptLine:
    """Turn one replayed growth event back into the transcript line it came from.

    A replay's transcript carries no counters: the run it is playing back cost
    what the receipt says, and this run cost nothing.
    """
    if isinstance(event, ProposalAccepted):
        in_words = "" if event.proposition is None else event.proposition.claim
        return TranscriptLine(at=at, what="accepted", in_words=in_words)
    return TranscriptLine(
        at=at, what="refused", in_words=event.claim_in_words, violations=event.violations
    )


def _nothing_spent(seconds: float) -> Receipt:
    """The receipt of a replay that had nothing to play: zeroes, and honestly so."""
    return receipt_event(nothing_spent_yet(), seconds=seconds, mode="replay")


def _scripted_insert(claim_in_words: str) -> Insert | None:
    """Find the one scripted intervention a recording can answer, or nothing at all.

    Matched on the exact words after trimming surrounding spaces — the same rule
    that picks which recording plays, because one matching rule is easier to trust
    than two. There is no fuzzy matching and there will not be: drafting a claim
    from a sentence is the model's job, and a similarity score doing it badly
    would be a piece of state nobody could trace to an input, a rule or a source.
    """
    wanted = claim_in_words.strip()
    for recording in replay.every_recording():
        if recording.header.insert.claim_in_words.strip() == wanted:
            drafted = recording.header.insert.answer
            return drafted
    return None


def _no_such_map(base_id: str) -> str:
    """Say that no map answers to that name, and say what a caller should send.

    The commonest wrong answer is a *generation's* identifier: a run and the map
    it built are two different things, and one run's map outlives the question
    that made it. So the sentence names both, rather than leaving somebody to
    guess which of two identifiers they are holding.
    """
    return (
        f"{engine.no_such_example(base_id)} If you are holding a map this program "
        "generated, send the map's own identifier — the one a world carries as its "
        "`base_id` — and not the identifier of the generation that built it."
    )


def _today() -> date:
    """The day this run is happening, read once and passed down.

    The one clock in the pipeline. Everything below takes the day as an argument,
    which is what lets a recorded run and a live one be compared at all.
    """
    return datetime.now(tz=UTC).date()


def _what_it_would_break(onto: Graph, drafted: Insert) -> tuple[Violation, ...]:
    """Check a drafted claim against the map it is going onto, exactly like any other.

    The same `validate`, the same codes, the same sentences a refused proposal
    gets — because a claim a person asked for is not held to a lower standard than
    one the model offered. Only what the edit **introduced** counts, for the same
    reason it does when a proposal is judged: a map already missing something
    would refuse every edit until the last one.

    Args:
        onto: The map the new claim is going onto.
        drafted: The claim and its arrows.

    Returns:
        Every reason it does not fit, or nothing at all.
    """
    folded = apply(
        onto, Branch(id="drafting", label="a claim somebody asked for", interventions=(drafted,))
    )
    if isinstance(folded, list):
        return tuple(folded)
    already = set(validate(onto))
    return tuple(one for one in validate(folded[0]) if one not in already)
