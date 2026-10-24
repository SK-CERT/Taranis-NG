"""AI answers are only kept when they are complete and keep their citations, and TLP limits hold.

A provider's answer is untrusted: report texts partly come from collected news, so a prompt
injection can steer it. These tests use a stand-in chat model; nothing is sent anywhere.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from managers import content_language, llm_manager, tlp

PROVIDER = SimpleNamespace(name="Local", api_type="openai", model="m", api_key="k", api_url="http://ai.example.test", max_tlp=None)


class FakeModel:
    """Answers each request with a function of the texts it was sent."""

    def __init__(self, answer: object) -> None:
        """Remember the answer, a string or a function of the texts."""
        self.answer = answer
        self.requests: list[dict] = []

    def invoke(self, messages: list) -> SimpleNamespace:
        """Answer like a chat model, recording the request."""
        texts = json.loads(messages[-1].content)
        self.requests.append({"instructions": messages[0].content, "texts": texts})
        content = self.answer(texts) if callable(self.answer) else self.answer
        return SimpleNamespace(content=content)


def _use(monkeypatch: pytest.MonkeyPatch, model: FakeModel) -> FakeModel:
    monkeypatch.setattr(llm_manager, "build_chat_model", lambda _provider: model)
    return model


def test_translations_that_keep_every_key_and_citation_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    def fenced(texts: dict) -> str:
        return "```json\n" + json.dumps({key: f"[cs] {text}" for key, text in texts.items()}) + "\n```"

    model = _use(monkeypatch, FakeModel(fenced))

    translated, failed = llm_manager.translate_texts(PROVIDER, {"title": "Fix", "12": "Patch now [#ab12cd]."}, "en", "cs", ["12"])

    assert translated == {"title": "[cs] Fix", "12": "[cs] Patch now [#ab12cd]."}
    assert failed == {}
    assert "from English into Czech" in model.requests[0]["instructions"]
    assert "(12)" in model.requests[0]["instructions"]


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ({"12": "Opravte hned."}, "lost or changed its citations"),
        ({"12": "Opravte [#zz99zz] hned."}, "lost or changed its citations"),
        ({"12": "   "}, "came back empty"),
        ({}, "missing from the answer"),
    ],
)
def test_a_translation_that_lost_something_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    answer: dict,
    reason: str,
) -> None:
    _use(monkeypatch, FakeModel(json.dumps(answer)))

    translated, failed = llm_manager.translate_texts(PROVIDER, {"12": "Patch [#ab12cd] now."}, "en", "cs")

    assert translated == {}
    assert failed == {"12": reason}


def test_an_answer_without_json_fails_its_texts_only(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, FakeModel("I cannot help with that."))

    translated, failed = llm_manager.translate_texts(PROVIDER, {"title": "Fix"}, None, "cs")

    assert translated == {}
    assert failed == {"title": "The AI provider did not answer with JSON"}


def test_an_unreachable_provider_fails_the_texts_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(_texts: dict) -> str:
        message = "refused"
        raise ConnectionError(message)

    _use(monkeypatch, FakeModel(refuse))

    _translated, failed = llm_manager.translate_texts(PROVIDER, {"title": "Fix"}, "en", "cs")

    assert failed == {"title": "the AI provider could not be reached"}


def test_big_inputs_go_in_several_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _use(monkeypatch, FakeModel(json.dumps))
    texts = {str(index): "x" * 3000 for index in range(5)}

    translated, _failed = llm_manager.translate_texts(PROVIDER, texts, "en", "cs")

    assert translated == texts
    assert len(model.requests) == 3  # 8000 characters per request
    assert all(len(json.dumps(request["texts"])) < 2 * llm_manager.CHUNK_CHARS for request in model.requests)


def test_an_unsupported_provider_type_is_refused() -> None:
    with pytest.raises(llm_manager.LlmError, match="Unsupported AI provider type 'azure'"):
        llm_manager.build_chat_model(SimpleNamespace(api_type="azure"))


@pytest.mark.parametrize(
    ("value", "level"),
    [
        ("amber", "AMBER"),
        ("TLP:RED", "RED"),
        ("WHITE", "CLEAR"),
        ("AMBER+STRICT", "AMBER+STRICT"),
        ("", None),
        ("purple", None),
        (None, None),
    ],
)
def test_tlp_values_are_normalized(value: object, level: str | None) -> None:
    assert tlp.normalize(value) == level


def test_a_tlp_limit_must_be_a_level() -> None:
    assert tlp.clean_limit("") is None
    assert tlp.clean_limit("green") == "GREEN"
    with pytest.raises(ValueError, match="Unknown TLP level: purple"):
        tlp.clean_limit("purple")


@pytest.mark.parametrize(
    ("limit", "levels", "refused"),
    [
        (None, ["RED"], None),
        ("AMBER", None, None),
        ("AMBER", ["GREEN"], None),
        ("AMBER", ["AMBER"], None),
        ("AMBER", ["CLEAR", "RED"], "The report is TLP:RED, and the AI provider 'Local' only accepts up to TLP:AMBER"),
        ("GREEN", [None], "The report has no TLP set, and the AI provider 'Local' only accepts up to TLP:GREEN"),
        ("GREEN", [], "The report has no TLP set, and the AI provider 'Local' only accepts up to TLP:GREEN"),
    ],
)
def test_reports_above_the_providers_tlp_are_refused(
    limit: str | None,
    levels: list | None,
    refused: str | None,
) -> None:
    provider = SimpleNamespace(name="Local", max_tlp=limit)

    assert llm_manager.tlp_refusal(provider, levels, "The report") == refused


def _tlp_item(item_type: str) -> SimpleNamespace:
    return SimpleNamespace(attribute=SimpleNamespace(type=SimpleNamespace(name=item_type)))


def test_a_report_type_without_a_tlp_field_has_no_tlp_levels() -> None:
    report_type = SimpleNamespace(attribute_groups=[SimpleNamespace(attribute_group_items=[_tlp_item("TEXT")])])
    report = SimpleNamespace(report_item_type=report_type, attributes=[])

    assert llm_manager.report_tlp_levels(report) is None


def test_the_tlp_levels_of_a_report_are_its_tlp_values() -> None:
    tlp_item = _tlp_item("TLP")
    report_type = SimpleNamespace(attribute_groups=[SimpleNamespace(attribute_group_items=[tlp_item, _tlp_item("TEXT")])])
    report = SimpleNamespace(
        report_item_type=report_type,
        attributes=[
            SimpleNamespace(attribute_group_item=tlp_item, value="amber"),
            SimpleNamespace(attribute_group_item=tlp_item, value=""),
            SimpleNamespace(attribute_group_item=_tlp_item("TEXT"), value="RED"),
        ],
    )

    assert llm_manager.report_tlp_levels(report) == ["AMBER", None]


@pytest.mark.parametrize(
    ("code", "valid"),
    [("cs", True), ("en", True), ("CS", False), ("cz", False), ("ces", False), ("", False), (None, False)],
)
def test_content_languages_are_iso_639_1_codes(code: object, valid: bool) -> None:
    assert content_language.is_language(code) is valid


def test_language_lists_and_label_translations_are_cleaned() -> None:
    assert content_language.clean_languages(["cs", "en", "cs", ""]) == ["cs", "en"]
    with pytest.raises(ValueError, match="Unknown language code: cz"):
        content_language.clean_languages(["cz"])
    assert content_language.clean_label_translations(
        {"cs": {"title": "Popis", "description": " ", "colour": "x"}, "sk": {"title": ""}},
        content_language.ITEM_LABEL_FIELDS,
    ) == {"cs": {"title": "Popis"}}
    with pytest.raises(ValueError, match="Label translations must map languages to texts"):
        content_language.clean_label_translations(["cs"], content_language.ITEM_LABEL_FIELDS)
