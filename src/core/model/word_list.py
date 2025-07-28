"""Word list model."""

import sqlalchemy
from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_
from sqlalchemy.sql.expression import cast

from managers.db_manager import db
from model.acl_entry import ACLEntry
from shared.schema.acl_entry import ItemType
from shared.schema.word_list import WordListCategorySchema, WordListEntrySchema, WordListSchema, WordListPresentationSchema


class NewWordListEntrySchema(WordListEntrySchema):
    """New Word List Entry schema."""

    @post_load
    def make(self, data, **kwargs):
        """Return a new WordListEntry object.

        Args:
            data (dict): Data to create a new WordListEntry object.
        Returns:
            WordListEntry: New WordListEntry object.
        """
        return WordListEntry(**data)


class NewWordListCategorySchema(WordListCategorySchema):
    """New Word List Category schema.

    Attributes:
        entries (list): List of entries
    """

    entries = fields.Nested(NewWordListEntrySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Return a new WordListCategory object.

        Args:
            data (dict): Data to create a new WordListCategory object.
        Returns:
            WordListCategory: New WordListCategory object.
        """
        return WordListCategory(**data)


class NewWordListSchema(WordListSchema):
    """New Word List schema.

    Attributes:
        categories (list): List of categories.
    """

    categories = fields.Nested(NewWordListCategorySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Return a new WordList object.

        Args:
            data (dict): Data to create a new WordList object.
        Returns:
            WordList: New WordList object.
        """
        return WordList(**data)


class WordList(db.Model):
    """Word list model.

    Attributes:
        id (int): Word list ID.
        name (str): Word list name.
        description (str): Word list description.
        use_for_stop_words (bool): Use for stop words.
        categories (list): List of categories.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    use_for_stop_words = db.Column(db.Boolean, default=False)

    categories = db.relationship("WordListCategory", cascade="all, delete-orphan", lazy="joined")

    def __init__(self, id, name, description, categories, use_for_stop_words):
        """Initialize a new WordList object."""
        self.id = None
        self.name = name
        if description is None:
            self.description = ""
        else:
            self.description = description
        self.categories = categories
        self.use_for_stop_words = use_for_stop_words
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-format-list-bulleted-square"

        self.categories.sort(key=WordListCategory.sort)

    @classmethod
    def find(cls, id):
        """Find a word list by ID.

        Args:
            id (int): Word list ID.
        Returns:
            WordList: Word list object.
        """
        return db.session.get(cls, id)

    @classmethod
    def allowed_with_acl(cls, word_list_id, user, see, access, modify):
        """Check if the user is allowed to access the word list.

        Args:
            word_list_id (int): Word list ID.
            user (User): User object.
            see (bool): See permission.
            access (bool): Access permission.
            modify (bool): Modify permission.
        Returns:
            bool: True if the user is allowed to access the word list, False otherwise.
        """
        query = db.session.query(WordList.id).distinct().group_by(WordList.id).filter(WordList.id == word_list_id)

        query = query.outerjoin(
            ACLEntry, and_(cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.WORD_LIST)
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_all(cls):
        """Get all word lists.

        Returns:
            list: List of word lists.
        """
        return cls.query.order_by(db.asc(WordList.name)).all()

    @classmethod
    def get(cls, search, user, acl_check):
        """Get word lists.

        Args:
            search (str): Search string.
            user (User): User object.
            acl_check (bool): ACL check.
        Returns:
            tuple: Tuple containing a list of word lists and the count.
        """
        query = cls.query.distinct().group_by(WordList.id)

        if acl_check is True:
            query = query.outerjoin(
                ACLEntry, and_(cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.WORD_LIST)
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(WordList.name.ilike(search_string), WordList.description.ilike(search_string)))

        return query.order_by(db.asc(WordList.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        """Get all word lists in JSON format.

        Args:
            search (str): Search string.
            user (User): User object.
            acl_check (bool): ACL check.
        Returns:
            dict: Dictionary containing the total count and a list of word lists.
        """
        word_lists, count = cls.get(search, user, acl_check)
        schema = WordListPresentationSchema(many=True)
        return {"total_count": count, "items": schema.dump(word_lists)}

    @classmethod
    def add_new(cls, data):
        """Add a new word list.

        Args:
            data (dict): Data to create a new word list.
        """
        schema = NewWordListSchema()
        word_list = schema.load(data)
        db.session.add(word_list)
        db.session.commit()

    @classmethod
    def update(cls, word_list_id, data):
        """Update a word list.

        Args:
            word_list_id (int): Word list ID.
            data (dict): Data to update the word list.
        """
        schema = NewWordListSchema()
        updated_word_list = schema.load(data)
        word_list = db.session.get(cls, word_list_id)
        word_list.name = updated_word_list.name
        word_list.description = updated_word_list.description
        word_list.use_for_stop_words = updated_word_list.use_for_stop_words
        word_list.categories = updated_word_list.categories
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete a word list.

        Args:
            id (int): Word list ID.
        """
        word_list = db.session.get(cls, id)
        db.session.delete(word_list)
        db.session.commit()

    @classmethod
    def add_word_list_category(cls, id, category):
        """Add a new word list category.

        Args:
            id (int): Word list ID.
            category (dict): Category data.
        """
        word_list = cls.find(id)

        category_schema = NewWordListCategorySchema()
        category = category_schema.load(category)

        word_list.categories.append(category)
        db.session.commit()


class WordListCategory(db.Model):
    """Word list category model.

    Attributes:
        id (int): Category ID.
        name (str): Category name.
        description (str): Category description.
        link (str): Category link.
        entries (list): List of entries.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    link = db.Column(db.String(), nullable=True, default=None)

    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id"))

    entries = db.relationship("WordListEntry", cascade="all, delete-orphan", lazy="joined")

    def __init__(self, name=None, description=None, link=None, entries=None):
        """Initialize a new WordListCategory object."""
        self.id = None
        if name in (None, ""):
            raise Exception("Empty category name!")
        self.name = name
        if description is None:
            self.description = ""
        else:
            self.description = description
        self.link = link
        self.entries = entries

    @staticmethod
    def sort(category):
        """Sort categories.

        Args:
            category (WordListCategory): Word list category object.
        Returns:
            str: Category name.
        """
        return category.name

    @classmethod
    def find(cls, id, name):
        """Find a word list category.

        Args:
            id (int): Word list ID.
            name (str): Category name.
        Returns:
            WordListCategory: Word list category object.
        """
        return cls.query.filter_by(word_list_id=id).filter_by(name=name).scalar()

    @classmethod
    def get_categories(cls, id):
        """Get categories.

        Args:
            id (int): Word list ID.
        Returns:
            list: List of categories.
        """
        categories = cls.query.filter_by(word_list_id=id).all()
        word_list_categories_schema = NewWordListCategorySchema(many=True)
        return word_list_categories_schema.dump(categories)


class WordListEntry(db.Model):
    """Word list entry model.

    Attributes:
        id (int): Entry ID.
        value (str): Entry value.
        description (str): Entry description.
        word_list_category_id (int): Word list category ID.
    """

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)

    word_list_category_id = db.Column(db.Integer, db.ForeignKey("word_list_category.id"))

    def __init__(self, value, description):
        """Initialize a new WordListEntry object."""
        self.id = None
        self.value = value
        if description is None:
            self.description = ""
        else:
            self.description = description

    @classmethod
    def identical(cls, value, word_list_category_id):
        """Check if the entry is identical.

        Args:
            value (str): Entry value.
            word_list_category_id (int): Word list category ID.
        Returns:
            bool: True if the entry is identical, False otherwise.
        """
        return db.session.query(
            db.exists().where(WordListEntry.value == value).where(WordListEntry.word_list_category_id == word_list_category_id)
        ).scalar()

    @classmethod
    def delete_entries(cls, id, name):
        """Delete entries.

        Args:
            id (int): Word list ID.
            name (str): Category name.
        """
        word_list_category = WordListCategory.find(id, name)
        cls.query.filter_by(word_list_category_id=word_list_category.id).delete()
        db.session.commit()

    @classmethod
    def update_word_list_entries(cls, id, name, entries):
        """Update word list entries.

        Args:
            id (int): Word list ID.
            name (str): Category name.
            entries (list): List of entries.
        """
        word_list_category = WordListCategory.find(id, name)

        entries_schema = NewWordListEntrySchema(many=True)
        entries = entries_schema.load(entries)

        for entry in entries:
            if not WordListEntry.identical(entry.value, word_list_category.id):
                word_list_category.entries.append(entry)
                db.session.commit()

    @classmethod
    def stopwords_subquery(cls):
        """Get stop words subquery.

        Returns:
            sqlalchemy.sql.selectable.Select: Stop words subquery.
        """
        return (
            db.session.query(func.lower(WordListEntry.value))
            .distinct()
            .group_by(WordListEntry.value)
            .join(WordListCategory, WordListCategory.id == WordListEntry.word_list_category_id)
            .join(WordList, WordList.id == WordListCategory.word_list_id)
            .filter(WordList.use_for_stop_words is True)
            .scalar_subquery()
        )
