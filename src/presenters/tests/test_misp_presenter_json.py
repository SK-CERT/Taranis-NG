"""The MISP presenter prints analyst text as JSON string content.

misp.json puts every value between double quotes and is rendered without autoescaping, so an
attribute value with a quote in it used to end the string and add keys of its own: published,
distribution and tags all came out the way the text said. The publisher then sent that event
to MISP.
"""

from __future__ import annotations

import base64
import json
import types
from pathlib import Path

import pytest
from presenters.base_presenter import BasePresenter
from presenters.misp_presenter import MISPPresenter, json_string_content

from presenters import misp_presenter

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"

INJECTION = 'x"}], "published": true, "distribution": "3", "Tag": [{"name": "tlp:clear"}], "zz": [{"a": "b'


def _render(attrs: dict) -> dict:
    data = {
        "product": {"title": "MISP product"},
        "report_items": [{"uuid": "11111111-2222-3333-4444-555555555555", "attrs": attrs}],
    }
    presenter_input = types.SimpleNamespace(param_key_values={"MISP_TEMPLATE_PATH": str(TEMPLATES_ROOT / "misp.json")})
    original = BasePresenter.generate_input_data
    BasePresenter.generate_input_data = staticmethod(lambda _input: data)
    try:
        output = MISPPresenter().generate(presenter_input)
    finally:
        BasePresenter.generate_input_data = original
    assert output["mime_type"] == "application/json", base64.b64decode(output["data"]).decode()
    return json.loads(base64.b64decode(output["data"]))


@pytest.fixture(autouse=True)
def _templates_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BasePresenter, "JINJA_TEMPLATES_ROOT", str(TEMPLATES_ROOT))


def test_a_quote_in_a_value_cannot_add_keys_to_the_event() -> None:
    event = _render({"event_info": "Phishing", "attribute_value": INJECTION, "event_distribution": "Your Organisation only"})["Event"]

    assert event["published"] is False
    assert event["distribution"] == "0"
    assert "Tag" not in event
    assert event["Attribute"][0]["value"] == INJECTION


@pytest.mark.parametrize("text", ['say "hi"', "back\\slash", "two\nlines", "tab\there", "\u2028separator", "Kampaň"])
def test_any_text_survives_the_round_trip(text: str) -> None:
    event = _render({"event_info": text, "attribute_contextual_comment": text})["Event"]

    assert event["info"] == text
    assert event["Attribute"][0]["comment"] == text


def test_markup_is_printed_as_the_template_wrote_it() -> None:
    assert json_string_content(misp_presenter.Markup('"already json"')) == '"already json"'
    assert json_string_content(3) == "3"
