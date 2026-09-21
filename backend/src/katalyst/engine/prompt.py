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
from datetime import date

from katalyst.domain import Graph, PropositionId

STANDING_TEXT = """\
You are helping somebody think through what an event they expect would set off,
step by step, until the story reaches something they could actually trade.

You do this one piece at a time, and you will be asked two kinds of question.

The first kind hands you a sentence somebody typed and asks you to write it as a
claim. That is the whole job on that call: one claim, done properly. It is worth
as much care as any other, because everything after it hangs off it.

The second kind shows you the map as it stands, points at one claim on it, and
asks for the single next piece. Somebody watches the map grow as your answers
arrive, so a small, well-argued piece beats a large, vague one.

What a claim is.
A claim is something that will be plainly true or false by a date, settled by a
named source. "The drug pipeline looks healthy" is not a claim, because two
honest people will never agree on whether it happened. "The United States Food
and Drug Administration grants full approval to at least one new obesity
treatment, listed in its own approvals database, before the thirty-first of
March" is a claim, because they will.

A claim stands on its own. Write it as a plain statement of the thing that
happens, with no lead-in and no explanation attached: "Retail pharmacy stocks of
the treatment run short in at least twenty states." Not "With approval granted,
retail stocks run short", not "Once the approval lands, stocks run short", not
"As a result, stocks run short". The *because* is not part of the claim — it
belongs in the arrow that reaches it, and putting it in both means a box on the
screen that argues with itself. Somebody reads this claim on a tile, on its own,
with nothing around it, and it has to make sense there.

Every claim carries the test that settles it, the name of whoever applies that
test, and the day by which the answer is known. The test is written so that two
people reading it would reach the same answer: a number, a threshold, a source
that publishes it. "At least fourteen consecutive days" is a test. "Returns to
normal" is not. The judge is a named publication, exchange, agency or venue —
"the Baltic Exchange daily assessments", not "the news", and never a placeholder.

Start from the outside, then come inside.
Before you say how likely a claim is, find out how often this kind of thing has
happened before. **Search for it.** Say what set of past cases you counted,
precisely enough that somebody else could count it again, how many of them came
out the way this claim describes, and out of how many.

Stop searching as soon as you have a countable set with a page behind it. If you
cannot find one — some claims genuinely have no honest reference class — leave
the count out altogether. A count you cannot point at a page for is worse than no
count: it looks like a measurement and it is a memory, and we will drop it.

Then say how likely this particular claim is, with the honest range around it —
wide when you are reaching, narrow when you are on familiar ground. The range is
how sure you are of your own number.

What an arrow is.
An arrow is a claim about a mechanism: this happening moves the odds of that.
It says which way and how hard it pushes, how many whole days it takes to arrive,
and what it does over time — a spike that fades, a switch that stays on, or a
climb that builds and then holds. It says whether the push survives its cause
going away: a toppled domino stays down, while an apple only stays up while the
desk is under it. And it says, in one to three sentences, why the mechanism is
real. An arrow with a number and no reason is worth nothing to the person reading
it. This is where the *because* goes.

Where the backing comes from.
Cite only addresses the search returned to you in this same call. If you did not
search, or nothing useful came back, cite nothing and say what you know in the
reason instead. An empty list of citations is an honest answer we can show. An
address you are recalling rather than reading is not backing, and we will not
treat it as backing.

How a story ends, and how it gets there.
Most pieces are steps: something that happens on the way, which causes the next
thing. Give the story its next step and let it run — a map that jumps from the
first claim to a trade has skipped the argument that makes the trade worth
anything.

An ending is different, and it is narrower than it sounds. A claim is an ending
you could trade **only when its own test is a price or a contract outcome
somebody could take a position on today**: a named contract at a named venue with
the side you would take, or an instrument with a direction and how far you expect
its price to move. "Storage across Europe is at least eighty per cent full" is a
step, however tradeable it feels — what settles it is a storage figure, not a
price. "The front-month contract settles below ninety" is an ending, because what
settles it is the price itself.

The other ending is a plain statement that there is nothing to trade here, and
why. Both are good endings. An ending that trails off into prose is not.

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

    The shapes it covers are the ones **as they go out over the wire**, not as
    they are written here. The client library tidies a shape before sending it,
    and what the model was actually asked for is the tidied one — so if that
    tidying ever changes, every recording made before it can be told from every
    recording made after, which is exactly what this is for.

    It deliberately does **not** cover the varying half. That differs on every
    call by design, and folding it in would make the fingerprint useless.

    Returns:
        The fingerprint as plain hexadecimal, the same on every machine.
    """
    # Imported inside the function rather than at the top of the file, because the
    # seam reads this module and this line reads the seam. Both are fully loaded
    # by the time anybody asks for a fingerprint.
    #
    # It asks the seam for the shapes rather than naming them, so this file still
    # does not know what the wire forced on them — the envelope is the seam's
    # business and nothing outside it names it (2026-09-20).
    from katalyst.engine.client import what_goes_out

    shapes = json.dumps(what_goes_out(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((STANDING_TEXT + shapes).encode("utf-8")).hexdigest()


def starting_question(sentence: str, *, is_the_hypothesis: bool, today: date) -> str:
    """Ask for one sentence a person typed, written as a claim anybody could settle.

    Asked once for the sentence the map starts from, once more for the place the
    person asked whether it gets to, and once for a claim they ask to add later.
    Nothing exists yet the first two times, so there is no map to show.

    **It asks for each part separately, and it says what a bad answer looks
    like.** The first measured run came back with a test reading `"Res "` and a
    judge reading `"x "`, in seven seconds, and the map's own rules accepted both
    because neither is empty. Nothing downstream can catch a two-character test
    without grading prose, so the fix is here: ask for one thing at a time, say
    what each one is for, and show the shape of an answer that is not good enough.

    Args:
        sentence: What the person typed, unchanged.
        is_the_hypothesis: True for the sentence the map starts from, False for
            the place they asked whether it gets to. It changes one sentence of
            framing and nothing else.
        today: The day this run is happening. A person writing "next week" means a
            week from a particular day, and nothing else in the request says
            which. It sits here, in the varying half, and never in the standing
            half, where it would change the bytes the service recognises on every
            single run.

    Returns:
        The varying half of the request, as plain text.
    """
    opening = (
        "Somebody typed this, and expects it to happen:"
        if is_the_hypothesis
        else "Somebody asked whether their expectation gets them to this:"
    )
    lines = [
        _today(today),
        "",
        opening,
        "",
        f"    {sentence.strip()}",
        "",
        "Write it as one claim. Take the care you would take over any other: "
        "everything else on this map hangs off this one, and a claim nobody can "
        "settle makes every number below it meaningless.",
        "",
        "Keep their meaning. Do not make it more modest or more dramatic than they "
        "did, and do not answer a question they did not ask.",
        "",
        "Four things, each one properly:",
        "",
        "  The claim itself, as a plain standalone statement of what happens. No "
        "lead-in, no explanation, nothing about what caused it.",
        "",
        "  The test that settles it — a number, a threshold, a count, something "
        "published. Written so that two people reading it reach the same answer. "
        "If your test is shorter than the claim, it is not a test.",
        "",
        "  The name of whoever applies that test: a publication, an exchange, an "
        "agency, a venue. A real one, by name.",
        "",
        "  The day by which the answer is known, worked out from today's date "
        "above and from what they said.",
        "",
        "Then search for how often this kind of thing has happened before, and give "
        "the count and the set you counted if you find one you can point at a page "
        "for. Leave it out if you cannot. Then how likely this one is, with the "
        "honest range around it.",
    ]
    if not is_the_hypothesis:
        lines += [
            "",
            "Write only this claim. Whether anything leads to it is the question "
            "they asked, not something to answer here.",
        ]
    return "\n".join(lines)


def adding_question(graph: Graph, sentence: str, *, today: date) -> str:
    """Ask for a claim somebody wants to add to a map, written so it can be checked.

    The first half of *Add a claim*. It is the starting question with the map
    shown beside it, because a claim being added to a story should be written in
    the terms that story already uses — the same dates, the same judges, the same
    level of detail — and because the words it uses are what the arrows will hang
    off.

    **It needs no shape of its own.** What comes back is a starting claim: the
    thing that happens, the test, the judge, the date. Its arrows are asked for
    afterwards, one per call, by the ordinary machinery.

    Args:
        graph: The map the claim is going onto.
        sentence: What the person typed.
        today: The day this is happening.

    Returns:
        The varying half of the request, as plain text.
    """
    return "\n".join(
        [
            _today(today),
            "",
            "Here is a map somebody has built. The short name in front of each claim is ours.",
            "",
            _map_as_text(graph),
            "",
            "They want to add this to it:",
            "",
            f"    {sentence.strip()}",
            "",
            "Write it as one claim, in the terms this map already uses — the same "
            "kind of test, the same kind of judge, dates in the same window. Keep "
            "their meaning; do not answer a question they did not ask, and do not "
            "say anything here about what it would cause. That comes next, and "
            "separately.",
            "",
            "The claim itself as a plain standalone statement; the test that settles "
            "it; the name of whoever applies that test; the day the answer is known. "
            "Then search for how often this kind of thing has happened before, and "
            "give the count only if you can point at a page for it. Then how likely "
            "it is, with the range around it.",
        ]
    )


def joining_question(graph: Graph, added: PropositionId, *, today: date) -> str:
    """Ask for one arrow between the newly added claim and the map it joined.

    The second half of *Add a claim*, asked over and over until the model says
    there is nothing more. **It needs no shape of its own either**: what comes
    back is an ordinary arrow between two claims already on the map, which is
    exactly what this is once the claim has been added.

    The new claim is named in the question rather than pinned by a field, because
    a field would be a fourth shape for something the words can say perfectly
    well — and a shape is forever while a sentence is not.

    Args:
        graph: The map, with the new claim already on it.
        added: The claim that was just added.
        today: The day this is happening.

    Returns:
        The varying half of the request, as plain text.
    """
    claims = {one.id: one for one in graph.propositions}
    joined = sorted(
        f"{claims[one.source].claim} -> {claims[one.target].claim}"
        for one in graph.links
        if added in (one.source, one.target)
    )
    lines = [
        _today(today),
        "",
        "Here is the map as it stands. The short name in front of each claim is "
        "ours; use one when you name either end of an arrow.",
        "",
        _map_as_text(graph),
        "",
        f"The claim {added} has just been added to it: {claims[added].claim}",
        "",
        "Give one arrow with that claim at one end — either end. It may cause "
        "something already on the map, or something already on the map may cause "
        "it; say which by which way round you draw it.",
    ]
    if joined:
        lines += ["", "It is already joined by:", *(f"  - {one}" for one in joined)]
    lines += [
        "",
        "Answer with that one arrow, or with a note that it is joined to this map "
        "as well as it needs to be.",
    ]
    return "\n".join(lines)


def expanding_question(
    graph: Graph,
    frontier: PropositionId,
    *,
    target: str | None,
    ending_only: bool,
    today: date,
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
        today: The day this run is happening, so a claim can be given a date the
            answer is known by. It sits in the varying half, never in the
            standing half.

    Returns:
        The varying half of the request, as plain text.
    """
    claims = {one.id: one for one in graph.propositions}
    here = claims[frontier]
    children = sorted(
        claims[arrow.target].claim for arrow in graph.links if arrow.source == frontier
    )

    lines = [
        _today(today),
        "",
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
            "The person wants to know whether the story reaches this:",
            "",
            f"    {target.strip()}",
            "",
            "Work towards it where the mechanism honestly goes that way, and do "
            "not bend a step to get there — if it does not reach, we would rather "
            "say so.",
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
    started_at = " (this is what the person expects)"
    lines += [
        f"  {one.id}  {one.claim}" + (started_at if one.kind == "hypothesis" else "")
        for one in claims
    ]
    arrows = sorted(graph.links, key=lambda one: (one.source, one.target, one.id))
    if arrows:
        lines += ["", "Arrows:", *(f"  {one.source} -> {one.target}" for one in arrows)]
    return "\n".join(lines)


def _today(today: date) -> str:
    """Say what day it is, once, at the top of the varying half.

    A person who types "next week" means a week from a particular day, and a
    claim's date has to be settleable against something. This is the only moving
    part in a request that is not the map itself, and it is deliberately below
    the block the service remembers: put it above and every run would pay full
    price for every call.

    Args:
        today: The day this run is happening.

    Returns:
        One line.
    """
    return f"Today is {today.isoformat()}."
