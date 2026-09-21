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
