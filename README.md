# Katalyst

You type an event you think will happen. Katalyst draws what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date and judged by a named source; each arrow says how one claim pushes on the next, how hard, and how long it takes. Every likelihood shows three numbers side by side — what the model thinks, what you think, what the market is pricing — never merged, and every one of them can say why.

A take-home prototype for [Catalyst](https://catalyst.app). The brief it answers is in [`ASSIGNMENT.md`](ASSIGNMENT.md).

## Run it

Docker is all you need. No key, nothing to configure.

```sh
make dev
```

| | |
|---|---|
| **The app** | <http://localhost:5173/> |
| **The server's routes**, each with a box for calling it from the browser | <http://localhost:8000/docs> |

`make dev` prints both addresses before it starts, copies files into the running containers as you save them so both halves reload themselves, and on **Ctrl+C** stops both halves and removes their containers. `make up` is the same without the watching, and `make down` stops them by hand.

## What to try first

Five steps on the Strait of Hormuz example. About two minutes, and no key.

1. **Open the map.** Under *A map that is already drawn*, press *Open the map* on the **Strait of Hormuz** card. Seven claims appear, wired left to right: a cause is always left of what it causes. A wire says in its shape — never in colour — what kind of push it is, how hard it pushes, whether it has to keep holding to keep working, and where it came from.
2. **Click a claim.** The panel on the right says why its likelihood is what it is: who says so, the range around it, and the source. Nothing in this product opens over the map.
3. **Change it.** In that panel take up *Change this claim*, then *Suppose this is true*. Only what is downstream moves, and the map as written stays beside it — two worlds painted in one set of coordinates.
4. **Read what moved.** *Where this edit ends up* ranks the endings your edit reached, and gives every claim one word: `unchanged`, `shifted`, `added` or `killed`.
5. **Open the prepared branch.** Press ⌘K (or Ctrl+K), type `Hormuz opens`, and choose *Open the branch: Hormuz opens, then Iran is struck* — the world in which Iran is struck the next day.

Press `?` for every key. The whole map works from the keyboard alone, and exists as a nested list for a reader who never sees the picture.

## With and without a model key

| | No key | With `ANTHROPIC_API_KEY` |
|---|---|---|
| The stored map, its six edits, the branch, the change list | yes | yes |
| Every test, and the whole build | yes | yes |
| *Watch it build* — a sentence becoming a map claim by claim, each proposal the rules refused shown beside it | the Strait of Hormuz card only, played back from a committed recording at the pace it was made | all four cards, and any sentence you type, live |
| What it costs | nothing | a live map is about a dollar and about ten minutes at the default effort; the first claim takes about half a minute to appear |

**Today a key makes every *Watch it build* card run live, and the recording is reachable only without one.** That is being changed: choosing the replay, and seeing it labelled a replay, is not the same as being handed it because something is missing.

What the paid runs have actually cost is written down, dated, in [`docs/measurements.md`](docs/measurements.md) — the committed Strait of Hormuz recording was $4.04 over 36 minutes, and `make eval ONLY=hormuz` was $0.94 over 11 minutes (2026-09-21).

If you have a key, copy `.env.example` to `.env` and fill it in; Docker reads that file by itself. `/api/readyz` reports which keys are present and never what they are.

## Commands

| Command | What it does | Key |
|---|---|---|
| `make dev` | Both halves in Docker, reloading as you edit. Ctrl+C brings them down | |
| `make up` | The same, without watching for edits | |
| `make down` | Stop both halves and remove their containers | |
| `make prod` | The packaged images instead, on <http://localhost:8080/>. Nothing reloads | |
| `make test` | Every test, server and browser app. No network | |
| `make lint` | Style, formatting, types. Changes no file | |
| `make types` | Rewrite the browser app's types from the server's description of itself | |
| `make numbers` | Rewrite the one file that owns every number the worked example quotes | |
| `make numbers-check` | Check that file still says what the engine says. Changes no file | |
| `make eval ONLY=hormuz` | Score what the model proposes, on structure and never on wording. **Spends money** | yes |
| `make record-demo ONLY=hormuz` | Record one example running live, so a copy with no key can play it back. **Spends money** | yes |
| `make run-demo` | The same run kept as a measurement; writes no recording. **Spends money** | yes |
| `make record-cassettes` | Re-record the model answers the tests replay. **Spends money** | yes |
| `make` | This list | |

Only the four marked *spends money* ever call a model, and none of them runs unless you ask for it. `CAP=5` lowers the ceiling for a run, and can only lower the one written in code, never lift it. `make eval` is deliberately not in the build: one prompt scores slightly differently twice, and a merge should not be blocked by a model's mood. The Makefile's own comments say more beside each task.

**Two of these rewrite a committed file from the code itself, and the build fails when either goes stale.** `make types` rewrites `frontend/src/api/schema.ts`, which is what stops the two halves drifting apart. `make numbers` rewrites [`docs/worked-numbers.txt`](docs/worked-numbers.txt), the one place an engine-computed number is written down; every document cites a line of that file by name rather than restating a figure.

**Without Docker**, the checks run on this machine directly and install what they need the first time: the server wants [`uv`](https://docs.astral.sh/uv/), which brings its own Python 3.12, and the browser app wants Node 24. To run the two halves by hand, in two terminals:

```sh
cd backend  && uv run uvicorn katalyst.api.main:app --reload --port 8000
cd frontend && npm ci && npm run dev
```

## Settings

All optional, all read in one place (`backend/src/katalyst/settings.py`), each with a paragraph of its own in `.env.example`.

| Setting | What it does |
|---|---|
| `KATALYST_MODEL` | Which model proposes the claims and the arrows. `claude-sonnet-5` unless you say otherwise; `claude-opus-5` is the only other name a price has been read for, and any other name stops the run rather than billing against a guess |
| `KATALYST_EFFORT` | How hard the model tries: `low`, `medium`, `high`, `xhigh` or `max`. Empty by default, and then one rule holds — **only the recorder sends nothing**, so a recording is the richest map, while everything else asks for `medium` so a map arrives in minutes |
| `KATALYST_RECORDINGS` | Where recorded generations are read from. Empty means the folder that ships here |
| `KATALYST_RUNS` | Where a paid run is written. Empty means `backend/.runs/` |
| `KATALYST_REPLAY_PACE` | Seconds a replay waits between two of its events. `0.6` is the speed a person watches a map arrive at; `0` means no pause at all |

## Tests

```sh
make test
```

No key, no network, and the same checks a pull request runs. On 2026-09-21 that was **642 tests on the server and 358 in the browser app**, none of them skipped. The figures are dated because they move with every round.

The rules are checked against hundreds of maps nobody wrote by hand, each damaged on exactly one rule. The browser app is checked both from what it draws and from reading its own source: no file that draws one of the map's numbers may combine two of them, and nothing anywhere may spin, pulse or sweep. The model boundary is checked against the model's own recorded answers, replayed with the keys stripped out, and a call that was never recorded fails the test rather than dialling out. [`ARCHITECTURE.md`](ARCHITECTURE.md) §7 sets out all six layers.

The 14 end-to-end tests are separate, because they want a browser downloaded first. They start both halves themselves, on ports of their own:

```sh
cd frontend
npx playwright install chromium   # once
npm run e2e
```

## Not built yet

So that nothing here reads as more finished than it is. [`ARCHITECTURE.md`](ARCHITECTURE.md) §10 has the full list, each with the stack it belongs to.

- **No thesis.** What to trade, when to enter, the one event that would prove you wrong: designed, not written. The sweep it would read is built, and nothing on screen reads it.
- **No outside data.** No prediction-market or economic-data adapter, so a market price on a map is a number a person wrote down with its source beside it.
- **One recording.** The Strait of Hormuz plays back with no key; the other three cards say so rather than pretending.
- **No multiplied-out likelihood for a path**, except where you name a destination. Everywhere else the bar names the route's steps and says honestly that there is nothing to show, rather than the browser inventing a second engine.
- **Nothing is stored.** No database, no accounts, no session. Close the tab and the branch you made is gone.

## Where things are

| Where | What |
|---|---|
| `backend/` | The Python server. `domain/` is the rules and the arithmetic, pure; `engine/` asks the model for one proposal at a time and prices, records and replays a run; `fixtures/` is the stored worked example; `api/` is the routes |
| `frontend/` | The browser app: the canvas, the panel, the two-world overlay, the keyboard, and the map growing from a stream. `src/api/schema.ts` is generated from the server, never hand-written; `e2e/` holds the end-to-end tests |
| `evals/` | The four example sentences as cases, the eight structural checks, and the scorecard each run writes. Run by hand, never in the build |
| `docker/`, `compose.yaml` | The images, and how the two halves run together |

## Going deeper

| | |
|---|---|
| [`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md) | What the tool must do and why: decisions, requirements, the invariants that must always hold. §1 is the product in one screen |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | How it is built. Every section says whether it exists yet or is still a plan |
| [`docs/adr/`](docs/adr/) | Numbered decision records — why each choice was made. A higher number supersedes a lower one |
| [`spec/`](spec/) | The spec as a book: one directory per idea, and `vocabulary.md` for the shared language |
| [`docs/measurements.md`](docs/measurements.md) | What the paid runs cost and took, dated. Added to, never rewritten |
| [`docs/worked-numbers.txt`](docs/worked-numbers.txt) | Every number the worked example quotes, generated from the engine |
| <http://localhost:8000/docs> | Every route, while the app is running. The three that do the arithmetic — `POST /api/worlds`, `/api/worlds/diff` and `/api/worlds/conditional` — are specified in [`spec/multiverse/`](spec/multiverse/); the one that writes a map from a sentence, `POST /api/generate`, in [`spec/generation/`](spec/generation/) |
