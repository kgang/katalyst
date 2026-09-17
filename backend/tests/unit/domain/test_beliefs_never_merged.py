"""No function in the rules layer turns two owners' numbers into one.

The product's value is the gap between what the model thinks, what you think and
what a market is pricing. If the model says .61, a market says .48 and you say
.30, the average .46 is a number nobody holds, describing nobody's view, and it
deletes the two gaps that are the actual output: model minus market is the edge
you might trade, user minus model is the argument you are having with the tool.

So the rule is narrow and absolute: **no function under `domain/` takes beliefs
of two different owners and returns one number.** Showing them next to each other
is encouraged. Subtracting one from another for display happens outside this
layer and is labelled a difference, not a belief.

This is checked by reading our own source code rather than by good intentions.
Every file under `domain/` is parsed, every function in it is found, and its type
annotations are read. A function is an offence when it takes two or more
likelihoods, or one set of the three slots, **and** hands back a plain number, a
likelihood, or anything built out of one.

What the check cannot see, stated plainly. It reads written annotations only, and
it does not count `self` or `cls`. A method defined on the three-slot class
receives a set of slots through `self` without saying so, and counting that would
flag the class's own check — which pydantic requires to return `self` — as a
merge. The narrower check is the one that can run; the wider claim is carried by
the second half of this rule, which watches what an edit actually does to a map
and arrives with the code that applies one.
"""

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_ROOT = BACKEND_ROOT / "src" / "katalyst" / "domain"

ONE_LIKELIHOOD = re.compile(r"\bBelief\b")
"""Matches the name of one likelihood, and deliberately not the name of the three slots."""

THREE_SLOTS = re.compile(r"\bBeliefs\b")
"""Matches the name of the set of three slots — the model's, the user's and a market's."""

ONE_NUMBER = re.compile(r"\bfloat\b|\bBelief\b|\bBeliefs\b")
"""Matches a plain number, a likelihood, or anything built out of one."""

NOT_REALLY_PARAMETERS = ("self", "cls")
"""The two names that stand for the object itself rather than for something passed in."""


@dataclass(frozen=True)
class Merge:
    """One function that takes two owners' numbers and hands back one."""

    file: Path
    line: int
    function: str
    takes: str
    returns: str

    def describe(self) -> str:
        """Say, in one line, what was found and where."""
        return (
            f"{self.file}:{self.line} {self.function}({self.takes}) -> {self.returns} "
            "turns more than one owner's number into one"
        )


def _annotation_text(annotation: ast.expr | None) -> str:
    """Write a type annotation back out as the source a person would have typed."""
    return "" if annotation is None else ast.unparse(annotation)


def _parameter_annotations(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """List the written type of every real parameter, leaving out `self` and `cls`."""
    arguments = function.args
    every = [
        *arguments.posonlyargs,
        *arguments.args,
        *([arguments.vararg] if arguments.vararg else []),
        *arguments.kwonlyargs,
        *([arguments.kwarg] if arguments.kwarg else []),
    ]
    return [
        _annotation_text(one.annotation)
        for one in every
        if one is not None and one.arg not in NOT_REALLY_PARAMETERS
    ]


def _functions_in(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield every function in a parsed file, including the ones inside classes."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def find_merges(root: Path) -> list[Merge]:
    """Read every Python file under a directory and list the functions that merge owners.

    The directory is an argument rather than a constant so that the checker can be
    pointed at a throwaway directory and shown to actually catch something.

    Args:
        root: The directory to read, including everything below it.

    Returns:
        One entry per offending function, in file and line order.
    """
    found: list[Merge] = []
    for module_file in sorted(root.rglob("*.py")):
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
        for function in _functions_in(tree):
            taken = _parameter_annotations(function)
            likelihoods = sum(1 for one in taken if ONE_LIKELIHOOD.search(one))
            slot_sets = sum(1 for one in taken if THREE_SLOTS.search(one))
            if likelihoods < 2 and slot_sets == 0:
                continue
            handed_back = _annotation_text(function.returns)
            if not ONE_NUMBER.search(handed_back):
                continue
            found.append(
                Merge(
                    file=module_file,
                    line=function.lineno,
                    function=function.name,
                    takes=", ".join(taken),
                    returns=handed_back,
                )
            )
    return found


def test_beliefs_never_merged() -> None:
    """No function in the rules layer derives one number from two owners' numbers."""
    offenders = find_merges(DOMAIN_ROOT)
    report = "\n".join(offender.describe() for offender in offenders)
    assert not offenders, (
        "The product's value is the gap between the model's number, the user's and a "
        "market's: average them and the gap, which is the whole signal, disappears. "
        "Show them side by side, and compute any difference outside this layer, "
        "labelled a difference:\n" + report
    )


def _write_pretend_rules(tmp_path: Path, body: str) -> Path:
    """Put a small pretend rules file in a throwaway directory."""
    written = tmp_path / "pretend_rules.py"
    written.write_text('"""A file written only to be checked."""\n\n' + body, encoding="utf-8")
    return written


def test_the_checker_catches_two_likelihoods_averaged(tmp_path: Path) -> None:
    """A test that passes because nothing is there yet would be worthless."""
    _write_pretend_rules(
        tmp_path,
        "def blend(mine: Belief, yours: Belief) -> float:\n    return (mine.p + yours.p) / 2\n",
    )

    found = find_merges(tmp_path)

    assert [one.function for one in found] == ["blend"]
    assert "blend" in found[0].describe()


def test_the_checker_catches_a_merge_hidden_in_a_structure(tmp_path: Path) -> None:
    """Handing back a tuple of numbers is handing back numbers."""
    _write_pretend_rules(
        tmp_path,
        "def spread(three: Beliefs) -> tuple[float, float]:\n    return (0.0, 0.0)\n",
    )

    assert [one.function for one in find_merges(tmp_path)] == ["spread"]


def test_the_checker_leaves_honest_functions_alone(tmp_path: Path) -> None:
    """Reading two owners' numbers and saying something about them in words is fine."""
    _write_pretend_rules(
        tmp_path,
        "def describe(mine: Belief, yours: Belief) -> str:\n    return 'they differ'\n"
        "def widen(one: Belief) -> Belief:\n    return one\n"
        "def count(three: Beliefs) -> int:\n    return 3\n",
    )

    assert find_merges(tmp_path) == []


def test_the_checker_is_pointed_at_the_real_rules_layer() -> None:
    """A checker pointed at an empty directory passes for the wrong reason.

    So this names the directory it read and confirms the file that defines a
    likelihood is in it.
    """
    read = sorted(one.name for one in DOMAIN_ROOT.rglob("*.py"))

    assert "belief.py" in read
    assert len(read) >= 8
