"""report-item-updated carries ids and change flags, never the text that changed.

The event was the request body as the model left it. Title, prefix and state were blanked, but
the new attribute value and its description went to every client of the stream - any signed-in
user whatever their permissions, every bots node, every remote access - regardless of the
report type's ACL.
"""

from __future__ import annotations

from managers.sse_manager import report_item_event


def test_the_text_of_an_update_is_not_broadcast() -> None:
    update = {
        "update": True,
        "report_item_id": 5,
        "user_id": 9,
        "attribute_id": 77,
        "attribute_value": "TLP:RED - victim ACME, attacker IP 203.0.113.7",
        "value_description": "internal note",
        "attribute_version": 2,
        "binary_description": "the attachment's description",
        "anything": "else the client sent",
    }

    assert report_item_event(update) == {"update": True, "report_item_id": 5, "user_id": 9, "attribute_id": 77, "attribute_version": 2}


def test_changed_fields_are_marked_not_sent() -> None:
    update = {"update": True, "report_item_id": 5, "title": "New title", "title_prefix": "[UPDATE]", "state_id": 3, "language": "cs"}

    assert report_item_event(update) == {
        "update": True,
        "report_item_id": 5,
        "title": "",
        "title_prefix": "",
        "state_id": "",
        "language": "cs",
    }


def test_what_the_gui_reads_survives() -> None:
    update = {
        "report_item_id": 5,
        "add": True,
        # useAttributes adds the new row only to the attribute group the event names
        "attribute_group_item_id": 12,
        "attribute_id": 40,
        "aggregate_ids": [1, 2],
        "remote_report_item_ids": [3],
        "translated": True,
        "languages": ["cs", "sk"],
        "source_language": "en",
        "results": [{"language": "cs", "translated": ["title"], "failed": {}, "skipped_locked": [], "skipped_manual": []}],
        "tags": [4],
        "completed": True,
    }

    assert report_item_event(update) == update
