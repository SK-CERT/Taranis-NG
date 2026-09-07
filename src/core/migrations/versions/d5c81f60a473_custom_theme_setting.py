"""add custom theme user setting.

Revision ID: d5c81f60a473
Revises: b8e4d1c37a92
Create Date: 2026-09-05 21:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d5c81f60a473"
down_revision = "b8e4d1c37a92"
branch_labels = None
depends_on = None


class SettingS7(Base):
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
        setting = session.query(SettingS7).filter_by(key=key).first()
        if not setting:
            session.add(SettingS7(key, set_type, value, description, is_global, options))

    @staticmethod
    def delete(session: Session, key: str) -> None:
        """Delete setting if exists."""
        record = session.query(SettingS7).filter_by(key=key).first()
        if record:
            session.delete(record)


def upgrade() -> None:
    """Add the per-user custom theme definition.

    Holds the palette authored in the GUI's theme editor, as JSON:
    {"basedOn": <family id>, "light": {<token>: <hex>}, "dark": {...}}.
    Empty until the user saves one. The value column is an unbounded String, so
    the blob (~1.5 kB) fits; the GUI validates every value on read, since
    nothing in this stack validates setting values on the way in.
    """
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS7.add(session, "CUSTOM_THEME", "S", "", "Custom theme definition", is_global=False, options="")
    session.commit()


def downgrade() -> None:
    """Remove the custom theme setting."""
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS7.delete(session, "CUSTOM_THEME")
    session.commit()
