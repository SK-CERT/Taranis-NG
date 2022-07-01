"""added default wordlists

Revision ID: 5d6687c91b82
Revises: 38b7aa1e4764
Create Date: 2022-07-01 11:24:12.099521

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
import csv


# revision identifiers, used by Alembic.
revision = '5d6687c91b82'
down_revision = '38b7aa1e4764'
branch_labels = None
depends_on = None

Base = declarative_base()

class WordListREV5d6687c91b82(Base):
    __tablename__ = 'word_list'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    use_for_stop_words = sa.Column(sa.Boolean, default=False)

    def __init__(self, name, description, use_for_stop_words = False):
        self.name = name
        self.description = description
        self.use_for_stop_words = use_for_stop_words


class WordListCategoryREV5d6687c91b82(Base):
    __tablename__ = 'word_list_category'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    word_list_id = sa.Column(sa.Integer, sa.ForeignKey('word_list.id'))

    def __init__(self, name, description, word_list_id):
        self.name = name
        self.description = description
        self.word_list_id = word_list_id

class WordListEntryREV5d6687c91b82(Base):
    __tablename__ = 'word_list_entry'
    id = sa.Column(sa.Integer, primary_key=True)
    value = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    word_list_category_id = sa.Column(sa.Integer, sa.ForeignKey('word_list_category.id'))

    def __init__(self, value, description, word_list_category_id):
        self.value = value
        self.description = description
        self.word_list_category_id = word_list_category_id

def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # English

    en_wordlist = WordListREV5d6687c91b82('Default EN stop list', 'English stop-word list packed with the standard Taranis NG installation.', True)
    session.add(en_wordlist)
    session.commit()

    en_wordlist_category = WordListCategoryREV5d6687c91b82('Default EN stop list', 'Source: https://www.maxqda.de/hilfe-mx20-dictio/stopp-listen', en_wordlist.id)
    session.add(en_wordlist_category)
    session.commit()

    with open('/app/migrations/wordlists/en_complete.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None) # skip headers
        for row in reader:
            session.add(WordListEntryREV5d6687c91b82(row[0], row[1], en_wordlist_category.id))

    session.commit()

    # Slovak

    sk_wordlist = WordListREV5d6687c91b82('Default SK stop list', 'Slovak stop-word list packed with the standard Taranis NG installation.', True)
    session.add(sk_wordlist)
    session.commit()

    sk_wordlist_category = WordListCategoryREV5d6687c91b82('Default SK stop list', 'Source: https://github.com/stopwords-iso/stopwords-sk/blob/master/stopwords-sk.txt', sk_wordlist.id)
    session.add(sk_wordlist_category)
    session.commit()

    with open('/app/migrations/wordlists/sk_complete.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None) # skip headers
        for row in reader:
            session.add(WordListEntryREV5d6687c91b82(row[0], row[1], sk_wordlist_category.id))

    session.commit()

    # Highlighting

    highlighting_wordlist = WordListREV5d6687c91b82('Default highlighting wordlist', 'Default highlighting list packed with the standard Taranis NG installation.', False)
    session.add(highlighting_wordlist)
    session.commit()

    highlighting_wordlist_category = WordListCategoryREV5d6687c91b82('Default highlighting wordlist', 'Sources: https://www.allot.com/100-plus-cybersecurity-terms-definitions/, https://content.teamascend.com/cybersecurity-glossary', highlighting_wordlist.id)
    session.add(highlighting_wordlist_category)
    session.commit()

    with open('/app/migrations/wordlists/highlighting.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader, None) # skip headers
        for row in reader:
            session.add(WordListEntryREV5d6687c91b82(row[0], row[1], highlighting_wordlist_category.id))

    session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    session.query(WordListREV5d6687c91b82).filter_by(name='Default EN stop list').delete()
    session.query(WordListREV5d6687c91b82).filter_by(name='Default SK stop list').delete()
    session.commit()
