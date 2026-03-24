"""add cascade states enabled setting.

Revision ID: d2b016063dc7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-24 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d2b016063dc7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


class SettingS(Base):
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
        setting = session.query(SettingS).filter_by(key=key).first()
        if not setting:
            session.add(SettingS(key, set_type, value, description, is_global, options))


def upgrade() -> None:
    """Add CASCADE_STATES_ENABLED setting."""
    bind = op.get_bind()
    session = Session(bind=bind)

    SettingS.add(
        session,
        key="CASCADE_STATES_ENABLED",
        set_type="B",
        value="true",
        description="Automatic cascade state changes",
        is_global=True,
        options="",
    )

    session.commit()
    print("Setting CASCADE_STATES_ENABLED added...", flush=True)  # noqa: T201


def downgrade() -> None:
    """Remove CASCADE_STATES_ENABLED setting."""
    bind = op.get_bind()
    session = Session(bind=bind)

    setting = session.query(SettingS).filter_by(key="CASCADE_STATES_ENABLED").first()
    if setting:
        session.delete(setting)
        session.commit()
        print("Setting CASCADE_STATES_ENABLED removed...", flush=True)  # noqa: T201
