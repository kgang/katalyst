"""The eval harness: the four example hypotheses, run live and scored on structure.

Deliberately outside `backend/`, and deliberately not in the build. These cost
money, they call a model, and the same prompt scores slightly differently twice —
so a build that ran them would be a build blocked by a model's mood. The build's
check on the model boundary is the recorded exchanges under
`backend/tests/cassettes/`, and nothing else.

What is in here: `cases/` holds one small file per example, `run.py` runs them and
prints a scorecard, and `runs/` holds one tab-separated file per day it was run.
The chapter that settles all of it is `spec/generation/evaluation.md`.
"""
