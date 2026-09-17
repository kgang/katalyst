"""The rules of the cause-and-effect map. Pure code, and the part we prove correct.

What this layer is for
----------------------
It defines what a proposition, a link, a belief, a graph, a branch, and a world
are, and it decides whether a proposed map is valid: every proposition is
resolvable by a date against a named source, every link says why it exists and
where its number came from, there are no loops, and every chain of reasoning
ends somewhere tradeable. It also applies interventions and propagates beliefs.

The one rule that shapes everything: **the model proposes; this layer disposes.**
A language model never edits the map. It returns proposals, and code in here
accepts a proposal or rejects it with reasons. That is why this layer can be
tested against thousands of generated inputs while the rest of the system cannot.

What this layer must never do
-----------------------------
- No input or output of any kind: no network calls, no files, no database, no
  printing.
- No clock. Nothing in here asks what time it is; a date that matters is passed
  in as an argument.
- No randomness unless a seed is passed in explicitly, so that the same inputs
  always give the same answer and any result can be reproduced.
- No imports from `katalyst.engine`, `katalyst.api`, or `katalyst.grounding`,
  and none from a language-model client library or any HTTP library. A test,
  `test_domain_imports_nothing_impure`, reads every file in this package and
  fails if one of those imports appears.

Nothing lives here yet. Stack 02 adds the data shapes and the validity rules.
"""
