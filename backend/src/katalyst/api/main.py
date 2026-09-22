"""The web application object, and the one place routers are mounted.

Every route is mounted under `/api/`. In the packaged app a single web server
serves the browser files and forwards anything beginning with `/api` to this
program, so both halves sit on one address and there is no cross-address
configuration to explain.

A later stack adds a router module next to this one and mounts it here in one
line. Routes are not written in this file.

Run it during development with:

    uv run uvicorn katalyst.api.main:app --reload --port 8000
"""

from fastapi import FastAPI

from katalyst import __version__
from katalyst.api import about, fixtures, generate, health, thesis, worlds

API_PREFIX = "/api"
"""Every browser-facing route hangs below this. There are no exceptions."""

app = FastAPI(
    title="Katalyst",
    version=__version__,
    summary="Turns a plain-English hypothesis into a cause-and-effect map that ends in trades.",
    description=(
        "The routes the Katalyst browser app calls. The description of this API is "
        "generated from the data shapes the program itself uses, and the browser app's "
        "TypeScript types are generated from this description, so the two halves cannot "
        "drift apart without a build failing."
    ),
)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(about.router, prefix=API_PREFIX)
app.include_router(fixtures.router, prefix=API_PREFIX)
app.include_router(worlds.router, prefix=API_PREFIX)
app.include_router(generate.router, prefix=API_PREFIX)
app.include_router(thesis.router, prefix=API_PREFIX)
