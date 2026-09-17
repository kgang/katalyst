"""A proposition: a claim that will be true or false by a date, judged by a named source.

A thesis usually lives in a sentence — "if Hormuz opens, oil falls". You cannot
check a sentence, you cannot put a number on it, and you certainly cannot trade
it. A proposition is the unit that fixes this: a claim that will be true or false
by a date, judged by a named source.

Everything else on the map is built on that promise. A likelihood means something
because someone will eventually settle the claim; a chain of claims can end in an
instrument because the last claim names one; and a map can be audited because
every box in it is a bet somebody could win or lose.

Every class here is frozen — once built, an instance cannot be changed. A change
to a proposition is never an edit; it is an intervention recorded on a branch.
Every collection is a tuple rather than a list, because a frozen object holding a
list is only half frozen. Every field carries a plain-words description rather
than a comment, for one reason: descriptions travel into the types generated for
the browser, so the same sentence explains the field in Python and in TypeScript.

Some rules about a proposition are checked here, when the object is built, and
some are checked later over the whole map. The line between them: a rule only our
own code could break raises an exception at construction; a rule a well-formed
model proposal could plausibly break comes back as a violation carrying a plain
sentence the user reads. That is why a `market` claim with no payoff can be built
but cannot be valid.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.ids import PropositionId


class Resolution(BaseModel):
    """How a claim gets settled: the test, who applies it, and by when.

    Every proposition has one. A claim with no resolution is a vibe, and a
    likelihood attached to a vibe can never be scored, right or wrong.
    """

    model_config = ConfigDict(frozen=True)

    criteria: str = Field(
        description=(
            "The test, written so that two people reading it would agree on the "
            "answer. 'At least 14 consecutive days of unrestricted commercial "
            "transit', not 'shipping returns to normal'."
        )
    )
    source: str = Field(
        description=(
            "Who or what applies the test: a named publication, exchange, agency "
            "or venue. 'Lloyd's List transit counts', not 'the news'."
        )
    )
    by: date = Field(
        description=(
            "The date by which the test has been applied. After this date the "
            "claim is true or false — never still open."
        )
    )


class BaseRate(BaseModel):
    """How often this kind of thing has happened before: k times out of n.

    The outside view — the anchor a likelihood starts from before anything
    specific to this case is considered. Optional, because some claims have no
    honest reference class, and absent is better than invented.
    """

    model_config = ConfigDict(frozen=True)

    reference_class: str = Field(
        description=(
            "The set of past cases being counted, stated precisely enough that "
            "someone else could recount them: 'Hormuz closure or disruption "
            "episodes since 1980 that ended within 90 days'."
        )
    )
    k: int = Field(ge=0, description="How many cases in that set came out true.")
    n: int = Field(gt=0, description="How many cases are in that set altogether.")
    # Open question 3 in spec/graph/proposition.md: these are plain web addresses
    # while a link's citations are a `Source` record with a title and a date. If
    # `Source` stays, does this field adopt it?
    sources: tuple[str, ...] = Field(
        default=(),
        description=(
            "Web addresses where the count can be checked. Empty means the count "
            "is the model's own recollection, and nothing downstream of it may "
            "claim to be documented."
        ),
    )

    @model_validator(mode="after")
    def _k_within_n(self) -> "BaseRate":
        """Check that the count of true cases is not larger than the set it is drawn from.

        You cannot count 7 cases out of 5.

        Returns:
            This same base rate, once the two counts have been checked.

        Raises:
            ValueError: If k is larger than n.
        """
        if self.k > self.n:
            raise ValueError(
                f"a base rate counts {self.k} cases out of {self.n}; k must not exceed n"
            )
        return self


class Evidence(BaseModel):
    """One published item that supports or undercuts a claim.

    Evidence moves no number by itself in this version. It is what the Inspector —
    the persistent side panel beside the canvas — shows when the user asks why a
    likelihood is what it is, and it is what lets the panel say "two for, one
    against" without re-reading the sources.
    """

    model_config = ConfigDict(frozen=True)

    claim: str = Field(description="What the source says, in one sentence, in our words.")
    # Open question 3 in spec/graph/proposition.md: a plain web address here,
    # while a link's citations carry a title and a date fetched as well.
    url: str = Field(description="Where to read it, so the reader can check us.")
    direction: Literal[1, -1] = Field(
        description=(
            "1 if this supports the proposition, -1 if it cuts against it. There "
            "is no 0: an item that points neither way is not attached at all."
        )
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How much this item counts, from 0 (barely) to 1 (decisive). Elicited "
            "and unitless; shown as a bar, never as a decimal."
        ),
    )


class Payoff(BaseModel):
    """What a `market` terminal is actually worth: instrument, side, size of move.

    This is what makes a terminal tradeable rather than merely interesting.
    """

    model_config = ConfigDict(frozen=True)

    # Open question 2 in spec/graph/proposition.md: a payoff names an instrument
    # but not the venue that quotes it.
    instrument: str = Field(
        description=(
            "The thing you would buy or sell, named the way its venue names it: "
            "a Polymarket contract title, a ticker, a futures contract."
        )
    )
    direction: Literal["long", "short"] = Field(
        description=(
            "'long' if the position makes money when the claim comes true, "
            "'short' if it makes money when the claim fails."
        )
    )
    # Open question 1 in spec/graph/proposition.md: is this a move in the
    # instrument's price, a return on the position, or a size of position? The
    # description below takes the first reading; the question is still open.
    magnitude: float = Field(
        ge=0.0,
        description=(
            "How far the instrument is expected to move if the claim resolves "
            "true, as a fraction: 0.03 means three per cent. The side is carried "
            "by `direction`, so this number is never negative."
        ),
    )


class Proposition(BaseModel):
    """A claim that will be true or false by a date, judged by a named source.

    The unit the whole map is built from. Never a vibe ("tensions ease"); always
    a check ("at least 14 consecutive days of unrestricted commercial transit
    through the Strait of Hormuz per Lloyd's List, by 2026-11-01").

    Frozen. A proposition is never edited in place; a change to one is an
    intervention recorded on a branch.
    """

    model_config = ConfigDict(frozen=True)

    id: PropositionId = Field(
        description=(
            "This proposition's identifier, minted by our code before the proposition is built."
        )
    )
    claim: str = Field(
        description=(
            "The claim in one sentence, as a person would say it out loud. The "
            "precise, settleable version lives in `resolution.criteria`."
        )
    )
    kind: Literal["hypothesis", "event", "market", "not_tradeable"] = Field(
        description=(
            "What this proposition is for: `hypothesis` is the user's root input, "
            "`event` a step in the middle, `market` an ending that names an "
            "instrument, `not_tradeable` an ending that names why there is none."
        )
    )
    resolution: Resolution = Field(description="How and when this claim gets settled, and by whom.")
    prior: Belief = Field(
        description=(
            "The model's likelihood for this claim before its causes are taken "
            "into account. Always owned by `model`."
        )
    )
    beliefs: Beliefs = Field(
        description=(
            "The three likelihoods shown side by side: the model's (causes taken "
            "into account), the user's, and the market's. Never merged."
        )
    )
    base_rate: BaseRate | None = Field(
        default=None,
        description=(
            "How often this kind of thing has happened before, when there is an "
            "honest reference class. None means there is not one."
        ),
    )
    evidence: tuple[Evidence, ...] = Field(
        default=(),
        description=(
            "Published items for and against, each with a direction and a weight. "
            "Empty is honest; invented sources are not."
        ),
    )
    payoff: Payoff | None = Field(
        default=None,
        description=(
            "What you would trade. Required when `kind` is `market` — required by "
            "the map's validity rules, not by this class."
        ),
    )
    not_tradeable_reason: str | None = Field(
        default=None,
        description=(
            "Why this chain ends without an instrument, in one plain sentence. "
            "Required when `kind` is `not_tradeable` — again by the validity rules."
        ),
    )

    @model_validator(mode="after")
    def _prior_is_the_models(self) -> "Proposition":
        """Check that the prior is the model's own number.

        The engine builds this belief, so any other owner is a bug in our own
        code rather than something a model proposal could do to us.

        Returns:
            This same proposition, once the prior's owner has been checked.

        Raises:
            ValueError: If the prior is owned by anyone but the model.
        """
        if self.prior.owner != "model":
            raise ValueError(
                f"a proposition's prior must be owned by 'model'; got '{self.prior.owner}'"
            )
        return self
