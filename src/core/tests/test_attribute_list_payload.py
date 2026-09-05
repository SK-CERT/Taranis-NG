"""The configuration attribute list must not carry every attribute's constants.

Listing attributes used to nest each one's constants in the response. CPE and CVE were skipped
because their dictionaries are huge, but CWE was not - a loaded CWE dictionary alone is on the
order of 1500 rows - and the constants of every RADIO/ENUM/MULTI_CHOICE attribute were serialised
too. None of it is read: both GUIs load an attribute's constants from the paginated
``/config/attributes/<id>/enums`` endpoint when the edit dialog opens.

Dropping them means an update round-tripped from a list row no longer carries the field, so the
schema has to tolerate its absence - which is the other half of what these tests pin down.
"""

import ast
from pathlib import Path

import pytest

CORE_ROOT = Path(__file__).parents[1]
ATTRIBUTE_MODEL = CORE_ROOT / "model" / "attribute.py"


def _function(module: ast.Module, name: str, *, within: str | None = None) -> ast.FunctionDef:
    scope: ast.AST = module
    if within is not None:
        scope = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == within)
    for node in ast.walk(scope):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    message = f"{name} is not defined"
    raise AssertionError(message)


def test_the_list_serialises_without_the_constants() -> None:
    """The dump schema must exclude them, or every constant ships on every page load."""
    module = ast.parse(ATTRIBUTE_MODEL.read_text(encoding="utf-8"))
    source = ast.get_source_segment(ATTRIBUTE_MODEL.read_text(encoding="utf-8"), _function(module, "get_all_json", within="Attribute"))

    assert source is not None
    assert 'exclude=("attribute_enums",)' in source
    # The old loop re-read every attribute's rows on top of the relationship's own eager load.
    assert "get_all_for_attribute" not in source


def test_listing_does_not_eagerly_load_the_constants() -> None:
    """The relationship is lazy="subquery", so the query has to opt out explicitly."""
    module = ast.parse(ATTRIBUTE_MODEL.read_text(encoding="utf-8"))
    source = ast.get_source_segment(ATTRIBUTE_MODEL.read_text(encoding="utf-8"), _function(module, "get", within="Attribute"))

    assert source is not None
    assert "noload(cls.attribute_enums)" in source


@pytest.mark.parametrize("schema_module", ["shared.schema.attribute", "model.attribute"])
def test_an_attribute_loads_without_the_constants_field(schema_module: str) -> None:
    """A list row sent back as an update has no constants; both schemas must still accept it."""
    import importlib  # noqa: PLC0415

    module = importlib.import_module(schema_module)
    schema = (module.NewAttributeSchema if hasattr(module, "NewAttributeSchema") else module.AttributeSchema)()

    attribute = schema.load(
        {
            "id": 1,
            "name": "Impact",
            "description": "",
            "type": "ENUM",
            "default_value": "",
            "validator": "NONE",
            "validator_parameter": "",
        },
    )

    assert attribute.attribute_enums == []


def test_constants_are_still_accepted_when_they_are_sent() -> None:
    """Creating an attribute still carries its constants in the same request."""
    from model.attribute import NewAttributeSchema  # noqa: PLC0415

    attribute = NewAttributeSchema().load(
        {
            "id": -1,
            "name": "Impact",
            "description": "",
            "type": "ENUM",
            "default_value": "",
            "validator": "NONE",
            "validator_parameter": "",
            "attribute_enums": [{"value": "High", "description": "", "index": 0}],
        },
    )

    assert [enum.value for enum in attribute.attribute_enums] == ["High"]
