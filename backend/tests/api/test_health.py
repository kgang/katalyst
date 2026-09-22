"""The two health routes, called in-process with no key in the environment.

The point of these tests is the promise the routes make. `/api/healthz` answers
whether the program is running and must not depend on anything else, so it is
called here with the keys deliberately removed from the environment.
`/api/readyz` answers whether a language-model key is configured, and must say so
without ever repeating the key back.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from katalyst.api.main import app
from katalyst.settings import Settings, get_settings

FAKE_KEY = "not-a-real-key"


@pytest.fixture(autouse=True)
def a_recordings_folder_with_nothing_in_it(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Point every test here at an empty recordings folder of its own.

    These tests ask one question: does the program know whether it has a model
    key? The readiness answer also lists what can be replayed, and with no key a
    single recording is enough to make the program ready. So read against the
    folder the repository ships, the answers below would change the day a
    recording is committed — which is exactly what happened the day the first
    one was. A test must not depend on what happens to be on the shelf.

    What readiness says when a recording IS there is pinned where recordings are
    tested, by `test_readyz_says_what_can_be_replayed_before_anything_runs`.

    **The settings are read once and remembered**, so setting the variable is not
    enough on its own: a module that ran earlier may already have asked, and its
    answer would be the one this test got. Clearing on the way in and on the way
    out is what makes the folder a fact about this test rather than about the
    order the suite happened to run in — these two files together went red
    exactly that way (2026-09-21).
    """
    monkeypatch.setenv("KATALYST_RECORDINGS", str(tmp_path_factory.mktemp("no-recordings")))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client that calls the application directly, opening no port."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings_from_environment() -> Iterator[None]:
    """Make the routes read fresh settings for this test, and nothing else.

    The routes normally ask for the settings once and reuse the answer for the
    life of the process. Here they are built again on each request, so a test
    can change an environment variable with `monkeypatch` and see the effect.
    Passing no local settings file means a developer's own `.env` cannot change
    the result. The swap is undone when the test ends.
    """
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield
    app.dependency_overrides.clear()


def test_healthz_is_ok_with_no_environment_variables_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The liveness answer depends on nothing, so removing both keys changes nothing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.usefixtures("settings_from_environment")
def test_readyz_reports_not_ready_when_no_model_key_is_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no key, the program still answers, and says plainly that it is not ready."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.get("/api/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_ready",
        "model_key_present": False,
        "replayable": [],
        "unreadable": [],
    }


def test_readyz_treats_an_empty_key_as_no_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copying .env.example unfilled sets the key to an empty string; that is not a key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from katalyst.settings import get_settings

    get_settings.cache_clear()

    response = client.get("/api/readyz")

    assert response.json() == {
        "status": "not_ready",
        "model_key_present": False,
        "replayable": [],
        "unreadable": [],
    }
    get_settings.cache_clear()


@pytest.mark.usefixtures("settings_from_environment")
def test_readyz_reports_ready_when_a_model_key_is_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a key, the program is ready — and the answer never repeats the key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)

    response = client.get("/api/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "model_key_present": True,
        "replayable": [],
        "unreadable": [],
    }
    assert FAKE_KEY not in response.text
