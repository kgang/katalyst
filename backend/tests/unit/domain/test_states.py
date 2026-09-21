"""A state's two times — writer D.

Empty on purpose. `katalyst.domain.states` lands as shapes and docstrings first;
the arithmetic and the tests below arrive together. Decision record 0017 is what
they check.

The tests this file holds when it is written:

* `test_a_state_with_nothing_to_end_it_is_an_event` — byte-identical. A state's
  stopping rate starts at zero, so with nothing on the map that can end it, it does
  not end.
* `test_the_sign_of_an_arrow_picks_which_rate_it_bends` — above the claim's own
  chance it bends the rate the claim comes on at; below it, the rate it goes off at.
* `test_the_chance_it_stops_is_closed_form` — a counter asserts **zero** searches
  and **zero** clamps. The old bisection goes with this.
* `test_a_sustain_arrow_reads_the_whole_interval_and_a_trigger_only_the_on_day`.
* `test_the_cheap_path_and_the_joint_agree` — identical to twelve decimal places,
  **and** a check on the source that the expensive pair of times is not built.
* `test_the_cheap_path_is_not_taken_for_an_event` — the guard that holds between the
  flip and the shape freeze, while every recorded claim is still minted as an event.
* `test_a_state_switches_on_at_most_once`.
* `test_a_states_range_is_measured_and_written_down` — a state's range against the
  same claim written as an event, measured, with the answer written into
  `docs/measurements.md`. Decision record 0017 promises this and nothing else
  schedules it.
"""
