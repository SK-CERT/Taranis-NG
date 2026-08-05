"""Remove obsolete UI language options metadata.

Revision ID: 6f3a8d9c2e11
Revises: d2b016063dc7
Create Date: 2026-08-05 00:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6f3a8d9c2e11"
down_revision = "d2b016063dc7"
branch_labels = None
depends_on = None


LEGACY_UI_LANGUAGE_OPTIONS = [
    {"id": "en", "txt": "English"},
    {"id": "cs", "txt": "Czech"},
    {"id": "sk", "txt": "Slovak"},
]

settings = sa.table(
    "settings",
    sa.column("key", sa.String()),
    sa.column("options", sa.String()),
)


def upgrade() -> None:
    """Clear the obsolete options only when they match the legacy list."""
    connection = op.get_bind()
    row = connection.execute(
        sa.select(settings.c.options).where(settings.c.key == "UI_LANGUAGE"),
    ).first()
    if row is None:
        return

    stored_options = row[0]
    try:
        parsed_options = json.loads(stored_options)
    except (json.JSONDecodeError, TypeError):
        return

    if parsed_options != LEGACY_UI_LANGUAGE_OPTIONS:
        return

    connection.execute(
        sa.update(settings).where(settings.c.key == "UI_LANGUAGE").where(settings.c.options == stored_options).values(options=None),
    )


def downgrade() -> None:
    """Restore the legacy options only when no options are currently set."""
    connection = op.get_bind()
    connection.execute(
        sa.update(settings)
        .where(settings.c.key == "UI_LANGUAGE")
        .where(settings.c.options.is_(None))
        .values(options=json.dumps(LEGACY_UI_LANGUAGE_OPTIONS)),
    )
