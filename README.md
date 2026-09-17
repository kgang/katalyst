# Katalyst

You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date, judged by a named source. Each arrow says how one claim pushes on the next, how strongly, and how long it takes. Every likelihood on the map shows three numbers side by side — what the model thinks, what you think, what the market is pricing — and every number can show why. Change a claim ("…but Iran is struck the next day") and only what is downstream moves; the original is kept for comparison. The map ends in a thesis: what to trade, when to enter, and the one event that would prove the idea wrong.

This is a take-home prototype for [Catalyst](https://catalyst.app). The brief is in `ASSIGNMENT.md`.

That is the whole product. It is being built in numbered stacks, and `ARCHITECTURE.md` says section by section what exists and what is still a plan. As of 2026-09-17: the rules of the map, a stored worked example, the engine that works a change through it, and the canvas that draws it are all built. **The engine and the canvas are not joined yet** — the canvas reads the stored example, and every number the engine would have computed is on screen as an absence with the reason beside it. Nothing here asks a language model anything, and there is no thesis.

## Run it

You need Docker, and nothing else. No key is needed to start the app or to run the tests.

```sh
docker compose up           # build both halves, then start them
```

Then open <http://localhost:5173>. That is the browser app. The Python server is on <http://localhost:8000>, and the browser app reaches it through `/api` on its own address, so there is nothing to point at anything.

## What you see

**The launchpad.** Two ways in — *Explore* ("what happens next?") and *Verify* ("does A really lead to B?") — and the four example hypotheses from the brief. One of them is live; the other three say so rather than failing when you press them. At the foot, a strip reporting what the server said about itself.

**The map.** Open the Strait of Hormuz and the page swaps for it: seven tiles with typed sockets, each with the claim, three belief chips side by side (what the model thinks, what you think, what the market prices), and its resolve-by date. Wires between them carry five things at once, and not one of them in colour: what kind of push it is and how hard it pushes (the stroke's pattern and its width), whether it has to keep holding to keep working (one stroke or two), whether it loops back on the world it is measuring, and where it came from — one, two or three dots at the wire's tail, never the line. A plate at each wire's midpoint reads the push back in words, with the delay in days. The layout is worked out left to right on a background thread, so a cause is always left of what it causes. Point at a claim and a lens dims everything that neither causes it nor is caused by it. A panel on the right answers "why is this number what it is" and never opens over the map. The line under the map says which address the numbers came from.

**The branch.** Press `⌘K` (or `Ctrl+K`), type "Hormuz opens", and the branch in which Iran is struck the next day opens over the base map: one layout, two worlds painted in the same coordinates, the claim the branch added drawn where it belongs, and one word per claim saying what the edit did to it. Beside it, a rail listing the endings the edit can reach and a panel listing the branch's edits in the order they were made. The hypothesis's own tile reads *Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"*, because the strike's arrow into it arrived after the supposition.

**Every computed number is an absence with a reason.** Where a likelihood would have moved, the screen says "no engine yet" and, in one more click, why: nothing has worked it out. The part of this system that works one out is the server's, and the two are not joined yet — that is the first job of stack 04. The whole map also works from the keyboard (`?` lists every key) and exists as a nested list for a reader who never sees the picture.

## What the server can already compute

`/api/fixtures` lists the stored examples; <http://localhost:8000/api/fixtures/hormuz> returns the Strait of Hormuz map together with the branch in which Iran is struck the next day, every claim and arrow with its own source beside it. That is written by hand. The three routes below are not — they fold a branch onto a map, work every likelihood through time, and hand back numbers nobody typed.

**One world.** A map, a branch and a seed are the whole of it; the same three give a byte-identical answer on any machine.

```sh
curl -s localhost:8000/api/worlds \
  -H 'content-type: application/json' \
  -d '{"base_id":"hormuz","seed":20261001}' | jq '.beliefs.M1'
```

```json
{ "p": 0.4562071732264012, "lo": 0.3183414645119589, "hi": 0.6011338456638751, "owner": "model" }
```

That is the Polymarket contract's likelihood with the range around it, worked out from two thousand versions of the map times eight worlds each, in under a tenth of a second. Leave the branch out for the map as written; send one, whole, to fold it on first. (`jq` above only pretty-prints one field of the answer. The route itself needs nothing but `curl`.)

**What a change did.** One map, two branches, one seed — one seed for the pair, so every difference is the edit rather than a wash of sampling noise. A branch is sent whole rather than by name, because there is nowhere to keep one yet, so this uses `jq` to lift the stored branch out of the example and pipe it straight into the request:

```sh
curl -s localhost:8000/api/fixtures/hormuz \
  | jq '{base_id: "hormuz", seed: 20261001, branch_b: .branches[0]}' \
  | curl -s localhost:8000/api/worlds/diff \
      -H 'content-type: application/json' --data @- \
  | jq -r '.summary'
```

```text
"Hormuz opens, then Iran is struck" moves A Polymarket contract "Brent below $70 on
2026-10-31" resolves YES from .50 to .42 by 2026-10-04 and leaves 1 claim untouched.
```

The whole answer also carries a word per claim (`unchanged`, `shifted`, `added`, `killed`) and the endings that moved in ranked order. A third route, `POST /api/worlds/conditional`, gives the number on one arrow: its target, with its source **supposed** true — never how often the two happen to show up together.

A branch that does not fit the map comes back as `422` with **every** reason at once, each a stable code and one plain sentence naming the claim or the arrow by its words. Never a half-applied branch, never a silent repair.

## While you work

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
make eval     # says out loud that it arrives in stack 04, rather than pretending
make          # the whole list of tasks
```

The one end-to-end test is not in `make test`, because it wants a browser downloaded first. It starts both halves itself, so there is nothing to have running:

```sh
cd frontend
npx playwright install chromium   # once
npm run e2e
```

## Tests

```sh
make test
```

No network, no key, and the same checks a pull request runs. Today that is **259 tests on the server and 177 in the browser app**, plus the one end-to-end test above:

- **The rules, checked against maps nobody wrote by hand.** Hundreds of random maps per test, built by the generators in `backend/tests/strategies.py` — some correct by construction, some damaged on exactly one rule — and when one fails, the `hypothesis` library shrinks it to the smallest map that still breaks. Every line and every branch of `backend/src/katalyst/domain/` is run.
- **The engine.** Folding a branch onto a map, working every likelihood through time, and saying what moved — including a state machine that re-checks *only what is still connected to the edit may move* after every step of a generated sequence of edits.
- **The stored example.** The Strait of Hormuz map and its "Iran is struck the next day" branch, held to every rule they claim to obey, and refusing to load at all if they break one.
- **The routes**, including the `422` that carries every reason a branch was refused.
- **The browser app**, from what it draws — tiles, belief chips, wires, layout, the diff overlay, the rail, the branch panel, the Inspector, the path bar, the keyboard, the outline — and from reading its own source: one test walks every file that draws one of the map's numbers and fails on any multiplication of one, because the moment this half works out a number of its own there are two engines on the map.
- **The one that matters most**: it reads every file under `backend/src/katalyst/domain/` — the layer that holds the rules — and fails if any of them imports the routes, the engine, the outside-data layer, or a language-model client. That layer must stay decidable by our own code alone.

**One of the 177 browser tests is skipped, on purpose.** It would compare the canvas's own answer to "what can this edit reach" against the server's, and there is nothing to compare against until the two are joined. It is skipped rather than deleted, because the day those two disagree is the day this stops being traceable.

One layer is built into the shape of the suite and is still empty: calls to the model replayed from responses recorded under `backend/tests/cassettes/`. There is nothing to record yet, because nothing calls a model until stack 04. A call that has not been recorded fails the test instead of dialling out, which is what keeps the suite free of keys forever.

Continuous integration runs five jobs on every pull request — `backend`, `frontend`, `types-fresh` (the committed browser types still match the server's data shapes), `docker` (both packaged images still build), and `e2e` (one browser, both halves, the stored example opened and edited by keyboard alone). None of them is given a key.

## Not built yet

So that nothing here reads as more finished than it is:

- **The canvas and the engine are not joined.** The browser reads the stored example; every number the engine would have computed is drawn as an absence with its reason. Switching one line over is the first job of stack 04.
- **No language model.** Nothing in this repository has ever called one. You cannot type a hypothesis and watch a map get written; the one map there is was written by hand, with a source beside every number.
- **No event stream.** Every route is an ordinary request and its answer, so the map is fetched whole rather than drawing itself as a model reasons.
- **No outside data.** There is no Polymarket adapter and no FRED adapter, so a market price on the map is a number a person wrote down with its source beside it.
- **No thesis.** What to trade, when to enter, the one event that would prove you wrong: designed, not written. The sweep it reads — flip each claim in turn and see what it does to every ending — is built, and nothing on screen reads it.
- **Nothing is stored.** No database, no accounts, no session. Close the tab and the branch you made is gone.

## Map of the repo

| Where | What |
|-------|------|
| `PRODUCT_REQUIREMENTS.md` | What the tool must do and why: decisions, requirements, the invariants that must always hold |
| `ARCHITECTURE.md` | How it is built. Every section says whether it is built yet or only planned |
| `AGENTS.md` | Rules of the repo and working agreements |
| `docs/adr/` | Numbered decision records — a journal of why each choice was made |
| `spec/` | The spec, organized as a book: one directory per idea, one file per chapter |
| `docs/research/` | Research reports that fed the requirements. Inputs, not decisions |
| `backend/` | Python server: `domain/` (the rules and the arithmetic, pure), `fixtures/` (the stored worked example), `engine/` (builds a world from a map, a branch and a seed; will also talk to the model), `grounding/` (will fetch outside data), `api/` (routes) |
| `frontend/` | React browser app: the canvas, the Inspector, the diff overlay, the keyboard. `src/api/schema.ts` is generated from the server, never hand-written; `e2e/` holds the one end-to-end test |
| `docker/`, `compose.yaml` | Container images and how they run together |

Start with `PRODUCT_REQUIREMENTS.md` §1 (the product in one screen), then `ARCHITECTURE.md`.
