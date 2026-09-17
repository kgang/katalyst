"""Writing a recording. The only thing that ever does, and it spends real money.

`make record-demo` runs an example live against a real key and writes one file
into `backend/recordings/`. **Nothing else may ever write one** — not a test, not
a fixture script, not a person with an editor. A hand-edited recording is a piece
of state that traces to no input, no rule and no source, and afterwards it is
indistinguishable from a real one.

Two things it will not do
--------------------------
It refuses to start with no key, and says so. And it will not raise the spending
ceiling: the argument may lower the figure written in code, never lift it, because
a cap a caller can raise is not a cap.

What it cannot do yet
---------------------
Each recording is meant to carry **one scripted intervention** — the "…but X
happens" its card offers — drafted live at record time. Drafting a claim somebody
named, with arrows in both directions onto a finished map, is a different question
from any this program asks today: `ClaimProposal` carries one arrow and it points
*into* the new claim, and a scripted insert's arrows mostly point out of it. No
chapter defines that shape. So this stops before writing and says so rather than
inventing one, and `--without-the-scripted-insert` writes the file anyway for
whoever has decided that is the right trade.
"""

import argparse
import json
import sys
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

from katalyst.engine import events
from katalyst.engine.client import live_answerer
from katalyst.engine.events import (
    Done,
    Event,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
)
from katalyst.engine.grow import Finished, grow
from katalyst.engine.ids import mint_seed
from katalyst.engine.outcome import Caps
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.replay import RECORDINGS
from katalyst.engine.transcript import makes_an_event
from katalyst.engine.verify import verdict

THE_FOUR = {
    "hormuz": "The Strait of Hormuz is going to open next week.",
    "midterms": "Republicans win the House but Democrats take the senate during the Midterm.",
    "export-controls": "Models more capable than Fable get export restricted by the United States.",
    "photonics": "Photonic chips get adopted faster than expected.",
}
"""The four example hypotheses, word for word from the assignment.

The key is the file's short name and the launchpad card's; the sentence is what a
run is asked for and what a replay is matched on.
"""

NO_KEY = (
    "make record-demo calls a model and spends money, and no key is configured. "
    "Nothing was written."
)
"""What it says when it cannot run at all."""

NO_SCRIPTED_INSERT = (
    "The generation ran, but this recording has no scripted intervention to carry: "
    "drafting a claim somebody named, onto a finished map, is a question this "
    "program does not ask yet, and inventing one here would put wording in front of "
    "a reviewer that no chapter agreed to. Nothing was written.\n"
    "Two ways on, and it is not this file's decision which: add that third answer "
    "shape and its prompt in the batched prompt round, or record without it now and "
    "add it when the shape exists — `--without-the-scripted-insert` does the second."
)
"""What it says when everything worked except the one thing nobody has designed."""


def record(
    example: str,
    *,
    cap: float,
    folder: Path,
    with_the_scripted_insert: bool = True,
) -> Path | None:
    """Run one example live and write it down, or say plainly why it did not.

    Args:
        example: The short name of the example, which is also the file's name.
        cap: What this run may spend, in dollars. Never above the figure in code.
        folder: Where the file goes.
        with_the_scripted_insert: Whether to insist on the one scripted
            intervention the chapter requires.

    Returns:
        The file that was written, or nothing at all when it stopped.
    """
    answerer = live_answerer()
    if answerer is None:
        print(NO_KEY, file=sys.stderr)
        return None

    ceiling = min(cap, Caps().dollars)
    hypothesis = THE_FOUR[example]
    print(f"recording {example}: {hypothesis!r} at a ceiling of ${ceiling:.2f}", file=sys.stderr)

    seed = mint_seed()
    today = datetime.now(tz=UTC).date()
    written: list[Event] = []
    for event in _run(hypothesis, answerer, seed=seed, today=today, ceiling=ceiling):
        written.append(event)
        print(f"  {events.name_of(event)}", file=sys.stderr)

    built = next((one for one in written if isinstance(one, ProposalAccepted)), None)
    if built is None or not any(isinstance(one, Done) for one in written):
        print("The run did not finish. Nothing was written.", file=sys.stderr)
        return None
    if not any(isinstance(one, ProposalRejected) for one in written):
        print(
            "This run produced no refusal, and every recording must show one. Run it "
            "again — never edit the file.",
            file=sys.stderr,
        )
        return None
    if with_the_scripted_insert:
        print(NO_SCRIPTED_INSERT, file=sys.stderr)
        return None

    folder.mkdir(parents=True, exist_ok=True)
    where = folder / f"{example}.jsonl"
    header = {
        "base_id": _map_id(written),
        "seed": seed,
        "recording_date": today.isoformat(),
        "prompt_hash": prompt_hash(),
        "insert": None,
    }
    where.write_text(
        "\n".join(
            [json.dumps(header)]
            + [
                json.dumps(
                    {"event": events.name_of(one), "data": json.loads(one.model_dump_json())}
                )
                for one in written
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {where} ({where.stat().st_size:,} bytes)", file=sys.stderr)
    return where


def _run(
    hypothesis: str, answerer: object, *, seed: int, today: date, ceiling: float
) -> Iterator[Event]:
    """Run one generation and hand back the events a recording stores.

    The likelihoods are not among them: they are recomputed from the seed when the
    file is played back, so storing them would be storing a number that could one
    day disagree with the engine that is running.
    """
    yield GenerationStarted(generation_id=_a_run(), seed=seed, hypothesis=hypothesis)
    started = time.monotonic()
    at = 0
    finished: Finished | None = None
    walking = grow(
        hypothesis,
        answerer=answerer,  # type: ignore[arg-type]
        on=today,
        caps=Caps(dollars=ceiling),
    )
    try:
        for step in walking:
            if isinstance(step, Finished):
                finished = step
                break
            if not makes_an_event(step):
                continue
            from katalyst.api.generate import _growth

            yield _growth(step, at)
            at += 1
    finally:
        walking.close()
    if finished is None or finished.graph is None:
        return
    if finished.destination is not None:
        yield verdict(finished.graph, finished.destination)
    spent = finished.receipt
    yield Receipt(
        model=spent.model,
        calls=spent.calls,
        input_tokens=spent.input_tokens,
        output_tokens=spent.output_tokens,
        cache_read_tokens=spent.cache_read_tokens,
        searches=spent.searches,
        dollars=spent.dollars,
        seconds=time.monotonic() - started,
        mode="live",
        prompt_hash=prompt_hash(),
    )
    yield Done(
        reason=finished.reason,
        claims=finished.claims,
        links=finished.links,
        rejected=finished.refused,
    )


def _a_run() -> str:
    """Mint the identifier this generation answers to."""
    from katalyst.engine.ids import mint_id

    return mint_id()


def _map_id(written: list[Event]) -> str:
    """The identifier of the map these events built, minted while they were made."""
    from katalyst.engine.ids import mint_id

    del written
    return mint_id()


def main() -> int:
    """Run `make record-demo`'s work, and report what it did.

    Returns:
        0 when every example asked for was written, 1 otherwise.
    """
    asking = argparse.ArgumentParser(
        prog="record-demo",
        description="Run an example live and write a recording. Spends money; needs a key.",
    )
    asking.add_argument(
        "--only", default="", help="One example's short name. Every one when left out."
    )
    asking.add_argument(
        "--cap",
        type=float,
        default=Caps().dollars,
        help="What one run may spend, in dollars. Can only lower the figure in code.",
    )
    asking.add_argument(
        "--without-the-scripted-insert",
        action="store_true",
        help="Write the file even though it carries no scripted intervention.",
    )
    said = asking.parse_args()

    wanted = [said.only] if said.only else list(THE_FOUR)
    unknown = [one for one in wanted if one not in THE_FOUR]
    if unknown:
        print(
            f"There is no example called {', '.join(unknown)}. "
            f"The ones this program ships with are: {', '.join(THE_FOUR)}.",
            file=sys.stderr,
        )
        return 1
    written = [
        record(
            one,
            cap=said.cap,
            folder=RECORDINGS,
            with_the_scripted_insert=not said.without_the_scripted_insert,
        )
        for one in wanted
    ]
    return 0 if all(one is not None for one in written) else 1


if __name__ == "__main__":
    raise SystemExit(main())
