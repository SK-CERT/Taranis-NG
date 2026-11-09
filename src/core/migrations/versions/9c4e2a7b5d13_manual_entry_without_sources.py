"""News items entered by hand go into a group; manual OSINT sources and the manual collector go.

An item typed in Assess used to need a "manual" OSINT source (of the MANUAL_COLLECTOR) in every
group it should land in. Now the user picks the group, and the item has no source:

- ``news_item_data`` gets ``entered_by`` (the name of who entered it; set = entered by hand),
  ``entered_by_user_id`` (their account, NULL once deleted) and ``source_label`` (the name of the
  manual source an item entered before this revision came from).
- Items of manual sources keep their aggregates, so they stay in the groups they are in; an
  aggregate without a group moves to the default group. Each gets ``source_label`` = its source's
  name and ``entered_by`` = its author (what the GUI filled in: the user's name), with the
  account when exactly one user has that name. Then their source is cleared.
- The manual sources go, with their parameter values and ACL entries (and their places in groups,
  word lists and remote accesses, by cascade), and so do the manual collectors with their
  parameters and ACL entries. Core no longer defines the collector type, so regenerating the
  parameters after the migrations would try to delete them anyway.

The columns may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models.

Downgrade drops the columns. The deleted sources and collectors are not restored: create a
manual collector's source again by hand if you go back.

Revision ID: 9c4e2a7b5d13
Revises: 7d3b9e5f1a2c
Create Date: 2026-11-08 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c4e2a7b5d13"
down_revision = "7d3b9e5f1a2c"
branch_labels = None
depends_on = None

TABLE = "news_item_data"
USER_FK = "fk_news_item_data_entered_by_user_id_user"

MANUAL_COLLECTORS = "SELECT id FROM collector WHERE type = 'MANUAL_COLLECTOR'"
MANUAL_SOURCES = f"SELECT id FROM osint_source WHERE collector_id IN ({MANUAL_COLLECTORS})"  # noqa: S608


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def _foreign_keys() -> set[str]:
    return {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys(TABLE)}


def upgrade() -> None:
    """Add the columns, move the manual sources' items onto them, delete the sources and collectors."""
    columns = _columns()
    if "entered_by" not in columns:
        op.add_column(TABLE, sa.Column("entered_by", sa.String(), nullable=True))
    if "entered_by_user_id" not in columns:
        op.add_column(TABLE, sa.Column("entered_by_user_id", sa.Integer(), nullable=True))
    if "source_label" not in columns:
        op.add_column(TABLE, sa.Column("source_label", sa.String(), nullable=True))
    if not any(fk for fk in sa.inspect(op.get_bind()).get_foreign_keys(TABLE) if fk["constrained_columns"] == ["entered_by_user_id"]):
        op.create_foreign_key(USER_FK, TABLE, "user", ["entered_by_user_id"], ["id"], ondelete="SET NULL")

    bind = op.get_bind()

    # The items: who entered them, and where they came from.
    bind.execute(
        sa.text(
            f"""
            UPDATE news_item_data AS d
            SET source_label = s.name,
                entered_by = COALESCE(btrim(d.author), ''),
                entered_by_user_id = (
                    SELECT min(u.id) FROM "user" AS u WHERE u.name = d.author HAVING count(*) = 1
                )
            FROM osint_source AS s
            WHERE s.id = d.osint_source_id AND s.id IN ({MANUAL_SOURCES})
            """,  # noqa: S608
        ),
    )
    # They stay in their groups; one whose group is gone goes to the default group.
    bind.execute(
        sa.text(
            f"""
            UPDATE news_item_aggregate AS a
            SET osint_source_group_id = (SELECT id FROM osint_source_group WHERE "default" IS TRUE ORDER BY id LIMIT 1)
            WHERE a.osint_source_group_id IS NULL
              AND EXISTS (
                SELECT 1 FROM news_item AS n JOIN news_item_data AS d ON d.id = n.news_item_data_id
                WHERE n.news_item_aggregate_id = a.id AND d.osint_source_id IN ({MANUAL_SOURCES})
              )
            """,  # noqa: S608
        ),
    )
    bind.execute(sa.text(f"UPDATE news_item_data SET osint_source_id = NULL WHERE osint_source_id IN ({MANUAL_SOURCES})"))  # noqa: S608

    # The ACL entries of the sources and collectors (acl_entry_role does not cascade).
    acl_entries = f"""
        SELECT id FROM acl_entry
        WHERE (item_type = 'OSINT_SOURCE' AND item_id IN ({MANUAL_SOURCES}))
           OR (item_type = 'COLLECTOR' AND item_id IN ({MANUAL_COLLECTORS}))
    """  # noqa: S608
    bind.execute(sa.text(f"DELETE FROM acl_entry_role WHERE acl_entry_id IN ({acl_entries})"))  # noqa: S608
    bind.execute(sa.text(f"DELETE FROM acl_entry_user WHERE acl_entry_id IN ({acl_entries})"))  # noqa: S608
    bind.execute(sa.text(f"DELETE FROM acl_entry WHERE id IN ({acl_entries})"))  # noqa: S608

    # The sources, with their parameter values (only the link to them cascades).
    bind.execute(
        sa.text(
            f"""
            DELETE FROM parameter_value WHERE id IN (
                SELECT parameter_value_id FROM osint_source_parameter_value WHERE osint_source_id IN ({MANUAL_SOURCES})
            )
            """,  # noqa: S608
        ),
    )
    bind.execute(sa.text(f"DELETE FROM osint_source WHERE id IN ({MANUAL_SOURCES})"))  # noqa: S608

    # The collectors, with their parameters (deleting a parameter takes its links and values).
    bind.execute(
        sa.text(
            f"""
            DELETE FROM parameter WHERE id IN (
                SELECT parameter_id FROM collector_parameter WHERE collector_id IN ({MANUAL_COLLECTORS})
            )
            """,  # noqa: S608
        ),
    )
    bind.execute(sa.text("DELETE FROM collector WHERE type = 'MANUAL_COLLECTOR'"))


def downgrade() -> None:
    """Drop the columns; the deleted sources and collectors are not restored."""
    if USER_FK in _foreign_keys():
        op.drop_constraint(USER_FK, TABLE, type_="foreignkey")
    columns = _columns()
    for column in ("source_label", "entered_by_user_id", "entered_by"):
        if column in columns:
            op.drop_column(TABLE, column)
