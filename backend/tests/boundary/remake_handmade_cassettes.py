"""Remake the four hand-shaped cassettes from the four recorded ones. Run by hand.

**Not a test, and never run by the build.** The file is deliberately not named
`test_*`, so `pytest` does not collect it and continuous integration never
touches it. It is run by whoever has just re-recorded, from `backend/`:

    uv run python tests/boundary/remake_handmade_cassettes.py

Why it exists
-------------
Four of the cases these boundary tests need are cases a live model will not
produce on request: a proposal that closes a loop, a claim with a blank test, a
citation the search never returned, and an arrow that cites only addresses it
never returned. Each is made by hand from a real recording — one recording, its
request untouched, one edit to the proposal in the final text block.

Doing that by hand took an afternoon the first time and most of another the
second. The edits themselves are four lines of intent; everything around them is
bookkeeping — finding the right recording, keeping the search results, fixing
the content length, writing the header comment that says what changed. So the
bookkeeping lives here and the intent stays readable below.

**It is not a recorder and it spends nothing.** It reads four files and writes
four files, all on disk, with no key and no network.

What each file becomes
----------------------
Every one carries a header comment naming the recording it came from and the one
edit made to it, so that `diff` between the two files is the whole of the change
and a reader never has to take this script's word for it.
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

CASSETTES = Path(__file__).resolve().parents[1] / "cassettes"
"""Where the recordings live. Beside the tests that play them back."""

NEVER_RETURNED = "https://example.test/a-page-the-search-never-returned"
"""An address no search will ever return, which is the whole of its job.

Deliberately on `example.test` — a name reserved for exactly this — so that
nobody can mistake it for a page somebody could go and read, and so that a
future reader cannot accidentally make it real.
"""


def read(name: str) -> dict[str, Any]:
    """Read one cassette as data.

    Args:
        name: The test's name, which is the file's name.

    Returns:
        The whole file, parsed.
    """
    loaded: dict[str, Any] = yaml.safe_load(
        (CASSETTES / f"{name}.yaml").read_text(encoding="utf-8")
    )
    return loaded


def proposal_of(interaction: dict[str, Any]) -> dict[str, Any]:
    """Take the proposal out of a recorded answer.

    The model's answer is the last text block of the response; everything before
    it is thinking and the search tool's own traffic.

    Args:
        interaction: One recorded request and its answer.

    Returns:
        The proposal, parsed, envelope and all.
    """
    body = json.loads(interaction["response"]["body"]["string"])
    text = [one for one in body["content"] if one["type"] == "text"][-1]
    parsed: dict[str, Any] = json.loads(text["text"])
    return parsed


def with_proposal(interaction: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Put an edited proposal back into a recorded answer, in place.

    The content length is rewritten with it. A recorded answer whose length
    header disagrees with its body is a recording that plays back wrongly in ways
    that are hard to see.

    Args:
        interaction: The recorded exchange to edit.
        proposal: The proposal to put in its answer.

    Returns:
        The same exchange, edited.
    """
    body = json.loads(interaction["response"]["body"]["string"])
    text = [one for one in body["content"] if one["type"] == "text"][-1]
    text["text"] = json.dumps(proposal, ensure_ascii=False)
    written = json.dumps(body, ensure_ascii=False)
    interaction["response"]["body"]["string"] = written
    headers = interaction["response"]["headers"]
    for key in list(headers):
        if key.lower() == "content-length":
            headers[key] = [str(len(written.encode("utf-8")))]
    return interaction


def copy_of(interaction: dict[str, Any]) -> dict[str, Any]:
    """Take a copy of one recorded exchange, so the original is never changed."""
    copied: dict[str, Any] = json.loads(json.dumps(interaction))
    return copied


def write(name: str, interaction: dict[str, Any], comment: str) -> None:
    """Write one hand-shaped cassette, with its header comment on top.

    Args:
        name: The test's name, which is the file's name.
        interaction: The recorded exchange, edited.
        comment: The header comment, already written as `#` lines.
    """
    document = yaml.safe_dump(
        {"interactions": [interaction], "version": 1}, sort_keys=False, width=100
    )
    (CASSETTES / f"{name}.yaml").write_text(comment + document, encoding="utf-8")


def main() -> int:
    """Remake all four, and say what was written.

    Returns:
        Nothing went wrong, always: every failure in here raises.
    """
    one_proposal = read("test_expand_returns_one_proposal_per_call")["interactions"][0]
    provenance = read("test_provenance_is_written_from_what_was_found")["interactions"][0]
    about_b = read("test_generation_receipt_records_cache_reads")["interactions"][1]

    # 1. A proposal that closes a loop. This test asks about B, so the request
    #    comes from the recording that asked about B; the arrow it reuses comes
    #    from the other. The only one of the four that needs two recordings.
    cycle = copy_of(about_b)
    arrow = dict(proposal_of(one_proposal)["proposal"]["link"])
    arrow.pop("half_life", None)
    arrow["shape"] = "step"
    with_proposal(
        cycle, {"proposal": {"kind": "link", "source": "B", "target": "H", "link": arrow}}
    )
    write(
        "test_expand_rejects_cycle",
        cycle,
        "# Shaped by hand from test_generation_receipt_records_cache_reads.yaml (its second\n"
        "# call, the one that asks about B) and test_expand_returns_one_proposal_per_call.yaml\n"
        "# (its arrow). The request is the first file's, untouched. The answer is an arrow\n"
        "# proposal drawn from B back to H, which closes H -> C -> B -> H. The search results,\n"
        "# the counters and the headers are the first file's. Diff them to see the whole of\n"
        "# the change. `make record-cassettes` leaves this one alone; it is remade by\n"
        "# tests/boundary/remake_handmade_cassettes.py.\n",
    )

    # 2. A claim nobody can settle: the same recorded answer, with its test blanked.
    blank = copy_of(one_proposal)
    proposal = proposal_of(one_proposal)
    proposal["proposal"]["resolution"]["criteria"] = ""
    with_proposal(blank, proposal)
    write(
        "test_expand_rejects_a_claim_with_no_resolution_criteria",
        blank,
        "# Shaped by hand from test_expand_returns_one_proposal_per_call.yaml.\n"
        "# One change: the `criteria` string inside the proposal's `resolution` is blanked,\n"
        "# so the claim says nothing about how it would be settled. Everything else — the\n"
        "# request, the search results, the counters, the headers — is that recording's,\n"
        "# untouched. Diff the two files to see the whole of the change.\n"
        "# `make record-cassettes` leaves this one alone; it is remade by\n"
        "# tests/boundary/remake_handmade_cassettes.py.\n",
    )

    # 3. A citation the search never returned, beside one it did.
    extra = copy_of(provenance)
    proposal = proposal_of(provenance)
    cited = list(proposal["proposal"]["link"].get("sources") or [])
    proposal["proposal"]["link"]["sources"] = [*cited, {"url": NEVER_RETURNED}]
    with_proposal(extra, proposal)
    write(
        "test_a_cited_url_the_search_never_returned_is_not_a_source",
        extra,
        "# Shaped by hand from test_provenance_is_written_from_what_was_found.yaml.\n"
        f"# One change: a second citation, {NEVER_RETURNED},\n"
        "# is added to the proposal's arrow. It appears nowhere in this recording's own\n"
        "# search results, so our code drops it and names it. The tool's results are left\n"
        "# exactly as they were recorded. Everything else — the request, the counters, the\n"
        "# headers — is that recording's, untouched. Diff the two files to see the whole of\n"
        "# the change. `make record-cassettes` leaves this one alone; it is remade by\n"
        "# tests/boundary/remake_handmade_cassettes.py.\n",
    )

    # 4. Every citation is one the search never returned.
    unbacked = copy_of(provenance)
    proposal = proposal_of(provenance)
    proposal["proposal"]["link"]["sources"] = [
        {"url": f"{NEVER_RETURNED}/{index}"} for index in (1, 2)
    ]
    with_proposal(unbacked, proposal)
    write(
        "test_expand_rejects_a_documented_arrow_that_cites_nothing",
        unbacked,
        "# Shaped by hand from test_provenance_is_written_from_what_was_found.yaml.\n"
        "# One change: every citation on the proposal's arrow is replaced with an address\n"
        "# this recording's own search results never held, so nothing it cites survives and\n"
        "# the arrow comes back saying it argued rather than that it documented. The tool's\n"
        "# results are left exactly as they were recorded. Everything else — the request,\n"
        "# the counters, the headers — is that recording's, untouched. Diff the two files to\n"
        "# see the whole of the change. `make record-cassettes` leaves this one alone; it is\n"
        "# remade by tests/boundary/remake_handmade_cassettes.py.\n",
    )

    for name in (
        "test_expand_rejects_cycle",
        "test_expand_rejects_a_claim_with_no_resolution_criteria",
        "test_a_cited_url_the_search_never_returned_is_not_a_source",
        "test_expand_rejects_a_documented_arrow_that_cites_nothing",
    ):
        size = len((CASSETTES / f"{name}.yaml").read_text(encoding="utf-8"))
        print(f"wrote {name}.yaml ({size:,} bytes)")
    print("\nNow run: uv run pytest tests/boundary -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
