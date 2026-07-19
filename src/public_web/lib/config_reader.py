# pylint: disable=missing-function-docstring
"""Runtime configuration for public-web.

There is no config file. The live per-web presentation settings (branding text,
feed sizes, languages, images) are edited in the Taranis GUI (Configuration ->
Public Web) and fetched from core; this module only provides:

* deployment/operational settings, taken from environment variables, and
* built-in *fallback defaults* for the per-web presentation - used only when a
  web leaves a field unset, or while core is unreachable (see lib/web/site.py).

The per-language interface translations still live in conf/i18n/<language>.json.
"""

import json
import os
from pathlib import Path
from typing import Any

MAIN_DIR = Path(__file__).parent.parent

# Default location of the mounted Docker secret holding the shared node ApiKey
# (the same api_key.txt used by the collector/presenter/publisher/bot nodes).
DEFAULT_API_KEY_FILE = "/run/secrets/api_key"

# -- Operational defaults ---------------------------------------------------
DEFAULT_LANGUAGE = "en"
DEFAULT_CACHE_TTL = 90 * 60  # seconds
DEFAULT_CORE_URL = "http://core"
DEFAULT_LOG_DIR = "/tmp/public-web-logs"  # noqa: S108

# -- Built-in per-web presentation fallback defaults ------------------------
# These are code constants, NOT user configuration: the authoritative per-web
# settings come from the GUI. They only fill fields a web leaves unset (and keep
# the page rendering when core is unreachable). site.py merges them per web/lang.
DEFAULT_MAX_REPORTS_HOMEPAGE = 10
DEFAULT_MAX_REPORTS_RSS = 15

WEB_METADATA_DEFAULTS = {
    "hostname": "https://public-web.example.org",
    "site_name": "Public Web",
    "rss_title": "Vulnerability Reports",
    "rss_description": "Public feed of vulnerability reports.",
    "meta_description": "Public feed of vulnerability reports.",
    "meta_keywords": "vulnerabilities, vulnerability reports",
}
WEB_CONTENT_DEFAULTS = {
    "homepage_title": "Vulnerability Reports",
    "service_description_title": "Service Description",
    "service_description_url": "",
    "organization": "Your Organization",
    "organization_url": "",
    "service_warning": (
        "This service is provided as a best-effort aid to security. It does not "
        "guarantee coverage of all vulnerabilities and should complement, not "
        "replace, your own security management."
    ),
}
WEB_FEEDBACK_DEFAULTS = {
    "question1": "Do you find this report well prepared?",
    "question2": "Do you use this technology?",
    "question3": "Was this report useful to you?",
    "comment": "We will appreciate your additional comments:",
}
WEB_IMAGES_DEFAULTS = {
    "favicon": "favicon.ico",
    "preview": "preview.png",
    "logo": "logo.svg",
    "logo_height": "45",
    "logo_width": "90",
}


class ConfigReader:
    """Reads operational settings from the environment and serves the built-in.

    presentation defaults; loads per-language translations from conf/i18n/.
    """

    CONF_DIR = MAIN_DIR / "conf"
    TRANSLATIONS_DIR = CONF_DIR / "i18n"
    DEFAULT_LANGUAGE = DEFAULT_LANGUAGE

    def __init__(self) -> None:
        """Initialize the ConfigReader."""
        self._translations: dict[str, Any] = {}
        self._api_key: str | None = None

    # -- operational (environment) ----------------------------------------

    def is_production(self) -> bool:
        """Check if running in production mode.

        Defaults to production; the dev overlay sets PUBLIC_WEB_PRODUCTION=false.
        """
        env = os.getenv("PUBLIC_WEB_PRODUCTION")
        if env is None:
            return True
        return env.strip().lower() in ("1", "true", "yes", "on")

    def log_dir(self) -> Path:
        """Get the log directory path.

        Returns the configured log directory or the default.
        """
        return Path(os.getenv("PUBLIC_WEB_LOG_DIR") or DEFAULT_LOG_DIR)

    def admin_mail(self) -> list[str]:
        """Recipients of error/admin mail (PUBLIC_WEB_MAIL_ADMINS env, comma-separated)."""
        return self._mail_list(os.getenv("PUBLIC_WEB_MAIL_ADMINS") or "admin@example.org")

    @staticmethod
    def _mail_list(value: str) -> list[str]:
        return [address for address in (part.strip() for part in value.split(",")) if address]

    # -- Taranis-NG API integration ---------------------------------------

    def taranis_core_url(self) -> str:
        """Base URL of the Taranis-NG core API.

        (TARANIS_NG_CORE_URL env, else the compose service name).
        """
        return os.getenv("TARANIS_NG_CORE_URL") or DEFAULT_CORE_URL

    def taranis_api_key(self) -> str:
        """The shared node ApiKey used to authenticate to Taranis core.

        The env var PUBLIC_WEB_API_KEY wins (handy for local testing); otherwise it is read
        from the mounted Docker secret (the same api_key.txt as the other nodes).
        """
        if self._api_key is not None:
            return self._api_key

        env_key = os.getenv("PUBLIC_WEB_API_KEY")
        if env_key:
            self._api_key = env_key.strip()
            return self._api_key

        secret_file = os.getenv("PUBLIC_WEB_API_KEY_FILE", DEFAULT_API_KEY_FILE)
        try:
            self._api_key = Path(secret_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            msg = f"Taranis node ApiKey not found at '{secret_file}'. Set PUBLIC_WEB_API_KEY or mount the 'api_key' Docker secret."
            raise RuntimeError(msg) from exc
        return self._api_key

    def max_reports_api(self) -> int:
        """How many of the latest published products to fetch/render from Taranis.

        (PUBLIC_WEB_MAX_REPORTS env, else the larger of the homepage and RSS limits).
        """
        value = (os.getenv("PUBLIC_WEB_MAX_REPORTS") or "").strip()
        if value:
            return int(value)
        return max(self.max_reports_homepage(), self.max_reports_rss())

    def cache_ttl(self) -> int:
        """Cache lifetime in seconds for fetched data.

        (PUBLIC_WEB_CACHE_TTL env, else 90 minutes).
        """
        value = (os.getenv("PUBLIC_WEB_CACHE_TTL") or "").strip()
        return int(value) if value else DEFAULT_CACHE_TTL

    # -- Web presentation (built-in fallback defaults) --------------------

    def max_reports_homepage(self) -> int:
        """Get the default maximum reports for homepage."""
        return DEFAULT_MAX_REPORTS_HOMEPAGE

    def max_reports_rss(self) -> int:
        """Get the default maximum reports for RSS feed."""
        return DEFAULT_MAX_REPORTS_RSS

    def web_metadata(self) -> dict[str, str]:
        """Get the default web metadata."""
        return dict(WEB_METADATA_DEFAULTS)

    def web_content(self) -> dict[str, str]:
        """Get the default web content."""
        return dict(WEB_CONTENT_DEFAULTS)

    def feedback_questions(self) -> dict[str, str]:
        """Get the default feedback questions."""
        return dict(WEB_FEEDBACK_DEFAULTS)

    def web_images(self) -> dict[str, str]:
        """Get the default web images configuration."""
        return dict(WEB_IMAGES_DEFAULTS)

    def default_language(self) -> str:
        """Get the default language."""
        return os.getenv("PUBLIC_WEB_DEFAULT_LANGUAGE") or DEFAULT_LANGUAGE

    def get_translations(self, language: str) -> dict[str, Any]:
        """Loads translations from conf/i18n/<language>.json (cached).

        Falling back to English when there is no file for the given language.
        """
        if language not in self._translations:
            path = self.TRANSLATIONS_DIR / f"{language}.json"
            if not path.is_file():
                return self.get_translations(self.DEFAULT_LANGUAGE)
            with Path.open(path, encoding="utf-8") as file:
                self._translations[language] = json.load(file)
        return self._translations[language]
