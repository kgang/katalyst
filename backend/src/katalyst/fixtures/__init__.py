"""The worked examples this program ships with, written by hand and checked as they load.

What is here
------------
`hormuz.py` is the one complete example: the Strait of Hormuz map, and the
branch where Iran is struck the day after the strait opens. `catalogue.py` lists
the examples and finds one by name, which is all a route needs.

Why an example is Python rather than a data file
------------------------------------------------
Every number in a map is supposed to be able to say where it came from. A data
file can hold the numbers but not the sentence beside each one explaining that
it is illustrative, or which chapter settled a sign, or why an arrow that looks
documented is honestly marked as argued. Written as code, the example carries
its own reasoning, and the reasoning is read every time somebody changes a
number.

Which way this layer may point
------------------------------
It reads the rules layer (`katalyst.domain`) and nothing else of ours. The rules
layer must never read this one — a stored example is data we happen to ship, and
nothing about whether a map is valid may depend on which examples exist. A test,
`test_domain_imports_nothing_impure`, holds the rules layer to its half of that.
"""

from katalyst.fixtures.catalogue import EXAMPLES, StoredExample, find
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE

__all__ = [
    "EXAMPLES",
    "FIXTURE_DATE",
    "HORMUZ",
    "HORMUZ_THEN_STRIKE",
    "StoredExample",
    "find",
]
