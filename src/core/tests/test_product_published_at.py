"""A product remembers when it was first published, and the public web gets its dates with an offset.

The public web shows that moment as the day the product was published, orders by it, and
gives it to feed readers (RSS ``pubDate``, Atom ``published``). Core stores local time without
an offset, so what it hands on says which zone it is in.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from api import public_web  # noqa: E402 - after every mapper is registered
from model.product import Product  # noqa: E402
from model.state import StateDefinition  # noqa: E402
from shared.common import TZ  # noqa: E402

PUBLISHED = 1
WORK_IN_PROGRESS = 2


@pytest.fixture(autouse=True)
def _states(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(StateDefinition, "get_by_name", classmethod(lambda _cls, name: SimpleNamespace(id=PUBLISHED, name=name)))


def _product(state_id: int | None, published_at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(state_id=state_id, published_at=published_at)


def test_the_first_publication_is_recorded_in_local_time() -> None:
    product = _product(PUBLISHED)

    Product.note_first_publication(product)

    assert product.published_at.tzinfo is None
    assert abs(product.published_at - datetime.now(TZ).replace(tzinfo=None)) < timedelta(minutes=1)


def test_publishing_again_keeps_the_first_date() -> None:
    first = datetime(2026, 9, 1, 8, 30)  # noqa: DTZ001 - core stores local time without an offset
    product = _product(PUBLISHED, first)

    Product.note_first_publication(product)

    assert product.published_at == first


@pytest.mark.parametrize("state_id", [WORK_IN_PROGRESS, None])
def test_a_product_not_published_has_no_publication_time(state_id: int | None) -> None:
    product = _product(state_id)

    Product.note_first_publication(product)

    assert product.published_at is None


def test_saving_a_product_notes_its_publication() -> None:
    """Both paths that set a product's state look whether it was just published."""
    import inspect  # noqa: PLC0415

    assert "product.note_first_publication()" in inspect.getsource(Product.add_product)
    assert "original_product.note_first_publication()" in inspect.getsource(Product.update_product)


def _stored(**dates: datetime | None) -> SimpleNamespace:
    created = datetime(2026, 9, 1, 8, 0)  # noqa: DTZ001 - core stores local time without an offset
    return SimpleNamespace(**{"created": created, "published_at": None, "updated_at": None, **dates})


def test_the_public_web_gets_the_dates_with_their_offset() -> None:
    stored = {"published_at": datetime(2026, 9, 3, 14, 5), "updated_at": datetime(2026, 9, 4, 9, 0)}  # noqa: DTZ001 - as core stores them
    product = _stored(**stored)

    dates = public_web._dates(product)

    assert dates == {
        "published": datetime(2026, 9, 3, 14, 5, tzinfo=TZ).isoformat(),
        "updated": datetime(2026, 9, 4, 9, 0, tzinfo=TZ).isoformat(),
    }
    assert datetime.fromisoformat(dates["published"]).utcoffset() is not None


def test_a_product_published_before_the_time_was_recorded_gives_its_creation() -> None:
    dates = public_web._dates(_stored())

    assert dates == {"published": datetime(2026, 9, 1, 8, 0, tzinfo=TZ).isoformat(), "updated": dates["published"]}


def test_a_moment_with_an_offset_keeps_it() -> None:
    moment = datetime(2026, 9, 3, 14, 5, tzinfo=TZ)

    assert public_web._iso(moment) == moment.isoformat()
    assert public_web._iso(None) is None


def test_the_newest_publication_comes_first() -> None:
    import inspect  # noqa: PLC0415

    source = inspect.getsource(Product.get_published)
    assert "func.coalesce(cls.published_at, cls.created)" in source
    assert "order_by(db.desc(newest), db.desc(cls.id))" in source
