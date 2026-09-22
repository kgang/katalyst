"""The rate model — writer A.

Every test here asserts an identity, a direction or an ordering on a map the test
builds. Not one number an engine worked out is written down.

The two words this file uses over and over:

*the claim's own chance* — the chance a claim reaches its deadline with none of the
map's causes on. *the chance with one cause on* — the chance it reaches its deadline
with that one cause on from day zero and no other. Those are the only two numbers
the new engine asks a person for, and the whole of `rates.py` is turning them into
rates and back again.
"""

import ast
import inspect
import textwrap
from collections.abc import Mapping, Sequence
from datetime import date, timedelta

import numpy
import pytest

from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.graph import Graph
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition, Resolution
from katalyst.domain.rates import (
    MOST_NUMBERS_AT_ONCE,
    POINTS_IN_A_SLICE,
    SLICES,
    ClaimShapes,
    Window,
    _push_at,
    added_up,
    clamped,
    rates_of,
    shapes_of,
    stated_chance_with,
    window_of,
)

DAY_ZERO = date(2026, 10, 1)


def _claim(identifier: str, *, prior: float = 0.3, days: int = 60) -> Proposition:
    """One plain claim, with the chance it comes true on its own and the day it is judged."""
    belief = Belief(p=prior, lo=max(0.0, prior - 0.1), hi=min(1.0, prior + 0.1), owner="model")
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind="event",
        persistence="event",
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=days),
        ),
        prior=belief,
        beliefs=Beliefs(model=belief),
    )


def _arrow(
    source: str,
    target: str,
    *,
    strength: float = 1.0,
    mode: str = "trigger",
    shape: str = "step",
    lag: float = 0.0,
    half_life: float | None = None,
) -> Link:
    """One plain arrow, with every field a test here might want to vary."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode=mode,  # type: ignore[arg-type]
        strength=strength,
        lag=lag,
        shape=shape,  # type: ignore[arg-type]
        half_life=half_life,
        rationale="The first claim moves the second one, for a stated reason.",
        provenance="argued",
    )


def _map(*claims: Proposition, arrows: tuple[Link, ...] = ()) -> Graph:
    """A whole small map, with the first claim as the one it started from."""
    return Graph(id="small", propositions=claims, links=arrows, hypothesis_id=claims[0].id)


def _shapes(
    claim: Proposition,
    arrows: Sequence[Link],
    window: Window,
    *,
    persistence: str = "event",
    kinds: Mapping[str, str] | None = None,
    days: Mapping[str, int] | None = None,
) -> ClaimShapes:
    """One claim's shapes, with each arrow's source described by kind and resolve-by day.

    A source not named in `kinds` is an event; one not named in `days` is judged on
    the last day of the map's window.
    """
    kinds = kinds or {}
    days = days or {}
    return shapes_of(
        claim,
        arrows,
        {one.id: kinds.get(one.source, "event") for one in arrows},  # type: ignore[misc]
        {one.id: days.get(one.source, window.days) for one in arrows},
        window,
        persistence=persistence,  # type: ignore[arg-type]
    )


def _one(value: float) -> numpy.ndarray:
    """One version's worth of one number."""
    return numpy.array([value])


def _chance_by_the_deadline(added_up_rate: numpy.ndarray) -> numpy.ndarray:
    """Turn a rate added up over a whole window into the chance the claim happened."""
    return 1.0 - numpy.exp(-added_up_rate)


# --- The window and its slices ---------------------------------------------


def test_a_window_runs_from_day_zero_to_the_last_day_anything_is_judged() -> None:
    near, far = _claim("near", days=20), _claim("far", days=55)
    window = window_of(_map(near, far), DAY_ZERO, slices=4)

    assert window.days == (far.resolution.by - DAY_ZERO).days
    assert window.edges[0] == 0.0
    assert window.edges[-1] == float(window.days)
    assert len(window.edges) == window.slices + 1


def test_a_claim_is_cut_from_its_own_deadline_and_from_nothing_else_on_the_map() -> None:
    early = _claim("early", days=20)
    on_its_own = window_of(_map(early), DAY_ZERO, slices=4)
    beside_a_later_one = window_of(_map(early, _claim("far", days=365)), DAY_ZERO, slices=4)

    assert on_its_own.days != beside_a_later_one.days
    mine = _shapes(early, (), on_its_own)
    still_mine = _shapes(early, (), beside_a_later_one)

    # The map got twelve times longer and this claim's grid did not move a bit.
    assert numpy.array_equal(mine.edges, still_mine.edges)
    assert numpy.array_equal(mine.middle_day, still_mine.middle_day)
    assert numpy.array_equal(mine.width, still_mine.width)
    assert numpy.array_equal(mine.points, still_mine.points)

    # And the claim's own slices cover its own window exactly: every slice the same
    # width, the last ending on its deadline, and nothing counted past it.
    assert mine.deadline == (early.resolution.by - DAY_ZERO).days
    assert float(mine.width.sum()) == float(mine.deadline)
    assert len(set(numpy.round(mine.width, 12).tolist())) == 1
    assert float(mine.edges[-1]) == float(mine.deadline)
    assert mine.points.shape == (on_its_own.slices, POINTS_IN_A_SLICE)
    assert numpy.all(mine.points < mine.deadline)


def test_a_claim_judged_before_day_zero_has_no_window_at_all() -> None:
    past = _claim("past", days=-9)
    window = window_of(_map(past, _claim("later", days=30)), DAY_ZERO, slices=4)

    assert window.days == 30
    shapes = _shapes(past, (), window)
    assert shapes.deadline == 0
    assert float(shapes.width.sum()) == 0.0


def test_an_arrival_is_taken_at_the_middle_of_its_slice() -> None:
    window = window_of(_map(_claim("alone", days=40)), DAY_ZERO, slices=4)
    effect, cause = _claim("effect", days=40), _claim("cause", days=40)
    arrow = _arrow("cause", "effect")
    shapes = _shapes(effect, (arrow,), window)

    starts, finishes = shapes.edges[:-1], shapes.edges[1:]
    assert numpy.array_equal(shapes.middle_day[:-1], 0.5 * (starts + finishes))
    assert numpy.isinf(shapes.middle_day[-1])
    # The middle of a slice is neither of its ends, which is the whole point of the
    # convention: taking an arrival at the slice's end is worth about three
    # hundredths of a point on a claim's number at twenty-four slices.
    assert not numpy.any(shapes.middle_day[:-1] == finishes)
    assert not numpy.any(shapes.middle_day[:-1] == starts)

    pushed = shapes.carried[0].for_each_reading()
    for arrived in range(window.slices):
        pushing = pushed[arrived] > 0.0
        assert numpy.array_equal(pushing, shapes.points >= shapes.middle_day[arrived])
    # The last index of the arrival axis means the cause never came, and a cause that
    # never came pushes nothing.
    assert not numpy.any(pushed[window.slices])
    assert cause.id == arrow.source


def test_a_cause_judged_sooner_than_its_effect_is_read_on_its_own_slices() -> None:
    window = window_of(_map(_claim("effect", days=40)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=40)
    arrow = _arrow("cause", "effect")
    shapes = _shapes(effect, (arrow,), window, days={"cause": 20})

    # The cause is judged halfway through the effect's window, so the day that stands
    # for its last slice is halfway through the effect's grid, not at the end of it.
    pushed = shapes.carried[0].for_each_reading()
    last = float(pushed[window.slices - 1].argmax())
    assert last >= 0.0
    first_push = shapes.points[pushed[window.slices - 1] > 0.0].min()
    assert first_push < shapes.middle_day[window.slices - 1]
    assert first_push > shapes.middle_day[window.slices // 2 - 1]


# --- What an arrow's push looks like over time ------------------------------


def test_the_three_shapes_are_the_ones_an_arrow_already_means() -> None:
    lag, half_life = 4.0, 3.0
    days = numpy.array([-1.0, 0.0, lag / 2.0, lag, lag + half_life, lag + 2.0 * half_life])

    step = _push_at(_arrow("a", "b", shape="step", lag=lag), days)
    assert set(numpy.unique(step)) == {0.0, 1.0}
    assert numpy.array_equal(step == 0.0, days < lag)

    ramp = _push_at(_arrow("a", "b", shape="ramp", lag=lag), days)
    assert float(ramp[0]) == 0.0
    assert float(ramp[2]) == 0.5  # halfway across the delay is half of full size
    assert numpy.all(ramp[3:] == 1.0)

    spike = _push_at(_arrow("a", "b", shape="impulse", lag=lag, half_life=half_life), days)
    assert float(spike[3]) == 1.0
    assert float(spike[4]) == 0.5  # one half-life after it lands
    assert float(spike[5]) == 0.25  # two half-lives after it lands
    assert numpy.all(spike[:3] == 0.0)

    # A ramp with no delay has no days to climb over, so it is a step; and a spike
    # that does not say how fast it fades holds rather than dividing by nothing.
    flat = _push_at(_arrow("a", "b", shape="ramp", lag=0.0), days)
    assert numpy.array_equal(flat, _push_at(_arrow("a", "b", shape="step", lag=0.0), days))
    for broken in (None, 0.0):
        held = _push_at(_arrow("a", "b", shape="impulse", lag=lag, half_life=broken), days)
        assert numpy.array_equal(held, step)


def test_a_sustain_arrow_out_of_a_state_is_dead_once_its_cause_stops_holding() -> None:
    window = window_of(_map(_claim("effect", days=40)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=40)
    keeps_pushing = _arrow("cause", "effect", mode="trigger")
    dies_with_it = _arrow("other", "effect", mode="sustain")
    shapes = _shapes(
        effect,
        (keeps_pushing, dies_with_it),
        window,
        kinds={"cause": "state", "other": "state"},
    )

    # A trigger arrow reads the day its cause came on and nothing else, so its push
    # is held for each arrival slice alone.
    triggered = shapes.carried[0].for_each_reading()
    assert not shapes.carried[0].whole_stretch
    assert triggered.shape == (window.slices + 1, window.slices, POINTS_IN_A_SLICE)
    # A sustain arrow out of a state reads the whole stretch, so its push is held for
    # each pair of *came on here, went off there*.
    sustained = shapes.carried[1].for_each_reading()
    assert shapes.carried[1].whole_stretch
    assert sustained.shape == (
        window.slices + 1,
        window.slices + 1,
        window.slices,
        POINTS_IN_A_SLICE,
    )

    came_on, still_holding = 0, window.slices
    alive = sustained[came_on, still_holding]
    assert numpy.array_equal(alive, triggered[came_on])
    for went_off in range(window.slices):
        stopped = sustained[came_on, went_off]
        gone = shapes.points >= shapes.middle_day[went_off]
        assert numpy.all(stopped[gone] == 0.0)
        assert numpy.array_equal(stopped[~gone], alive[~gone])


def test_a_sustain_arrow_out_of_an_event_reads_one_moment_like_any_other_arrow() -> None:
    window = window_of(_map(_claim("effect", days=40)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=40)
    sustained = _arrow("cause", "effect", mode="sustain")
    triggered = _arrow("other", "effect", mode="trigger")
    shapes = _shapes(effect, (sustained, triggered), window)

    assert numpy.array_equal(
        shapes.carried[0].for_each_reading(), shapes.carried[1].for_each_reading()
    )


# --- Which of the three things an arrow does --------------------------------


def test_the_number_stated_for_an_arrow_puts_it_in_one_of_three_lists() -> None:
    window = window_of(_map(_claim("effect", days=40)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=40)
    up = _arrow("up", "effect", strength=1.2)
    down = _arrow("down", "effect", strength=-1.2)

    own = _one(effect.prior.p)
    assert float(stated_chance_with(own, _one(up.strength))[0]) > float(own[0])
    assert float(stated_chance_with(own, _one(down.strength))[0]) < float(own[0])

    as_event = _shapes(effect, (up, down), window)
    assert as_event.helps == (0,)
    assert as_event.holds_back == (1,)
    assert as_event.ends == ()

    as_state = _shapes(effect, (up, down), window, persistence="state")
    assert as_state.helps == (0,)
    assert as_state.holds_back == ()
    assert as_state.ends == (1,)

    assert as_event.arrows == (up.id, down.id) == as_state.arrows


def test_a_claim_a_map_calls_certain_or_impossible_still_sorts_its_arrows_by_their_sign() -> None:
    """The floor under the log-odds scale must not decide which list an arrow goes in.

    An arrow's number is read through the log-odds scale — the logarithm of the
    ratio of a chance to its opposite — which has no room for exactly nought or
    exactly one, so it is clipped a hair inside both. A claim's own stated chance
    is not clipped: a map may say a thing is **certain** (one) or **impossible**
    (nought), and no rule forbids it.

    Compared raw against clipped, the floor wins over the arrow. Every arrow that
    helps a certain claim then comes out fractionally below it and is filed among
    the arrows that hold it back — which is the one list whose cost multiplies,
    three such arrows costing fifteen thousand combinations instead of one — and
    every arrow that holds an impossible claim back is filed among those that help.
    Neither answer is wrong; the cost is (review of 2026-09-22, should-fix 5).

    So both sides are read the same way, and this is the test that says so: the sign
    of the push decides, at a stated chance of one, of nought, and in between.
    """
    for chance in (1.0, 0.0, 0.5):
        claim = _claim("effect", prior=chance, days=40)
        window = window_of(_map(claim), DAY_ZERO, slices=4)
        up = _arrow("up", "effect", strength=1.2)
        down = _arrow("down", "effect", strength=-1.2)

        as_event = _shapes(claim, (up, down), window)
        assert as_event.helps == (0,), (
            f"an arrow that pushes a claim upward is not among the arrows that help it, "
            f"on a claim the map states at {chance}"
        )
        assert as_event.holds_back == (1,), (
            f"an arrow that pushes a claim downward is not among the arrows that hold it "
            f"back, on a claim the map states at {chance}"
        )


def test_the_bridge_moves_the_odds_by_the_push_and_leaves_them_alone_at_nothing() -> None:
    own = numpy.array([0.1, 0.3, 0.6, 0.9])
    nothing = stated_chance_with(own, numpy.zeros(4))
    assert numpy.allclose(nothing, own, atol=1e-12)

    push = numpy.full(4, 0.7)
    moved = stated_chance_with(own, push)
    odds_before = own / (1.0 - own)
    odds_after = moved / (1.0 - moved)
    assert numpy.allclose(odds_after / odds_before, numpy.exp(push), atol=1e-12)

    # A chance of exactly nought or exactly one has no odds; both are allowed on a
    # map, and both come back inside the range rather than as infinity.
    certain = stated_chance_with(numpy.array([0.0, 1.0]), numpy.array([2.0, -2.0]))
    assert numpy.all(numpy.isfinite(certain))
    assert numpy.all((certain >= 0.0) & (certain <= 1.0))


# --- The calibration --------------------------------------------------------


def test_the_calibration_reproduces_the_stated_chance() -> None:
    window = window_of(_map(_claim("alone", days=60)), DAY_ZERO, slices=8)
    alone = _claim("alone", prior=0.3, days=60)
    shapes = _shapes(alone, (), window)

    own = numpy.array([0.05, 0.3, 0.72, 0.99])
    rates = rates_of(shapes, own, {}, persistence="event")
    whole_window = rates.leak * float(shapes.width.sum())

    assert numpy.allclose(_chance_by_the_deadline(whole_window), own, atol=1e-12)
    # Nothing is searched for. The calibration holds no loop that narrows in on an
    # answer: every rate comes out of one formula, which is what closed form means.
    written = ast.parse(textwrap.dedent(inspect.getsource(rates_of)))
    assert [node for node in ast.walk(written) if isinstance(node, ast.While)] == []


def test_an_arrow_alone_reproduces_its_own_stated_chance() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=8)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4)
    holding = _arrow("holds", "effect", strength=-1.1)

    own = numpy.array([0.2, 0.3, 0.4])
    with_help = numpy.array([0.5, 0.62, 0.77])
    with_hold = numpy.array([0.04, 0.06, 0.09])

    as_event = _shapes(effect, (helping, holding), window)
    rates = rates_of(as_event, own, {0: with_help, 1: with_hold}, persistence="event")
    window_days = float(as_event.width.sum())

    # A helping arrow adds its own rate on top of the leak, from day zero.
    alone = rates.leak * window_days + rates.helps[0] * as_event.area[0]
    assert numpy.allclose(_chance_by_the_deadline(alone), with_help, atol=1e-12)

    # A holding-back arrow scales the rate down while it is on, again from day zero.
    assert not numpy.any(rates.saturated[1])
    held = rates.leak * (window_days - (1.0 - rates.leaves[1]) * as_event.area[1])
    assert numpy.allclose(_chance_by_the_deadline(held), with_hold, atol=1e-12)

    # On a state the same low number ends the claim instead, and what it reproduces
    # is the chance the state stops.
    as_state = _shapes(effect, (helping, holding), window, persistence="state")
    stopping = rates_of(as_state, own, {0: with_help, 1: with_hold}, persistence="state")
    stops = stopping.ends[1] * as_state.area[1]
    assert numpy.allclose(_chance_by_the_deadline(stops), 1.0 - with_hold / own, atol=1e-12)


def test_two_causes_add_as_independent_routes() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=8)
    effect = _claim("effect", prior=0.3, days=60)
    first = _arrow("first", "effect", strength=1.4)
    second = _arrow("second", "effect", strength=0.9, shape="impulse", half_life=12.0)

    own = numpy.array([0.1, 0.3])
    with_first = numpy.array([0.4, 0.55])
    with_second = numpy.array([0.25, 0.48])

    shapes = _shapes(effect, (first, second), window)
    rates = rates_of(shapes, own, {0: with_first, 1: with_second}, persistence="event")

    both = (
        rates.leak * float(shapes.width.sum())
        + rates.helps[0] * shapes.area[0]
        + rates.helps[1] * shapes.area[1]
    )
    together = _chance_by_the_deadline(both)

    # Each cause is an independent route: the chance neither of them brings the claim
    # about is the product of the chances that neither severally does, over and above
    # what the claim manages on its own.
    routes = 1.0 - (1.0 - with_first) * (1.0 - with_second) / (1.0 - own)
    assert numpy.allclose(together, routes, atol=1e-12)
    assert numpy.all(together < 1.0 - (1.0 - with_first) * (1.0 - with_second))


def test_a_version_that_redraws_a_number_the_other_way_pushes_nothing() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=8)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4)
    holding = _arrow("holds", "effect", strength=-1.1)

    own = numpy.array([0.3, 0.3])
    # The second version draws each arrow's number the wrong side of the claim's own.
    with_help = numpy.array([0.6, 0.1])
    with_hold = numpy.array([0.1, 0.6])

    shapes = _shapes(effect, (helping, holding), window)
    rates = rates_of(shapes, own, {0: with_help, 1: with_hold}, persistence="event")

    assert float(rates.helps[0][1]) == 0.0  # helps nothing rather than holding back
    assert float(rates.leaves[1][1]) == 1.0  # leaves the whole rate rather than helping

    as_state = _shapes(effect, (helping, holding), window, persistence="state")
    stopping = rates_of(as_state, own, {0: with_help, 1: with_hold}, persistence="state")
    assert float(stopping.ends[1][1]) == 0.0  # ends nothing rather than starting


def test_the_rates_refuse_shapes_worked_out_for_the_other_kind_of_truth() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=60)
    down = _arrow("down", "effect", strength=-1.2)
    as_state = _shapes(effect, (down,), window, persistence="state")

    assert as_state.ends == (0,)
    with pytest.raises(ValueError, match="the other kind"):
        rates_of(as_state, _one(0.3), {0: _one(0.1)}, persistence="event")


def test_an_arrow_that_cannot_hold_a_claim_back_says_so() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=8)
    effect = _claim("effect", prior=0.3, days=60)
    # A spike that has faded long before the deadline cannot suppress a whole window.
    brief = _arrow("brief", "effect", strength=-2.4, shape="impulse", half_life=2.0)
    lasting = _arrow("lasting", "effect", strength=-2.4, shape="step")

    own = _one(effect.prior.p)
    asked = {
        0: stated_chance_with(own, _one(brief.strength)),
        1: stated_chance_with(own, _one(lasting.strength)),
    }
    shapes = _shapes(effect, (brief, lasting), window)
    rates = rates_of(shapes, own, asked, persistence="event")

    assert shapes.area[0] < shapes.area[1]
    assert bool(rates.saturated[0].all())
    assert not bool(rates.saturated[1].any())
    assert float(rates.leaves[0][0]) == 0.0  # the rate suppressed entirely, and still short

    fell_short = clamped(shapes, rates, asked)
    assert tuple(one.arrow for one in fell_short) == (brief.id,)
    only = fell_short[0]
    assert only.delivered > only.asked
    assert only.asked == pytest.approx(float(asked[0][0]))

    # An arrow that holds its claim back as far as it asked says nothing at all.
    kept = _shapes(effect, (lasting,), window)
    assert (
        clamped(kept, rates_of(kept, own, {0: asked[1]}, persistence="event"), {0: asked[1]}) == ()
    )


# --- Adding the rates up across the window ----------------------------------


def test_adding_up_gives_the_running_total_the_calibration_was_written_for() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=8)
    effect = _claim("effect", prior=0.3, days=60)
    shapes = _shapes(effect, (), window)
    own = numpy.array([0.2, 0.45])
    rates = rates_of(shapes, own, {}, persistence="event")
    added = added_up(shapes, rates)

    assert added.leak.shape == (2, 1, window.slices)
    assert added.helps == {}
    # A running total only rises, and by the end of the last slice it is the whole
    # window's worth — which is the claim's own chance back again.
    assert numpy.all(numpy.diff(added.leak, axis=-1) >= 0.0)
    assert numpy.allclose(_chance_by_the_deadline(added.leak[:, 0, -1]), own, atol=1e-12)


def test_a_helping_causes_total_is_nothing_until_it_arrives_and_nothing_if_it_never_does() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=6)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4)
    shapes = _shapes(effect, (helping,), window)
    rates = rates_of(shapes, _one(0.3), {0: _one(0.6)}, persistence="event")
    added = added_up(shapes, rates)

    # Every axis below the shapes counts the arrow's **different** pushes, so an
    # arrival slice is turned into the row of the push it takes before it is read.
    row = shapes.carried[0].of_each_reading
    assert added.helps[0].shape == (1, 1, shapes.carried[0].different, window.slices)
    never = added.helps[0].whole()[:, :, row[window.slices], :]
    assert numpy.all(never == 0.0)
    for arrived in range(window.slices):
        running = added.helps[0].whole()[0, 0, row[arrived]]
        # Nothing before the slice the cause arrived in, because the push had not
        # started; and never falling afterwards, because a rate is never negative.
        assert numpy.all(running[:arrived] == 0.0)
        assert numpy.all(numpy.diff(running) >= 0.0)
        assert float(running[-1]) > 0.0


def test_arrival_slices_that_push_the_same_are_kept_once_between_them() -> None:
    """The fold, stated as shapes and as an identity — never as a clock.

    A cause judged long after the claim it pushes has arrival slices that start after
    the claim's own deadline, and an arrow whose cause arrives then pushes **nothing
    at all** over that claim's window: the same array of noughts, over and over. They
    are kept once between them, and the chances of the readings that share a row are
    added together before anything is worked out.
    """
    window = window_of(_map(_claim("effect", days=10)), DAY_ZERO, slices=6)
    effect = _claim("effect", days=10)
    slow = _arrow("slow", "effect", strength=1.4, lag=2.0)
    carried = _shapes(effect, (slow,), window, days={"slow": 120}).carried[0]

    # Nothing is lost: the fold written back out is the push read by read.
    written_out = carried.for_each_reading()
    assert written_out.shape == (window.slices + 1, window.slices, POINTS_IN_A_SLICE)
    assert numpy.array_equal(written_out, carried.push[carried.of_each_reading])
    assert carried.readings == window.slices + 1

    # The cause is judged twelve times later than the claim, so only its first
    # arrival slice lands inside the claim's window at all; every later one, and
    # *the cause never came*, push nothing, and those share one row.
    assert carried.different < carried.readings
    pushes_nothing = ~written_out.any(axis=(1, 2))
    assert pushes_nothing.sum() > 1
    assert len(set(carried.of_each_reading[pushes_nothing].tolist())) == 1

    # Folding a spread of chances keeps the whole of the chance and puts each
    # reading's share on the row that reading takes.
    spread = numpy.linspace(0.02, 0.3, carried.readings)[None, :]
    spread = spread / spread.sum()
    folded = carried.fold(spread)
    assert folded.shape == (1, carried.different)
    assert numpy.allclose(folded.sum(), spread.sum(), atol=1e-15)
    for row in range(carried.different):
        belongs = carried.of_each_reading == row
        assert numpy.isclose(folded[0, row], spread[0, belongs].sum(), atol=1e-15)


def test_a_block_is_already_a_running_total_so_no_version_takes_one() -> None:
    """The second fix, as an identity: the adding-up across slices happens once.

    Every block a `Spread` keeps is a running total from day zero to the end of each
    slice, taken where the block is a few hundred numbers rather than the same block
    repeated once per version. Two things say so without a clock: a running total
    never falls, and the total on the deadline read off the pieces is the very same
    array of bytes as the last slice of the whole thing built out.
    """
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=5)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4, shape="impulse", half_life=9.0)
    holding = _arrow("holds", "effect", strength=-1.1, shape="ramp", lag=3.0)
    shapes = _shapes(effect, (helping, holding), window)
    own = numpy.array([0.12, 0.3, 0.47])
    rates = rates_of(
        shapes,
        own,
        {0: numpy.array([0.4, 0.55, 0.7]), 1: numpy.array([0.03, 0.07, 0.15])},
        persistence="event",
    )
    added = added_up(shapes, rates)

    for block in added.helps[0].blocks:
        assert numpy.all(numpy.diff(block, axis=-1) >= -1e-15)
    assert numpy.all(numpy.diff(added.leak, axis=-1) >= 0.0)
    assert numpy.array_equal(added.helps[0].over_the_window(), added.helps[0].whole()[..., -1])


def test_an_arrow_that_holds_a_claim_back_is_carried_over_every_arrival_it_could_have() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=5)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4)
    first = _arrow("first", "effect", strength=-1.1)
    second = _arrow("second", "effect", strength=-0.8)

    shapes = _shapes(effect, (helping, first, second), window)
    own, hold = _one(0.3), _one(0.08)
    rates = rates_of(shapes, own, {0: _one(0.6), 1: hold, 2: hold}, persistence="event")
    added = added_up(shapes, rates)

    # A combination names one row of each holding-back arrow's push, not one arrival
    # slice of each, because arrival slices whose push is the same array of numbers
    # are kept once between them. Here every arrival pushes differently, so the count
    # is the same either way, and the two rows below are what turns a slice into a row.
    rows_of_first = shapes.carried[1].of_each_reading
    rows_of_second = shapes.carried[2].of_each_reading
    sides = (shapes.carried[1].different, shapes.carried[2].different)
    combos = sides[0] * sides[1]
    assert combos == (window.slices + 1) ** 2
    assert added.leak.shape == (1, combos, window.slices)
    assert added.helps[0].shape == (1, combos, shapes.carried[0].different, window.slices)

    over_the_window = added.leak[:, :, -1]
    # Neither holding-back cause ever came: the rate is the plain one, and the claim
    # comes back out at its own stated chance.
    neither = numpy.ravel_multi_index(
        (rows_of_first[window.slices], rows_of_second[window.slices]), sides
    )
    assert numpy.allclose(_chance_by_the_deadline(over_the_window[:, neither]), own, atol=1e-12)

    # Both came on at the very start: the rate is held down as far as it can be, so
    # the claim's chance is lower than when neither of them came; and one of them
    # alone sits between the two.
    both_early = numpy.ravel_multi_index((rows_of_first[0], rows_of_second[0]), sides)
    one_early = numpy.ravel_multi_index((rows_of_first[0], rows_of_second[window.slices]), sides)
    assert (
        float(over_the_window[0, both_early])
        < float(over_the_window[0, one_early])
        < float(over_the_window[0, neither])
    )


def test_many_versions_in_one_pass_equal_one_at_a_time() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=5)
    effect = _claim("effect", prior=0.3, days=60)
    helping = _arrow("helps", "effect", strength=1.4, shape="impulse", half_life=9.0)
    holding = _arrow("holds", "effect", strength=-1.1, shape="ramp", lag=3.0)
    shapes = _shapes(effect, (helping, holding), window)

    own = numpy.array([0.12, 0.3, 0.47, 0.66])
    with_help = numpy.array([0.4, 0.55, 0.7, 0.81])
    with_hold = numpy.array([0.03, 0.07, 0.15, 0.3])

    at_once = added_up(
        shapes, rates_of(shapes, own, {0: with_help, 1: with_hold}, persistence="event")
    )
    for version in range(own.shape[0]):
        alone = added_up(
            shapes,
            rates_of(
                shapes,
                own[version : version + 1],
                {0: with_help[version : version + 1], 1: with_hold[version : version + 1]},
                persistence="event",
            ),
        )
        assert numpy.array_equal(alone.leak[0], at_once.leak[version])
        assert numpy.array_equal(alone.helps[0][0], at_once.helps[0][version])


def test_an_arrow_whose_push_lands_after_the_deadline_is_a_fault_and_not_a_crash() -> None:
    window = window_of(_map(_claim("effect", days=10)), DAY_ZERO, slices=4)
    effect = _claim("effect", prior=0.3, days=10)
    late = _arrow("late", "effect", strength=1.4, lag=99.0)
    shapes = _shapes(effect, (late,), window)

    assert shapes.area[0] == 0.0
    rates = rates_of(shapes, _one(0.3), {0: _one(0.6)}, persistence="event")
    assert numpy.all(numpy.isfinite(rates.helps[0]))
    added = added_up(shapes, rates)
    assert numpy.all(added.helps[0].whole() == 0.0)


def test_shapes_built_by_hand_are_refused_rather_than_quietly_worked_out() -> None:
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=4)
    effect = _claim("effect", days=60)
    down = _arrow("down", "effect", strength=-1.2)
    as_event = _shapes(effect, (down,), window)

    muddled = ClaimShapes(
        claim=as_event.claim,
        deadline=as_event.deadline,
        edges=as_event.edges,
        middle_day=as_event.middle_day,
        width=as_event.width,
        points=as_event.points,
        arrows=as_event.arrows,
        helps=as_event.helps,
        holds_back=as_event.holds_back,
        ends=as_event.holds_back,
        carried=as_event.carried,
        area=as_event.area,
    )
    with pytest.raises(ValueError, match="the other kind"):
        rates_of(muddled, _one(0.3), {0: _one(0.1)}, persistence="state")


def test_a_claim_two_arrows_hold_back_is_never_held_as_one_array() -> None:
    """The memory wall, and where it was taken down.

    Two arrows holding one claim back multiply out over every pair of slices they
    might have arrived in — twenty-five each, six hundred and twenty-five pairs. A
    helping arrow's running total across every version, every one of those pairs,
    every time its own cause might have come and every slice is one array of
    gigabytes, and the committed Hormuz strike branch needed 12.53 of them.

    It is never built. What is stored is one version-free block per term of the
    expansion plus one number per version, and the big array is built for as many
    versions at a time as the ceiling allows. This asserts on shapes and on bytes,
    and on nothing that has a clock in it.
    """
    window = window_of(_map(_claim("effect", days=60)), DAY_ZERO, slices=SLICES)
    effect = _claim("effect", prior=0.3, days=60)
    arrows = (
        _arrow("helps", "effect", strength=1.4),
        _arrow("first", "effect", strength=-1.1),
        _arrow("second", "effect", strength=-0.8),
    )
    shapes = _shapes(effect, arrows, window)
    versions = 200
    hold = numpy.full(versions, 0.08)
    rates = rates_of(
        shapes,
        numpy.full(versions, 0.3),
        {0: numpy.full(versions, 0.6), 1: hold, 2: hold},
        persistence="event",
    )
    added = added_up(shapes, rates)
    spread = added.helps[0]

    combos = (SLICES + 1) ** 2
    assert spread.shape == (versions, combos, SLICES + 1, SLICES)

    as_one_array = versions * combos * (SLICES + 1) * SLICES * 8
    kept = (
        spread.coefficients.nbytes
        + sum(block.nbytes for block in spread.blocks)
        + sum(row.nbytes for row in spread.rows)
    )
    assert kept * 100 < as_one_array

    # Every version is read exactly once, in order, and no block asks for more
    # numbers at a time than the ceiling allows.
    blocks = spread.version_blocks()
    assert len(blocks) > 1
    assert blocks[0][0] == 0
    assert blocks[-1][1] == versions
    assert all(blocks[index][1] == blocks[index + 1][0] for index in range(len(blocks) - 1))
    biggest = max(last - first for first, last in blocks) * combos * (SLICES + 1) * SLICES
    assert biggest <= MOST_NUMBERS_AT_ONCE

    # The total on the deadline is the last entry of the running total. It is read
    # off the pieces rather than off the running total, so the two agree to the last
    # place a double carries rather than bit for bit.
    ends = spread.over_the_window()
    assert ends.shape == (versions, combos, SLICES + 1)
    numpy.testing.assert_allclose(ends[3], spread[3][:, :, -1], rtol=1e-12, atol=0.0)
