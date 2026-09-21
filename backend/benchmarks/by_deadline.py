"""Time the by-deadline engine on a map built to be hard, and print what each stage cost.

**Recorded, never gated.** No test fails because this printed a big number. A
wall-clock timing on a shared machine is a band and not a value, so what this is
for is a line in `docs/measurements.md` that says what was measured, on what, and
when — and that names the cell nobody has measured rather than leaving it out.

Run it, from `backend/`:

    uv run python benchmarks/by_deadline.py
    uv run python benchmarks/by_deadline.py --claims 20 --states 5 --repeats 5

The hard map, which is the default
----------------------------------
Twenty claims, up to three causes each, five of them states with a `sustain` arrow
leaving each, and three arrows that hold their claim back — the one place the work
still multiplies out. Two thousand versions, twenty-four slices.

**The target this is read against** is thirty milliseconds a claim at two thousand
versions: decision record 0016's limit, which is a target proportional to the map
rather than a fixed ceiling. It is a stated target, not a measurement.

**Stubs.** The measuring itself raises until the engine behind it is written. The
arguments and the shape of what is printed are settled here, so that the person who
finishes the engine changes one function and nothing about how this is run or read.
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

MILLISECONDS_A_CLAIM = 30.0
"""The target one world is read against, per claim on the map, at two thousand versions.

Decision record 0016, which replaced a fixed six hundred milliseconds with a target
that grows with the map. A target somebody chose, never something measured.
"""


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
    )


def measure(settings: Settings) -> tuple[Stage, ...]:
    """Build the map, run one world, and time each stage of it.

    **Not written yet.** It raises until the by-deadline engine behind it exists.

    Args:
        settings: What to build and how many times to time it.

    Returns:
        One entry per named stage, each carrying one reading per repeat.
    """
    raise NotImplementedError


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
    lines = [
        (
            f"{settings.claims} claims, up to {settings.causes} causes each, "
            f"{settings.states} of them states, {settings.holding_back} arrows holding a "
            f"claim back, {settings.versions} versions, {settings.slices} slices, "
            f"seed {settings.seed}, {settings.repeats} repeats."
        ),
        "",
        f"{'stage':<24}{'fastest':>12}{'slowest':>12}",
    ]
    total_fastest = 0.0
    total_slowest = 0.0
    for stage in stages:
        fastest = min(stage.milliseconds)
        slowest = max(stage.milliseconds)
        total_fastest += fastest
        total_slowest += slowest
        lines.append(f"{stage.name:<24}{fastest:>10.1f} ms{slowest:>10.1f} ms")
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
