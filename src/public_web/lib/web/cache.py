"""Report, web, and image caching for the public-web service.

Wraps cachelib's FileSystemCache and the Taranis API client to fetch, cache,
and invalidate vulnerability reports and web branding with a TTL.
"""

from cachelib import FileSystemCache
from flask import Response
from lib import config
from lib.logger import get_logger
from lib.report.vulnerability_report import VulnerabilityReport
from lib.web.taranis_client import TaranisClient, TaranisClientError

logger = get_logger("web-cache", silent=True)

CACHE_KEY_ALL_REPORTS = "ALL_REPORTS"
CACHE_KEY_RSS_RESPONSE = "RSS_RESPONSE"
CACHE_KEY_WEBS = "WEBS"


class WebCache:
    """Cache for reports fetched from the Taranis-NG API for the public web feed.

    Reports are fetched from the Taranis-NG core public-web API on a cache miss
    and cached with a TTL. This replaces the upstream file-based source.
    """

    def __init__(self, client: TaranisClient | None = None) -> None:
        """Initialize the cache with an optional custom Taranis client."""
        self.cache = FileSystemCache(
            cache_dir="/tmp/public-web-cache",  # noqa: S108
            default_timeout=config.cache_ttl(),
        )
        self.client = client or TaranisClient()

    def _fetch_all_reports(self, web_id: int | None = None) -> list[VulnerabilityReport]:
        """Fetch the latest published products from Taranis, newest first.

        Products that are not a valid TLP:CLEAR vulnerability report are skipped
        so one bad product cannot break the feed.
        """
        limit = config.max_reports_api()
        ids = self.client.list_published_product_ids(limit, web_id=web_id)
        reports: list[VulnerabilityReport] = []
        for product_id in ids:
            data = self.client.get_product(product_id, web_id=web_id)
            if data is None:
                continue
            try:
                reports.append(VulnerabilityReport.from_dict(data))
            except (ValueError, TypeError) as exc:
                logger.info("Skipping product %s: %s", product_id, exc)
        return reports

    def get_all_reports(self, web_id: int | None = None) -> list[VulnerabilityReport]:
        """Return the latest reports (newest first), fetched from Taranis and cached.

        Cached with a TTL. On an API failure, logs and returns an empty list
        without caching so the next request retries.
        """
        cache_key = f"{CACHE_KEY_ALL_REPORTS}:{web_id}" if web_id is not None else CACHE_KEY_ALL_REPORTS
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        try:
            reports = self._fetch_all_reports(web_id=web_id)
        except TaranisClientError as exc:
            logger.exception("Could not fetch reports from Taranis: %s", exc)
            return []
        # Only cache non-empty results: an empty feed usually means nothing is
        # published yet, and caching [] would hide a report published moments
        # later until the TTL expires.
        if reports:
            self.cache.set(cache_key, reports)
        return reports

    def get_report(self, report_id: str, web_id: int | None = None) -> VulnerabilityReport | None:
        """Return a single report by its Taranis product id.

        Looks in the cached list first, then fetches the product directly on a
        miss. Returns None if it is not a valid displayable report.
        """
        for report in self.get_all_reports(web_id=web_id):
            if str(report.get_id()) == str(report_id):
                return report
        try:
            product_id = int(report_id)
        except (TypeError, ValueError):
            return None
        try:
            data = self.client.get_product(product_id, web_id=web_id)
        except TaranisClientError as exc:
            logger.exception("Could not fetch product %s from Taranis: %s", report_id, exc)
            return None
        if data is None:
            return None
        try:
            return VulnerabilityReport.from_dict(data)
        except (ValueError, TypeError) as exc:
            logger.info("Product %s is not a displayable report: %s", report_id, exc)
            return None

    def get_rss_response(self) -> Response | None:
        """Returns cached RSS response, or None if the cache is empty/expired."""
        return self.cache.get(CACHE_KEY_RSS_RESPONSE)

    def cache_rss_response(self, response: Response) -> None:
        """Saves the RSS response to cache."""
        self.cache.set(CACHE_KEY_RSS_RESPONSE, response)

    def clear(self) -> None:
        """Drop everything (webs, images, reports) so the next requests refetch.

        Used by the management API when core pushes a cache reset after a config
        change. FileSystemCache is on disk, so this clears the shared cache.
        """
        self.cache.clear()

    def get_webs(self) -> list[dict]:
        """Return the node's webs (branded feeds + config) from Taranis, cached.

        Cached with a TTL. On an API failure, logs and returns an empty list
        without caching so the next request retries.
        """
        cached = self.cache.get(CACHE_KEY_WEBS)
        if cached:
            return cached
        try:
            webs = self.client.list_webs()
        except TaranisClientError as exc:
            logger.exception("Could not fetch webs from Taranis: %s", exc)
            return []
        if webs:
            self.cache.set(CACHE_KEY_WEBS, webs)
        return webs

    def get_web_image(self, web_id: int, kind: str) -> tuple[bytes, str] | None:
        """Return ``(bytes, mime_type)`` of a web's image, cached with a TTL.

        Returns None if it is absent / cannot be fetched.
        """
        cache_key = f"WEB_IMAGE:{web_id}:{kind}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            result = self.client.get_web_image(web_id, kind)
        except TaranisClientError as exc:
            logger.exception("Could not fetch image %s for web %s: %s", kind, web_id, exc)
            return None
        if result is not None:
            self.cache.set(cache_key, result)
        return result
