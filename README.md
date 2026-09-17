# Katalyst

You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date, judged by a named source. Each arrow says how one claim pushes on the next, how strongly, and how long it takes. Every likelihood on the map shows three numbers side by side — what the model thinks, what you think, what the market is pricing — and every number can show why. Change a claim ("…but Iran is struck the next day") and only what is downstream moves; the original is kept for comparison. The map ends in a thesis: what to trade, when to enter, and the one event that would prove the idea wrong.

This is a take-home prototype for [Catalyst](https://catalyst.app). The brief is in `ASSIGNMENT.md`.

That is the whole product. It is being built in numbered stacks, and `ARCHITECTURE.md` says section by section what exists and what is still a plan. As of 2026-09-17: the rules of the map, a stored worked example, and the two halves that serve it are built; the canvas, the model that writes a map, and the thesis are not.

## Run it

You need Docker, and nothing else. No key is needed to start the app or to run the tests.

```sh
docker compose up           # build both halves, then start them
```

Then open <http://localhost:5173>. That is the browser app. The Python server is on <http://localhost:8000>, and the browser app reaches it through `/api` on its own address, so there is nothing to point at anything.

One worked example is stored in the repository and served read-only: <http://localhost:8000/api/fixtures/hormuz> returns the Strait of Hormuz map together with the branch in which Iran is struck the next day, every claim and arrow with its own source beside it (`/api/fixtures` lists what there is). Nothing draws it yet — today the browser app is a status screen, and the canvas is stack 03b.

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

No network, no key, and the same checks a pull request runs. Today that is 137 tests on the server and 3 in the browser app:

- **The rules, checked against maps nobody wrote by hand.** Hundreds of random maps per test, built by the generators in `backend/tests/strategies.py` — some correct by construction, some damaged on exactly one rule — and when one fails, the `hypothesis` library shrinks it to the smallest map that still breaks. Every line and every branch of `backend/src/katalyst/domain/` is run.
- **The stored example.** The Strait of Hormuz map and its "Iran is struck the next day" branch, held to every rule they claim to obey, and refusing to load at all if they break one.
- **The routes**, and the browser app's component tests for the status screen.
- **The one that matters most**: it reads every file under `backend/src/katalyst/domain/` — the layer that holds the rules — and fails if any of them imports the routes, the engine, the outside-data layer, or a language-model client. That layer must stay decidable by our own code alone.

One layer is built into the shape of the suite and is still empty: calls to the model replayed from responses recorded under `backend/tests/cassettes/`. There is nothing to record yet, because nothing calls a model until stack 04. A call that has not been recorded fails the test instead of dialling out, which is what keeps the suite free of keys forever.

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
| `backend/` | Python server: `domain/` (the rules, pure), `fixtures/` (the stored worked example), `engine/` (will talk to the model), `grounding/` (will fetch outside data), `api/` (routes) |
| `frontend/` | React browser app; `src/api/schema.ts` is generated from the server, never hand-written |
| `docker/`, `compose.yaml` | Container images and how they run together |

Start with `PRODUCT_REQUIREMENTS.md` §1 (the product in one screen), then `ARCHITECTURE.md`.
