"""What a model call costs. The price table, and nothing else.

Every number here was read on **2026-09-20** from the `claude-api` reference bundle — the
reference bundle this repository consults before writing a model name, a
parameter or a price, because all three change and memory is unreliable. The
skill's own table is marked as cached on 2026-06-24. Decision record 0006 says
prices live in exactly one module with the day they were read beside them; this
is that module.

**Nothing in this file does anything.** No call, no arithmetic, no reading of the
environment. The folding of one call's usage into a running total lives next
door, in `receipt.py`, so that a reader who wants to know what something costs
finds one list of numbers, and a reader who wants to know how a bill is added up
finds one function.

**One row per model**, because the pipeline can be pointed at either of two and a
bill worked out at the wrong model's prices is worse than no bill. Each row also
carries the one number that silently changes a bill without changing any code:
how long a prefix has to be before that model will remember it at all.

**When to re-read it.** Whenever the model changes, whenever a run's cost looks
wrong, and at the top of any stack that spends money. Change the date in the
same edit, or the date stops meaning anything.

What this file must never do
----------------------------
- Never hold a number nobody read from the bundle. A price typed from memory is
  exactly the state this product refuses to show.
- Never quietly keep an old date. The date is the claim; the numbers are the
  evidence.
- Never guess at a model nobody has priced. Refuse and say which are known.
"""

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field

PRICES_READ_ON = "2026-09-20"
"""The day these numbers were read from the `claude-api` reference bundle.

Written out rather than stored as a date, because it is a fact about this file's
history and not something anything computes with.
"""


class Prices(BaseModel):
    """What one model charges, per million tokens and per thousand searches.

    Two of the five are given by the reference bundle as multipliers on the input
    price rather than as rows of their own, so they are worked out here from one
    number read once rather than typed twice.
    """

    model_config = ConfigDict(frozen=True)

    input_tokens: float = Field(description="Dollars per million tokens of question.")
    output_tokens: float = Field(description="Dollars per million tokens of answer.")
    cacheable_from: int = Field(
        description=(
            "How many tokens a prefix must reach before this model will remember it "
            "at all. **It is not the same for every model** — below it nothing is "
            "cached, no error is raised, and the bill simply goes up. A shorter "
            "standing prompt that cached on one model can stop caching on another."
        )
    )

    @property
    def cache_read_tokens(self) -> float:
        """Dollars per million tokens served back out of the cache."""
        return self.input_tokens * CACHE_READ_SHARE_OF_INPUT

    @property
    def cache_write_tokens(self) -> float:
        """Dollars per million tokens written into the cache as they are read."""
        return self.input_tokens * CACHE_WRITE_SHARE_OF_INPUT


CACHE_READ_SHARE_OF_INPUT = 0.1
"""What a token read back out of the cache costs, as a share of a fresh one."""

CACHE_WRITE_SHARE_OF_INPUT = 1.25
"""What a token costs the first time, when it is also written into the cache.

The five-minute cache, which is the one this program uses. The bundle's other
figure — twice the input price — is for the hour-long cache, which is not used
here: our calls come a minute or so apart, so the short cache never goes cold and
the longer one would only cost more to write.
"""

DOLLARS_PER_THOUSAND_SEARCHES = 10.00
"""What a thousand web searches cost, on top of the tokens the results take up.

The same for every model, because the searching is not the model's work.
"""

PER_MODEL: Mapping[str, Prices] = MappingProxyType(
    {
        "claude-sonnet-5": Prices(input_tokens=2.00, output_tokens=10.00, cacheable_from=1_024),
        "claude-opus-5": Prices(input_tokens=5.00, output_tokens=25.00, cacheable_from=512),
    }
)
"""What each model this program may be pointed at costs, and what it will remember.

Two entries, because those are the two the settings allow. Adding a third is
adding a row here and nothing else — and reading its **minimum cacheable prefix**
from the bundle at the same time, because that number is the one that changes a
bill without changing a line of code.
"""

A_MILLION = 1_000_000
"""The unit the token prices above are quoted in."""

A_THOUSAND = 1_000
"""The unit the search price above is quoted in."""


def prices_for(model: str) -> Prices:
    """What one model charges.

    Args:
        model: The model's exact name.

    Returns:
        Its prices.

    Raises:
        KeyError: If nobody has read that model's prices. A bill worked out from
            a guess is worse than no bill at all, so this refuses rather than
            falling back to another model's numbers.
    """
    if model not in PER_MODEL:
        raise KeyError(
            f"Nobody has read the prices for {model!r}. Read them from the claude-api "
            f"reference bundle, add a row to PER_MODEL with the day you read them, and "
            f"read that model's minimum cacheable prefix at the same time. "
            f"The ones this program knows are: {', '.join(PER_MODEL)}."
        )
    return PER_MODEL[model]
