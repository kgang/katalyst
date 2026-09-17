"""Building a world from a stored example, which is why this lives here and not in the rules layer.

The rules layer works a map and a list of fixed values through time. It cannot
find the map: it reads no store and no clock, and that is exactly what makes it
pure, repeatable and testable against thousands of generated inputs. So the
fetching happens out here, at the edge, and the finished map is passed in as an
ordinary value.

Four things happen in this file and nowhere else:

* the base map is found among the stored examples, by the short name a request
  gives;
* a branch's chain of parents is walked and its edits put in order, oldest
  ancestor's first;
* day zero is read from the stored example's own date, so the example reads the
  same whenever it is opened;
* the seed travels through from the request, because there is nowhere to keep one
  yet.

**Failure is a list of violations, never an exception.** An edit that names a
claim the map does not have, a branch that continues from one nobody stored, an
arrow that is not there: each comes back as a stable code, the identifier of the
thing at fault, and one plain sentence the user can act on. A name that matches no
stored example comes back as nothing at all, which the route turns into its own
answer.

What this file must never do
----------------------------
- Never change a stored example. Every map here is frozen and every branch is
  folded onto a copy, so the example the next request sees is the one this one
  saw.
- Never repair a branch. Nothing here drops an edit that does not fit, renames an
  identifier that is taken, or quietly skips a claim it cannot find.
- Never invent a day zero. It is the stored example's own date, never today's.
- Never keep a world. A world is a computed result that can always be thrown away
  and rebuilt from the base map, the branch and the seed; anything kept here would
  eventually disagree with those three.
"""

from collections.abc import Mapping

from katalyst.domain import (
    Assignment,
    Belief,
    Branch,
    Diff,
    Do,
    Graph,
    Intervention,
    Link,
    LinkId,
    Violation,
    World,
    apply,
    diff,
    flatten,
    introduced_by,
    propagate,
)
from katalyst.fixtures import EXAMPLES, StoredExample, find

VERSIONS = 2_000
"""How many versions of the map a world is built from when a request does not say.

The outer loop: how sure we are of the numbers put in. It is the same number
`propagate` carries as its own default, and `test_a_world_is_built_at_the_shipped
_budget` fails if the two ever part company.
"""

WORLDS = 8
"""How many worlds run under each version when a request does not say.

The inner loop: how the dice fall. The same number `propagate` defaults to.
"""


def no_such_example(base_id: str) -> str:
    """Say, in one sentence, that no example is stored under this name, and name the ones that are.

    Args:
        base_id: The short name that was asked for.

    Returns:
        A sentence for the reader, never a code and never a stack trace.
    """
    offered = ", ".join(one.id for one in EXAMPLES)
    return (
        f"There is no stored example called '{base_id}'. "
        f"The ones this program ships with are: {offered}."
    )


def build_world(
    base_id: str,
    branch: Branch | None,
    seed: int,
    *,
    versions: int = VERSIONS,
    worlds: int = WORLDS,
) -> World | list[Violation] | None:
    """Fold a branch onto a stored example and work every likelihood through time.

    Args:
        base_id: The short name of the stored example, such as `hormuz`.
        branch: The branch to fold, sent whole because there is nowhere to keep
            one yet. Nothing at all means the base world — the empty branch.
        seed: The one number every random draw in the answer comes from.
        versions: The outer loop: how many versions of the map to try.
        worlds: The inner loop: how many worlds to run under each version.

    Returns:
        One world, or the list of reasons the branch could not be folded, or
        nothing at all when no example is stored under that name.
    """
    example = find(base_id)
    if example is None:
        return None
    folded = _fold(example, branch)
    if isinstance(folded, list):
        return folded
    graph, fixed, told = folded
    return _worked_through(graph, fixed, example, branch, seed, told, versions, worlds)


def difference(
    base_id: str,
    branch_a: Branch | None,
    branch_b: Branch,
    seed: int,
    *,
    versions: int = VERSIONS,
    worlds: int = WORLDS,
) -> Diff | list[Violation] | None:
    """Build two worlds from one map and one seed, and say what moved between them.

    Both worlds are built from the **same** seed, which is not an optimisation: it
    is what makes the comparison mean anything. The stream that picks which
    versions of the map to try never depends on the branch, so version 7 of one
    world and version 7 of the other were built from the same underlying numbers
    and differ only by the edit.

    Args:
        base_id: The short name of the stored example both worlds are built from.
        branch_a: The branch to compare from. Nothing at all means the base world.
        branch_b: The branch to compare to. Required, because its name is what the
            summary sentence calls the change — a world carries the identifier of
            its branch and not the name the user gave it.
        seed: The one seed both worlds are built from.
        versions: The outer loop both worlds run.
        worlds: The inner loop both worlds run.

    Returns:
        One difference, or the list of reasons one of the branches could not be
        folded, or nothing at all when no example is stored under that name.
    """
    before = build_world(base_id, branch_a, seed, versions=versions, worlds=worlds)
    if before is None or isinstance(before, list):
        return before
    after = build_world(base_id, branch_b, seed, versions=versions, worlds=worlds)
    if after is None or isinstance(after, list):
        return after
    return diff(before, after, edit_in_words=branch_b.label)


def conditional(
    base_id: str,
    branch: Branch | None,
    seed: int,
    link_id: LinkId,
    *,
    versions: int = VERSIONS,
    worlds: int = WORLDS,
) -> Belief | list[Violation] | None:
    """Work out one arrow's number: its target's likelihood with its source **supposed** true.

    Supposed, never observed. "How often do these two show up together" is a
    correlation, and a wire claims a mechanism; the two disagree whenever a third
    thing caused both, and a reader looking at the wire would have no way to tell.
    So the source is supposed true — cut loose from whatever would have caused it —
    and the target is read off the world that produces.

    It is worked out one arrow at a time because it costs a whole extra run of the
    engine per arrow, for a number most readers never open. Nothing is lost by
    waiting: the number is a pure function of the same inputs plus the arrow, so a
    number fetched when somebody asks is identical to one worked out in advance.

    Args:
        base_id: The short name of the stored example.
        branch: The branch to fold first. Nothing at all means the base map.
        seed: The one number every random draw comes from.
        link_id: The arrow whose number is wanted.
        versions: The outer loop, which should match the world the number is shown
            beside.
        worlds: The inner loop, for the same reason.

    Returns:
        One likelihood with its range, owned by the model, or the list of reasons
        the answer could not be worked out, or nothing at all when no example is
        stored under that name.
    """
    example = find(base_id)
    if example is None:
        return None
    folded = _fold(example, branch)
    if isinstance(folded, list):
        return folded
    graph, fixed, told = folded

    arrow = next((one for one in graph.links if one.id == link_id), None)
    if arrow is None:
        return [
            Violation(
                code="unknown_link",
                subject=link_id,
                message=(
                    "This asks for the number on an arrow that is not on this map, so "
                    "there is nothing here to work out."
                ),
            )
        ]

    supposed = _suppose_the_cause(graph, fixed, arrow)
    if isinstance(supposed, list):  # pragma: no cover
        # Unreachable: the only thing a supposition is refused for is naming a
        # claim that is not on the map, and this one is an end of an arrow that
        # was read off the map a line ago. Kept so that a wrong assumption here
        # is said out loud rather than producing a number nobody can account for.
        return supposed
    with_the_cause, also_fixed = supposed
    world = _worked_through(
        with_the_cause, also_fixed, example, branch, seed, told, versions, worlds
    )
    return world.beliefs[arrow.target]


# --- Putting a branch in order and folding it ------------------------------


def _fold(
    example: StoredExample, branch: Branch | None
) -> tuple[Graph, tuple[Assignment, ...], Mapping[LinkId, int]] | list[Violation]:
    """Put a branch's chain of parents in order, fold the whole run onto the map, and fold in order.

    A child branch continues from its parent, so its world is built from the
    parent's edits followed by its own. The rules layer sees one branch at a time
    and never the collection, so the collection is assembled here: the branches
    the stored example ships with, plus the one the request sent, which wins if
    both carry the same name.

    Args:
        example: The stored example, for its base map and its own branches.
        branch: The branch the request sent, or nothing at all for the base world.

    Returns:
        The map the edits left behind, every value they fixed, and which edit added
        which arrow — or the list of reasons the branch was refused.
    """
    edits = _edits_in_order(example, branch)
    if isinstance(edits, list):
        return edits
    whole = Branch(
        id=branch.id if branch is not None else "base",
        label=branch.label if branch is not None else "the untouched map",
        parent=None,
        interventions=edits,
    )
    folded = apply(example.graph, whole)
    if isinstance(folded, list):
        return folded
    graph, fixed = folded
    return graph, fixed, introduced_by(edits)


def _edits_in_order(
    example: StoredExample, branch: Branch | None
) -> tuple[Intervention, ...] | list[Violation]:
    """List a branch's edits with its parents' edits in front of them.

    Args:
        example: The stored example, for the branches it ships with.
        branch: The branch the request sent, or nothing at all.

    Returns:
        Every edit on the chain, the oldest ancestor's first, or one violation
        saying why the chain could not be put in order.
    """
    if branch is None:
        return ()
    known: dict[str, Branch] = {one.id: one for one in example.branches}
    known[branch.id] = branch
    return flatten(known, branch.id)


def _suppose_the_cause(
    graph: Graph, fixed: tuple[Assignment, ...], arrow: Link
) -> tuple[Graph, tuple[Assignment, ...]] | list[Violation]:
    """Suppose one arrow's cause true, on top of whatever the branch already did.

    Args:
        graph: The map the branch's edits left behind.
        fixed: Every value those edits fixed.
        arrow: The arrow whose cause is being supposed.

    Returns:
        The map with the cause's own causes cut away and the supposition recorded,
        or the reason the supposition was refused.
    """
    return apply(
        graph,
        Branch(
            id="conditional",
            label="One arrow's cause, supposed true",
            interventions=(Do(target=arrow.source, value=True, at=None),),
        ),
        fixed,
    )


def _worked_through(
    graph: Graph,
    fixed: tuple[Assignment, ...],
    example: StoredExample,
    branch: Branch | None,
    seed: int,
    told: Mapping[LinkId, int],
    versions: int,
    worlds: int,
) -> World:
    """Work every likelihood through time, and write in which branch it was.

    Day zero is the stored example's own date and never today's, so the example
    reads the same in a year as it does now. Which branch a world came from is
    written in here because working the numbers through takes a map and the values
    its edits fixed, and never the branch itself.

    Args:
        graph: The map the edits left behind.
        fixed: Every value they fixed, in order.
        example: The stored example, for its date.
        branch: The branch that was folded, or nothing at all for the base world.
        seed: The one number every draw comes from.
        told: Which edit added each arrow, so a supposition something undermined
            can name the edit responsible.
        versions: The outer loop.
        worlds: The inner loop.

    Returns:
        One world, naming the branch it came from.
    """
    world = propagate(
        graph,
        fixed,
        as_of=example.fixture_date,
        seed=seed,
        versions=versions,
        worlds=worlds,
        introduced_by=told,
    )
    return world.model_copy(update={"branch_id": branch.id if branch is not None else None})
