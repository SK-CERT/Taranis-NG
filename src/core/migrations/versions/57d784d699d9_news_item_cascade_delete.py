"""add cascade delete to NEWS_ITEM releated tables

Revision ID: 57d784d699d9
Revises: f0a4860000ff
Create Date: 2024-05-07 10:06:33.066000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57d784d699d9'
down_revision = 'f0a4860000ff'
branch_labels = None
depends_on = None


def upgrade():
    delete_previous()
    # news_item_attribute
    op.create_foreign_key('news_item_data_news_item_attribute_news_item_attribute_id_fkey',  'news_item_data_news_item_attribute',      'news_item_attribute', ['news_item_attribute_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('news_item_aggregate_news_item_attri_news_item_attribute_id_fkey', 'news_item_aggregate_news_item_attribute', 'news_item_attribute', ['news_item_attribute_id'], ['id'], ondelete='CASCADE')
    # news_item_data  -   manual delete in Taranis keeps DATA tree records (to not crawl again?)
    op.create_foreign_key('news_item_data_news_item_attribute_news_item_data_id_fkey', 'news_item_data_news_item_attribute', 'news_item_data', ['news_item_data_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('news_item_news_item_data_id_fkey',                          'news_item',                          'news_item_data', ['news_item_data_id'], ['id'], ondelete='CASCADE')
    # news_item_aggregate
    op.create_foreign_key('news_item_aggregate_news_item_attri_news_item_aggregate_id_fkey', 'news_item_aggregate_news_item_attribute', 'news_item_aggregate', ['news_item_aggregate_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('report_item_news_item_aggregate_news_item_aggregate_id_fkey',     'report_item_news_item_aggregate',         'news_item_aggregate', ['news_item_aggregate_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('news_item_aggregate_search_index_news_item_aggregate_id_fkey',    'news_item_aggregate_search_index',        'news_item_aggregate', ['news_item_aggregate_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('news_item_news_item_aggregate_id_fkey',                           'news_item',                               'news_item_aggregate', ['news_item_aggregate_id'], ['id'], ondelete='CASCADE')
    # news_item
    op.create_foreign_key('news_item_vote_news_item_id_fkey', 'news_item_vote', 'news_item', ['news_item_id'], ['id'], ondelete='CASCADE')

def downgrade():
    delete_previous()
    # news_item_attribute
    op.create_foreign_key('news_item_data_news_item_attribute_news_item_attribute_id_fkey',  'news_item_data_news_item_attribute',      'news_item_attribute', ['news_item_attribute_id'], ['id'])
    op.create_foreign_key('news_item_aggregate_news_item_attri_news_item_attribute_id_fkey', 'news_item_aggregate_news_item_attribute', 'news_item_attribute', ['news_item_attribute_id'], ['id'])
    # news_item_data
    op.create_foreign_key('news_item_data_news_item_attribute_news_item_data_id_fkey', 'news_item_data_news_item_attribute', 'news_item_data', ['news_item_data_id'], ['id'])
    op.create_foreign_key('news_item_news_item_data_id_fkey',                          'news_item',                          'news_item_data', ['news_item_data_id'], ['id'])
    # news_item_aggregate
    op.create_foreign_key('news_item_aggregate_news_item_attri_news_item_aggregate_id_fkey', 'news_item_aggregate_news_item_attribute', 'news_item_aggregate', ['news_item_aggregate_id'], ['id'])
    op.create_foreign_key('report_item_news_item_aggregate_news_item_aggregate_id_fkey',     'report_item_news_item_aggregate',         'news_item_aggregate', ['news_item_aggregate_id'], ['id'])
    op.create_foreign_key('news_item_aggregate_search_index_news_item_aggregate_id_fkey',    'news_item_aggregate_search_index',        'news_item_aggregate', ['news_item_aggregate_id'], ['id'])
    op.create_foreign_key('news_item_news_item_aggregate_id_fkey',                           'news_item',                               'news_item_aggregate', ['news_item_aggregate_id'], ['id'])
    # news_item
    op.create_foreign_key('news_item_vote_news_item_id_fkey', 'news_item_vote', 'news_item', ['news_item_id'], ['id'], ondelete='CASCADE')

def delete_previous():
    print("deleting previous objects...", flush=True)
    # news_item_attribute
    op.drop_constraint('news_item_data_news_item_attribute_news_item_attribute_id_fkey',  'news_item_data_news_item_attribute', type_='foreignkey')
    op.drop_constraint('news_item_aggregate_news_item_attri_news_item_attribute_id_fkey', 'news_item_aggregate_news_item_attribute', type_='foreignkey')
    # news_item_data
    op.drop_constraint('news_item_data_news_item_attribute_news_item_data_id_fkey', 'news_item_data_news_item_attribute', type_='foreignkey')
    op.drop_constraint('news_item_news_item_data_id_fkey',                          'news_item', type_='foreignkey')
    # news_item_aggregate
    op.drop_constraint('news_item_aggregate_news_item_attri_news_item_aggregate_id_fkey', 'news_item_aggregate_news_item_attribute', type_='foreignkey')
    op.drop_constraint('report_item_news_item_aggregate_news_item_aggregate_id_fkey',     'report_item_news_item_aggregate', type_='foreignkey')
    op.drop_constraint('news_item_aggregate_search_index_news_item_aggregate_id_fkey',    'news_item_aggregate_search_index', type_='foreignkey')
    op.drop_constraint('news_item_news_item_aggregate_id_fkey',                           'news_item', type_='foreignkey')
    # news_item
    op.drop_constraint('news_item_vote_news_item_id_fkey', 'news_item_vote', type_='foreignkey')

