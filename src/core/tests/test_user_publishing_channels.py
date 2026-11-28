"""People who may publish get the publishing channels' names, not their settings.

GET /users/my-publishing-channels (PUBLISH_ACCESS) returned every channel with all its
parameter values. The mask goes by key suffix (…PASSWORD, …TOKEN, …), so the FTP publisher's
FTP_URL - user and password in the URL - the mail, MISP and SFTP hosts and user names and the
proxy URLs reached anyone who may publish.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from api import user as user_api
from flask import Flask

if TYPE_CHECKING:
    import pytest

APP = Flask(__name__)


def _channels() -> dict:
    """The channel listing as PublishingChannelPresentationSchema dumps it."""
    return {
        "total_count": 1,
        "items": [
            {
                "id": "channel-ftp",
                "name": "Partner FTP",
                "description": "Reports for the partners",
                "use_for_notifications": False,
                "publisher_id": "publisher-ftp",
                "item_name": "FTP Publisher",
                "title": "Partner FTP",
                "subtitle": "Reports for the partners",
                "tag": "mdi-file-star-outline",
                "parameter_values": [
                    {"value": "ftp://publisher:Sup3rS3cret@ftp.example.org/in/", "parameter": {"key": "FTP_URL"}},
                    {"value": "http://proxyuser:proxypass@proxy.example.org:3128", "parameter": {"key": "PROXY_SERVER"}},
                    {"value": "", "value_set": True, "parameter": {"key": "PASSWORD"}},
                ],
            },
        ],
    }


def test_the_channels_come_without_their_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user_api.PublishingChannel, "get_all_json", classmethod(lambda _cls, _search: _channels()))

    with APP.test_request_context("/"):
        body = user_api.UserPublishingChannels.get.__wrapped__(user_api.UserPublishingChannels())

    assert body == {
        "total_count": 1,
        "items": [{"id": "channel-ftp", "name": "Partner FTP", "description": "Reports for the partners"}],
    }
    for leaked in ("Sup3rS3cret", "ftp.example.org", "proxypass", "parameter_values", "FTP Publisher"):
        assert leaked not in json.dumps(body)
