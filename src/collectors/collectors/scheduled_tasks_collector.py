"""Module for Scheduled tasks collector."""

import datetime
import hashlib
import os
import random
import string
import uuid

from .base_collector import BaseCollector
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


class ScheduledTasksCollector(BaseCollector):
    """ScheduledTasksCollector is a class that collects data from scheduled tasks.

    Attributes:
        type (str): The type of the collector.
        config (Config): Configuration object for the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (dict): Parameters for the collector.
    """

    type = "SCHEDULED_TASKS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from scheduled tasks.

        Args:
            source (Source): The source object containing the parameters for the collection.
        Raises:
            Exception: If the collection fails for any reason.
        """
        self.source = source
        news_items = []
        head, tail = os.path.split(source.param_key_values["TASK_COMMAND"])
        task_title = source.param_key_values["TASK_TITLE"]

        try:
            if head == "":
                task_command = source.param_key_values["TASK_COMMAND"]
            else:
                task_command = os.popen("." + source.param_key_values["TASK_COMMAND"]).read()

            review = source.param_key_values["TASK_DESCRIPTION"]
            author = ""
            osint_source = "TaranisNG System"
            link = ""
            content = task_command
            collected = datetime.datetime.now()
            published = datetime.datetime.now()

            letters = string.ascii_lowercase
            random_string = "".join(random.choice(letters) for i in range(10))

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
                source.id,
                [],
            )

            news_items.append(news_item)

            BaseCollector.publish(news_items, source)

        except Exception as error:
            self.source.logger.exception(f"Collection failed: {error}")
