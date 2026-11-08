"""Taranis as a GCVE Numbering Authority: the CVD Report type, the GCVE Advisory preset, identifiers.

- Six attribute types for the structured fields of a CVD Report (AFFECTED, CREDIT, TIMELINE,
  RELATIONSHIP, REFERENCE, JSON). Their labels are committed in an autocommit block before they
  are used, and the enum's real name is read from the catalog (see c7a1b4e9d203).
- ``report_item_type`` and ``product_preset`` get ``system_key`` (set on the ones Taranis ships,
  which are locked) and ``enabled`` (switched off: not offered for new reports and products).
- ``gcve_counter`` keeps the last number allocated per GNA and year, ``gcve_assignment`` every
  identifier allocated and its report.
- ``organization_gna``: an organization's GNA - its number (unique), its short name and its entry
  in the gcve.eu GNA directory (copied from there by core, never typed in), the licence of its
  records and its conformance details. ``report_item.organization_id``: a CVD Report's organization
  (its author's), whose GNA number gives it its identifier.
- The tables are created only when missing: ``create_app()`` runs ``create_all()``, which may have
  made them already.
- The setting ``GCVE_GNA_DIRECTORY_URL``: where the GNA directory is downloaded from. The
  ``settings`` model declared ``type`` unique, which no migration ever created but ``create_all()``
  would; such a constraint is dropped.
- The shipped "CVD Report" type (``system_key='cvd'``) with its attributes and constants, and the
  "GCVE Advisory" product preset (``system_key='gcve'``), both switched off until an administrator
  switches them on. Seeding is keyed on ``system_key``, so running it again changes nothing.
  The fields are a copy of ``shared.gcve`` as of this revision; a test keeps the two equal.

The downgrade refuses while identifiers have been allocated: dropping them would let a number
be given again, which GCVE-BCP-06 forbids. The attribute type labels stay (Postgres cannot drop
enum labels).

Revision ID: 6d1f0a9c3e25
Revises: 7a4c1e9b2d36
Create Date: 2026-11-08 18:00:00.000000

"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "6d1f0a9c3e25"
down_revision = "7a4c1e9b2d36"
branch_labels = None
depends_on = None

NEW_ATTRIBUTE_TYPES = ("AFFECTED", "CREDIT", "TIMELINE", "RELATIONSHIP", "REFERENCE", "JSON")
LOCKED_TABLES = ("report_item_type", "product_preset")

CVD_TYPE_KEY = "cvd"
CVD_TYPE_TITLE = "CVD Report"
CVD_TYPE_DESCRIPTION = "Coordinated Vulnerability Disclosure, published as a GCVE record"
CVD_TYPE_ICON = "mdi-shield-bug-outline"
GCVE_PRESET_KEY = "gcve"
GCVE_PRESET_NAME = "GCVE Advisory"
GCVE_PRESET_DESCRIPTION = "CVD Reports published as GCVE records on the public webs that publish GCVE records"
GCVE_PRESET_ICON = "mdi-shield-check-outline"

GNA_ID_MIN = 1
GNA_ID_MAX = 65535

SETTINGS = (("GCVE_GNA_DIRECTORY_URL", "S", "https://gcve.eu/dist/gcve.json", "GCVE numbering authorities (GNA) - directory URL"),)

# shared.gcve as of this revision: (name, type, description, constants, default_value, validator_parameter)
OFFERED_RECORD_TYPES = (
    "advisory",
    "update",
    "analysis",
    "metadata",
    "reference",
    "comment",
    "statement",
    "remediation",
    "deprecation",
    "detection",
    "bundle",
)
RELATIONSHIP_TYPES = ("possibly_related", "related", "not equal", "equal", "superset", "subset", "overlap", "opposes", "not_applicable")
CREDIT_TYPES = (
    "finder",
    "reporter",
    "analyst",
    "coordinator",
    "remediation developer",
    "remediation reviewer",
    "remediation verifier",
    "tool",
    "sponsor",
    "other",
)
REFERENCE_TAGS = (
    "broken-link",
    "customer-entitlement",
    "exploit",
    "government-resource",
    "issue-tracking",
    "mailing-list",
    "mitigation",
    "not-applicable",
    "patch",
    "permissions-required",
    "media-coverage",
    "product",
    "related",
    "release-notes",
    "signature",
    "technical-description",
    "third-party-advisory",
    "vendor-advisory",
    "vdb-entry",
)
ATTRIBUTES = (
    ("CVD Record type", "RADIO", "GCVE record type (GCVE-BCP-05)", OFFERED_RECORD_TYPES, "advisory", None),
    ("CVD Discovery", "RADIO", "How the vulnerability was discovered", ("INTERNAL", "EXTERNAL", "USER", "UNKNOWN"), None, None),
    ("CVD Tags", "MULTI_CHOICE", "CVE record tags", ("unsupported-when-assigned", "exclusively-hosted-service", "disputed"), None, None),
    ("CVD Affected product", "AFFECTED", "Affected product with its versions", ("affected", "unaffected", "unknown"), None, None),
    ("CVD Credit", "CREDIT", "Credit for work on the vulnerability", CREDIT_TYPES, None, None),
    ("CVD Timeline event", "TIMELINE", "Dated event of the disclosure", (), None, None),
    ("CVD Relationship", "RELATIONSHIP", "Relationship to another record (GCVE-BCP-05)", RELATIONSHIP_TYPES, None, None),
    ("CVD Reference", "REFERENCE", "Reference with its name and tags", REFERENCE_TAGS, None, None),
    ("CVD Other metric", "JSON", "Other impact metric (CVE metrics.other)", (), None, "metric_other"),
    ("CVD Taxonomy mapping", "JSON", "Taxonomy mapping (CVE taxonomyMappings)", (), None, "taxonomy_mapping"),
)
MANY = 1000
# The generic attribute of each of these types, the first of the type, serves the fields of that
# type (named as the type in GROUPS); created with this name where there is none.
GENERIC_ATTRIBUTES = {"STRING": "Text", "RICH_TEXT": "Rich Text", "DATE": "Date", "CVSS": "CVSS", "CVE": "CVE", "CWE": "CWE"}
# (group title, ((field title, attribute name or generic type, min, max, description), ...))
GROUPS = (
    (
        "Record",
        (
            ("Record type", "CVD Record type", 1, 1, "The GCVE record type; deprecation withdraws the record"),
            ("CVE", "CVE", 0, 1, "The CVE of the same vulnerability, if it has one"),
            ("Related records", "CVD Relationship", 0, MANY, "Other records this one relates to"),
            ("Tags", "CVD Tags", 0, 1, "CVE record tags"),
        ),
    ),
    (
        "Vulnerability",
        (
            ("Description", "RICH_TEXT", 1, 1, "What the vulnerability is"),
            ("Affected products", "CVD Affected product", 1, MANY, "Products and versions affected"),
            ("CVSS", "CVSS", 0, MANY, "CVSS vectors (2.0, 3.0, 3.1 or 4.0)"),
            ("Other metrics", "CVD Other metric", 0, MANY, "Metrics in another format, e.g. SSVC"),
            ("CWE", "CWE", 0, MANY, "Weaknesses (problem types)"),
            ("Problem types", "STRING", 0, MANY, "Problem types without a CWE"),
            ("Impacts", "RICH_TEXT", 0, MANY, "Impacts; a leading CAPEC-<n> names the CAPEC pattern"),
            ("Taxonomy mappings", "CVD Taxonomy mapping", 0, MANY, "Mappings to other taxonomies"),
            ("Date public", "DATE", 0, 1, "When the vulnerability was disclosed publicly"),
        ),
    ),
    (
        "Remediation",
        (
            ("Solutions", "RICH_TEXT", 0, MANY, "Fixes"),
            ("Workarounds", "RICH_TEXT", 0, MANY, "Temporary mitigations"),
            ("Configurations", "RICH_TEXT", 0, MANY, "Configurations required for exposure"),
            ("Exploits", "RICH_TEXT", 0, MANY, "Known exploits and exploitation"),
        ),
    ),
    (
        "Source",
        (
            ("Discovery", "CVD Discovery", 0, 1, "How the vulnerability was discovered"),
            ("Defects", "STRING", 0, MANY, "Defect (bug tracker) identifiers"),
            ("Advisories", "STRING", 0, MANY, "Advisory identifiers"),
        ),
    ),
    (
        "Disclosure",
        (
            ("Timeline", "CVD Timeline event", 0, MANY, "Events of the disclosure"),
            ("Credits", "CVD Credit", 0, MANY, "People, organisations and tools credited"),
        ),
    ),
    ("Resources", (("References", "CVD Reference", 1, MANY, "References; texts cite them as [n]"),)),
)


def _enum_type_name(connection: Connection, table: str, column: str) -> str:
    """Read the Postgres enum type actually backing a column, which is not always the model's name."""
    return connection.execute(
        sa.text(
            "SELECT t.typname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_type t ON t.oid = a.atttypid "
            "WHERE c.relname = :table AND a.attname = :column AND a.attnum > 0 AND NOT a.attisdropped",
        ),
        {"table": table, "column": column},
    ).scalar_one()


def _tables(connection: Connection) -> set[str]:
    return set(sa.inspect(connection).get_table_names())


def _columns(connection: Connection, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(connection).get_columns(table)}


def _foreign_keys(connection: Connection, table: str) -> set[str]:
    return {key["name"] for key in sa.inspect(connection).get_foreign_keys(table) if key.get("name")}


def _indexes(connection: Connection, table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(connection).get_indexes(table)}


def _add_attribute_types() -> None:
    type_name = _enum_type_name(op.get_bind(), "attribute", "type")
    with op.get_context().autocommit_block():
        for attribute_type in NEW_ATTRIBUTE_TYPES:
            op.execute(f"ALTER TYPE \"{type_name}\" ADD VALUE IF NOT EXISTS '{attribute_type}'")


def _add_lock_columns(connection: Connection) -> None:
    for table in LOCKED_TABLES:
        columns = _columns(connection, table)
        if "system_key" not in columns:
            op.add_column(table, sa.Column("system_key", sa.String(32), nullable=True))
            op.create_unique_constraint(f"{table}_system_key_key", table, ["system_key"])
        if "enabled" not in columns:
            op.add_column(table, sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))


def _create_tables(connection: Connection) -> None:
    tables = _tables(connection)
    if "gcve_counter" not in tables:
        op.create_table(
            "gcve_counter",
            sa.Column("gna_id", sa.Integer(), autoincrement=False, nullable=False),
            sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
            sa.Column("last_number", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("gna_id", "year"),
        )
    if "gcve_assignment" not in tables:
        op.create_table(
            "gcve_assignment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("gcve_id", sa.String(255), nullable=False),
            sa.Column("gna_id", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("report_item_id", sa.Integer(), nullable=True),
            sa.Column("state", sa.String(16), nullable=False),
            sa.Column("date_reserved", sa.DateTime(timezone=True), nullable=False),
            sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
            sa.Column("date_updated", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["report_item_id"], ["report_item.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("gcve_id"),
            sa.UniqueConstraint("report_item_id"),
            sa.UniqueConstraint("gna_id", "year", "number", name="uq_gcve_assignment_number"),
            sa.CheckConstraint("state IN ('RESERVED', 'PUBLISHED', 'REJECTED')", name="ck_gcve_assignment_state"),
        )
    if "organization_gna" not in tables:
        op.create_table(
            "organization_gna",
            sa.Column("organization_id", sa.Integer(), autoincrement=False, nullable=False),
            sa.Column("gna_id", sa.Integer(), nullable=False),
            sa.Column("short_name", sa.String(32), nullable=True),
            sa.Column("directory", sa.JSON(), nullable=True),
            sa.Column("directory_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("records_license", sa.String(255), nullable=False),
            sa.Column("conformance", sa.JSON(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("organization_id"),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("gna_id"),
            sa.CheckConstraint(f"gna_id BETWEEN {GNA_ID_MIN} AND {GNA_ID_MAX}", name="ck_organization_gna_gna_id"),
        )


def _add_report_organization(connection: Connection) -> None:
    """``report_item.organization_id``, named as ``create_all()`` names it."""
    if "organization_id" not in _columns(connection, "report_item"):
        op.add_column("report_item", sa.Column("organization_id", sa.Integer(), nullable=True))
    if "report_item_organization_id_fkey" not in _foreign_keys(connection, "report_item"):
        op.create_foreign_key(
            "report_item_organization_id_fkey",
            "report_item",
            "organization",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "ix_report_item_organization_id" not in _indexes(connection, "report_item"):
        op.create_index("ix_report_item_organization_id", "report_item", ["organization_id"])


def _add_settings(connection: Connection) -> None:
    op.execute("ALTER TABLE settings DROP CONSTRAINT IF EXISTS settings_type_key")
    has_options = "options" in _columns(connection, "settings")
    for key, setting_type, value, description in SETTINGS:
        if connection.execute(sa.text("SELECT 1 FROM settings WHERE key = :key"), {"key": key}).scalar() is not None:
            continue
        options = ", options" if has_options else ""
        options_value = ", ''" if has_options else ""
        connection.execute(
            sa.text(
                f"INSERT INTO settings (key, type, value, default_val, description, is_global, updated_by{options}) "  # noqa: S608 (fixed column names)
                f"VALUES (:key, :type, :value, :value, :description, true, 'system-migration'{options_value})",
            ),
            {"key": key, "type": setting_type, "value": value, "description": description},
        )


def _attribute_ids(connection: Connection) -> dict[str, int]:
    """The id of every attribute the CVD Report uses, created where missing."""
    type_name = _enum_type_name(connection, "attribute", "type")
    validator_type = _enum_type_name(connection, "attribute", "validator")
    ids: dict[str, int] = {}
    for name, attribute_type, description, constants, default_value, validator_parameter in ATTRIBUTES:
        found = connection.execute(sa.text("SELECT id FROM attribute WHERE name = :name ORDER BY id LIMIT 1"), {"name": name}).scalar()
        if found is None:
            # The interpolated names come from pg_catalog, not from user input.
            found = connection.execute(
                sa.text(
                    "INSERT INTO attribute (name, description, type, default_value, validator, validator_parameter) "  # noqa: S608
                    f'VALUES (:name, :description, CAST(:type AS "{type_name}"), :default_value, '
                    f'CAST(:validator AS "{validator_type}"), :validator_parameter) RETURNING id',
                ),
                {
                    "name": name,
                    "description": description,
                    "type": attribute_type,
                    "default_value": default_value,
                    "validator": "NONE",
                    "validator_parameter": validator_parameter,
                },
            ).scalar_one()
            for index, value in enumerate(constants):
                connection.execute(
                    sa.text(
                        'INSERT INTO attribute_enum ("index", value, description, imported, attribute_id) '
                        "VALUES (:index, :value, '', false, :attribute_id)",
                    ),
                    {"index": index, "value": value, "attribute_id": found},
                )
        ids[name] = found
    for generic_type, generic_name in GENERIC_ATTRIBUTES.items():
        # The first attribute of the type, preferring one without a validator; for CVE and CWE it
        # is the one holding the imported dictionary (Attribute.find_by_type).
        found = connection.execute(
            sa.text(
                f'SELECT id FROM attribute WHERE type = CAST(:type AS "{type_name}") '  # noqa: S608
                "ORDER BY CASE WHEN validator IS NULL OR CAST(validator AS text) = 'NONE' THEN 0 ELSE 1 END, id LIMIT 1",
            ),
            {"type": generic_type},
        ).scalar()
        if found is None:
            found = connection.execute(
                sa.text(
                    "INSERT INTO attribute (name, description, type, validator) "  # noqa: S608
                    f'VALUES (:name, :name, CAST(:type AS "{type_name}"), CAST(:validator AS "{validator_type}")) RETURNING id',
                ),
                {"name": generic_name, "type": generic_type, "validator": "NONE"},
            ).scalar_one()
        ids[generic_type] = found
    return ids


def _seed_cvd_type(connection: Connection) -> None:
    if connection.execute(sa.text("SELECT 1 FROM report_item_type WHERE system_key = :key"), {"key": CVD_TYPE_KEY}).scalar() is not None:
        return
    attribute_ids = _attribute_ids(connection)
    type_id = connection.execute(
        sa.text(
            "INSERT INTO report_item_type (title, description, icon, languages, label_language, translations, system_key, enabled) "
            # Switched off until an administrator switches it on: not every Taranis publishes CVD Reports.
            "VALUES (:title, :description, :icon, '[]', 'en', '{}', :key, false) RETURNING id",
        ),
        {"title": CVD_TYPE_TITLE, "description": CVD_TYPE_DESCRIPTION, "icon": CVD_TYPE_ICON, "key": CVD_TYPE_KEY},
    ).scalar_one()
    for group_index, (group_title, fields) in enumerate(GROUPS):
        group_id = connection.execute(
            sa.text(
                'INSERT INTO attribute_group (title, description, section, section_title, "index", report_item_type_id, translations) '
                "VALUES (:title, '', NULL, NULL, :index, :type_id, '{}') RETURNING id",
            ),
            {"title": group_title, "index": group_index, "type_id": type_id},
        ).scalar_one()
        for item_index, (title, attribute, minimum, maximum, description) in enumerate(fields):
            connection.execute(
                sa.text(
                    'INSERT INTO attribute_group_item (title, description, "index", min_occurrence, max_occurrence, '
                    "attribute_group_id, attribute_id, translate, translations) "
                    "VALUES (:title, :description, :index, :minimum, :maximum, :group_id, :attribute_id, false, '{}')",
                ),
                {
                    "title": title,
                    "description": description,
                    "index": item_index,
                    "minimum": minimum,
                    "maximum": maximum,
                    "group_id": group_id,
                    "attribute_id": attribute_ids[attribute],
                },
            )


def _seed_gcve_preset(connection: Connection) -> None:
    if connection.execute(sa.text("SELECT 1 FROM product_preset WHERE system_key = :key"), {"key": GCVE_PRESET_KEY}).scalar() is not None:
        return
    name = GCVE_PRESET_NAME
    # The name is unique: one of this name made by hand keeps it.
    if connection.execute(sa.text("SELECT 1 FROM product_preset WHERE lower(name) = lower(:name)"), {"name": name}).scalar() is not None:
        name = f"{GCVE_PRESET_NAME} (GCVE)"
    connection.execute(
        sa.text(
            "INSERT INTO product_preset (name, description, icon, public_web_enabled, system_key, enabled, created, updated_at, updated_by) "
            # Switched off until an administrator switches it on.
            "VALUES (:name, :description, :icon, true, :key, false, :now, :now, 'system-migration')",
        ),
        # The columns are naive local time, as the model writes them.
        {"name": name, "description": GCVE_PRESET_DESCRIPTION, "icon": GCVE_PRESET_ICON, "key": GCVE_PRESET_KEY, "now": datetime.now()},  # noqa: DTZ005
    )


def upgrade() -> None:
    """Add the attribute types, the lock columns, the identifier and GNA tables, the report's organization, the setting and the seeds."""
    _add_attribute_types()
    # A new transaction starts here, so the committed labels may now be used.
    connection = op.get_bind()
    _add_lock_columns(connection)
    _create_tables(connection)
    _add_report_organization(connection)
    _add_settings(connection)
    _seed_cvd_type(connection)
    _seed_gcve_preset(connection)


def downgrade() -> None:
    """Remove the GCVE pieces, unless identifiers were allocated (they must never be given again).

    Raises:
        RuntimeError: When ``gcve_assignment`` holds identifiers, or CVD Reports or GCVE Advisories exist.
    """
    connection = op.get_bind()
    tables = _tables(connection)
    if "gcve_assignment" in tables and connection.execute(sa.text("SELECT 1 FROM gcve_assignment LIMIT 1")).scalar() is not None:
        msg = "GCVE identifiers have been allocated; dropping them would let a number be given again (GCVE-BCP-06)"
        raise RuntimeError(msg)
    in_use = connection.execute(
        sa.text(
            "SELECT 1 FROM report_item r JOIN report_item_type t ON t.id = r.report_item_type_id WHERE t.system_key = :key "
            "UNION ALL SELECT 1 FROM product p JOIN product_preset s ON s.id = p.product_preset_id WHERE s.system_key = :preset LIMIT 1",
        ),
        {"key": CVD_TYPE_KEY, "preset": GCVE_PRESET_KEY},
    ).scalar()
    if in_use is not None:
        msg = "CVD Reports or GCVE Advisories exist; delete them before downgrading"
        raise RuntimeError(msg)

    connection.execute(sa.text("DELETE FROM product_preset WHERE system_key = :key"), {"key": GCVE_PRESET_KEY})
    connection.execute(sa.text("DELETE FROM report_item_type WHERE system_key = :key"), {"key": CVD_TYPE_KEY})
    names = [attribute[0] for attribute in ATTRIBUTES]
    connection.execute(
        sa.text(
            "DELETE FROM attribute WHERE name = ANY(:names) AND NOT EXISTS "
            "(SELECT 1 FROM attribute_group_item i WHERE i.attribute_id = attribute.id)",
        ),
        {"names": names},
    )
    connection.execute(sa.text("DELETE FROM settings WHERE key = ANY(:keys)"), {"keys": [setting[0] for setting in SETTINGS]})
    if "ix_report_item_organization_id" in _indexes(connection, "report_item"):
        op.drop_index("ix_report_item_organization_id", table_name="report_item")
    if "organization_id" in _columns(connection, "report_item"):
        op.drop_column("report_item", "organization_id")
    for table in ("organization_gna", "gcve_assignment", "gcve_counter"):
        if table in tables:
            op.drop_table(table)
    for table in LOCKED_TABLES:
        columns = _columns(connection, table)
        if "system_key" in columns:
            op.drop_constraint(f"{table}_system_key_key", table, type_="unique")
            op.drop_column(table, "system_key")
        if "enabled" in columns:
            op.drop_column(table, "enabled")
