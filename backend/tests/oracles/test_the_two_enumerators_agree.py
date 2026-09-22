"""The two oracles, checked against each other and against the judge they came from.

An oracle nobody checks is a second program that can be wrong in private. These
tests do the three things that can be done before there is a new engine to judge:

* the generated maps really are adversarial — an impulse, a diamond, states,
  `sustain` arrows — and the same maps on every machine and in every run;
* the two enumerators answer the same questions with the same numbers, where a
  question can be put to both of them;
* `by_integrating` reproduces the stack-05 spike's own scratch judge, which is the
  program every measurement in records 0016 and 0017 was taken with.

**Where the two can be compared, and why that is the one place.** `by_summing`
is given yes/no tables and `by_integrating` works over event *times*, so the two
speak different languages — except at **one slice**, where a claim's time
variable has exactly two values, *it happened in the one slice* and *it never
happened*. At one slice an event map's factors **are** yes/no tables, written in
the opposite order, and the two enumerators can be put side by side over every
question. What that comparison does not reach is the time grid itself; what it
does reach is everything else — several causes on one claim, a diamond, the
*Suppose this is true* surgery, the *This happened* conditioning, and the
elimination against the whole joint added up by brute force.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from tests.oracles import by_integrating as integrating
from tests.oracles import maps as generated
from tests.oracles.by_summing import ImpossibleEvidence, Pin, Tables, by_summing

TO_THE_LAST_BIT = 1e-12
"""The distance two programs adding up the same numbers are allowed to be apart.

Both enumerators do double-precision arithmetic over the same quantities in a
different order, so they agree to round-off — around `1e-16` on these maps — and
this is the loosest the difference is ever allowed to be. It is not an accuracy
tolerance: record 0016's `.005` is a different measurement, of the engine against
`by_integrating`, and lives in the engine's own test.
"""

ONE_SLICE = integrating.Grid(days=generated.WINDOW, slices=1)
"""The window uncut, where an event map's factors are yes/no tables."""

WHAT_THE_JUDGE_SAID = Path(__file__).with_name("what_the_scratch_judge_said.json")


# --- The maps ---------------------------------------------------------------


def test_the_generated_maps_are_adversarial() -> None:
    """The set holds every shape the oracles exist to be attacked with.

    An **impulse** is an arrow whose push fades by halves, which is where timing
    error lives. A **diamond** is one claim reaching another both straight and
    round through a third, which is where the red team's worst cases all were. And
    maps carrying **states** — claims that hold over a stretch and can stop — with
    `sustain` arrows out of them, because a `sustain` arrow is the only thing that
    reads a state's whole interval.
    """
    events = [graph for _name, graph in generated.adversarial_events()]
    with_states = [graph for _name, graph, _events in generated.with_and_without_states()]
    hard = [graph for _name, graph in generated.hard_on_states()]

    assert events and with_states and hard, "every recipe produced at least one map"
    assert any(generated.has_an_impulse(one) for one in events)
    assert any(generated.has_a_diamond(one) for one in events)
    assert any(generated.has_a_diamond(one) for one in hard)
    assert all(generated.has_a_state(one) for one in with_states)
    assert any(generated.has_a_sustain_arrow(one) for one in with_states)
    assert all(generated.has_a_sustain_arrow(one) for one in hard)


def test_both_halves_of_a_skeleton_are_the_same_map_but_for_its_states() -> None:
    """The control really is the same map: only which claims are states differs.

    Every deadline, every stated chance, every delay, every shape and every
    half-life is the one draw, so a comparison between the two halves is a
    comparison about states and about nothing else.
    """
    for name, with_states, all_events in generated.with_and_without_states():
        assert sorted(with_states) == sorted(all_events), name
        for claim in with_states:
            mine, theirs = with_states[claim], all_events[claim]
            assert mine.deadline == theirs.deadline, (name, claim)
            assert mine.own_chance == theirs.own_chance, (name, claim)
            assert [one.source for one in mine.causes] == [one.source for one in theirs.causes], (
                name,
                claim,
            )
            for one, two in zip(mine.causes, theirs.causes, strict=True):
                assert (one.with_this_cause, one.lag, one.shape, one.half_life) == (
                    two.with_this_cause,
                    two.lag,
                    two.shape,
                    two.half_life,
                ), (name, claim)
        assert generated.has_a_state(with_states) and not generated.has_a_state(all_events)


def test_the_generator_is_seeded() -> None:
    """Drawn twice, the recipes hand back the very same maps.

    A judge that is different on a second run cannot say anything about a
    difference between two engines.
    """
    for recipe in (generated.adversarial_events, generated.hard_on_states):
        first, again = recipe(), recipe()
        assert [name for name, _ in first] == [name for name, _ in again]
        assert all(a == b for (_n, a), (_m, b) in zip(first, again, strict=True))


def test_every_generated_map_is_within_the_second_oracles_reach() -> None:
    """Four claims or fewer, which is the largest map anybody can enumerate times over.

    Record 0016 says in as many words that its accuracy is measured on four-claim
    maps only. This is the line that makes that true of the set rather than of the
    intention.
    """
    for name, graph in generated.a_few_of_each():
        assert len(graph) <= 4, name


# --- The two enumerators, side by side --------------------------------------


def _as_yes_no_tables(graph: integrating.Map, versions: list[integrating.Map] | None = None):
    """One map's factors at a single slice, rewritten as yes/no tables.

    At one slice a claim's time variable runs `[it happened, it never did]`, where
    a yes/no table's own axis runs `[it did not, it did]` — the opposite way round.
    Reversing every axis turns one coding into the other, and that is the whole of
    the translation.

    Args:
        graph: The map, every claim an event.
        versions: The same map with its stated chances redrawn, when a leading
            version axis is wanted. Left out, the tables carry no version axis.

    Returns:
        The tables, ready for `by_summing`.
    """
    assert not generated.has_a_state(graph), "a state has four values at one slice, not two"
    drawn = versions or [graph]
    backwards = {}
    for one in drawn:
        ready = integrating.prepare(one, ONE_SLICE)
        for name in ready.order:
            flipped = ready.factor[name][tuple(slice(None, None, -1) for _ in ready.axes[name])]
            backwards.setdefault(name, []).append(flipped)
    ready = integrating.prepare(graph, ONE_SLICE)
    return Tables(
        order=ready.order,
        causes={name: ready.axes[name][:-1] for name in ready.order},
        table={name: (np.stack(rows) if versions else rows[0]) for name, rows in backwards.items()},
    )


def _both_ways(graph: integrating.Map, supposed: dict, observed: dict):
    """Ask the same question of both enumerators, and hand back the two answers."""
    theirs = integrating.by_integrating(
        graph, ONE_SLICE, supposed=supposed or None, observed=observed or None
    )
    pinned = {name: Pin(value, "do") for name, value in supposed.items()}
    pinned |= {name: Pin(value, "observe") for name, value in observed.items()}
    try:
        added = by_summing(_as_yes_no_tables(graph), pinned)
    except ImpossibleEvidence:
        return theirs, None
    return theirs, {name: float(one) for name, one in added.items()}


def test_the_two_enumerators_agree_on_every_question() -> None:
    """Adding the joint up by hand and eliminating it give the same numbers.

    Over the red team's adversarial event maps, at one slice, on every question
    the product can ask: no edit, *Suppose this is true* both ways on every claim,
    and *This happened* both ways on every claim. Two different programs, two
    different methods — the whole joint multiplied out and added up, against one
    claim summed out at a time — and they have to answer alike.
    """
    checked = 0
    for name, graph in generated.adversarial_events()[:20]:
        for label, supposed, observed in generated.all_the_questions(list(graph)):
            theirs, mine = _both_ways(graph, supposed, observed)
            if theirs is None or mine is None:
                assert theirs is None and mine is None, (name, label)
                continue
            for claim in theirs:
                assert abs(theirs[claim] - mine[claim]) < TO_THE_LAST_BIT, (name, label, claim)
            checked += 1
    assert checked, "no question was put to both enumerators"


def test_the_version_axis_is_one_pass_and_not_many() -> None:
    """A stack of versions answered at once equals each version answered alone.

    A version of a map is one coherent redraw of every number a person stated.
    `by_summing` takes them as a leading axis so a whole range is one pass, and
    that has to be the same arithmetic as running the versions one at a time —
    bit for bit, not merely close.
    """
    rng = np.random.default_rng(20260922)
    for name, graph in generated.adversarial_events()[:6]:
        versions = [_redrawn(graph, rng) for _which in range(4)]
        together = by_summing(_as_yes_no_tables(graph, versions))
        for which, one in enumerate(versions):
            alone = by_summing(_as_yes_no_tables(one))
            for claim in alone:
                assert together[claim][which] == alone[claim], (name, which, claim)


def test_a_version_axis_answers_both_verbs_too() -> None:
    """Supposing and reporting hold in every version at once, and version by version.

    The test above stacks versions with nothing edited, and the tests that edit
    something use a single version, so between them neither ever put a pin and a
    version axis in the same call. That gap hid a real fault: a pinned claim's
    certainty was built without the version axis the rest of the joint carries, and
    the oracle could not answer at all. A claim is pinned in **every** version — it
    is the same lever and the same news whatever numbers were drawn — so a stack of
    versions has to give, bit for bit, what each version alone gives.
    """
    rng = np.random.default_rng(20260923)
    for name, graph in generated.adversarial_events()[:4]:
        versions = [_redrawn(graph, rng) for _which in range(3)]
        stacked = _as_yes_no_tables(graph, versions)
        for claim in stacked.order:
            for kind in ("do", "observe"):
                for value in (True, False):
                    pinned = {claim: Pin(value, kind)}
                    together = by_summing(stacked, pinned)
                    for which, one in enumerate(versions):
                        alone = by_summing(_as_yes_no_tables(one), pinned)
                        for other in alone:
                            assert together[other][which] == alone[other], (
                                name,
                                claim,
                                kind,
                                value,
                                which,
                                other,
                            )


def _redrawn(graph: integrating.Map, rng: np.random.Generator) -> integrating.Map:
    """One version of a map: every stated chance redrawn, nothing else touched.

    A version changes only the numbers a person stated — never a delay, a shape or
    a half-life — which is the rule the engine's own version draw obeys.
    """
    return {
        name: integrating.Claim(
            deadline=claim.deadline,
            own_chance=float(rng.uniform(0.05, 0.6)),
            persistence=claim.persistence,
            causes=tuple(
                integrating.Arrow(
                    one.source,
                    float(rng.uniform(0.02, 0.95)),
                    one.lag,
                    one.shape,
                    one.half_life,
                    one.mode,
                )
                for one in claim.causes
            ),
        )
        for name, claim in graph.items()
    }


def test_supposing_a_claim_leaves_its_causes_where_they_were() -> None:
    """*Suppose this is true* is a lever, so nothing upstream of it may move.

    This is invariant INV-3 read off the oracle rather than off the engine: in
    `by_summing`, supposing a claim throws its table away, and with it every arrow
    into it, so its causes are answered by the map that is left — which is the map
    they were already on.

    **To the last bit rather than bit for bit**, and the difference is worth the
    sentence. Supposing a claim zeroes half of this oracle's joint, so the answer
    is the sum of a different set of numbers in a different order, and the last
    place or two of the arithmetic moves — measured at `8e-17` on the first map
    this runs. The engine's own locality claim *is* bit for bit, because it never
    builds the whole joint; it is checked where it belongs, in `test_patches.py`.
    """
    for name, graph in generated.adversarial_events()[:10]:
        tables = _as_yes_no_tables(graph)
        base = by_summing(tables)
        for claim in tables.order:
            causes = {one.source for one in graph[claim].causes}
            if not causes:
                continue
            for value in (True, False):
                levered = by_summing(tables, {claim: Pin(value, "do")})
                for cause in causes:
                    moved = abs(float(levered[cause]) - float(base[cause]))
                    assert moved < TO_THE_LAST_BIT, (name, claim, cause, value, moved)


def test_an_impossible_report_is_refused_rather_than_divided_by_zero() -> None:
    """News that cannot happen is said out loud, never answered with a number.

    The two tables here are inputs written by hand for this one case, not numbers
    anything worked out: a cause that never happens, and an effect that reads it.
    Reporting that the cause happened leaves no world at all, and a likelihood read
    off nothing is exactly the untraceable number this repository vetoes — so the
    oracle raises rather than dividing by zero and calling the answer a number.
    """
    tables = Tables(
        order=("cause", "effect"),
        causes={"cause": (), "effect": ("cause",)},
        table={
            "cause": np.array([1.0, 0.0]),
            "effect": np.array([[0.75, 0.25], [0.25, 0.75]]),
        },
    )
    assert by_summing(tables)["effect"] > 0.0, "the map answers perfectly well until the news"
    with pytest.raises(ImpossibleEvidence):
        by_summing(tables, {"cause": Pin(True, "observe")})


# --- Which window a claim is cut from ---------------------------------------


def test_each_claim_is_cut_from_its_own_deadline() -> None:
    """The default grid ends every claim's last slice exactly on the day it is judged.

    Cut from the map's longest deadline instead, every claim's boundaries move when
    somebody inserts a claim judged far later — including claims that insertion has
    no arrow to. Cut from a claim's own deadline, nothing else on the map can move
    one, which is how the engine makes locality a shape of the arithmetic rather
    than a promise. The oracle has to follow, or it would judge the engine on a grid
    the engine does not run on.
    """
    for name, graph in generated.a_few_of_each():
        for claim, written in graph.items():
            edges = integrating.slice_edges(written.deadline, generated.GRID)
            assert edges[0] == 0.0, (name, claim)
            assert edges[-1] == written.deadline, (name, claim)
            middles = integrating.middle_days(written.deadline, generated.GRID)
            assert middles[-1] == np.inf, (name, claim)
            assert np.all(middles[:-1] > edges[:-1]) and np.all(middles[:-1] < edges[1:]), (
                name,
                claim,
            )


def test_the_two_cuts_are_a_real_choice_and_not_the_same_grid() -> None:
    """The shared window is kept runnable, and it is genuinely a different grid.

    A named choice nobody can tell apart is a comment. On any map whose claims are
    not all judged on the same day, the two cuts put a claim's boundaries in
    different places and answer differently — which is exactly why the committed
    comparison against the spike's scratch judge names the window it was measured
    on rather than taking whatever the default happens to be.
    """
    shared = integrating.Grid(days=generated.WINDOW, cut=integrating.ONE_SHARED)
    apart = 0
    for _name, graph in generated.a_few_of_each():
        late = max(one.deadline for one in graph.values())
        early = [name for name, one in graph.items() if one.deadline < late]
        if not early:
            continue
        for claim in early:
            deadline = graph[claim].deadline
            mine = integrating.slice_edges(deadline, generated.GRID)
            theirs = integrating.slice_edges(deadline, shared)
            assert not np.allclose(mine, theirs)
            apart += 1
    assert apart, "no map in the set had two claims judged on different days"


# --- Against the judge every published measurement was taken with -----------


def test_by_integrating_reproduces_the_scratch_judge() -> None:
    """The committed oracle answers what the spike's own judge answered.

    `by_integrating` is lifted from `st2_core.py`'s `exact_over_times`, the
    program every accuracy number in records 0016 and 0017 was measured with, kept
    locally under `plans/analysis/scripts/spike-05/`. That directory is not part of
    the repository, so what is committed here is **what that judge answered**, map
    by map and question by question, written by
    `plans/analysis/scripts/stack-05-oracles/check_against_the_spike.py` and by
    nothing else. Re-run that script to rebuild the file and to compare the two
    programs directly.

    The comparison is on one grid, stated whole: **twenty-four slices of one
    sixty-day window shared by every claim** — which is what the scratch judge cut,
    and not what the engine cuts — eight points inside each slice, an arrival taken
    at the **middle** of its slice, and an arrow that ends a state read as *the
    chance it stops*. The grid is read out of the recorded file rather than assumed,
    so the day the default changed under this test it said so instead of drifting.
    """
    recorded = json.loads(WHAT_THE_JUDGE_SAID.read_text())
    assert recorded["cut"] == integrating.ONE_SHARED, "this regression is the shared window"
    grid = integrating.Grid(
        days=recorded["window_days"],
        slices=recorded["slices"],
        points=recorded["points_in_a_slice"],
        cut=recorded["cut"],
    )
    chosen = dict(generated.a_few_of_each(recorded["maps_from_how_many"]))
    assert sorted(chosen) == sorted(recorded["answers"]), "the maps are not the recorded maps"

    checked = 0
    for name, graph in chosen.items():
        ready = integrating.prepare(graph, grid)
        asked = {
            label: (supposed, observed)
            for label, supposed, observed in generated.all_the_questions(list(graph))
        }
        for label, theirs in recorded["answers"][name].items():
            supposed, observed = asked[label]
            mine = integrating.by_integrating(
                graph, grid, supposed=supposed or None, observed=observed or None, ready=ready
            )
            assert mine is not None, (name, label)
            assert sorted(mine) == sorted(theirs), (name, label)
            for claim in theirs:
                assert abs(theirs[claim] - mine[claim]) < TO_THE_LAST_BIT, (name, label, claim)
            checked += 1
    assert checked == sum(len(one) for one in recorded["answers"].values())
