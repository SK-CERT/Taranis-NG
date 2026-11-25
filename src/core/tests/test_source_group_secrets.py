"""OSINT source groups and the source export never carry a source's credentials.

A group nests its sources whole, parameter values included, and neither group listing masked
them: GET /assess/osint-source-groups handed every analyst (ASSESS_ACCESS) the mailbox passwords,
Slack and Twitter tokens and basic-auth passwords of every source in the groups they can see.
The export (CONFIG_OSINT_SOURCE_ACCESS, a look-only permission) blanked only PROXY_SERVER.
"""

from __future__ import annotations

import json
import types

import pytest
from api import assess, config
from flask import Flask
from managers import collectors_manager

APP = Flask(__name__)


def _source() -> dict:
    return {
        "id": "source-1",
        "name": "Shared mailbox",
        "parameter_values": [
            {"value": "imap.corp.example", "parameter": {"key": "EMAIL_SERVER_HOSTNAME"}},
            {"value": "Sup3rS3cret-IMAP", "parameter": {"key": "EMAIL_PASSWORD"}},
            {"value": "xoxb-token", "parameter": {"key": "SLACK_API_TOKEN"}},
        ],
    }


def _groups() -> dict:
    return {"total_count": 1, "items": [{"id": "group-1", "name": "Default", "default": True, "osint_sources": [_source()]}]}


@pytest.fixture
def groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assess.OSINTSourceGroup, "get_all_json", classmethod(lambda _cls, *_args, **_kwargs: _groups()))
    monkeypatch.setattr(assess.auth_manager, "get_user_from_jwt", lambda: types.SimpleNamespace(id=1))


def _values(body: dict) -> dict:
    return {value["parameter"]["key"]: value["value"] for value in body["items"][0]["osint_sources"][0]["parameter_values"]}


@pytest.mark.usefixtures("groups")
@pytest.mark.parametrize("resource", [assess.OSINTSourceGroupsAssess, config.OSINTSourceGroupsResource])
def test_group_listings_mask_source_credentials(resource: type) -> None:
    with APP.test_request_context("/"):
        body = resource.get.__wrapped__(resource())

    assert _values(body) == {"EMAIL_SERVER_HOSTNAME": "imap.corp.example", "EMAIL_PASSWORD": "", "SLACK_API_TOKEN": ""}
    assert "Sup3rS3cret" not in json.dumps(body)


def test_the_export_carries_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    exported = {"version": 1, "data": [_source()]}
    exported["data"][0]["parameter_values"].append({"value": "http://user:pw@proxy:3128", "parameter": {"key": "PROXY_SERVER"}})
    monkeypatch.setattr(collectors_manager.OSINTSource, "get_all", classmethod(lambda _cls: []))
    monkeypatch.setattr(collectors_manager, "OSINTSourceExportRootSchema", lambda: types.SimpleNamespace(dump=lambda _root: exported))

    document = json.loads(collectors_manager.export_osint_sources(None))

    values = {value["parameter"]["key"]: value["value"] for value in document["data"][0]["parameter_values"]}
    assert values == {"EMAIL_SERVER_HOSTNAME": "imap.corp.example", "EMAIL_PASSWORD": "", "SLACK_API_TOKEN": "", "PROXY_SERVER": ""}
