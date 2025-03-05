"""Remote Access and Remote Node models."""

import uuid as uuid_generator
from datetime import datetime
from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_

from managers.db_manager import db
from managers.log_manager import logger
from model.osint_source import OSINTSource
from model.report_item_type import ReportItemType
from shared.schema.osint_source import OSINTSourceIdSchema
from shared.schema.remote import RemoteAccessSchema, RemoteAccessPresentationSchema, RemoteNodeSchema, RemoteNodePresentationSchema
from shared.schema.report_item_type import ReportItemTypeIdSchema


class NewRemoteAccessSchema(RemoteAccessSchema):
    """Marshmallow schema for creating a new Remote Access.

    Args:
        RemoteAccessSchema: Base schema for Remote Access.
    Attributes:
        osint_sources: List of OSINT sources.
        report_item_types: List of report item types.
    """

    osint_sources = fields.Nested(OSINTSourceIdSchema, many=True)
    report_item_types = fields.Nested(ReportItemTypeIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Create a new Remote Access object from the schema data.

        Args:
            data: Schema data.
        Returns:
            RemoteAccess: New Remote Access object.
        """
        return RemoteAccess(**data)


class RemoteAccess(db.Model):
    """Model for Remote Access.

    Attributes:
        id: Unique identifier.
        name: Name of the Remote Access.
        description: Description of the Remote Access.
        enabled: Whether the Remote Access is enabled.
        connected: Whether the Remote Access is connected.
        api_key: API key for the Remote Access.
        osint_sources: List of OSINT sources.
        report_item_types: List of report item types.
        event_id: Unique identifier for the Remote Access.
        last_synced_news_items: Last time news items were synced.
        last_synced_report_items: Last time report items were synced.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    connected = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String(), unique=True)

    osint_sources = db.relationship("OSINTSource", secondary="remote_access_osint_source")
    report_item_types = db.relationship("ReportItemType", secondary="remote_access_report_item_type")

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime, default=datetime.now())
    last_synced_report_items = db.Column(db.DateTime, default=datetime.now())

    def __init__(self, id, name, description, enabled, api_key, osint_sources, report_item_types):
        """Initialize a new Remote Access object."""
        self.id = None
        self.name = name
        self.description = description
        self.enabled = enabled
        self.api_key = api_key
        self.event_id = str(uuid_generator.uuid4())
        self.title = ""
        self.subtitle = ""
        self.tag = ""
        self.status = ""

        self.osint_sources = []
        for osint_source in osint_sources:
            self.osint_sources.append(OSINTSource.find(osint_source.id))

        self.report_item_types = []
        for report_item_type in report_item_types:
            self.report_item_types.append(ReportItemType.find(report_item_type.id))

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the Remote Access object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-remote-desktop"
        if self.enabled is False:
            self.status = "red"
        elif self.connected is True:
            self.status = "green"
        else:
            self.status = "orange"

    @classmethod
    def get_by_api_key(cls, api_key):
        """Get a node by API key.

        Args:
            api_key (str): The API key
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get(cls, search):
        """Get all Remote Accesses.

        Args:
            search: Search string.
        Returns:
            list: List of Remote Accesses.
            int: Number of Remote Accesses.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(func.lower(RemoteAccess.name).like(search_string), func.lower(RemoteAccess.description).like(search_string))
            )

        return query.order_by(db.asc(RemoteAccess.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all Remote Accesses as JSON.

        Args:
            search: Search string.
        Returns:
            dict: JSON object containing Remote Accesses.
        """
        remote_accesses, count = cls.get(search)
        schema = RemoteAccessPresentationSchema(many=True)
        return {"total_count": count, "items": schema.dump(remote_accesses)}

    @classmethod
    def get_relevant_for_news_items(cls, osint_source_ids):
        """Get Remote Accesses relevant for news items.

        Args:
            osint_source_ids: List of OSINT source IDs.
        Returns:
            list: List of Remote Access IDs.
        """
        query = db.session.query(RemoteAccess.event_id).join(
            RemoteAccessOSINTSource,
            and_(RemoteAccessOSINTSource.remote_access_id == RemoteAccess.id, RemoteAccessOSINTSource.osint_source_id.in_(osint_source_ids)),
        )

        response = query.all()
        ids = set()
        for rows in response:
            ids.add(rows[0])

        return list(ids)

    @classmethod
    def get_relevant_for_report_item(cls, report_type_id):
        """Get Remote Accesses relevant for a report item type.

        Args:
            report_type_id: Report item type ID.
        Returns:
            list: List of Remote Access IDs.
        """
        query = db.session.query(RemoteAccess.event_id).join(
            RemoteAccessReportItemType,
            and_(
                RemoteAccessReportItemType.remote_access_id == RemoteAccess.id,
                RemoteAccessReportItemType.report_item_type_id == report_type_id,
            ),
        )

        response = query.all()
        ids = set()
        for rows in response:
            ids.add(rows[0])

        return list(ids)

    @classmethod
    def add(cls, data):
        """Add a new Remote Access.

        Args:
            data: Data for the new Remote Access.
        """
        schema = NewRemoteAccessSchema()
        remote_access = schema.load(data)
        db.session.add(remote_access)
        db.session.commit()

    @classmethod
    def delete(cls, remote_access_id):
        """Delete a Remote Access.

        Args:
            remote_access_id: ID of the Remote Access to delete.
        """
        remote_access = db.session.get(cls, remote_access_id)
        db.session.delete(remote_access)
        db.session.commit()

    @classmethod
    def update(cls, remote_access_id, data):
        """Update a Remote Access.

        Args:
            remote_access_id: ID of the Remote Access to update.
            data: Data to update the Remote Access with.
        Returns:
            str: Event ID of the Remote Access.
            bool: Whether the Remote Access should be disconnected.
        """
        schema = NewRemoteAccessSchema()
        updated_remote_access = schema.load(data)
        remote_access = db.session.get(cls, remote_access_id)
        remote_access.name = updated_remote_access.name
        remote_access.description = updated_remote_access.description
        remote_access.osint_sources = updated_remote_access.osint_sources
        remote_access.report_item_types = updated_remote_access.report_item_types

        disconnect = False
        event_id = remote_access.event_id

        if remote_access.enabled and not updated_remote_access.enabled:
            remote_access.enabled = False
            if remote_access.connected:
                remote_access.connected = False
                disconnect = True
        else:
            remote_access.enabled = updated_remote_access.enabled

        if remote_access.api_key != updated_remote_access.api_key or not remote_access.enabled:
            disconnect = True
            remote_access.connected = False
            remote_access.event_id = str(uuid_generator.uuid4())

        remote_access.api_key = updated_remote_access.api_key
        db.session.commit()

        return event_id, disconnect

    def connect(self):
        """Remote Access is connecting.

        Returns:
            dict: Information about the connection.
            int: HTTP status code.
        """
        try:
            logger.info(f"Remote Access is connecting: {self.name}")
            if self.enabled:
                self.connected = True
                db.session.commit()
                return {
                    "event_id": self.event_id,
                    "last_synced_news_items": format(self.last_synced_news_items),
                    "last_synced_report_items": format(self.last_synced_report_items),
                    "news_items_provided": len(self.osint_sources) > 0,
                    "report_items_provided": len(self.report_item_types) > 0,
                }
            else:
                return {"error": "unauthorized"}, 401

        except Exception as ex:
            msg = f"Remote Access connecting failed: {ex}"
            logger.exception(msg)
            return {"error": msg}, 400

    def disconnect(self):
        """Disconnecting Remote Access."""
        logger.info(f"Disconnecting Remote Access: {self.name}")
        self.connected = False
        db.session.commit()
        return {}

    def update_news_items_sync(self, data):
        """Update the last time news items were synced.

        Args:
            data: Data containing the last sync time.
        """
        self.last_synced_news_items = datetime.strptime(data["last_sync_time"], "%Y-%m-%d %H:%M:%S.%f")
        db.session.commit()

    def update_report_items_sync(self, data):
        """Update the last time report items were synced.

        Args:
            data: Data containing the last sync time.
        """
        self.last_synced_report_items = datetime.strptime(data["last_sync_time"], "%Y-%m-%d %H:%M:%S.%f")
        db.session.commit()


class RemoteAccessOSINTSource(db.Model):
    """Model for Remote Access OSINT Source.

    Attributes:
        remote_access_id: ID of the Remote Access.
        osint_source_id: ID of the OSINT source.
    """

    remote_access_id = db.Column(db.Integer, db.ForeignKey("remote_access.id"), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), primary_key=True)


class RemoteAccessReportItemType(db.Model):
    """Model for Remote Access Report Item Type.

    Attributes:
        remote_access_id: ID of the Remote Access.
        report_item_type_id: ID of the report item type.
    """

    remote_access_id = db.Column(db.Integer, db.ForeignKey("remote_access.id"), primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), primary_key=True)


class NewRemoteNodeSchema(RemoteNodeSchema):
    """Marshmallow schema for creating a new Remote Node."""

    @post_load
    def make(self, data, **kwargs):
        """Create a new Remote Node object from the schema data.

        Args:
            data: Schema data.
        Returns:
            RemoteNode: New Remote Node object.
        """
        return RemoteNode(**data)


class RemoteNode(db.Model):
    """Model for Remote Node.

    Attributes:
        id: Unique identifier.
        name: Name of the Remote Node.
        description: Description of the Remote Node.
        enabled: Whether the Remote Node is enabled.
        remote_url: URL of the Remote Node.
        events_url: URL of the Remote Node events.
        api_key: API key for the Remote Node.
        sync_news_items: Whether to sync news items.
        osint_source_group_id: ID of the OSINT source group.
        sync_report_items: Whether to sync report items.
        event_id: Unique identifier for the Remote Node.
        last_synced_news_items: Last time news items were synced.
        last_synced_report_items: Last time report items were synced.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    remote_url = db.Column(db.String())
    events_url = db.Column(db.String())
    api_key = db.Column(db.String())

    sync_news_items = db.Column(db.Boolean)
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id"))
    sync_report_items = db.Column(db.Boolean)

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime)
    last_synced_report_items = db.Column(db.DateTime)

    def __init__(
        self, id, name, description, enabled, remote_url, events_url, api_key, sync_news_items, sync_report_items, osint_source_group_id
    ):
        """Initialize a new Remote Node object."""
        self.id = None
        self.name = name
        self.description = description
        self.remote_url = remote_url
        self.events_url = events_url
        self.enabled = enabled
        self.api_key = api_key
        self.sync_news_items = sync_news_items
        self.sync_report_items = sync_report_items
        self.osint_source_group_id = osint_source_group_id
        self.title = ""
        self.subtitle = ""
        self.tag = ""
        self.status = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the Remote Node object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-share-variant"
        if self.enabled is False or not self.event_id:
            self.status = "red"
        else:
            self.status = "green"

    @classmethod
    def find(cls, node_id):
        """Find a Remote Node by ID.

        Args:
            node_id: ID of the Remote Node to find.
        Returns:
            RemoteNode: Remote Node object.
        """
        return db.session.get(cls, node_id)

    @classmethod
    def get(cls, search):
        """Get all Remote Nodes.

        Args:
            search: Search string.
        Returns:
            list: List of Remote Nodes.
            int: Number of Remote Nodes.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(or_(func.lower(RemoteNode.name).like(search_string), func.lower(RemoteNode.description).like(search_string)))

        return query.order_by(db.asc(RemoteNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all Remote Nodes as JSON.

        Args:
            search: Search string.
        Returns:
            dict: JSON object containing Remote Nodes.
        """
        remote_nodes, count = cls.get(search)
        schema = RemoteNodePresentationSchema(many=True)
        return {"total_count": count, "items": schema.dump(remote_nodes)}

    @classmethod
    def add(cls, data):
        """Add a new Remote Node.

        Args:
            data: Data for the new Remote Node.
        """
        schema = NewRemoteNodeSchema()
        remote_node = schema.load(data)
        db.session.add(remote_node)
        db.session.commit()

    @classmethod
    def delete(cls, remote_node_id):
        """Delete a Remote Node.

        Args:
            remote_node_id: ID of the Remote Node to delete.
        """
        remote_node = db.session.get(cls, remote_node_id)
        db.session.delete(remote_node)
        db.session.commit()

    @classmethod
    def update(cls, remote_node_id, data):
        """Update a Remote Node.

        Args:
            remote_node_id: ID of the Remote Node to update.
            data: Data to update the Remote Node with.
        Returns:
            bool: Whether the Remote Node is enabled.
        """
        schema = NewRemoteNodeSchema()
        updated_remote_node = schema.load(data)
        remote_node = db.session.get(cls, remote_node_id)
        remote_node.name = updated_remote_node.name
        remote_node.description = updated_remote_node.description
        remote_node.enabled = updated_remote_node.enabled
        remote_node.remote_url = updated_remote_node.remote_url
        remote_node.events_url = updated_remote_node.events_url
        remote_node.api_key = updated_remote_node.api_key
        remote_node.sync_news_items = updated_remote_node.sync_news_items
        remote_node.sync_report_items = updated_remote_node.sync_report_items
        remote_node.osint_source_group_id = updated_remote_node.osint_source_group_id
        if remote_node.enabled is False:
            remote_node.event_id = None
        db.session.commit()
        return remote_node.enabled

    def connect(self, access_info):
        """Connect to a Remote Node.

        Args:
            access_info: Information about the connection.
        """
        self.event_id = access_info["event_id"]
        self.last_synced_news_items = datetime.strptime(access_info["last_synced_news_items"], "%Y-%m-%d %H:%M:%S.%f")
        self.last_synced_report_items = datetime.strptime(access_info["last_synced_report_items"], "%Y-%m-%d %H:%M:%S.%f")
        db.session.commit()

    def disconnect(self):
        """Disconnect from a Remote Node."""
        self.event_id = None
        db.session.commit()
