"""Run the four example hypotheses against a real model and score what comes back.

**Structure only, never wording.** Every one of the eight checks below is a count
or a shape: no loops, an ending that names a trade, a reason on every arrow, a
test on every claim, a graded route or an honest refusal, the cache actually
being read back, a named reason for stopping inside the ceiling, and a count with
a page behind it. Not one of them is a judgement about a sentence, because a test
that judges a sentence fails when somebody improves the prompt and passes when
somebody makes it worse in the same words.

**One driver, not a second walk.** The map is grown by `engine.grow` and followed
by `engine.following.Following` — the very loop the stream route and the recorder
use. A harness with a walk of its own would eventually score a pipeline nobody
ships.

**A paid run is never thrown away.** Whatever the score, every run writes
everything it produced into `backend/.runs/` through the recorder's own keeper,
exactly as `make record-demo` does: every proposal with the seconds and the
thinking tokens it took, the receipt, the reason it stopped and the map it built.
A run that cost money and left nothing behind is an afternoon nobody can account
for.

**The spending ceiling bounds the round.** `--cap` is what the whole round may
spend across every case it runs, never what each one may spend on its own: a
running total is carried from case to case, each is handed what is left of the
ceiling, and a case there is nothing left for is not started. Anything else would
let a four-case round spend four times the figure on the command line, and a word
must mean what it says (Kent, G5: a hard stop per run in code at $15).

What this program will not do
-----------------------------
- It will not start with no key, and it will not raise the spending ceiling: the
  argument may lower the figure written in code, never lift it.
- It will not start a case it cannot pay for, and it will not leave that quiet:
  the scorecard says which cases ran, which did not, and what was spent.
- It will not write a scorecard for a run answered by a stand-in. A row in
  `runs/` is a measurement of a model, and a run answered from a list in a test
  file is not one, whatever else it is.
- It will not grade a sentence, ask a model to grade one, or assert on which
  claim the answer named.

**Which model answered is one setting and nowhere else.** `KATALYST_MODEL` is
what the bill is priced against, what the scorecard's own column reports, and
what a reader compares two runs by — so there is no flag here that could name a
third. Two rows from two models are two measurements, never a before-and-after.

The chapter is `spec/generation/evaluation.md`; it names these fields and these
checks, and it is the thing to change first if one of them should move.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

# The case files are YAML because a person writes them by hand and reads them in
# a pull request. The reader comes with the server's own web server
# (`uvicorn[standard]`), so nothing new is installed for this — and if it ever
# went away, this import would fail loudly on a program nobody's build depends
# on rather than quietly anywhere that matters.
import yaml
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Graph, Link, PropositionId, Violation, validate
from katalyst.domain.validity import TERMINAL_KINDS
from katalyst.engine.client import Answerer, a_stand_in_answerer, live_answerer
from katalyst.engine.events import (
    Done,
    Event,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
)
from katalyst.engine.following import Following, receipt_event
from katalyst.engine.grow import Finished, grow
from katalyst.engine.ids import mint_id
from katalyst.engine.outcome import Caps
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.receipt import Receipt as RunningTotal
from katalyst.engine.record import Run, keep
from katalyst.engine.transcript import Transcript
from katalyst.engine.verify import Verdict, verdict
from katalyst.settings import get_settings

HERE = Path(__file__).resolve().parent
"""The `evals/` directory: the cases are beside this file and the runs below it."""

NO_KEY = "This calls a model and spends money, and no key is configured. Nothing was run."
"""What it says when it cannot start at all."""

ANSWERED_BY_A_STAND_IN = (
    "This run was answered by a stand-in named by KATALYST_ANSWERER, not by a "
    "model, so it is a measurement of nothing. The scorecard was printed and no "
    "row was written to evals/runs/."
)
"""Why a run that never reached a model writes no scorecard.

The same rule the recorder keeps for recordings, for the same reason: a file the
repository commits as evidence has to be evidence.
"""

EVAL_RUNS_WRITE_NO_RECORDING = (
    "This was an eval run, so no recording was written. The whole run is kept here all the same."
)
"""What the kept run says about itself, so nobody mistakes it for a recording."""


class Case(BaseModel):
    """One example to run, read from its own file in `cases/`.

    Small on purpose: everything interesting about a case is what the *model* does
    with it, so the file holds the question and nothing about the answer.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        description=(
            "The example's short name, which is also what the launchpad's card and "
            "the recording file are called, so one name follows an example through "
            "all three."
        )
    )
    hypothesis: str = Field(description="The sentence a person would have typed, word for word.")
    door: Literal["explore", "verify"] = Field(
        description=(
            "Which of the two questions this case asks: what does this cause, or "
            "does this get me to a named place."
        )
    )
    target: str | None = Field(
        default=None,
        description=(
            "The place the story is asked whether it reaches, in a person's own "
            "words. Nothing at all on an Explore case."
        ),
    )
    unreachable: bool = Field(
        default=False,
        description=(
            "True on the one case whose destination no mechanism reaches, where the "
            "only honest answer is that there is no route. It is how we know the "
            "pipeline is not inventing a bridge."
        ),
    )
    seed: int = Field(
        description=(
            "The one number the likelihoods on this map would be worked out from. "
            "Written into the file rather than drawn, so two runs of one case "
            "differ only by the model."
        )
    )


class CaseScore(BaseModel):
    """One case's row. Every field is counted off the finished map or read off the receipt.

    Nothing here is a judgement about a sentence. Two fields are derived and say
    so — `searches_per_claim` and `seconds_per_call` are the two fields above each
    of them divided — and if either ever disagrees with what it came from, it is
    the derived one that is wrong.
    """

    model_config = ConfigDict(frozen=True)

    case: str = Field(description="The case file's own short name.")
    door: Literal["explore", "verify"] = Field(description="Which question this case asked.")

    claims: int = Field(description="Claims on the finished map.")
    links: int = Field(description="Arrows on it.")
    rejected: int = Field(
        description="Proposals the map's own rules refused along the way. May be zero."
    )
    endings: int = Field(
        description="Claims that name an instrument or say why there is none to name."
    )
    deepest_layer: int = Field(
        description="How far the map got from the claim it started at, counted in arrows."
    )

    base_rates_kept: int = Field(
        description="Claims whose count of past cases cites a page the research actually returned."
    )
    base_rates_dropped: int = Field(
        description=(
            "Counts the model recalled with no such page. They are dropped, and each "
            "one leaves its note in the transcript."
        )
    )

    documented_links: int = Field(
        description="Arrows backed by an address the search tool itself returned."
    )
    argued_links: int = Field(description="Arrows with a mechanism and no such address.")
    asserted_links: int = Field(
        description=(
            "Arrows with neither. Expected to read zero: every arrow must carry a "
            "mechanism, so a non-zero reading means an arrow reached the map without "
            "going through the accept step."
        )
    )

    verdict: Literal["reached", "no_path"] | None = Field(
        description="What the Verify door answered. Nothing at all on an Explore case."
    )
    path_length: int | None = Field(
        description="Steps in the graded route. Nothing at all when there is no route."
    )

    stopped_for: str = Field(description="The reason the run gave for stopping, in one word.")
    violations: int = Field(
        description=(
            "What the map's own rules still find on the finished map. Expected to "
            "read zero, because the pipeline only ever mints what passed them."
        )
    )

    calls: int = Field(description="Round trips to the model.")
    input_tokens: int = Field(description="Tokens of question read fresh.")
    output_tokens: int = Field(description="Tokens of answer written, thinking included.")
    cache_read_tokens: int = Field(description="Tokens recognised from an earlier call.")
    thinking_tokens: int = Field(
        description=(
            "How many of the written tokens were the model thinking rather than "
            "answering. Read off the transcript's own lines, because it is "
            "deliberately not on the receipt: a number shown in two places is two "
            "numbers that eventually disagree."
        )
    )
    searches: int = Field(
        description="Web searches this run made, off the receipt, which carries them apart."
    )
    searches_per_claim: float = Field(
        description="Searches divided by claims. Derived, and never a source."
    )
    dollars: float = Field(description="What the run cost, at the prices in `engine/pricing.py`.")
    seconds: float = Field(description="How long it took, wall clock.")
    seconds_per_call: float = Field(
        description=(
            "Seconds divided by calls. Derived. Generation is sequential by nature, "
            "so this is the number that sets how long a person waits for a map."
        )
    )


class Scorecard(BaseModel):
    """One run of the cases, and what it cost.

    A scorecard compares runs of **the same model**. Two rows from two models are
    not a before-and-after; they are two measurements, and reading them as one
    would credit a prompt change with a model change or the reverse. That is why
    `model` is on every run.
    """

    model_config = ConfigDict(frozen=True)

    run_at: datetime = Field(
        description="When the run started. Two runs in one day are told apart by it."
    )
    model: str = Field(description="Which model answered.")
    prompt_hash: str = Field(description="The fingerprint of the prompt that produced these rows.")
    cases: tuple[CaseScore, ...] = Field(description="One row per case, in the order they ran.")
    passed: int = Field(description="Cases where all eight checks held.")
    failed: int = Field(description="Cases where at least one did not.")


class Check(BaseModel):
    """One of the eight structural checks, and what it found on one case.

    Not part of the scorecard's own shape — the row records the counts each check
    was read from, and this records which check read them — so it is printed to
    the terminal and never written into a committed file.
    """

    model_config = ConfigDict(frozen=True)

    number: int = Field(description="Which of the eight, as `evaluation.md` numbers them.")
    name: str = Field(description="What it checks, in a few plain words.")
    held: bool = Field(description="Whether it held on this case.")
    why: str = Field(description="What it found, in one plain sentence. Empty when it held.")


class Scored(BaseModel):
    """Everything one case's run produced: its row, its checks, and where it was kept."""

    model_config = ConfigDict(frozen=True)

    score: CaseScore = Field(description="The row this case contributes to the scorecard.")
    checks: tuple[Check, ...] = Field(description="All eight, whether they held or not.")
    kept_at: Path | None = Field(
        default=None, description="Where the whole run was written. Always, whatever the score."
    )

    @property
    def passed(self) -> bool:
        """Say whether every one of the eight checks held on this case."""
        return all(one.held for one in self.checks)


# --- Reading the cases ------------------------------------------------------


def cases(folder: Path | None = None, *, only: str = "") -> tuple[Case, ...]:
    """Read the case files, in the order their names sort.

    Args:
        folder: Where the cases live. `evals/cases/` when not said.
        only: One case's short name, or empty for all of them.

    Returns:
        The cases, in a settled order so two runs list them the same way.

    Raises:
        ValueError: If a name was asked for that no file answers to. Naming a
            case that does not exist is a typing mistake, and a run that quietly
            scored nothing would look like a run that scored everything.
    """
    where = folder or HERE / "cases"
    found = tuple(
        Case.model_validate(yaml.safe_load(one.read_text(encoding="utf-8")))
        for one in sorted(where.glob("*.yaml"))
    )
    if not only:
        return found
    wanted = tuple(one for one in found if one.id == only)
    if not wanted:
        raise ValueError(
            f"There is no case called {only!r}. The ones in {where} are: "
            f"{', '.join(one.id for one in found)}."
        )
    return wanted


# --- Running one case -------------------------------------------------------


def run_one(
    case: Case,
    *,
    answerer: Answerer,
    cap: float,
    on: date | None = None,
    keep_in: Path | None = None,
    say: Callable[[str], None] | None = None,
) -> Scored:
    """Run one case against a model, keep the whole run, and score what it built.

    Args:
        case: The case to run.
        answerer: Whatever the run asks its questions of.
        cap: What this case may spend — **what is left of the round's ceiling**,
            which `main` works out and hands in. Never above the figure in code.
        on: The day to run as. Today when not said.
        keep_in: Where to write what the run produced. `backend/.runs/` when not
            said, or wherever `KATALYST_RUNS` says.
        say: Where progress goes. The terminal's error stream when not said.

    Returns:
        The row, the eight checks, and where the run was kept.
    """
    telling = _telling(say)
    ceiling = min(cap, Caps().dollars)
    today = on or datetime.now(tz=UTC).date()

    telling(f"{case.id}: {case.hypothesis!r}")
    telling(f"  {case.door} door, ceiling ${ceiling:.2f}, seed {case.seed}, as of {today}")
    if case.target is not None:
        telling(f"  asking whether the story reaches: {case.target!r}")

    working = Transcript(
        generation_id=mint_id(),
        hypothesis=case.hypothesis,
        target=case.target,
        seed=case.seed,
        on=today,
        mode="live",
    )
    written: list[Event] = [
        GenerationStarted(
            generation_id=working.generation_id,
            seed=case.seed,
            hypothesis=case.hypothesis,
            target=case.target,
        )
    ]

    # The one driver. `Following` folds every answer into the transcript and onto
    # the running total **before** its event is handed over, so a run that breaks
    # part way through still says what it spent.
    watching = Following(working)
    walking = grow(
        case.hypothesis,
        target=case.target,
        answerer=answerer,
        on=today,
        caps=Caps(dollars=ceiling),
        never_seen=watching.never_seen,
    )
    try:
        for event in watching.follow(walking):
            written.append(event)
            telling(f"  {_what_landed(event)}")
    finally:
        walking.close()
    if watching.broke is not None:
        telling("  the run stopped for a reason nobody chose; see the log above.")

    finished = watching.finished
    graded = (
        verdict(finished.graph, finished.destination)
        if finished is not None and finished.graph is not None and finished.destination is not None
        else None
    )
    written.extend(
        _closing(finished, watching.spent, watching.seconds, answerer.effort_used, graded)
    )

    run = Run(
        example=case.id,
        hypothesis=case.hypothesis,
        seed=case.seed,
        on=today,
        seconds=watching.seconds,
        events=tuple(written),
        transcript=watching.ended(),
        finished=finished,
        effort=answerer.effort_used,
        broke=watching.broke,
    )
    # The recorder's own keeper, so an eval run and a recorded run leave the same
    # kind of file behind and nobody has to learn two shapes.
    kept_at = keep(run, (EVAL_RUNS_WRITE_NO_RECORDING,), folder=keep_in)
    telling(f"  the whole run is on disk at {kept_at}")

    return Scored(
        score=row_for(case, run, watching.spent, graded),
        checks=tuple(checks_on(case, run, watching.spent, ceiling, graded)),
        kept_at=kept_at,
    )


def _closing(
    finished: Finished | None,
    spent: RunningTotal,
    seconds: float,
    effort: str,
    graded: Verdict | None,
) -> tuple[Event, ...]:
    """The events that close a generation: the verdict, the receipt and the ending.

    An eval keeps the events so that a run nobody can afford to repeat can still
    be read. It does **not** work the likelihoods through the map: nothing this
    harness scores is a likelihood, and a scorecard that quietly ran the engine
    would be measuring two things at once.

    Args:
        finished: What the walk handed back, or nothing when it never got there.
        spent: The running total, which is what the receipt is built from.
        seconds: How long the run took, wall clock.
        effort: How hard the model was asked to try, as a plain word.
        graded: The Verify door's answer, when there was a destination.

    Returns:
        The closing events, in the order the stream's grammar wants them.
    """
    if finished is None:
        return ()
    closing: list[Event] = []
    if graded is not None:
        closing.append(graded)
    closing.append(receipt_event(spent, seconds=seconds, effort=effort))
    closing.append(
        Done(
            reason=finished.reason,
            claims=finished.claims,
            links=finished.links,
            rejected=finished.refused,
        )
    )
    return tuple(closing)


# --- Counting what is on the finished map -----------------------------------


def row_for(case: Case, run: Run, spent: RunningTotal, graded: Verdict | None) -> CaseScore:
    """Count one finished run into the row it contributes to the scorecard.

    Args:
        case: The case that was run.
        run: Everything the run produced.
        spent: What it cost.
        graded: The Verify door's answer, when there was a destination.

    Returns:
        One row. A run that never built a map still gets one, because a row that
        says a map was never built is more use than no row at all.
    """
    built = run.finished.graph if run.finished is not None else None
    claims = () if built is None else built.propositions
    arrows: Sequence[Link] = () if built is None else built.links
    thinking = sum(one.thinking_tokens for one in run.transcript.lines)
    return CaseScore(
        case=case.id,
        door=case.door,
        claims=len(claims),
        links=len(arrows),
        rejected=0 if run.finished is None else run.finished.refused,
        endings=sum(1 for one in claims if one.kind in TERMINAL_KINDS),
        deepest_layer=_deepest_layer(built),
        base_rates_kept=sum(
            1 for one in claims if one.base_rate is not None and one.base_rate.sources
        ),
        base_rates_dropped=sum(
            1 for one in run.transcript.lines if one.no_reference_class is not None
        ),
        documented_links=sum(1 for one in arrows if one.provenance == "documented"),
        argued_links=sum(1 for one in arrows if one.provenance == "argued"),
        asserted_links=sum(1 for one in arrows if one.provenance == "asserted"),
        verdict=None if graded is None else graded.kind,
        path_length=None if graded is None or not graded.path else len(graded.path) - 1,
        stopped_for="" if run.finished is None else run.finished.reason,
        violations=0 if built is None else len(validate(built)),
        calls=spent.calls,
        input_tokens=spent.input_tokens,
        output_tokens=spent.output_tokens,
        cache_read_tokens=spent.cache_read_tokens,
        thinking_tokens=thinking,
        searches=spent.searches,
        searches_per_claim=_divided(spent.searches, len(claims)),
        dollars=spent.dollars,
        seconds=run.seconds,
        seconds_per_call=_divided(run.seconds, spent.calls),
    )


def _divided(above: float, below: int) -> float:
    """Divide one column by another, and say nothing rather than divide by nothing."""
    return above / below if below else 0.0


def _deepest_layer(graph: Graph | None) -> int:
    """How far the map got from the claim it started at, counted in arrows.

    The **fewest** arrows to the furthest claim the story reaches, which is the
    same way the walk itself counts a layer when it decides a line has run out of
    room — so this column and the depth cap that ends a run are the same
    measurement, and a map that stopped at the cap reads the cap's own number.

    A feedback arrow is set aside, exactly as the map's own loop check and the
    arithmetic set it aside: nothing is worked through one in this version, so
    nothing reaches a claim along one.

    Args:
        graph: The finished map, or nothing when none was built.

    Returns:
        How many arrows from the starting claim to the furthest one it reaches.
        Zero on a map of one claim, and zero when there is no map.
    """
    if graph is None:
        return 0
    present = {one.id for one in graph.propositions}
    onward: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        if arrow.reflexive or arrow.source not in present or arrow.target not in present:
            continue
        onward.setdefault(arrow.source, []).append(arrow.target)
    deepest = 0
    reached = {graph.hypothesis_id}
    waiting = [(graph.hypothesis_id, 0)]
    while waiting:
        here, layer = waiting.pop(0)
        deepest = max(deepest, layer)
        for onto in onward.get(here, []):
            if onto not in reached:
                reached.add(onto)
                waiting.append((onto, layer + 1))
    return deepest


# --- The eight checks -------------------------------------------------------


def checks_on(
    case: Case, run: Run, spent: RunningTotal, ceiling: float, graded: Verdict | None
) -> list[Check]:
    """Run the eight structural checks over one finished run.

    Every one is a count or a shape. Checks 1 to 4 are the map's own rules — the
    same rules the pipeline refused proposals with — asked the other way round:
    *does the model's own output satisfy them, on a map nobody hand-wrote?*

    **Five of the eight are about the map and three are about the run**, and that
    line matters when a run built no map at all: the five say so, and the other
    three are still read, because "it could not say why it stopped" is worth
    knowing about a run that produced nothing.

    Args:
        case: The case that was run.
        run: Everything the run produced.
        spent: What it cost.
        ceiling: What it was allowed to spend.
        graded: The Verify door's answer, when there was a destination.

    Returns:
        All eight, in order, each saying what it found.
    """
    built = run.finished.graph if run.finished is not None else None
    found = validate(built) if built is not None else []
    return [
        _about_the_map(1, built, lambda: _from_the_rules(1, found, ("cycle",))),
        _about_the_map(2, built, lambda: _from_the_rules(2, found, ("no_terminal",))),
        _about_the_map(
            3,
            built,
            lambda: _from_the_rules(3, found, ("missing_rationale", "documented_without_source")),
        ),
        _about_the_map(4, built, lambda: _from_the_rules(4, found, ("missing_resolution",))),
        _the_verify_door(case, graded),
        _the_cache_was_read(run),
        _it_stopped_inside_its_ceiling(run, spent, ceiling),
        _about_the_map(8, built, lambda: _every_count_has_a_page(built)),  # type: ignore[arg-type]
    ]


NO_MAP = "This run built no map, so there is nothing to check."
"""What a check about the map says when the run never built one.

Not held, and not silently skipped: a check nobody could read is a check nobody
should be told held.
"""


def _about_the_map(number: int, built: Graph | None, reading: Callable[[], Check]) -> Check:
    """Read one check that needs a map, or say plainly that there is none to read."""
    if built is None:
        return Check(number=number, name=_named(number), held=False, why=NO_MAP)
    return reading()


_EIGHT: tuple[tuple[int, str], ...] = (
    (1, "no loops"),
    (2, "an ending that names a trade, or says why there is none"),
    (3, "a reason on every arrow, and a page behind every documented one"),
    (4, "a test and a judge on every claim"),
    (5, "a graded route, or an honest statement that there is none"),
    (6, "the cache was read back"),
    (7, "a named reason for stopping, inside the ceiling"),
    (8, "a page behind every count of past cases"),
)
"""The eight checks, numbered as `evaluation.md` numbers them, with their names."""


def _named(number: int) -> str:
    """The name of one of the eight, by its number."""
    return next(name for one, name in _EIGHT if one == number)


def _from_the_rules(number: int, found: Sequence[Violation], codes: tuple[str, ...]) -> Check:
    """Read one check off what the map's own rules said about the finished map.

    The rules' own sentences are carried through word for word rather than
    rewritten here: the thing that refused the proposals is the thing that should
    say what is wrong with the map they built.

    Args:
        number: Which of the eight this is.
        found: Every fault the rules found.
        codes: The rules' own codes this check is about.

    Returns:
        The check, carrying the rules' own sentences when it did not hold.
    """
    hit = [one for one in found if one.code in codes]
    return Check(
        number=number,
        name=_named(number),
        held=not hit,
        why=" ".join(one.message for one in hit),
    )


def _the_verify_door(case: Case, graded: Verdict | None) -> Check:
    """Check that a Verify case came back with a graded route or an honest refusal.

    **Nothing here reads which claim the answer named.** Which route the story
    took and which claim it came nearest to are the model's answer, and grading
    them would be grading wording. What is checked is that one of the only two
    honest answers came back — and, on the case whose destination nothing reaches,
    that it was the second one.

    Args:
        case: The case that was run.
        graded: The Verify door's answer, when there was a destination.

    Returns:
        The check. An Explore case holds it by having no door to answer.
    """
    if case.door == "explore":
        return Check(number=5, name=_named(5), held=True, why="")
    if graded is None:
        return Check(
            number=5,
            name=_named(5),
            held=False,
            why="This case names a destination and the run came back with no answer about it.",
        )
    if graded.kind == "reached" and not graded.path:
        return Check(
            number=5,
            name=_named(5),
            held=False,
            why="The answer says the story reaches the destination and names no route to it.",
        )
    if case.unreachable and graded.kind != "no_path":
        return Check(
            number=5,
            name=_named(5),
            held=False,
            why=(
                "Nothing reaches this destination, and the run says it does. Either a "
                "mechanism genuinely exists and somebody should read it, or a bridge "
                "was invented."
            ),
        )
    return Check(number=5, name=_named(5), held=True, why="")


def _the_cache_was_read(run: Run) -> Check:
    """Check that the service read something back out of its cache after the first call.

    The standing half of every request is written into the service's cache on the
    first call and read back at about a tenth of the price on every call after it.
    A run whose cache reads stay at nothing is a bug in how the request is put
    together, not a slow day — so this is a check rather than a column somebody
    might glance at.

    Args:
        run: Everything the run produced.

    Returns:
        The check.
    """
    after_the_first = run.transcript.lines[1:]
    read_back = sum(one.cache_read_tokens for one in after_the_first)
    if not after_the_first:
        return Check(
            number=6,
            name=_named(6),
            held=False,
            why=(
                "This run made one call, so there was never a second one for the "
                "cache to be read back on."
            ),
        )
    return Check(
        number=6,
        name=_named(6),
        held=read_back > 0,
        why=""
        if read_back > 0
        else (
            f"None of the {len(after_the_first)} calls after the first read anything back "
            "out of the cache."
        ),
    )


def _it_stopped_inside_its_ceiling(run: Run, spent: RunningTotal, ceiling: float) -> Check:
    """Check that the run stopped for a reason somebody can read, inside its ceiling.

    Stopping because the money ran out is a decision rather than a fault, and it
    is a named reason like any other — so a run that reached its ceiling holds
    this check. What fails it is a run that cannot say why it stopped, or one that
    spent more than it was allowed to before it noticed.

    Args:
        run: Everything the run produced.
        spent: What it cost.
        ceiling: What it was allowed to spend.

    Returns:
        The check.
    """
    reason = "" if run.finished is None else run.finished.reason
    if not reason:
        return Check(
            number=7, name=_named(7), held=False, why="This run cannot say why it stopped."
        )
    if spent.dollars > ceiling:
        return Check(
            number=7,
            name=_named(7),
            held=False,
            why=(
                f"This run was allowed ${ceiling:.2f} and spent ${spent.dollars:.2f}. "
                "A round's calls all go out together, so the ceiling is passed by at "
                "most the calls in flight when it was reached — more than that is a bug."
            ),
        )
    return Check(number=7, name=_named(7), held=True, why="")


def _every_count_has_a_page(graph: Graph) -> Check:
    """Check that every count of past cases on the finished map cites a page research returned.

    A count with no page behind it reads as measured however it is marked, so the
    accept step drops one and leaves its note in the transcript. A count that
    reached the map without a page is therefore not a worse map; it is evidence
    that a claim got past the accept step, which is a fault of a different order.

    Args:
        graph: The finished map.

    Returns:
        The check.
    """
    bare = [
        one.claim
        for one in graph.propositions
        if one.base_rate is not None and not one.base_rate.sources
    ]
    return Check(
        number=8,
        name=_named(8),
        held=not bare,
        why=""
        if not bare
        else (
            f"{len(bare)} claim{'' if len(bare) == 1 else 's'} carry a count of past "
            "cases with no page behind it."
        ),
    )


# --- Printing and writing the scorecard --------------------------------------


def scorecard_of(run_at: datetime, scored: Sequence[Scored], model: str) -> Scorecard:
    """Gather the cases that ran into one scorecard.

    Args:
        run_at: When the run started.
        scored: What each case produced, in the order they ran.
        model: Which model answered. On every scorecard because two rows from two
            models are two measurements rather than a before-and-after.

    Returns:
        The scorecard.
    """
    return Scorecard(
        run_at=run_at,
        model=model,
        prompt_hash=prompt_hash(),
        cases=tuple(one.score for one in scored),
        passed=sum(1 for one in scored if one.passed),
        failed=sum(1 for one in scored if not one.passed),
    )


ABOUT_THE_WHOLE_RUN: tuple[str, ...] = ("run_at", "model", "prompt_hash")
"""The three columns that read the same on every row: when, which model, which prompt.

Repeated on each row rather than written once at the top of the file, because a
second run on the same day appends to that same file and a heading would then be
a heading over somebody else's rows.
"""

COLUMNS: tuple[str, ...] = (*ABOUT_THE_WHOLE_RUN, *CaseScore.model_fields)
"""The scorecard's columns, in order: when and what, then the case's own row.

Read off `CaseScore` itself rather than written out again, so a field added there
cannot be missing here.
"""


def as_a_table(card: Scorecard) -> list[str]:
    """Lay the scorecard out for a terminal, one row per field and one column per case.

    Turned on its side because a row per case would be twenty-five columns wide
    and nobody reads that. A person comparing two runs reads down a column.

    Args:
        card: The scorecard.

    Returns:
        The lines to print.
    """
    heads = ["", *(one.case for one in card.cases)]
    body = [
        [named, *(_as_text(getattr(one, named)) for one in card.cases)]
        for named in CaseScore.model_fields
    ]
    widths = [max(len(row[at]) for row in [heads, *body]) for at in range(len(heads))]
    lines = [_laid_out(heads, widths), _laid_out(["-" * one for one in widths], widths)]
    lines += [_laid_out(row, widths) for row in body]
    return lines


def _laid_out(row: Sequence[str], widths: Sequence[int]) -> str:
    """Pad one row of the table out to the column widths, with the first left-aligned."""
    numbers = zip(row[1:], widths[1:], strict=True)
    return "  ".join([row[0].ljust(widths[0]), *(one.rjust(width) for one, width in numbers)])


def _as_text(value: object) -> str:
    """Write one field the way a person reads it, and an absence as a dash.

    Two decimals on anything fractional, because the columns a person compares
    between runs — dollars, seconds a call, searches a claim — are all fractional
    and sixteen digits of them is noise.
    """
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def write_tsv(card: Scorecard, folder: Path | None = None) -> Path:
    """Write one row per case into `runs/<date>.tsv`, appending to a file already there.

    Tab-separated because it opens in a spreadsheet and still reads as text in a
    difference between two commits. A second run on the same day appends; its rows
    are told apart by `run_at` and by the prompt's fingerprint.

    Args:
        card: The scorecard to write.
        folder: Where to write it. `evals/runs/` when not said.

    Returns:
        The file that was written.
    """
    where = folder or HERE / "runs"
    where.mkdir(parents=True, exist_ok=True)
    written = where / f"{card.run_at.date().isoformat()}.tsv"
    already = written.exists()
    lines = [] if already else ["\t".join(COLUMNS)]
    for one in card.cases:
        lines.append("\t".join(_as_a_cell(card, one, named) for named in COLUMNS))
    with written.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    return written


def _as_a_cell(card: Scorecard, score: CaseScore, named: str) -> str:
    """Write one cell of the tab-separated file, empty where there is no value.

    Deliberately not the terminal's dash: a file a spreadsheet opens should have
    an empty cell where there is nothing, and a tab is the only thing in here that
    separates two of them, so nothing written may contain one.
    """
    value = getattr(card if named in ABOUT_THE_WHOLE_RUN else score, named)
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).replace("\t", " ")


# --- Saying what happened ----------------------------------------------------


def _telling(say: Callable[[str], None] | None) -> Callable[[str], None]:
    """Where progress goes: the terminal's error stream unless a caller says otherwise."""
    if say is not None:
        return say

    def to_the_terminal(line: str) -> None:
        print(line, file=sys.stderr, flush=True)

    return to_the_terminal


ENOUGH_OF_A_CLAIM = 64
"""How much of a claim a progress line shows before trimming it."""


def _what_landed(event: Event) -> str:
    """One short line saying what just landed, so nine silent minutes are legible.

    Args:
        event: What the walk handed over.

    Returns:
        One line for the terminal.
    """
    if isinstance(event, ProposalAccepted):
        claim = event.proposition.claim if event.proposition is not None else ""
        what = _trimmed(claim) if claim else "an arrow between two claims already on the map"
        return f"{event.at:>3}  accepted  {what}"
    if isinstance(event, ProposalRejected):
        codes = ", ".join(one.code for one in event.violations)
        return f"{event.at:>3}  refused   {codes or 'the model gave us nothing to check'}"
    return f"an event of a kind this line did not expect: {type(event).__name__}"


def _trimmed(claim: str) -> str:
    """Show enough of a claim to follow the run, and no more."""
    tidied = " ".join(claim.split())
    if len(tidied) <= ENOUGH_OF_A_CLAIM:
        return tidied
    return tidied[: ENOUGH_OF_A_CLAIM - 1].rstrip() + "…"


def what_the_round_spent(
    ceiling: float, spent: float, ran: Sequence[Scored], not_started: Sequence[Case]
) -> str:
    """Say in one plain sentence what the round cost and which cases it got to.

    **The ceiling bounds the round, not each case** (Kent, G5: a hard stop per run
    in code at $15). Each case may spend only what is left of it, and when there
    is nothing left the cases still waiting are not started — so the scorecard has
    to say which ones those were, or a reader would take four columns of silence
    for four cases that had nothing to report.

    Args:
        ceiling: What the whole round was allowed to spend.
        spent: What it actually spent, added up across the cases that ran.
        ran: What each case that ran produced, in the order they ran.
        not_started: The cases there was no money left for, in the order they
            would have run.

    Returns:
        One sentence for the terminal, beneath the table.
    """
    names = ", ".join(one.score.case for one in ran) or "no case at all"
    if not not_started:
        return f"The round spent ${spent:.2f} of its ${ceiling:.2f} ceiling, over {names}."
    left_out = ", ".join(one.id for one in not_started)
    one_of_them = len(not_started) == 1
    return (
        f"The round spent ${spent:.2f} of its ${ceiling:.2f} ceiling on {names} and stopped "
        f"there: {left_out} {'was' if one_of_them else 'were'} never started, so "
        f"{'it is' if one_of_them else 'they are'} on no row of this scorecard."
    )


def _how_it_went(scored: Sequence[Scored]) -> list[str]:
    """Name every check that did not hold, case by case, in plain sentences.

    The committed row carries the counts each check was read from; which check
    read them is said here, on the terminal, where somebody is looking.

    Args:
        scored: What each case produced.

    Returns:
        The lines to print. Empty when every check held everywhere.
    """
    lines: list[str] = []
    for one in scored:
        missed = [check for check in one.checks if not check.held]
        if not missed:
            continue
        lines.append(f"{one.score.case}: {len(missed)} of the eight checks did not hold")
        lines += [f"  {check.number}. {check.name} — {check.why}".rstrip(" —") for check in missed]
    return lines


# --- The command line --------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the cases, print the scorecard, write the day's file, and say what failed.

    **The spending ceiling is the round's, not each case's.** One running total is
    carried across the cases; each is handed what is left of the ceiling, and the
    cases there is nothing left for are never started. The sentence beneath the
    table names them.

    Returns:
        0 when every check held on every case **and** every case ran, 1 otherwise
        — so this is usable from a script even though nothing schedules it. A
        round that stopped short has not scored what it did not run, and a zero
        there would say it had.
    """
    asking = argparse.ArgumentParser(
        prog="eval",
        description=(
            "Run the example hypotheses live and score what comes back on structure. "
            "Spends money; needs a key. Every run is kept under backend/.runs/ "
            "whatever it scores."
        ),
    )
    asking.add_argument(
        "--only", default="", help="One case's short name. All of them when left out."
    )
    asking.add_argument(
        "--cap",
        type=float,
        default=Caps().dollars,
        help=(
            "What the whole round may spend, in dollars, across every case it runs. "
            "Can only lower the figure in code."
        ),
    )
    asking.add_argument(
        "--effort",
        default="",
        choices=["", "low", "medium", "high", "xhigh", "max"],
        help=(
            "How hard the model tries, pinned for the whole of this run. Empty "
            "leaves the service's own default and sends nothing — the same effort "
            "the recordings are made at, so a scorecard measures the maps a "
            "reviewer actually sees."
        ),
    )
    said = asking.parse_args(argv)

    try:
        wanted = cases(only=said.only)
    except ValueError as unknown:
        print(unknown, file=sys.stderr)
        return 1

    # The stand-in is asked for here and nowhere else, exactly as the recorder
    # asks for it: a seam that answered a reader from a test file would be a map
    # that looked generated.
    answerer = a_stand_in_answerer() or live_answerer(effort=said.effort or None)
    if answerer is None:
        print(NO_KEY, file=sys.stderr)
        return 1

    run_at = datetime.now(tz=UTC)
    # **The ceiling bounds the round, not each case.** One running total across
    # the cases: each may spend only what is left of it, and when nothing is left
    # the rest are not started. Handing every case the whole figure would let a
    # four-case round spend four times what the argument says, which is the one
    # word this argument has to mean.
    ceiling = min(said.cap, Caps().dollars)
    scored: list[Scored] = []
    spent = 0.0
    for one in wanted:
        left = ceiling - spent
        if left <= 0.0:
            break
        scored.append(run_one(one, answerer=answerer, cap=left))
        spent += scored[-1].score.dollars
    not_started = wanted[len(scored) :]

    # The same setting the bill was priced against, so the row's dollars and the
    # model beside them can never name two different models.
    card = scorecard_of(run_at, scored, model=get_settings().KATALYST_MODEL)

    for line in as_a_table(card):
        print(line)
    print(f"\n{card.passed} of {len(card.cases)} cases held all eight checks.")
    print(what_the_round_spent(ceiling, spent, scored, not_started))
    for line in _how_it_went(scored):
        print(line, file=sys.stderr)

    if get_settings().KATALYST_ANSWERER:
        print(ANSWERED_BY_A_STAND_IN, file=sys.stderr)
        return 1
    written = write_tsv(card)
    print(f"wrote the scorecard at {written}", file=sys.stderr)
    # A round that ran out of money before it reached every case has not scored
    # them, so it never comes back saying all is well.
    return 0 if card.failed == 0 and not not_started else 1


# **The guard is the last thing in this file, and must stay there.** Started as a
# program, `main()` runs before anything written below it exists — which cost a
# 26-minute paid run on 2026-09-20, in the recorder, for exactly that reason.
# Imported by a test every name is defined first, so nothing catches it but
# starting the program, which `test_the_eval_harness_as_a_program.py` does.
if __name__ == "__main__":
    raise SystemExit(main())
