"""The rate model — writer A.

Empty on purpose. `katalyst.domain.rates` lands as shapes and docstrings first, so
that everyone writing the new engine can build against each other from the first
minute. The arithmetic and the tests below arrive together.

The tests this file holds when it is written:

* `test_the_calibration_reproduces_the_stated_chance` — feed a stated chance in,
  get the same chance back out of the rate, to twelve decimal places, with nothing
  searched for.
* `test_an_arrow_alone_reproduces_its_own_stated_chance` — one arrow on, no other,
  and the claim comes out at the number stated for that arrow.
* `test_an_arrival_is_taken_at_the_middle_of_its_slice` — not its end.
* `test_a_deadline_inside_a_slice_is_not_counted_past` — a slice the deadline falls
  inside counts only the days before it.
* `test_an_arrow_that_cannot_hold_a_claim_back_says_so` — an arrow whose push covers
  only part of the window cannot hold its claim back as far as its number asks, and
  the clamp names the arrow and both numbers rather than quietly missing.
"""
