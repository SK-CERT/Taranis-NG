"""API manager to initialize all API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api import isalive, presenters
from flask_restful import Api

if TYPE_CHECKING:
    import Flask


def initialize(app: Flask) -> None:
    """Initialize all API endpoints."""
    api = Api(app)

    isalive.initialize(api)
    presenters.initialize(api)
