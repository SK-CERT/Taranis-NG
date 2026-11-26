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


def _collected_source() -> dict:
    """A source as the group schema dumps it, with what a collector run and its node leave behind."""
    return {
        **_source(),
        "description": "Team mailbox on imap.corp.example",
        "word_lists": [{"id": 4, "name": "Internal projects", "entries": [{"value": "project-codename"}]}],
        "collector_id": "collector-email",
        "collector": {"id": "collector-email", "type": "EMAIL_COLLECTOR", "node": {"api_url": "https://collectors.corp.example"}},
        "last_attempted": "01.11.2026 - 10:00:00",
        "last_collected": "01.11.2026 - 09:00:00",
        "last_error_message": "Proxy http://proxyuser:proxypass@proxy.corp.example:3128 refused the connection",
        "enabled": True,
        "collecting": False,
        "next_run": "2026-11-01T11:00:00+00:00",
        "status": "red",
    }


def _groups() -> dict:
    group = {
        "id": "group-1",
        "name": "Default",
        "description": "Sources of the CERT",
        "default": True,
        "title": "Default",
        "subtitle": "Sources of the CERT",
        "tag": "mdi-folder",
        "osint_sources": [_collected_source()],
    }
    return {"total_count": 1, "items": [group]}


@pytest.fixture
def groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assess.OSINTSourceGroup, "get_all_json", classmethod(lambda _cls, *_args, **_kwargs: _groups()))
    monkeypatch.setattr(assess.auth_manager, "get_user_from_jwt", lambda: types.SimpleNamespace(id=1))


def _values(body: dict) -> dict:
    return {value["parameter"]["key"]: value["value"] for value in body["items"][0]["osint_sources"][0]["parameter_values"]}


@pytest.mark.usefixtures("groups")
def test_the_configuration_listing_masks_source_credentials() -> None:
    with APP.test_request_context("/"):
        body = config.OSINTSourceGroupsResource.get.__wrapped__(config.OSINTSourceGroupsResource())

    assert _values(body) == {"EMAIL_SERVER_HOSTNAME": "imap.corp.example", "EMAIL_PASSWORD": "", "SLACK_API_TOKEN": ""}
    assert "Sup3rS3cret" not in json.dumps(body)


@pytest.mark.usefixtures("groups")
def test_the_assess_listing_carries_no_source_parameters() -> None:
    """Every analyst reads it: no host names, user names, feed or proxy URLs either."""
    with APP.test_request_context("/"):
        body = assess.OSINTSourceGroupsAssess.get.__wrapped__(assess.OSINTSourceGroupsAssess())

    source = body["items"][0]["osint_sources"][0]
    assert "parameter_values" not in source
    assert "imap.corp.example" not in json.dumps(body)
    assert "Sup3rS3cret" not in json.dumps(body)


@pytest.mark.usefixtures("groups")
def test_the_assess_listing_carries_only_what_assess_reads() -> None:
    """The group's id, name and default flag; of a source its id and name, which its news items show."""
    with APP.test_request_context("/"):
        body = assess.OSINTSourceGroupsAssess.get.__wrapped__(assess.OSINTSourceGroupsAssess())

    assert body == {
        "total_count": 1,
        "items": [{"id": "group-1", "name": "Default", "default": True, "osint_sources": [{"id": "source-1", "name": "Shared mailbox"}]}],
    }
    for leaked in ("proxypass", "corp.example", "project-codename", "EMAIL_COLLECTOR"):
        assert leaked not in json.dumps(body)


def test_the_export_carries_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    exported = {"version": 1, "data": [_source()]}
    exported["data"][0]["parameter_values"].append({"value": "http://user:pw@proxy:3128", "parameter": {"key": "PROXY_SERVER"}})
    monkeypatch.setattr(collectors_manager.OSINTSource, "get_all", classmethod(lambda _cls: []))
    monkeypatch.setattr(collectors_manager, "OSINTSourceExportRootSchema", lambda: types.SimpleNamespace(dump=lambda _root: exported))

    document = json.loads(collectors_manager.export_osint_sources(None))

    values = {value["parameter"]["key"]: value["value"] for value in document["data"][0]["parameter_values"]}
    assert values == {"EMAIL_SERVER_HOSTNAME": "imap.corp.example", "EMAIL_PASSWORD": "", "SLACK_API_TOKEN": "", "PROXY_SERVER": ""}
