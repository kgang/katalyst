"""One route that names this program and the version of it that is running.

It exists so that a browser tab, a screenshot, or a bug report can say which
build it came from without anyone guessing. The version is not written here: it
is read from the installed package, which takes it from `pyproject.toml`.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from katalyst import __version__

router = APIRouter(tags=["about"])


class About(BaseModel):
    """What this program calls itself, and which build is running."""

    name: str = Field(description='The product name, always "Katalyst".')
    version: str = Field(
        description="The version of the running build, such as 0.1.0.",
    )


@router.get("/about")
def about() -> About:
    """Report the product name and the running version.

    Returns:
        The name and the version of this build.
    """
    return About(name="Katalyst", version=__version__)
