"""Definition for collector modules."""

from shared.schema.parameter import ParameterType

from .config_base import ConfigBase, ModuleType, ParamType


class ConfigCollector(ConfigBase):
    """Configuration for collector modules."""

    def add_default(self) -> list[ParamType]:
        """Add default parameters."""
        return [
            ParamType(
                "PROXY_SERVER",
                "Proxy server",
                "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                ParameterType.STRING,
            ),
            ParamType(
                "REFRESH_INTERVAL",
                "Refresh interval in minutes (0 to disable)",
                "How often is this collector queried for new data",
                ParameterType.NUMBER,
                "180",
            ),
            ParamType(
                "WARNING_INTERVAL",
                "No new data warning interval in days (0 to disable)",
                "How long to wait before marking the source with a warning due to no new data received",
                ParameterType.NUMBER,
                "30",
            ),
        ]

    def __init__(self) -> None:
        """Initialize collector modules."""
        self.modules: list[ModuleType] = []

        mod = ModuleType(
            "CSAF_COLLECTOR",
            "CSAF Collector",
            "Collector for security advisories in the CSAF format (OASIS Common Security Advisory Framework 2.0 and 2.1)",
        )
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType(
                    "CSAF_URL",
                    "CSAF URL",
                    (
                        "Where the advisories are published: a domain (discovered through /.well-known/csaf or security.txt), "
                        "a provider-metadata.json URL, a ROLIE feed, an RSS or Atom feed linking to CSAF documents, "
                        "a directory containing changes.csv, or a GitHub repository (https://github.com/<owner>/<repo>, "
                        "optionally /tree/<branch>/<folder>). Provider metadata pulls every distribution it lists, "
                        "except one named as VEX (e.g. csaf-vex/) while csaf_vex is skipped; point at one directory or "
                        "feed to limit that."
                    ),
                    ParameterType.STRING,
                ),
                ParamType(
                    "USER_AGENT",
                    "User agent",
                    (
                        "OPTIONAL: String sent in the request header to identify the collector. Leave empty to send the "
                        "standard client identifier (python-requests): some providers block unknown or browser-like values."
                    ),
                    ParameterType.STRING,
                ),
                ParamType(
                    "PUBLIC_KEY_URLS",
                    "Public OpenPGP key URLs",
                    (
                        "OPTIONAL: Comma-separated URLs of OpenPGP public keys used to verify signatures, in addition to the "
                        "keys listed in the provider metadata. Needed when the provider metadata cannot be reached."
                    ),
                    ParameterType.STRING,
                ),
                ParamType(
                    "SKIP_CATEGORIES",
                    "Skip document categories",
                    (
                        "OPTIONAL: Comma-separated CSAF document categories to ignore (e.g. csaf_vex). Empty collects every "
                        "category. While csaf_vex is skipped, a distribution named as VEX (e.g. csaf-vex/ or vex/) is not "
                        "read at all."
                    ),
                    ParameterType.STRING,
                    "csaf_vex",
                ),
                ParamType(
                    "MAX_DOCUMENTS",
                    "Limit for documents per run",
                    (
                        "Maximum number of new or changed documents collected from each distribution in one run. "
                        "The first run collects only this many of the newest documents."
                    ),
                    ParameterType.NUMBER,
                    "100",
                ),
                ParamType(
                    "VERIFY_SIGNATURES",
                    "Verify hashes and signatures",
                    (
                        "OPTIONAL: Check each document against its published SHA-256/SHA-512 hash and OpenPGP signature. "
                        "Documents are collected either way; the result is stored as an attribute. Default: true"
                    ),
                    ParameterType.BOOLEAN,
                    "true",
                ),
                ParamType(
                    "CHECK_IF_MODIFIED",
                    "Check if modified",
                    (
                        "OPTIONAL: Ask the server whether each listing (changes.csv, feed or repository tree) changed "
                        "since the last run (If-None-Match / If-Modified-Since) and skip reading it when it reports "
                        "no change. Turn off for servers that refuse the request or answer it wrongly. Default: true"
                    ),
                    ParameterType.BOOLEAN,
                    "true",
                ),
                ParamType(
                    "RESURFACE_NEW_VERSIONS",
                    "Resurface new versions",
                    (
                        "OPTIONAL: When a newer version of an advisory already collected arrives, mark its news item unread "
                        "again and list it with the items collected now, showing it again if it was deleted. Turn off to "
                        "update the item quietly: it shows the new version and keeps the older ones in its history, but "
                        "stays read and where it was listed. Default: true"
                    ),
                    ParameterType.BOOLEAN,
                    "true",
                ),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("EMAIL_COLLECTOR", "EMAIL Collector", "Collector for gathering data from emails")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("EMAIL_SERVER_TYPE", "Email server type", "IMAP or POP3 protocol", ParameterType.STRING),
                ParamType("EMAIL_SERVER_HOSTNAME", "Email server hostname", "Hostname of email server", ParameterType.STRING),
                ParamType("EMAIL_SERVER_PORT", "Email server port", "Port of email server", ParameterType.NUMBER),
                ParamType("EMAIL_USERNAME", "Username", "Username of email account", ParameterType.STRING),
                ParamType("EMAIL_PASSWORD", "Password", "Password of email account", ParameterType.STRING),
                ParamType("EMAIL_SENDER", "Sender (optional)", "Address of the sender (used for sorting)", ParameterType.STRING),
                ParamType(
                    "EMAILS_LIMIT",
                    "Limit for emails (optional)",
                    "Limit number of emails to process. Default: all",
                    ParameterType.NUMBER,
                ),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("MANUAL_COLLECTOR", "Manual Collector", "Collector for manual input of news items")
        mod.parameters = self.add_default()
        self.modules.append(mod)

        mod = ModuleType("RSS_COLLECTOR", "RSS Collector", "Collector for gathering data from RSS and Atom feeds")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("FEED_URL", "Feed URL", "Full URL for RSS or Atom feed", ParameterType.STRING),
                ParamType(
                    "USER_AGENT",
                    "User agent",
                    "String sent in the request header to identify itself to the web server (e.g. browser type, version, OS...)",
                    ParameterType.STRING,
                ),
                ParamType(
                    "LINKS_LIMIT",
                    "Limit for article links",
                    "OPTIONAL: Maximum number of article links to process. Default: all",
                    ParameterType.NUMBER,
                ),
                ParamType(
                    "PREFER_SCRAPING",
                    "Prefer web scraping over feed content",
                    (
                        "OPTIONAL: Whether to try scraping content from the link in the feed. "
                        "Otherwise uses web scraping only if there is no feed content. "
                        "Default: Prefer RSS content."
                    ),
                    ParameterType.BOOLEAN,
                    "false",
                ),
                ParamType(
                    "CHECK_IF_MODIFIED",
                    "Check if modified",
                    (
                        "OPTIONAL: Ask the server whether the content changed since the last collection "
                        "(If-Modified-Since) and skip the run when it reports no change. Turn off for sites "
                        "that refuse the request or answer it wrongly. Default: true"
                    ),
                    ParameterType.BOOLEAN,
                    "true",
                ),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("SCHEDULED_TASKS_COLLECTOR", "Scheduled tasks Collector", "Collector for collecting scheduled tasks")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("TASK_TITLE", "Task title", "Title of scheduled task", ParameterType.STRING),
                ParamType("TASK_COMMAND", "Task command", "Command which will be executed", ParameterType.STRING),
                ParamType("TASK_DESCRIPTION", "Task description", "Description of scheduled task", ParameterType.STRING),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("SLACK_COLLECTOR", "Slack Collector", "Collector for gathering data from Slack")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("SLACK_API_TOKEN", "Slack API token", "API token for Slack authentication.", ParameterType.STRING),
                ParamType(
                    "WORKSPACE_CHANNELS_ID",
                    "Collected workspace's channels ID",
                    "Channels which will be collected.",
                    ParameterType.STRING,
                ),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("TWITTER_COLLECTOR", "Twitter Collector", "Collector for gathering data from Twitter")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
                ParamType("TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account", ParameterType.STRING),
                ParamType("TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account", ParameterType.STRING),
                ParamType(
                    "TWITTER_ACCESS_TOKEN_SECRET",
                    "Twitter access token secret",
                    "Twitter access token secret of Twitter account",
                    ParameterType.STRING,
                ),
                ParamType("SEARCH_KEYWORDS", "Search by keywords", "Search tweets by keywords", ParameterType.STRING),
                ParamType("SEARCH_HASHTAGS", "Search by hashtags", "Search tweets by hashtags", ParameterType.STRING),
                ParamType("NUMBER_OF_TWEETS", "Number of tweets", "How many tweets will be provided", ParameterType.NUMBER),
            ],
        )
        self.modules.append(mod)

        mod = ModuleType("WEB_COLLECTOR", "Web Collector", "Collector for gathering data from web page")
        mod.parameters = self.add_default()
        mod.parameters.extend(
            [
                ParamType("WEB_URL", "Web URL", "Full url for web page or folder of html file", ParameterType.STRING),
                # TODO (Ján): implement ENUM for the keys?
                ParamType("WEBDRIVER", "Name of Webdriver", "Name of webdriver for Selenium (chrome | firefox)", ParameterType.STRING),
                ParamType("TOR", "Route traffic through Tor", "Using Tor service (true | false)", ParameterType.BOOLEAN, "false"),
                ParamType(
                    "CHECK_IF_MODIFIED",
                    "Check if modified",
                    (
                        "OPTIONAL: Ask the server whether the content changed since the last collection "
                        "(If-Modified-Since) and skip the run when it reports no change. Turn off for sites "
                        "that refuse the request or answer it wrongly. Default: true"
                    ),
                    ParameterType.BOOLEAN,
                    "true",
                ),
                ParamType(
                    "USER_AGENT",
                    "User agent",
                    "String sent in the request header to identify itself to the web server (e.g. browser type, version, OS...)",
                    ParameterType.STRING,
                ),
                # authentication options
                ParamType(
                    "AUTH_USERNAME",
                    "Username for web page authentication",
                    "Username for authentication with basic auth header",
                    ParameterType.STRING,
                ),
                ParamType(
                    "AUTH_PASSWORD",
                    "Password for web page authentication",
                    "Password for authentication with basic auth header",
                    ParameterType.STRING,
                ),
                # TODO (*): reimplement for new web collector
                ParamType(
                    "CLIENT_CERT_DIR",
                    "PATH to directory with client's certificates",
                    "PATH to client's certificates directory",
                    ParameterType.STRING,
                ),
                # removing popups
                ParamType(
                    "POPUP_CLOSE_SELECTOR",
                    "SELECTOR at TITLE PAGE: Popup removal",
                    "OPTIONAL: For sites with popups, this is a selector of the clickable element (button or a link) "
                    "for the popup removal button",
                    ParameterType.STRING,
                ),
                # navigating the list of articles page by page
                ParamType(
                    "NEXT_BUTTON_SELECTOR",
                    "SELECTOR at TITLE PAGE: Next page",
                    "OPTIONAL: For sites with pagination, this is a selector of the clickable element (button or a link) for the 'next page'",
                    ParameterType.STRING,
                ),
                ParamType(
                    "LOAD_MORE_BUTTON_SELECTOR",
                    "SELECTOR at TITLE PAGE: Load more",
                    "OPTIONAL: For sites with progressive loading, this is a selector of the clickable element (button or a link) "
                    "for the 'load more'",
                    ParameterType.STRING,
                ),
                ParamType(
                    "PAGINATION_LIMIT",
                    "Pagination limit",
                    "OPTIONAL: For sites with pagination or progressive loading, maximum number of pages to visit. "
                    "Default: 1 (stay on the first page only)",
                    ParameterType.NUMBER,
                ),
                # obtaining links to articles (optional)
                ParamType(
                    "SINGLE_ARTICLE_LINK_SELECTOR",
                    "SELECTOR at TITLE PAGE: Links to articles",
                    "Selector that matches the link to the article. Matching results should contain a 'href' attribute.",
                    ParameterType.STRING,
                ),
                ParamType(
                    "LINKS_LIMIT",
                    "Limit for article links",
                    "OPTIONAL: Maximum number of article links to process. Default: all",
                    ParameterType.NUMBER,
                ),
                # parsing a single article
                ParamType("TITLE_SELECTOR", "SELECTOR at ARTICLE: Article title", "Selector for article title", ParameterType.STRING),
                ParamType(
                    "ARTICLE_DESCRIPTION_SELECTOR",
                    "SELECTOR at ARTICLE: short summary",
                    "OPTIONAL: Selector of article description or summary",
                    ParameterType.STRING,
                ),
                ParamType(
                    "ARTICLE_FULL_TEXT_SELECTOR",
                    "SELECTOR at ARTICLE: Article content",
                    "Selector for the article content / text of the article",
                    ParameterType.STRING,
                ),
                ParamType(
                    "AUTHOR_SELECTOR",
                    "SELECTOR at ARTICLE: Author",
                    "OPTIONAL: Selector to find the author of the post",
                    ParameterType.STRING,
                ),
                ParamType(
                    "PUBLISHED_SELECTOR",
                    "SELECTOR at ARTICLE: Date published",
                    "OPTIONAL: Selector of the 'published' date",
                    ParameterType.STRING,
                ),
                # TODO (*): reimplement for new web collector
                ParamType(
                    "ATTACHMENT_SELECTOR",
                    "SELECTOR at ARTICLE: Attachment selector",
                    "OPTIONAL: Selector for links to article attachments",
                    ParameterType.STRING,
                ),
                ParamType(
                    "WORD_LIMIT",
                    "Limit article body to this many words",
                    "Collect only first few words of the article (perhaps for legal reasons)",
                    ParameterType.STRING,
                ),
                # legacy options, to be studied in more detail or removed
                ParamType(
                    "ADDITIONAL_ID_SELECTOR",
                    "SELECTOR at ARTICLE: Additional ID selector",
                    "OPTIONAL: Selector of an additional article ID",
                    ParameterType.STRING,
                ),
            ],
        )
        self.modules.append(mod)
