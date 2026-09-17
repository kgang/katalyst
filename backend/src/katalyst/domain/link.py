"""A link: the arrow that says why one claim makes another more, or less, likely.

A link is one causal claim, and it is an argument rather than a correlation. It
must say why it thinks the mechanism is real, how hard it pushes, how long the
push takes to arrive, what the push looks like over time, and whether the push
survives its cause going away.

Both classes here are frozen — once built, an instance cannot be changed. A
change is a new instance, recorded as an intervention on a branch.

A warning about the word *source*, which does three different jobs nearby.
`Link.source` is the **cause**: the claim an arrow starts at. `Link.sources` is
the **citations** backing that arrow, and `Source` is the type of one of them.
(`Resolution.source` in `proposition.py` is a fourth thing, the adjudicator who
settles a claim, and it never appears in this file.)

No arithmetic happens here. Nothing in this layer yet evaluates a shape, adds a
strength, or moves a likelihood. These fields are defined now, with their
meanings pinned down, so that the code that works the numbers through fits
shapes that already exist.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.ids import LinkId, PropositionId

Days = float
"""A span of time measured in days.

1.0 is one day, 0.5 is twelve hours, 14.0 is a fortnight. A plain number rather
than a duration written as text (the style that writes a fortnight as "P14D"),
because such a duration crosses to the browser as a string, and nobody can do
timing arithmetic on a string.
"""

Provenance = Literal[
    "asserted", "argued", "documented", "market_implied", "user", "historical", "simulated"
]
"""Where a number or a link came from, as a fact about our own pipeline.

Set from what actually happened, never declared by the model. `asserted`: the
model gave a link with no mechanism worth the name and no sources. `argued`: it
stated a mechanism, and nothing was retrieved to back it. `documented`: the
retrieval step attached at least one real source. `market_implied`: the number
was read off a live price. `historical`: the number came from a study of past
cases. `user`: a person typed it. `simulated`: a probe produced it.
"""


class Source(BaseModel):
    """Something a reader can open to check what we are claiming.

    A source exists because our retrieval step actually fetched a document, or
    because a person typed one in. It is never something the model reports having
    read. A source is never invented to make a link look better than it is.
    """

    model_config = ConfigDict(frozen=True)

    # Open question 2 in spec/graph/link.md: these three fields are a proposal.
    # Does a source also need a publisher, a quoted snippet, or an access date
    # separate from the day we fetched it?
    url: str = Field(
        description=(
            "Where the reader goes to check it. One address that opens, not a search query."
        )
    )
    title: str = Field(
        description=(
            "What the reader will see when they get there, in the publisher's words, not ours."
        )
    )
    retrieved: date | None = Field(
        default=None,
        description=(
            "The day our retrieval step fetched it. None when a person supplied the source by hand."
        ),
    )


class Link(BaseModel):
    """A causal claim from one proposition to another: A makes B more, or less, likely.

    A link is an argument, not a correlation. It must say why it thinks the
    mechanism is real (`rationale`), how hard it pushes (`strength`), how long the
    push takes to arrive (`lag`), what the push looks like over time (`shape`),
    and whether the push survives its cause going away (`mode`).

    A link records where its number came from and nothing about how sure the model
    is of its own mechanism: the sentence in `rationale` is the model's argument,
    and `provenance` is our receipt for it. A link must never carry a number
    without a reason. A link with no rationale, or one claiming evidence it does
    not cite, is rejected with a message — never quietly patched up. Those two
    checks belong to the map's validity rules, not to this class, because a
    well-formed model proposal breaks them often and the user has to be told which
    arrow it was.
    """

    model_config = ConfigDict(frozen=True)

    id: LinkId = Field(description="Minted by our code, never by the model.")
    source: PropositionId = Field(
        description=(
            "The cause. The proposition this arrow starts at. Must name a "
            "proposition in the same graph."
        )
    )
    target: PropositionId = Field(
        description=(
            "The effect. The proposition this arrow ends at. Must name a "
            "proposition in the same graph."
        )
    )

    mode: Literal["trigger", "sustain"] = Field(
        description=(
            "How the push behaves when the cause goes away. 'trigger': a one-time shove — once the "
            "cause becomes true the effect is pushed and stays pushed, fading on its own; undoing "
            "the cause later does not undo it (a toppled domino). 'sustain': a continuous hold — "
            "the push exists only while the cause holds, and vanishes the moment it stops (an "
            "apple on a desk)."
        )
    )
    # Open question 6 in spec/graph/link.md: strength has no sanity ceiling, so a
    # model that writes 12 has asserted certainty while looking like it gave a
    # number.
    strength: float = Field(
        description=(
            "How far this link shifts the target's log-odds while the push is at full size. "
            "Signed: positive makes the target claim more likely to be TRUE, negative less likely. "
            "Log-odds is the scale on which separate pushes add up instead of multiplying. This is "
            "not a probability and is not capped at 1. Roughly: +1 triples the odds, -1 cuts "
            "them to a third."
        )
    )
    lag: Days = Field(
        description=(
            "Days from the cause becoming true to the push reaching full size. 0.0 means the same "
            "day. Must be greater than 0 when `reflexive` is true."
        )
    )
    shape: Literal["impulse", "step", "ramp"] = Field(
        description=(
            "What the push does over time. 'impulse': nothing during the lag, then a spike that "
            "decays by `half_life`. 'step': nothing during the lag, then full size, held. 'ramp': "
            "climbs from nothing to full size across the lag, then held."
        )
    )
    # Open question 4 in spec/graph/link.md: no rule yet says a half-life belongs
    # only on an 'impulse' link, so a 'step' link carrying one is accepted and the
    # field ignored.
    half_life: Days | None = Field(
        default=None,
        description=(
            "Days for an 'impulse' push to fall to half its size. Meaningful only when `shape` is "
            "'impulse'; None for 'step' and 'ramp'."
        ),
    )

    rationale: str = Field(
        description=(
            "The mechanism in one to three plain sentences: why this cause moves this effect. "
            "Required on every link. An empty rationale is a violation, not a default."
        )
    )
    sources: tuple[Source, ...] = Field(
        default=(),
        description=(
            "What backs the link. At least one is required when `provenance` claims evidence — "
            "'documented', 'historical' or 'market_implied'."
        ),
    )
    provenance: Provenance = Field(
        description=(
            "Where this link and its number came from, as a fact about our pipeline. Set from what "
            "actually happened; the model never fills this in."
        )
    )
    reflexive: bool = Field(
        default=False,
        description=(
            "True when this arrow is a market feeding back on the world — a price outcome changing "
            "what people do. A reflexive link is allowed to close a loop, and must have a lag "
            "greater than 0."
        ),
    )
