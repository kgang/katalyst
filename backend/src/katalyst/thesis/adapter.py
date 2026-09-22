"""The two places the map's own shapes are turned into the ones the trade layer takes.

Everything above `draws.py` is pure arithmetic over a sample of worlds and a
handful of stated moves. Neither of those shapes is the one the rest of the
program holds, so the translation happens here, in one file, and nowhere else.

**Two translations, and they are different in kind.**

*The sample.* The engine draws worlds forward and hands back a window, the claims
in a fixed order, the day each claim came on and went off in each world, a weight
per world and how many equally-weighted worlds those weights are worth. Field for
field that is what `Draws` holds, so `draws_of` **renames and never computes**:
every number goes across untouched and the only thing added is the name of the
sampler it came from.

*The move.* A map states how far an instrument moves as a **share of its price** —
`0.03` means three per cent — with the side carried separately, so the number is
never negative. A price path takes a **level gap in price units**, signed, because
two claims moving one instrument then need only their own chances and no joint
between them. `moves_on` converts one to the other against the price the reader
entered at. That is a conversion rather than an identity, and it is said out loud
here rather than left for a reader to discover: a share compounds where this
arithmetic adds, and above a move of about a fifth of the price the difference
puts free drift back in the reader's favour.

**Only the ending's own claim moves its own instrument.** A map says how far one
instrument moves if *this* claim comes true, and says nothing about what any other
claim does to it. A claim with no stated move moves the price by nothing, which is
exactly what the map says about it.

What this file must never do
----------------------------
- Never compute a number while renaming one. `draws_of` copies; anything that
  needed arithmetic would belong to whichever module owns that arithmetic.
- Never invent a move for a claim the map states none for. Silence in a map is a
  move of nothing, not a move worth guessing.
- Never hand a contract ending a price path. A probability does not follow one,
  and `position.py` refuses that question by name.
"""

from katalyst.domain import ContractPayoff, Proposition, Sample
from katalyst.thesis.draws import Draws
from katalyst.thesis.paths import ClaimMove

A_MOVE_IS_A_SHARE_OF_THE_PRICE = (
    "The map states this move as a share of the instrument's price, and a price path takes a "
    "level gap in price units, so the share was multiplied by the price you entered at. A "
    "share compounds where this arithmetic adds, and above a move of about a fifth of the "
    "price the two part company in your favour."
)
"""What the conversion from a stated share to a level gap costs, in plain words.

Carried as data rather than written into a screen, so that every surface showing a
converted move shows the same sentence and none of them can show the number
without it.
"""


def draws_of(sample: Sample) -> Draws:
    """Read the engine's weighted forward sample as the trade layer's set of drawn worlds.

    **A rename, not a computation.** The window, the claims, the two day tables,
    the weights and the effective count all cross untouched; the one thing added is
    the name of the sampler, which no first-touch number may be reported without.

    The engine's own two markers — *it never came on* and *it came on and has not
    stopped* — are the two this layer declares, so nothing is remapped either.

    Args:
        sample: What the engine drew: worlds carried forward under the full time
            model, each weighted by how well it matches what was reported.

    Returns:
        The same worlds, as the one shape the trade layer reads.

    Raises:
        ValueError: If the sample does not hang together as a set of draws — a
            window shorter than a day, a day outside it, a claim that went off
            without coming on, or an effective count the weights do not imply. That
            is a broken promise between our own pieces of code rather than anything
            a reader did, so it is said out loud here.
    """
    return Draws(
        day_zero=sample.day_zero,
        days=sample.days,
        claims=sample.claims,
        on_day=sample.on_day,
        off_day=sample.off_day,
        weight=sample.weight,
        effective=sample.effective,
        sample="weighted_forward_sample",
    )


def moves_on(ending: Proposition, *, entry: float) -> tuple[ClaimMove, ...]:
    """What the map says this ending's own claim does to the price of what it names.

    One move at most, because a map states how far an instrument moves if **this**
    claim comes true and says nothing about what any other claim does to it. A claim
    with no stated move moves the price by nothing, and that is the map's own
    statement rather than a gap in it.

    **The level gap carries the sign the payoff carries as a side.** The stated
    share is never negative; a payoff that would be **short** is one whose
    instrument stands *lower* in a world where the claim is true, so the gap is
    negative there and positive where it would be long.

    **The market's chance is left for the path to read off the drawn worlds.** That
    is the neutral assumption — the market believes what the model believes, except
    where a venue says otherwise — and it is the only reading under which the path
    carries no drift at all. Nothing here hands one in, so nothing here can hand in
    a different one by accident.

    Args:
        ending: The claim being traded, whose payoff names the instrument and the
            move.
        entry: The price the reader entered at, in the instrument's own units,
            which the stated share is converted against.

    Returns:
        One move where the ending names an instrument; nothing at all where it names
        a contract, or names no trade, because neither gets a price path.
    """
    payoff = ending.payoff
    if payoff is None or isinstance(payoff, ContractPayoff):
        return ()
    toward = 1.0 if payoff.direction == "long" else -1.0
    return (
        ClaimMove(
            claim=ending.id,
            move=toward * payoff.move * entry,
            market_chance=None,
            market_chance_from="sample_share",
        ),
    )
