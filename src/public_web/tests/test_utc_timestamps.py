"""Public-web formats timestamp dates in UTC, preserving calendar-only inputs."""

import importlib.util
from pathlib import Path

import pytest

# Import the pure utility without initializing lib (which reads deployment config).
_spec = importlib.util.spec_from_file_location("report_dates", Path(__file__).parents[1] / "lib" / "report" / "__init__.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
format_iso_date = _module.format_iso_date


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-01", "1. 7. 2026"),
        ("2026-07-02T00:30:00+02:00", "1. 7. 2026"),
        ("2026-07-01T22:30:00Z", "1. 7. 2026"),
    ],
)
def test_format_iso_date_uses_utc_for_instants(value: str, expected: str) -> None:
    assert format_iso_date(value) == expected
