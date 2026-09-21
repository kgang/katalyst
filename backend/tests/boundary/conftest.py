"""How a recorded exchange with the model is matched and what is scrubbed out of it.

**Matching.** Every call this pipeline makes goes to the same address. A recorder
matching on the address alone would hand two calls each other's answers the moment
three lines of a map are expanded at once — silently, and differently on every
run. So a recorded answer is matched on the request's body as well, which is the
whole question: the standing half, the map as it stands, and the claim being asked
about. Two different questions cannot collide, and a question that has drifted
since the recording was made fails to match rather than replaying the wrong
answer.

**Scrubbing.** A recording is committed to a repository other people read. The
credentials are stripped one directory up, in `tests/conftest.py`, and that
setting is asked for here rather than repeated. What that does not cover is the
*answer*: the service replies with headers naming the organisation and the
workspace the call was billed to, what that account's rate limits are, and a
handful of identifiers tying the exchange to one account's traffic. None of it is
a secret and all of it is somebody's business but the reader's, and none of it is
read on the way back — so it comes out before anything reaches a file.

If a cassette is ever recorded outside this directory, this scrubbing does not
reach it. `test_no_cassette_contains_a_key` checks every file wherever it came
from, which is the net under that.
"""

from typing import Any

import pytest

WHOSE_ACCOUNT_THIS_WAS = (
    "anthropic-organization-id",
    "anthropic-workspace-id",
)
"""Headers naming the account a call was billed to. Nobody's business but Kent's."""

WHAT_THIS_ACCOUNT_MAY_SPEND = (
    "anthropic-ratelimit-input-tokens-limit",
    "anthropic-ratelimit-input-tokens-remaining",
    "anthropic-ratelimit-input-tokens-reset",
    "anthropic-ratelimit-output-tokens-limit",
    "anthropic-ratelimit-output-tokens-remaining",
    "anthropic-ratelimit-output-tokens-reset",
    "anthropic-ratelimit-requests-limit",
    "anthropic-ratelimit-requests-remaining",
    "anthropic-ratelimit-requests-reset",
    "anthropic-ratelimit-tokens-limit",
    "anthropic-ratelimit-tokens-remaining",
    "anthropic-ratelimit-tokens-reset",
)
"""Headers reporting what this account has bought and how much of it is left."""

TIES_IT_TO_ONE_EXCHANGE = (
    "request-id",
    "cf-ray",
    "traceresponse",
    "set-cookie",
)
"""Identifiers for this one exchange. Nothing reads them back, and they only date the file."""

NEVER_WRITTEN_DOWN = (
    *WHOSE_ACCOUNT_THIS_WAS,
    *WHAT_THIS_ACCOUNT_MAY_SPEND,
    *TIES_IT_TO_ONE_EXCHANGE,
)
"""Everything that comes out of a recorded answer before it reaches a file.

Deliberately **not** here: the day the exchange happened, which is honest
provenance for a recording, and how long the service took, which is the only
measurement of that a keyless machine can read.
"""


def scrubbed(response: dict[str, Any]) -> dict[str, Any]:
    """Take out of one recorded answer everything a reader has no business seeing.

    Used by the recorder as it writes, and by hand on files recorded before it
    existed — which is why it is a plain function of a response rather than a
    closure over anything.

    Args:
        response: One answer as the recorder is about to write it.

    Returns:
        The same answer, with the headers above gone.
    """
    headers = response.get("headers")
    if isinstance(headers, dict):
        for named in NEVER_WRITTEN_DOWN:
            headers.pop(named, None)
            headers.pop(named.title(), None)
    return response


@pytest.fixture
def vcr_config(vcr_config: dict[str, Any]) -> dict[str, Any]:
    """Add body matching and answer scrubbing to the shared settings.

    Args:
        vcr_config: The settings from `tests/conftest.py` — the ones that strip a
            key out of a request before it is written.

    Returns:
        Those settings, with the matching rule, the scrubbing and readable bodies
        added.
    """
    return {
        **vcr_config,
        "match_on": ["method", "scheme", "host", "port", "path", "query", "body"],
        "before_record_response": scrubbed,
        # Write the answer as text rather than as a compressed blob, so a person
        # reviewing a recording can read it and a secret scanner can search it.
        "decode_compressed_response": True,
    }
