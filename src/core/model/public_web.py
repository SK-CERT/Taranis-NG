"""PublicWeb model.

A "public web" is one branded public feed hosted by a :class:`PublicWebNode`,
mirroring how a collectors node hosts multiple collectors. Each web has its own
hostname, its own configuration (branding text, feed sizes, languages, stored as
a free-form JSON object owned by the GUI), and its own images. The public-web
container selects the web to serve per request by the incoming Host header.
"""

from __future__ import annotations

from managers import crypto_manager
from managers.db_manager import db
from marshmallow import post_load
from model.traefik_settings import cert_not_after, cert_subject, check_cert_key_pair
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
        cert_resolver: ACME resolver for this hostname's router. Empty inherits
            the instance-wide value (Application Settings -> Routing & TLS).
        hsts: Strict-Transport-Security for this hostname: "on", "off", or empty
            to inherit the instance-wide policy. Host-scoped, hence per web.
        tls_cert: PEM chain served for this hostname, matched by SNI. Empty falls
            back to the instance default certificate, or to ACME when a resolver
            is set.
        tls_key: The matching private key, encrypted at rest.
    """

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey("public_web_node.id"), nullable=False)
    name = db.Column(db.String(), nullable=False)
    hostname = db.Column(db.String())
    config = db.Column(db.JSON, default=dict)
    # A disabled web is not served by the node (omitted from the node-facing list).
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    cert_resolver = db.Column(db.String())
    hsts = db.Column(db.String())
    tls_cert = db.Column(db.Text())
    tls_key = db.Column(db.Text())

    node = db.relationship("PublicWebNode", back_populates="webs")
    images = db.relationship("PublicWebImage", back_populates="web", cascade="all, delete-orphan")

    def __init__(
        self,
        name: str,
        node_id: int | None = None,
        hostname: str = "",
        config: dict | None = None,
        enabled: bool = True,
        cert_resolver: str | None = "",
        hsts: str | None = "",
        tls_cert: str | None = "",
        tls_key: str | None = "",
        id: int | None = None,  # noqa: A002, ARG002
    ) -> None:
        """Initialize a new PublicWeb (id is auto-assigned)."""
        self.id = None
        self.node_id = node_id
        self.name = name
        self.hostname = hostname
        self.config = config if config is not None else {}
        self.enabled = enabled
        self.cert_resolver = cert_resolver or ""
        self.hsts = hsts or ""
        self.tls_cert = tls_cert or ""
        self.tls_key = tls_key or ""
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
    def get_all_enabled(cls) -> list[PublicWeb]:
        """Every enabled web across all nodes, whoever fronts them."""
        return cls.query.filter_by(enabled=True).order_by(db.asc(cls.id)).all()

    @classmethod
    def get_enabled_fronted_by_core(cls) -> list[PublicWeb]:
        """Enabled webs that CORE's own Traefik should publish.

        Drives the unscoped provider route, which core's Traefik polls over the compose
        network. Not :meth:`get_all_enabled`: core's Traefik requests an ACME
        certificate for every hostname it is given, so a remote node's web made it ask
        its own CA account for a name it does not serve - refused by a CA that
        pre-validates domains, then retried indefinitely - while the owning node claimed
        that same hostname.

        Returns:
            (list[PublicWeb]): Enabled webs whose node is fronted by core.
        """
        return cls.query.join(cls.node).filter(cls.enabled.is_(True), PublicWebNode.fronted_by_core.is_(True)).order_by(db.asc(cls.id)).all()

    @classmethod
    def get_enabled_for_node(cls, node_id: int) -> list[PublicWeb]:
        """One node's enabled webs (drives the per-node Traefik provider).

        A remote node's Traefik must never be handed another node's hostnames or, more
        to the point, the private keys inlined beside them - so the payload it polls is
        built from this, not from :meth:`get_all_enabled`.

        Args:
            node_id (int): The owning node.

        Returns:
            (list[PublicWeb]): The node's enabled webs, in the same order as
                :meth:`get_all_enabled`.
        """
        return cls.query.filter_by(enabled=True, node_id=node_id).order_by(db.asc(cls.id)).all()

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
        _apply_certificate(web, web.tls_cert, web.tls_key)
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
        web.cert_resolver = updated.cert_resolver or ""
        web.hsts = updated.hsts or ""
        _apply_certificate(web, updated.tls_cert, updated.tls_key)
        db.session.commit()

    @classmethod
    def delete(cls, web_id: int) -> None:
        """Delete a web."""
        web = db.session.get(cls, web_id)
        db.session.delete(web)
        db.session.commit()

    @property
    def has_tls_key(self) -> bool:
        """Whether a private key is stored (the key itself is never exposed)."""
        return bool(self.tls_key)

    @property
    def tls_cert_subject(self) -> str:
        """Subject of this web's certificate, for display."""
        return cert_subject(self.tls_cert)

    @property
    def tls_cert_not_after(self) -> str:
        """Expiry of this web's certificate, for display."""
        return cert_not_after(self.tls_cert)

    def get_tls_key_plaintext(self) -> str:
        """Return the decrypted private key, or an empty string when there is none."""
        if not self.tls_key:
            return ""
        return crypto_manager.decrypt(self.tls_key) or ""

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


def _apply_certificate(web: PublicWeb, certificate: str | None, key: str | None) -> None:
    """Store this web's certificate, validating the pair before it reaches Traefik.

    Traefik would accept a mismatched pair into its configuration and only fail in
    the handshake, on every request to that hostname - so it is checked here, where
    the message can reach the form. An empty key keeps the stored one, the same rule
    the instance-wide certificate and the auth-provider secrets follow.

    Args:
        web (PublicWeb): The row to update.
        certificate (str | None): PEM chain, or empty to clear.
        key (str | None): PEM private key, or empty to keep the stored one.

    Raises:
        ValueError: When the pair is unreadable or does not belong together.
    """
    certificate = (certificate or "").strip()
    key = (key or "").strip()

    if not certificate:
        # A key alone is unusable, and leaving it behind keeps a secret nobody can see.
        web.tls_cert = ""
        web.tls_key = ""
        return

    plaintext_key = key or web.get_tls_key_plaintext()
    if not plaintext_key:
        msg = "A certificate needs its private key"
        raise ValueError(msg)
    check_cert_key_pair(certificate, plaintext_key)
    # Normalised to exactly one trailing newline: PEM is whitespace-sensitive.
    web.tls_cert = certificate + "\n"
    if key:
        web.tls_key = crypto_manager.encrypt(key + "\n")


# Deferred to the bottom to break the circular import with public_web_node, which
# imports this module for the relationship on its side. Used at runtime by
# get_enabled_fronted_by_core, and by SQLAlchemy to resolve the mapper by name.
from model.public_web_node import PublicWebNode  # noqa: E402
