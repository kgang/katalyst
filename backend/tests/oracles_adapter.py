"""Turning one of the engine's maps into a map the time-enumerating oracle reads, and back.

**Why this lives here and not in `tests/oracles/`.** Nothing in that package imports
`katalyst`, on purpose: an oracle that could reach into the engine could not say it
judged the engine from outside. So the translation between the two dialects lives
beside the test that needs it.

There are two directions and they do different jobs.

* `a_map_the_oracle_reads` is the one the judging depends on. It takes a map the
  engine understands and writes down what the oracle must be told about it: each
  claim's deadline and its own chance, and for each arrow **the chance its target
  reaches its deadline with that one cause on** — which the engine's own bridge,
  `stated_chance_with`, works out from the push a person stated in log-odds.
* `a_graph_the_engine_reads` goes the other way, and exists only so that the
  seeded adversarial maps the oracle lane committed can be fed to the engine. The
  thing under test is always **the engine on a map, judged by the oracle on what
  this file says that same map is** — so nothing downstream ever compares against
  the generator's own map, and a lossy step here cannot flatter anybody.

The one place the two dialects really differ
--------------------------------------------
**A ramp means something different in each.** On an arrow, a ramp climbs from
nothing to full size across the arrow's **delay** and then holds, which is what
`link.py` says and what the engine computes. The oracle's ramp is nothing through
the delay and then climbs over the **half-life**. So a ramp is carried across as
*no delay, and a half-life equal to the arrow's delay*, which is the same curve
written in the other dialect. Every other shape carries across unchanged: a step
is nothing through the delay then full size held, and an impulse is nothing
through the delay then full size halving every half-life.

An impulse that does not say how fast it fades is a fault in a map, refused by the
map's own rules; where one arrives anyway the engine holds the push instead of
dividing by nothing, so it is carried across as a step, which is that same curve.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, timedelta

import numpy

from katalyst.domain import (
    Belief,
    Beliefs,
    Graph,
    Link,
    Persistence,
    Proposition,
    PropositionId,
    Resolution,
    stated_chance_with,
)
from tests.oracles.by_integrating import Arrow, Claim, Map

A_PLAIN_REASON = "The first claim changes the chance of the second, for a stated reason."
"""What every generated arrow says about itself. The maps are drawn, not argued."""

A_PLAIN_TEST = "A check two readers of it would agree on."
"""How every generated claim is settled. The maps are drawn, not argued."""


def a_map_the_oracle_reads(
    graph: Graph,
    day_zero: date,
    persistence: Mapping[PropositionId, Persistence] | None = None,
) -> Map:
    """Write down what the time-enumerating oracle has to be told about one of the engine's maps.

    Args:
        graph: The map, as the engine holds it.
        day_zero: The day the window starts on, from which every deadline is
            counted. This layer reads no clock.
        persistence: Which claims hold over a stretch of time and can stop. A claim
            not named is an event, which is what every claim on a map is until the
            flip puts the field on the claim itself.

    Returns:
        The same map in the oracle's dialect.
    """
    kinds = dict(persistence or {})
    claims = {one.id: one for one in graph.propositions}
    return {
        name: Claim(
            deadline=float(_days_to(one.resolution.by, day_zero)),
            own_chance=float(one.prior.p),
            causes=tuple(
                _one_arrow(arrow, float(claims[arrow.target].prior.p))
                for arrow in sorted(graph.links, key=lambda link: link.id)
                if arrow.target == name and not arrow.reflexive
            ),
            persistence=kinds.get(name, "event"),
        )
        for name, one in claims.items()
    }


def a_graph_the_engine_reads(
    name: str, oracle_map: Map, day_zero: date
) -> tuple[Graph, dict[PropositionId, Persistence]]:
    """Build one of the engine's maps from a map the oracle's own generator drew.

    Every stated range is a **point** — the same number at both ends — so a version
    of the map is the map itself and the engine's answer is the map's answer.
    Deadlines are whole days, because a claim is judged on a date.

    Args:
        name: What to call the map.
        oracle_map: The map as the generator drew it.
        day_zero: The day the window starts on.

    Returns:
        The map the engine reads, and which of its claims are states.
    """
    order = sorted(oracle_map)
    claims = tuple(
        Proposition(
            id=who,
            claim=f"The claim written down under the name {who}, on the map {name}.",
            kind="hypothesis" if who == order[0] else "event",
            resolution=Resolution(
                criteria=A_PLAIN_TEST,
                source="The publication that would carry it.",
                by=day_zero + timedelta(days=round(oracle_map[who].deadline)),
            ),
            prior=_a_point_at(oracle_map[who].own_chance),
            beliefs=Beliefs(model=_a_point_at(oracle_map[who].own_chance)),
        )
        for who in order
    )
    arrows = tuple(
        Link(
            id=f"{arrow.source}->{who}",
            source=arrow.source,
            target=who,
            mode="sustain" if arrow.mode == "sustain" else "trigger",
            strength=_the_push_behind(arrow.with_this_cause, oracle_map[who].own_chance),
            lag=float(arrow.lag),
            shape=arrow.shape,  # type: ignore[arg-type]
            half_life=float(arrow.half_life),
            rationale=A_PLAIN_REASON,
            provenance="argued",
            reflexive=False,
        )
        for who in order
        for arrow in oracle_map[who].causes
    )
    graph = Graph(id=name, propositions=claims, links=arrows, hypothesis_id=order[0])
    states: dict[PropositionId, Persistence] = {
        who: "state" for who in order if oracle_map[who].persistence == "state"
    }
    return graph, states


def _one_arrow(arrow: Link, own_chance_of_the_target: float) -> Arrow:
    """Write one of the engine's arrows down the way the oracle reads an arrow.

    Args:
        arrow: The arrow, as the engine holds it.
        own_chance_of_the_target: The chance the claim it points at reaches its
            deadline with no cause on. It is what the arrow's push is measured
            against.

    Returns:
        The same arrow in the oracle's dialect.
    """
    shape, lag, half_life = _the_same_curve(arrow)
    return Arrow(
        source=arrow.source,
        with_this_cause=float(
            stated_chance_with(
                numpy.array([own_chance_of_the_target]), numpy.array([float(arrow.strength)])
            )[0]
        ),
        lag=lag,
        shape=shape,
        half_life=half_life,
        mode=arrow.mode,
    )


def _the_same_curve(arrow: Link) -> tuple[str, float, float]:
    """Say one arrow's push in the oracle's dialect: its shape, its delay and its half-life.

    See this file's own opening: a ramp is the one shape whose two dialects disagree,
    and an impulse with no half-life is the one arrow a map should not hold.

    Args:
        arrow: The arrow, as the engine holds it.

    Returns:
        The shape, the delay and the half-life the oracle should be given.
    """
    fades = arrow.half_life
    if arrow.shape == "ramp":
        if arrow.lag <= 0.0:
            return "step", 0.0, 1.0
        return "ramp", 0.0, float(arrow.lag)
    if arrow.shape == "impulse" and (fades is None or fades <= 0.0):
        return "step", float(arrow.lag), 1.0
    return arrow.shape, float(arrow.lag), float(fades if fades is not None else 1.0)


def _a_point_at(chance: float) -> Belief:
    """One stated likelihood with no range at all: the same number at both ends."""
    return Belief(p=chance, lo=chance, hi=chance, owner="model")


def _the_push_behind(with_this_cause: float, own_chance: float) -> float:
    """Work back from a stated chance with one cause on to the push a person would have written.

    The engine's own bridge turns a push in log-odds into that chance; this is that
    bridge run backwards, so a map built here and handed back through
    `a_map_the_oracle_reads` says the number it started from.

    Args:
        with_this_cause: The chance the target reaches its deadline with this one
            cause on and no other.
        own_chance: The chance it reaches its deadline with no cause on.

    Returns:
        The push, in log-odds.
    """
    return _log_odds(with_this_cause) - _log_odds(own_chance)


def _log_odds(chance: float) -> float:
    """The logarithm of the ratio of a chance to its opposite."""
    return math.log(chance / (1.0 - chance))


def _days_to(when: date, day_zero: date) -> int:
    """How many whole days after day zero a date falls, never fewer than none."""
    return max(0, (when - day_zero).days)
