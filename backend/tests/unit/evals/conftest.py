"""Let these tests import the eval harness, which lives outside `backend/`.

`evals/` is deliberately not part of the server package. It is not in the build,
it calls a model, it costs money, and it is run by hand — so putting it inside
the package that ships would be putting a thing that spends money one import
away from the thing that serves requests.

Its tests still belong in this suite, because they are the only thing that says
the eight structural checks do what the chapter says they do. So the repository
root goes on the import path **for this directory and no other**, which is what a
conftest beside these files buys.
"""

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[4]
"""The repository root: `backend/tests/unit/evals/` is four directories below it."""

if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))
