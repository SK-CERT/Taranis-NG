"""Report item type model."""

import sqlalchemy
from managers.db_manager import db
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.ai_provider import AiProvider
from shared.schema.acl_entry import ItemType
from shared.schema.report_item_type import (
    AttributeGroupBaseSchema,
    AttributeGroupItemSchema,
    ReportItemTypeBaseSchema,
    ReportItemTypePresentationSchema,
)
from sqlalchemy import and_, or_, orm
from sqlalchemy.sql.expression import cast


class ReportTypeFieldInUseError(Exception):
    """Raised when report type fields cannot be removed because report items hold their values."""

    def __init__(self, fields_in_use: dict[str, int]) -> None:
        """Record which fields block the change.

        Args:
            fields_in_use (dict[str, int]): Field title -> number of stored values.
        """
        self.fields_in_use = fields_in_use
        detail = ", ".join(f"{title} ({count})" for title, count in sorted(fields_in_use.items()))
        super().__init__(f"Report type fields still hold report item values: {detail}")


class ReportTypeInUseError(Exception):
    """Raised when a report type cannot be deleted because report items are based on it."""

    def __init__(self, report_item_count: int) -> None:
        """Record how many report items block the deletion.

        Args:
            report_item_count (int): Number of report items of this type.
        """
        self.report_item_count = report_item_count
        plural = "" if report_item_count == 1 else "s"
        super().__init__(f"Report type is used by {report_item_count} report item{plural}")


class NewAttributeGroupItemSchema(AttributeGroupItemSchema):
    """New attribute group item schema.

    Attributes:
        attribute_id (int): Attribute id.
    """

    attribute_id = fields.Integer()

    @post_load
    def make_attribute_group_item(self, data: dict, **kwargs) -> "AttributeGroupItem":  # noqa: ANN003, ARG002
        """Make attribute group item.

        Args:
            data (dict): Data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

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
        ai_provider_id (int): Local AI model id.
        ai_provider (AiProvider): Local AI model.
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

    # `id` shadows the builtin, but it is the schema field marshmallow unpacks into this
    # constructor, so renaming it would break deserialization.
    def __init__(
        self,
        id: int | None,  # noqa: A002
        title: str,
        description: str,
        index: int,
        min_occurrence: int,
        max_occurrence: int,
        attribute_id: int,
        ai_provider_id: int | None,
        ai_prompt: str | None,
    ) -> None:
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
    # `id` shadows the builtin; it is part of this classmethod's existing call signature.
    def find(cls, id: int) -> "AttributeGroupItem | None":  # noqa: A002
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
    def make_attribute_group(self, data: dict, **kwargs) -> "AttributeGroup":  # noqa: ANN003, ARG002
        """Make attribute group.

        Args:
            data (dict): Data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

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
        "AttributeGroupItem",
        back_populates="attribute_group",
        cascade="all, delete-orphan",
        lazy="joined",
        order_by=AttributeGroupItem.index,
    )

    # `id` shadows the builtin, but it is the schema field marshmallow unpacks into this
    # constructor, so renaming it would break deserialization.
    def __init__(
        self,
        id: int | None,  # noqa: A002
        title: str,
        description: str,
        section: int | None,
        section_title: str | None,
        index: int,
        attribute_group_items: list["AttributeGroupItem"],
    ) -> None:
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

    def update(self, updated_attribute_group: "AttributeGroup") -> None:
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
    def make_report_item_type(self, data: dict, **kwargs) -> "ReportItemType":  # noqa: ANN003, ARG002
        """Make report item type.

        Args:
            data (dict): Data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

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
        "AttributeGroup",
        back_populates="report_item_type",
        cascade="all, delete-orphan",
        lazy="joined",
        order_by=AttributeGroup.index,
    )

    # `id` shadows the builtin, but it is the schema field marshmallow unpacks into this
    # constructor, so renaming it would break deserialization.
    def __init__(self, id: int | None, title: str, description: str, attribute_groups: list["AttributeGroup"]) -> None:  # noqa: A002, ARG002
        """Initialize report item type."""
        self.id = None
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct."""
        self.subtitle = self.description
        self.tag = "mdi-file-table-outline"

    @classmethod
    # `id` shadows the builtin; it is part of this classmethod's existing call signature.
    def find(cls, id: int) -> "ReportItemType | None":  # noqa: A002
        """Find report item type.

        Args:
            id (int): Id.

        Returns:
            ReportItemType: Report item type.
        """
        return db.session.get(cls, id)

    @classmethod
    def get_all(cls) -> list["ReportItemType"]:
        """Get all report item types.

        Returns:
            list: Report item types.
        """
        return cls.query.order_by(ReportItemType.title).all()

    @classmethod
    def allowed_with_acl(cls, report_item_type_id: int, user: object, see: bool, access: bool, modify: bool) -> bool:
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
            ACLEntry,
            and_(cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get(cls, search: str | None, user: object, acl_check: bool) -> tuple[list["ReportItemType"], int]:
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
            query = ACLEntry.apply_query(query, user, True, False, False)  # noqa: FBT003

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(ReportItemType.title.ilike(search_string), ReportItemType.description.ilike(search_string)))

        return query.order_by(ReportItemType.title).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None, user: object, acl_check: bool) -> dict:
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
    def add_report_item_type(cls, report_item_type_data: dict) -> None:
        """Add report item type.

        Args:
            report_item_type_data (dict): Report item type data.
        """
        report_item_type_schema = NewReportItemTypeSchema()
        report_item_type = report_item_type_schema.load(report_item_type_data)
        db.session.add(report_item_type)
        db.session.commit()

    @staticmethod
    def _refuse_removing_used_fields(report_type: "ReportItemType", updated_report_type: "ReportItemType") -> None:
        """Reject an update that would drop fields report items still hold values for.

        Args:
            report_type (ReportItemType): The stored report type.
            updated_report_type (ReportItemType): The report type as submitted.

        Raises:
            ReportTypeFieldInUseError: If a field being removed still has stored values.
        """
        # Imported here: report_item imports this module, so a module-level import is circular.
        from model.report_item import ReportItemAttribute  # noqa: PLC0415

        # An item kept anywhere in the payload survives, even if it moved to another group.
        submitted_ids = {
            item.id for group in updated_report_type.attribute_groups for item in group.attribute_group_items if item.id is not None
        }
        removed = {
            item.id: item.title
            for group in report_type.attribute_groups
            for item in group.attribute_group_items
            if item.id not in submitted_ids
        }
        if not removed:
            return

        counts = (
            db.session.query(ReportItemAttribute.attribute_group_item_id, sqlalchemy.func.count(ReportItemAttribute.id))
            .filter(ReportItemAttribute.attribute_group_item_id.in_(removed))
            .group_by(ReportItemAttribute.attribute_group_item_id)
            .all()
        )
        fields_in_use = {removed[item_id]: count for item_id, count in counts}
        if fields_in_use:
            raise ReportTypeFieldInUseError(fields_in_use)

    @classmethod
    def update(cls, report_type_id: int, data: dict) -> None:
        """Update report item type.

        Args:
            report_type_id (int): Report type id.
            data (dict): Data.
        """
        schema = NewReportItemTypeSchema()
        updated_report_type = schema.load(data)
        report_type = db.session.get(cls, report_type_id)

        # Dropping a field from a report type deletes its attribute_group_item row, which
        # report_item_attribute still points at (ON DELETE NO ACTION). Left to the flush that
        # surfaces as a raw foreign key violation and the whole edit is lost, so refuse up
        # front and name the fields whose stored values are in the way.
        cls._refuse_removing_used_fields(report_type, updated_report_type)

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
    # `id` shadows the builtin; it is part of this classmethod's existing call signature.
    def delete_report_item_type(cls, id: int) -> None:  # noqa: A002
        """Delete report item type.

        Args:
            id (int): Id.
        """
        # report_item.report_item_type_id is ON DELETE NO ACTION, so deleting a type that
        # reports were written against fails in the flush. Say what is in the way instead.
        from model.report_item import ReportItem  # noqa: PLC0415

        report_item_count = db.session.query(ReportItem).filter(ReportItem.report_item_type_id == id).count()
        if report_item_count:
            raise ReportTypeInUseError(report_item_count)

        report_item_type = db.session.get(cls, id)
        db.session.delete(report_item_type)
        db.session.commit()
