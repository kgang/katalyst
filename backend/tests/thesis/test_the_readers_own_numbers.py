"""Nothing in this layer makes up a stop, and that is read off our own source.

The roadmap promised a *derived* stop-loss for a year. It was withdrawn, because
on this product's own worked example the derivation names the claim the trade
rests on — *get out if the thing you are betting on stops being true*. **The stop,
the target and the horizon are the reader's own prices**, and what the map
computes beside them is what takes you out and what to watch.

A promise like that decays into a convention unless something checks it, so this
file parses our own source and checks three things a later edit could quietly
break:

* **A position is built in exactly one place.** A second construction site is a
  second place the rule has to be remembered, and it would be remembered until it
  was not.
* **That one place takes the three numbers and never defaults them.** A default
  stop is a stop nobody typed.
* **Nothing in the layer computes one.** No function assigns to a name called
  `stop`, `target` or `horizon`. Reading `position.stop` is fine and is the point;
  working one out is what is forbidden.

What this check cannot see, stated plainly. It reads written source, so something
that reached the builder through a variable, or unpacked a dictionary into it,
would pass. The narrow check is the one that can run.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
THE_TRADE_LAYER = BACKEND_ROOT / "src" / "katalyst" / "thesis"
WHERE_A_POSITION_IS_BUILT = THE_TRADE_LAYER / "position.py"

THE_ONE_BUILDER = "position_on"
"""The only function allowed to build a position."""

A_POSITION = "Position"
"""What a position is called, which is what a second construction site would name."""

THE_READERS_OWN = ("stop", "target", "horizon")
"""The three numbers nobody but the reader may set."""


@dataclass(frozen=True)
class Derived:
    """One place in our own source that sets one of the reader's own numbers."""

    file: Path
    line: int
    name: str
    inside: str

    def describe(self) -> str:
        """Say, in one line, what was found and where."""
        return f"{self.file}:{self.line} works out a '{self.name}' inside {self.inside}"


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


def find_stops_worked_out(root: Path) -> list[Derived]:
    """Read every Python file under a directory and list the reader's numbers somebody set.

    A *set* means an assignment to a plain name called `stop`, `target` or
    `horizon`. Reading one off a position is not an assignment and is not reported;
    that is what those fields are for.

    The directory is an argument rather than a constant so that the checker can be
    pointed at a throwaway directory and shown to actually catch something.

    Args:
        root: The directory to read, including everything below it.

    Returns:
        One entry per place a reader's number is worked out, in file and line
        order.
    """
    found: list[Derived] = []
    for module_file in sorted(root.rglob("*.py")):
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
        inside = _enclosing_functions(tree)
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                # A bare `stop: float` declares the field a reader fills in; only a
                # declaration that also *sets* a value is somebody working one out.
                targets = [node.target]
            for one in targets:
                if isinstance(one, ast.Name) and one.id in THE_READERS_OWN:
                    found.append(
                        Derived(
                            file=module_file,
                            line=node.lineno,
                            name=one.id,
                            inside=inside.get(node.lineno, "the file itself"),
                        )
                    )
    return found


def find_positions_built_elsewhere(root: Path) -> list[Derived]:
    """List the places a position is built that are not the one function allowed to build one."""
    found: list[Derived] = []
    for module_file in sorted(root.rglob("*.py")):
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
        inside = _enclosing_functions(tree)
        for node in ast.walk(tree):
            called = node.func if isinstance(node, ast.Call) else None
            if not isinstance(called, ast.Name) or called.id != A_POSITION:
                continue
            within = inside.get(node.lineno, "the file itself")
            if within == THE_ONE_BUILDER:
                continue
            found.append(
                Derived(file=module_file, line=node.lineno, name=A_POSITION, inside=within)
            )
    return found


def test_a_stop_is_never_derived() -> None:
    """Nothing under the trade layer works out a stop, a target or a horizon."""
    offenders = find_stops_worked_out(THE_TRADE_LAYER)
    report = "\n".join(one.describe() for one in offenders)

    assert not offenders, (
        "The stop, the target and the horizon are prices the reader owns. Nothing in "
        "this layer may work one out:\n" + report
    )


def test_a_position_is_built_in_exactly_one_place() -> None:
    """One construction site, so there is one place the rule has to hold."""
    offenders = find_positions_built_elsewhere(THE_TRADE_LAYER)
    report = "\n".join(one.describe() for one in offenders)

    assert not offenders, (
        "A position's instrument and side come from the map, and its three prices from "
        "the reader. A second place that builds one is a second place that can get either "
        "wrong:\n" + report
    )


def test_the_one_builder_takes_the_reader_s_three_numbers_and_defaults_none_of_them() -> None:
    """A default stop is a stop nobody typed, and it would be the easiest one to add."""
    tree = ast.parse(WHERE_A_POSITION_IS_BUILT.read_text(encoding="utf-8"))
    builder = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == THE_ONE_BUILDER
    )
    named = [one.arg for one in builder.args.kwonlyargs]
    defaults = dict(zip(named, builder.args.kw_defaults, strict=True))

    for one in THE_READERS_OWN:
        assert one in named, f"'{one}' is keyword-only, so every call site spells it"
        assert defaults[one] is None, f"'{one}' has no default at all"


def _write_pretend_source(tmp_path: Path, body: str) -> Path:
    """Put a small pretend source file in a throwaway directory."""
    written = tmp_path / "pretend_thesis.py"
    written.write_text('"""A file written only to be checked."""\n\n' + body, encoding="utf-8")
    return written


def test_the_checker_catches_a_stop_somebody_worked_out(tmp_path: Path) -> None:
    """A test that passes because nothing is there yet would be worthless."""
    _write_pretend_source(
        tmp_path,
        "def suggest(world):\n    stop = world.entry * 0.97\n    return stop\n",
    )

    found = find_stops_worked_out(tmp_path)

    assert [(one.name, one.inside) for one in found] == [("stop", "suggest")]
    assert "works out a 'stop'" in found[0].describe()


def test_the_checker_catches_an_annotated_or_adjusted_one_too(tmp_path: Path) -> None:
    """Two more ways to set a name, both of which a narrower check would walk past."""
    _write_pretend_source(
        tmp_path,
        "def suggest(world):\n    target: float = 1.0\n    horizon = 0\n    horizon += 1\n",
    )

    found = find_stops_worked_out(tmp_path)

    assert sorted(one.name for one in found) == ["horizon", "horizon", "target"]


def test_the_checker_leaves_a_field_declaration_alone(tmp_path: Path) -> None:
    """`stop: float` on the shape the reader fills in is the field, not a worked-out number."""
    _write_pretend_source(tmp_path, "class Position:\n    stop: float\n    target: float\n")

    assert find_stops_worked_out(tmp_path) == []


def test_the_checker_leaves_a_position_s_own_fields_alone(tmp_path: Path) -> None:
    """Reading the reader's numbers is the point; it is working one out that is forbidden."""
    _write_pretend_source(
        tmp_path,
        "def size(position):\n    return position.risk_budget / (position.entry - position.stop)\n",
    )

    assert find_stops_worked_out(tmp_path) == []


def test_the_checker_catches_a_position_built_somewhere_else(tmp_path: Path) -> None:
    """A second construction site is found wherever it hides."""
    _write_pretend_source(
        tmp_path,
        "def card(ending):\n    return Position(ending=ending, stop=1.0)\n",
    )

    found = find_positions_built_elsewhere(tmp_path)

    assert [one.inside for one in found] == ["card"]


def test_the_checker_leaves_the_one_builder_alone(tmp_path: Path) -> None:
    """The function allowed to build a position is not reported for building one."""
    _write_pretend_source(
        tmp_path,
        "def position_on(ending):\n    return Position(ending=ending)\n",
    )

    assert find_positions_built_elsewhere(tmp_path) == []


def test_the_checker_is_pointed_at_our_own_source() -> None:
    """A checker pointed at an empty directory passes for the wrong reason."""
    read = sorted(one.name for one in THE_TRADE_LAYER.rglob("*.py"))

    assert "position.py" in read
    assert "draws.py" in read
    assert len(read) >= 6
