"""delete NEWS_SHOW_SOURCE_LINK setting.

Revision ID: fdc6bba17c9b
Revises: 6a7431435320
Create Date: 2025-10-24 19:29:07.532393

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "fdc6bba17c9b"
down_revision = "6a7431435320"
branch_labels = None
depends_on = None


class SettingS3(Base):
    """Settings table."""

    __tablename__ = "settings"
    id = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.String(40), unique=True, nullable=False)


def upgrade() -> None:
    """Delete old NEWS_SHOW_SOURCE_LINK setting."""
    bind = op.get_bind()
    session = Session(bind=bind)

    perm = session.query(SettingS3).filter_by(key="NEWS_SHOW_SOURCE_LINK").first()
    if perm:
        session.delete(perm)
        session.commit()
        print("Setting NEWS_SHOW_SOURCE_LINK deleted...", flush=True)  # noqa: T201


def downgrade() -> None:
    """No need."""
