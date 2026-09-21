"""A whole case run end to end through the harness, and the scorecard it produces.

The stand-ins here are the recorder's own: answerers that tell a fixed story, so
a run reaches the very same walk a paid run reaches and nothing about the result
depends on what a model felt like saying. What is being checked is the harness —
that it drives one walk and not a second one, keeps every run, counts what is on
the finished map, and writes a file somebody can open next month.

**Nothing below compares a count with a number somebody typed.** Each is compared
with the thing it was counted from, or with the other columns it has to agree
with — which is the only kind of assertion that still means something when the
story changes.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from evals.run import (
    COLUMNS,
    Case,
    Scored,
    as_a_table,
    run_one,
    scorecard_of,
    write_tsv,
)

from katalyst.engine.record import KeptRun
from tests.unit.engine import stand_ins
from tests.unit.engine.stand_ins import (
    THE_DESTINATION,
    THE_STRAIT,
    an_eval_that_holds_every_check,
    an_eval_whose_map_ends_nowhere,
)

A_DAY = date(2026, 9, 17)
"""The day these runs happen on. Passed in, because nothing in this layer reads a clock."""

A_VERIFY_CASE = Case(
    id="hormuz",
    hypothesis=THE_STRAIT,
    door="verify",
    target=THE_DESTINATION,
    unreachable=False,
    seed=20261001,
)
AN_EXPLORE_CASE = Case(id="photonics", hypothesis=THE_STRAIT, door="explore", seed=20280701)
A_CASE_NOTHING_REACHES = A_VERIFY_CASE.model_copy(
    update={"id": "export-controls", "unreachable": True}
)


def quietly(case: Case, answerer: object, tmp_path: Path, *, cap: float = 15.0) -> Scored:
    """Run one case against a stand-in, keeping everything in a throwaway directory.

    Nothing here may touch `backend/.runs/`: that folder holds what real money
    bought.
    """
    return run_one(
        case,
        answerer=answerer,  # type: ignore[arg-type]
        cap=cap,
        on=A_DAY,
        keep_in=tmp_path,
        say=lambda _: None,
    )


def the_kept_run(tmp_path: Path) -> KeptRun:
    """Read the one file the run left behind."""
    kept = sorted(tmp_path.glob("*.json"))
    assert len(kept) == 1, f"expected one kept run, found {[one.name for one in kept]}"
    return KeptRun.model_validate_json(kept[0].read_text(encoding="utf-8"))


# --- A run that gives all eight checks nothing to find ----------------------


def test_a_sound_run_holds_every_one_of_the_eight_checks(tmp_path: Path) -> None:
    """The story is built so that each check has something real to read and finds it sound."""
    scored = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path)

    assert [one.number for one in scored.checks] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert scored.passed, [one.why for one in scored.checks if not one.held]


def test_the_row_counts_what_is_actually_on_the_map_it_kept(tmp_path: Path) -> None:
    """Every count is compared with the map the same run wrote to disk, not with a figure."""
    scored = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path)
    kept = the_kept_run(tmp_path)
    assert kept.graph is not None

    assert scored.score.claims == len(kept.graph.propositions)
    assert scored.score.links == len(kept.graph.links)
    assert scored.score.endings == sum(
        1 for one in kept.graph.propositions if one.kind in ("market", "not_tradeable")
    )


def test_every_arrow_carries_exactly_one_word_for_where_it_came_from(tmp_path: Path) -> None:
    """The three provenance columns have to add up to the arrows, or one arrow is counted twice."""
    score = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path).score

    assert score.documented_links + score.argued_links + score.asserted_links == score.links


def test_no_arrow_reaches_the_map_with_neither_a_page_nor_a_mechanism(tmp_path: Path) -> None:
    """`asserted` reads zero because every arrow must carry a mechanism to be accepted at all.

    A non-zero reading is not a worse map; it is an arrow that reached the map
    without going through the accept step.
    """
    score = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path).score

    assert score.asserted_links == 0
    assert score.violations == 0


def test_a_derived_column_never_disagrees_with_what_it_came_from(tmp_path: Path) -> None:
    """The two divided columns are a convenience, and never a source.

    If either ever disagreed with the two columns above it, it would be the
    derived one that was wrong — so this pins them to each other rather than to a
    number.

    **The tolerance is the last bits of a float and is not a fudge.** Dividing and
    multiplying back does not round-trip: `seconds / calls * calls` differs from
    `seconds` in its last bit for about a fifth of the wall-clock values this test
    can produce, so an exact comparison here fails about one run in five on the
    arithmetic alone. Measured 2026-09-21, over 200 000 drawn durations at two to
    eleven calls: 44 446 of them do not round-trip. A relative tolerance of a
    million-millionth is far tighter than any disagreement worth catching — a
    column read off the wrong field, or divided by the wrong one — and far looser
    than the one bit the division costs.
    """
    score = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path).score

    assert score.searches_per_claim * score.claims == pytest.approx(score.searches, rel=1e-12)
    assert score.seconds_per_call * score.calls == pytest.approx(score.seconds, rel=1e-12)


def test_a_count_of_past_cases_is_kept_only_when_the_search_returned_its_page(
    tmp_path: Path,
) -> None:
    """The story cites the one address its own search returned, so the count survives."""
    scored = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path)
    kept = the_kept_run(tmp_path)
    assert kept.graph is not None

    assert scored.score.base_rates_kept == sum(
        1 for one in kept.graph.propositions if one.base_rate is not None
    )
    assert scored.score.base_rates_dropped == 0


def test_the_verify_door_grades_a_route_when_one_exists(tmp_path: Path) -> None:
    """The story joins a claim on the map to the destination with an ordinary arrow.

    Nothing invents a bridge: the arrow is proposed like any other and the map's
    own rules accept it like any other.
    """
    score = quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path).score

    assert score.verdict == "reached"
    assert score.path_length is not None
    assert score.path_length > 0


def test_an_explore_case_is_asked_no_question_about_a_destination(tmp_path: Path) -> None:
    """There is no door to answer, so the two columns about one read as absences."""
    score = quietly(AN_EXPLORE_CASE, an_eval_that_holds_every_check(), tmp_path).score

    assert score.verdict is None
    assert score.path_length is None


# --- The three failures a real run can actually produce ---------------------


def test_a_map_that_ends_nowhere_fails_the_ending_check(tmp_path: Path) -> None:
    """Check 2, through the harness: every open line was asked for an ending and none came."""
    scored = quietly(AN_EXPLORE_CASE, an_eval_whose_map_ends_nowhere(), tmp_path)

    assert not scored.passed
    assert {one.number for one in scored.checks if not one.held} == {2}
    assert scored.score.stopped_for == "no_terminal"
    assert scored.score.endings == 0


def test_a_run_that_never_reads_its_cache_back_fails_that_check(tmp_path: Path) -> None:
    """Check 6, through the harness. Zero cache reads is a bug, not a slow day."""
    scored = quietly(AN_EXPLORE_CASE, stand_ins.a_whole_story(), tmp_path)

    assert not scored.passed
    assert 6 in {one.number for one in scored.checks if not one.held}
    assert scored.score.cache_read_tokens == 0


def test_saying_it_reached_what_nothing_reaches_fails_the_door_check(tmp_path: Path) -> None:
    """Check 5, through the harness, on the case the whole set exists for.

    The same story that holds every check on a reachable case fails this one, and
    only this one, when the case says nothing should reach the destination. Either
    a mechanism genuinely exists and somebody should read it, or a bridge was
    invented — and both are worth the whole harness.
    """
    scored = quietly(A_CASE_NOTHING_REACHES, an_eval_that_holds_every_check(), tmp_path)

    assert {one.number for one in scored.checks if not one.held} == {5}
    assert scored.score.verdict == "reached"


# --- What is kept, and what is written --------------------------------------


def test_every_run_is_kept_whatever_it_scores(tmp_path: Path) -> None:
    """A paid run is never thrown away, and a low score is no exception."""
    scored = quietly(AN_EXPLORE_CASE, an_eval_whose_map_ends_nowhere(), tmp_path)
    kept = the_kept_run(tmp_path)

    assert scored.kept_at is not None
    assert kept.receipt is not None
    assert kept.done is not None
    assert kept.transcript.lines
    assert kept.became_a_recording is False
    assert any("eval run" in one for one in kept.faults)


def test_the_scorecard_writes_one_row_per_case_under_one_heading(tmp_path: Path) -> None:
    """A file a spreadsheet opens and a difference between two commits still reads."""
    scored = [
        quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path / "one"),
        quietly(AN_EXPLORE_CASE, an_eval_whose_map_ends_nowhere(), tmp_path / "two"),
    ]
    card = scorecard_of(_at_noon(), scored, model="a-model")

    written = write_tsv(card, folder=tmp_path)
    rows = written.read_text(encoding="utf-8").splitlines()

    assert rows[0].split("\t") == list(COLUMNS)
    assert len(rows) == 1 + len(scored)
    assert all(len(one.split("\t")) == len(COLUMNS) for one in rows)


def test_a_second_run_on_the_same_day_appends_rather_than_overwrites(tmp_path: Path) -> None:
    """Two runs in a day are told apart by when they started and by the prompt's fingerprint.

    Overwriting would throw away the run somebody is comparing against, which is
    the only reason the file exists.
    """
    scored = [quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path / "one")]
    card = scorecard_of(_at_noon(), scored, model="a-model")

    first = write_tsv(card, folder=tmp_path)
    second = write_tsv(card, folder=tmp_path)
    rows = second.read_text(encoding="utf-8").splitlines()

    assert first == second
    assert len(rows) == 1 + 2 * len(scored)
    assert rows.count(rows[0]) == 1


def test_the_terminal_table_shows_every_column_the_file_does(tmp_path: Path) -> None:
    """Turned on its side, because a row per case would be twenty-five columns wide.

    A person comparing two runs reads down a column, so the table has one line per
    field and one column per case — and no field may be missing from it.
    """
    scored = [quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path)]
    card = scorecard_of(_at_noon(), scored, model="a-model")

    table = as_a_table(card)
    named = [one.split("  ")[0].strip() for one in table[2:]]

    assert table[0].strip() == "hormuz"
    assert named == [one for one in COLUMNS if one not in ("run_at", "model", "prompt_hash")]


def test_the_scorecard_counts_the_cases_that_held_every_check(tmp_path: Path) -> None:
    """`passed` and `failed` are the two halves of the same count, and add up."""
    scored = [
        quietly(A_VERIFY_CASE, an_eval_that_holds_every_check(), tmp_path / "one"),
        quietly(AN_EXPLORE_CASE, an_eval_whose_map_ends_nowhere(), tmp_path / "two"),
    ]
    card = scorecard_of(_at_noon(), scored, model="a-model")

    assert card.passed == sum(1 for one in scored if one.passed)
    assert card.passed + card.failed == len(card.cases)


def _at_noon() -> datetime:
    """One fixed moment, so no test here is about a clock."""
    return datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
