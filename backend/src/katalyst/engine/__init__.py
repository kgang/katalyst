"""The pipeline between a language model and the rules layer.

What this layer is for
----------------------
It turns a sentence the user typed into a map, one proposal at a time: it builds
the request to the model, receives a proposal for a single proposition or a
single link, mints the identifier, records where the number came from, and hands
the result to `katalyst.domain` to accept or reject. A rejected proposal keeps
its list of reasons; it is never quietly patched up. The layer may re-ask the
model once, naming the reasons; a second failure becomes a visible error rather
than a spinner that never stops.

What this layer must never do
-----------------------------
- Never decide whether a map is valid. That belongs to `katalyst.domain`, so
  that correctness is proven by tests rather than requested of a model.
- Never let a model choose an identifier or declare where its own numbers came
  from. Both are facts about what this pipeline actually did.
- Never read an environment variable directly; ask `katalyst.settings` instead.
- Never import from `katalyst.api`.

Nothing lives here yet. Stack 04 adds the model calls; stack 03a adds belief
propagation's entry points.
"""
