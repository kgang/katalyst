"""Minting identifiers at the edge, where a clock and randomness are allowed.

The rules layer never makes an identifier, because making one that is unique
without any central register needs the current time and a source of randomness,
and reading neither is what makes that layer repeatable. So the minting lives in
the pipeline layer, and the finished string is passed in.
"""

import time

from katalyst.engine.ids import BIGGEST_SEED, mint_id, mint_seed

ULID_LENGTH = 26
"""How many characters one of these identifiers has, always."""


def test_mint_id_returns_a_twenty_six_character_identifier() -> None:
    """One identifier is a plain string of twenty-six characters, and no two are alike."""
    minted = mint_id()

    assert isinstance(minted, str)
    assert len(minted) == ULID_LENGTH
    assert minted.isalnum()
    assert minted != mint_id()


def test_minted_identifiers_sort_in_the_order_they_were_made() -> None:
    """Sorting a list of these identifiers puts it back in the order they were made.

    That is the whole reason for choosing this kind of identifier: a log of them
    reads in order instead of arbitrarily. The pause between one and the next is
    there because the order only holds across different milliseconds — two made
    inside the same one share a timestamp, and which of them sorts first is then
    down to the random half. Two thousandths of a second is enough to be sure the
    timestamps differ.
    """
    minted = []
    for _ in range(5):
        minted.append(mint_id())
        time.sleep(0.002)

    assert minted == sorted(minted)


def test_a_minted_seed_survives_the_trip_to_a_browser_and_back() -> None:
    """Measured, 2026-09-17: the first run minted a seed a browser could not hold.

    It minted 4803646386380448080; JavaScript reads that back as
    4803646386380448300. Nothing errors. The browser then asks for a world under
    a seed the server never used, gets different numbers, and every explanation
    of why is wrong. So every seed is minted inside the range a double holds
    exactly, and the check below is the browser's own arithmetic.
    """
    for _ in range(200):
        minted = mint_seed()

        assert 0 < minted <= BIGGEST_SEED
        assert int(float(minted)) == minted


def test_the_ceiling_is_the_largest_whole_number_a_double_holds() -> None:
    """One above it is the first number that comes back as something else."""
    assert int(float(BIGGEST_SEED)) == BIGGEST_SEED
    assert float(BIGGEST_SEED + 1) == float(BIGGEST_SEED + 2)
