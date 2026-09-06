"""Tests for the mail header sanitizer.

Header values come from analyst-entered report item attributes, and the email publisher
hands whatever survives here straight to ``envelope.header()`` — which reroutes ``bcc``
into the real SMTP recipient list. So the properties asserted here are: no attribute value
can ever produce a header that changes delivery, no attribute value can escape its own
header line, and a template typo costs one header rather than the whole publish.
"""

import pytest
from shared.mail_headers import (
    MAX_HEADERS,
    MAX_TOTAL_LENGTH,
    MAX_VALUE_LENGTH,
    RESERVED_HEADERS,
    RESERVED_PREFIXES,
    parse_header_block,
    sanitize_header,
    sanitize_headers,
    scrub_header_text,
)


def test_plain_header_survives_intact() -> None:
    assert parse_header_block("X-Report-Category: Ransomware") == [{"name": "X-Report-Category", "value": "Ransomware"}]


# --- injection ---------------------------------------------------------------------


def test_newline_in_a_value_cannot_smuggle_a_bcc() -> None:
    # The whole point of the module: an analyst types a newline and an address into an
    # attribute, and it must not become a recipient.
    headers = parse_header_block("X-Report-Category: Ransomware\nBcc: attacker@evil.test")

    assert headers == [{"name": "X-Report-Category", "value": "Ransomware"}]
    assert not [h for h in headers if h["name"].lower() == "bcc"]


def test_bcc_is_refused_whatever_its_casing() -> None:
    assert parse_header_block("BcC: attacker@evil.test") == []


@pytest.mark.parametrize("name", sorted(RESERVED_HEADERS))
def test_every_reserved_header_is_dropped(name: str) -> None:
    assert parse_header_block(f"{name}: whatever") == []


@pytest.mark.parametrize("prefix", RESERVED_PREFIXES)
def test_every_reserved_prefix_is_dropped(prefix: str) -> None:
    assert parse_header_block(f"{prefix}something: whatever") == []


def test_a_refused_header_does_not_take_its_neighbours_with_it() -> None:
    block = "X-Report-Type: Advisory\nBcc: attacker@evil.test\nX-Report-Category: Phishing"

    assert [h["name"] for h in parse_header_block(block)] == ["X-Report-Type", "X-Report-Category"]


# --- field names -------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "X-Colon: Injected",  # a second colon would serialise as "X-Colon: Injected: value"
        "X Bad Name",  # space is not ftext
        "X-ü",  # non-ASCII names are accepted by the stdlib and serialised raw
        "",
        "  ",
        "X" * 65,  # over MAX_NAME_LENGTH
    ],
)
def test_invalid_field_names_are_dropped(name: str) -> None:
    assert sanitize_header(name, "value") is None


@pytest.mark.parametrize("name", ["X-Report-Category", "X-Report-Max-CVSS", "Organization", "Auto-Submitted"])
def test_valid_field_names_are_kept(name: str) -> None:
    assert sanitize_header(name, "value") == (name, "value")


def test_space_before_the_colon_is_tolerated() -> None:
    assert parse_header_block("X-Report-Type : Advisory") == [{"name": "X-Report-Type", "value": "Advisory"}]


# --- value scrubbing ---------------------------------------------------------------


@pytest.mark.parametrize(
    "char",
    [
        "\x00",
        "\x0b",
        "\x0c",
        "\r",
        "\x1f",
        "\x7f",
        "\u0085",  # NEL
        "\u2028",  # LINE SEPARATOR - not a "\n", but str.splitlines() breaks on it
        "\u2029",  # PARAGRAPH SEPARATOR
    ],
)
def test_line_breaking_characters_become_a_single_space(char: str) -> None:
    assert scrub_header_text(f"Ransomware{char}Phishing") == "Ransomware Phishing"


def test_tabs_and_runs_of_whitespace_collapse() -> None:
    assert scrub_header_text("  Ransomware \t\t  Phishing  ") == "Ransomware Phishing"


def test_none_scrubs_to_empty_string() -> None:
    # Guards the max_cvss case: Jinja stringifies None as "None" without this.
    assert scrub_header_text(None) == ""


def test_non_ascii_values_are_kept_verbatim() -> None:
    # EmailMessage.__setitem__ does the RFC 2047 encoding; doing it here would deliver
    # literal "=?utf-8?q?" text to the reader.
    assert sanitize_header("X-Report-Category", "Ransomware, Špionáž") == ("X-Report-Category", "Ransomware, Špionáž")


# --- empty values ------------------------------------------------------------------


@pytest.mark.parametrize("block", ["X-Report-Category:", "X-Report-Category: ", "X-Report-Category:   \t "])
def test_empty_values_are_dropped(block: str) -> None:
    # The common case: the template's join() produced nothing because no report item
    # carries the attribute. An empty header must not reach the wire.
    assert parse_header_block(block) == []


# --- folding -----------------------------------------------------------------------


def test_a_continuation_line_joins_the_previous_header() -> None:
    block = "X-Report-Category: Ransomware,\n  Phishing"

    assert parse_header_block(block) == [{"name": "X-Report-Category", "value": "Ransomware, Phishing"}]


def test_a_continuation_without_a_header_is_dropped() -> None:
    assert parse_header_block("   orphaned continuation") == []


def test_blank_lines_do_not_terminate_the_block() -> None:
    # Unlike a real message parser. Jinja output is ragged and a template author should
    # not have to fight whitespace control to emit a header block.
    block = "X-Report-Type: Advisory\n\n\n   \n\nX-Report-Category: Phishing"

    assert [h["name"] for h in parse_header_block(block)] == ["X-Report-Type", "X-Report-Category"]


def test_crlf_line_endings_are_handled() -> None:
    assert len(parse_header_block("X-Report-Type: Advisory\r\nX-Report-Category: Phishing")) == 2


def test_a_line_without_a_colon_is_dropped() -> None:
    assert parse_header_block("this is not a header\nX-Report-Type: Advisory") == [{"name": "X-Report-Type", "value": "Advisory"}]


# --- limits ------------------------------------------------------------------------


def test_header_count_is_capped() -> None:
    block = "\n".join(f"X-Header-{index}: value" for index in range(MAX_HEADERS + 10))

    assert len(parse_header_block(block)) == MAX_HEADERS


def test_an_overlong_value_is_truncated_rather_than_dropped() -> None:
    headers = parse_header_block(f"X-Report-Category: {'a' * 5000}")

    assert len(headers) == 1
    assert len(headers[0]["value"]) == MAX_VALUE_LENGTH
    assert headers[0]["value"].endswith("…")


def test_total_value_length_is_capped() -> None:
    # Each value is just under MAX_VALUE_LENGTH, so the cap bites before MAX_HEADERS does.
    block = "\n".join(f"X-Header-{index}: {'a' * 900}" for index in range(MAX_HEADERS))
    headers = parse_header_block(block)

    assert 0 < len(headers) < MAX_HEADERS
    assert sum(len(h["value"]) for h in headers) <= MAX_TOTAL_LENGTH


# --- contract the publisher relies on ----------------------------------------------


def test_sanitize_headers_is_idempotent() -> None:
    # The email publisher re-runs sanitize_headers on what the presenter sent it, so a
    # second pass must be a no-op for anything that legitimately survived the first.
    block = "X-Report-Category: Ransomware, Phishing\nX-Report-Max-CVSS: 9.8"
    once = parse_header_block(block)

    assert sanitize_headers(once) == once


def test_sanitize_headers_accepts_both_mappings_and_tuples() -> None:
    expected = [{"name": "X-Report-Type", "value": "Advisory"}]

    assert sanitize_headers([("X-Report-Type", "Advisory")]) == expected
    assert sanitize_headers([{"name": "X-Report-Type", "value": "Advisory"}]) == expected


def test_a_hostile_pair_is_still_refused_when_it_arrives_pre_structured() -> None:
    # Defence in depth: a version-skewed or compromised presenter node sends the pair
    # directly rather than through parse_header_block.
    assert sanitize_headers([{"name": "Bcc", "value": "attacker@evil.test"}]) == []


def test_repeated_names_are_preserved() -> None:
    # envelope.header() appends on repeat, so a template may emit one line per value.
    block = "X-Report-Category: Ransomware\nX-Report-Category: Phishing"

    assert parse_header_block(block) == [
        {"name": "X-Report-Category", "value": "Ransomware"},
        {"name": "X-Report-Category", "value": "Phishing"},
    ]
