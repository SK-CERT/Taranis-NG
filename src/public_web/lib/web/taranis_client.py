"""Client for fetching vulnerability report data from the Taranis-NG API.

public-web is a Taranis-NG *node*: it authenticates to core with the shared node
ApiKey (``Authorization: ApiKey ...``), exactly like the collector/presenter/
publisher/bot nodes, and reads published report products from the dedicated
public-web node endpoints:

  * ``GET /api/v1/public-web/products``          -> list published products
  * ``GET /api/v1/public-web/products/<id>``     -> product with report items

Core serializes the product directly from its database (no presenter involved):
product info plus report items, each with a flat list of attributes
({"key", "value", "description"}). ``VulnerabilityReport`` consumes this
structure. Products that are not published are returned as 404 by core and
skipped by the caller, so one bad product cannot break the feed.
"""

import requests
from lib import config
from lib.logger import get_logger

logger = get_logger("taranis-client", silent=True)

# Network timeout (seconds) for all Taranis API calls.
_TIMEOUT = 30
# HTTP status codes returned by the Taranis API that we branch on.
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404


class TaranisClientError(Exception):
    """Raised when the Taranis API cannot be reached or returns an error."""


class TaranisClient:
    """Node ApiKey client for the Taranis-NG public-web endpoints."""

    def __init__(self, core_url: str | None = None, api_key: str | None = None) -> None:
        """Initialize the client with the core URL and shared node ApiKey."""
        self._core_url = (core_url or config.taranis_core_url()).rstrip("/")
        self._api_key = api_key or config.taranis_api_key()
        self._session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"ApiKey {self._api_key}"}

    def _get(self, path: str, **kwargs: str) -> requests.Response:
        url = f"{self._core_url}{path}"
        try:
            return self._session.get(url, headers=self._headers(), timeout=_TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            msg = f"Taranis request to {path} failed: {exc}"
            raise TaranisClientError(msg) from exc

    def list_published_product_ids(self, limit: int, web_id: int | None = None) -> list[int]:
        """Return ids of published products, newest first (up to ``limit``)."""
        params = {"limit": max(1, min(limit, 200))}
        if web_id is not None:
            params["web_id"] = web_id

        resp = self._get(
            "/api/v1/public-web/products",
            params=params,
        )
        if resp.status_code == HTTP_UNAUTHORIZED:
            msg = "Taranis rejected the public-web ApiKey (401). Is the node registered in core with this key?"
            raise TaranisClientError(msg)
        if resp.status_code != HTTP_OK:
            msg = f"Listing products failed (HTTP {resp.status_code}): {resp.text[:200]}"
            raise TaranisClientError(msg)
        items = resp.json().get("items", [])
        return [item["id"] for item in items if "id" in item]

    def get_product(self, product_id: int, web_id: int | None = None) -> dict[str, object] | None:
        """Return one published product (with report items and attributes).

        Returns ``None`` (and logs) if the product does not exist or is not
        published (HTTP 404).
        """
        params = {"web_id": web_id} if web_id is not None else None
        resp = self._get(f"/api/v1/public-web/products/{product_id}", params=params)
        if resp.status_code == HTTP_NOT_FOUND:
            logger.info("Skipping product %s: not found or not published.", product_id)
            return None
        if resp.status_code != HTTP_OK:
            logger.warning(
                "Fetching product %s failed (HTTP %s): %s",
                product_id,
                resp.status_code,
                resp.text[:200],
            )
            return None
        try:
            return resp.json()
        except ValueError:
            logger.warning("Product %s response was not valid JSON.", product_id)
            return None

    def list_webs(self) -> list[dict[str, object]]:
        """Return the webs (branded feeds + config) this node hosts."""
        resp = self._get("/api/v1/public-web/webs")
        if resp.status_code == HTTP_UNAUTHORIZED:
            msg = "Taranis rejected the public-web ApiKey (401). Is the node registered in core with this key?"
            raise TaranisClientError(msg)
        if resp.status_code != HTTP_OK:
            msg = f"Listing webs failed (HTTP {resp.status_code}): {resp.text[:200]}"
            raise TaranisClientError(msg)
        return resp.json().get("items", [])

    def get_web_image(self, web_id: int, kind: str) -> tuple[bytes, str] | None:
        """Return ``(bytes, mime_type)`` of a web's image, or None if absent."""
        resp = self._get(f"/api/v1/public-web/webs/{web_id}/images/{kind}")
        if resp.status_code != HTTP_OK:
            return None
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
