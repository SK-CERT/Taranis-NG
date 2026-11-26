"""A change to a report that a published product carries reaches the public webs.

Core decides from the reports - their TLP above all - which products a public web may have, but
the webs keep what they loaded for their cache lifetime (90 minutes). Only publishing, unpublishing
or editing a product pushed a cache reset, so a report edited inside a published product (a raised
TLP included) stayed on the webs as it was. Reports are saved a field at a time, so these resets
are gathered and sent once.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from api import analyze
from flask import Flask
from managers import public_web_manager
from sqlalchemy import select

APP = Flask(__name__)
NODE = SimpleNamespace(name="web", api_url="http://web", api_key="k", enabled=True, is_reachable=lambda: True)


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Resets sent and timers started; a timer runs only when the test calls it."""
    recorded = SimpleNamespace(sent=[], timers=[])
    monkeypatch.setattr(public_web_manager, "public_web_enabled", lambda: True)
    monkeypatch.setattr(public_web_manager, "_push_reset_cache", lambda targets: recorded.sent.append(sorted(targets)))
    monkeypatch.setattr(public_web_manager, "_pending_targets", None)

    class Timer:
        def __init__(self, delay: float, function: object) -> None:
            self.delay = delay
            self.function = function
            self.daemon = False

        def start(self) -> None:
            recorded.timers.append(self)

    monkeypatch.setattr(public_web_manager.threading, "Timer", Timer)
    return recorded


def test_changes_within_the_window_send_one_reset(pushes: SimpleNamespace) -> None:
    for _ in range(3):
        public_web_manager.notify_nodes_soon([NODE])

    assert len(pushes.timers) == 1
    timer = pushes.timers[0]
    assert (timer.delay, timer.daemon) == (public_web_manager.REPORT_RESET_DELAY_SECONDS, True)
    timer.function()
    assert pushes.sent == [[("web", "http://web", "k")]]

    # a change after the reset went out starts a new batch
    public_web_manager.notify_nodes_soon([NODE])
    assert len(pushes.timers) == 2


def test_unreachable_or_disabled_nodes_are_not_gathered(pushes: SimpleNamespace) -> None:
    public_web_manager.notify_nodes_soon(
        [SimpleNamespace(name="off", api_url="http://off", api_key="k", enabled=False, is_reachable=lambda: True)],
    )
    public_web_manager.notify_nodes_soon(
        [SimpleNamespace(name="down", api_url="http://down", api_key="k", enabled=True, is_reachable=lambda: False)],
    )

    assert pushes.timers == []


@pytest.mark.parametrize(("published", "expected"), [(True, 1), (False, 0)])
def test_only_a_report_of_a_published_product_resets_the_webs(
    monkeypatch: pytest.MonkeyPatch,
    pushes: SimpleNamespace,  # noqa: ARG001
    *,
    published: bool,
    expected: int,
) -> None:
    asked: list = []
    monkeypatch.setattr(analyze.public_web_manager, "notify_nodes_soon", asked.append)
    monkeypatch.setattr(public_web_manager.PublicWebNode, "get_all", classmethod(lambda _cls: [NODE]))
    from model.product import Product  # noqa: PLC0415

    monkeypatch.setattr(Product, "published_with_report_item", classmethod(lambda _cls, _id: published))

    public_web_manager.report_item_changed(5)

    assert len(asked) == expected


def test_any_report_update_asks(monkeypatch: pytest.MonkeyPatch) -> None:
    changed: list = []
    monkeypatch.setattr(analyze.ReportItem, "update_report_item", classmethod(lambda _cls, *_args: (True, {"title": ""})))
    monkeypatch.setattr(analyze.ReportItem, "find", classmethod(lambda _cls, _id: SimpleNamespace(report_item_type_id=1)))
    monkeypatch.setattr(analyze.asset_manager, "report_item_changed", lambda _item: None)
    monkeypatch.setattr(analyze.sse_manager, "report_item_updated", lambda _data: None)
    monkeypatch.setattr(analyze.sse_manager, "remote_access_report_items_updated", lambda _type_id: None)
    monkeypatch.setattr(analyze.auth_manager, "get_user_from_jwt", lambda: SimpleNamespace(id=1))
    monkeypatch.setattr(analyze.public_web_manager, "report_item_changed", changed.append)

    with APP.test_request_context("/", method="PUT", json={"update": True, "title": "New title"}):
        analyze.ReportItemResource.put.__wrapped__(analyze.ReportItemResource(), 5)

    assert changed == [5]


def test_the_lookup_asks_for_a_published_product_holding_the_report(monkeypatch: pytest.MonkeyPatch) -> None:
    from model import product as product_module  # noqa: PLC0415 - the module whose session is replaced
    from sqlalchemy.dialects import postgresql  # noqa: PLC0415

    asked: list = []

    class Query:
        def __init__(self, *columns: object) -> None:
            self.statement = select(*columns)

        def join(self, *args: object) -> Query:
            self.statement = self.statement.join(*args)
            return self

        def filter(self, *conditions: object) -> Query:
            self.statement = self.statement.where(*conditions)
            return self

        def first(self) -> None:
            asked.append(str(self.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})))

    monkeypatch.setattr(product_module, "db", SimpleNamespace(session=SimpleNamespace(query=Query)))
    monkeypatch.setattr(product_module.StateDefinition, "get_by_name", classmethod(lambda _cls, _name: SimpleNamespace(id=3)))

    assert product_module.Product.published_with_report_item(5) is False
    assert "JOIN product_report_item ON product_report_item.product_id = product.id" in asked[0]
    assert "product_report_item.report_item_id = 5 AND product.state_id = 3" in asked[0]


def test_a_failure_never_fails_the_change(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> bool:
        msg = "no database"
        raise RuntimeError(msg)

    monkeypatch.setattr(public_web_manager, "public_web_enabled", broken)

    public_web_manager.report_item_changed(5)  # does not raise
