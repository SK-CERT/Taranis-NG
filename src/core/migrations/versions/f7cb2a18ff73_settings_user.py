"""add settings_user table.

Revision ID: f7cb2a18ff73
Revises: 146979f5f4c2
Create Date: 2025-09-29 14:18:16.589131

"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "f7cb2a18ff73"
down_revision = "146979f5f4c2"
branch_labels = None
depends_on = None


class SettingS2(Base):
    """Settings table."""

    __tablename__ = "settings"
    id = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.String(40), unique=True, nullable=False)
    type = sa.Column(sa.String(1), unique=True, nullable=False)
    value = sa.Column(sa.String(), nullable=False)
    default_val = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    is_global = sa.Column(sa.Boolean(), nullable=False)
    options = sa.Column(sa.String(), nullable=False)
    updated_by = sa.Column(sa.String(), nullable=True)

    def __init__(self, key: str, set_type: str, value: str, description: str, is_global: bool, options: str) -> None:
        """Initialize setting."""
        self.id = None
        self.key = key
        self.type = set_type
        self.value = value
        self.default_val = value
        self.description = description
        self.is_global = is_global
        self.options = options
        self.updated_by = "system-migration"

    @staticmethod
    def add(session: Session, key: str, set_type: str, value: str, description: str, is_global: bool, options: str) -> None:
        """Add setting if not exists."""
        setting = session.query(SettingS2).filter_by(key=key).first()
        if not setting:
            session.add(SettingS2(key, set_type, value, description, is_global, options))


def upgrade() -> None:
    """Create settings_user table."""
    conn = op.get_bind()
    session = Session(bind=conn)

    inspector = inspect(conn)
    if "settings_user" in inspector.get_table_names():
        return

    op.create_table(
        "settings_user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("settings_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["settings_id"], ["settings.id"], ondelete="CASCADE"),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=True, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id", name="settings_user_pkey"),
        sa.UniqueConstraint("settings_id", "user_id", name="settings_user_settings_id_user_id_uniq"),
    )

    op.add_column("settings", sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))
    op.add_column("settings", sa.Column("options", sa.String()))
    op.alter_column("settings", "updated_at", existing_type=postgresql.TIMESTAMP(), nullable=True, server_default=sa.func.current_timestamp())

    SettingS2.add(session, "SPELLCHECK", "B", "true", "Spellcheck", is_global=False, options="")
    SettingS2.add(session, "DARK_THEME", "B", "false", "Dark theme", is_global=False, options="")
    options = [
        {"id": "en", "txt": "English"},
        {"id": "cs", "txt": "Czech"},
        {"id": "sk", "txt": "Slovak"},
    ]
    SettingS2.add(session, "LANGUAGE", "S", "en", "Language", is_global=False, options=json.dumps(options))
    SettingS2.add(session, "NEWS_SHOW_LINK", "B", "true", "Show source link in news items", is_global=False, options="")

    session.commit()

    # Migrate user_profile_word_list -> user_word_list
    if "user_word_list" in inspector.get_table_names():
        return

    op.create_table(
        "user_word_list",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_list_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_user_word_list_user"),
        sa.ForeignKeyConstraint(["word_list_id"], ["word_list.id"], name="fk_user_word_list_word_list"),
        sa.PrimaryKeyConstraint("user_id", "word_list_id", name="user_word_list_pkey"),
    )
    if "user_profile_word_list" in inspector.get_table_names():
        conn.execute(
            sa.text(
                """
                INSERT INTO user_word_list (user_id, word_list_id)
                SELECT "user".id, uwl.word_list_id FROM "user"
                JOIN user_profile up ON up.id = "user".profile_id
                JOIN user_profile_word_list uwl ON uwl.user_profile_id = up.id
                 """,
            ),
        )
        op.drop_table("user_profile_word_list")
        op.drop_table("user_profile")

    columns = [column["name"] for column in inspector.get_columns("user")]
    if "profile_id" in columns:
        op.drop_column("user", "profile_id")


def downgrade() -> None:
    """Delete settings_user table."""
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    op.drop_table("settings_user")
    op.drop_table("user_word_list")
    op.drop_column("settings", "is_global")
    op.drop_column("settings", "options")

    session.commit()
