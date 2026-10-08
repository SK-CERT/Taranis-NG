"""CoreApi.add_news_items tells a timeout apart from a rejection.

Core keeps working after the collector stops waiting, and usually stores the items anyway,
so a timeout is reported with its own status rather than as a failure of core.
"""

from http import HTTPStatus

import pytest
import requests
from remote import core_api
from remote.core_api import CoreApi


def _failing_post(error: Exception) -> object:
    def post(*_args: object, **_kwargs: object) -> None:
        raise error

    return post


def test_a_timeout_is_reported_as_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core_api.requests, "post", _failing_post(requests.exceptions.ReadTimeout("read timed out")))

    assert CoreApi.add_news_items([]) == ({"error": "Add news items timed out"}, HTTPStatus.GATEWAY_TIMEOUT)


def test_other_failures_stay_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core_api.requests, "post", _failing_post(requests.exceptions.ConnectionError("refused")))

    assert CoreApi.add_news_items([]) == ({"error": "Add news items failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
