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
.PHONY: help dev up down prod test lint types eval record-cassettes

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
	@echo "make eval arrives in stack 04, the stack that first asks a language model for anything."

# --- the one task that spends money -----------------------------------------
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
