"""Report type export and import: the document shape, and the two-pass pairing with attribute types.

The models are built in memory (no database); the session and the queries the manager issues are
stubbed, so what is under test is the manager's own logic - what it serialises, how it pairs a
field with an attribute type, and what it refuses to overwrite.
"""

from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from managers import report_types_manager  # noqa: E402 - after every mapper is registered
from model.attribute import Attribute  # noqa: E402
from model.report_item_type import ReportItemType  # noqa: E402
from shared.schema.attribute import AttributeType, AttributeValidator  # noqa: E402
from shared.schema.report_item_type_export import (  # noqa: E402
    EXPORT_VERSION,
    ReportTypeExportRootSchema,
)


class _FakeQuery:
    """The few query verbs the manager uses, over a fixed list of rows."""

    def __init__(self, model: type, rows: list) -> None:
        """Hold the model the query runs against and the rows its table contains."""
        self.model = model
        self.rows = rows

    def filter_by(self, **kwargs: object) -> _FakeQuery:
        """Keep the rows whose attributes match every keyword."""
        return _FakeQuery(self.model, [row for row in self.rows if all(getattr(row, key) == value for key, value in kwargs.items())])

    def all(self) -> list:
        """Every remaining row."""
        return list(self.rows)

    def order_by(self, _column: object) -> _FakeQuery:
        """Ignore the ordering; the fake rows are already in id order."""
        return self

    def first(self) -> object | None:
        """The first remaining row, or None."""
        return self.rows[0] if self.rows else None


class _FakeSession:
    """Records what an import wrote, and answers the queries the models build against it.

    ``Model.query`` is a Flask-SQLAlchemy descriptor that builds ``Model.query_class(model,
    session=Model.__fsa__.session())``. Making this session callable and swapping in a fake query
    class lets the real descriptor run, so the manager is exercised through the same ``Model.query``
    it uses in production rather than through a patched-away stand-in.
    """

    def __init__(self, rows_by_model: dict[type, list]) -> None:
        """Start recording, with the given rows behind each model's queries."""
        self.rows_by_model = rows_by_model
        self.added: list = []
        self.commits = 0
        self._next_id = 100

    def __call__(self) -> _FakeSession:
        """Hand back the session Flask-SQLAlchemy asks for."""
        return self

    def query_class(self, model: type, session: object) -> _FakeQuery:  # noqa: ARG002
        """Build the query a model's ``query`` property would build."""
        return _FakeQuery(model, list(self.rows_by_model.get(model, [])))

    def add(self, item) -> None:  # noqa: ANN001 - the added type varies with the call under test
        """Take the object and give it the id a flush would have given it."""
        item.id = self._next_id
        self._next_id += 1
        self.added.append(item)

    def commit(self) -> None:
        """Count the commit; there is nothing to write."""
        self.commits += 1

    def get(self, _model: object, _id: object) -> None:
        """No identity lookup is needed by the code under test."""
        return


def _attribute(
    id_: int,
    name: str,
    attribute_type: AttributeType = AttributeType.STRING,
    enums: list[tuple[str, str]] | None = None,
) -> SimpleNamespace:
    """An attribute row light enough for the manager to read."""
    return SimpleNamespace(
        id=id_,
        name=name,
        description=f"{name} description",
        type=attribute_type,
        default_value=None,
        validator=None,
        validator_parameter=None,
        enums=[SimpleNamespace(value=value, description=description) for value, description in enums or []],
    )


def _group_item(title: str, attribute: SimpleNamespace | None) -> SimpleNamespace:
    """A field of a group, built on an attribute type."""
    return SimpleNamespace(
        title=title,
        description=f"{title} description",
        index=0,
        min_occurrence=0,
        max_occurrence=3,
        attribute=attribute,
    )


def _group(title: str, items: list[SimpleNamespace], section: int | None = -1, section_title: str | None = "") -> SimpleNamespace:
    """An attribute group of a report type."""
    return SimpleNamespace(
        title=title,
        description=f"{title} description",
        section=section,
        section_title=section_title,
        index=0,
        attribute_group_items=items,
    )


def _report_type(title: str, groups: list[SimpleNamespace], icon: str | None = "mdi-bug") -> SimpleNamespace:
    """A report type light enough for the manager to read."""
    return SimpleNamespace(title=title, description=f"{title} description", icon=icon, attribute_groups=groups)


def _install_session(monkeypatch: pytest.MonkeyPatch, rows_by_model: dict[type, list]) -> _FakeSession:
    """Swap the session the manager writes and queries through for one that only records.

    Args:
        monkeypatch: The pytest fixture undoing the swap afterwards.
        rows_by_model: The rows each model's ``query`` should see.

    Returns:
        _FakeSession: The session, so the test can read what it recorded.
    """
    session = _FakeSession(rows_by_model)
    monkeypatch.setattr(db, "session", session)
    for model in rows_by_model:
        # `query` resolves as `model.query_class(model, session=model.__fsa__.session())`, so both
        # halves are swapped: the session the descriptor asks for, and the class it builds.
        monkeypatch.setattr(model, "__fsa__", SimpleNamespace(session=session), raising=False)
        monkeypatch.setattr(model, "query_class", session.query_class, raising=False)
    return session


def test_the_export_describes_each_used_attribute_type_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two fields on the same attribute type produce one entry in the attribute section."""
    text = _attribute(1, "Text")
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "get",
        classmethod(
            lambda _cls, _search, _user, _acl: (
                [
                    _report_type("One", [_group("G", [_group_item("A", text), _group_item("B", text)])]),
                    _report_type("Two", [_group("G", [_group_item("C", text)])]),
                ],
                2,
            ),
        ),
    )
    monkeypatch.setattr(report_types_manager.AttributeEnum, "for_attribute", classmethod(lambda _cls, _id: []))

    document = json.loads(report_types_manager.export_report_types(SimpleNamespace()))

    assert document["version"] == EXPORT_VERSION
    assert [item["title"] for item in document["report_types"]] == ["One", "Two"]
    assert [item["name"] for item in document["attribute_types"]] == ["Text"]
    # The field pairs by name, never by the id that means nothing on the target.
    assert document["report_types"][0]["attribute_groups"][0]["attribute_group_items"][0]["attribute_type_key"] == "Text"
    assert "id" not in document["report_types"][0]["attribute_groups"][0]["attribute_group_items"][0]


def test_the_export_includes_only_selected_visible_report_type_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selected ids are intersected with the types the caller is allowed to see."""
    text = _attribute(1, "Text")
    visible = _report_type("Visible", [_group("G", [_group_item("A", text)])])
    hidden = _report_type("Hidden", [_group("G", [_group_item("B", text)])])
    visible.id = 7
    hidden.id = 8
    monkeypatch.setattr(report_types_manager.ReportItemType, "get", classmethod(lambda _cls, _search, _user, _acl: ([visible], 1)))
    monkeypatch.setattr(report_types_manager.AttributeEnum, "for_attribute", classmethod(lambda _cls, _id: []))

    document = json.loads(report_types_manager.export_report_types(SimpleNamespace(), selection=[7, 8]))

    assert [item["title"] for item in document["report_types"]] == ["Visible"]
    assert [item["name"] for item in document["attribute_types"]] == ["Text"]


def test_the_export_ships_constants_only_for_the_enum_backed_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """A RADIO attribute carries its constants; a CPE attribute does not carry a million rows."""
    radio = _attribute(1, "Threat level", AttributeType.RADIO, [("High", "High risk"), ("Low", "Low risk")])
    cpe = _attribute(2, "CPE", AttributeType.CPE, [("cpe:/a:foo", "")] * 500)
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "get",
        classmethod(
            lambda _cls, _search, _user, _acl: (
                [_report_type("Vulnerability", [_group("G", [_group_item("Severity", radio), _group_item("Affected", cpe)])])],
                1,
            ),
        ),
    )

    def _constants(_cls: object, attribute_id: int) -> list[SimpleNamespace]:
        return (radio if attribute_id == 1 else cpe).enums

    monkeypatch.setattr(report_types_manager.AttributeEnum, "for_attribute", classmethod(_constants))

    document = json.loads(report_types_manager.export_report_types(SimpleNamespace()))
    by_name = {item["name"]: item for item in document["attribute_types"]}

    assert [(enum["value"], enum["index"]) for enum in by_name["Threat level"]["attribute_enums"]] == [("High", 0), ("Low", 1)]
    assert by_name["CPE"]["attribute_enums"] == []


def test_the_export_document_round_trips_through_its_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """What the export writes is what the import reads; the two do not drift apart."""
    text = _attribute(1, "Text")
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "get",
        classmethod(
            lambda _cls, _search, _user, _acl: (
                [_report_type("Incident", [_group("Overview", [_group_item("Summary", text)])], icon=None)],
                1,
            ),
        ),
    )
    monkeypatch.setattr(report_types_manager.AttributeEnum, "for_attribute", classmethod(lambda _cls, _id: []))

    document = json.loads(report_types_manager.export_report_types(SimpleNamespace()))
    loaded = ReportTypeExportRootSchema().load(document)

    assert loaded.version == EXPORT_VERSION
    assert loaded.report_types[0].title == "Incident"
    assert loaded.report_types[0].icon is None
    assert loaded.report_types[0].attribute_groups[0].attribute_group_items[0].max_occurrence == 3
    assert loaded.attribute_types[0].name == "Text"


def test_a_field_without_an_attribute_type_exports_a_null_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stored field whose attribute row vanished exports rather than crashing the export."""
    orphan = _group_item("Broken", None)
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "get",
        classmethod(lambda _cls, _search, _user, _acl: ([_report_type("Odd", [_group("G", [orphan])])], 1)),
    )

    document = json.loads(report_types_manager.export_report_types(SimpleNamespace()))

    assert document["report_types"][0]["attribute_groups"][0]["attribute_group_items"][0]["attribute_type_key"] is None
    assert document["attribute_types"] == []


def test_the_import_creates_a_missing_attribute_type_before_its_field_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass one writes the attribute types, and pass two points the fields at the ids it produced."""
    payloads: list[dict] = []
    session = _install_session(monkeypatch, {Attribute: [], ReportItemType: []})
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "add_report_item_type",
        classmethod(lambda _cls, payload: payloads.append(payload)),
    )

    document = {
        "version": EXPORT_VERSION,
        "attribute_types": [
            {
                "name": "Threat level",
                "description": "",
                "type": "RADIO",
                "default_value": None,
                "validator": None,
                "validator_parameter": None,
                "attribute_enums": [{"index": 0, "value": "High", "description": ""}],
            },
        ],
        "report_types": [
            {
                "title": "Vulnerability",
                "description": "",
                "icon": "mdi-bug",
                "attribute_groups": [
                    {
                        "title": "Impact",
                        "description": "",
                        "section": -1,
                        "section_title": "",
                        "index": 0,
                        "attribute_group_items": [
                            {
                                "title": "Severity",
                                "description": "",
                                "index": 0,
                                "min_occurrence": 0,
                                "max_occurrence": 1,
                                "attribute_type_key": "Threat level",
                            },
                        ],
                    },
                ],
            },
        ],
    }

    result = report_types_manager.import_report_types(io.BytesIO(json.dumps(document).encode("utf-8")))

    assert result.attribute_types_created == 1
    assert result.report_types_created == 1
    assert result.fields_skipped == []
    created_attribute = session.added[0]
    assert isinstance(created_attribute, Attribute)
    assert [enum.value for enum in created_attribute.attribute_enums] == ["High"]

    payload = payloads[0]
    assert payload["attribute_groups"][0]["attribute_group_items"][0]["attribute_id"] == created_attribute.id
    # AI model references never travel; the payload says so explicitly.
    assert payload["attribute_groups"][0]["attribute_group_items"][0]["ai_provider_id"] is None


def test_the_import_keeps_an_existing_attribute_type_and_ignores_its_exported_definition(monkeypatch: pytest.MonkeyPatch) -> None:
    """The target installation owns its attribute types; an export cannot rewrite their constants."""
    stored = _attribute(7, "TLP", AttributeType.RADIO)
    payloads: list[dict] = []
    session = _install_session(monkeypatch, {Attribute: [stored], ReportItemType: []})
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "add_report_item_type",
        classmethod(lambda _cls, payload: payloads.append(payload)),
    )

    document = {
        "version": EXPORT_VERSION,
        "attribute_types": [
            {
                "name": "TLP",
                "description": "overwritten",
                "type": "ENUM",
                "default_value": None,
                "validator": AttributeValidator.NONE.name,
                "validator_parameter": None,
                "attribute_enums": [{"index": 0, "value": "Invented", "description": ""}],
            },
        ],
        "report_types": [
            {
                "title": "Incident",
                "description": "",
                "icon": None,
                "attribute_groups": [
                    {
                        "title": "Handling",
                        "description": "",
                        "section": -1,
                        "section_title": "",
                        "index": 0,
                        "attribute_group_items": [
                            {
                                "title": "TLP",
                                "description": "",
                                "index": 0,
                                "min_occurrence": 0,
                                "max_occurrence": 1,
                                "attribute_type_key": "TLP",
                            },
                        ],
                    },
                ],
            },
        ],
    }

    result = report_types_manager.import_report_types(io.BytesIO(json.dumps(document).encode("utf-8")))

    assert result.attribute_types_created == 0
    assert session.added == []
    assert payloads[0]["attribute_groups"][0]["attribute_group_items"][0]["attribute_id"] == 7


def test_the_import_skips_a_report_type_whose_title_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """A title already configured is left alone, whatever case the file wrote it in."""
    existing = SimpleNamespace(title="Vulnerability")
    payloads: list[dict] = []
    _install_session(monkeypatch, {Attribute: [], ReportItemType: [existing]})
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "add_report_item_type",
        classmethod(lambda _cls, payload: payloads.append(payload)),
    )

    document = {
        "version": EXPORT_VERSION,
        "attribute_types": [],
        "report_types": [{"title": "vulnerability", "description": "", "icon": None, "attribute_groups": []}],
    }

    result = report_types_manager.import_report_types(io.BytesIO(json.dumps(document).encode("utf-8")))

    assert result.report_types_created == 0
    assert result.report_types_skipped == ["vulnerability"]
    assert payloads == []


def test_the_import_drops_a_field_whose_attribute_type_is_in_neither_place(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unresolvable field is named and dropped, not replaced with an invented type."""
    payloads: list[dict] = []
    _install_session(monkeypatch, {Attribute: [], ReportItemType: []})
    monkeypatch.setattr(
        report_types_manager.ReportItemType,
        "add_report_item_type",
        classmethod(lambda _cls, payload: payloads.append(payload)),
    )

    document = {
        "version": EXPORT_VERSION,
        "attribute_types": [],
        "report_types": [
            {
                "title": "Odd",
                "description": "",
                "icon": None,
                "attribute_groups": [
                    {
                        "title": "G",
                        "description": "",
                        "section": -1,
                        "section_title": "",
                        "index": 0,
                        "attribute_group_items": [
                            {
                                "title": "Kept",
                                "description": "",
                                "index": 0,
                                "min_occurrence": 0,
                                "max_occurrence": 1,
                                "attribute_type_key": "Missing",
                            },
                            {
                                "title": "Also kept",
                                "description": "",
                                "index": 1,
                                "min_occurrence": 0,
                                "max_occurrence": 1,
                                "attribute_type_key": None,
                            },
                        ],
                    },
                ],
            },
        ],
    }

    result = report_types_manager.import_report_types(io.BytesIO(json.dumps(document).encode("utf-8")))

    assert result.fields_skipped == ["Kept", "Also kept"]
    assert payloads[0]["attribute_groups"][0]["attribute_group_items"] == []
    # The type itself still arrives: dropping its unresolvable fields is not a reason to lose it.
    assert result.report_types_created == 1


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"not json", "not a valid JSON"),
        (b"[1, 2]", "not a report type export document"),
        (json.dumps({"version": 99, "report_types": [], "attribute_types": []}).encode("utf-8"), "Unsupported export format version"),
        (json.dumps({"version": EXPORT_VERSION, "report_types": [{"description": ""}]}).encode("utf-8"), "does not match"),
    ],
)
def test_a_bad_import_file_is_rejected_with_the_reason(body: bytes, reason: str) -> None:
    """The admin picked the file, so a rejected one gets a message they can act on."""
    with pytest.raises(ValueError, match=reason):
        report_types_manager.import_report_types(io.BytesIO(body))
