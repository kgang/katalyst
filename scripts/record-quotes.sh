#!/usr/bin/env bash
#
# Read a contract's price from Polymarket and commit it, dated.
#
# Polymarket is a prediction market: a venue where people buy and sell contracts
# that pay one dollar if a stated question comes out yes and nothing if it comes
# out no, so the price of a contract reads directly as a likelihood.
#
# **This is the only thing in the repository that writes a price file, and the
# only task here that opens a connection to a venue.** Everything else — the
# demo, the tests, the build — reads what this wrote, from
# `backend/recordings/quotes/`. That is the rule the whole price layer is built
# on: recorded first, fetched second. A reader may ask the venue again from the
# app, but nothing does it on their behalf.
#
# It needs no key and no account, and it spends nothing.
#
# Run it from anywhere, through make:
#
#     make record-quotes                          re-read every price already committed
#     make record-quotes SLUG=<slug> TOKEN=<id>   record a contract for the first time
#
# SLUG is the venue's own name for the **event** a market belongs to — the last
# part of its public web address. TOKEN is the identifier of the one outcome
# being priced: a contract's yes and its no are two separate order books, so one
# file is one side of one contract. Both appear in a market record, and both are
# already inside every file this has written before, which is why re-reading
# needs no arguments.
#
# Two public addresses are read for each contract, exactly as saved in the file
# afterwards: the market record, which carries the identifiers, the venue's own
# question and resolution rules, the end date, how much is resting and traded,
# and the flags saying whether the market still trades; and the order book, which
# carries the two sides of the book and the instant they were true.
#
# **Nothing in a written file is a number somebody typed.** The file holds the
# venue's two answers word for word, wrapped in one line saying why they are in
# this repository and the exact commands that produced them. The price, the day,
# the identifiers and the side are all worked out from those answers afterwards
# by the same code the app reads them with — which this runs before writing, so a
# file that cannot be read is never committed.
#
# A file is named after the market and the day the **venue** stamped the book
# with, never this machine's clock. Running it twice on one day rewrites that
# day's file; running it on a later day leaves the older reading in place, and
# the app reads the most recent.
#
# If the reads fail with nothing else wrong, suspect the resolver before the
# venue: on the machine this was written on, the local one answers "no such host"
# for every Polymarket address while a public resolver answers normally.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
backend_dir="${repo_root}/backend"

if ! command -v uv >/dev/null 2>&1; then
  echo "record-quotes: uv is not installed, and it is what runs the Python that reads a venue's answer. Install it from https://docs.astral.sh/uv/getting-started/installation/ and run this again." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "record-quotes: curl is not installed, and it is what fetches the venue's two answers." >&2
  exit 1
fi

slug="${1-}"
token="${2-}"

if [ -n "${slug}" ] && [ -z "${token}" ]; then
  echo "record-quotes: a slug was given with no outcome token. One file is one side of one contract, so both are needed: make record-quotes SLUG=<slug> TOKEN=<id>" >&2
  exit 1
fi

cd "${backend_dir}"

# The program below does three things for each contract: ask the venue twice,
# work the price out of the two answers with the app's own code, and write the
# file only once that has succeeded. It is handed the pair to record, or nothing
# at all, in which case it reads the pairs out of the files already committed.
env -u ANTHROPIC_API_KEY -u FRED_API_KEY uv run python - "${slug}" "${token}" <<'PYTHON'
"""Write one committed price file per contract, from the venue's own answers."""

import json
import subprocess
import sys
from pathlib import Path

from katalyst.grounding.polymarket import MARKET_RECORDS, ORDER_BOOKS, quote_from
from katalyst.grounding.recorded import PURPOSE, quotes_live_in

WHY = (
    "A dated quote from Polymarket, committed for research and development "
    "purposes (Kent's decision R23, 2026-09-21). It is the venue's own answers, "
    "kept word for word, so that this repository's demo, tests and build read a "
    "real price with no key and no network."
)

HOW_LONG_TO_WAIT = "25"
"""Seconds one read may take before it is given up on, passed to curl."""


def ask(address: str) -> tuple[str, object]:
    """Fetch one public address and parse it, returning the command used as well.

    The command is kept because it goes into the file: a reader of the repository
    should be able to run the very same line and see the same answer.
    """
    command = ["curl", "-sS", "-f", "-m", HOW_LONG_TO_WAIT, address]
    answer = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    return f"curl '{address}'", json.loads(answer)


def record(slug: str, token: str, folder: Path) -> Path:
    """Read one contract from the venue and write its file. Returns the file written."""
    event_command, events = ask(f"{MARKET_RECORDS}?slug={slug}")
    if not isinstance(events, list) or not events:
        raise SystemExit(f"record-quotes: the venue knows no event called '{slug}'.")
    book_command, book = ask(f"{ORDER_BOOKS}?token_id={token}")
    # Working the quote out BEFORE writing anything is the whole check: this is the
    # same function the app reads a committed file with, so an answer this program
    # cannot read never reaches the repository as a file that looks fine. It is
    # also where the file's name comes from — the venue's identifier for the
    # market and the day the venue stamped the book with, never this machine's
    # clock.
    quote = quote_from(events[0], book, source="recorded")
    written = folder / f"{quote.market_id}-{quote.as_of.date().isoformat()}.json"
    folder.mkdir(parents=True, exist_ok=True)
    written.write_text(
        json.dumps(
            {
                PURPOSE: WHY,
                "how_it_was_read": [event_command, book_command],
                "event": events[0],
                "book": book,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return written


def already_committed(folder: Path) -> list[tuple[str, str]]:
    """Read the slug and outcome token out of every file already written here.

    A committed file carries both, because it carries the venue's answers whole,
    so re-reading every price needs nothing typed.
    """
    pairs = []
    for file in sorted(folder.glob("*.json")):
        held = json.loads(file.read_text(encoding="utf-8"))
        pairs.append((str(held["event"]["slug"]), str(held["book"]["asset_id"])))
    return pairs


folder = quotes_live_in()
slug, token = sys.argv[1], sys.argv[2]
wanted = [(slug, token)] if slug else already_committed(folder)
if not wanted:
    raise SystemExit(
        "record-quotes: nothing is committed yet and no contract was named, so there "
        "is nothing to read. Say which one: make record-quotes SLUG=<slug> TOKEN=<id>"
    )
for one_slug, one_token in wanted:
    print(f"{one_slug} · {one_token[:12]}…", flush=True)
    print(f"  written: {record(one_slug, one_token, folder)}", flush=True)
PYTHON
