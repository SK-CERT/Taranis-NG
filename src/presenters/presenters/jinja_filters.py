"""Custom Jinja2 filters for presenters.

The format-neutral filters (dates, regex, TLP colours) live in ``shared.jinja_filters``,
because public-web's report templates use them too; they are re-exported here under
their old names. What stays here is specific to presenter output, such as mail headers.
"""

from collections.abc import Iterable

from shared.jinja_filters import filter_regex_replace, filter_strfdate, filter_tlp_color, filter_truncate_on_symbol
from shared.mail_headers import scrub_header_text

__all__ = [
    "filter_collect_attrs",
    "filter_header_value",
    "filter_regex_replace",
    "filter_strfdate",
    "filter_tlp_color",
    "filter_truncate_on_symbol",
]


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
