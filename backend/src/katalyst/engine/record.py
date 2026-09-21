"""Running an example for real: what it cost, what it built, and — sometimes — a recording.

`make record-demo` and `make run-demo` both come here. Both call a model and both
spend real money, and the difference between them is only what is written at the
end.

**A paid run is never thrown away.** Whatever becomes of it, the run prints its
whole receipt and its reason for stopping as plain lines, and writes everything it
produced — every proposal with the seconds and the thinking tokens it took, the
receipt, the reason, the prompt's fingerprint and the finished map — into
`backend/.runs/`, which is not committed. A run that cost money and left nothing
behind is a measurement nobody can quote and an afternoon nobody can account for.

**A recording is a narrower thing**, and the rules around it do not move: only
this module ever writes one, nobody edits one afterwards, and a run that shows no
refusal is run again rather than repaired. Those checks now decide whether a run
*also* becomes a recording — never whether it is kept.

What it will not do
-------------------
It refuses to start with no key. It will not raise the spending ceiling: the
argument may lower the figure written in code, never lift it, because a cap a
caller can raise is not a cap.

The one scripted intervention
-----------------------------
Each recording carries **one scripted intervention** — the "…but X happens" its
card offers — drafted live at record time by `expand.add_a_claim`, which needed
no shape of its own: one starting-claim call writes the sentence, then ordinary
arrows join it one per call. A run whose insert could not be drafted does not
become a recording, because a keyless reviewer would press the card's button and
get nothing. There is no flag to write the file anyway: the whole point of the
file is that the button works (Kent, 2026-09-20).
"""

import argparse
import json
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Graph, Insert
from katalyst.engine import events
from katalyst.engine.client import Answerer, a_stand_in_answerer, live_answerer
from katalyst.engine.events import (
    Done,
    Event,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
)
from katalyst.engine.expand import add_a_claim
from katalyst.engine.following import Following, receipt_event
from katalyst.engine.grow import Finished, grow
from katalyst.engine.ids import mint_id, mint_seed
from katalyst.engine.outcome import Caps, Outcome
from katalyst.engine.pricing import PRICES_READ_ON
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.receipt import Receipt as RunningTotal
from katalyst.engine.receipt import fold, nothing_spent_yet
from katalyst.engine.replay import faults_in, where_they_live
from katalyst.engine.replay import read as read_recording
from katalyst.engine.transcript import Transcript, TranscriptLine
from katalyst.engine.verify import verdict
from katalyst.settings import get_settings

THE_FOUR = {
    "hormuz": "The Strait of Hormuz is going to open next week.",
    "midterms": "Republicans win the House but Democrats take the senate during the Midterm.",
    "export-controls": "Models more capable than Fable get export restricted by the United States.",
    "photonics": "Photonic chips get adopted faster than expected.",
}
"""The four example hypotheses, word for word from the assignment.

**The keys are the four the launchpad's cards use**, so a card and a recording
find each other by the same name; the sentence is what a run is asked for and,
letter for letter, what a replay is matched on. Change either half here and
nowhere else.
"""

KEPT_RUNS = Path(__file__).resolve().parents[3] / ".runs"
"""Where every paid run is written when nothing else is said.

Not committed, and not `backend/recordings/`: those two are different things.
A recording is a file the product plays back and the build checks; this is the
record of an afternoon's spending, kept so that nobody has to pay twice to answer
the same question.
"""


def where_runs_are_kept() -> Path:
    """Where this running program writes what its runs produced.

    Read when asked rather than when this module was written, so that a test
    starting the recorder as a program can point it somewhere throwaway. Nothing
    may overwrite `backend/.runs/`: it holds what real money bought.

    Returns:
        The folder, from the settings when they name one and `backend/.runs/`
        when they do not.
    """
    said = get_settings().KATALYST_RUNS
    return Path(said) if said else KEPT_RUNS


NOT_FINISHED_YET = "This run is not finished yet."
"""What the first write of a run says, before anybody knows how it ends.

Overwritten by the second write, in the same file. A file still carrying this
sentence is a run that was interrupted between the two — a terminal closed, a
machine that went to sleep — and what is in it is everything that was paid for.
"""

DOLLARS_EVERY = 4
"""How often the running total is printed while a run is going.

Often enough that nine silent minutes are legible, rarely enough that the lines
about what was proposed are still what the eye lands on.
"""

ENOUGH_OF_A_CLAIM = 64
"""How much of a claim a progress line shows before trimming it."""

NO_KEY = "This calls a model and spends money, and no key is configured. Nothing was run."
"""What it says when it cannot start at all."""

THE_ONE_THEY_OFFER = {
    "hormuz": "…but Iran is struck the next day",
    "midterms": "…but the Senate result is contested into January",
    "export-controls": "…but the restrictions are stayed by a court within a month",
    "photonics": "…but the packaging supply chain cannot keep up",
}
"""The one "…but X happens" each card offers a reviewer with no key.

Product text: it is what the button fills the field with, word for word, and what
a keyless run matches on letter for letter. One per example, drafted live when
the recording is made and answered from the file afterwards.
"""


class KeptRun(BaseModel):
    """Everything one paid run produced, kept whether or not it became a recording.

    Written to `backend/.runs/` and never committed. It carries more than a
    recording does on purpose: the seconds and the thinking tokens behind every
    call, which are on no event and which a recording does not store, because the
    whole reason to keep this is so that a run nobody can afford to repeat can
    still be read.
    """

    model_config = ConfigDict(frozen=True)

    example: str = Field(description="Which of the four this was.")
    hypothesis: str = Field(description="The sentence it was asked for.")
    seed: int = Field(description="The one number its likelihoods were worked out from.")
    on: date = Field(description="The day it ran, which is its map's day zero.")
    prompt_hash: str = Field(description="The fingerprint of the prompt it ran against.")
    seconds: float = Field(description="How long the whole run took, wall clock.")
    became_a_recording: bool = Field(
        description="Whether this run also passed the checks a recording has to pass."
    )
    faults: tuple[str, ...] = Field(
        default=(), description="Why it did not, in plain sentences. Empty when it did."
    )
    transcript: Transcript = Field(
        description="Every proposal, with what each one cost and how long it took."
    )
    done: Done | None = Field(default=None, description="Why it stopped, and what it built.")
    receipt: Receipt | None = Field(default=None, description="What it cost.")
    graph: Graph | None = Field(default=None, description="The map it built.")
    events: tuple[Event, ...] = Field(
        default=(),
        description=(
            "The events it produced, which are what a recording would have held. "
            "Kept so a run that failed a recording's checks can still be read."
        ),
    )
    broke: str | None = Field(
        default=None,
        description=(
            "One plain sentence, when the run stopped for a reason nobody chose. "
            "A crash is not a reason to lose what was already paid for, so this "
            "file is written the moment a generation ends and again once the "
            "scripted intervention has been drafted (Kent, 2026-09-20)."
        ),
    )


class Run(BaseModel):
    """What one run of the model produced, before anybody decides what to do with it."""

    model_config = ConfigDict(frozen=True)

    example: str
    hypothesis: str
    seed: int
    on: date
    seconds: float
    events: tuple[Event, ...]
    transcript: Transcript
    finished: Finished | None
    scripted_insert: Insert | None = None
    broke: str | None = None
    """One plain sentence when the run stopped for a reason nobody chose."""
    kept_at: Path | None = None
    """Where it was written the moment its generation ended, before the insert."""


def run_one(
    example: str,
    *,
    answerer: Answerer,
    cap: float,
    on: date | None = None,
    seed: int | None = None,
    keep_in: Path | None = None,
    say: Callable[[str], None] | None = None,
) -> Run:
    """Run one example against a model, telling the terminal what is happening.

    Nine minutes with nothing on screen is nine minutes nobody can tell from a
    program that has stopped, so each proposal prints as it lands and the running
    total prints every few calls.

    Args:
        example: The short name of the example.
        answerer: Whatever the run asks its questions of.
        cap: What this run may spend. Never above the figure in code.
        on: The day to run as. Today when not said.
        seed: The seed to use. A minted one when not said.
        keep_in: Where to write what the run produced, as it produces it.
            `backend/.runs/` when not said, or wherever `KATALYST_RUNS` says. A
            test passes a throwaway directory: that folder holds what real money
            bought and nothing may overwrite it.
        say: Where progress goes. The terminal's error stream when not said.

    Returns:
        Everything the run produced, whatever anybody does with it next.
    """
    telling = _telling(say)
    hypothesis = THE_FOUR[example]
    ceiling = min(cap, Caps().dollars)
    today = on or datetime.now(tz=UTC).date()
    its_seed = seed if seed is not None else mint_seed()

    telling(f"{example}: {hypothesis!r}")
    telling(f"  at a ceiling of ${ceiling:.2f}, seed {its_seed}, as of {today}")

    started = time.monotonic()
    # The running total, folded here as each answer lands. It used to be read off
    # the transcript's own receipt, which is only filled in at the very end — so
    # every progress line said $0.00 while the run spent real money.
    so_far = nothing_spent_yet()
    working = Transcript(
        generation_id=mint_id(),
        hypothesis=hypothesis,
        target=None,
        seed=its_seed,
        on=today,
        mode="live",
    )
    written: list[Event] = [
        GenerationStarted(generation_id=working.generation_id, seed=its_seed, hypothesis=hypothesis)
    ]

    # The same follower the route uses. One loop, one running receipt, one
    # answer to "what did this cost" (2026-09-20).
    watching = Following(working)
    walking = grow(
        hypothesis,
        answerer=answerer,
        on=today,
        caps=Caps(dollars=ceiling),
        never_seen=watching.never_seen,
    )
    try:
        for event in watching.follow(walking):
            written.append(event)
            telling(_progress(event, watching.working.lines[-1]))
            if watching.at % DOLLARS_EVERY == 0:
                telling(_so_far(watching.spent, watching.working, watching.seconds))
    finally:
        walking.close()
    if watching.broke is not None:
        telling("  the run stopped for a reason nobody chose; see the log above.")
    working, so_far, finished, broke = (
        watching.working,
        watching.spent,
        watching.finished,
        watching.broke,
    )

    # **The generation is on disk before anything else is asked for.** A paid run
    # is never discarded, and a crash is no exception: everything from here on is
    # another model call, and a bug after one of them used to take the whole
    # afternoon's spending with it (Kent, 2026-09-20).
    so_far_a_run = _a_run(
        example,
        hypothesis,
        its_seed,
        today,
        started,
        (*written, *_closing_events(finished, so_far, started)),
        _with_the_ending(working, finished),
        finished,
    ).model_copy(update={"broke": broke})
    kept_at = keep(so_far_a_run, (NOT_FINISHED_YET,), folder=keep_in)
    telling(f"  what it has so far is on disk at {kept_at}")
    so_far_a_run = so_far_a_run.model_copy(update={"kept_at": kept_at})
    if broke is not None:
        return so_far_a_run

    drafted: Insert | None = None
    if finished is not None and finished.graph is not None:
        telling(f"  drafting the one intervention the card offers: {THE_ONE_THEY_OFFER[example]!r}")
        try:
            drafted, its_calls = add_a_claim(
                finished.graph,
                THE_ONE_THEY_OFFER[example],
                answerer=answerer,
                on=today,
                width=Caps().width,
                # **What is left of this run's ceiling**, not a fresh one. It was
                # called with no ceiling at all, so `--cap 5` bought a generation
                # of five dollars and then an insert of fifteen (2026-09-20).
                dollars=max(ceiling - so_far.dollars, 0.0),
            )
        except Exception as went_wrong:
            telling("    it stopped for a reason nobody chose while drafting:")
            traceback.print_exc(file=sys.stderr)
            return so_far_a_run.model_copy(
                update={"broke": _in_one_plain_sentence(went_wrong), "seconds": _since(started)}
            )
        for one in its_calls:
            # Through the same follower, so the insert's calls reach the working
            # and the running total by the one path everything else does.
            watching.never_seen(one)
        so_far, working = watching.spent, watching.working
        telling("    drafted" if drafted is not None else "    it could not be drafted")
        finished = finished.model_copy(
            update={"receipt": _with_the_insert(finished.receipt, its_calls)}
        )

    return _a_run(
        example,
        hypothesis,
        its_seed,
        today,
        started,
        (*written, *_closing_events(finished, so_far, started)),
        _with_the_ending(working, finished),
        finished,
    ).model_copy(update={"scripted_insert": drafted, "kept_at": kept_at})


def _closing_events(
    finished: Finished | None, spent: RunningTotal, started: float
) -> tuple[Event, ...]:
    """The events that close a generation: the verdict, the receipt and the ending.

    Built twice on purpose — once the moment the generation ends, and once more
    once the scripted intervention has been drafted and added to the bill — so
    that the file written before the insert already carries the receipt. A kept
    run with a map in it and no receipt beside it is the one thing this file
    exists to prevent (Kent, 2026-09-20).

    Args:
        finished: What the walk handed back, or nothing when it never got there.
        spent: The running total, which is what the receipt is built from — a
            walk that broke hands nothing back, and what it spent is still spent.
        started: When the clock was started.

    Returns:
        The closing events, in the order the grammar wants them. Empty when the
        walk never finished.
    """
    if finished is None:
        return ()
    closing: list[Event] = []
    if finished.graph is not None and finished.destination is not None:
        closing.append(verdict(finished.graph, finished.destination))
    closing.append(receipt_event(spent, seconds=_since(started)))
    closing.append(
        Done(
            reason=finished.reason,
            claims=finished.claims,
            links=finished.links,
            rejected=finished.refused,
        )
    )
    return tuple(closing)


def _with_the_ending(working: Transcript, finished: Finished | None) -> Transcript:
    """Put what the walk spent, and why it stopped, onto the transcript.

    Args:
        working: The transcript as it stands.
        finished: What the walk handed back, or nothing at all.

    Returns:
        The transcript, with the ending on it when there is one.
    """
    if finished is None:
        return working
    return working.model_copy(
        update={"receipt": finished.receipt, "reason": finished.reason, "why": finished.why}
    )


def _since(started: float) -> float:
    """How long it has been, in seconds, since the clock was started."""
    return time.monotonic() - started


def _in_one_plain_sentence(broke: BaseException) -> str:
    """Say that a run stopped for a reason nobody chose, without a stack trace in it.

    What goes in the kept file is what a reader of that file needs: that this run
    did not finish, that what is in the file is everything it got to, and that
    somebody should look at the terminal. The exception itself is printed there.

    Args:
        broke: Whatever went wrong.

    Returns:
        One plain sentence.
    """
    return (
        "This run stopped for a reason nobody chose, after the money below had "
        f"already been spent. It was a {type(broke).__name__}; the terminal that "
        "ran it has the rest."
    )


def _a_run(
    example: str,
    hypothesis: str,
    its_seed: int,
    today: date,
    started: float,
    written: Sequence[Event],
    working: Transcript,
    finished: Finished | None,
) -> Run:
    """Gather what a run has produced so far into the one shape everything reads.

    Called twice: once the moment the generation ends, and once more when the
    scripted intervention has been drafted. Both write to the same file.

    Args:
        example: Which of the four this is.
        hypothesis: The sentence it was asked for.
        its_seed: The number its likelihoods are worked out from.
        today: The day it ran.
        started: When the clock was started.
        written: The events so far.
        working: The transcript so far.
        finished: What the walk handed back, if it got that far.

    Returns:
        The run as it stands.
    """
    return Run(
        example=example,
        hypothesis=hypothesis,
        seed=its_seed,
        on=today,
        seconds=_since(started),
        events=tuple(written),
        transcript=working,
        finished=finished,
        scripted_insert=None,
    )


def faults_of(run: Run) -> tuple[str, ...]:
    """List every reason this run may not become a recording, in plain sentences.

    Every reason at once, never the first — the same rule a refused proposal gets.

    **A run that showed no refusal is not one of them** (Kent, 2026-09-20). The rule
    used to be that every recording must hold one, and in twenty-six live
    proposals across two runs the model never once gave the validator something
    to refuse. Re-running until it errs is waiting for a mistake and calling it
    evidence, and it is the one thing on this list that would have been staged. A
    recording shows every refusal that happened; when none did, the screen says so
    in a line.

    Args:
        run: What the run produced.

    Returns:
        One sentence per reason, or nothing at all when it may.
    """
    found: list[str] = []
    if run.broke is not None:
        found.append(run.broke)
    if get_settings().KATALYST_ANSWERER:
        found.append(
            "This run was answered by a stand-in named by KATALYST_ANSWERER, not by "
            "a model, so it is a recording of nothing. It is kept, and it is not "
            "written to the recordings folder."
        )
    if run.finished is None or run.finished.graph is None:
        found.append("The run did not finish, so there is no map to play back.")
    if not any(isinstance(one, Done) for one in run.events):
        found.append("The run did not end where a generation ends.")
    if run.scripted_insert is None:
        found.append(
            "The one scripted intervention this recording offers could not be "
            "drafted, so a keyless reviewer would press the card's button and get "
            "nothing. Run it again."
        )
    return tuple(found)


def keep(run: Run, faults: tuple[str, ...], *, folder: Path | None = None) -> Path:
    """Write everything a paid run produced, whatever becomes of it.

    Always. This is the one thing that happens to every run, before anybody asks
    whether it is good enough to play back: the money is already spent, and the
    measurements in here — the seconds and the thinking tokens behind every call —
    are on no event and in no recording.

    Args:
        run: What the run produced.
        faults: Why it may not become a recording, if it may not.
        folder: Where to write it. `backend/.runs/` when not said, or wherever
            `KATALYST_RUNS` says.

    Returns:
        The file that was written — the run's own, when it already has one.
    """
    where = folder or where_runs_are_kept()
    where.mkdir(parents=True, exist_ok=True)
    # Written to the same file the generation was written to, when there is one,
    # so a run leaves one record of itself rather than two halves of one.
    stamped = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    # The generation's own identifier is in the name as well as the day and the
    # time, so two runs started inside one second are still two files.
    written = run.kept_at or where / f"{run.example}-{stamped}-{run.transcript.generation_id}.json"
    written.write_text(
        KeptRun(
            example=run.example,
            hypothesis=run.hypothesis,
            seed=run.seed,
            on=run.on,
            prompt_hash=prompt_hash(),
            seconds=run.seconds,
            became_a_recording=not faults,
            faults=faults,
            transcript=run.transcript,
            done=next((one for one in run.events if isinstance(one, Done)), None),
            receipt=next((one for one in run.events if isinstance(one, Receipt)), None),
            graph=None if run.finished is None else run.finished.graph,
            events=run.events,
            broke=run.broke,
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    return written


def write_recording(run: Run, *, folder: Path | None = None) -> Path:
    """Write the recording a keyless clone plays back.

    Only reached by a run that passed every check. The map's identifier is the one
    it was minted with while the run happened — never the example's short name,
    which the file is called after and which a stored example already answers to.

    Args:
        run: What the run produced.
        folder: Where to write it. When not said, wherever recordings are read
            back from — the setting, not the constant. A writer that ignored the
            setting the reader obeys would write into the shipped folder from a
            test, which is exactly what it did once (2026-09-20).

    Returns:
        The file that was written.
    """
    where = folder or where_they_live()
    where.mkdir(parents=True, exist_ok=True)
    written = where / f"{run.example}.jsonl"
    built = run.finished.graph if run.finished is not None else None
    header = {
        "base_id": "" if built is None else built.id,
        "seed": run.seed,
        "recording_date": run.on.isoformat(),
        "prompt_hash": prompt_hash(),
        "insert": (
            None
            if run.scripted_insert is None
            else {
                "claim_in_words": THE_ONE_THEY_OFFER[run.example],
                "answer": json.loads(run.scripted_insert.model_dump_json()),
            }
        ),
    }
    written.write_text(
        "\n".join(
            [json.dumps(header)]
            + [
                json.dumps(
                    {"event": events.name_of(one), "data": json.loads(one.model_dump_json())}
                )
                for one in run.events
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return written


# --- Saying what happened ---------------------------------------------------


def _telling(say: "Callable[[str], None] | None") -> "Callable[[str], None]":
    """Where progress goes: the terminal's error stream unless a caller says otherwise."""
    if say is not None:
        return say

    def to_the_terminal(line: str) -> None:
        print(line, file=sys.stderr, flush=True)

    return to_the_terminal


def _progress(grown: Event, line: TranscriptLine) -> str:
    """One line saying what just landed, in enough words to follow along."""
    if isinstance(grown, ProposalAccepted):
        claim = grown.proposition.claim if grown.proposition is not None else ""
        what = _trimmed(claim) if claim else "an arrow between two claims already on the map"
        return f"  {grown.at:>3}  accepted  {what}  ({line.seconds:.0f}s)"
    if isinstance(grown, ProposalRejected):
        codes = (
            ", ".join(one.code for one in grown.violations) or "the model gave us nothing to check"
        )
        return f"  {grown.at:>3}  refused   {codes}  ({line.seconds:.0f}s)"
    return f"  an event of a kind this line did not expect: {type(grown).__name__}"


def _so_far(so_far: RunningTotal, working: Transcript, seconds: float) -> str:
    """One line saying what the run has spent so far, and how long it has been going.

    The money is read off a receipt folded as the run goes, not off the
    transcript's own, which is filled in only at the end — that was the bug that
    printed `$0.00` on every line of a run that spent $1.32. The thinking is read
    off the transcript, because it is not on a receipt and deliberately never will
    be: the receipt's shape is settled, and a number shown in two places is two
    numbers that eventually disagree.
    """
    thinking = sum(one.thinking_tokens for one in working.lines)
    return (
        f"       so far: {so_far.calls} calls, ${so_far.dollars:.2f}, "
        f"{so_far.searches} searches, {so_far.input_tokens:,} in / "
        f"{so_far.output_tokens:,} out ({thinking:,} of it thinking), "
        f"{int(seconds // 60)}m{int(seconds % 60):02d}s"
    )


def what_it_cost(run: Run) -> list[str]:
    """Say what a paid run cost and what it built, as plain lines for the terminal.

    Printed whatever becomes of the run, because the money is spent either way and
    a figure nobody wrote down is a figure somebody pays for twice.

    Args:
        run: What the run produced.

    Returns:
        The lines to print.
    """
    receipt = next((one for one in run.events if isinstance(one, Receipt)), None)
    done = next((one for one in run.events if isinstance(one, Done)), None)
    lines = [f"what {run.example} cost:"]
    if receipt is None:
        lines.append("  nothing was billed: the run never made a call.")
    else:
        lines += [
            f"  model            {receipt.model}",
            f"  calls            {receipt.calls}",
            f"  searches         {receipt.searches}",
            f"  tokens in        {receipt.input_tokens:,} fresh, "
            f"{receipt.cache_read_tokens:,} read back from the cache",
            f"  tokens out       {receipt.output_tokens:,}",
            f"  dollars          ${receipt.dollars:.2f}",
            f"  seconds          {receipt.seconds:.1f} "
            f"({int(receipt.seconds // 60)}m{int(receipt.seconds % 60):02d}s)",
        ]
    lines.append(f"  priced at        what {PRICES_READ_ON} said, per `engine/pricing.py`")
    thinking = sum(one.thinking_tokens for one in run.transcript.lines)
    written = sum(one.output_tokens for one in run.transcript.lines)
    if written:
        lines.append(
            f"  thinking         {thinking:,} of {written:,} written tokens "
            f"({100 * thinking / written:.0f}%)"
        )
    slowest = max((one.seconds for one in run.transcript.lines), default=0.0)
    if slowest:
        quickest = min(one.seconds for one in run.transcript.lines)
        lines.append(f"  a call took      {quickest:.0f}s at best, {slowest:.0f}s at worst")
    if done is None:
        lines.append("  it did not reach an ending.")
    else:
        lines += [
            f"  it stopped       {done.reason} — {run.transcript.why or ''}".rstrip(" —"),
            f"  it built         {done.claims} claims, {done.links} arrows, "
            f"{done.rejected} refused",
        ]
    return lines


def _trimmed(claim: str) -> str:
    """Show enough of a claim to follow the run, and no more."""
    tidied = " ".join(claim.split())
    if len(tidied) <= ENOUGH_OF_A_CLAIM:
        return tidied
    return tidied[: ENOUGH_OF_A_CLAIM - 1].rstrip() + "…"


# --- The command line -------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run one or more examples, keep everything, and write a recording if it earned one.

    Returns:
        0 when everything asked for was written, 1 otherwise. A measurement run
        that finished returns 0 even though it writes no recording: it did what it
        was asked.
    """
    asking = argparse.ArgumentParser(
        prog="record-demo",
        description=(
            "Run an example live. Spends money; needs a key. Everything a run "
            "produces is kept under backend/.runs/ whatever becomes of it."
        ),
    )
    asking.add_argument(
        "--only", default="", help="One example's short name. All four when left out."
    )
    asking.add_argument(
        "--cap",
        type=float,
        default=Caps().dollars,
        help="What one run may spend, in dollars. Can only lower the figure in code.",
    )
    asking.add_argument(
        "--measure-only",
        action="store_true",
        help="Run it as a measurement: keep everything, write no recording.",
    )
    asking.add_argument(
        "--model",
        default="",
        help=(
            "Which model to ask, pinned for this whole run. The one the settings "
            "name when left out, which is claude-sonnet-5."
        ),
    )
    asking.add_argument(
        "--effort",
        default="",
        choices=["", "low", "medium", "high", "xhigh", "max"],
        help=(
            "How hard the model tries, pinned for this whole run. Empty leaves the "
            "service's own default and sends nothing."
        ),
    )
    said = asking.parse_args(argv)

    wanted = [said.only] if said.only else list(THE_FOUR)
    unknown = [one for one in wanted if one not in THE_FOUR]
    if unknown:
        print(
            f"There is no example called {', '.join(unknown)}. "
            f"The ones this program ships with are: {', '.join(THE_FOUR)}.",
            file=sys.stderr,
        )
        return 1

    # The stand-in is asked for **here and nowhere else**: the stream route calls
    # `live_answerer`, and a seam that answered a reader from a test file would
    # be a map that looked generated (Kent, 2026-09-20).
    answerer = a_stand_in_answerer() or live_answerer(
        effort=said.effort or None, model=said.model or None
    )
    if answerer is None:
        print(NO_KEY, file=sys.stderr)
        return 1

    wrote_everything = True
    for example in wanted:
        run = run_one(example, answerer=answerer, cap=said.cap)
        for line in what_it_cost(run):
            print(line, file=sys.stderr)

        faults = faults_of(run)
        if said.measure_only:
            faults = ("This was a measurement run, so no recording was written.",)
        kept = keep(run, faults)
        print(f"kept the whole run at {kept}", file=sys.stderr)

        if faults:
            print("no recording was written:", file=sys.stderr)
            for fault in faults:
                print(f"  {fault}", file=sys.stderr)
            if not said.measure_only:
                wrote_everything = False
            continue
        written = write_recording(run)
        left_out = _why_it_is_not_a_recording(written)
        if left_out:
            # Promoted only if it passes the very checks the build runs, read back
            # off the file rather than off the run in memory. A recording that
            # would fail in continuous integration should never have been copied
            # across in the first place (`replay.md` B6, B9).
            written.unlink()
            print("the recording was written and taken away again:", file=sys.stderr)
            for fault in left_out:
                print(f"  {fault}", file=sys.stderr)
            wrote_everything = False
            continue
        print(f"wrote the recording at {written}", file=sys.stderr)
    return 0 if wrote_everything else 1


def _why_it_is_not_a_recording(written: Path) -> tuple[str, ...]:
    """Read a just-written recording back and run the build's own checks over it.

    Read off the file rather than off the run that made it, because the file is
    what a keyless reviewer plays and what continuous integration reads. A
    recording that would fail there should never be copied across.

    Args:
        written: The file that was just written.

    Returns:
        One sentence per fault, or nothing at all when it is sound.
    """
    return tuple(faults_in(read_recording(written), current_prompt_hash=prompt_hash()))


def _with_the_insert(spent: RunningTotal, its_calls: tuple[Outcome, ...]) -> RunningTotal:
    """Add what drafting the scripted intervention cost to what the run spent.

    It is part of making the recording, so it is part of the bill. A cost that
    happened and is not on the receipt is a cost somebody pays for twice.
    """
    for one in its_calls:
        spent = fold(spent, one)
    return spent


# **The guard is the last thing in this file, and must stay there.** Started as a
# program, `main()` runs before anything written below it exists — which cost a
# 26-minute paid run on 2026-09-20, when this very function sat underneath it and
# the run died with a `NameError` after the money was spent. Imported by a test
# every name is defined first, so nothing caught it.
# `test_nothing_follows_the_guard_that_runs_a_module_as_a_program` reads this
# file, and every other module of ours, to keep it true.
if __name__ == "__main__":
    raise SystemExit(main())
