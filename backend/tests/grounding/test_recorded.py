"""The committed quotes: what is in the file, and what happens when there is not one.

The demo, the tests and the build read a price from a committed, dated file and
from nowhere else, so all three see the same number and none of them needs a key.
These tests pin three things about that file: it says why a venue's answers are in
this repository, it holds the venue's own answers rather than a summary of them,
and a market with no file gives back *nothing* rather than a stand-in — because
*no venue prices this* is a finding and a stand-in would hide it.
"""

import json
from pathlib import Path

import pytest

from katalyst.grounding import every_recorded_quote, quotes_live_in, recorded_quote
from katalyst.grounding.recorded import PURPOSE

HORMUZ_MARKET = "3501950"


def test_the_committed_quote_is_a_real_dated_venue_price() -> None:
    """The Hormuz contract's committed quote reads back as the venue's own price on a day."""
    quote = recorded_quote(HORMUZ_MARKET)

    assert quote is not None
    assert quote.source == "recorded"
    assert quote.market_id == HORMUZ_MARKET
    assert quote.live is True
    assert 0.0 < quote.bid <= quote.offer < 1.0
    assert quote.question and quote.rules and quote.url
    # The file is named after the day the venue stamped its own order book with.
    named = sorted(quotes_live_in().glob(f"{HORMUZ_MARKET}-*.json"))[-1]
    assert named.stem.endswith(quote.as_of.date().isoformat())


def test_the_committed_file_says_why_it_is_in_this_repository() -> None:
    """Every committed quote states its purpose, and states it first."""
    for file in sorted(quotes_live_in().glob("*.json")):
        text = file.read_text(encoding="utf-8")
        held = json.loads(text)

        assert str(held[PURPOSE]).strip(), f"{file.name} does not say why it is here"
        assert "research and development" in held[PURPOSE]
        assert held["how_it_was_read"], f"{file.name} does not say how it was read"
        # The purpose is the first thing in the file a person opening it reads.
        assert text.splitlines()[1].strip().startswith(f'"{PURPOSE}"')


def test_the_committed_file_holds_the_venues_own_answers() -> None:
    """Nothing in the file is a number somebody typed: the price is worked out of the answers."""
    file = sorted(quotes_live_in().glob(f"{HORMUZ_MARKET}-*.json"))[-1]
    held = json.loads(file.read_text(encoding="utf-8"))

    quote = recorded_quote(HORMUZ_MARKET)

    assert quote is not None
    assert quote.bid == max(float(one["price"]) for one in held["book"]["bids"])
    assert quote.offer == min(float(one["price"]) for one in held["book"]["asks"])
    assert quote.token_id == held["book"]["asset_id"]
    assert quote.condition_id == held["book"]["market"]


def test_a_market_with_no_file_is_nothing_rather_than_a_stand_in() -> None:
    """No file means no price, which the card says out loud and answers with a break-even."""
    assert recorded_quote("a-market-nobody-recorded") is None


def test_every_committed_quote_reads(tmp_path: Path) -> None:
    """Reading the whole folder gives one quote per file, and no folder at all is not an error."""
    assert every_recorded_quote() != ()
    assert every_recorded_quote(tmp_path) == ()
    assert every_recorded_quote(tmp_path / "a-folder-nobody-made") == ()


def test_a_file_that_is_not_a_quote_is_named(tmp_path: Path) -> None:
    """A broken file is said out loud, because a broken file and an absent one mean opposites."""
    (tmp_path / "1234-2026-09-21.json").write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="not readable as JSON"):
        recorded_quote("1234", tmp_path)


def test_a_file_that_does_not_say_why_it_is_here_is_refused(tmp_path: Path) -> None:
    """The one line saying why a venue's answers are committed is required, not decorative."""
    file = sorted(quotes_live_in().glob(f"{HORMUZ_MARKET}-*.json"))[-1]
    held = json.loads(file.read_text(encoding="utf-8"))
    (tmp_path / file.name).write_text(
        json.dumps({**held, PURPOSE: "  "}, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="does not say why"):
        recorded_quote(HORMUZ_MARKET, tmp_path)


def test_a_file_missing_an_answer_is_refused(tmp_path: Path) -> None:
    """Half the venue's answers is not a price, so it is refused by name."""
    file = sorted(quotes_live_in().glob(f"{HORMUZ_MARKET}-*.json"))[-1]
    held = json.loads(file.read_text(encoding="utf-8"))
    without = {key: value for key, value in held.items() if key != "book"}
    (tmp_path / file.name).write_text(json.dumps(without, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="does not carry the venue's book answer"):
        recorded_quote(HORMUZ_MARKET, tmp_path)


def test_a_file_whose_answers_do_not_match_is_refused(tmp_path: Path) -> None:
    """Two answers that describe different contracts are refused rather than guessed past."""
    file = sorted(quotes_live_in().glob(f"{HORMUZ_MARKET}-*.json"))[-1]
    held = json.loads(file.read_text(encoding="utf-8"))
    mismatched = {**held, "book": {**held["book"], "market": "0xsomething-else"}}
    (tmp_path / file.name).write_text(json.dumps(mismatched, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="does not hold a price this program can read"):
        recorded_quote(HORMUZ_MARKET, tmp_path)
