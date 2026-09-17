# Katalyst

You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date, judged by a named source. Each arrow says how one claim pushes on the next, how strongly, and how long it takes. Every likelihood on the map shows three numbers side by side — what the model thinks, what you think, what the market is pricing — and every number can show why. Change a claim ("…but Iran is struck the next day") and only what is downstream moves; the original is kept for comparison. The map ends in a thesis: what to trade, when to enter, and the one event that would prove the idea wrong.

This is a take-home prototype for [Catalyst](https://catalyst.app). The brief is in `ASSIGNMENT.md`.

## Run it

You need Docker. No API key is needed to start the app or run the tests.

```sh
cp .env.example .env        # keys are optional; each one says which feature needs it
docker compose up           # build and start both halves
```

Then open <http://localhost:5173>. For live reload while editing, use `docker compose watch` instead of `up`.

Without Docker: the server needs Python 3.12 and [`uv`](https://docs.astral.sh/uv/); the browser app needs Node 24.

```sh
make dev                    # both halves, with reload
make test                   # all tests, no key needed
make lint                   # lint, format check, type check
make types                  # regenerate the browser's types from the server's API description
```

## Tests

`make test` runs everything and needs no network and no API key. The server's core rules are property-tested: the `hypothesis` library generates thousands of random maps and shrinks any failure to the smallest example that still breaks. Calls to the model are replayed from recorded responses committed under `backend/tests/cassettes/`. The browser app has component tests. Continuous integration runs four jobs on every pull request — `backend`, `frontend`, `types-fresh` (the committed browser types must match the server), `docker` (both images build) — none with a key.

## Map of the repo

| Where | What |
|-------|------|
| `PRODUCT_REQUIREMENTS.md` | What the tool must do and why: decisions, requirements, the invariants that must always hold |
| `ARCHITECTURE.md` | How it is built. Every section says whether it is built yet or only planned |
| `AGENTS.md` | Rules of the repo and working agreements |
| `docs/adr/` | Numbered decision records — a journal of why each choice was made |
| `spec/` | The spec, organized as a book: one directory per idea, one file per chapter |
| `docs/research/` | Research reports that fed the requirements. Inputs, not decisions |
| `backend/` | Python server: `domain/` (the rules, pure), `engine/` (talks to the model), `grounding/` (outside data), `api/` (routes) |
| `frontend/` | React browser app; `src/api/schema.ts` is generated from the server, never hand-written |
| `docker/`, `compose.yaml` | Container images and how they run together |

Start with `PRODUCT_REQUIREMENTS.md` §1 (the product in one screen), then `ARCHITECTURE.md`.
