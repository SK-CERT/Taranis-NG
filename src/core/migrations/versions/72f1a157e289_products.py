"""Product formats, publishing channels and product presets.

A product is the content (title, description, reports). This revision names what publishes it,
and lets one product be published in several languages, formats and channels:

- a product type is a **product format** (a presenter and its template: PDF, HTML, a message,
  JSON), and a publisher preset a **publishing channel** (where a rendered product goes: SFTP,
  e-mail, Mastodon);
- a **product preset** bundles them: deliveries, each a language (none: the one the product is
  written in), a format and a channel (none: previewed, never sent), plus an icon, whether its
  products appear on the public web and on which webs (none listed: every web). A product picks
  a product preset instead of a product type.

This revision:

1. Adds ``PRODUCT_PRESET`` to the ACL item type enum. Postgres refuses to use a label in the
   transaction that added it, so this runs first, in an autocommit block; the enum's real name
   is read from the catalog (see ``c7a1b4e9d203``). ``PRODUCT_TYPE`` stays: Postgres cannot drop
   an enum label, and the downgrade uses it.
2. Renames ``product_type`` and ``publisher_preset`` and their parameter value tables, with the
   columns, id sequences and constraints named after them, so they are named as Postgres names
   them for new tables. Empty tables with the new names that a core started on the new code
   already made (``db.create_all()``) are dropped first.
3. Creates ``product_preset``, ``product_preset_delivery`` and ``product_preset_public_web``.
4. Creates one product preset per product format: same title and description, one delivery of
   that format without a channel, and the public web on for every web. Core served every
   published product to every web, so the feeds stay as they were. Which presets products were
   sent to was never recorded, so an admin assigns the channels.
5. Points each product at its format's product preset (``product.product_preset_id``) and drops
   ``product.product_type_id``; products without a type get a product preset of their own. A
   product keeps the webs it is limited to (``product_public_web``), and can now be kept off the
   public web (``product.public_web_enabled``, on for every existing product).
6. Rewrites ``PRODUCT_TYPE`` ACL entries to ``PRODUCT_PRESET`` entries of the mapped preset.
7. Renames the ``CONFIG_PRODUCT_TYPE_*`` and ``CONFIG_PUBLISHER_PRESET_*`` permissions, for every
   role and user holding them, and grants ``CONFIG_PRODUCT_PRESET_*`` wherever the product type
   ones were.
8. Gives report item types an icon (``report_item_type.icon``; none shows the default one).
9. Indexes attribute constants by attribute. The table holds the CPE and CVE dictionaries, over
   a million rows, and every load of an attribute scanned them all: about a quarter of a second
   for each product the public web asked for, and for each report opened in Analyze.

Columns and indexes that a core started on the new code already made are kept. The helpers are
self-contained SQL, so this conversion stays as written whatever later happens to the models.

Revision ID: 72f1a157e289
Revises: c580a8db010f
Create Date: 2026-11-04 12:00:00.000000

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "72f1a157e289"
down_revision = "c580a8db010f"
branch_labels = None
depends_on = None

logger = logging.getLogger(f"alembic.{revision}")

PRODUCT_PRESET_ITEM = "PRODUCT_PRESET"
PRODUCT_TYPE_ITEM = "PRODUCT_TYPE"
UNTYPED_NAME = "Products without a type"
ACTIONS = ("ACCESS", "CREATE", "UPDATE", "DELETE")
# old word -> new word, with the tables named after the old one and the words the permission
# names use.
RENAMES = (
    ("product_type", "product_format", ("product_type", "product_type_parameter_value"), ("product type", "product format")),
    (
        "publisher_preset",
        "publishing_channel",
        ("publisher_preset", "publisher_preset_parameter_value"),
        ("publisher preset", "publishing channel"),
    ),
)
PRESET_TABLES = ("product_preset", "product_preset_delivery", "product_preset_public_web")
DELIVERY_CONSTRAINT = "uq_product_preset_delivery"
ICON_LENGTH = 50
ENUM_INDEX = "ix_attribute_enum_attribute_id_index"


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


# -- renaming -----------------------------------------------------------------


def _words(upgrade: bool) -> list[tuple[str, str]]:
    """The renames, as (from, to) for the direction asked."""
    return [(old, new) if upgrade else (new, old) for old, new, _tables, _names in RENAMES]


def _rename(name: str, words: list[tuple[str, str]]) -> str:
    for old, new in words:
        name = name.replace(old, new)
    return name


def _renamed_tables(upgrade: bool) -> list[str]:
    """The tables to rename, by their current names."""
    tables = [table for _old, _new, names, _words in RENAMES for table in names]
    return tables if upgrade else [_rename(table, _words(upgrade=True)) for table in tables]


def _drop_premature_tables(connection: Connection) -> None:
    """Drop the tables with the new names that create_all() made before this revision ran.

    They are dropped in one statement, as they may reference each other. One that holds rows
    stops the migration: its rows would have to be merged by hand.
    """
    tables = _tables(connection)
    words = _words(upgrade=True)
    premature = [_rename(table, words) for table in _renamed_tables(upgrade=True) if table in tables and _rename(table, words) in tables]
    premature += [table for table in PRESET_TABLES if table in tables]
    for table in premature:
        if connection.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one():  # noqa: S608
            message = f"{table} holds rows before the migration that makes it ran; merge them by hand before migrating"
            raise RuntimeError(message)
    if premature:
        logger.info("Dropping %s, made empty by a core before this migration ran", ", ".join(premature))
        op.execute("DROP TABLE " + ", ".join(f'"{table}"' for table in premature))


def _rename_schema(connection: Connection, upgrade: bool) -> None:
    """Rename the tables, then the columns, id sequences and constraints named after them."""
    words = _words(upgrade)
    present = _tables(connection)
    for table in _renamed_tables(upgrade):
        if table in present:
            op.rename_table(table, _rename(table, words))

    involved = [_rename(table, words) for table in _renamed_tables(upgrade)]
    inspector = sa.inspect(connection)
    for table in involved:
        for column in inspector.get_columns(table):
            new_name = _rename(column["name"], words)
            if new_name != column["name"]:
                op.alter_column(table, column["name"], new_column_name=new_name)

    # The sequences the tables' columns own (serial or identity).
    sequences = connection.execute(
        sa.text(
            "SELECT s.relname FROM pg_class s "
            "JOIN pg_depend d ON d.objid = s.oid AND d.deptype IN ('a', 'i') "
            "JOIN pg_class t ON t.oid = d.refobjid "
            "WHERE s.relkind = 'S' AND t.relnamespace = current_schema()::regnamespace AND t.relname IN :tables ORDER BY 1",
        ).bindparams(sa.bindparam("tables", expanding=True)),
        {"tables": involved},
    ).scalars()
    for name in list(sequences):
        if _rename(name, words) != name:
            op.execute(f'ALTER SEQUENCE "{name}" RENAME TO "{_rename(name, words)}"')

    # Renaming a primary key or unique constraint renames its index too.
    constraints = connection.execute(
        sa.text(
            "SELECT t.relname, c.conname FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid "
            "WHERE t.relnamespace = current_schema()::regnamespace AND t.relname IN :tables ORDER BY 1, 2",
        ).bindparams(sa.bindparam("tables", expanding=True)),
        {"tables": involved},
    ).all()
    for table, constraint in constraints:
        if _rename(constraint, words) != constraint:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{constraint}" TO "{_rename(constraint, words)}"')


# -- permissions --------------------------------------------------------------


def _permission_names(action: str, singular: str) -> tuple[str, str]:
    plural = f"{singular}s"
    if action == "ACCESS":
        return f"Config {plural} access", f"Access to {plural} configuration"
    return f"Config {singular} {action.lower()}", f"{action.capitalize()} {singular} configuration"


def _grant(connection: Connection, permission_id: str, words: str, source_id: str) -> None:
    """Add a permission and grant it to every role and user holding ``source_id``."""
    name, description = _permission_names(permission_id.rsplit("_", 1)[1], words)
    connection.execute(
        sa.text("INSERT INTO permission (id, name, description) VALUES (:id, :name, :description) ON CONFLICT (id) DO NOTHING"),
        {"id": permission_id, "name": name, "description": description},
    )
    for table, owner in (("role_permission", "role_id"), ("user_permission", "user_id")):
        connection.execute(
            sa.text(
                f"INSERT INTO {table} ({owner}, permission_id) "  # noqa: S608
                f"SELECT {owner}, :permission_id FROM {table} WHERE permission_id = :source_id "
                f"ON CONFLICT ({owner}, permission_id) DO NOTHING",
            ),
            {"permission_id": permission_id, "source_id": source_id},
        )


def _drop_permission(connection: Connection, permission_id: str) -> None:
    for table, column in (("role_permission", "permission_id"), ("user_permission", "permission_id"), ("permission", "id")):
        connection.execute(sa.text(f"DELETE FROM {table} WHERE {column} = :id"), {"id": permission_id})  # noqa: S608


def _rename_permissions(connection: Connection, upgrade: bool) -> None:
    """Move every renamed ``CONFIG_*`` permission, and who holds it, to its new id."""
    for old, new, _tables, (old_words, new_words) in RENAMES:
        source, target = (old, new) if upgrade else (new, old)
        for action in ACTIONS:
            source_id = f"CONFIG_{source.upper()}_{action}"
            _grant(connection, f"CONFIG_{target.upper()}_{action}", new_words if upgrade else old_words, source_id)
            _drop_permission(connection, source_id)


# -- product presets ----------------------------------------------------------


def _create_preset_tables() -> None:
    op.create_table(
        "product_preset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("icon", sa.String(length=ICON_LENGTH), nullable=True),
        sa.Column("public_web_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "product_preset_delivery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_preset_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("product_format_id", sa.Integer(), nullable=False),
        sa.Column("publishing_channel_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["product_preset_id"], ["product_preset.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_format_id"], ["product_format.id"]),
        sa.ForeignKeyConstraint(["publishing_channel_id"], ["publishing_channel.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_preset_id",
            "language",
            "product_format_id",
            "publishing_channel_id",
            name=DELIVERY_CONSTRAINT,
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "product_preset_public_web",
        sa.Column("product_preset_id", sa.Integer(), nullable=False),
        sa.Column("public_web_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_preset_id"], ["product_preset.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["public_web_id"], ["public_web.id"]),
        sa.PrimaryKeyConstraint("product_preset_id", "public_web_id"),
    )


def _free_name(connection: Connection, name: str, suffix: str) -> str:
    """The name, or the name with a suffix when a product preset (case-insensitively) has it."""
    candidate = name
    counter = 1
    while connection.execute(
        sa.text("SELECT 1 FROM product_preset WHERE lower(name) = lower(:name)"),
        {"name": candidate},
    ).scalar():
        candidate = f"{name} ({suffix})" if counter == 1 else f"{name} ({suffix} {counter})"
        counter += 1
    return candidate


def _add_preset(connection: Connection, name: str, description: str | None) -> int:
    return connection.execute(
        sa.text(
            "INSERT INTO product_preset (name, description, public_web_enabled, created, updated_at, updated_by) "
            "VALUES (:name, :description, true, now(), now(), 'migration') RETURNING id",
        ),
        {"name": name, "description": description or ""},
    ).scalar_one()


def _presets_for_formats(connection: Connection) -> dict[int, int]:
    """Create a product preset for each product format; returns format id -> product preset id."""
    mapping = {}
    formats = connection.execute(sa.text("SELECT id, title, description FROM product_format ORDER BY id")).all()
    for format_id, title, description in formats:
        name = _free_name(connection, (title or "").strip() or f"Product type {format_id}", f"type {format_id}")
        preset_id = _add_preset(connection, name, description)
        connection.execute(
            sa.text(
                "INSERT INTO product_preset_delivery (product_preset_id, position, product_format_id) VALUES (:preset_id, 0, :format_id)",
            ),
            {"preset_id": preset_id, "format_id": format_id},
        )
        mapping[format_id] = preset_id
    return mapping


def _point_products_at_presets(connection: Connection, mapping: dict[int, int]) -> None:
    """Give every product its format's product preset, then drop the product type column."""
    op.add_column("product", sa.Column("product_preset_id", sa.Integer(), nullable=True))
    for format_id, preset_id in mapping.items():
        connection.execute(
            sa.text("UPDATE product SET product_preset_id = :preset_id WHERE product_type_id = :format_id"),
            {"preset_id": preset_id, "format_id": format_id},
        )
    untyped = connection.execute(sa.text("SELECT count(*) FROM product WHERE product_preset_id IS NULL")).scalar_one()
    if untyped:
        # No format: these can be listed and shown on the public web, but not rendered.
        preset_id = _add_preset(connection, _free_name(connection, UNTYPED_NAME, "migration"), "")
        connection.execute(
            sa.text("UPDATE product SET product_preset_id = :preset_id WHERE product_preset_id IS NULL"),
            {"preset_id": preset_id},
        )
        logger.warning("%d products had no product type; they now use the product preset '%s'", untyped, UNTYPED_NAME)

    op.alter_column("product", "product_preset_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("product_product_preset_id_fkey", "product", "product_preset", ["product_preset_id"], ["id"])
    op.drop_column("product", "product_type_id")


def _move_acl_entries(connection: Connection, item_type: str, source: str, target: str, mapping: dict[int, int]) -> None:
    """Point the ``source`` ACL entries at the mapped ``target`` items; drop those that map to none."""
    entries = connection.execute(
        sa.text(f'SELECT id, item_id FROM acl_entry WHERE item_type = CAST(:item AS "{item_type}")'),  # noqa: S608
        {"item": source},
    ).all()
    for entry_id, item_id in entries:
        target_id = mapping.get(int(item_id)) if item_id and item_id.isdigit() else None
        if target_id is None:
            # Nothing to guard any more.
            connection.execute(sa.text("DELETE FROM acl_entry_user WHERE acl_entry_id = :id"), {"id": entry_id})
            connection.execute(sa.text("DELETE FROM acl_entry_role WHERE acl_entry_id = :id"), {"id": entry_id})
            connection.execute(sa.text("DELETE FROM acl_entry WHERE id = :id"), {"id": entry_id})
            continue
        connection.execute(
            sa.text(f'UPDATE acl_entry SET item_type = CAST(:item AS "{item_type}"), item_id = :item_id WHERE id = :id'),  # noqa: S608
            {"item": target, "item_id": str(target_id), "id": entry_id},
        )


# -- columns and indexes of their own -----------------------------------------


def _add_column(connection: Connection, table: str, column: sa.Column) -> None:
    if column.name not in _columns(connection, table):
        op.add_column(table, column)


def _ensure_product_public_web(connection: Connection) -> None:
    """The webs a product is limited to; an older database may lack the table."""
    if "product_public_web" not in _tables(connection):
        op.create_table(
            "product_public_web",
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("public_web_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["public_web_id"], ["public_web.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("product_id", "public_web_id"),
        )


def _index_attribute_enums(connection: Connection) -> None:
    if ENUM_INDEX not in {index["name"] for index in sa.inspect(connection).get_indexes("attribute_enum")}:
        op.create_index(ENUM_INDEX, "attribute_enum", ["attribute_id", "index"])


def upgrade() -> None:
    """Publish products through product presets of product formats and publishing channels."""
    item_type = _enum_type_name(op.get_bind(), "acl_entry", "item_type")
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE \"{item_type}\" ADD VALUE IF NOT EXISTS '{PRODUCT_PRESET_ITEM}'")

    # A new transaction starts here, so the committed label may now be used.
    connection = op.get_bind()
    _drop_premature_tables(connection)
    _rename_schema(connection, upgrade=True)
    _create_preset_tables()
    mapping = _presets_for_formats(connection)
    _point_products_at_presets(connection, mapping)
    _move_acl_entries(connection, item_type, PRODUCT_TYPE_ITEM, PRODUCT_PRESET_ITEM, mapping)
    _rename_permissions(connection, upgrade=True)
    for action in ACTIONS:
        _grant(connection, f"CONFIG_PRODUCT_PRESET_{action}", "product preset", f"CONFIG_PRODUCT_FORMAT_{action}")

    _ensure_product_public_web(connection)
    _add_column(connection, "product", sa.Column("public_web_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column(connection, "report_item_type", sa.Column("icon", sa.String(length=ICON_LENGTH), nullable=True))
    _index_attribute_enums(connection)


def downgrade() -> None:
    """Give each product the first format of its product preset again, and drop product presets.

    What a product type cannot express is lost: the channels, the languages, the formats after
    the first, the icons, whether a product preset is on the public web, and that a product is
    kept off it. A product preset's webs narrow the webs of each of its products, or become them
    for a product without any. An ACL entry of a product preset without a format is dropped.
    """
    connection = op.get_bind()
    item_type = _enum_type_name(connection, "acl_entry", "item_type")
    first_format = (
        "SELECT DISTINCT ON (product_preset_id) product_preset_id, product_format_id "
        "FROM product_preset_delivery ORDER BY product_preset_id, position, id"
    )

    op.drop_index(ENUM_INDEX, table_name="attribute_enum")
    op.drop_column("report_item_type", "icon")
    kept_off = connection.execute(sa.text("SELECT count(*) FROM product WHERE NOT public_web_enabled")).scalar_one()
    if kept_off:
        logger.warning("%d products were kept off the public web; they now appear on their webs", kept_off)
    op.drop_column("product", "public_web_enabled")

    op.add_column("product", sa.Column("product_type_id", sa.Integer(), nullable=True))
    op.create_foreign_key("product_product_type_id_fkey", "product", "product_format", ["product_type_id"], ["id"])
    connection.execute(
        sa.text(
            f"UPDATE product SET product_type_id = first.product_format_id FROM ({first_format}) AS first "  # noqa: S608
            "WHERE first.product_preset_id = product.product_preset_id",
        ),
    )
    connection.execute(
        sa.text(
            "DELETE FROM product_public_web AS own USING product "
            "WHERE product.id = own.product_id "
            "AND EXISTS (SELECT 1 FROM product_preset_public_web AS target WHERE target.product_preset_id = product.product_preset_id) "
            "AND NOT EXISTS (SELECT 1 FROM product_preset_public_web AS target "
            "WHERE target.product_preset_id = product.product_preset_id AND target.public_web_id = own.public_web_id)",
        ),
    )
    connection.execute(
        sa.text(
            "INSERT INTO product_public_web (product_id, public_web_id) "
            "SELECT product.id, target.public_web_id FROM product "
            "JOIN product_preset_public_web AS target ON target.product_preset_id = product.product_preset_id "
            "WHERE NOT EXISTS (SELECT 1 FROM product_public_web AS own WHERE own.product_id = product.id)",
        ),
    )

    formats = dict(connection.execute(sa.text(first_format)).all())
    _move_acl_entries(connection, item_type, PRODUCT_PRESET_ITEM, PRODUCT_TYPE_ITEM, formats)
    for action in ACTIONS:
        _drop_permission(connection, f"CONFIG_PRODUCT_PRESET_{action}")
    _rename_permissions(connection, upgrade=False)

    op.drop_constraint("product_product_preset_id_fkey", "product", type_="foreignkey")
    op.drop_column("product", "product_preset_id")
    for table in reversed(PRESET_TABLES):
        op.drop_table(table)
    _rename_schema(connection, upgrade=False)
    # Postgres cannot drop the PRODUCT_PRESET enum label; no row uses it any more.
