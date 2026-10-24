"""Templates get content in the language rendered without anything they compare changing.

Core sends texts already translated, and choice constants and labels as extra fields
(``value_label``, ``label`` ...). ``attrs`` keeps the raw constants and the keys from the original
titles, which shipped templates compare (``misp.json``: ``event_threat_level == 'High'``);
``attrs_display``, ``labels`` and ``type_label`` carry the language.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from presenters.base_presenter import BasePresenter
from shared.schema.presenter import PresenterInputSchema

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"


def _group_item(group_item_id: int, title: str, attribute_type: str, max_occurrence: int, label: str | None) -> dict:
    item = {
        "id": group_item_id,
        "title": title,
        "description": "",
        "index": group_item_id,
        "min_occurrence": 0,
        "max_occurrence": max_occurrence,
        "ai_provider_id": None,
        "ai_prompt": None,
        "attribute": {
            "id": group_item_id,
            "name": title,
            "description": "",
            "type": attribute_type,
            "default_value": None,
            "validator": None,
            "validator_parameter": None,
        },
    }
    if label is not None:
        item["label"] = label
    return item


def _attribute(attribute_id: int, group_item_id: int, value: str, value_label: str | None) -> dict:
    attribute = {
        "id": attribute_id,
        "attribute_group_item_id": group_item_id,
        "value": value,
        "value_description": None,
        "created": "01.10.2026 - 10:00",
        "last_updated": "01.10.2026 - 10:00",
        "version": 1,
        "current": True,
        "user": {"username": "analyst", "name": "Analyst"},
    }
    if value_label is not None:
        attribute["value_label"] = value_label
    return attribute


def _input(*, translated: bool) -> dict:
    product = {
        "title": "Bulletin",
        "description": "",
        "product_type": "MISP",
        "product_type_description": "",
        "user": {"name": "A"},
        "id": "7",
    }
    if translated:
        product["language"] = "sk"
    report_type = {
        "id": 1,
        "title": "MISP Report",
        "description": "",
        "attribute_groups": [
            {
                "id": 1,
                "title": "Event",
                "description": "",
                "section": None,
                "section_title": None,
                "index": 0,
                "attribute_group_items": [
                    _group_item(10, "Event threat level", "ENUM", 1, "Úroveň hrozby" if translated else None),
                    _group_item(11, "Event info", "STRING", 1, "Informácie" if translated else None),
                    _group_item(12, "Sectors", "MULTI_CHOICE", 1, "Sektory" if translated else None),
                ],
            },
        ],
    }
    if translated:
        report_type["label"] = "Správa MISP"
    return {
        "type": "MISP_PRESENTER",
        "parameter_values": [],
        "product": product,
        "report_types": [report_type],
        "reports": [
            {
                "id": 1,
                "uuid": "uuid-1",
                "title": "Phishing",
                "title_prefix": "",
                "created": "01.10.2026 - 10:00",
                "last_updated": "01.10.2026 - 10:00",
                "report_item_type_id": 1,
                "state_id": None,
                "remote_user": None,
                "news_item_aggregates": [],
                "remote_report_items": [],
                "attributes": [
                    _attribute(101, 10, "High", "Vysoká" if translated else None),
                    _attribute(102, 11, "Kampaň" if translated else "Campaign", None),
                    _attribute(103, 12, "Energy\nHealth", "Energetika\nZdravotníctvo" if translated else None),
                ],
            },
        ],
    }


def _data(*, translated: bool) -> dict:
    return BasePresenter.generate_input_data(PresenterInputSchema().load(_input(translated=translated)))


def test_attrs_keep_raw_constants_and_display_carries_the_language() -> None:
    report = _data(translated=True)["report_items"][0]

    assert report["attrs"]["event_threat_level"] == "High"
    assert report["attrs_display"]["event_threat_level"] == "Vysoká"
    assert report["attrs"]["sectors"] == ["Energy", "Health"]
    assert report["attrs_display"]["sectors"] == ["Energetika", "Zdravotníctvo"]
    # Free text arrives translated in both.
    assert report["attrs"]["event_info"] == report["attrs_display"]["event_info"] == "Kampaň"


def test_labels_and_type_label_follow_the_language_and_keys_stay() -> None:
    data = _data(translated=True)
    report = data["report_items"][0]

    assert report["type"] == "MISP Report"
    assert report["type_label"] == "Správa MISP"
    assert report["labels"] == {"event_threat_level": "Úroveň hrozby", "event_info": "Informácie", "sectors": "Sektory"}
    assert data["product"]["language"] == "sk"


def test_without_a_language_display_and_labels_are_the_originals() -> None:
    report = _data(translated=False)["report_items"][0]

    assert report["attrs_display"] == report["attrs"]
    assert report["type_label"] == "MISP Report"
    assert report["labels"]["event_threat_level"] == "Event threat level"


def test_misp_output_compares_the_raw_constants() -> None:
    template = Environment(loader=FileSystemLoader(TEMPLATES_ROOT), autoescape=False).get_template("misp.json")  # noqa: S701 - JSON template

    english = template.render(data=_data(translated=False))
    slovak = template.render(data=_data(translated=True))

    assert '"threat_level_id": "1"' in slovak
    assert slovak == english.replace("Campaign", "Kampaň")
