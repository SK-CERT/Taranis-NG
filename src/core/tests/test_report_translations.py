"""Report translations: who may write what, when a translation is stale, and what AI may replace.

The models are built in memory (no database); commits are stubbed. Every model module is
imported first so the mappers can be configured.
"""

from __future__ import annotations

import importlib
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import analyze as analyze_api
from api import config as config_api
from flask import Flask
from managers import translation_manager
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.attribute import Attribute  # noqa: E402 - after every mapper is registered
from model.report_item import ReportItem, ReportItemAttribute  # noqa: E402
from model.report_item_type import AttributeGroup, AttributeGroupItem, ReportItemType  # noqa: E402
from model.translation import (  # noqa: E402
    ORIGIN_AI,
    ORIGIN_MANUAL,
    ReportItemAttributeTranslation,
    ReportItemTranslation,
    source_hash,
)
from shared.schema.attribute import AttributeType  # noqa: E402

USER = SimpleNamespace(id=3, name="Ann Analyst")


@pytest.fixture(autouse=True)
def _no_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db.session, "commit", lambda: None)


def _item(item_id: int, title: str, attribute_type: AttributeType, *, translate: bool = True) -> AttributeGroupItem:
    item = AttributeGroupItem(item_id, title, "", item_id, 0, 1, item_id, None, None, translate=translate)
    item.attribute = Attribute(None, title, "", attribute_type, None, None, None, [])
    return item


def _report(language: str | None = "cs", languages: tuple[str, ...] = ("cs", "en", "sk")) -> ReportItem:
    """A Czech report with a translated description, an untranslated note and a CVE."""
    items = [
        _item(1, "Description", AttributeType.RICH_TEXT),
        _item(2, "Note", AttributeType.TEXT, translate=False),
        _item(3, "CVE", AttributeType.CVE),
    ]
    group = AttributeGroup(None, "Main", "", None, None, 0, items)
    report_type = ReportItemType(None, "Vulnerability", "", [group], languages=list(languages))
    values = ["<p>Útočník může [#ab12cd]</p>", "interní", "CVE-2026-1"]
    attributes = []
    for attribute_id, (item, value) in enumerate(zip(items, values, strict=True), start=10):
        attribute = ReportItemAttribute(None, value, "", None, 0, None, item.id, item.title)
        attribute.id = attribute_id
        attribute.attribute_group_item = item
        attributes.append(attribute)
    report = ReportItem(7, None, "Kritická chyba", "VULN", None, None, [], [], attributes)
    report.report_item_type = report_type
    report.language = language
    return report


def _translate_title(report: ReportItem, language: str, value: str, origin: str = ORIGIN_AI) -> ReportItemTranslation:
    row = ReportItemTranslation(language=language, field="title", value="", version=0)
    row.write(value, report.title, origin, USER.id)
    report.translations.append(row)
    return row


def _translate_attribute(
    attribute: ReportItemAttribute,
    language: str,
    value: str,
    origin: str = ORIGIN_AI,
) -> ReportItemAttributeTranslation:
    row = ReportItemAttributeTranslation(language=language, value="", version=0)
    row.write(value, attribute.value, origin, USER.id)
    attribute.translations.append(row)
    return row


def test_variants_are_the_types_languages_except_the_reports_own() -> None:
    assert _report().variant_languages() == ["en", "sk"]
    assert _report(language=None).variant_languages() == []


def test_only_ticked_text_fields_are_translated() -> None:
    description, note, cve = (attribute.attribute_group_item for attribute in _report().attributes)
    assert description.is_translated
    assert not note.is_translated
    cve.translate = True
    assert not cve.is_translated


def test_a_person_writes_a_translated_name_as_a_manual_translation() -> None:
    report = _report()

    modified, data = ReportItem._update_translation(report, {"update": True, "language": "en", "title": "Critical bug"}, USER)

    assert modified
    row = report.title_translation("en", "title")
    assert (row.value, row.origin, row.version, row.user_id) == ("Critical bug", ORIGIN_MANUAL, 1, USER.id)
    assert row.source_hash == source_hash("Kritická chyba")
    assert data["title"] == ""
    assert data["report_item_id"] == 7
    assert report.title_translations == {"en": {"title": "Critical bug"}}


def test_a_person_writes_a_translated_value_and_gets_its_version() -> None:
    report = _report()
    description = report.attributes[0]

    modified, data = ReportItem._update_translation(
        report,
        {
            "update": True,
            "language": "sk",
            "attribute_id": description.id,
            "attribute_value": "<p>Útočník môže [#ab12cd]</p>",
            "base_version": 0,
        },
        USER,
    )

    assert modified
    assert data["attribute_version"] == 1
    assert description.translation("sk").value == "<p>Útočník môže [#ab12cd]</p>"


def test_a_translation_changed_meanwhile_is_a_conflict_and_nothing_is_written() -> None:
    report = _report()
    description = report.attributes[0]
    _translate_attribute(description, "en", "An attacker can [#ab12cd]")

    modified, data = ReportItem._update_translation(
        report,
        {"update": True, "language": "en", "attribute_id": description.id, "attribute_value": "mine", "base_version": 0},
        USER,
    )

    assert not modified
    assert data["conflict"]["current_value"] == "An attacker can [#ab12cd]"
    assert data["conflict"]["current_version"] == 1
    assert description.translation("en").value == "An attacker can [#ab12cd]"


@pytest.mark.parametrize(
    ("language", "payload", "error"),
    [
        (None, {"title": "x"}, "Set the report's language before translating it"),
        ("cs", {"language": "de", "title": "x"}, "The report type is not translated into German"),
        ("cs", {"attribute_id": 11, "attribute_value": "x"}, "This field is not translated"),
        ("cs", {"attribute_id": 12, "attribute_value": "x"}, "This field is not translated"),
    ],
)
def test_translations_the_report_does_not_have_are_refused(language: str | None, payload: dict, error: str) -> None:
    report = _report(language=language)
    data = {"update": True, "language": "en", **payload}

    modified, data = ReportItem._update_translation(report, data, USER)

    assert not modified
    assert data["error"] == error


def test_a_translation_goes_stale_when_its_source_changes() -> None:
    report = _report()
    description = report.attributes[0]
    _translate_title(report, "en", "Critical bug")
    _translate_attribute(description, "en", "An attacker can [#ab12cd]")

    report.title = "Kritická chyba v jádře"
    state = report.translations_json()

    assert state["translations"]["en"]["title"]["outdated"] is True
    assert state["attributes"][description.id]["en"]["outdated"] is False
    assert state["attributes"][description.id]["en"]["origin"] == ORIGIN_AI


def test_the_reports_language_is_set_but_not_to_one_it_is_translated_into() -> None:
    report = _report(language=None)
    assert ReportItem._set_source_language(report, "cs") is None
    assert report.language == "cs"

    _translate_title(report, "en", "Critical bug")
    assert ReportItem._set_source_language(report, "en") == "The report is already translated into English"
    assert ReportItem._set_source_language(report, None) == "A report's language cannot be unset"
    assert ReportItem._set_source_language(report, "cz") == "Unknown language code: cz"
    assert report.language == "cs"


def test_an_update_notification_carries_the_translated_value() -> None:
    report = _report()
    description = report.attributes[0]
    _translate_attribute(description, "en", "An attacker can [#ab12cd]")

    notification = {"update": True, "language": "en", "attribute_id": str(description.id), "title": ""}
    data = ReportItem._get_updated_translation(report, "en", notification)

    assert data["attribute_value"] == "An attacker can [#ab12cd]"
    assert data["attribute_version"] == 1
    assert data["attribute_translation"]["origin"] == ORIGIN_AI
    assert data["title"] == ""
    assert data["title_translation"] is None


def _select(
    report: ReportItem,
    language: str,
    wanted: set[str] | None = None,
    locked: frozenset[str] = frozenset(),
    *,
    overwrite: bool = False,
) -> tuple:
    result = translation_manager.LanguageResult(language)
    texts, _owners = translation_manager.select_fields(report, language, wanted, set(locked), result, overwrite)
    return texts, result


def test_ai_fills_what_is_missing_and_what_went_stale() -> None:
    report = _report()
    _translate_title(report, "en", "Critical bug")
    stale = _translate_attribute(report.attributes[0], "en", "old")
    stale.source_hash = source_hash("an older source")

    texts, result = _select(report, "en")

    assert set(texts) == {"title_prefix", "10"}
    assert result.skipped_manual == []


def test_ai_keeps_what_a_person_wrote_unless_told_to_replace_it() -> None:
    report = _report()
    manual = _translate_title(report, "en", "Critical bug", origin=ORIGIN_MANUAL)
    manual.source_hash = source_hash("an older source")

    texts, result = _select(report, "en")
    assert "title" not in texts
    assert result.skipped_manual == ["title"]

    texts, result = _select(report, "en", {"title"}, overwrite=True)
    assert texts == {"title": "Kritická chyba"}


def test_ai_never_writes_a_field_somebody_else_is_editing() -> None:
    texts, result = _select(_report(), "en", locked={"10"})

    assert "10" not in texts
    assert result.skipped_locked == ["10"]


def test_named_fields_are_translated_even_when_current() -> None:
    report = _report()
    _translate_title(report, "en", "Critical bug")

    texts, _result = _select(report, "en", {"title"})

    assert texts == {"title": "Kritická chyba"}


def test_only_other_users_locks_of_that_language_count(monkeypatch: pytest.MonkeyPatch) -> None:
    locks = {"title:en": {"user_id": 9}, "10:en": {"user_id": USER.id}, "10:sk": {"user_id": 9}, "title": {"user_id": 9}}
    monkeypatch.setattr(translation_manager.sse_manager, "get_report_item_locks", lambda _report_item_id: locks)

    assert translation_manager.locked_keys(7, "en", USER.id) == {"title"}


def test_a_review_keeps_the_ai_text_as_a_persons_current_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(translation_manager.sse_manager, "get_report_item_locks", lambda _report_item_id: {})
    report = _report()
    title = _translate_title(report, "en", "Critical bug")
    title.source_hash = source_hash("an older name")
    description = _translate_attribute(report.attributes[0], "en", "<p>An attacker can</p>")
    written = _translate_title(report, "sk", "Kritická chyba (sk)", origin=ORIGIN_MANUAL)

    reviewed, skipped = translation_manager.review_language(report, "en", USER)

    assert sorted(reviewed) == ["10", "title"]
    assert skipped == []
    assert (title.value, title.origin, title.is_outdated(report.title), title.version) == ("Critical bug", ORIGIN_MANUAL, False, 2)
    assert (description.value, description.origin) == ("<p>An attacker can</p>", ORIGIN_MANUAL)
    assert written.version == 1
    assert report.updated_by == USER.name


def test_a_review_of_named_fields_leaves_the_rest_and_fields_others_are_editing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(translation_manager.sse_manager, "get_report_item_locks", lambda _report_item_id: {"10:en": {"user_id": 9}})
    report = _report()
    title = _translate_title(report, "en", "Critical bug")
    description = _translate_attribute(report.attributes[0], "en", "<p>An attacker can</p>")
    _translate_title(report, "sk", "Kritická chyba (sk)")

    reviewed, skipped = translation_manager.review_language(report, "en", USER, ["title", "10"])

    assert (reviewed, skipped) == (["title"], ["10"])
    assert (title.origin, description.origin) == (ORIGIN_MANUAL, ORIGIN_AI)
    assert report.title_translation("sk", "title").origin == ORIGIN_AI


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """A bare app and an analyst; SSE goes nowhere."""
    monkeypatch.setattr(analyze_api.auth_manager, "get_user_from_jwt", lambda: USER)
    published: list = []
    monkeypatch.setattr(analyze_api.sse_manager, "report_item_updated", published.append)
    app = Flask(__name__)
    app.published = published
    return app


def _call(app: Flask, resource: object, method: str, body: dict, *args: object) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/", method=method.upper(), json=body):
        return getattr(type(resource), method).__wrapped__.__get__(resource)(*args)


def test_translating_a_report_without_a_provider_is_refused(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _report()
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    payload, status = _call(app, analyze_api.ReportItemTranslate(), "post", {}, 7)

    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "The report type has no AI provider for translation"


def test_translating_above_the_providers_tlp_is_refused(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _report()
    tlp_item = _item(4, "TLP", AttributeType.TLP, translate=False)
    report.report_item_type.attribute_groups[0].attribute_group_items.append(tlp_item)
    tlp_value = ReportItemAttribute(None, "RED", "", None, 0, None, 4, "TLP")
    tlp_value.attribute_group_item = tlp_item
    report.attributes.append(tlp_value)
    report.report_item_type.translation_ai_provider = SimpleNamespace(name="Cloud", max_tlp="GREEN")
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    payload, status = _call(app, analyze_api.ReportItemTranslate(), "post", {}, 7)

    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "The report is TLP:RED, and the AI provider 'Cloud' only accepts up to TLP:GREEN"


def test_fields_of_one_language_are_translated_in_the_request(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _report()
    report.report_item_type.translation_ai_provider = SimpleNamespace(name="Local", max_tlp=None)
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))
    monkeypatch.setattr(translation_manager, "job_running", lambda _id: False)
    calls: list = []

    def translate(
        report_item: ReportItem,
        language: str,
        user: object,
        fields: list,
        overwrite: bool,
    ) -> translation_manager.LanguageResult:
        calls.append((report_item, language, user, fields, overwrite))
        return translation_manager.LanguageResult(language, translated=["title"])

    monkeypatch.setattr(translation_manager, "translate_language", translate)

    payload, status = _call(app, analyze_api.ReportItemTranslate(), "post", {"languages": ["en"], "fields": ["title"]}, 7)

    assert status == HTTPStatus.OK
    assert calls == [(report, "en", USER, ["title"], False)]
    assert payload["results"][0]["translated"] == ["title"]
    assert app.published == [{"report_item_id": 7, "translated": True, "languages": ["en"], "user_id": USER.id}]


def test_a_whole_report_is_translated_in_the_background_once_at_a_time(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _report()
    report.report_item_type.translation_ai_provider = SimpleNamespace(name="Local", max_tlp=None)
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))
    monkeypatch.setattr(translation_manager, "job_running", lambda _id: False)
    started: list = []

    def start_job(*args: object) -> bool:
        started.append(args)
        return len(started) == 1

    monkeypatch.setattr(translation_manager, "start_job", start_job)

    payload, status = _call(app, analyze_api.ReportItemTranslate(), "post", {}, 7)
    assert status == HTTPStatus.ACCEPTED
    assert payload == {"started": True, "languages": ["en", "sk"]}
    assert started == [(7, ["en", "sk"], USER, False)]

    payload, status = _call(app, analyze_api.ReportItemTranslate(), "post", {}, 7)
    assert status == HTTPStatus.CONFLICT


def test_label_translation_needs_a_language_a_provider_and_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    resource = config_api.ReportItemTypeLabelsTranslateResource()
    monkeypatch.setattr(config_api.ai_provider.AiProvider, "find", classmethod(lambda _cls, _id: None))

    assert _call(app, resource, "post", {"texts": ["x"]})[0]["error"] == "texts must map keys to labels"
    assert _call(app, resource, "post", {"texts": {"t": "Title"}, "target_language": "cz"})[0]["error"] == "Unknown language code: cz"
    assert _call(app, resource, "post", {"texts": {"t": "Title"}})[0]["error"] == "target_language is required"
    assert _call(app, resource, "post", {"texts": {"t": "Title"}, "target_language": "cs", "ai_provider_id": 1})[0]["error"] == (
        "Choose an AI provider for translation"
    )


def test_report_type_languages_must_be_language_codes() -> None:
    with pytest.raises(ValueError, match="Unknown language code: cz"):
        ReportItemType(None, "T", "", [], languages=["cs", "cz"])
    report_type = ReportItemType(
        None,
        "T",
        "",
        [],
        languages=["cs", "en", "cs"],
        label_language="",
        translations={"en": {"title": "T", "x": "y"}},
    )
    assert report_type.languages == ["cs", "en"]
    assert report_type.label_language is None
    assert report_type.translations == {"en": {"title": "T"}}


@pytest.mark.parametrize(
    ("language", "body"),
    [("cs", {"language": "de"}), ("cs", {"language": "cs"}), (None, {"language": "en"}), ("cs", {"language": "en", "fields": "title"})],
)
def test_a_review_names_one_of_the_reports_languages(app: Flask, monkeypatch: pytest.MonkeyPatch, language: str | None, body: dict) -> None:
    report = _report(language)
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    _payload, status = _call(app, analyze_api.ReportItemTranslationReview(), "post", body, 7)

    assert status == HTTPStatus.BAD_REQUEST
    assert app.published == []


def test_a_review_answers_with_the_translations_and_tells_the_others(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _report()
    _translate_title(report, "en", "Critical bug")
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))
    monkeypatch.setattr(translation_manager.sse_manager, "get_report_item_locks", lambda _report_item_id: {})
    lists: list = []
    monkeypatch.setattr(analyze_api.sse_manager, "report_items_updated", lambda: lists.append(True))

    payload, status = _call(app, analyze_api.ReportItemTranslationReview(), "post", {"language": "en"}, 7)

    assert status == HTTPStatus.OK
    assert (payload["reviewed"], payload["skipped_locked"]) == (["title"], [])
    assert payload["translations"]["translations"]["en"]["title"]["origin"] == ORIGIN_MANUAL
    assert app.published == [{"report_item_id": 7, "translated": True, "languages": ["en"], "user_id": USER.id}]
    assert lists == [True]

    # Nothing left to review: nobody is told.
    _call(app, analyze_api.ReportItemTranslationReview(), "post", {"language": "en"}, 7)
    assert len(app.published) == 1
