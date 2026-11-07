"""Report, web, and image caching for the public-web service.

Wraps cachelib's FileSystemCache and the Taranis API client to fetch, cache,
and invalidate vulnerability reports and web branding with a TTL.
"""

import threading
import time

from cachelib import FileSystemCache
from flask import Response
from lib import config
from lib.logger import get_logger
from lib.report.vulnerability_report import VulnerabilityReport
from lib.web.taranis_client import TaranisClient, TaranisClientError

logger = get_logger("web-cache", silent=True)

CACHE_KEY_ALL_REPORTS = "ALL_REPORTS"
CACHE_KEY_RESET_AT = "RESET_AT"
CACHE_KEY_RSS_RESPONSE = "RSS_RESPONSE"
CACHE_KEY_WEBS = "WEBS"

# Products are loaded this many at a time (core serves at most 200).
PAGE_SIZE = 100
# How many products a core from before paging lists at most.
LEGACY_LIMIT = 200

# Loading every product takes seconds, so each web and language is loaded once at a time in this
# process: a visitor arriving meanwhile waits for that load instead of starting another. These are
# shared by every WebCache, as the site and the management API each have their own.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
# The webs and languages visitors asked for, which a cache reset loads again right away.
_asked: set[tuple[int | None, str | None]] = set()
# The reports this process last read, by cache key: reading all of them from disk again on every
# page takes longer than the page. A small stamp beside them on disk says when they are out of date.
_remembered: dict[str, dict] = {}


def _lock(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


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

    def _fetch_all_products(self, web_id: int | None, language: str | None) -> list[dict]:
        """Fetch every published product from Taranis (up to PUBLIC_WEB_MAX_REPORTS), newest first, in ``language``."""
        most = config.max_reports_api()
        products: list[dict] = []
        while most is None or len(products) < most:
            limit = PAGE_SIZE if most is None else min(PAGE_SIZE, most - len(products))
            items, total = self.client.list_published_products(len(products), limit, web_id=web_id, language=language)
            if items and "report_items" not in items[0]:
                return self._fetch_products_one_by_one(web_id, language, most)
            products.extend(items)
            if not items or len(products) >= total:
                break
        return products

    def _fetch_products_one_by_one(self, web_id: int | None, language: str | None, most: int | None) -> list[dict]:
        """Fetch the latest published products from a core that does not page them, one request each."""
        limit = LEGACY_LIMIT if most is None else min(most, LEGACY_LIMIT)
        products = []
        for product_id in self.client.list_published_product_ids(limit, web_id=web_id):
            data = self.client.get_product(product_id, web_id=web_id, language=language)
            if data is not None:
                products.append(data)
        return products

    def _fetch_all_reports(self, web_id: int | None = None, language: str | None = None) -> list[VulnerabilityReport]:
        """Fetch every published product from Taranis, newest first, in ``language``.

        Products that are not a valid TLP:CLEAR vulnerability report are skipped
        so one bad product cannot break the feed.
        """
        reports: list[VulnerabilityReport] = []
        for data in self._fetch_all_products(web_id, language):
            try:
                reports.append(VulnerabilityReport.from_dict(data))
            except (ValueError, TypeError) as exc:
                logger.info("Skipping product %s: %s", data.get("id"), exc)
        return reports

    def _load_reports(self, web_id: int | None, language: str | None, *, again: bool) -> list[VulnerabilityReport] | None:
        """Load the reports of a web in a language from Taranis and cache them; None when Taranis fails.

        One load at a time: a caller that waited for another's load takes its reports, unless it
        asks to load ``again`` (the reports it has are out of date).
        """
        cache_key = f"{CACHE_KEY_ALL_REPORTS}:{web_id}:{language}"
        with _lock(cache_key):
            entry = self._cached_reports(cache_key)
            if entry is not None and not again:
                return entry["reports"]
            started = time.time()
            try:
                reports = self._fetch_all_reports(web_id=web_id, language=language)
            except TaranisClientError as exc:
                logger.exception("Could not fetch reports from Taranis: %s", exc)
                return None
            # Only cache non-empty results: an empty feed usually means nothing is
            # published yet, and caching [] would hide a report published moments
            # later. Nor reports loaded before a reset: they may show one unpublished since.
            if reports and started >= (self.cache.get(CACHE_KEY_RESET_AT) or 0):
                entry = {"fetched_at": started, "reports": reports}
                self.cache.set(cache_key, entry, timeout=0)
                self.cache.set(f"{cache_key}:at", started, timeout=0)
                _remembered[cache_key] = entry
            return reports

    def _cached_reports(self, cache_key: str) -> dict | None:
        """The cached reports with when they were loaded, from memory unless another process loaded them since."""
        fetched_at = self.cache.get(f"{cache_key}:at")
        if fetched_at is None:
            return None
        remembered = _remembered.get(cache_key)
        if remembered is not None and remembered["fetched_at"] == fetched_at:
            return remembered
        entry = self.cache.get(cache_key)
        if not isinstance(entry, dict):
            return None
        _remembered[cache_key] = entry
        return entry

    def _load_reports_in_background(self, web_id: int | None, language: str | None) -> None:
        """Load the reports again without making anyone wait; nothing when they are loading already."""
        if _lock(f"{CACHE_KEY_ALL_REPORTS}:{web_id}:{language}").locked():
            return
        threading.Thread(target=self._load_reports, args=(web_id, language), kwargs={"again": True}, daemon=True).start()

    def get_all_reports(self, web_id: int | None = None, language: str | None = None) -> list[VulnerabilityReport]:
        """Return every published report (newest first) in ``language``, fetched from Taranis and cached.

        Cached per web and language. Older than the TTL, they are still returned while they load
        again in the background, as loading them all takes seconds. Only with none cached (at
        start, or after a reset) does the caller wait for them. On an API failure, logs and
        returns an empty list without caching so the next request retries.
        """
        _asked.add((web_id, language))
        entry = self._cached_reports(f"{CACHE_KEY_ALL_REPORTS}:{web_id}:{language}")
        if entry is not None:
            if time.time() - entry["fetched_at"] >= config.cache_ttl():
                self._load_reports_in_background(web_id, language)
            return entry["reports"]
        return self._load_reports(web_id, language, again=False) or []

    def get_report(self, report_id: str, web_id: int | None = None, language: str | None = None) -> VulnerabilityReport | None:
        """Return a single report by its Taranis product id, in ``language``.

        Looks in the cached list first, then fetches the product directly on a
        miss. Returns None if it is not a valid displayable report.
        """
        for report in self.get_all_reports(web_id=web_id, language=language):
            if str(report.get_id()) == str(report_id):
                return report
        try:
            product_id = int(report_id)
        except (TypeError, ValueError):
            return None
        try:
            data = self.client.get_product(product_id, web_id=web_id, language=language)
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
        change. FileSystemCache is on disk, so this clears the shared cache. The reports
        visitors asked for start loading again right away.
        """
        self.cache.clear()
        self.cache.set(CACHE_KEY_RESET_AT, time.time(), timeout=0)
        for web_id, language in list(_asked):
            self._load_reports_in_background(web_id, language)

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
