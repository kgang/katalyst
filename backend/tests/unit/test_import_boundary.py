"""The rules layer may not import anything that reaches outside itself.

Katalyst's one shaping rule is "the model proposes; our code decides". A
language model hands us proposals; code we wrote and tested decides whether a
map is valid. That rule only means something if the deciding code cannot quietly
start asking a model, calling a service, or reaching back into the routes. This
file makes the rule mechanical.

How it works: every file under `src/katalyst/domain` is parsed, its import lines
are read, and each one is resolved to the full dotted name it brings in
(including the shortened forms, so `from katalyst import engine` is caught as
surely as `import katalyst.engine`, and so is the relative form `from ..api
import main`). If any of them lands inside a forbidden package, the test fails
and names the file and the line.

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
DOMAIN_ROOT = BACKEND_ROOT / "src" / "katalyst" / "domain"
DOMAIN_PACKAGE = "katalyst.domain"

FORBIDDEN_PACKAGES: tuple[str, ...] = (
    # The other layers. The rules must not depend on the pipeline that feeds
    # them, the routes that expose them, or the fetching of outside facts.
    "katalyst.engine",
    "katalyst.api",
    "katalyst.grounding",
    # Talking to a language model.
    "anthropic",
    # Talking to anything at all over the network.
    "httpx",
    "requests",
    # Serving anything over the network.
    "fastapi",
    "uvicorn",
)


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
