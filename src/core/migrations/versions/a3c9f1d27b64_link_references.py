"""Stable link references.

Text used to cite a report's links by position: "[2]" meant the report's second link, so
inserting, moving or deleting a link silently changed what every later citation pointed at.
Links now carry a stable key and text cites that key with a token such as "[#k3f9a2]"; core
renders the tokens to numbers whenever it hands data to presenters or public-web nodes.

This revision converts the existing data, so no positional citations remain:

1. ``product.links`` (jsonb) holds a product's own links ([{"key", "url"}]) that its description
   cites. It must be jsonb rather than json: product queries use SELECT DISTINCT, and Postgres has
   no equality operator for json.
2. A "Link" attribute of type LINK is ensured, and every attribute group item titled "Links"
   that used a STRING or TEXT attribute is switched to it.
3. Every LINK value gets a key (kept in ``value_description``).
4. In report text (STRING, TEXT and RICH_TEXT values, remote report items included), "[n]"
   becomes the token of the report's n-th link.
5. In product descriptions, "[n]" used the product-wide numbering the presenter built: the
   links of the product's vulnerability reports, de-duplicated. It becomes the token of that
   link. A product of vulnerability reports keeps its numbers; in one that mixes report
   types, the links of the other reports are numbered now as well, which can shift later
   numbers (consistently with the product's list of links).

Citations out of range of the links are left as they are. Every step checks what is already
there, so the upgrade can run again: set alembic_version back to e7b2c4a91d53 and restart core.
The helpers here are deliberately self-contained, so that this conversion stays as it was
written whatever later happens to core's own link handling.

Revision ID: a3c9f1d27b64
Revises: e7b2c4a91d53
Create Date: 2026-10-10 12:00:00.000000

"""

from __future__ import annotations

import re
import secrets
import string
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "a3c9f1d27b64"
down_revision = "e7b2c4a91d53"
branch_labels = None
depends_on = None

LINK_TYPE = "LINK"
LINK_ATTRIBUTE_NAME = "Link"
LINK_ATTRIBUTE_DESCRIPTION = "Source link; text attributes of the report can cite it"
# What the "Links" group items used before; the downgrade switches them back to it.
TEXT_ATTRIBUTE_NAME = "Text"
LINKS_TITLE_KEY = "links"
CONVERTED_TYPES = ("STRING", "TEXT")
CITING_TYPES = ("STRING", "TEXT", "RICH_TEXT")
VULNERABILITY_TYPE_PREFIX = "Vulnerability Report"

KEY_ALPHABET = string.ascii_lowercase + string.digits
KEY_LENGTH = 6
KEY_RE = re.compile(r"[a-z0-9]{4,12}")
POSITIONAL_RE = re.compile(r"\[(\d+)\]")
TOKEN_RE = re.compile(r"\[#([a-z0-9]{4,12})\]")


def new_key(taken: set[str]) -> str:
    """Return a random link key that is not in ``taken``, and add it there."""
    while True:
        key = "".join(secrets.choice(KEY_ALPHABET) for _ in range(KEY_LENGTH))
        if key not in taken:
            taken.add(key)
            return key


def tokens_from_positions(text: str | None, keys: Sequence[str]) -> str | None:
    """Replace each positional "[n]" with the token of ``keys[n - 1]``; out-of-range ones stay."""
    if not text or not keys:
        return text

    def replace(match: re.Match) -> str:
        position = int(match.group(1))
        return f"[#{keys[position - 1]}]" if 1 <= position <= len(keys) else match.group(0)

    return POSITIONAL_RE.sub(replace, text)


def positions_from_tokens(text: str | None, keys: Sequence[str]) -> str | None:
    """Replace each token of a key in ``keys`` with its 1-based position; other tokens stay."""
    if not text or not keys:
        return text
    positions = {}
    for position, key in enumerate(keys, start=1):
        positions.setdefault(key, position)

    def replace(match: re.Match) -> str:
        position = positions.get(match.group(1))
        return f"[{position}]" if position is not None else match.group(0)

    return TOKEN_RE.sub(replace, text)


def legacy_product_keys(reports: Iterable[tuple[str | None, Sequence[tuple[str, str]]]]) -> list[str]:
    """Return the link keys in the order of the old product-wide numbering.

    The presenter numbered the links of the product's vulnerability reports, in report order,
    skipping a link whose value an earlier report already listed.

    Args:
        reports: For every report of the product, in product order, its report type title and
            its ``(key, value)`` links in report order.
    """
    keys: list[str] = []
    values: list[str] = []
    for type_title, links in reports:
        if not (type_title or "").startswith(VULNERABILITY_TYPE_PREFIX):
            continue
        for key, value in links:
            if value not in values:
                values.append(value)
                keys.append(key)
    return keys


def _enum_type_name(connection: Connection, table: str, column: str) -> str:
    """Read the Postgres enum type actually backing a column (see revision c7a1b4e9d203)."""
    return connection.execute(
        sa.text(
            "SELECT t.typname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_type t ON t.oid = a.atttypid "
            "WHERE c.relname = :table AND a.attname = :column AND a.attnum > 0 AND NOT a.attisdropped",
        ),
        {"table": table, "column": column},
    ).scalar_one()


def _add_product_links(connection: Connection) -> None:
    """Add product.links as jsonb.

    A core started with the new model may have created the column already. An earlier draft of
    this revision created it as json, which breaks every SELECT DISTINCT over products; such a
    column is converted.
    """
    data_type = connection.execute(
        sa.text("SELECT data_type FROM information_schema.columns WHERE table_name = 'product' AND column_name = 'links'"),
    ).scalar()
    if data_type is None:
        op.add_column("product", sa.Column("links", JSONB(), nullable=False, server_default=sa.text("'[]'")))
    elif data_type != "jsonb":
        op.execute("ALTER TABLE product ALTER COLUMN links DROP DEFAULT")
        op.execute("ALTER TABLE product ALTER COLUMN links TYPE jsonb USING links::jsonb")
        op.execute("ALTER TABLE product ALTER COLUMN links SET DEFAULT '[]'::jsonb")


def _link_attribute_id(connection: Connection) -> int:
    """Return the id of a LINK attribute, creating the "Link" attribute when there is none."""
    existing = connection.execute(
        sa.text("SELECT id FROM attribute WHERE type::text = :type ORDER BY id LIMIT 1"),
        {"type": LINK_TYPE},
    ).scalar()
    if existing is not None:
        return existing

    type_name = _enum_type_name(connection, "attribute", "type")
    validator_type = _enum_type_name(connection, "attribute", "validator")
    # The interpolated names come from pg_catalog, not from user input; enum type names
    # cannot be bound as parameters.
    return connection.execute(
        sa.text(
            "INSERT INTO attribute (name, description, type, default_value, validator, validator_parameter) "  # noqa: S608
            f'VALUES (:name, :description, CAST(:type AS "{type_name}"), NULL, CAST(:validator AS "{validator_type}"), NULL) '
            "RETURNING id",
        ),
        {"name": LINK_ATTRIBUTE_NAME, "description": LINK_ATTRIBUTE_DESCRIPTION, "type": LINK_TYPE, "validator": "NONE"},
    ).scalar_one()


def _switch_links_items(connection: Connection, attribute_id: int, from_types: Sequence[str]) -> None:
    """Point the group items titled "Links" whose attribute has one of ``from_types`` at ``attribute_id``."""
    connection.execute(
        sa.text(
            "UPDATE attribute_group_item SET attribute_id = :attribute_id FROM attribute "
            "WHERE attribute.id = attribute_group_item.attribute_id "
            "AND lower(replace(attribute_group_item.title, ' ', '_')) = :title_key "
            "AND attribute.type::text IN :types",
        ).bindparams(sa.bindparam("types", expanding=True)),
        {"attribute_id": attribute_id, "title_key": LINKS_TITLE_KEY, "types": list(from_types)},
    )


def _report_values(connection: Connection) -> list[sa.RowMapping]:
    """Return the link and citing values of all report items.

    Ordered per report item as the report shows them: by attribute group, group item and id.
    """
    return (
        connection.execute(
            sa.text(
                "SELECT ria.id, ria.report_item_id, ria.value, ria.value_description, a.type::text AS type "
                "FROM report_item_attribute ria "
                "JOIN attribute_group_item agi ON agi.id = ria.attribute_group_item_id "
                "JOIN attribute_group ag ON ag.id = agi.attribute_group_id "
                "JOIN attribute a ON a.id = agi.attribute_id "
                "WHERE ria.report_item_id IS NOT NULL AND a.type::text IN :types "
                "ORDER BY ria.report_item_id, ag.index, agi.index, ria.id",
            ).bindparams(sa.bindparam("types", expanding=True)),
            {"types": [LINK_TYPE, *CITING_TYPES]},
        )
        .mappings()
        .all()
    )


def _link_keys_by_report(rows: Iterable[sa.RowMapping]) -> dict[int, list[tuple[int, str | None, str]]]:
    """Group the LINK values by report item as (attribute id, key, value), in report order."""
    links: dict[int, list[tuple[int, str | None, str]]] = {}
    for row in rows:
        if row["type"] == LINK_TYPE:
            links.setdefault(row["report_item_id"], []).append((row["id"], row["value_description"], row["value"] or ""))
    return links


def _key_report_links(connection: Connection, links: dict[int, list[tuple[int, str | None, str]]]) -> None:
    """Give every LINK value a key; ``links`` is updated to hold the keys."""
    updates = []
    for report_item_id, values in links.items():
        taken = {key for _, key, _ in values if key and KEY_RE.fullmatch(key)}
        seen: set[str] = set()
        keyed = []
        for attribute_id, key, value in values:
            if not key or not KEY_RE.fullmatch(key) or key in seen:
                key = new_key(taken)  # noqa: PLW2901 - the replacement is what gets stored
                updates.append({"id": attribute_id, "key": key})
            seen.add(key)
            keyed.append((attribute_id, key, value))
        links[report_item_id] = keyed
    if updates:
        connection.execute(sa.text("UPDATE report_item_attribute SET value_description = :key WHERE id = :id"), updates)


def _rewrite_report_text(connection: Connection, rows: Iterable[sa.RowMapping], links: dict, convert) -> None:  # noqa: ANN001
    """Apply ``convert(text, keys)`` to every citing value whose report item has links."""
    updates = []
    for row in rows:
        if row["type"] not in CITING_TYPES:
            continue
        keys = [key for _, key, _ in links.get(row["report_item_id"], [])]
        converted = convert(row["value"], keys)
        if converted != row["value"]:
            updates.append({"id": row["id"], "value": converted})
    if updates:
        connection.execute(sa.text("UPDATE report_item_attribute SET value = :value WHERE id = :id"), updates)


def _rewrite_product_descriptions(connection: Connection, links: dict, pattern: str, convert) -> None:  # noqa: ANN001
    """Apply ``convert(description, keys)`` to every product description matching ``pattern``.

    ``keys`` are the link keys in the order of the old product-wide numbering.
    """
    products = connection.execute(
        sa.text("SELECT id, description FROM product WHERE description ~ :pattern"),
        {"pattern": pattern},
    ).all()
    for product_id, description in products:
        # No ORDER BY, like the product's report_items relationship: the presenter numbered the
        # reports in whatever order that relationship loaded them.
        reports = connection.execute(
            sa.text(
                "SELECT pri.report_item_id, rit.title FROM product_report_item pri "
                "JOIN report_item ri ON ri.id = pri.report_item_id "
                "LEFT JOIN report_item_type rit ON rit.id = ri.report_item_type_id "
                "WHERE pri.product_id = :product_id",
            ),
            {"product_id": product_id},
        ).all()
        keys = legacy_product_keys(
            (type_title, [(key, value) for _, key, value in links.get(report_item_id, [])]) for report_item_id, type_title in reports
        )
        converted = convert(description, keys)
        if converted != description:
            connection.execute(
                sa.text("UPDATE product SET description = :description WHERE id = :id"),
                {"id": product_id, "description": converted},
            )


def upgrade() -> None:
    """Store link keys, give products links, and turn positional citations into key tokens."""
    type_name = _enum_type_name(op.get_bind(), "attribute", "type")
    # LINK has been part of the enum since the early revisions; make sure, outside the
    # transaction, because Postgres refuses to use a label added in the same one.
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE \"{type_name}\" ADD VALUE IF NOT EXISTS '{LINK_TYPE}'")

    connection = op.get_bind()
    _add_product_links(connection)
    _switch_links_items(connection, _link_attribute_id(connection), CONVERTED_TYPES)

    rows = _report_values(connection)
    links = _link_keys_by_report(rows)
    _key_report_links(connection, links)
    _rewrite_report_text(connection, rows, links, tokens_from_positions)
    _rewrite_product_descriptions(connection, links, POSITIONAL_RE.pattern, tokens_from_positions)


def downgrade() -> None:
    """Turn key tokens back into positional citations and drop the product links.

    The keys stay in value_description, where the old code ignores them, and the "Link"
    attribute stays configured. Citations of product links cannot be expressed without
    product.links and are left as tokens.
    """
    connection = op.get_bind()
    rows = _report_values(connection)
    links = _link_keys_by_report(rows)
    _rewrite_report_text(connection, rows, links, positions_from_tokens)
    _rewrite_product_descriptions(connection, links, TOKEN_RE.pattern, positions_from_tokens)

    text_attribute_id = connection.execute(
        sa.text("SELECT id FROM attribute WHERE name = :name AND type::text = 'STRING' ORDER BY id LIMIT 1"),
        {"name": TEXT_ATTRIBUTE_NAME},
    ).scalar()
    if text_attribute_id is not None:
        _switch_links_items(connection, text_attribute_id, (LINK_TYPE,))

    if "links" in {column["name"] for column in sa.inspect(connection).get_columns("product")}:
        op.drop_column("product", "links")
