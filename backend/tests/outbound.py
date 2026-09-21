"""Refusing every outbound connection, so a test that would dial out fails instead of dialling.

A price is the one thing in this program that comes from a venue, and the rule
about it is absolute: **no test and no build makes a network call.** A rule like
that is worth nothing as an intention, because the day somebody adds a live read
to a code path a test already walks, the test goes on passing — slowly — and
nobody finds out until the build runs somewhere with no way out.

So the rule is made mechanical. Every test under the two directories that import
this fixture runs with the machinery for opening a connection replaced by
something that raises, whatever library is used and whatever address is asked
for: a test that reaches a venue fails, by name, on the line that reached it.

It is deliberately a **fixture other directories opt into**, not a global one.
The tests at the model boundary replay recorded exchanges through a library that
intercepts connections itself, and two guards fighting over the same machinery
would tell a confusing story about which one refused.
"""

import socket
from collections.abc import Iterator
from typing import Any, NoReturn

import pytest


class WentOutbound(RuntimeError):
    """A test tried to open a connection to somewhere outside this machine."""


def _refuse(*_arguments: Any, **_named: Any) -> NoReturn:
    """Refuse to open a connection, and say why in one sentence."""
    raise WentOutbound(
        "This test tried to open a connection. No test in this program calls out: a price "
        "comes from the committed, dated file under backend/recordings/quotes/, and asking "
        "a venue again is something a reader opts into and a test never does."
    )


@pytest.fixture(autouse=True)
def refuse_outbound_connections(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make every way of opening a connection raise, for the length of one test.

    Yields:
        Nothing. The guard is in force while the test runs and is taken off after.
    """
    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    yield
