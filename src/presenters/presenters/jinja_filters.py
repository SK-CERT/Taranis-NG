"""Custom Jinja2 filters for presenters."""

import datetime
import re
from collections.abc import Iterable

from shared.common import TZ
from shared.mail_headers import scrub_header_text


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
            native = datetime.datetime.strptime(date, fmt).replace(tzinfo=TZ)
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


def _attr_values(value: object) -> list[str]:
    """Flatten one report item's value for a single attribute into a list of strings.

    ``BasePresenter.ReportItemObject`` stores an attribute in one of several shapes
    depending on how the report item type declares it, so unpack them all:

    * ``str`` -- the attribute group item has ``max_occurrence == 1``
    * ``list[str]`` -- any other ``max_occurrence``
    * ``dict`` -- the ``cwe*`` shape, ``{value: value_description}``; the keys are the values
    * ``list[list]`` -- two attribute group items in different groups share a title

    Args:
        value (object): The raw ``attrs`` entry.

    Returns:
        list[str]: The values it holds, unscrubbed.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(key) for key in value]
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_attr_values(item))
        return values
    return [str(value)]


def filter_collect_attrs(report_items: Iterable, key: str, *, unique: bool = True) -> list[str]:
    """Collect one attribute's values from every report item of a product.

    This is what lets a headers template list the values of every report item combined into
    a product: ``{{ data.report_items | collect_attrs('report_category') | join(', ') }}``.
    Every value is scrubbed of characters that would break out of a header line, so the
    result is safe to interpolate directly.

    Report items reach a filter as plain dicts, not objects -- ``generate_input_data`` runs
    them through ``BasePresenter.to_template_data`` first -- so this reads them with
    ``.get()``. An ``getattr``-based implementation would silently return an empty list.

    Takes an iterable rather than a list so it composes with ``selectattr``, e.g.
    ``data.report_items | selectattr('type', 'equalto', 'Vulnerability Report') | collect_attrs('cve')``.

    Note that ``collect_attrs('cvss')`` is not useful: by this point ``attrs.cvss`` is the
    parsed CVSS dict, so you would get its keys. Use ``data.product.max_cvss`` instead.

    Args:
        report_items (Iterable): ``data.report_items``, or a filtered subset of it.
        key (str): The ``attrs`` key, i.e. the attribute group item title lowercased with
            spaces replaced by underscores.
        unique (bool): Drop repeats, keeping first-seen order. Defaults to True -- three
            report items all tagged "Ransomware" should list it once.

    Returns:
        list[str]: The collected values.
    """
    collected = []
    for report_item in report_items:
        attrs = report_item.get("attrs") if isinstance(report_item, dict) else None
        if not attrs:
            continue
        for value in _attr_values(attrs.get(key)):
            scrubbed = scrub_header_text(value)
            if scrubbed:
                collected.append(scrubbed)

    return list(dict.fromkeys(collected)) if unique else collected


def filter_header_value(value: object) -> str:
    """Make a single value safe to interpolate into a mail header.

    Mandatory whenever a headers template interpolates a value it did not get from
    ``collect_attrs``, e.g. ``X-Report-Type: {{ report_item.attrs.report_type | header_value }}``.
    Returns an empty string for None, which also keeps ``data.product.max_cvss`` from
    rendering as the literal "None" when no report item carries a CVSS score.

    Args:
        value (object): The raw value.

    Returns:
        str: The scrubbed value, possibly empty.
    """
    return scrub_header_text(value)
