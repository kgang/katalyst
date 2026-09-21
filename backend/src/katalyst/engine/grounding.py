"""Where an arrow came from, decided by us from what the search actually returned.

An arrow that says *why* is worth more than an arrow that says *how much*, and an
arrow with a document behind it is worth more than either. This file is the
receipt for that: three small pure functions that answer one question with a
checkable answer — **did the search tool itself hand us at least one of the
addresses this arrow cites?**

The rule fits in a sentence a reader can check: **citations come from the search
tool's own results.** Anything else is the model reporting what it remembers
reading, which is the thing a source's own description already refuses. A model
that can write the word `documented` will write it, so the field is not on the
shape it fills, and the word is written here.

Nothing here talks to anything. It reads a `Said` — a call's answer already
translated into our own words — and the arrow the model drew, and returns values.
Everything it needs is in hand.

What this file must never do
----------------------------
- Never let an address the model typed become a source. That is the whole rule.
- Never repair, guess at, or go and fetch a dropped address to see whether it was
  real. It is dropped, and a reader is told which one.
- Never return the four words that belong to somebody else: a study of past
  cases, a live price, a person and a probe each write their own.
- Never name a type from the library we call the model with.
"""

from collections.abc import Sequence
from datetime import date

from katalyst.domain import Provenance, Source
from katalyst.engine.outcome import Said
from katalyst.engine.proposal import LinkDraft


def found_in(said: Said, *, on: date) -> tuple[Source, ...]:
    """Turn what the search tool returned in one call into sources a reader can open.

    **The only place a source is built during generation.** The day is stamped on
    here rather than carried across the seam, because the day a run happened is a
    fact about the run and not about the page.

    It can never include an address that came from the model's own text: what the
    model wrote and what the search returned arrive in two different fields, and
    this reads only the second.

    Args:
        said: One call's answer, already in our own words.
        on: The day the call ran, which is the day these were fetched.

    Returns:
        One source per result, in the order the tool returned them.
    """
    return tuple(Source(url=page.url, title=page.title, retrieved=on) for page in said.found)


def keep_cited(
    draft: LinkDraft, found: tuple[Source, ...]
) -> tuple[tuple[Source, ...], tuple[str, ...]]:
    """Split what an arrow cites into what we can stand behind, and what we drop.

    Matching is an exact comparison of the address, after trimming surrounding
    whitespace and any trailing slashes. Nothing cleverer: deciding that two
    slightly different addresses are "the same page" is a judgement, and a
    judgement is how a dropped citation quietly comes back.

    A dropped address is never repaired, guessed at, or fetched to see whether it
    was real. It is dropped, and a reader is told which one.

    Args:
        draft: The arrow as the model wrote it, with the addresses it cited.
        found: What the search tool returned in that same call.

    Returns:
        The sources the search actually returned, in the order the model cited
        them, and the addresses it cited that the search never returned.
    """
    by_address = {same_address(source.url): source for source in found}
    kept: list[Source] = []
    dropped: list[str] = []
    for cited in draft.sources:
        match = by_address.get(same_address(cited.url))
        if match is None:
            dropped.append(cited.url)
        elif match not in kept:
            kept.append(match)
    return tuple(kept), tuple(dropped)


def keep_returned(
    cited: Sequence[str], found: tuple[Source, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split plain addresses into the ones the search returned and the ones it did not.

    The same rule `keep_cited` applies to an arrow's citations, over the bare
    strings a base rate's sources are. **One rule, used for both**, because a
    count somebody cannot open a page for and a mechanism somebody cannot open a
    page for are the same failure wearing two hats — and the first measured run
    produced eight of the second kind in ten claims.

    Args:
        cited: The addresses as they were written.
        found: What the search tool returned in that same call.

    Returns:
        The addresses the search returned, in the order they were cited, and the
        ones it did not.
    """
    returned = {same_address(source.url) for source in found}
    kept = [one for one in cited if same_address(one) in returned]
    dropped = [one for one in cited if same_address(one) not in returned]
    return tuple(kept), tuple(dropped)


def provenance_of(draft: LinkDraft, kept: tuple[Source, ...]) -> Provenance:
    """Say which word this arrow has earned, from what actually happened.

    `documented` when at least one cited source survived; otherwise `argued` when
    the arrow states a mechanism; otherwise `asserted`.

    It never reads anything the model said about its own confidence, and it never
    returns the four words that belong to somebody else.

    In practice no arrow this pipeline accepts is ever `asserted`, because every
    arrow must carry a mechanism and the map's own rules refuse one that does not.
    The word is written here anyway, a moment before that refusal, because the
    alternative is a judgement about whether a sentence is a good enough
    mechanism — and grading prose is exactly what we refuse to ask code to do.

    Args:
        draft: The arrow as the model wrote it.
        kept: The sources that survived `keep_cited`.

    Returns:
        One of three words.
    """
    if kept:
        return "documented"
    if draft.rationale.strip():
        return "argued"
    return "asserted"


def same_address(url: str) -> str:
    """Put one address into the form two addresses are compared in.

    Surrounding whitespace and **every** trailing slash come off, and nothing
    else. Every rather than one, because `…/reports/` and `…/reports//` are the
    same page and nobody would say otherwise; the docstring used to say one, and
    a rule described wrongly is a rule nobody can rely on (2026-09-20). A page
    written with something extra on the end — a tracking parameter, say — loses
    its citation and the arrow falls back to saying it argued rather than
    documented. That is the safe direction to be wrong in.

    Args:
        url: The address as it was written.

    Returns:
        The form used for comparison. Never shown to anybody.
    """
    return url.strip().rstrip("/")
