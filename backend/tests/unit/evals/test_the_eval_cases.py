"""The four case files say what the chapter and the recorder say they say.

A case file is the only hand-written thing in this harness, so it is the only
thing that can drift from the rest of the product by somebody typing. These read
the shipped files and compare them with the shipped hypotheses, which are the
same four strings the launchpad's cards and the recordings use.
"""

import pytest
from evals.run import cases

from katalyst.engine.record import THE_FOUR


def test_the_cases_are_the_four_examples_this_product_ships() -> None:
    """One short name follows an example through the card, the recording and the scorecard."""
    assert [one.id for one in cases()] == sorted(THE_FOUR)


def test_every_hypothesis_is_the_one_the_product_actually_runs() -> None:
    """Word for word, so a scorecard is about the sentence a person can also type.

    The recorder holds the four sentences; a case file that drifted from one of
    them would score a question nobody asks.
    """
    assert {one.id: one.hypothesis for one in cases()} == THE_FOUR


def test_both_doors_are_covered_twice_over() -> None:
    """The assignment names two use cases, so two cases ask each of the two questions."""
    doors = sorted(one.door for one in cases())

    assert doors == ["explore", "explore", "verify", "verify"]


def test_exactly_one_case_asks_for_something_nothing_reaches() -> None:
    """The load-bearing case: we ask for a chain that cannot exist.

    It is how the harness answers "how do you know it is not making the chain
    up?", so there has to be exactly one of them and it has to be a Verify case —
    an Explore case has no destination to fail to reach.
    """
    cannot = [one for one in cases() if one.unreachable]

    assert len(cannot) == 1
    assert cannot[0].door == "verify"


def test_a_verify_case_names_a_destination_and_an_explore_case_does_not() -> None:
    """The door and the destination are one fact written twice, so they must agree."""
    for one in cases():
        assert (one.target is not None) == (one.door == "verify"), one.id


def test_every_seed_is_written_down_rather_than_drawn() -> None:
    """Two runs of one case differ only by the model, which is the whole point of a case.

    A drawn seed would mean two runs differ by the seed as well, and a scorecard
    comparing them would be reading a prompt change plus a wash of noise.
    """
    for one in cases():
        assert one.seed > 0, one.id


def test_one_case_can_be_asked_for_by_name() -> None:
    """`make eval ONLY=hormuz` is one case, so the harness has to be able to pick one."""
    assert [one.id for one in cases(only="hormuz")] == ["hormuz"]


def test_a_name_no_file_answers_to_is_refused_by_name() -> None:
    """A run that quietly scored nothing would look exactly like a run that scored everything."""
    with pytest.raises(ValueError, match="There is no case called 'nonesuch'"):
        cases(only="nonesuch")
