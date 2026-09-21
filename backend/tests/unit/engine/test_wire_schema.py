"""What the service will accept as a description of an answer, checked before we call.

The first live call was refused, and nothing was recorded:

    output_config.format.schema: For 'anyOf', '$defs' is not supported

A choice between three shapes at the very top of a description, with those shapes
named by reference, is not something the service will take. Putting the same
choice one field down fixes it, and that is the only thing the wire forced on
this design.

**These read what the library will actually send**, not the shapes as they are
written: the library tidies a description before sending it, dropping what the
service does not support and checking those parts on this side instead. Reading
the untidied shape would tell you nothing about what goes out.

Every rule below comes from the structured-output limits in the `claude-api`
reference bundle, read on 2026-09-17, or from the service's own sentence above.
One 400 at a time is an expensive way to learn a schema.
"""

import json
from typing import Any

import pytest

from katalyst.engine.client import OneProposal, wire_schema
from katalyst.engine.proposal import StartingClaim

EVERY_SHAPE_WE_SEND = [OneProposal, StartingClaim]
"""The two descriptions of an answer this program ever sends."""

KEYWORDS_THE_SERVICE_DOES_NOT_TAKE = frozenset(
    {
        # Numbers and strings cannot be constrained; the library drops these and
        # checks them here instead.
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        # Arrays may not be constrained beyond what they hold.
        "minItems",
        "maxItems",
        "uniqueItems",
        "prefixItems",
        "contains",
        "minContains",
        "maxContains",
        # Nothing conditional, and no choice spelled a second way.
        "not",
        "if",
        "then",
        "else",
        "oneOf",
        "dependentSchemas",
        "patternProperties",
        "propertyNames",
    }
)
"""What the reference bundle lists as unsupported, spelled as it would appear."""

FORMATS_THE_SERVICE_TAKES = frozenset(
    {
        "date-time",
        "time",
        "date",
        "duration",
        "email",
        "hostname",
        "uri",
        "ipv4",
        "ipv6",
        "uuid",
    }
)
"""The only ways a string may be described."""


def every_part(node: Any) -> Any:
    """Walk a description and hand back every key and value in it, however deep."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from every_part(value)
    elif isinstance(node, list):
        for value in node:
            yield from every_part(value)


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_the_top_of_every_description_is_an_ordinary_object(shape: Any) -> None:
    """The one thing the service refused, named so it cannot come back."""
    sent = wire_schema(shape)

    assert sent["type"] == "object"
    assert "anyOf" not in sent
    assert "oneOf" not in sent


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_every_object_refuses_fields_nobody_asked_for(shape: Any) -> None:
    """The one thing the reference bundle requires of every object."""
    sent = wire_schema(shape)
    objects = sum(1 for key, value in every_part(sent) if key == "type" and value == "object")
    refusing = [value for key, value in every_part(sent) if key == "additionalProperties"]

    assert len(refusing) == objects
    assert all(one is False for one in refusing)


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_no_description_carries_a_keyword_the_service_does_not_take(shape: Any) -> None:
    """The library drops these on the way out; this is what proves it still does."""
    sent = wire_schema(shape)
    found = sorted(
        {key for key, _ in every_part(sent) if key in KEYWORDS_THE_SERVICE_DOES_NOT_TAKE}
    )

    assert found == []


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_a_string_is_only_ever_described_a_way_the_service_knows(shape: Any) -> None:
    """One date, and nothing else."""
    sent = wire_schema(shape)
    formats = {value for key, value in every_part(sent) if key == "format"}

    assert formats <= FORMATS_THE_SERVICE_TAKES


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_every_shape_named_by_reference_is_one_the_description_carries(shape: Any) -> None:
    """A reference to a shape that is not there would be refused, and rightly."""
    sent = wire_schema(shape)
    referred_to = {value for key, value in every_part(sent) if key == "$ref"}
    carried = {f"#/$defs/{one}" for one in sent.get("$defs", {})}

    assert referred_to <= carried


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_no_shape_describes_itself(shape: Any) -> None:
    """A description that refers to itself never ends, and the service refuses one."""
    sent = wire_schema(shape)
    for name, described in sent.get("$defs", {}).items():
        assert f"#/$defs/{name}" not in {
            value for key, value in every_part(described) if key == "$ref"
        }


def test_the_envelope_is_put_on_for_the_wire_and_taken_off_again() -> None:
    """A proposal goes out inside it and comes back out of it, both inside the seam."""
    sent = wire_schema(OneProposal)

    assert list(sent["properties"]) == ["proposal"]
    assert sent["required"] == ["proposal"]
    # The choice between the three shapes is now one field down, which is the
    # whole of the change.
    assert "anyOf" in sent["properties"]["proposal"]


def test_a_single_shape_needs_no_envelope() -> None:
    """A starting claim is already an object at the top, so it goes as it is."""
    sent = wire_schema(StartingClaim)

    assert "claim" in sent["properties"]
    assert "proposal" not in sent["properties"]


THE_HERO_CASE = (
    "Hormuz",
    "Strait",
    "Brent",
    "Iran",
    "Lloyd",
    "OPEC",
    "XLE",
    "tanker",
    "oil",
)
"""Every word the stored example's own claims are made of.

One word of it is deliberately not here. `ContractPayoff.venue` still says "by
the venue's own name: 'Polymarket', 'Kalshi'", and the stored example's trade is
on Polymarket. That is a venue example rather than a Hormuz example — it names
the *kind* of answer wanted and there is no way to ask for a venue's own name
without naming one — and the field it sits on belongs to the rules layer, so it
is reported rather than changed (2026-09-20).
"""


@pytest.mark.parametrize("shape", EVERY_SHAPE_WE_SEND, ids=lambda one: one.__name__)
def test_no_description_hands_the_model_the_stored_example(shape: Any) -> None:
    """Measured, 2026-09-17: the model gave back the schema's own example as a fact.

    A claim came back counting "37 of 41 cases since 1980", and "since 1980" was
    a phrase from the description of the field it filled in. A field description
    that carries a worked example is a field description the model will fill in
    with that example. So every description says what a good answer is *like* and
    none of them says what one *is* — least of all in the words of the example
    map this program ships (Kent, 2026-09-20).
    """
    written = json.dumps(wire_schema(shape)).lower()
    found = sorted(one for one in THE_HERO_CASE if one.lower() in written)

    assert found == []
