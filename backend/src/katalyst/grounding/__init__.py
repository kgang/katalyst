"""Fetching facts from the outside world and attaching them to the map as citations.

What this layer is for
----------------------
Everything that reaches outside this process for a fact: a market price, an
economic series, a web search behind the model's own answers. Each thing it
fetches comes back with the address it came from and the moment it was read, so a
number on the screen can always say where it came from.

What lives here now
-------------------
Prices. `quote.py` holds the one shape allowed to carry a price and turns a
venue's price into the market's likelihood on a claim — a **point**, because the
gap between a venue's two prices is what dealing costs rather than how unsure the
venue is. `polymarket.py` reads one prediction market's public answers, and holds
the single function in this program that opens a connection to a venue.
`recorded.py` reads the committed, dated files that the demo, the tests and the
build actually run on.

**Recorded first, fetched second.** A price comes from a committed file before it
comes from a venue, so everything here runs with no key and no network; asking the
venue again is something a reader opts into, and a failed ask keeps the recorded
price and says that it did.

The web search behind generation is part of the model boundary, so it lives in
`engine/client.py`, which declares the tool, and `engine/grounding.py`, which
turns what the tool returned into sources. The economic-data adapter — a measured
historical level, which is an observation about the past and never a price on a
future claim — arrives with the work on positions, because nothing before that has
a use for a level.

What this layer must never do
-----------------------------
- Never decide whether a map is valid, and never change one. It supplies facts;
  `katalyst.domain` decides what they mean.
- Never invent a source. A claim with no address attached is not documented, and
  saying otherwise is the one thing this layer cannot be allowed to do.
- Never read an environment variable directly; ask `katalyst.settings` instead.
- Never import from `katalyst.api`.
- Never reach over a network unless a reader asked it to. Nothing in the demo, the
  tests or the build does.
"""

from katalyst.grounding.polymarket import Book, Refreshed, quote_from, read_book, refresh
from katalyst.grounding.quote import Quote, QuoteSource, market_belief
from katalyst.grounding.recorded import every_recorded_quote, quotes_live_in, recorded_quote

__all__ = [
    "Book",
    "Quote",
    "QuoteSource",
    "Refreshed",
    "every_recorded_quote",
    "market_belief",
    "quote_from",
    "quotes_live_in",
    "read_book",
    "recorded_quote",
    "refresh",
]
