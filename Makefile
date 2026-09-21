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
.PHONY: help dev up down prod test lint types eval record-cassettes record-demo run-demo

help: ## Show this list
	@echo "Katalyst — make <task>"
	@echo
	@grep -E '^[a-z][a-z-]*:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN { FS = ":.*## " }; { printf "  %-17s  %s\n", $$1, $$2 }'

# --- running the app --------------------------------------------------------

dev: ## Start both halves in Docker and reload them as you edit (http://localhost:5173)
	docker compose watch

up: ## Start both halves in Docker, without watching for edits
	docker compose up

down: ## Stop both halves and remove their containers
	docker compose down

prod: ## Build and run the packaged versions of both halves (http://localhost:8080)
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

eval: ## Score what the language model proposes against saved examples
	@echo "make eval arrives in the next pull request of this stack: the four saved"
	@echo "examples, scored on structure and never on wording."

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
	cd backend && $(if $(MODEL),KATALYST_MODEL=$(MODEL) ,)uv run python -m katalyst.engine.record \
		$(if $(ONLY),--only $(ONLY),) $(if $(CAP),--cap $(CAP),) \
		$(if $(EFFORT),--effort $(EFFORT),)

run-demo: ## Run an example for real as a measurement, and write no recording. Spends money; needs a key
	cd backend && $(if $(MODEL),KATALYST_MODEL=$(MODEL) ,)uv run python -m katalyst.engine.record \
		--measure-only \
		$(if $(ONLY),--only $(ONLY),) $(if $(CAP),--cap $(CAP),) \
		$(if $(EFFORT),--effort $(EFFORT),)

record-cassettes: ## Record the model's real answers for the tests to replay. Spends money; needs a key
	cd backend && uv run pytest tests/boundary -m "not handmade" --record-mode=rewrite
	cd backend && env -u ANTHROPIC_API_KEY uv run pytest \
		tests/boundary/test_expand_cassettes.py::test_no_cassette_contains_a_key

# --- the one rule here that builds a real thing -----------------------------

# The browser app's packages. `uv` installs the server's packages by itself the
# first time `uv run` is used; npm does not, so this does the same job for it.
# The rule runs only when the lock file is newer than the installed packages,
# which means a fresh clone can go straight to `make test`.
frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci
	@touch frontend/node_modules
