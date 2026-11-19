"""What the preview URL answers with.

It is the one document the API serves without a JWT (a browser tab cannot send the header), so
whoever holds the ticket URL gets the document. The answer therefore stays out of caches and out
of Referer headers, and the ticket stops working after a few redemptions.
"""

from __future__ import annotations

import base64
import json
from http import HTTPStatus

import pytest
from api import publish
from flask import Flask


class FakeRedis:
    """The few Redis commands the preview endpoint uses, over a dict."""

    def __init__(self, entries: dict[str, bytes]) -> None:
        """Start with the given keys."""
        self.entries: dict[str, object] = dict(entries)

    def get(self, key: str) -> object:
        """Return the value, or None."""
        return self.entries.get(key)

    def incr(self, key: str) -> int:
        """Count one up and return the new count."""
        self.entries[key] = int(self.entries.get(key, 0)) + 1
        return self.entries[key]

    def expire(self, key: str, seconds: int) -> None:
        """Nothing expires within a test."""

    def delete(self, *keys: str) -> None:
        """Forget the keys."""
        for key in keys:
            self.entries.pop(key, None)


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """One cached HTML preview under the ticket ``ticket-1``."""
    cached = {"data": base64.b64encode(b"<html>report</html>").decode(), "mime": "text/html", "filename": "report.html"}
    fake = FakeRedis({"preview:ticket-1": json.dumps(cached).encode()})
    monkeypatch.setattr(publish, "redis_client", fake)
    monkeypatch.setattr(publish.log_manager, "store_auth_error_activity", lambda *_args, **_kwargs: None)
    return fake


def _get(token: str) -> object:
    with Flask(__name__).test_request_context(f"/api/v1/publish/products/preview/{token}"):
        return publish.ProductGetPreview().get(token)


@pytest.mark.usefixtures("redis")
def test_the_preview_is_not_cached_and_sends_no_referrer() -> None:
    response = _get("ticket-1")

    assert response.status_code == HTTPStatus.OK
    assert response.data == b"<html>report</html>"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Disposition"].startswith("inline;")


def test_a_ticket_is_spent_after_its_redemptions(redis: FakeRedis) -> None:
    for _ in range(publish.PREVIEW_TICKET_MAX_REDEMPTIONS):
        assert _get("ticket-1").status_code == HTTPStatus.OK

    assert _get("ticket-1").status_code == HTTPStatus.NOT_FOUND
    assert "preview:ticket-1" not in redis.entries


@pytest.mark.usefixtures("redis")
def test_an_unknown_ticket_is_not_found() -> None:
    assert _get("no-such-ticket").status_code == HTTPStatus.NOT_FOUND
