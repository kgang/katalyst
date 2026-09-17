"""What a model call costs. The price table, and nothing else.

Every number here was read on **2026-09-17** from the `claude-api` skill — the
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

**When to re-read it.** Whenever the model changes, whenever a run's cost looks
wrong, and at the top of any stack that spends money. Change the date in the
same edit, or the date stops meaning anything.

What this file must never do
----------------------------
- Never hold a number nobody read from the skill. A price typed from memory is
  exactly the state this product refuses to show.
- Never quietly keep an old date. The date is the claim; the numbers are the
  evidence.
- Never grow a function. It is a table.
"""

PRICES_READ_ON = "2026-09-17"
"""The day these numbers were read from the `claude-api` skill.

Written out rather than stored as a date, because it is a fact about this file's
history and not something anything computes with.
"""

MODEL = "claude-opus-5"
"""The model every call in this program goes to (decision record 0006).

The exact string the service expects. Never a version with a date after it: the
skill is explicit that the plain name is the whole name.
"""

DOLLARS_PER_MILLION_INPUT_TOKENS = 5.00
"""What a million tokens of question cost."""

DOLLARS_PER_MILLION_OUTPUT_TOKENS = 25.00
"""What a million tokens of answer cost."""

CACHE_READ_SHARE_OF_INPUT = 0.1
"""What a token read back out of the cache costs, as a share of a fresh one.

The skill gives this as a multiplier rather than as its own row, so the price is
worked out from the input price rather than typed in beside it — one number,
read once, used twice.
"""

CACHE_WRITE_SHARE_OF_INPUT = 1.25
"""What a token costs the first time, when it is also written into the cache.

The five-minute cache, which is the one this program uses. The skill's other
figure — twice the input price — is for the hour-long cache, which is not used
here: our calls come a few seconds apart, so the short cache never goes cold and
the longer one would only cost more to write.
"""

DOLLARS_PER_MILLION_CACHE_READ_TOKENS = (
    DOLLARS_PER_MILLION_INPUT_TOKENS * CACHE_READ_SHARE_OF_INPUT
)
"""What a million tokens served out of the cache cost."""

DOLLARS_PER_MILLION_CACHE_WRITE_TOKENS = (
    DOLLARS_PER_MILLION_INPUT_TOKENS * CACHE_WRITE_SHARE_OF_INPUT
)
"""What a million tokens cost the first time, written into the cache as they go."""

DOLLARS_PER_THOUSAND_SEARCHES = 10.00
"""What a thousand web searches cost, on top of the tokens the results take up."""

A_MILLION = 1_000_000
"""The unit the token prices above are quoted in."""

A_THOUSAND = 1_000
"""The unit the search price above is quoted in."""
