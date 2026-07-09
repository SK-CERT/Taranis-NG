"""Report processing utilities for public-web.

This module provides classes and functions for processing vulnerability reports.
"""

import re
from datetime import datetime


class MissingFieldError(TypeError):
    """Raised when a mandatory field is missing from a report."""

    def __init__(self, field: str, report_type: object) -> None:
        """Initialize a new MissingFieldError.

        Args:
            field: The missing field name.
            report_type: The type of report where the field is missing.
        """
        msg = f"Mandatory report field {field} is missing in {type(report_type)} JSON!"
        super().__init__(msg)


def format_iso_date(date: str | None) -> str:
    """Format an ISO 8601 date or datetime string.

    Input is an ISO 8601 date or datetime string (as served by the Taranis-NG
    core API). Returns the date formatted into 'D. M. YYYY' format (without
    leading zeroes).
    """
    if not date:
        msg = f"Wrong date input: {date}. It must be an ISO date string."
        raise ValueError(msg)
    try:
        parsed = datetime.fromisoformat(date)
    except ValueError as exc:
        msg = f"Wrong date input: {date}. It must be an ISO date string."
        raise ValueError(msg) from exc
    return f"{parsed.day}. {parsed.month}. {parsed.year}"


def reformat_date(date: str) -> str:
    """Reformat date from 'YYYY.MM.DD' to 'DD. MM. YYYY'.

    Input date is in 'YYYY.MM.DD' format. Returns the date formatted into
    'DD. MM. YYYY' format (but without leading zeroes).
    """
    if date is None or len(date.split(".")) != 3:  # noqa: PLR2004
        msg = f"Wrong date format: {date}. It must be in YYYY.MM.DD."
        raise ValueError(msg)
    year, month, day = date.strip().split(".")
    return f"{int(day)}. {int(month)}. {year}"


def capitalize(string: str) -> str:
    """Capitalize only the first letter of a string.

    This is needed because string.capitalize() in Python makes all other letters
    lowercase, which is not an expected behavior.
    """
    if len(string) == 0:
        return string
    return string[0].upper() + string[1:]


def fix_spaces(string: str) -> str:
    """Remove double spaces from a Taranis report string.

    A report from Taranis can contain double spaces, which is always not wanted.
    So this function also removes them.
    """
    return re.sub(" +", " ", string).strip()


def get_cvss_severity(score: float | None) -> str | None:
    """Returns the severity of the CVSS score.

    Based on: https://www.first.org/cvss/specification-document,
    or None if the CVSS score is missing.
    """
    if score is None:
        return None
    if score >= 9.0:  # noqa: PLR2004
        return "Critical"
    if score >= 7.0:  # noqa: PLR2004
        return "High"
    if score >= 4.0:  # noqa: PLR2004
        return "Medium"
    if score > 0:
        return "Low"
    return "None"
