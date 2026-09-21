"""The exact solve — writer B.

Empty on purpose. `katalyst.domain.solving` lands as shapes and docstrings first;
the arithmetic and the tests below arrive together. This file builds its own
two-claim forward pass by hand, so it needs nothing from the other three writers.

The tests this file holds when it is written:

* `test_the_elimination_is_exact` — the answer matches summing the whole joint by
  hand over the engine's own yes/no tables, to nine decimal places.
* `test_supposing_redoes_the_forward_pass_rather_than_patching_a_factor` — *Suppose
  this is true* pins the claim and the pass is redone with it pinned. A finished
  table is never edited afterwards.
* `test_this_happened_masks_and_renormalises` — *This happened* keeps only what
  agrees with what was seen and makes the result add back up to one.
* `test_an_impossible_observation_answers_rather_than_dividing_by_zero` — an
  observation nothing on the map can produce is answered, never divided through.
* `test_the_elimination_order_does_not_change_the_answer` — the order claims are
  summed out in changes how much work is done and nothing else.
* `test_a_claim_cut_off_from_the_evidence_is_bit_for_bit` — a claim joined to the
  evidence by no chain of arrows and sharing no cause with it comes out byte for
  byte identical, not merely close. The restated version of this over the whole
  engine lives in `test_patches.py` and belongs to the oracle commit; this is the
  same promise asserted against the solve alone.
"""
