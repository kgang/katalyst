"""The stored examples this program ships with, and how to find one by name.

A stored example is a complete, valid map plus the branches that go with it,
written by hand and checked when it loads. It is what the product shows before a
user has typed anything, what the golden test measures the arithmetic against,
and what the canvas is developed against without spending a model call.

There is one today. The shape here is a list rather than a single value because
the product's empty screen offers four seeded examples, and adding the next one
should mean writing a file and adding a line to the tuple below — not touching a
route.

This layer may read the rules layer and does. The rules layer must never read
this one: an example is data we happen to ship, and nothing about whether a map
is valid may depend on it.
"""

from dataclasses import dataclass
from datetime import date

from katalyst.domain import Branch, Graph
from katalyst.fixtures.hormuz import (
    FIXTURE_DATE,
    HORMUZ,
    HORMUZ_THEN_STRIKE,
    ONE_LINE,
    TITLE,
)


@dataclass(frozen=True)
class StoredExample:
    """One worked example: a map, the branches that go with it, and how to name it.

    Frozen, like everything it holds. It is assembled once when this file loads
    and read from then on.
    """

    id: str
    """The short name the route and the browser use, such as `hormuz`."""

    title: str
    """What the example is called on screen."""

    one_line: str
    """The example in one sentence, for a list where the map itself is not drawn."""

    fixture_date: date
    """The day the example is set on. Every date in it is a span from this one."""

    graph: Graph
    """The base map: every claim and every arrow, already checked."""

    branches: tuple[Branch, ...]
    """The branches that go with it. Each one is an ordered list of edits, not a copy."""


EXAMPLES: tuple[StoredExample, ...] = (
    StoredExample(
        id="hormuz",
        title=TITLE,
        one_line=ONE_LINE,
        fixture_date=FIXTURE_DATE,
        graph=HORMUZ,
        branches=(HORMUZ_THEN_STRIKE,),
    ),
)
"""Every stored example, in the order they are offered."""


def find(example_id: str) -> StoredExample | None:
    """Find the stored example with this name, or report that there is none.

    Returns nothing rather than raising, because the caller is a route and the
    answer "there is no example called that" is an ordinary reply with a
    sentence in it, not an error.

    Args:
        example_id: The short name being asked for, such as `hormuz`.

    Returns:
        The example with that name, or None if no example has it.
    """
    for example in EXAMPLES:
        if example.id == example_id:
            return example
    return None
