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
The data shapes, and nothing that computes with them. `belief.py`, `proposition.py`
and `link.py` hold the three things a map is made of; `graph.py` holds a whole
map; `intervention.py` holds the six typed edits and `branch.py` the ordered list
of them; `ids.py` holds the identifier names. Folding a branch onto a map and
working the likelihoods through arrive in a later stack.
"""

from katalyst.domain.belief import Belief, Beliefs
from katalyst.domain.branch import Branch
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
from katalyst.domain.proposition import (
    BaseRate,
    Evidence,
    Payoff,
    Proposition,
    Resolution,
)

__all__ = [
    "BaseRate",
    "Belief",
    "Beliefs",
    "Believe",
    "Branch",
    "BranchId",
    "Days",
    "Do",
    "Evidence",
    "Graph",
    "Insert",
    "Intervention",
    "Link",
    "LinkId",
    "Observe",
    "Payoff",
    "Proposition",
    "PropositionId",
    "Provenance",
    "Refine",
    "Resolution",
    "Retune",
    "Source",
]
