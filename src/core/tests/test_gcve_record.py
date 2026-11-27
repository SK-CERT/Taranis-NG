"""GCVE records of CVD Reports: every field mapped, and every record valid (managers.gcve_publication).

The records are checked against the official CVE Record Format 5.2.0 schema, vendored unmodified,
with only the relaxations GCVE makes (see ``record_schema``); the relaxed schema is also checked
against a record a live GNA publishes.
"""

from __future__ import annotations

import json
import types
from datetime import UTC, datetime
from pathlib import Path

import pytest
from managers import gcve_publication
from shared.schema.attribute import AttributeType

from shared import gcve

RESOURCES = Path(__file__).parent / "resources" / "gcve"
GROUPS = {group.title: index for index, group in enumerate(gcve.CVD_GROUPS)}
FIELDS = gcve.cvd_fields()
ATTRIBUTES = {attribute.name: attribute for attribute in gcve.CVD_ATTRIBUTES}


def _group_item(key: str) -> types.SimpleNamespace:
    field = FIELDS[key]
    group = next(group for group in gcve.CVD_GROUPS if field in group.fields)
    attribute = ATTRIBUTES.get(field.attribute)
    attribute_type = AttributeType[attribute.type if attribute else field.attribute]
    return types.SimpleNamespace(
        title=field.title,
        index=group.fields.index(field),
        attribute=types.SimpleNamespace(type=attribute_type, validator_parameter=attribute.validator_parameter if attribute else None),
        attribute_group=types.SimpleNamespace(index=GROUPS[group.title]),
    )


def _value(key: str, value: object, description: str | None = None, number: int = 0) -> types.SimpleNamespace:
    text = json.dumps(value) if isinstance(value, dict) else value
    group_item = _group_item(key)
    return types.SimpleNamespace(
        id=number,
        value=text,
        value_description=description,
        attribute_group_item=group_item,
        attribute_group_item_title=group_item.title,
    )


MOMENT = datetime(2026, 11, 8, 10, 0, tzinfo=UTC)


def _assignment(**fields: object) -> types.SimpleNamespace:
    defaults = {
        "gcve_id": "GCVE-65535-2026-0001",
        "date_reserved": MOMENT,
        "date_published": MOMENT,
        "date_updated": None,
        "published": True,
    }
    return types.SimpleNamespace(**{**defaults, **fields})


def _report(*values: types.SimpleNamespace, **fields: object) -> types.SimpleNamespace:
    numbered = [types.SimpleNamespace(**{**vars(value), "id": number}) for number, value in enumerate(values, start=1)]
    defaults = {
        "title": "Login bypass",
        "title_prefix": "",
        "language": "en",
        "attributes": numbered,
        "report_item_type": types.SimpleNamespace(system_key=gcve.CVD_TYPE_KEY),
        "gcve_assignment": _assignment(),
    }
    return types.SimpleNamespace(**{**defaults, **fields})


AFFECTED = {
    "vendor": "Example",
    "product": "Portal",
    "cpes": ["cpe:2.3:a:example:portal:*:*:*:*:*:*:*:*"],
    "defaultStatus": "unaffected",
    "versions": [{"version": "1.0", "lessThan": "1.4.2", "status": "affected", "versionType": "semver"}],
}
REFERENCE = {"url": "https://example.com/advisory", "name": "Vendor advisory", "tags": ["vendor-advisory", "patch"]}


def _minimal(*extra: types.SimpleNamespace, **fields: object) -> types.SimpleNamespace:
    return _report(
        _value("record_type", "advisory"),
        _value("description", "<p>The portal lets anyone log in [#refkey].</p>"),
        _value("affected_products", AFFECTED),
        _value("references", REFERENCE, "refkey"),
        *extra,
        **fields,
    )


def _record(report: types.SimpleNamespace, short_name: str | None = "TEST-GNA") -> dict:
    return gcve_publication.build_record(report, report.gcve_assignment, short_name)


def test_a_minimal_record_is_valid_and_carries_the_gcve_identifier() -> None:
    report = _minimal()
    record = _record(report)

    assert gcve_publication.schema_errors(record) == []
    assert record["dataType"] == "CVE_RECORD"
    assert record["dataVersion"] == "5.2.0"
    metadata = record["cveMetadata"]
    # The identifier is in x_gcve only (GCVE-BCP-05); cveMetadata.vulnId is its deprecated place.
    assert "vulnId" not in metadata
    assert metadata["state"] == "PUBLISHED"
    assert "cveId" not in metadata
    # GCVE-BCP-03: the organisation UUIDs MAY be omitted, and are.
    assert "assignerOrgId" not in metadata
    assert "orgId" not in record["containers"]["cna"]["providerMetadata"]
    assert metadata["datePublished"] == "2026-11-08T10:00:00.000Z"
    cna = record["containers"]["cna"]
    assert cna["x_gcve"] == [{"vulnId": "GCVE-65535-2026-0001", "recordType": "advisory"}]
    assert cna["title"] == "Login bypass"
    assert gcve_publication.problems(report, "TEST-GNA") == []


def test_texts_are_plain_with_their_html_as_supporting_media_and_citations_numbered() -> None:
    cna = _record(_minimal())["containers"]["cna"]

    (description,) = cna["descriptions"]
    assert description["lang"] == "en"
    assert description["value"] == "The portal lets anyone log in [1]."
    assert description["supportingMedia"] == [{"type": "text/html", "base64": False, "value": "<p>The portal lets anyone log in [1].</p>"}]
    assert cna["references"] == [REFERENCE]


def test_a_cve_relates_the_record_to_it() -> None:
    cna_and_metadata = _record(_minimal(_value("cve", "CVE-2026-12345")))

    assert cna_and_metadata["cveMetadata"]["cveId"] == "CVE-2026-12345"
    assert cna_and_metadata["containers"]["cna"]["x_gcve"][0]["relationships"] == [{"destId": "CVE-2026-12345", "type": "equal"}]


def test_every_optional_field_is_mapped_and_the_record_stays_valid() -> None:
    report = _minimal(
        _value("cve", "CVE-2026-12345"),
        _value("related_records", {"destId": "GCVE-1-2026-0042", "type": "related"}),
        _value("tags", "disputed\nexclusively-hosted-service"),
        _value("cvss", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "Default configuration"),
        _value("cvss", "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:P/S:N/AU:Y/U:Amber"),
        _value("other_metrics", {"type": "ssvc", "content": {"exploitation": "poc"}}),
        _value("cwe", "287", "Improper Authentication"),
        _value("problem_types", "Login bypass"),
        _value("impacts", "<p>CAPEC-115 Authentication Bypass</p>"),
        _value(
            "taxonomy_mappings",
            {
                "taxonomyName": "ATT&CK",
                "taxonomyRelations": [{"taxonomyId": "T1078", "relationshipName": "mitigatedBy", "relationshipValue": "M1032"}],
            },
        ),
        _value("date_public", "2026-11-01"),
        _value("solutions", "<p>Update to 1.4.2.</p>"),
        _value("workarounds", "<p>Block /login.</p>"),
        _value("configurations", "<p>SSO enabled.</p>"),
        _value("exploits", "<p>A proof of concept exists.</p>"),
        _value("discovery", "EXTERNAL"),
        _value("defects", "BUG-17"),
        _value("advisories", "EX-2026-03"),
        _value("timeline", {"time": "2026-10-01T09:30", "value": "Reported to the vendor"}),
        _value("credits", {"value": "Example Researcher", "type": "finder"}),
    )
    record = _record(report)
    cna = record["containers"]["cna"]

    assert gcve_publication.schema_errors(record) == []
    assert cna["x_gcve"][0]["relationships"] == [
        {"destId": "CVE-2026-12345", "type": "equal"},
        {"destId": "GCVE-1-2026-0042", "type": "related"},
    ]
    assert cna["tags"] == ["disputed", "exclusively-hosted-service"]
    v3, v4, other = cna["metrics"]
    assert v3["cvssV3_1"]["baseScore"] == 9.8
    assert v3["cvssV3_1"]["baseSeverity"] == "CRITICAL"
    assert v3["scenarios"] == [{"lang": "en", "value": "Default configuration"}]
    assert v4["cvssV4_0"]["attackRequirements"] == "NONE"
    assert v4["cvssV4_0"]["vulnConfidentialityImpact"] == "HIGH"
    assert v4["cvssV4_0"]["exploitMaturity"] == "PROOF_OF_CONCEPT"
    assert v4["cvssV4_0"]["Automatable"] == "YES"
    assert v4["cvssV4_0"]["providerUrgency"] == "AMBER"
    assert other == {"format": "ssvc", "other": {"type": "ssvc", "content": {"exploitation": "poc"}}}
    assert cna["problemTypes"] == [
        {"descriptions": [{"lang": "en", "cweId": "CWE-287", "description": "CWE-287 Improper Authentication", "type": "CWE"}]},
        {"descriptions": [{"lang": "en", "description": "Login bypass", "type": "text"}]},
    ]
    assert cna["impacts"][0]["capecId"] == "CAPEC-115"
    assert cna["taxonomyMappings"][0]["taxonomyName"] == "ATT&CK"
    assert cna["datePublic"] == "2026-11-01T00:00:00.000Z"
    assert cna["solutions"][0]["value"] == "Update to 1.4.2."
    assert cna["workarounds"][0]["value"] == "Block /login."
    assert cna["configurations"][0]["value"] == "SSO enabled."
    assert cna["exploits"][0]["value"] == "A proof of concept exists."
    assert cna["source"] == {"discovery": "EXTERNAL", "defect": ["BUG-17"], "advisory": ["EX-2026-03"]}
    assert cna["timeline"] == [{"time": "2026-10-01T09:30:00.000Z", "lang": "en", "value": "Reported to the vendor"}]
    assert cna["credits"] == [{"lang": "en", "value": "Example Researcher", "type": "finder"}]
    assert cna["cpeApplicability"] == [
        {"nodes": [{"operator": "OR", "negate": False, "cpeMatch": [{"vulnerable": True, "criteria": AFFECTED["cpes"][0]}]}]},
    ]
    assert gcve_publication.problems(report) == []


def test_a_range_may_change_status_within_it() -> None:
    affected = {
        **AFFECTED,
        "versions": [
            {
                "version": "1.0",
                "lessThan": "2.0",
                "status": "affected",
                "versionType": "semver",
                "changes": [{"at": "1.4.2", "status": "unaffected"}],
            },
        ],
    }
    assert gcve_publication.validate_value("AFFECTED", json.dumps(affected)) is None
    record = _record(
        _report(
            _value("record_type", "advisory"),
            _value("description", "<p>Fixed in 1.4.2.</p>"),
            _value("affected_products", affected),
            _value("references", REFERENCE, "refkey"),
        ),
    )

    assert gcve_publication.schema_errors(record) == []
    assert record["containers"]["cna"]["affected"][0]["versions"][0]["changes"] == [{"at": "1.4.2", "status": "unaffected"}]
    assert gcve_publication.summary("AFFECTED", affected) == "Example Portal: 1.0 to before 2.0 (affected; unaffected from 1.4.2)"

    without_version = {**affected, "versions": [{**affected["versions"][0], "changes": [{"status": "unaffected"}]}]}
    assert "'at' is a required property" in gcve_publication.validate_value("AFFECTED", json.dumps(without_version))


def test_the_required_fields_are_required() -> None:
    report = _report(_value("record_type", "advisory"))

    found = gcve_publication.problems(report)

    assert "Description: required" in found
    assert "Affected products: required" in found
    assert "References: required" in found


def test_only_english_cvd_reports_of_an_allocated_identifier_are_published() -> None:
    assert gcve_publication.problems(_minimal(language="cs")) == ["a CVD Report must be written in English"]
    assert gcve_publication.problems(_minimal(gcve_assignment=None)) == ["it has no GCVE identifier"]
    other = _minimal(report_item_type=types.SimpleNamespace(system_key=None))
    assert gcve_publication.problems(other) == ["only CVD Reports can be published in a GCVE Advisory"]


def test_an_update_carries_its_identifier_in_its_only_x_gcve_entry() -> None:
    report = _report(
        _value("record_type", "update"),
        _value("description", "<p>Fixed in 1.4.3 too.</p>"),
        _value("affected_products", AFFECTED),
        _value("references", REFERENCE, "refkey"),
        _value("related_records", {"destId": "GCVE-65535-2026-0002", "type": "related"}),
    )
    record = _record(report)

    assert gcve_publication.schema_errors(record) == []
    assert "vulnId" not in record["cveMetadata"]
    assert record["containers"]["cna"]["x_gcve"] == [
        {"vulnId": "GCVE-65535-2026-0001", "recordType": "update", "relationships": [{"destId": "GCVE-65535-2026-0002", "type": "related"}]},
    ]


def _of_type(record_type: str, *extra: types.SimpleNamespace) -> types.SimpleNamespace:
    return _report(
        _value("record_type", record_type),
        _value("description", "<p>About GCVE-65535-2026-0002.</p>"),
        _value("affected_products", AFFECTED),
        _value("references", REFERENCE, "refkey"),
        *extra,
    )


# GCVE-BCP-05 1.8: every record type but advisory and bundle MUST include a relationships table
# (translation is not offered: records are English only).
NEEDING_RELATIONSHIPS = ["update", "analysis", "metadata", "reference", "comment", "statement", "remediation", "deprecation", "detection"]


def test_every_record_type_but_advisory_and_bundle_needs_relationships() -> None:
    assert sorted(gcve.RECORD_TYPES_NEEDING_RELATIONSHIPS) == sorted([*NEEDING_RELATIONSHIPS, "translation"])


@pytest.mark.parametrize("record_type", NEEDING_RELATIONSHIPS)
def test_a_record_other_than_an_advisory_or_a_bundle_relates_to_another_record(record_type: str) -> None:
    alone = _of_type(record_type)
    assert gcve_publication.problems(alone) == [f"Related records: a record of type '{record_type}' must relate to another record"]

    related = _of_type(record_type, _value("related_records", {"destId": "GCVE-65535-2026-0002", "type": "related"}))
    assert gcve_publication.problems(related) == []
    # The CVE of the same vulnerability is a relationship too (equal).
    assert gcve_publication.problems(_of_type(record_type, _value("cve", "CVE-2026-12345"))) == []


@pytest.mark.parametrize("record_type", ["advisory", "bundle"])
def test_an_advisory_or_a_bundle_may_stand_alone(record_type: str) -> None:
    assert gcve_publication.problems(_of_type(record_type)) == []


def test_a_translation_record_is_not_published() -> None:
    report = _minimal(record_type="ignored")
    report.attributes[0].value = "translation"
    assert "Record type: 'translation' cannot be published" in gcve_publication.problems(report)


def test_a_bare_cvss_score_cannot_be_published() -> None:
    assert gcve_publication.problems(_minimal(_value("cvss", "7.5"))) == [
        "CVSS: '7.5' is not a CVSS vector (2.0, 3.0, 3.1 or 4.0); a bare score cannot be published",
    ]


@pytest.mark.parametrize(
    ("attribute_type", "value", "parameter", "reason"),
    [
        # The alternatives the format offers are named by what each still misses.
        ("AFFECTED", {"vendor": "Example"}, None, "add product, or collectionURL and packageName"),
        ("AFFECTED", {"vendor": "Example", "product": "Portal"}, None, "add versions, or defaultStatus"),
        (
            "AFFECTED",
            {"vendor": "Example", "product": "Portal", "versions": [{"version": "0", "lessThan": "2.0", "status": "affected"}]},
            None,
            "versions/0: add versionType",
        ),
        ("AFFECTED", {"vendor": "Example", "product": "Portal", "defaultStatus": "broken"}, None, "defaultStatus"),
        ("CREDIT", {"value": "Researcher", "type": "hero"}, None, "type"),
        ("TIMELINE", {"time": "yesterday", "value": "Reported"}, None, "time"),
        ("RELATIONSHIP", {"destId": "CVE-2026-1", "type": "cousin"}, None, "type"),
        ("REFERENCE", {"url": "https://example.com", "tags": ["nonsense"]}, None, "tags"),
        ("JSON", {"type": "ssvc"}, gcve.JSON_METRIC_OTHER, "content"),
        ("JSON", {"taxonomyName": "ATT&CK"}, gcve.JSON_TAXONOMY_MAPPING, "taxonomyRelations"),
    ],
)
def test_structured_values_are_checked_against_the_cve_schema(attribute_type: str, value: dict, parameter: str | None, reason: str) -> None:
    found = gcve_publication.validate_value(attribute_type, json.dumps(value), parameter)

    assert found is not None
    assert reason in found


def test_empty_and_unstructured_values_need_no_check() -> None:
    assert gcve_publication.validate_value("AFFECTED", "", None) is None
    assert gcve_publication.validate_value("STRING", "{not json", None) is None
    assert gcve_publication.validate_value("CREDIT", "{not json", None) == "The value is not valid JSON"
    assert gcve_publication.validate_value("CREDIT", json.dumps({"value": "Researcher", "type": "finder"}), None) is None


def test_the_relaxed_schema_accepts_what_a_live_gna_publishes() -> None:
    # A made-up record in the shape live GNAs publish (2026-11-08): dataVersion 5.1, a placeholder
    # orgId, cveMetadata.vulnId, and x_gcve with an extension and a generator of its own.
    record = json.loads((RESOURCES / "gna_record.json").read_text(encoding="utf-8"))

    assert gcve_publication.schema_errors(record) == []


def test_records_skip_unpublished_and_repeated_reports() -> None:
    published = _minimal()
    reserved = _minimal(gcve_assignment=_assignment(gcve_id="GCVE-65535-2026-0002", published=False))

    records = gcve_publication.records([published, reserved, published])

    assert [record["containers"]["cna"]["x_gcve"][0]["vulnId"] for record in records] == ["GCVE-65535-2026-0001"]


def test_timestamps_are_utc_with_milliseconds() -> None:
    assert gcve_publication.timestamp(datetime(2026, 1, 2, 3, 4, 5, 678000, tzinfo=UTC)) == "2026-01-02T03:04:05.678Z"
    assert gcve_publication.timestamp(None) is None
