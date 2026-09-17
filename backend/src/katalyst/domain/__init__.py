"""The rules of the cause-and-effect map. Pure code, and the part we prove correct.

What this layer is for
----------------------
It defines what a proposition, a link, a belief, a graph, a branch, and a world
are, and it decides whether a proposed map is valid: every proposition is
resolvable by a date against a named source, every link says why it exists and
where its number came from, there are no loops, and every chain of reasoning
ends somewhere tradeable. It also applies interventions and propagates beliefs.

The one rule that shapes everything: **the model proposes; this layer disposes.**
A language model never edits the map. It returns proposals, and code in here
accepts a proposal or rejects it with reasons. That is why this layer can be
tested against thousands of generated inputs while the rest of the system cannot.

What this layer must never do
-----------------------------
- No input or output of any kind: no network calls, no files, no database, no
  printing.
- No clock. Nothing in here asks what time it is; a date that matters is passed
  in as an argument.
- No randomness unless a seed is passed in explicitly, so that the same inputs
  always give the same answer and any result can be reproduced.
- No imports from `katalyst.engine`, `katalyst.api`, or `katalyst.grounding`,
  and none from a language-model client library or any HTTP library. A test,
  `test_domain_imports_nothing_impure`, reads every file in this package and
  fails if one of those imports appears.

What is here now
----------------
The data shapes. `belief.py`, `proposition.py` and `link.py` hold the three
things a map is made of; `graph.py` holds a whole map; `intervention.py` holds
the six typed edits and `branch.py` the ordered list of them; `ids.py` holds the
identifier names. `validity.py` decides whether a proposed map is well-formed,
and returns every fault at once rather than the first. `patch.py` folds a
branch's edits onto a map, puts a chain of branches in order, and says which
claims an edit is allowed to move. `propagation.py` works the likelihoods
through: it turns a map and the values its edits fixed into a world — a number
and a range for every claim on the day it is judged, a number for every day in
between, and a named state for each of those days. `diff.py` compares two such
worlds: what happened to every claim, which endings moved and in what order, and
one fixed sentence saying so; it also sweeps a world one claim at a time, to see
what each flip would move.
"""

from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.branch import Branch
from katalyst.domain.diff import (
    ClaimDiff,
    ClaimState,
    DeltaRow,
    Diff,
    SensitivityRow,
    diff,
    sensitivity,
)
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, LinkId, PropositionId
from katalyst.domain.intervention import (
    Believe,
    Do,
    Insert,
    Intervention,
    Observe,
    Refine,
    Retune,
)
from katalyst.domain.link import Days, Link, Provenance, Source
from katalyst.domain.patch import (
    Assignment,
    affected_set,
    apply,
    flatten,
    introduced_by,
)
from katalyst.domain.propagation import (
    Retraction,
    SeriesState,
    Versions,
    World,
    propagate,
    versions_of,
)
from katalyst.domain.proposition import (
    BaseRate,
    ContractPayoff,
    Evidence,
    Payoff,
    PricePayoff,
    Proposition,
    Resolution,
)
from katalyst.domain.validity import Violation, ViolationCode, validate

__all__ = [
    "Assignment",
    "BaseRate",
    "Belief",
    "Beliefs",
    "Believe",
    "Branch",
    "BranchId",
    "ClaimDiff",
    "ClaimState",
    "ContractPayoff",
    "Days",
    "DeltaRow",
    "Diff",
    "Do",
    "Evidence",
    "Graph",
    "Insert",
    "Intervention",
    "Link",
    "LinkId",
    "Observe",
    "Payoff",
    "PricePayoff",
    "Proposition",
    "PropositionId",
    "Provenance",
    "Refine",
    "Resolution",
    "Retraction",
    "Retune",
    "SensitivityRow",
    "SeriesState",
    "Source",
    "Versions",
    "Violation",
    "ViolationCode",
    "World",
    "affected_set",
    "apply",
    "diff",
    "flatten",
    "introduced_by",
    "propagate",
    "sensitivity",
    "validate",
    "versions_of",
]
