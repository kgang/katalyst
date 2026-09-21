"""From a map of causes to a trade: what it is worth, and against which price.

What this layer is for
----------------------
A map of causes is not a trade. This layer turns one into a trade and is careful
about which numbers are ours and which are the reader's. **We compute** the
**edge** — the model's number for a claim against the price a venue would actually
deal at — and the **break-even** that stands in for it when no venue quotes the
claim. **The reader types** their stop, their target and their horizon; none of
those is derivable from a map of claims.

What lives here now
-------------------
`edge.py`, and one function in it: `priced`, the only way an edge is built. It
takes **two** worlds, both required — the world with nothing fixed by an edit,
which is where the compared number is read from, and the world the reader is
looking at — so a caller holding only a branch world cannot produce an edge at
all. Where an edge cannot be built, it hands back a named refusal carrying the
sentence the card prints and a break-even wherever one is defined.

What this layer must never do
-----------------------------
- Never compare a number from a world where an edit fixed something against a
  venue's price. They answer different questions.
- Never compute an edge against the midpoint between a venue's two prices, and
  never subtract the spread twice: you buy at the offer and sell at the bid, and
  the spread is already inside those.
- Never merge the model's number, the reader's and a venue's. An edge is a
  *difference*, computed out here and labelled as one — which is exactly why it is
  not in `katalyst.domain`.
- Never change a map. It reads worlds and quotes, and builds an answer beside them.
"""

from katalyst.thesis.edge import (
    UNKNOWN_FEE,
    BreakEven,
    Edge,
    Mixture,
    NotComparable,
    NotComparableReason,
    priced,
)

__all__ = [
    "UNKNOWN_FEE",
    "BreakEven",
    "Edge",
    "Mixture",
    "NotComparable",
    "NotComparableReason",
    "priced",
]
