# Katalyst

You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

Each step is a claim that can be checked by a date, judged by a named source. Each arrow says how one claim pushes on the next, how strongly, and how long it takes. Every likelihood on the map shows three numbers side by side — what the model thinks, what you think, what the market is pricing — and every number can show why. Change a claim ("…but Iran is struck the next day") and only what is downstream moves; the original is kept for comparison. The map ends in a thesis: what to trade, when to enter, and the one event that would prove the idea wrong.

This is a take-home prototype for [Catalyst](https://catalyst.app). The brief is in `ASSIGNMENT.md`.

That is the whole product. It is being built in numbered stacks, and `ARCHITECTURE.md` says section by section what exists and what is still a plan. As of 2026-09-21: the rules of the map, a stored worked example, the engine that works a change through it, the canvas that draws it, and **the pipeline that writes a map from a sentence** are built. A hypothesis goes to a language model one claim at a time; every proposal is checked against the rules of the map before it is allowed on, what the checker refuses is shown rather than hidden, and **the map draws itself on screen as the answers arrive** — a reserved rectangle where the next claim will go, never a spinner. **The thesis is the one part deliberately not here yet.**

## Run it

You need Docker, and nothing else. No key is needed to start the app or to run the tests.

```sh
docker compose up           # build both halves, then start them
```

Then open <http://localhost:5173>. That is the browser app. The Python server is on <http://localhost:8000>, and the browser app reaches it through `/api` on its own address, so there is nothing to point at anything.

## What you see

**The launchpad.** Two ways in — *Explore* ("what happens next?") and *Verify* ("does A really lead to B?") — and the four example hypotheses from the brief. With a model key all four run live. With none, the Strait of Hormuz card plays a recorded generation back through the same route and the same canvas, and the other three say plainly that nothing has been recorded for them yet rather than failing when you press them. At the foot, a strip reporting what the server said about itself.

**Start here.** With no key, press the Strait of Hormuz card. That one press is the whole product: a sentence becomes a map claim by claim, the rules refuse some of what the model proposes and the refusals stay on screen, the likelihoods arrive once at the end, and then every button works — suppose a claim, report one as news, change a push, add your own number — with no key and no network.

**The map.** Open the Strait of Hormuz and the page swaps for it: seven tiles with typed sockets, each with the claim, three belief chips side by side (what the model thinks, what you think, what the market prices), and its resolve-by date. Wires between them carry five things at once, and not one of them in colour: what kind of push it is and how hard it pushes (the stroke's pattern and its width), whether it has to keep holding to keep working (one stroke or two), whether it loops back on the world it is measuring, and where it came from — one, two or three dots at the wire's tail, never the line. A plate at each wire's midpoint reads the push back in words, with the delay in days. The layout is worked out left to right on a background thread, so a cause is always left of what it causes. Point at a claim and a lens dims everything that neither causes it nor is caused by it. A panel on the right answers "why is this number what it is" and never opens over the map. The line under the map says which address the numbers came from.

**The branch.** Press `⌘K` (or `Ctrl+K`), type "Hormuz opens", and the branch in which Iran is struck the next day opens over the base map: one layout, two worlds painted in the same coordinates, the claim the branch added drawn where it belongs, and one word per claim saying what the edit did to it. Beside it, a rail listing the endings the edit can reach and a panel listing the branch's edits in the order they were made. The hypothesis's own tile reads *Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"*, because the strike's arrow into it arrived after the supposition.

**The growing map.** Type a sentence of your own, or press a card, and the map builds itself: a rectangle held open where the first claim will land, then claims as the model proposes them and our rules accept them, wires in the order cause runs, and the likelihood chips filling in once at the end — never four times as the causes arrive, because a number that changes four times is four numbers nobody computed. Beside the map, one row per proposal the rules refused, in the validator's own words, and a strip saying what the run cost. There is no spinner anywhere in this product and a test walks every component and every stylesheet to prove it.

**Every number on those screens came from the server.** The canvas asks the three world routes below for a world, a difference and the number on one arrow, and draws what comes back — it works nothing out for itself, and a test reads its own source to keep it that way. If the server cannot answer, the page falls back to the stored example and says on screen that it has done so, because a map you can still read beats a blank screen. The whole map also works from the keyboard (`?` lists every key) and exists as a nested list for a reader who never sees the picture.

## What the server can already compute

`/api/fixtures` lists the stored examples; <http://localhost:8000/api/fixtures/hormuz> returns the Strait of Hormuz map together with the branch in which Iran is struck the next day, every claim and arrow with its own source beside it. That is written by hand. The three routes below are not — they fold a branch onto a map, work every likelihood through time, and hand back numbers nobody typed.

**One world.** A map, a branch and a seed are the whole of it; the same three give a byte-identical answer on any machine.

```sh
curl -s localhost:8000/api/worlds \
  -H 'content-type: application/json' \
  -d '{"base_id":"hormuz","seed":20261001}' | jq '.beliefs.M1'
```

```text
the shape of the answer:  { "p": …, "lo": …, "hi": …, "owner": "model" }
```

That is the Polymarket contract's likelihood with the range around it, worked out from two thousand versions of the map times eight worlds each, in under a tenth of a second. **The four figures are not printed here**, and that is deliberate: the route answers at full precision, and the sixteenth digit of a number that came out of a floating-point sum is not the same on every machine, so printing it would promise a reader something this program cannot deliver. They are in [`docs/worked-numbers.txt`](docs/worked-numbers.txt) instead, on the line named `M1 · base · reading`, along with every other number the worked example quotes. That file is generated by `make numbers` and the build fails when it goes stale, so it is the one place in this repository where an engine-computed number is written down and kept true.

Leave the branch out for the map as written; send one, whole, to fold it on first. (`jq` above only pretty-prints one field of the answer. The route itself needs nothing but `curl`.)

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

That sentence is quoted here word for word from [`docs/worked-numbers.txt`](docs/worked-numbers.txt), where it is the line named `strike · the sentence beside the list`. Its two numbers are written the way every likelihood in this product is written — two significant figures, with `<.01` and `>.99` standing in for the two claims nobody here is entitled to make.

The whole answer also carries a word per claim (`unchanged`, `shifted`, `added`, `killed`) and the endings that moved in ranked order. A third route, `POST /api/worlds/conditional`, gives the number on one arrow: its target, with its source **supposed** true — never how often the two happen to show up together.

A branch that does not fit the map comes back as `422` with **every** reason at once, each a stable code and one plain sentence naming the claim or the arrow by its words. Never a half-applied branch, never a silent repair.

**A map, written from a sentence.** `POST /api/generate` takes the sentence, asks the model for one claim at a time, and answers as a stream — `event:` and `data:` lines you can watch arrive in a terminal — so the map is readable while it is still being built:

```sh
curl -N -s localhost:8000/api/generate \
  -H 'content-type: application/json' \
  -d '{"hypothesis":"The Strait of Hormuz reopens to unrestricted commercial transit"}'
```

Leave the seed out and the server mints one, and says in the first event which it minted, so the run reproduces from the moment it starts. Add a `target` and the run is graded against it and says plainly when there is no route to it, rather than inventing a bridge. Every proposal the rules refuse arrives as its own event, with the refusal's own sentence — watching the checker refuse the model is half of what there is to see.

Two more routes go with it: `POST /api/generate/insert` drafts one new claim and its arrows for a map that already exists, and `GET /api/generate/{id}/transcript` hands back what a generation proposed, accepted and refused, in order, for as long as the process that ran it is alive. Nothing is kept on disk between requests.

**With no key**, the same route plays a *recording* back through the same stream, at the same pace, and the receipt says it was a replay and cost nothing. It is chosen by the sentence in the request and nothing else, so the keyless path and the live path send byte-identical requests. A recording is one whole generation, written only by `make record-demo` into `backend/recordings/`, and `/api/readyz` lists which are present — so the screen can say what a keyless clone can and cannot do, rather than guessing. **One is committed today**, the Strait of Hormuz.

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
make numbers  # rewrite the one file that owns every number the worked example quotes
make numbers-check  # check that file still says what the engine says. Changes no file
make          # the whole list of tasks
```

**Two of these tasks rewrite a committed file from the code itself, and the build fails when either output goes stale.** `make types` rewrites `frontend/src/api/schema.ts` from the server's own description of itself, which is what stops the two halves drifting apart. `make numbers` rewrites [`docs/worked-numbers.txt`](docs/worked-numbers.txt), which holds every number the Strait of Hormuz example quotes — each claim's reading, what the strike branch did to it, the number on every arrow — with the numbers a person typed into the example kept separately from the numbers the engine worked out. Prose quotes a computed number only where that file is one link away, so that the day the arithmetic changes, the diff of one file is the whole list of what moved. `make numbers-check` is what the build runs: it works every number out again and compares numbers *as numbers*, so "stale" means a number moved rather than that one machine's last bit differed from another's. None of the three needs a key or the network.

**Four tasks call a model and spend real money**, and none of them runs unless you ask for it. Everything else in this repository runs with no key at all.

```sh
make record-cassettes            # the real exchanges the tests replay
make record-demo                 # a whole generation per example, for a keyless clone to play back
make record-demo ONLY=hormuz     # just one of them
make record-demo CAP=5           # the same, with a lower spending ceiling
make run-demo                    # the same run as a measurement: keeps everything, writes no recording
make run-demo EFFORT=medium      # the same run, thinking less hard
make run-demo MODEL=claude-opus-5  # the same run, on the other model
make eval                        # score the four examples on structure, and print a scorecard
make eval ONLY=hormuz CAP=5      # one case, with a lower spending ceiling
```

**`make eval` is the one that says whether the prompt is any good**, and it is deliberately not in `make test`: it needs a key, it costs money, and one prompt scores slightly differently twice, so a merge would be blocked by a model's mood. It runs each example live through the same walk the stream route uses, and scores only **structure, never wording** — no loops; an ending that names something to trade or says why there is none; a reason on every arrow and a page behind every arrow claiming one; criteria, a judge and a date on every claim; a graded route or an honest refusal from the Verify door, including one case whose destination is deliberately out of reach; the remembered prefix actually read back on the second call; a named reason for stopping, inside the ceiling; and a page behind every count of past cases. It prints the scorecard, writes one row per case into `evals/runs/<date>.tsv` — committed, so two of them side by side are how a prompt change is judged — and exits non-zero if a check did not hold. A check on a model's *sentences* would fail when somebody improved the prompt, so there is none.

**`make record-demo` writes the recordings a keyless clone plays back** — one whole generation per example, into `backend/recordings/` — and it is the only thing that ever writes one, because a recording edited by hand is a piece of state that traces to nobody. **`make run-demo` is the same run meant as a measurement**: it keeps everything and writes no recording. **No paid run is ever thrown away.** All three of the whole-map tasks — `record-demo`, `run-demo` and `eval` — print the whole receipt and the reason the run stopped, and write every proposal — with the seconds and the thinking tokens it took — into `backend/.runs/`, which is not committed, because it is the record of one afternoon's spending rather than something the product plays back. What those runs have cost so far is written down, dated, in [`docs/measurements.md`](docs/measurements.md).

`CAP` can only lower the spending ceiling written in code, never lift it: a cap a caller can raise is not a cap. A run that reaches it stops and says what it spent and what it got. `EFFORT` and `MODEL` are pinned for a whole run and never varied between its calls — changing either mid-run would throw away the remembered prefix the run is reading back at a tenth of the price. All four refuse to start with no key and say so.

Re-run `make record-demo` whenever a prompt changes: a recording made against different words shows wording this program no longer uses, and the build says so rather than letting it pass unnoticed.

**Five settings you may want**, all optional, and read in exactly one place (`backend/src/katalyst/settings.py`); each is in `.env.example` with a paragraph of its own:

| Setting | What it does |
|---|---|
| `KATALYST_MODEL` | Which model proposes the claims and the arrows. `claude-sonnet-5` unless you say otherwise, which is what the measured runs and the recorded answers were made on; `claude-opus-5` is the only other name a price has been read for, and asking for anything else stops the run rather than billing against a guess |
| `KATALYST_EFFORT` | How hard the model tries — `low`, `medium`, `high`, `xhigh` or `max`. Empty by default, and then each path takes its own: **the recorder sends nothing**, so the service's own default stands and a recording is the richest map; **a live run asks for `medium`**, so a map arrives in minutes rather than the best part of an hour (Kent, 2026-09-21; the measured runs are in `docs/measurements.md`). Set it to override both. The receipt and a recording's first line say which effort made the map |
| `KATALYST_RECORDINGS` | Where recorded generations are read from. Empty means the folder that ships here. Point it elsewhere to play a recording back through the real route before committing it |
| `KATALYST_RUNS` | Where a paid run is written. Empty means `backend/.runs/` |
| `KATALYST_REPLAY_PACE` | How long a replay waits between two of its events, in seconds. `0.6` unless you say otherwise, which is the speed a person watches a map arrive at; `0` means no pause at all. One number rather than a length and a switch beside it, and never something a request can ask for — a client that could skip the pacing could skip the thing a recording exists to show |

The end-to-end tests are not in `make test`, because they want a browser downloaded first. They start both halves themselves, on ports of their own, so there is nothing to have running:

```sh
cd frontend
npx playwright install chromium   # once
npm run e2e
```

They run side by side, five browsers at a time here and two on the build machine, and they start the server at a **shortened** replay pace rather than none — `playwright.config.ts` carries both numbers and the reasoning behind each. Shortened rather than off because what they are about is a map *arriving*: with no pause at all every event lands in one tick, and there is no moment at which that is true.

**They never attach to a server that is already up.** If you have two worktrees of this repository open, the second run stops at once and names the port it wanted rather than quietly testing the branch checked out in the first — which has happened, in both directions, with neither side able to tell from the output. Give it ports of its own with `KATALYST_E2E_BACKEND_PORT` and `KATALYST_E2E_FRONTEND_PORT`; the defaults are the two numbers continuous integration uses.

## Tests

```sh
make test
```

No network, no key, and the same checks a pull request runs. On 2026-09-21 that was **`<<COUNT: server>>` tests on the server and `<<COUNT: browser>>` in the browser app**, plus `<<COUNT: end-to-end>>` end-to-end tests. The figures are dated because they move with every round; what does not move is that all of them run with no key and no network:

- **The rules, checked against maps nobody wrote by hand.** Hundreds of random maps per test, built by the generators in `backend/tests/strategies.py` — some correct by construction, some damaged on exactly one rule — and when one fails, the `hypothesis` library shrinks it to the smallest map that still breaks. Every line and every branch of `backend/src/katalyst/domain/` is run.
- **The engine.** Folding a branch onto a map, working every likelihood through time, and saying what moved — including a state machine that re-checks *only what is still connected to the edit may move* after every step of a generated sequence of edits.
- **The stored example.** The Strait of Hormuz map and its "Iran is struck the next day" branch, held to every rule they claim to obey, and refusing to load at all if they break one.
- **The routes**, including the `422` that carries every reason a branch was refused.
- **The browser app**, from what it draws — the launchpad, tiles, belief chips, wires, layout, the diff overlay, the rail, the branch panel, the Inspector, the path bar, the keyboard, the outline, and the map growing from a stream — and from reading its own source: one test walks every file that draws one of the map's numbers and fails on any multiplication of one, because the moment this half works out a number of its own there are two engines on the map; another walks every component and every stylesheet and fails on anything that spins, pulses or sweeps.
- **The one that matters most**: it reads every file under `backend/src/katalyst/domain/` — the layer that holds the rules — and fails if any of them imports the routes, the engine, the outside-data layer, or a language-model client. That layer must stay decidable by our own code alone.

**Nothing in either suite is skipped.** The one test that used to be — the canvas's own answer to "what can this edit reach", compared against the server's — had nothing to compare against until the two were joined. They are joined, so it runs, and the day those two disagree is the day this stops being traceable.

**The model boundary is tested against the model's own real answers**, recorded once to `backend/tests/cassettes/` and replayed ever after with the keys stripped out. Four of those recordings are honest ones edited by hand in exactly one place, because a live model will not produce the case on request: a proposal that closes a loop, a claim with a blank test, a citation the search never returned. Each of those tests says in its own docstring which edit it needs, and `make record-cassettes` leaves them alone. A call that has not been recorded fails the test instead of dialling out, which is what keeps the suite free of keys forever.

Continuous integration runs six jobs on every pull request — `backend`, `frontend`, `types-fresh` (the committed browser types still match the server's data shapes), `docker` (both packaged images still build), `e2e` (one browser, both halves, the stored example opened and edited by keyboard alone) and `recordings` (every committed recording still parses and was made against the words this program uses now). None of them is given a key, and none needs one.

## Not built yet

So that nothing here reads as more finished than it is:

- **Only one example is recorded.** The Strait of Hormuz plays back with no key; the other three cards say so rather than pretending. Each of the three is about forty minutes of live model time and a few dollars, written by `make record-demo ONLY=<example>` whenever somebody chooses to pay for it.
- **No path product on a stored map.** A chain of four plausible steps is not a plausible chain, and the number that says so is only worked out for the *Verify* door, where you name a destination. Everywhere else the bar names the route's steps and says honestly that there is no product to show, rather than the browser multiplying and inventing a second engine.
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
| `docs/measurements.md` | What the paid runs actually cost and took, dated. Added to, never rewritten |
| `docs/research/` | Research reports that fed the requirements. Inputs, not decisions |
| `backend/` | Python server: `domain/` (the rules and the arithmetic, pure), `fixtures/` (the stored worked example), `engine/` (asks the model for one proposal at a time, decides where each number came from, prices the run, records it and plays it back), `grounding/` (will fetch outside data), `api/` (routes, including the generation stream) |
| `frontend/` | React browser app: the canvas, the Inspector, the diff overlay, the keyboard, and the map growing from a stream. `src/api/schema.ts` is generated from the server, never hand-written; `e2e/` holds the end-to-end tests |
| `evals/` | The four example hypotheses as cases, the eight structural checks, and the scorecards each run writes. Run by hand with `make eval`; never in the build |
| `docker/`, `compose.yaml` | Container images and how they run together |

Start with `PRODUCT_REQUIREMENTS.md` §1 (the product in one screen), then `ARCHITECTURE.md`.
