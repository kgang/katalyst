This is a take home coding assignment for https://catalyst.app/.

Catalyst is the agent layer for finance. We turn natural language — a thesis, strategy, hedge, or trading idea — into live execution across any market, venue, or asset class from prediction markets to commodities to tokens to private markets. It is a seed stage company with investments from Sequoia, Jump Trading, and Lux Capital.

Here are more details about Catalyst: https://coastalhq.co/scoop/e3a34548-1964-4b30-96ea-52801a558dd2

The goal of the project is to create a functional protoype of the concept behind Catalyst as a company. The full brief I was provided for this is located at ./ASSIGNMENT.md

RULES FOR THIS REPO

* Significant architectural decisions should be recorded at ./docs/adr in a numbered order. Higher number records supersede lower numbered ones.
* Enduring context between agents should live as all caps docs in the root of the repo, e.g. AGENTS.md, ASSIGNMENT.md, PRODUCT_REQUIREMENTS.md. These should always be kept up to date if you notice them drifting.
* More detailed descriptions, diagrams about particular systems or complex features should be written to ./spec
* Specs should follow best practices regarding spec-driven development. Some key aspects of specs for this repo should include invariants and anti-patterns
* This is an experimental prototype and I am a solo developer. However, I would like to use best practices regarding commit messages, PRs, and PR stacks to maintain the navigability, hygiene, and legibility of this repo.