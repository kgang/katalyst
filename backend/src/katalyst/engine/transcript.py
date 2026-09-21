"""What a generation did, kept so a reader can ask afterwards — and measured as it goes.

A map is the answer; the transcript is the working. Every proposal, accepted or
refused, in the order it happened, with the rules' own sentences beside the ones
that were refused — and, on each line, what that one call cost and how long it
took. It is a product artifact, shown in the Inspector, not a log.

**Two numbers per line that are on no event.** How many of a call's written tokens
were the model thinking rather than answering, and how many seconds it took. The
first five recorded calls spent half to two-thirds of their output on thinking and
took about a minute each; keeping both here means the next full run answers
"where does the minute go" by itself, rather than needing an experiment of its
own. They are deliberately **not** on the receipt: that shape is settled, and a
number shown in two places is two numbers that eventually disagree.

**Where it lives, and for how long.** In memory, keyed by the generation's
identifier, for the life of the process — and filled from the same pass that
writes the stream, never from a second one. A process keeps the most recent
generations and drops the oldest. A restart empties it, and the route then says
the generation is no longer held rather than handing back an empty transcript
that reads like a run which proposed nothing.

The map is kept beside it, under the same key, because a reviewer who has just
watched a map draw itself then wants to suppose something on it — and the world
routes need a map to fold a branch onto.

Writing a second store on disk now would be a store to migrate in stack 05 for no
gain today. That is where sessions, maps, branches and transcripts go.

What this file must never do
----------------------------
- Never write anything to disk. `make record-demo` is the only writer of a file.
- Never hold a likelihood or a range. Numbers are recomputed from the seed.
- Never grow without bound. A long-lived process that remembers every generation
  it ever ran is a process that eventually stops.
"""

from collections import OrderedDict
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Graph, PropositionId, Violation
from katalyst.engine.outcome import Accepted, Outcome, Refused, Stopped
from katalyst.engine.receipt import Receipt

HOW_MANY_GENERATIONS_A_PROCESS_KEEPS = 8
"""How many finished generations one process remembers before it drops the oldest.

Enough for a reviewer to walk several examples and go back to an earlier one, and
small enough that a map and its transcript cannot pile up unbounded. The honest
default wants one measurement — the size of a finished thirty-claim map and its
transcript in memory — which the first full run will give; until then this is a
number chosen to be obviously safe rather than obviously right, and it is an
argument so a caller can say otherwise.
"""


class TranscriptLine(BaseModel):
    """One thing that was proposed, what happened to it, and what it cost.

    Three kinds of line and no others: a proposal was accepted, a proposal was
    refused, or the model said this part of the story was finished. The third
    makes no event on the wire — nothing changed on the map — but it belongs here,
    because "we asked and it said there was nothing more" is exactly the kind of
    thing a reader goes to the working for.
    """

    model_config = ConfigDict(frozen=True)

    at: int | None = Field(
        default=None,
        description=(
            "Where this sits on the stream, counting from 0 across accepted and "
            "refused proposals together. Nothing at all on a line that made no "
            "event, which is how the gaps in the stream's numbering are explained."
        ),
    )
    what: Literal["accepted", "refused", "stopped"] = Field(
        description="What happened to this proposal."
    )
    about: PropositionId | None = Field(
        default=None,
        description=(
            "The claim the call was asking about, so a refusal can be followed back "
            "to the question that produced it. Nothing at all on the two calls that "
            "turn a person's own sentences into claims."
        ),
    )
    in_words: str = Field(
        description=(
            "What the model wrote: the claim, the arrow's reason, or the sentence "
            "saying this line is finished. Never an identifier."
        )
    )
    violations: tuple[Violation, ...] = Field(
        default=(),
        description="Every reason the map's own rules gave, in their words. Empty unless refused.",
    )
    dropped: tuple[str, ...] = Field(
        default=(),
        description=(
            "Every address this call's answer cited that the search never "
            "returned. The reader is told which one rather than left to notice "
            "that an arrow says it argued where it might have said it documented."
        ),
    )
    no_reference_class: str | None = Field(
        default=None,
        description=(
            "The reference class of a count that was offered with nothing behind "
            "it, when one was. The count itself is not kept: a figure with no page "
            "behind it reads as measured however it is marked, so the transcript "
            "says a class was offered and that nothing backed it, and shows no "
            "number (Kent, 2026-09-20)."
        ),
    )
    calls: int = Field(default=0, description="How many round trips this question took.")
    searches: int = Field(default=0, description="How many web searches it ran.")
    input_tokens: int = Field(default=0, description="Tokens of question read fresh.")
    output_tokens: int = Field(default=0, description="Tokens of answer written.")
    cache_read_tokens: int = Field(default=0, description="Tokens recognised from an earlier call.")
    thinking_tokens: int = Field(
        default=0, description="How many written tokens were thinking rather than answering."
    )
    seconds: float = Field(default=0.0, description="How long this question took, wall clock.")


class Transcript(BaseModel):
    """The whole working of one generation, in the order it happened."""

    model_config = ConfigDict(frozen=True)

    generation_id: str = Field(description="The identifier this generation answers to.")
    played_from: str | None = Field(
        default=None,
        description=(
            "The identifier the recording this was played from carries, when this "
            "is a replay. **Not the identifier of this viewing**: that is minted "
            "per viewing, because a recording's own is a constant in a committed "
            "file and two people opening one card would otherwise share a single "
            "entry and overwrite each other's working (2026-09-20)."
        ),
    )
    hypothesis: str = Field(description="The sentence the person typed, unaltered.")
    target: str | None = Field(
        default=None, description="The place they asked whether the story gets to."
    )
    seed: int = Field(
        description="The one number every likelihood on this map was worked out from."
    )
    on: date = Field(description="The day this generation ran, which is its map's day zero.")
    mode: Literal["live", "replay"] = Field(
        description="Whether this run called a model or played a recording back."
    )
    lines: tuple[TranscriptLine, ...] = Field(
        default=(), description="Every proposal, in the order it was folded in."
    )
    receipt: Receipt | None = Field(
        default=None, description="What the run spent. Absent until the run has finished."
    )
    reason: str | None = Field(
        default=None, description="Why the run stopped. Absent until it has."
    )
    why: str | None = Field(default=None, description="That reason in one plain sentence.")

    def plus(self, line: TranscriptLine) -> "Transcript":
        """Add one line, and hand back a new transcript. This one is unchanged."""
        return self.model_copy(update={"lines": (*self.lines, line)})


def line_for(outcome: Outcome, at: int | None) -> TranscriptLine:
    """Turn one call's outcome into the line that records it.

    Args:
        outcome: What happened to one proposal, and what it cost.
        at: Where it sits on the stream, or nothing at all when it made no event.

    Returns:
        One line, carrying every counter the outcome carried.
    """
    result = outcome.result
    if isinstance(result, Accepted):
        what: Literal["accepted", "refused", "stopped"] = "accepted"
        in_words = "" if result.proposition is None else result.proposition.claim
        if not in_words and result.links:
            in_words = result.links[0].rationale
        violations: tuple[Violation, ...] = ()
        dropped, no_reference_class = result.sources_dropped, result.base_rate_dropped
    elif isinstance(result, Refused):
        what, in_words, violations = "refused", result.claim_in_words, result.violations
        dropped, no_reference_class = (), None
    else:
        what, in_words, violations = "stopped", result.why, ()
        dropped, no_reference_class = (), None
    return TranscriptLine(
        at=at,
        what=what,
        about=outcome.about,
        in_words=in_words,
        violations=violations,
        dropped=dropped,
        no_reference_class=no_reference_class,
        calls=outcome.calls,
        searches=outcome.searches,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        cache_read_tokens=outcome.cache_read_tokens,
        thinking_tokens=outcome.thinking_tokens,
        seconds=outcome.seconds,
    )


def makes_an_event(outcome: Outcome) -> bool:
    """Say whether this outcome puts something on the wire.

    Two of the three do. The model saying a line is finished changes nothing on
    the map, so it makes no event — the next growth event's frontier is how a
    reader learns that claim has closed.
    """
    return not isinstance(outcome.result, Stopped)


class Generations:
    """The generations this process is holding: their working, and their maps.

    Bounded and oldest-first: a long-lived process that remembered every run it
    ever made would eventually stop. A generation's working and its map are held
    and dropped **together**, under one key, so a map can never outlive the
    transcript that explains it. Nothing here is written to disk, and a restart
    empties it.
    """

    def __init__(self, keep: int = HOW_MANY_GENERATIONS_A_PROCESS_KEEPS) -> None:
        """Start holding nothing.

        Args:
            keep: How many generations to remember before dropping the oldest.
        """
        self._keep = keep
        self._held: OrderedDict[str, tuple[Transcript, Graph | None]] = OrderedDict()
        self._which_generation: dict[str, str] = {}
        self._watching: set[str] = set()

    def remember(
        self, transcript: Transcript, graph: Graph | None, *, in_flight: bool | None = None
    ) -> None:
        """Hold one generation's working and its map, dropping the oldest if full.

        Args:
            transcript: The working so far. Called again as it grows.
            graph: The map it built, once there is one.
            in_flight: True while somebody is still watching this run arrive, and
                False once it has ended. **A run still streaming is never
                dropped**: a busy process used to forget one while it was still
                writing into it, so the reader's own transcript answered 404
                halfway through their map arriving (2026-09-20). Left unsaid, it
                does not change.
        """
        self._held[transcript.generation_id] = (transcript, graph)
        self._held.move_to_end(transcript.generation_id)
        if in_flight is True:
            self._watching.add(transcript.generation_id)
        elif in_flight is False:
            self._watching.discard(transcript.generation_id)
        if graph is not None:
            self._which_generation[graph.id] = transcript.generation_id
        self._drop_the_oldest()

    def _drop_the_oldest(self) -> None:
        """Forget the oldest generations nobody is watching, until the bound holds.

        A map's name is only forgotten if **this** run still owns it. Two runs of
        one stored example share a `base_id`, and popping it blindly made the
        newer run's map unreachable while its own transcript was still held — a
        map that outlives nothing, reachable by nobody (2026-09-20).
        """
        evictable = [one for one in self._held if one not in self._watching]
        while len(self._held) > self._keep and evictable:
            oldest = evictable.pop(0)
            _, its_map = self._held.pop(oldest)
            if its_map is not None and self._which_generation.get(its_map.id) == oldest:
                self._which_generation.pop(its_map.id, None)

    def how_many(self) -> int:
        """How many generations this process is holding."""
        return len(self._held)

    def working(self, generation_id: str) -> Transcript | None:
        """The working of one generation, or nothing at all if it is no longer held."""
        found = self._held.get(generation_id)
        return None if found is None else found[0]

    def map_of(self, base_id: str) -> Graph | None:
        """A map this process generated, by its identifier, or nothing at all."""
        generation_id = self._which_generation.get(base_id)
        if generation_id is None:
            return None
        return self._held[generation_id][1]

    def day_zero_of(self, base_id: str) -> date | None:
        """The day a generated map's window starts on: the day its run happened."""
        generation_id = self._which_generation.get(base_id)
        if generation_id is None:
            return None
        return self._held[generation_id][0].on

    def forget_everything(self) -> None:
        """Drop everything. For a test that wants a process which has just started."""
        self._held.clear()
        self._which_generation.clear()
        self._watching.clear()


held = Generations()
"""The generations this process is holding.

One per process, because that is what it is: a fact about this running program,
not a value anybody passes around. A test that wants a fresh one calls
`forget_everything`.
"""
