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
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Graph, Insert
from katalyst.engine import events
from katalyst.engine.client import Answerer, live_answerer
from katalyst.engine.events import (
    Done,
    Event,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
    growth_event,
)
from katalyst.engine.expand import add_a_claim
from katalyst.engine.grow import Finished, grow
from katalyst.engine.ids import mint_id, mint_seed
from katalyst.engine.outcome import Caps, Outcome
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.receipt import Receipt as RunningTotal
from katalyst.engine.receipt import fold, nothing_spent_yet
from katalyst.engine.replay import RECORDINGS
from katalyst.engine.transcript import Transcript, line_for, makes_an_event
from katalyst.engine.verify import verdict

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
"""Where every paid run is written, whatever becomes of it.

Not committed, and not `backend/recordings/`: those two are different things.
A recording is a file the product plays back and the build checks; this is the
record of an afternoon's spending, kept so that nobody has to pay twice to answer
the same question.
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


def run_one(
    example: str,
    *,
    answerer: Answerer,
    cap: float,
    on: date | None = None,
    seed: int | None = None,
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

    at = 0
    finished: Finished | None = None
    walking = grow(hypothesis, answerer=answerer, on=today, caps=Caps(dollars=ceiling))
    try:
        for step in walking:
            if isinstance(step, Finished):
                finished = step
                break
            so_far = fold(so_far, step)
            working = working.plus(line_for(step, at if makes_an_event(step) else None))
            if not makes_an_event(step):
                telling("     ·      the model had nothing more to say about that line")
                continue
            grown = growth_event(step, at)
            written.append(grown)
            telling(_progress(grown, step))
            at += 1
            if at % DOLLARS_EVERY == 0:
                telling(_so_far(so_far, working, time.monotonic() - started))
    finally:
        walking.close()

    drafted: Insert | None = None
    if finished is not None and finished.graph is not None:
        telling(f"  drafting the one intervention the card offers: {THE_ONE_THEY_OFFER[example]!r}")
        drafted, its_calls = add_a_claim(
            finished.graph,
            THE_ONE_THEY_OFFER[example],
            answerer=answerer,
            on=today,
            width=Caps().width,
        )
        for one in its_calls:
            so_far = fold(so_far, one)
            working = working.plus(line_for(one, None))
        telling("    drafted" if drafted is not None else "    it could not be drafted")
        finished = finished.model_copy(
            update={"receipt": _with_the_insert(finished.receipt, its_calls)}
        )

    if finished is not None:
        working = working.model_copy(
            update={"receipt": finished.receipt, "reason": finished.reason, "why": finished.why}
        )
        if finished.graph is not None and finished.destination is not None:
            written.append(verdict(finished.graph, finished.destination))
        written.append(_receipt_of(finished, time.monotonic() - started))
        written.append(
            Done(
                reason=finished.reason,
                claims=finished.claims,
                links=finished.links,
                rejected=finished.refused,
            )
        )
    return Run(
        example=example,
        hypothesis=hypothesis,
        seed=its_seed,
        on=today,
        seconds=time.monotonic() - started,
        events=tuple(written),
        transcript=working,
        finished=finished,
        scripted_insert=drafted,
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
        folder: Where to write it. `backend/.runs/` when not said.

    Returns:
        The file that was written.
    """
    where = folder or KEPT_RUNS
    where.mkdir(parents=True, exist_ok=True)
    stamped = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    written = where / f"{run.example}-{stamped}.json"
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
        folder: Where to write it. `backend/recordings/` when not said.

    Returns:
        The file that was written.
    """
    where = folder or RECORDINGS
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


def _progress(grown: ProposalAccepted | ProposalRejected, outcome: Outcome) -> str:
    """One line saying what just landed, in enough words to follow along."""
    if isinstance(grown, ProposalAccepted):
        claim = grown.proposition.claim if grown.proposition is not None else ""
        what = _trimmed(claim) if claim else "an arrow between two claims already on the map"
        return f"  {grown.at:>3}  accepted  {what}  ({outcome.seconds:.0f}s)"
    codes = ", ".join(one.code for one in grown.violations) or "the model gave us nothing to check"
    return f"  {grown.at:>3}  refused   {codes}  ({outcome.seconds:.0f}s)"


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


def _receipt_of(finished: Finished, seconds: float) -> Receipt:
    """Turn what the walk spent into the receipt event."""
    spent = finished.receipt
    return Receipt(
        model=spent.model,
        calls=spent.calls,
        input_tokens=spent.input_tokens,
        output_tokens=spent.output_tokens,
        cache_read_tokens=spent.cache_read_tokens,
        searches=spent.searches,
        dollars=spent.dollars,
        seconds=seconds,
        mode="live",
        prompt_hash=prompt_hash(),
    )


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

    answerer = live_answerer(effort=said.effort or None)
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
        print(f"wrote the recording at {written}", file=sys.stderr)
    return 0 if wrote_everything else 1


if __name__ == "__main__":
    raise SystemExit(main())


def _with_the_insert(spent: RunningTotal, its_calls: tuple[Outcome, ...]) -> RunningTotal:
    """Add what drafting the scripted intervention cost to what the run spent.

    It is part of making the recording, so it is part of the bill. A cost that
    happened and is not on the receipt is a cost somebody pays for twice.
    """
    for one in its_calls:
        spent = fold(spent, one)
    return spent
