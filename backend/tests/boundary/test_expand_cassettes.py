"""The pipeline against **real** exchanges with the model, recorded once and replayed.

Why these exist beside the fast tests
--------------------------------------
The tests under `tests/unit/engine/` hand the pipeline answers written out by
hand. They are exact, they cover the cases a live model will not produce on
demand, and they run in a fraction of a second. What they cannot do is notice the
day the service starts putting a search result somewhere else, or the day the
client library renames a counter. These can: every answer below was a real answer
once, saved to disk with the credentials stripped out, and replayed from then on
(decision record 0008). The suite runs with recording off, so a call nobody has
recorded fails rather than dialling out — no key, no network, no money.

**Until somebody records them, every test in this file fails, and that is the
intended state.** They fail with a sentence saying which recording is missing and
what to run. The pipeline agent does not hold a key; the coordinator records.

How the recordings are made
---------------------------
`make record-cassettes` runs the tests marked as recordable against a real key
and writes one file per test into `tests/cassettes/`. Four of them make a real
call. The other four cannot: a live model does not produce a proposal that closes
a loop, a claim with a blank test, or a citation it never looked at, on request.
Those are marked `handmade` — the recording is one of the honest ones with its
answer edited by hand to hold the case, and `make record-cassettes` leaves them
alone so that re-recording cannot throw the deliberate case away. Each one says,
in its own docstring, exactly which edit it needs.

**Whenever a prompt changes, the recordings are remade.** The same checklist line
the demo recordings carry.
"""

from datetime import date
from pathlib import Path

import pytest

from katalyst.domain import Graph
from katalyst.engine.client import Model, live_answerer
from katalyst.engine.expand import expand
from katalyst.engine.grounding import found_in, keep_cited, provenance_of, same_address
from katalyst.engine.outcome import Accepted, Refused, Said
from katalyst.engine.prompt import expanding_question
from katalyst.engine.proposal import ClaimProposal, LinkDraft, LinkProposal

CASSETTES = Path(__file__).resolve().parents[1] / "cassettes"

# **The map these tests ask about is a frozen copy, not the one the product
# ships** *(2026-09-22)*. A recorded answer is found again by matching the whole
# request body, and the request body writes the map out as text: every claim's
# short name and sentence, and every arrow between them. The curated example was
# rewritten on 2026-09-22 — claims renamed, two added, sentences changed — so
# every recording here stopped matching the moment it was.
#
# Re-recording is held. Kent's decision, row R5 of the 2026-09-21 decisions note:
# every change to what the model is asked for goes in **one freeze after the
# engine's flip**, and only then is anything paid for again. So the tests' input
# moves back instead: the file beside this one is the curated map exactly as it
# stood on the day these exchanges were recorded, with one field written in that
# the request body does not carry — `persistence`, which says whether a claim
# happens once or holds for a while, required on every claim since decision
# record 0017 and absent from the map when these were made. The freeze re-records
# all of them against the map the product actually ships, and this file goes then.
#
# It was written by `plans/analysis/scripts/stack-05-flip/freeze_the_map_the_cassettes_saw.py`,
# out of the fixture and the rules layer as they stood before the flip.
THE_MAP_THE_RECORDINGS_WERE_MADE_AGAINST = Graph.model_validate_json(
    (Path(__file__).resolve().parent / "the_map_the_cassettes_saw.json").read_text(encoding="utf-8")
)
"""The curated map as it was on 2026-09-17, the day these exchanges were recorded."""

THE_DAY_THE_RUN_HAPPENED = date(2026, 9, 17)
"""The day these questions were asked, written onto anything the search found."""

NOTHING_IN_A_RECORDING_MAY_LOOK_LIKE_A_KEY = (
    "sk-ant-",
    "x-api-key: sk",
    "authorization: Bearer sk",
)
"""What a leaked credential looks like in a file somebody might publish."""

NOTHING_IN_A_RECORDING_SAYS_WHOSE_ACCOUNT_IT_WAS = (
    "anthropic-organization-id",
    "anthropic-workspace-id",
    "anthropic-ratelimit-",
    "request-id",
    "cf-ray",
    "traceresponse",
    "set-cookie",
)
"""What the service says about the account a call was billed to.

None of it is a secret and none of it is read back on replay, and all of it is
somebody's business but the reader's: which organisation and workspace paid for
the call, what that account has bought and how much of it is left, and a handful
of identifiers tying the exchange to one account's traffic. The recorder takes
them out as it writes (`tests/conftest.py`); this is the net under that,
and it checks every recording wherever it was made.
"""


@pytest.fixture
def answerer(request: pytest.FixtureRequest) -> Model:
    """Hand over a live answerer, or say plainly which recording is missing.

    With no key and no recording there is nothing to replay, and the useful thing
    to say is not "connection refused" but the name of the file and the command
    that writes it.
    """
    recording = CASSETTES / f"{request.node.name}.yaml"
    built = live_answerer()
    if built is None and not recording.exists():
        pytest.fail(
            f"There is no recording at {recording.name} and no key to make one with. "
            "Run `make record-cassettes` with a key in the environment."
        )
    if built is not None:
        return built
    # Replaying: the client still needs something in the credential slot, and the
    # recorder answers before anything reaches the network.
    from anthropic import Anthropic

    return Model(Anthropic(api_key="not-a-key-nothing-is-sent"))


def ask(answerer: Model, frontier: str = "C") -> object:
    """Put one question about the stored example's map."""
    return expand(
        THE_MAP_THE_RECORDINGS_WERE_MADE_AGAINST,
        frontier,
        target=None,
        answerer=answerer,
        on=THE_DAY_THE_RUN_HAPPENED,
    )


RECORD_IT_AGAIN = (
    "This recording came back with no proposal in it, so the rule below was never "
    "put to anything. A test that passes because there was nothing to check is a "
    "test that has stopped working without saying so — record it again."
)
"""What a recording that proves nothing is told, instead of being skipped.

Three tests here used to `skip` or quietly do nothing when a re-recording came
back as a `Stop` or a refusal. A green suite that had checked nothing is the
worst of both worlds: it costs the same and says the same as one that did
(2026-09-20).
"""


def asking(answerer: Model, frontier: str = "C") -> Said:
    """Put one question straight to the seam, so the test can read what the search found.

    The same one recorded exchange `ask` uses, and one call's worth of the
    cassette. Reading `said.found` is the only way to check the grounding rules
    against **what the tool actually returned** rather than against a
    re-statement of the rule in the test.
    """
    return answerer.proposal(
        expanding_question(
            THE_MAP_THE_RECORDINGS_WERE_MADE_AGAINST,
            frontier,
            target=None,
            ending_only=False,
            today=THE_DAY_THE_RUN_HAPPENED,
        ),
        may_search=True,
    )


def cited_by(draft: LinkDraft) -> tuple[str, ...]:
    """The addresses an arrow cites, as the one grounding rule wants them."""
    return tuple(one.url for one in draft.sources)


def what_it_proposed(said: Said) -> ClaimProposal | LinkProposal:
    """Take the proposal out of an answer, or say loudly that there is not one."""
    proposed = said.answered
    assert isinstance(proposed, ClaimProposal | LinkProposal), RECORD_IT_AGAIN
    return proposed


# --- Recorded from a real call ---------------------------------------------


@pytest.mark.vcr
def test_expand_returns_one_proposal_per_call(answerer: Model) -> None:
    """One question, one answer, and at most one new claim in it."""
    outcome = ask(answerer)

    assert outcome.calls >= 1  # type: ignore[union-attr]
    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Accepted), RECORD_IT_AGAIN
    assert len(result.links) <= 1
    assert result.proposition is None or isinstance(result.proposition.claim, str)


@pytest.mark.vcr
def test_provenance_is_written_from_what_was_found(answerer: Model) -> None:
    """The word on an arrow is the one our rule gives for that call's own search results.

    Read against `said.found` — the tool's own result set out of this very
    recording — rather than against the rule written out a second time in the
    test. A test that re-states the rule agrees with the code by construction and
    would agree with it just as readily if both were wrong (2026-09-20).
    """
    said = asking(answerer)
    draft = what_it_proposed(said).link
    found = found_in(said, on=THE_DAY_THE_RUN_HAPPENED)

    kept, _ = keep_cited(cited_by(draft), found)
    word = provenance_of(draft, kept)

    assert word == ("documented" if kept else "argued" if draft.rationale.strip() else "asserted")
    assert word not in ("historical", "market_implied", "user", "simulated")


@pytest.mark.vcr
def test_generation_receipt_records_cache_reads(answerer: Model) -> None:
    """The second call of a run reads the standing half back rather than paying for it.

    A run whose cache reads stay at nothing is a bug in how the request is put
    together, not a slow day.
    """
    first = ask(answerer)
    second = ask(answerer, frontier="B")

    assert first.input_tokens > 0  # type: ignore[union-attr]
    assert second.cache_read_tokens > 0  # type: ignore[union-attr]


@pytest.mark.vcr
def test_a_source_is_only_ever_one_the_search_tool_returned(answerer: Model) -> None:
    """Read against the tool's own result set, out of the same recording.

    Every address that survives is one this very call's search returned, compared
    against `said.found` rather than against a shape the test asserts for itself.
    """
    said = asking(answerer)
    draft = what_it_proposed(said).link
    found = found_in(said, on=THE_DAY_THE_RUN_HAPPENED)
    returned = {same_address(one.url) for one in found}

    kept, dropped = keep_cited(cited_by(draft), found)

    assert all(same_address(one.url) in returned for one in kept)
    assert all(same_address(one) not in returned for one in dropped)
    assert all(one.retrieved == THE_DAY_THE_RUN_HAPPENED for one in found)


# --- Shaped by hand from one of the recordings above ------------------------


@pytest.mark.vcr
@pytest.mark.handmade
def test_expand_rejects_cycle(answerer: Model) -> None:
    """A recorded proposal that would close a loop is refused, and the map is unchanged.

    **The edit this recording needs:** take the recorded answer from
    `test_expand_returns_one_proposal_per_call`, and replace the proposal in its
    body with an arrow proposal from `B` back to `H` — `{"kind": "link", "source":
    "B", "target": "H", "link": {...the recorded arrow...}}`. The stored example
    already runs `H` to `C` to `B`, so that arrow closes the loop.
    """
    arrows_before = len(THE_MAP_THE_RECORDINGS_WERE_MADE_AGAINST.links)

    outcome = ask(answerer, frontier="B")

    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Refused)
    assert [one.code for one in result.violations] == ["cycle"]
    assert len(THE_MAP_THE_RECORDINGS_WERE_MADE_AGAINST.links) == arrows_before


@pytest.mark.vcr
@pytest.mark.handmade
def test_expand_rejects_a_claim_with_no_resolution_criteria(answerer: Model) -> None:
    """A claim nobody can settle is not a claim, whoever wrote it.

    **The edit this recording needs:** take the recorded answer from
    `test_expand_returns_one_proposal_per_call` and blank the `criteria` string
    inside its `resolution`.
    """
    outcome = ask(answerer)

    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Refused)
    assert "missing_resolution" in [one.code for one in result.violations]


@pytest.mark.vcr
@pytest.mark.handmade
def test_a_cited_url_the_search_never_returned_is_not_a_source(answerer: Model) -> None:
    """An address the model typed that the tool never returned is dropped, and named.

    **The edit this recording needs:** take the recorded answer from
    `test_provenance_is_written_from_what_was_found` and add a second citation to
    the proposal's arrow — any address that appears nowhere in the same
    recording's search results. Leave the tool's results untouched.
    """
    outcome = ask(answerer)

    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Accepted)
    assert result.sources_dropped
    kept = {source.url for arrow in result.links for source in arrow.sources}
    assert all(dropped not in kept for dropped in result.sources_dropped)


@pytest.mark.vcr
@pytest.mark.handmade
def test_expand_rejects_a_documented_arrow_that_cites_nothing(answerer: Model) -> None:
    """Nothing this pipeline accepts says it read something and cites nothing.

    **The edit this recording needs:** take the recorded answer from
    `test_provenance_is_written_from_what_was_found` and replace every citation on
    the proposal's arrow with an address the same recording's search results never
    held. The arrow must come back saying it argued, never that it documented.
    """
    outcome = ask(answerer)

    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Accepted)
    for arrow in result.links:
        assert arrow.sources == ()
        assert arrow.provenance == "argued"
    assert result.sources_dropped


# --- True with or without a recording ---------------------------------------


def test_no_cassette_contains_a_key() -> None:
    """Nothing in a committed recording would embarrass us in a public repository.

    A key first, and then everything the service's own reply says about the
    account that paid for the call. Passes on an empty folder, so it was green
    from the commit that added it and bit the moment the first recording landed —
    which is exactly what happened: the first four came back naming an
    organisation, a workspace and that account's rate limits.
    """
    for recording in sorted(CASSETTES.rglob("*.yaml")):
        said = recording.read_text(encoding="utf-8")
        for looks_like_a_key in NOTHING_IN_A_RECORDING_MAY_LOOK_LIKE_A_KEY:
            assert looks_like_a_key not in said, f"{recording.name} holds something like a key"
        for whose_account in NOTHING_IN_A_RECORDING_SAYS_WHOSE_ACCOUNT_IT_WAS:
            assert whose_account not in said, (
                f"{recording.name} says whose account this was, at {whose_account!r}"
            )
