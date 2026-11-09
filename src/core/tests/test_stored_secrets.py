"""Credentials the GUI never receives back: node and provider API keys, secret parameter values.

Node lists handed every node's API key (with which one can act as that node toward core) to
whoever may read the node configuration; publishing channel lists handed mail and SFTP passwords,
SSH keys and API tokens to anyone who may publish. Lists now say whether a secret is stored, and
a save that leaves it empty keeps it.
"""

from __future__ import annotations

import types

import pytest
from managers import stored_secrets
from shared.schema.ai_provider import AiProviderPresentationSchema
from shared.schema.collectors_node import CollectorsNodePresentationSchema
from shared.schema.public_web_node import PublicWebNodePresentationSchema
from shared.schema.remote import RemoteAccessPresentationSchema, RemoteNodePresentationSchema


@pytest.mark.parametrize(
    "schema",
    [
        CollectorsNodePresentationSchema,
        PublicWebNodePresentationSchema,
        RemoteAccessPresentationSchema,
        RemoteNodePresentationSchema,
        AiProviderPresentationSchema,
    ],
)
def test_lists_say_a_key_is_stored_but_never_show_it(schema: type) -> None:
    stored = types.SimpleNamespace(id=1, name="node", api_key="s3cr3t-node-key", api_url="http://n")
    empty = types.SimpleNamespace(id=2, name="other", api_key="", api_url="http://m")

    with_key, without_key = schema(many=True).dump([stored, empty])

    assert "s3cr3t-node-key" not in str(with_key)
    assert (with_key["api_key"], with_key["api_key_set"]) == ("", True)
    assert without_key["api_key_set"] is False


@pytest.mark.parametrize(
    ("key", "secret"),
    [
        ("EMAIL_PASSWORD", True),
        ("PASSWORD", True),
        ("SSH_KEY", True),
        ("MISP_API_KEY", True),
        ("SLACK_API_TOKEN", True),
        ("TWITTER_API_KEY_SECRET", True),
        ("FEED_URL", False),
        ("SEARCH_KEYWORDS", False),
        ("EMAIL_SIGN", False),
        (None, False),
    ],
)
def test_which_parameters_are_secret(key: str | None, secret: bool) -> None:
    assert stored_secrets.is_secret_parameter(key) is secret


def test_secret_parameter_values_are_blanked_anywhere_in_a_response() -> None:
    response = {
        "items": [
            {
                "parameter_values": [
                    {"value": "hunter2", "parameter": {"key": "EMAIL_PASSWORD"}},
                    {"value": "", "parameter": {"key": "SSH_KEY"}},
                    {"value": "smtp.example", "parameter": {"key": "EMAIL_SERVER"}},
                ],
                # A remote access lists its sources, with their parameters.
                "osint_sources": [{"parameter_values": [{"value": "xoxb-1", "parameter": {"key": "SLACK_API_TOKEN"}}]}],
            },
        ],
    }

    stored_secrets.hide_secret_parameters(response)

    password, ssh_key, server = response["items"][0]["parameter_values"]
    assert (password["value"], password["value_set"]) == ("", True)
    assert (ssh_key["value"], ssh_key["value_set"]) == ("", False)
    assert server == {"value": "smtp.example", "parameter": {"key": "EMAIL_SERVER"}}
    assert response["items"][0]["osint_sources"][0]["parameter_values"][0]["value"] == ""
    assert "hunter2" not in str(response)


@pytest.mark.parametrize(
    ("key", "stored", "submitted", "kept"),
    [
        ("EMAIL_PASSWORD", "hunter2", "", "hunter2"),
        ("EMAIL_PASSWORD", "hunter2", None, "hunter2"),
        ("EMAIL_PASSWORD", "hunter2", "new-one", "new-one"),
        ("FEED_URL", "https://old", "", ""),
    ],
)
def test_a_secret_saved_empty_keeps_its_value(key: str, stored: str, submitted: str | None, kept: str) -> None:
    assert stored_secrets.keep_secret_parameter(key, stored, submitted) == kept


def test_a_record_saved_without_a_key_keeps_the_stored_one(monkeypatch: pytest.MonkeyPatch) -> None:
    records = {7: types.SimpleNamespace(api_key="stored-key")}
    monkeypatch.setattr(stored_secrets.db, "session", types.SimpleNamespace(get=lambda _model, record_id: records.get(record_id)))

    assert stored_secrets.keep_stored_api_key({"name": "n", "api_key": ""}, object, 7) == {"name": "n", "api_key": "stored-key"}
    assert stored_secrets.keep_stored_api_key({"name": "n"}, object, 7)["api_key"] == "stored-key"
    assert stored_secrets.keep_stored_api_key({"name": "n", "api_key": "new"}, object, 7)["api_key"] == "new"
    assert stored_secrets.keep_stored_api_key({"name": "n", "api_key": ""}, object, 8) == {"name": "n", "api_key": ""}
