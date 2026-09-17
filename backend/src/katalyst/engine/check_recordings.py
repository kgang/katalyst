"""Read every committed recording and say what is wrong with it, or nothing at all.

What the build's `recordings` job runs. It needs no key and has none: a recording
is a file, and everything below is read off it.

**It passes on an empty folder**, so it is green from the commit that adds it and
bites the moment the first recording lands. That matters more than it sounds:
this check is the one mitigation for the worst thing a recording can do, which is
to go stale in silence. A cassette that drifts breaks a test; a recording that
drifts just shows a reviewer old wording, and nothing anywhere goes red. The
prompt's fingerprint is what turns that silence into a failing check.

The consequence, said plainly so nobody is surprised by it: **change a prompt and
this job goes red until the recordings are made again**, and only somebody with a
key can do that. It is the same bargain the recorded model answers already
struck, taken knowingly.
"""

import sys

from katalyst.engine.prompt import prompt_hash
from katalyst.engine.replay import RECORDINGS, every_recording, faults_in


def main() -> int:
    """Read every recording and report every fault, not the first.

    Returns:
        0 when every file is sound, or when there are none yet. 1 otherwise.
    """
    recordings = every_recording()
    if not recordings:
        print(f"No recordings in {RECORDINGS}. Nothing to check, and nothing wrong with that.")
        return 0

    shipping = prompt_hash()
    faults = [
        one
        for recording in recordings
        for one in faults_in(recording, current_prompt_hash=shipping)
    ]
    sentences = {one.hypothesis.strip() for one in recordings}
    if len(sentences) != len(recordings):
        faults.append(
            "Two recordings were made from the same sentence, so which one plays would "
            "depend on the order the files happen to be read in."
        )

    for recording in recordings:
        print(f"read {recording.example}: {len(recording.lines)} events")
    for fault in faults:
        print(f"  {fault}", file=sys.stderr)
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
