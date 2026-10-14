"""A collectors node waits for core at startup, and must say so when core never answers.

Until core's /api/v1/isalive answers 200 the node registers no collectors and sends no
heartbeat, so the GUI shows it red. A remote node calls that path on core's satellite port,
and when Traefik there did not route it the answer was a plain-text 404: the JSON parse
failed, the failure was swallowed, and the node waited forever with nothing in its log.
"""

import types
from http import HTTPStatus

import pytest
from managers import collectors_manager
from remote import core_api
from remote.core_api import CoreApi


class FakeResponse:
    """Just enough of requests.Response for CoreApi.is_live."""

    def __init__(self, status_code: int, body: dict | None = None, text: str = "") -> None:
        """Answer with the given status, and with JSON only when a body is given."""
        self.status_code = status_code
        self.body = body
        self.text = text

    def json(self) -> dict:
        """Parse like requests does: plain text raises a ValueError."""
        if self.body is None:
            msg = "Expecting value"
            raise ValueError(msg)
        return self.body


def answer_with(monkeypatch: pytest.MonkeyPatch, response: FakeResponse) -> None:
    """Make every GET to core return the given response."""
    monkeypatch.setattr(core_api.requests, "get", lambda *_args, **_kwargs: response)


def test_core_answering_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_with(monkeypatch, FakeResponse(HTTPStatus.OK, {"isalive": True}))

    assert CoreApi.is_live(show_error=False) == ({"isalive": True}, HTTPStatus.OK)


def test_a_proxy_404_keeps_its_status(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_with(monkeypatch, FakeResponse(HTTPStatus.NOT_FOUND, text="404 page not found"))

    body, status_code = CoreApi.is_live(show_error=False)

    assert status_code == HTTPStatus.NOT_FOUND
    assert "404 page not found" in body["error"]


def test_a_200_that_is_not_core_is_not_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_with(monkeypatch, FakeResponse(HTTPStatus.OK, text="<html>some other site</html>"))

    _, status_code = CoreApi.is_live(show_error=False)

    assert status_code != HTTPStatus.OK


def test_waiting_for_core_is_logged_then_collectors_start(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(
        [
            ({"error": "not routed"}, HTTPStatus.NOT_FOUND),
            ({"error": "not routed"}, HTTPStatus.NOT_FOUND),
            ({"isalive": True}, HTTPStatus.OK),
        ],
    )
    monkeypatch.setattr(CoreApi, "is_live", classmethod(lambda _cls, **_kwargs: next(answers)))
    monkeypatch.setattr(collectors_manager.time, "sleep", lambda _seconds: None)

    warnings: list[str] = []
    monkeypatch.setattr(
        collectors_manager,
        "logger",
        types.SimpleNamespace(debug=lambda _msg: None, warning=warnings.append),
    )

    registered: list[object] = []
    monkeypatch.setattr(collectors_manager, "register_collector", registered.append)

    started: list[object] = []
    monkeypatch.setattr(
        collectors_manager.threading,
        "Thread",
        lambda target: types.SimpleNamespace(daemon=False, start=lambda: started.append(target)),
    )

    collectors_manager.initialize_after_core_is_ready()

    # Warned on the first failure only - the second falls inside the once-a-minute window.
    assert len(warnings) == 1
    assert "/api/v1/isalive" in warnings[0]
    assert "404" in warnings[0]
    # Core answered on the third try, so the collectors and the heartbeat started.
    assert registered
    assert started == [collectors_manager.report_status]
