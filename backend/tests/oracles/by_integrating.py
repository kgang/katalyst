"""The second oracle: enumerate the whole joint of event times, from the arrows alone.

**Forbidden the engine's tables.** Nothing here reads anything the engine builds.
It is handed the map's arrows and nothing else — each cause's stated chance, its
delay, its shape, its half-life, which of the source's times it reads, and
whether each claim is an event or a state — and works out, from those, the full
joint over *when* every claim happened. That is what lets it catch an error in
how a table was built, which `by_summing` cannot see at all.

**The model, in five sentences.** A claim happens at some *rate* each day; with
none of the map's causes active that rate is the one constant that reaches the
claim's own stated chance by its deadline. Each cause that **helps** adds its own
rate on top, from the day it happened plus its delay, fading with its shape —
each cause an independent route, which is Kent's decision R18. Each cause that
**holds an event back** scales the whole rate down while it is on. A **state**
has two times, the day it switches on and the day it switches off: its on-rate is
bent by its helpers exactly as an event's is, and its off-rate starts at nothing
and is the sum of its ending causes, so a state nothing on the map can end does
not end. Which rate an arrow bends is decided by its sign — a stated chance above
the claim's own helps, one below it ends a state or holds an event back — and an
ending arrow's number is read as *the chance it stops*, which is closed form and
needs no root finding (record 0017, Kent's decision R26).

**A claim's number.** For an event, the chance it has happened by its deadline;
for a state, the chance it is still holding on its deadline.

**The one grid, said in one sentence.** This enumerator runs on **the same slices
as the engine and the same within-slice convention** — twenty-four slices of each
claim's **own** window, day zero to that claim's own resolve-by day, with an
arrival taken at the **middle** of its slice rather than its end and read off the
window of the claim that arrived — so a disagreement between the two is a
disagreement about the arithmetic and never about the grid. At twenty-four slices
the middle-day convention alone is the difference between a gap of `.0290` and one
of `.0027` against a fine reference, so running the two on different conventions
would swallow every tolerance in the stack whole.

**Why each claim's own window and not the map's.** Cut from the map's longest
deadline, every claim's grid moves when somebody inserts a claim judged far later,
including claims that insertion has no arrow to — which this repository has
already paid for once. Cut from a claim's own deadline, nothing else on the map
can move a boundary, and locality stops being a property somebody has to keep true.
The map's shared window is still reachable, as `Grid(cut=ONE_SHARED)`, because the
stack-05 spike's scratch judge used it and that comparison is kept runnable.

**What it costs.** An event is one variable with twenty-five values — the slice
it happened in, or *never*. A state is one variable with six hundred and
twenty-five — every pair of a switch-on slice and a switch-off slice. So this is
computable on maps of four claims or fewer with a couple of states, and on
nothing larger; that is why record 0016 says in as many words that its accuracy
is measured on four-claim maps only.

**Where it is lifted from.** `plans/analysis/scripts/spike-05/states/round2/`
`st2_core.py`, the function `exact_over_times` and everything it calls, kept
locally. That file reproduces the events-only additive judge of
`observe/round2/add_engine.py` to `4.4e-16` on maps with no state, so the two
halves are provably one engine. Two of its branches are gone rather than carried:
the alternative reading of an ending arrow's number, which decision R26 settled,
and the alternative rate for an arrow below a state's own number, which record
0017 settled. With both gone the bisection goes too.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

SLICES = 24
"""How many equal pieces a claim's window is cut into. The engine's number."""

POINTS_IN_A_SLICE = 8
"""Where inside each slice the rate is read. The engine's number."""


@dataclass(frozen=True)
class Arrow:
    """One arrow, exactly as a person stated it."""

    source: str
    """The claim this arrow comes from."""

    with_this_cause: float
    """The chance the target reaches its own question by its own deadline if this
    cause happens at the start of the window and no other cause on the map does.
    For an arrow that ends a state, the chance the state stops."""

    lag: float = 0.0
    """How many days pass before the push begins."""

    shape: str = "step"
    """`step` (it arrives and stays), `impulse` (it arrives and fades by halves)
    or `ramp` (it climbs to full size over the delay)."""

    half_life: float = 10.0
    """How many days an impulse takes to halve, or how long a ramp climbs for."""

    mode: str = "trigger"
    """Which of the source's times this arrow reads. `trigger` reads the day the
    source came on and keeps pushing afterwards — a domino. `sustain` reads the
    source's whole interval and is dead once the source stops holding — an apple
    on a desk."""


@dataclass(frozen=True)
class Claim:
    """One claim, with its deadline, its own chance and its causes."""

    deadline: float
    """The day it is judged, counting from day zero."""

    own_chance: float
    """The chance it comes true by that day with none of the map's causes active."""

    causes: tuple[Arrow, ...] = ()
    """The arrows pointing at it."""

    persistence: str = "event"
    """`event` — it happens once and stays happened — or `state`, which holds over
    a stretch of time and can stop."""


Map = dict[str, Claim]
"""A whole map: every claim by name."""


EACH_CLAIMS_OWN = "each claim's own window"
"""Every claim is cut from day zero to **its own** resolve-by day, and nothing else.

What the engine does, and the default here. A claim inserted with a deadline far
past everything else re-grids nothing it has no arrow to, so locality stops being
a property somebody has to keep true and becomes a shape of the arithmetic.
"""

ONE_SHARED = "one shared window"
"""Every claim is cut from day zero to the **map's** last resolve-by day.

What the stack-05 spike's scratch judge did, and what the committed comparison
against it was measured on. Kept as a named choice so that regression stays
runnable; nothing the engine is judged on uses it.
"""


@dataclass(frozen=True)
class Grid:
    """How finely the window is cut, and which window each claim is cut from."""

    days: float
    """The map's whole stretch, day zero to its latest resolve-by day.

    Read only when `cut` is `one shared window`. Under `each claim's own window` a
    claim's grid comes from its own deadline and this is carried for the record.
    """

    slices: int = SLICES
    """How many equal pieces a window is cut into."""

    points: int = POINTS_IN_A_SLICE
    """How many places inside each piece the rate is read at."""

    cut: str = EACH_CLAIMS_OWN
    """Which window each claim is cut from: `EACH_CLAIMS_OWN` or `ONE_SHARED`."""


Pinned = Mapping[str, bool | tuple[bool, int]]
"""Which claims are supposed true or false, and — where it is said — in which slice.

A plain `True` supposes the claim on from the very first slice, which is what
*Suppose this is true* with no date means.
"""


@dataclass(frozen=True)
class Prepared:
    """One map worked out as far as it can be before anybody edits it.

    A claim's factor says how its own times fall out for each combination of its
    causes' times, and **nothing anywhere else on the map can change it** — not a
    supposition, not a piece of news. So it is worked out once and every question
    asked of that map reuses it, which is what makes running every question over a
    whole set of maps affordable.
    """

    grid: Grid
    order: tuple[str, ...]
    """Every claim, causes before effects."""

    sizes: Mapping[str, int]
    """How many values each claim's time variable takes."""

    axes: Mapping[str, tuple[str, ...]]
    """Which axes each claim's factor is written over: its causes, then itself."""

    factor: Mapping[str, np.ndarray]
    """Each claim's own factor."""


def prepare(graph: Map, grid: Grid) -> Prepared:
    """Work out every claim's factor from the arrows alone, with nothing edited.

    Args:
        graph: The map: every claim, with its causes.
        grid: The window, how many slices it is cut into and how many points are
            read inside each.

    Returns:
        The map, ready for any question to be asked of it.
    """
    order = tuple(in_order(graph))
    axes: dict[str, tuple[str, ...]] = {}
    factor: dict[str, np.ndarray] = {}
    for name in order:
        claim = graph[name]
        causes = tuple(arrow.source for arrow in claim.causes)
        axes[name] = (*causes, name)
        factor[name] = _one_claims_block(
            claim,
            fit(claim, grid),
            [is_a_state(graph[who]) for who in causes],
            [graph[who].deadline for who in causes],
            grid,
        )
    return Prepared(
        grid=grid,
        order=order,
        sizes={name: _how_many_values(graph[name], grid) for name in order},
        axes=axes,
        factor=factor,
    )


def by_integrating(
    graph: Map,
    grid: Grid,
    *,
    supposed: Pinned | None = None,
    observed: Mapping[str, bool] | None = None,
    ready: Prepared | None = None,
) -> dict[str, float] | None:
    """Work out every claim's number by enumerating the whole joint of event times.

    Args:
        graph: The map: every claim, with its causes.
        grid: The window, how many slices it is cut into and how many points are
            read inside each.
        supposed: *Suppose this is true* — which claims are held to a value, and
            in which slice. A supposed claim's own factor is thrown away and a
            certainty put in its place, **which is what cuts the arrows into it**.
        observed: *This happened* — which claims are reported to have come out
            which way. Every factor stays where it is; only the worlds that
            disagree with the news go, and what is left is scaled back up.
        ready: The map already worked out by `prepare`, when one question of many
            is being asked of it. Left out, it is worked out here.

    Returns:
        One number per claim: for an event the chance it has happened by its
        deadline, for a state the chance it is still holding on it. None if what
        was reported cannot happen on this map at all.

    Raises:
        ValueError: If the map handed in was worked out at a different grid from
            the one asked for. Two grids in one answer is exactly the mistake
            record 0016 warns about — twenty-four slices judged by sixty with
            another within-slice convention differs by `.0290` on its own — so it
            is refused rather than quietly mixed.
    """
    if ready is None:
        ready = prepare(graph, grid)
    elif ready.grid != grid:
        raise ValueError(
            f"This map was worked out at {ready.grid} and the question asks for {grid}."
        )
    held = dict(supposed or {})
    written: list[tuple[tuple[str, ...], np.ndarray]] = []
    for name in ready.order:
        if name in held:
            value, at = _value_and_slice(held[name])
            certain = np.zeros(ready.sizes[name], dtype=np.float64)
            certain[_one_value(graph[name], value, at, grid)] = 1.0
            written.append(((name,), certain))
            continue
        written.append((ready.axes[name], ready.factor[name]))

    if observed:
        for name, value in observed.items():
            keep = np.zeros(ready.sizes[name], dtype=np.float64)
            true = _the_true_values(graph[name], grid)
            keep[true if value else ~true] = 1.0
            written.append(((name,), keep))

    answers: dict[str, float] = {}
    for name in ready.order:
        spread = _eliminate(written, name, ready.order, ready.sizes)
        if spread is None:
            return None
        answers[name] = _number_from(spread, graph[name], grid)
    return answers


def in_order(graph: Map) -> list[str]:
    """Every claim, causes before effects. Raises if the map runs round in circles."""
    seen: list[str] = []
    while len(seen) < len(graph):
        for name, claim in graph.items():
            if name in seen:
                continue
            if all(arrow.source in seen for arrow in claim.causes):
                seen.append(name)
                break
        else:
            raise ValueError("This map runs round in circles, so it has no causes-first order.")
    return seen


def is_a_state(claim: Claim) -> bool:
    """Say whether a claim is a state — something that holds and can stop."""
    return claim.persistence == "state"


def slice_edges(deadline: float, grid: Grid) -> np.ndarray:
    """Where one claim's slice boundaries fall, from day zero to the end of its window.

    Which day that window ends on is the grid's one named choice: under
    `EACH_CLAIMS_OWN` it is **this claim's own deadline**, so nothing else on the
    map can move a boundary; under `ONE_SHARED` it is the map's last resolve-by day,
    which is what the spike's scratch judge did.

    Args:
        deadline: This claim's own resolve-by day, counting from day zero.
        grid: How finely to cut, and which window to cut.

    Returns:
        `(slices + 1,)` the day each boundary falls on, the first being day zero.
    """
    ends_at = deadline if grid.cut == EACH_CLAIMS_OWN else grid.days
    return np.linspace(0.0, ends_at, grid.slices + 1)


def middle_days(deadline: float, grid: Grid) -> np.ndarray:
    """The day that stands for an arrival in each of one claim's slices: its **middle**.

    One entry per slice, then a last entry of infinity meaning *it never happened*.
    The middle rather than the last day is the convention record 0016 adopted, and
    the engine runs on the same one — **on the claim's own grid**, so a cause's
    arrival day is read off the cause's window and never off its effect's.

    Args:
        deadline: The claim's own resolve-by day, counting from day zero.
        grid: How finely to cut, and which window to cut.
    """
    edges = slice_edges(deadline, grid)
    return np.append(0.5 * (edges[:-1] + edges[1:]), np.inf)


def carried(kind: str, since: np.ndarray, half_life: float) -> np.ndarray:
    """How much of full strength an arrow carries, so many days after it switched on.

    Nothing before it switches on. A `step` arrives and stays. An `impulse`
    arrives and halves every half-life. A `ramp` climbs from nothing to full size
    over the delay and then holds.
    """
    on = since >= 0.0
    if kind == "step":
        return np.where(on, 1.0, 0.0)
    if kind == "impulse":
        return np.where(on, 0.5 ** (np.clip(since, 0.0, None) / max(half_life, 1e-9)), 0.0)
    if kind == "ramp":
        climb = np.clip(np.clip(since, 0.0, None) / max(half_life, 1e-9), 0.0, 1.0)
        return np.where(on, climb, 0.0)
    raise ValueError(f"No arrow has the shape {kind!r}.")


# --- Turning the stated chances into rates ---------------------------------


@dataclass(frozen=True)
class Fitted:
    """One claim's rates, worked out from what a person stated. No root finding."""

    leak: float
    """The rate with none of the map's causes active."""

    helps: Mapping[int, float]
    """Which cause adds how much to the on-rate, by its place in the claim's list."""

    leaves: Mapping[int, float]
    """What a cause that holds an **event** back leaves of the rate, between 0 and 1."""

    ends: Mapping[int, float]
    """What a cause that ends a **state** adds to its off-rate."""

    saturated: int
    """How many holding-back causes could not hold the claim back as far as stated."""


def fit(claim: Claim, grid: Grid) -> Fitted:
    """Turn one claim's stated chances into rates — closed form, every shape.

    Three formulas, one per kind of arrow, where *area* is the arrow's shape added
    up over the claim's window with its cause firing on day zero:

    * a cause that **helps**: `rate x area = ln(1 - own) - ln(1 - with this cause)`
    * a cause that **holds an event back**: `leak x (window - (1 - leaves) x area)
      = -ln(1 - with this cause)`
    * a cause that **ends a state**: `rate x area = -ln(1 - it stops)`, where *it
      stops* is `1 - with this cause / own`

    The sign of the arrow picks which of the three it is: a stated chance at or
    above the claim's own helps, and one below it ends a state or holds an event
    back.
    """
    width, _points = _window_of(claim.deadline, grid)
    whole = float(width.sum())
    leak = -math.log1p(-claim.own_chance) / claim.deadline
    areas = _areas(claim, grid)

    helps: dict[int, float] = {}
    leaves: dict[int, float] = {}
    ends: dict[int, float] = {}
    saturated = 0
    for index, arrow in enumerate(claim.causes):
        area = max(areas[index], 1e-12)
        if arrow.with_this_cause >= claim.own_chance:
            gain = math.log1p(-claim.own_chance) - math.log1p(-arrow.with_this_cause)
            helps[index] = max(gain / area, 0.0)
        elif is_a_state(claim):
            stops = 1.0 - arrow.with_this_cause / max(claim.own_chance, 1e-12)
            stops = float(np.clip(stops, 0.0, 1.0 - 1e-12))
            ends[index] = -math.log1p(-stops) / area
        else:
            gap = (whole + math.log1p(-arrow.with_this_cause) / max(leak, 1e-12)) / area
            if gap > 1.0:
                saturated += 1
            leaves[index] = float(np.clip(1.0 - gap, 0.0, 1.0))
    return Fitted(leak=leak, helps=helps, leaves=leaves, ends=ends, saturated=saturated)


def _areas(claim: Claim, grid: Grid) -> list[float]:
    """Each arrow's shape added up over the claim's window, its cause firing on day zero."""
    width, points = _window_of(claim.deadline, grid)
    out = []
    for arrow in claim.causes:
        at_zero = carried(arrow.shape, points - arrow.lag, arrow.half_life)
        out.append(float((width * at_zero.mean(axis=1)).sum()))
    return out


def _window_of(deadline: float, grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    """This claim's own window: days in each slice, and the days the rate is read at.

    Under `EACH_CLAIMS_OWN` the boundaries run from day zero to this claim's
    deadline, so every slice is the same width and the last one ends exactly on the
    day the claim is judged — nothing is ever counted past it and the clipping below
    does nothing. Under `ONE_SHARED` the boundaries are the map's, and a claim
    judged early has its last slices clipped to nothing.
    """
    edges = slice_edges(deadline, grid)
    low, high = edges[:-1], np.minimum(edges[1:], deadline)
    width = np.clip(high - low, 0.0, None)
    inside = (np.arange(grid.points)[None, :] + 0.5) * (width[:, None] / grid.points)
    return width, low[:, None] + inside


# --- The rates, added up ---------------------------------------------------


def _push(arrow: Arrow, on: float, off: float, points: np.ndarray) -> np.ndarray:
    """How much of full strength one arrow carries at each point the rate is read at.

    `on` and `off` are the **source's** own times. A `sustain` arrow is dead once
    the source stops holding; a `trigger` arrow keeps pushing.
    """
    strength = carried(arrow.shape, points - (on + arrow.lag), arrow.half_life)
    if arrow.mode == "sustain":
        return np.where(points < off, strength, 0.0)
    return strength


def _on_rate(claim: Claim, f: Fitted, on, off, grid: Grid) -> np.ndarray:
    """The rate of switching on, added up over each slice.

    The helpers **add**, each an independent route; anything holding the claim
    back **scales** the whole rate down while it is on. A state has nothing
    holding it back on this side, because the sign sends those to the off-rate.
    """
    width, points = _window_of(claim.deadline, grid)
    added = np.zeros_like(points)
    for index, rate in f.helps.items():
        if not np.isfinite(on[index]):
            continue
        added = added + rate * _push(claim.causes[index], on[index], off[index], points)
    left = np.ones_like(points)
    for index, share in f.leaves.items():
        if not np.isfinite(on[index]):
            continue
        held = _push(claim.causes[index], on[index], off[index], points)
        left = left * (1.0 - (1.0 - share) * held)
    return (left * (f.leak + added)).mean(axis=1) * width


def _when_it_came_on(claim: Claim, f: Fitted, on, off, grid: Grid) -> np.ndarray:
    """The chance it switched on in each slice, then the chance it never did."""
    added = _on_rate(claim, f, on, off, grid)
    still = np.exp(-np.concatenate([[0.0], np.cumsum(added)]))
    return np.append(still[:-1] - still[1:], still[-1])


def _off_rate(claim: Claim, f: Fitted, on, off, from_day: float, grid: Grid) -> np.ndarray:
    """The rate of stopping, added up over each slice, accruing only once it is on.

    From a base of nothing: each ending cause is its own independent way for the
    state to stop, and the ways add. Nothing on the map that can end it means it
    does not end.
    """
    width, points = _window_of(claim.deadline, grid)
    rate = np.zeros_like(points)
    for index, added in f.ends.items():
        if not np.isfinite(on[index]):
            continue
        rate = rate + added * _push(claim.causes[index], on[index], off[index], points)
    return np.where(points >= from_day, rate, 0.0).mean(axis=1) * width


def _when_it_stopped(claim: Claim, f: Fitted, on, off, from_day: float, grid: Grid) -> np.ndarray:
    """The chance it stopped in each slice given it came on, then still holding."""
    added = _off_rate(claim, f, on, off, from_day, grid)
    still = np.exp(-np.concatenate([[0.0], np.cumsum(added)]))
    return np.append(still[:-1] - still[1:], still[-1])


def own_times(claim: Claim, f: Fitted, on, off, grid: Grid) -> np.ndarray:
    """One claim's own times, given every cause's.

    For an event, the chance it happened in each slice and then the chance it
    never did. For a state, the same over every pair of a switch-on slice and a
    switch-off slice, flattened row by row, where a last switch-off slot means
    *still holding* and a last switch-on slot means *never came on*.
    """
    came_on = _when_it_came_on(claim, f, on, off, grid)
    if not is_a_state(claim):
        return came_on
    last = grid.slices
    # The state's OWN grid: the day it came on is the middle of one of its own
    # slices, and that is the day its stopping rate starts accruing from.
    days = middle_days(claim.deadline, grid)
    pairs = np.zeros((last + 1, last + 1))
    endable = bool(f.ends) and any(np.isfinite(on[index]) for index in f.ends)
    for slot in range(last):
        if came_on[slot] < 1e-16:
            continue
        if endable:
            pairs[slot, :] = came_on[slot] * _when_it_stopped(
                claim, f, on, off, float(days[slot]), grid
            )
        else:
            pairs[slot, last] = came_on[slot]
    pairs[last, last] = came_on[last]
    return pairs.reshape(-1)


# --- One claim's whole factor ----------------------------------------------


def _how_many_values(claim: Claim, grid: Grid) -> int:
    """How many values a claim's time variable takes: a slice, or a pair of them."""
    return (grid.slices + 1) ** 2 if is_a_state(claim) else grid.slices + 1


def _times_of(value: int, deadline: float, from_a_state: bool, grid: Grid) -> tuple[float, float]:
    """Read one value of a cause's time variable back as a switch-on and switch-off day.

    **Read off the cause's own grid, never its effect's.** A cause arriving in its
    third slice arrived on the middle day of the third slice of the window cut to
    *that cause's* deadline, and the effect it pushes may be judged much later.

    Args:
        value: One value of the cause's time variable.
        deadline: The **cause's** own resolve-by day, counting from day zero.
        from_a_state: Whether the cause is a state, and so carries two times.
        grid: How finely to cut, and which window to cut.
    """
    days = middle_days(deadline, grid)
    if not from_a_state:
        return float(days[value]), float(np.inf)
    on, off = divmod(value, grid.slices + 1)
    return float(days[on]), (float(days[off]) if off < grid.slices else float(np.inf))


def _one_claims_block(
    claim: Claim,
    f: Fitted,
    causes_are_states: Sequence[bool],
    cause_deadlines: Sequence[float],
    grid: Grid,
) -> np.ndarray:
    """One claim's times for every combination of its causes' times.

    Each cause's arrival day is read off **that cause's** own window, which is why
    its deadline has to be handed in alongside whether it is a state.
    """
    mine = _how_many_values(claim, grid)
    theirs = [
        (grid.slices + 1) ** 2 if a_state else grid.slices + 1 for a_state in causes_are_states
    ]
    if not theirs:
        return own_times(claim, f, [], [], grid)
    block = np.zeros((*theirs, mine))
    for combination in itertools.product(*[range(size) for size in theirs]):
        on, off = [], []
        for place, value in enumerate(combination):
            came_on, went_off = _times_of(
                value, cause_deadlines[place], causes_are_states[place], grid
            )
            on.append(came_on)
            off.append(went_off)
        block[combination] = own_times(claim, f, on, off, grid)
    return block


def _value_and_slice(held: bool | tuple[bool, int]) -> tuple[bool, int]:
    """Read a supposition as a value and the slice it is supposed from."""
    return (held, 0) if isinstance(held, bool) else held


def _one_value(claim: Claim, value: bool, at: int, grid: Grid) -> int:
    """Which single value of a claim's time variable a supposition holds it to.

    Supposed true, an event happened in the slice it was supposed at, and a state
    came on then and never went off. Supposed false, neither ever came on.
    """
    last = grid.slices
    if not is_a_state(claim):
        return at if value else last
    return at * (last + 1) + last if value else last * (last + 1) + last


def _the_true_values(claim: Claim, grid: Grid) -> np.ndarray:
    """Which values of a claim's time variable count as the claim being true.

    An event is true if it happened in any slice. A state is true if it came on in
    some slice and is still holding — which is what its tile's sentence asks.
    """
    last = grid.slices
    if not is_a_state(claim):
        true = np.zeros(last + 1, dtype=bool)
        true[:last] = True
        return true
    pairs = np.zeros((last + 1, last + 1), dtype=bool)
    pairs[:last, last] = True
    return pairs.reshape(-1)


def _number_from(spread: np.ndarray, claim: Claim, grid: Grid) -> float:
    """One claim's number, read off its whole spread over times."""
    last = grid.slices
    if not is_a_state(claim):
        return float(1.0 - spread[last])
    return float(spread.reshape(last + 1, last + 1)[:last, last].sum())


# --- Adding the joint up, one claim at a time ------------------------------


def _eliminate(
    factors: Sequence[tuple[tuple[str, ...], np.ndarray]],
    target: str,
    names: Sequence[str],
    sizes: Mapping[str, int],
) -> np.ndarray | None:
    """Sum every claim but one out of the joint, and scale what is left to add to one.

    The joint over times is far too large to hold whole — four claims at
    twenty-four slices with two states is already hundreds of millions of entries
    — so it is never built. Each claim in turn is summed out of the factors that
    mention it, which is the textbook method and gives the same answer as building
    the whole thing would.
    """
    live = [(list(axes), table.copy()) for axes, table in factors]
    for name in names:
        if name == target:
            continue
        touching = [one for one in live if name in one[0]]
        live = [one for one in live if name not in one[0]]
        if not touching:
            continue
        over: list[str] = []
        for axes, _table in touching:
            for axis in axes:
                if axis not in over:
                    over.append(axis)
        together = np.ones(tuple(sizes[axis] for axis in over))
        for axes, table in touching:
            where = [over.index(axis) for axis in axes]
            wide = table.reshape(table.shape + (1,) * (len(over) - len(axes)))
            together = together * np.moveaxis(wide, range(len(axes)), where)
        together = together.sum(axis=over.index(name))
        live.append(([axis for axis in over if axis != name], together))

    answer = np.ones(sizes[target])
    for axes, table in live:
        if axes == [target]:
            answer = answer * table
        elif not axes:
            answer = answer * float(table)
        else:
            raise AssertionError(f"An axis was left over after eliminating: {axes}.")
    total = answer.sum()
    return None if total <= 0 else answer / total
