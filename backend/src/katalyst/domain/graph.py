"""A graph: a whole cause-and-effect map, and the one rule it checks about itself.

*Map* and *graph* mean the same thing throughout. `Graph` is the type's name;
*map* is what the user sees.

A graph is immutable. Nothing edits one in place — a change is an intervention
recorded on a branch, and applying a branch produces a new graph. A graph is a
*proposal* until the validity rules have returned an empty list for it; nothing
reaches the canvas before that.

Almost everything that can be wrong with a map is decided by those rules rather
than here, because a well-formed model proposal breaks them all the time and the
user has to be told which claim or arrow it was, in a sentence. The one exception
is the rule below: a map whose starting claim is not on the map is not a map at
all, and only our own code could assemble one.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalyst.domain.ids import PropositionId
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition


class Graph(BaseModel):
    """A whole cause-and-effect map: claims, the arrows between them, and which claim started it.

    A graph is immutable. Nothing edits one in place — a change is an intervention
    recorded on a branch, and applying a branch produces a new graph. A graph is a
    proposal until the validity rules have returned an empty list for it; nothing
    reaches the canvas before that.
    """

    model_config = ConfigDict(frozen=True)

    # Open question 2 in spec/graph/validity.md: claims, arrows and branches each
    # have a named identifier type, and a map does not. Add `GraphId`, or leave
    # this a plain string?
    id: str = Field(description="Minted by our code, never by the model.")
    propositions: tuple[Proposition, ...] = Field(
        description=(
            "Every claim on the map, in no particular order. A tuple, so it cannot be appended to."
        )
    )
    links: tuple[Link, ...] = Field(
        description=(
            "Every arrow on the map. Each names a source and a target that must be present above."
        )
    )
    hypothesis_id: PropositionId = Field(
        description=(
            "The claim the user started from. Must name a proposition present in `propositions` — "
            "that much is checked when the object is built. That the named claim is actually of "
            "kind 'hypothesis', and that no second one exists, is checked by the validity rules."
        )
    )

    @model_validator(mode="after")
    def _hypothesis_is_on_the_map(self) -> "Graph":
        """Check that the claim the map started from is one of the claims on it.

        A map pointing at a claim that does not exist cannot be drawn, cannot be
        diffed and cannot be explained, and no model proposal produces one — our
        own code assembles this object, so a mismatch is our bug.

        Returns:
            This same graph, once the starting claim has been found.

        Raises:
            ValueError: If no proposition on the map carries that identifier.
        """
        if not any(proposition.id == self.hypothesis_id for proposition in self.propositions):
            raise ValueError(
                f"a graph's hypothesis_id must name a proposition on the same map; "
                f"'{self.hypothesis_id}' is not one of them"
            )
        return self
