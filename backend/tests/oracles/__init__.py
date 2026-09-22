"""Two independent enumerators that judge the engine, and the maps they judge it on.

An **oracle** here is a second program that answers the same question as the
engine by a different route, so that a disagreement between the two says one of
them is wrong. Record 0016 asks for two, because they see different things:

* `by_summing` takes the engine's **own** yes/no tables — for each claim, how
  likely it is to come true given which of its causes came true — and adds up the
  whole joint by brute force. It proves the elimination, the *Suppose this is
  true* surgery and the *This happened* conditioning. It is **blind to a wrong
  table**: hand it a table built from the wrong arithmetic and it will agree with
  the engine to the last bit.

* `by_integrating` is **forbidden every table the engine builds**. It is given
  the arrow parameters alone — each cause's stated chance, its delay, its shape,
  its half-life, which of the source's times it reads, and whether the claim is an
  event or a state — and enumerates the full joint of event times. That is the
  oracle that could have caught the error record 0016 found in its own first
  design. It is only computable on maps of four claims or fewer.

* `maps` is the seeded generator both of them run on: the red team's adversarial
  four-claim maps, and the maps built to break a state, on the same seeds.

Why the second is forbidden the engine's internals is lesson 20 of the handoff,
paid for once: a hundred per cent coverage and 259 green tests proved nothing
about whether the arithmetic was right, because no test compared the engine with
an answer worked out independently.

Nothing in this package imports `katalyst`. That is the independence, made
mechanical rather than promised.
"""
