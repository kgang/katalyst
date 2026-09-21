"""Lift: the claims over-represented where the stop went first, and what the rail refuses.

The rail is built from a thousand worlds laid out on purpose, so every share in
this file is a fraction a reader can check in their head. Half of them end with the
stop touched first, on day ten, and each claim comes on in a stated number of them.

Four things these tests exist to catch:

* **Counting a claim that came on after the stop.** It cannot have contributed, and
  counting it inflates every row in the direction that makes the rail look useful.
  One claim here comes on ten days *after* the stop and reads a lift of nothing —
  where counting it as having happened at all would have read two.
* **Reading a lift without what it rests on.** Below the floor no rows come back at
  all, and the reason does. The floor counts **effective** worlds, so a sample one
  world dominates clears nothing.
* **Printing a claim that tells you nothing.** A claim whose interval covers its
  own base share is dropped, with its reason, rather than ranked.
* **Claiming coverage for the ratio.** The interval is on the numerator. A
  repetition test checks it covers the numerator's true share about as often as it
  says, and claims nothing at all about the lift.
"""

import numpy
import pytest

from katalyst.domain import PropositionId
from katalyst.thesis.draws import NEVER, STILL_HOLDING, Draws, effective_draws
from katalyst.thesis.lift import (
    COVERAGE,
    DROPPED,
    THE_FLOOR,
    WhatTakesYouOut,
    what_takes_you_out,
    wilson,
)
from katalyst.thesis.position import FirstTouch
from tests.thesis.synthetic import DAY_ZERO

WORLDS = 1000
"""A thousand drawn worlds, so the floor of two hundred effective ones is cleared."""

STOPPED = 500
"""The first five hundred end with the stop touched first. The rest do not."""

STOP_DAY = 10
"""The day the stop was touched, in every world where it went first."""

DAYS = 30
CAME_ON = 5
"""The day a claim comes on, in every world where it comes on before the stop."""

AFTER = 20
"""The day the late claim comes on: ten days after the stop was already touched."""


def a_rail(weight: numpy.ndarray | None = None) -> tuple[Draws, FirstTouch]:
    """A thousand worlds over six claims, laid out so every share is a plain fraction.

    | claim | comes on, of the 500 stop-first | comes on, of the other 500 | day |
    |---|---|---|---|
    | `strongly` | 475 | none | 5 |
    | `somewhat` | 375 | 125 | 5 |
    | `unrelated` | 250 — every other world | 250 — every other world | 5 |
    | `late` | all 500 | none | **20**, ten days after the stop |
    | `held-true` | all 500 | all 500 | 0 |
    | `never` | none | none | — |
    | `on-the-day` | 475 | 100 | **10**, the very day the stop was touched |

    So `somewhat` came on in half of all the worlds and in three quarters of the
    stop-first ones: a lift of one and a half. `strongly` came on in 475 of 1000,
    and in 475 of the 500: `0.95 / 0.475`, a lift of two.
    """
    names = ["strongly", "somewhat", "unrelated", "late", "held-true", "never", "on-the-day"]
    came = numpy.full((WORLDS, len(names)), NEVER, dtype=numpy.int32)
    came[:475, 0] = CAME_ON
    came[:375, 1] = CAME_ON
    came[500:625, 1] = CAME_ON
    came[::2, 2] = CAME_ON
    came[:STOPPED, 3] = AFTER
    came[:, 4] = 0
    came[:475, 6] = STOP_DAY
    came[500:600, 6] = STOP_DAY

    counts = numpy.ones(WORLDS) if weight is None else weight
    drawn = Draws(
        day_zero=DAY_ZERO,
        days=DAYS,
        claims=tuple(PropositionId(one) for one in names),
        on_day=came,
        off_day=numpy.where(came == NEVER, NEVER, STILL_HOLDING).astype(numpy.int32),
        weight=counts,
        effective=effective_draws(counts),
        sample="built_by_hand",
    )
    return drawn, a_first_touch(counts)


def a_first_touch(weight: numpy.ndarray) -> FirstTouch:
    """The stop went first in the first five hundred worlds, on day ten, and nowhere else.

    Written by hand rather than walked, so these tests are about the division and
    not about a price path.
    """
    stop_on = numpy.full(WORLDS, NEVER, dtype=numpy.int32)
    stop_on[:STOPPED] = STOP_DAY
    return FirstTouch(
        stop_first=0.5,
        target_first=0.5,
        neither=0.0,
        stop_touched=0.5,
        finished_beyond_the_stop=0.5,
        stop_at=97.0,
        target_at=106.0,
        shift=0.0,
        effective_draws=effective_draws(weight),
        through=DAYS,
        stop_first_on=stop_on,
        sample="built_by_hand",
    )


def rows_by_claim(rail: WhatTakesYouOut) -> dict[str, object]:
    """The rail's rows, looked up by the claim they are about."""
    return {str(one.claim): one for one in rail.rows}


# --- The division -----------------------------------------------------------


def test_lift_is_the_stop_first_share_over_the_share_everywhere() -> None:
    """`somewhat` came on in 375 of the 500 stop-first worlds and 500 of all 1000.

    Three quarters over one half is **one and a half**: it had already happened
    half again as often in the worlds where the stop went first.
    """
    rail = what_takes_you_out(*a_rail())

    row = rows_by_claim(rail)["somewhat"]

    assert row.came_on_first == pytest.approx(0.75)  # type: ignore[attr-defined]
    assert row.came_on == pytest.approx(0.5)  # type: ignore[attr-defined]
    assert row.lift == pytest.approx(1.5)  # type: ignore[attr-defined]


def test_a_claim_that_came_on_after_the_stop_reads_no_lift_at_all() -> None:
    """`late` came on in every stop-first world — ten days **after** the stop was touched.

    It cannot have contributed, so the numerator counts none of those worlds and
    the lift is nothing. Counting it as *having happened at all* would have read
    `1.0 / 0.5`, a lift of two, and put it top of the rail.
    """
    rail = what_takes_you_out(*a_rail())

    row = rows_by_claim(rail)["late"]

    assert row.came_on_first == pytest.approx(0.0)  # type: ignore[attr-defined]
    assert row.came_on == pytest.approx(0.5)  # type: ignore[attr-defined]
    assert row.lift == pytest.approx(0.0)  # type: ignore[attr-defined]


def test_a_row_the_numerator_counted_no_world_for_has_no_typical_gap() -> None:
    """`late` never came on before the stop, so there is no gap to be typical of."""
    rail = what_takes_you_out(*a_rail())

    assert rows_by_claim(rail)["late"].days_before_the_stop is None  # type: ignore[attr-defined]


def test_a_row_says_how_many_days_before_the_stop_the_claim_came_on() -> None:
    """`somewhat` comes on day five and the stop is touched on day ten: five days."""
    rail = what_takes_you_out(*a_rail())

    assert rows_by_claim(rail)["somewhat"].days_before_the_stop == pytest.approx(  # type: ignore[attr-defined]
        STOP_DAY - CAME_ON
    )


def test_the_rail_is_ranked_by_lift() -> None:
    """Two, then five thirds, then three halves, then nothing."""
    rail = what_takes_you_out(*a_rail())

    assert [str(one.claim) for one in rail.rows] == [
        "strongly",
        "on-the-day",
        "somewhat",
        "late",
    ]
    assert rail.rows[0].lift == pytest.approx(0.95 / 0.475)


# --- What the rail leaves off -----------------------------------------------


def test_a_claim_held_true_by_an_edit_has_lift_one_and_is_not_shown() -> None:
    """`held-true` came on in every drawn world, so it is dropped with its reason.

    Its numerator and its denominator would both be one, so its lift would be one
    by construction. The rail is about what varies.
    """
    rail = what_takes_you_out(*a_rail())

    dropped = {str(one.claim): one.because for one in rail.dropped}

    assert dropped["held-true"] == "held_true_everywhere"
    assert "held-true" not in rows_by_claim(rail)


def test_a_claim_that_never_came_on_has_nothing_to_divide_by() -> None:
    """`never` came on in no world, so there is no denominator and no row."""
    rail = what_takes_you_out(*a_rail())

    dropped = {str(one.claim): one for one in rail.dropped}

    assert dropped["never"].because == "never_came_on"
    assert dropped["never"].sentence == DROPPED["never_came_on"]


def test_an_unrelated_claim_reads_no_lift_and_is_dropped_with_its_reason() -> None:
    """`unrelated` came on in every other world, so its two shares are the same half.

    Its numerator interval covers its own base share, so the rail cannot tell it
    apart from a claim that keeps no company with losing — and says so rather than
    printing a row that reads one.
    """
    rail = what_takes_you_out(*a_rail())

    dropped = {str(one.claim): one for one in rail.dropped}

    assert dropped["unrelated"].because == "tells_you_nothing"
    assert "unrelated" not in rows_by_claim(rail)


def test_every_row_carries_its_interval_its_count_and_its_coverage() -> None:
    """A lift of four over six worlds and one over two thousand are different claims."""
    rail = what_takes_you_out(*a_rail())

    for row in rail.rows:
        assert row.came_on_first_lo <= row.came_on_first <= row.came_on_first_hi
        assert row.effective_draws == pytest.approx(float(STOPPED))
        assert row.coverage == COVERAGE
        assert not (row.came_on_first_lo <= row.came_on <= row.came_on_first_hi)


def test_the_rail_names_the_sample_its_days_came_from() -> None:
    """The rail is read off drawn worlds, so it says which ones."""
    rail = what_takes_you_out(*a_rail())

    assert rail.sample == "built_by_hand"
    assert rail.stop_first_worlds == STOPPED
    assert rail.floor == THE_FLOOR
    assert rail.too_few_draws is None


# --- The floor --------------------------------------------------------------


def test_no_rows_come_back_below_the_floor_and_the_reason_does() -> None:
    """An empty rail without a reason reads as *nothing takes you out*, which is flattering."""
    drawn, touch = a_rail()
    barely = numpy.full(WORLDS, NEVER, dtype=numpy.int32)
    barely[:5] = STOP_DAY
    thin = what_takes_you_out(drawn, FirstTouch(**{**touch.__dict__, "stop_first_on": barely}))

    assert thin.rows == ()
    assert thin.dropped == ()
    assert thin.too_few_draws is not None
    assert str(THE_FLOOR) in thin.too_few_draws
    assert thin.effective_draws == pytest.approx(5.0)


def test_the_floor_counts_effective_worlds_and_not_rows() -> None:
    """Five hundred stop-first worlds, one of them carrying a thousand times the rest.

    The weights are worth a handful of equally-weighted worlds, so the rail
    refuses — where a count of rows would have read five hundred and printed
    everything.
    """
    lopsided = numpy.ones(WORLDS)
    lopsided[0] = 1000.0
    drawn, touch = a_rail(weight=lopsided)

    rail = what_takes_you_out(drawn, touch)

    assert rail.stop_first_worlds == STOPPED
    assert rail.effective_draws < THE_FLOOR
    assert rail.rows == ()
    assert rail.too_few_draws is not None


def test_the_shares_are_weighted() -> None:
    """Weighting the first quarter of the worlds up moves both shares, not the counts.

    Worlds 0 to 249 weigh three and the rest weigh one, so the whole sample weighs
    `250 x 3 + 750 x 1 = 1500` and the stop-first half weighs
    `250 x 3 + 250 x 1 = 1000`.

    `somewhat` comes on in worlds 0 to 374 and 500 to 624. Of the stop-first
    weight, `250 x 3 + 125 x 1 = 875` had it — seven eighths, where counting worlds
    would give three quarters. Of the whole sample's weight,
    `750 + 125 + 125 = 1000` had it — two thirds. So the lift is
    `(7/8) / (2/3) = 21/16`, and neither share is the one a count of worlds reads.
    """
    weight = numpy.ones(WORLDS)
    weight[:250] = 3.0
    drawn, touch = a_rail(weight=weight)

    rail = what_takes_you_out(drawn, touch)

    assert rows_by_claim(rail)["somewhat"].came_on_first == pytest.approx(875.0 / 1000.0)  # type: ignore[attr-defined]
    assert rows_by_claim(rail)["somewhat"].came_on == pytest.approx(2.0 / 3.0)  # type: ignore[attr-defined]
    assert rows_by_claim(rail)["somewhat"].lift == pytest.approx(21.0 / 16.0)  # type: ignore[attr-defined]


def test_a_rail_built_over_a_different_sample_is_refused() -> None:
    """Dividing one sample's numerator by another's denominator is two questions differenced."""
    drawn, touch = a_rail()
    shorter = touch.stop_first_on[:10]

    with pytest.raises(ValueError, match="counted over one sample"):
        what_takes_you_out(drawn, FirstTouch(**{**touch.__dict__, "stop_first_on": shorter}))


def test_a_rail_from_a_different_sampler_is_refused() -> None:
    """Days from the engine's sampler and worlds written by hand are not one sample."""
    drawn, touch = a_rail()

    with pytest.raises(ValueError, match="counted over one sample"):
        what_takes_you_out(
            drawn, FirstTouch(**{**touch.__dict__, "sample": "weighted_forward_sample"})
        )


# --- The interval -----------------------------------------------------------


def test_the_interval_stays_inside_nothing_and_one_at_a_share_of_nothing() -> None:
    """The obvious interval has no width at a share of nothing, which says a thing nobody saw."""
    low, high = wilson(0.0, 20.0, COVERAGE)

    assert low == 0.0
    assert 0.0 < high < 1.0


def test_the_interval_stays_inside_nothing_and_one_at_a_share_of_everything() -> None:
    """And the same at the other end."""
    low, high = wilson(1.0, 20.0, COVERAGE)

    assert high == 1.0
    assert 0.0 < low < 1.0


def test_more_draws_pin_a_share_down_more_tightly() -> None:
    """The same half over twenty draws and over two thousand are different claims."""
    few = wilson(0.5, 20.0, COVERAGE)
    many = wilson(0.5, 2000.0, COVERAGE)

    assert many[1] - many[0] < few[1] - few[0]


def test_asking_for_more_coverage_asks_for_a_wider_interval() -> None:
    """Being surer of containing the answer costs width, and nothing else."""
    narrow = wilson(0.5, 200.0, 0.80)
    wide = wilson(0.5, 200.0, 0.99)

    assert wide[0] < narrow[0] <= narrow[1] < wide[1]


@pytest.mark.parametrize(
    ("share", "count", "coverage", "complaint"),
    [
        (1.5, 100.0, 0.95, "from nothing to one"),
        (-0.1, 100.0, 0.95, "from nothing to one"),
        (0.5, 0.0, 0.95, "rests on some draws"),
        (0.5, 100.0, 0.0, "strictly between"),
        (0.5, 100.0, 1.0, "strictly between"),
    ],
)
def test_the_interval_refuses_what_it_cannot_take(
    share: float, count: float, coverage: float, complaint: str
) -> None:
    """A share outside the scale, a count of nothing, and a coverage that is not one."""
    with pytest.raises(ValueError, match=complaint):
        wilson(share, count, coverage)


def test_the_numerator_interval_covers_its_true_share_about_as_often_as_it_says() -> None:
    """A hundred seeded repetitions of a claim generated independently of the stop.

    The claim comes on in a known share of the drawn worlds, unrelated to which of
    them stopped out, so the true numerator share is that same known share. The
    interval is checked against it — and **nothing is checked about the ratio**,
    because a ratio of two shares over overlapping sets is not a share.

    The bar is worked out from the coverage and the number of repetitions rather
    than typed: three standard deviations below the coverage the interval claims.
    """
    repetitions, base = 100, 0.3
    rng = numpy.random.default_rng(20260922)
    covered = 0
    for _ in range(repetitions):
        happened = rng.random(STOPPED) < base
        low, high = wilson(float(happened.mean()), float(STOPPED), COVERAGE)
        covered += int(low <= base <= high)

    spread = numpy.sqrt(repetitions * COVERAGE * (1.0 - COVERAGE))
    assert covered >= repetitions * COVERAGE - 3.0 * spread


def test_a_claim_that_came_on_the_day_the_stop_was_touched_counts() -> None:
    """The boundary, stated once and pinned here: **the arrival day counts**.

    The path applies a claim's whole surprise **on** the day it comes on, so the
    close that first touch reads on that day already carries the move. A claim
    whose jump is what pushed the price through the stop therefore arrives on the
    very day the stop is touched — and counting it as *after* the stop would rank
    the claim that took you out below the ones that did nothing.

    `on-the-day` comes on day ten in 475 of the 500 stop-first worlds and in 100
    others, so its numerator is `0.95` and its base share `575 / 1000`. Reading the
    boundary the other way reads a numerator of nothing and a lift of nothing.
    """
    rail = what_takes_you_out(*a_rail())

    row = rows_by_claim(rail)["on-the-day"]

    assert row.came_on_first == pytest.approx(0.95)  # type: ignore[attr-defined]
    assert row.lift == pytest.approx(0.95 / 0.575)  # type: ignore[attr-defined]
    assert row.days_before_the_stop == pytest.approx(0.0)  # type: ignore[attr-defined]


def test_a_claim_that_came_on_the_day_after_the_stop_does_not_count() -> None:
    """The other side of the same boundary, so the rule is pinned from both directions.

    `late` comes on ten days after the stop was touched, and counts for nothing.
    One day after would count for nothing too: the rule is *on the day or before*,
    and nothing later.
    """
    drawn, touch = a_rail()
    came = drawn.on_day.copy()
    came[:STOPPED, 3] = STOP_DAY + 1
    just_after = Draws(**{**drawn.__dict__, "on_day": came})

    rail = what_takes_you_out(just_after, touch)

    assert rows_by_claim(rail)["late"].came_on_first == pytest.approx(0.0)  # type: ignore[attr-defined]


def test_the_interval_is_measured_on_effective_worlds_and_not_on_a_count_of_rows() -> None:
    """Weight a quarter of the worlds up and the interval widens, because the sample is worth less.

    Five hundred worlds end with the stop first either way. Weighted three to one
    they are worth four hundred equally-weighted ones, so the interval around the
    same numerator is the one four hundred draws buy — wider than the one five
    hundred would.
    """
    weight = numpy.ones(WORLDS)
    weight[:250] = 3.0
    rail = what_takes_you_out(*a_rail(weight=weight))

    row = rows_by_claim(rail)["somewhat"]
    on_effective = wilson(row.came_on_first, rail.effective_draws, COVERAGE)  # type: ignore[attr-defined]
    on_a_count = wilson(row.came_on_first, float(STOPPED), COVERAGE)  # type: ignore[attr-defined]

    assert rail.effective_draws == pytest.approx(400.0)
    assert (row.came_on_first_lo, row.came_on_first_hi) == pytest.approx(on_effective)  # type: ignore[attr-defined]
    assert on_effective[1] - on_effective[0] > on_a_count[1] - on_a_count[0]


def a_rail_of_gaps(days: list[int], weight: list[float]) -> tuple[Draws, FirstTouch]:
    """A thousand worlds: the five hundred that stop out carry a stated spread of arrival days.

    The pattern of days and weights repeats to fill the stop-first half; the other
    half never has the claim at all, so the rail has something to divide by and the
    claim is not dropped as one held true everywhere.
    """
    times = STOPPED // len(days)
    came = numpy.full((WORLDS, 1), NEVER, dtype=numpy.int32)
    came[:STOPPED, 0] = numpy.array(days * times, dtype=numpy.int32)
    weights = numpy.ones(WORLDS)
    weights[:STOPPED] = numpy.array(weight * times, dtype=numpy.float64)
    stop_on = numpy.full(WORLDS, NEVER, dtype=numpy.int32)
    stop_on[:STOPPED] = STOP_DAY
    return (
        Draws(
            day_zero=DAY_ZERO,
            days=DAYS,
            claims=(PropositionId("the-claim"),),
            on_day=came,
            off_day=numpy.where(came == NEVER, NEVER, STILL_HOLDING).astype(numpy.int32),
            weight=weights,
            effective=effective_draws(weights),
            sample="built_by_hand",
        ),
        FirstTouch(
            stop_first=0.5,
            target_first=0.5,
            neither=0.0,
            stop_touched=0.5,
            finished_beyond_the_stop=0.5,
            stop_at=97.0,
            target_at=106.0,
            shift=0.0,
            effective_draws=effective_draws(weights),
            through=DAYS,
            stop_first_on=stop_on,
            sample="built_by_hand",
        ),
    )


def test_the_typical_gap_is_the_middle_one_and_not_the_average() -> None:
    """Gaps of 9, 9, 9 and 1 days: the middle is nine, the average is seven.

    The middle rather than the average, because a handful of worlds where the claim
    came on the day the window opened would drag an average away from the days most
    of the worlds actually show.
    """
    rail = what_takes_you_out(*a_rail_of_gaps(days=[1, 1, 1, 9], weight=[1.0, 1.0, 1.0, 1.0]))

    assert rail.rows[0].days_before_the_stop == pytest.approx(9.0)
    assert rail.rows[0].days_before_the_stop != pytest.approx(7.0)


def test_the_typical_gap_is_weighted() -> None:
    """The same four gaps, with the world nine days out weighing nine times the others.

    Its weight is over half the total, so the middle gap by weight is its one — a
    day — where counting worlds would still read nine.
    """
    rail = what_takes_you_out(*a_rail_of_gaps(days=[1, 1, 1, 9], weight=[1.0, 1.0, 1.0, 9.0]))

    assert rail.rows[0].days_before_the_stop == pytest.approx(1.0)
