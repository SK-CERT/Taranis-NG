"""Module for Scheduled tasks collector."""

import datetime
import hashlib
import os
import secrets
import shlex
import subprocess
import uuid

from shared.common import TZ, ignore_exceptions
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData

from .base_collector import BaseCollector


class ScheduledTasksCollector(BaseCollector):
    """ScheduledTasksCollector is a class that collects data from scheduled tasks.

    Attributes:
        collector_type (str): The type of the collector.
        config (Config): Configuration object for the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (dict): Parameters for the collector.
    """

    collector_type = "SCHEDULED_TASKS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(collector_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @ignore_exceptions
    def collect(self) -> None:
        """Collect data from scheduled tasks.

        Raises:
            Exception: If the collection fails for any reason.
        """
        news_items = []
        cmd = self.source.param_key_values["TASK_COMMAND"]
        head, _tail = os.path.split(cmd)
        task_title = self.source.param_key_values["TASK_TITLE"]

        try:
            if head == "":
                task_command = cmd
            else:
                result = subprocess.run(  # noqa: S603
                    shlex.split(cmd),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                task_command = result.stdout

            review = self.source.param_key_values["TASK_DESCRIPTION"]
            author = ""
            osint_source = "TaranisNG System"
            link = ""
            content = task_command
            collected = datetime.datetime.now(TZ)
            published = datetime.datetime.now(TZ)
            random_string = secrets.token_urlsafe(10)

            news_item = NewsItemData(
                uuid.uuid4(),
                hashlib.sha256(random_string.encode()).hexdigest(),
                task_title,
                review,
                osint_source,
                link,
                published,
                author,
                collected,
                content,
                self.source.id,
                [],
            )

            news_items.append(news_item)

            self.publish(news_items, self.source)

        except Exception as error:
            self.source.logger.exception(f"Collection failed: {error}")
