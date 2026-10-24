"""Tags: labels admins define for reports and products, and the built-in translation status tags.

People put admin tags on items; they are stored in ``report_item_tag`` and ``product_tag``.
System tags (``system_key`` set) are never stored on an item: Taranis works out which apply
(``managers/translation_status.py``), so they cannot go stale. Admins may restyle and rename
system tags and switch them off per entity type, but not delete them or put them on an item.

A system tag's ``display_name`` starts as its key, which the GUI translates
(``workflow.tags.system.<key>``), the way system states are shown; a name an admin gives it is
shown as written.
"""

from __future__ import annotations

import re
from datetime import datetime
from http import HTTPStatus

from managers.db_manager import db
from model.state import StateEntityTypeEnum
from shared.common import TZ

# The translation status of an item in one language, and an item whose language is not set.
TRANSLATION_MISSING = "translation_missing"
TRANSLATION_PARTIAL = "translation_partial"
TRANSLATION_OUTDATED = "translation_outdated"
TRANSLATION_AI = "translation_ai"
TRANSLATION_DONE = "translation_done"
LANGUAGE_NOT_SET = "language_not_set"
SYSTEM_KEYS = (TRANSLATION_MISSING, TRANSLATION_PARTIAL, TRANSLATION_OUTDATED, TRANSLATION_AI, TRANSLATION_DONE, LANGUAGE_NOT_SET)

ENTITY_TYPES = (StateEntityTypeEnum.REPORT_ITEM.value, StateEntityTypeEnum.PRODUCT.value)

_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
_NAME_LENGTH = 100
_DESCRIPTION_LENGTH = 500
_ICON_LENGTH = 50

report_item_tag = db.Table(
    "report_item_tag",
    db.Column("report_item_id", db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    db.Column("created", db.DateTime, nullable=True),
)

product_tag = db.Table(
    "product_tag",
    db.Column("product_id", db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    db.Column("created", db.DateTime, nullable=True),
)

# Which assignment table holds the tags of each entity type, and the column naming the item.
_ASSIGNMENTS = {
    StateEntityTypeEnum.REPORT_ITEM.value: (report_item_tag, "report_item_id"),
    StateEntityTypeEnum.PRODUCT.value: (product_tag, "product_id"),
}


def clean_tag(data: object, *, system: bool = False) -> dict:
    """Validate what a tag form sends.

    Args:
        data (object): The submitted tag.
        system (bool): Whether it is a system tag; it has no other rules, but no key can be sent.

    Returns:
        dict: ``display_name``, ``description``, ``color`` and ``icon``.

    Raises:
        ValueError: If a field is missing, too long or malformed.
    """
    if not isinstance(data, dict):
        msg = "A tag must be an object"
        raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
    name = str(data.get("display_name") or "").strip()
    if not name:
        msg = "A tag needs a name"
        raise ValueError(msg)
    if len(name) > _NAME_LENGTH:
        msg = f"A tag name has at most {_NAME_LENGTH} characters"
        raise ValueError(msg)
    description = str(data.get("description") or "").strip()[:_DESCRIPTION_LENGTH]
    color = str(data.get("color") or "").strip()
    if color and not _COLOR.fullmatch(color):
        msg = f"Not a colour: {color}"
        raise ValueError(msg)
    icon = str(data.get("icon") or "").strip()[:_ICON_LENGTH]
    if data.get("system_key") and not system:
        msg = "System tags are built in"
        raise ValueError(msg)
    return {"display_name": name, "description": description, "color": color or None, "icon": icon or None}


class Tag(db.Model):
    """A tag admins define, or a built-in one (``system_key`` set)."""

    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(_NAME_LENGTH), nullable=False)
    description = db.Column(db.String(_DESCRIPTION_LENGTH))
    color = db.Column(db.String(7))
    icon = db.Column(db.String(_ICON_LENGTH))
    system_key = db.Column(db.String(50), unique=True, nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    entity_types = db.relationship("TagEntityType", back_populates="tag", cascade="all, delete-orphan", passive_deletes=True)

    @property
    def is_system(self) -> bool:
        """Whether Taranis sets this tag, rather than people."""
        return self.system_key is not None

    def to_dict(self) -> dict:
        """The tag for the configuration screens."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "system_key": self.system_key,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_all_json(cls, search: str | None = None) -> dict:
        """Every tag, the built-in ones last.

        Args:
            search (str | None): Text the name or description contains.

        Returns:
            dict: ``{"total_count", "items"}``.
        """
        query = cls.query
        if search:
            query = query.filter(db.or_(cls.display_name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%")))
        tags = query.order_by(cls.system_key.isnot(None), cls.display_name).all()
        return {"total_count": len(tags), "items": [tag.to_dict() for tag in tags]}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> Tag:
        """Create an admin tag.

        Raises:
            ValueError: If the form is not valid (see :func:`clean_tag`).
        """
        tag = cls(**clean_tag(data), updated_by=user_name, updated_at=datetime.now(TZ))
        db.session.add(tag)
        db.session.commit()
        return tag

    def update(self, data: dict, user_name: str) -> Tag:
        """Rename or restyle the tag; a system tag keeps its key.

        Raises:
            ValueError: If the form is not valid (see :func:`clean_tag`).
        """
        for field, value in clean_tag(data, system=self.is_system).items():
            setattr(self, field, value)
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)
        db.session.commit()
        return self

    def usage(self) -> int:
        """How many reports and products carry this tag."""
        return sum(
            db.session.execute(db.select(db.func.count()).select_from(table).where(table.c.tag_id == self.id)).scalar_one()
            for table, _column in _ASSIGNMENTS.values()
        )

    def delete(self) -> tuple[dict, HTTPStatus]:
        """Delete an admin tag no item carries."""
        if self.is_system:
            return {"error": "Built-in tags cannot be deleted; switch them off in Tag Workflow instead"}, HTTPStatus.FORBIDDEN
        count = self.usage()
        if count:
            return {"error": "The tag is still on reports or products", "usage_count": count}, HTTPStatus.CONFLICT
        db.session.delete(self)
        db.session.commit()
        return {"message": "Tag deleted"}, HTTPStatus.OK

    @classmethod
    def offered(cls, entity_type: str) -> list[dict]:
        """The tags active for an entity type, in their order, for lists, pickers and filters.

        Args:
            entity_type (str): ``report_item`` or ``product``.

        Returns:
            list[dict]: Each tag with its ``system_key`` and ``sort_order``.
        """
        rows = (
            db.session.query(cls, TagEntityType)
            .join(TagEntityType, TagEntityType.tag_id == cls.id)
            .filter(TagEntityType.entity_type == entity_type, TagEntityType.is_active.is_(True))
            .order_by(TagEntityType.sort_order, cls.display_name)
            .all()
        )
        return [{**tag.to_dict(), "sort_order": link.sort_order} for tag, link in rows]

    @classmethod
    def assignable(cls, entity_type: str, tag_ids: object) -> list[int]:
        """Check the tags a person puts on an item: admin tags active for its entity type.

        Args:
            entity_type (str): ``report_item`` or ``product``.
            tag_ids (object): The submitted tag ids.

        Returns:
            list[int]: The ids, without repeats.

        Raises:
            ValueError: If one is not an id of such a tag.
        """
        if tag_ids is None:
            return []
        if not isinstance(tag_ids, list) or not all(isinstance(tag_id, int) and not isinstance(tag_id, bool) for tag_id in tag_ids):
            msg = "Tags must be a list of tag ids"
            raise ValueError(msg)
        wanted = list(dict.fromkeys(tag_ids))
        offered = {tag["id"] for tag in cls.offered(entity_type) if tag["system_key"] is None}
        refused = [tag_id for tag_id in wanted if tag_id not in offered]
        if refused:
            msg = f"These tags cannot be put on this item: {', '.join(map(str, refused))}"
            raise ValueError(msg)
        return wanted


def set_item_tags(entity_type: str, item_id: int, tag_ids: list[int], user_id: int | None) -> None:
    """Make ``tag_ids`` the admin tags of an item, keeping who added the ones it already had.

    The caller has checked them with :meth:`Tag.assignable`, and commits.

    Args:
        entity_type (str): ``report_item`` or ``product``.
        item_id (int): The report or product.
        tag_ids (list[int]): Its tags from now on.
        user_id (int | None): Who adds the new ones.
    """
    table, column = _ASSIGNMENTS[entity_type]
    item = table.c[column]
    current = set(db.session.execute(db.select(table.c.tag_id).where(item == item_id)).scalars())
    removed = current - set(tag_ids)
    if removed:
        db.session.execute(table.delete().where(item == item_id, table.c.tag_id.in_(removed)))
    added = [tag_id for tag_id in tag_ids if tag_id not in current]
    if added:
        now = datetime.now(TZ)
        db.session.execute(table.insert(), [{column: item_id, "tag_id": tag_id, "user_id": user_id, "created": now} for tag_id in added])


class TagEntityType(db.Model):
    """Which tags reports and products use (Tag Workflow), in which order, and whether shown."""

    __tablename__ = "tag_entity_type"

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tag.id", ondelete="CASCADE"), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    tag = db.relationship(Tag, back_populates="entity_types")

    __table_args__ = (db.UniqueConstraint("tag_id", "entity_type", name="uq_tag_entity_type"),)

    def to_dict(self) -> dict:
        """The link for the Tag Workflow screen, with its tag."""
        return {
            "id": self.id,
            "tag_id": self.tag_id,
            "entity_type": self.entity_type,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "tag": self.tag.to_dict() if self.tag else None,
        }

    @staticmethod
    def _clean(data: object) -> dict:
        if not isinstance(data, dict):
            msg = "A tag link must be an object"
            raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
        if data.get("entity_type") not in ENTITY_TYPES:
            msg = f"Tags are for: {', '.join(ENTITY_TYPES)}"
            raise ValueError(msg)
        try:
            sort_order = int(data.get("sort_order") or 0)
        except (TypeError, ValueError) as error:
            msg = "The order must be a number"
            raise ValueError(msg) from error
        return {"entity_type": data["entity_type"], "is_active": bool(data.get("is_active", True)), "sort_order": sort_order}

    @classmethod
    def get_all_json(cls, entity_type: str | None = None) -> dict:
        """Every link, of one entity type when given."""
        query = cls.query
        if entity_type:
            query = query.filter(cls.entity_type == entity_type)
        links = query.order_by(cls.entity_type, cls.sort_order).all()
        return {"total_count": len(links), "items": [link.to_dict() for link in links]}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> TagEntityType:
        """Link a tag to an entity type.

        Raises:
            ValueError: If the tag does not exist or the link is not valid.
        """
        fields = cls._clean(data)
        tag = db.session.get(Tag, data.get("tag_id")) if isinstance(data.get("tag_id"), int) else None
        if tag is None:
            msg = "No such tag"
            raise ValueError(msg)
        link = cls(tag_id=tag.id, **fields, updated_by=user_name, updated_at=datetime.now(TZ))
        db.session.add(link)
        db.session.commit()
        return link

    def update(self, data: dict, user_name: str) -> TagEntityType:
        """Change whether the link is active and its order; its tag and entity type stay.

        Raises:
            ValueError: If the link is not valid.
        """
        fields = self._clean({**data, "entity_type": self.entity_type})
        self.is_active = fields["is_active"]
        self.sort_order = fields["sort_order"]
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)
        db.session.commit()
        return self

    def delete(self) -> tuple[dict, HTTPStatus]:
        """Unlink an admin tag; a built-in tag's link can only be switched off."""
        if self.tag is not None and self.tag.is_system:
            return {"error": "Built-in tags stay linked; switch them off instead"}, HTTPStatus.FORBIDDEN
        db.session.delete(self)
        db.session.commit()
        return {"message": "Tag link deleted"}, HTTPStatus.OK
