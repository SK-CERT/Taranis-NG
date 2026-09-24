"""Detection of vulnerability identifiers in news item text.

The matcher is shared: collectors run it as text arrives from RSS/web/email, and core runs
it for manually entered items, which never pass through a collector. Both call the same
function, so this suite is the one place its behaviour is pinned.

The seeded patterns are asserted here as literals rather than imported from core, so a
change to either side has to be a deliberate change to both.
"""

from __future__ import annotations

import re
import time

import pytest
from shared.attribute_extraction import (
    TIMEOUT_SUPPORTED,
    ExtractionRule,
    build_text,
    extract_attributes,
    pattern_error,
)

# The rules seeded by the migration. Kept verbatim so a regression in either copy is visible.
SEEDED = {
    "CVE": r"\bCVE-\d{4}-\d{4,}",
    "CWE": r"CWE-\d+",
    "GHSA": r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}",
    "RHSA": r"RHSA-\d{4}:\d+",
    "EUVD": r"EUVD-\d{4}-\d+",
    "GCVE": (
        r"""GCVE-(?=(?:(?![<>"'])[\x22-\x7E]){0,249}(?![<>"'.,;:!?)])[\x22-\x7E][.,;:!?)]*(?:[<>"']|[^\x22-\x7E]|$))"""
        r"""[0-9]+-(?:(?![<>"'])[\x22-\x7E])*(?![<>"'.,;:!?)])[\x22-\x7E]"""
    ),
    "CPE": r"cpe:2\.3:[aho](?::(?:[A-Za-z0-9_\-*?]|\\[^\s]|\.(?=[A-Za-z0-9_\-*?\\]))+){2,10}",
    "CVSS2": r"\bAV:[LAN]/AC:[HML]/Au:[MSN]/C:[NPC]/I:[NPC]/A:[NPC](?:/(?:E|RL|RC|CDP|TD|CR|IR|AR):(?:POC|ND|OF|TF|UC|UR|LM|MH|[A-Z]))*\b",
    "CVSS3": r"CVSS:3\.[01]/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH](?:/[A-Z]{1,3}:[A-Z])*",
    "CVSS4": (
        r"CVSS:4\.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[HLN]/VI:[HLN]/VA:[HLN]/SC:[HLN]/SI:[HLN]/SA:[HLN]"
        r"(?:/[A-Z]{1,3}:(?:Clear|Green|Amber|Red|[A-Z]))*"
    ),
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
        ("CVE", "https://nvd.nist.gov/vuln/detail/CVE-2024-1234", "CVE-2024-1234"),
        ("CWE", "classified CWE-79 (XSS)", "CWE-79"),
        ("GHSA", "advisory GHSA-jfh8-c2jp-5v3q here", "GHSA-jfh8-c2jp-5v3q"),
        ("RHSA", "see RHSA-2024:1234 for details", "RHSA-2024:1234"),
        ("EUVD", "tracked as EUVD-2025-12345", "EUVD-2025-12345"),
        ("GCVE", "id GCVE-1-2025-0001 assigned", "GCVE-1-2025-0001"),
        ("CPE", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*"),
        # HTML around the name, and a sentence's full stop after it, are not part of it.
        ("CPE", "<code>cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*</code>", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*"),
        ("CPE", "Affected: cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*.", "cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*"),
        ("CPE", '<a href="/cpe:2.3:o:linux:linux_kernel:5.10:-:*:*:*:*:*:*">', "cpe:2.3:o:linux:linux_kernel:5.10:-:*:*:*:*:*:*"),
        ("CPE", r"cpe:2.3:a:foo\:bar:baz:1.0:*:*:*:*:*:*:*", r"cpe:2.3:a:foo\:bar:baz:1.0:*:*:*:*:*:*:*"),  # escaped colon
        ("CPE", "abbreviated cpe:2.3:a:apache:log4j, then", "cpe:2.3:a:apache:log4j"),
        ("CVSS2", "scored (AV:N/AC:L/Au:N/C:P/I:P/A:P)", "AV:N/AC:L/Au:N/C:P/I:P/A:P"),
        ("CVSS2", "NVD: (AV:N/AC:L/Au:N/C:P/I:P/A:P/E:POC/RL:OF/RC:C)", "AV:N/AC:L/Au:N/C:P/I:P/A:P/E:POC/RL:OF/RC:C"),
        (
            "CVSS3",
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:P/RL:O/RC:C/CR:H/IR:H/AR:H/MAV:N/MAC:L/MPR:N/MUI:N/MS:U/MC:H/MI:H/MA:H.",
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:P/RL:O/RC:C/CR:H/IR:H/AR:H/MAV:N/MAC:L/MPR:N/MUI:N/MS:U/MC:H/MI:H/MA:H",
        ),
        ("CVSS3", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
        ("CVSS3", "CVSS:3.0/AV:L/AC:H/PR:H/UI:R/S:C/C:L/I:N/A:N", "CVSS:3.0/AV:L/AC:H/PR:H/UI:R/S:C/C:L/I:N/A:N"),
        (
            "CVSS4",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
        ),
        (
            "CVSS4",
            "(CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:A)",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:A",
        ),
        (
            "CVSS4",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/S:P/AU:Y/R:A/V:D/RE:L/U:Red",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/S:P/AU:Y/R:A/V:D/RE:L/U:Red",
        ),
        (
            "CVSS4",  # a word value must not be cut to its first letter
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/U:Clear",
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/U:Clear",
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
        ("CVE", "Tracked as GCVE-1337-2025-0001"),  # the tail of a GCVE ID with a four-digit GNA
        ("CWE", "CWE-"),
        ("RHSA", "RHSA-2024-1234"),  # RHSA uses a colon, not a dash
        ("GCVE", "GCVE-x-2024-1"),  # the GNA ID is numeric
        ("GCVE", "GCVE-1- next"),  # no local ID
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


# --- GCVE: GCVE-<GNA ID>-<local ID>, where each GNA picks its own local IDs ---------------

# The validation form of a GCVE identifier. The seeded rule searches inside text, so it has no
# anchors; these tests hold it to exactly the identifiers this accepts.
GCVE_SPEC = r"^(?=.{8,255}$)GCVE-[0-9]+-[\x22-\x7E]+$"

GCVE_EXAMPLES = [
    "GCVE-0-2024-13987",
    "GCVE-1337-2025-00000000000000000000000000000000000000000000000001011111011111010111111001000000000000000000000000000000000000000000000000000000001",
    "GCVE-65535-2021-XX-[222]_XX{1}",
    "GCVE-65535-2021-XX-[222]_XX{1}/1/1/1",
    r"GCVE-65535-2021-XX-[222]_XX{1}\1/1\1",
    "GCVE-65535-GHSA-jc7w-c686-c4v9",
    "GCVE-65535-jc7w-c686-c4v9",
    "GCVE-65535-ababcbbe.onion-1",
    "GCVE-65535-Ivanti/Avalanche-1",
]
GCVE_LONGEST = "GCVE-1-" + "a" * 248  # 255 characters, the most an identifier may have

# Where an identifier turns up in collected text: prose, HTML, a link, and next to punctuation
# that is not part of it.
GCVE_CONTEXTS = [
    "{}",
    "Tracked as {} today",
    "<p>{}</p><p>Next</p>",
    '<a href="https://db.gcve.eu/vuln/{}">advisory</a>',
    "(see {}).",
    "{}, and more",
    "Ends with {}.",
    "Fixed {}!",
]


@pytest.mark.parametrize("identifier", [*GCVE_EXAMPLES, GCVE_LONGEST])
def test_gcve_examples_are_valid_identifiers(identifier: str) -> None:
    assert re.fullmatch(GCVE_SPEC, identifier)


@pytest.mark.parametrize("context", GCVE_CONTEXTS)
@pytest.mark.parametrize("identifier", [*GCVE_EXAMPLES, GCVE_LONGEST])
def test_a_gcve_identifier_is_found_whole_in_text(identifier: str, context: str) -> None:
    assert found(context.format(identifier), "GCVE") == [identifier]


@pytest.mark.parametrize("context", GCVE_CONTEXTS)
def test_a_gcve_identifier_over_255_characters_is_not_found(context: str) -> None:
    # Not even as a truncated prefix: that would be a different identifier.
    too_long = GCVE_LONGEST + "a"
    assert not re.fullmatch(GCVE_SPEC, too_long)
    assert found(context.format(too_long), "GCVE") == []


def test_gcve_identifiers_in_a_list_are_found_separately() -> None:
    text = "Affects GCVE-0-2024-13987, GCVE-65535-Ivanti/Avalanche-1 and GCVE-65535-2021-XX-[222]_XX{1}."
    assert found(text, "GCVE") == ["GCVE-0-2024-13987", "GCVE-65535-Ivanti/Avalanche-1", "GCVE-65535-2021-XX-[222]_XX{1}"]


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


def test_capture_group_zero_is_the_whole_match_even_when_the_pattern_has_groups() -> None:
    # The GUI promises "0 stores the whole match"; a grouped alternation must not store the prefix.
    advisory = ExtractionRule("Advisory", "ADVISORY", r"(CVE|GHSA)-\d{4}-\d+")
    assert extract_attributes("", "", "see CVE-2024-1234", [advisory]) == [("ADVISORY", "CVE-2024-1234")]


def test_a_missing_capture_group_falls_back_to_the_whole_match() -> None:
    # Saving rejects this (pattern_error); a rule stored before that check still yields something.
    ticket = ExtractionRule("Ticket", "TICKET", r"INC-(\d+)", capture_group=3)
    assert extract_attributes("", "", "raised INC-7 today", [ticket]) == [("TICKET", "INC-7")]


@pytest.mark.parametrize("pattern", ["(unclosed", "a{2,1}", "[z-a]", "*nothing-to-repeat"])
def test_pattern_error_reports_a_pattern_that_does_not_compile(pattern: str) -> None:
    assert pattern_error(pattern)


@pytest.mark.parametrize("pattern", [r"(?P<id>CVE-\d+)", r"(?i)cve-\d+", ""])
def test_pattern_error_accepts_python_only_syntax(pattern: str) -> None:
    # Named groups and inline flags are Python syntax that a browser RegExp rejects.
    assert pattern_error(pattern) is None


def test_pattern_error_reports_a_capture_group_the_pattern_does_not_have() -> None:
    assert pattern_error(r"INC-(\d+)", 1) is None
    assert "capture group 2" in pattern_error(r"INC-(\d+)", 2)


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
