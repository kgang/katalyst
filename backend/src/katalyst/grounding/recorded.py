"""The committed quotes: prices read from a venue once, kept, dated, and read back here.

**Recorded first, fetched second.** A price reaches this program from a committed
file before it reaches it from a venue, so the demo, the tests and the build all
run with no key and no network — and so a reviewer walking the flow sees exactly
the price the tests do. Asking the venue again is something a reader opts into,
and it lives in `polymarket.py`.

Each file under `backend/recordings/quotes/` holds the venue's **own answers,
word for word** — the market record and the order book — wrapped in two things a
reader of the repository needs: one line saying why the file is here, and the
exact commands that produced it. Nothing in a file is a number somebody typed:
the price, the instant, the identifiers and the side are all worked out from the
answers by the same code an opt-in read uses, so a replay is the real thing
played back rather than a summary of it.

**Why a venue's answers may be committed.** Kent's decision of 2026-09-21, in his
words: *"On the terms of service, we can commit a dated quote for research and
development purposes."* Each file says that, in its own first line.

What this file must never do
----------------------------
- Never reach over a network. It reads files, and only files.
- Never invent a quote for a market it has no file for. Nothing is better than a
  stand-in: a card with no price says so and prints a break-even instead.
- Never repair a file it cannot read. A file that is not a quote is named and the
  reason is said out loud.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from katalyst.grounding.polymarket import quote_from
from katalyst.grounding.quote import Quote
from katalyst.settings import get_settings

COMMITTED = Path(__file__).resolve().parents[3] / "recordings"
"""Where the committed recordings live when nothing says otherwise: `backend/recordings/`."""

INSIDE = "quotes"
"""The folder inside the recordings folder that holds the quotes, and nothing else."""

PURPOSE = "purpose"
"""The key whose value says, in one line, why a venue's answers are in this repository."""


def quotes_live_in(folder: Path | None = None) -> Path:
    """Say which folder this running program reads its committed quotes from.

    The same setting that moves the generation recordings moves these, so there is
    one answer to "where do the recordings live" rather than two.

    Args:
        folder: The folder to read, when a caller — a test, a browser run — names
            one. Left out, the committed folder.

    Returns:
        The folder the quotes are read from.
    """
    if folder is not None:
        return folder
    said = get_settings().KATALYST_RECORDINGS.strip()
    return (Path(said) if said else COMMITTED) / INSIDE


def recorded_quote(market_id: str, folder: Path | None = None) -> Quote | None:
    """Read back the committed quote for one market, by the venue's own identifier for it.

    A quote file is named after the market it is for and the day it was read, so a
    market with more than one recorded day gives back the most recent one — the
    days sort the same way the names do.

    Args:
        market_id: The venue's own identifier for the market, which is what the
            payoff on a claim names and what the file is named after.
        folder: Where to look. Left out, the committed folder.

    Returns:
        The quote, or nothing at all when no file has been recorded for that market.

    Raises:
        ValueError: If a file for that market exists and is not a quote this program
            can read. A file that cannot be read is said out loud rather than
            treated as an absence, because the two mean opposite things: one is
            "no venue prices this" and the other is "something here is broken".
    """
    looking_in = quotes_live_in(folder)
    found = sorted(looking_in.glob(f"{market_id}-*.json"))
    if not found:
        return None
    return _quote_in(found[-1])


def every_recorded_quote(folder: Path | None = None) -> tuple[Quote, ...]:
    """Read back every committed quote, in a settled order.

    Args:
        folder: Where to look. Left out, the committed folder.

    Returns:
        One quote per file, in the order the file names sort in. Empty when there
        are no files, which is not an error.

    Raises:
        ValueError: If any file in the folder is not a quote this program can read.
    """
    looking_in = quotes_live_in(folder)
    if not looking_in.is_dir():
        return ()
    return tuple(_quote_in(one) for one in sorted(looking_in.glob("*.json")))


def _quote_in(file: Path) -> Quote:
    """Read one committed file and work the quote out of the venue's own answers.

    Args:
        file: The file to read.

    Returns:
        The quote the venue's answers describe, marked as having come from a
        recording.

    Raises:
        ValueError: If the file is not valid JSON, does not carry the line saying
            why it is in this repository, or does not hold both of the venue's
            answers in a shape the parsing recognises.
    """
    try:
        held: Mapping[str, Any] = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as trouble:
        raise ValueError(f"{file.name} is not readable as JSON: {trouble}") from trouble
    if not str(held.get(PURPOSE, "")).strip():
        raise ValueError(
            f"{file.name} does not say why a venue's answers are in this repository. "
            "Every committed quote states its purpose in its own first line."
        )
    for named in ("event", "book"):
        if not isinstance(held.get(named), dict):
            raise ValueError(
                f"{file.name} does not carry the venue's {named} answer, so there is "
                "nothing here to work a price out of."
            )
    try:
        return quote_from(held["event"], held["book"], source="recorded")
    except (KeyError, TypeError, ValueError) as trouble:
        raise ValueError(
            f"{file.name} does not hold a price this program can read: {trouble}"
        ) from trouble
