"""regenerate parameters of bots, collectors, presenters, publishers

Revision ID: 92bdc4caa54c
Revises: 7a45ba122177
Create Date: 2025-02-26 15:09:18.757913

"""

# revision identifiers, used by Alembic.
revision = "92bdc4caa54c"
down_revision = "7a45ba122177"
branch_labels = None
depends_on = None


def upgrade():
    """This has been removed because it caused issues with the migration.
    Now the regeneration is done automatically after the migration.
    """
    pass


def downgrade():
    pass
