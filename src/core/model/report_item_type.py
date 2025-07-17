"""Report item type model."""

from marshmallow import fields, post_load
from sqlalchemy import orm, func, or_, and_
import sqlalchemy
from sqlalchemy.sql.expression import cast

from managers.db_manager import db
from model.acl_entry import ACLEntry
from model.ai_provider import AiProvider
from shared.schema.acl_entry import ItemType
from shared.schema.report_item_type import (
    AttributeGroupItemSchema,
    AttributeGroupBaseSchema,
    ReportItemTypeBaseSchema,
    ReportItemTypePresentationSchema,
)


class NewAttributeGroupItemSchema(AttributeGroupItemSchema):
    """New attribute group item schema.

    Attributes:
        attribute_id (int): Attribute id.
    """

    attribute_id = fields.Integer()

    @post_load
    def make_attribute_group_item(self, data, **kwargs):
        """Make attribute group item.

        Args:
            data (dict): Data.
        Returns:
            AttributeGroupItem: Attribute group item.
        """
        return AttributeGroupItem(**data)


class AttributeGroupItem(db.Model):
    """Attribute group item model.

    Attributes:
        id (int): Id.
        title (str): Title.
        description (str): Description.
        index (int): Index.
        min_occurrence (int): Min occurrence.
        max_occurrence (int): Max occurrence.
        attribute_group_id (int): Attribute group id.
        attribute_group (AttributeGroup): Attribute group.
        attribute_id (int): Attribute id.
        attribute (Attribute): Attribute.
        ai_provider_id (int): AI provider id.
        ai_provider (AiProvider): AI provider.
        ai_prompt (str): AI prompt.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    index = db.Column(db.Integer)
    min_occurrence = db.Column(db.Integer)
    max_occurrence = db.Column(db.Integer)

    attribute_group_id = db.Column(db.Integer, db.ForeignKey("attribute_group.id"))
    attribute_group = db.relationship("AttributeGroup", back_populates="attribute_group_items", viewonly=True, lazy="joined")

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute", lazy="joined")

    ai_provider_id = db.Column(db.Integer, db.ForeignKey("ai_provider.id"))
    ai_provider = db.relationship(AiProvider, viewonly=True, lazy="joined")
    ai_prompt = db.Column(db.String())

    def __init__(self, id, title, description, index, min_occurrence, max_occurrence, attribute_id, ai_provider_id, ai_prompt):
        """Initialize attribute group item."""
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_id = attribute_id
        self.ai_provider_id = ai_provider_id
        self.ai_prompt = ai_prompt

    @classmethod
    def find(cls, id):
        """Find attribute group item.

        Args:
            id (int): Id.
        Returns:
            AttributeGroupItem: Attribute group item.
        """
        return db.session.get(cls, id)


class NewAttributeGroupSchema(AttributeGroupBaseSchema):
    """New attribute group schema.

    Attributes:
        attribute_group_items (list): Attribute group items.
    """

    attribute_group_items = fields.Nested("NewAttributeGroupItemSchema", many=True)

    @post_load
    def make_attribute_group(self, data, **kwargs):
        """Make attribute group.

        Args:
            data (dict): Data.
        Returns:
            AttributeGroup: Attribute group.
        """
        return AttributeGroup(**data)


class AttributeGroup(db.Model):
    """Attribute group model.

    Attributes:
        id (int): Id.
        title (str): Title.
        description (str): Description.
        section (int): Section.
        section_title (str): Section title.
        index (int): Index.
        report_item_type_id (int): Report item type id.
        report_item_type (ReportItemType): Report item type.
        attribute_group_items (list): Attribute group items.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    section = db.Column(db.Integer)
    section_title = db.Column(db.String())
    index = db.Column(db.Integer)

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"))
    report_item_type = db.relationship("ReportItemType")

    attribute_group_items = db.relationship(
        "AttributeGroupItem", back_populates="attribute_group", cascade="all, delete-orphan", lazy="joined", order_by=AttributeGroupItem.index
    )

    def __init__(self, id, title, description, section, section_title, index, attribute_group_items):
        """Initialize attribute group."""
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items

    def update(self, updated_attribute_group):
        """Update attribute group.

        Args:
            updated_attribute_group (AttributeGroup): Updated attribute group.
        """
        self.title = updated_attribute_group.title
        self.description = updated_attribute_group.description
        self.section = updated_attribute_group.section
        self.section_title = updated_attribute_group.section_title
        self.index = updated_attribute_group.index

        for updated_item in updated_attribute_group.attribute_group_items:
            found = False
            for item in self.attribute_group_items:
                if updated_item.id == item.id:
                    item.title = updated_item.title
                    item.description = updated_item.description
                    item.index = updated_item.index
                    item.min_occurrence = updated_item.min_occurrence
                    item.max_occurrence = updated_item.max_occurrence
                    item.attribute_id = updated_item.attribute_id
                    item.ai_provider_id = updated_item.ai_provider_id
                    item.ai_prompt = updated_item.ai_prompt
                    found = True
                    break

            if found is False:
                updated_item.attribute_group = None
                self.attribute_group_items.append(updated_item)

        for item in self.attribute_group_items[:]:
            found = False
            for updated_item in updated_attribute_group.attribute_group_items:
                if updated_item.id == item.id:
                    found = True
                    break

            if found is False:
                self.attribute_group_items.remove(item)


class NewReportItemTypeSchema(ReportItemTypeBaseSchema):
    """New report item type schema.

    Attributes:
        attribute_groups (list): Attribute groups.
    """

    attribute_groups = fields.Nested("NewAttributeGroupSchema", many=True)

    @post_load
    def make_report_item_type(self, data, **kwargs):
        """Make report item type.

        Args:
            data (dict): Data.
        Returns:
            ReportItemType: Report item type.
        """
        return ReportItemType(**data)


class ReportItemType(db.Model):
    """Report item type model.

    Attributes:
        id (int): Id.
        title (str): Title.
        description (str): Description.
        attribute_groups (list): Attribute groups.
        subtitle (str): Subtitle.
        tag (str): Tag.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    attribute_groups = db.relationship(
        "AttributeGroup", back_populates="report_item_type", cascade="all, delete-orphan", lazy="joined", order_by=AttributeGroup.index
    )

    def __init__(self, id, title, description, attribute_groups):
        """Initialize report item type."""
        self.id = None
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct."""
        self.subtitle = self.description
        self.tag = "mdi-file-table-outline"

    @classmethod
    def find(cls, id):
        """Find report item type.

        Args:
            id (int): Id.
        Returns:
            ReportItemType: Report item type.
        """
        return db.session.get(cls, id)

    @classmethod
    def get_all(cls):
        """Get all report item types.

        Returns:
            list: Report item types.
        """
        return cls.query.order_by(ReportItemType.title).all()

    @classmethod
    def allowed_with_acl(cls, report_item_type_id, user, see, access, modify):
        """Check if user is allowed with acl.

        Args:
            report_item_type_id (int): Report item type id.
            user (User): User.
            see (bool): See.
            access (bool): Access.
            modify (bool): Modify.
        Returns:
            bool: True if allowed, False otherwise.
        """
        query = db.session.query(ReportItemType.id).distinct().group_by(ReportItemType.id).filter(ReportItemType.id == report_item_type_id)

        query = query.outerjoin(
            ACLEntry, and_(cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE)
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get(cls, search, user, acl_check):
        """Get report item types.

        Args:
            search (str): Search.
            user (User): User.
            acl_check (bool): Acl check.
        Returns:
            list: Report item types.
        """
        query = cls.query.distinct().group_by(ReportItemType.id)

        if acl_check is True:
            query = query.outerjoin(
                ACLEntry,
                and_(cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(func.lower(ReportItemType.title).like(search_string), func.lower(ReportItemType.description).like(search_string))
            )

        return query.order_by(ReportItemType.title).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        """Get all report item types in json format.

        Args:
            search (str): Search.
            user (User): User.
            acl_check (bool): Acl check.
        Returns:
            dict: Report item types.
        """
        report_item_types, count = cls.get(search, user, acl_check)

        report_item_type_schema = ReportItemTypePresentationSchema(many=True)
        return {"total_count": count, "items": report_item_type_schema.dump(report_item_types)}

    @classmethod
    def add_report_item_type(cls, report_item_type_data):
        """Add report item type.

        Args:
            report_item_type_data (dict): Report item type data.
        """
        report_item_type_schema = NewReportItemTypeSchema()
        report_item_type = report_item_type_schema.load(report_item_type_data)
        db.session.add(report_item_type)
        db.session.commit()

    @classmethod
    def update(cls, report_type_id, data):
        """Update report item type.

        Args:
            report_type_id (int): Report type id.
            data (dict): Data.
        """
        schema = NewReportItemTypeSchema()
        updated_report_type = schema.load(data)
        report_type = db.session.get(cls, report_type_id)
        report_type.title = updated_report_type.title
        report_type.description = updated_report_type.description

        for updated_attribute_group in updated_report_type.attribute_groups:
            found = False
            for attribute_group in report_type.attribute_groups:
                if updated_attribute_group.id is not None and updated_attribute_group.id == attribute_group.id:
                    attribute_group.update(updated_attribute_group)
                    found = True
                    break

            if found is False:
                updated_attribute_group.report_item_type = None
                report_type.attribute_groups.append(updated_attribute_group)

        for attribute_group in report_type.attribute_groups[:]:
            found = False
            for updated_attribute_group in updated_report_type.attribute_groups:
                if updated_attribute_group.id == attribute_group.id:
                    found = True
                    break

            if found is False:
                report_type.attribute_groups.remove(attribute_group)

        db.session.commit()

    @classmethod
    def delete_report_item_type(cls, id):
        """Delete report item type.

        Args:
            id (int): Id.
        """
        report_item_type = db.session.get(cls, id)
        db.session.delete(report_item_type)
        db.session.commit()
