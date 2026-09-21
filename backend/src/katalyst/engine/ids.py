"""Minting identifiers, which is why this lives here and not in the rules layer.

Every claim, arrow, map and branch carries an identifier, and our own code makes
all of them — never a language model. A model asked for identifiers reuses them
between calls, collides the moment two branches fork from the same map, and
refers to claims it never created. So the model names a claim by its text and by
where it sits in its own proposal, and this module turns that into a real
identifier.

Why the rules layer cannot do this. Making an identifier that is unique without
any central register needs two things the rules layer refuses to have: the
current time, and a source of randomness. Reading neither is exactly what makes
that layer pure, repeatable and testable against thousands of generated inputs.
So minting happens out here, at the edge, and the finished string is passed in as
an ordinary value.

The rules layer never checks the format of what it is given. That is deliberate,
and it is what lets the stored Hormuz example use identifiers a person can read —
`H`, `C`, `B` — instead of twenty-six characters that teach nobody anything when
a test fails.
"""

import secrets

from ulid import ULID

BIGGEST_SEED = 2**53 - 1
"""The largest whole number that survives the trip to a browser and back.

**This is not a style choice.** A browser holds every number as a double, and
above this it starts rounding silently: the first measured run minted
`4803646386380448080`, and JavaScript reads that back as `4803646386380448300`.
Nothing errors. The browser then asks for a world under a seed the server never
used, gets different numbers, and every explanation of why is wrong.

So a seed is minted inside the range a browser can hold exactly, and every route
that takes one refuses anything above it rather than accepting a number it knows
will not come back the same.
"""


def mint_id() -> str:
    """Make one new identifier: unique without coordination, and sorted by creation time.

    The value is a ULID — twenty-six characters, made from the current
    millisecond plus random bits. Two of them made on two machines at the same
    moment will not collide, and sorting a list of them puts it in the order they
    were made, which makes a log of identifiers readable rather than arbitrary.

    Returns:
        The identifier as a plain string, ready to pass into a domain model.
    """
    return str(ULID())


def mint_seed() -> int:
    """Make one new seed: the number every likelihood on a map is worked out from.

    Minted here, at the edge, for the same reason an identifier is: it needs a
    source of randomness, and the rules layer reads none. A request that leaves
    the seed out gets one from here, and the generation's first event says which —
    so a run is reproducible from the moment it starts.

    **The browser never invents one.** It sends a seed only to reproduce a run it
    was handed, which is the one case where a seed means something to whoever is
    sending it; a number made up at the other end would be a number nobody
    computed sitting inside the reproducibility of the answer.

    Returns:
        A whole number, positive, and small enough that a browser reads it back
        unchanged.
    """
    return secrets.randbelow(BIGGEST_SEED) + 1
