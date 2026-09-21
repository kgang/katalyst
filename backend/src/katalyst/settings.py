"""The one place environment variables are read.

Why one place
-------------
If any module could reach for an environment variable, no one could say what the
program reads or what it does when something is missing. Here the answer is one
small class: the names it reads are its field names, and the default for each is
written next to it. Everywhere else asks `get_settings()`.

The field names are spelled in capitals on purpose, so that the name in the code
and the name in the environment are the same string. There is no rule to learn.

Both keys are optional while the program starts. A missing key is not a crash; it
is a fact `/api/readyz` reports, so the first screen can say plainly what works
and what does not.
"""

import math
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

A_COMFORTABLE_PACE = 0.6
"""Seconds between two events of a replay when nobody says otherwise.

Cosmetic and nothing else: pacing never changes an event, an order or a number.
The figure is chosen against a measurement rather than taste — a live proposal
took about a minute to come back on the first five recorded calls, so a replay
that raced would teach a reviewer that the product is faster than it is, and one
that matched would be unwatchable. This is the slowest speed somebody will sit
through and the fastest that still reads as *arriving* rather than *appearing*.
"""

THE_SLOWEST_PACE = 10.0
"""The longest pause between two events this program will accept, in seconds.

Not a safety rail around a number that matters; a bound that makes the setting
mean what it says. A recording holds tens of events, so ten seconds between them
is minutes of watching an unchanged screen — past watching and into waiting, and
far more likely to be a typed-in millisecond figure than anybody's intention.
"""


class Settings(BaseSettings):
    """Everything this program reads from its environment.

    Attributes:
        ANTHROPIC_API_KEY: The key for the language model that proposes
            propositions and links. First needed in stack 04, which generates a
            map from a sentence. Until then the program runs without it, and
            the tests run without it forever: they replay recorded answers.
        FRED_API_KEY: The key for the Federal Reserve Economic Data service, a
            public source of economic time series. First needed in stack 05,
            where a proposition can be grounded in a published series.
        KATALYST_MODEL: Which model the pipeline asks. One setting, read once, and
            nothing outside `engine/client.py` and `engine/pricing.py` knows
            which it is. The default is the cheaper of the two while the shape of
            the thing is still being worked out; the more capable one is one
            setting away for a final recording.
        KATALYST_EFFORT: How hard the model tries, pinned for a whole run and
            never varied between calls — varying it would throw away the
            remembered prefix the run is reading back cheaply. Left empty, each
            path takes its own pinned default (`engine/client.py`): the recorder
            sends nothing at all and the service's own default applies; a live
            run and the scorecard, `make eval`, ask for `medium`.
        KATALYST_RECORDINGS: Where the committed recordings are read from. Left
            empty, `backend/recordings/`. A test or an end-to-end browser run
            points it at a folder of its own.
        KATALYST_RUNS: Where every paid run is written, whatever becomes of it.
            Left empty, `backend/.runs/`. A test that starts the recorder as a
            program points it somewhere throwaway, because that folder holds what
            real money bought and nothing may overwrite it.
        KATALYST_ANSWERER: The import path of a factory that builds the answerer,
            as `module:name`. Left empty — which it is everywhere but a test — the
            live answerer is built from the key. It exists so that the recorder
            can be run **as a program**, end to end, with no key and no network:
            two paid runs have been lost to bugs that only exist when a module is
            started rather than imported. A run answered this way is never written
            as a recording, whatever else it produces.
        KATALYST_REPLAY_PACE: How long a recorded generation waits between two of
            its events, in seconds. The default is the speed a person watches at
            (`A_COMFORTABLE_PACE` above); `0` means no pause at all. It is one
            number rather than a speed and a switch beside it, because "how long
            to wait" has one answer and a second way of saying *none* is a second
            answer to the same question. It is deliberately not something a
            request can ask for, since a client that could skip the pacing could
            skip the thing a recording exists to show. The end-to-end browser run
            sets a short pace rather than none: its subject is a map *arriving*,
            and with no pause at all there is no moment at which that is true.
    """

    model_config = SettingsConfigDict(
        # A local `.env` file is read when present. It is never committed.
        env_file=".env",
        env_file_encoding="utf-8",
        # Unrelated environment variables are ignored rather than rejected.
        extra="ignore",
        # Field names match environment-variable names exactly.
        case_sensitive=True,
    )

    ANTHROPIC_API_KEY: str | None = None
    FRED_API_KEY: str | None = None
    KATALYST_MODEL: str = "claude-sonnet-5"
    KATALYST_EFFORT: Literal["low", "medium", "high", "xhigh", "max", ""] = ""
    KATALYST_RECORDINGS: str = ""
    KATALYST_RUNS: str = ""
    KATALYST_ANSWERER: str = ""
    KATALYST_REPLAY_PACE: float = A_COMFORTABLE_PACE

    @field_validator("KATALYST_REPLAY_PACE")
    @classmethod
    def _a_pace_somebody_could_watch(cls, given: float) -> float:
        """Refuse a pause that is not a length of time somebody could watch.

        Says the whole thing in one sentence, because the person reading it is
        looking at their own shell and not at this file: what the setting is,
        what it may be, and what it was given.

        **Asked as "is it a length of time in range", not as "is it out of
        range".** A float can also be *not a number* or *infinite*, and neither
        is less than zero or greater than anything — so a test written the other
        way round lets both straight through to a program that would then sleep
        for ever, or not at all, with nothing saying why.
        """
        if not math.isfinite(given) or not 0 <= given <= THE_SLOWEST_PACE:
            raise ValueError(
                "KATALYST_REPLAY_PACE is how many seconds a replay waits between "
                "two of its events. It goes from 0, meaning no pause at all, to "
                f"{THE_SLOWEST_PACE}. It was given {given}."
            )
        return given


@lru_cache
def get_settings() -> Settings:
    """Return the settings, reading the environment only on the first call.

    The answer is cached so that the environment is read once per process and
    every caller sees the same values. A test that needs different values does
    not edit the environment: it replaces this function, either through the web
    framework's dependency override or by clearing the cache with
    `get_settings.cache_clear()`.

    Returns:
        The settings for this process.
    """
    return Settings()
