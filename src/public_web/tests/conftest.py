"""Shared fixtures: the fixture products and a Flask client wired to a fake core.

The tests run from src/public_web (``pythonpath = ["."]`` in pyproject.toml), so
``lib`` imports as the service's own package. Tests that only need the template
renderer import nothing beyond jinja2/markupsafe/cvss; ``site_client`` drives the
whole Flask app and so needs the service's own dependencies (bleach, feedgen,
cachelib), which ``scripts/dev_setup.py`` installs into the root .venv - it skips
without them.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# Before anything imports `lib`: the logger and the API client read these at import.
os.environ.setdefault("PUBLIC_WEB_API_KEY", "test-api-key")
os.environ.setdefault("PUBLIC_WEB_PRODUCTION", "false")
os.environ.setdefault("PUBLIC_WEB_LOG_DIR", str(Path(tempfile.gettempdir()) / "public-web-test-logs"))

FIXTURES = Path(__file__).parent / "fixtures" / "products.json"
CUSTOM_TEMPLATES = Path(__file__).parent / "fixtures" / "templates"

# The fixture products are those of an instance whose "Vulnerability Report" type was changed from
# the one Taranis creates: it has other attributes (affected systems with their versions, ...).
# The built-in templates fit only the types as Taranis creates them, so this instance gives that
# type a template of its own - the one its pages were made with before templates could be changed.
VULNERABILITY_TYPE_ID = 2


def custom_templates() -> list[dict]:
    """The fixture instance's own templates for its changed report item types, as core serves them."""
    return [
        {
            "id": 102,
            "name": "Vulnerability",
            "product_preset_id": None,
            "report_item_type_id": VULNERABILITY_TYPE_ID,
            "source": (CUSTOM_TEMPLATES / "custom_item_vulnerability.html").read_text(encoding="utf-8"),
            "require_tlp_clear": True,
            "public_web_ids": [],
        },
    ]


def load_fixtures() -> dict:
    """The fixture webs and products, freshly parsed so a test may mutate them."""
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


class FakeTaranisClient:
    """Stands in for ``TaranisClient``, answering like core's public-web endpoints.

    Products are listed newest first. Which webs get a product is decided in core by
    its product preset; every fixture product is served to every web.
    """

    def __init__(self, data: dict) -> None:
        """Serve the given fixture webs and products."""
        self.webs = data["webs"]
        self.products = {product["id"]: product for product in data["products"]}
        self.templates: list[dict] = custom_templates()
        self.disabled_builtins: list[str] = []

    def _newest_first(self) -> list[dict]:
        return sorted(self.products.values(), key=lambda product: product["created"], reverse=True)

    def list_published_products(
        self,
        offset: int,
        limit: int,
        web_id: int | None = None,  # noqa: ARG002
        language: str | None = None,  # noqa: ARG002
    ) -> tuple[list[dict], int]:
        """A page of whole products, newest first, and how many there are; the fixtures have no translations."""
        products = self._newest_first()
        return copy.deepcopy(products[offset : offset + limit]), len(products)

    def list_published_product_ids(self, limit: int, web_id: int | None = None) -> list[int]:  # noqa: ARG002
        """Ids of the products, newest first."""
        return [product["id"] for product in self._newest_first()[:limit]]

    def get_product(self, product_id: int, web_id: int | None = None, language: str | None = None) -> dict | None:  # noqa: ARG002
        """One product, or None when it does not exist; the fixtures have no translations."""
        product = self.products.get(product_id)
        return copy.deepcopy(product) if product is not None else None

    def list_webs(self) -> list[dict]:
        """The node's webs."""
        return copy.deepcopy(self.webs)

    def get_web_image(self, web_id: int, kind: str) -> None:  # noqa: ARG002
        """No uploaded images: the shipped defaults are used."""
        return

    def get_report_templates(self) -> dict[str, list]:
        """The report templates stored in core, and the built-ins switched off."""
        return {"items": copy.deepcopy(self.templates), "disabled_builtins": list(self.disabled_builtins)}


@pytest.fixture
def fixtures() -> dict:
    """The fixture webs and products."""
    return load_fixtures()


@pytest.fixture
def site_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A Flask test client for the whole site, backed by ``FakeTaranisClient``."""
    for module in ("bleach", "feedgen", "cachelib"):
        pytest.importorskip(module)
    from cachelib import FileSystemCache  # noqa: PLC0415 (optional dependency)
    from lib.web import routes  # noqa: PLC0415 (needs the env vars above)
    from run import app  # noqa: PLC0415

    fake = FakeTaranisClient(load_fixtures())
    monkeypatch.setattr(routes.cache, "client", fake)
    monkeypatch.setattr(routes.cache, "cache", FileSystemCache(cache_dir=str(tmp_path / "cache")))
    app.config["TESTING"] = True
    return SimpleNamespace(client=app.test_client(), fake=fake, cache=routes.cache)
