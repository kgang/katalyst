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

Nothing lives here yet. Stack 04 adds search behind generation; stack 05 adds
the market and economic-data adapters.
"""
