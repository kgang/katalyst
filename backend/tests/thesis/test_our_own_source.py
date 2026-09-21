"""Nothing in this program can price the world on screen, and that is read off our own source.

The rule this file makes mechanical is the one decision record 0018 chose a
*shape* for rather than a check: an edge is read from the world with nothing fixed
by an edit, and the way that is guaranteed is that the one function which builds
an edge takes **two** worlds and both are required. A caller holding only the
branch world cannot write the mistake down — the type checker refuses it on every
path, including the ones no test walks.

Two things have to hold for that to be worth anything, and both are checked here
by parsing our own source rather than by good intentions:

* **`priced` really does take two required worlds.** A later edit giving the
  second one a default, or dropping it, would quietly turn a guarantee into a
  convention.
* **Nothing else builds an edge.** A second construction site — a helper, a route,
  a card builder assembling one field at a time — would be a second place the rule
  has to be remembered, and it would be remembered until it was not.

What this check cannot see, stated plainly. It reads written source, so a caller
that reached `priced` through a variable, or built an edge by unpacking a
dictionary into it, would pass. The narrower check is the one that can run; the
wider claim is carried by the type checker, which runs over both new packages in
the strict mode this repository holds its rules layer to.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
OUR_SOURCE = BACKEND_ROOT / "src" / "katalyst"
WHERE_AN_EDGE_IS_BUILT = OUR_SOURCE / "thesis" / "edge.py"

THE_ONE_BUILDER = "priced"
"""The only function allowed to build an edge."""

AN_EDGE = "Edge"
"""What an edge is called, which is what a second construction site would name."""

TWO_WORLDS = ("base", "shown")
"""The two worlds `priced` takes, in order. Both required, and the first is read."""


@dataclass(frozen=True)
class BuiltElsewhere:
    """One place an edge is built that is not the one function allowed to build one."""

    file: Path
    line: int
    inside: str

    def describe(self) -> str:
        """Say, in one line, what was found and where."""
        return f"{self.file}:{self.line} builds an {AN_EDGE} inside {self.inside}"


def _enclosing_functions(tree: ast.AST) -> dict[int, str]:
    """Map every line of a parsed file to the function it sits inside, innermost first."""
    inside: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            last = max(
                (getattr(one, "lineno", node.lineno) for one in ast.walk(node)), default=node.lineno
            )
            for line in range(node.lineno, last + 1):
                inside.setdefault(line, node.name)
    return inside


def find_edges_built_elsewhere(root: Path) -> list[BuiltElsewhere]:
    """Read every Python file under a directory and list the edges built outside `priced`.

    The directory is an argument rather than a constant so that the checker can be
    pointed at a throwaway directory and shown to actually catch something.

    Args:
        root: The directory to read, including everything below it.

    Returns:
        One entry per offending construction, in file and line order.
    """
    found: list[BuiltElsewhere] = []
    for module_file in sorted(root.rglob("*.py")):
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
        inside = _enclosing_functions(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = node.func
            named = called.id if isinstance(called, ast.Name) else None
            if named != AN_EDGE:
                continue
            within = inside.get(node.lineno, "the file itself, outside any function")
            if within == THE_ONE_BUILDER:
                continue
            found.append(BuiltElsewhere(file=module_file, line=node.lineno, inside=within))
    return found


def test_no_call_site_prices_a_branch_world() -> None:
    """An edge is built in exactly one place, so there is one place the rule has to hold."""
    offenders = find_edges_built_elsewhere(OUR_SOURCE)
    report = "\n".join(offender.describe() for offender in offenders)

    assert not offenders, (
        "An edge is read from the world with nothing fixed by an edit, and that is "
        f"guaranteed by {THE_ONE_BUILDER} taking two required worlds. A second place that "
        "builds one is a second place the rule can be got wrong:\n" + report
    )


def test_the_one_builder_takes_two_required_worlds() -> None:
    """`priced` takes the base world and the world on screen, both required, in that order.

    Giving the second a default, or dropping it, would turn a guarantee the type
    checker enforces into a convention a caller has to remember.
    """
    tree = ast.parse(WHERE_AN_EDGE_IS_BUILT.read_text(encoding="utf-8"))
    builder = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == THE_ONE_BUILDER
    )
    taken = [one.arg for one in builder.args.posonlyargs + builder.args.args]
    annotations = {
        one.arg: ast.unparse(one.annotation) if one.annotation else ""
        for one in builder.args.posonlyargs + builder.args.args
    }

    assert taken[:2] == list(TWO_WORLDS)
    assert [annotations[one] for one in TWO_WORLDS] == ["World", "World"]
    # A default on either of them would make one of the two optional. Defaults line
    # up with the *last* parameters, so two worlds first means no default can reach
    # them unless everything after them has one too.
    assert len(builder.args.defaults) <= len(taken) - len(TWO_WORLDS)


def _write_pretend_source(tmp_path: Path, body: str) -> Path:
    """Put a small pretend source file in a throwaway directory."""
    written = tmp_path / "pretend_thesis.py"
    written.write_text('"""A file written only to be checked."""\n\n' + body, encoding="utf-8")
    return written


def test_the_checker_catches_an_edge_built_somewhere_else(tmp_path: Path) -> None:
    """A test that passes because nothing is there yet would be worthless."""
    _write_pretend_source(
        tmp_path,
        "def card(shown):\n    return Edge(claim='a', model=shown.beliefs['a'])\n",
    )

    found = find_edges_built_elsewhere(tmp_path)

    assert [one.inside for one in found] == ["card"]
    assert "card" in found[0].describe()


def test_the_checker_leaves_the_one_builder_alone(tmp_path: Path) -> None:
    """The function that is allowed to build an edge is not reported for building one."""
    _write_pretend_source(
        tmp_path,
        "def priced(base, shown, claim, quote):\n    return Edge(claim=claim)\n"
        "def show(edge):\n    return str(edge)\n",
    )

    assert find_edges_built_elsewhere(tmp_path) == []


def test_the_checker_is_pointed_at_our_own_source() -> None:
    """A checker pointed at an empty directory passes for the wrong reason."""
    read = sorted(one.name for one in OUR_SOURCE.rglob("*.py"))

    assert "edge.py" in read
    assert "quote.py" in read
    assert len(read) >= 8
