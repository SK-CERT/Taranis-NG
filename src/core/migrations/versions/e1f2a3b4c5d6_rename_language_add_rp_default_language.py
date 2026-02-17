"""Rename LANGUAGE to UI_LANGUAGE and add R_P_DEFAULT_LANGUAGE with ISO 639-1 support.

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-02-17 14:00:00.000000

"""

import json

import pycountry
import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


class SettingS5(Base):
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

    def __init__(
        self,
        key: str,
        set_type: str,
        value: str,
        description: str,
        is_global: bool,
        options: str,
    ) -> None:
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
    def add(
        session: Session,
        key: str,
        set_type: str,
        value: str,
        description: str,
        is_global: bool,
        options: str,
    ) -> None:
        """Add setting if not exists."""
        setting = session.query(SettingS5).filter_by(key=key).first()
        if not setting:
            session.add(SettingS5(key, set_type, value, description, is_global, options))

    @staticmethod
    def delete(session: Session, key: str) -> None:
        """Delete setting if exists."""
        record = session.query(SettingS5).filter_by(key=key).first()
        if record:
            session.delete(record)


def upgrade() -> None:
    """Rename LANGUAGE to UI_LANGUAGE and add R_P_DEFAULT_LANGUAGE setting."""
    conn = op.get_bind()
    session = Session(bind=conn)

    # Step 1: Get the old LANGUAGE setting ID and its details
    language_setting = session.query(SettingS5).filter_by(key="LANGUAGE").first()
    old_language_id = None
    if language_setting:
        old_language_id = language_setting.id
        options = language_setting.options

        # Step 2: Create new UI_LANGUAGE setting
        ui_language_setting = SettingS5(
            "UI_LANGUAGE",
            "S",
            "en",
            "UI Language",
            is_global=False,
            options=options,
        )
        session.add(ui_language_setting)
        session.flush()  # Flush to get the new ID
        new_language_id = ui_language_setting.id

        # Step 3: Migrate settings_user entries from LANGUAGE to UI_LANGUAGE
        # Update all user setting overrides to point to the new UI_LANGUAGE setting
        update_query = (
            sa.update(sa.table("settings_user", sa.column("settings_id")))
            .where(
                sa.column("settings_id") == old_language_id,
            )
            .values(
                settings_id=new_language_id,
            )
        )
        conn.execute(update_query)

        # Step 4: Delete old LANGUAGE setting (now safe as no FK references remain)
        session.delete(language_setting)

    # Step 5: Generate full ISO 639-1 language list with pycountry
    iso_languages = [
        {
            "id": lang.alpha_2,
            "txt": lang.name or lang.alpha_2,
        }
        for lang in pycountry.languages
        if hasattr(lang, "alpha_2")
    ]

    # Sort by language name for better UX
    iso_languages.sort(key=lambda x: x["txt"])

    # Step 6: Add R_P_DEFAULT_LANGUAGE setting with full ISO 639-1 support
    rp_language_options = json.dumps(iso_languages)
    SettingS5.add(
        session,
        "R_P_DEFAULT_LANGUAGE",
        "S",
        "en",
        "Report/Product Default Language",
        is_global=False,
        options=rp_language_options,
    )

    session.commit()


def downgrade() -> None:
    """Revert rename LANGUAGE to UI_LANGUAGE and remove R_P_DEFAULT_LANGUAGE setting."""
    conn = op.get_bind()
    session = Session(bind=conn)

    # Step 1: Get the new UI_LANGUAGE setting and its ID
    ui_language_setting = session.query(SettingS5).filter_by(key="UI_LANGUAGE").first()
    new_language_id = None
    if ui_language_setting:
        new_language_id = ui_language_setting.id
        options = ui_language_setting.options

        # Step 2: Recreate LANGUAGE setting with original options
        language_setting = SettingS5(
            "LANGUAGE",
            "S",
            "en",
            "Language",
            is_global=False,
            options=options,
        )
        session.add(language_setting)
        session.flush()
        old_language_id = language_setting.id

        # Step 3: Migrate settings_user entries back from UI_LANGUAGE to LANGUAGE
        update_query = (
            sa.update(sa.table("settings_user", sa.column("settings_id")))
            .where(
                sa.column("settings_id") == new_language_id,
            )
            .values(
                settings_id=old_language_id,
            )
        )
        conn.execute(update_query)

        # Step 4: Delete UI_LANGUAGE setting
        session.delete(ui_language_setting)

    # Step 5: Delete R_P_DEFAULT_LANGUAGE setting
    SettingS5.delete(session, "R_P_DEFAULT_LANGUAGE")

    session.commit()
