"""The weighted sample — writer C.

Every test here asserts an identity, a direction, an ordering or a state on a map
the test builds. Not one number an engine worked out is written down.

Two words, used throughout. *the claim's own chance* — the chance it reaches its
deadline with none of the map's causes on. *the chance with one cause on* — the
chance it reaches its deadline with that one cause on from day zero and no other.

**Where a tolerance appears, its arithmetic is in the test.** A weighted share of a
yes-or-no answer has a standard error of at most the square root of one quarter
divided by the effective number of draws, so four of those is one over the square
root of the effective count. Every tolerance below is that expression, read off the
sample's own effective count — never a number somebody chose.
"""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

import numpy
import pytest

from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.forward import Forward, forward_pass
from katalyst.domain.graph import Graph
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition, Resolution
from katalyst.domain.rates import Drawn, Persistence, Pin, Window, window_of
from katalyst.domain.sampling import Sample, sample_forward
from katalyst.domain.solving import ImpossibleObservation, solve
from katalyst.domain.states import NEVER, STILL_HOLDING
from tests.oracles import by_integrating as integrating

DAY_ZERO = date(2026, 10, 1)
SEED = 20260922
"""One seed for the whole file, so every test in it draws the same worlds."""

FOUR_STANDARD_ERRORS = 4.0
"""How many standard errors a sampled number is allowed to sit from an exact one.

Four, which is the usual *this did not happen by chance* distance. It is the one
choice in this file that is a judgement rather than an arithmetic consequence, and
it is written once here rather than beside each number it governs.
"""


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
    with_cause: Mapping[str, float] | None = None,
) -> Drawn:
    """One draw of every stated number, the same in every version.

    A claim's own chance is the one written on it. The chance with one cause on is
    stated per arrow, and defaults to a number above every prior this file uses, so
    that an arrow helps unless a test says otherwise.
    """
    with_cause = with_cause or {}
    return Drawn(
        versions=versions,
        own_chance={one.id: numpy.full(versions, float(one.prior.p)) for one in graph.propositions},
        with_this_cause={
            one.id: numpy.full(versions, with_cause.get(one.id, 0.6)) for one in graph.links
        },
    )


def _pass(
    graph: Graph,
    *,
    slices: int = 6,
    versions: int = 1,
    with_cause: Mapping[str, float] | None = None,
    pinned: Mapping[str, Pin] | None = None,
    persistence: Mapping[str, Persistence] | None = None,
) -> tuple[Window, Forward]:
    """One forward pass over a map, and the window it was cut on."""
    window = window_of(graph, DAY_ZERO, slices=slices)
    forward = forward_pass(
        graph,
        window,
        _drawn(graph, versions=versions, with_cause=with_cause),
        pinned=dict(pinned or {}),
        persistence=dict(persistence or {}),
    )
    return window, forward


def _sample(
    graph: Graph,
    *,
    slices: int = 6,
    versions: int = 1,
    with_cause: Mapping[str, float] | None = None,
    pinned: Mapping[str, Pin] | None = None,
    persistence: Mapping[str, Persistence] | None = None,
    worlds: int = 4_000,
    chunk: int = 50_000,
    seed: int = SEED,
) -> tuple[Sample, Mapping[str, numpy.ndarray]]:
    """Work a map through and draw worlds from it, with the exact answer beside them."""
    held = dict(pinned or {})
    window, forward = _pass(
        graph,
        slices=slices,
        versions=versions,
        with_cause=with_cause,
        pinned=held,
        persistence=persistence,
    )
    exact = solve(forward, held)
    drawn = sample_forward(
        forward,
        held,
        window=window,
        version=0,
        seed=seed,
        worlds=worlds,
        chunk=chunk,
        exact=exact,
    )
    return drawn, exact


def _corrected(drawn: Sample, exact: Mapping[str, numpy.ndarray]) -> dict[str, float]:
    """Each claim's number at the drawn version, with the sample's correction added."""
    return {claim: float(exact[claim][0]) + drawn.correction[claim] for claim in drawn.claims}


def _a_diamond() -> Graph:
    """One cause reaching one effect two ways at once — the shape the tables get wrong.

    Seeing the sink happened says something about *when* the source happened, not
    only whether it did, and the two routes share that source. It is the case the
    control variate exists for.
    """
    return _map(
        [_claim("a"), _claim("b"), _claim("c"), _claim("d")],
        [
            _arrow("a", "b", shape="impulse", half_life=4.0),
            _arrow("a", "c", lag=6.0),
            _arrow("b", "d"),
            _arrow("c", "d", shape="impulse", half_life=8.0),
        ],
    )


def _the_diamond_for_the_enumerator(slices: int) -> tuple[integrating.Map, integrating.Grid]:
    """The same diamond, written in the second oracle's own words.

    The oracle is forbidden the engine's tables: it is handed the arrows as a
    person stated them and enumerates the whole joint of arrival slices itself. So
    the map has to be written out twice, once for each. Both run on the **same
    twelve slices of each claim's own window with an arrival taken at the middle of
    its slice**, because at a different grid the two would differ about the grid
    rather than about the arithmetic.
    """
    graph = _a_diamond()
    own = {one.id: float(one.prior.p) for one in graph.propositions}
    with_cause = float(_drawn(graph).with_this_cause[graph.links[0].id][0])
    causes: dict[str, list[integrating.Arrow]] = {one.id: [] for one in graph.propositions}
    for arrow in graph.links:
        causes[arrow.target].append(
            integrating.Arrow(
                source=arrow.source,
                with_this_cause=with_cause,
                lag=arrow.lag,
                shape=arrow.shape,
                half_life=arrow.half_life if arrow.half_life is not None else 10.0,
                mode=arrow.mode,
            )
        )
    days = float((graph.propositions[0].resolution.by - DAY_ZERO).days)
    written = {
        one.id: integrating.Claim(
            deadline=float((one.resolution.by - DAY_ZERO).days),
            own_chance=own[one.id],
            causes=tuple(causes[one.id]),
        )
        for one in graph.propositions
    }
    return written, integrating.Grid(days=days, slices=slices, cut=integrating.EACH_CLAIMS_OWN)


def _a_map_with_states() -> tuple[Graph, dict[str, Persistence], dict[str, float]]:
    """A state something can end, a state nothing can end, and an arrow reading a stretch.

    `s` holds over a stretch and `e` can end it — an arrow whose stated chance is
    below the claim's own bends the rate a state stops at. `t` reads `s`'s whole
    stretch through a `sustain` arrow, which is the one arrow that goes dead when
    its source stops holding. `u` is a state nothing on the map can end, which
    decision record 0017 says is identical to the same claim written as an event.
    """
    graph = _map(
        [_claim("e"), _claim("s", prior=0.5), _claim("t"), _claim("u", prior=0.4)],
        [_arrow("e", "s", strength=-1.2), _arrow("s", "t", mode="sustain")],
    )
    # The chance with `e` on is stated **below** `s`'s own chance, which is what makes
    # the arrow an ending one rather than a helping one.
    return graph, {"s": "state", "u": "state"}, {"e->s": 0.2}


# --- The control variate ----------------------------------------------------


def test_the_control_variate_leaves_the_exact_answer_where_no_evidence_moves_it() -> None:
    """Where the two models cannot disagree, the correction is nought to twelve places.

    Both models read the **same** random number for a claim's truth. On a map of
    claims with no causes the two chances are the same number, so the two draws
    agree world for world and the difference is exactly nothing. Supposing a claim
    does the same for what it feeds: a supposed cause happened in one known slice,
    so averaging over when it happened averages over one thing.
    """
    nothing_joined, _ = _sample(_map([_claim("x"), _claim("y", prior=0.7), _claim("z")]))
    for moved in nothing_joined.correction.values():
        assert abs(moved) < 1e-12

    supposed, _ = _sample(
        _map([_claim("a"), _claim("b")], [_arrow("a", "b")]),
        pinned={"a": Pin(value=True, kind="do")},
    )
    for moved in supposed.correction.values():
        assert abs(moved) < 1e-12


def test_the_sample_and_the_tables_agree_where_no_evidence_moves_them() -> None:
    """With nothing reported, the sample says what the exact tables already said.

    Not to the last bit — the two models really do differ on a diamond, which is
    the whole reason the sampler exists — but inside four standard errors of a
    weighted share, read off this sample's own effective count.
    """
    drawn, exact = _sample(_a_diamond(), slices=12, worlds=20_000)
    allowed = FOUR_STANDARD_ERRORS * (0.25 / drawn.effective) ** 0.5

    for claim in drawn.claims:
        assert abs(drawn.correction[claim]) < allowed
        corrected = exact[claim] + drawn.correction[claim]
        assert bool(((corrected >= 0.0) & (corrected <= 1.0)).all())


def test_this_happened_moves_the_cause_the_way_the_enumerator_says() -> None:
    """News about the sink of a diamond moves its source, and by as much as the judge says.

    The judge is `tests/oracles/by_integrating.py`, which is forbidden the engine's
    tables and enumerates the whole joint of arrival slices from the arrows alone.
    Both run on twelve slices of each claim's own window with an arrival taken at
    the middle of its slice. The distance allowed is four standard errors of a
    weighted share at this sample's own effective count.
    """
    graph = _a_diamond()
    written, grid = _the_diamond_for_the_enumerator(12)
    news = {"d": Pin(value=True, kind="observe")}

    quiet, before = _sample(graph, slices=12, worlds=20_000)
    told, exact = _sample(graph, slices=12, worlds=20_000, pinned=news)
    judged = integrating.by_integrating(written, grid, observed={"d": True})
    assert judged is not None

    corrected = _corrected(told, exact)
    untouched = _corrected(quiet, before)

    # The news is that the effect happened, and every arrow on this map helps, so
    # every claim upstream of it can only have become more likely.
    assert corrected["a"] > untouched["a"]
    assert quiet.correction["a"] != told.correction["a"]

    allowed = FOUR_STANDARD_ERRORS * (0.25 / told.effective) ** 0.5
    for claim in told.claims:
        assert abs(corrected[claim] - judged[claim]) < allowed


def test_the_correction_is_one_scalar_per_claim_shared_across_versions() -> None:
    """One number per claim, not one per version — which is what makes the sample cheap.

    Two thousand versions redraw the numbers a person stated; the sample is drawn
    once, at version zero, and hands back one number for every claim. Drawing the
    same map at one version and at three gives the same corrections, because
    version zero is the same row of numbers in both.
    """
    graph = _a_diamond()
    news = {"d": Pin(value=True, kind="observe")}
    one_version, _ = _sample(graph, pinned=news)
    three_versions, exact = _sample(graph, versions=3, pinned=news)

    assert set(one_version.correction) == set(one_version.claims)
    assert all(isinstance(moved, float) for moved in one_version.correction.values())
    assert one_version.correction == three_versions.correction
    assert all(one.shape == (3,) for one in exact.values())


def test_a_correction_never_takes_a_version_outside_nought_and_one() -> None:
    """One step serves every version, so it is held to what the whole range can take.

    A claim the map already calls all but certain cannot be moved further up by a
    sample, however the worlds fall.
    """
    graph = _map(
        [_claim("a", prior=0.99), _claim("b", prior=0.99)],
        [_arrow("a", "b", strength=3.0)],
    )
    drawn, exact = _sample(
        graph, with_cause={"a->b": 0.999}, pinned={"b": Pin(value=True, kind="observe")}
    )
    for claim in drawn.claims:
        corrected = exact[claim] + drawn.correction[claim]
        assert bool(((corrected >= 0.0) & (corrected <= 1.0)).all())


# --- The draw itself --------------------------------------------------------


def test_the_sample_is_seeded() -> None:
    """The same seed gives the same days and the same weights, bit for bit.

    A different seed does not, which is what makes the first assertion mean
    something.
    """
    graph = _a_diamond()
    news = {"d": Pin(value=True, kind="observe")}
    once, _ = _sample(graph, pinned=news, seed=SEED)
    again, _ = _sample(graph, pinned=news, seed=SEED)
    elsewhere, _ = _sample(graph, pinned=news, seed=SEED + 1)

    assert once.on_day.tobytes() == again.on_day.tobytes()
    assert once.off_day.tobytes() == again.off_day.tobytes()
    assert once.weight.tobytes() == again.weight.tobytes()
    assert once.weight.tobytes() != elsewhere.weight.tobytes()


def test_how_many_worlds_are_held_at_once_changes_nothing() -> None:
    """Blocking is about memory and nothing else.

    Every claim draws from its own stream of random numbers in world order, so
    cutting the worlds into blocks cannot change which world is which. The days and
    the weights are therefore bit for bit the same. The correction is the same to
    the last bit or two and no further, because a running total added a block at a
    time adds the very same numbers in a different order, and that is worth an ulp
    of a double.
    """
    graph = _a_diamond()
    news = {"d": Pin(value=True, kind="observe")}
    whole, _ = _sample(graph, pinned=news, worlds=3_000, chunk=3_000)
    blocked, _ = _sample(graph, pinned=news, worlds=3_000, chunk=700)

    assert whole.on_day.tobytes() == blocked.on_day.tobytes()
    assert whole.off_day.tobytes() == blocked.off_day.tobytes()
    assert whole.weight.tobytes() == blocked.weight.tobytes()
    for claim in whole.claims:
        assert whole.correction[claim] == pytest.approx(blocked.correction[claim], abs=1e-12)


def test_the_effective_count_is_never_above_the_worlds_drawn() -> None:
    """What the two-hundred-draw floor counts is this, never the number of rows.

    With nothing reported every world counts the same and the effective count is
    the number drawn. With something reported the worlds stop counting the same,
    and the count falls.
    """
    graph = _a_diamond()
    quiet, _ = _sample(graph, worlds=2_000)
    assert quiet.effective == quiet.worlds

    told, _ = _sample(graph, worlds=2_000, pinned={"d": Pin(value=True, kind="observe")})
    assert 0.0 < told.effective < told.worlds
    assert told.weight.shape == (told.worlds,)


def test_a_sample_nothing_agrees_with_is_refused_rather_than_divided_through() -> None:
    """No world agreeing with the news means no answer, said out loud by name.

    A claim the map gives no chance at all, reported to have happened, leaves every
    world weighing nothing. Dividing by that and calling the result a chance is the
    untraceable number this repository refuses, so the sampler raises what the solve
    raises.
    """
    graph = _map([_claim("a", prior=0.0)])
    window, forward = _pass(graph)
    news = {"a": Pin(value=True, kind="observe")}

    with pytest.raises(ImpossibleObservation):
        sample_forward(
            forward,
            news,
            window=window,
            version=0,
            seed=SEED,
            worlds=200,
            exact=solve(forward, {}),
        )


def test_a_sample_is_at_least_one_world_drawn_at_least_one_at_a_time() -> None:
    """Nothing to draw is refused rather than answered with an empty table."""
    window, forward = _pass(_map([_claim("a")]))
    with pytest.raises(ValueError, match="at least one world"):
        sample_forward(
            forward,
            {},
            window=window,
            version=0,
            seed=SEED,
            worlds=0,
            exact=solve(forward, {}),
        )


# --- The days stack 06 reads ------------------------------------------------


def test_the_days_are_slice_middles_rounded_to_whole_days() -> None:
    """The one contract stack 06 reads: an arrival lands on a slice's middle and nowhere else.

    Read off each claim's **own** grid, because each claim is cut from its own
    resolve-by day. A reader stepping one day at a time sees a surprise on at most
    as many days as there are slices, however long the window is.
    """
    slices = 24
    graph = _map(
        [_claim("a"), _claim("b", days=30)],
        [_arrow("a", "b")],
    )
    drawn, _ = _sample(graph, slices=slices, worlds=3_000)

    assert drawn.day_zero == DAY_ZERO
    assert drawn.days == 60
    _, forward = _pass(graph, slices=slices)
    for column, claim in enumerate(drawn.claims):
        middles = forward.shapes[claim].middle_day[:slices]
        allowed = set(numpy.rint(middles).astype(int).tolist()) | {NEVER}
        landed = set(drawn.on_day[:, column].tolist())
        assert landed <= allowed
        assert len(landed - {NEVER}) <= slices
        assert bool((drawn.on_day[:, column] <= drawn.days).all())


def test_an_event_never_goes_off() -> None:
    """An event happens once and stays happened, so it carries the still-holding marker.

    Except where it never came on at all, when both tables say so: a claim that
    never started cannot have stopped.
    """
    drawn, _ = _sample(_a_diamond(), worlds=2_000)
    never = drawn.on_day == NEVER

    assert bool((drawn.off_day[~never] == STILL_HOLDING).all())
    assert bool((drawn.off_day[never] == NEVER).all())
    assert bool(never.any()), "this map never left a claim that failed to happen"


def test_a_states_off_day_is_never_before_its_on_day() -> None:
    """A state cannot stop before it starts, and a state nothing can end does not stop.

    Built into how the off day is drawn rather than checked afterwards: the chance
    a state stopped is nought for every slice before the one it came on in.
    """
    graph, kinds, stated = _a_map_with_states()
    drawn, _ = _sample(graph, persistence=kinds, with_cause=stated, worlds=3_000)
    ended = (drawn.off_day != STILL_HOLDING) & (drawn.off_day != NEVER)

    assert bool((drawn.off_day[ended] >= drawn.on_day[ended]).all())
    assert bool(ended.any()), "nothing on this map ever stopped holding"
    assert bool(((drawn.on_day == NEVER) == (drawn.off_day == NEVER)).all())

    nothing_ends_it = drawn.claims.index("u")
    assert bool((drawn.off_day[:, nothing_ends_it] != drawn.days).all())
    assert set(drawn.off_day[:, nothing_ends_it].tolist()) <= {STILL_HOLDING, NEVER}


def test_a_state_reported_holding_is_still_holding_in_every_world_kept() -> None:
    """*This happened* on a state means it is holding on its deadline, and nothing else.

    So every world kept has it on and not yet off. Reported the other way, every
    world kept has it never on or already stopped.
    """
    graph, kinds, stated = _a_map_with_states()
    column = None
    for value, expected in ((True, True), (False, False)):
        drawn, _ = _sample(
            graph,
            persistence=kinds,
            with_cause=stated,
            worlds=2_000,
            pinned={"s": Pin(value=value, kind="observe")},
        )
        column = drawn.claims.index("s")
        holding = (drawn.on_day[:, column] != NEVER) & (drawn.off_day[:, column] == STILL_HOLDING)
        assert bool(holding.all()) is expected
    assert column is not None


def test_a_supposed_claim_is_on_from_the_first_slice_or_never() -> None:
    """Supposing a claim true puts it on at the very start of the window, in every world.

    Supposing it false means it never came on, and then neither table says a day.
    """
    graph = _map([_claim("a"), _claim("b")], [_arrow("a", "b")])
    _, forward = _pass(graph)
    first_day = int(numpy.rint(forward.shapes["a"].middle_day[0]))

    held, _ = _sample(graph, pinned={"a": Pin(value=True, kind="do")}, worlds=500)
    column = held.claims.index("a")
    assert bool((held.on_day[:, column] == first_day).all())
    assert bool((held.off_day[:, column] == STILL_HOLDING).all())

    denied, _ = _sample(graph, pinned={"a": Pin(value=False, kind="do")}, worlds=500)
    assert bool((denied.on_day[:, column] == NEVER).all())
    assert bool((denied.off_day[:, column] == NEVER).all())


def test_an_arrow_that_holds_a_claim_back_is_drawn_over_the_slices_its_cause_arrived_in() -> None:
    """The one place the work still multiplies out, drawn one world at a time.

    An arrow stated below its target's own chance scales that target's rate down
    while it is on, so the target's whole spread depends on **when** the arrow's
    cause arrived. A world gathers the row for the slice its cause landed in.
    """
    graph = _map([_claim("c"), _claim("d")], [_arrow("c", "d", strength=-1.5)])
    _, forward = _pass(graph)
    assert forward.shapes["d"].holds_back == (0,)

    drawn, _ = _sample(graph, worlds=2_000, pinned={"d": Pin(value=False, kind="observe")})
    column = drawn.claims.index("d")
    assert bool((drawn.on_day[:, column] == NEVER).all())
    assert 0.0 < drawn.effective <= drawn.worlds
