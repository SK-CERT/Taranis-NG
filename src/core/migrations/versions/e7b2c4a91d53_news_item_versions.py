"""News item versions, lookup indexes and the tag cloud key.

A versioned news item (e.g. a CSAF advisory) keeps one row in news_item_data holding its
newest revision, and the revisions it replaced in the new news_item_data_version table.
Adds the provider's version label and the key shared by every revision to news_item_data.
History entries that only repeat a revision - copies a provider republished under the same
version label, which earlier code stored as revisions - are dropped.

Storing a news item looks up its hash, its news items and its aggregates' search rows; none
of those columns had an index, so each lookup read a whole table. They get one here.

The tag cloud gets one row per day and word, as a unique key: duplicate rows are merged
first. Its retention becomes the TAG_CLOUD_RETENTION_DAYS setting, 7 days as before.

Every step checks what is already there, so the whole upgrade can run again on a database
that already had it: set alembic_version back to d4f1c8a70b62 and restart core.

Applying a migration also regenerates collector parameters (see env.py), which registers the
new CSAF collector on existing collectors nodes.

Revision ID: e7b2c4a91d53
Revises: d4f1c8a70b62
Create Date: 2026-09-25 21:41:19.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7b2c4a91d53"
down_revision = "d4f1c8a70b62"
branch_labels = None
depends_on = None

DATA_TABLE = "news_item_data"
VERSION_TABLE = "news_item_data_version"
VERSION_KEY_INDEX = "ix_news_item_data_version_key"

# Named as the models' index=True names them, so a create_all() database has the same ones.
LOOKUP_INDEXES = (
    ("ix_news_item_data_hash", "news_item_data", "hash"),
    ("ix_news_item_news_item_data_id", "news_item", "news_item_data_id"),
    ("ix_news_item_news_item_aggregate_id", "news_item", "news_item_aggregate_id"),
    ("ix_news_item_aggregate_osint_source_group_id", "news_item_aggregate", "osint_source_group_id"),
    ("ix_news_item_aggregate_search_index_news_item_aggregate_id", "news_item_aggregate_search_index", "news_item_aggregate_id"),
)

TAG_CLOUD_TABLE = "tag_cloud"
TAG_CLOUD_KEY = "uq_tag_cloud_collected_word"
TAG_CLOUD_COLUMNS = ("word", "word_quantity", "collected")
# Longer words are junk the old tokenizer glued together, and too long for a B-tree key.
TAG_CLOUD_MAX_WORD_LENGTH = 100

RETENTION_SETTING = "TAG_CLOUD_RETENTION_DAYS"


def _drop_empty_premature_table() -> bool:
    """Drop the version table if a core started before this migration created it empty.

    `create_app()` runs `db.create_all()`, so a core started with the new model while the
    database was still at the previous revision has already created the table - without the
    ON DELETE CASCADE declared below. An empty one is dropped and recreated, so the result
    matches a clean upgrade. One that holds rows is kept rather than lose them.

    Returns:
        bool: Whether the table still exists.
    """
    bind = op.get_bind()
    if VERSION_TABLE not in sa.inspect(bind).get_table_names():
        return False
    if bind.execute(sa.select(sa.literal(1)).select_from(sa.table(VERSION_TABLE)).limit(1)).first() is None:
        op.drop_table(VERSION_TABLE)
        return False
    return True


def _drop_repeated_revisions() -> None:
    """Drop history entries that only repeat a revision.

    A copy of the stored revision published again under the same version label (Red Hat does so
    every few hours) became an entry of its own, so items gathered many copies of one version.
    Copies of the revision an item still holds go, and of a version kept several times in history
    only the last copy stays. Entries without a version label cannot be told apart and stay.
    """
    op.execute(
        "DELETE FROM news_item_data_version AS copy USING news_item_data AS item "
        "WHERE copy.news_item_data_id = item.id AND copy.version IS NOT NULL AND copy.version = item.version",
    )
    op.execute(
        "DELETE FROM news_item_data_version AS copy USING news_item_data_version AS later "
        "WHERE later.news_item_data_id = copy.news_item_data_id AND later.version = copy.version AND later.id > copy.id",
    )


def _create_lookup_indexes() -> None:
    """Index the columns storing a news item looks up. A column already indexed is left alone."""
    inspector = sa.inspect(op.get_bind())
    for name, table, column in LOOKUP_INDEXES:
        existing = inspector.get_indexes(table)
        if any(index["name"] == name or index["column_names"] == [column] for index in existing):
            continue
        op.create_index(name, table, [column])


def _tag_cloud_one_row_per_word() -> None:
    """Merge duplicate tag cloud rows, then key the table by day and word.

    Nothing stopped two batches inserting the same word on the same day, so a word could have
    several rows; their counts are summed into the oldest. Rows without a word or a day, and
    overlong words, are dropped. A table that already has the key (a database `create_all()`
    built) needs none of this.
    """
    if TAG_CLOUD_KEY in {constraint["name"] for constraint in sa.inspect(op.get_bind()).get_unique_constraints(TAG_CLOUD_TABLE)}:
        return
    op.execute(
        sa.text("DELETE FROM tag_cloud WHERE word IS NULL OR collected IS NULL OR length(word) > :max_length").bindparams(
            max_length=TAG_CLOUD_MAX_WORD_LENGTH,
        ),
    )
    op.execute("UPDATE tag_cloud SET word_quantity = 0 WHERE word_quantity IS NULL")
    op.execute(
        "UPDATE tag_cloud SET word_quantity = totals.quantity "
        "FROM (SELECT min(id) AS id, sum(word_quantity) AS quantity FROM tag_cloud GROUP BY collected, word HAVING count(*) > 1) AS totals "
        "WHERE tag_cloud.id = totals.id",
    )
    op.execute(
        "DELETE FROM tag_cloud USING tag_cloud AS kept "
        "WHERE tag_cloud.collected = kept.collected AND tag_cloud.word = kept.word AND tag_cloud.id > kept.id",
    )
    for column in TAG_CLOUD_COLUMNS:
        op.alter_column(TAG_CLOUD_TABLE, column, nullable=False)
    op.create_unique_constraint(TAG_CLOUD_KEY, TAG_CLOUD_TABLE, ["collected", "word"])


def _add_retention_setting() -> None:
    """Add the tag cloud retention setting, unless it is there: 7 days, what was always kept."""
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("type", sa.String),
        sa.column("value", sa.String),
        sa.column("default_val", sa.String),
        sa.column("description", sa.String),
        sa.column("is_global", sa.Boolean),
        sa.column("options", sa.String),
        sa.column("updated_by", sa.String),
    )
    if op.get_bind().execute(sa.select(settings.c.key).where(settings.c.key == RETENTION_SETTING)).first() is not None:
        return
    op.bulk_insert(
        settings,
        [
            {
                "key": RETENTION_SETTING,
                "type": "I",
                "value": "7",
                "default_val": "7",
                "description": "Tag cloud retention (days)",
                "is_global": True,
                "options": "",
                "updated_by": "system-migration",
            },
        ],
    )


def upgrade() -> None:
    """Add the version columns and table, the lookup indexes, the tag cloud key and its setting."""
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns(DATA_TABLE)}
    # Nullable without a default: Postgres adds these without rewriting the table.
    if "version" not in columns:
        op.add_column(DATA_TABLE, sa.Column("version", sa.String(), nullable=True))
    if "version_key" not in columns:
        op.add_column(DATA_TABLE, sa.Column("version_key", sa.String(), nullable=True))
    if VERSION_KEY_INDEX not in {index["name"] for index in inspector.get_indexes(DATA_TABLE)}:
        # Partial: only versioned items have a key, so the index stays small on the largest table.
        op.create_index(VERSION_KEY_INDEX, DATA_TABLE, ["version_key"], postgresql_where=sa.text("version_key IS NOT NULL"))

    if not _drop_empty_premature_table():
        op.create_table(
            VERSION_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("news_item_data_id", sa.String(length=64), nullable=False),
            sa.Column("hash", sa.String(), nullable=True),
            sa.Column("version", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("review", sa.String(), nullable=True),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("link", sa.String(), nullable=True),
            sa.Column("content", sa.String(), nullable=True),
            sa.Column("published", sa.String(), nullable=True),
            sa.Column("collected", sa.DateTime(), nullable=True),
            sa.Column("superseded", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["news_item_data_id"], [f"{DATA_TABLE}.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_news_item_data_version_news_item_data_id"), VERSION_TABLE, ["news_item_data_id"])
        op.create_index(op.f("ix_news_item_data_version_hash"), VERSION_TABLE, ["hash"])

    _drop_repeated_revisions()
    _create_lookup_indexes()
    _tag_cloud_one_row_per_word()
    _add_retention_setting()


def downgrade() -> None:
    """Drop the setting, the tag cloud key, the lookup indexes, the version table and columns."""
    op.execute(sa.text("DELETE FROM settings WHERE key = :key").bindparams(key=RETENTION_SETTING))
    op.execute(f"ALTER TABLE {TAG_CLOUD_TABLE} DROP CONSTRAINT IF EXISTS {TAG_CLOUD_KEY}")
    for column in TAG_CLOUD_COLUMNS:
        op.alter_column(TAG_CLOUD_TABLE, column, nullable=True)
    for name, _table, _column in LOOKUP_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.drop_table(VERSION_TABLE)
    op.drop_index(VERSION_KEY_INDEX, table_name=DATA_TABLE)
    op.drop_column(DATA_TABLE, "version_key")
    op.drop_column(DATA_TABLE, "version")
