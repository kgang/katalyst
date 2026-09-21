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

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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
            remembered prefix the run is reading back cheaply. Left empty, the
            service's own default applies and the setting is not sent at all.
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
        REPLAY_INSTANT: Whether a recorded generation plays back with no pause
            between its events. Off by default, because the pause is what makes a
            replay read as a map arriving rather than appearing. The test suite
            and the build's own check turn it on; it is deliberately not
            something a request can ask for, since a client that could skip the
            pacing could skip the thing a recording exists to show.
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
    REPLAY_INSTANT: bool = False


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
