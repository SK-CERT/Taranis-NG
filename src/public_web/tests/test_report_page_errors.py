"""A report shows without its optional fields, and an unexpected error is logged as well as mailed.

The report page asked for the exposure date as if it were mandatory, so a report without one
failed to render: a 500 whose only trace was an e-mail to the admins, lost whenever no mail
server was reachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask
from lib.report.product import build_product
from lib.report.renderer import ReportRenderer
from lib.web import exceptions

if TYPE_CHECKING:
    import pytest


def _detail(*extra_attributes: dict) -> str:
    """The report page body of a one-vulnerability product, with phrase keys for its phrases."""
    item = {
        "title": "Kernel flaw",
        "type": "Vulnerability Report",
        "attributes": [
            {"key": "description", "attribute_type": "TEXT", "value": "An attacker can run code.", "description": None},
            {"key": "tlp", "attribute_type": "TLP", "value": "CLEAR", "description": None},
            {"key": "affected_systems", "attribute_type": "STRING", "value": "Linux: kernel; <6.1", "description": None},
            *extra_attributes,
        ],
    }
    product = build_product(
        {
            "id": 7,
            "title": "Bulletin",
            "links": [],
            "created": "2026-10-01T10:00:00",
            "user": {"name": "Analyst", "username": "analyst"},
            "report_items": [item],
        },
    )
    return str(ReportRenderer([]).render(product, "detail"))


def test_a_report_item_without_an_exposure_date_shows_without_one() -> None:
    detail = _detail()

    assert "An attacker can run code." in detail
    assert "vulnerability_exposed" not in detail


def test_a_report_item_shows_its_exposure_date() -> None:
    exposure = {"key": "exposure_date", "attribute_type": "DATE", "value": "2026.10.01", "description": None}

    assert "vulnerability_exposed 1. 10. 2026." in " ".join(_detail(exposure).split())


def test_an_unexpected_error_is_logged_as_well_as_mailed(monkeypatch: pytest.MonkeyPatch) -> None:
    logged: list[tuple] = []
    mailed: list[str] = []
    monkeypatch.setattr(exceptions.logger, "error", lambda *args, **kwargs: logged.append((args, kwargs)))
    monkeypatch.setattr(exceptions, "send_mail", lambda body, *_args, **_kwargs: mailed.append(body))
    monkeypatch.setattr(exceptions, "render_template", lambda *_args, **_kwargs: "error page")
    app = Flask(__name__)
    exceptions.register_error_handlers(app)

    @app.get("/reports/7")
    def report() -> str:
        msg = "boom"
        raise RuntimeError(msg)

    assert app.test_client().get("/reports/7").status_code == 500
    ((args, kwargs),) = logged
    assert args[1:] == (500, "/reports/7?")
    assert isinstance(kwargs["exc_info"], RuntimeError)
    assert "RuntimeError: boom" in mailed[0]
