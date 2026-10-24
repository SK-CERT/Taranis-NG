"""The AI translation glossary: what an entry may hold, which entries reach the AI, and how.

An entry applies when its term occurs in the texts (ignoring case, and inside longer, inflected
words); a report type's own entries come first and override the instance's; the answer is not
checked against them. A stand-in chat model is used; nothing is sent anywhere.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import config as config_api
from flask import Flask
from managers import glossary, llm_manager

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.glossary import GlossaryEntry, clean_entry  # noqa: E402 - after every mapper is registered
from model.report_item_type import ReportItemType  # noqa: E402

PROVIDER = SimpleNamespace(name="Local", api_type="openai", model="m", api_key="k", api_url="http://ai.example.test", max_tlp=None)


def _entry(terms: dict, *, keep: bool = False, note: str = "", type_id: int | None = None, entry_id: int = 1) -> GlossaryEntry:
    entry = GlossaryEntry(terms=terms, keep=keep, note=note, report_item_type_id=type_id)
    entry.id = entry_id
    return entry


def test_an_entry_has_terms_in_two_languages_or_one_term_to_keep() -> None:
    assert clean_entry({"terms": {"cs": " zranitelnost ", "en": "vulnerability", "sk": ""}, "note": " domain term "}) == {
        "terms": {"cs": "zranitelnost", "en": "vulnerability"},
        "keep": False,
        "note": "domain term",
    }
    assert clean_entry({"terms": {"en": "Taranis NG"}, "keep": True})["terms"] == {"en": "Taranis NG"}
    with pytest.raises(ValueError, match="at least two languages"):
        clean_entry({"terms": {"en": "vulnerability"}})
    with pytest.raises(ValueError, match="needs the term"):
        clean_entry({"terms": {}, "keep": True})
    with pytest.raises(ValueError, match="Unknown language code: cz"):
        clean_entry({"terms": {"cz": "zranitelnost", "en": "vulnerability"}})
    with pytest.raises(ValueError, match="at most 200"):
        clean_entry({"terms": {"en": "x" * 201}, "keep": True})


def test_an_entry_applies_when_its_source_term_occurs_even_inflected() -> None:
    entries = [_entry({"cs": "zranitelnost", "en": "vulnerability"}), _entry({"cs": "záplata", "en": "patch"}, entry_id=2)]

    lines = glossary.glossary_lines(entries, ["Kritické ZRANITELNOSTI v jádře"], "cs", "en")

    assert lines == ["Translate «zranitelnost» as «vulnerability»."]


def test_a_term_to_keep_matches_in_any_language_and_notes_go_along() -> None:
    entries = [_entry({"en": "Taranis NG"}, keep=True, note="our product")]

    assert glossary.glossary_lines(entries, ["Nová verze Taranis NG"], "cs", "sk") == ["Keep «Taranis NG» exactly as written. (our product)"]


def test_without_a_term_in_the_target_language_an_entry_says_nothing() -> None:
    assert glossary.glossary_lines([_entry({"cs": "zranitelnost", "en": "vulnerability"})], ["zranitelnost"], "cs", "sk") == []


def test_a_source_of_no_known_language_matches_every_term() -> None:
    entries = [_entry({"cs": "zranitelnost", "en": "vulnerability", "sk": "zraniteľnosť"})]

    assert glossary.glossary_lines(entries, ["a vulnerability"], None, "sk") == ["Translate «vulnerability» as «zraniteľnosť»."]


def test_the_report_types_entry_overrides_the_instances_for_the_same_term() -> None:
    own = _entry({"cs": "záplata", "en": "fix"}, type_id=9)
    instance = _entry({"cs": "záplata", "en": "patch"}, entry_id=2)

    assert glossary.glossary_lines([own, instance], ["Vydána záplata"], "cs", "en") == ["Translate «záplata» as «fix»."]


def test_a_prompt_carries_at_most_fifty_entries() -> None:
    entries = [_entry({"en": f"Term{index}"}, keep=True, entry_id=index) for index in range(60)]

    lines = glossary.glossary_lines(entries, [" ".join(f"Term{index}" for index in range(60))], "en", "cs")

    assert len(lines) == glossary.MAX_ENTRIES


def test_the_glossary_goes_into_the_instructions_of_the_chunks_it_occurs_in(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[str] = []

    class Model:
        def invoke(self, messages: list) -> SimpleNamespace:
            requests.append(messages[0].content)
            texts = json.loads(messages[-1].content)
            return SimpleNamespace(content=json.dumps({key: f"[en] {text}" for key, text in texts.items()}))

    monkeypatch.setattr(llm_manager, "build_chat_model", lambda _provider: Model())
    entries = [_entry({"cs": "zranitelnost", "en": "vulnerability"})]

    llm_manager.translate_texts(PROVIDER, {"title": "Zranitelnost v jádře"}, "cs", "en", glossary=entries)
    llm_manager.translate_texts(PROVIDER, {"title": "Nic"}, "cs", "en", glossary=entries)

    assert "Glossary - use these terms:\n- Translate «zranitelnost» as «vulnerability»." in requests[0]
    assert "Glossary" not in requests[1]


class _Query:
    def __init__(self, entries: list) -> None:
        self.entries = entries

    def filter(self, *_conditions: object) -> _Query:
        return self

    def order_by(self, *_columns: object) -> _Query:
        return self

    def all(self) -> list:
        return self.entries


def test_a_report_types_own_entries_come_before_the_instances() -> None:
    instance = _entry({"en": "A"}, keep=True, entry_id=1)
    second_type = _entry({"en": "B"}, keep=True, type_id=8, entry_id=2)
    first_type = _entry({"en": "C"}, keep=True, type_id=9, entry_id=3)
    # Model.query needs an app to read, so monkeypatch can't save it; it lives on db.Model, though.
    assert "query" not in vars(GlossaryEntry)
    GlossaryEntry.query = _Query([instance, second_type, first_type])
    try:
        assert [entry.id for entry in GlossaryEntry.for_report_types([9, 8, 9])] == [3, 2, 1]
    finally:
        del GlossaryEntry.query


def test_the_instance_glossary_offers_every_report_and_label_language(monkeypatch: pytest.MonkeyPatch) -> None:
    types = [SimpleNamespace(languages=["sk", "en"], label_language="cs"), SimpleNamespace(languages=[], label_language=None)]
    monkeypatch.setattr(ReportItemType, "get_all", classmethod(lambda _cls: types))
    GlossaryEntry.query = _Query([_entry({"de": "Schwachstelle", "en": "vulnerability"})])
    try:
        listed = GlossaryEntry.get_json(None)
    finally:
        del GlossaryEntry.query

    assert listed["languages"] == ["cs", "de", "en", "sk"]
    assert [item["terms"] for item in listed["items"]] == [{"de": "Schwachstelle", "en": "vulnerability"}]


def test_an_invalid_entry_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: SimpleNamespace(name="Admin"))
    monkeypatch.setattr(config_api.db.session, "rollback", lambda: None)
    resource = config_api.GlossaryEntriesResource()
    with Flask(__name__).test_request_context("/", method="POST", json={"terms": {"en": "vulnerability"}}):
        payload, status = type(resource).post.__wrapped__(resource)

    assert status == HTTPStatus.BAD_REQUEST
    assert "two languages" in payload["error"]


MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "8b3f5c1d7e24_glossary.py"


def test_the_glossary_migration_follows_the_tags_and_matches_the_model() -> None:
    spec = importlib.util.spec_from_file_location("glossary_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (module.revision, module.down_revision) == ("8b3f5c1d7e24", "6e1d4b8a2f97")
    revises = re.compile(r'^down_revision = "6e1d4b8a2f97"$', re.MULTILINE)
    assert [path.name for path in MIGRATION.parent.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))] == [MIGRATION.name]
    assert GlossaryEntry.__tablename__ == module.TABLE
    assert module.INDEX in {index.name for index in GlossaryEntry.__table__.indexes}
    assert "if TABLE not in" in MIGRATION.read_text(encoding="utf-8")
