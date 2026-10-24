"""The AI translation glossary: terms to translate consistently, or to keep as written.

The instance glossary (no report type) applies to every translation; a report type's own entries
apply to its reports and labels on top of it. An entry is a term per language
(``{"en": "vulnerability", "cs": "zranitelnost"}``), or a term to keep as written in every
language (``keep``, e.g. a product's or the organisation's name). See ``managers/glossary.py`` for
how entries reach the AI.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import sqlalchemy
from managers import content_language
from managers.db_manager import db
from model.report_item_type import ReportItemType
from shared.common import TZ
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from collections.abc import Iterable

_TERM_LENGTH = 200
_NOTE_LENGTH = 500


def clean_entry(data: object) -> dict:
    """Validate what a glossary form sends.

    Args:
        data (object): The submitted entry.

    Returns:
        dict: ``terms``, ``keep`` and ``note``.

    Raises:
        ValueError: If a language is not a code, a term is too long, or there is nothing to apply:
            a term to keep needs one term, any other entry a term in two languages.
    """
    if not isinstance(data, dict):
        msg = "A glossary entry must be an object"
        raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
    submitted = data.get("terms")
    if not isinstance(submitted, dict):
        msg = "A glossary entry needs its terms per language"
        raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
    terms: dict[str, str] = {}
    for language, term in submitted.items():
        code = content_language.clean_language(language)
        text = str(term or "").strip()
        if code is None or not text:
            continue
        if len(text) > _TERM_LENGTH:
            msg = f"A term has at most {_TERM_LENGTH} characters"
            raise ValueError(msg)
        terms[code] = text
    keep = bool(data.get("keep"))
    if keep and not terms:
        msg = "A term to keep as written needs the term"
        raise ValueError(msg)
    if not keep and len(terms) < 2:  # noqa: PLR2004 - a translation joins two languages
        msg = "A glossary entry needs its term in at least two languages"
        raise ValueError(msg)
    return {"terms": terms, "keep": keep, "note": str(data.get("note") or "").strip()[:_NOTE_LENGTH]}


class GlossaryEntry(db.Model):
    """One glossary term, of the instance or of a report type."""

    __tablename__ = "glossary_entry"

    id = db.Column(db.Integer, primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id", ondelete="CASCADE"), nullable=True, index=True)
    terms = db.Column(JSONB, nullable=False, default=dict, server_default=sqlalchemy.text("'{}'"))
    keep = db.Column(db.Boolean, nullable=False, default=False, server_default=sqlalchemy.false())
    note = db.Column(db.String(_NOTE_LENGTH))
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    def to_dict(self) -> dict:
        """The entry for the configuration screens."""
        return {
            "id": self.id,
            "report_item_type_id": self.report_item_type_id,
            "terms": self.terms or {},
            "keep": self.keep,
            "note": self.note or "",
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_json(cls, report_item_type_id: int | None) -> dict:
        """The entries of a report type, or of the instance when ``report_item_type_id`` is None.

        ``languages`` are those the entries may need a term in: the report languages and label
        languages of that type, or of every type, and any language an entry already has.
        """
        scope = cls.report_item_type_id.is_(None) if report_item_type_id is None else cls.report_item_type_id == report_item_type_id
        items = [entry.to_dict() for entry in cls.query.filter(scope).order_by(cls.id).all()]
        types = ReportItemType.get_all() if report_item_type_id is None else [db.session.get(ReportItemType, report_item_type_id)]
        languages = {code for report_type in types if report_type for code in [*(report_type.languages or []), report_type.label_language]}
        languages.update(code for item in items for code in item["terms"])
        return {"total_count": len(items), "items": items, "languages": sorted(code for code in languages if code)}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> GlossaryEntry:
        """Add an entry to the instance glossary, or to the report type ``data`` names.

        Raises:
            ValueError: If the entry is not valid (see :func:`clean_entry`).
        """
        report_item_type_id = data.get("report_item_type_id") if isinstance(data, dict) else None
        if report_item_type_id is not None and not isinstance(report_item_type_id, int):
            msg = "Not a report type"
            raise ValueError(msg)
        entry = cls(**clean_entry(data), report_item_type_id=report_item_type_id, updated_by=user_name, updated_at=datetime.now(TZ))
        db.session.add(entry)
        db.session.commit()
        return entry

    def update(self, data: dict, user_name: str) -> GlossaryEntry:
        """Change the entry's terms, whether they are kept, and its note; its glossary stays.

        Raises:
            ValueError: If the entry is not valid (see :func:`clean_entry`).
        """
        for field, value in clean_entry(data).items():
            setattr(self, field, value)
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)
        db.session.commit()
        return self

    def delete(self) -> tuple[dict, HTTPStatus]:
        """Remove the entry."""
        db.session.delete(self)
        db.session.commit()
        return {"message": "Glossary entry deleted"}, HTTPStatus.OK

    @classmethod
    def for_report_types(cls, report_item_type_ids: Iterable[int]) -> list[GlossaryEntry]:
        """The entries that apply to translating for these report types, most specific first.

        The report types' own entries come first, in the order given, then the instance's, so an
        entry of a type can override an instance entry for the same term.

        Args:
            report_item_type_ids (Iterable[int]): The report types the texts belong to; none for
                the instance glossary alone.

        Returns:
            list[GlossaryEntry]: The entries.
        """
        type_ids = list(dict.fromkeys(report_item_type_ids))
        entries = cls.query.filter(sqlalchemy.or_(cls.report_item_type_id.is_(None), cls.report_item_type_id.in_(type_ids))).all()
        rank = {type_id: index for index, type_id in enumerate(type_ids)}
        return sorted(entries, key=lambda entry: (rank.get(entry.report_item_type_id, len(rank)), entry.id))
