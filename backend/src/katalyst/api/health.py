"""Two routes that answer "is this program running?" and "can it do its job yet?".

They are deliberately separate questions. The first one is what a container
manager restarts the program over, so it must stay true even when nothing else
works. The second one is what the first screen reads to tell the user, in plain
words, which parts of the product are available right now.

Neither route ever reveals a key. The readiness answer says only whether one is
configured.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from katalyst.settings import Settings, get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    """The answer to "is this program running?"."""

    status: Literal["ok"] = Field(
        description='Always "ok". If the program cannot answer at all, nothing is returned.',
    )


class Readiness(BaseModel):
    """The answer to "can this program do its job yet?"."""

    status: Literal["ready", "not_ready"] = Field(
        description=(
            'Reads "ready" when everything needed to generate a map is configured, '
            'and "not_ready" when something is missing.'
        ),
    )
    model_key_present: bool = Field(
        description=(
            "Whether a key for the language model is configured. The key itself is "
            "never included in this answer."
        ),
    )


@router.get("/healthz")
def healthz() -> Health:
    """Report that the program is running.

    This answer depends on nothing: no key, no database, no other service. That
    is the point. A container manager restarts the program when this route stops
    answering, so anything it depended on could cause restarts for a reason that
    has nothing to do with the program being alive.

    Returns:
        A fixed status of "ok".
    """
    return Health(status="ok")


@router.get("/readyz")
def readyz(settings: Annotated[Settings, Depends(get_settings)]) -> Readiness:
    """Report whether the program can generate a map yet.

    Today that comes down to one thing: whether a key for the language model is
    configured. Without it the program still runs, still serves the stored
    example map, and still says so honestly here rather than failing later with
    an error the user cannot interpret.

    Args:
        settings: The program's settings. Supplied by the web framework, which
            lets a test replace them without touching the real environment.

    Returns:
        Whether the program is ready, and whether a model key is configured.
    """
    model_key_present = settings.ANTHROPIC_API_KEY is not None
    return Readiness(
        status="ready" if model_key_present else "not_ready",
        model_key_present=model_key_present,
    )
