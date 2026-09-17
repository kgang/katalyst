"""Minting identifiers at the edge, where a clock and randomness are allowed.

The rules layer never makes an identifier, because making one that is unique
without any central register needs the current time and a source of randomness,
and reading neither is what makes that layer repeatable. So the minting lives in
the pipeline layer, and the finished string is passed in.
"""

import time

from katalyst.engine.ids import mint_id

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
