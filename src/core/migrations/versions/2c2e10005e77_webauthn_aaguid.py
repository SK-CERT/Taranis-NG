"""Record the AAGUID of passkeys, and the settings that name their authenticators.

The AAGUID names the authenticator model a passkey lives on (a security key, a password manager,
a platform keychain). It is recorded from now on; passkeys registered earlier keep NULL, since it
can only be read during registration.

Naming the authenticator means downloading a community list from GitHub, so it is a setting an
administrator turns on: PASSKEY_AUTHENTICATOR_LOOKUP starts off, and PASSKEY_AUTHENTICATOR_LIST_URL
starts at the upstream list.

Every step checks what is already there, so the upgrade can run again on a database that already
has it.

Revision ID: 2c2e10005e77
Revises: a3c9f1d27b64
Create Date: 2026-10-14 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2c2e10005e77"
down_revision = "a3c9f1d27b64"
branch_labels = None
depends_on = None

TABLE = "user_webauthn_credential"
COLUMN = "aaguid"

LOOKUP_SETTING = "PASSKEY_AUTHENTICATOR_LOOKUP"
URL_SETTING = "PASSKEY_AUTHENTICATOR_LIST_URL"
DEFAULT_URL = "https://raw.githubusercontent.com/passkeydeveloper/passkey-authenticator-aaguids/main/combined_aaguid.json"
SETTINGS = (
    {
        "key": LOOKUP_SETTING,
        "type": "B",
        "value": "false",
        "default_val": "false",
        "description": "Passkey authenticator AAGUID - use community list",
    },
    {
        "key": URL_SETTING,
        "type": "S",
        "value": DEFAULT_URL,
        "default_val": DEFAULT_URL,
        "description": "Passkey authenticator AAGUID - list URL",
    },
)

settings_table = sa.table(
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


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add user_webauthn_credential.aaguid and the authenticator lookup settings."""
    if not _has_column():
        op.add_column(TABLE, sa.Column(COLUMN, sa.String(36), nullable=True))

    existing = set(op.get_bind().execute(sa.select(settings_table.c.key)).scalars())
    rows = [
        {**setting, "is_global": True, "options": "", "updated_by": "system-migration"}
        for setting in SETTINGS
        if setting["key"] not in existing
    ]
    if rows:
        op.bulk_insert(settings_table, rows)


def downgrade() -> None:
    """Drop the settings and user_webauthn_credential.aaguid."""
    for key in (LOOKUP_SETTING, URL_SETTING):
        op.execute(sa.text("DELETE FROM settings WHERE key = :key").bindparams(key=key))
    if _has_column():
        op.drop_column(TABLE, COLUMN)
