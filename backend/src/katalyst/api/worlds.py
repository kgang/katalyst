"""Three routes that work a branch through a map and say what it did.

They are the first routes that compute anything. Everything before them handed
back something written by hand; these fold a branch onto a stored example, work
every likelihood through time, and give back numbers nobody typed.

Three questions, three routes:

* **What does this branch make the map say?** One world: a likelihood and a range
  for every claim on the day it is judged, a likelihood for every day in between,
  and a named word for each of those days.
* **What moved between these two branches?** One difference: what happened to
  every claim, the endings that moved in ranked order, and one fixed sentence.
* **What is the number on this one arrow?** The arrow's target with the arrow's
  source **supposed** true — never how often the two happen to show up together.

**A branch is sent whole, not by name.** There is nowhere to keep one yet, so the
browser holds the branch it built and sends it with every question. The seed
travels the same way, which is what makes an answer reproducible from three
values: the name of the example, the branch, and the seed.

**A branch that does not fit the map comes back as 422 with every reason at
once** — each a stable code, the identifier of the thing at fault, and one plain
sentence naming the claim or the arrow by its words. Never a server error, never
a half-applied branch, never a silent repair. A name that matches no stored
example is a 404 with a sentence saying which examples exist.

Nothing here asks a language model anything, and none of it needs a key.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from katalyst.domain import Belief, Branch, Diff, LinkId, Violation, World
from katalyst.engine import worlds as engine

router = APIRouter(tags=["worlds"])


class RefusedEdit(BaseModel):
    """Why a branch could not be folded onto a map: every reason at once, never just the first.

    A person fixing a branch one fault per attempt learns only that the tool is
    hostile, so the whole list comes back together. Each entry is addressed to two
    readers at once: the code and the subject are for the interface, which uses
    them to highlight the right tile or wire, and the message is the sentence the
    person reads.
    """

    detail: tuple[Violation, ...] = Field(
        description="Every reason the branch was refused, in a settled order."
    )


REFUSED: dict[int | str, dict[str, Any]] = {
    422: {
        "model": RefusedEdit,
        "description": (
            "The request cannot be carried out as written — on these routes, always a "
            "branch that does not fit the map, because both worlds of a comparison are "
            "built here from the one base map, seed and pair of loop sizes. The answer "
            "lists every reason at once, each with a stable code the interface can switch "
            "on, the identifier of the thing at fault, and one plain sentence naming the "
            "claim or the arrow by its words. A body the server cannot read at all is also "
            "a 422, and says so in its own words."
        ),
    }
}
"""How a refused branch is described to whatever generates the browser's types."""


class WorldRequest(BaseModel):
    """What it takes to build one world: a map, a branch, and a seed.

    Those three are the whole of a world. The same three give a byte-identical
    answer on any machine and at any time, which is what makes a screenshot from
    three days ago reproducible.
    """

    base_id: str = Field(
        description='The short name of the stored example, such as "hormuz".',
    )
    branch: Branch | None = Field(
        default=None,
        description=(
            "The branch to fold, sent whole because there is nowhere to keep one yet. "
            "Leave it out for the base world — the map with nothing done to it."
        ),
    )
    seed: int = Field(
        description=(
            "The one number every random draw in the answer comes from. The same seed "
            "always gives the same world."
        )
    )
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description=(
            "How many versions of the map to try: how sure we are of the numbers put in. "
            "Each version is one coherent set of numbers this model would have stood "
            "behind, and the range on every answer is the spread across them. Bounded "
            "at both ends: a request above the ceiling is refused, never quietly made "
            "smaller, because a caller who asks for one run and gets another is reading "
            "numbers that answer a question nobody asked."
        ),
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description=(
            "How many worlds to run under each version: how the dice fall. At least two, "
            "or there is no spread inside a version to subtract from the range; and no "
            "more than the ceiling, which is measured rather than chosen."
        ),
    )


class DiffRequest(BaseModel):
    """What it takes to compare two branches: one map, two branches, and one seed.

    One seed for the pair, and that is not an optimisation. The stream that picks
    which versions of the map to try never depends on the branch, so version 7 of
    one world and version 7 of the other were built from the same underlying
    numbers and differ only by the edit. Build them from two seeds and every
    difference is the edit plus a wash of sampling noise.
    """

    base_id: str = Field(description="The short name of the stored example both worlds use.")
    branch_a: Branch | None = Field(
        default=None,
        description="The branch to compare from. Leave it out for the base world.",
    )
    branch_b: Branch = Field(
        description=(
            "The branch to compare to. Required, because the name the user gave it is "
            "what the summary sentence calls the change."
        )
    )
    seed: int = Field(description="The one seed both worlds are built from.")
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description="The outer loop both worlds run.",
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description="The inner loop both worlds run.",
    )


class ConditionalRequest(BaseModel):
    """What it takes to work out the number on one arrow.

    One arrow at a time, because each one costs a whole extra run of the engine
    for a number most readers never open. Nothing is lost by waiting: the answer
    is a pure function of these four things, so a number fetched when somebody
    asks is identical to one worked out in advance.
    """

    base_id: str = Field(description="The short name of the stored example.")
    branch: Branch | None = Field(
        default=None,
        description="The branch to fold first. Leave it out for the untouched map.",
    )
    seed: int = Field(description="The one number every random draw comes from.")
    link_id: LinkId = Field(description="The arrow whose number is wanted.")
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description="The outer loop. Match the world this number is shown beside.",
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description="The inner loop, for the same reason.",
    )


@router.post("/worlds", responses=REFUSED)
def build_world(request: WorldRequest) -> World:
    """Fold a branch onto a stored example and work every likelihood through time.

    Ask with no branch for the base world — the map as it stands, with nothing
    done to it. That is what the browser asks for first, and it is why the route
    that hands out the stored examples still hands out a map and its branches and
    nothing computed: a map is written by hand and a world never is.

    Args:
        request: Which example, which branch, which seed, and how big a run.

    Returns:
        One world, naming the branch it came from.

    Raises:
        HTTPException: With status 404 and a sentence naming the examples that do
            exist, when nothing is stored under that name. With status 422 and the
            list of reasons, when the branch does not fit the map.
    """
    built = engine.build_world(
        request.base_id,
        request.branch,
        request.seed,
        versions=request.versions,
        worlds=request.worlds,
    )
    return _answered(built, request.base_id)


@router.post("/worlds/diff", responses=REFUSED)
def compare_worlds(request: DiffRequest) -> Diff:
    """Build two worlds from one map and one seed, and say what moved between them.

    The answer is exactly what asking for the two worlds separately and comparing
    them gives, to the byte. This route exists because the comparison needs both
    worlds at once and sending two whole worlds to the browser so that it can
    subtract them would be sending it work it has no way to check.

    Args:
        request: Which example, which two branches, which seed, and how big a run.

    Returns:
        One difference: every claim with what happened to it, the endings that
        moved in ranked order, one fixed sentence, and every warning either world
        carried.

    Raises:
        HTTPException: With status 404 when nothing is stored under that name, or
            422 with the list of reasons when one of the branches does not fit.
    """
    compared = engine.difference(
        request.base_id,
        request.branch_a,
        request.branch_b,
        request.seed,
        versions=request.versions,
        worlds=request.worlds,
    )
    return _answered(compared, request.base_id)


@router.post("/worlds/conditional", responses=REFUSED)
def read_conditional(request: ConditionalRequest) -> Belief:
    """Give the number on one arrow: its target, with its source **supposed** true.

    Supposed, never observed. "How often do these two show up together" is a
    correlation, and an arrow claims a mechanism; the two disagree whenever a
    third thing caused both, and nothing on the wire would tell the reader which
    they were looking at.

    Args:
        request: Which example, which branch, which seed, and which arrow.

    Returns:
        One likelihood with its range, owned by the model.

    Raises:
        HTTPException: With status 404 when nothing is stored under that name, or
            422 when the branch does not fit the map or the arrow is not on it.
    """
    number = engine.conditional(
        request.base_id,
        request.branch,
        request.seed,
        request.link_id,
        versions=request.versions,
        worlds=request.worlds,
    )
    return _answered(number, request.base_id)


def _answered[Answer](outcome: Answer | list[Violation] | None, base_id: str) -> Answer:
    """Hand back the answer, or turn a refusal into the status that says what happened.

    Three outcomes, and each is somebody's fault in a different place. Nothing at
    all means the name does not match any stored example, which is the caller
    asking for something that is not here: 404. A list of violations means the
    branch does not fit the map, which is a branch the user can still repair: 422,
    with every reason at once. Anything else is the answer.

    Args:
        outcome: What the engine gave back.
        base_id: The name that was asked for, for the sentence when it matches
            nothing.

    Returns:
        The answer, when there is one.

    Raises:
        HTTPException: With status 404 or 422, carrying text a person can read.
    """
    if outcome is None:
        raise HTTPException(status_code=404, detail=engine.no_such_example(base_id))
    if isinstance(outcome, list):
        raise HTTPException(status_code=422, detail=[one.model_dump() for one in outcome])
    return outcome
