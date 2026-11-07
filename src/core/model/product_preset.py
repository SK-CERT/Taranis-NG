"""Product preset model: what a product is published as.

A product is the content (title, description, reports). A product preset - "Cyberfeed", say - says
where it goes: a named set of deliveries, each a language, a product format (a presenter with
its template) and a publishing channel. A delivery without a channel is a format that is only
previewed or downloaded. Deliveries combine freely: the Czech version to two Mastodon accounts,
the English and the Czech one to one e-mail address (two e-mails), the Slovak one as a PDF and
an HTML file to one SFTP server. A product preset can also put its products on the public web -
all webs, or the ones it lists.

A product picks a product preset, and publishing it runs the preset's deliveries; the analyst can
leave some out of one publish. Access to products is controlled by ACLs on their product preset.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy
from managers import content_language
from managers.db_manager import db
from model.acl_entry import ACLEntry
from model.product_format import ProductFormat
from model.public_web import PublicWeb
from model.publishing_channel import PublishingChannel
from model.tag import ICON_LENGTH, clean_icon
from shared.common import TZ
from shared.schema.acl_entry import ItemType
from shared.schema.product_preset import ProductPresetPresentationSchema, ProductPresetSchema
from sqlalchemy import and_, false, or_, orm
from sqlalchemy.sql.expression import cast

if TYPE_CHECKING:
    from model.user import User

# The icon a product preset and its products show unless the preset names another.
DEFAULT_ICON = "mdi-package-variant-closed"


class ProductPresetValidationError(ValueError):
    """A product preset that cannot be saved; the message is meant for the form."""


class ProductPresetPublicWeb(db.Model):
    """A public web a product preset's products appear on (none listed: every web)."""

    __tablename__ = "product_preset_public_web"

    product_preset_id = db.Column(db.Integer, db.ForeignKey("product_preset.id", ondelete="CASCADE"), primary_key=True)
    # A web a product preset is restricted to cannot be deleted: dropping the last target would
    # turn the restriction into "every web".
    public_web_id = db.Column(db.Integer, db.ForeignKey("public_web.id"), primary_key=True)


class ProductPresetDelivery(db.Model):
    """One delivery of a product preset: a language and a format, and the channel it is sent to.

    Attributes:
        position: Order of the deliveries in the product preset.
        language: The language the product is rendered in (ISO 639-1); None for the language
            the product is written in.
        product_format_id: The format the product is rendered in.
        publishing_channel_id: The channel the rendered product is sent to;
            None for a format that is only previewed.
    """

    __tablename__ = "product_preset_delivery"
    __table_args__ = (
        # NULLS NOT DISTINCT: a format can be listed without a language or a channel once only.
        db.UniqueConstraint(
            "product_preset_id",
            "language",
            "product_format_id",
            "publishing_channel_id",
            name="uq_product_preset_delivery",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_preset_id = db.Column(db.Integer, db.ForeignKey("product_preset.id", ondelete="CASCADE"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    language = db.Column(db.String(8), nullable=True)
    # A format or channel in use cannot be deleted, so a product preset never silently stops
    # sending somewhere.
    product_format_id = db.Column(db.Integer, db.ForeignKey("product_format.id"), nullable=False)
    publishing_channel_id = db.Column(db.String(64), db.ForeignKey("publishing_channel.id"), nullable=True)

    product_format = db.relationship(ProductFormat, lazy="joined", viewonly=True)
    publishing_channel = db.relationship(PublishingChannel, lazy="joined", viewonly=True)

    def __init__(
        self,
        product_format_id: int,
        publishing_channel_id: str | None = None,
        position: int = 0,
        language: str | None = None,
    ) -> None:
        """Initialize a delivery."""
        self.product_format_id = product_format_id
        self.publishing_channel_id = publishing_channel_id
        self.position = position
        self.language = language

    @property
    def key(self) -> tuple[str | None, int, str | None]:
        """What tells deliveries apart: the language, the format and the channel."""
        return (self.language, self.product_format_id, self.publishing_channel_id)

    @property
    def product_format_title(self) -> str | None:
        """The format's title."""
        return self.product_format.title if self.product_format else None

    @property
    def publishing_channel_name(self) -> str | None:
        """The channel's name."""
        return self.publishing_channel.name if self.publishing_channel else None

    @property
    def publisher_type(self) -> str | None:
        """The kind of the channel's publisher (e-mail, SFTP, ...)."""
        publisher = self.publishing_channel.publisher if self.publishing_channel else None
        return publisher.type if publisher else None


class ProductPreset(db.Model):
    """What a product is published as: formats, the channels they go to, and the public web.

    Attributes:
        name: Unique name.
        description: Description.
        icon: The MDI icon it and its products show; None for :data:`DEFAULT_ICON`.
        deliveries: The language/format/channel deliveries, in order.
        public_web_enabled: Whether published products appear on the public web.
        public_webs: The webs they appear on; none listed means every web.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)
    description = db.Column(db.String())
    icon = db.Column(db.String(ICON_LENGTH))
    public_web_enabled = db.Column(db.Boolean(), nullable=False, default=False, server_default=false())
    created = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String())

    deliveries = db.relationship(
        ProductPresetDelivery,
        order_by=ProductPresetDelivery.position,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    public_webs = db.relationship(PublicWeb, secondary="product_preset_public_web", lazy="selectin")

    def __init__(self, name: str, description: str = "", public_web_enabled: bool = False, icon: str | None = None) -> None:
        """Initialize a product preset (the id is assigned by the database)."""
        self.name = name
        self.description = description
        self.public_web_enabled = public_web_enabled
        self.icon = icon
        self.title = name
        self.subtitle = description

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Fill the presentation fields."""
        self.title = self.name
        self.subtitle = self.description

    @property
    def tag(self) -> str:
        """The icon lists show for it and its products."""
        return self.icon or DEFAULT_ICON

    @property
    def public_web_ids(self) -> list[int]:
        """The ids of the webs the product preset's products appear on (empty: every web)."""
        return sorted(web.id for web in self.public_webs)

    @property
    def public_web_names(self) -> list[str]:
        """The names of the webs the product preset's products appear on (empty: every web)."""
        return sorted(web.name or str(web.id) for web in self.public_webs)

    @property
    def web_choices(self) -> list[dict]:
        """The webs a product of it can be shown on, ``{"id", "name"}``: those it lists, else every web.

        None when it keeps its products off the public web. A product may leave some of them out.
        """
        if not self.public_web_enabled:
            return []
        webs = self.public_webs or PublicWeb.query.all()
        return [{"id": web.id, "name": web.name or str(web.id)} for web in sorted(webs, key=lambda web: (web.name or "", web.id))]

    @property
    def formats(self) -> list[ProductFormat]:
        """The distinct formats of the deliveries, in delivery order."""
        formats: dict[int, ProductFormat] = {}
        for delivery in self.deliveries:
            formats.setdefault(delivery.product_format_id, delivery.product_format)
        return list(formats.values())

    def shown_on_web(self, web_id: int | None) -> bool:
        """Whether a published product of this product preset belongs on the web."""
        if not self.public_web_enabled:
            return False
        targets = self.public_web_ids
        return web_id is None or not targets or web_id in targets

    # -- queries -----------------------------------------------------------

    @classmethod
    def find(cls, product_preset_id: int) -> ProductPreset | None:
        """Get a product preset by id."""
        return db.session.get(cls, product_preset_id)

    @classmethod
    def _with_acl(cls, query: sqlalchemy.orm.Query, user: User, see: bool, access: bool, modify: bool) -> sqlalchemy.orm.Query:
        query = query.outerjoin(
            ACLEntry,
            and_(cast(cls.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_PRESET),
        )
        return ACLEntry.apply_query(query, user, see, access, modify)

    @classmethod
    def allowed_with_acl(cls, product_preset_id: int, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check whether the user may see, access or modify the products of a product preset."""
        query = db.session.query(cls.id).distinct().group_by(cls.id).filter(cls.id == product_preset_id)
        return cls._with_acl(query, user, see, access, modify).scalar() is not None

    @classmethod
    def allowed_product_with_acl(cls, product_id: int, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check the user's access to a product, which is the access to its product preset."""
        from model.product import Product  # noqa: PLC0415 - product imports this module

        product = db.session.get(Product, product_id)
        if not product:
            return False
        return cls.allowed_with_acl(product.product_preset_id, user, see, access, modify)

    @classmethod
    def get(cls, search: str | None, user: User | None, acl_check: bool) -> list[ProductPreset]:
        """Get product presets, those the user may see when acl_check is set."""
        query = cls.query.distinct().group_by(cls.id)
        if acl_check:
            query = cls._with_acl(query, user, see=True, access=False, modify=False)
        if search:
            search_string = f"%{search}%"
            query = query.filter(or_(cls.name.ilike(search_string), cls.description.ilike(search_string)))
        return query.order_by(db.asc(cls.name)).all()

    @classmethod
    def get_all_json(cls, search: str | None, user: User | None, acl_check: bool) -> dict:
        """Get product presets as JSON."""
        product_presets = cls.get(search, user, acl_check)
        return {"total_count": len(product_presets), "items": ProductPresetPresentationSchema(many=True).dump(product_presets)}

    # -- changes -----------------------------------------------------------

    @classmethod
    def _checked(cls, data: dict, product_preset_id: int | None = None) -> tuple[dict, list[ProductPresetDelivery], list[PublicWeb]]:
        """Load submitted data and check it can be saved.

        Returns:
            The product preset's fields, its deliveries and its webs.

        Raises:
            ProductPresetValidationError: With what is wrong.
        """
        loaded = ProductPresetSchema().load(data)
        name = (loaded["name"] or "").strip()
        if not name:
            msg = "The product preset needs a name."
            raise ProductPresetValidationError(msg)
        if cls.query.filter(sqlalchemy.func.lower(cls.name) == name.lower(), cls.id != product_preset_id).first() is not None:
            msg = f"A product preset named '{name}' already exists."
            raise ProductPresetValidationError(msg)

        deliveries = []
        keys = set()
        for position, submitted in enumerate(loaded["deliveries"]):
            format_id = submitted["product_format_id"]
            channel_id = submitted.get("publishing_channel_id") or None
            try:
                language = content_language.clean_language(submitted.get("language"))
            except ValueError as error:
                raise ProductPresetValidationError(str(error)) from error
            if db.session.get(ProductFormat, format_id) is None:
                msg = f"Format {format_id} does not exist."
                raise ProductPresetValidationError(msg)
            if channel_id is not None and db.session.get(PublishingChannel, channel_id) is None:
                msg = f"Channel {channel_id} does not exist."
                raise ProductPresetValidationError(msg)
            delivery = ProductPresetDelivery(format_id, channel_id, position, language)
            if delivery.key in keys:
                msg = "A format is listed twice in the same language with the same channel."
                raise ProductPresetValidationError(msg)
            keys.add(delivery.key)
            deliveries.append(delivery)

        webs = []
        for web_id in dict.fromkeys(loaded["public_web_ids"]):
            web = PublicWeb.find(web_id)
            if web is None:
                msg = f"Public web {web_id} does not exist."
                raise ProductPresetValidationError(msg)
            webs.append(web)

        if not deliveries and not loaded["public_web_enabled"]:
            msg = "A product preset needs at least one format, or the public web."
            raise ProductPresetValidationError(msg)

        fields = {
            "name": name,
            "description": loaded.get("description") or "",
            "icon": clean_icon(loaded.get("icon")),
            "public_web_enabled": loaded["public_web_enabled"],
        }
        return fields, deliveries, webs

    @classmethod
    def add(cls, data: dict, user_name: str) -> ProductPreset:
        """Create a product preset.

        Raises:
            ProductPresetValidationError: When it cannot be saved (see :meth:`_checked`).
        """
        fields, deliveries, webs = cls._checked(data)
        product_preset = cls(**fields)
        product_preset.deliveries = deliveries
        product_preset.public_webs = webs
        product_preset.updated_at = datetime.now(TZ)
        product_preset.updated_by = user_name
        db.session.add(product_preset)
        db.session.commit()
        return product_preset

    @classmethod
    def update(cls, product_preset_id: int, data: dict, user_name: str) -> ProductPreset | None:
        """Update a product preset; None when it does not exist.

        Deliveries that stay keep their row; the others are replaced.

        Raises:
            ProductPresetValidationError: When it cannot be saved (see :meth:`_checked`).
        """
        product_preset = cls.find(product_preset_id)
        if product_preset is None:
            return None
        fields, deliveries, webs = cls._checked(data, product_preset_id)
        for key, value in fields.items():
            setattr(product_preset, key, value)

        existing = {delivery.key: delivery for delivery in product_preset.deliveries}
        kept = []
        for delivery in deliveries:
            stored = existing.get(delivery.key)
            if stored is not None:
                stored.position = delivery.position
                kept.append(stored)
            else:
                kept.append(delivery)
        product_preset.deliveries = kept
        product_preset.public_webs = webs
        product_preset.updated_at = datetime.now(TZ)
        product_preset.updated_by = user_name
        db.session.commit()
        return product_preset

    @classmethod
    def delete(cls, product_preset_id: int) -> tuple[dict, int]:
        """Delete a product preset; one that products still use is refused by the database."""
        product_preset = cls.find(product_preset_id)
        if product_preset is None:
            return {"error": "Product preset not found"}, 404
        db.session.delete(product_preset)
        db.session.commit()
        return {"message": "Product preset deleted"}, 200
