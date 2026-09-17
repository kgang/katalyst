"""What one call leaves behind, in our own words, and every limit a run has.

The bottom of the pipeline. Everything else in this layer reads these shapes and
nothing here reads anything else of ours except the map's own types and the
shapes a model may answer with — so a reader can start here and work outward.

Two halves, and the line between them is the seam
-------------------------------------------------
**`Said` is a question's answer, translated.** The library we call the model with
has its own types for a reply, and exactly one module — `client.py` — ever names
them. It hands back one of these instead: what was answered, what the search tool
returned, whether the model declined, and what the call cost. Everything past
that point works in our words, which is what lets the rest of the pipeline be
tested with no key, no network and no library.

**`Outcome` is what our own code then decided.** Three things can happen to a
proposal and nothing else can: it is accepted and minted, it is refused with
every reason at once, or the model says this part of the story is finished.

What this file must never do
----------------------------
- Never name a type from the library we call the model with. That is `client.py`'s
  job alone, and a test reads this layer's source to keep it so.
- Never hold arithmetic, a network call, or a rule about whether a map is legal.
  It is a set of shapes.
- Never import from anything else in this layer. It is the bottom.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Link, Proposition, PropositionId, Violation
from katalyst.engine.proposal import Proposal, StartingClaim

# --- What a question came back with -----------------------------------------


class FoundPage(BaseModel):
    """One page the search tool itself returned during a call.

    Not a page the model mentioned, and not a page anybody went looking for after
    the fact: one the tool handed back, in the order it handed it back. The
    difference is the whole of how an arrow earns the word `documented`.

    It carries no day. The day is a fact about the run rather than about the page,
    so it is stamped on in `grounding.py` where a source is built.
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(description="Where the page is. One address that opens.")
    title: str = Field(description="What a reader sees on arriving, in the publisher's words.")


class Said(BaseModel):
    """One question's answer, translated out of the library's types into ours.

    Three fields carry what happened and six carry what it cost. They are kept
    apart on purpose: **what the model wrote and what the search returned arrive
    in two different fields**, so no code downstream could mistake one for the
    other, which is the mistake the whole grounding rule exists to prevent.

    `calls` counts round trips rather than questions. A question whose answer came
    back part finished is sent straight back to be continued, and each trip is on
    the bill.
    """

    model_config = ConfigDict(frozen=True)

    answered: Proposal | StartingClaim | None = Field(
        default=None,
        description=(
            "What the model answered with, already checked against the shape the "
            "call asked for. Nothing at all when it declined, or when it wrote "
            "nothing we could read."
        ),
    )
    found: tuple[FoundPage, ...] = Field(
        default=(),
        description=(
            "What the search tool returned during this call, in the order it "
            "returned it. Never anything the model typed."
        ),
    )
    declined: str | None = Field(
        default=None,
        description=(
            "One plain sentence, when the vendor's own safety check turned the "
            "call down. Nothing at all otherwise. A refusal is shown to the "
            "person, never hidden and never quietly re-routed."
        ),
    )
    calls: int = Field(default=1, description="How many round trips this question took.")
    searches: int = Field(default=0, description="How many web searches it ran.")
    input_tokens: int = Field(default=0, description="Tokens of question read fresh.")
    output_tokens: int = Field(default=0, description="Tokens of answer written.")
    cache_read_tokens: int = Field(default=0, description="Tokens recognised from an earlier call.")
    cache_write_tokens: int = Field(default=0, description="Tokens written into the cache.")


# --- What our own code decided ----------------------------------------------


class Accepted(BaseModel):
    """A proposal that passed every rule, with the identifiers we minted for it."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["accepted"] = "accepted"
    proposition: Proposition | None = Field(
        default=None,
        description=(
            "The new claim, with the identifier we minted for it. Nothing at all "
            "when the answer was an arrow between two claims already on the map."
        ),
    )
    links: tuple[Link, ...] = Field(
        default=(),
        description=(
            "The arrows that arrived with it, each with an identifier we minted "
            "and a word for where it came from that we wrote."
        ),
    )
    sources_dropped: tuple[str, ...] = Field(
        default=(),
        description=(
            "Addresses the answer cited that the search tool never returned in "
            "that call. They are not behind anything, and this is where a reader "
            "is told so."
        ),
    )


class Refused(BaseModel):
    """A proposal that did not become part of the map, and every reason why.

    Three different things arrive this way, and the list of violations tells them
    apart. A proposal the map's own rules turned down carries those rules' own
    sentences. A call the model declined to answer, and an answer that did not fit
    the shape we asked for, carry **no** violations — there is no fault in a map to
    name, because no map was proposed — and the plain sentence of what happened is
    in `claim_in_words` instead.

    A refusal is an event a person sees, not an error they are spared. A
    generation that hides its misses has deleted half the product.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["refused"] = "refused"
    claim_in_words: str = Field(
        description=(
            "What the model wrote, or the plain sentence of what happened when it "
            "wrote nothing we could read. Never minted, never drawn as a tile."
        )
    )
    violations: tuple[Violation, ...] = Field(
        default=(),
        description=(
            "Everything the map's own rules found wrong with the map this answer "
            "would have left behind, in their words. Empty when no map was "
            "proposed at all."
        ),
    )


class Stopped(BaseModel):
    """The model has nothing more to add on this line.

    Not a failure. It is the ordinary way a line ends, it is kept in the
    transcript, and it puts no event on the wire: nothing changed on the map.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["stopped"] = "stopped"
    why: str = Field(
        description="One plain sentence saying why this part of the story is finished."
    )


class Outcome(BaseModel):
    """What one call to the model left behind: what happened, and what it cost.

    The counters are what `receipt.py` folds into the run's one receipt, and what
    the spending cap is checked against after every call. **An outcome must never
    be thrown away**: a call that cost money and is not counted is money the
    receipt cannot account for.
    """

    model_config = ConfigDict(frozen=True)

    result: Accepted | Refused | Stopped = Field(discriminator="kind")
    about: PropositionId | None = Field(
        default=None,
        description=(
            "The claim this call was asking about, so a reader can follow a "
            "refusal back to the question that produced it. Nothing at all on the "
            "two calls that turn a person's own sentences into claims."
        ),
    )
    frontier: tuple[PropositionId, ...] = Field(
        default=(),
        description=(
            "The claims still open to expand once this answer had been folded in. "
            "Filled by the walk, which is the only thing that knows it, and read "
            "by whatever draws the map: no answer ever says 'this claim is now "
            "closed', so a claim leaving this list is how a reader learns it."
        ),
    )
    calls: int = Field(default=1, description="How many round trips this question took.")
    searches: int = Field(default=0, description="How many web searches it ran.")
    input_tokens: int = Field(default=0, description="Tokens of question read fresh.")
    output_tokens: int = Field(default=0, description="Tokens of answer written.")
    cache_read_tokens: int = Field(default=0, description="Tokens recognised from an earlier call.")
    cache_write_tokens: int = Field(default=0, description="Tokens written into the cache.")


def costing(
    result: Accepted | Refused | Stopped, about: PropositionId | None, said: Said
) -> Outcome:
    """Put what happened and what the call cost together into one outcome.

    Args:
        result: What our own code decided about the answer.
        about: The claim the call was asking about, if it was asking about one.
        said: The answer, for its counters.

    Returns:
        One outcome, ready to be folded into the run's receipt.
    """
    return Outcome(
        result=result,
        about=about,
        calls=said.calls,
        searches=said.searches,
        input_tokens=said.input_tokens,
        output_tokens=said.output_tokens,
        cache_read_tokens=said.cache_read_tokens,
        cache_write_tokens=said.cache_write_tokens,
    )


# --- Every limit a run has --------------------------------------------------


class Caps(BaseModel):
    """Every limit a run has, in one place, each with a default and a reason.

    They are arguments rather than constants so that a test can set them low, an
    evaluation can set them where the measurement wants them, and nobody has to
    read a function body to find out what stopped a run.
    """

    model_config = ConfigDict(frozen=True)

    depth: int = Field(default=5, description="How many layers a line may run from the hypothesis.")
    width: int = Field(default=3, description="How many arrows may leave one claim.")
    claims: int = Field(default=30, description="How large the map may get.")
    refusals_in_a_row: int = Field(
        default=3,
        description=(
            "How many proposals for one claim may fail before that claim is "
            "closed. Anything that is not an accepted proposal counts: a rejection "
            "by the map's rules, a refusal by the vendor, an answer that did not "
            "fit the shape. One rule, not three."
        ),
    )
    at_once: int = Field(default=3, description="How many lines are expanded at the same time.")
    searches: int = Field(
        default=30,
        description=(
            "How many web searches the whole run may make. It is the claims cap: "
            "one search's worth of budget for each claim the map is allowed to "
            "hold, so it adds no new number to the product. Reaching it turns "
            "searching off; it never ends the run."
        ),
    )
    dollars: float = Field(
        default=15.0, description="What one run may spend before it stops (Kent, 2026-09-17)."
    )
