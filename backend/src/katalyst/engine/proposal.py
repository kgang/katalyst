"""What the model is allowed to hand back. One answer, one thing in it.

A language model writes most of the map. It is useful at *proposing* a claim and
the arrow that reaches it, and unreliable at deciding whether the result is a
legal map. So the shapes in this file are deliberately small: they are the whole
of what a model may say to us, and everything they leave out is something our own
code decides afterwards.

Three things a model cannot do here, because the fields do not exist
--------------------------------------------------------------------
1. **It cannot make up an identifier.** No shape below carries one. A new claim's
   identifier is minted by `engine/ids.py` the moment we accept it; an existing
   claim is pointed at by an identifier this call's own map already listed.
2. **It cannot say where its numbers came from.** That is a receipt about what
   our pipeline actually did — it searched, or it did not, and something came
   back, or nothing did — and `expand.py` writes it from what happened.
3. **It cannot return more than one thing.** One answer is one new claim with the
   one arrow that reaches it, or one arrow between two claims already on the map,
   or the sentence "there is nothing more here". Never a list, never a map.

Three more absences follow from the same principle. An arrow draft has no way to
say it is a market feeding back on the world, so a generated map holds none of
those and an arrow that closes a loop is refused rather than legalised. A claim
proposal has no slot for published items for and against, because two of the four
things such an item carries are numbers nobody elicited. And nothing here names
whose a number is, so the model's, the person's and a market's stay ours to keep
apart.

Why these are shapes and not requests in a prompt
-------------------------------------------------
A prompt asking politely for one claim at a time gets one claim at a time until
the day it does not. A shape with no second slot cannot be filled with two
claims on any day. The rules that a shape cannot carry — a claim nobody can
check, an arrow that closes a loop, a map that ends nowhere — are checked by
`katalyst.domain`, over the map the proposal would leave behind, and a proposal
that breaks one comes back with every reason at once and is never patched up.

**If you find yourself writing a check that the model did not do one of the
three, the shape is wrong.** A check for a field that does not exist is a sign
the field crept back.

What this file must never do
----------------------------
- Never gain a field for an identifier, for where a number came from, for whose
  a number is, or for a second claim. Each of the four is the whole point.
- Never hold arithmetic, a network call, or a rule about whether a map is legal.
  It is a set of shapes.
- Never import from `katalyst.api`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from katalyst.domain import BaseRate, Payoff, Resolution


class Ranged(BaseModel):
    """A likelihood and the range around it, with nobody's name on it.

    The model gives three numbers and no owner, because whose number this is is a
    fact about our pipeline: every likelihood a proposal carries is stamped as
    the model's own by us on the way in.

    The two ends are the tenth and ninetieth of a hundred: if this claim were
    settled a hundred times over, nine in ten of the answers would sit between
    them. They say how sure the number is, not how much the world can move.

    This shape must never grow a field for whose number it is. The moment it has
    one, a model can hand us a number wearing the person's name on it.
    """

    model_config = ConfigDict(frozen=True)

    p: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How likely this claim is to come out true, from 0 (certainly not) to "
            "1 (certainly yes), before anything on the map pushes it."
        ),
    )
    lo: float = Field(
        ge=0.0,
        le=1.0,
        description="The bottom of the honest range around that number. Never above it.",
    )
    hi: float = Field(
        ge=0.0,
        le=1.0,
        description="The top of the honest range around that number. Never below it.",
    )

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Ranged":
        """Check that the three numbers really are a range around a number.

        Checked here, in the shape, rather than later: an answer whose low end
        sits above its high end did not fit the shape this call asked for, and
        that is one plainly named outcome rather than a second kind of fault.

        Returns:
            This same triple, once the order has been checked.

        Raises:
            ValueError: If the three numbers are not in order.
        """
        if not (self.lo <= self.p <= self.hi):
            raise ValueError(
                "a range must satisfy low <= likelihood <= high; got "
                f"low={self.lo}, likelihood={self.p}, high={self.hi}"
            )
        return self


class SourceDraft(BaseModel):
    """An address the model says backs an arrow, before we have checked it.

    It is a *claim about a document*, not a document. Our code decides whether it
    becomes something a reader can open, and it does so only if the search tool
    itself returned that address in the same call.

    There is deliberately no field for the day it was fetched. That day is the
    day *our* retrieval step fetched something, which is a fact about us, so a
    model must have no way to write it.
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(
        description=(
            "One address that opens, not a search query, and one the search tool "
            "returned to you in this call rather than one you are recalling."
        )
    )
    title: str = Field(
        description="What a reader sees on arriving, in the publisher's words, not yours."
    )


class LinkDraft(BaseModel):
    """The arrow itself: how hard it pushes, how long it takes, and why it is real.

    An arrow is an argument, never a correlation, so a mechanism in plain words
    is required of every one. What is absent is as deliberate as what is here:
    no identifier, and nothing saying how well-backed the arrow is. The second is
    a fact about what our pipeline found, not a claim a model may make about
    itself.

    The two spans of time here are whole days. A model is asked for two days, not
    for two and a half; the arrow it becomes allows the half day, because
    arithmetic on a timeline needs it, and the widening happens on the way in.
    """

    model_config = ConfigDict(frozen=True)

    mode: Literal["trigger", "sustain"] = Field(
        description=(
            "How the push behaves when the cause goes away. 'trigger': a one-time "
            "shove — once the cause becomes true the effect is pushed and stays "
            "pushed, fading on its own; undoing the cause later does not undo it. "
            "'sustain': a continuous hold — the push exists only while the cause "
            "holds, and vanishes the moment it stops."
        )
    )
    strength: float = Field(
        description=(
            "How far this arrow shifts the effect's odds while the push is at full "
            "size, on the scale where separate pushes add up instead of "
            "multiplying. Signed: positive makes the effect more likely to be "
            "true, negative less likely. Roughly: +1 triples the odds, -1 cuts "
            "them to a third. This is not a probability."
        )
    )
    lag: int = Field(
        description=(
            "Whole days from the cause becoming true to the push reaching full "
            "size. 0 means the same day."
        )
    )
    shape: Literal["impulse", "step", "ramp"] = Field(
        description=(
            "What the push does over time. 'impulse': nothing during the delay, "
            "then a spike that fades. 'step': nothing during the delay, then full "
            "size, held. 'ramp': climbs from nothing to full size across the "
            "delay, then held."
        )
    )
    half_life: int | None = Field(
        default=None,
        description=(
            "Whole days for a spike to fall to half its size. Belongs to a spike "
            "and to nothing else: a step and a ramp switch on and hold, so they "
            "have nothing to fade."
        ),
    )
    rationale: str = Field(
        description=(
            "The mechanism in one to three plain sentences: why this cause moves "
            "this effect. An arrow with a number and no reason is worth nothing to "
            "the person reading it."
        )
    )
    sources: tuple[SourceDraft, ...] = Field(
        default=(),
        description=(
            "Addresses this call's search tool returned that back the mechanism "
            "above. Leave it empty when you did not search or found nothing — an "
            "empty list is an honest answer we can show, and an address you are "
            "recalling rather than reading is not."
        ),
    )


class ClaimProposal(BaseModel):
    """One new claim, and the one arrow that reaches it from a claim already there.

    The ordinary answer while a map is growing. The pair travels together because
    a claim with nothing causing it is not a step in a story, and an arrow with
    nothing at its far end is not an argument. That is still one thing: one
    question, one answer.

    A claim is something that will be plainly true or false by a date, settled by
    a named source. Never a mood ("tensions ease"); always a check ("at least 14
    consecutive days of unrestricted commercial transit through the Strait of
    Hormuz per Lloyd's List, by 2026-11-01").
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["claim"] = Field(
        description="Says this answer is a new claim with the arrow that reaches it."
    )
    claim: str = Field(
        description=(
            "The claim in one sentence, as a person would say it out loud. The "
            "precise, settleable version goes in the test below."
        )
    )
    claim_kind: Literal["event", "market", "not_tradeable"] = Field(
        description=(
            "What this claim is for. 'event': a step in the middle of the story. "
            "'market': an ending that names something you could trade. "
            "'not_tradeable': an ending that names why there is nothing to trade."
        )
    )
    resolution: Resolution = Field(
        description="How this claim gets settled, by whom, and by when. All three required."
    )
    prior: Ranged = Field(
        description=(
            "How likely this claim is before anything on the map pushes it, with "
            "the honest range around it."
        )
    )
    base_rate: BaseRate | None = Field(
        default=None,
        description=(
            "How often this kind of thing has happened before: how many cases out "
            "of how many, and what set was counted. Leave it out when there is no "
            "honest set to count — absent is better than invented."
        ),
    )
    payoff: Payoff | None = Field(
        default=None,
        description=(
            "What you would trade. Belongs to a 'market' ending: either a named "
            "contract at a named venue and which side you would take, or an "
            "instrument, a direction, and how far its price would move."
        ),
    )
    not_tradeable_reason: str | None = Field(
        default=None,
        description=(
            "Why this chain ends with nothing to trade, in one plain sentence. "
            "Belongs to a 'not_tradeable' ending."
        ),
    )
    cause: str = Field(
        description=(
            "The claim this arrow starts at, named by one of the short names this "
            "call's map listed. It is a claim already on the map; nothing new is "
            "named here, and nothing new is named anywhere else either."
        )
    )
    link: LinkDraft = Field(description="The arrow from that cause into the new claim above.")


class LinkProposal(BaseModel):
    """One arrow between two claims that are both already on the map.

    The answer when the missing piece is not a new step but a connection between
    two steps that are already there.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["link"] = Field(
        description="Says this answer is an arrow between two claims already on the map."
    )
    source: str = Field(description="The cause: one of the short names this call's map listed.")
    target: str = Field(
        description="The effect: another of the short names this call's map listed."
    )
    link: LinkDraft = Field(description="The arrow from that cause to that effect.")


class Stop(BaseModel):
    """The answer that says this part of the story is finished.

    Not a failure and not an error. A chain that has reached somewhere you could
    act on, or a step with nothing honest to hang off it, is done — and saying so
    is more useful than inventing one more box.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["stop"] = Field(description="Says there is nothing more to add here.")
    why: str = Field(
        description=(
            "One plain sentence saying why this part of the story is finished. It "
            "is kept and shown, so write it for a person."
        )
    )


Proposal = Annotated[ClaimProposal | LinkProposal | Stop, Field(discriminator="kind")]
"""The whole of what a model may answer with: one of exactly three things.

Read the `kind` field to know which, rather than guessing from which other fields
happen to be filled in — the same way the six edits and the two payoffs are
already told apart. There is no fourth shape and no way to combine two, which is
what makes "one call, one proposal" a fact about the program rather than a
request in a prompt.
"""


class StartingClaim(BaseModel):
    """One sentence a person typed, turned into a claim that can be checked.

    Used twice at most in a run: for the claim the map starts from, and for the
    place the person asked whether it gets to. It carries no cause and no arrow,
    because neither claim has anything before it yet; and it carries no kind,
    because neither is an ending.

    The claim the map starts from enters as exactly that, and a map has exactly
    one, so the model is never asked which. The destination enters as a step in
    the middle, because a destination is where a person wants the story to *get
    to*, not where it *ends*: an ending that names a trade names a venue and a
    contract, which is a fact about a venue nobody has looked up yet, and the map
    must still run on to an ending of its own.

    It must never carry an identifier, a word for where its numbers came from, or
    whose they are, for the same reasons a proposal must not.
    """

    model_config = ConfigDict(frozen=True)

    claim: str = Field(
        description=(
            "The claim in one sentence, as a person would say it out loud. Keep "
            "their meaning: do not make it more modest or more dramatic than they "
            "did."
        )
    )
    resolution: Resolution = Field(
        description="How this claim gets settled, by whom, and by when. All three required."
    )
    prior: Ranged = Field(
        description=(
            "How likely this claim is before anything on the map pushes it, with "
            "the honest range around it."
        )
    )
    base_rate: BaseRate | None = Field(
        default=None,
        description=(
            "How often this kind of thing has happened before, when there is an "
            "honest set of past cases to count. Leave it out when there is not."
        ),
    )
