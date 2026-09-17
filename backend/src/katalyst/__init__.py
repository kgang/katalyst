"""Katalyst: turn a plain-English hypothesis into a cause-and-effect map that ends in trades.

The package is split into four layers, each with its own module docstring saying
what it is for and what it must never do:

- `domain` — the rules of the map. Pure; knows nothing about the outside world.
- `engine` — the pipeline that asks a language model for proposals and hands
  each one to `domain` to accept or reject.
- `grounding` — fetching outside facts (prices, series, documents) and attaching
  them to the map as cited evidence.
- `api` — the routes the browser app calls.

One settings module, `settings.py`, is the only place environment variables are
read.
"""

from importlib.metadata import version

__version__ = version("katalyst")
"""The version of the installed package.

Read from the package metadata, which comes from `pyproject.toml`, so the number
is written in exactly one place. The `/api/about` route reports it.
"""
