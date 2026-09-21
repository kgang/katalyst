"""The reader's exit: what the form refuses, and how often each end of it is reached first.

Every path in this file is **written out day by day**, so which level is touched
first is something the reader of the test can see rather than take on trust. Where
a path is walked rather than written, it is walked with no day-to-day variability,
so the levels are the claim arithmetic and nothing else.

Three things these tests exist to catch:

* **A number that flatters the trade.** Reading only the end of the window misses a
  stop touched on day three; reading past the reader's horizon counts a stop they
  were never open for; checking daily misses touches between closes; and a day on
  which both levels are first reached could be read either way. Each has a test,
  and each correction runs against the trade.
* **A stop that somebody derived.** The stop, the target and the horizon arrive on
  a position the reader filled in. A separate file walks our own source to check
  nothing in this layer makes one up.
* **A contract on a price path.** A probability does not follow a random walk, and
  the question is refused by name rather than answered badly.
"""

from datetime import date, timedelta

import numpy
import pytest
from hypothesis import given, settings

from katalyst.domain import (
    Belief,
    Beliefs,
    ContractPayoff,
    PricePayoff,
    Proposition,
    PropositionId,
    Resolution,
)
from katalyst.thesis.draws import NEVER, effective_draws
from katalyst.thesis.paths import ClaimMove, Paths, walk
from katalyst.thesis.position import (
    BARRIER_SHIFT,
    REFUSALS,
    FirstTouch,
    Position,
    Refusal,
    first_touch,
    position_on,
    what_the_form_refuses,
    what_your_risk_budget_implies,
)
from tests.thesis.synthetic import DAY_ZERO, draws, positions, worlds_of

a_few = settings(max_examples=12, deadline=None)

ENTRY = 100.0
SETTLED = date(2026, 10, 31)
"""The day the ending is judged. A horizon after it is refused."""

HORIZON = date(2026, 10, 20)


def an_ending(payoff: ContractPayoff | PricePayoff | None) -> Proposition:
    """One tradeable ending, with the payoff the test wants to take a position on."""
    return Proposition(
        id=PropositionId("the-ending"),
        claim="Brent crude settles below sixty-eight dollars for five sessions",
        kind="market" if payoff is not None else "event",
        resolution=Resolution(
            criteria="five consecutive settlements below sixty-eight dollars",
            source="ICE settlement prices",
            by=SETTLED,
        ),
        prior=Belief(p=0.3, lo=0.2, hi=0.4, owner="model"),
        beliefs=Beliefs(model=Belief(p=0.3, lo=0.2, hi=0.4, owner="model")),
        payoff=payoff,
    )


AN_INSTRUMENT = PricePayoff(instrument="Brent crude futures", direction="short", move=0.06)
A_CONTRACT = ContractPayoff(
    venue="Polymarket",
    contract_id="3501950",
    title="Will the Strait of Hormuz be open?",
    side="yes",
)


def long_on(stop: float = 97.0, target: float = 106.0, daily_move: float = 0.0) -> Position:
    """A long position on the instrument ending, with the reader's own three numbers."""
    return Position(
        ending=PropositionId("the-ending"),
        instrument="Brent crude futures",
        side="long",
        trades="instrument",
        entry=ENTRY,
        stop=stop,
        target=target,
        horizon=HORIZON,
        risk_budget=0.02,
        daily_move=daily_move,
    )


def paths_of(*rows: list[float], weight: list[float] | None = None, daily_move: float = 0.0):
    """Write price paths out day by day, one row per drawn world, day zero first."""
    level = numpy.array(rows, dtype=numpy.float64)
    counts = numpy.ones(len(rows)) if weight is None else numpy.array(weight, dtype=numpy.float64)
    return Paths(
        day_zero=DAY_ZERO,
        days=level.shape[1] - 1,
        entry=ENTRY,
        daily_move=daily_move,
        level=level,
        weight=counts,
        sample="built_by_hand",
        decay_shape={},
        market_chance={},
    )


def touched(paths: Paths, position: Position) -> FirstTouch:
    """First touch **read to the last day these paths carry**, with the refusal ruled out.

    The reader's horizon is what says how far to walk, and almost every test below
    is about which level is reached rather than about the window, so the horizon is
    set here to the end of the paths the test wrote. The window has tests of its
    own.
    """
    to_the_end = Position(
        **{**position.__dict__, "horizon": paths.day_zero + timedelta(days=paths.days)}
    )
    answer = first_touch(paths, to_the_end)
    assert isinstance(answer, FirstTouch)
    return answer


# --- Building a position from the map ---------------------------------------


def test_the_instrument_and_the_side_come_from_the_map_not_the_form() -> None:
    """The reader is shown what is traded and which way; they do not type it.

    The payoff says the position is **short** the instrument, because it makes
    money when the claim comes true and the instrument falls. So the stop is
    *above* the entry price and the target below it — which is why the position
    below would be refused if the two were the other way round.
    """
    built = position_on(
        an_ending(AN_INSTRUMENT),
        entry=ENTRY,
        stop=103.0,
        target=94.0,
        horizon=HORIZON,
        risk_budget=0.02,
        daily_move=1.0,
    )

    assert isinstance(built, Position)
    assert built.instrument == "Brent crude futures"
    assert built.side == "short"
    assert built.trades == "instrument"


def test_a_contract_ending_trades_in_probability_and_names_its_contract() -> None:
    """The contract's own identifier, and the yes side read as long the claim."""
    built = position_on(
        an_ending(A_CONTRACT),
        entry=0.4,
        stop=0.3,
        target=0.6,
        horizon=HORIZON,
        risk_budget=0.02,
        daily_move=0.0,
    )

    assert isinstance(built, Position)
    assert built.instrument == "3501950"
    assert built.side == "long"
    assert built.trades == "contract"


def test_the_no_side_of_a_contract_is_short_the_claim() -> None:
    """A no-side ending makes money when the claim fails, so the prices run the other way."""
    built = position_on(
        an_ending(A_CONTRACT.model_copy(update={"side": "no"})),
        entry=0.4,
        stop=0.5,
        target=0.2,
        horizon=HORIZON,
        risk_budget=0.02,
        daily_move=0.0,
    )

    assert isinstance(built, Position)
    assert built.side == "short"


def test_an_ending_that_names_no_trade_has_no_position_to_take() -> None:
    """Not something the reader did: whatever offered it as tradeable offered the wrong claim."""
    with pytest.raises(ValueError, match="names no trade"):
        position_on(
            an_ending(None),
            entry=ENTRY,
            stop=97.0,
            target=106.0,
            horizon=HORIZON,
            risk_budget=0.02,
            daily_move=1.0,
        )


# --- What the form refuses --------------------------------------------------


def test_a_stop_where_the_trade_is_already_working_is_refused() -> None:
    """A long position's stop is below the entry price. Above it is a target by another name."""
    refused = what_the_form_refuses(long_on(stop=104.0), an_ending(AN_INSTRUMENT))

    assert [one.code for one in refused] == ["stop_on_the_wrong_side"]
    assert refused[0].field == "stop"
    assert refused[0].sentence == REFUSALS["stop_on_the_wrong_side"]


def test_a_stop_at_the_entry_price_is_refused_too() -> None:
    """Out at the price you came in at is not a stop; it is a decision not to trade."""
    refused = what_the_form_refuses(long_on(stop=ENTRY), an_ending(AN_INSTRUMENT))

    assert [one.code for one in refused] == ["stop_on_the_wrong_side"]


def test_a_target_you_are_already_at_is_refused() -> None:
    """A long position's target is above the entry price."""
    refused = what_the_form_refuses(long_on(target=ENTRY), an_ending(AN_INSTRUMENT))

    assert [one.code for one in refused] == ["target_not_beyond_entry"]


def test_a_horizon_past_the_day_the_claim_is_judged_is_refused() -> None:
    """The ending is settled on the thirty-first, so a trade open in November is not one."""
    late = long_on()

    refused = what_the_form_refuses(
        Position(**{**late.__dict__, "horizon": date(2026, 11, 15)}), an_ending(AN_INSTRUMENT)
    )

    assert [one.code for one in refused] == ["horizon_after_the_claim"]


def test_a_horizon_on_the_day_the_claim_is_judged_is_allowed() -> None:
    """The boundary is the settlement day itself, and being open on it is ordinary."""
    late = long_on()

    refused = what_the_form_refuses(
        Position(**{**late.__dict__, "horizon": SETTLED}), an_ending(AN_INSTRUMENT)
    )

    assert refused == ()


@pytest.mark.parametrize("budget", [0.0, -0.1, 1.5])
def test_a_risk_budget_that_is_not_a_share_of_capital_is_refused(budget: float) -> None:
    """Nothing at risk is not a trade, and more than everything is not a share."""
    late = long_on()

    refused = what_the_form_refuses(
        Position(**{**late.__dict__, "risk_budget": budget}), an_ending(AN_INSTRUMENT)
    )

    assert [one.code for one in refused] == ["risk_budget_out_of_range"]


def test_a_contract_price_outside_nothing_to_one_is_refused() -> None:
    """A contract cannot trade above everything, whatever a reader types."""
    built = position_on(
        an_ending(A_CONTRACT),
        entry=0.4,
        stop=0.3,
        target=1.4,
        horizon=HORIZON,
        risk_budget=0.02,
        daily_move=0.0,
    )

    assert isinstance(built, tuple)
    assert [one.code for one in built] == ["price_outside_the_contract"]


def test_every_fault_comes_back_at_once() -> None:
    """A form that reveals one mistake at a time is a form nobody finishes.

    Three things wrong here: the stop is above the entry price, the target is below
    it, and the risk budget is more than all their capital. All three come back
    together, in the order the rules are written.
    """
    late = long_on(stop=104.0, target=95.0)

    refused = what_the_form_refuses(
        Position(**{**late.__dict__, "risk_budget": 2.0}), an_ending(AN_INSTRUMENT)
    )

    assert [one.code for one in refused] == [
        "stop_on_the_wrong_side",
        "target_not_beyond_entry",
        "risk_budget_out_of_range",
    ]


# --- First touch ------------------------------------------------------------


def test_the_stop_is_first_when_it_is_touched_first() -> None:
    """Written out by hand: the path falls to the stop on day two and rallies past the target.

    Stop 97, target 106. The path reads 100, 99, 96, 103, 108. It is at or below 97
    on day two and at or above 106 on day four, so the stop went first — and a
    method that read only the last day would have called this a winner.
    """
    answer = touched(paths_of([100.0, 99.0, 96.0, 103.0, 108.0]), long_on())

    assert answer.stop_first == pytest.approx(1.0)
    assert answer.target_first == pytest.approx(0.0)
    assert answer.stop_first_on.tolist() == [2]


def test_the_target_is_first_when_it_is_touched_first() -> None:
    """The same two levels, and a path that reaches 106 on day one before falling to 96."""
    answer = touched(paths_of([100.0, 106.0, 101.0, 96.0, 96.0]), long_on())

    assert answer.target_first == pytest.approx(1.0)
    assert answer.stop_first == pytest.approx(0.0)
    assert answer.stop_first_on.tolist() == [NEVER]


def test_when_both_levels_are_first_reached_on_the_same_day_the_stop_is_first() -> None:
    """The tie, on an input that actually reaches it.

    A daily close cannot say which level the price reached first inside the day, so
    when both are first reached on the same day the stop is taken — the only
    reading that cannot flatter the trade.

    The tie is reachable because the barrier shift moves both levels toward the
    entry price and never past it. A stop a tenth below a hundred and a target a
    tenth above, at a variability of five points a day, both clamp to a hundred; a
    close of exactly a hundred then reaches both on the same day.
    """
    answer = touched(
        paths_of([100.0, 100.0], daily_move=5.0),
        long_on(stop=99.9, target=100.1, daily_move=5.0),
    )

    assert answer.stop_at == pytest.approx(ENTRY)
    assert answer.target_at == pytest.approx(ENTRY)
    assert answer.stop_first == pytest.approx(1.0)
    assert answer.target_first == pytest.approx(0.0)


def test_a_close_exactly_on_the_stop_is_a_touch() -> None:
    """A level is reached the moment the path touches it, and landing on it is touching it."""
    answer = touched(paths_of([100.0, 97.0, 99.0]), long_on(stop=97.0))

    assert answer.stop_first == pytest.approx(1.0)
    assert answer.stop_first_on.tolist() == [1]


def test_a_close_exactly_on_the_target_is_a_touch_too() -> None:
    """The same rule on the other level, so neither side of it is free."""
    answer = touched(paths_of([100.0, 106.0, 101.0]), long_on())

    assert answer.target_first == pytest.approx(1.0)


def test_neither_touched_is_its_own_answer_and_the_three_shares_sum_to_one() -> None:
    """A window that closes with the trade still open is a third outcome, not a rounding."""
    answer = touched(paths_of([100.0, 101.0, 99.0, 100.0]), long_on())

    assert answer.neither == pytest.approx(1.0)
    assert answer.stop_first + answer.target_first + answer.neither == pytest.approx(1.0)


def test_the_shares_are_weighted_by_the_worlds_own_weights() -> None:
    """Two worlds, one stopped and one at target, weighing one and three.

    So the stop goes first in a quarter of the weight and the target in three
    quarters — not the one-in-two that counting worlds would give.
    """
    answer = touched(
        paths_of([100.0, 96.0, 96.0], [100.0, 107.0, 107.0], weight=[1.0, 3.0]),
        long_on(),
    )

    assert answer.stop_first == pytest.approx(0.25)
    assert answer.target_first == pytest.approx(0.75)
    assert answer.effective_draws == pytest.approx(effective_draws(numpy.array([1.0, 3.0])))


def test_a_short_position_is_stopped_out_upward() -> None:
    """The same rule read the other way: a short's stop is above the entry, its target below."""
    short = Position(**{**long_on().__dict__, "side": "short", "stop": 103.0, "target": 94.0})

    answer = touched(paths_of([100.0, 104.0, 93.0]), short)

    assert answer.stop_first == pytest.approx(1.0)


def test_the_barrier_shift_moves_each_level_toward_the_entry_price() -> None:
    """A daily check misses touches between closes, so the levels move in by the correction.

    The stop is three points below a hundred and the target six above, and the
    instrument moves a point a day. The shift is the constant times that one point,
    so the stop is checked a shift *above* 97 and the target a shift *below* 106 —
    both nearer the entry price, both making a touch likelier.
    """
    answer = touched(paths_of([100.0, 100.0], daily_move=1.0), long_on(daily_move=1.0))

    assert answer.shift == pytest.approx(BARRIER_SHIFT * 1.0)
    assert answer.stop_at == pytest.approx(97.0 + BARRIER_SHIFT)
    assert answer.target_at == pytest.approx(106.0 - BARRIER_SHIFT)
    assert 97.0 < answer.stop_at < ENTRY < answer.target_at < 106.0


def test_the_barrier_shift_catches_a_touch_a_daily_count_would_miss() -> None:
    """A close at 97.4 does not reach a stop of 97, and the corrected check says it did.

    The shift at a variability of one point is about six tenths of a point, so the
    stop is checked at about 97.58 — above the close. Without the correction this
    world would be counted as never stopped out, which is the flattering direction.
    """
    just_above = paths_of([100.0, 97.4, 99.0], daily_move=1.0)

    corrected = touched(just_above, long_on(daily_move=1.0))
    uncorrected = touched(paths_of([100.0, 97.4, 99.0]), long_on(daily_move=0.0))

    assert corrected.stop_first == pytest.approx(1.0)
    assert uncorrected.stop_first == pytest.approx(0.0)


def test_the_shift_never_moves_a_level_past_the_entry_price() -> None:
    """A stop nearer the entry than the correction is touched on the first day either way."""
    tight = long_on(stop=99.9, target=100.1, daily_move=5.0)

    answer = touched(paths_of([100.0, 100.0], daily_move=5.0), tight)

    assert answer.stop_at == pytest.approx(ENTRY)
    assert answer.target_at == pytest.approx(ENTRY)


def test_the_stop_is_at_least_as_likely_as_finishing_beyond_it() -> None:
    """True by containment: a path that ends past the stop touched it on the way.

    Two worlds. One dips to 96 on day two and recovers to 101 — touched, and did not
    finish beyond. One falls to 95 and stays — touched, and finished beyond. So the
    share touched is everything and the share finishing beyond is half of it.
    """
    answer = touched(
        paths_of([100.0, 99.0, 96.0, 101.0], [100.0, 98.0, 95.0, 95.0]),
        long_on(),
    )

    assert answer.stop_touched == pytest.approx(1.0)
    assert answer.finished_beyond_the_stop == pytest.approx(0.5)
    assert answer.stop_touched >= answer.finished_beyond_the_stop


def test_finishing_beyond_is_read_against_the_reader_s_own_stop() -> None:
    """The shift is a correction to a *count*, not a change to the price the reader typed."""
    answer = touched(paths_of([100.0, 97.4], daily_move=1.0), long_on(daily_move=1.0))

    assert answer.stop_first == pytest.approx(1.0)
    assert answer.finished_beyond_the_stop == pytest.approx(0.0)


def test_a_first_touch_number_names_the_sample_its_days_came_from() -> None:
    """The one number the reader acts on, so it cannot be printed without saying where from."""
    answer = touched(paths_of([100.0, 96.0]), long_on())

    assert answer.sample == "built_by_hand"


def test_a_contract_ending_refuses_first_touch_by_name() -> None:
    """A probability does not follow a random walk, and the honest answer says so."""
    contract = Position(**{**long_on().__dict__, "trades": "contract"})

    answer = first_touch(paths_of([100.0, 96.0]), contract)

    assert isinstance(answer, Refusal)
    assert answer.code == "first_touch_on_a_contract"
    assert answer.sentence == "A contract is held to resolution; there is no path to touch."


def test_a_path_walked_from_some_other_price_is_refused() -> None:
    """Checking a stop against a path that started elsewhere answers a question nobody asked."""
    elsewhere = Position(**{**long_on().__dict__, "entry": 90.0, "stop": 87.0, "target": 96.0})

    with pytest.raises(ValueError, match="the reader's own position was walked"):
        first_touch(paths_of([100.0, 96.0]), elsewhere)


def test_a_path_walked_at_some_other_variability_is_refused() -> None:
    """The correction is built from the variability, so it has to be the path's own."""
    with pytest.raises(ValueError, match="the reader's own position was walked"):
        first_touch(paths_of([100.0, 96.0], daily_move=2.0), long_on(daily_move=1.0))


def test_first_touch_over_a_walked_path_reads_the_claim_arithmetic() -> None:
    """End to end from drawn worlds, with the variability switched off so the path is exact.

    Two worlds over ten days, weighing one and three: in the first the claim comes
    on day four, in the second it never does. The market gives the claim a quarter
    and the level gap is eight points, so the arriving world rises six points to
    106 on day four and the other gives two points back to 98.

    With a stop at 99 and a target at 106: the light world reaches the target, the
    heavy one is stopped. So the stop goes first in three quarters of the weight.
    """
    drawn = worlds_of(claims=["c"], on=[[4], [NEVER]], weight=[1.0, 3.0], days=10)
    moves = (
        ClaimMove(
            claim=PropositionId("c"), move=8.0, market_chance=0.25, market_chance_from="base_world"
        ),
    )
    paths = walk(drawn, moves, entry=ENTRY, daily_move=0.0, seed=1)

    answer = touched(paths, long_on(stop=99.0, target=106.0))

    assert answer.stop_first == pytest.approx(0.75)
    assert answer.target_first == pytest.approx(0.25)
    assert answer.stop_first_on.tolist() == [NEVER, 4]


# --- What their own risk budget implies -------------------------------------


def test_the_size_their_own_rule_implies_is_arithmetic_on_two_numbers_they_typed() -> None:
    """Entry 100, stop 95, budget two per cent.

    A five-point move is five per cent of the entry price, so putting two fifths of
    their capital in loses exactly two per cent of it when the stop is reached:
    `0.02 x 100 / 5 = 0.4`.
    """
    assert what_your_risk_budget_implies(long_on(stop=95.0)) == pytest.approx(0.4)


def test_a_tight_stop_implies_more_than_all_their_capital_and_says_so() -> None:
    """Entry 100, stop 99: one point is one per cent, so two per cent needs twice their capital.

    It is not clipped to one. What their own rule implies is more useful than a
    number quietly made to look reasonable.
    """
    assert what_your_risk_budget_implies(long_on(stop=99.0)) == pytest.approx(2.0)


def test_a_stop_at_the_entry_price_has_no_loss_to_size_against() -> None:
    """Nothing to divide by, and nothing a risk budget could mean."""
    with pytest.raises(ValueError, match="not a loss to size against"):
        what_your_risk_budget_implies(long_on(stop=ENTRY))


# --- Over worlds and positions nobody wrote by hand -------------------------


@a_few
@given(drawn=draws(claims=1, events_only=True), position=positions())
def test_touching_is_always_at_least_as_likely_as_finishing_beyond(
    drawn: object, position: Position
) -> None:
    """True by containment, whatever the path model: to finish past a level is to touch it."""
    assert isinstance(drawn, object)
    moves = (
        ClaimMove(
            claim=drawn.claims[0],  # type: ignore[attr-defined]
            move=2.0,
            market_chance=0.3,
            market_chance_from="base_world",
        ),
    )
    paths = walk(
        drawn,  # type: ignore[arg-type]
        moves,
        entry=position.entry,
        daily_move=position.daily_move,
        seed=7,
    )

    answer = touched(paths, position)

    assert answer.stop_touched >= answer.finished_beyond_the_stop - 1e-12
    assert answer.stop_first + answer.target_first + answer.neither == pytest.approx(1.0)
    assert answer.stop_first <= answer.stop_touched + 1e-12


# --- The window the two shares are over -------------------------------------


def test_first_touch_stops_at_the_reader_s_horizon() -> None:
    """The window is the reader's, not whatever window the drawn worlds happen to carry.

    One path over five days: 100, 101, 100, 99, 96. The stop is 97 and is reached
    on day four. A reader whose horizon is day two is out before that, so for them
    neither level is reached — and reading the whole five days would tell them they
    were stopped out of a trade they had already closed.
    """
    paths = paths_of([100.0, 101.0, 100.0, 99.0, 96.0])
    early = Position(**{**long_on().__dict__, "horizon": DAY_ZERO + timedelta(days=2)})
    late = Position(**{**long_on().__dict__, "horizon": DAY_ZERO + timedelta(days=4)})

    out_early = first_touch(paths, early)
    out_late = first_touch(paths, late)

    assert isinstance(out_early, FirstTouch) and isinstance(out_late, FirstTouch)
    assert out_early.neither == pytest.approx(1.0)
    assert out_early.stop_first == pytest.approx(0.0)
    assert out_late.stop_first == pytest.approx(1.0)


def test_the_answer_says_which_day_it_was_read_to() -> None:
    """Two shares over an unnamed window are two numbers nobody can check."""
    paths = paths_of([100.0, 101.0, 100.0, 99.0, 96.0])
    early = Position(**{**long_on().__dict__, "horizon": DAY_ZERO + timedelta(days=2)})

    answer = first_touch(paths, early)

    assert isinstance(answer, FirstTouch)
    assert answer.through == 2


def test_finishing_beyond_the_stop_is_read_on_the_horizon_and_not_at_the_end() -> None:
    """A trade closed on day two finished where it stood on day two."""
    paths = paths_of([100.0, 96.0, 101.0, 99.0, 96.0])
    early = Position(**{**long_on().__dict__, "horizon": DAY_ZERO + timedelta(days=2)})

    answer = first_touch(paths, early)

    assert isinstance(answer, FirstTouch)
    assert answer.finished_beyond_the_stop == pytest.approx(0.0), "on day two it stood at 101"
    assert answer.stop_touched == pytest.approx(1.0), "it was touched on day one on the way"


def test_a_horizon_the_paths_do_not_reach_is_refused() -> None:
    """Whatever built the draws built too short a window; answering a shorter question is worse."""
    with pytest.raises(ValueError, match="does not reach"):
        first_touch(paths_of([100.0, 96.0]), long_on())


def test_a_horizon_on_the_day_the_window_opens_is_refused() -> None:
    """A trade that is over before its first close has no path to touch."""
    same_day = Position(**{**long_on().__dict__, "horizon": DAY_ZERO})

    with pytest.raises(ValueError, match="at least one day"):
        first_touch(paths_of([100.0, 96.0]), same_day)
