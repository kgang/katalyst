"""Which layer may import which, checked by reading our own import lines.

Katalyst's one shaping rule is "the model proposes; our code decides". A
language model hands us proposals; code we wrote and tested decides whether a
map is valid. That rule only means something if the deciding code cannot quietly
start asking a model, calling a service, or reaching back into the routes. This
file makes the rule mechanical.

How it works: every file under a named directory is parsed, its import lines are
read, and each one is resolved to the full dotted name it brings in (including
the shortened forms, so `from katalyst import engine` is caught as surely as
`import katalyst.engine`, and so is the relative form `from ..api import main`).
If any of them lands inside a forbidden package, the test fails and names the
file and the line.

Three directories are checked, and the order they are allowed to depend in runs
one way only.

* **The rules layer** (`domain/`) may import nothing that reaches outside itself:
  not the pipeline that feeds it, not the routes that expose it, not the layer
  that fetches prices, not the layer that turns a map into a trade, and nothing
  that talks over a network. It is the part whose correctness we claim, and it is
  property-tested against maps nobody wrote by hand precisely because it depends
  on nothing.
* **The layer that fetches prices** (`grounding/`) may import the rules layer,
  because a price becomes a likelihood on a claim. It may not import the routes,
  the model-facing pipeline, or the trade layer above it.
* **The layer that turns a map into a trade** (`thesis/`) may import both of
  those, because an edge is a claim's number set against a venue's price. It may
  not import the routes.

The rules layer is no longer close to empty — propositions, links, beliefs,
validity, propagation, branches, worlds and diffs all live in it — so this check
walks real files and has real work to do. The sentence here used to say the
opposite, which was true when it was written in stack 01 and stopped being true
in 02 (2026-09-20).
"""

import ast
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = BACKEND_ROOT / "src" / "katalyst"
DOMAIN_ROOT = SOURCE_ROOT / "domain"
DOMAIN_PACKAGE = "katalyst.domain"

TALKING_TO_A_MODEL: tuple[str, ...] = ("anthropic",)
"""The one library that talks to a language model."""

TALKING_OVER_A_NETWORK: tuple[str, ...] = ("httpx", "requests", "urllib.request")
"""Libraries that open a connection to somewhere else."""

THE_ONE_WAY_OUT = "urllib.request"
"""The one of those the price-fetching layer is allowed, in one named function."""

SERVING_OVER_A_NETWORK: tuple[str, ...] = ("fastapi", "uvicorn")
"""Libraries that answer requests from somewhere else."""

FORBIDDEN_PACKAGES: tuple[str, ...] = (
    # The other layers. The rules must not depend on the pipeline that feeds
    # them, the routes that expose them, the fetching of outside facts, or the
    # layer that turns a map into a trade.
    "katalyst.engine",
    "katalyst.api",
    "katalyst.grounding",
    "katalyst.thesis",
    *TALKING_TO_A_MODEL,
    *TALKING_OVER_A_NETWORK,
    *SERVING_OVER_A_NETWORK,
)

FORBIDDEN_TO_GROUNDING: tuple[str, ...] = (
    # The layer that fetches prices sits below the one that turns a map into a
    # trade, and beside the pipeline that talks to a model rather than under it.
    "katalyst.api",
    "katalyst.engine",
    "katalyst.thesis",
    *TALKING_TO_A_MODEL,
    *SERVING_OVER_A_NETWORK,
    # And the network libraries this layer does **not** use. Its own docstring
    # says the one way it opens a connection is the standard library's, in one
    # named function; a client from one of these could appear tomorrow and the
    # rule would say nothing, because one of them is already in the environment
    # for the sake of the model boundary.
    *(one for one in TALKING_OVER_A_NETWORK if one != THE_ONE_WAY_OUT),
)
"""What the price-fetching layer may not import.

Deliberately **not** on this list: the rules layer, because a price becomes a
likelihood on a claim; and the standard library's way of opening a connection,
because this is the one layer allowed to reach a venue — and it does so in one
named function that nothing in the demo, the tests or the build ever calls.
"""

FORBIDDEN_TO_THESIS: tuple[str, ...] = (
    # The layer that turns a map into a trade reads worlds and quotes and builds
    # an answer beside them. It serves nothing, fetches nothing, and asks nothing.
    "katalyst.api",
    "katalyst.engine",
    *TALKING_TO_A_MODEL,
    *TALKING_OVER_A_NETWORK,
    *SERVING_OVER_A_NETWORK,
)
"""What the trade layer may not import.

Deliberately **not** on this list: the rules layer and the price-fetching layer,
which are exactly the two things an edge is made of — a claim's own number, and a
venue's price for it.
"""


@dataclass(frozen=True)
class ForbiddenImport:
    """One import that the rules layer is not allowed to have."""

    file: Path
    line: int
    imported: str
    forbidden_package: str

    def describe(self) -> str:
        """Say, in one line, what was found and where."""
        return (
            f"{self.file}:{self.line} imports {self.imported}, "
            f"which lives in the forbidden package {self.forbidden_package}"
        )


def _package_of(module_file: Path, root: Path, root_package: str) -> str:
    """Name the package a file sits in, so relative imports can be resolved.

    A file at `<root>/a/b/thing.py` sits in `<root_package>.a.b`. A file at
    `<root>/a/b/__init__.py` *is* the package `<root_package>.a.b`, and a
    relative import written inside it counts from there too, so the answer is
    the same either way.
    """
    parts = module_file.relative_to(root).parts[:-1]
    return ".".join([root_package, *parts])


def _imported_names(node: ast.AST, package: str) -> Iterator[tuple[str, int]]:
    """Yield every dotted name an import statement brings in, with its line.

    A `from X import y` line is reported twice, as `X` and as `X.y`, because
    either half may be the forbidden one: `from katalyst import engine` hides
    the forbidden name in the second half.
    """
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name, alias.lineno
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0:
            base = node.module or ""
        else:
            # A leading dot means "this package"; each further dot climbs one
            # level up from it.
            parts = package.split(".")
            climbed = parts[: len(parts) - (node.level - 1)]
            base = ".".join([*climbed, node.module] if node.module else climbed)
        if base:
            yield base, node.lineno
            for alias in node.names:
                yield f"{base}.{alias.name}", node.lineno


def _forbidden_package_of(name: str, forbidden: Sequence[str]) -> str | None:
    """Return the forbidden package a dotted name falls inside, or nothing."""
    for package in forbidden:
        if name == package or name.startswith(f"{package}."):
            return package
    return None


def find_forbidden_imports(
    root: Path,
    root_package: str,
    forbidden: Sequence[str] = FORBIDDEN_PACKAGES,
) -> list[ForbiddenImport]:
    """Read every Python file under a directory and list its forbidden imports.

    The directory is an argument rather than a constant so that the checker can
    be pointed at a throwaway directory and shown to actually catch something.

    Args:
        root: The directory to read, including everything below it.
        root_package: The dotted name of that directory as a package, used to
            work out what a relative import points at.
        forbidden: The packages that may not be imported.

    Returns:
        One entry per offending import line, in file and line order.
    """
    found: list[ForbiddenImport] = []
    already_reported: set[tuple[Path, int]] = set()
    for module_file in sorted(root.rglob("*.py")):
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
        package = _package_of(module_file, root, root_package)
        for node in ast.walk(tree):
            for name, line in _imported_names(node, package):
                forbidden_package = _forbidden_package_of(name, forbidden)
                if forbidden_package is None or (module_file, line) in already_reported:
                    continue
                already_reported.add((module_file, line))
                found.append(
                    ForbiddenImport(
                        file=module_file,
                        line=line,
                        imported=name,
                        forbidden_package=forbidden_package,
                    )
                )
    return found


def test_domain_imports_nothing_impure() -> None:
    """The rules layer imports nothing that could reach outside itself."""
    offenders = find_forbidden_imports(DOMAIN_ROOT, DOMAIN_PACKAGE)
    report = "\n".join(offender.describe() for offender in offenders)
    assert not offenders, (
        "The rules layer decides whether a map is valid, so it must not depend on "
        "the pipeline that feeds it, the routes that expose it, or anything that "
        "talks over a network. Move this code into katalyst.engine instead:\n" + report
    )


def test_grounding_imports_nothing_above_it() -> None:
    """The layer that fetches prices depends on the rules layer, and on nothing above it."""
    offenders = find_forbidden_imports(
        SOURCE_ROOT / "grounding", "katalyst.grounding", FORBIDDEN_TO_GROUNDING
    )
    report = "\n".join(offender.describe() for offender in offenders)
    assert not offenders, (
        "Fetching a price is the bottom of the two layers that turn a map into a "
        "trade: it may read the rules layer, because a price becomes a likelihood on "
        "a claim, and nothing above it:\n" + report
    )


def test_thesis_imports_nothing_that_serves_or_fetches() -> None:
    """The layer that turns a map into a trade reads worlds and quotes, and asks nobody."""
    offenders = find_forbidden_imports(
        SOURCE_ROOT / "thesis", "katalyst.thesis", FORBIDDEN_TO_THESIS
    )
    report = "\n".join(offender.describe() for offender in offenders)
    assert not offenders, (
        "An edge is a claim's own number set against a venue's price, so this layer "
        "reads the rules layer and the price-fetching layer and nothing else. Fetching "
        "belongs in katalyst.grounding and serving in katalyst.api:\n" + report
    )


def test_the_price_layer_may_not_reach_for_another_network_library() -> None:
    """A checker that allowed every network library would pass on a layer that used one.

    So the rule is shown catching what it claims to catch: the standard library's
    way out is allowed in this layer and the two client libraries are not — and one
    of them is already installed, for the model boundary, so it is a real risk and
    not a hypothetical one.
    """
    allowed = tmp_written(THE_ONE_WAY_OUT)
    forbidden = [tmp_written(one) for one in TALKING_OVER_A_NETWORK if one != THE_ONE_WAY_OUT]

    assert allowed == []
    assert forbidden and all(found for found in forbidden), (
        "every network library but the standard library's must be refused in this layer"
    )


def tmp_written(imported: str) -> list[ForbiddenImport]:
    """What the checker says about a price-layer file importing one named library."""
    import tempfile

    with tempfile.TemporaryDirectory() as where:
        file = Path(where) / "pretend_grounding.py"
        file.write_text(
            f'"""A file written only to be checked."""\n\nimport {imported}\n', encoding="utf-8"
        )
        return find_forbidden_imports(Path(where), "katalyst.grounding", FORBIDDEN_TO_GROUNDING)


def test_every_layer_that_is_checked_really_has_files_in_it() -> None:
    """A boundary test pointed at an empty directory passes for the wrong reason."""
    for directory in (DOMAIN_ROOT, SOURCE_ROOT / "grounding", SOURCE_ROOT / "thesis"):
        written = [one.name for one in directory.rglob("*.py") if one.name != "__init__.py"]
        assert written, f"{directory} has nothing in it for the boundary check to read"


@pytest.mark.parametrize(
    ("import_line", "expected_package"),
    [
        ("import anthropic", "anthropic"),
        ("import httpx", "httpx"),
        ("from fastapi import APIRouter", "fastapi"),
        ("from katalyst.api.main import app", "katalyst.api"),
        ("from katalyst import engine", "katalyst.engine"),
        ("from ..grounding import prices", "katalyst.grounding"),
    ],
)
def test_the_checker_catches_a_forbidden_import(
    tmp_path: Path, import_line: str, expected_package: str
) -> None:
    """A test that passes because nothing is there yet would be worthless.

    So we write a file that breaks the rule into a throwaway directory and
    confirm the checker finds it, names it, and points at the right line.
    """
    offending_file = tmp_path / "pretend_rules.py"
    offending_file.write_text(
        '"""A file written only to be caught."""\n\nimport math\n' + import_line + "\n",
        encoding="utf-8",
    )

    found = find_forbidden_imports(tmp_path, DOMAIN_PACKAGE)

    assert [offender.forbidden_package for offender in found] == [expected_package]
    assert found[0].file == offending_file
    assert found[0].line == 4
    assert str(offending_file) in found[0].describe()


def test_the_checker_leaves_allowed_imports_alone(tmp_path: Path) -> None:
    """Ordinary imports the rules layer is meant to use raise no complaint."""
    allowed = tmp_path / "pretend_rules.py"
    allowed.write_text(
        '"""A file that plays by the rules."""\n\n'
        "import math\n"
        "from dataclasses import dataclass\n"
        "import networkx\n"
        "from katalyst.domain import graph\n"
        "from . import graph as sibling\n",
        encoding="utf-8",
    )

    assert find_forbidden_imports(tmp_path, DOMAIN_PACKAGE) == []
