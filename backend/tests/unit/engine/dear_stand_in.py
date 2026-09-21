"""A stand-in whose every answer is dear, so a ceiling can be watched from outside.

Named by `KATALYST_ANSWERER` when a test starts the recorder as a program and
wants to know what a `--cap` really buys. One call of it costs about a dollar on
the shipped price table, so a low cap is reached in two or three and the
overshoot is legible in dollars rather than in fractions of a cent.
"""

from katalyst.engine.outcome import WHAT_THE_SERVICE_DEFAULTS_TO, Said
from katalyst.engine.receipt import Receipt
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Storyteller,
    a_claim,
    a_link,
    a_starting_claim,
    an_answer,
)

THE_STRAIT = "The Strait of Hormuz is going to open next week."
A_STEP = "War-risk cover for Gulf transits gets cheap again."
AN_ENDING = "A contract on Brent below $70 resolves yes."
THE_INSERT = "Iran is struck the next day."

DEAR = {"read_fresh": 200_000, "written": 40_000, "thinking": 20_000}
"""One call of about $1.20 on the shipped price table."""


class Dear:
    """Answers a long story, and every answer costs about a dollar."""

    def __init__(self) -> None:
        """Start with nothing asked."""
        self._story = Storyteller(
            {
                THE_STRAIT: [
                    an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), **DEAR),
                    an_answer(a_claim(f"{A_STEP} again", cause=FROM_THE_QUESTION), **DEAR),
                ],
                A_STEP: [
                    an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"), **DEAR),
                ],
            },
            starting=[
                an_answer(a_starting_claim(THE_STRAIT), **DEAR),
                an_answer(a_starting_claim(THE_INSERT), **DEAR),
            ],
            joining=[an_answer(a_link(THE_INSERT, AN_ENDING), **DEAR)],
            otherwise=an_answer(a_claim("Another step.", cause=FROM_THE_QUESTION), **DEAR),
        )
        self.calls = 0
        self.effort_used = WHAT_THE_SERVICE_DEFAULTS_TO

    def watching(self, spent: Receipt, cap: float) -> None:
        """Take note of the purse and do nothing with it, like every fake."""

    def starting_claim(self, question: str, *, may_search: bool = True) -> Said:
        """Answer dearly."""
        self.calls += 1
        return self._story.starting_claim(question, may_search=may_search)

    def proposal(self, question: str, *, may_search: bool) -> Said:
        """Answer dearly."""
        self.calls += 1
        return self._story.proposal(question, may_search=may_search)


HELD: list[Dear] = []


def dear() -> Dear:
    """Build one, and keep it so a test can read what it was asked."""
    made = Dear()
    HELD.append(made)
    return made
