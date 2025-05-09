"""Provide functionality for managing the tag cloud.

This module implements Server-Sent Events (SSE) functionality and
schedules a daily job to manage the tag cloud.
"""

from shared import time_manager
from model.tag_cloud import TagCloud


def job(app):
    """Delete words from the tag cloud.

    This function runs within the application context and deletes
    words from the tag cloud.

    Parameters:
        app: The Flask application instance.
    """
    with app.app_context():
        TagCloud.delete_words()


def initialize(app):
    """Initialize the tag cloud manager.

    This function schedules a daily job to delete words from the
    tag cloud at a specified time.

    Parameters:
        app: The Flask application instance.
    """
    time_manager.schedule_job_every_day("00:01", job, app)
