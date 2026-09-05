"""add ui theme user setting.

Revision ID: b8e4d1c37a92
Revises: c4a9f2e17b38
Create Date: 2026-09-05 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "b8e4d1c37a92"
down_revision = "c4a9f2e17b38"
branch_labels = None
depends_on = None


class SettingS6(Base):
    """Settings table."""

    __tablename__ = "settings"
    id = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.String(40), unique=True, nullable=False)
    type = sa.Column(sa.String(1), nullable=False)
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
        setting = session.query(SettingS6).filter_by(key=key).first()
        if not setting:
            session.add(SettingS6(key, set_type, value, description, is_global, options))

    @staticmethod
    def delete(session: Session, key: str) -> None:
        """Delete setting if exists."""
        record = session.query(SettingS6).filter_by(key=key).first()
        if record:
            session.delete(record)


def upgrade() -> None:
    """Add new user setting selecting the GUI theme family.

    The light/dark variant stays controlled by DARK_THEME; this setting only
    picks which family that variant belongs to. `options` is deliberately left
    empty - the GUI owns the list of available themes (same arrangement as
    UI_LANGUAGE), so shipping a new theme needs no migration.
    """
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS6.add(session, "UI_THEME", "S", "taranis", "User interface theme", is_global=False, options="")
    session.commit()


def downgrade() -> None:
    """Remove the UI theme setting."""
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS6.delete(session, "UI_THEME")
    session.commit()
