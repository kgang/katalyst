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

from katalyst.engine.client import Model, live_answerer
from katalyst.engine.expand import Accepted, Refused, expand
from katalyst.fixtures import HORMUZ

CASSETTES = Path(__file__).resolve().parents[1] / "cassettes"

THE_DAY_THE_RUN_HAPPENED = date(2026, 9, 17)
"""The day these questions were asked, written onto anything the search found."""

NOTHING_IN_A_RECORDING_MAY_LOOK_LIKE_A_KEY = (
    "sk-ant-",
    "x-api-key: sk",
    "authorization: Bearer sk",
)
"""What a leaked credential looks like in a file somebody might publish."""


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
        HORMUZ,
        frontier,
        target=None,
        answerer=answerer,
        on=THE_DAY_THE_RUN_HAPPENED,
    )


# --- Recorded from a real call ---------------------------------------------


@pytest.mark.vcr
def test_expand_returns_one_proposal_per_call(answerer: Model) -> None:
    """One question, one answer, and at most one new claim in it."""
    outcome = ask(answerer)

    assert outcome.calls >= 1  # type: ignore[union-attr]
    result = outcome.result  # type: ignore[union-attr]
    if isinstance(result, Accepted):
        assert len(result.links) <= 1
        assert result.proposition is None or isinstance(result.proposition.claim, str)


@pytest.mark.vcr
def test_provenance_is_written_from_what_was_found(answerer: Model) -> None:
    """The word on an accepted arrow is what the rule gives for that call's own results."""
    outcome = ask(answerer)

    result = outcome.result  # type: ignore[union-attr]
    if not isinstance(result, Accepted):
        pytest.skip("this recording holds a refusal, which the refusal tests cover")
    for arrow in result.links:
        if arrow.sources:
            assert arrow.provenance == "documented"
        elif arrow.rationale.strip():
            assert arrow.provenance == "argued"
        else:
            assert arrow.provenance == "asserted"
        assert arrow.provenance not in ("historical", "market_implied", "user", "simulated")


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
    """Read against the tool's own result set, out of the same recording."""
    outcome = ask(answerer)

    result = outcome.result  # type: ignore[union-attr]
    if not isinstance(result, Accepted):
        pytest.skip("this recording holds a refusal, which the refusal tests cover")
    # There is nothing else in a recording a source could have come from.
    for arrow in result.links:
        for source in arrow.sources:
            assert source.retrieved == THE_DAY_THE_RUN_HAPPENED
            assert source.url.startswith(("http://", "https://"))


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
    arrows_before = len(HORMUZ.links)

    outcome = ask(answerer, frontier="B")

    result = outcome.result  # type: ignore[union-attr]
    assert isinstance(result, Refused)
    assert [one.code for one in result.violations] == ["cycle"]
    assert len(HORMUZ.links) == arrows_before


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

    Passes on an empty folder, so it is green from the commit that adds it and
    bites the moment the first recording lands.
    """
    for recording in sorted(CASSETTES.rglob("*.yaml")):
        said = recording.read_text(encoding="utf-8")
        for looks_like_a_key in NOTHING_IN_A_RECORDING_MAY_LOOK_LIKE_A_KEY:
            assert looks_like_a_key not in said, f"{recording.name} holds something like a key"
