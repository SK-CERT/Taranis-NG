"""Translations of report content into the language variants of its report type.

A report is written in one language (``report_item.language``). Its report type lists the
languages it is translated into, and each translation is one row: the translated name or name
prefix of a report (``report_item_translation``), or the translated value of one attribute
(``report_item_attribute_translation``).

Every row remembers a hash of the source text it was made from. When the source changes later,
the hash no longer matches and the translation is *outdated*: still shown, but marked, so
somebody can bring it up to date. ``origin`` tells whether the AI or a person wrote it, and
``version`` protects a translation against concurrent edits the same way attribute versions do.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from managers.db_manager import db
from shared.common import TZ
from sqlalchemy.orm import declared_attr

ORIGIN_AI = "ai"
ORIGIN_MANUAL = "manual"

# The report fields that are translated besides attribute values.
TITLE_FIELDS = ("title", "title_prefix")


def source_hash(text: str | None) -> str:
    """Fingerprint of a source text, stored with its translation to tell when it went stale.

    Args:
        text (str | None): The source text; None counts as empty.

    Returns:
        str: The hex SHA-256 of the text.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class TranslationMixin:
    """The columns every translation row has."""

    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(8), nullable=False)
    value = db.Column(db.String(), nullable=False, default="")
    source_hash = db.Column(db.String(64), nullable=False, default="")
    origin = db.Column(db.String(8), nullable=False, default=ORIGIN_MANUAL)
    version = db.Column(db.Integer, nullable=False, default=1)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(TZ))

    @declared_attr
    def user_id(cls):  # noqa: ANN201, N805 - declared_attr passes the mapped class; an annotation would be read as a mapping
        """The user who wrote the translation, or asked the AI to."""
        return db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def user(cls):  # noqa: ANN201, N805 - declared_attr passes the mapped class; an annotation would be read as a mapping
        """The user who wrote the translation, or asked the AI to."""
        return db.relationship("User")

    def is_outdated(self, source: str | None) -> bool:
        """Tell whether the source changed since this translation was made.

        Args:
            source (str | None): The current source text.

        Returns:
            bool: True when the translation was made from a different text.
        """
        return self.source_hash != source_hash(source)

    def write(self, value: str, source: str | None, origin: str, user_id: int | None) -> None:
        """Store a new translated text made from ``source``.

        Args:
            value (str): The translated text.
            source (str | None): The source text it translates.
            origin (str): ORIGIN_AI or ORIGIN_MANUAL.
            user_id (int | None): Who wrote it, or asked the AI to.
        """
        self.value = value or ""
        self.source_hash = source_hash(source)
        self.origin = origin
        self.user_id = user_id
        self.last_updated = datetime.now(TZ)
        self.version = (self.version or 0) + 1

    def review(self, source: str | None, user_id: int | None) -> None:
        """Confirm the text as a person's translation of ``source``, unchanged.

        A reviewed AI translation counts as written by ``user_id``, and was checked against the
        current source, so it is no longer outdated either.

        Args:
            source (str | None): The current source text.
            user_id (int | None): Who reviewed it.
        """
        self.write(self.value, source, ORIGIN_MANUAL, user_id)

    def to_dict(self, source: str | None) -> dict:
        """Serialize for the GUI, with whether it went stale against ``source``.

        Args:
            source (str | None): The current source text.

        Returns:
            dict: value, origin, version, outdated, user and last_updated.
        """
        return {
            "value": self.value,
            "origin": self.origin,
            "version": self.version or 1,
            "outdated": self.is_outdated(source),
            "user": self.user.name if self.user else None,
            "last_updated": self.last_updated.strftime("%d.%m.%Y - %H:%M") if self.last_updated else None,
        }


class ReportItemTranslation(TranslationMixin, db.Model):
    """The translated name or name prefix of a report item in one language."""

    __tablename__ = "report_item_translation"
    __table_args__ = (db.UniqueConstraint("report_item_id", "language", "field", name="uq_report_item_translation"),)

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=False, index=True)
    field = db.Column(db.String(16), nullable=False)


class ReportItemAttributeTranslation(TranslationMixin, db.Model):
    """The translated value of one report item attribute in one language."""

    __tablename__ = "report_item_attribute_translation"
    __table_args__ = (db.UniqueConstraint("report_item_attribute_id", "language", name="uq_report_item_attribute_translation"),)

    report_item_attribute_id = db.Column(
        db.Integer,
        db.ForeignKey("report_item_attribute.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
