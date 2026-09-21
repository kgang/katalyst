"""The Verify door: a graded route to the place a person asked about, or none.

A person can ask *does this get me there?* The only two honest answers are a
route, graded, and a plain statement that there is no route. Making one up is the
state this product exists to refuse, and there is no code path here that could:
this file reads a finished map and never builds an arrow.

**The route is chosen by the map's own rule, not by one of ours.**
`katalyst.domain` holds one way of choosing a route — over every route, the one
whose weakest arrow is strongest — and the change list's ranking, the Inspector's
path bar and this door all read it. One rule, three readers, so nobody can be
shown two different "best" routes for the same map.

This file reads the map's own types and nothing else of ours. It needs no
answerer, no receipt and no walk: it is asked once, after the numbers have been
worked through, and it only looks.

What this file must never do
----------------------------
- Never add an arrow, a claim or a route so that an answer exists.
- Never invent a nearness it cannot compute. Where "closest" has no meaning on a
  map, it says how far the story got instead, and the sentence says which of the
  two it is.
- Never multiply out a likelihood that has not been worked through the map. An
  absent number is honest; a made-up one is not.
"""

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Belief, Graph, PropositionId
from katalyst.domain.diff import Route, best_backed_routes


class Verdict(BaseModel):
    """Whether the story reached the place the person asked about.

    One of two answers, and never a third.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["reached", "no_path"] = Field(
        description="Whether a route from the starting claim to the destination exists."
    )
    path: tuple[PropositionId, ...] = Field(
        default=(), description="The route, claim by claim. Empty when there is none."
    )
    product: float | None = Field(
        default=None,
        description=(
            "The likelihoods along that route multiplied together. Nothing at all "
            "until the numbers have been worked through the map."
        ),
    )
    nearest: PropositionId | None = Field(
        default=None,
        description=(
            "When there is no route: the claim the story did reach that sits "
            "closest to the destination, or — when nothing on the map touches the "
            "destination at all — the furthest the story got. The sentence beside "
            "it says which of the two it is."
        ),
    )
    why: str = Field(description="The answer in one plain sentence, for a person to read.")


def verdict(
    graph: Graph,
    destination: PropositionId,
    *,
    beliefs: Mapping[PropositionId, Belief] | None = None,
) -> Verdict:
    """Grade the route from the claim the map started at to the destination.

    The route shown is the **best-backed** one: over every route, the one whose
    weakest arrow is strongest, by the map's own rule.

    An honest caveat belongs beside the multiplied-out number wherever it is
    shown: it multiplies likelihoods each read on a different day, so it is not a
    joint probability.

    Args:
        graph: The finished map.
        destination: The claim the person asked whether the story reaches.
        beliefs: The worked-through likelihood of every claim, when the numbers
            have been run. Without them the route is still graded structurally and
            the multiplied-out number is absent rather than invented.

    Returns:
        A route and its number, or an honest statement that there is none.
    """
    routes = best_backed_routes(graph, frozenset({graph.hypothesis_id}))
    claims = {claim.id: claim for claim in graph.propositions}
    wanted = claims[destination].claim

    reached = routes.get(destination)
    if reached is not None and len(reached.path) > 1:
        return Verdict(
            kind="reached",
            path=reached.path,
            product=_multiplied_out(reached.path, beliefs),
            why=(
                f"The story reaches {wanted} in {len(reached.path) - 1} steps, "
                "along the best-backed route on this map."
            ),
        )

    touching, hops = _nearest_to(graph, destination, routes)
    if touching is not None:
        return Verdict(
            kind="no_path",
            nearest=touching,
            why=(
                f"Nothing on this map reaches {wanted}. The closest claim the "
                f"story does reach is {claims[touching].claim}, {hops} arrows away "
                "from it."
            ),
        )
    best_backed = _best_backed_end(graph, routes)
    if best_backed is None:
        return Verdict(
            kind="no_path",
            why=f"Nothing on this map reaches {wanted}. The story never left where it started.",
        )
    return Verdict(
        kind="no_path",
        nearest=best_backed,
        why=(
            f"Nothing on this map reaches {wanted}, and no arrow on it touches "
            f"that claim at all. The best-backed thing the story does reach is "
            f"{claims[best_backed].claim}."
        ),
    )


def _multiplied_out(
    route: Sequence[PropositionId], beliefs: Mapping[PropositionId, Belief] | None
) -> float | None:
    """Multiply the likelihoods along a route together.

    The claim the map started from is left out: it is what the person is supposing
    happens, so it is not one of the steps that has to go right.

    The map's own arithmetic has no such number today — nothing in `domain/`
    multiplies a route out — so it is worked out here, over numbers the map
    produced. It moves the day it does.

    Args:
        route: The route, claim by claim, starting at the claim the map started
            from.
        beliefs: The worked-through likelihood of every claim, or nothing at all.

    Returns:
        The product, or nothing at all when the numbers have not been run.
    """
    if beliefs is None:
        return None
    product = 1.0
    for claim_id in route[1:]:
        found = beliefs.get(claim_id)
        if found is None:
            return None
        product *= found.p
    return product


def _nearest_to(
    graph: Graph, destination: PropositionId, routes: Mapping[PropositionId, Route]
) -> tuple[PropositionId | None, int]:
    """Find the claim the story reached that is fewest arrows from the destination.

    Arrows are walked in either direction here, because the question is how close
    the map came and not which way the causing ran. That is a different question
    from choosing a route, which is why it is not the map's route rule.

    When nothing on the map touches the destination, there is no such distance,
    and we do not guess at one: nothing comes back, and the caller says so in
    plain words instead.

    Args:
        graph: The finished map.
        destination: The claim the person asked about.
        routes: Every claim the story reaches, by the map's own route rule.

    Returns:
        That claim and how many arrows away it is, or nothing at all and zero.
    """
    beside: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        beside.setdefault(arrow.source, []).append(arrow.target)
        beside.setdefault(arrow.target, []).append(arrow.source)

    reached = set(routes) - {destination}
    hops = {destination: 0}
    waiting = [destination]
    while waiting:
        here = waiting.pop(0)
        for neighbour in sorted(beside.get(here, [])):
            if neighbour not in hops:
                hops[neighbour] = hops[here] + 1
                waiting.append(neighbour)
                if neighbour in reached:
                    return neighbour, hops[neighbour]
    return None, 0


def _best_backed_end(graph: Graph, routes: Mapping[PropositionId, Route]) -> PropositionId | None:
    """Find where the story gets to along its best-backed route.

    Used only when nothing on the map touches the destination at all, so
    "closest" has no meaning there. **It orders by how well-backed a route is
    first and by how long it is only to separate two equally backed ones** — the
    name used to say "furthest reached", which reads as longest and is not what
    this does. Where the story got to along the road with the highest low bridge
    is the honest answer to "and what did it reach instead?" (2026-09-20).

    Args:
        graph: The finished map.
        routes: Every claim the story reaches, by the map's own route rule.

    Returns:
        That claim, or nothing at all when the story never left where it started.
    """
    got_to = [
        (route.width, len(route.path), claim_id)
        for claim_id, route in sorted(routes.items())
        if claim_id != graph.hypothesis_id
    ]
    return max(got_to)[2] if got_to else None
