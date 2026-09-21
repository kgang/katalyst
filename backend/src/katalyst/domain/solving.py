"""Whether each claim is true, solved exactly over the map's small yes/no tables.

**Stubs.** Every function below raises `NotImplementedError`. Decision record 0016
is what this file implements.

What this module is for
-----------------------
The forward pass works out **when** each claim happens and leaves a small yes/no
table for each one. This module answers **whether**, exactly: it multiplies those
tables together and sums out one claim at a time until only the claim being asked
about is left. The standard name for that procedure is *variable elimination*, and
on the maps this product builds it is a few milliseconds of work.

Exactly means exactly. No sampling, no iteration, no tolerance. The only thing
between the answer and arithmetic truth is the tables themselves.

The two verbs
-------------
* ***Suppose this is true*** pins the claim to its day and **redoes the forward
  pass** with it pinned, then solves. A finished table is never patched afterwards.
  That is why this module takes what the fixed values were: it must know which
  claims were supposed, but it does not apply them itself.
* ***This happened*** multiplies in a mask that keeps only what agrees with what was
  seen, then makes the result add back up to one.

**Locality is a theorem here, not a hope.** A claim joined to the evidence by no
chain of arrows and sharing no cause with it has a factor that already adds to one,
so summing it out leaves the answer untouched — **bit for bit**, not merely close.
That is the strictest promise in this stack.

**There is no share-of-the-range working here.** Splitting a claim's range across
the claims that caused it would cost one more solve per claim, and the assembly
reads it off the exact per-version numbers instead.
"""

from collections.abc import Mapping

import numpy
from numpy.typing import NDArray

from katalyst.domain.forward import Forward
from katalyst.domain.ids import PropositionId
from katalyst.domain.rates import Pin


def solve(
    forward: Forward, pinned: Mapping[PropositionId, Pin]
) -> Mapping[PropositionId, NDArray[numpy.float64]]:
    """Answer, for every claim, the chance it is true, given everything that was fixed.

    True means what the claim's own tile says: for an event, that it happened by its
    deadline; for a state, that it is holding on its deadline.

    An observation nothing on the map can produce — one whose mask leaves no chance
    at all — is **answered**, with a violation-shaped refusal from the caller, and
    never divided through by zero.

    Args:
        forward: The finished forward pass, whose tables this solves over.
        pinned: The claims an edit fixed a value on. The *Suppose this is true*
            entries were already honoured by the pass; the *This happened* entries
            are applied here as a mask.

    Returns:
        Claim -> `(versions,)` the chance it is true.
    """
    raise NotImplementedError


def all_marginals(
    forward: Forward, pinned: Mapping[PropositionId, Pin]
) -> Mapping[PropositionId, NDArray[numpy.float64]]:
    """Every claim's number, in the one call the whole assembly makes.

    **One elimination pass per claim in this pull request.** The faster arrangement
    — one tree built once and passed over twice — is a change behind this signature
    and nothing else. It is not built here because it replaces twenty elimination
    passes rather than the pass itself, which is about a tenth of the cost of a hard
    map, and nothing now asks for twenty in one request.

    Args:
        forward: The finished forward pass.
        pinned: The claims an edit fixed a value on.

    Returns:
        Claim -> `(versions,)` the chance it is true.
    """
    raise NotImplementedError


def elimination_order(forward: Forward) -> tuple[PropositionId, ...]:
    """Choose the order claims are summed out in, so the tables stay small.

    Two standard steps. First the map is made **moral**: every arrow loses its
    direction, and any two causes of the same claim are joined to each other,
    because summing that claim out would join them anyway. Then claims are taken in
    **minimum-fill** order: at each step, the one whose removal would add the fewest
    new joins.

    The order changes how much work the solve does and **never** changes the answer.

    Args:
        forward: The finished forward pass, for which claim causes which.

    Returns:
        Every claim, in the order they are summed out.
    """
    raise NotImplementedError
