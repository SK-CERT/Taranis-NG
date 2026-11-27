"""Exporting and importing report type definitions.

A report type is only portable through names: its fields point at ``Attribute`` rows by foreign
key, and those keys mean nothing on another installation. So the export carries the attribute
types the report types use in their own section, keyed by name, and the import resolves each
field against them - reusing an attribute type that already exists, creating one that does not,
before any report type is written.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import ValidationError
from model.attribute import Attribute, AttributeEnum
from model.report_item_type import ReportItemType
from shared.schema.report_item_type_export import (
    ENUM_BACKED_TYPES,
    EXPORT_VERSION,
    AttributeEnumExport,
    AttributeGroupExport,
    AttributeGroupItemExport,
    AttributeTypeExport,
    ReportTypeExport,
    ReportTypeExportRoot,
    ReportTypeExportRootSchema,
)
from sqlalchemy import func

if TYPE_CHECKING:
    from model.user import User


def _attribute_type_export(attribute: Attribute) -> AttributeTypeExport:
    """The portable definition of an attribute type.

    Args:
        attribute (Attribute): The attribute to describe.

    Returns:
        AttributeTypeExport: Its definition, with constants only for the enum-backed types.
    """
    enums: list[AttributeEnumExport] = []
    if attribute.type in ENUM_BACKED_TYPES:
        for enum_index, enum in enumerate(AttributeEnum.for_attribute(attribute.id)):
            enums.append(AttributeEnumExport(index=enum_index, value=enum.value, description=enum.description or ""))

    return AttributeTypeExport(
        name=attribute.name,
        description=attribute.description,
        type=attribute.type,
        default_value=attribute.default_value,
        validator=attribute.validator,
        validator_parameter=attribute.validator_parameter,
        attribute_enums=enums,
    )


def _report_type_export(report_type: ReportItemType) -> ReportTypeExport:
    """The portable definition of a report type.

    Args:
        report_type (ReportItemType): The report type to describe.

    Returns:
        ReportTypeExport: Its definition, without ids, translations or AI model references.
    """
    groups: list[AttributeGroupExport] = []
    for group_index, group in enumerate(report_type.attribute_groups):
        items: list[AttributeGroupItemExport] = []
        for item_index, item in enumerate(group.attribute_group_items):
            attribute = item.attribute
            items.append(
                AttributeGroupItemExport(
                    title=item.title,
                    description=item.description or "",
                    index=item_index,
                    min_occurrence=item.min_occurrence or 0,
                    max_occurrence=item.max_occurrence or 1,
                    # The name is the only identity an attribute type has across installations.
                    attribute_type_key=attribute.name if attribute is not None else None,
                ),
            )
        groups.append(
            AttributeGroupExport(
                title=group.title,
                description=group.description or "",
                section=group.section,
                section_title=group.section_title,
                index=group_index,
                attribute_group_items=items,
            ),
        )

    return ReportTypeExport(
        title=report_type.title,
        description=report_type.description or "",
        icon=report_type.icon,
        attribute_groups=groups,
    )


def export_report_types(user: User, selection: list[str | int] | None = None) -> bytes:
    """Serialize selected report type definitions the user may see.

    Args:
        user (User): The exporting user; the ACL decides which types they may see.
        selection (list[str | int] | None): The selected report type ids; all visible types if absent.

    Returns:
        (bytes): The export document.
    """
    report_types, _count = ReportItemType.get(None, user, True)
    if selection is not None:
        selected_ids = {str(item_id) for item_id in selection}
        report_types = [report_type for report_type in report_types if str(report_type.id) in selected_ids]

    exports = [_report_type_export(report_type) for report_type in report_types]

    # Collected after the report types are built, so the attribute types are exactly those the
    # export references. Names are unique in practice but not constrained, so the first row of a
    # name wins and each name is described once.
    described: dict[str, AttributeTypeExport] = {}
    for report_type in report_types:
        for group in report_type.attribute_groups:
            for item in group.attribute_group_items:
                attribute = item.attribute
                if attribute is None or attribute.name in described:
                    continue
                described[attribute.name] = _attribute_type_export(attribute)

    root = ReportTypeExportRoot(version=EXPORT_VERSION, report_types=exports, attribute_types=list(described.values()))
    schema = ReportTypeExportRootSchema()
    return json.dumps(schema.dump(root), indent=2).encode("utf-8")


class ReportTypeImportResult:
    """What an import did, so the presenter can report it rather than a bare success.

    Attributes:
        report_types_created (int): Report types written.
        report_types_skipped (list[str]): Titles of the report types that already existed.
        attribute_types_created (int): Attribute types written.
        fields_skipped (list[str]): Titles of the fields whose attribute type was in neither the
            target installation nor the file, so they were dropped.
    """

    def __init__(self) -> None:
        """Start an empty result."""
        self.report_types_created = 0
        self.report_types_skipped: list[str] = []
        self.attribute_types_created = 0
        self.fields_skipped: list[str] = []

    def to_dict(self) -> dict:
        """The result in the shape the GUI reads.

        Returns:
            dict: Counts and the names that were skipped.
        """
        return {
            "report_types_created": self.report_types_created,
            "report_types_skipped": self.report_types_skipped,
            "attribute_types_created": self.attribute_types_created,
            "fields_skipped": self.fields_skipped,
        }


def _find_attribute_by_name(name: str) -> Attribute | None:
    """The attribute type stored under a name, deterministically.

    ``Attribute.name`` is not unique-constrained, so a name can match several rows. Ordering by id
    keeps the choice stable across a retry rather than leaving it to the planner.

    Args:
        name (str): The name to look up.

    Returns:
        (Attribute | None): The attribute type, or None when the installation has none.
    """
    return Attribute.query.filter_by(name=name).order_by(Attribute.id).first()


def _resolve_attribute_types(attribute_types: list[AttributeTypeExport], result: ReportTypeImportResult) -> dict[str, int]:
    """Resolve every exported attribute type to an id, creating the missing ones.

    An attribute type that already exists is reused as it is: its constants may be a loaded
    dictionary or carry translations, and overwriting them from an export would destroy data the
    target installation owns. Only a missing one is written.

    Args:
        attribute_types (list[AttributeTypeExport]): The attribute types the file describes.
        result (ReportTypeImportResult): Accumulates what was created.

    Returns:
        dict[str, int]: Attribute type name -> id.
    """
    resolved: dict[str, int] = {}
    for exported in attribute_types:
        if not exported.name:
            continue
        existing = _find_attribute_by_name(exported.name)
        if existing is not None:
            resolved[existing.name] = existing.id
            continue

        attribute = Attribute(
            id=None,
            name=exported.name,
            description=exported.description,
            type=exported.type,
            default_value=exported.default_value,
            validator=exported.validator,
            validator_parameter=exported.validator_parameter,
            # Constants travel only for the enum-backed types; for the rest the file ships none,
            # and their real values come from the dictionary loader.
            attribute_enums=[
                AttributeEnum(id=None, index=enum.index, value=enum.value, description=enum.description)
                for enum in exported.attribute_enums
                if exported.type in ENUM_BACKED_TYPES
            ],
        )
        db.session.add(attribute)
        db.session.commit()
        resolved[attribute.name] = attribute.id
        result.attribute_types_created += 1

    return resolved


def _report_type_payload(exported: ReportTypeExport, attributes: dict[str, int], result: ReportTypeImportResult) -> dict:
    """The payload ``ReportItemType.add_report_item_type`` takes for an exported report type.

    Args:
        exported (ReportTypeExport): The report type from the file.
        attributes (dict[str, int]): Resolved attribute type name -> id.
        result (ReportTypeImportResult): Accumulates the fields that could not be resolved.

    Returns:
        dict: The payload, with the fields whose attribute type is unavailable dropped.
    """
    groups = []
    for group_index, group in enumerate(exported.attribute_groups):
        items = []
        for item_index, item in enumerate(group.attribute_group_items):
            attribute_id = attributes.get(item.attribute_type_key) if item.attribute_type_key else None
            if attribute_id is None:
                # The name matched nothing in the target installation and nothing in the file's
                # own attribute section. Dropping the field is the only safe reading: inventing a
                # type would give the report a field nobody defined.
                result.fields_skipped.append(item.title or f"(unnamed field {item_index + 1} of {group.title})")
                continue
            items.append(
                {
                    "id": -1,
                    "index": item_index,
                    "attribute_id": attribute_id,
                    "title": item.title,
                    "description": item.description,
                    "min_occurrence": item.min_occurrence,
                    "max_occurrence": item.max_occurrence,
                    # AI model references are installation-local and carry no meaning here.
                    "ai_provider_id": None,
                    "ai_prompt": None,
                },
            )
        groups.append(
            {
                "id": -1,
                "title": group.title,
                "description": group.description,
                "section": group.section,
                "section_title": group.section_title,
                "index": group_index,
                "attribute_group_items": items,
            },
        )

    return {
        "id": -1,
        "title": exported.title,
        "description": exported.description,
        "icon": exported.icon,
        "attribute_groups": groups,
    }


def _title_exists(title: str) -> bool:
    """Whether a report type with exactly that title is already configured.

    ``ReportItemType.title`` has no unique constraint, so "already imported" has to be decided by
    query. The match is exact but ignores case: a type called "Vulnerability Report" must not
    block importing one called "Vulnerability", while "vulnerability" and "Vulnerability" are the
    same thing to whoever reads the list.

    Args:
        title (str): The title to look for.

    Returns:
        bool: True when a report type of that title exists.
    """
    return db.session.query(ReportItemType.id).filter(func.lower(ReportItemType.title) == title.lower()).first() is not None


def import_report_types(file: Any) -> ReportTypeImportResult:  # noqa: ANN401
    """Create report types from an export document.

    Two passes, in this order, because the second depends on the first: attribute types are
    resolved and created, then the report types are written against the ids that produced.

    Args:
        file: The uploaded export document.

    Returns:
        ReportTypeImportResult: What was created and what was skipped.

    Raises:
        ValueError: When the file is not JSON, is not a version this core reads, or is malformed.
    """
    result = ReportTypeImportResult()

    try:
        json_data = json.loads(file.read().decode("utf8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        msg = "The import file is not a valid JSON document"
        raise ValueError(msg) from ex

    if not isinstance(json_data, dict):
        # A JSON array or scalar is a wrong shape rather than a wrong Python type, and the admin
        # chose the file - so it stays a ValueError, which the endpoint turns into a 400.
        msg = "The import file is not a report type export document"
        raise ValueError(msg)  # noqa: TRY004

    version = json_data.get("version")
    if version != EXPORT_VERSION:
        msg = f"Unsupported export format version: {version}"
        raise ValueError(msg)

    try:
        import_data = ReportTypeExportRootSchema().load(json_data)
    except ValidationError as ex:
        msg = f"The import file does not match the report type export format: {ex.messages}"
        raise ValueError(msg) from ex

    attributes = _resolve_attribute_types(import_data.attribute_types, result)

    for exported in import_data.report_types:
        if not exported.title:
            continue
        if _title_exists(exported.title):
            result.report_types_skipped.append(exported.title)
            continue
        payload = _report_type_payload(exported, attributes, result)
        ReportItemType.add_report_item_type(payload)
        result.report_types_created += 1

    logger.info(
        f"Report type import: {result.report_types_created} created, "
        f"{len(result.report_types_skipped)} skipped as existing, "
        f"{result.attribute_types_created} attribute types created, "
        f"{len(result.fields_skipped)} fields dropped",
    )
    return result
