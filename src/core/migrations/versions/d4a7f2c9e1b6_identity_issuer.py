"""The IdP an identity link is bound to: ``user_auth_identity.issuer``.

A SAML provider in federation mode (eduGAIN, InCommon, eduID.cz, ...) stands for every identity
provider of the federation. Identity links were matched by external id or username alone, so any
IdP of the federation could log in as another institution's user by asserting that user's
identifier. A link now records the IdP entityID that created it and only works through that IdP.

Existing links start without an issuer. In federation mode such a link is bound at its next login
when the scoped username (checked against the IdP's ``<shibmd:Scope>``) equals its username, and
refused otherwise. Other providers only record the issuer.

The column may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models.

Downgrade drops the column.

Revision ID: d4a7f2c9e1b6
Revises: 7a4c1e9b2d36
Create Date: 2026-11-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a7f2c9e1b6"
down_revision = "7a4c1e9b2d36"
branch_labels = None
depends_on = None

TABLE = "user_auth_identity"
COLUMN = "issuer"


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add user_auth_identity.issuer, empty for every existing link."""
    if _has_column():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.String(), nullable=True))


def downgrade() -> None:
    """Drop user_auth_identity.issuer."""
    if _has_column():
        op.drop_column(TABLE, COLUMN)
