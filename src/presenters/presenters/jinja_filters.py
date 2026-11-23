"""Custom Jinja2 filters for presenters.

The format-neutral filters (dates, regex, TLP colours) live in ``shared.jinja_filters``,
because public-web's report templates use them too; they are re-exported here under
their old names. What stays here is specific to presenter output, such as mail headers.
"""

import math
import re
from collections.abc import Iterable

from markupsafe import Markup
from shared.jinja_filters import filter_regex_replace, filter_safe_url, filter_strfdate, filter_tlp_color, filter_truncate_on_symbol
from shared.mail_headers import scrub_header_text

__all__ = [
    "doughnut_svg",
    "filter_collect_attrs",
    "filter_header_value",
    "filter_regex_replace",
    "filter_safe_url",
    "filter_strfdate",
    "filter_tlp_color",
    "filter_truncate_on_symbol",
]

_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

# Chart geometry bounds, validated at the filter boundary.
MIN_CHART_SIZE = 100
MAX_CHART_SIZE = 2000
MIN_INNER_RATIO = 0.1
MAX_INNER_RATIO = 0.9
HALF_CIRCLE_DEGREES = 180.0


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


def doughnut_svg(
    values: Iterable,
    colors: Iterable[str] | None = None,
    size: int = 300,
    inner_ratio: float = 0.52,
) -> Markup:
    """Generate a static SVG doughnut chart.

    Args:
        values:
            Numeric values representing chart segments.

        colors:
            Optional list of hexadecimal colors.
            Colors are reused cyclically when necessary.

        size:
            SVG viewBox dimensions in pixels.

        inner_ratio:
            Inner radius relative to outer radius (0.1 - 0.9).

    Returns:
        Trusted, generated SVG markup.
        Empty markup when there is no positive data.

    Raises:
        ValueError: Invalid dimensions, values or colors.
    """
    # Validate dimensions.
    if isinstance(size, bool) or not isinstance(size, int) or not MIN_CHART_SIZE <= size <= MAX_CHART_SIZE:
        msg = f"Chart size must be an integer between {MIN_CHART_SIZE} and {MAX_CHART_SIZE}."
        raise ValueError(msg)

    if not math.isfinite(inner_ratio) or not MIN_INNER_RATIO <= inner_ratio <= MAX_INNER_RATIO:
        msg = f"inner_ratio must be between {MIN_INNER_RATIO} and {MAX_INNER_RATIO}."
        raise ValueError(msg)

    colors = list(colors)

    if not colors:
        msg = "At least one chart color is required."
        raise ValueError(msg)

    for color in colors:
        if not isinstance(color, str) or not _COLOR_PATTERN.fullmatch(color):
            msg = f"Invalid chart color: {color!r}"
            raise ValueError(msg)

    normalized = []
    for value in values:
        try:
            number = float(value or 0)
        except (ValueError, TypeError, OverflowError):
            msg = f"Invalid chart value: {value!r}"
            raise ValueError(msg) from None

        if not math.isfinite(number) or number < 0:
            msg = f"Invalid chart value: {value!r}"
            raise ValueError(msg)

        normalized.append(number)

    total = math.fsum(normalized)
    if total <= 0:
        return Markup("")

    # Geometry.
    cx = cy = size / 2
    outer = size * 0.46
    inner = outer * inner_ratio

    def point(radius: float, angle: float) -> tuple[float, float]:
        angle_rad = math.radians(angle)

        return (
            cx + radius * math.cos(angle_rad),
            cy + radius * math.sin(angle_rad),
        )

    paths = []

    # Ignore zero-valued segments.
    nonzero = [(index, value) for index, value in enumerate(normalized) if value > 0]

    # A single segment representing 100% needs a special case.
    if len(nonzero) == 1:
        index, _ = nonzero[0]
        paths.append(
            f'<circle cx="{cx}" cy="{cy}" r="{outer}" fill="{colors[index % len(colors)]}"/>',
        )
        paths.append(
            f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="#ffffff"/>',
        )
    else:
        angle = -90.0
        for index, value in nonzero:
            sweep = value / total * 360.0
            end_angle = angle + sweep
            x1, y1 = point(outer, angle)
            x2, y2 = point(outer, end_angle)
            x3, y3 = point(inner, end_angle)
            x4, y4 = point(inner, angle)
            large_arc = 1 if sweep > HALF_CIRCLE_DEGREES else 0
            path = (
                f"M {x1:.3f} {y1:.3f} "
                f"A {outer:.3f} {outer:.3f} "
                f"0 {large_arc} 1 {x2:.3f} {y2:.3f} "
                f"L {x3:.3f} {y3:.3f} "
                f"A {inner:.3f} {inner:.3f} "
                f"0 {large_arc} 0 {x4:.3f} {y4:.3f} Z"
            )
            color = colors[index % len(colors)]
            paths.append(
                f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>',
            )
            angle = end_angle

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {size} {size}" '
        f'width="100%" '
        f'height="auto" '
        f'role="img" '
        f'aria-label="Doughnut chart">'
        f"{''.join(paths)}"
        f"</svg>"
    )

    # Safe because the SVG structure is generated here. All dynamic attributes have been validated.
    return Markup(svg)  # noqa: S704 - generated markup, all dynamic values validated above
