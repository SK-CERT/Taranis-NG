"""The ``safe_url`` template filter: what may be put in an ``href``.

Autoescaping keeps a value inside its attribute; it does not stop a browser from running a
``javascript:`` URL when the link is clicked. Links of a report are typed in by analysts.
"""

from __future__ import annotations

import pytest
from shared.jinja_filters import filter_safe_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/advisory?id=1&lang=en#top",
        "http://example.org/",
        "HTTPS://EXAMPLE.ORG/",
        "mailto:csirt@example.org",
        "/relative/path",
        "advisories/2026/01.html",
        "#section",
        "?page=2",
    ],
)
def test_ordinary_links_pass_unchanged(url: str) -> None:
    assert filter_safe_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "  javascript:alert(1)",
        "\x01javascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "blob:https://example.org/1",
        "http://[broken",
    ],
)
def test_a_link_that_could_run_or_read_something_is_dropped(url: str) -> None:
    assert filter_safe_url(url) == ""


def test_surrounding_whitespace_is_trimmed_from_a_good_link() -> None:
    assert filter_safe_url("  https://example.org/") == "https://example.org/"


@pytest.mark.parametrize("value", [None, ""])
def test_nothing_gives_nothing(value: object) -> None:
    assert filter_safe_url(value) == ""
