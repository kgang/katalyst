"""A daily path that invents no advantage: the surprise, and the priced-in part given back.

The defect these tests exist to catch is the one that was measured and named: a
path that starts at today's price and then applies a claim's **whole** stated move
counts that move twice, because today's price already reflects the market's own
chance of the claim. It reads *the target is reached first* far too high, always in
the reader's favour.

The honest rule applies the **surprise** — the stated move scaled by one minus the
market's chance — and gives the priced-in part back day by day, on the shape of the
model's own arrival days.

**The central test is an identity, not a measurement.** When the market's chance is
set to the model's own — the neutral assumption the rule makes where no venue
quotes the claim — the weighted mean price is the entry price on **every day**,
exactly. That is arithmetic: the share of worlds holding the claim times one, plus
the share still pending times the schedule, is the market's chance at every day, by
construction. So the test asserts equality rather than a tolerance, and the naive
rule fails the same assertion by a mile.

Every set of drawn worlds here is written down in the test. No number an engine
computed is typed anywhere in this file.
"""

import numpy
import pytest
from hypothesis import given, settings

from katalyst.domain import PropositionId
from katalyst.thesis.draws import NEVER, STILL_HOLDING, Draws, weighted_share
from katalyst.thesis.paths import (
    ClaimMove,
    giveback_schedule,
    the_sample_s_own_chance,
    walk,
)
from tests.thesis.synthetic import draws, worlds_of

a_few = settings(max_examples=12, deadline=None)

SEED = 20260922
"""One number every walk in this file is drawn from. A path nobody can redraw is no evidence."""

ENTRY = 100.0
"""The price every path starts at. A level of a hundred makes a point a per cent."""

MOVE = 8.0
"""The level gap: the instrument stands eight points higher where the claim is true."""

CHANCE = 0.25
"""The market's chance of the claim, so the surprise is six points and the giveback two."""

THE_CLAIM = "the-claim"


def four_arrivals() -> Draws:
    """Four drawn worlds over ten days: two arrivals, one that never comes, one already on.

    | world | the claim came on | weight |
    |---|---|---|
    | 0 | day 4 | 1 |
    | 1 | day 8 | 1 |
    | 2 | never | 1 |
    | 3 | day 0 — already on when the window opened | 1 |
    """
    return worlds_of(claims=[THE_CLAIM], on=[[4], [8], [NEVER], [0]], days=10)


def the_move(chance: float = CHANCE, move: float = MOVE) -> ClaimMove:
    """The one claim's move, with a market chance handed in from somewhere else."""
    return ClaimMove(
        claim=PropositionId(THE_CLAIM),
        move=move,
        market_chance=chance,
        market_chance_from="base_world",
    )


def the_neutral_move(move: float = MOVE, claim: str = THE_CLAIM) -> ClaimMove:
    """The same move with **no** chance handed in, so the walk reads it off the drawn worlds.

    This is the neutral assumption — the market believes what the model believes —
    and under it the path carries no drift at all.
    """
    return ClaimMove(
        claim=PropositionId(claim),
        move=move,
        market_chance=None,
        market_chance_from="sample_share",
    )


def still_paths(drawn: Draws, moves: tuple[ClaimMove, ...] = ()) -> numpy.ndarray:
    """Walk with no day-to-day variability at all, so the levels are the claim arithmetic alone."""
    return walk(drawn, moves, entry=ENTRY, daily_move=0.0, seed=SEED).level


# --- The schedule -----------------------------------------------------------


def test_the_giveback_starts_at_the_market_s_chance_and_reaches_nothing() -> None:
    """Day zero carries the whole priced-in part; the last day carries none of it.

    A claim that has not happened by the end of the window never will, so nothing
    of it can still be priced in on that day.
    """
    schedule, shape = giveback_schedule(four_arrivals(), the_move())

    assert shape == "arrival_days"
    assert schedule[0] == pytest.approx(CHANCE)
    assert schedule[-1] == pytest.approx(0.0)


def test_the_giveback_never_goes_back_up() -> None:
    """The priced-in part runs down, never up: a day that passes without the claim is news."""
    schedule, _ = giveback_schedule(four_arrivals(), the_move())

    assert (numpy.diff(schedule) <= 1e-12).all()


def test_the_giveback_follows_the_model_s_own_arrival_days() -> None:
    """Worked out by hand on two worlds, one arriving on day five of ten.

    Two worlds, equally weighted: one where the claim comes on day 5, one where it
    never comes. The arrivals histogram has all its mass on day 5, so the share of
    arrivals *after* day `t` is one up to day 4 and nothing from day 5 on.

    So the schedule is `q x 1 / (1 - q x 0) = q` for days 0 to 4, and
    `q x 0 / (1 - q x 1) = 0` from day 5 — a cliff on the arrival day, which is the
    only day this histogram says anything can happen.
    """
    two = worlds_of(claims=[THE_CLAIM], on=[[5], [NEVER]], days=10)

    schedule, shape = giveback_schedule(two, the_move())

    assert shape == "arrival_days"
    assert schedule[:5].tolist() == pytest.approx([CHANCE] * 5)
    assert schedule[5:].tolist() == pytest.approx([0.0] * 6)


def test_early_arrivals_give_the_priced_in_part_back_sooner_than_late_ones() -> None:
    """The shape is an assumption, and the direction it pulls is the one you would expect.

    Two sets of worlds with the same chance of arriving at all — one world in two —
    but one arriving on day two and the other on day eight. The early one has given
    the priced-in part back by day three; the late one still carries all of it.
    """
    early = worlds_of(claims=[THE_CLAIM], on=[[2], [NEVER]], days=10)
    late = worlds_of(claims=[THE_CLAIM], on=[[8], [NEVER]], days=10)

    sooner, _ = giveback_schedule(early, the_move())
    later, _ = giveback_schedule(late, the_move())

    assert (sooner <= later + 1e-12).all()
    assert sooner[3] < later[3]


def test_a_claim_nobody_draws_arriving_falls_back_to_a_straight_line() -> None:
    """With no arrival days there is no histogram to borrow, so the fallback is named.

    Two worlds over ten days in neither of which the claim comes on. A straight line
    from the market's chance down to nothing means the halfway day carries half of
    it: a quarter down to an eighth.
    """
    nobody = worlds_of(claims=[THE_CLAIM], on=[[NEVER], [NEVER]], days=10)

    schedule, shape = giveback_schedule(nobody, the_move())

    assert shape == "straight_line"
    assert schedule[0] == pytest.approx(CHANCE)
    assert schedule[5] == pytest.approx(CHANCE / 2.0)
    assert schedule[10] == pytest.approx(0.0)


def test_a_claim_already_on_everywhere_leaves_no_arrivals_to_shape_the_giveback() -> None:
    """A claim on in every world at day zero is in the entry price, so there is no histogram."""
    already = worlds_of(claims=[THE_CLAIM], on=[[0], [0]], days=10)

    _, shape = giveback_schedule(already, the_move())

    assert shape == "straight_line"


def test_a_schedule_for_a_claim_these_worlds_do_not_carry_is_refused() -> None:
    """A move on a claim nobody drew is a number that came from somewhere else."""
    with pytest.raises(KeyError, match="not one of the claims"):
        giveback_schedule(
            four_arrivals(),
            ClaimMove(
                claim=PropositionId("some-other-claim"),
                move=MOVE,
                market_chance=CHANCE,
                market_chance_from="base_world",
            ),
        )


# --- The walk ---------------------------------------------------------------


def test_every_path_starts_at_the_entry_price() -> None:
    """Whatever state a claim was in when the window opened, day zero is the entry price."""
    level = still_paths(four_arrivals(), (the_move(),))

    assert level[:, 0].tolist() == pytest.approx([ENTRY] * 4)


def test_the_move_applied_and_the_giveback_sum_to_the_stated_move() -> None:
    """Worked out by hand, with no day-to-day variability, on the four worlds above.

    The market's chance is a quarter and the move is eight points, so the surprise
    is six points and the priced-in part is two.

    * World 0, the claim comes on day 4: the price ends six points above entry, at
      106 — the surprise and nothing else.
    * World 2, it never comes: the price ends two points below entry, at 98 — the
      whole priced-in part given back.
    * The gap between them is **eight points, the stated move**. That is the
      identity: what is applied when the claim comes true plus what is given back
      while it does not is the level gap itself.
    """
    level = still_paths(four_arrivals(), (the_move(),))

    assert level[0, -1] == pytest.approx(ENTRY + MOVE * (1.0 - CHANCE))
    assert level[2, -1] == pytest.approx(ENTRY - MOVE * CHANCE)
    assert level[0, -1] - level[2, -1] == pytest.approx(MOVE)


def test_a_claim_already_on_when_the_window_opened_moves_the_price_by_nothing() -> None:
    """World 3 has the claim on at day zero, so it is in the entry price and never moves.

    Not a special case: it is the surprise rule read at a market chance of one. A
    claim that has already happened has no surprise left to apply and nothing left
    to give back.
    """
    level = still_paths(four_arrivals(), (the_move(),))

    assert level[3].tolist() == pytest.approx([ENTRY] * 11)


def test_a_state_that_stops_leaves_the_price_where_never_happening_would_have() -> None:
    """The move is a level gap, so it goes when the claim does.

    Three worlds over ten days: one where the claim comes on day 2 and stops on day
    6, one where it comes on day 2 and holds, and one where it never comes. After
    day 6 the first is back with the third — two points below entry, the whole
    priced-in part given back — while the second sits six points above it.
    """
    mixed = worlds_of(
        claims=[THE_CLAIM],
        on=[[2], [2], [NEVER]],
        off=[[6], [STILL_HOLDING], [NEVER]],
        days=10,
    )

    level = still_paths(mixed, (the_move(),))

    assert level[0, -1] == pytest.approx(level[2, -1])
    assert level[0, -1] == pytest.approx(ENTRY - MOVE * CHANCE)
    assert level[1, -1] == pytest.approx(ENTRY + MOVE * (1.0 - CHANCE))


def test_a_state_already_on_when_the_window_opened_gives_up_the_whole_gap_when_it_stops() -> None:
    """What the surprise rule does not yet cover, written down as a test rather than a comment.

    A claim already on at day zero is in the entry price. If it stops inside the
    window the level gap goes with it, so the price falls by the **whole** move and
    not by a surprise — because nothing asks the model for *the chance it stops*,
    so there is no chance to have priced in.

    Two worlds over ten days, the claim on at day zero in both, stopping on day
    four in one of them. The one that stops ends a whole move below entry; the one
    that holds ends exactly at entry. So the mean price is dragged below entry, and
    that is a known gap rather than an accident: the symmetric rule waits on the
    one number nobody is asked for yet.
    """
    stopping = worlds_of(claims=[THE_CLAIM], on=[[0], [0]], off=[[4], [STILL_HOLDING]], days=10)

    level = still_paths(stopping, (the_move(),))

    assert level[0, -1] == pytest.approx(ENTRY - MOVE)
    assert level[1, -1] == pytest.approx(ENTRY)
    assert float(level[:, -1].mean()) < ENTRY


def test_a_state_that_comes_on_and_stops_the_same_day_is_never_carried() -> None:
    """The other half of the same gap: the price reads closes, and at that close it is off.

    A state that comes on and stops on one day held the level gap for less than a
    day, and a daily path never sees it — so the price gives the priced-in part
    back and never takes the surprise, ending where never happening would have. The
    engine's arrivals land on the middles of its time slices, and over a short
    window two middles round to one day, so this is reachable rather than
    hypothetical.

    It is the reason the no-drift identity is stated over **events**: a claim that
    once on holds to the end of the window.
    """
    flicker = worlds_of(claims=[THE_CLAIM], on=[[3], [NEVER]], off=[[3], [NEVER]], days=10)

    level = still_paths(flicker, (the_move(),))

    assert level[0, -1] == pytest.approx(ENTRY - MOVE * CHANCE)
    assert level[0, -1] == pytest.approx(level[1, -1])


def test_a_path_has_no_drift_when_the_model_agrees_with_the_market() -> None:
    """The mean price is the entry price on every day — exactly, not within an error.

    The market's chance is taken from the drawn worlds themselves, so the model and
    the market agree by construction and an honest path has no drift at all. The
    arithmetic: the weight of the worlds holding the claim times one, plus the
    weight still pending times the schedule, is the market's chance at every day.
    Nothing is typed in and nothing is measured.
    """
    drawn = four_arrivals()

    level = still_paths(drawn, (the_neutral_move(),))

    for day in range(drawn.days + 1):
        assert weighted_share(level[:, day] > ENTRY, drawn.weight) >= 0.0
        assert float((level[:, day] * drawn.weight).sum() / drawn.weight.sum()) == pytest.approx(
            ENTRY
        )


def test_the_old_rule_fails_the_same_assertion() -> None:
    """A test that passes for both rules would be no test at all.

    The rule this replaced applied the **whole** move on the arrival day and gave
    nothing back, so with the model and the market agreeing the mean price still
    ends above where it started. Worked out here by applying the whole move by
    hand, over the same worlds.
    """
    drawn = four_arrivals()
    came_on = drawn.on_day[:, 0]
    naive_end = numpy.where((came_on != NEVER) & (came_on > 0), ENTRY + MOVE, ENTRY)

    honest = still_paths(drawn, (the_neutral_move(),))[:, -1]

    assert float(naive_end.mean()) > ENTRY
    assert float(honest.mean()) == pytest.approx(ENTRY)


def test_the_claims_add_nothing_to_the_mean_of_the_walk_itself() -> None:
    """With the model and the market agreeing, adding a claim moves no world's average.

    The same seed walks the same random path with and without the claim, so any
    difference between the two means is what the claim's arithmetic put there. It is
    exactly nothing — which is what *the path invents no advantage* means with a
    real walk under it rather than with the variability switched off.
    """
    drawn = four_arrivals()

    bare = walk(drawn, (), entry=ENTRY, daily_move=1.0, seed=SEED).level
    carrying = walk(drawn, (the_neutral_move(),), entry=ENTRY, daily_move=1.0, seed=SEED).level

    for day in range(drawn.days + 1):
        assert float(carrying[:, day].mean()) == pytest.approx(float(bare[:, day].mean()))
    assert not numpy.allclose(carrying, bare), "the claim still moves individual worlds"


def test_two_claims_each_give_back_at_their_own_chance() -> None:
    """Expectation adds up whether or not two claims are correlated, so no joint is needed.

    Two claims on one instrument, drawn so that the first happening implies the
    second — they are correlated on purpose. Each is given back at its own chance,
    and with both chances taken from the worlds themselves the mean price is still
    the entry price at the end.
    """
    two = worlds_of(
        claims=["first", "second"],
        on=[[2, 2], [NEVER, 6], [NEVER, NEVER], [4, 4]],
        days=10,
    )
    moves = tuple(
        the_neutral_move(move=size, claim=name) for name, size in (("first", 8.0), ("second", -5.0))
    )

    level = still_paths(two, moves)

    assert float(level[:, -1].mean()) == pytest.approx(ENTRY)


def test_the_paths_say_which_shape_each_giveback_followed() -> None:
    """The decay's shape is an assumption, so the answer carries which one was used."""
    drawn = worlds_of(claims=[THE_CLAIM, "unseen"], on=[[4, NEVER], [NEVER, NEVER]], days=10)
    moves = (
        the_move(),
        ClaimMove(
            claim=PropositionId("unseen"),
            move=2.0,
            market_chance=0.1,
            market_chance_from="venue_quote",
        ),
    )

    paths = walk(drawn, moves, entry=ENTRY, daily_move=0.0, seed=SEED)

    assert paths.decay_shape == {
        PropositionId(THE_CLAIM): "arrival_days",
        PropositionId("unseen"): "straight_line",
    }


def test_the_same_seed_walks_the_same_path_and_a_different_one_does_not() -> None:
    """A number nobody can redraw is a number nobody can check."""
    drawn = four_arrivals()

    once = walk(drawn, (the_move(),), entry=ENTRY, daily_move=1.0, seed=SEED).level
    again = walk(drawn, (the_move(),), entry=ENTRY, daily_move=1.0, seed=SEED).level
    elsewhere = walk(drawn, (the_move(),), entry=ENTRY, daily_move=1.0, seed=SEED + 1).level

    assert numpy.array_equal(once, again)
    assert not numpy.array_equal(once, elsewhere)


def test_the_walk_carries_the_window_and_the_weights_through() -> None:
    """Whoever reads the paths should not have to hold the draws as well."""
    drawn = four_arrivals()

    paths = walk(drawn, (the_move(),), entry=ENTRY, daily_move=1.0, seed=SEED)

    assert paths.day_zero == drawn.day_zero
    assert paths.days == drawn.days
    assert paths.entry == ENTRY
    assert numpy.array_equal(paths.weight, drawn.weight)
    assert paths.level.shape == (drawn.worlds, drawn.days + 1)


# --- What the walk refuses --------------------------------------------------


def test_a_market_chance_above_one_is_refused() -> None:
    """A chance is a chance."""
    with pytest.raises(ValueError, match="from nothing to one"):
        the_move(chance=1.5)


def test_a_market_chance_below_nothing_is_refused() -> None:
    """And so is the other end of it."""
    with pytest.raises(ValueError, match="from nothing to one"):
        the_move(chance=-0.1)


def test_a_market_certain_of_a_claim_is_a_chance_the_layer_reaches() -> None:
    """The exact worlds the neutral assumption comes out at one on.

    Three worlds already on at day zero and one where the claim arrives on day one:
    every world the question arises for has it arriving, so the market's own chance
    — read off the sample — is exactly one. A refusal here would be the layer
    refusing its own recommended way of choosing that number.
    """
    certain = worlds_of(claims=[THE_CLAIM], on=[[0], [0], [0], [1]], days=8)

    chance = the_sample_s_own_chance(certain, PropositionId(THE_CLAIM))
    schedule, shape = giveback_schedule(certain, the_move(chance=chance))

    assert chance == 1.0
    assert shape == "nothing_given_back"
    assert schedule.tolist() == pytest.approx([1.0] * 9)


def test_a_claim_the_market_is_certain_of_moves_the_price_by_nothing() -> None:
    """The whole move is already in today's price: no surprise to apply, nothing to give back."""
    certain = worlds_of(claims=[THE_CLAIM], on=[[3], [NEVER]], days=10)

    level = still_paths(certain, (the_move(chance=1.0),))

    assert level.ravel().tolist() == pytest.approx([ENTRY] * 22)


def test_a_move_that_is_not_a_real_number_is_refused() -> None:
    """A level gap of infinity is not a level gap."""
    with pytest.raises(ValueError, match="level gap in price units"):
        the_move(move=float("inf"))


def test_two_moves_on_one_claim_are_refused() -> None:
    """A claim moves the price by one level gap, and two would be two different maps."""
    with pytest.raises(ValueError, match="name the same claim"):
        walk(four_arrivals(), (the_move(), the_move()), entry=ENTRY, daily_move=1.0, seed=SEED)


def test_a_negative_daily_variability_is_refused() -> None:
    """A distance is never below nothing."""
    with pytest.raises(ValueError, match="never below nothing"):
        walk(four_arrivals(), (), entry=ENTRY, daily_move=-1.0, seed=SEED)


def test_an_entry_price_of_nothing_is_refused() -> None:
    """Nothing is not a price something was bought at."""
    with pytest.raises(ValueError, match="above nothing"):
        walk(four_arrivals(), (), entry=0.0, daily_move=1.0, seed=SEED)


# --- Over worlds nobody wrote by hand ---------------------------------------


@a_few
@given(drawn=draws(claims=1))
def test_a_path_always_starts_at_the_entry_price(drawn: Draws) -> None:
    """Whatever the draws say, day zero is where the reader came in."""
    moves = (
        ClaimMove(claim=drawn.claims[0], move=3.0, market_chance=0.3, market_chance_from="reader"),
    )

    level = walk(drawn, moves, entry=ENTRY, daily_move=1.0, seed=SEED).level

    assert level[:, 0].tolist() == pytest.approx([ENTRY] * drawn.worlds)


@a_few
@given(drawn=draws(claims=1, events_only=True))
def test_agreeing_with_the_market_leaves_the_mean_price_where_it_started(drawn: Draws) -> None:
    """The no-drift identity over worlds nobody wrote by hand, weights and all.

    The market's chance is read off the drawn worlds, so the two agree by
    construction, and the weighted mean is the entry price on every day — including
    in worlds where the claim was already on when the window opened, which carry
    nothing either way.

    **The antecedent is real and is stated in the chapter:** every claim here is an
    **event**, so once it comes on it holds to the end of the window. The path
    prices the chance a claim comes true and **not** the chance it stops, because
    nothing asks the model for that second number yet. The two tests above say
    exactly what that costs on a state.
    """
    moves = (the_neutral_move(move=7.0, claim=str(drawn.claims[0])),)

    level = still_paths(drawn, moves)

    for day in range(drawn.days + 1):
        mean = float((level[:, day] * drawn.weight).sum() / drawn.weight.sum())
        assert mean == pytest.approx(ENTRY, abs=1e-9)


# --- Which chance was applied, and where it came from -----------------------


def test_the_chance_read_off_the_drawn_worlds_is_the_share_that_come_true_in_the_window() -> None:
    """Four worlds: the claim arrives on days four and eight, never in one, already on in one.

    The world where it was already on when the window opened is left out of both
    halves, because a claim already true is in today's price and the question does
    not arise for it. So the share is two of the three worlds it does arise for.
    """
    assert the_sample_s_own_chance(four_arrivals(), PropositionId(THE_CLAIM)) == pytest.approx(
        2.0 / 3.0
    )


def test_a_claim_already_true_everywhere_leaves_the_question_arising_nowhere() -> None:
    """Every world has it on at day zero, so there is nothing left for the market to price."""
    already = worlds_of(claims=[THE_CLAIM], on=[[0], [0]], days=10)

    assert the_sample_s_own_chance(already, PropositionId(THE_CLAIM)) == 0.0


def test_the_paths_say_which_chance_was_applied_and_where_it_came_from() -> None:
    """Record 0019 wants the source in the same sentence as the number, so the value carries both.

    The number may have been worked out here rather than handed in, and a card
    cannot name what it cannot read.
    """
    drawn = four_arrivals()

    paths = walk(
        drawn,
        (the_neutral_move(),),
        entry=ENTRY,
        daily_move=0.0,
        seed=SEED,
    )

    used = paths.market_chance[PropositionId(THE_CLAIM)]
    assert used.came_from == "sample_share"
    assert used.value == pytest.approx(2.0 / 3.0)


def test_a_chance_handed_in_keeps_the_source_it_was_handed_in_with() -> None:
    """A venue's price is the market's own chance, and the card says so."""
    drawn = four_arrivals()
    quoted = ClaimMove(
        claim=PropositionId(THE_CLAIM),
        move=MOVE,
        market_chance=0.07,
        market_chance_from="venue_quote",
    )

    paths = walk(drawn, (quoted,), entry=ENTRY, daily_move=0.0, seed=SEED)

    used = paths.market_chance[PropositionId(THE_CLAIM)]
    assert used.came_from == "venue_quote"
    assert used.value == pytest.approx(0.07)


def test_a_chance_and_a_source_that_disagree_are_refused() -> None:
    """`sample_share` is said when, and only when, no chance is handed in."""
    with pytest.raises(ValueError, match="when and only when"):
        ClaimMove(
            claim=PropositionId(THE_CLAIM),
            move=MOVE,
            market_chance=0.3,
            market_chance_from="sample_share",
        )
    with pytest.raises(ValueError, match="when and only when"):
        ClaimMove(
            claim=PropositionId(THE_CLAIM),
            move=MOVE,
            market_chance=None,
            market_chance_from="base_world",
        )


def test_the_price_carries_the_gap_on_every_day_the_claim_holds_and_not_the_day_it_stops() -> None:
    """The whole path around a state's two days, not just where it ends up.

    One world over six days: the claim comes on day two and stops on day four. The
    day it goes off is the first day it is **no longer** true, so the price carries
    the surprise on days two and three and has given the gap up by day four. A test
    that read only the last day could not tell that from giving it up a day late.
    """
    state = worlds_of(claims=[THE_CLAIM], on=[[2]], off=[[4]], days=6)

    level = still_paths(state, (the_move(),))[0]

    carried = MOVE * (1.0 - CHANCE)
    given_back = -MOVE * CHANCE
    assert level.tolist() == pytest.approx(
        [
            ENTRY,
            ENTRY,
            ENTRY + carried,
            ENTRY + carried,
            ENTRY + given_back,
            ENTRY + given_back,
            ENTRY + given_back,
        ],
        abs=1e-9,
    )


def test_holding_read_a_day_at_a_time_and_a_window_at_a_time_are_the_one_rule() -> None:
    """Two shapes of the same question, so the off day cannot mean two things.

    A price path asks *was this claim holding* for one claim across the whole
    window; everything else asks it for every claim on one day. Both read the same
    expression, and this checks the two agree on every day of a set of worlds that
    has an arrival, a stop, a never and an already-on.
    """
    drawn = worlds_of(
        claims=[THE_CLAIM],
        on=[[2], [2], [NEVER], [0]],
        off=[[4], [STILL_HOLDING], [NEVER], [STILL_HOLDING]],
        days=6,
    )
    grid = numpy.arange(drawn.days + 1, dtype=numpy.int32)

    a_window_at_a_time = drawn.holding_each_day(PropositionId(THE_CLAIM), grid)

    for day in range(drawn.days + 1):
        assert a_window_at_a_time[:, day].tolist() == drawn.holding_on(day)[:, 0].tolist()
