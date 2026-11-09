"""Report templates of the public web, and its switches.

``public_web_template``: public-web renders every product through a Jinja template. An
administrator can store templates for a product preset (the page, homepage entry and RSS text
of its products) and for a report item type (one item block); anything without one uses the
built-in templates.

``public_web_template_web``: the webs a template applies to; a template that lists none applies
to every web. A product preset or report item type may so have several templates, one per web
or set of webs, so the template targets are not unique.

``public_web_builtin_template``: public-web falls back on built-in templates for a product or
report item without a custom one. An administrator may switch each of those off
(Configuration -> Public Web -> Report templates) to rely on custom templates alone; a
built-in without a row is on.

``public_web_node.enabled``: off, core neither checks nor resets the node, publishes none of
its webs and serves it no products. Every existing node stays on.

All may exist already: ``create_app()`` runs ``db.create_all()``, so a core started with the
new models before this revision ran has created the tables from its models (with the same
columns) - and on a fresh database the node table with its new column. An empty template
table from before product presets (keyed by ``distribution_id``) is dropped and made again,
and unique template targets an earlier version of this branch created are dropped.

Revision ID: 7d3b9e5f1a2c
Revises: 5a9e3c7d1b42
Create Date: 2026-10-10 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7d3b9e5f1a2c"
down_revision = "5a9e3c7d1b42"
branch_labels = None
depends_on = None

TABLE = "public_web_template"
ONE_TARGET = "ck_public_web_template_one_target"
TEMPLATE_TARGETS = ("product_preset_id", "report_item_type_id")
TEMPLATE_WEB_TABLE = "public_web_template_web"
BUILTIN_TABLE = "public_web_builtin_template"
NODE_TABLE = "public_web_node"
NODE_COLUMN = "enabled"


def _tables() -> list[str]:
    return sa.inspect(op.get_bind()).get_table_names()


def _has_node_column() -> bool:
    return NODE_COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(NODE_TABLE)}


def _existing_table_is_current() -> bool:
    """Whether the template table exists as this revision makes it; an empty outdated one is dropped.

    Raises:
        RuntimeError: For an outdated table that holds templates, which cannot be matched to
            product presets.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE not in inspector.get_table_names():
        return False
    if "product_preset_id" in {column["name"] for column in inspector.get_columns(TABLE)}:
        return True
    if bind.execute(sa.select(sa.literal(1)).select_from(sa.table(TABLE)).limit(1)).first() is not None:
        msg = f"{TABLE} holds templates of distributions, which no longer exist; move them aside and run the upgrade again"
        raise RuntimeError(msg)
    op.drop_table(TABLE)
    return False


def _target_unique_constraints() -> list[str]:
    """Unique constraints on a template's product preset or type, which an earlier version created."""
    constraints = sa.inspect(op.get_bind()).get_unique_constraints(TABLE)
    return [
        constraint["name"]
        for constraint in constraints
        if len(constraint["column_names"]) == 1 and constraint["column_names"][0] in TEMPLATE_TARGETS
    ]


def upgrade() -> None:
    """Create the templates, their webs and the switches, unless create_all() already did."""
    if not _existing_table_is_current():
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            # Not unique: a template can be for chosen webs, beside one for every web.
            sa.Column("product_preset_id", sa.Integer(), sa.ForeignKey("product_preset.id", ondelete="CASCADE"), nullable=True),
            sa.Column("report_item_type_id", sa.Integer(), sa.ForeignKey("report_item_type.id", ondelete="CASCADE"), nullable=True),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("require_tlp_clear", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_at", sa.DateTime()),
            sa.Column("updated_by", sa.String()),
            sa.CheckConstraint("(product_preset_id IS NULL) <> (report_item_type_id IS NULL)", name=ONE_TARGET),
        )
    for name in _target_unique_constraints():
        op.drop_constraint(name, TABLE, type_="unique")
    if TEMPLATE_WEB_TABLE not in _tables():
        op.create_table(
            TEMPLATE_WEB_TABLE,
            sa.Column("public_web_template_id", sa.Integer(), sa.ForeignKey(f"{TABLE}.id", ondelete="CASCADE"), primary_key=True),
            # No cascade: a web a template is restricted to cannot be deleted, or the
            # template would silently apply to every web.
            sa.Column("public_web_id", sa.Integer(), sa.ForeignKey("public_web.id"), primary_key=True),
        )
    if BUILTIN_TABLE not in _tables():
        op.create_table(
            BUILTIN_TABLE,
            sa.Column("name", sa.String(), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_at", sa.DateTime()),
            sa.Column("updated_by", sa.String()),
        )
    if not _has_node_column():
        op.add_column(NODE_TABLE, sa.Column(NODE_COLUMN, sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    """Drop it all: the templates, their webs, the switches; every built-in and node is in use again."""
    if _has_node_column():
        op.drop_column(NODE_TABLE, NODE_COLUMN)
    tables = _tables()
    for table in (BUILTIN_TABLE, TEMPLATE_WEB_TABLE, TABLE):
        if table in tables:
            op.drop_table(table)
