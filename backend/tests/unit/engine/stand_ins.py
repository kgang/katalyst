"""Answerers a test can put in front of a program that calls a model, and run it.

`KATALYST_ANSWERER` names one of these by import path. Nothing here is ever
reached with the setting empty, which is what it is everywhere but a test. Two
programs read it — the recorder and the eval harness — and both refuse to write
their committed file from a run answered this way, so a run from here can never
be mistaken for a measurement of a model.

Why a setting rather than a flag: both programs are run by one person with one
key, and the thing that needed testing is the whole path — the argument parsing,
the module-level guard, the writing, the exit code. A `--fake` flag would have to
be parsed by the very code under test and would be a real flag a real run could
reach; a setting is read in one place already (`katalyst.settings`).
"""

from collections.abc import Callable
from datetime import date

from katalyst.domain import BaseRate
from katalyst.engine.client import TheModelDidNotAnswer
from katalyst.engine.outcome import WHAT_THE_SERVICE_DEFAULTS_TO, Said
from katalyst.engine.receipt import Receipt
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Storyteller,
    a_claim,
    a_link,
    a_starting_claim,
    a_stop,
    an_answer,
)

THE_STRAIT = "The Strait of Hormuz is going to open next week."
"""The stored example's own sentence, word for word, so the story is keyed by it."""

A_STEP = "War-risk cover for Gulf transits gets cheap again."
AN_ENDING = "A contract on Brent below $70 resolves yes."
THE_INSERT = "Iran is struck the next day."
THE_DESTINATION = "Brent crude settles below $68 for five sessions."
"""The Verify door's destination, word for word from the `hormuz` eval case."""

A_PAGE = "https://example.test/war-risk-premiums"
"""One address the search tool hands back, so an arrow can earn the word `documented`.

It is the same address the arrow and the count of past cases both cite, which is
what makes them both keepable: a citation the tool never returned is dropped.
"""

READ_BACK = 1_800
"""Tokens a call after the first reads back out of the service's own cache.

Every call but the first has some, because that is what a real run does: the
standing half of the request is written into the cache on the first call and read
back at about a tenth of the price on every call after it. A run where this stays
at nothing is the bug check 6 exists to catch.
"""


def a_whole_story() -> Storyteller:
    """A run that grows a small map, ends on a trade, and takes the scripted insert."""
    return Storyteller(
        {
            THE_STRAIT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), read_fresh=400, written=900),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(
                    a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"),
                    read_fresh=420,
                    written=1100,
                    thinking=600,
                ),
                an_answer(a_stop()),
            ],
        },
        starting=[
            an_answer(a_starting_claim(THE_STRAIT), read_fresh=300, written=700, thinking=400),
            an_answer(a_starting_claim(THE_INSERT), read_fresh=310),
        ],
        joining=[an_answer(a_link(THE_INSERT, AN_ENDING))],
    )


# --- Stories the eval harness is scored against -----------------------------


def an_eval_that_holds_every_check() -> Storyteller:
    """A Verify run that reaches its destination and gives all eight checks nothing.

    Everything the eight checks read is here on purpose: a map that ends on a
    contract, an arrow with a page behind it, a count of past cases citing that
    same page, a route from the starting claim to the destination, and the cache
    read back on every call after the first.

    Two calls are what make the destination reachable without anything inventing a
    bridge: the story proposes an ordinary arrow from a claim already on the map
    to the destination already on the map, and the map's own rules accept it like
    any other.
    """
    counted = BaseRate(
        reference_class="Gulf transit insurance rates after a strait reopened, 1990 to 2025",
        k=7,
        n=11,
        sources=(A_PAGE,),
    )
    return Storyteller(
        {
            THE_STRAIT: [
                an_answer(
                    a_claim(A_STEP, cause=FROM_THE_QUESTION, cites=(A_PAGE,), counted=counted),
                    found=(A_PAGE,),
                    searches=1,
                    read_fresh=400,
                    written=900,
                    read_from_cache=READ_BACK,
                ),
                an_answer(a_stop(), read_from_cache=READ_BACK),
            ],
            A_STEP: [
                an_answer(
                    a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"),
                    read_fresh=420,
                    written=1100,
                    thinking=600,
                    read_from_cache=READ_BACK,
                ),
                an_answer(a_link(A_STEP, THE_DESTINATION), read_from_cache=READ_BACK),
                an_answer(a_stop(), read_from_cache=READ_BACK),
            ],
        },
        starting=[
            an_answer(a_starting_claim(THE_STRAIT), read_fresh=300, written=700, thinking=400),
            an_answer(a_starting_claim(THE_DESTINATION), read_from_cache=READ_BACK),
        ],
    )


def an_eval_whose_map_ends_nowhere() -> Storyteller:
    """A run that builds a map and never reaches anything anybody could act on.

    One step, then nothing more to say — including when every open line is asked
    one last time for an ending. The walk stops at `no_terminal` and the map's own
    rules say the same thing about the finished map, which is check 2 doing its
    job: a chain that ends in prose is not a chain anybody can trade.
    """
    return Storyteller(
        {
            THE_STRAIT: [
                an_answer(
                    a_claim(A_STEP, cause=FROM_THE_QUESTION),
                    read_fresh=400,
                    written=900,
                    read_from_cache=READ_BACK,
                ),
                an_answer(a_stop(), read_from_cache=READ_BACK),
            ]
        },
        starting=[an_answer(a_starting_claim(THE_STRAIT), read_fresh=300, written=700)],
        otherwise=an_answer(a_stop(), read_from_cache=READ_BACK),
    )


class BreaksOnCall:
    """An answerer that runs a story and then stops answering, part way through.

    What a 429 on call twenty of forty looks like from inside a test, and what a
    crash of our own looks like: the first is a sentence the pipeline folds, the
    second is an exception nobody wrote a sentence for.
    """

    def __init__(self, story: Storyteller, *, after: int, raising: Exception) -> None:
        """Set out which call to stop on and what to raise."""
        self._story = story
        self._after = after
        self._raising = raising
        self.calls = 0
        self.effort_used = WHAT_THE_SERVICE_DEFAULTS_TO

    def watching(self, spent: Receipt, cap: float) -> None:
        """Take note of nothing."""

    def starting_claim(self, question: str, *, may_search: bool = True) -> Said:
        """Answer, or break if this is the call to break on."""
        return self._maybe(lambda: self._story.starting_claim(question, may_search=may_search))

    def proposal(self, question: str, *, may_search: bool) -> Said:
        """Answer, or break if this is the call to break on."""
        return self._maybe(lambda: self._story.proposal(question, may_search=may_search))

    def _maybe(self, answering: Callable[[], Said]) -> Said:
        """Count the call, break on the one named, otherwise let the story answer."""
        self.calls += 1
        if self.calls > self._after:
            raise self._raising
        return answering()


def stops_answering() -> BreaksOnCall:
    """A run the service stops answering after two calls: ordinary, and survivable."""
    return BreaksOnCall(
        a_whole_story(),
        after=2,
        raising=TheModelDidNotAnswer("The model is busy and turned this question away."),
    )


def breaks_after_the_generation() -> BreaksOnCall:
    """A run that crashes the way a bug of ours crashes, after the map is built.

    Five calls is the whole generation in `a_whole_story` — the starting claim,
    then two rounds — so the sixth is the first of the scripted insert. The money
    for a finished map is spent, and then something nobody wrote a sentence for
    happens.
    """
    return BreaksOnCall(
        a_whole_story(),
        after=5,
        raising=RuntimeError("something nobody wrote a sentence for"),
    )


TODAY = date(2026, 9, 17)
"""The day the measured runs happened, so a stand-in run reads like one of them."""
