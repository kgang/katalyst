"""The weighted sample — writer C.

Empty on purpose. `katalyst.domain.sampling` lands as shapes and docstrings first;
the arithmetic and the tests below arrive together. This is the one piece that
cannot be finished at the stub: its correction is *defined* against the exact
answer, so its tests need real numbers from the forward pass and the solve.

The tests this file holds when it is written:

* `test_the_control_variate_leaves_the_exact_answer_where_no_evidence_moves_it` —
  to twelve decimal places. Drawing each world twice from the same random numbers
  means the difference is zero where nothing was observed.
* `test_the_sample_is_seeded` — the same seed gives byte-identical days and weights.
* `test_the_effective_count_is_never_above_the_worlds_drawn`.
* `test_an_event_never_goes_off` — an event's off day is always the still-holding
  marker.
* `test_a_states_off_day_is_never_before_its_on_day`.
* `test_the_days_are_slice_middles_rounded_to_whole_days` — this pins the one
  contract stack 06 reads: at twenty-four slices over a sixty-day window every
  arrival lands on one of twenty-four days, about two and a half days apart.
* `test_the_correction_is_one_scalar_per_claim_shared_across_versions` — one draw
  serves every version, which is what makes the sample a fixed cost.
"""
