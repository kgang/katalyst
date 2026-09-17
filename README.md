# Katalyst

You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date, judged by a named source. Each arrow says how one claim pushes on the next, how strongly, and how long it takes. Every likelihood on the map shows three numbers side by side — what the model thinks, what you think, what the market is pricing — and every number can show why. Change a claim ("…but Iran is struck the next day") and only what is downstream moves; the original is kept for comparison. The map ends in a thesis: what to trade, when to enter, and the one event that would prove the idea wrong.

This is a take-home prototype for [Catalyst](https://catalyst.app). The brief is in `ASSIGNMENT.md`.

## Run it

You need Docker, and nothing else. No key is needed to start the app or to run the tests.

```sh
docker compose up           # build both halves, then start them
```

Then open <http://localhost:5173>. That is the browser app. The Python server is on <http://localhost:8000>, and the browser app reaches it through `/api` on its own address, so there is nothing to point at anything.

While editing, run `docker compose watch` (or `make dev`) instead. It starts the same two halves and then copies files into the running containers as you save them, so both reload themselves. Changing which packages are installed rebuilds the image instead, because copying a file cannot install a package.

`docker compose down` (or `make down`) stops everything.

`make prod` builds and runs the packaged versions of the same two halves on <http://localhost:8080>: the browser app as a folder of built files served by a small web server, which also forwards `/api` to the Python server. Nothing reloads there — it is what a deployment would run.

Keys are optional. If you have one, copy `.env.example` to `.env` and fill it in; Docker reads that file on its own. `/api/readyz` reports which keys are present and never what they are.

### Without Docker

The server needs [`uv`](https://docs.astral.sh/uv/), which brings its own Python 3.12. The browser app needs Node 24. In two terminals:

```sh
cd backend  && uv run uvicorn katalyst.api.main:app --reload --port 8000
cd frontend && npm ci && npm run dev
```

The checks below run the same way with or without Docker, and install what they need the first time:

```sh
make test     # every test, server and browser app. No key, no network
make lint     # style, formatting, types. Changes no file
make types    # rewrite the browser app's types from the server's description of itself
make          # the whole list of tasks
```

## Tests

```sh
make test
```

No network, no key, and the same checks a pull request runs. Today that means the server's route tests, the browser app's component tests, and the one test that matters most: it reads every file under `backend/src/katalyst/domain/` — the layer that holds the rules — and fails if any of them imports the routes, the engine, the outside-data layer, or a language-model client. That layer must stay decidable by our own code alone.

Two more layers are built into the shape of the suite and are empty until later stacks: property tests, where the `hypothesis` library generates thousands of random maps and shrinks any failure to the smallest example that still breaks; and calls to the model replayed from responses recorded under `backend/tests/cassettes/`. A call that has not been recorded fails the test instead of dialling out, which is what keeps the suite free of keys forever.

Continuous integration runs four jobs on every pull request — `backend`, `frontend`, `types-fresh` (the committed browser types still match the server's data shapes), and `docker` (both packaged images still build). None of them is given a key.

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
