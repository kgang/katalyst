"""Where an arrow says it came from, decided by us from what the search returned.

The rule fits in a sentence a reader can check: **citations come from the search
tool's own results.** Anything else is the model reporting what it remembers
reading, which is the thing a source's own description already refuses.
"""

from katalyst.domain import BaseRate, Link, Source, validate
from katalyst.engine.client import what_it_said
from katalyst.engine.expand import expand
from katalyst.engine.grounding import found_in, keep_cited, keep_returned, provenance_of
from katalyst.engine.outcome import Accepted, Refused
from katalyst.fixtures import HORMUZ
from tests.unit.engine.answers import (
    THE_DAY_THE_RUN_HAPPENED,
    Scripted,
    a_claim,
    a_search_that_failed,
    an_answer,
    an_arrow,
)

A_PAGE = "https://example.test/what-the-search-found"
ANOTHER_PAGE = "https://example.test/also-found"
NEVER_RETURNED = "https://example.test/remembered-not-read"


def ask(answerer: Scripted, frontier: str = "C") -> object:
    """Put one question about the stored example's map."""
    return expand(
        HORMUZ,
        frontier,
        target=None,
        answerer=answerer,  # type: ignore[arg-type]
        on=THE_DAY_THE_RUN_HAPPENED,
    )


def test_a_source_is_built_from_the_tools_own_results_and_carries_the_day_we_looked() -> None:
    """The only place a source is made during generation reads the tool, and nothing else."""
    said = what_it_said([an_answer(a_claim("Anything.", cause="C"), found=(A_PAGE, ANOTHER_PAGE))])

    found = found_in(said, on=THE_DAY_THE_RUN_HAPPENED)

    assert [one.url for one in found] == [A_PAGE, ANOTHER_PAGE]
    assert all(one.retrieved == THE_DAY_THE_RUN_HAPPENED for one in found)


def test_a_search_that_failed_reads_as_nothing_found_and_never_as_a_crash() -> None:
    """An error where a list of results would be is one more empty-handed call."""
    said = what_it_said([a_search_that_failed(a_claim("Anything.", cause="C"))])

    assert found_in(said, on=THE_DAY_THE_RUN_HAPPENED) == ()


def test_an_address_is_the_same_address_after_whitespace_and_one_trailing_slash() -> None:
    """Matching is exact, and deliberately not clever."""
    found = (Source(url=A_PAGE, title="What is there", retrieved=THE_DAY_THE_RUN_HAPPENED),)
    cited = an_arrow(cites=(f"  {A_PAGE}/  ",))

    kept, dropped = keep_cited(cited, found)

    assert [one.url for one in kept] == [A_PAGE]
    assert dropped == ()


def test_a_cited_address_the_search_never_returned_is_dropped_and_named() -> None:
    """It is not fetched to see whether it was real, and not kept with a caveat."""
    found = (Source(url=A_PAGE, title="What is there", retrieved=THE_DAY_THE_RUN_HAPPENED),)
    cited = an_arrow(cites=(A_PAGE, NEVER_RETURNED))

    kept, dropped = keep_cited(cited, found)

    assert [one.url for one in kept] == [A_PAGE]
    assert dropped == (NEVER_RETURNED,)


def test_the_word_is_earned_by_the_survivor_and_not_lost_to_the_impostor() -> None:
    """One cited source that the search returned is enough, whatever else was cited."""
    kept = (Source(url=A_PAGE, title="What is there", retrieved=THE_DAY_THE_RUN_HAPPENED),)

    assert provenance_of(an_arrow(cites=(A_PAGE, NEVER_RETURNED)), kept) == "documented"


def test_an_arrow_that_found_nothing_says_it_argued() -> None:
    """A mechanism stated and nothing fetched to back it is the honest common case."""
    assert provenance_of(an_arrow(), ()) == "argued"


def test_an_arrow_with_no_mechanism_at_all_says_it_asserted() -> None:
    """Written a moment before the map's own rules refuse it for having no mechanism."""
    assert provenance_of(an_arrow(rationale="   "), ()) == "asserted"


def test_no_word_is_ever_upgraded_or_downgraded_after_the_fact() -> None:
    """The four words that belong to somebody else never come out of a proposal."""
    everything_it_can_say = {
        provenance_of(an_arrow(cites=(A_PAGE,)), (Source(url=A_PAGE, title="t"),)),
        provenance_of(an_arrow(), ()),
        provenance_of(an_arrow(rationale=""), ()),
    }
    assert everything_it_can_say == {"documented", "argued", "asserted"}


def test_an_accepted_arrow_never_carries_a_source_the_search_did_not_return() -> None:
    """End to end: what the model cited, what survived, and what the arrow says."""
    proposed = a_claim("Something backed by one page.", cause="C", cites=(A_PAGE, NEVER_RETURNED))
    outcome = ask(Scripted([an_answer(proposed, found=(A_PAGE,), searches=1)]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    arrow = accepted.links[0]
    assert [one.url for one in arrow.sources] == [A_PAGE]
    assert arrow.provenance == "documented"
    assert accepted.sources_dropped == (NEVER_RETURNED,)


def test_an_arrow_whose_every_citation_was_never_returned_says_it_argued() -> None:
    """Nothing survived, so nothing is claimed — and the dropped address is named."""
    proposed = a_claim("Something backed by nothing.", cause="C", cites=(NEVER_RETURNED,))
    outcome = ask(Scripted([an_answer(proposed, found=(A_PAGE,), searches=1)]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    assert accepted.links[0].sources == ()
    assert accepted.links[0].provenance == "argued"
    assert accepted.sources_dropped == (NEVER_RETURNED,)


def test_a_documented_arrow_that_cites_nothing_is_refused_whoever_wrote_it() -> None:
    """The pipeline cannot produce one, and the map's own rules refuse one anyway."""
    unbacked = Link(
        id="an-arrow",
        source="H",
        target="C",
        mode="sustain",
        strength=0.5,
        lag=1.0,
        shape="step",
        rationale="Says it read something, and cites nothing.",
        sources=(),
        provenance="documented",
    )
    faults = validate(HORMUZ.model_copy(update={"links": (*HORMUZ.links, unbacked)}))

    assert [one.code for one in faults] == ["documented_without_source"]


def test_a_base_rates_addresses_are_kept_by_the_same_rule_as_an_arrows() -> None:
    """An empty count of sources already means the count is the model's own recollection."""
    counted = BaseRate(
        reference_class="Past cases of this kind.",
        k=7,
        n=9,
        sources=(A_PAGE, NEVER_RETURNED),
    )
    proposed = a_claim("Something with a count behind it.", cause="C", counted=counted)
    outcome = ask(Scripted([an_answer(proposed, found=(A_PAGE,), searches=1)]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    assert accepted.proposition is not None
    assert accepted.proposition.base_rate is not None
    assert accepted.proposition.base_rate.sources == (A_PAGE,)
    assert accepted.proposition.base_rate.k == counted.k


def test_a_generated_claim_carries_no_published_items_for_and_against() -> None:
    """Turning a search result into one would need a direction and a weight nobody gave."""
    outcome = ask(Scripted([an_answer(a_claim("Anything.", cause="C"), found=(A_PAGE,))]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    assert accepted.proposition is not None
    assert accepted.proposition.evidence == ()


def test_an_arrows_whole_days_widen_to_days_as_a_number() -> None:
    """The one shape change between a draft and the arrow it becomes."""
    outcome = ask(Scripted([an_answer(a_claim("Anything.", cause="C"))]))

    accepted = outcome.result  # type: ignore[union-attr]
    assert isinstance(accepted, Accepted)
    assert isinstance(accepted.links[0].lag, float)


def test_a_refusal_keeps_the_arrow_off_the_map_sources_and_all() -> None:
    """Nothing a refused proposal cited reaches anything."""
    proposed = a_claim("A claim nobody can settle.", cause="C", criteria="  ", cites=(A_PAGE,))
    outcome = ask(Scripted([an_answer(proposed, found=(A_PAGE,), searches=1)]))

    assert isinstance(outcome.result, Refused)  # type: ignore[union-attr]
    assert all(A_PAGE not in [s.url for s in one.sources] for one in HORMUZ.links)


def test_a_count_whose_pages_the_search_never_returned_is_thrown_away() -> None:
    """Measured, 2026-09-17: eight claims in ten carried a count behind no page.

    One of them was "37 of 41 cases since 1980" — which is the schema's own
    example wearing a number. A count nobody can open a page for is the same
    failure as a mechanism nobody can open a page for, so it goes through the
    same rule and the claim arrives without it.
    """
    counted = BaseRate(
        reference_class="Closures of a major strait since 1980",
        k=37,
        n=41,
        sources=(NEVER_RETURNED,),
    )
    answered = a_claim("A claim with a remembered count.", cause="C", counted=counted)

    outcome = ask(Scripted([an_answer(answered, found=(A_PAGE,), searches=1)]))

    accepted = outcome.result  # type: ignore[attr-defined]
    assert isinstance(accepted, Accepted)
    assert accepted.proposition is not None
    assert accepted.proposition.base_rate is None
    assert accepted.base_rate_dropped == "Closures of a major strait since 1980"


def test_a_count_the_search_did_return_is_kept_with_only_those_pages() -> None:
    """The other side of the same rule: a sourced count survives, minus what was not found."""
    counted = BaseRate(
        reference_class="Something somebody counted and published",
        k=3,
        n=10,
        sources=(A_PAGE, NEVER_RETURNED),
    )
    answered = a_claim("A claim with a checkable count.", cause="C", counted=counted)

    outcome = ask(Scripted([an_answer(answered, found=(A_PAGE,), searches=1)]))

    accepted = outcome.result  # type: ignore[attr-defined]
    assert isinstance(accepted, Accepted)
    assert accepted.proposition is not None
    assert accepted.proposition.base_rate is not None
    assert accepted.proposition.base_rate.sources == (A_PAGE,)
    assert accepted.base_rate_dropped is None


def test_one_rule_splits_the_addresses_for_arrows_and_for_counts_alike() -> None:
    """The reason there is one function: two failures, one law, one place to change it."""
    found = (Source(url=A_PAGE, title="A page", retrieved_at=THE_DAY_THE_RUN_HAPPENED),)

    kept, dropped = keep_returned((A_PAGE, NEVER_RETURNED), found)

    assert kept == (A_PAGE,)
    assert dropped == (NEVER_RETURNED,)
