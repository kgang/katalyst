# Every task you need while working on Katalyst.
#
# Run `make` on its own to see the list.
#
# The Docker tasks need nothing installed but Docker. The rest — `test`, `lint`,
# `types` — run on this machine directly and need `uv` (which brings its own
# Python) and Node 24.

# `make` with no task named prints the list rather than doing something.
.DEFAULT_GOAL := help

# These are names of tasks, not names of files to build. Saying so means `make
# test` still works if a file called `test` ever appears.
.PHONY: help dev up down prod test lint types numbers numbers-check eval record-cassettes record-demo run-demo record-quotes

help: ## Show this list
	@echo "Katalyst — make <task>"
	@echo
	@grep -E '^[a-z][a-z-]*:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN { FS = ":.*## " }; { printf "  %-17s  %s\n", $$1, $$2 }'

# --- running the app --------------------------------------------------------
#
# The three tasks below all run in the foreground and all end the same way:
# Ctrl+C stops both halves AND removes their containers, so the machine is left
# as it was found.
#
# Stopping is not the same as removing. Docker Compose on its own stops the
# containers and leaves them lying about, still carrying the image and the
# environment they were made with — so a later start can quietly be running
# something other than what you just edited. `make down` already promises
# removal; Ctrl+C now keeps the same promise. `docker compose watch`, which
# `dev` used to be, is worse still: Ctrl+C ends only the watching and leaves
# both containers running. `docker compose up --watch` does the same file
# copying while holding the terminal, so stopping it stops the app.
#
# Two traps do that, and they are worth reading once:
#
#   trap 'docker compose down' EXIT   whatever ends this task — Ctrl+C, a crash,
#                                     a clean exit — take the containers down.
#   trap 'exit 0' INT                 Ctrl+C reaches every program in the
#                                     terminal at once. Compose catches it and
#                                     stops the containers; this keeps the shell
#                                     from being killed by the same signal, so
#                                     make does not sign off a deliberate Ctrl+C
#                                     with `*** [dev] Error 130`. A real failure
#                                     is untouched: the trap never runs.
#
# WHERE is the two addresses, printed before Compose's own output starts:
#
#   * the browser app, on port 5173;
#   * the Python server's own page listing every route, with a box beside each
#     one for calling it from the browser, on port 8000.
#
# That second page is NOT reachable through port 5173. The dev server forwards
# only addresses beginning with `/api` to the Python server and answers
# everything else with the app's own page, so `localhost:5173/docs` gives you
# the app, not the routes.
#
# The lines are printed once, up front, rather than again when the two halves
# report themselves healthy. Printing them a second time means a background
# process polling a health route while Compose holds the terminal, and a
# background process that can outlive the task it was helping is worse than a
# line you scroll back to.
WHERE = printf '\n  The app                      http://localhost:5173/\n  The server'"'"'s routes, to try  http://localhost:8000/docs\n\n  Press Ctrl+C to stop everything.\n\n'

dev: ## Start both halves in Docker, reload them as you edit, and stop them on Ctrl+C (http://localhost:5173/)
	@$(WHERE)
	@trap 'docker compose down' EXIT; trap 'exit 0' INT; docker compose up --build --watch

up: ## The same, without watching for edits (http://localhost:5173/)
	@$(WHERE)
	@trap 'docker compose down' EXIT; trap 'exit 0' INT; docker compose up --build

down: ## Stop both halves and remove their containers
	docker compose down

# The packaged run publishes one address and one port: a small web server holds
# the built browser files and hands anything beginning with `/api` to the Python
# server over the private network between the two containers. The server is not
# published on this machine at all, so there is no route list to open here.
prod: ## Build and run the packaged versions of both halves (http://localhost:8080/)
	@printf '\n  The packaged app  http://localhost:8080/\n\n  Press Ctrl+C to stop everything.\n\n'
	@trap 'docker compose -f compose.yaml -f compose.prod.yaml down' EXIT; \
		trap 'exit 0' INT; \
		docker compose -f compose.yaml -f compose.prod.yaml up --build

# --- checks -----------------------------------------------------------------

test: frontend/node_modules ## Run every test, server and browser app. No key needed
	cd backend && env -u ANTHROPIC_API_KEY -u FRED_API_KEY uv run pytest
	cd frontend && npm run check

lint: frontend/node_modules ## Check style and types. Changes no file
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd backend && uv run mypy src
	cd frontend && npm run lint

types: frontend/node_modules ## Rewrite the browser app's types from the server's description of itself
	./scripts/gen-types.sh

# One generated file owns every number the worked example quotes, so that the day
# the engine's arithmetic changes, the diff of that one file is the whole story.
# `numbers` writes it and you review the diff; `numbers-check` is what the build
# runs. Neither needs a key or the network.
#
# The check compares numbers **as numbers, with room**, and everything else
# character for character. It does not compare the file byte for byte, and that is
# not laziness: the first version did, and went red on the build machine over a
# number that differs from this one's in its eighth decimal place. Stale has to
# mean a number moved, not that a machine's last bit differed.
numbers: ## Rewrite the one file that owns every number the worked example quotes
	cd backend && env -u ANTHROPIC_API_KEY -u FRED_API_KEY \
		uv run python -m katalyst.engine.worked_numbers

numbers-check: ## Check that file still says what the engine says. Changes no file
	cd backend && env -u ANTHROPIC_API_KEY -u FRED_API_KEY \
		uv run python -m katalyst.engine.worked_numbers --check

# `eval` runs the saved examples live and scores what comes back on **structure,
# never on wording**: no loops, an ending that names a trade, a reason on every
# arrow, a test on every claim, a graded route or an honest refusal, the cache
# actually being read back, a named reason for stopping inside the ceiling, and a
# page behind every count of past cases. Not one check is a judgement about a
# sentence, because a test that judges a sentence fails when somebody improves
# the prompt.
#
#   make eval ONLY=hormuz         THE ONE TO RUN TODAY - see the paragraph below
#   make eval ONLY=hormuz CAP=5   the same, with a lower ceiling over the round
#   make eval ONLY=hormuz EFFORT=high     the same, thinking harder than the default
#   make eval ONLY=hormuz EFFORT=as-recorded   the same, at the effort the recordings are made at
#   make eval                     all four cases, for the ceiling written in code
#
# **Run it as `ONLY=hormuz` until the prompt is frozen** (Kent, 2026-09-21). Only
# the Strait of Hormuz has a committed recording; the other three cases each mean
# a live run of about forty minutes against words that are about to change, and
# every such change is being batched into one freeze at the end of the engine
# work. When that freeze lands, all four are recorded together and `make eval`
# with nothing else on the line is the ordinary use again. **The program's own
# default is still all four** - this is a standing instruction about what to run
# now, not a change to what the command means, so nothing here silently scores
# less than it says it did.
#
# **A round asks the model for `medium` effort unless told otherwise** (Kent,
# 2026-09-21). At the service's own default one case took the best part of an
# hour, and a scorecard nobody has the patience to run measures nothing. `medium`
# is what a live run in the browser already asks for, so the round also scores the
# maps a person typing a sentence actually gets. The rule is one rule: ONLY THE
# RECORDER SENDS NOTHING. `EFFORT=as-recorded` sends nothing too, for the day you
# want the scorecard of the maps a reviewer with no key is shown. Which model
# answers is unchanged: KATALYST_MODEL, `claude-sonnet-5` unless you say otherwise.
#
# The same three flags as `record-demo`, meaning the same three things. CAP can
# only lower the $15 hard stop written in code, never lift it — and it bounds the
# WHOLE ROUND, not each case: one running total is carried from case to case, each
# is handed what is left, and a case there is nothing left for is not started. The
# scorecard says which ones those were. Which model answers is the KATALYST_MODEL
# setting and nothing else, so the bill and the scorecard's own column can never
# name two different models.
#
# It prints a scorecard, writes one row per case into `evals/runs/<date>.tsv`, and
# exits non-zero if any check did not hold or if the round ran out of money before
# it reached every case. **Every run is kept under `backend/.runs/` whatever it
# scores**, exactly as a recorded run is.
#
# It is deliberately **not** in the build: it costs money, it needs a key, and
# the same prompt scores slightly differently twice — so a merge would be blocked
# by a model's mood. The build's check on the model boundary is the recorded
# exchanges under `backend/tests/cassettes/`, and nothing else.

eval: ## Score what the language model proposes against saved examples. Spends money; needs a key
	cd backend && PYTHONPATH=.. uv run python -m evals.run \
		$(if $(ONLY),--only $(ONLY),) $(if $(CAP),--cap $(CAP),) \
		$(if $(EFFORT),--effort $(EFFORT),)

# --- the two tasks that spend money -----------------------------------------
#
# `record-demo` writes the files a keyless clone plays back: one whole generation
# per example, one JSON object per line. It is the only thing that ever writes
# one — a hand-edited recording is a piece of state that traces to nobody.
#
#   make record-demo                  every example, at the ceiling written in code
#   make record-demo ONLY=hormuz      one of them
#   make record-demo CAP=5            the same, with a lower ceiling
#   make run-demo EFFORT=medium       the same run, thinking less hard
#   make run-demo MODEL=claude-opus-5 the same run, on the other model
#
# All four are flags on the one program, rather than two flags and an
# environment variable: one way to say a thing is one place to look for it.
#
# EFFORT and MODEL are pinned for the whole of one run and never varied between
# its calls: both are read once when the run starts, and changing either mid-run
# would throw away the remembered prefix the run is reading back at a tenth of
# the price. Left unset, EFFORT sends no such field at all and the service's own
# default stands, so the request is byte for byte what it was before anybody had
# an opinion (Kent, 2026-09-20).
#
# CAP can only lower the $15 hard stop that is written in code, never lift it: a
# cap a caller can raise is not a cap. A run that reaches it stops and says what
# it spent and what it got.
#
# `run-demo` is the same run meant as a measurement: it keeps everything and
# writes no recording. One code path, one flag.
#
# **Either way the run is kept.** Whatever becomes of it, both print the whole
# receipt and the reason it stopped, and write everything the run produced —
# every proposal with the seconds and thinking tokens it took, the receipt, the
# map — into `backend/.runs/`, which is not committed. A run that cost money and
# left nothing behind is an afternoon nobody can account for.
#
# Re-run `record-demo` whenever a prompt changes. A recording made against
# different words shows wording this program no longer uses, and the build says
# so.
#
# Everything else in this file runs with no key. This one calls the model for
# real and writes what it says into backend/tests/cassettes, so that every later
# run — and every run of the build — replays those answers instead of paying for
# them again.
#
# It records only the tests that can be recorded. The ones marked `handmade`
# hold a case a live model will not produce on request — a proposal that closes
# a loop, a claim with a blank test, a citation the search never returned — and
# their recordings are one of the honest ones edited by hand. Re-recording them
# would throw the deliberate case away, so this leaves them alone. Each of those
# tests says in its own docstring exactly which edit it needs.
#
# Re-run this whenever a prompt changes. A recording made against different
# words is a recording of a question we no longer ask.

record-demo: ## Record an example running for real, so a keyless clone can watch it. Spends money; needs a key
	cd backend && uv run python -m katalyst.engine.record \
		$(if $(ONLY),--only $(ONLY),) $(if $(CAP),--cap $(CAP),) \
		$(if $(EFFORT),--effort $(EFFORT),) $(if $(MODEL),--model $(MODEL),)

run-demo: ## Run an example for real as a measurement, and write no recording. Spends money; needs a key
	cd backend && uv run python -m katalyst.engine.record --measure-only \
		$(if $(ONLY),--only $(ONLY),) $(if $(CAP),--cap $(CAP),) \
		$(if $(EFFORT),--effort $(EFFORT),) $(if $(MODEL),--model $(MODEL),)

record-cassettes: ## Record the model's real answers for the tests to replay. Spends money; needs a key
	cd backend && uv run pytest tests/boundary -m "not handmade" --record-mode=rewrite
	cd backend && env -u ANTHROPIC_API_KEY uv run pytest \
		tests/boundary/test_expand_cassettes.py::test_no_cassette_contains_a_key

# --- the one task that reads a price from a venue ---------------------------
#
# `record-quotes` writes the committed dated price files under
# `backend/recordings/quotes/`. Everything else in this repository reads those
# files — the demo, the tests and the build alike — so a price reaches the
# product from a committed file before it ever reaches it from a venue. This is
# the only thing that writes one, and the only task here that opens a connection
# to a venue.
#
#   make record-quotes                          re-read every price already committed
#   make record-quotes SLUG=<slug> TOKEN=<id>   record a contract for the first time
#
# It spends nothing and needs no key. It is out of `test` and out of the build
# for the same reason `eval` is out of them: a check that leaves the machine goes
# red the day somebody else's server is busy.
#
# SLUG is the venue's own name for the event a market belongs to — the last part
# of its public web address. TOKEN identifies the one outcome being priced, since
# a contract's yes and its no are two separate order books and one file is one
# side of one contract. Both are already inside every file this has written
# before, which is why re-reading them all needs nothing typed.
#
# Nothing in a written file is a number somebody typed: it holds the venue's two
# answers word for word, and the price, the day, the identifiers and the side are
# worked out from them afterwards by the same code the app reads them with. That
# reading happens BEFORE the file is written, so an answer this program cannot
# read never lands in the repository looking fine. The rest is in the script.

record-quotes: ## Read a contract's price from the venue and commit it, dated. Needs the network; no key
	./scripts/record-quotes.sh $(SLUG) $(TOKEN)

# --- the one rule here that builds a real thing -----------------------------

# The browser app's packages. `uv` installs the server's packages by itself the
# first time `uv run` is used; npm does not, so this does the same job for it.
# The rule runs only when the lock file is newer than the installed packages,
# which means a fresh clone can go straight to `make test`.
frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci
	@touch frontend/node_modules
