"""Module for Slack collector."""

import datetime
import hashlib
import uuid
import time
import traceback
import socket

from slack import WebClient
from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.schema.news_item import NewsItemData
from shared.schema.parameter import Parameter, ParameterType


# the slackclient project is in maintenance mode now, "slack_sdk" is successor: https://pypi.org/project/slack-sdk/
class SlackCollector(BaseCollector):
    """Collector for gathering data from Slack.

    Attributes:
        type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.
    Methods:
        collect(source): Collects data from Slack source.
    """

    type = "SLACK_COLLECTOR"
    name = "Slack Collector"
    description = "Collector for gathering data from Slack"

    parameters = [
        Parameter(0, "SLACK_API_TOKEN", "Slack API token", "API token for Slack authentication.", ParameterType.STRING),
        Parameter(0, "WORKSPACE_CHANNELS_ID", "Collected workspace's channels ID", "Channels which will be collected.", ParameterType.STRING),
    ]

    parameters.extend(BaseCollector.parameters)

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from Slack source.

        Arguments:
            source: Source object.
        """
        self.collector_source = f"{self.name} '{source.name}':"
        BaseCollector.update_last_attempt(source)
        news_items = []
        proxy_server = source.parameter_values["PROXY_SERVER"]

        if proxy_server:

            server = "https://slack.com"
            port = 443

            server_proxy = proxy_server.rsplit(":", 1)[0]
            server_proxy_port = proxy_server.rsplit(":", 1)[-1]

            try:
                proxy = (str(server_proxy), int(server_proxy_port))
                connection = f"CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n"

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(proxy)
                s.send(str.encode(connection))
                s.recv(4096)
            except Exception:
                print(f"OSINTSource ID: {source.id}")
                print(f"OSINTSource name: {source.name}")
                print("Proxy connection failed")

        ids = source.parameter_values["WORKSPACE_CHANNELS_ID"].replace(" ", "")
        channels_list = ids.split(",")

        slack_client = WebClient(source.parameter_values["SLACK_API_TOKEN"])

        try:
            for channel_id in channels_list:
                logger.info(f"{self.collector_source} Channel: {channel_id}")
                channel_info = slack_client.conversations_info(channel=channel_id)
                channel_name = channel_info["channel"]["name"]

                # in future we can use parameter "oldest" - Only messages after this Unix timestamp will be included in results
                data = slack_client.conversations_history(channel=channel_id, limit=30)
                count = 0
                for message in data["messages"]:
                    count += 1
                    logger.debug(f"{self.collector_source} Message: {0}".format(count))
                    published = time.ctime(float(message["ts"]))
                    content = message["text"]
                    preview = content[:500]

                    user_id = message["user"]
                    user_name = slack_client.users_profile_get(user=user_id)
                    author = user_name["profile"]["real_name"]

                    team_id = message.get("team", "")
                    if team_id:
                        team_info = slack_client.team_info(team=team_id)
                        team_name = team_info["team"]["name"]
                    else:
                        team_name = ""

                    title = f"Slack post from channel {channel_name}"
                    if team_name:
                        title += f" ({team_name})"
                    link = ""
                    url = ""
                    for_hash = user_id + channel_id + content

                    logger.debug(f"{self.collector_source} ... Title    : {title}")
                    logger.debug(f"{self.collector_source} ... Content  : {content.replace('\r', '').replace('\n', ' ').strip()[:100]}")
                    logger.debug(f"{self.collector_source} ... Author   : {author}")
                    logger.debug(f"{self.collector_source} ... Published: {published}")

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        title,
                        preview,
                        url,
                        link,
                        published,
                        author,
                        datetime.datetime.now(),
                        content,
                        source.id,
                        [],
                    )
                    news_items.append(news_item)

            BaseCollector.publish(news_items, source)

        except Exception as ex:  # noqa F841
            logger.info(f"{self.collector_source} Error: {traceback.format_exc()}")
