"""The forward pass — writer A.

Empty on purpose. `katalyst.domain.forward` lands as shapes and docstrings first;
the arithmetic and the tests below arrive together.

The tests this file holds when it is written:

* `test_two_causes_add_as_independent_routes` — the identity that two causes, each
  an independent route, compose to `1 - (1 - a) * (1 - b) / (1 - own)`, writing
  `own` for the claim's chance with no cause on. Asserted as that identity, never
  against a number typed in by hand.
* `test_one_cause_at_a_time_equals_the_full_table` — averaging one cause at a time
  gives the same answer as averaging over every combination of arrival days. This
  is the whole reason a twenty-claim map is worked out in a fraction of a second,
  and it is exact rather than close.
* `test_many_versions_in_one_pass_equal_one_at_a_time` — bit for bit. The version
  axis is broadcasting and never a loop, and this is what says so.
"""
