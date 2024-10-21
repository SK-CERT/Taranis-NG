"""add cascade delete/null to osint_source_group releated tables

Revision ID: 9de844252cd5
Revises: 90249a322ae1
Create Date: 2024-10-18 14:13:00.653593

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9de844252cd5'
down_revision = '90249a322ae1'
branch_labels = None
depends_on = None


def upgrade():
    delete_previous()

    # news_item_aggregate
    op.create_foreign_key('news_item_aggregate_osint_source_group_id_fkey',             'news_item_aggregate',             'osint_source_group', ['osint_source_group_id'], ['id'], ondelete='SET NULL')
    # remote_node
    op.create_foreign_key('remote_node_osint_source_group_id_fkey',                     'remote_node',                     'osint_source_group', ['osint_source_group_id'], ['id'], ondelete='SET NULL')
    # news_item
    op.create_foreign_key('osint_source_group_osint_source_osint_source_group_id_fkey', 'osint_source_group_osint_source', 'osint_source_group', ['osint_source_group_id'], ['id'], ondelete='CASCADE')

def downgrade():
    delete_previous()
    # news_item_aggregate
    op.create_foreign_key('news_item_aggregate_osint_source_group_id_fkey',             'news_item_aggregate',             'osint_source_group', ['osint_source_group_id'], ['id'])
    # remote_node
    op.create_foreign_key('remote_node_osint_source_group_id_fkey',                     'remote_node',                     'osint_source_group', ['osint_source_group_id'], ['id'])
    # news_item
    op.create_foreign_key('osint_source_group_osint_source_osint_source_group_id_fkey', 'osint_source_group_osint_source', 'osint_source_group', ['osint_source_group_id'], ['id'])

def delete_previous():
    print("deleting previous objects...", flush=True)
    # news_item_aggregate
    op.drop_constraint('news_item_aggregate_osint_source_group_id_fkey',             'news_item_aggregate', type_='foreignkey')
    # remote_node
    op.drop_constraint('remote_node_osint_source_group_id_fkey',                     'remote_node',         type_='foreignkey')
    # news_item
    op.drop_constraint('osint_source_group_osint_source_osint_source_group_id_fkey', 'osint_source_group_osint_source', type_='foreignkey')
