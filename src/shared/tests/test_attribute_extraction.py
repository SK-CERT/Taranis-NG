"""Detection of vulnerability identifiers in news item text.

The matcher is shared: collectors run it as text arrives from RSS/web/email, and core runs
it for manually entered items, which never pass through a collector. Both call the same
function, so this suite is the one place its behaviour is pinned.

The seeded patterns are asserted here as literals rather than imported from core, so a
change to either side has to be a deliberate change to both.
"""

from __future__ import annotations

import time

import pytest
from shared.attribute_extraction import (
    TIMEOUT_SUPPORTED,
    ExtractionRule,
    build_text,
    extract_attributes,
)

# The rules seeded by the migration. Kept verbatim so a regression in either copy is visible.
SEEDED = {
    "CVE": r"CVE-\d{4}-\d{4,}",
    "CWE": r"CWE-\d+",
    "GHSA": r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}",
    "RHSA": r"RHSA-\d{4}:\d+",
    "EUVD": r"EUVD-\d{4}-\d+",
    "GCVE": r"GCVE-\d+-\d{4}-\d+",
    "CPE": r"cpe:2\.3:[aho]:[^\s:]+:[^\s:]+(?::[^\s:]*){0,9}",
    "CVSS2": r"\bAV:[LAN]/AC:[HML]/Au:[MSN]/C:[NPC]/I:[NPC]/A:[NPC]\b",
    "CVSS3": r"CVSS:3\.[01]/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH](?:/[A-Z]{1,2}:[A-Z]{1,2})*",
    "CVSS4": r"CVSS:4\.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[HLN]/VI:[HLN]/VA:[HLN]/SC:[HLN]/SI:[HLN]/SA:[HLN]",
}


def rule(key: str, **kwargs: object) -> ExtractionRule:
    """Build a rule for one seeded pattern."""
    return ExtractionRule(name=key, attribute_key=key, pattern=SEEDED[key], **kwargs)


def found(text: str, *keys: str) -> list[str]:
    """Return the values the named seeded rules find in text."""
    return [value for _key, value in extract_attributes("", "", text, [rule(k) for k in keys])]


# --- the preconfigured patterns ----------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "text", "expected"),
    [
        ("CVE", "flaw CVE-2021-44228 in Log4j", "CVE-2021-44228"),
        ("CVE", "CVE-2024-1234.", "CVE-2024-1234"),
        ("CWE", "classified CWE-79 (XSS)", "CWE-79"),
        ("GHSA", "advisory GHSA-jfh8-c2jp-5v3q here", "GHSA-jfh8-c2jp-5v3q"),
        ("RHSA", "see RHSA-2024:1234 for details", "RHSA-2024:1234"),
        ("EUVD", "tracked as EUVD-2025-12345", "EUVD-2025-12345"),
        ("GCVE", "id GCVE-1-2025-0001 assigned", "GCVE-1-2025-0001"),
        ("CPE", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*"),
        ("CVSS2", "scored (AV:N/AC:L/Au:N/C:P/I:P/A:P)", "AV:N/AC:L/Au:N/C:P/I:P/A:P"),
        ("CVSS3", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
        ("CVSS3", "CVSS:3.0/AV:L/AC:H/PR:H/UI:R/S:C/C:L/I:N/A:N", "CVSS:3.0/AV:L/AC:H/PR:H/UI:R/S:C/C:L/I:N/A:N"),
        (
            "CVSS4",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
        ),
    ],
)
def test_seeded_pattern_matches_a_real_identifier(key: str, text: str, expected: str) -> None:
    assert found(text, key) == [expected]


@pytest.mark.parametrize(
    ("key", "text"),
    [
        ("CVE", "CVE-99-1"),  # year and sequence both too short
        ("CVE", "CVE-2024-123"),  # sequence below four digits
        ("CWE", "CWE-"),
        ("RHSA", "RHSA-2024-1234"),  # RHSA uses a colon, not a dash
        ("CPE", "cpe:1.3:a:apache:log4j"),  # only the 2.3 form is matched
        ("CVSS2", "AV:X/AC:L/Au:N/C:P/I:P/A:P"),  # AV:X is not a v2 value
        ("CVSS2", "AV:N/AC:L/C:P/I:P/A:P"),  # partial vector, Au: missing
        ("CVSS3", "CVSS:2.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),  # no such prefix
        ("CVSS3", "CVSS:3.1/AV:N/AC:X/PR:N/UI:N/S:U/C:H/I:H/A:H"),  # AC:X is not a value
    ],
)
def test_seeded_pattern_rejects_a_near_miss(key: str, text: str) -> None:
    assert found(text, key) == []


def test_the_v2_rule_does_not_fire_on_a_v3_vector() -> None:
    # v2 has no CVSS: prefix to anchor on, so this is the ambiguity that matters.
    # Au: exists only in v2, which is what keeps them apart.
    assert found("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "CVSS2") == []


def test_v3_accepts_trailing_temporal_metrics() -> None:
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:F/RL:O/RC:C"
    assert found(vector, "CVSS3") == [vector]


# --- behaviour shared by every rule ------------------------------------------------------


def test_searches_title_review_and_content() -> None:
    got = extract_attributes("CVE-2024-0001", "CVE-2024-0002", "CVE-2024-0003", [rule("CVE")])
    assert [v for _k, v in got] == ["CVE-2024-0001", "CVE-2024-0002", "CVE-2024-0003"]


def test_the_same_value_is_reported_once() -> None:
    got = extract_attributes("CVE-2021-44228", "CVE-2021-44228 again", "and CVE-2021-44228", [rule("CVE")])
    assert got == [("CVE", "CVE-2021-44228")]


def test_max_matches_bounds_one_rule() -> None:
    # a loose pattern must not be able to add thousands of attributes to one item
    text = " ".join(f"CVE-2024-{n:04d}" for n in range(1, 51))
    assert len(extract_attributes("", "", text, [rule("CVE", max_matches=5)])) == 5


def test_capture_group_selects_part_of_the_match() -> None:
    ticket = ExtractionRule("Ticket", "TICKET", r"INC-(\d+)", capture_group=1)
    assert extract_attributes("", "", "raised INC-4242 today", [ticket]) == [("TICKET", "4242")]


def test_group_one_is_used_when_the_pattern_defines_one() -> None:
    # ANALYST_BOT behaviour, so rules written for the old bot keep working
    ticket = ExtractionRule("Ticket", "TICKET", r"INC-(\d+)")
    assert extract_attributes("", "", "raised INC-7 today", [ticket]) == [("TICKET", "7")]


def test_text_is_truncated_before_matching() -> None:
    text = ("x" * 200) + " CVE-2024-1234"
    assert extract_attributes("", "", text, [rule("CVE")], max_text=50) == []


def test_empty_text_and_empty_rules_are_handled() -> None:
    assert extract_attributes("", "", "", [rule("CVE")]) == []
    assert extract_attributes("CVE-2024-1234", "", "", []) == []


def test_rules_missing_a_pattern_or_key_are_skipped() -> None:
    blank = ExtractionRule("blank", "", r"CVE-\d{4}-\d{4,}")
    no_pattern = ExtractionRule("no pattern", "CVE", "")
    assert extract_attributes("", "", "CVE-2024-1234", [blank, no_pattern]) == []


def test_build_text_ignores_missing_parts() -> None:
    assert build_text(None, "review", None) == "review"
    assert build_text("t", "r", "c") == "t r c"


# --- one bad rule must never stop the others ---------------------------------------------


def test_an_invalid_pattern_is_skipped() -> None:
    broken = ExtractionRule("broken", "BAD", r"(unclosed")
    got = extract_attributes("", "", "CVE-2024-1234", [broken, rule("CVE")])
    assert got == [("CVE", "CVE-2024-1234")]


@pytest.mark.skipif(not TIMEOUT_SUPPORTED, reason="the regex module is required for a per-rule timeout")
def test_a_catastrophic_pattern_times_out_without_stalling_the_batch() -> None:
    # The reason this feature is bounded at all: the patterns are operator-editable and run
    # against every collected item, so `(a+)+$` would otherwise hang collection for every
    # source on the node.
    evil = ExtractionRule("catastrophic", "EVIL", r"(a+)+$")
    text = "a" * 5000 + "!  CVE-2024-1234"

    started = time.monotonic()
    got = extract_attributes("", "", text, [evil, rule("CVE")], timeout=0.5)
    elapsed = time.monotonic() - started

    assert elapsed < 5, f"the timeout did not interrupt the pattern ({elapsed:.1f}s)"
    assert got == [("CVE", "CVE-2024-1234")], "the following rule must still run"


# --- rules arrive from core as JSON ------------------------------------------------------


def test_optional_fields_fall_back_to_defaults() -> None:
    parsed = ExtractionRule.from_dict({"name": "CVE", "attribute_key": "CVE", "pattern": SEEDED["CVE"]})
    assert parsed.capture_group == 0
    assert parsed.max_matches > 0


def test_all_fields_are_read() -> None:
    parsed = ExtractionRule.from_dict(
        {"name": "Ticket", "attribute_key": "TICKET", "pattern": r"INC-(\d+)", "capture_group": 1, "max_matches": 7},
    )
    assert parsed == ExtractionRule("Ticket", "TICKET", r"INC-(\d+)", 1, 7)


def test_a_null_optional_field_does_not_become_none() -> None:
    # core serialises unset integers as null; they must not reach re as None
    parsed = ExtractionRule.from_dict({"attribute_key": "CVE", "pattern": "x", "capture_group": None, "max_matches": None})
    assert parsed.capture_group == 0
    assert parsed.max_matches > 0
