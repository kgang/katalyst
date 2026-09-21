"""The forward pass — writer A.

Every test here asserts an identity, a direction or an ordering on a map the test
builds. Not one number an engine worked out is written down.

Two words, used throughout. *the claim's own chance* — the chance it reaches its
deadline with none of the map's causes on. *the chance with one cause on* — the
chance it reaches its deadline with that one cause on from day zero and no other.
"""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

import numpy
import pytest

from katalyst.domain import states
from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.forward import forward_pass
from katalyst.domain.graph import Graph
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition, Resolution
from katalyst.domain.rates import Drawn, Pin, window_of
from katalyst.domain.states import Times, as_joint, is_true_on_its_deadline

DAY_ZERO = date(2026, 10, 1)


def _claim(identifier: str, *, prior: float = 0.3, days: int = 60) -> Proposition:
    """One plain claim, with the chance it comes true on its own and the day it is judged."""
    belief = Belief(p=prior, lo=max(0.0, prior - 0.1), hi=min(1.0, prior + 0.1), owner="model")
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind="event",
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


def _map(claims: Sequence[Proposition], arrows: Sequence[Link] = ()) -> Graph:
    """A whole small map, with the first claim as the one it started from."""
    return Graph(
        id="small", propositions=tuple(claims), links=tuple(arrows), hypothesis_id=claims[0].id
    )


def _drawn(
    graph: Graph,
    *,
    versions: int = 1,
    own: Mapping[str, Sequence[float]] | None = None,
    with_cause: Mapping[str, Sequence[float]] | None = None,
) -> Drawn:
    """One draw of every stated number, the same in every version unless a test says otherwise."""
    own = own or {}
    with_cause = with_cause or {}
    return Drawn(
        versions=versions,
        own_chance={
            one.id: numpy.array(own.get(one.id, [one.prior.p] * versions), dtype=float)
            for one in graph.propositions
        },
        with_this_cause={
            one.id: numpy.array(with_cause.get(one.id, [0.6] * versions), dtype=float)
            for one in graph.links
        },
    )


def _given_it_happened(times: Times, slices: int) -> numpy.ndarray:
    """An event cause's arrival spread, read again on the worlds where it did happen."""
    live = times.spread[:, :slices]
    return live / live.sum(axis=1, keepdims=True)


# --- The order the map is worked through ------------------------------------


def test_causes_come_before_the_effects_they_feed() -> None:
    graph = _map(
        [_claim("z"), _claim("a"), _claim("m")],
        [_arrow("z", "a"), _arrow("a", "m")],
    )
    window = window_of(graph, DAY_ZERO, slices=4)
    forward = forward_pass(graph, window, _drawn(graph))

    assert forward.order == ("z", "a", "m")
    assert forward.causes == {"z": (), "a": ("z",), "m": ("a",)}
    # Two runs of the same map give the same order, so two worlds can be compared.
    assert forward_pass(graph, window, _drawn(graph)).order == forward.order


def test_a_map_that_runs_round_in_circles_is_refused() -> None:
    graph = _map(
        [_claim("first"), _claim("second")],
        [_arrow("first", "second"), _arrow("second", "first")],
    )
    window = window_of(graph, DAY_ZERO, slices=4)
    with pytest.raises(ValueError, match="causes before effects"):
        forward_pass(graph, window, _drawn(graph))


# --- The yes/no table -------------------------------------------------------


def test_the_table_adds_to_one_along_the_claims_own_axis() -> None:
    graph = _map(
        [_claim("cause"), _claim("other"), _claim("effect")],
        [_arrow("cause", "effect"), _arrow("other", "effect", strength=-1.2)],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    forward = forward_pass(graph, window, _drawn(graph, versions=3))

    assert forward.table["cause"].shape == (3, 2)
    assert forward.table["effect"].shape == (3, 2, 2, 2)
    for claim_id, table in forward.table.items():
        assert numpy.allclose(table.sum(axis=-1), 1.0, atol=1e-12), claim_id
        assert numpy.all(table >= 0.0)
        assert numpy.all(table <= 1.0)


def test_a_claim_with_no_causes_comes_out_at_its_own_stated_chance() -> None:
    graph = _map([_claim("alone", prior=0.42)])
    window = window_of(graph, DAY_ZERO, slices=6)
    own = numpy.array([0.11, 0.42, 0.87])
    forward = forward_pass(graph, window, _drawn(graph, versions=3, own={"alone": own}))

    assert numpy.allclose(forward.table["alone"][:, 1], own, atol=1e-12)
    assert numpy.allclose(is_true_on_its_deadline(forward.times["alone"]), own, atol=1e-12)


def test_a_cause_being_true_moves_its_effect_the_way_its_arrow_points() -> None:
    graph = _map(
        [_claim("cause"), _claim("effect")],
        [_arrow("cause", "effect", strength=1.5)],
    )
    window = window_of(graph, DAY_ZERO, slices=6)
    helped = forward_pass(graph, window, _drawn(graph)).table["effect"]
    assert float(helped[0, 1, 1]) > float(helped[0, 0, 1])

    held = _map(
        [_claim("cause"), _claim("effect")],
        [_arrow("cause", "effect", strength=-1.5)],
    )
    kept_down = forward_pass(
        held, window, _drawn(held, with_cause={"cause->effect": [0.05]})
    ).table["effect"]
    assert float(kept_down[0, 1, 1]) < float(kept_down[0, 0, 1])


def test_one_cause_at_a_time_equals_the_full_table() -> None:
    graph = _map(
        [_claim("first"), _claim("second"), _claim("effect", prior=0.25)],
        [
            _arrow("first", "effect", strength=1.3),
            _arrow("second", "effect", strength=0.8, shape="impulse", half_life=11.0),
        ],
    )
    window = window_of(graph, DAY_ZERO, slices=6)
    slices = window.slices
    forward = forward_pass(graph, window, _drawn(graph, versions=2))
    added = forward.added["effect"]

    # The pass averages each cause on its own, because the rates add. Here the same
    # answer is worked out the slow way instead: every combination of the two causes'
    # arrival slices, enumerated and weighed. An arrival slice is turned into the row
    # of its arrow's push it takes, because arrival slices whose push is the same
    # array of numbers are kept once between them.
    leak = added.leak[:, 0, -1]
    first = added.helps[0].over_the_window()[:, 0, :]
    second = added.helps[1].over_the_window()[:, 0, :]
    first_row = forward.shapes["effect"].carried[0].of_each_reading
    second_row = forward.shapes["effect"].carried[1].of_each_reading
    when_first = _given_it_happened(forward.times["first"], slices)
    when_second = _given_it_happened(forward.times["second"], slices)

    not_yet = numpy.zeros_like(leak)
    for one in range(slices):
        for other in range(slices):
            weight = when_first[:, one] * when_second[:, other]
            not_yet = not_yet + weight * numpy.exp(
                -(leak + first[:, first_row[one]] + second[:, second_row[other]])
            )

    assert numpy.allclose(forward.table["effect"][:, 1, 1, 1], 1.0 - not_yet, atol=1e-12)


def test_many_versions_in_one_pass_equal_one_at_a_time() -> None:
    graph = _map(
        [_claim("cause"), _claim("other"), _claim("effect")],
        [
            _arrow("cause", "effect", strength=1.4, shape="ramp", lag=4.0),
            _arrow("other", "effect", strength=-1.1, shape="impulse", half_life=15.0),
        ],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    own = {"effect": [0.2, 0.31, 0.44], "cause": [0.5, 0.36, 0.28], "other": [0.15, 0.4, 0.62]}
    with_cause = {"cause->effect": [0.6, 0.7, 0.55], "other->effect": [0.05, 0.09, 0.12]}

    at_once = forward_pass(graph, window, _drawn(graph, versions=3, own=own, with_cause=with_cause))
    for version in range(3):
        alone = forward_pass(
            graph,
            window,
            _drawn(
                graph,
                versions=1,
                own={name: [rows[version]] for name, rows in own.items()},
                with_cause={name: [rows[version]] for name, rows in with_cause.items()},
            ),
        )
        for claim_id in at_once.order:
            assert numpy.array_equal(alone.table[claim_id][0], at_once.table[claim_id][version]), (
                claim_id
            )
            assert numpy.array_equal(
                alone.times[claim_id].spread[0], at_once.times[claim_id].spread[version]
            ), claim_id


# --- What an edit cannot reach does not move --------------------------------


def test_a_longer_window_moves_nothing_it_cannot_reach() -> None:
    """Inserting a claim judged a year later leaves an unrelated claim byte-identical.

    The product's central correctness claim, in the one place the new engine could
    have broken it: a grid cut from the map's longest deadline would widen every
    slice on the map the moment a far-off claim was inserted, and claims the
    insertion has no arrow to would move with it. Every claim is cut from its own
    deadline instead, so this holds bit for bit rather than closely.
    """
    piece = [
        _claim("cause", days=30),
        _claim("middle", days=45),
        _claim("ending", prior=0.2, days=50),
    ]
    arrows = [
        _arrow("cause", "middle", strength=1.3, shape="impulse", half_life=7.0),
        _arrow("middle", "ending", strength=-1.1, lag=3.0),
    ]
    before = _map(piece, arrows)
    after = _map([*piece, _claim("inserted", days=365)], arrows)

    window_before = window_of(before, DAY_ZERO)
    window_after = window_of(after, DAY_ZERO)
    assert window_before.days != window_after.days

    with_cause = {"cause->middle": [0.62], "middle->ending": [0.05]}
    base = forward_pass(before, window_before, _drawn(before, with_cause=with_cause))
    branched = forward_pass(after, window_after, _drawn(after, with_cause=with_cause))

    for claim_id in base.order:
        assert numpy.array_equal(base.table[claim_id], branched.table[claim_id]), (
            f"{claim_id}'s table moved"
        )
        assert numpy.array_equal(base.times[claim_id].spread, branched.times[claim_id].spread), (
            f"{claim_id}'s times moved"
        )
        assert numpy.array_equal(base.shapes[claim_id].edges, branched.shapes[claim_id].edges), (
            f"{claim_id}'s slices moved"
        )


# --- The two verbs ----------------------------------------------------------


def test_supposing_a_claim_cuts_the_arrows_into_it_and_fixes_its_table() -> None:
    graph = _map(
        [_claim("cause"), _claim("effect")],
        [_arrow("cause", "effect", strength=1.5)],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(graph, versions=2)

    for value in (True, False):
        supposed = forward_pass(
            graph, window, drawn, pinned={"effect": Pin(value=value, kind="do")}
        )
        assert supposed.causes["effect"] == ()
        assert supposed.table["effect"].shape == (2, 2)
        assert numpy.array_equal(
            supposed.table["effect"], numpy.tile([1.0 - value, float(value)], (2, 1))
        )
        # The cause it was cut loose from is untouched.
        plain = forward_pass(graph, window, drawn)
        assert numpy.array_equal(supposed.table["cause"], plain.table["cause"])


def test_this_happened_is_not_honoured_by_the_pass() -> None:
    graph = _map(
        [_claim("cause"), _claim("effect")],
        [_arrow("cause", "effect", strength=1.5)],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(graph)

    plain = forward_pass(graph, window, drawn)
    observed = forward_pass(graph, window, drawn, pinned={"effect": Pin(True, kind="observe")})

    # *This happened* narrows the answer rather than changing the map's workings, so
    # the pass leaves the arrows in and the table alone; the solve is what reads it.
    assert observed.causes["effect"] == ("cause",)
    assert numpy.array_equal(observed.table["effect"], plain.table["effect"])


# --- States -----------------------------------------------------------------


def test_a_state_nothing_can_end_comes_out_exactly_as_an_event() -> None:
    graph = _map(
        [_claim("cause"), _claim("holds")],
        [_arrow("cause", "holds", strength=1.3)],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(graph)

    as_event = forward_pass(graph, window, drawn)
    as_state = forward_pass(graph, window, drawn, persistence={"holds": "state"})

    assert as_state.times["holds"].persistence == "state"
    assert numpy.array_equal(as_event.table["holds"], as_state.table["holds"])


def test_a_state_something_can_end_is_read_as_still_holding_on_its_deadline() -> None:
    graph = _map(
        [_claim("opens", prior=0.5), _claim("strike"), _claim("ending", prior=0.3)],
        [
            _arrow("strike", "opens", strength=-2.0),
            _arrow("opens", "ending", strength=1.2, mode="sustain"),
        ],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(graph, with_cause={"strike->opens": [0.1], "opens->ending": [0.7]})
    forward = forward_pass(graph, window, drawn, persistence={"opens": "state"})

    times = forward.times["opens"]
    assert times.persistence == "state"
    # Anything that reads the state at all needs its pair of times, because a state's
    # truth is a fact about the whole stretch and not about the moment it came on.
    assert times.pairs is not None
    square = as_joint(times)
    assert numpy.allclose(square.sum(axis=(1, 2)), 1.0, atol=1e-12)
    # The chance it is holding on its deadline is the chance it came on and never
    # went off, which is the one corner of the square that says so.
    assert numpy.allclose(
        is_true_on_its_deadline(times),
        square[:, : window.slices, window.slices].sum(axis=1),
        atol=1e-12,
    )
    # The strike ends it, so the state is worth less than the same claim with nothing
    # that can end it.
    without = forward_pass(
        _map([_claim("opens", prior=0.5)]),
        window_of(_map([_claim("opens", prior=0.5)]), DAY_ZERO, slices=5),
        _drawn(_map([_claim("opens", prior=0.5)])),
        persistence={"opens": "state"},
    )
    assert float(is_true_on_its_deadline(times)[0]) < float(
        is_true_on_its_deadline(without.times["opens"])[0]
    )


def test_a_sustain_arrow_out_of_a_state_stops_pushing_and_a_trigger_keeps_going() -> None:
    claims = [_claim("opens", prior=0.5), _claim("strike"), _claim("ending", prior=0.3)]
    ends_it = _arrow("strike", "opens", strength=-2.0)
    drawn_values = {"strike->opens": [0.1], "opens->ending": [0.7]}

    answers = {}
    for mode in ("trigger", "sustain"):
        graph = _map(claims, [ends_it, _arrow("opens", "ending", strength=1.2, mode=mode)])
        window = window_of(graph, DAY_ZERO, slices=5)
        forward = forward_pass(
            graph, window, _drawn(graph, with_cause=drawn_values), persistence={"opens": "state"}
        )
        answers[mode] = float(is_true_on_its_deadline(forward.times["ending"])[0])

    # A trigger arrow is a toppled domino: once the state came on it keeps pushing
    # whether or not the state is still holding. A sustain arrow is dead the moment
    # the state stops, so it can only ever push less.
    assert answers["sustain"] < answers["trigger"]


def test_supposing_a_state_holds_it_on_from_the_start_and_never_off() -> None:
    graph = _map(
        [_claim("opens", prior=0.5), _claim("strike"), _claim("ending", prior=0.3)],
        [
            _arrow("strike", "opens", strength=-2.0),
            _arrow("opens", "ending", strength=1.2, mode="sustain"),
        ],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(graph, with_cause={"strike->opens": [0.1], "opens->ending": [0.7]})
    supposed = forward_pass(
        graph,
        window,
        drawn,
        pinned={"opens": Pin(value=True, kind="do")},
        persistence={"opens": "state"},
    )

    square = as_joint(supposed.times["opens"])
    assert float(square[0, 0, window.slices]) == 1.0
    assert float(square.sum()) == 1.0
    assert numpy.array_equal(supposed.table["opens"], numpy.array([[0.0, 1.0]]))
    # A cause the map says nothing can end is worth more to its effect than one the
    # strike might stop.
    plain = forward_pass(graph, window, drawn, persistence={"opens": "state"})
    assert float(is_true_on_its_deadline(supposed.times["ending"])[0]) > float(
        is_true_on_its_deadline(plain.times["ending"])[0]
    )


def test_the_square_of_still_holding_chances_is_built_once_a_state(monkeypatch) -> None:
    """A state's yes/no table re-weighs the pass; it does not run the pass again.

    The square of *came on in this slice, still holding at the end of that one* is
    the costliest thing a state asks for. A state with two causes has four
    combinations of their truths, and its table used to be filled by running the
    whole state pass once for each of them. This counts what is built on a map with
    one state and two causes: one square, for the state's own times, and no more.
    """
    graph = _map(
        [
            _claim("shock", prior=0.4),
            _claim("strike", prior=0.35),
            _claim("opens", prior=0.5),
            _claim("ending", prior=0.3),
        ],
        [
            _arrow("shock", "opens", strength=1.4),
            _arrow("strike", "opens", strength=-2.0),
            _arrow("opens", "ending", strength=1.2, mode="sustain"),
        ],
    )
    window = window_of(graph, DAY_ZERO, slices=5)
    drawn = _drawn(
        graph,
        with_cause={"shock->opens": [0.8], "strike->opens": [0.1], "opens->ending": [0.7]},
    )

    built: list[int] = []
    real = states._still_on_at_each_slice

    def watched(*arguments, **keywords):
        built.append(1)
        return real(*arguments, **keywords)

    monkeypatch.setattr(states, "_still_on_at_each_slice", watched)
    forward = forward_pass(graph, window, drawn, persistence={"opens": "state"})

    assert forward.table["opens"].shape == (1, 2, 2, 2)
    assert len(built) == 1
