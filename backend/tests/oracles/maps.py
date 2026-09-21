"""The seeded adversarial maps both oracles judge the engine on.

Three recipes, all of them lifted from the stack-05 spike with **their own
seeds** so the maps here are the same maps every measurement in record 0016 and
record 0017 was taken on:

| Recipe | Lifted from | Seed |
|---|---|---|
| `adversarial_events` | `spike-05/observe/spike_core.py`, `adversarial_maps` | 7 |
| `with_and_without_states` | `spike-05/states/maps.py`, `redteam_like` | 20260921 |
| `hard_on_states` | `spike-05/states/maps.py`, `hard` | 20260922 |

All three build four-claim maps, because that is the largest map `by_integrating`
can enumerate: an event is one variable with twenty-five values and a state is
one with six hundred and twenty-five.

**The same maps for both halves.** `with_and_without_states` returns each
skeleton twice — once with some claims made states, once with every claim an
event — from one draw, so the two halves differ in nothing but which claims are
states. That is the spike's own control, and what lets a report say a state is no
less accurate than an event without also changing the map.

**These are plain functions, not property-test generators.** They build their
inputs and hand back maps; nothing is drawn and then discarded at check time. A
trial that happens to draw no arrow at all is not a map and is passed over inside
the recipe, which is a decision about what a map is rather than a filter over a
generated stream. That matters: a property test that throws most of its inputs
away passes here and fails the build's health check on a bad seed.

**What the set is guaranteed to hold**, asserted in
`test_the_two_enumerators_agree.py` rather than promised here: an arrow carrying
a decaying impulse; a **diamond**, where one claim reaches another both directly
and round through a third, which is where the red team's worst cases all were;
and maps carrying states, with `sustain` arrows out of them.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from tests.oracles.by_integrating import Arrow, Claim, Grid, Map

WINDOW = 60.0
"""The map's whole stretch in days, as every measurement in the spike ran at."""

GRID = Grid(days=WINDOW)
"""The engine's own grid: twenty-four slices of **each claim's own** window.

Day zero to that claim's resolve-by day, eight points inside each slice, an arrival
at the middle of its slice. `Grid(days=WINDOW, cut=ONE_SHARED)` is the map's shared
window instead, which is what the spike's scratch judge cut.
"""

SHAPES = ("step", "impulse", "ramp")
EVENT = "event"
STATE = "state"


def adversarial_events(count: int = 140, seed: int = 7) -> list[tuple[str, Map]]:
    """The red team's four-claim maps, every claim an event.

    Deadlines close on one another's heels, delays up to seven tenths of the gap
    to the next deadline, mixed shapes, up to three causes a claim, and — the part
    that makes them adversarial — each arrow's stated chance drawn without regard
    to its target's, so arrows that hold a claim back appear of their own accord.

    Args:
        count: How many trials to draw. A trial that draws no arrow at all is not
            a map and is passed over, so fewer than this may come back.
        seed: The one number every draw comes from.

    Returns:
        Each map with a name, in the order they were drawn.
    """
    rng = np.random.default_rng(seed)
    out: list[tuple[str, Map]] = []
    for trial in range(count):
        deadlines = np.sort(rng.uniform(8.0, 58.0, size=4))
        names = ["c0", "c1", "c2", "c3"]
        graph: Map = {}
        for place, name in enumerate(names):
            causes: list[Arrow] = []
            for which in _which_causes(rng, deadlines, place):
                room = deadlines[place] - deadlines[which]
                # Drawn in this order, and not another, because that is the order
                # the spike drew them in and these have to be the same maps.
                lag = float(rng.uniform(0.0, 0.7) * room)
                shape = str(rng.choice(["step", "step", "impulse", "ramp"]))
                causes.append(
                    Arrow(
                        names[which],
                        float(rng.uniform(0.02, 0.95)),
                        lag,
                        shape,
                        float(rng.uniform(1.0, 15.0)),
                    )
                )
            graph[name] = Claim(
                deadline=float(deadlines[place]),
                own_chance=float(rng.uniform(0.05, 0.6)),
                causes=tuple(causes),
                persistence=EVENT,
            )
        if not any(graph[name].causes for name in names):
            continue
        out.append((f"events{trial:03d}", graph))
    return out


def with_and_without_states(
    count: int = 110, seed: int = 20260921, state_share: float = 0.9
) -> list[tuple[str, Map, Map]]:
    """The same four-claim skeletons twice: with states, and with every claim an event.

    A claim is made a state only where the recipe has **already** handed it an
    arrow whose stated chance is below its own — something that could end it — so
    no number is changed by the choice; a state nothing can end behaves exactly
    like an event and would measure nothing. Some of the arrows out of a state are
    then made `sustain`, which is the only kind of arrow that reads a state's whole
    interval.

    Args:
        count: How many trials to draw.
        seed: The one number every draw comes from.
        state_share: How often a claim that could be a state is made one.

    Returns:
        Each skeleton as (name, the map with states, the same map all events).
    """
    rng = np.random.default_rng(seed)
    out: list[tuple[str, Map, Map]] = []
    for trial in range(count):
        deadlines = np.sort(rng.uniform(8.0, 58.0, size=4))
        names = ["c0", "c1", "c2", "c3"]
        drawn: dict[str, tuple[float, float, list[tuple[str, float, float, str, float]]]] = {}
        for place, name in enumerate(names):
            causes: list[tuple[str, float, float, str, float]] = []
            for which in _which_causes(rng, deadlines, place):
                room = deadlines[place] - deadlines[which]
                causes.append(
                    (
                        names[which],
                        float(rng.uniform(0.02, 0.95)),
                        float(rng.uniform(0.0, 0.7) * room),
                        str(rng.choice(["step", "step", "impulse", "ramp"])),
                        float(rng.uniform(1.0, 15.0)),
                    )
                )
            drawn[name] = (float(deadlines[place]), float(rng.uniform(0.05, 0.6)), causes)
        if not any(drawn[name][2] for name in names):
            continue

        wanted = {
            name
            for name in names[1:]
            if rng.random() < state_share
            and any(chance < drawn[name][1] for _src, chance, *_rest in drawn[name][2])
        }
        wanted = _within_the_oracles_reach(names, drawn, wanted)
        if not wanted:
            continue
        sustaining = {
            (name, source)
            for name in names
            for source, *_rest in drawn[name][2]
            if source in wanted and rng.random() < 0.65
        }

        def build(states: set[str], drawn=drawn, names=names, sustaining=sustaining) -> Map:
            graph: Map = {}
            for name in names:
                deadline, own, causes = drawn[name]
                graph[name] = Claim(
                    deadline=deadline,
                    own_chance=own,
                    causes=tuple(
                        Arrow(
                            source,
                            chance,
                            lag,
                            shape,
                            half_life,
                            mode=(
                                "sustain"
                                if (name, source) in sustaining and source in states
                                else "trigger"
                            ),
                        )
                        for source, chance, lag, shape, half_life in causes
                    ),
                    persistence=STATE if name in states else EVENT,
                )
            return graph

        out.append((f"states{trial:03d}", build(wanted), build(set())))
    return out


def hard_on_states(count: int = 150, seed: int = 20260922) -> list[tuple[str, Map]]:
    """Maps built to break a state, rather than merely to vary.

    A state that switches on often enough by itself that both halves of *never
    came on* and *came on and stopped again* carry real weight; an ending cause
    strong enough that a good share of the worlds where it did come on end before
    the deadline; a `sustain` child whose whole number rides on that push; and, in
    most of them, a **diamond** — the ending cause pushes the child directly as
    well, so what a world knows about which half it is in matters.

    Args:
        count: How many maps to draw.
        seed: The one number every draw comes from.

    Returns:
        Each map with a name, in the order they were drawn.
    """
    rng = np.random.default_rng(seed)
    out: list[tuple[str, Map]] = []
    for trial in range(count):
        event_by = float(rng.uniform(6.0, 24.0))
        own = float(rng.uniform(0.25, 0.60))
        ends_at = float(np.clip(own * rng.uniform(0.01, 0.25), 0.002, own - 0.02))
        ending_shape = SHAPES[int(rng.integers(0, 3))]
        sustain_shape = SHAPES[int(rng.integers(0, 3))]
        diamond = rng.random() < 0.7
        graph: Map = {
            "Ev": Claim(
                deadline=event_by,
                own_chance=float(rng.uniform(0.35, 0.7)),
                persistence=EVENT,
            ),
            "O": Claim(
                deadline=55.0,
                own_chance=own,
                persistence=STATE,
                causes=(
                    Arrow(
                        "Ev",
                        ends_at,
                        float(rng.uniform(0.0, 6.0)),
                        ending_shape,
                        float(rng.uniform(2.0, 25.0)),
                    ),
                ),
            ),
        }
        child = [
            Arrow(
                "O",
                float(rng.uniform(0.55, 0.95)),
                float(rng.uniform(0.0, 12.0)),
                sustain_shape,
                float(rng.uniform(1.5, 20.0)),
                mode="sustain",
            )
        ]
        if diamond:
            child.append(
                Arrow(
                    "Ev",
                    float(rng.uniform(0.02, 0.60)),
                    float(rng.uniform(0.0, 20.0)),
                    SHAPES[int(rng.integers(0, 3))],
                    float(rng.uniform(1.5, 20.0)),
                )
            )
        graph["B"] = Claim(
            deadline=58.0,
            own_chance=float(rng.uniform(0.08, 0.30)),
            causes=tuple(child),
            persistence=EVENT,
        )
        if rng.random() < 0.5:
            graph["Z"] = Claim(
                deadline=58.0,
                own_chance=float(rng.uniform(0.08, 0.30)),
                persistence=EVENT,
                causes=(
                    Arrow(
                        "O",
                        float(rng.uniform(0.5, 0.95)),
                        float(rng.uniform(0.0, 10.0)),
                        SHAPES[int(rng.integers(0, 3))],
                        float(rng.uniform(1.5, 20.0)),
                        mode="trigger",
                    ),
                ),
            )
        out.append((f"hard{trial:03d}", graph))
    return out


def a_few_of_each(how_many: int = 4) -> list[tuple[str, Map]]:
    """A small set covering all three recipes, for a test that has to finish quickly.

    Enumerating the joint of event times over a map with states costs seconds
    rather than milliseconds, so a test that runs `by_integrating` takes the first
    few of each recipe rather than the whole set. The recipes are seeded, so
    "the first few" is the same few on every machine and in every run.

    Args:
        how_many: How many maps to take from each recipe.

    Returns:
        Each map with a name saying which recipe it came from.
    """
    out: list[tuple[str, Map]] = []
    out += adversarial_events()[:how_many]
    for name, with_states, all_events in with_and_without_states()[:how_many]:
        out.append((name, with_states))
        out.append((f"{name}-as-events", all_events))
    out += hard_on_states()[:how_many]
    return out


def all_the_questions(names: Sequence[str]) -> list[tuple[str, dict, dict]]:
    """Every question worth asking of a map: no edit, then both verbs, both ways.

    Args:
        names: Every claim on the map.

    Returns:
        Each question as (what to call it, what is supposed, what was observed).
    """
    asked: list[tuple[str, dict, dict]] = [("no edit", {}, {})]
    for name in names:
        asked.append((f"suppose {name} true", {name: True}, {}))
        asked.append((f"suppose {name} false", {name: False}, {}))
        asked.append((f"{name} happened", {}, {name: True}))
        asked.append((f"{name} did not happen", {}, {name: False}))
    return asked


# --- What a map holds, for the test that checks the set is adversarial -----


def has_an_impulse(graph: Map) -> bool:
    """Say whether any arrow on this map carries a decaying spike."""
    return any(arrow.shape == "impulse" for claim in graph.values() for arrow in claim.causes)


def has_a_diamond(graph: Map) -> bool:
    """Say whether one claim reaches another both directly and round through a third."""
    for claim in graph.values():
        sources = [arrow.source for arrow in claim.causes]
        for source in sources:
            if any(other != source and _reaches(graph, source, other) for other in sources):
                return True
    return False


def has_a_state(graph: Map) -> bool:
    """Say whether any claim on this map is a state rather than an event."""
    return any(claim.persistence == STATE for claim in graph.values())


def has_a_sustain_arrow(graph: Map) -> bool:
    """Say whether any arrow reads its source's whole interval rather than its on day."""
    return any(arrow.mode == "sustain" for claim in graph.values() for arrow in claim.causes)


def _reaches(graph: Map, source: str, target: str) -> bool:
    """Say whether a chain of arrows runs from one claim to another."""
    seen: set[str] = set()
    walk = [source]
    while walk:
        here = walk.pop()
        if here == target:
            return True
        if here in seen:
            continue
        seen.add(here)
        walk += [
            name for name, claim in graph.items() if any(a.source == here for a in claim.causes)
        ]
    return False


# --- The two pieces of the recipes that are worth their own names ----------


def _which_causes(rng: np.random.Generator, deadlines: np.ndarray, place: int) -> list[int]:
    """Which earlier claims cause this one: up to three, each judged a day sooner."""
    if not place:
        return []
    earlier = [other for other in range(place) if deadlines[other] < deadlines[place] - 1.0]
    if not earlier:
        return []
    how_many = int(rng.integers(1, min(len(earlier), 3) + 1))
    return [int(one) for one in rng.choice(earlier, size=how_many, replace=False)]


def _within_the_oracles_reach(
    names: Sequence[str],
    drawn: dict[str, tuple[float, float, list[tuple[str, float, float, str, float]]]],
    wanted: set[str],
) -> set[str]:
    """Drop states until `by_integrating` can still enumerate the map.

    A state's variable has six hundred and twenty-five values where an event's has
    twenty-five, so a claim with three state causes is already hundreds of millions
    of entries. The cap is at most two state causes on an event and at most one on
    a state, which is the spike's own.
    """
    wanted = set(wanted)
    for _try in range(8):
        over = None
        for name in names:
            states = [source for source, *_rest in drawn[name][2] if source in wanted]
            cap = 1 if name in wanted else 2
            if len(states) > cap:
                over = states[-1]
                break
        if over is None:
            break
        wanted.discard(over)
    return wanted
