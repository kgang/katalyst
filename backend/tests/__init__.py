"""The test suite, in three layers.

- `unit` — the rules of the map, checked on their own with no network and no
  moving parts. This is where the correctness claims live.
- `boundary` — the edge where we talk to a language model, checked against
  answers recorded once and replayed since, so no test needs a key.
- `api` — the routes, called in-process through a test client.

`cassettes` holds the recorded answers the boundary layer replays.
"""
