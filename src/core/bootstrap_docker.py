"""Initialize the opinionated services and workflow bundle for Docker."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

from flask import Flask
from managers import bots_manager, collectors_manager, db_manager, presenters_manager, publishers_manager
from migrations.repair_distribution_bundle import repair_distribution_bundle
from model import (  # noqa: F401  Import the complete relationship graph before configuring mappers.
    attribute,
    bot,
    bot_preset,
    bots_node,
    collector,
    collectors_node,
    osint_source,
    parameter,
    presenter,
    presenters_node,
    product,
    product_type,
    publisher,
    publisher_preset,
    publishers_node,
    report_item,
    report_item_type,
)
from model.bots_node import BotsNode
from model.collectors_node import CollectorsNode
from model.presenters_node import PresentersNode
from model.publishers_node import PublishersNode
from sqlalchemy import func

NodeModel = type[BotsNode] | type[CollectorsNode] | type[PresentersNode] | type[PublishersNode]
NodeOperation = Callable[[dict[str, str]], HTTPStatus | int]
NodeUpdateOperation = Callable[[str, dict[str, str]], HTTPStatus | int]

DEFAULT_PRESENTER_URL = "http://presenters/"
MAX_ATTEMPTS = 30
RETRY_SECONDS = 2


@dataclass(frozen=True)
class NodeSpec:
    """One satellite included in the default Compose application."""

    label: str
    model: NodeModel
    relationship: str
    api_url: str
    default_name: str
    description: str
    add: NodeOperation
    update: NodeUpdateOperation
    required_capability: str | None = None


def _read_api_key() -> str:
    """Read and validate the shared satellite API key."""
    api_key = Path("/run/secrets/api_key").read_text(encoding="utf-8").strip()
    if not api_key:
        message = "The Docker satellite API key is empty"
        raise RuntimeError(message)
    return api_key


def _node_by_url(model: NodeModel, api_url: str) -> Any | None:  # noqa: ANN401
    """Find an existing node without changing operator-selected display data."""
    normalized_url = api_url.rstrip("/")
    return model.query.filter(func.rtrim(model.api_url, "/") == normalized_url).order_by(model.id).first()


def _available_name(model: NodeModel, preferred_name: str) -> str:
    """Avoid overwriting an unrelated node that already owns the default name."""
    if model.query.filter_by(name=preferred_name).first() is None:
        return preferred_name

    suffix = 2
    while model.query.filter_by(name=f"{preferred_name} ({suffix})").first() is not None:
        suffix += 1
    return f"{preferred_name} ({suffix})"


def _payload(spec: NodeSpec, api_key: str, existing: Any | None) -> dict[str, str]:  # noqa: ANN401
    """Build a create/update payload while preserving existing display metadata."""
    return {
        "id": existing.id if existing is not None else "",
        "name": existing.name if existing is not None else _available_name(spec.model, spec.default_name),
        "description": existing.description if existing is not None else spec.description,
        "api_url": spec.api_url,
        "api_key": api_key,
    }


def _capability_types(node: Any, relationship: str) -> set[str]:  # noqa: ANN401
    """Return the discovered capability types for a persisted node."""
    return {capability.type for capability in getattr(node, relationship)}


def _ensure_node(spec: NodeSpec, api_key: str) -> Any:  # noqa: ANN401
    """Create or refresh one node, retrying until its service is ready."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        existing = _node_by_url(spec.model, spec.api_url)
        payload = _payload(spec, api_key, existing)
        try:
            status = spec.update(existing.id, payload) if existing is not None else spec.add(payload)
            db_manager.db.session.expire_all()
            node = _node_by_url(spec.model, spec.api_url)
            capabilities = _capability_types(node, spec.relationship) if node is not None else set()
            capability_ready = spec.required_capability is None or spec.required_capability in capabilities
            if status == HTTPStatus.OK and capabilities and capability_ready:
                print(f"Default {spec.label} ready: {', '.join(sorted(capabilities))}", flush=True)  # noqa: T201
                return node
        except Exception as error:
            db_manager.db.session.rollback()
            print(f"Default {spec.label} attempt {attempt}/{MAX_ATTEMPTS} failed: {error}", flush=True)  # noqa: T201

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_SECONDS)

    message = f"Default {spec.label} did not become ready after {MAX_ATTEMPTS} attempts"
    raise RuntimeError(message)


def _node_specs() -> tuple[NodeSpec, ...]:
    """Return the default Compose satellite manifest."""
    return (
        NodeSpec(
            "collector",
            CollectorsNode,
            "collectors",
            "http://collectors/",
            "Default Docker Collector",
            "Collector included in the default Docker installation.",
            collectors_manager.add_collectors_node,
            collectors_manager.update_collectors_node,
        ),
        NodeSpec(
            "bot",
            BotsNode,
            "bots",
            "http://bots/",
            "Default Docker Bot",
            "Bot included in the default Docker installation.",
            bots_manager.add_bots_node,
            bots_manager.update_bots_node,
        ),
        NodeSpec(
            "presenter",
            PresentersNode,
            "presenters",
            DEFAULT_PRESENTER_URL,
            "Default Docker Presenter",
            "Presenter included in the default Docker installation.",
            presenters_manager.add_presenters_node,
            presenters_manager.update_presenters_node,
            "HTML_PRESENTER",
        ),
        NodeSpec(
            "publisher",
            PublishersNode,
            "publishers",
            "http://publishers/",
            "Default Docker Publisher",
            "Publisher included in the default Docker installation.",
            publishers_manager.add_publishers_node,
            publishers_manager.update_publishers_node,
        ),
    )


def bootstrap() -> None:
    """Run the idempotent Docker initialization sequence."""
    app = Flask(__name__)
    app.config.from_object("config.Config")
    db_manager.initialize(app)
    db_manager.wait_for_db(app)

    with app.app_context():
        api_key = _read_api_key()
        for spec in _node_specs():
            _ensure_node(spec, api_key)

        repair_distribution_bundle(db_manager.db.engine, DEFAULT_PRESENTER_URL, preserve_partial=True)
        print("Docker initialization complete.", flush=True)  # noqa: T201
        db_manager.db.session.remove()
        db_manager.db.engine.dispose()


if __name__ == "__main__":
    bootstrap()
