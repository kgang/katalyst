"""Fetching facts from the outside world and attaching them to the map as citations.

What this layer is for
----------------------
Everything that reaches outside this process for a fact: a web search behind the
model's own answers, a market price, an economic series. Each thing it fetches
comes back with the address it came from and the moment it was read, so a number
on the screen can always say where it came from.

What this layer must never do
-----------------------------
- Never decide whether a map is valid, and never change one. It supplies facts;
  `katalyst.domain` decides what they mean.
- Never invent a source. A claim with no address attached is not documented, and
  saying otherwise is the one thing this layer cannot be allowed to do.
- Never read an environment variable directly; ask `katalyst.settings` instead.
- Never import from `katalyst.api`.

Nothing lives here yet, and stack 04 did not change that: the web search behind
generation is part of the model boundary, so it lives in `engine/client.py`,
which declares the tool, and `engine/grounding.py`, which turns what the tool
returned into sources. This package waits for stack 05's market and
economic-data adapters, which reach outside this process on their own account
rather than through a model's answer.
"""
