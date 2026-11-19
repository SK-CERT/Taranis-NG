"""Jinja2 filters shared by every service that renders report templates.

The presenters and public-web both render administrator-written Jinja templates over
report data, so the filters that are not specific to one output format live here
and read the same on both sides.

Kept free of ``shared.common`` on purpose: that module imports BeautifulSoup, which
public-web does not install.
"""

import datetime as dt
import os
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

# The same zone as shared.common.TZ (see the module docstring for why it is not imported).
TZ = ZoneInfo(os.getenv("TZ", "UTC"))

# The schemes a link written by a report author may carry into an ``href``.
SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto"})


def filter_strfdate(date: str, fmtin: str | None = None, fmtout: str | None = None) -> str:
    """Convert a date string to a different format.

    Args:
        date (str): The date string to convert.
        fmtin (str): The input format of the date string (default: "%Y.%m.%d").
        fmtout (str): The output format of the date string (default: "%-d.%-m.%Y").

    Returns:
        str: The converted date string.

    """
    if not date:
        return ""

    formats = [fmtin] if fmtin else ["%Y-%m-%d", "%Y.%m.%d"]
    for fmt in formats:
        try:
            native = dt.datetime.strptime(date, fmt).replace(tzinfo=TZ)
            break
        except ValueError:
            continue
    else:
        msg = f"Unsupported date format: {date!r}. Expected one of: {', '.join(formats)}"
        raise ValueError(msg)

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
        return text.split(symbol, maxsplit=1)[0]
    return text


def filter_tlp_color(tlp: str) -> str:
    """Return color code for TLP value."""
    mapping = {"CLEAR": "white", "WHITE": "white", "GREEN": "#33ff00", "AMBER": "#ffc000", "AMBER+STRICT": "#ffc000", "RED": "#ff2b2b"}
    return mapping.get(tlp, "white")


def filter_safe_url(value: object) -> str:
    """Return the URL when it is safe to put in an ``href``, an empty string otherwise.

    Escaping keeps a value inside its attribute, but it does not stop the browser from
    running a ``javascript:`` (or ``data:``) URL when the link is clicked. Report links are
    typed in by analysts, so a template that links to them filters the scheme first.

    Args:
        value: The link as stored in the report.

    Returns:
        str: The URL if it is http(s), mailto or has no scheme; ``""`` for anything else.
    """
    if value is None:
        return ""
    # Browsers drop tabs and newlines inside a scheme ("java\tscript:") and ignore leading
    # control characters and spaces, so they are removed before the scheme is read.
    url = re.sub(r"[\t\r\n]", "", str(value)).lstrip("".join(map(chr, range(33))))
    try:
        scheme = urlsplit(url).scheme.lower()
    except ValueError:
        return ""
    if scheme:
        return url if scheme in SAFE_URL_SCHEMES else ""
    # No scheme urlsplit recognises: anything with a colon before the first "/", "?" or "#"
    # could still be read as one by a browser, so only plainly relative links pass.
    return "" if ":" in re.split(r"[/?#]", url, maxsplit=1)[0] else url
