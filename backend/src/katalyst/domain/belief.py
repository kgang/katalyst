"""A belief: a likelihood with an honest range and a name on it.

A bare number on a box is a claim from nowhere. A belief is a likelihood that
says whose it is and how sure it is: a value between 0 and 1, a range around it,
and an owner — the model, the user, or a market. Every claim on the map carries
up to three of them side by side, and they are never combined into one.

That is the product in one design choice. The model's .61, the market's .48 and
your own .30 on the same claim are not three attempts at one true number to be
averaged away. They are the disagreement you are about to trade: model minus
market is the edge, user minus model is the argument you are having with the
tool.

Both classes here are frozen — once built, an instance cannot be changed. A
change is a new instance, recorded as an intervention on a branch.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Belief(BaseModel):
    """A likelihood with an honest range and a name on it.

    `p` is the likelihood, `lo` and `hi` are the range around it, and `owner`
    says whose number this is. There are exactly three owners and no code path
    ever combines two of them into one number.

    A belief is a number, never text. This layer does not round it and does not
    store it as a string; rounding happens once, at the moment of display.
    """

    model_config = ConfigDict(frozen=True)

    # Open question 1 in spec/graph/belief.md: a belief records no provenance,
    # so a model number anchored on a documented count and one asserted from
    # nothing look alike. Owner is not yet the whole answer.
    p: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How likely the claim is to come out true, from 0 (certainly not) to 1 (certainly yes)."
        ),
    )
    lo: float = Field(
        ge=0.0,
        le=1.0,
        description="The bottom of the honest range around `p`. Never above `p`.",
    )
    hi: float = Field(
        ge=0.0,
        le=1.0,
        description="The top of the honest range around `p`. Never below `p`.",
    )
    owner: Literal["model", "user", "market"] = Field(
        description=(
            "Whose number this is: the model's estimate, the user's own, or a live "
            "price at a venue."
        ),
    )

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Belief":
        """Check that low is at most the likelihood, which is at most high.

        The field bounds above already cover 0 and 1; this covers the order.

        Returns:
            This same belief, once the order has been checked.

        Raises:
            ValueError: If the three numbers are not in order.
        """
        if not (self.lo <= self.p <= self.hi):
            raise ValueError(
                "a belief must satisfy low <= likelihood <= high; got "
                f"low={self.lo}, likelihood={self.p}, high={self.hi}"
            )
        return self


class Beliefs(BaseModel):
    """The three voices on one claim: the model's, the user's, and a market's.

    Three named slots, deliberately not a dictionary, so that nothing can loop
    over them and average them by accident. `model` is always present. `user` is
    absent until the user says what they think. `market` is absent when no venue
    quotes this claim — and absent means the words "no market", never a blank and
    never a stand-in number.

    The field named `model` is legal. Pydantic protects names beginning with
    `model_`, so `model_config` and `model_dump` are reserved; plain `model` is
    not one of them. It stays `model` because that is the word the shared
    vocabulary uses, on the canvas and in the code alike.
    """

    model_config = ConfigDict(frozen=True)

    model: Belief = Field(
        description=(
            "What the model thinks, with this claim's causes taken into account. Always present."
        ),
    )
    user: Belief | None = Field(
        default=None,
        description=(
            "What the user thinks. Written only by the `believe` intervention. None means "
            "the user has not said."
        ),
    )
    market: Belief | None = Field(
        default=None,
        description=(
            "What a venue is currently pricing, read live and read-only. None means no "
            "venue quotes this claim."
        ),
    )

    @model_validator(mode="after")
    def _owners_match_slots(self) -> "Beliefs":
        """Check that each slot holds a belief owned by the voice the slot is named for.

        A belief sitting in the wrong slot would make the never-merge rule
        unenforceable: a user's number could sit in the model's chip and nothing
        would notice.

        Returns:
            This same set of beliefs, once every slot has been checked.

        Raises:
            ValueError: If any slot holds a belief owned by someone else.
        """
        for slot, belief in (("model", self.model), ("user", self.user), ("market", self.market)):
            if belief is not None and belief.owner != slot:
                raise ValueError(f"the '{slot}' slot holds a belief owned by '{belief.owner}'")
        return self
