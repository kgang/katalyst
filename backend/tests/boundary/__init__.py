"""Tests of the edge where we talk to a language model.

Each test replays an answer recorded once and committed under
`backend/tests/cassettes`, so the suite needs no key and makes no network call.
An answer that was never recorded fails the test rather than dialling out.

Nothing lives here yet. Stack 04 adds the first recorded answer, including one
in which the model proposes a loop and the rules layer rejects it.
"""
