"""A round of questions hands each answer over as its own call comes back.

Three lines are asked about at the same time. On Kent's own kept run one round's
calls took 131, 44 and 65 seconds and all three claims appeared at 131 — the
screen was dead for the 87 seconds after the first answer already existed. His
answer, 2026-09-22: **as each call returns.**

The promise that rule re-orders is Kent's, 2026-09-21: *a paid call never falls
off the receipt.* It used to be kept by billing the whole round before folding
any of it. It is kept here another way — each call is billed the moment it comes
back, before it is folded — and these tests hold the two ways it could still be
broken: a fold that throws, and a reader who goes away while the round is in
flight.

**The waiting is injected, not slept.** A test that reads a moment — what was
true when the first answer arrived — injects the timing on purpose rather than
racing a clock (lesson 22, 2026-09-21). The two slow calls here wait on an event
the test sets; the fast one is never held at all. So a run that hands answers
over as they land finishes these tests in no measurable time, and only a run that
holds the round for its slowest call pays the second these calls are worth.
"""

import threading
from collections.abc import Iterable

import pytest

from katalyst.engine import grow as the_walk
from katalyst.engine.expand import map_with
from katalyst.engine.grow import Finished, grow
from katalyst.engine.outcome import Accepted, Caps, Outcome
from katalyst.engine.receipt import Receipt, fold, nothing_spent_yet
from tests.unit.engine.answers import (
    ASKING_ABOUT,
    FROM_THE_QUESTION,
    THE_DAY_THE_RUN_HAPPENED,
    Storyteller,
    a_claim,
    a_link,
    a_stop,
    an_answer,
)

STARTED_AT = "The thing the person expects happens."
FIRST_STEP = "A step the story reaches on its first round."
SECOND_STEP = "A second step, reached on the round after."
THE_FAST_ANSWER = "Something you could put money on."

ANSWERS_BEFORE_THE_ROUND_OF_THREE = 4
"""How many answers arrive before the round this file is about.

The starting claim, then one answer to the first round, then two to the second.
Only after those is the frontier three claims long, which is what makes the third
round a round of three.
"""

HOW_LONG_A_HELD_CALL_WAITS = 1.0
"""How long a held call waits to be let go before answering anyway, in seconds.

The analysis measured 1, 20 and 20 seconds; no test may sleep for that, so this
is the same shape an order of magnitude down. A walk that hands answers over as
they land never spends it — the test lets the held calls go the moment it has
checked what it came to check. A walk that holds a round for its slowest call
waits the whole second here and then fails, which is the point.
"""

A_MOMENT = 0.05
"""Long enough that a call really is still in flight, in seconds.

Used only where a test needs the calls of a round to be unfinished at the moment
it walks away from them, so that what happens next is a real wait on a real call
rather than a tidy-up of answers that had already arrived.
"""


class ThisFoldWentWrong(Exception):
    """A bug of ours, thrown where an answer is put onto the map.

    Nothing in the program raises this. It stands in for any bug in the folding,
    which is the one thing that could take a paid call off the receipt.
    """


class Paced(Storyteller):
    """A storyteller whose calls about named claims wait until the test lets them go.

    `Storyteller` answers by which claim the question is about, and holds a lock
    while it does. A call held inside that lock would hold the whole round, so
    the waiting happens out here, before the story is asked anything.
    """

    def __init__(self, story: dict[str, list[object]] | None = None) -> None:
        """Set out the story, with nothing held back yet."""
        super().__init__(story)  # type: ignore[arg-type]
        self._held: dict[str, threading.Event] = {}
        self.in_flight: dict[str, threading.Event] = {}
        self.answered: dict[str, threading.Event] = {}

    def hold(self, *claims: str) -> None:
        """From now on, a question about one of these claims waits to be let go."""
        for claim in claims:
            self._held[claim] = threading.Event()
            self.in_flight[claim] = threading.Event()
            self.answered[claim] = threading.Event()

    def let_go(self) -> None:
        """Let every held call answer."""
        for gate in self._held.values():
            gate.set()

    def let_go_shortly(self) -> None:
        """Let every held call answer, but not yet — so a caller really has to wait."""
        threading.Timer(A_MOMENT, self.let_go).start()

    def proposal(self, question: str, *, may_search: bool) -> object:
        """Answer the question, after waiting if this claim is one of the held ones."""
        about = (
            question.split(ASKING_ABOUT, 1)[1].splitlines()[0] if ASKING_ABOUT in question else ""
        )
        gate = self._held.get(about)
        if gate is not None:
            self.in_flight[about].set()
            gate.wait(HOW_LONG_A_HELD_CALL_WAITS)
        said = super().proposal(question, may_search=may_search)
        if gate is not None:
            self.answered[about].set()
        return said


def a_story_whose_third_round_asks_three() -> Paced:
    """Tell a story that opens three lines and then asks about all three at once.

    Round one asks the starting claim alone. Round two asks the starting claim
    and the step it produced — the step's answer is refused, which adds nothing
    and closes nothing, so the frontier is exactly three claims long and in a
    fixed order. Round three asks all three.
    """
    return Paced(
        {
            STARTED_AT: [
                an_answer(a_claim(FIRST_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(SECOND_STEP, cause=FROM_THE_QUESTION)),
                # Round three, held: the slowest call of the round.
                an_answer(a_stop()),
            ],
            FIRST_STEP: [
                # An arrow from a claim to itself, refused: it leaves the map and
                # the frontier exactly as they were.
                an_answer(a_link(FIRST_STEP, FIRST_STEP)),
                # Round three, never held: the answer this file is about.
                an_answer(a_claim(THE_FAST_ANSWER, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            # Round three, held: the round's other slow call.
            SECOND_STEP: [an_answer(a_stop())],
        }
    )


def a_walk(told: Paced, **rest: object) -> object:
    """Start one walk over that story, without pulling anything out of it yet."""
    return grow(
        STARTED_AT,
        answerer=told,  # type: ignore[arg-type]
        on=THE_DAY_THE_RUN_HAPPENED,
        caps=Caps(at_once=3),
        **rest,  # type: ignore[arg-type]
    )


def up_to_the_round_of_three(steps: object, told: Paced) -> list[Outcome]:
    """Pull every answer before the round of three, then hold that round's slow calls.

    The two slow calls are held only from here, because the starting claim is
    asked about in all three rounds and the first two have to run at full speed to
    open the three lines.
    """
    pulled = [next(steps) for _ in range(ANSWERS_BEFORE_THE_ROUND_OF_THREE)]  # type: ignore[call-overload]
    told.hold(STARTED_AT, SECOND_STEP)
    return pulled


def claim_on(outcome: object) -> str | None:
    """The words of the claim an answer brought, when it brought one."""
    result = getattr(outcome, "result", None)
    if isinstance(result, Accepted) and result.proposition is not None:
        return result.proposition.claim
    return None


def what_it_all_cost(outcomes: Iterable[Outcome]) -> Receipt:
    """Add up what a caller can still account for: every answer it was handed.

    A run that breaks mid-round never hands back a `Finished`, so its receipt is
    the one the caller folded as it went — which is exactly what `following.py`
    keeps, and the only receipt anybody would ever see.
    """
    spent = nothing_spent_yet()
    for one in outcomes:
        spent = fold(spent, one)
    return spent


def test_the_first_answer_of_a_round_is_not_held_for_the_slowest() -> None:
    """The answer that came back first reaches the reader first (Kent, 2026-09-22).

    Two of the round's three calls are held open. The third is never held. The
    reader is handed that third answer while the other two calls are still out,
    which is the whole of what Kent asked for: on his kept run the three answers
    existed at 44, 65 and 131 seconds and all three appeared at 131.
    """
    told = a_story_whose_third_round_asks_three()
    steps = a_walk(told)
    up_to_the_round_of_three(steps, told)

    first_of_the_round = next(steps)  # type: ignore[call-overload]

    # The two held calls were asked and have not answered.
    assert told.in_flight[STARTED_AT].wait(HOW_LONG_A_HELD_CALL_WAITS)
    assert told.in_flight[SECOND_STEP].wait(HOW_LONG_A_HELD_CALL_WAITS)
    assert not told.answered[STARTED_AT].is_set()
    assert not told.answered[SECOND_STEP].is_set()
    # And the answer already on the reader's screen is the one call that finished.
    assert claim_on(first_of_the_round) == THE_FAST_ANSWER

    told.let_go()
    rest = list(steps)  # type: ignore[call-overload]

    finished = rest[-1]
    assert isinstance(finished, Finished)
    assert finished.reason == "reached_terminal"
    assert finished.receipt.calls == len(told.asked)


def test_a_fold_that_throws_leaves_every_call_of_its_round_on_the_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kent's promise of 2026-09-21, kept the other way round (Kent, 2026-09-22).

    It used to be kept by billing the whole round before folding any of it. Now
    each call is billed the moment it comes back, before it is folded — so a bug
    in the folding still cannot take a paid call off the receipt, and the calls
    that were still out when it threw are waited for, billed and folded where
    nobody will see them.
    """

    def a_fold_that_throws(graph: object, result: object) -> object:
        """Break only where the fast answer lands, so the held calls fold normally."""
        arrived = getattr(result, "proposition", None)
        if arrived is not None and arrived.claim == THE_FAST_ANSWER:
            raise ThisFoldWentWrong("a bug where an answer is put onto the map")
        return map_with(graph, result)  # type: ignore[arg-type]

    told = a_story_whose_third_round_asks_three()
    nobody_saw: list[Outcome] = []
    steps = a_walk(told, never_seen=nobody_saw.append)
    handed_over = up_to_the_round_of_three(steps, told)

    monkeypatch.setattr(the_walk, "map_with", a_fold_that_throws)
    # The held calls are still out when the fold throws, so the drain really has
    # to wait for them rather than tidying up answers that had already arrived.
    told.let_go_shortly()
    with pytest.raises(ThisFoldWentWrong):
        next(steps)  # type: ignore[call-overload]

    # Every question the run asked is accounted for: the ones the reader was
    # handed, plus the ones nobody will ever see.
    assert told.answered[STARTED_AT].is_set()
    assert told.answered[SECOND_STEP].is_set()
    assert len(handed_over) + len(nobody_saw) == len(told.asked)
    assert what_it_all_cost([*handed_over, *nobody_saw]).calls == len(told.asked)
    # The answer whose fold threw was paid for too, and it is one of them.
    assert THE_FAST_ANSWER in [claim_on(one) for one in nobody_saw]


def test_a_reader_who_leaves_mid_round_still_pays_for_every_call_in_flight() -> None:
    """The rule of 2026-09-20, unchanged by handing answers over one at a time.

    The reader goes away with two calls still out. They were asked, so they are
    waited for, billed and folded into the working — nobody watches them arrive,
    and that is the only thing lost.
    """
    told = a_story_whose_third_round_asks_three()
    nobody_saw: list[Outcome] = []
    steps = a_walk(told, never_seen=nobody_saw.append)
    handed_over = up_to_the_round_of_three(steps, told)
    handed_over.append(next(steps))  # type: ignore[call-overload,arg-type]

    # Still out, so leaving now is leaving mid-round.
    assert not told.answered[STARTED_AT].is_set()
    assert not told.answered[SECOND_STEP].is_set()
    told.let_go_shortly()
    steps.close()  # type: ignore[attr-defined]

    assert told.answered[STARTED_AT].is_set()
    assert told.answered[SECOND_STEP].is_set()
    assert len(nobody_saw) == 2
    assert len(handed_over) + len(nobody_saw) == len(told.asked)
    assert what_it_all_cost([*handed_over, *nobody_saw]).calls == len(told.asked)
