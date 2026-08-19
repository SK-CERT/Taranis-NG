"""How core probes a public-web node's liveness.

Every satellite now answers liveness at ``/api/v1/isalive``; public-web previously had
only ``/management/isalive``. The client tries the shared path and falls back, because
this probe also gates node creation and update - without the fallback a core upgraded
ahead of a remote node could not register that node at all, which is a worse failure
than a stale status dot.
"""

from http import HTTPStatus

import pytest
from remote import public_web_api
from remote.public_web_api import PublicWebApi

KEY = "node-key"


class _Response:
    """Just enough of a requests.Response for the probe."""

    def __init__(self, status_code: int, body: bytes = b'{"status": "ok"}') -> None:
        self.status_code = status_code
        self.content = body

    def json(self) -> dict:
        return {"status": "ok"}


class _Recorder:
    """The GETs the probe made, and the answers waiting for it."""

    def __init__(self) -> None:
        self.made: list[dict] = []
        self.queue: list[_Response] = []

    def __len__(self) -> int:
        return len(self.made)

    def __getitem__(self, index: int) -> dict:
        return self.made[index]

    @property
    def urls(self) -> list[str]:
        return [call["url"] for call in self.made]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """Record every GET the probe makes, answering from a queue of responses."""
    recorder = _Recorder()

    def fake_get(url: str, headers: dict | None = None, **_kwargs: object) -> _Response:
        recorder.made.append({"url": url, "headers": headers or {}})
        return recorder.queue.pop(0)

    monkeypatch.setattr(public_web_api.requests, "get", fake_get)
    return recorder


def test_the_shared_path_is_tried_first(calls: _Recorder) -> None:
    """A current node answers on the path every satellite shares."""
    calls.queue.append(_Response(HTTPStatus.OK))

    body, status = PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert status == HTTPStatus.OK
    assert body == {"status": "ok"}
    assert calls.urls == ["https://node.example.com:8443/api/v1/isalive"]


def test_an_older_node_is_still_reachable_on_its_original_path(calls: _Recorder) -> None:
    """The upgrade-skew case: core is ahead of the node, registration must still work."""
    calls.queue.extend([_Response(HTTPStatus.NOT_FOUND), _Response(HTTPStatus.OK)])

    _, status = PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert status == HTTPStatus.OK
    assert calls.urls == [
        "https://node.example.com:8443/api/v1/isalive",
        "https://node.example.com:8443/management/isalive",
    ]


def test_the_probe_authenticates(calls: _Recorder) -> None:
    """The node's endpoints are not open, so an unauthenticated probe would 401."""
    calls.queue.append(_Response(HTTPStatus.OK))

    PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert calls[0]["headers"]["Authorization"] == f"ApiKey {KEY}"


def test_a_node_that_is_up_but_wrong_is_not_retried_forever(calls: _Recorder) -> None:
    """404 on both is the node's answer, not a reason to keep going."""
    calls.queue.extend([_Response(HTTPStatus.NOT_FOUND), _Response(HTTPStatus.NOT_FOUND, b"")])

    _, status = PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert status == HTTPStatus.NOT_FOUND
    assert len(calls) == 2


@pytest.mark.parametrize("status", [HTTPStatus.UNAUTHORIZED, HTTPStatus.INTERNAL_SERVER_ERROR])
def test_any_other_answer_is_returned_as_is(calls: _Recorder, status: HTTPStatus) -> None:
    """A 401 means the key is wrong; retrying the legacy path would only hide that."""
    calls.queue.append(_Response(status))

    _, returned = PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert returned == status
    assert len(calls) == 1


def test_an_unreachable_host_is_not_probed_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    """A transport failure is about the host, so the second path would only repeat it."""
    attempts = []

    def fake_get(url: str, **_kwargs: object) -> _Response:
        attempts.append(url)
        message = "no route to host"
        raise public_web_api.requests.RequestException(message)

    monkeypatch.setattr(public_web_api.requests, "get", fake_get)

    body, status = PublicWebApi("https://node.example.com:8443", KEY).isalive()

    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert "error" in body
    assert len(attempts) == 1
