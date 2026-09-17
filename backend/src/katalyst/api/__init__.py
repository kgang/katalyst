"""The routes the browser app calls.

What this layer is for
----------------------
It exposes the rest of the system over HTTP and nothing more: read the request,
call one layer below, shape the answer. Every route lives under `/api/`, because
in the packaged app one web server serves the pages and forwards everything
beginning with `/api` to this process. The shapes of the answers are declared as
data classes, so the framework can publish a description of this API that the
browser app turns into TypeScript types. That generated file is the only place
those types exist; nobody writes them twice.

What this layer must never do
-----------------------------
- Never hold the rules. Deciding whether a map is valid belongs to
  `katalyst.domain`; talking to a language model belongs to `katalyst.engine`.
- Never put a secret in an answer. `/api/readyz` says whether a key is
  configured; it never says what the key is.
- Never read an environment variable directly; ask `katalyst.settings` instead.

Each concern gets its own router module, and `main.py` mounts them. A later
stack adds a router rather than editing `main.py`.
"""
