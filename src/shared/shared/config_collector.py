"""Definition for collector modules."""

from .config_base import ConfigBase, module_type, param_type
from typing import List
from shared.schema.parameter import ParameterType


class ConfigCollector(ConfigBase):
    """XXX_2069."""

    def add_default(self) -> List[param_type]:
        """XXX_2069."""
        return [
            param_type(
                "PROXY_SERVER", "Proxy server", "Type SOCKS5 proxy server as username:password@ip:port or ip:port", ParameterType.STRING
            ),
            param_type(
                "REFRESH_INTERVAL",
                "Refresh interval in minutes (0 to disable)",
                "How often is this collector queried for new data",
                ParameterType.NUMBER,
            ),
        ]

    def __init__(self):
        """XXX_2069."""
        self.modules: List[module_type] = []

        mod = module_type("ATOM_COLLECTOR", "Atom Collector", "Collector for gathering data from Atom feeds")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("ATOM_FEED_URL", "Atom feed URL", "Full url for Atom feed", ParameterType.STRING),
                param_type("USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING),
                param_type(
                    "LINKS_LIMIT",
                    "Limit for article links",
                    "OPTIONAL: Maximum number of article links to process. Default: all",
                    ParameterType.NUMBER,
                ),
            ]
        )
        self.modules.append(mod)

        mod = module_type("EMAIL_COLLECTOR", "EMAIL Collector", "Collector for gathering data from emails")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("EMAIL_SERVER_TYPE", "Email server type", "IMAP or POP3 protocol", ParameterType.STRING),
                param_type("EMAIL_SERVER_HOSTNAME", "Email server hostname", "Hostname of email server", ParameterType.STRING),
                param_type("EMAIL_SERVER_PORT", "Email server port", "Port of email server", ParameterType.NUMBER),
                param_type("EMAIL_USERNAME", "Username", "Username of email account", ParameterType.STRING),
                param_type("EMAIL_PASSWORD", "Password", "Password of email account", ParameterType.STRING),
            ]
        )
        self.modules.append(mod)

        mod = module_type("MANUAL_COLLECTOR", "Manual Collector", "Collector for manual input of news items")
        mod.parameters = self.add_default()
        self.modules.append(mod)

        mod = module_type("RSS_COLLECTOR", "RSS Collector", "Collector for gathering data from RSS and Atom feeds")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("FEED_URL", "Feed URL", "Full URL for RSS or Atom feed", ParameterType.STRING),
                param_type("USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING),
                param_type(
                    "LINKS_LIMIT",
                    "Limit for article links",
                    "OPTIONAL: Maximum number of article links to process. Default: all",
                    ParameterType.NUMBER,
                ),
            ]
        )
        self.modules.append(mod)

        mod = module_type("SCHEDULED_TASKS_COLLECTOR", "Scheduled tasks Collector", "Collector for collecting scheduled tasks")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("TASK_TITLE", "Task title", "Title of scheduled task", ParameterType.STRING),
                param_type("TASK_COMMAND", "Task command", "Command which will be executed", ParameterType.STRING),
                param_type("TASK_DESCRIPTION", "Task description", "Description of scheduled task", ParameterType.STRING),
            ]
        )
        self.modules.append(mod)

        mod = module_type("SLACK_COLLECTOR", "Slack Collector", "Collector for gathering data from Slack")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("SLACK_API_TOKEN", "Slack API token", "API token for Slack authentication.", ParameterType.STRING),
                param_type(
                    "WORKSPACE_CHANNELS_ID", "Collected workspace's channels ID", "Channels which will be collected.", ParameterType.STRING
                ),
            ]
        )
        self.modules.append(mod)

        mod = module_type("TWITTER_COLLECTOR", "Twitter Collector", "Collector for gathering data from Twitter")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
                param_type("TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account", ParameterType.STRING),
                param_type("TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account", ParameterType.STRING),
                param_type(
                    "TWITTER_ACCESS_TOKEN_SECRET",
                    "Twitter access token secret",
                    "Twitter access token secret of Twitter account",
                    ParameterType.STRING,
                ),
                param_type("SEARCH_KEYWORDS", "Search by keywords", "Search tweets by keywords", ParameterType.STRING),
                param_type("SEARCH_HASHTAGS", "Search by hashtags", "Search tweets by hashtags", ParameterType.STRING),
                param_type("NUMBER_OF_TWEETS", "Number of tweets", "How many tweets will be provided", ParameterType.NUMBER),
            ]
        )
        self.modules.append(mod)

        mod = module_type("WEB_COLLECTOR", "Web Collector", "Collector for gathering data from web page")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                param_type("WEB_URL", "Web URL", "Full url for web page or folder of html file", ParameterType.STRING),
                # TODO: implement ENUM
                param_type("WEBDRIVER", "Name of Webdriver", "Name of webdriver for Selenium (chrome|firefox)", ParameterType.STRING),
                # TODO: change to BOOLEAN, implement defaults, default False
                param_type("TOR", "Do you want to use Tor service? Enter Yes or No", "Using Tor service (yes|no)", ParameterType.STRING),
                param_type("USER_AGENT", "User agent", "Set user agent", ParameterType.STRING),
                # authentication options
                param_type(
                    "AUTH_USERNAME",
                    "Username for web page authentication",
                    "Username for authentication with basic auth header",
                    ParameterType.STRING,
                ),
                param_type(
                    "AUTH_PASSWORD",
                    "Password for web page authentication",
                    "Password for authentication with basic auth header",
                    ParameterType.STRING,
                ),
                # TODO reimplement for new web collector
                param_type(
                    "CLIENT_CERT_DIR",
                    "PATH to directory with client's certificates",
                    "PATH to client's certificates directory",
                    ParameterType.STRING,
                ),
                # removing popups
                param_type(
                    "POPUP_CLOSE_SELECTOR",
                    "SELECTOR at TITLE PAGE: Popup removal",
                    "OPTIONAL: For sites with popups, this is a selector of the clickable element (button or a link) "
                    "for the popup removal button",
                    ParameterType.STRING,
                ),
                # navigating the list of articles page by page
                param_type(
                    "NEXT_BUTTON_SELECTOR",
                    "SELECTOR at TITLE PAGE: Next page",
                    "OPTIONAL: For sites with pagination, this is a selector of the clickable element (button or a link) for the 'next page'",
                    ParameterType.STRING,
                ),
                param_type(
                    "LOAD_MORE_BUTTON_SELECTOR",
                    "SELECTOR at TITLE PAGE: Load more",
                    "OPTIONAL: For sites with progressive loading, this is a selector of the clickable element (button or a link) "
                    "for the 'load more'",
                    ParameterType.STRING,
                ),
                param_type(
                    "PAGINATION_LIMIT",
                    "Pagination limit",
                    "OPTIONAL: For sites with pagination or progressive loading, maximum number of pages to visit. "
                    "Default: 1 (stay on the first page only)",
                    ParameterType.NUMBER,
                ),
                # obtaining links to articles (optional)
                param_type(
                    "SINGLE_ARTICLE_LINK_SELECTOR",
                    "SELECTOR at TITLE PAGE: Links to articles",
                    "Selector that matches the link to the article. Matching results should contain a 'href' attribute.",
                    ParameterType.STRING,
                ),
                param_type(
                    "LINKS_LIMIT",
                    "Limit for article links",
                    "OPTIONAL: Maximum number of article links to process. Default: all",
                    ParameterType.NUMBER,
                ),
                # parsing a single article
                param_type("TITLE_SELECTOR", "SELECTOR at ARTICLE: Article title", "Selector for article title", ParameterType.STRING),
                param_type(
                    "ARTICLE_DESCRIPTION_SELECTOR",
                    "SELECTOR at ARTICLE: short summary",
                    "OPTIONAL: Selector of article description or summary",
                    ParameterType.STRING,
                ),
                param_type(
                    "ARTICLE_FULL_TEXT_SELECTOR",
                    "SELECTOR at ARTICLE: Article content",
                    "Selector for the article content / text of the article",
                    ParameterType.STRING,
                ),
                param_type(
                    "AUTHOR_SELECTOR",
                    "SELECTOR at ARTICLE: Author",
                    "OPTIONAL: Selector to find the author of the post",
                    ParameterType.STRING,
                ),
                param_type(
                    "PUBLISHED_SELECTOR",
                    "SELECTOR at ARTICLE: Date published",
                    "OPTIONAL: Selector of the 'published' date",
                    ParameterType.STRING,
                ),
                # TODO reimplement for new web collector
                param_type(
                    "ATTACHMENT_SELECTOR",
                    "SELECTOR at ARTICLE: Attachment selector",
                    "OPTIONAL: Selector for links to article attachments",
                    ParameterType.STRING,
                ),
                param_type(
                    "WORD_LIMIT",
                    "Limit article body to this many words",
                    "Collect only first few words of the article (perhaps for legal reasons)",
                    ParameterType.STRING,
                ),
                # legacy options, to be studied in more detail or removed
                param_type(
                    "ADDITIONAL_ID_SELECTOR",
                    "SELECTOR at ARTICLE: Additional ID selector",
                    "OPTIONAL: Selector of an additional article ID",
                    ParameterType.STRING,
                ),
            ]
        )
        self.modules.append(mod)
