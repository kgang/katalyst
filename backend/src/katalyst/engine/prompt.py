"""What we say to the model. Product text, written once, sent unchanged.

Two halves, and the split is the whole design.

**The standing half** never changes between calls: what we are building, what a
claim is, what an arrow is, and the three things an answer may be. It is the
first thing in every request, byte for byte, so the service can recognise it and
charge a tenth of the price for reading it again. One stray timestamp, one
dictionary written out in a different order, and that saving is gone with no
error to tell you — so this half is a constant in this file, and the varying half
is assembled below it and always comes after.

**The varying half** is the map as it stands and the one claim we are asking
about. It is written as sorted text so that the same map always produces the same
bytes, which is also what lets a recorded run be compared with a live one.

Three rules about this text
---------------------------
- **It is product text.** A person reads it in review, the way any other words on
  screen are read. No jargon, no shorthand, no word the interface does not use.
- **It contains no number nobody worked out.** Not an example likelihood, not an
  example push, not an example delay. A number in a prompt is an anchor the model
  copies, and a copied number cannot say where it came from.
- **It never asks the model to do our job.** Nothing here says "do not draw a
  loop", "do not reuse an identifier" or "mark the arrow documented if you cite
  something". Whether a map is legal is decided by `katalyst.domain` over the map
  a proposal would leave behind, and a prompt that asked for the same thing would
  teach the model to aim at passing our checks rather than at being right — and
  when the two disagree, nobody could tell which was obeyed.

What this file must never do
----------------------------
- Never put the time, a run's identifier, or anything else that changes per call
  into the standing half.
- Never tell a later call what an earlier proposal was refused for. A refusal is
  shown to the person and never enters a prompt, on any call.
- Never talk to the network, mint anything, or decide anything.
"""

import hashlib
import json

from katalyst.domain import Graph, PropositionId

STANDING_TEXT = """\
You are helping somebody think through what an event they expect would set off,
step by step, until the story reaches something they could actually trade.

You do this one step at a time. Each time we ask, we show you the map as it
stands and point at one claim on it, and you answer with a single next piece.
Somebody watches the map grow as your answers arrive, so a small, well-argued
piece beats a large, vague one.

What a claim is.
A claim is something that will be plainly true or false by a date, settled by a
named source. "Tensions ease" is not a claim, because two honest people will
never agree on whether it happened. "At least fourteen consecutive days of
unrestricted commercial transit through the Strait of Hormuz, counted by Lloyd's
List, by the first of November" is a claim, because they will. Every claim you
write carries the test, the name of whoever applies it, and the day by which the
answer is known.

Start from the outside, then come inside. Before you say how likely this claim
is, ask what set of past cases it belongs to, how many of them came out true, and
out of how many. Say what that set was, precisely enough that somebody else could
count it again. Then say how likely this particular claim is, with the honest
range around it — wide when you are reaching, narrow when you are on familiar
ground. The range is how sure you are of your own number. Where there is no
honest set of past cases, leave it out; absent is better than invented.

What an arrow is.
An arrow is a claim about a mechanism: this happening moves the odds of that.
It says which way and how hard it pushes, how many whole days it takes to arrive,
and what it does over time — a spike that fades, a switch that stays on, or a
climb that builds and then holds. It says whether the push survives its cause
going away: a toppled domino stays down, while an apple only stays up while the
desk is under it. And it says, in one to three sentences, why the mechanism is
real. An arrow with a number and no reason is worth nothing to the person reading
it.

Where the backing comes from.
Use the search tool when the ground is checkable and you are not certain of it,
and cite only addresses the search returned to you in this same call. If you did
not search, or nothing useful came back, cite nothing and say what you know in
the reason instead. An empty list of citations is an honest answer we can show.
An address you are recalling rather than reading is not backing, and we will not
treat it as backing.

How a story ends.
A chain ends either at something somebody could put money on — a contract at a
named venue with the side you would take, or an instrument with a direction and
how far you expect its price to move — or at a plain statement that there is
nothing to trade here, and why. Both are good endings. An ending that trails off
into prose is not.

What an answer is.
Exactly one of three things:
  a new claim, together with the one arrow that reaches it from a claim already
  on the map;
  an arrow between two claims that are both already on the map;
  or a note that this part of the story is finished, with one sentence saying
  why.

You never name a new claim with anything but its words. The short names in the
map we show you are ours; point at one when you name a cause, and never invent
another.
"""
"""The standing half of every request: the same bytes on every call, for ever.

Kept as one constant rather than assembled, so that a reader can see the whole of
what we say to a model in one place and so that nothing can quietly vary.
"""


def prompt_hash() -> str:
    """Return one string that changes whenever what we ask for changes.

    A recording of a run is only worth playing back while the questions behind it
    still hold. This fingerprint covers both halves of a question that can drift
    without anybody noticing: the standing text above, and the shapes an answer
    must fit. Change a sentence or add a field, and every recording made before
    the change can be told apart from one made after.

    It deliberately does **not** cover the varying half. That differs on every
    call by design, and folding it in would make the fingerprint useless.

    Returns:
        The fingerprint as plain hexadecimal, the same on every machine.
    """
    # Imported inside the function rather than at the top of the file: the shapes
    # module reads the map's own types and this one reads the shapes, and a plain
    # import both ways round is a circle waiting to happen the first time either
    # grows.
    from pydantic import TypeAdapter

    from katalyst.engine.proposal import Proposal, StartingClaim

    shapes = json.dumps(
        {
            "proposal": TypeAdapter(Proposal).json_schema(),
            "starting_claim": TypeAdapter(StartingClaim).json_schema(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256((STANDING_TEXT + shapes).encode("utf-8")).hexdigest()


def starting_question(sentence: str, *, is_the_hypothesis: bool) -> str:
    """Ask for one sentence a person typed, written as a claim anybody could settle.

    Asked once for the sentence the map starts from, and once more for the place
    the person asked whether it gets to. Nothing exists yet either time, so there
    is no map to show and nothing to point at.

    Args:
        sentence: What the person typed, unchanged.
        is_the_hypothesis: True for the sentence the map starts from, False for
            the place they asked whether it gets to. It changes one sentence of
            framing and nothing else.

    Returns:
        The varying half of the request, as plain text.
    """
    opening = (
        "Somebody typed this, and expects it to happen:"
        if is_the_hypothesis
        else "Somebody asked whether their expectation gets them to this:"
    )
    closing = (
        "Write it as a claim: the test, who applies it, the day the answer is "
        "known, what usually happens in cases like it, and how likely this one is "
        "with the range around it."
    )
    if not is_the_hypothesis:
        closing += (
            " Write only this claim. Whether anything leads to it is the question "
            "they asked, not something to answer here."
        )
    return "\n".join([opening, "", f"    {sentence.strip()}", "", closing])


def expanding_question(
    graph: Graph,
    frontier: PropositionId,
    *,
    target: str | None,
    ending_only: bool,
) -> str:
    """Show the map as it stands, point at one claim, and ask for the next piece.

    The varying half of every call after the first. The map is written out as
    sorted text so that the same map always produces the same bytes: a run can
    then be recorded, replayed and compared without the question drifting
    underneath it.

    Nothing in here says what an earlier proposal was refused for. A claim that
    has just been refused is asked about again with these same bytes, which is
    what makes "the next call is never told why" a fact a test can check rather
    than a promise.

    Args:
        graph: The map as it stands, including the claim being pointed at.
        frontier: The claim we are asking about.
        target: The place the person asked whether the story gets to, in their own
            words, or nothing at all when they did not name one.
        ending_only: True on the one last call a run makes when it has run out of
            room and the map still ends nowhere anybody could act on. It narrows
            the question to an ending and nothing else.

    Returns:
        The varying half of the request, as plain text.
    """
    claims = {one.id: one for one in graph.propositions}
    here = claims[frontier]
    children = sorted(claims[arrow.target].claim for arrow in graph.links if arrow.source == frontier)

    lines = [
        "Here is the map as it stands. The short name in front of each claim is "
        "ours; use one when you name a cause.",
        "",
        _map_as_text(graph),
        "",
        f"We are asking about this claim: {here.claim}",
    ]
    if children:
        lines += ["", "It already leads to:", *(f"  - {child}" for child in children)]
    if target is not None:
        lines += [
            "",
            "The person wants to know whether the story reaches this: "
            f"{target.strip()}. Work towards it where the mechanism honestly goes "
            "that way, and do not bend a step to get there — if it does not "
            "reach, we would rather say so.",
        ]
    if ending_only:
        lines += [
            "",
            "This run has no more room to grow, and the map still ends nowhere "
            "anybody could act on. So this once, answer only with an ending: "
            "something somebody could put money on, or a plain statement that "
            "there is nothing to trade here and why. If neither is honest from "
            "this claim, say that this part of the story is finished.",
        ]
    else:
        lines += [
            "",
            "Answer with the one next piece, or with a note that this part of the "
            "story is finished.",
        ]
    return "\n".join(lines)


def _map_as_text(graph: Graph) -> str:
    """Write the map out as one block of sorted text.

    Sorted, so the same map is always the same bytes. Small, so the growing half
    of a request stays cheap: one line per claim — its short name and its
    sentence — and one line per arrow joining two of those names.

    The likelihoods are deliberately left out. A model shown its own earlier
    numbers anchors on them, and none of them is needed to propose the next step.

    Args:
        graph: The map to write out.

    Returns:
        The map as plain text, claims first and then arrows.
    """
    claims = sorted(graph.propositions, key=lambda one: one.id)
    lines = ["Claims:"]
    lines += [
        f"  {one.id}  {one.claim}" + (" (this is what the person expects)" if one.kind == "hypothesis" else "")
        for one in claims
    ]
    arrows = sorted(graph.links, key=lambda one: (one.source, one.target, one.id))
    if arrows:
        lines += ["", "Arrows:", *(f"  {one.source} -> {one.target}" for one in arrows)]
    return "\n".join(lines)
