"""Taranis as a CVE Numbering Authority: the CVE Services account, CVE IDs, the CVE Record preset.

- ``cve_services_account``: an organization's account core calls MITRE's CVE Services with (the
  API key Fernet-encrypted by core); one per organization.
- ``cve_assignment``: every CVE ID reserved through it, its CVD Report, and where its record stands
  (RESERVED, PUBLISHED, REJECTED; out of date; the last error). At most one live ID per report.
- The shipped "CVE Record" product preset (``system_key='cve'``), off the public web, without
  deliveries and switched off until an administrator switches it on: publishing one submits its
  CVD Reports to CVE Services. Seeding is keyed on
  ``system_key``. Its texts are a copy of ``shared.gcve`` as of this revision; a test keeps them equal.
- The CVD Report type's description now names both records it is published as.

Both tables are created only when missing: ``create_app()`` runs ``create_all()`` before the
migrations. The downgrade refuses while CVE IDs were reserved: the CNA owns them, and their
state must not be lost.

Revision ID: 9e4b2d7c1a38
Revises: 6d1f0a9c3e25
Create Date: 2026-11-08 21:00:00.000000

"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "9e4b2d7c1a38"
down_revision = "6d1f0a9c3e25"
branch_labels = None
depends_on = None

CVE_PRESET_KEY = "cve"
CVE_PRESET_NAME = "CVE Record"
CVE_PRESET_DESCRIPTION = "CVD Reports published as CVE records through CVE Services (this organisation as a CNA)"
CVE_PRESET_ICON = "mdi-shield-star-outline"

CVD_TYPE_KEY = "cvd"
CVD_TYPE_DESCRIPTION_BEFORE = "Coordinated Vulnerability Disclosure, published as a GCVE record"
CVD_TYPE_DESCRIPTION = "Coordinated Vulnerability Disclosure, published as a GCVE or a CVE record"


def _tables(connection: Connection) -> set[str]:
    return set(sa.inspect(connection).get_table_names())


def _create_tables(connection: Connection) -> None:
    tables = _tables(connection)
    if "cve_services_account" not in tables:
        op.create_table(
            "cve_services_account",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("environment", sa.String(16), nullable=False),
            sa.Column("short_name", sa.String(64), nullable=False),
            sa.Column("username", sa.String(255), nullable=False),
            sa.Column("api_key", sa.String(), nullable=True),
            sa.Column("org_uuid", sa.String(64), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("organization_id"),
        )
    if "cve_assignment" not in tables:
        op.create_table(
            "cve_assignment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cve_id", sa.String(64), nullable=False),
            sa.Column("report_item_id", sa.Integer(), nullable=True),
            sa.Column("state", sa.String(16), nullable=False),
            sa.Column("rejected_reason", sa.Text(), nullable=True),
            sa.Column("date_reserved", sa.DateTime(timezone=True), nullable=False),
            sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
            sa.Column("date_submitted", sa.DateTime(timezone=True), nullable=True),
            sa.Column("date_changed", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["report_item_id"], ["report_item.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("cve_id"),
            sa.CheckConstraint("state IN ('RESERVED', 'PUBLISHED', 'REJECTED')", name="ck_cve_assignment_state"),
        )
        op.create_index("ix_cve_assignment_report_item_id", "cve_assignment", ["report_item_id"])
        op.create_index(
            "uq_cve_assignment_live_report",
            "cve_assignment",
            ["report_item_id"],
            unique=True,
            postgresql_where=sa.text("state <> 'REJECTED' AND report_item_id IS NOT NULL"),
        )


def _seed_cve_preset(connection: Connection) -> None:
    if connection.execute(sa.text("SELECT 1 FROM product_preset WHERE system_key = :key"), {"key": CVE_PRESET_KEY}).scalar() is not None:
        return
    name = CVE_PRESET_NAME
    # The name is unique: one of this name made by hand keeps it.
    if connection.execute(sa.text("SELECT 1 FROM product_preset WHERE lower(name) = lower(:name)"), {"name": name}).scalar() is not None:
        name = f"{CVE_PRESET_NAME} (CVE)"
    connection.execute(
        sa.text(
            "INSERT INTO product_preset (name, description, icon, public_web_enabled, system_key, enabled, created, updated_at, updated_by) "
            # Off the public web, and switched off until an administrator switches it on.
            "VALUES (:name, :description, :icon, false, :key, false, :now, :now, 'system-migration')",
        ),
        # The columns are naive local time, as the model writes them.
        {"name": name, "description": CVE_PRESET_DESCRIPTION, "icon": CVE_PRESET_ICON, "key": CVE_PRESET_KEY, "now": datetime.now()},  # noqa: DTZ005
    )


def _describe_cvd_type(connection: Connection, before: str, after: str) -> None:
    connection.execute(
        sa.text("UPDATE report_item_type SET description = :after WHERE system_key = :key AND description = :before"),
        {"key": CVD_TYPE_KEY, "before": before, "after": after},
    )


def upgrade() -> None:
    """Add the account and CVE ID tables, the CVE Record preset, and describe the CVD Report type anew."""
    connection = op.get_bind()
    _create_tables(connection)
    _seed_cve_preset(connection)
    _describe_cvd_type(connection, CVD_TYPE_DESCRIPTION_BEFORE, CVD_TYPE_DESCRIPTION)


def downgrade() -> None:
    """Remove the CVE pieces, unless CVE IDs were reserved (the CNA's, whose state must not be lost).

    Raises:
        RuntimeError: When ``cve_assignment`` holds CVE IDs, or CVE Record products exist.
    """
    connection = op.get_bind()
    tables = _tables(connection)
    if "cve_assignment" in tables and connection.execute(sa.text("SELECT 1 FROM cve_assignment LIMIT 1")).scalar() is not None:
        msg = "CVE IDs have been reserved through CVE Services; their state would be lost"
        raise RuntimeError(msg)
    in_use = connection.execute(
        sa.text("SELECT 1 FROM product p JOIN product_preset s ON s.id = p.product_preset_id WHERE s.system_key = :key LIMIT 1"),
        {"key": CVE_PRESET_KEY},
    ).scalar()
    if in_use is not None:
        msg = "CVE Record products exist; delete them before downgrading"
        raise RuntimeError(msg)

    connection.execute(sa.text("DELETE FROM product_preset WHERE system_key = :key"), {"key": CVE_PRESET_KEY})
    _describe_cvd_type(connection, CVD_TYPE_DESCRIPTION, CVD_TYPE_DESCRIPTION_BEFORE)
    if "cve_assignment" in tables:
        op.drop_table("cve_assignment")
    if "cve_services_account" in tables:
        op.drop_table("cve_services_account")
