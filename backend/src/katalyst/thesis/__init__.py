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

`draws.py` holds the one thing this layer asks of the engine: a sample of worlds
carrying, per claim, the day it came on and the day it went off, with a weight per
world. Everything else here is pure arithmetic over that shape. `paths.py` walks a
daily price path through each drawn world, applying only a claim's **surprise** —
what the market has not already priced — so the path invents no advantage of its
own. `position.py` holds what the reader typed and answers how often their stop
and their target are each reached first, with the correction a daily check needs
and the refusal a contract gets. `lift.py` ranks the claims over-represented in
the worlds where the stop went first. `ceiling.py` works out the greyed
quartered-Kelly ceiling that sits beside the reader's own arithmetic under the
words *never size to this*.

`card.py` builds the thesis a reader carries away — what carries it, what is
priced in, what takes them out, what to watch, what they typed and what it does
not know — and holds no bare numbers at all: each one carries whether it is the
reader's, the model's, a venue's or something this program worked out. `export.py`
turns a card into a declarative document a program can read and a page a person
can read, and owns the committed description of the document beside it.

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
- Never derive the reader's stop, and never recommend a size.
- Never report a number read off a sample of worlds without naming the sample.
"""

from katalyst.thesis.ceiling import NEVER_SIZE_TO_THIS, Ceiling, ceiling_of
from katalyst.thesis.draws import (
    NEVER,
    STILL_HOLDING,
    Draws,
    SampleFrom,
    effective_draws,
    weighted_share,
)
from katalyst.thesis.edge import (
    BreakEven,
    Edge,
    Mixture,
    NotComparable,
    NotComparableReason,
    priced,
    what_this_side_pays_on,
)
from katalyst.thesis.lift import (
    Dropped,
    DroppedBecause,
    LiftRow,
    WhatTakesYouOut,
    what_takes_you_out,
    wilson,
)
from katalyst.thesis.paths import ClaimMove, DecayShape, MarketChanceFrom, Paths, walk
from katalyst.thesis.position import (
    FirstTouch,
    Position,
    Refusal,
    RefusalCode,
    first_touch,
    position_on,
    what_the_form_refuses,
    what_your_risk_budget_implies,
    worth_of,
)

__all__ = [
    "NEVER",
    "NEVER_SIZE_TO_THIS",
    "STILL_HOLDING",
    "BreakEven",
    "Ceiling",
    "ClaimMove",
    "DecayShape",
    "Draws",
    "Dropped",
    "DroppedBecause",
    "Edge",
    "FirstTouch",
    "LiftRow",
    "MarketChanceFrom",
    "Mixture",
    "NotComparable",
    "NotComparableReason",
    "Paths",
    "Position",
    "Refusal",
    "RefusalCode",
    "SampleFrom",
    "WhatTakesYouOut",
    "ceiling_of",
    "effective_draws",
    "first_touch",
    "position_on",
    "priced",
    "walk",
    "weighted_share",
    "what_takes_you_out",
    "what_the_form_refuses",
    "what_this_side_pays_on",
    "what_your_risk_budget_implies",
    "wilson",
    "worth_of",
]

# --- The card and the export -------------------------------------------------
# Added as one block at the end of this file rather than folded into the imports
# above, so that two people building in this package at the same time never edit
# the same line. `card.py` builds what the panel draws; `export.py` writes the
# document a program reads, the page a person reads, and owns the committed
# description of the document beside it. The imports sit below a statement, which
# is why each one says the layout rule does not apply to it.
from katalyst.thesis.card import (
    Card,
    Carried,
    CeilingShown,
    Figure,
    Kind,
    MixtureShown,
    NotPriced,
    NotRanked,
    Owner,
    PricedIn,
    QuotedPrices,
    RankedEnding,
    Shift,
    Shocked,
    ShockRow,
    Tail,
    TailRow,
    TakesYouOutRow,
    TheTrade,
    Unhedgeable,
    UnhedgeableShown,
    Watched,
    WhatCarriesIt,
    WhatElseCanITrade,
    WhatIsPricedIn,
    WhatTakesYouOutShown,
    WhatThisDoesNotKnow,
    WhatToWatch,
    YourExit,
    card_of,
    what_else_can_i_trade,
    where_the_numbers_came_from,
)
from katalyst.thesis.export import (
    EXPORT_SCHEMA_FILE,
    SCHEMA_NAME,
    Conditions,
    Export,
    Hypothesis,
    Leg,
    RiskExit,
    ShockExported,
    Stamp,
    as_it_is,
    as_json,
    as_markdown,
    export_of,
    say,
    schema_json,
    two_significant,
)

__all__ += [
    "EXPORT_SCHEMA_FILE",
    "SCHEMA_NAME",
    "Card",
    "Carried",
    "CeilingShown",
    "Conditions",
    "Export",
    "Figure",
    "Hypothesis",
    "Kind",
    "Leg",
    "MixtureShown",
    "NotPriced",
    "NotRanked",
    "Owner",
    "PricedIn",
    "QuotedPrices",
    "RankedEnding",
    "RiskExit",
    "Shift",
    "ShockExported",
    "ShockRow",
    "Shocked",
    "Stamp",
    "Tail",
    "TailRow",
    "TakesYouOutRow",
    "TheTrade",
    "Unhedgeable",
    "UnhedgeableShown",
    "Watched",
    "WhatCarriesIt",
    "WhatElseCanITrade",
    "WhatIsPricedIn",
    "WhatTakesYouOutShown",
    "WhatThisDoesNotKnow",
    "WhatToWatch",
    "YourExit",
    "as_it_is",
    "as_json",
    "as_markdown",
    "card_of",
    "export_of",
    "say",
    "schema_json",
    "two_significant",
    "what_else_can_i_trade",
    "where_the_numbers_came_from",
]
