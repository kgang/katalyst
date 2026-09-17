"""Nothing between the server and the browser may hold the stream back.

A proxy that buffers collects the whole answer and delivers it at once. The map
growing then becomes a spinner and then a dump — the exact thing FR-5 and UX-8
forbid — and it does it **silently in the packaged image while working perfectly
in development**, which is why this is checked rather than assumed.

Two halves, and the first is the one that can run anywhere:

* **The server's own answer is written as it goes.** Read from the route itself,
  with the clock: the first event arrives before the last one is written. It
  needs no fixed number of milliseconds, because it is an ordering claim and not
  a latency one.
* **The packaged proxy is told not to collect it.** Read from
  `docker/nginx.conf`, because a build that has to pull two images to prove one
  line of configuration is a build nobody runs. The `docker` job builds the
  images; this says what the file must contain for that build to be worth
  anything.
"""

import re
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from katalyst.api.main import app
from katalyst.engine import replay
from katalyst.settings import get_settings
from tests.unit.engine.a_recording import THE_SENTENCE, written_to

NGINX = Path(__file__).resolve().parents[3] / "docker" / "nginx.conf"
"""The packaged image's own web server configuration."""

MUST_BE_TOLD_NOT_TO_COLLECT = (
    "proxy_buffering off;",
    "proxy_cache off;",
)
"""What the `/api/` location must say, or the packaged build delivers a dump."""


@pytest.fixture
def a_paced_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A copy with one recording, no key, and the pacing left on."""
    folder = tmp_path / "recordings"
    written_to(folder)
    monkeypatch.setattr(replay, "RECORDINGS", folder)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("REPLAY_INSTANT", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_the_first_event_arrives_before_the_last_one_is_written(a_paced_replay: None) -> None:
    """The ordering claim, read with the clock off the route itself."""
    del a_paced_replay
    seen: list[tuple[float, str]] = []
    with TestClient(app).stream(
        "POST",
        "/api/generate",
        json={"hypothesis": THE_SENTENCE, "versions": 16, "worlds": 4},
    ) as answer:
        for line in answer.iter_lines():
            if line.startswith("event: "):
                seen.append((time.monotonic(), line.removeprefix("event: ")))

    assert len(seen) > 2
    first, last = seen[0][0], seen[-1][0]
    assert first < last, "every event arrived at the same moment, which means something buffered"
    assert seen[0][1] == "generation_started"
    assert seen[-1][1] in ("done", "failed")


def test_the_packaged_proxy_is_told_not_to_collect_the_body() -> None:
    """One line of configuration, and the whole of the packaged build's honesty."""
    said = NGINX.read_text(encoding="utf-8")
    api = re.search(r"location /api/ \{(.*?)\n    \}", said, re.S)

    assert api is not None, "there is no /api/ location in the packaged proxy any more"
    for rule in MUST_BE_TOLD_NOT_TO_COLLECT:
        assert rule in api.group(1), f"the packaged proxy does not say {rule!r}"


def test_the_answer_carries_the_header_a_proxy_reads() -> None:
    """Belt as well as braces: the configuration says it, and so does every answer."""
    with TestClient(app).stream(
        "POST", "/api/generate", json={"hypothesis": "nothing recorded", "versions": 16}
    ) as answer:
        assert answer.headers["x-accel-buffering"] == "no"
        assert answer.headers["cache-control"] == "no-store"
