"""The six ways to change a map, and nothing else.

A user reads the map, gets to the third box, and disagrees with it. That
disagreement is a typed edit: one of exactly six operations, recorded in a branch
— a named, ordered list of edits over an untouched original. Each one says up
front which part of the map it is allowed to touch, which is what makes the rest
of the product possible: only what is downstream can move, the change can be
replayed later, and every number that shifted can name the edit that shifted it.

The six are told apart by a field named `kind`. That makes them a *discriminated
union*: a reader — or the TypeScript generated for the browser — can look at
`kind` alone and know which of the six shapes the rest of the object has, with no
guessing from which fields happen to be present.

Each class is frozen, so an edit is a fact rather than a mutable object.

What is checked here and what is not. These classes check their own shape: a
`believe` edit carrying anyone but the user's number cannot be built at all,
because there is no valid map in which that is acceptable. Everything that
depends on the *map* — that the target is actually on it, that an identifier is
not already in use, that the result still has no loops — is a precondition, and
preconditions are checked when a branch is folded onto a map, which is not part
of this stack.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from katalyst.domain.belief import Belief
from katalyst.domain.ids import LinkId, PropositionId
from katalyst.domain.link import Link
from katalyst.domain.proposition import Proposition


class Do(BaseModel):
    """Suppose a claim is true — and cut it loose from whatever would have caused it.

    This is what a hypothesis is. The user is pulling a lever, not reporting news,
    so nothing upstream of the claim may move: supposing the strait opens must not
    quietly raise the odds that a diplomatic deal happened. To record something
    that actually happened, use `Observe` instead.

    The cut reaches only the arrows into the target that exist at the moment this
    edit is applied; an arrow added after it is live, and can push the target back
    the other way. This is a supposition that starts on a day — "true from `at`" —
    not a permanent seal on the claim.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["do"] = "do"
    target: PropositionId = Field(description="The claim being supposed true or false.")
    value: bool = Field(
        description="True to suppose the claim holds; False to suppose it does not."
    )
    # Open question 3 in spec/multiverse/interventions.md: `Do` carries a date and
    # `Observe` does not. "The premium printed below 0.4% on the 3rd" seems to
    # want one as much as a supposition does.
    at: date | None = Field(
        default=None,
        description=(
            "The day the supposition takes effect. Links out of the target measure "
            "their delay from this day. None means the map's own start date."
        ),
    )


class Observe(BaseModel):
    """Record that a claim actually came true (or false) — this is news, not a lever.

    Unlike `Do`, the claim's causes are left connected, so learning it may also
    revise what we believe about what caused it, and therefore about everything
    those causes lead to. This is the one operation allowed to move things
    upstream.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["observe"] = "observe"
    target: PropositionId = Field(
        description="The claim that has been observed to be true or false."
    )
    value: bool = Field(description="True if the claim came out true; False if it came out false.")


class Insert(BaseModel):
    """Add a new claim to the map, together with the arrows that connect it.

    This is the "…but X also happens" move. The new claim and its arrows arrive as
    one edit, so the map is never left holding a claim that causes nothing and is
    caused by nothing.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["insert"] = "insert"
    proposition: Proposition = Field(
        description="The new claim, complete with how and when it will be checked."
    )
    links: tuple[Link, ...] = Field(
        description=(
            "The arrows that attach the new claim to the map. Each one has the new "
            "claim at one end and an existing claim at the other."
        )
    )


class Retune(BaseModel):
    """Change how hard one arrow pushes — and change nothing else about it.

    The user disagrees with the model's number on a single link. This edit reaches
    exactly one field of exactly one link: its `strength`. It cannot touch the
    arrow's mechanism, its delay, its shape, which two claims it joins, or any
    belief anywhere.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["retune"] = "retune"
    link: LinkId = Field(description="The one arrow whose push is being changed.")
    strength: float = Field(
        description=(
            "The new push, on a log-odds scale — the scale on which separate "
            "influences add together instead of multiplying. Signed: a negative "
            "number pushes the downstream claim toward false."
        )
    )


class Refine(BaseModel):
    """Split one claim into finer claims that must add back up to it.

    "US election goes this way" becomes a claim per state. The finer claims
    replace the original as the thing the map reasons about, and their combined
    likelihood has to equal the original's — otherwise splitting a claim would
    quietly change the map's answer. The type exists from this stack; the
    operation is applied later.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["refine"] = "refine"
    target: PropositionId = Field(description="The claim being split.")
    # "At least two" is a precondition, checked when the branch is folded onto a
    # map, not here: see the preconditions table in
    # spec/multiverse/interventions.md.
    into: tuple[Proposition, ...] = Field(
        description="The finer claims that replace it. At least two."
    )
    reconcile: Literal["marginalize"] = Field(
        default="marginalize",
        description=(
            "How the finer claims are made to agree with the original. "
            "'marginalize' means their combined likelihood must equal the "
            "original's, within a small tolerance."
        ),
    )


class Believe(BaseModel):
    """Record what the *user* thinks the likelihood of one claim is.

    The user's number is a first-class input, not a correction. It is written to
    the user's own slot and sits beside the model's and the market's; it never
    overwrites either of them and they are never averaged together. In this
    version it is not pushed through the map.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["believe"] = "believe"
    target: PropositionId = Field(description="The claim the user is putting a number on.")
    belief: Belief = Field(
        description=(
            "The user's likelihood with its honest range. Its owner must be 'user'; "
            "a belief owned by the model or by a market is rejected."
        )
    )

    @field_validator("belief")
    @classmethod
    def owner_must_be_user(cls, value: Belief) -> Belief:
        """Check that a `believe` edit carries only the user's own number.

        This runs while the object is being built, so a `Believe` carrying the
        model's number cannot exist. It is not a later check over a whole map:
        there is no valid map in which this is acceptable, so it fails at the
        door.

        Args:
            value: The belief the edit was given.

        Returns:
            That same belief, once its owner has been checked.

        Raises:
            ValueError: If the belief is owned by anyone but the user.
        """
        if value.owner != "user":
            raise ValueError(
                "a believe intervention carries the user's own belief; "
                f"this one is owned by '{value.owner}'"
            )
        return value


Intervention = Annotated[
    Do | Observe | Insert | Retune | Refine | Believe,
    Field(discriminator="kind"),
]
"""One typed edit to a map. Read the `kind` field to know which of the six it is."""
