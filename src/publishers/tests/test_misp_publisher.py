"""The MISP publisher checks the server's certificate.

It used to construct PyMISP with ``ssl=False`` and silence urllib3's warning, so anyone on
the network path to MISP got the API key and the (possibly TLP-restricted) event.
"""

from __future__ import annotations

import base64
import json
import types

import pytest
from publishers.misp_publisher import MISPPublisher

from publishers import misp_publisher


@pytest.fixture
def constructed(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []

    class FakeMISP:
        def __init__(self, *args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

        def add_event(self, _event: object) -> None:
            return None

    monkeypatch.setattr(misp_publisher, "PyMISP", FakeMISP)
    return calls


def publish(**parameters: str) -> tuple:
    event = {"Event": {"info": "x", "Attribute": []}}
    publisher_input = types.SimpleNamespace(
        name="MISP channel",
        param_key_values={"MISP_URL": "https://misp.example.org", "MISP_API_KEY": "k3y", **parameters},
        data=base64.b64encode(json.dumps(event).encode()).decode(),
    )
    return MISPPublisher().publish(publisher_input)


def test_the_certificate_is_checked(constructed: list[tuple]) -> None:
    publish()

    args, _kwargs = constructed[0]
    assert args == ("https://misp.example.org", "k3y", True)


def test_a_private_ca_bundle_is_used_for_the_check(constructed: list[tuple]) -> None:
    publish(MISP_CA_BUNDLE=" /app/crypto/misp-ca.pem ")

    args, _kwargs = constructed[0]
    assert args[2] == "/app/crypto/misp-ca.pem"
