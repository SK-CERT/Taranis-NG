"""PublicWebNode model.

A public-web node is a read-only consumer of published report products (e.g. the
public-web / CyberFeed-style feed). It authenticates to core with the shared node
ApiKey exactly like the other nodes, and is managed under Configuration.
"""

from __future__ import annotations

from datetime import UTC, datetime

from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import post_load
from shared.common import TZ
from shared.schema.public_web_node import PublicWebNodePresentationSchema, PublicWebNodeSchema
from sqlalchemy import or_, orm

# Node health thresholds (seconds since last successful contact), lenient
# relative to the 1-minute isalive ping so a healthy node stays green.
_STATUS_GREEN_SECONDS = 180
_STATUS_ORANGE_SECONDS = 600


class NewPublicWebNodeSchema(PublicWebNodeSchema):
    """Schema for creating/updating a PublicWebNode."""

    @post_load
    def make(self, data, **kwargs):  # noqa: ANN001, ANN003, ANN201, ARG002
        """Build a PublicWebNode from the loaded data."""
        return PublicWebNode(**data)


class PublicWebNode(db.Model):
    """Model for a public-web node.

    Attributes:
        id: Unique identifier.
        name: Node name.
        description: Node description.
        api_key: Shared API key the node uses to authenticate to core.
        created: Creation timestamp.
        last_seen: Last time the node contacted core.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())
    # URL core uses to reach this node's management API (health check + cache
    # reset push). Empty means no core->node channel (the node still pulls).
    api_url = db.Column(db.String())
    api_key = db.Column(db.String(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    last_seen = db.Column(db.DateTime, default=datetime.now)

    # The distinct branded feeds ("webs") this node serves, one per hostname.
    webs = db.relationship("PublicWeb", back_populates="node", cascade="all, delete-orphan")

    def __init__(self, name: str, description: str = "", api_key: str = "", api_url: str = "", id: int | None = None) -> None:  # noqa: A002, ARG002
        """Initialize a new PublicWebNode (id is auto-assigned)."""
        self.id = None
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the object for presentation."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-rss"

    @classmethod
    def get_by_api_key(cls, api_key: str) -> PublicWebNode | None:
        """Get a node by its API key."""
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_by_name(cls, name: str) -> PublicWebNode | None:
        """Get a node by its name."""
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_all(cls) -> list[PublicWebNode]:
        """Get all nodes ordered by name."""
        return cls.query.order_by(db.asc(cls.name)).all()

    @classmethod
    def get(cls, search: str | None) -> tuple[list[PublicWebNode], int]:
        """Get nodes matching an optional search string."""
        query = cls.query
        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(cls.name.ilike(search_string), cls.description.ilike(search_string)))
        return query.order_by(db.asc(cls.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Get all nodes as JSON for the configuration UI, with a health status.

        ``status`` is green/orange/red derived from how recently the node was
        last seen (updated by the periodic isalive ping), mirroring the other
        nodes' status indicator.
        """
        nodes, count = cls.get(search)
        schema = PublicWebNodePresentationSchema(many=True)
        items = schema.dump(nodes)
        for i in range(len(items)):
            try:
                created = nodes[i].created.replace(tzinfo=TZ)
                last_seen = nodes[i].last_seen.replace(tzinfo=TZ) if nodes[i].last_seen is not None else created
                inactive = (datetime.now(TZ) - max(created, last_seen)).total_seconds()
                items[i]["status"] = "green" if inactive < _STATUS_GREEN_SECONDS else "orange" if inactive < _STATUS_ORANGE_SECONDS else "red"
            except Exception as ex:
                logger.exception(f"Cannot compute public-web node status: {ex}")
                items[i]["status"] = "red"
        return {"total_count": count, "items": items}

    @classmethod
    def add(cls, data: dict) -> None:
        """Add a new node."""
        schema = NewPublicWebNodeSchema()
        node = schema.load(data)
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id: int, data: dict) -> None:
        """Update an existing node. An empty api_key leaves the current key unchanged."""
        schema = NewPublicWebNodeSchema()
        updated = schema.load(data)
        node = db.session.get(cls, node_id)
        node.name = updated.name
        node.description = updated.description
        node.api_url = updated.api_url
        if updated.api_key:
            node.api_key = updated.api_key
        db.session.commit()

    @classmethod
    def delete(cls, node_id: int) -> None:
        """Delete a node."""
        node = db.session.get(cls, node_id)
        db.session.delete(node)
        db.session.commit()

    def touch(self) -> None:
        """Record that the node just contacted core (updated on the node's pulls)."""
        self.last_seen = datetime.now(UTC)
        db.session.commit()

    def update_last_seen(self) -> None:
        """Record a successful core->node health ping (drives the GUI status)."""
        self.last_seen = datetime.now(UTC)
        db.session.commit()


# Ensure the child model is registered whenever the node model is imported (the
# node is imported early by auth_manager), so create_all/mapper resolution of the
# ``webs`` relationship works. Imported at the bottom to avoid an import cycle.
from model.public_web import PublicWeb  # noqa: E402, F401
