"""Product titles in other languages, constant translation, and the publish endpoints that use them.

Titles are saved with the product; one that did not change keeps its source fingerprint, so a
changed original still marks it outdated. Models are built in memory; commits are stubbed.
"""

from __future__ import annotations

import importlib
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import config as config_api
from api import publish as publish_api
from flask import Flask
from managers import llm_manager
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.attribute import AttributeEnum  # noqa: E402 - after every mapper is registered
from model.product import Product  # noqa: E402
from model.translation import ORIGIN_AI, ORIGIN_MANUAL  # noqa: E402

USER = SimpleNamespace(id=3, name="Ann Analyst")


@pytest.fixture(autouse=True)
def _no_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db.session, "commit", lambda: None)
    monkeypatch.setattr(db.session, "rollback", lambda: None)


def _product(language: str | None = "cs") -> Product:
    return Product(-1, "Bulletin", "", 1, None, [], language=language)


def test_titles_are_stored_with_their_origin() -> None:
    product = _product()

    product.apply_translations({"en": {"title": "Bulletin (en)", "origin": ORIGIN_AI}, "sk": {"title": " Bulletin (sk) "}}, USER.id)

    assert product.title_translations == {"en": {"title": "Bulletin (en)"}, "sk": {"title": "Bulletin (sk)"}}
    states = product.translations
    assert (states["en"]["title"]["origin"], states["sk"]["title"]["origin"]) == (ORIGIN_AI, ORIGIN_MANUAL)
    assert states["en"]["title"]["outdated"] is False


def test_an_unchanged_title_stays_outdated_after_the_original_changes() -> None:
    product = _product()
    product.apply_translations({"en": {"title": "Bulletin (en)", "origin": ORIGIN_AI}}, USER.id)

    product.title = "Weekly bulletin"
    product.apply_translations({"en": {"title": "Bulletin (en)", "origin": ORIGIN_AI}}, USER.id)
    assert product.translations["en"]["title"]["outdated"] is True

    product.apply_translations({"en": {"title": "Weekly bulletin (en)", "origin": ORIGIN_MANUAL}}, USER.id)
    assert product.translations["en"]["title"] | {"user": None, "last_updated": None} == {
        "value": "Weekly bulletin (en)",
        "origin": ORIGIN_MANUAL,
        "version": 2,
        "outdated": False,
        "user": None,
        "last_updated": None,
    }


def test_a_language_left_out_is_removed_and_none_keeps_everything() -> None:
    product = _product()
    product.apply_translations({"en": {"title": "Bulletin (en)"}, "sk": {"title": "Bulletin (sk)"}}, USER.id)

    product.apply_translations(None, USER.id)
    assert set(product.title_translations) == {"en", "sk"}

    product.apply_translations({"sk": {"title": "Bulletin (sk)"}, "en": {"title": ""}}, USER.id)
    assert set(product.title_translations) == {"sk"}


@pytest.mark.parametrize(
    ("translations", "error"),
    [
        ({"cs": {"title": "Bulletin"}}, "The product is written in Czech; it cannot also be translated into it"),
        ({"cz": {"title": "Bulletin"}}, "Unknown language code: cz"),
        (["en"], "Product translations must map languages to titles"),
    ],
)
def test_titles_the_product_cannot_have_are_refused(translations: object, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        _product().apply_translations(translations, USER.id)


def test_a_product_language_must_be_a_language_code() -> None:
    with pytest.raises(ValueError, match="Unknown language code: cz"):
        _product(language="cz")


# ---- endpoints -------------------------------------------------------------------------


def _call(app: Flask, resource: object, method: str, body: dict, *args: object) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/", method=method.upper(), json=body):
        return getattr(type(resource), method).__wrapped__.__get__(resource)(*args)


def _report(provider: object, tlp: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(report_item_type=SimpleNamespace(translation_ai_provider=provider), tlp=tlp)


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """A bare app; reports are looked up in a dict and TLP comes from the stand-in."""
    reports = {
        1: _report(None),
        2: _report(SimpleNamespace(name="Local", max_tlp="GREEN"), tlp=["GREEN"]),
        3: _report(SimpleNamespace(name="Local", max_tlp="GREEN"), tlp=["RED"]),
    }
    monkeypatch.setattr(publish_api.ReportItem, "find", classmethod(lambda _cls, item_id: reports.get(item_id)))
    monkeypatch.setattr(llm_manager, "report_tlp_levels", lambda report: report.tlp)
    monkeypatch.setattr(publish_api.auth_manager, "get_user_from_jwt", lambda: USER)
    return Flask(__name__)


def test_a_title_is_translated_with_the_first_report_types_provider(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []

    def translate(provider: object, texts: dict, source: str | None, target: str) -> tuple[dict, dict]:
        calls.append((provider.name, texts, source, target))
        return ({"title": f"[{target}] {texts['title']}"}, {}) if target != "de" else ({}, {"title": "came back empty"})

    monkeypatch.setattr(llm_manager, "translate_texts", translate)

    payload, status = _call(
        app,
        publish_api.ProductTranslateTitle(),
        "post",
        {"title": "Bulletin", "source_language": "cs", "languages": ["en", "cs", "de"], "report_item_ids": [1, 2]},
    )

    assert status == HTTPStatus.OK
    assert payload == {"translations": {"en": "[en] Bulletin"}, "failed": {"de": "came back empty"}}
    assert [call[3] for call in calls] == ["en", "de"]


def test_a_title_is_not_sent_above_the_providers_tlp(app: Flask) -> None:
    payload, status = _call(
        app,
        publish_api.ProductTranslateTitle(),
        "post",
        {"title": "Bulletin", "languages": ["en"], "report_item_ids": [2, 3]},
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "The product's reports is TLP:RED, and the AI provider 'Local' only accepts up to TLP:GREEN"


def test_a_title_needs_a_provider_and_languages(app: Flask) -> None:
    resource = publish_api.ProductTranslateTitle()

    assert _call(app, resource, "post", {"title": "B", "languages": ["en"], "report_item_ids": [1]})[0]["error"] == (
        "None of the product's report types has an AI provider for translation"
    )
    assert _call(app, resource, "post", {"title": "B", "languages": []})[0]["error"] == "languages is required"
    assert _call(app, resource, "post", {"title": " ", "languages": ["en"]})[0]["error"] == "The product has no title to translate"


def test_constants_missing_a_language_are_translated_in_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    enums = [AttributeEnum(index, index, f"Value {index}", "", {"sk": {"value": "hotovo"}} if index == 0 else None) for index in range(3)]
    for index, enum in enumerate(enums):
        enum.id = index + 10
    record = SimpleNamespace(type=SimpleNamespace(name="ENUM"))
    monkeypatch.setattr(config_api.db.session, "get", lambda _model, _id: record)
    monkeypatch.setattr(config_api.attribute.AttributeEnum, "for_attribute", classmethod(lambda _cls, _attribute_id: enums))
    monkeypatch.setattr(config_api.ai_provider.AiProvider, "find", classmethod(lambda _cls, _id: SimpleNamespace(name="Local")))
    monkeypatch.setattr(config_api, "CONSTANTS_PER_TRANSLATION", 1)
    sent: list = []

    def translate(_provider: object, texts: dict, source: str | None, target: str) -> tuple[dict, dict]:
        sent.append((texts, source, target))
        return {key: f"[{target}] {text}" for key, text in texts.items()}, {}

    monkeypatch.setattr(config_api.llm_manager, "translate_texts", translate)

    payload, status = _call(
        Flask(__name__),
        config_api.AttributeEnumsTranslateResource(),
        "post",
        {"language": "sk", "ai_provider_id": 1, "source_language": "cs"},
        5,
    )

    assert status == HTTPStatus.OK
    assert payload == {"translated": 1, "failed": 0, "remaining": 1}
    assert sent == [({"11.value": "Value 1"}, "cs", "sk")]
    assert enums[1].translations == {"sk": {"value": "[sk] Value 1"}}
    assert enums[0].translations == {"sk": {"value": "hotovo"}}


def test_only_choice_constants_are_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_api.db.session, "get", lambda _model, _id: SimpleNamespace(type=SimpleNamespace(name="CWE")))

    payload, status = _call(Flask(__name__), config_api.AttributeEnumsTranslateResource(), "post", {"language": "sk"}, 5)

    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "Only radio, enumeration and multiple choice constants are translated"


def test_a_constant_update_without_translations_keeps_them(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = AttributeEnum(10, 0, "High", "", {"sk": {"value": "Vysoká"}})
    monkeypatch.setattr(db.session, "get", lambda _model, _id: stored)

    AttributeEnum.update(10, [{"id": 10, "index": 0, "value": "High!", "description": ""}])
    assert stored.translations == {"sk": {"value": "Vysoká"}}

    AttributeEnum.update(10, [{"id": 10, "index": 0, "value": "High!", "description": "", "translations": {"sk": {"value": "Vysoká!"}}}])
    assert stored.translations == {"sk": {"value": "Vysoká!"}}


def test_the_language_check_needs_access_to_the_product_type(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    product = SimpleNamespace(product_type_id=4)
    monkeypatch.setattr(publish_api, "load_product", lambda _data, _user, _token: (product, None))
    monkeypatch.setattr(publish_api.content_localizer, "language_check", lambda _product, language: {"missing": [], "language": language})
    monkeypatch.setattr(publish_api.log_manager, "store_auth_error_activity", lambda _message: None)
    allowed: list = []

    def refuse(_cls: object, type_id: int, _user: object, **access: bool) -> bool:
        allowed.append((type_id, access))
        return False

    monkeypatch.setattr(publish_api.ProductType, "allowed_with_acl", classmethod(refuse))
    resource = publish_api.ProductLanguageCheck()

    payload, status = _call(app, resource, "post", {"product": {"id": 5}, "language": "sk"})
    assert (status, payload) == (HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized access attempt to Product Type"})
    assert allowed == [(4, {"see": False, "access": True, "modify": False})]

    monkeypatch.setattr(publish_api.ProductType, "allowed_with_acl", classmethod(lambda _cls, *_args, **_access: True))
    assert _call(app, resource, "post", {"product": {"id": 5}, "language": "sk"}) == ({"missing": [], "language": "sk"}, HTTPStatus.OK)
