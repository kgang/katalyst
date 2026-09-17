"""Two routes that hand out the worked examples this program ships with.

They are read-only. Nothing here builds a map, edits one, or works any
likelihoods through: the examples are written by hand in `katalyst.fixtures`,
checked the moment that package loads, and these routes only pass them on.

This is also the first place the product's real shapes cross to the browser. The
answer to the second route is a whole map — every claim, every arrow, every
belief — and the browser's TypeScript types are generated from the description
these routes publish, so the two halves cannot drift apart without a build
failing.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from katalyst.domain import Branch, Graph
from katalyst.fixtures import EXAMPLES, find

router = APIRouter(tags=["fixtures"])


class FixtureSummary(BaseModel):
    """One stored example as it appears in a list, before the map itself is drawn."""

    id: str = Field(
        description='The short name this example is asked for by, such as "hormuz".',
    )
    title: str = Field(description="What the example is called on screen.")
    one_line: str = Field(
        description="The example in one sentence, for a list where the map is not drawn.",
    )


class FixtureBundle(BaseModel):
    """One stored example in full: the base map and the branches that go with it.

    A branch is an ordered list of edits, not a second copy of the map, so the
    whole bundle is one map plus a few small lists of changes.
    """

    id: str = Field(
        description='The short name this example is asked for by, such as "hormuz".',
    )
    title: str = Field(description="What the example is called on screen.")
    fixture_date: date = Field(
        description=(
            "The day the example is set on. Every resolve-by date in it is a span "
            "from this day, so the example reads the same whenever it is opened."
        ),
    )
    graph: Graph = Field(
        description="The base map: every claim, every arrow, and which claim started it.",
    )
    branches: tuple[Branch, ...] = Field(
        description=(
            "The branches that go with this example, each an ordered list of edits "
            "over the base map. The base map itself is never changed by one."
        ),
    )


@router.get("/fixtures")
def list_fixtures() -> list[FixtureSummary]:
    """List the worked examples this program ships with.

    The list is enough to draw a chooser: a name to ask for, a title to show,
    and a sentence saying what the example is about. The maps themselves are not
    included, because a map is large and a chooser does not draw one.

    Returns:
        One entry per stored example, in the order they are offered.
    """
    return [
        FixtureSummary(id=example.id, title=example.title, one_line=example.one_line)
        for example in EXAMPLES
    ]


@router.get("/fixtures/{fixture_id}")
def read_fixture(fixture_id: str) -> FixtureBundle:
    """Give back one worked example in full: its base map and its branches.

    Args:
        fixture_id: The short name of the example, as the list route gives it.

    Returns:
        The base map and the branches that go with it.

    Raises:
        HTTPException: With status 404 and a sentence naming the examples that do
            exist, when nothing is stored under that name. The sentence is what
            the screen shows, so it is written for a reader rather than for a log.
    """
    example = find(fixture_id)
    if example is None:
        offered = ", ".join(one.id for one in EXAMPLES)
        raise HTTPException(
            status_code=404,
            detail=(
                f"There is no stored example called '{fixture_id}'. "
                f"The ones this program ships with are: {offered}."
            ),
        )
    return FixtureBundle(
        id=example.id,
        title=example.title,
        fixture_date=example.fixture_date,
        graph=example.graph,
        branches=example.branches,
    )
