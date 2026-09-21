"""Settings shared by the whole test suite.

Two rules about recorded network answers live here, because both must hold before
the first one is ever written — and because a rule that only reaches one directory
is a rule that stops holding the day somebody records somewhere else.

**Nothing that identifies anybody reaches a file.** A recording is a real exchange
with a real service: the request carried a real key, and the reply named the
organisation and the workspace the call was billed to, what that account has
bought and how much of it is left, and a handful of identifiers tying the exchange
to one account's traffic. None of it is a secret, none of it is read back on
replay, and all of it is somebody's business but the reader's. It comes out on the
way in, in both directions.
"""

from pathlib import Path
from typing import Any

import pytest

CASSETTE_DIR = Path(__file__).parent / "cassettes"

WHERE_A_KEY_WOULD_BE = ["x-api-key", "authorization"]
"""The two request headers a credential travels in."""

WHOSE_ACCOUNT_THIS_WAS = (
    "anthropic-organization-id",
    "anthropic-workspace-id",
)
"""Reply headers naming the account a call was billed to."""

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
"""Reply headers reporting what this account has bought and how much is left."""

TIES_IT_TO_ONE_EXCHANGE = (
    "request-id",
    "cf-ray",
    "traceresponse",
    "set-cookie",
)
"""Identifiers for this one exchange. Nothing reads them back."""

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
        The same answer, with those headers gone.
    """
    headers = response.get("headers")
    if isinstance(headers, dict):
        for named in NEVER_WRITTEN_DOWN:
            headers.pop(named, None)
            headers.pop(named.title(), None)
    return response


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> str:
    """Keep every recorded answer in one directory: `backend/tests/cassettes`.

    Without this the recorder puts a `cassettes` folder next to each test file,
    and the recordings end up scattered. One directory means one place to look,
    one place to re-record, and one place a secret scanner checks.

    Returns:
        The directory recorded answers are read from and written to.
    """
    return str(CASSETTE_DIR)


@pytest.fixture
def vcr_config() -> dict[str, object]:
    """Strip out of a recording everything that identifies anybody, both ways.

    Returns:
        The recorder's settings.
    """
    return {
        "filter_headers": WHERE_A_KEY_WOULD_BE,
        "before_record_response": scrubbed,
    }
