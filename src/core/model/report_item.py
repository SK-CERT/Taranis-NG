"""This module contains the ReportItem class and its associated schema.

The ReportItem class represents a report item, which is a component of a larger report. It contains attributes such as ID, UUID, title,
created timestamp, and more. The class also includes methods for finding report item attributes by ID.

The module also defines several schemas for creating and validating report items and their attributes.

Classes:
    - ReportItem: A class representing a report item.
    - ReportItemAttribute: A class representing an attribute of a report item.
    - ReportItemRemoteReportItem: A class representing the relationship between a report item and a remote report item.

Schemas:
    - NewReportItemSchema: Schema for creating a new report item.
    - NewReportItemAttributeSchema: Schema for creating a new report item attribute.

Relationships:
    - ReportItem has a many-to-one relationship with User and ReportItemType.
    - ReportItem has a many-to-many relationship with NewsItemAggregate and ReportItem.
"""

from datetime import datetime
import uuid as uuid_generator
from sqlalchemy import orm, or_, func, text, and_
from sqlalchemy.sql.expression import cast
import sqlalchemy
from marshmallow import fields, post_load

from managers.db_manager import db
from model.news_item import NewsItemAggregate
from model.report_item_type import AttributeGroupItem
from model.report_item_type import ReportItemType
from model.acl_entry import ACLEntry
from shared.schema.acl_entry import ItemType
from shared.schema.attribute import AttributeType
from shared.schema.news_item import NewsItemAggregateIdSchema, NewsItemAggregateSchema
from shared.schema.report_item import (
    ReportItemAttributeBaseSchema,
    ReportItemBaseSchema,
    ReportItemIdSchema,
    RemoteReportItemSchema,
    ReportItemRemoteSchema,
    ReportItemSchema,
    ReportItemPresentationSchema,
)


class NewReportItemAttributeSchema(ReportItemAttributeBaseSchema):
    """Schema for creating a new report item attribute.

    This schema is used to validate and deserialize data for creating a new report item attribute.

    Arguments:
        ReportItemAttributeBaseSchema -- The base schema for report item attributes.

    Returns:
        An instance of the ReportItemAttribute class.
    """

    @post_load
    def make_report_item_attribute(self, data, **kwargs):
        """Create a report item attribute.

        This method takes in data and creates a ReportItemAttribute object.

        Arguments:
            data (dict): A dictionary containing the data for the report item attribute.

        Returns:
            ReportItemAttribute: The created report item attribute object.
        """
        return ReportItemAttribute(**data)


class ReportItemAttribute(db.Model):
    """A class representing an attribute of a report item.

    Attributes:
        id (int): The unique identifier of the attribute.
        value (str): The value of the attribute.
        value_description (str): The description of the attribute value.
        binary_mime_type (str): The MIME type of the binary data, if applicable.
        binary_data (bytes): The binary data associated with the attribute.
        binary_size (int): The size of the binary data in bytes.
        binary_description (str): The description of the binary data.
        created (datetime): The timestamp of when the attribute was created.
        last_updated (datetime): The timestamp of when the attribute was last updated.
        version (int): The version number of the attribute.
        current (bool): Indicates whether the attribute is the current version.
        attribute_group_item_id (int): The ID of the attribute group item that the attribute belongs to.
        attribute_group_item (AttributeGroupItem): The attribute group item that the attribute belongs to.
        attribute_group_item_title (str): The title of the attribute group item.
        report_item_id (int): The ID of the report item that the attribute belongs to.
        report_item (ReportItem): The report item that the attribute belongs to.
        user_id (int): The ID of the user who created the attribute.
        user (User): The user who created the attribute.

    Methods:
        __init__: Initializes a new instance of the ReportItemAttribute class.
        find: Finds a report item attribute by its ID.

    """

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    value_description = db.Column(db.String())
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    binary_size = db.Column(db.Integer)
    binary_description = db.Column(db.String())
    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)

    version = db.Column(db.Integer, default=1)
    current = db.Column(db.Boolean, default=True)

    attribute_group_item_id = db.Column(db.Integer, db.ForeignKey("attribute_group_item.id"))
    attribute_group_item = db.relationship("AttributeGroupItem", viewonly=True)
    attribute_group_item_title = db.Column(db.String)

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), nullable=True)
    report_item = db.relationship("ReportItem")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User")

    def __init__(
        self,
        id,
        value,
        value_description,
        binary_mime_type,
        binary_size,
        binary_description,
        attribute_group_item_id,
        attribute_group_item_title,
    ):
        """Initialize a ReportItem object.

        Arguments:
            id (int): The ID of the report item.
            value (str): The value of the report item.
            value_description (str): The description of the value.
            binary_mime_type (str): The MIME type of the binary data.
            binary_size (int): The size of the binary data.
            binary_description (str): The description of the binary data.
            attribute_group_item_id (int): The ID of the attribute group item.
            attribute_group_item_title (str): The title of the attribute group item.
        """
        self.id = None
        self.value = value
        self.value_description = value_description
        self.binary_mime_type = binary_mime_type
        self.binary_size = binary_size
        self.binary_description = binary_description
        self.attribute_group_item_id = attribute_group_item_id
        self.attribute_group_item_title = attribute_group_item_title

    @classmethod
    def find(cls, attribute_id):
        """Find a report item attribute by its ID.

        Args:
            attribute_id (int): The ID of the attribute to find.

        Returns:
            ReportItemAttribute: The report item attribute with the specified ID, or None if not found.

        """
        report_item_attribute = cls.query.get(attribute_id)
        return report_item_attribute


class NewReportItemSchema(ReportItemBaseSchema):
    """Schema for creating a new report item.

    This schema defines the structure and validation rules for creating a new report item.

    Arguments:
        ReportItemBaseSchema -- The base schema for report items.

    Returns:
        An instance of the NewReportItemSchema class.
    """

    news_item_aggregates = fields.Nested(NewsItemAggregateIdSchema, many=True, missing=[])
    remote_report_items = fields.Nested(ReportItemIdSchema, many=True, missing=[])
    attributes = fields.Nested(NewReportItemAttributeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Create a new ReportItem object.

        Arguments:
            data (dict): A dictionary containing the data for the ReportItem.

        Returns:
            ReportItem: A new ReportItem object.
        """
        return ReportItem(**data)


class ReportItemRemoteReportItem(db.Model):
    """A class representing the relationship between a report item and a remote report item.

    Arguments:
        db -- The database object used for defining the model.
    """

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)
    remote_report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)


class ReportItem(db.Model):
    """A class representing a report item.

    Attributes:
        id (int): The unique identifier of the report item.
        uuid (str): The UUID of the report item.
        title (str): The title of the report item.
        title_prefix (str): The prefix of the report item title.
        created (datetime): The datetime when the report item was created.
        last_updated (datetime): The datetime when the report item was last updated.
        completed (bool): Indicates whether the report item is completed or not.
        user_id (int): The ID of the user associated with the report item.
        user (User): The user associated with the report item.
        remote_user (str): The remote user associated with the report item.
        report_item_type_id (int): The ID of the report item type associated with the report item.
        report_item_type (ReportItemType): The report item type associated with the report item.
        news_item_aggregates (list): The list of news item aggregates associated with the report item.
        remote_report_items (list): The list of remote report items associated with the report item.
        attributes (list): The list of attributes associated with the report item.
        report_item_cpes (list): The list of report item CPES associated with the report item.
        subtitle (str): The subtitle of the report item.
        tag (str): The tag of the report item.
    """

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64))

    title = db.Column(db.String())
    title_prefix = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", viewonly=True)
    remote_user = db.Column(db.String())

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), nullable=True)
    report_item_type = db.relationship("ReportItemType", viewonly=True)

    news_item_aggregates = db.relationship("NewsItemAggregate", secondary="report_item_news_item_aggregate")

    remote_report_items = db.relationship(
        "ReportItem",
        secondary="report_item_remote_report_item",
        primaryjoin=ReportItemRemoteReportItem.report_item_id == id,
        secondaryjoin=ReportItemRemoteReportItem.remote_report_item_id == id,
    )

    attributes = db.relationship("ReportItemAttribute", back_populates="report_item", cascade="all, delete-orphan")

    report_item_cpes = db.relationship("ReportItemCpe", cascade="all, delete-orphan")

    def __init__(self, id, uuid, title, title_prefix, report_item_type_id, news_item_aggregates, remote_report_items, attributes, completed):
        """Initialize a new instance of the ReportItem class.

        Arguments:
            id (int): The ID of the report item.
            uuid (str): The UUID of the report item.
            title (str): The title of the report item.
            title_prefix (str): The prefix of the report item's title.
            report_item_type_id (int): The ID of the report item type.
            news_item_aggregates (list): A list of news item aggregates associated with the report item.
            remote_report_items (list): A list of remote report items associated with the report item.
            attributes (dict): A dictionary of attributes for the report item.
            completed (bool): Indicates whether the report item is completed or not.
        """
        self.id = id

        if uuid is None:
            self.uuid = str(uuid_generator.uuid4())
        else:
            self.uuid = uuid

        self.title = title
        self.title_prefix = title_prefix
        self.report_item_type_id = report_item_type_id
        self.attributes = attributes
        self.completed = completed
        self.report_item_cpes = []
        self.subtitle = ""
        self.tag = ""

        self.news_item_aggregates = []
        for news_item_aggregate in news_item_aggregates:
            self.news_item_aggregates.append(NewsItemAggregate.find(news_item_aggregate.id))

        self.remote_report_items = []
        for remote_report_item in remote_report_items:
            self.remote_report_items.append(ReportItem.find(remote_report_item.id))

    @orm.reconstructor
    def reconstruct(self):
        """Reconstructs the report item.

        This method clears the subtitle, sets the tag to "mdi-file-table-outline",
        and sorts the attributes based on the attribute group index, attribute group item index, and attribute ID.
        """
        self.subtitle = ""
        self.tag = "mdi-file-table-outline"
        self.attributes.sort(key=lambda obj: (obj.attribute_group_item.attribute_group.index, obj.attribute_group_item.index, obj.id))

    @classmethod
    def count_all(cls, is_completed):
        """Count the number of report items based on completion status.

        Arguments:
            is_completed (bool): A flag indicating whether to count completed or incomplete report items.
        Returns:
            int: The count of report items matching the completion status.
        """
        return cls.query.filter_by(completed=is_completed).count()

    @classmethod
    def find(cls, report_item_id):
        """Find a report item by its ID.

        Arguments:
            report_item_id (int): The ID of the report item.
        Returns:
            ReportItem: The report item with the specified ID.
        """
        report_item = cls.query.get(report_item_id)
        return report_item

    @classmethod
    def find_by_uuid(cls, report_item_uuid):
        """Find a report item by its UUID.

        Arguments:
            report_item_uuid (str): The UUID of the report item.
        Returns:
            ReportItem: The report item with the specified UUID.
        """
        report_item = cls.query.filter_by(uuid=report_item_uuid)
        return report_item

    @classmethod
    def allowed_with_acl(cls, report_item_id, user, see, access, modify):
        """Check if the user is allowed to perform actions on a report item based on ACL.

        Arguments:
            report_item_id (int): The ID of the report item.
            user (User): The user object.
            see (bool): Whether the user can see the report item.
            access (bool): Whether the user can access the report item.
            modify (bool): Whether the user can modify the report item.
        Returns:
            bool: True if the user is allowed, False otherwise.
        """
        query = db.session.query(ReportItem.id).distinct().group_by(ReportItem.id).filter(ReportItem.id == report_item_id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(ReportItem.uuid == ACLEntry.item_id, ACLEntry.item_type == ItemType.REPORT_ITEM),
                and_(
                    cast(ReportItem.report_item_type_id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE,
                ),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_for_sync(cls, last_synced, report_item_types):
        """Retrieve report items for synchronization.

        This method retrieves report items that have been updated since the last synchronization time,
        and belong to the specified report item types.
        Args:
            last_synced (datetime): The last synchronization time.
            report_item_types (list): A list of report item types.
        Returns:
            tuple: A tuple containing two elements:
                - items (list): A list of report items that need to be synchronized.
                - last_sync_time (datetime): The current synchronization time.
        """
        report_item_type_ids = set()
        for report_item_type in report_item_types:
            report_item_type_ids.add(report_item_type.id)

        last_sync_time = datetime.now()

        query = cls.query.filter(
            ReportItem.last_updated >= last_synced,
            ReportItem.last_updated <= last_sync_time,
            ReportItem.report_item_type_id.in_(report_item_type_ids),
        )

        report_items = query.all()

        for report_item in report_items:
            for attribute in report_item.attributes:
                attribute.attribute_group_item_title = attribute.attribute_group_item.title

        report_item_remote_schema = ReportItemRemoteSchema(many=True)
        items = report_item_remote_schema.dump(report_items)

        return items, last_sync_time

    @classmethod
    def get(cls, group, filter, offset, limit, user):
        """Retrieve report items based on specified criteria.

        Arguments:
            group (str): The remote user group.
            filter (dict): The filter criteria.
            offset (int): The offset for pagination.
            limit (int): The limit for pagination.
            user (str): The user performing the query.
        Returns:
            tuple: A tuple containing the list of report items and the total count.
        """
        if group:
            query = cls.query.filter(ReportItem.remote_user == group)
        else:
            query = (
                db.session.query(
                    ReportItem,
                    func.count().filter(ACLEntry.id > 0).label("acls"),
                    func.count().filter(ACLEntry.access.is_(True)).label("access"),
                    func.count().filter(ACLEntry.modify.is_(True)).label("modify"),
                )
                .distinct()
                .group_by(ReportItem.id)
            )

            query = query.filter(ReportItem.remote_user.is_(None))

            query = query.outerjoin(
                ACLEntry,
                or_(
                    and_(ReportItem.uuid == ACLEntry.item_id, ACLEntry.item_type == ItemType.REPORT_ITEM),
                    and_(
                        cast(ReportItem.report_item_type_id, sqlalchemy.String) == ACLEntry.item_id,
                        ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE,
                    ),
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        search_string = filter.get("search", "").lower()
        if search_string:
            search_string = f"%{search_string}%"
            query = query.join(ReportItemAttribute, ReportItem.id == ReportItemAttribute.report_item_id).filter(
                or_(
                    func.lower(ReportItemAttribute.value).like(search_string),
                    func.lower(ReportItem.title).like(search_string),
                    func.lower(ReportItem.title_prefix).like(search_string),
                )
            )

        if filter.get("completed", "").lower() == "true":
            query = query.filter(ReportItem.completed)

        if filter.get("incompleted", "").lower() == "true":
            query = query.filter(ReportItem.completed.is_(False))

        if filter.get("range", "ALL") != "ALL":
            date_limit = datetime.now()
            if filter["range"] == "TODAY":
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            query = query.filter(ReportItem.created >= date_limit)

        if filter.get("sort"):
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(ReportItem.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(ReportItem.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def identical(cls, uuid):
        """Check if a report item with the given UUID exists.

        Arguments:
            uuid -- The UUID of the report item to check.
        Returns:
            True if a report item with the given UUID exists, False otherwise.
        """
        return db.session.query(db.exists().where(ReportItem.uuid == uuid)).scalar()

    @classmethod
    def get_by_cpe(cls, cpes):
        """Retrieve report items by Common Platform Enumeration (CPE).

        This method queries the database to retrieve report items that match the provided CPEs.
        Arguments:
            cpes (list): A list of CPEs to search for.
        Returns:
            list: A list of report item IDs that match the provided CPEs.
        """
        if len(cpes) > 0:
            query_string = "SELECT DISTINCT report_item_id FROM report_item_cpe WHERE value LIKE ANY(:cpes) OR {}"
            params = {"cpes": cpes}

            inner_query = ""
            for i in range(len(cpes)):
                if i > 0:
                    inner_query += " OR "
                param = "cpe" + str(i)
                inner_query += ":" + param + " LIKE value"
                params[param] = cpes[i]

            result = db.engine.execute(text(query_string.format(inner_query)), params)

            return [row[0] for row in result]
        else:
            return []

    @classmethod
    def get_json(cls, group, filter, offset, limit, user):
        """Get the JSON representation of report items.

        This method retrieves report items based on the provided parameters and returns them in JSON format.
        Arguments:
            group (str): The group parameter.
            filter (str): The filter parameter.
            offset (int): The offset parameter.
            limit (int): The limit parameter.
            user (str): The user parameter.
        Returns:
            dict: A dictionary containing the total count of report items and a list of report items in JSON format.
        """
        results, count = cls.get(group, filter, offset, limit, user)
        report_items = []
        if group:
            for result in results:
                report_item = result
                report_item.see = True
                report_item.access = True
                report_item.modify = False
                report_items.append(report_item)
        else:
            for result in results:
                report_item = result.ReportItem
                report_item.see = True
                report_item.access = result.access > 0 or result.acls == 0
                report_item.modify = result.modify > 0 or result.acls == 0
                report_items.append(report_item)

        report_items_schema = ReportItemPresentationSchema(many=True)
        return {"total_count": count, "items": report_items_schema.dump(report_items)}

    @classmethod
    def get_detail_json(cls, id):
        """Get the detailed JSON representation of a report item.

        Arguments:
            cls -- The class object.
            id -- The ID of the report item.
        Returns:
            The detailed JSON representation of the report item.
        """
        report_item = cls.query.get(id)
        report_item_schema = ReportItemSchema()
        return report_item_schema.dump(report_item)

    @classmethod
    def get_groups(cls):
        """Get the distinct groups associated with the report items.

        Returns:
            list: A list of distinct groups.
        """
        result = (
            db.session.query(ReportItem.remote_user)
            .distinct()
            .group_by(ReportItem.remote_user)
            .filter(ReportItem.remote_user.isnot(None))
            .all()
        )
        groups = set()
        for row in result:
            groups.add(row[0])

        return list(groups)

    @classmethod
    def add_report_item(cls, report_item_data, user):
        """Add a report item to the database.

        This method takes in report_item_data and user as arguments and adds a new report item to the database.
        It performs authorization checks to ensure that the user has the necessary permissions to add the report item.
        Arguments:
            report_item_data (dict): The data for the report item.
            user (User): The user adding the report item.
        Returns:
            tuple: A tuple containing the added report item and the HTTP status code.
        """
        report_item_schema = NewReportItemSchema()
        report_item = report_item_schema.load(report_item_data)

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return "Unauthorized access to report item type", 401

        report_item.user_id = user.id
        for attribute in report_item.attributes:
            attribute.user_id = user.id

        report_item.update_cpes()

        db.session.add(report_item)
        db.session.commit()

        return report_item, 200

    @classmethod
    def add_remote_report_items(cls, report_item_data, remote_node_name):
        """Add remote report items to the database.

        This method takes a list of report item data and a remote node name,
        and adds the report items to the database. If a report item with the
        same UUID already exists, it updates the existing report item with the
        new data.
        Arguments:
            report_item_data (list): A list of report item data.
            remote_node_name (str): The name of the remote node.
        """
        report_item_schema = NewReportItemSchema(many=True)
        report_items = report_item_schema.load(report_item_data)

        for report_item in report_items:
            original_report_item = cls.find_by_uuid(report_item.uuid)
            if original_report_item is None:
                report_item.remote_user = remote_node_name
                db.session.add(report_item)
            else:
                original_report_item.title = report_item.title
                original_report_item.title_prefix = report_item.title_prefix
                original_report_item.completed = report_item.completed
                original_report_item.last_updated = datetime.now()
                original_report_item.attributes = report_item.attributes

        db.session.commit()

    @classmethod
    def update_report_item(cls, id, data, user):
        """Update a report item with the given data.

        Arguments:
            id (int): The ID of the report item.
            data (dict): The data to update the report item with.
            user (User): The user performing the update.
        Returns:
            tuple: A tuple containing a boolean indicating whether the report item was modified and the updated data.
        """
        modified = False
        new_attribute = None
        report_item = cls.query.get(id)
        if report_item is not None:
            if "update" in data:
                if "title" in data:
                    if report_item.title != data["title"]:
                        modified = True
                        report_item.title = data["title"]
                        data["title"] = ""

                if "title_prefix" in data:
                    if report_item.title_prefix != data["title_prefix"]:
                        modified = True
                        report_item.title_prefix = data["title_prefix"]
                        data["title_prefix"] = ""

                if "completed" in data:
                    if report_item.completed != data["completed"]:
                        modified = True
                        report_item.completed = data["completed"]
                        data["completed"] = ""

                if "attribute_id" in data:
                    for attribute in report_item.attributes:
                        # Compare attribute IDs
                        if str(attribute.id) == str(data["attribute_id"]):
                            if attribute.value != data["attribute_value"]:
                                modified = True
                                attribute.value = data["attribute_value"]
                                data["attribute_value"] = ""
                                attribute.user = user
                                attribute.last_updated = datetime.now()
                            if attribute.value_description != data["value_description"]:
                                modified = True
                                attribute.value_description = data["value_description"]
                                data["value_description"] = ""
                                attribute.user = user
                                attribute.last_updated = datetime.now()
                            break

            if "add" in data:
                if "attribute_id" in data:
                    modified = True
                    new_attribute = ReportItemAttribute(None, "", "", None, 0, None, data["attribute_group_item_id"], None)
                    new_attribute.user = user
                    report_item.attributes.append(new_attribute)

                if "aggregate_ids" in data:
                    modified = True
                    for aggregate_id in data["aggregate_ids"]:
                        aggregate = NewsItemAggregate.find(aggregate_id)
                        report_item.news_item_aggregates.append(aggregate)

                if "remote_report_item_ids" in data:
                    modified = True
                    for remote_report_item_id in data["remote_report_item_ids"]:
                        remote_report_item = ReportItem.find(remote_report_item_id)
                        report_item.remote_report_items.append(remote_report_item)

            if "delete" in data:
                if "attribute_id" in data:
                    attribute_to_delete = None
                    for attribute in report_item.attributes:
                        # sometime we compare: int & int or int & str
                        if str(attribute.id) == str(data["attribute_id"]):
                            attribute_to_delete = attribute
                            break

                    if attribute_to_delete is not None:
                        modified = True
                        report_item.attributes.remove(attribute_to_delete)

                if "aggregate_id" in data:
                    aggregate_to_delete = None
                    for aggregate in report_item.news_item_aggregates:
                        if aggregate.id == data["aggregate_id"]:
                            aggregate_to_delete = aggregate
                            break

                    if aggregate_to_delete is not None:
                        modified = True
                        report_item.news_item_aggregates.remove(aggregate_to_delete)

                if "remote_report_item_id" in data:
                    remote_report_item_to_delete = None
                    for remote_report_item in report_item.remote_report_items:
                        if remote_report_item.id == data["remote_report_item_id"]:
                            remote_report_item_to_delete = remote_report_item
                            break

                    if remote_report_item_to_delete is not None:
                        modified = True
                        report_item.remote_report_items.remove(remote_report_item_to_delete)

            if modified:
                report_item.last_updated = datetime.now()
                data["user_id"] = user.id
                data["report_item_id"] = int(id)
                report_item.update_cpes()

            db.session.commit()

            if new_attribute is not None:
                data["attribute_id"] = new_attribute.id

        return modified, data

    @classmethod
    def get_updated_data(cls, id, data):
        """Get the updated data for a report item.

        This method retrieves the updated data for a report item based on the provided ID and data.
        Arguments:
            cls (class): The class object.
            id (int): The ID of the report item.
            data (dict): The data containing the updates.
        Returns:
            dict: The updated data for the report item.
        """
        report_item = cls.query.get(id)
        if report_item is not None:
            if "update" in data:
                if "title" in data:
                    data["title"] = report_item.title

                if "title_prefix" in data:
                    data["title_prefix"] = report_item.title_prefix

                if "completed" in data:
                    data["completed"] = report_item.completed

                if "attribute_id" in data:
                    for attribute in report_item.attributes:
                        if str(attribute.id) == data["attribute_id"]:
                            data["attribute_value"] = attribute.value
                            data["attribute_value_description"] = attribute.value_description
                            data["attribute_last_updated"] = attribute.last_updated.strftime("%d.%m.%Y - %H:%M")
                            data["attribute_user"] = attribute.user.name
                            break

            if "add" in data:
                if "aggregate_ids" in data:
                    schema = NewsItemAggregateSchema()
                    data["news_item_aggregates"] = []
                    for aggregate_id in data["aggregate_ids"]:
                        aggregate = NewsItemAggregate.find(aggregate_id)
                        data["news_item_aggregates"].append(schema.dump(aggregate))

                if "remote_report_item_ids" in data:
                    schema = RemoteReportItemSchema()
                    data["remote_report_items"] = []
                    for remote_report_item_id in data["remote_report_item_ids"]:
                        remote_report_item = ReportItem.find(remote_report_item_id)
                        data["remote_report_items"].append(schema.dump(remote_report_item))

                if "attribute_id" in data:
                    for attribute in report_item.attributes:
                        if str(attribute.id) == data["attribute_id"]:
                            data["attribute_value"] = attribute.value
                            data["attribute_value_description"] = attribute.value_description
                            data["binary_mime_type"] = attribute.binary_mime_type
                            data["binary_size"] = attribute.binary_size
                            data["binary_description"] = attribute.binary_description
                            data["attribute_last_updated"] = attribute.last_updated.strftime("%d.%m.%Y - %H:%M")
                            data["attribute_user"] = attribute.user.name
                            break

        return data

    @classmethod
    def add_attachment(cls, id, attribute_group_item_id, user, file, description):
        """Add an attachment to a report item.

        Arguments:
            id (int): The ID of the report item.
            attribute_group_item_id (int): The ID of the attribute group item.
            user (User): The user who is adding the attachment.
            file (FileStorage): The file to be attached.
            description (str): The description of the attachment.
        Returns:
            dict: A dictionary containing information about the attachment.
                - "add" (bool): True if the attachment was added successfully.
                - "user_id" (int): The ID of the user who added the attachment.
                - "report_item_id" (int): The ID of the report item.
                - "attribute_id" (int): The ID of the newly created attribute.
        """
        report_item = cls.query.get(id)
        file_data = file.read()
        new_attribute = ReportItemAttribute(
            None, file.filename, "", file.mimetype, len(file_data), description, attribute_group_item_id, None
        )
        new_attribute.user = user
        new_attribute.binary_data = file_data
        report_item.attributes.append(new_attribute)

        report_item.last_updated = datetime.now()

        data = dict()
        data["add"] = True
        data["user_id"] = user.id
        data["report_item_id"] = int(id)
        data["attribute_id"] = new_attribute.id

        db.session.commit()

        return data

    @classmethod
    def remove_attachment(cls, id, attribute_id, user):
        """Remove an attachment from a report item.

        Arguments:
            cls (ReportItem): The class object.
            id (int): The ID of the report item.
            attribute_id (int): The ID of the attribute to be removed.
            user (User): The user performing the action.
        Returns:
            dict: A dictionary containing information about the deletion.
                - delete (bool): Indicates whether the attribute was successfully deleted.
                - user_id (int): The ID of the user performing the action.
                - report_item_id (int): The ID of the report item.
                - attribute_id (int): The ID of the attribute that was deleted.
        """
        report_item = cls.query.get(id)
        attribute_to_delete = None
        for attribute in report_item.attributes:
            if attribute.id == attribute_id:
                attribute_to_delete = attribute
                break

        if attribute_to_delete is not None:
            report_item.attributes.remove(attribute_to_delete)

        report_item.last_updated = datetime.now()

        data = dict()
        data["delete"] = True
        data["user_id"] = user.id
        data["report_item_id"] = int(id)
        data["attribute_id"] = attribute_id

        db.session.commit()

        return data

    @classmethod
    def delete_report_item(cls, id):
        """Delete a report item by its ID.

        Arguments:
            id (int): The ID of the report item to be deleted.
        Returns:
            tuple: A tuple containing the status message and the HTTP status code.
                The status message is "success" if the report item was deleted successfully.
                The HTTP status code is 200 if the report item was deleted successfully.
        """
        report_item = cls.query.get(id)
        if report_item is not None:
            db.session.delete(report_item)
            db.session.commit()
            return "success", 200

    def update_cpes(self):
        """Update the list of CPES for the report item.

        This method clears the existing list of CPES and populates it with new CPES
        based on the attributes of the report item. Only attributes of type CPE are considered.
        """
        self.report_item_cpes = []
        if self.completed is True:
            for attribute in self.attributes:
                attribute_group = AttributeGroupItem.find(attribute.attribute_group_item_id)
                if attribute_group.attribute.type == AttributeType.CPE:
                    self.report_item_cpes.append(ReportItemCpe(attribute.value))


class ReportItemCpe(db.Model):
    """A class representing a CPE (Common Platform Enumeration) report item.

    Attributes:
        id (int): The unique identifier of the report item.
        value (str): The value of the report item.
        report_item_id (int): The foreign key referencing the parent report item.
    Args:
        db (object): The database object.
    """

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"))

    def __init__(self, value):
        """Initialize a ReportItemCpe object.

        Args:
            value (any): The value of the report item.
        """
        self.id = None
        self.value = value
