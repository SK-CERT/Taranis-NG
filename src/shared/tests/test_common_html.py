"""Tests for the HTML helpers every collector runs its content through.

``simplify_html_text`` is the last thing standing between a collected page or email and
the database, and the news item detail view renders its output with ``v-html``. So the
two properties asserted here are: text is never lost to markup the application does not
render itself, and nothing outside the allowlist survives.
"""

from shared.common import remove_empty_html_tags, resolve_relative_links, simplify_html_text, strip_html, text_to_simple_html


def test_allowed_tags_are_kept_with_their_href() -> None:
    html = '<p>See <a href="https://example.com/" class="link">this</a>.</p>'

    assert simplify_html_text(html) == '<p>See <a href="https://example.com/">this</a>.</p>'


def test_unsupported_tag_is_unwrapped_and_keeps_its_text() -> None:
    # <article> is not rendered, but everything a sender wrote inside it still is.
    assert "the text" in simplify_html_text("<article>the text</article>")


def test_full_html_document_keeps_its_body() -> None:
    html = "<html><head><title>Subject</title></head><body><p>Body text</p></body></html>"

    result = simplify_html_text(html)

    assert "<p>Body text</p>" in result
    assert "Subject" not in result  # the <head> goes, with everything in it


def test_table_layout_keeps_its_cells_and_row_breaks() -> None:
    html = "<table><tr><td>First</td><td>Second</td></tr><tr><td>Third</td></tr></table>"

    result = simplify_html_text(html)

    # Cells stay on their row's line, rows are separated by the <div> a row becomes.
    assert "First Second" in strip_html(result)
    assert result.count("<div>") >= 2
    assert "<td>" not in result


def test_script_and_style_are_dropped_with_their_content() -> None:
    html = "<div><style>p { color: red }</style><script>alert(1)</script><p>Body</p></div>"

    result = simplify_html_text(html)

    assert "alert" not in result
    assert "color: red" not in result
    assert "<p>Body</p>" in result


def test_comments_are_dropped() -> None:
    # Outlook conditional comments are pure bulk in an HTML email.
    assert "mso" not in simplify_html_text("<!--[if mso]><p>hidden</p><![endif]--><p>Body</p>")


def test_event_handler_attributes_do_not_survive() -> None:
    result = simplify_html_text('<p onclick="steal()">Body</p><img src="x" onerror="steal()">')

    assert "onclick" not in result
    assert "onerror" not in result


def test_preformatted_text_is_escaped_not_parsed() -> None:
    # A plain text email quoting a bracketed URL keeps it; unescaped it would be read as
    # a tag and disappear.
    result = text_to_simple_html("Advisory at <https://example.com/a>\n  indented", preformatted_text=True)

    assert result == "<pre>Advisory at &lt;https://example.com/a&gt;\n  indented</pre>"
    assert simplify_html_text(result) == result


def test_preformatted_text_survives_the_full_sanitization_chain() -> None:
    content = text_to_simple_html("line one\nline two", preformatted_text=True)

    assert remove_empty_html_tags(simplify_html_text(content)) == "<pre>line one\nline two</pre>"


def test_empty_text_stays_empty() -> None:
    assert text_to_simple_html("", preformatted_text=True) == ""
    assert text_to_simple_html(None, preformatted_text=False) == ""


def test_root_relative_link_is_resolved_against_the_source_page() -> None:
    # Left relative, the GUI resolves this against the Taranis origin and the link points
    # back at this instance instead of the advisory it was collected from.
    html = '<a href="/security/security-advisories/cve-2026-75889/">Alloy</a>'

    result = resolve_relative_links(html, "https://grafana.com/security/security-advisories/")

    assert result == '<a href="https://grafana.com/security/security-advisories/cve-2026-75889/">Alloy</a>'


def test_path_relative_link_is_resolved_against_the_source_page() -> None:
    html = '<a href="cve-2026-75889/">Alloy</a>'

    result = resolve_relative_links(html, "https://grafana.com/security/security-advisories/")

    assert 'href="https://grafana.com/security/security-advisories/cve-2026-75889/"' in result


def test_absolute_and_non_network_links_are_left_alone() -> None:
    html = '<a href="https://example.com/a">a</a><a href="mailto:x@example.com">b</a>'

    assert resolve_relative_links(html, "https://grafana.com/security/") == html


def test_missing_base_url_leaves_the_html_untouched() -> None:
    # Manually entered items have no source page to resolve against.
    html = '<a href="/relative">a</a>'

    assert resolve_relative_links(html, "") == html


def test_links_survive_the_full_sanitization_chain_absolute() -> None:
    # The order the collectors use: simplify, then resolve, then drop empties.
    content = '<table><tr><td><a href="/a/b" class="x">Advisory</a></td></tr></table>'

    result = remove_empty_html_tags(resolve_relative_links(simplify_html_text(content), "https://example.com/list/"))

    assert '<a href="https://example.com/a/b">Advisory</a>' in result
