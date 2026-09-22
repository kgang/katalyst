"""Time the by-deadline engine on a map built to be hard, and print what each stage cost.

**Recorded, never gated.** No test fails because this printed a big number. A
wall-clock timing on a shared machine is a band and not a value, so what this is
for is a line in `docs/measurements.md` that says what was measured, on what, and
when — and that names the cell nobody has measured rather than leaving it out.

Run it, from `backend/`:

    uv run python benchmarks/by_deadline.py
    uv run python benchmarks/by_deadline.py --claims 20 --states 5 --repeats 5
    uv run python benchmarks/by_deadline.py --example hormuz --versions 2000

The hard map, which is the default
----------------------------------
Twenty claims, up to three causes each, five of them states with a `sustain` arrow
leaving each, and three arrows that hold their claim back — the one place the work
still multiplies out. Two thousand versions, twenty-four slices.

**The three arrows that hold a claim back sit on three different claims**, which is
the arrangement decision record 0016 measured. Two of them on one claim is a
different and much more expensive map: the work multiplies out over every
combination of their arrival slices, so two cost twenty-five times one rather than
twice it. The committed worked example has exactly that shape once its strike
branch is folded on, and `docs/measurements.md` says what it costs.

**What each clock covers.** *The forward pass* is working out when every claim
happens, one pass over the whole map, causes before effects — rates, shapes and all
— at every version. *The exact solve* is one elimination per claim over the yes/no
tables that pass leaves, at every version. *The weighted sample* is drawing worlds
forward at one version with one claim reported to have happened, and the correction
it hands back. The three are timed on the same map and the same numbers, and *the
whole world* is their sum. Nothing here times the drawing of the versions, which
both engines share.

**The target this is read against** is thirty milliseconds a claim at two thousand
versions: decision record 0016's limit, which is a target proportional to the map
rather than a fixed ceiling. It is a stated target, not a measurement.
"""

import argparse
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import numpy

from katalyst.domain import (
    Belief,
    Beliefs,
    Drawn,
    Graph,
    Link,
    Persistence,
    Pin,
    Proposition,
    PropositionId,
    Resolution,
    forward_pass,
    propagate,
    sample_forward,
    solve,
    stated_chance_with,
    window_of,
)
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ

MILLISECONDS_A_CLAIM = 30.0
"""The target one world is read against, per claim on the map, at two thousand versions.

Decision record 0016, which replaced a fixed six hundred milliseconds with a target
that grows with the map. A target somebody chose, never something measured.
"""

DAY_ZERO = date(2026, 1, 1)
"""The day the generated map's window starts on. This layer reads no clock."""

WINDOW = 60
"""How many days the generated map's window runs for, as every spike measurement ran at."""


@dataclass(frozen=True)
class Settings:
    """What to build and how many times to time it."""

    claims: int
    """How many claims the generated map has."""

    causes: int
    """The most arrows into any one claim."""

    states: int
    """How many of the claims hold over a stretch of time and can stop."""

    holding_back: int
    """How many arrows are stated below their claim's own chance on an event.

    These are the one place the work still multiplies out over arrival days, so the
    count is an argument rather than a constant.
    """

    versions: int
    """How many versions of the map to work through: how sure we are of the numbers put in."""

    slices: int
    """How many equal pieces each claim's window is cut into."""

    seed: int
    """The one number the generated map and every draw come from."""

    repeats: int
    """How many times to time the same work. The spread across repeats is printed, not hidden."""

    example: str | None = None
    """The name of a committed example to time instead of a generated map, or nothing at all."""


@dataclass(frozen=True)
class Stage:
    """One named piece of the work, and what it cost across the repeats."""

    name: str
    """What was timed: `the forward pass`, `the exact solve`, `the weighted sample`."""

    milliseconds: tuple[float, ...]
    """One reading per repeat, in the order they were taken."""


def parse(argv: Sequence[str] | None = None) -> Settings:
    """Read the command line.

    Args:
        argv: The arguments, or nothing at all to read the real command line.

    Returns:
        What to build and how many times to time it.
    """
    parser = argparse.ArgumentParser(
        prog="by_deadline",
        description=(
            "Time the by-deadline engine on a generated map and print what each stage "
            "cost. Recorded, never gated: nothing here fails a build."
        ),
    )
    parser.add_argument("--claims", type=int, default=20, help="how many claims the map has")
    parser.add_argument("--causes", type=int, default=3, help="the most arrows into one claim")
    parser.add_argument("--states", type=int, default=5, help="how many claims are states")
    parser.add_argument(
        "--holding-back",
        type=int,
        default=3,
        help="how many arrows hold their claim back, the one place the work multiplies out",
    )
    parser.add_argument("--versions", type=int, default=2_000, help="how many versions to run")
    parser.add_argument(
        "--slices", type=int, default=24, help="how many slices a window is cut into"
    )
    parser.add_argument("--seed", type=int, default=7, help="the one number every draw comes from")
    parser.add_argument("--repeats", type=int, default=3, help="how many times to time the work")
    parser.add_argument(
        "--example",
        default=None,
        help="time a committed example end to end instead of a generated map: hormuz",
    )
    read = parser.parse_args(argv)
    return Settings(
        claims=read.claims,
        causes=read.causes,
        states=read.states,
        holding_back=read.holding_back,
        versions=read.versions,
        slices=read.slices,
        seed=read.seed,
        repeats=read.repeats,
        example=read.example,
    )


def measure(settings: Settings) -> tuple[Stage, ...]:
    """Build the map, run one world, and time each stage of it.

    Args:
        settings: What to build and how many times to time it.

    Returns:
        One entry per named stage, each carrying one reading per repeat.
    """
    if settings.example is not None:
        return _timed_example(settings)
    return _timed_stages(settings)


def _timed_example(settings: Settings) -> tuple[Stage, ...]:
    """Time one committed example the whole way through, as a request would ask for it.

    Args:
        settings: What to time, and how many times.

    Returns:
        One stage, the whole world, with one reading per repeat.

    Raises:
        ValueError: If no example is stored under the name given.
    """
    if settings.example != "hormuz":
        raise ValueError(f"there is no committed example called {settings.example!r}")
    return (
        Stage(
            name="the whole world",
            milliseconds=_clocked(
                lambda: propagate(
                    HORMUZ,
                    (),
                    as_of=FIXTURE_DATE,
                    seed=settings.seed,
                    versions=settings.versions,
                    engine="by_deadline",
                    slices=settings.slices,
                ),
                settings.repeats,
            ),
        ),
    )


def _timed_stages(settings: Settings) -> tuple[Stage, ...]:
    """Time the forward pass, the exact solve and the weighted sample on a generated map.

    Args:
        settings: What to build, and how many times to time it.

    Returns:
        One entry per stage, each with one reading per repeat.
    """
    graph, persistence = _a_hard_map(settings)
    window = window_of(graph, DAY_ZERO, slices=settings.slices)
    drawn = _drawn_for(graph, settings.versions)
    reported = {_reported_claim(graph): Pin(value=True, kind="observe")}

    forward = forward_pass(graph, window, drawn, persistence=persistence)
    exact = solve(forward, reported)
    return (
        Stage(
            name="the forward pass",
            milliseconds=_clocked(
                lambda: forward_pass(graph, window, drawn, persistence=persistence),
                settings.repeats,
            ),
        ),
        Stage(
            name="the exact solve",
            milliseconds=_clocked(lambda: solve(forward, reported), settings.repeats),
        ),
        Stage(
            name="the weighted sample",
            milliseconds=_clocked(
                lambda: sample_forward(
                    forward,
                    reported,
                    window=window,
                    version=0,
                    seed=settings.seed,
                    exact=exact,
                ),
                settings.repeats,
            ),
        ),
    )


def _clocked(work: Callable[[], object], repeats: int) -> tuple[float, ...]:
    """Run one piece of work over and over and say how many milliseconds each run took."""
    taken: list[float] = []
    for _again in range(repeats):
        started = time.perf_counter()
        work()
        taken.append((time.perf_counter() - started) * 1_000.0)
    return tuple(taken)


def _reported_claim(graph: Graph) -> PropositionId:
    """Pick the claim the sample is told happened: the one in the middle of the map.

    The middle rather than an end, because a claim at the top has nothing above it
    for the news to reach and a claim at the bottom has nothing below it.
    """
    return graph.propositions[len(graph.propositions) // 2].id


def _a_hard_map(settings: Settings) -> tuple[Graph, dict[PropositionId, Persistence]]:
    """Generate the map decision record 0016 timed: many claims, some states, some held back.

    Every number is drawn from the seed and from nothing else, so two runs on two
    machines build the same map. Deadlines are spread evenly across the window and
    a claim's causes are drawn from the claims judged before it, so the map has an
    order and no loop.

    **The arrows that hold a claim back go on different claims**, one each, because
    two of them on one claim is a different map: the work multiplies out over every
    combination of their arrival slices.

    Args:
        settings: How many claims, causes, states and holding-back arrows to build.

    Returns:
        The map, and which of its claims hold over a stretch of time.
    """
    drawing = numpy.random.default_rng(settings.seed)
    names = [f"c{index:02d}" for index in range(settings.claims)]
    judged = {
        name: 4 + round(index * (WINDOW - 4) / max(settings.claims - 1, 1))
        for index, name in enumerate(names)
    }
    states = {name: "state" for name in names[1 : 1 + settings.states]}

    claims: list[Proposition] = []
    arrows: list[Link] = []
    held_back_on = set(names[-settings.holding_back :]) if settings.holding_back else set()
    for index, name in enumerate(names):
        own = float(drawing.uniform(0.15, 0.55))
        claims.append(_a_claim(name, own, judged[name], index))
        earlier = [one for one in names[:index] if judged[one] < judged[name]]
        if not earlier:
            continue
        how_many = min(len(earlier), int(drawing.integers(1, settings.causes + 1)))
        for source in drawing.choice(earlier, size=how_many, replace=False):
            source = str(source)
            holds_back = name in held_back_on and not arrows_into(arrows, name)
            arrows.append(
                _an_arrow(
                    source,
                    name,
                    drawing,
                    holds_back=holds_back,
                    from_a_state=source in states,
                )
            )
    graph = Graph(
        id="a generated map built to be hard",
        propositions=tuple(claims),
        links=tuple(arrows),
        hypothesis_id=names[0],
    )
    return graph, dict(states)  # type: ignore[arg-type]


def arrows_into(arrows: Sequence[Link], target: PropositionId) -> list[Link]:
    """List the arrows already pointing at one claim, so the second one is not held back too."""
    return [one for one in arrows if one.target == target]


def _a_claim(name: str, own: float, judged: int, index: int) -> Proposition:
    """One generated claim, with a stated range half as wide again above as below."""
    stated = Belief(
        p=own,
        lo=max(0.01, own - 0.10),
        hi=min(0.99, own + 0.15),
        owner="model",
    )
    kind: Literal["hypothesis", "event"] = "hypothesis" if index == 0 else "event"
    return Proposition(
        id=name,
        claim=f"The claim written down under the name {name}.",
        kind=kind,
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=judged),
        ),
        prior=stated,
        beliefs=Beliefs(model=stated),
        payoff=None,
    )


def _an_arrow(
    source: str,
    target: str,
    drawing: numpy.random.Generator,
    *,
    holds_back: bool,
    from_a_state: bool,
) -> Link:
    """One generated arrow: how hard it pushes, how long it takes, and what it reads.

    An arrow out of a state is a `sustain` arrow, which reads its source's whole
    stretch and is the one kind that costs the on-and-off joint. Every other arrow is a
    `trigger`, which reads only the day its source came on.

    Args:
        source: The claim the arrow comes from.
        target: The claim it points at.
        drawing: Where every number comes from.
        holds_back: Whether this arrow is stated below its target's own chance.
        from_a_state: Whether its source holds over a stretch of time.

    Returns:
        The arrow.
    """
    shape = str(drawing.choice(["step", "step", "impulse", "ramp"]))
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="sustain" if from_a_state else "trigger",
        strength=float(drawing.uniform(-2.5, -1.0) if holds_back else drawing.uniform(0.4, 2.0)),
        lag=float(drawing.uniform(0.0, 5.0)),
        shape=shape,  # type: ignore[arg-type]
        half_life=float(drawing.uniform(2.0, 15.0)),
        rationale="The first claim changes the chance of the second, for a stated reason.",
        provenance="argued",
        reflexive=False,
    )


def _drawn_for(graph: Graph, versions: int) -> Drawn:
    """Draw every stated number once per version, the way the engine's own assembly does.

    Written here rather than reached into the engine for, because the engine's
    drawing is behind a private name and a benchmark that reaches past a boundary
    stops measuring the thing the boundary describes. The draw is a plain even
    spread across each stated range, which is enough to make the arrays the right
    size and the right shape; how a range is fitted is measured elsewhere.

    Args:
        graph: The map.
        versions: How many versions to draw.

    Returns:
        One draw per version of every number the map states.
    """
    spread = numpy.linspace(0.15, 0.85, versions)
    own = {
        one.id: numpy.clip(one.prior.lo + spread * (one.prior.hi - one.prior.lo), 1e-6, 1.0 - 1e-6)
        for one in graph.propositions
    }
    return Drawn(
        versions=versions,
        own_chance=own,
        with_this_cause={
            arrow.id: stated_chance_with(
                own[arrow.target], numpy.full(versions, float(arrow.strength))
            )
            for arrow in graph.links
        },
    )


def report(settings: Settings, stages: Sequence[Stage]) -> str:
    """Write what was measured, on what, and how it reads against the target.

    Every line says both of its conditions out loud — how many claims, how many of
    them states, how many arrows hold a claim back, how many versions, how many
    slices — because a timing quoted without them is a number nobody can check.

    Args:
        settings: What was built.
        stages: What each stage cost, one reading per repeat.

    Returns:
        The whole report, ready to print and to paste into `docs/measurements.md`.
    """
    target = MILLISECONDS_A_CLAIM * settings.claims
    if settings.example is not None:
        opening = (
            f"The committed example '{settings.example}', end to end through "
            f'`propagate(engine="by_deadline")`, at {settings.versions} versions, '
            f"{settings.slices} slices, seed {settings.seed}, {settings.repeats} repeats."
        )
    else:
        opening = (
            f"{settings.claims} claims, up to {settings.causes} causes each, "
            f"{settings.states} of them states, {settings.holding_back} arrows holding a "
            f"claim back on {settings.holding_back} different claims, {settings.versions} "
            f"versions, {settings.slices} slices, seed {settings.seed}, "
            f"{settings.repeats} repeats, one claim reported to have happened."
        )
    lines = [opening, "", f"{'stage':<24}{'fastest':>12}{'slowest':>12}"]
    total_fastest = 0.0
    total_slowest = 0.0
    for stage in stages:
        fastest = min(stage.milliseconds)
        slowest = max(stage.milliseconds)
        total_fastest += fastest
        total_slowest += slowest
        lines.append(f"{stage.name:<24}{fastest:>10.1f} ms{slowest:>10.1f} ms")
    if len(stages) > 1:
        lines.append(f"{'the whole world':<24}{total_fastest:>10.1f} ms{total_slowest:>10.1f} ms")
    lines += [
        "",
        (
            f"The target is {MILLISECONDS_A_CLAIM:.0f} ms a claim at 2 000 versions, so "
            f"{target:.0f} ms for this map. It is a target somebody chose, and nothing "
            f"here fails because a reading is above it."
        ),
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Read the command line, time the work, and print the report.

    Args:
        argv: The arguments, or nothing at all to read the real command line.
    """
    settings = parse(argv)
    print(report(settings, measure(settings)))


if __name__ == "__main__":
    main()
