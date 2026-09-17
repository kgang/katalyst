"""The pipeline between a language model and the rules layer.

What this layer is for
----------------------
It turns a sentence the user typed into a map, one proposal at a time: it builds
the request to the model, receives a proposal for a single claim and the one
arrow that reaches it, mints the identifiers, records where the number came
from, and hands the result to `katalyst.domain` to accept or reject. A rejected
proposal keeps its list of reasons; it is never quietly patched up.

**After a refusal the same question is asked again, up to three times, and no
attempt is ever told what was wrong with the last** (Kent, 2026-09-17; the dated
amendment to decision record 0003). Three failures in a row close that line.
Violation text never enters a prompt, so a prompt can never steer the model
toward passing our checks rather than toward being right. Every refusal is an
event the person sees.

Where each part lives
---------------------
`pricing.py` holds the price table and the day it was read. `proposal.py` holds
the whole of what a model may answer with. `prompt.py` holds what we say to it.
`outcome.py` holds what one call leaves behind, in our own words, and every limit
a run has. `client.py` is the seam — the one place the model is called and the
one place the vendor library's types are named. `grounding.py` decides where an
arrow came from, from what the search actually returned. `expand.py` turns one
answer into one outcome; `grow.py` walks the whole map; `verify.py` grades the
route to the place a person asked about. `receipt.py` adds the bill up. `ids.py`
mints identifiers and `worlds.py` builds a world from a stored example.

What this layer must never do
-----------------------------
- Never decide whether a map is valid. That belongs to `katalyst.domain`, so
  that correctness is proven by tests rather than requested of a model.
- Never let a model choose an identifier or declare where its own numbers came
  from. Both are facts about what this pipeline actually did.
- Never read an environment variable directly; ask `katalyst.settings` instead.
- Never import from `katalyst.api`.
"""
