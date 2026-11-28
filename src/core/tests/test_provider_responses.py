"""Saving an AI or data provider does not send its API key back.

The lists hide the key (api_key_set only), but POST and PUT answered with the plain schema - so
saving a provider with the key left empty, which keeps the stored one, returned the stored key
to anyone with CONFIG_AI_UPDATE or CONFIG_DATA_PROVIDER_UPDATE.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

import pytest
from api import config as config_api
from flask import Flask

if TYPE_CHECKING:
    from collections.abc import Callable

APP = Flask(__name__)


def _ai_provider() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id=1,
        name="gpt",
        api_type="openai",
        api_url="https://api.example/v1",
        api_key="sk-STORED",
        model="m",
        max_tlp=None,
        updated_by="a",
        updated_at=None,
    )


def _data_provider() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id=1,
        name="NVD",
        api_type="nvd",
        api_url="https://nvd.example",
        api_key="STORED-NVD",
        user_agent="",
        web_url="",
        updated_by="a",
        updated_at=None,
    )


@pytest.mark.parametrize(
    ("resource", "model", "record", "method", "args"),
    [
        (config_api.AiProviderResource, "AiProvider", _ai_provider, "put", (1,)),
        (config_api.AiProvidersResource, "AiProvider", _ai_provider, "post", ()),
        (config_api.DataProviderResource, "DataProvider", _data_provider, "put", (1,)),
        (config_api.DataProvidersResource, "DataProvider", _data_provider, "post", ()),
    ],
)
def test_the_saved_record_comes_back_without_its_key(
    monkeypatch: pytest.MonkeyPatch,
    resource: type,
    model: str,
    record: Callable[[], types.SimpleNamespace],
    method: str,
    args: tuple,
) -> None:
    module = config_api.ai_provider if model == "AiProvider" else config_api.data_provider
    saved = record()
    monkeypatch.setattr(getattr(module, model), "update", classmethod(lambda _cls, *_args: saved))
    monkeypatch.setattr(getattr(module, model), "add_new", classmethod(lambda _cls, *_args: saved))
    monkeypatch.setattr(config_api.auth_manager, "get_user_from_jwt", lambda: types.SimpleNamespace(name="Admin"))

    with APP.test_request_context("/", method=method.upper(), json={"api_key": ""}):
        body, _status = getattr(resource, method).__wrapped__(resource(), *args)

    assert body["api_key"] == ""
    assert body["api_key_set"] is True
    assert "STORED" not in str(body)
