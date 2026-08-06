"""Tests for dashboard tag-cloud query parsing."""

# Assertions are the native test contract in this module.
# ruff: noqa: S101

from datetime import date
from unittest import TestCase

from api.dashboard import TagCloudQueryError, parse_tag_cloud_interval


class ParseTagCloudIntervalTest(TestCase):
    """Verify supported interval modes and invalid combinations."""

    today = date(2026, 8, 6)

    def test_defaults_to_today(self) -> None:
        """An empty query retains the historical today-only behavior."""
        assert parse_tag_cloud_interval({}, self.today) == (self.today, self.today)

    def test_legacy_day_is_inclusive(self) -> None:
        """The legacy relative day selects its cutoff through today."""
        assert parse_tag_cloud_interval({"tag_cloud_day": ["2"]}, self.today) == (date(2026, 8, 4), self.today)

    def test_legacy_day_preserves_upper_cap(self) -> None:
        """Legacy values greater than seven continue to be capped."""
        assert parse_tag_cloud_interval({"tag_cloud_day": ["99"]}, self.today) == (date(2026, 7, 30), self.today)

    def test_named_ranges(self) -> None:
        """Named ranges follow established Core range vocabulary."""
        expected = {
            "TODAY": (self.today, self.today),
            "WEEK": (date(2026, 8, 3), self.today),
            "MONTH": (date(2026, 8, 1), self.today),
            "LAST_7_DAYS": (date(2026, 7, 30), self.today),
            "LAST_31_DAYS": (date(2026, 7, 6), self.today),
        }
        for value, interval in expected.items():
            with self.subTest(value=value):
                assert parse_tag_cloud_interval({"tag_cloud_range": [value]}, self.today) == interval

    def test_explicit_interval_is_inclusive(self) -> None:
        """A valid ISO date pair is returned unchanged without a span cap."""
        arguments = {
            "tag_cloud_date_from": ["2026-06-01"],
            "tag_cloud_date_to": ["2026-08-05"],
        }
        assert parse_tag_cloud_interval(arguments, self.today) == (date(2026, 6, 1), date(2026, 8, 5))

    def test_conflicting_modes_are_rejected(self) -> None:
        """Day, named range, and explicit interval modes cannot be mixed."""
        conflicting_queries = (
            {"tag_cloud_day": ["7"], "tag_cloud_range": ["TODAY"]},
            {"tag_cloud_day": ["7"], "tag_cloud_date_from": ["2026-08-04"], "tag_cloud_date_to": ["2026-08-05"]},
            {"tag_cloud_range": ["TODAY"], "tag_cloud_date_from": ["2026-08-04"], "tag_cloud_date_to": ["2026-08-05"]},
        )
        for arguments in conflicting_queries:
            with self.subTest(arguments=arguments):
                self._assert_invalid(arguments)

    def test_invalid_arguments_are_rejected(self) -> None:
        """Reject incomplete, malformed, reversed, and duplicate values."""
        invalid_queries = (
            {"tag_cloud_day": ["-1"]},
            {"tag_cloud_day": ["invalid"]},
            {"tag_cloud_range": ["DATE"]},
            {"tag_cloud_date_from": ["2026-08-04"]},
            {"tag_cloud_date_from": ["2026-08-05"], "tag_cloud_date_to": ["2026-08-04"]},
            {"tag_cloud_date_from": ["not-a-date"], "tag_cloud_date_to": ["2026-08-06"]},
            {"tag_cloud_range": ["TODAY", "WEEK"]},
        )
        for arguments in invalid_queries:
            with self.subTest(arguments=arguments):
                self._assert_invalid(arguments)

    def _assert_invalid(self, arguments: dict[str, list[str]]) -> None:
        """Assert that parsing fails without requiring a pytest dependency."""
        try:
            parse_tag_cloud_interval(arguments, self.today)
        except TagCloudQueryError:
            return
        msg = f"Expected TagCloudQueryError for {arguments!r}"
        raise AssertionError(msg)
