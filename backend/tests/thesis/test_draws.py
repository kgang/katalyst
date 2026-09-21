"""The one contract between the trade and the engine: two days per claim, and a real weight.

Every set of drawn worlds in this file is written down here, so every answer is
one that can be worked out on paper — and the working is in each test's docstring.
Nothing here reads a number an engine computed.

Three things the shape exists to make impossible, and each has tests whose only
job is to catch them:

* **Telling *it never started* apart from *it started and has not stopped*.** Two
  markers, not one, and a reader that mixed them would call a claim that never
  happened one that is still holding.
* **Counting a state as still true after it stopped.** A claim that came on and
  went off has still *happened* — which is what lift reads — and is no longer
  *holding* — which is what a price path reads. One array, two questions.
* **Reading a weighted sample as if the worlds were equally likely.** Every count
  is weighted, and the effective count says how many equally-weighted worlds the
  weights are worth.
"""

from datetime import date

import numpy
import pytest
from hypothesis import given, settings

from katalyst.domain import PropositionId
from katalyst.thesis.draws import (
    NEVER,
    STILL_HOLDING,
    THE_SAMPLE_SAYS,
    Draws,
    effective_draws,
    weighted_share,
)
from tests.thesis.synthetic import DAY_ZERO, draws, slice_middles, worlds_of

a_few = settings(max_examples=12, deadline=None)

CLAIMS = ("a", "b", "c")
"""Three claims, so a test can show one holding, one stopped and one that never came."""

FOUR_WORLDS = {
    "claims": CLAIMS,
    "days": 10,
    #     a   b   c
    "on": [
        [2, NEVER, 0],  # world 0: a came on day 2, c was already on when the window opened
        [5, 3, NEVER],  # world 1
        [NEVER, 3, 7],  # world 2
        [2, 8, 2],  # world 3
    ],
    "off": [
        [STILL_HOLDING, NEVER, 6],  # world 0: c stopped on day 6
        [STILL_HOLDING, STILL_HOLDING, NEVER],
        [NEVER, 3, STILL_HOLDING],  # world 2: b came on and stopped on the same day
        [STILL_HOLDING, STILL_HOLDING, STILL_HOLDING],
    ],
    "weight": [1.0, 3.0, 2.0, 4.0],
}
"""Four drawn worlds over three claims, written out so every count below is arithmetic.

The weights sum to ten, so a share is *the weight of the worlds it happened in,
over ten*. They are deliberately uneven, because the engine's are.
"""


def a_small_sample() -> Draws:
    """The four worlds above."""
    return worlds_of(**FOUR_WORLDS)  # type: ignore[arg-type]


# --- Reading the two days ---------------------------------------------------


def test_holding_on_a_day_is_came_on_and_has_not_stopped() -> None:
    """Worked out by hand on day three of the four worlds above.

    World 0: `a` came on day 2 and is still holding, so yes; `b` never came on;
    `c` came on day 0 and stops on day 6, which is after day 3, so yes.
    World 1: `a` comes on day 5, which is later; `b` came on day 3 and is still
    holding, so yes; `c` never came on.
    World 2: `a` never came on; `b` came on day 3 **and stopped on day 3**, and the
    day a claim goes off is the first day it is no longer true, so no; `c` comes on
    day 7, which is later.
    World 3: `a` came on day 2, so yes; `b` comes on day 8, which is later; `c`
    came on day 2, so yes.
    """
    holding = a_small_sample().holding_on(3)

    assert holding.tolist() == [
        [True, False, True],
        [False, True, False],
        [False, False, False],
        [True, False, True],
    ]


def test_a_claim_that_stopped_had_still_happened() -> None:
    """The same day three, asking whether each claim had come on **at all**.

    The one row that differs from the answer above is world 2's `b`, which came on
    day 3 and stopped the same day. It is not holding on day 3 and it did happen by
    day 3 — which is exactly the difference between what a price path reads and
    what lift reads.
    """
    sample = a_small_sample()

    came = sample.came_on_by(3)
    holding = sample.holding_on(3)

    assert came[2].tolist() == [False, True, False]
    assert holding[2].tolist() == [False, False, False]
    assert (came | ~holding).all(), "anything holding on a day had come on by it"


def test_a_claim_that_never_came_on_is_neither_holding_nor_happened() -> None:
    """On the last day of the window, `b` in world 0 has neither come on nor stopped.

    Its two markers are different numbers on purpose: `NEVER` in both arrays says
    it never started, where `STILL_HOLDING` in the second would say it started and
    is running.
    """
    sample = a_small_sample()

    assert not bool(sample.came_on_by(sample.days)[0, 1])
    assert not bool(sample.holding_on(sample.days)[0, 1])
    assert int(sample.on_day[0, 1]) == NEVER
    assert int(sample.off_day[0, 1]) == NEVER
    assert NEVER != STILL_HOLDING


def test_a_claim_already_on_when_the_window_opened_is_holding_on_day_zero() -> None:
    """World 0's `c` came on day zero, so it is holding on day zero and every day to five."""
    sample = a_small_sample()

    assert bool(sample.holding_on(0)[0, 2])
    assert bool(sample.holding_on(5)[0, 2])
    assert not bool(sample.holding_on(6)[0, 2]), "it stopped on day six"


def test_the_columns_are_found_by_name() -> None:
    """A claim's column is its place in the fixed order, and an unknown one is said out loud."""
    sample = a_small_sample()

    assert [sample.column(PropositionId(one)) for one in CLAIMS] == [0, 1, 2]
    with pytest.raises(KeyError, match="not one of the claims"):
        sample.column(PropositionId("nothing-like-this"))


def test_how_many_worlds_were_drawn() -> None:
    """Four rows, four worlds."""
    assert a_small_sample().worlds == 4


# --- Weighting --------------------------------------------------------------


def test_even_weights_are_worth_exactly_every_world() -> None:
    """Ten worlds each counting one are worth ten: ten squared over ten ones is ten."""
    assert effective_draws(numpy.ones(10)) == pytest.approx(10.0)


def test_one_world_carrying_everything_is_worth_one_world() -> None:
    """A weight of one against nine of nothing is one: one squared over one is one."""
    lopsided = numpy.array([1.0] + [0.0] * 9)

    assert effective_draws(lopsided) == pytest.approx(1.0)


def test_uneven_weights_are_worth_fewer_worlds_than_were_drawn() -> None:
    """The four worlds above: ten squared over thirty is ten thirds, which is under four.

    One plus nine plus four plus sixteen is thirty; one plus three plus two plus
    four is ten.
    """
    sample = a_small_sample()

    assert sample.effective == pytest.approx(10.0 / 3.0)
    assert sample.effective < sample.worlds


def test_no_weight_at_all_is_worth_nothing() -> None:
    """Weights that are all nothing are worth no worlds, rather than dividing by nothing."""
    assert effective_draws(numpy.zeros(5)) == 0.0


def test_a_share_is_the_weight_of_the_worlds_it_happened_in() -> None:
    """`b` had come on by day eight in worlds 1, 2 and 3, which weigh three, two and four.

    Three plus two plus four is nine, over the ten the weights sum to, so the share
    is nine tenths — and **not** the three-in-four that counting worlds would give.
    """
    sample = a_small_sample()

    share = weighted_share(sample.came_on_by(8)[:, 1], sample.weight)

    assert share == pytest.approx(0.9)
    assert share != pytest.approx(3.0 / 4.0)


def test_a_share_over_the_wrong_number_of_worlds_is_refused() -> None:
    """Three answers against four weights is a comparison of two different samples."""
    with pytest.raises(ValueError, match="one answer per drawn world"):
        weighted_share(numpy.array([True, False, True]), numpy.ones(4))


def test_a_share_needs_some_weight_somewhere() -> None:
    """Every world weighing nothing leaves nothing to take a share of."""
    with pytest.raises(ValueError, match="carries any weight"):
        weighted_share(numpy.array([True, False]), numpy.zeros(2))


# --- What the shape refuses -------------------------------------------------


def damaged(**changes: object) -> Draws:
    """Build the four worlds with one thing changed, to see whether it is caught."""
    table = dict(FOUR_WORLDS) | changes
    return worlds_of(**table)  # type: ignore[arg-type]


def test_a_window_runs_for_at_least_one_day() -> None:
    """A window of no days has no day for anything to happen on."""
    with pytest.raises(ValueError, match="at least one day"):
        damaged(days=0)


def test_a_claim_may_not_name_two_columns() -> None:
    """Two columns under one name is two answers to one question."""
    with pytest.raises(ValueError, match="only one column"):
        damaged(claims=("a", "a", "c"))


def test_the_two_day_arrays_have_to_agree_on_their_shape() -> None:
    """A day a claim went off for every claim but one is a hole somebody would read."""
    with pytest.raises(ValueError, match="the same shape"):
        Draws(
            day_zero=DAY_ZERO,
            days=10,
            claims=(PropositionId("a"),),
            on_day=numpy.array([[1], [2]], dtype=numpy.int32),
            off_day=numpy.array([[STILL_HOLDING]], dtype=numpy.int32),
            weight=numpy.ones(2),
            effective=2.0,
            sample="built_by_hand",
        )


def test_there_is_one_column_for_each_claim() -> None:
    """Three claims and two columns means one claim's days are some other claim's."""
    with pytest.raises(ValueError, match="that many columns"):
        Draws(
            day_zero=DAY_ZERO,
            days=10,
            claims=tuple(PropositionId(one) for one in CLAIMS),
            on_day=numpy.array([[1, 2]], dtype=numpy.int32),
            off_day=numpy.array([[STILL_HOLDING, STILL_HOLDING]], dtype=numpy.int32),
            weight=numpy.ones(1),
            effective=1.0,
            sample="built_by_hand",
        )


def test_a_day_has_to_be_a_whole_number() -> None:
    """Half a day is not a day the engine can have put an arrival on."""
    with pytest.raises(ValueError, match="whole day"):
        Draws(
            day_zero=DAY_ZERO,
            days=10,
            claims=(PropositionId("a"),),
            on_day=numpy.array([[1.5]]),
            off_day=numpy.array([[STILL_HOLDING]], dtype=numpy.int32),
            weight=numpy.ones(1),
            effective=1.0,
            sample="built_by_hand",
        )


def test_a_day_outside_the_window_is_refused() -> None:
    """Day eleven of a ten-day window is a day nobody drew."""
    with pytest.raises(ValueError, match="the day a claim came on"):
        damaged(on=[[11, NEVER, 0], [5, 3, NEVER], [NEVER, 3, 7], [2, 8, 2]])


def test_a_day_a_claim_went_off_outside_the_window_is_refused() -> None:
    """And so is a marker nobody defined, such as minus three."""
    with pytest.raises(ValueError, match="the day a claim went off"):
        damaged(
            off=[
                [STILL_HOLDING, NEVER, -3],
                [STILL_HOLDING, STILL_HOLDING, NEVER],
                [NEVER, 3, STILL_HOLDING],
                [STILL_HOLDING, STILL_HOLDING, STILL_HOLDING],
            ]
        )


def test_a_claim_that_never_came_on_may_not_be_said_to_have_ended() -> None:
    """World 0's `b` never came on, so saying it is still holding is saying it happened."""
    with pytest.raises(ValueError, match="never came on never went off"):
        damaged(
            off=[
                [STILL_HOLDING, STILL_HOLDING, 6],
                [STILL_HOLDING, STILL_HOLDING, NEVER],
                [NEVER, 3, STILL_HOLDING],
                [STILL_HOLDING, STILL_HOLDING, STILL_HOLDING],
            ]
        )


def test_a_claim_may_not_go_off_before_it_came_on() -> None:
    """World 0's `c` came on day zero; saying it stopped the day before is nonsense."""
    with pytest.raises(ValueError, match="before the day it came on"):
        damaged(
            on=[[2, NEVER, 4], [5, 3, NEVER], [NEVER, 3, 7], [2, 8, 2]],
            off=[
                [STILL_HOLDING, NEVER, 1],
                [STILL_HOLDING, STILL_HOLDING, NEVER],
                [NEVER, 3, STILL_HOLDING],
                [STILL_HOLDING, STILL_HOLDING, STILL_HOLDING],
            ],
        )


def test_there_is_one_weight_for_each_drawn_world() -> None:
    """Three weights over four worlds leaves one world counting for nothing stated."""
    with pytest.raises(ValueError, match="one weight for each world"):
        damaged(weight=[1.0, 2.0, 3.0])


def test_a_weight_is_a_real_number_and_never_below_nothing() -> None:
    """A world that counts a negative amount is a world that subtracts itself."""
    with pytest.raises(ValueError, match="never below nothing"):
        damaged(weight=[1.0, -2.0, 3.0, 4.0])


def test_some_world_has_to_carry_some_weight() -> None:
    """Every world weighing nothing is a sample with nothing in it."""
    with pytest.raises(ValueError, match="nothing to count"):
        damaged(weight=[0.0, 0.0, 0.0, 0.0])


def test_the_effective_count_must_be_the_one_these_weights_imply() -> None:
    """A count from some other sample would let a rail's floor be cleared by a stranger."""
    good = a_small_sample()

    with pytest.raises(ValueError, match="some other sample's count"):
        Draws(
            day_zero=good.day_zero,
            days=good.days,
            claims=good.claims,
            on_day=good.on_day,
            off_day=good.off_day,
            weight=good.weight,
            effective=good.worlds * 1.0,
            sample=good.sample,
        )


def test_a_sample_with_no_worlds_in_it_answers_nothing() -> None:
    """Nought rows is not a small sample; it is no sample."""
    with pytest.raises(ValueError, match="no worlds in it"):
        Draws(
            day_zero=DAY_ZERO,
            days=10,
            claims=(PropositionId("a"),),
            on_day=numpy.zeros((0, 1), dtype=numpy.int32),
            off_day=numpy.zeros((0, 1), dtype=numpy.int32),
            weight=numpy.zeros(0),
            effective=0.0,
            sample="built_by_hand",
        )


def test_a_weight_array_of_the_wrong_kind_is_refused() -> None:
    """Whole-number weights would silently round every share the layer takes."""
    with pytest.raises(ValueError, match="one ordinary number per drawn world"):
        Draws(
            day_zero=DAY_ZERO,
            days=10,
            claims=(PropositionId("a"),),
            on_day=numpy.array([[1]], dtype=numpy.int32),
            off_day=numpy.array([[STILL_HOLDING]], dtype=numpy.int32),
            weight=numpy.array([1], dtype=numpy.int64),
            effective=1.0,
            sample="built_by_hand",
        )


# --- Over worlds nobody wrote by hand ---------------------------------------


@a_few
@given(drawn=draws())
def test_anything_holding_on_a_day_had_come_on_by_it(drawn: Draws) -> None:
    """Holding is came on and has not stopped, so it can never be the wider of the two."""
    for day in (0, drawn.days // 2, drawn.days):
        assert (drawn.came_on_by(day) | ~drawn.holding_on(day)).all()


@a_few
@given(drawn=draws())
def test_having_come_on_never_stops_being_true_as_the_window_runs(drawn: Draws) -> None:
    """A claim that had happened by day five had happened by day six. Events do not unhappen."""
    for day in range(drawn.days):
        assert (drawn.came_on_by(day) <= drawn.came_on_by(day + 1)).all()


@a_few
@given(drawn=draws())
def test_the_effective_count_is_never_more_than_the_worlds_drawn(drawn: Draws) -> None:
    """A weighted sample is worth at most the number of worlds in it, and usually fewer."""
    assert 0.0 < drawn.effective <= drawn.worlds + 1e-9


@a_few
@given(drawn=draws())
def test_every_arrival_lands_on_the_middle_of_a_slice(drawn: Draws) -> None:
    """The engine puts an arrival in the middle of its time slice, so the days are coarse.

    This is a check on the generator rather than on the shape: a test that drew a
    day uniformly would be testing arithmetic nobody will run.
    """
    grid = set(slice_middles(drawn.days))
    landed = {int(one) for one in drawn.on_day.ravel() if int(one) != NEVER}

    assert landed <= grid


def test_a_hand_made_sample_says_it_is_hand_made() -> None:
    """No screen may print a first-touch number without naming the sample its days came from."""
    assert THE_SAMPLE_SAYS[a_small_sample().sample] == "a set of worlds built by hand"
    assert THE_SAMPLE_SAYS["weighted_forward_sample"] == "the engine's weighted forward sample"


def test_the_window_carries_the_day_it_opened_on() -> None:
    """Day zero is a date, so a screen can say which day day three was."""
    assert a_small_sample().day_zero == date(2026, 10, 1)
