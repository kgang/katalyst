"""Settings shared by the whole test suite.

Two rules about recorded network answers live here, because both must hold
before the first one is ever written.
"""

from pathlib import Path

import pytest

CASSETTE_DIR = Path(__file__).parent / "cassettes"


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
    """Strip credentials out of a recording before it is written to disk.

    A recording is a real exchange with a real service, which means the request
    carried a real key. These two headers are where a key would sit, and they
    are replaced before anything reaches a file that gets committed.

    Returns:
        The recorder's settings.
    """
    return {"filter_headers": ["x-api-key", "authorization"]}
