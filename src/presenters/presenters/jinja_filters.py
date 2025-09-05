"""Custom Jinja2 filters for presenters."""

import datetime
import re

from shared.common import TZ


def filter_strfdate(date: str, fmtin: str | None = None, fmtout: str | None = None) -> str:
    """Convert a date string to a different format.

    Args:
        date (str): The date string to convert.
        fmtin (str): The input format of the date string (default: "%Y.%m.%d").
        fmtout (str): The output format of the date string (default: "%-d.%-m.%Y").

    Returns:
        str: The converted date string.

    """
    if date == "":
        return ""
    if not fmtin:
        fmtin = "%Y.%m.%d"
    date = datetime.datetime.strptime(date, fmtin).replace(tzinfo=TZ)
    native = date
    if not fmtout:
        fmtout = "%-d.%-m.%Y"
    return native.strftime(fmtout)


def filter_regex_replace(text: str, pattern: str, replacement: str) -> str:
    """Replace all occurrences of a pattern in a string with a replacement string.

    Args:
        pattern (str): The regex pattern to search for.
        replacement (str): The string to replace the pattern with.
        text (str): The input string.

    Returns:
        str: The modified string with the pattern replaced.

    """
    return re.sub(pattern, replacement, text)


def filter_truncate_on_symbol(text: str, symbol: str) -> str:
    """Truncate a string at the first occurrence of a specified symbol.

    Args:
        text (str): The input string.
        symbol (str): The symbol to truncate at.

    Returns:
        str: The truncated string.

    """
    if symbol in text:
        return text.split(symbol)[0]
    return text


def filter_tlp_color(tlp: str) -> str:
    """Return color code for TLP value."""
    mapping = {"CLEAR": "white", "WHITE": "white", "GREEN": "#33ff00", "AMBER": "#ffc000", "AMBER+STRICT": "#ffc000", "RED": "#ff2b2b"}
    return mapping.get(tlp, "white")
