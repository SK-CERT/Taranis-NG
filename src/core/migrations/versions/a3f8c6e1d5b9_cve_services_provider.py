"""The data provider published CVE records are read from: "CVE Services (MITRE)".

A CVD Report can be filled in from an existing CVE's published record (managers.cve_import). The
record is read from the data provider of type ``CVE_SERVICES``, seeded here with MITRE's public CVE
Services API (no account needed for published records); an administrator may point it at a mirror.
Without such a provider core reads MITRE's API all the same, so a database that skipped this
revision still works.

The row is inserted only when no provider of the type exists (``api_type`` is unique), so an
existing one is left as it is. Its texts are a copy of ``shared.gcve`` as of this revision; a
test keeps them equal. Downgrade removes the provider of the type.

Revision ID: a3f8c6e1d5b9
Revises: 9e4b2d7c1a38
Create Date: 2026-11-26 18:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3f8c6e1d5b9"
down_revision = "9e4b2d7c1a38"
branch_labels = None
depends_on = None

API_TYPE = "CVE_SERVICES"
NAME = "CVE Services (MITRE)"
API_URL = "https://cveawg.mitre.org/api/"
WEB_URL = "https://www.cve.org/CVERecord?id="
USER_AGENT = "Taranis-NG (+https://github.com/SK-CERT/Taranis-NG)"

# The type is used twice; PostgreSQL deduces a bare parameter's type from where it stands (text in
# the SELECT list, varchar in the comparison) and refuses the mismatch, so both say varchar.
INSERT = sa.text(
    "INSERT INTO data_provider (name, api_type, api_url, api_key, user_agent, web_url, updated_by, updated_at) "
    "SELECT :name, CAST(:api_type AS VARCHAR), :api_url, '', :user_agent, :web_url, 'system-migration', now() "
    "WHERE NOT EXISTS (SELECT 1 FROM data_provider WHERE api_type = CAST(:api_type AS VARCHAR))",
)
DELETE = sa.text("DELETE FROM data_provider WHERE api_type = :api_type")


def upgrade() -> None:
    """Seed the CVE Services data provider, unless one exists."""
    op.get_bind().execute(INSERT, {"name": NAME, "api_type": API_TYPE, "api_url": API_URL, "user_agent": USER_AGENT, "web_url": WEB_URL})


def downgrade() -> None:
    """Remove the CVE Services data provider."""
    op.get_bind().execute(DELETE, {"api_type": API_TYPE})
