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

    def _as_written(self) -> tuple[str, str, str]:
        """Give this belief's three numbers the way the product writes a likelihood.

        Two significant figures, in the order low, likelihood, high. Nothing that
        reaches a reader — a chip on the canvas, a sentence in a refusal, the body
        of a rejected request — quotes a likelihood at the precision a computer
        happens to hold it at, because `0.30000000000000004` is not a number
        anybody wrote or could act on.

        **A number outside 0 to 1 is said to be outside 0 to 1**, and is not put
        through the likelihood rule. The fields on this class cannot hold such a
        number, but the rule in `domain/validity.py` that re-checks a map which
        arrived some other way can meet one, and it reports the fault in words
        this method writes. The likelihood rule answers `>.99` for 1.4 and `<.01`
        for -0.3, and either word inside a sentence saying the number is out of
        range would tell the reader the opposite of the truth.

        The likelihood rule itself lives in `domain/diff.py`, which is where the
        sentences beside a change list are written. It is fetched when it is needed
        rather than at the top of this file: that module reads whole maps, and
        reading a map needs this one, so naming it up here would leave the two
        modules waiting on each other before either had finished loading.

        Returns:
            The low, the likelihood and the high, each as text.
        """
        from katalyst.domain.diff import _two_figures

        def written(number: float) -> str:
            return _two_figures(number) if 0.0 <= number <= 1.0 else "outside 0 to 1"

        return written(self.lo), written(self.p), written(self.hi)

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Belief":
        """Check that low is at most the likelihood, which is at most high.

        The field bounds above already cover 0 and 1; this covers the order. So by
        the time this runs all three numbers are real likelihoods, and the sentence
        it raises can write them the way the product writes every likelihood.

        Returns:
            This same belief, once the order has been checked.

        Raises:
            ValueError: If the three numbers are not in order.
        """
        if not (self.lo <= self.p <= self.hi):
            low, likelihood, high = self._as_written()
            raise ValueError(
                "a belief must satisfy low <= likelihood <= high; got "
                f"low={low}, likelihood={likelihood}, high={high}"
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
