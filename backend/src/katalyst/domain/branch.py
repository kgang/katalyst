"""A branch: a named, ordered list of edits sitting beside an original nobody touches.

The user asks "…but what if Iran is struck the next day?" and expects two things
at once: the new answer, and the old one still there to compare it against. That
only works if changing the map never changes the map. So a branch is not a copy
of the map with edits made to it — it is the ordered list of edits themselves.

A *world* is what you get when a branch is folded onto the original and the
likelihoods are worked through. The branch is the durable thing; the world is a
result that can always be thrown away and rebuilt. No world is defined in this
stack, and nothing here folds a branch onto anything.

The base world is not a special case in the code, not a null and not a flag: it
is a branch whose edit list is empty.
"""

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.ids import BranchId
from katalyst.domain.intervention import Intervention


class Branch(BaseModel):
    """A named, ordered list of edits over a base map. A branch *is* a patch.

    It holds no propositions, no links, no likelihoods and no results — only the
    edits. Everything a branch shows on screen is computed from the base map plus
    this list, which is what makes a branch cheap to create, exact to replay, and
    impossible to drift from the original it forked out of.
    """

    model_config = ConfigDict(frozen=True)

    id: BranchId = Field(description="This branch's identifier.")
    label: str = Field(
        description=(
            "The name the user reads: 'Hormuz opens, then Iran is struck'. "
            "Required — an unnamed branch is unusable once there are three of them."
        )
    )
    parent: BranchId | None = Field(
        default=None,
        description=(
            "The branch this one continues from, whose edits are applied first. "
            "None means this branch forks directly off the untouched base map."
        ),
    )
    interventions: tuple[Intervention, ...] = Field(
        default=(),
        description=(
            "The edits, in the order the user made them. Order matters: an edit can "
            "act on what an earlier edit added. An empty list is the base world."
        ),
    )
