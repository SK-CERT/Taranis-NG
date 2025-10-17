"""enable colors in tag cloud.

Revision ID: a07f4e5b5943
Revises: f7cb2a18ff73
Create Date: 2025-10-17 09:23:05.230345

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "a07f4e5b5943"
down_revision = "f7cb2a18ff73"
branch_labels = None
depends_on = None


class SettingS3(Base):
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
        setting = session.query(SettingS3).filter_by(key=key).first()
        if not setting:
            session.add(SettingS3(key, set_type, value, description, is_global, options))

    @staticmethod
    def delete(session: Session, key: str) -> None:
        """Delete setting if exists."""
        record = session.query(SettingS3).filter_by(key=key).first()
        if record:
            session.delete(record)


def upgrade() -> None:
    """Add new user setting."""
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS3.add(session, "TAG_COLOR", "B", "false", "Colorful tag cloud", is_global=False, options="")
    session.commit()


def downgrade() -> None:
    """Remove setting."""
    conn = op.get_bind()
    session = Session(bind=conn)
    SettingS3.delete(session, "TAG_COLOR")
    session.commit()
