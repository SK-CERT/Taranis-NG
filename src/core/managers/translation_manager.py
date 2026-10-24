"""Translating report items with AI, on request.

A request names the languages and, optionally, the fields. Without fields, every empty or
outdated translation is filled; a translation a person wrote is only replaced when they asked
for that explicitly. A field somebody else is editing (holds the lock of) is never written.

One field answers in the request. A language or the whole report runs in a background thread,
because a slow provider and several languages easily outlast the request timeout; progress goes
out over SSE, and a Redis key keeps it to one job per report.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from flask import current_app
from managers import content_language, llm_manager
from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.sse_manager import sse_manager
from model.report_item import ReportItem
from model.translation import ORIGIN_AI, ORIGIN_MANUAL, TITLE_FIELDS, ReportItemAttributeTranslation, ReportItemTranslation
from model.user import User
from shared.common import TZ
from shared.log_manager import logger

if TYPE_CHECKING:
    from flask import Flask
    from model.report_item import ReportItemAttribute

JOB_KEY_PREFIX = "report_item_translation_job:"
# Long enough for a big report over a slow provider; a crashed job frees the report after it.
JOB_TTL_SECONDS = 1800


@dataclass
class LanguageResult:
    """What translating one language did."""

    language: str
    translated: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    skipped_locked: list[str] = field(default_factory=list)
    skipped_manual: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for the API and SSE."""
        return {
            "language": self.language,
            "translated": self.translated,
            "failed": self.failed,
            "skipped_locked": self.skipped_locked,
            "skipped_manual": self.skipped_manual,
        }


def check_translatable(report_item: ReportItem, languages: list[str]) -> str | None:
    """Explain why the report cannot be translated into these languages, or return None.

    Args:
        report_item (ReportItem): The report.
        languages (list[str]): The requested languages.

    Returns:
        str | None: The reason.
    """
    if not report_item.language:
        return "Set the report's language before translating it"
    variants = report_item.variant_languages()
    if not variants:
        return "The report type has no other languages"
    unknown = [language for language in languages if language not in variants]
    if unknown:
        return f"The report type is not translated into {', '.join(content_language.language_name(code) for code in unknown)}"
    provider = report_item.report_item_type.translation_ai_provider
    if provider is None:
        return "The report type has no AI provider for translation"
    return llm_manager.tlp_refusal(provider, llm_manager.report_tlp_levels(report_item), "The report")


def _translatable_attributes(report_item: ReportItem) -> list[ReportItemAttribute]:
    return [
        attribute
        for attribute in report_item.attributes
        if attribute.attribute_group_item is not None and attribute.attribute_group_item.is_translated
    ]


def _source_texts(report_item: ReportItem) -> dict[str, tuple[str, object]]:
    """Every translatable source text of the report: key -> (text, the row's owner)."""
    texts: dict[str, tuple[str, object]] = {name: (getattr(report_item, name) or "", report_item) for name in TITLE_FIELDS}
    for attribute in _translatable_attributes(report_item):
        texts[str(attribute.id)] = (attribute.value or "", attribute)
    return texts


def _existing(
    report_item: ReportItem,
    key: str,
    language: str,
    owner: object,
) -> ReportItemTranslation | ReportItemAttributeTranslation | None:
    if key in TITLE_FIELDS:
        return report_item.title_translation(language, key)
    return owner.translation(language)


def locked_keys(report_item_id: int, language: str, user_id: int) -> set[str]:
    """The fields of one language somebody other than ``user_id`` is editing.

    Lock ids of translated fields are ``<field>:<language>`` (``title:cs``, ``123:cs``).

    Args:
        report_item_id (int): The report.
        language (str): The variant.
        user_id (int): Who asks; their own locks do not count.

    Returns:
        set[str]: Field keys ("title", "title_prefix" or an attribute id).
    """
    suffix = f":{language}"
    return {
        field_id.removesuffix(suffix)
        for field_id, lock in sse_manager.get_report_item_locks(report_item_id).items()
        if field_id.endswith(suffix) and str(lock.get("user_id")) != str(user_id)
    }


def select_fields(
    report_item: ReportItem,
    language: str,
    wanted: set[str] | None,
    locked: set[str],
    result: LanguageResult,
    overwrite_manual: bool,
) -> tuple[dict[str, str], dict[str, object]]:
    """Choose the fields to send to the AI, recording the ones skipped in ``result``.

    A field is sent when it has source text and either was asked for by name, or (no names
    given) has no translation yet or an outdated one. A translation a person wrote is only
    replaced with ``overwrite_manual``; a field somebody else is editing never.

    Args:
        report_item (ReportItem): The report.
        language (str): The variant.
        wanted (set[str] | None): The keys asked for; None for "whatever needs it".
        locked (set[str]): Keys other users are editing.
        result (LanguageResult): Collects skipped_manual and skipped_locked.
        overwrite_manual (bool): Replace translations a person wrote, too.

    Returns:
        tuple[dict[str, str], dict[str, object]]: Key to source text, and key to the row's owner.
    """
    texts: dict[str, str] = {}
    owners: dict[str, object] = {}
    for key, (source, owner) in _source_texts(report_item).items():
        if not source.strip() or (wanted is not None and key not in wanted):
            continue
        row = _existing(report_item, key, language, owner)
        if wanted is None and row is not None and row.value and not row.is_outdated(source):
            continue
        if row is not None and row.value and row.origin == ORIGIN_MANUAL and not overwrite_manual:
            result.skipped_manual.append(key)
            continue
        if key in locked:
            result.skipped_locked.append(key)
            continue
        texts[key] = source
        owners[key] = owner
    return texts, owners


def review_language(report_item: ReportItem, language: str, user: User, fields: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Mark the AI translations of one language as reviewed, keeping their text.

    Only translations the AI made and nobody edited count; a field with no source text, no
    translation or somebody else's lock is left alone.

    Args:
        report_item (ReportItem): The report.
        language (str): The variant.
        user (User): Who reviewed them.
        fields (list[str] | None): Only these keys ("title", "title_prefix", attribute ids);
            None for every AI translation of the language.

    Returns:
        tuple[list[str], list[str]]: The keys reviewed, and the keys skipped for a lock.
    """
    wanted = {str(key) for key in fields} if fields is not None else None
    locked = locked_keys(report_item.id, language, user.id)
    reviewed: list[str] = []
    skipped_locked: list[str] = []
    for key, (source, owner) in _source_texts(report_item).items():
        if not source.strip() or (wanted is not None and key not in wanted):
            continue
        row = _existing(report_item, key, language, owner)
        if row is None or not row.value or row.origin != ORIGIN_AI:
            continue
        if key in locked:
            skipped_locked.append(key)
            continue
        row.review(source, user.id)
        reviewed.append(key)
    if reviewed:
        report_item.last_updated = datetime.now(TZ)
        report_item.updated_by = user.name
        db.session.commit()
    return reviewed, skipped_locked


def translate_language(
    report_item: ReportItem,
    language: str,
    user: User,
    fields: list[str] | None = None,
    overwrite_manual: bool = False,
) -> LanguageResult:
    """Translate the report into one language and store what passed the checks.

    Args:
        report_item (ReportItem): The report, its language and provider already checked.
        language (str): The variant.
        user (User): Who asked.
        fields (list[str] | None): Only these keys ("title", "title_prefix", attribute ids);
            None for every empty or outdated field.
        overwrite_manual (bool): Replace translations a person wrote, too.

    Returns:
        LanguageResult: What was translated, failed or skipped.
    """
    result = LanguageResult(language)
    wanted = {str(key) for key in fields} if fields is not None else None
    texts, owners = select_fields(report_item, language, wanted, locked_keys(report_item.id, language, user.id), result, overwrite_manual)

    if not texts:
        return result

    html_keys = [
        key
        for key, owner in owners.items()
        if key not in TITLE_FIELDS and owner.attribute_group_item.attribute.type.name in content_language.HTML_TYPES
    ]
    provider = report_item.report_item_type.translation_ai_provider
    translated, failed = llm_manager.translate_texts(provider, texts, report_item.language, language, html_keys)
    result.failed = failed

    # The texts may have changed or been locked while the provider worked: re-read before writing.
    db.session.expire_all()
    locked = locked_keys(report_item.id, language, user.id)
    current = _source_texts(report_item)
    for key, value in translated.items():
        if key not in current or current[key][0] != texts[key]:
            result.failed[key] = "the source changed while it was being translated"
            continue
        if key in locked:
            result.skipped_locked.append(key)
            continue
        owner = current[key][1]
        row = _existing(report_item, key, language, owner)
        if row is None:
            if key in TITLE_FIELDS:
                row = ReportItemTranslation(language=language, field=key, value="", version=0)
                report_item.translations.append(row)
            else:
                row = ReportItemAttributeTranslation(language=language, value="", version=0)
                owner.translations.append(row)
        elif row.origin == ORIGIN_MANUAL and row.value and not overwrite_manual:
            result.skipped_manual.append(key)
            continue
        row.write(value, texts[key], ORIGIN_AI, user.id)
        result.translated.append(key)
    db.session.commit()
    return result


def translate_report(
    report_item_id: int,
    languages: list[str],
    user: User,
    fields: list[str] | None = None,
    overwrite_manual: bool = False,
) -> list[LanguageResult]:
    """Translate a report into several languages, announcing progress after each.

    Args:
        report_item_id (int): The report.
        languages (list[str]): The variants.
        user (User): Who asked.
        fields (list[str] | None): Only these keys; None for every empty or outdated field.
        overwrite_manual (bool): Replace translations a person wrote, too.

    Returns:
        list[LanguageResult]: One result per language.
    """
    results: list[LanguageResult] = []
    for done, language in enumerate(languages, start=1):
        report_item = ReportItem.find(report_item_id)
        if report_item is None:
            break
        try:
            results.append(translate_language(report_item, language, user, fields, overwrite_manual))
        except llm_manager.LlmError as error:
            results.append(LanguageResult(language, failed={"*": str(error)}))
        sse_manager.report_item_translation_progress(
            {
                "report_item_id": report_item_id,
                "user_id": user.id,
                "done": done,
                "total": len(languages),
                "result": results[-1].to_dict(),
            },
        )
    return results


def _job_key(report_item_id: int) -> str:
    return f"{JOB_KEY_PREFIX}{report_item_id}"


def job_running(report_item_id: int) -> bool:
    """Tell whether a translation job is running for the report.

    Args:
        report_item_id (int): The report.

    Returns:
        bool: True while the job's key exists.
    """
    return bool(redis_client.exists(_job_key(report_item_id)))


def start_job(report_item_id: int, languages: list[str], user: User, overwrite_manual: bool = False) -> bool:
    """Translate a report in the background.

    Args:
        report_item_id (int): The report.
        languages (list[str]): The variants.
        user (User): Who asked.
        overwrite_manual (bool): Replace translations a person wrote, too.

    Returns:
        bool: False when a job for the report is already running.
    """
    if not redis_client.set(_job_key(report_item_id), str(user.id), nx=True, ex=JOB_TTL_SECONDS):
        return False
    app = current_app._get_current_object()  # noqa: SLF001 - the thread needs the app itself
    threading.Thread(
        target=_run_job,
        args=(app, report_item_id, languages, user.id, overwrite_manual),
        name=f"report-item-translation-{report_item_id}",
        daemon=True,
    ).start()
    return True


def _run_job(app: Flask, report_item_id: int, languages: list[str], user_id: int, overwrite_manual: bool) -> None:
    with app.app_context():
        results: list[LanguageResult] = []
        try:
            user = User.find_by_id(user_id)
            if user is not None:
                results = translate_report(report_item_id, languages, user, None, overwrite_manual)
        except Exception as error:
            logger.exception(f"Translating report item {report_item_id} failed: {error}")
        finally:
            db.session.remove()
            redis_client.delete(_job_key(report_item_id))
            # No user_id: the one who asked refreshes too.
            sse_manager.report_item_updated(
                {
                    "report_item_id": report_item_id,
                    "translated": True,
                    "languages": languages,
                    "results": [result.to_dict() for result in results],
                },
            )
