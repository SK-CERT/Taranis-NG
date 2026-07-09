"""PublicWeb model.

A "public web" is one branded public feed hosted by a :class:`PublicWebNode`,
mirroring how a collectors node hosts multiple collectors. Each web has its own
hostname, its own configuration (branding text, feed sizes, languages, stored as
a free-form JSON object owned by the GUI), and its own images. The public-web
container selects the web to serve per request by the incoming Host header.
"""

from __future__ import annotations

from managers.db_manager import db
from marshmallow import post_load
from shared.schema.public_web import PublicWebPresentationSchema, PublicWebSchema
from sqlalchemy import or_, orm

# The image kinds a web can carry.
IMAGE_KINDS = ("logo", "favicon", "preview")


class NewPublicWebSchema(PublicWebSchema):
    """Schema for creating/updating a PublicWeb."""

    @post_load
    def make(self, data, **kwargs):  # noqa: ANN001, ANN003, ANN201, ARG002
        """Build a PublicWeb from the loaded data."""
        return PublicWeb(**data)


class PublicWebImage(db.Model):
    """An uploaded image (logo/favicon/preview) belonging to a public web."""

    id = db.Column(db.Integer, primary_key=True)
    web_id = db.Column(db.Integer, db.ForeignKey("public_web.id", ondelete="CASCADE"), nullable=False)
    kind = db.Column(db.String(), nullable=False)
    mime_type = db.Column(db.String())
    filename = db.Column(db.String())
    # Deferred so listing webs never loads the blobs.
    data = orm.deferred(db.Column(db.LargeBinary))

    web = db.relationship("PublicWeb", back_populates="images")

    def __init__(self, web_id: int, kind: str, mime_type: str, filename: str, data: bytes) -> None:
        """Initialize an image."""
        self.web_id = web_id
        self.kind = kind
        self.mime_type = mime_type
        self.filename = filename
        self.data = data


class PublicWeb(db.Model):
    """Model for a public web (one branded feed under a public-web node).

    Attributes:
        id: Unique identifier.
        node_id: The owning public-web node.
        name: Human-readable name (shown in the configuration UI).
        hostname: The public host this web answers on (Host routing + absolute links).
        config: Free-form configuration object (branding, feed sizes, languages).
    """

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey("public_web_node.id"), nullable=False)
    name = db.Column(db.String(), nullable=False)
    hostname = db.Column(db.String())
    config = db.Column(db.JSON, default=dict)
    # A disabled web is not served by the node (omitted from the node-facing list).
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    node = db.relationship("PublicWebNode", back_populates="webs")
    images = db.relationship("PublicWebImage", back_populates="web", cascade="all, delete-orphan")

    def __init__(
        self,
        name: str,
        node_id: int | None = None,
        hostname: str = "",
        config: dict | None = None,
        enabled: bool = True,
        id: int | None = None,  # noqa: A002, ARG002
    ) -> None:
        """Initialize a new PublicWeb (id is auto-assigned)."""
        self.id = None
        self.node_id = node_id
        self.name = name
        self.hostname = hostname
        self.config = config if config is not None else {}
        self.enabled = enabled
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the object for presentation."""
        self.title = self.name
        self.subtitle = self.hostname
        self.tag = "mdi-web"

    # -- queries -----------------------------------------------------------

    @classmethod
    def find(cls, web_id: int) -> PublicWeb | None:
        """Get a web by id."""
        return db.session.get(cls, web_id)

    @classmethod
    def get_for_node(cls, node_id: int, search: str | None = None) -> tuple[list[PublicWeb], int]:
        """Get a node's webs matching an optional search string."""
        query = cls.query.filter_by(node_id=node_id)
        if search:
            search_string = f"%{search}%"
            query = query.filter(or_(cls.name.ilike(search_string), cls.hostname.ilike(search_string)))
        return query.order_by(db.asc(cls.name)).all(), query.count()

    @classmethod
    def get_all_json_for_node(cls, node_id: int, search: str | None = None) -> dict:
        """Get a node's webs as JSON for the configuration UI."""
        webs, count = cls.get_for_node(node_id, search)
        schema = PublicWebPresentationSchema(many=True)
        return {"total_count": count, "items": schema.dump(webs)}

    # -- CRUD --------------------------------------------------------------

    @classmethod
    def add(cls, node_id: int, data: dict) -> PublicWeb:
        """Add a new web to a node."""
        schema = NewPublicWebSchema()
        web = schema.load(data)
        web.node_id = node_id
        db.session.add(web)
        db.session.commit()
        return web

    @classmethod
    def update(cls, web_id: int, data: dict) -> None:
        """Update an existing web."""
        schema = NewPublicWebSchema()
        updated = schema.load(data)
        web = db.session.get(cls, web_id)
        web.name = updated.name
        web.hostname = updated.hostname
        web.config = updated.config if updated.config is not None else {}
        web.enabled = updated.enabled
        db.session.commit()

    @classmethod
    def delete(cls, web_id: int) -> None:
        """Delete a web."""
        web = db.session.get(cls, web_id)
        db.session.delete(web)
        db.session.commit()

    # -- images ------------------------------------------------------------

    def get_image(self, kind: str) -> PublicWebImage | None:
        """Return the image of the given kind, or None."""
        return next((image for image in self.images if image.kind == kind), None)

    def set_image(self, kind: str, mime_type: str, filename: str, data: bytes) -> None:
        """Create or replace the image of the given kind."""
        existing = self.get_image(kind)
        if existing is not None:
            existing.mime_type = mime_type
            existing.filename = filename
            existing.data = data
        else:
            self.images.append(PublicWebImage(self.id, kind, mime_type, filename, data))
        db.session.commit()

    def remove_image(self, kind: str) -> None:
        """Remove the image of the given kind if present."""
        existing = self.get_image(kind)
        if existing is not None:
            db.session.delete(existing)
            db.session.commit()


# Ensure the parent model is registered whenever the public-web model is
# imported, so mapper resolution of the ``node`` relationship works during
# migration-time model initialization.
from model.public_web_node import PublicWebNode  # noqa: E402, F401
