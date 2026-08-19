"""PublicWebNode model.

A public-web node is a read-only consumer of published report products (e.g. the
public-web / CyberFeed-style feed). It authenticates to core with the shared node
ApiKey exactly like the other nodes, and is managed under Configuration.
"""

from __future__ import annotations

from datetime import datetime

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
        last_seen: Last time the node was actually in touch with core (it pulled
            data, or answered the isalive ping). ``None`` until that first
            contact — registering a node says nothing about it running.
        cert_resolver: Name of the ACME resolver THIS node's Traefik declares, used
            for its webs unless a web names its own. Node-scoped because a resolver
            name means nothing outside the Traefik that declares it: given core's
            name, a remote node disables ACME for the router and serves its default
            certificate. Empty inherits the instance-wide name, which is right only
            for a node core fronts.
        fronted_by_core: Whether CORE's own Traefik publishes this node's webs.
            True for the node beside core in the same compose stack - the only one
            core's Traefik can reach, and the single-host default.

            Recorded rather than inferred, because core's Traefik requests an ACME
            certificate for every hostname it is given: handed a remote node's, it
            asks its own CA account for a name it does not serve, which a CA that
            pre-validates domains refuses and Traefik then retries forever. Two Traefiks would
            also both claim the hostname, leaving DNS to decide the winner.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())
    # URL core uses to reach this node's management API (health check + cache
    # reset push). Empty means no core->node channel (the node still pulls).
    api_url = db.Column(db.String())
    api_key = db.Column(db.String(), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    # Deliberately has no default: a node that has never been reached must not
    # look alive just because it was created a moment ago.
    last_seen = db.Column(db.DateTime)
    # Ansible sends the name its worker template declares, so a deployed node arrives
    # self-consistent.
    cert_resolver = db.Column(db.String())
    # False by default so a node registered by a path that does not set it - ansible
    # above all - is treated as remote, which is the safe direction.
    fronted_by_core = db.Column(db.Boolean, nullable=False, default=False, server_default="false")

    # The distinct branded feeds ("webs") this node serves, one per hostname.
    webs = db.relationship("PublicWeb", back_populates="node", cascade="all, delete-orphan")

    def __init__(
        self,
        name: str,
        description: str = "",
        api_key: str = "",
        api_url: str = "",
        id: int | None = None,  # noqa: A002, ARG002
        fronted_by_core: bool = False,
        cert_resolver: str | None = "",
    ) -> None:
        """Initialize a new PublicWebNode (id is auto-assigned)."""
        self.id = None
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.fronted_by_core = fronted_by_core
        self.cert_resolver = cert_resolver or ""
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
        last seen (updated by the periodic isalive ping and by the node's own
        pulls), mirroring the other nodes' status indicator.
        """
        nodes, count = cls.get(search)
        schema = PublicWebNodePresentationSchema(many=True)
        items = schema.dump(nodes)
        for i in range(len(items)):
            items[i]["status"] = nodes[i].status()
        return {"total_count": count, "items": items}

    @classmethod
    def add(cls, data: dict) -> PublicWebNode:
        """Add a new node and return it."""
        schema = NewPublicWebNodeSchema()
        node = schema.load(data)
        db.session.add(node)
        db.session.commit()
        return node

    @classmethod
    def update(cls, node_id: int, data: dict) -> None:
        """Update an existing node. An empty api_key leaves the current key unchanged."""
        schema = NewPublicWebNodeSchema()
        updated = schema.load(data)
        node = db.session.get(cls, node_id)
        node.name = updated.name
        node.description = updated.description
        node.api_url = updated.api_url
        node.cert_resolver = updated.cert_resolver
        if updated.api_key:
            node.api_key = updated.api_key
        db.session.commit()

    @classmethod
    def delete(cls, node_id: int) -> None:
        """Delete a node."""
        node = db.session.get(cls, node_id)
        db.session.delete(node)
        db.session.commit()

    def seconds_since_last_seen(self) -> float | None:
        """Seconds since the node was last in touch, or ``None`` if it never was."""
        if self.last_seen is None:
            return None
        try:
            return (datetime.now(TZ) - self.last_seen.replace(tzinfo=TZ)).total_seconds()
        except Exception as ex:
            logger.exception(f"Cannot compute public-web node age: {ex}")
            return None

    def status(self) -> str:
        """Health colour for the configuration UI: green, orange or red.

        A node that has never been seen is red — registering it in the GUI is
        not evidence that anything is running at the other end.
        """
        inactive = self.seconds_since_last_seen()
        if inactive is None:
            return "red"
        return "green" if inactive < _STATUS_GREEN_SECONDS else "orange" if inactive < _STATUS_ORANGE_SECONDS else "red"

    def is_reachable(self) -> bool:
        """Whether calling this node is worth attempting at all.

        Deliberately more lenient than :meth:`status`: a node that has answered
        within the orange window may well still be up, and a skipped cache-reset
        push costs the admin a long cache TTL. A node that has never answered, or
        has been silent for longer than that, is treated as not running.
        """
        inactive = self.seconds_since_last_seen()
        return inactive is not None and inactive < _STATUS_ORANGE_SECONDS

    def touch(self) -> None:
        """Record that the node just contacted core (updated on the node's pulls)."""
        self.last_seen = datetime.now(TZ)
        db.session.commit()

    def update_last_seen(self) -> None:
        """Record a successful core->node health ping (drives the GUI status)."""
        self.last_seen = datetime.now(TZ)
        db.session.commit()


# Ensure the child model is registered whenever the node model is imported (the
# node is imported early by auth_manager), so create_all/mapper resolution of the
# ``webs`` relationship works. Imported at the bottom to avoid an import cycle.
from model.public_web import PublicWeb  # noqa: E402, F401
