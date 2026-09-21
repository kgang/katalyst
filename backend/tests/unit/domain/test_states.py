"""A state's two times — decision record 0017, checked as identities and directions.

Every input below is built by hand: a four-slice window, two reading days inside
each slice, two versions, and pushes that are one or nought so that the arithmetic
can be worked on paper. Nothing here quotes a number the engine computed; every
assertion is an identity between two ways of getting the same answer, a direction
one number must move in, or an ordering two must keep.
"""

import ast
from datetime import date
from pathlib import Path

import numpy
import pytest

from katalyst.domain import states
from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.graph import Graph
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition, Resolution
from katalyst.domain.rates import AddedUp, ClaimShapes, Rates, Window
from katalyst.domain.states import (
    Times,
    as_joint,
    holding_curve,
    is_true_on_its_deadline,
    needs_the_joint,
    on_and_off,
)

SLICES = 4
POINTS = 2
VERSIONS = 2
DAYS = 8.0


# --- the map's window, and the days a rate is read at ----------------------


def a_window(slices: int = SLICES, days: float = DAYS) -> Window:
    edges = numpy.linspace(0.0, days, slices + 1)
    middle = numpy.empty(slices + 1)
    middle[:slices] = (edges[:-1] + edges[1:]) / 2.0
    middle[slices] = numpy.inf
    return Window(
        day_zero=date(2026, 1, 1), days=int(days), slices=slices, edges=edges, middle_day=middle
    )


def reading_days(window: Window, slices: int = SLICES, points: int = POINTS):
    width = window.edges[1 : slices + 1] - window.edges[:slices]
    inside = (numpy.arange(points) + 0.5) / points
    return window.edges[:slices][:, None] + width[:, None] * inside[None, :]


def slice_widths(window: Window, slices: int = SLICES):
    return window.edges[1 : slices + 1] - window.edges[:slices]


# --- the two shapes a carried push can have --------------------------------


def a_push_that_keeps_going(window: Window, days_read, slices: int = SLICES):
    """`(slices + 1, slices, points)` — full size from the day the cause came on.

    The shape a `trigger` arrow has: it reads the moment its cause came on and keeps
    pushing afterwards. The last entry of the first axis is *the cause never came*,
    and it pushes not at all.
    """
    push = numpy.zeros((slices + 1, slices, days_read.shape[1]))
    for came_on in range(slices):
        push[came_on] = (days_read >= window.middle_day[came_on]).astype(numpy.float64)
    return push


def a_push_that_dies_with_its_cause(window: Window, days_read, slices: int = SLICES):
    """`(slices + 1, slices + 1, slices, points)` — full size only while the cause holds.

    The shape a `sustain` arrow out of a state has: it reads its cause's whole
    stretch. An off-slice at the last index means the cause never stopped, and the
    window's last middle day is positive infinity, which is what says so.
    """
    push = numpy.zeros((slices + 1, slices + 1, slices, days_read.shape[1]))
    for came_on in range(slices):
        started = days_read >= window.middle_day[came_on]
        for went_off in range(slices + 1):
            stopped = days_read >= window.middle_day[went_off]
            push[came_on, went_off] = (started & ~stopped).astype(numpy.float64)
    return push


def area_of(push, width, slices: int = SLICES) -> float:
    """One arrow's push added up over the window, with its cause arriving in the first slice.

    For an arrow that reads its cause's whole stretch, that means on in the first
    slice and never off, which is the last index of the off axis.
    """
    from_day_zero = push[0] if push.ndim == 3 else push[0, slices]
    return float((width * from_day_zero.mean(axis=1)).sum())


# --- the three shapes writer A hands over, built by hand -------------------


def some_shapes(
    window: Window,
    *,
    carried: dict[int, numpy.ndarray],
    helps: tuple[int, ...] = (),
    holds_back: tuple[int, ...] = (),
    ends: tuple[int, ...] = (),
    claim: str = "claim-b",
    slices: int = SLICES,
) -> ClaimShapes:
    width = slice_widths(window, slices)
    return ClaimShapes(
        claim=claim,
        deadline=int(window.edges[slices]),
        edges=window.edges,
        middle_day=window.middle_day,
        width=width,
        points=reading_days(window, slices),
        arrows=tuple(f"arrow-{index}" for index in sorted(carried)),
        helps=helps,
        holds_back=holds_back,
        ends=ends,
        carried=carried,
        area={index: area_of(push, width, slices) for index, push in carried.items()},
    )


def some_rates(
    *,
    leak: float,
    helps: dict[int, float] | None = None,
    leaves: dict[int, float] | None = None,
    ends: dict[int, float] | None = None,
    versions: int = VERSIONS,
) -> Rates:
    row = numpy.ones(versions)
    return Rates(
        leak=row * leak,
        helps={index: row * value for index, value in (helps or {}).items()},
        leaves={index: row * value for index, value in (leaves or {}).items()},
        ends={index: row * value for index, value in (ends or {}).items()},
        saturated={},
    )


def added_up_by_hand(
    shapes: ClaimShapes, rates: Rates, *, combinations: int = 1, slices: int = SLICES
) -> AddedUp:
    """The same adding-up `rates.added_up` does, written out here so this file stands alone.

    A rate multiplied by its push, averaged over the reading days of each slice,
    multiplied by how many days of the window that slice holds, and then kept as a
    **running total to the end of each slice** — which is the shape `AddedUp` says
    its entries are in, so that survival is one exponential and nothing else.
    """
    versions = rates.leak.shape[0]
    width = shapes.width
    leak = numpy.broadcast_to(
        rates.leak[:, None, None] * numpy.cumsum(width)[None, None, :],
        (versions, combinations, slices),
    ).copy()
    helps = {}
    for index in shapes.helps:
        push = shapes.carried[index]
        per_slice = width * push.reshape(-1, push.shape[-2], push.shape[-1]).mean(axis=2)
        block = (
            rates.helps[index][:, None, None, None] * numpy.cumsum(per_slice, axis=1)[None, None]
        )
        helps[index] = numpy.broadcast_to(
            block, (versions, combinations, per_slice.shape[0], slices)
        ).reshape(versions, combinations, *push.shape[:-2], slices)
    return AddedUp(leak=leak, helps=helps)


# --- times built by hand, for a claim's causes -----------------------------


def times_of_an_event(came_on_in: int, claim: str = "claim-a", slices: int = SLICES) -> Times:
    spread = numpy.zeros((VERSIONS, slices + 1))
    spread[:, came_on_in] = 1.0
    return Times(
        claim=claim,
        persistence="event",
        spread=spread,
        holding=numpy.cumsum(spread[:, :slices], axis=1),
        pairs=None,
    )


def times_of_a_state(pairs_by_hand, claim: str = "claim-a", slices: int = SLICES) -> Times:
    """A state's times from a square of chances over *(on-slice, off-slice)*."""
    square = numpy.asarray(pairs_by_hand, dtype=numpy.float64)
    square = numpy.broadcast_to(square, (VERSIONS, slices + 1, slices + 1)).copy()
    spread = square.sum(axis=2)
    positions = numpy.arange(slices)
    at_or_after = positions[None, :] >= positions[:, None]
    still_on = numpy.zeros((VERSIONS, slices, slices))
    for came_on in range(slices):
        for end_of in range(slices):
            if at_or_after[came_on, end_of]:
                went_off_later = square[:, came_on, end_of + 1 : slices].sum(axis=1)
                still_on[:, came_on, end_of] = went_off_later + square[:, came_on, slices]
    holding = numpy.einsum("va,vak->vk", spread[:, :slices], still_on)
    return Times(
        claim=claim,
        persistence="state",
        spread=spread,
        holding=holding,
        pairs=square.reshape(VERSIONS, -1),
    )


# --- a map, for the cheap path's guard -------------------------------------


def a_claim(identifier: str) -> Proposition:
    number = Belief(p=0.3, lo=0.2, hi=0.4, owner="model")
    return Proposition(
        id=identifier,
        claim="The strait stays open to commercial transit through 1 November.",
        kind="hypothesis" if identifier == "claim-a" else "event",
        resolution=Resolution(
            criteria="A seven-day moving average of transits at or above sixty.",
            source="IMF PortWatch",
            by=date(2026, 11, 1),
        ),
        prior=number,
        beliefs=Beliefs(model=number),
    )


def an_arrow(identifier: str, source: str, target: str, mode: str) -> Link:
    return Link(
        id=identifier,
        source=source,
        target=target,
        mode=mode,
        strength=0.5,
        lag=0.0,
        shape="step",
        rationale="Closing the lane keeps the cargo at sea, which keeps the price up.",
        provenance="argued",
    )


def a_map(*arrows: Link) -> Graph:
    return Graph(
        id="map-1",
        propositions=(a_claim("claim-a"), a_claim("claim-b")),
        links=arrows,
        hypothesis_id="claim-a",
    )


# --- one claim with one helping arrow, used by several tests ---------------


def a_claim_with_one_helper(window: Window, *, help_rate: float = 0.4, leak: float = 0.05):
    push = a_push_that_keeps_going(window, reading_days(window))
    shapes = some_shapes(window, carried={0: push}, helps=(0,))
    rates = some_rates(leak=leak, helps={0: help_rate})
    return shapes, rates, added_up_by_hand(shapes, rates)


def _called_name(func) -> str:
    """The bare name of whatever is being called: `clip` for both `clip()` and `numpy.clip()`."""
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def the_same_bytes(left, right) -> bool:
    return (
        left.dtype == right.dtype
        and left.shape == right.shape
        and left.tobytes() == right.tobytes()
    )


# --- the tests -------------------------------------------------------------


def test_a_state_with_nothing_to_end_it_is_an_event():
    """A state's off-rate starts at nought, so nothing that can end it means it does not end."""
    window = a_window()
    shapes, rates, added = a_claim_with_one_helper(window)
    causes = [times_of_an_event(1)]

    as_an_event = on_and_off(shapes, rates, added, causes, persistence="event", joint=False)
    as_a_state = on_and_off(shapes, rates, added, causes, persistence="state", joint=False)
    as_a_state_with_its_pair = on_and_off(
        shapes, rates, added, causes, persistence="state", joint=True
    )

    assert not shapes.ends
    assert the_same_bytes(as_a_state.spread, as_an_event.spread)
    assert the_same_bytes(as_a_state.holding, as_an_event.holding)
    assert the_same_bytes(as_a_state_with_its_pair.holding, as_an_event.holding)
    assert the_same_bytes(is_true_on_its_deadline(as_a_state), is_true_on_its_deadline(as_an_event))
    # The pair of times says the same thing: it came on, and it never went off.
    square = as_joint(as_a_state_with_its_pair)
    assert numpy.array_equal(square[:, :SLICES, SLICES], as_an_event.spread[:, :SLICES])


def test_the_sign_of_an_arrow_picks_which_rate_it_bends():
    """Above the claim's own chance it bends the rate it comes on at; below, the one it stops at."""
    window = a_window()
    push = a_push_that_keeps_going(window, reading_days(window))
    causes = [times_of_an_event(0)]

    bare_shapes = some_shapes(window, carried={0: push})
    bare_rates = some_rates(leak=0.05)
    bare = on_and_off(
        bare_shapes,
        bare_rates,
        added_up_by_hand(bare_shapes, bare_rates),
        causes,
        persistence="state",
        joint=False,
    )

    helping_shapes = some_shapes(window, carried={0: push}, helps=(0,))
    helping_rates = some_rates(leak=0.05, helps={0: 0.6})
    helping = on_and_off(
        helping_shapes,
        helping_rates,
        added_up_by_hand(helping_shapes, helping_rates),
        causes,
        persistence="state",
        joint=False,
    )

    ending_shapes = some_shapes(window, carried={0: push}, ends=(0,))
    ending_rates = some_rates(leak=0.05, ends={0: 0.6})
    ending = on_and_off(
        ending_shapes,
        ending_rates,
        added_up_by_hand(ending_shapes, ending_rates),
        causes,
        persistence="state",
        joint=False,
    )

    # A helping arrow moves the moment the claim comes on, and moves it earlier.
    assert not the_same_bytes(helping.spread, bare.spread)
    assert (helping.spread[:, 0] > bare.spread[:, 0]).all()
    assert (is_true_on_its_deadline(helping) > is_true_on_its_deadline(bare)).all()

    # An ending arrow leaves the moment it came on exactly where it was, and only
    # takes away from the chance it is still holding.
    assert the_same_bytes(ending.spread, bare.spread)
    assert (is_true_on_its_deadline(ending) < is_true_on_its_deadline(bare)).all()


def test_the_chance_it_stops_is_closed_form():
    """The ending rate is one formula, and this file finds no search and no clamp in the module."""
    window = a_window()
    width = slice_widths(window)

    # An ending arrow that pushes in every slice but the first. Its cause certainly
    # arrived in the first slice, and the claim's own rate is large enough that the
    # chance it came on after the first slice is under a millionth of a millionth.
    push = numpy.zeros((SLICES + 1, SLICES, POINTS))
    for arrived in range(SLICES):
        push[arrived, 1:] = 1.0
    shapes = some_shapes(window, carried={0: push}, ends=(0,))
    area = shapes.area[0]
    assert area == pytest.approx(float(width[1:].sum()))

    stops = 0.4
    rate = -numpy.log1p(-stops) / area
    rates = some_rates(leak=50.0 / float(width[0]), ends={0: float(rate)})
    added = added_up_by_hand(shapes, rates)

    times = on_and_off(
        shapes,
        rates,
        added,
        [times_of_an_event(0)],
        persistence="state",
        joint=False,
    )
    came_on_at_once = times.spread[:, 0]
    numpy.testing.assert_allclose(
        is_true_on_its_deadline(times), came_on_at_once * (1.0 - stops), rtol=0.0, atol=1e-12
    )

    # The counter: nothing in the module narrows a bracket and nothing is clipped.
    source = Path(states.__file__).read_text()
    tree = ast.parse(source)
    searches = sum(isinstance(node, ast.While) for node in ast.walk(tree))
    searching_names = {"clip", "clamp", "bisect", "brentq", "fsolve", "newton", "minimize"}
    clamps = sum(
        isinstance(node, ast.Call) and _called_name(node.func) in searching_names
        for node in ast.walk(tree)
    )
    assert searches == 0
    assert clamps == 0


def test_a_sustain_arrow_reads_the_whole_interval_and_a_trigger_only_the_on_day():
    """Change only when the cause stopped: a trigger child does not notice, a sustain child does."""
    window = a_window()
    days_read = reading_days(window)

    holds_on = numpy.zeros((SLICES + 1, SLICES + 1))
    holds_on[0, SLICES] = 1.0  # came on in the first slice and never stopped
    stops_early = numpy.zeros((SLICES + 1, SLICES + 1))
    stops_early[0, 1] = 1.0  # came on in the first slice and stopped in the second

    unchanging = times_of_a_state(holds_on)
    stopping = times_of_a_state(stops_early)
    assert the_same_bytes(unchanging.spread, stopping.spread)

    trigger_push = a_push_that_keeps_going(window, days_read)
    trigger_shapes = some_shapes(window, carried={0: trigger_push}, helps=(0,))
    trigger_rates = some_rates(leak=0.05, helps={0: 0.6})
    trigger_added = added_up_by_hand(trigger_shapes, trigger_rates)
    kept = on_and_off(
        trigger_shapes,
        trigger_rates,
        trigger_added,
        [unchanging],
        persistence="event",
        joint=False,
    )
    dropped = on_and_off(
        trigger_shapes,
        trigger_rates,
        trigger_added,
        [stopping],
        persistence="event",
        joint=False,
    )
    assert the_same_bytes(kept.spread, dropped.spread)

    sustain_push = a_push_that_dies_with_its_cause(window, days_read)
    sustain_shapes = some_shapes(window, carried={0: sustain_push}, helps=(0,))
    sustain_rates = some_rates(leak=0.05, helps={0: 0.6})
    sustain_added = added_up_by_hand(sustain_shapes, sustain_rates)
    while_it_held = on_and_off(
        sustain_shapes,
        sustain_rates,
        sustain_added,
        [unchanging],
        persistence="event",
        joint=False,
    )
    after_it_stopped = on_and_off(
        sustain_shapes,
        sustain_rates,
        sustain_added,
        [stopping],
        persistence="event",
        joint=False,
    )
    assert not the_same_bytes(while_it_held.spread, after_it_stopped.spread)
    assert (
        is_true_on_its_deadline(while_it_held) > is_true_on_its_deadline(after_it_stopped)
    ).all()


def test_the_cheap_path_and_the_joint_agree(monkeypatch):
    """The same holding curve either way, and the cheap path never builds the pair of times."""
    window = a_window()
    days_read = reading_days(window)
    push = a_push_that_keeps_going(window, days_read)
    shapes = some_shapes(window, carried={0: push, 1: push}, helps=(0,), ends=(1,))
    rates = some_rates(leak=0.08, helps={0: 0.5}, ends={1: 0.35})
    added = added_up_by_hand(shapes, rates)
    causes = [times_of_an_event(0), times_of_an_event(1)]

    cheap = on_and_off(shapes, rates, added, causes, persistence="state", joint=False)
    whole = on_and_off(shapes, rates, added, causes, persistence="state", joint=True)

    numpy.testing.assert_allclose(holding_curve(cheap), holding_curve(whole), rtol=0.0, atol=1e-12)
    numpy.testing.assert_allclose(
        is_true_on_its_deadline(cheap), is_true_on_its_deadline(whole), rtol=0.0, atol=1e-12
    )
    assert the_same_bytes(cheap.spread, whole.spread)
    assert cheap.pairs is None
    assert whole.pairs is not None

    # The proof it is not built: make the square impossible to build, and watch the
    # cheap path go through while the whole pair of times does not.
    def refuse(*arguments, **keywords):
        raise AssertionError("the square of still-holding chances was built")

    monkeypatch.setattr(states, "_still_on_at_each_slice", refuse)
    again = on_and_off(shapes, rates, added, causes, persistence="state", joint=False)
    assert the_same_bytes(again.holding, cheap.holding)
    with pytest.raises(AssertionError, match="was built"):
        on_and_off(shapes, rates, added, causes, persistence="state", joint=True)


def test_the_cheap_path_is_not_taken_for_an_event():
    """The guard that holds until the shape freeze, while every recorded claim is an event."""
    claim = a_claim("claim-a")
    sustained = a_map(an_arrow("arrow-0", "claim-a", "claim-b", "sustain"))
    triggered = a_map(an_arrow("arrow-0", "claim-a", "claim-b", "trigger"))
    elsewhere = a_map(an_arrow("arrow-0", "claim-b", "claim-a", "sustain"))

    assert needs_the_joint(sustained, claim, "state")
    assert not needs_the_joint(sustained, claim, "event")
    assert not needs_the_joint(triggered, claim, "state")
    assert not needs_the_joint(elsewhere, claim, "state")


def test_a_state_switches_on_at_most_once():
    """One stretch: one moment it came on, one moment it stopped, and never the other way round."""
    window = a_window()
    push = a_push_that_keeps_going(window, reading_days(window))
    shapes = some_shapes(window, carried={0: push, 1: push}, helps=(0,), ends=(1,))
    rates = some_rates(leak=0.08, helps={0: 0.5}, ends={1: 0.35})
    times = on_and_off(
        shapes,
        rates,
        added_up_by_hand(shapes, rates),
        [times_of_an_event(0), times_of_an_event(1)],
        persistence="state",
        joint=True,
    )

    square = as_joint(times)
    assert square.shape == (VERSIONS, SLICES + 1, SLICES + 1)
    assert (square >= 0.0).all()
    numpy.testing.assert_allclose(
        square.sum(axis=(1, 2)), numpy.ones(VERSIONS), rtol=0.0, atol=1e-12
    )
    # It cannot stop before it started.
    for came_on in range(SLICES + 1):
        for went_off in range(came_on):
            assert (square[:, came_on, went_off] == 0.0).all()
    # A claim that never came on is recorded as still holding, not as having stopped.
    assert (square[:, SLICES, :SLICES] == 0.0).all()
    # The moment it came on is the square read across its off times.
    numpy.testing.assert_allclose(square.sum(axis=2), times.spread, rtol=0.0, atol=1e-12)


def test_an_events_number_only_rises_and_a_states_can_fall():
    """The per-slice reading of the two kinds of truth, and what tells them apart."""
    window = a_window()
    push = a_push_that_keeps_going(window, reading_days(window))
    shapes = some_shapes(window, carried={0: push, 1: push}, helps=(0,), ends=(1,))
    rates = some_rates(leak=0.3, helps={0: 0.6}, ends={1: 1.2})
    added = added_up_by_hand(shapes, rates)
    causes = [times_of_an_event(0), times_of_an_event(1)]

    event_shapes = some_shapes(window, carried={0: push, 1: push}, helps=(0,))
    event_rates = some_rates(leak=0.3, helps={0: 0.6})
    an_event = on_and_off(
        event_shapes,
        event_rates,
        added_up_by_hand(event_shapes, event_rates),
        causes,
        persistence="event",
        joint=False,
    )
    a_state = on_and_off(shapes, rates, added, causes, persistence="state", joint=False)

    rises = numpy.diff(holding_curve(an_event), axis=1)
    assert (rises >= 0.0).all()
    assert (numpy.diff(holding_curve(a_state), axis=1) < 0.0).any()
    numpy.testing.assert_allclose(
        is_true_on_its_deadline(an_event), 1.0 - an_event.spread[:, SLICES], rtol=0.0, atol=1e-12
    )
    assert the_same_bytes(is_true_on_its_deadline(a_state), holding_curve(a_state)[:, -1])


def test_a_pair_of_times_is_refused_by_name():
    """An event has no pair, and a state nobody reads the stretch of was never given one."""
    window = a_window()
    shapes, rates, added = a_claim_with_one_helper(window)
    causes = [times_of_an_event(1)]

    an_event = on_and_off(shapes, rates, added, causes, persistence="event", joint=False)
    with pytest.raises(ValueError, match="claim-b is an event"):
        as_joint(an_event)

    unread = on_and_off(shapes, rates, added, causes, persistence="state", joint=False)
    with pytest.raises(ValueError, match="claim-b is a state whose pair of times"):
        as_joint(unread)


def test_arrows_that_hold_a_claim_back_are_averaged_over_their_arrival_slices():
    """One pass over every combination equals the weighted average of the passes one at a time."""
    window = a_window()
    width = slice_widths(window)
    push = a_push_that_keeps_going(window, reading_days(window))
    shapes = some_shapes(window, carried={0: push, 1: push}, helps=(0,), holds_back=(1,))
    rates = some_rates(leak=0.25, helps={0: 0.4}, leaves={1: 0.3})

    # The holding-back arrow scales the claim's own rate down while its cause is on,
    # which is one added-up leak per slice the cause might have arrived in.
    on_amount = width * push.mean(axis=2)
    per_slice = width[None, :] - (1.0 - rates.leaves[1][:, None, None]) * on_amount[None, :, :]
    leak = rates.leak[:, None, None] * numpy.cumsum(per_slice, axis=2)
    helps_push = numpy.cumsum(width * push.mean(axis=2), axis=1)
    helps = {
        0: numpy.broadcast_to(
            rates.helps[0][:, None, None, None] * helps_push[None, None],
            (VERSIONS, SLICES + 1, SLICES + 1, SLICES),
        ).copy()
    }
    added = AddedUp(leak=leak, helps=helps)

    holding_back_arrived = numpy.full((VERSIONS, SLICES + 1), 1.0 / (SLICES + 1))
    causes = [
        times_of_an_event(0),
        Times(
            claim="claim-c",
            persistence="event",
            spread=holding_back_arrived,
            holding=numpy.cumsum(holding_back_arrived[:, :SLICES], axis=1),
            pairs=None,
        ),
    ]
    together = on_and_off(shapes, rates, added, causes, persistence="event", joint=False)

    one_at_a_time = numpy.zeros((VERSIONS, SLICES + 1))
    for arrived in range(SLICES + 1):
        just_this_one = AddedUp(
            leak=leak[:, arrived : arrived + 1, :],
            helps={0: helps[0][:, arrived : arrived + 1, :, :]},
        )
        pinned = numpy.zeros((VERSIONS, SLICES + 1))
        pinned[:, arrived] = 1.0
        alone = on_and_off(
            shapes,
            rates,
            just_this_one,
            [
                causes[0],
                Times(
                    claim="claim-c",
                    persistence="event",
                    spread=pinned,
                    holding=numpy.cumsum(pinned[:, :SLICES], axis=1),
                    pairs=None,
                ),
            ],
            persistence="event",
            joint=False,
        )
        one_at_a_time += holding_back_arrived[:, arrived][:, None] * alone.spread

    numpy.testing.assert_allclose(together.spread, one_at_a_time, rtol=0.0, atol=1e-12)


def test_every_row_of_times_is_a_chance_and_adds_to_one():
    """Each version is one world's worth of chance, in full precision, and none goes missing."""
    window = a_window()
    shapes, rates, added = a_claim_with_one_helper(window)
    causes = [times_of_an_event(1)]
    for persistence in ("event", "state"):
        times = on_and_off(shapes, rates, added, causes, persistence=persistence, joint=False)
        assert times.claim == shapes.claim
        assert times.persistence == persistence
        assert times.spread.dtype == numpy.float64
        assert times.holding.dtype == numpy.float64
        assert times.spread.shape == (VERSIONS, SLICES + 1)
        assert times.holding.shape == (VERSIONS, SLICES)
        assert (times.spread >= 0.0).all()
        numpy.testing.assert_allclose(
            times.spread.sum(axis=1), numpy.ones(VERSIONS), rtol=0.0, atol=1e-12
        )
