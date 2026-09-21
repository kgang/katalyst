# What takes you out — the claims over-represented where the stop went first, and the ones worth watching

## Purpose

The brief's most distinctive question is *what events could lead to a stop-loss?* This chapter answers it by arithmetic, and answers a second, smaller question beside it.

* **What takes you out** — of the worlds where the reader's stop was touched before their target, which claims had already happened? Computed, ranked, with an interval and a count.
* **What to watch** — which single adverse turn would damage this ending most, *and* resolves before it, *and* can be seen by anybody? A watchlist, never a stop.

The first is a list the map itself cannot give: not the causes of the ending, but the claims that keep company with losing.

---

## Data model

Two modules in `backend/src/katalyst/thesis/`, and one change to an existing function.

**`lift.py` — a row per claim**, carrying the claim, its **lift**, the interval, the number of drawn worlds behind it, and the typical number of days between the claim happening and the stop being touched.

**Lift is one division.** Among the worlds where the stop was touched first, how often had this claim **already come on before the stop was touched**? Divide by how often it came on across all the drawn worlds. Three means three times as often; one means it tells you nothing; below one means it kept company with the trade working.

*Before the stop* is load-bearing: a claim that happened afterwards cannot have contributed, counting it inflates the rail in the flattering direction, and it is what keeps a row's "days before the stop" from coming out negative. **Both shares are weighted** by the drawn worlds' own weights, so a weighted sampler changes nothing here.

The interval is a **Wilson interval** — the standard interval for a share, which stays sensible when counts are small — **on the numerator share only**, that is on how often the claim came on first among the stop-first worlds; the denominator is taken from all draws. **No coverage is claimed for the ratio**, because a ratio of two shares over overlapping sets is not a share. A row's interval says how firmly the numerator is pinned down, and nothing more.

Two rules keep the rail honest. **No row below two hundred effective drawn worlds** — *effective* meaning how many equally-weighted worlds the weighted sample is worth, which the engine's own measurement puts at 96.7% of the worlds drawn on average and 41.8% at worst. It is a **chosen floor, not a measured one**, carried over from the finance analysis because some floor is needed; what would replace it with a measurement is the draw count at which the top rows stop changing order between seeds. And **a claim an edit holds true has lift one by construction**, so it is dropped rather than printed.

Lift reads the day each claim came on. Those days are the engine's **weighted forward sample** — worlds drawn forward carrying event days, each weighted by how well it matches what was observed — whose days sit within `.0064` of the exact answer at worst, with a median day moving by at most two and a half days. Record 0019 carries the table, the script and the caveats.

**`watch.py` — the watchlist.** It takes the sweep's rows, keeps the adverse direction for the side the reader is on, and applies the two filters INV-14 has always asked for: the claim **resolves before** the ending it is watched for, and it is **publicly observable** — its resolution names a source anybody can go and read. What survives is the watchlist; what is adverse but resolves too late, or cannot be seen, is listed under **unhedgeable** with the reason, and never used as a stop.

**The sweep gains a second direction.** `sensitivity()` in `backend/src/katalyst/domain/diff.py` flips each claim one way only, chosen by which side of one half the claim sits on, so the reader's side is never consulted; record 0019's measured section has the numbers. It therefore flips each claim **both** ways and returns both rows, and whoever reads them picks the adverse one — which direction hurts depends on the trade, and the sweep has no idea what the trade is. About fifteen lines inside the existing function, landing after the engine stack has finished rewriting that file.

---

## Behaviour

### B1 — What takes you out, on the Hormuz map

The reader is short oil through an ending the map offers, with a stop above their entry. The rail lists the claims that had already happened in the worlds where that stop went first: the claim, its lift with an interval, the number of drawn worlds behind it, and the typical days between the claim happening and the stop being touched. Rows are ordered by lift, and a row whose interval leaves the claim indistinguishable from telling you nothing is not shown.

### B2 — What to watch, on the same map

The contract ending resolves at the end of October, and exactly one claim resolves strictly before it — the oil-price step the thesis rests on, a fortnight earlier — and it is publicly observable, because its resolution names published settlement prices. So the watchlist has one row and the card says so; everything else adverse resolves on the same day or later and is listed as **unhedgeable** with its date. A reader who learns that nothing else on this map can warn them in time has learned something true about the trade.

### B3 — A claim the reader has supposed

They suppose the strait opens, then ask what takes them out. The supposed claim is true in every drawn world, so its lift is exactly one and it never reaches the rail. The rail is about what varies.

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. This chapter owns `INV-thesis.10`–`INV-thesis.12`, and refines the product invariant INV-14, which this part owns.

**INV-thesis.10 — A claim held true tells you nothing, and is not shown** *(refines INV-14)*. For every set of draws from `draws()` and every claim held true in all of them: its lift is exactly one and it does not appear in the returned rows. **Test:** `test_a_claim_held_true_by_an_edit_has_lift_one`.

**INV-thesis.11 — An unrelated claim's numerator interval covers its base share.** For every set of draws from `draws()` in which a claim is generated independently of the path: the Wilson interval on the numerator share contains that claim's base share, at the interval's own stated coverage, over a stated number of repetitions with a fixed seed. A test against **synthetic draws**, not against the engine, so it tests the arithmetic rather than the map — and it claims nothing about the ratio. **Test:** `test_an_unrelated_claim_reads_no_lift`.

**INV-thesis.12 — Every row says what it rests on** *(refines INV-14)*. For every set of draws from `draws()`: no returned row rests on fewer than two hundred effective drawn worlds, and every row carries its count and its interval. For every row on the watchlist: the claim's resolve-by date is strictly before the ending's, and its resolution names a source. Anything adverse failing either filter appears under *unhedgeable* with the reason, and nowhere else. **Tests:** `test_a_lift_row_says_how_many_draws_it_rests_on`, `test_the_watchlist_resolves_before_and_can_be_seen`.

---

## ANTI-PATTERNS

1. **Do not call the watchlist a stop.** Because a ranking of flips is a list of things to keep an eye on, and the one claim it reliably names on this product's own example is the claim the trade rests on. **Instead:** the reader types the stop; this says what to watch, and by when.

2. **Do not read lift as a cause.** Because it measures company, not mechanism: a claim can be over-represented in the worlds that stopped you out because it shares a cause with whatever did. **Instead:** say *over-represented*, and keep the map beside it for the mechanism.

3. **Do not count a claim that happened after the stop was touched.** Because it cannot have contributed, and counting it inflates every row in the direction that makes the rail look useful. **Instead:** the numerator is *came on before the stop*.

4. **Do not print a lift without its interval and its count, and do not claim coverage for the ratio.** Because a lift of four over six worlds and one over two thousand are different claims, and only one is a claim. **Instead:** both numbers on every row, the interval read as being about the numerator, and nothing returned below the floor.

5. **Do not sweep in one direction, and do not quietly drop an adverse claim that fails the filters.** Because which direction hurts depends on the reader's side, and *this would hurt and you cannot see it coming* is one of the most useful sentences the product can say. **Instead:** flip both ways and let the caller pick; list the rest as unhedgeable, with the reason and the date.

---

## Open questions

*Raised 2026-09-21.*

1. **How many drawn worlds does a stable rail need?** Two hundred is a chosen floor; the count that makes the top rows stable is still to be measured.
2. **Rank by lift, or by lift weighted by how often the claim happens at all?** A rare claim can carry a huge lift and almost no mass. Today: ranked by lift, with the count beside it.
3. **Pairs.** *"Hormuz opens **and** Iran is struck"* is the same division over a pair — the brief's own sentence — and needs more drawn worlds for the same interval width, so it ships only if the single-claim rail is finished.
