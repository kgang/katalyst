"""Following one walk: its events, its working, and what it has spent so far.

`grow.py` decides what to ask next. This turns what comes back into the three
things every caller of a walk needs at once — the events a reader watches, the
transcript they can read afterwards, and the running receipt — and it is the
only place that does.

There were two copies of this before, one in the route and one in the recorder,
and they had drifted: the recorder folded a receipt as it went and survived a
crash with the money intact, and the route did not, so a run that broke after
four billed calls reported a receipt of zeroes. Two copies of a loop is two
answers to "what did this cost".

What this must never do
-----------------------
- Never decide anything about a map, and never call a model. It reads a walk.
- Never lose what was paid for. Every outcome is folded into the transcript and
  the running total **before** its event is offered to anybody, so a reader who
  goes away, or a bug, or the money running out, leaves the working behind.
- Never raise. A walk that breaks leaves a plain sentence on `broke`, and the
  exception goes to the log.
"""

import logging
import time
from collections.abc import Generator, Iterable

from katalyst.engine.events import Event, Receipt, growth_event
from katalyst.engine.grow import Finished
from katalyst.engine.outcome import WHAT_THE_SERVICE_DEFAULTS_TO, Outcome
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.receipt import Receipt as Spent
from katalyst.engine.receipt import fold, nothing_spent_yet
from katalyst.engine.transcript import Transcript, line_for, makes_an_event

WENT_WRONG = (
    "This run stopped before it finished, and not for a reason anybody chose. "
    "Nothing was lost that had already been drawn; try it again."
)
"""What a person is told when a bug of ours ends a generation.

One plain sentence. The exception's name, its message and its stack go to the
server's own log, where somebody can act on them, and nowhere near the screen.
"""


class Following:
    """One walk, followed: what it has said, what it has written, what it has cost.

    Made once per generation and read as it goes. Everything on it is true at
    every moment, not only at the end — which is the whole reason it exists.
    """

    def __init__(self, working: Transcript) -> None:
        """Start following, with the transcript this generation writes into.

        Args:
            working: The transcript as it stands before anything has been asked.
        """
        self.working = working
        self.spent: Spent = nothing_spent_yet()
        self.finished: Finished | None = None
        self.broke: str | None = None
        self.at = 0
        self._started = time.monotonic()

    @property
    def seconds(self) -> float:
        """How long this generation has been going, in seconds."""
        return time.monotonic() - self._started

    def follow(self, walking: Iterable[Outcome | Finished]) -> Generator[Event, None, None]:
        """Drive the walk, yielding one event per answer that makes one.

        Every answer is folded into the transcript and the running total first,
        and only then is its event offered. A reader who stops reading, a bug, or
        a walk that ends itself all leave everything already paid for behind.

        Args:
            walking: The walk, as `grow` hands it back.

        Yields:
            One growth event per answer that makes one. The closing events are
            the caller's, because what closes a run differs between a stream with
            a world in it and a recorder without one.
        """
        try:
            for step in walking:
                if isinstance(step, Finished):
                    self.finished = step
                    break
                self._fold(step)
                if not makes_an_event(step):
                    continue
                yield growth_event(step, self.at - 1)
        except Exception:
            logging.getLogger(__name__).exception("a generation stopped where it should not have")
            self.broke = WENT_WRONG

    def never_seen(self, outcome: Outcome) -> None:
        """Take an answer nobody will ever see, and keep what it cost anyway.

        Handed to `grow` for the answers of a round that was already in flight
        when the reader went away. They were asked, they were billed, and the
        only thing lost is that nobody watched them arrive (2026-09-20).
        """
        self._fold(outcome)

    def _fold(self, outcome: Outcome) -> None:
        """Put one answer into the working and onto the running total."""
        makes_one = makes_an_event(outcome)
        self.working = self.working.plus(line_for(outcome, self.at if makes_one else None))
        self.spent = fold(self.spent, outcome)
        if makes_one:
            self.at += 1

    def ended(self) -> Transcript:
        """Put the ending onto the transcript, and hand it back.

        The receipt is the running one, not the walk's: a walk that broke hands
        nothing back, and what it spent before it broke was still spent.
        """
        ending = self.finished
        self.working = self.working.model_copy(
            update={
                "receipt": self.spent,
                "reason": None if ending is None else ending.reason,
                "why": self.broke if ending is None else ending.why,
            }
        )
        return self.working

    def receipt(
        self, *, mode: str = "live", recording_date: object = None, effort: str | None = None
    ) -> Receipt:
        """The receipt event, built from the running total.

        Args:
            mode: Whether this run called a model or played a recording back.
            recording_date: The day a recording was made, when this is a replay.
            effort: How hard the model was asked to try, as the plain word a
                reader sees.

        Returns:
            The event. A run that broke before its first call still gets one, of
            zeroes, which is also true: the promise that every generation records
            what it cost has no exception for runs that went wrong.
        """
        return receipt_event(
            self.spent,
            seconds=self.seconds,
            mode=mode,
            recording_date=recording_date,
            effort=effort,
        )


def receipt_event(
    spent: Spent,
    *,
    seconds: float,
    mode: str = "live",
    recording_date: object = None,
    effort: str | None = None,
) -> Receipt:
    """Turn what a run spent into the receipt event it puts on the stream.

    One builder, because two of them is two answers to "what did this cost" and
    the difference shows up as a number on somebody's screen.

    Args:
        spent: What the run spent.
        seconds: How long it took, wall clock.
        mode: Whether it called a model or played a recording back.
        recording_date: The day a recording was made, when this is a replay.
        effort: How hard the model was asked to try, as the plain word a reader
            sees. The service's own default when not said.

    Returns:
        The event.
    """
    return Receipt(
        model=spent.model,
        calls=spent.calls,
        input_tokens=spent.input_tokens,
        output_tokens=spent.output_tokens,
        cache_read_tokens=spent.cache_read_tokens,
        searches=spent.searches,
        dollars=spent.dollars,
        seconds=seconds,
        mode="live" if mode == "live" else "replay",
        recording_date=recording_date,  # type: ignore[arg-type]
        effort=effort or WHAT_THE_SERVICE_DEFAULTS_TO,
        prompt_hash=prompt_hash(),
    )
