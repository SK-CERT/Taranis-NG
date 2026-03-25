"""Provide functionality for managing the tag cloud."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import Flask
    from shared.time_manager import SchedulerManager


from model.tag_cloud import TagCloud


def job(app: Flask) -> None:
    """Delete words from the tag cloud.

    This function runs within the application context and deletes
    words from the tag cloud.

    Args:
        app: The Flask application instance.
    """
    with app.app_context():
        TagCloud.delete_words()


def initialize(app: Flask) -> None:
    """Initialize the tag cloud manager.

    Args:
        app: The Flask application instance.
    """


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Schedule tag cloud words cleanup.

    Args:
        manager: time manager class.
        app: The Flask application instance.
    """
    manager.schedule_job_every_day("00:01", job, "Tag cloud words cleanup", app)
