"""Indexes for the queries Assess, Analyze, the dashboard and authentication run on every view.

- ``news_item_aggregate (created, id)`` and ``(osint_source_group_id, created, id)``: Assess lists
  aggregates newest first and pages on by (created, id), in all groups or in one.
- ``news_item_vote (news_item_id)``: the votes of the news items on an Assess page.
- ``report_item_attribute (report_item_id)``: a report's attributes.
- ``report_item_news_item_aggregate (news_item_aggregate_id)``: the reports of an aggregate (the
  primary key leads with the report).
- ``news_item_data (collected)``: the dashboard's latest and per-day counts.
- ``token_blacklist (token)``: checked on every authenticated request.
- ``acl_entry (item_type, item_id)``: every ACL check joins the entries of an item.

All may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh database
with the models' indexes. Downgrade drops them.

Revision ID: 4b8e6d2a9c71
Revises: 9c4e2a7b5d13
Create Date: 2026-11-08 03:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4b8e6d2a9c71"
down_revision = "9c4e2a7b5d13"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_news_item_aggregate_created_id", "news_item_aggregate", ["created", "id"]),
    ("ix_news_item_aggregate_group_created_id", "news_item_aggregate", ["osint_source_group_id", "created", "id"]),
    ("ix_news_item_vote_news_item_id", "news_item_vote", ["news_item_id"]),
    ("ix_report_item_attribute_report_item_id", "report_item_attribute", ["report_item_id"]),
    ("ix_report_item_news_item_aggregate_news_item_aggregate_id", "report_item_news_item_aggregate", ["news_item_aggregate_id"]),
    ("ix_news_item_data_collected", "news_item_data", ["collected"]),
    ("ix_token_blacklist_token", "token_blacklist", ["token"]),
    ("ix_acl_entry_item", "acl_entry", ["item_type", "item_id"]),
)


def upgrade() -> None:
    """Create the indexes that do not exist yet."""
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, if_not_exists=True)


def downgrade() -> None:
    """Drop the indexes."""
    for name, table, _columns in INDEXES:
        op.drop_index(name, table_name=table, if_exists=True)
