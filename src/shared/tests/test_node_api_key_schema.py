"""Validate the API-key contract shared by service-node schemas."""

import pytest
from marshmallow import ValidationError
from shared.schema.bots_node import BotsNodeSchema
from shared.schema.collectors_node import CollectorsNodeSchema
from shared.schema.presenters_node import PresentersNodeSchema
from shared.schema.publishers_node import PublishersNodeSchema

SCHEMAS = (CollectorsNodeSchema, PresentersNodeSchema, PublishersNodeSchema, BotsNodeSchema)


def _payload(api_key: str | None) -> dict[str, str]:
    payload = {
        "id": "node-id",
        "name": "Node",
        "description": "Description",
        "api_url": "https://service.invalid",
    }
    if api_key is not None:
        payload["api_key"] = api_key
    return payload


@pytest.mark.parametrize("schema_type", SCHEMAS)
@pytest.mark.parametrize("invalid_key", [None, "", "   "])
def test_missing_empty_and_whitespace_api_keys_are_rejected(schema_type: type, invalid_key: str | None) -> None:
    """Reject keys that cannot authenticate a service request."""
    with pytest.raises(ValidationError):
        schema_type().load(_payload(invalid_key))


@pytest.mark.parametrize("schema_type", SCHEMAS)
def test_non_empty_api_key_is_accepted(schema_type: type) -> None:
    """Continue accepting ordinary service-node payloads."""
    node = schema_type().load(_payload("secret"))
    assert node.api_key == "secret"  # noqa: S101
