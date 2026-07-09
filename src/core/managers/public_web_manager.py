"""Periodic health check for public-web nodes.

A scheduled job calls each public-web node's management ``isalive`` endpoint and
records a successful contact in ``last_seen``, which drives the green/orange/red
status shown in the Configuration UI (mirroring the other nodes).
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask
    from shared.time_manager import SchedulerManager

from managers.log_manager import logger
from model.public_web_node import PublicWebNode
from remote.public_web_api import PublicWebApi


def job(app: Flask) -> None:
    """Ping every public-web node that has a management URL; refresh last_seen."""
    with app.app_context():
        for node in PublicWebNode.get_all():
            if not node.api_url:
                continue
            try:
                _, status = PublicWebApi(node.api_url, node.api_key).isalive()
                if status == HTTPStatus.OK:
                    node.update_last_seen()
            except Exception as ex:
                logger.debug(f"Public-web node '{node.name}' health check error: {ex}")


def initialize(app: Flask) -> None:
    """No-op initializer (kept for symmetry with the other managers)."""


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Schedule the public-web node health check every minute."""
    manager.schedule_job_minutes(1, job, "Public-web node health check", app)
