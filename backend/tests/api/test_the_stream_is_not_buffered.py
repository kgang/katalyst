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
    monkeypatch.delenv("KATALYST_REPLAY_INSTANT", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


A_QUICK_PACE = 0.05
"""A pace short enough for a test, since what is under test is *whether* it paces."""


def test_the_events_of_a_replay_are_let_go_of_one_at_a_time(
    a_paced_replay: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route hands events over as they come, rather than building the whole body.

    **What this can and cannot see.** The test client collects a response before
    handing it back, so the arrival times of the lines are all the same instant
    however the server behaved; the old assertion here — that the first of them
    was read before the last — is true of any two clock readings in sequence and
    could not fail however thoroughly anything buffered (2026-09-20). What *is*
    visible is the server's own clock: a paced replay waits between events, so a
    request that returns without having waited is a request whose events were
    never let go of one at a time. The other half, that nothing between here and
    a browser collects the body, is what the proxy configuration below is for.
    """
    del a_paced_replay
    monkeypatch.setattr(replay, "A_COMFORTABLE_PACE", A_QUICK_PACE)
    seen: list[tuple[float, str]] = []
    started = time.monotonic()
    with TestClient(app).stream(
        "POST",
        "/api/generate",
        json={"hypothesis": THE_SENTENCE, "versions": 16, "worlds": 4},
    ) as answer:
        for line in answer.iter_lines():
            if line.startswith("event: "):
                seen.append((time.monotonic(), line.removeprefix("event: ")))
    took = time.monotonic() - started

    assert len(seen) > 2
    paced = A_QUICK_PACE * (len(seen) - 1)
    assert took > paced / 2, (
        f"{len(seen)} events came back inside {took:.3f}s, which is far less than "
        f"the {paced:.3f}s a paced replay spends waiting between them — so they "
        "were never let go of one at a time."
    )
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
