"""Per-request site context: which web is being served, in which language, and the branding/feed config.

A public-web container serves several "webs" (branded feeds), one per hostname.
For each request we pick the web by the ``Host`` header, choose a language
(``?lang=`` → ``Accept-Language`` → the web's default), and expose the config
resolved for that web+language (with the built-in presentation defaults from
``lib/config_reader.py`` as the fallback layer). The result is attached to
``flask.g.site``.
"""

from urllib.parse import urlparse

from flask import g, request, url_for
from lib import config

# Translatable branding fields, grouped by the template dict they feed. Stored
# per-language under web.config["text"][field] = {lang: value}.
_METADATA_TEXT = ["site_name", "rss_title", "rss_description", "meta_description", "meta_keywords"]
# Per-language content fields (the URLs are per-language too, each with a legacy
# neutral fallback handled in `content`).
_CONTENT_TEXT = ["homepage_title", "service_description_title", "organization_url", "service_description_url", "service_warning"]
# Per-language URLs that keep a legacy neutral (top-level) fallback for configs
# created before they moved into config["text"].
_CONTENT_URL = ["organization_url", "service_description_url"]
_FEEDBACK_KEYS = ["question1", "question2", "question3", "comment"]

IMAGE_KINDS = ("logo", "favicon", "preview")


def _pick(variants: dict[str, str] | str, language: str, default_language: str) -> str | None:
    """Pick the best value from a `{lang: value}` map (or a plain string)."""
    if isinstance(variants, dict):
        return variants.get(language) or variants.get(default_language) or next((v for v in variants.values() if v), None)
    if isinstance(variants, str):
        return variants or None
    return None


class SiteContext:
    """The web + language resolved for the current request."""

    def __init__(self, web: dict | None, language: str) -> None:
        """Initialize the site context with the resolved web and language."""
        self.web = web or {}
        self.cfg = self.web.get("config") or {}
        self.language = language

    # -- basics ------------------------------------------------------------

    @property
    def id(self) -> int | None:
        """The database id of the resolved web, or ``None``."""
        return self.web.get("id")

    @property
    def default_language(self) -> str:
        """The web's default language, falling back to the global default."""
        return self.cfg.get("default_language") or config.default_language()

    @property
    def languages(self) -> list[str]:
        """Languages offered by this web; defaults to the default language."""
        langs = self.cfg.get("languages")
        return langs if isinstance(langs, list) and langs else [self.default_language]

    @property
    def hostname(self) -> str:
        """Absolute base URL for RSS/OG links (scheme + host)."""
        host = self.web.get("hostname")
        if host:
            return host if "://" in host else f"https://{host}"
        return request.url_root.rstrip("/")

    def text(self, field: str, fallback: str = "") -> str:
        """Resolve a per-language branding text field, or return ``fallback``."""
        value = _pick((self.cfg.get("text") or {}).get(field), self.language, self.default_language)
        return value if value is not None else fallback

    # -- resolved config dicts (built-in presentation defaults as fallback) -

    @property
    def metadata(self) -> dict:
        """Resolved metadata dict (site name, RSS title/description, meta fields)."""
        base = dict(config.web_metadata())
        for field in _METADATA_TEXT:
            if value := self.text(field):
                base[field] = value
        base["rss_name"] = base.get("site_name", "")
        return base

    @property
    def content(self) -> dict:
        """Resolved content dict (homepage title, URLs, organization label, warning)."""
        base = dict(config.web_content())
        for field in _CONTENT_TEXT:
            if value := self.text(field):
                base[field] = value
        for field in _CONTENT_URL:
            # Per-language URL wins; fall back to a legacy neutral (top-level) value.
            if not self.text(field) and (legacy := self.cfg.get(field)):
                base[field] = legacy
        # Organization label: a neutral dropdown value, legacy per-language fallback.
        if value := (self.cfg.get("organization") or self.text("organization")):
            base["organization"] = value
        return base

    @property
    def images(self) -> dict:
        """Resolved image URLs plus logo dimensions for this web."""
        defaults = config.web_images()
        result = {kind: self.image_url(kind) for kind in IMAGE_KINDS}
        result["logo_height"] = self.cfg.get("logo_height") or defaults.get("logo_height")
        result["logo_width"] = self.cfg.get("logo_width") or defaults.get("logo_width")
        return result

    @property
    def feedback_questions(self) -> dict:
        """Resolved feedback question/comment labels for this web."""
        base = dict(config.feedback_questions())
        for key in _FEEDBACK_KEYS:
            if value := self.text(f"feedback_{key}"):
                base[key] = value
        return base

    @property
    def feedback_recipients(self) -> list[str]:
        """Recipient list for feedback e-mails for this specific website.

        Falls back to the global PUBLIC_WEB_MAIL_ADMINS when unset.
        """
        value = self.cfg.get("feedback_recipients")
        if isinstance(value, list):
            recipients = [address.strip() for address in value if isinstance(address, str) and address.strip()]
            if recipients:
                return recipients
        if isinstance(value, str):
            recipients = [address.strip() for address in value.split(",") if address.strip()]
            if recipients:
                return recipients
        return config.admin_mail()

    @property
    def feedback_sender(self) -> str:
        """Envelope sender for feedback e-mails for this specific website."""
        value = self.cfg.get("email_sender")
        return value.strip() if isinstance(value, str) and value.strip() else "public-web@localhost"

    @property
    def feedback_subject(self) -> str:
        """Subject template/value for feedback e-mails for this specific website."""
        value = self.cfg.get("email_subject")
        return value.strip() if isinstance(value, str) and value.strip() else ""

    @property
    def feedback_smtp(self) -> dict[str, str | int] | None:
        """SMTP config for feedback e-mails for this specific website.

        Returns None when no SMTP host is configured.
        """
        host = self.cfg.get("smtp_url")
        if not isinstance(host, str) or not host.strip():
            return None

        host_value = host.strip()
        parsed = urlparse(host_value)
        if parsed.scheme and parsed.hostname:
            host_value = parsed.hostname

        smtp: dict[str, str | int] = {"host": host_value}

        port = self.cfg.get("smtp_port")
        if isinstance(port, int):
            smtp["port"] = port
        elif isinstance(port, str) and port.strip().isdigit():
            smtp["port"] = int(port.strip())
        elif parsed.scheme and parsed.port:
            smtp["port"] = parsed.port

        user = self.cfg.get("smtp_username")
        if isinstance(user, str) and user.strip():
            smtp["user"] = user.strip()

        password = self.cfg.get("smtp_password")
        if isinstance(password, str) and password.strip():
            smtp["password"] = password.strip()

        return smtp

    @property
    def max_reports_homepage(self) -> int:
        """Max reports shown on the homepage, falling back to the global default."""
        return int(self.cfg.get("max_reports_homepage") or config.max_reports_homepage())

    @property
    def max_reports_rss(self) -> int:
        """Max reports included in the RSS feed, falling back to the global default."""
        return int(self.cfg.get("max_reports_rss") or config.max_reports_rss())

    # -- images ------------------------------------------------------------

    def image_url(self, kind: str) -> str:
        """URL for a branding image: the per-web image if uploaded, else the shipped default."""
        external = kind == "preview"  # og:image needs an absolute URL
        if kind in (self.web.get("images") or []):
            return url_for("reports.branding", kind=kind, _external=external)
        filename = config.web_images().get(kind)
        return url_for("static", filename=filename, _external=external) if filename else ""


def _match_web(webs: list[dict], host: str) -> dict | None:
    """Match a web strictly by hostname (no single-web fallback)."""
    host = (host or "").split(":")[0].lower()
    for web in webs:
        if (web.get("hostname") or "").split(":")[0].lower() == host:
            return web
    return None


def _select_language(web_cfg: dict) -> str:
    """`?lang=` (if offered) → best Accept-Language match → default_language."""
    languages = web_cfg.get("languages") if isinstance(web_cfg.get("languages"), list) else []
    default = web_cfg.get("default_language") or config.default_language()
    requested = request.args.get("lang")
    if requested and (not languages or requested in languages):
        return requested
    if languages:
        best = request.accept_languages.best_match(languages)
        if best:
            return best
    return default


def load_site(webs: list[dict]) -> SiteContext:
    """Build the SiteContext for the current request from the cached webs list."""
    web = _match_web(webs, request.host)
    language = _select_language(web.get("config") or {} if web else {})
    site = SiteContext(web, language)
    g.site = site
    return site


def current_site() -> SiteContext:
    """The current request's SiteContext (empty/defaults if none was loaded)."""
    site = getattr(g, "site", None)
    if site is None:
        site = SiteContext(None, config.default_language())
        g.site = site
    return site
