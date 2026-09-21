"""The new engine, end to end, behind its flag — writer A.

Nearly empty on purpose. `_by_deadline` lands as a seam first; the assembly and the
tests below arrive together.

The tests this file holds when it is written:

* `test_the_tables_agree_with_integrating_over_time` — the new engine's tables
  against an enumerator built from the arrow parameters alone, within five
  thousandths per verb, on at least ninety-nine per cent of a seeded generated set,
  at the same twenty-four slices and the same middle-of-the-slice convention as the
  engine, with the size of the set named and any failing case named.
* `test_todays_engine_is_byte_identical_under_the_flag` — the old arithmetic is
  untouched by the new argument.

The one test below is here from the first day, because it is what proves the flag
is wired to something and not merely declared.
"""

from datetime import date

import pytest

from katalyst.domain import propagate


def test_asking_for_the_new_engine_says_it_is_not_written_yet(a_small_valid_graph):
    """The flag reaches the new engine, and the new engine is honest about being a stub.

    This is the whole of what `engine="by_deadline"` promises today: the argument is
    real, it dispatches, and what it dispatches to raises rather than quietly
    answering with the old engine's numbers. It goes the moment there is arithmetic
    behind the seam.
    """
    with pytest.raises(NotImplementedError):
        propagate(
            a_small_valid_graph,
            (),
            as_of=date(2026, 9, 22),
            seed=1,
            engine="by_deadline",
        )
