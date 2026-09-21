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

from katalyst.engine.replay import RecordingSummary, readable
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
            'Reads "ready" when this program can build a map — with a key, or from '
            'a recording — and "not_ready" only when it can do neither. A copy with '
            "no key and four recordings draws four maps, refuses proposals in public "
            "and takes every intervention at full fidelity; calling that not ready "
            "would be the screen lying about itself in the one place it exists to be "
            "honest."
        ),
    )
    model_key_present: bool = Field(
        description=(
            "Whether a key for the language model is configured. The key itself is "
            "never included in this answer."
        ),
    )
    replayable: tuple[RecordingSummary, ...] = Field(
        default=(),
        description=(
            "The examples this copy can play back from a committed recording, and "
            "the day each one was made. The first screen reads it before anything "
            "runs, which is the only way it can name a date at all: the day a "
            "recording was made travels on the receipt, and the receipt arrives last."
        ),
    )
    unreadable: tuple[str, ...] = Field(
        default=(),
        description=(
            "One plain sentence per file in the recordings folder that this "
            "engine could not read. **A bad file never hides the good ones**: it "
            "is named here and the others still play, because a recording is a "
            "committed file that outlives the code that wrote it and meeting an "
            "old one is ordinary rather than exceptional (Kent, 2026-09-20)."
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

    Two ways it can: with a key, by calling a model, or with none, by playing a
    committed recording back through the same stream and the same canvas. It is
    `not_ready` only when it can do neither, because a copy that can replay four
    examples can do almost everything this product is judged on.

    Args:
        settings: The program's settings. Supplied by the web framework, which
            lets a test replace them without touching the real environment.

    Returns:
        Whether the program is ready, whether a model key is configured, and what
        it can play back.
    """
    # An empty string counts as no key: copying .env.example unfilled must not read as ready.
    model_key_present = bool(settings.ANTHROPIC_API_KEY)
    good, unreadable = readable()
    replayable = tuple(
        RecordingSummary(example=one.example, recording_date=one.header.recording_date)
        for one in good
    )
    return Readiness(
        status="ready" if model_key_present or replayable else "not_ready",
        model_key_present=model_key_present,
        replayable=replayable,
        unreadable=unreadable,
    )
