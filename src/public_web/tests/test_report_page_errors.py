"""A report shows without its optional fields, and an unexpected error is logged as well as mailed.

The report page asked for the exposure date as if it were mandatory, so a report without one
failed to render: a 500 whose only trace was an e-mail to the admins, lost whenever no mail
server was reachable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask
from lib.report.vulnerability_report import VulnerabilityReport
from lib.web import exceptions

if TYPE_CHECKING:
    import pytest


def _report(*extra_attributes: dict) -> VulnerabilityReport:
    item = {
        "title": "Kernel flaw",
        "type": "Vulnerability Report",
        "attributes": [
            {"key": "description", "type": "TEXT", "value": "An attacker can run code.", "description": None},
            {"key": "tlp", "type": "TLP", "value": "CLEAR", "description": None},
            {"key": "affected_systems", "type": "TEXT", "value": "Linux: kernel; <6.1", "description": None},
            *extra_attributes,
        ],
    }
    return VulnerabilityReport.from_dict(
        {
            "id": 7,
            "title": "Bulletin",
            "links": [],
            "created": "2026-10-01T10:00:00",
            "user": {"name": "Analyst", "username": "analyst"},
            "report_items": [item],
        },
    )


def test_a_report_item_without_an_exposure_date_has_none() -> None:
    assert _report().get_report_items()[0].get_exposure_date() is None


def test_a_report_item_shows_its_exposure_date() -> None:
    exposure = {"key": "exposure_date", "type": "DATE", "value": "2026.10.01", "description": None}

    assert _report(exposure).get_report_items()[0].get_exposure_date() == "1. 10. 2026"


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
