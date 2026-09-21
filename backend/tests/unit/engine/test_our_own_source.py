"""Rules we keep by reading our own source, because good intentions rot.

Several of this pipeline's promises are about what the code *cannot* do, not
about what it does with a given input: a model can never name an identifier, no
call ever asks for a whole map, one function builds every arrow, one module names
the vendor library's types, and one rule chooses every route. A test that fed
inputs in could only ever show that those held today. These read the files
instead.

The same trick the rules layer already uses to prove that nothing in it merges
two owners' numbers into one.
"""

import ast
from pathlib import Path

from pydantic import BaseModel

from katalyst.engine import expand as the_pipeline
from katalyst.engine import proposal as the_shapes

ENGINE = Path(the_pipeline.__file__).parent

NEVER_A_FIELD = ("id", "provenance", "owner")
"""Three things a model may never fill in, whatever else changes."""

WORDS_ONLY_SOMEBODY_ELSE_EARNS = ("historical", "market_implied")
"""Where a number came from when a study of past cases or a live price gave it.

Stack 05's adapters write these. Nothing in this layer may, because nothing in
this layer has read a price or run an event study.
"""


def shapes_a_model_may_fill() -> list[type[BaseModel]]:
    """List every shape in the file that says what a model may answer with."""
    return [
        found
        for found in vars(the_shapes).values()
        if isinstance(found, type) and issubclass(found, BaseModel)
    ]


def test_the_model_never_names_an_identifier() -> None:
    """No shape a model fills has a slot for one, so no check has to watch for one.

    The same pass covers the other two things a model may not do: say where its
    numbers came from, and put somebody's name on one.
    """
    for shape in shapes_a_model_may_fill():
        for named in shape.model_fields:
            assert named not in NEVER_A_FIELD, f"{shape.__name__}.{named}"
            assert not named.endswith("_id"), f"{shape.__name__}.{named}"


def test_the_pipeline_never_reprompts_for_a_whole_map() -> None:
    """No shape a model fills can carry a list of claims or a list of arrows.

    One call asks one question and gets one answer. A list cannot be drawn one
    refusal at a time, one bad member spoils the whole answer, and it records as
    one large recording instead of several small stable ones.
    """
    for shape in shapes_a_model_may_fill():
        for named, field in shape.model_fields.items():
            written = str(field.annotation)
            carries_many = written.startswith(("tuple[", "list[", "typing.Tuple", "typing.List"))
            if not carries_many:
                continue
            assert "ClaimProposal" not in written, f"{shape.__name__}.{named}"
            assert "LinkDraft" not in written, f"{shape.__name__}.{named}"
            assert "StartingClaim" not in written, f"{shape.__name__}.{named}"


def test_only_two_shapes_are_ever_asked_for() -> None:
    """Exactly two answer shapes exist, and both are one thing rather than a map.

    Everything that goes out as a question comes back as one of these two, so the
    question "could a call ask for a whole map?" is answered by counting them.
    """
    asked_for: set[str] = set()
    for source in sorted(ENGINE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            named = node.func
            if not (isinstance(named, ast.Attribute) and named.attr == "_ask"):
                continue
            # The first thing handed over is the question; the second is the
            # shape an answer has to fit.
            asked_for.update(one.id for one in node.args[1:] if isinstance(one, ast.Name))
    # A proposal travels inside the envelope the wire forced on it; a starting
    # claim is already an object at the top and goes as it is.
    assert asked_for == {"OneProposal", "StartingClaim"}, asked_for


def test_an_arrow_is_only_ever_built_where_a_proposal_is_accepted() -> None:
    """One place mints an arrow, so no code path can invent one to make a route exist."""
    built_in: list[str] = []
    for source in sorted(ENGINE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for holder in ast.walk(tree):
            if not isinstance(holder, ast.FunctionDef):
                continue
            for node in ast.walk(holder):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "Link"
                ):
                    built_in.append(f"{source.name}:{holder.name}")
    assert built_in == ["expand.py:_arrow"], built_in


def test_no_code_in_this_layer_writes_a_word_only_a_price_or_a_study_earns() -> None:
    """Neither ever comes from a proposal, and nothing here has read a price."""
    for source in sorted(ENGINE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        written = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        for word in WORDS_ONLY_SOMEBODY_ELSE_EARNS:
            assert word not in written, f"{source.name} writes {word}"


def test_the_shapes_file_never_says_where_a_number_came_from() -> None:
    """Not in a field, not in a sentence: the word is not in that file at all."""
    said = Path(the_shapes.__file__).read_text(encoding="utf-8")
    assert "provenance" not in said


def test_the_vendor_library_is_named_in_exactly_one_module() -> None:
    """One seam talks to the model, and one seam knows what its replies look like.

    Everything past `client.py` works in our own shapes, which is what lets the
    rest of the pipeline be read, tested and replayed without the library at all.
    """
    names_it: set[str] = set()
    for source in sorted(ENGINE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            brought_in: list[str] = []
            if isinstance(node, ast.Import):
                brought_in = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                brought_in = [node.module]
            if any(one == "anthropic" or one.startswith("anthropic.") for one in brought_in):
                names_it.add(source.name)
    assert names_it == {"client.py"}, names_it


def test_one_rule_chooses_every_route_and_it_is_the_maps_own() -> None:
    """The change list, the path bar and the Verify door read the same rule.

    A second search here would eventually disagree with the first, and two
    readers would be shown two different best routes for one map.
    """
    from katalyst.domain.diff import best_backed_routes
    from katalyst.engine import verify

    assert verify.best_backed_routes is best_backed_routes
    chose_a_route = [
        f"{source.name}:{holder.name}"
        for source in sorted(ENGINE.rglob("*.py"))
        for holder in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(holder, ast.FunctionDef) and "route" in holder.name
    ]
    assert chose_a_route == [], chose_a_route


# --- The guard that runs a module as a program is the last thing in it -----


def every_module_of_ours() -> list[Path]:
    """Every Python file this package ships, so nothing can be added and missed."""
    root = Path(the_pipeline.__file__).parent.parent
    return sorted(one for one in root.rglob("*.py") if "__pycache__" not in one.parts)


def test_nothing_follows_the_guard_that_runs_a_module_as_a_program() -> None:
    """A 26-minute paid run was lost to this, on 2026-09-20.

    `record.py` had `if __name__ == "__main__": raise SystemExit(main())` at line
    617 and defined a function `main` calls at line 621 — below the guard. Run as
    a program, `main()` executes before the rest of the module exists, and the run
    died with a `NameError` after the money was spent. Imported by a test, every
    name is defined first, so every test passed and no linter saw it.

    Nothing catches this by running the code: the only reliable check is that the
    guard is the last thing in the file. Blank lines and comments after it are
    fine; a definition, an assignment or a statement is not.
    """
    offenders: list[str] = []
    for module in every_module_of_ours():
        written = ast.parse(module.read_text(encoding="utf-8"))
        guards = [
            one
            for one in written.body
            if isinstance(one, ast.If)
            and ast.unparse(one.test) in ('__name__ == "__main__"', "__name__ == '__main__'")
        ]
        if not guards:
            continue
        after = [one for one in written.body if one.lineno > guards[-1].lineno]
        if after:
            offenders.append(f"{module.name}: {', '.join(ast.unparse(one)[:40] for one in after)}")

    assert offenders == []


# --- The word *agreement* stays free ---------------------------------------


AGREEMENT_LIVES_HERE = "katalyst/domain/diff.py"
"""The one file allowed a field called `agreement`: the diff's same-direction share.

`ClaimDiff.agreement` and `Ranked.agreement` answer one question — of the worlds
that were run, what share moved the same way as the headline. It is a column,
never a factor, and it is about worlds inside one run.
"""


def every_field_called_agreement() -> list[str]:
    """Find every field named `agreement` in our own source, with the file it is in."""
    found: list[str] = []
    for module in every_module_of_ours():
        written = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(written):
            named = (
                node.target.id
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                else None
            )
            if named == "agreement":
                found.append(f"{module}:{node.lineno}")
    return found


def test_the_word_agreement_means_same_direction_and_nothing_else() -> None:
    """Decision record 0015 said *not yet* to an ensemble, and this keeps that door shut.

    There is no `engine/ensemble.py`, no run-to-run number anywhere in the code
    and no screen that says *runs agree* — so a field called `agreement` may
    exist in exactly one place, where it means the share of worlds that moved the
    same way as the headline **inside one run**. Anywhere else the same word
    would quietly come to mean two models agreeing, which is a claim this product
    has not earned and a reader would believe.

    Read over our own source rather than trusted to memory, for the same reason
    `test_beliefs_never_merged` is: an invariant that depends on good intentions
    is a wish (`evaluation.md`, INV-generation.31).
    """
    elsewhere = [one for one in every_field_called_agreement() if AGREEMENT_LIVES_HERE not in one]

    assert elsewhere == []


def test_nothing_in_the_engine_runs_the_model_twice_to_compare_answers() -> None:
    """The other half of the same door: record 0015 said *not yet* to an ensemble.

    No module anywhere in this package is one, by name — and a module is where
    one would have to live, because running the model twice and comparing needs
    somewhere to hold both answers.
    """
    named = sorted(one.name for one in every_module_of_ours() if "ensemble" in one.name)

    assert named == []
