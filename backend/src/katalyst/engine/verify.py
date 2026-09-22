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

**What grades a route: three worked-out numbers, never a product** (decision
record 0022). Multiplying the likelihoods along a route is not the chance of
anything once two claims on the map share a cause — if a second claim is true
exactly when the first is and both stand at a half, the product says a quarter
where the chance every step goes right is a half. So this door works three real
quantities out instead, each of them a probability or a difference of two:

* **the shift** — how much supposing the map's starting claim true moves the
  destination: the destination's chance with that claim supposed true, minus its
  chance with it supposed false.
* **the joint** — the chance **every** step on the named route goes right, with
  the starting claim supposed true. One elimination that keeps the whole route,
  never each step's own chance multiplied together.
* **the weakest arrow** — which single arrow on the route carries most of the
  shift, and how much of the shift goes with it: the arrow whose removal from the
  map leaves the smallest shift behind.

**What one verdict costs.** Two passes over the map for the shift — one with the
starting claim supposed true, one with it supposed false — and two more for every
arrow on the route, because removing an arrow moves both of those numbers and the
shift is the difference between them. The joint is free: it is read off the tables
the supposed-true pass already built. A route of three arrows therefore costs
eight passes.

This file needs no answerer, no receipt and no walk: it is asked once, after the
map is finished, and it works its own numbers out from the map, the branch and the
seed a world carries.

What this file must never do
----------------------------
- Never add an arrow, a claim or a route so that an answer exists.
- Never invent a nearness it cannot compute. Where "closest" has no meaning on a
  map, it says how far the story got instead, and the sentence says which of the
  two it is.
- Never multiply likelihoods along a route and call the result a chance. An absent
  number is honest; a number that is not the probability of anything is not.
"""

from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Literal

import numpy
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Belief, Do, Graph, Link, LinkId, PropositionId
from katalyst.domain.branch import Branch
from katalyst.domain.diff import Route, best_backed_routes
from katalyst.domain.patch import Assignment, apply
from katalyst.domain.propagation import (
    SAMPLED_WORLDS,
    Numbers,
    World,
    _worked_out,
    _WorkedOut,
)
from katalyst.domain.rates import SLICES
from katalyst.domain.solving import all_true

SUPPOSED_BY_THIS_DOOR = "verdict"
"""The name this door's own supposition is recorded under while it works.

A supposition needs a branch to belong to, and the two this door makes — the
starting claim true, the starting claim false — are its own working and are never
stored, shown, or handed back. Named once here so the two read the same.
"""


class Verdict(BaseModel):
    """Whether the story reached the place the person asked about, and how firmly.

    One of two answers, and never a third. When a world is handed in, the answer
    also carries the three numbers decision record 0022 puts beside a route: the
    shift, the joint and the weakest arrow. Without a world the route is graded
    structurally and all three are absent rather than invented.
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
            "Always nothing at all. This door used to multiply the likelihoods along "
            "a route together, and that number is not the probability of anything "
            "once two claims on the map share a cause, so it was deleted (decision "
            "record 0022). Dated 2026-09-22: the field stays on the wire, always "
            "empty, until the browser round closes and the empty fields go together."
        ),
    )
    shift: float | None = Field(
        default=None,
        description=(
            "How much supposing the map's starting claim true moves the destination: "
            "the destination's chance with that claim supposed true, minus its chance "
            "with it supposed false. Positive when supposing it makes the destination "
            "likelier. Nothing at all when no world was handed in."
        ),
    )
    joint: float | None = Field(
        default=None,
        description=(
            "The chance every step on the route goes right at once, with the map's "
            "starting claim supposed true — worked out as one joint over the map's "
            "own tables, never as each step's chance multiplied together. Nothing at "
            "all when there is no route, or when no world was handed in."
        ),
    )
    weakest_arrow: LinkId | None = Field(
        default=None,
        description=(
            "The single arrow on the route that carries most of the shift: the one "
            "whose removal from the map leaves the smallest shift behind. Two arrows "
            "that lose exactly the same amount are separated by taking whichever "
            "comes first in the map's own list of arrows. Nothing at all when there "
            "is no route, when no world was handed in, or when the shift is nought "
            "and so no arrow carries any of it."
        ),
    )
    share_of_the_shift: float | None = Field(
        default=None,
        description=(
            "How much of the shift goes with the weakest arrow: the shift lost by "
            "removing it, over the whole shift. A half means half the effect goes "
            "with that one arrow. It can read above one, or below nought, when "
            "removing the arrow turns the shift around, and it is reported as worked "
            "out rather than trimmed to fit. Nothing at all whenever the weakest "
            "arrow is."
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
    world: World | None = None,
    beliefs: Mapping[PropositionId, Belief] | None = None,
) -> Verdict:
    """Grade the route from the claim the map started at to the destination.

    The route shown is the **best-backed** one: over every route, the one whose
    weakest arrow is strongest, by the map's own rule.

    With a world in hand the answer also carries the three numbers of decision
    record 0022. **The shift is worked out whichever answer comes back**, because
    "does supposing this move that claim at all?" is a fair question even when no
    route reaches it — and the answer is then nought, exactly, which is the
    strongest way there is to say the story does not get there. The joint and the
    weakest arrow are about the route itself, so they are absent when there is none.

    Args:
        graph: The finished map.
        destination: The claim the person asked whether the story reaches.
        world: The world the numbers are read against — for the map it was built
            from, the values its edits fixed, its first day, its seed and how many
            versions of the map it tried. Without it the route is graded
            structurally and all three numbers are absent rather than invented.
        beliefs: **Read by nothing, and it goes when its one caller moves.** This
            door used to be handed every claim's likelihood so it could multiply
            them along the route; decision record 0022 deleted that multiplication.
            The argument is kept so that `katalyst.api.generate`, which belongs to
            another lane this week, still calls this door without a change it has
            not been given. Dated 2026-09-22; the one-line replacement is recorded
            with this pull request.

    Returns:
        A route and its three numbers, or an honest statement that there is none.
    """
    del beliefs
    routes = best_backed_routes(graph, frozenset({graph.hypothesis_id}))
    claims = {claim.id: claim for claim in graph.propositions}
    wanted = claims[destination].claim
    supposed = None if world is None else _both_ways(graph, world)
    shift = None if supposed is None else _shift_between(supposed, destination)

    reached = routes.get(destination)
    if reached is not None and len(reached.path) > 1:
        arrow, share = (
            (None, None)
            if world is None or shift is None
            else _weakest_arrow_on(graph, destination, reached.path, world, shift)
        )
        return Verdict(
            kind="reached",
            path=reached.path,
            shift=shift,
            joint=None if supposed is None else _joint_along(supposed[0], reached.path),
            weakest_arrow=arrow,
            share_of_the_shift=share,
            why=(
                f"The story reaches {wanted} in {len(reached.path) - 1} steps, "
                "along the best-backed route on this map."
            ),
        )

    touching, hops = _nearest_to(graph, destination, routes)
    if touching is not None:
        return Verdict(
            kind="no_path",
            shift=shift,
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
            shift=shift,
            why=f"Nothing on this map reaches {wanted}. The story never left where it started.",
        )
    return Verdict(
        kind="no_path",
        shift=shift,
        nearest=best_backed,
        why=(
            f"Nothing on this map reaches {wanted}, and no arrow on it touches "
            f"that claim at all. The best-backed thing the story does reach is "
            f"{claims[best_backed].claim}."
        ),
    )


# --- The three worked-out numbers ------------------------------------------


def _both_ways(graph: Graph, world: World) -> tuple[_WorkedOut, _WorkedOut]:
    """Work the map through twice: the starting claim supposed true, then supposed false.

    **Two supposed worlds, never a supposed one against the map as it stands.**
    Both sides are the same lever pulled the two ways it goes, so the distance
    between them is the claim's own effect and nothing else — not the effect plus
    wherever the map happened to leave the starting claim.

    Both passes are kept whole rather than reduced to two numbers, because the
    supposed-true one carries the tables the joint is read off and working them out
    a second time would be a whole pass over the map for a number already in hand.

    Args:
        graph: The finished map.
        world: The world the numbers are read against.

    Returns:
        The supposed-true pass and the supposed-false pass, in that order.
    """
    return (
        _pass_over(*_supposing(graph, world.assignments, graph.hypothesis_id, value=True), world),
        _pass_over(*_supposing(graph, world.assignments, graph.hypothesis_id, value=False), world),
    )


def _shift_between(supposed: tuple[_WorkedOut, _WorkedOut], destination: PropositionId) -> float:
    """Read how far apart the two supposed worlds leave one claim.

    A destination no chain of arrows reaches from the starting claim comes back
    **exactly nought**, and that is arithmetic rather than a special case:
    supposing a claim cuts the arrows into it, so it can move nothing that is not
    downstream of it, and the exact solve leaves such a claim bit for bit where it
    was under either supposition.

    Args:
        supposed: The supposed-true pass and the supposed-false pass.
        destination: The claim being moved.

    Returns:
        The destination's chance supposing the starting claim true, minus its
        chance supposing it false.
    """
    true_side, false_side = supposed
    return _one_number(true_side.answers[destination]) - _one_number(
        false_side.answers[destination]
    )


def _joint_along(supposed_true: _WorkedOut, path: Sequence[PropositionId]) -> float:
    """The chance every step on a route goes right, with the starting claim supposed true.

    **The claim the map started from is not one of the steps**: it is what the
    person is supposing happens, so it is supposed true here rather than counted
    as something that has to go right. Everything after it on the route is a step.

    Worked out as one joint over the map's own tables — the elimination keeps every
    step on the route at once and reads the corner where all of them are true. The
    steps' own chances are never multiplied together, because two steps that share
    a cause are not independent and a product would claim they were.

    Args:
        supposed_true: The pass made with the starting claim supposed true.
        path: The route, claim by claim, the starting claim first.

    Returns:
        The chance every step after the starting claim is true at once.
    """
    return _one_number(all_true(supposed_true.forward, supposed_true.pinned, tuple(path[1:])))


def _weakest_arrow_on(
    graph: Graph,
    destination: PropositionId,
    path: Sequence[PropositionId],
    world: World,
    shift: float,
) -> tuple[LinkId | None, float | None]:
    """Find which single arrow on the route carries most of the shift.

    Each arrow on the route is taken off the map in turn and the shift is worked
    out again on what is left; the arrow that loses the most is the one that
    carries the most. **Both halves of the shift are worked out again**, because
    removing an arrow moves the supposed-true world and the supposed-false world
    alike, and the shift is the distance between them.

    Only the arrows on the named route are tried. Trying every arrow on the map
    would answer a different question — *what matters most anywhere?* — and would
    cost two passes per arrow on a map of any size.

    **Two arrows that lose exactly the same amount** are separated by taking
    whichever comes first in the map's own list of arrows: the same tie-break the
    map's route rule uses, so a reader who has learned one has learned both.

    **A shift of nought has no arrow to attribute**, so nothing comes back rather
    than a share worked out by dividing by nought.

    Args:
        graph: The finished map.
        destination: The claim the shift is measured on.
        path: The route, claim by claim.
        world: The world the numbers are read against.
        shift: The shift on the whole map, which this is a share of.

    Returns:
        That arrow and its share of the shift, or nothing at all twice over.
    """
    if shift == 0.0:
        return None, None
    carrying: LinkId | None = None
    most_lost: float | None = None
    for arrow in _arrows_on(graph, path):
        without = graph.model_copy(
            update={"links": tuple(one for one in graph.links if one.id != arrow.id)}
        )
        lost = shift - _shift_between(_both_ways(without, world), destination)
        if most_lost is None or lost > most_lost:
            carrying, most_lost = arrow.id, lost
    if carrying is None or most_lost is None:  # pragma: no cover - a route has arrows
        return None, None
    return carrying, most_lost / shift


def _arrows_on(graph: Graph, path: Sequence[PropositionId]) -> tuple[Link, ...]:
    """Every arrow the route runs along, in the map's own order.

    A route is a list of claims, and two claims can be joined by more than one
    arrow. Each of those is its own candidate, because the question decision record
    0022 asks is which **single** arrow carries the shift. An arrow that feeds back
    on itself is left out here for the same reason the route rule leaves it out:
    the arithmetic sets it aside.

    Args:
        graph: The finished map.
        path: The route, claim by claim.

    Returns:
        The arrows whose source and target are a step of the route, in order.
    """
    steps = set(pairwise(path))
    return tuple(
        one for one in graph.links if not one.reflexive and (one.source, one.target) in steps
    )


def _supposing(
    graph: Graph,
    fixed: tuple[Assignment, ...],
    claim_id: PropositionId,
    *,
    value: bool,
) -> tuple[Graph, tuple[Assignment, ...]]:
    """Suppose one claim true or false, on top of whatever the branch already did.

    The product's own way of supposing, rather than a second one written here: the
    same fold every edit goes through, so the arrows into the supposed claim are
    cut exactly as they are cut anywhere else, and a claim the branch had already
    supposed is overruled by this supposition rather than fighting it.

    Args:
        graph: The map the branch's edits left behind.
        fixed: Every value those edits fixed.
        claim_id: The claim to suppose.
        value: What to suppose it is.

    Returns:
        The map with that claim's own causes cut away, and every value fixed.
    """
    folded = apply(
        graph,
        Branch(
            id=SUPPOSED_BY_THIS_DOOR,
            label="The claim this map started from, supposed",
            interventions=(Do(target=claim_id, value=value, at=None),),
        ),
        fixed,
    )
    if isinstance(folded, list):  # pragma: no cover
        # Unreachable: a supposition is refused only for naming a claim that is not
        # on the map, and this one is the map's own starting claim. Kept so that a
        # wrong assumption here is said out loud rather than quietly answered.
        raise ValueError(f"Supposing {claim_id} was refused: {folded[0].message}")
    return folded


def _pass_over(graph: Graph, fixed: tuple[Assignment, ...], world: World) -> _WorkedOut:
    """Work a map and its fixed values through the exact core, and keep what came out.

    **The engine's own single route, reached rather than copied.** Building a
    second assembly here would be a second chance for this door and the tiles
    beside it to disagree about the same map, which is the one thing a verdict may
    never do. What this door needs and a finished world does not carry is the
    tables the solve ran over — the joint is one more elimination across them — so
    it asks the assembly for its working rather than for its result.

    **There is one engine.** This is the by-deadline core's own route — decision
    record 0016's arithmetic, reached directly — and since the flip it is the only
    arithmetic there is, so these three numbers and the tiles beside them are worked
    out the same way.

    Dated 2026-09-22: `katalyst.domain.propagation` belongs to another lane this
    week, so the name is reached as it stands. The one-line change that makes it a
    public seam is recorded with this pull request.

    Args:
        graph: The map to work through.
        fixed: Every value its edits fixed.
        world: The world whose first day and seed this matches.

    Returns:
        The finished pass, the values it was given, and every claim's one number.
    """
    return _worked_out(
        graph,
        fixed,
        as_of=world.day_zero,
        seed=world.seed,
        slices=SLICES,
        sampled_worlds=SAMPLED_WORLDS,
    )


def _one_number(answer: Numbers) -> float:
    """Read the one number off a claim's answer.

    The engine works out one version of the map and one likelihood per claim
    (decision record 0028), so an answer is an array of exactly one number and this
    reads it. The average is taken rather than the first element because the array
    is still shaped as an array; with one entry the two are the same number, and the
    day the shape goes this function goes with it. Dated 2026-09-22.

    Args:
        answer: A claim's solved likelihood, as the core carries it.

    Returns:
        The one number, held between nought and one.
    """
    return float(numpy.clip(answer.mean(), 0.0, 1.0))


# --- Where the story got to, when it did not get there ---------------------


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
