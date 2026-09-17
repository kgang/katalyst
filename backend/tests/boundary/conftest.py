"""How a recorded exchange with the model is matched, and why it must be the body.

Every call this pipeline makes goes to the **same** address. A recorder matching
on the address alone would hand two calls each other's answers the moment three
lines of a map are expanded at once — silently, and differently on every run.

So a recorded answer is matched on the request's body as well, which is the whole
question: the standing half, the map as it stands, and the claim being asked
about. Two different questions cannot collide, and a question that has drifted
since the recording was made fails to match rather than replaying the wrong
answer.

The credentials are stripped one directory up, in `tests/conftest.py`, and that
setting is asked for here rather than repeated, so there is one place a secret
scanner's promise is kept.
"""

from typing import Any

import pytest


@pytest.fixture
def vcr_config(vcr_config: dict[str, Any]) -> dict[str, Any]:
    """Add body matching, and keep everything the shared settings already do.

    Args:
        vcr_config: The settings from `tests/conftest.py` — the ones that strip a
            key out of a recording before it is written.

    Returns:
        Those settings, with the matching rule and readable bodies added.
    """
    return {
        **vcr_config,
        "match_on": ["method", "scheme", "host", "port", "path", "query", "body"],
        # Write the answer as text rather than as a compressed blob, so a person
        # reviewing a recording can read it and a secret scanner can search it.
        "decode_compressed_response": True,
    }
