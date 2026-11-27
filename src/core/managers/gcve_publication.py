"""GCVE records of CVD Reports: CVE Record Format 5.2.0 with the GCVE extension (GCVE-BCP-05).

A CVD Report (see shared.gcve) becomes one record. Its fields map onto the CNA container of the
CVE Record Format; its GCVE identifier goes into its single ``x_gcve`` entry (GCVE-BCP-05), whatever
the record type. The deprecated ``cveMetadata.vulnId`` is not written: Vulnerability-Lookup, the
reference implementation, reads the identifier from ``x_gcve`` since its 7.0.0 fixes
(vulnerability-lookup#803). The organisation UUIDs the CVE Program requires are left out, as
GCVE-BCP-03 allows.

Records are checked against the official CVE Record Format 5.2.0 schema (vendored, CC0, in
``cve_schema/``) with the relaxations GCVE makes, see :func:`record_schema`. The same schema
checks the structured field values (affected products, credits, timeline, relationships,
references, other metrics, taxonomy mappings) when they are written.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from cvss import CVSS2, CVSS3, CVSS4
from jsonschema import Draft7Validator
from managers.link_references import ReferenceIndex
from shared.common import TZ
from shared.log_manager import logger

from shared import gcve

if TYPE_CHECKING:
    from collections.abc import Iterable

    from jsonschema.exceptions import ValidationError
    from jsonschema.protocols import Validator
    from model.gcve_assignment import GcveAssignment
    from model.report_item import ReportItem, ReportItemAttribute

SCHEMA_PATH = Path(__file__).with_name("cve_schema") / "CVE_Record_Format_bundled.json"

# Attribute types whose ``value`` holds a JSON object.
STRUCTURED_TYPES = frozenset({"AFFECTED", "CREDIT", "TIMELINE", "RELATIONSHIP", "REFERENCE", "JSON"})

CAPEC_PREFIX = re.compile(r"^\s*(CAPEC-[1-9][0-9]{0,4})\b[\s:.,-]*")
CWE_NUMBER = re.compile(r"^(?:CWE-)?([0-9]+)$", re.IGNORECASE)
CPE23 = re.compile(r"^cpe:2\.3:[aho*\-]:")

# CVSS 4.0 vector abbreviations -> the CVE Record Format's (FIRST) property names and values.
_V4_VALUES = {
    "AV": ("attackVector", {"N": "NETWORK", "A": "ADJACENT", "L": "LOCAL", "P": "PHYSICAL"}),
    "AC": ("attackComplexity", {"L": "LOW", "H": "HIGH"}),
    "AT": ("attackRequirements", {"N": "NONE", "P": "PRESENT"}),
    "PR": ("privilegesRequired", {"N": "NONE", "L": "LOW", "H": "HIGH"}),
    "UI": ("userInteraction", {"N": "NONE", "P": "PASSIVE", "A": "ACTIVE"}),
    "VC": ("vulnConfidentialityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "VI": ("vulnIntegrityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "VA": ("vulnAvailabilityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "SC": ("subConfidentialityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "SI": ("subIntegrityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "SA": ("subAvailabilityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE"}),
    "E": ("exploitMaturity", {"A": "ATTACKED", "P": "PROOF_OF_CONCEPT", "U": "UNREPORTED", "X": "NOT_DEFINED"}),
    "CR": ("confidentialityRequirement", {"H": "HIGH", "M": "MEDIUM", "L": "LOW", "X": "NOT_DEFINED"}),
    "IR": ("integrityRequirement", {"H": "HIGH", "M": "MEDIUM", "L": "LOW", "X": "NOT_DEFINED"}),
    "AR": ("availabilityRequirement", {"H": "HIGH", "M": "MEDIUM", "L": "LOW", "X": "NOT_DEFINED"}),
    "MAV": ("modifiedAttackVector", {"N": "NETWORK", "A": "ADJACENT", "L": "LOCAL", "P": "PHYSICAL", "X": "NOT_DEFINED"}),
    "MAC": ("modifiedAttackComplexity", {"L": "LOW", "H": "HIGH", "X": "NOT_DEFINED"}),
    "MAT": ("modifiedAttackRequirements", {"N": "NONE", "P": "PRESENT", "X": "NOT_DEFINED"}),
    "MPR": ("modifiedPrivilegesRequired", {"N": "NONE", "L": "LOW", "H": "HIGH", "X": "NOT_DEFINED"}),
    "MUI": ("modifiedUserInteraction", {"N": "NONE", "P": "PASSIVE", "A": "ACTIVE", "X": "NOT_DEFINED"}),
    "MVC": ("modifiedVulnConfidentialityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "X": "NOT_DEFINED"}),
    "MVI": ("modifiedVulnIntegrityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "X": "NOT_DEFINED"}),
    "MVA": ("modifiedVulnAvailabilityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "X": "NOT_DEFINED"}),
    "MSC": ("modifiedSubConfidentialityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "X": "NOT_DEFINED"}),
    "MSI": ("modifiedSubIntegrityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "S": "SAFETY", "X": "NOT_DEFINED"}),
    "MSA": ("modifiedSubAvailabilityImpact", {"H": "HIGH", "L": "LOW", "N": "NONE", "S": "SAFETY", "X": "NOT_DEFINED"}),
    "S": ("Safety", {"N": "NEGLIGIBLE", "P": "PRESENT", "X": "NOT_DEFINED"}),
    "AU": ("Automatable", {"N": "NO", "Y": "YES", "X": "NOT_DEFINED"}),
    "R": ("Recovery", {"A": "AUTOMATIC", "U": "USER", "I": "IRRECOVERABLE", "X": "NOT_DEFINED"}),
    "V": ("valueDensity", {"D": "DIFFUSE", "C": "CONCENTRATED", "X": "NOT_DEFINED"}),
    "RE": ("vulnerabilityResponseEffort", {"L": "LOW", "M": "MODERATE", "H": "HIGH", "X": "NOT_DEFINED"}),
    "U": ("providerUrgency", {"Clear": "CLEAR", "Green": "GREEN", "Amber": "AMBER", "Red": "RED", "X": "NOT_DEFINED"}),
}


class RecordProblemError(ValueError):
    """A record that cannot be published as it is; the message lists why."""


# -- schema -----------------------------------------------------------------------------------


@cache
def record_schema() -> dict:
    """The CVE Record Format 5.2.0 schema with the relaxations GCVE makes.

    - ``cveMetadata``: only ``state`` is required. A GCVE record has a CVE id only when the
      vulnerability has one, and the organisation UUID MAY be omitted (GCVE-BCP-03).
    - ``cveMetadata.vulnId`` is allowed: the deprecated place of the GCVE identifier, which
      other GNAs' records still carry; ours have it in ``x_gcve`` only.
    - ``providerMetadata.orgId`` MAY be omitted (GCVE-BCP-03).
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    definitions = schema["definitions"]
    metadata = definitions["cveMetadataPublished"]
    metadata["required"] = ["state"]
    metadata["properties"]["vulnId"] = {
        "type": "string",
        "description": "The GCVE identifier (GCVE-BCP-04).",
        "pattern": r"^GCVE-[0-9]+-[\x22-\x7E]+$",
        "maxLength": 255,
    }
    definitions["providerMetadata"]["required"] = []
    return schema


@cache
def _validator(pointer: str | None = None) -> Validator:
    """A validator for a published record, or for one definition of it (a JSON pointer).

    A record is checked against the schema's "Published" form directly rather than its root
    ``oneOf`` (published or rejected), so that an error names the field instead of the form.
    """
    schema = record_schema()
    if pointer is None:
        published = next(form for form in schema["oneOf"] if form.get("title") == "Published")
        return Draft7Validator({**published, "definitions": schema["definitions"]})
    return Draft7Validator({"$ref": f"#/{pointer}", "definitions": schema["definitions"]})


_RELATIONSHIP_SCHEMA = {
    "type": "object",
    "required": ["destId", "type"],
    "additionalProperties": False,
    "properties": {
        "destId": {"type": "string", "minLength": 1, "maxLength": 255},
        "type": {"enum": list(gcve.RELATIONSHIP_TYPES)},
        "srcId": {"type": "string", "minLength": 1, "maxLength": 255},
    },
}

# What each structured type is checked against: a definition of the CVE schema, or our own.
_VALUE_POINTERS = {
    "AFFECTED": "definitions/product",
    "CREDIT": "definitions/credits/items",
    "TIMELINE": "definitions/timeline/items",
    "REFERENCE": "definitions/reference",
    gcve.JSON_METRIC_OTHER: "definitions/metrics/items/properties/other",
    gcve.JSON_TAXONOMY_MAPPING: "definitions/taxonomyMappings/items",
}


def _path_key(error: ValidationError) -> list[tuple[int, int | str]]:
    # A path mixes list indexes and property names, which do not compare with each other.
    return [(0, part) if isinstance(part, int) else (1, str(part)) for part in error.absolute_path]


def _describe(error: ValidationError) -> str:
    """An error as a person can act on it, where it is.

    The CVE Record Format offers alternatives (anyOf/oneOf) for what an object must hold - an
    affected product names a vendor and a product, or a collection URL and a package name; a version
    range needs a version scheme - and jsonschema reports those by repeating the whole value. What
    each alternative still misses says it better.
    """
    where = "/".join(str(part) for part in error.absolute_path)
    message = error.message
    if error.validator in ("anyOf", "oneOf") and error.context:
        missing: dict[int, list[str]] = defaultdict(list)
        for alternative in error.context:
            if alternative.validator == "required" and alternative.relative_schema_path:
                index = alternative.relative_schema_path[0]
                missing[int(index)].extend(
                    name for name in alternative.validator_value if isinstance(name, str) and name not in (alternative.instance or {})
                )
        # Each alternative once, its names once; one that asks for more than another is left out.
        wanted = [list(dict.fromkeys(names)) for _, names in sorted(missing.items()) if names]
        options = [names for names in wanted if not any(set(other) < set(names) for other in wanted)]
        texts = list(dict.fromkeys(" and ".join(names) for names in options))
        message = f"add {', or '.join(texts)}" if texts else "does not match the CVE Record Format"
    return f"{where}: {message}" if where else message


def _first_error(validator: Validator, data: object) -> str | None:
    errors = sorted(validator.iter_errors(data), key=_path_key)
    return _describe(errors[0]) if errors else None


def parse_value(value: str | None) -> dict | None:
    """The object a structured value holds; None for an empty or malformed one."""
    if not value or not value.strip():
        return None
    try:
        data = json.loads(value)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def validate_value(attribute_type: str | None, value: str | None, validator_parameter: str | None = None) -> str | None:
    """Why a value of a structured attribute type cannot be stored; None when it can.

    An empty value (a row just added) is always fine.

    Args:
        attribute_type: The attribute type's name.
        value: The submitted value.
        validator_parameter: For JSON attributes, the CVE sub-schema to check against.

    Returns:
        str | None: The reason, or None.
    """
    if attribute_type not in STRUCTURED_TYPES or value is None or not value.strip():
        return None
    try:
        data = json.loads(value)
    except ValueError:
        return "The value is not valid JSON"
    if not isinstance(data, dict):
        return "The value must be a JSON object"
    if attribute_type == "RELATIONSHIP":
        return _first_error(Draft7Validator(_RELATIONSHIP_SCHEMA), data)
    if attribute_type in ("CREDIT", "TIMELINE"):
        # Records carry English only; the language is added when the record is built.
        data = {**data, "lang": gcve.CVD_LANGUAGE}
    if attribute_type == "TIMELINE":
        # The time is stored as the date-time field gives it, and written out in full in the record.
        moment = parse_moment(str(data.get("time") or ""))
        if moment is not None:
            data["time"] = timestamp(moment)
    if attribute_type == "JSON":
        pointer = _VALUE_POINTERS.get(validator_parameter or "")
        if pointer is None:
            return None
        return _first_error(_validator(pointer), data)
    return _first_error(_validator(_VALUE_POINTERS[attribute_type]), data)


def _versions_summary(versions: list) -> str:
    parts = []
    for version in versions or []:
        if not isinstance(version, dict):
            continue
        start = version.get("version") or ""
        if version.get("lessThan"):
            span = f"{start} to before {version['lessThan']}" if start not in ("", "0", "*") else f"before {version['lessThan']}"
        elif version.get("lessThanOrEqual"):
            span = f"{start} to {version['lessThanOrEqual']}" if start not in ("", "0", "*") else f"up to {version['lessThanOrEqual']}"
        else:
            span = start
        # Status changes within a range: "affected; unaffected from 1.2".
        changes = "".join(
            f"; {change.get('status') or 'unknown'} from {change.get('at', '')}"
            for change in version.get("changes") or []
            if isinstance(change, dict)
        )
        parts.append(f"{span} ({version.get('status', 'unknown')}{changes})".strip())
    return ", ".join(parts)


def summary(attribute_type: str, data: dict) -> str:
    """One readable line for a structured value, for whatever does not read its ``data``."""
    if attribute_type == "AFFECTED":
        name = " ".join(str(part) for part in (data.get("vendor"), data.get("product") or data.get("packageName")) if part)
        versions = _versions_summary(data.get("versions") or [])
        return f"{name}: {versions}" if versions else name
    if attribute_type == "CREDIT":
        return f"{data.get('value', '')} ({data['type']})" if data.get("type") else str(data.get("value", ""))
    if attribute_type == "TIMELINE":
        moment = parse_moment(str(data.get("time") or ""))
        when = moment.strftime("%Y-%m-%d %H:%M") if moment else str(data.get("time") or "")
        return f"{when}: {data.get('value', '')}"
    if attribute_type == "RELATIONSHIP":
        return f"{data.get('type', '')} {data.get('destId', '')}".strip()
    if attribute_type == "REFERENCE":
        return f"{data['name']} <{data.get('url', '')}>" if data.get("name") else str(data.get("url", ""))
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


# -- helpers ----------------------------------------------------------------------------------


def timestamp(moment: datetime | date | None) -> str | None:
    """A CVE Record Format timestamp: UTC, with milliseconds and ``Z``.

    A naive datetime is Taranis local time (``TZ``); a date is its midnight in UTC.
    """
    if moment is None:
        return None
    if not isinstance(moment, datetime):
        moment = datetime(moment.year, moment.month, moment.day, tzinfo=UTC)
    elif moment.tzinfo is None:
        moment = moment.replace(tzinfo=TZ)
    moment = moment.astimezone(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def parse_moment(value: str | None) -> datetime | None:
    """A date or date-time as the date and timeline fields store it; None when it is not one."""
    if not value or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    for parse in (datetime.fromisoformat, lambda raw: datetime.strptime(raw, "%d.%m.%Y")):  # noqa: DTZ007
        try:
            parsed = parse(text)
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def html_to_text(html: str | None) -> str:
    """The plain text of rich text: paragraphs and line breaks kept, other markup dropped."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")
    blocks = [block.get_text(" ", strip=True) for block in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre"])]
    text = "\n\n".join(block for block in blocks if block) if blocks else soup.get_text(" ", strip=True)
    return re.sub(r"[ \t]+", " ", text).strip()


def _description(html: str, index: ReferenceIndex, local: dict) -> dict | None:
    """A ``description`` object (plain text, the HTML as supporting media) with citations numbered."""
    rendered = index.render(html, local) or ""
    text = html_to_text(rendered)
    if not text:
        return None
    entry: dict[str, Any] = {"lang": gcve.CVD_LANGUAGE, "value": text}
    if "<" in rendered:
        entry["supportingMedia"] = [{"type": "text/html", "base64": False, "value": rendered}]
    return entry


def cvss_metric(vector: str) -> tuple[str, dict]:
    """The CVE Record Format metric of a CVSS vector: its property name and object.

    Raises:
        RecordProblemError: When the value is not a CVSS 2.0, 3.0, 3.1 or 4.0 vector.
    """
    vector = (vector or "").strip()
    try:
        if vector.startswith("CVSS:4.0/"):
            return "cvssV4_0", _cvss4(vector)
        if vector.startswith(("CVSS:3.1/", "CVSS:3.0/")):
            data = CVSS3(vector).as_json(minimal=True)
            data["baseSeverity"] = str(data["baseSeverity"]).upper()
            return ("cvssV3_1" if vector.startswith("CVSS:3.1/") else "cvssV3_0"), data
        if vector.startswith("AV:") and "Au:" in vector:
            return "cvssV2_0", CVSS2(vector).as_json(minimal=True)
    except Exception as error:  # the cvss library raises its own errors for a malformed vector
        msg = f"'{vector}' is not a valid CVSS vector: {error}"
        raise RecordProblemError(msg) from error
    msg = f"'{vector}' is not a CVSS vector (2.0, 3.0, 3.1 or 4.0); a bare score cannot be published"
    raise RecordProblemError(msg)


def _cvss4(vector: str) -> dict:
    """A CVSS 4.0 vector as the CVE Record Format writes it (FIRST property names)."""
    score = CVSS4(vector)
    data: dict[str, Any] = {"version": "4.0", "vectorString": vector}
    for part in vector.split("/")[1:]:
        metric, _, value = part.partition(":")
        name, values = _V4_VALUES.get(metric, (None, {}))
        if name and value in values:
            data[name] = values[value]
    data["baseScore"] = float(score.base_score or 0)
    data["baseSeverity"] = str(score.severity).upper()
    return data


def _cwe_id(value: str) -> str | None:
    match = CWE_NUMBER.match((value or "").strip())
    return f"CWE-{match.group(1)}" if match else None


def _position(attribute: ReportItemAttribute) -> tuple:
    group_item = attribute.attribute_group_item
    group = getattr(group_item, "attribute_group", None)
    return (getattr(group, "index", None) or 0, getattr(group_item, "index", None) or 0, attribute.id or 0)


def field_values(report_item: ReportItem) -> dict[str, list[ReportItemAttribute]]:
    """The values of each CVD field that hold something, by field key, in the order shown."""
    keys_by_title = {field.title: key for key, field in gcve.cvd_fields().items()}
    values: dict[str, list[ReportItemAttribute]] = defaultdict(list)
    for attribute in sorted(report_item.attributes, key=_position):
        group_item = attribute.attribute_group_item
        title = group_item.title if group_item is not None else attribute.attribute_group_item_title
        key = keys_by_title.get(title)
        if key is not None and attribute.value is not None and attribute.value.strip():
            values[key].append(attribute)
    return values


def _attribute_type(attribute: ReportItemAttribute) -> str | None:
    group_item = attribute.attribute_group_item
    if group_item is None or group_item.attribute is None or group_item.attribute.type is None:
        return None
    return group_item.attribute.type.name


def _references(values: dict[str, list[ReportItemAttribute]]) -> tuple[ReferenceIndex, dict, list[dict]]:
    """The references of a report: the citation index, its local numbers, and the record entries."""
    index = ReferenceIndex()
    local: dict[str, int] = {}
    entries: dict[str, dict] = {}
    for attribute in values.get("references", []):
        data = parse_value(attribute.value) or {}
        url = str(data.get("url") or "").strip()
        number = index.add(attribute.value_description, url)
        if number is None:
            continue
        if attribute.value_description:
            local.setdefault(attribute.value_description, number)
        if url not in entries:
            entry: dict[str, Any] = {"url": url}
            if data.get("name"):
                entry["name"] = data["name"]
            if data.get("tags"):
                entry["tags"] = list(dict.fromkeys(data["tags"]))
            entries[url] = entry
    return index, local, [entries[url] for url in index.urls]


# -- records ----------------------------------------------------------------------------------


class Fields:
    """The values of a CVD Report's fields, read the way a record needs them."""

    def __init__(self, report_item: ReportItem) -> None:
        """Read the report's values, and number its references for the citations in its texts."""
        self.values = field_values(report_item)
        self.index, self.local, self.references = _references(self.values)

    def get(self, key: str) -> list[ReportItemAttribute]:
        """The values of a field."""
        return self.values.get(key, [])

    def texts(self, key: str) -> list[dict]:
        """A rich-text field's values as record descriptions (plain text plus the HTML)."""
        return [entry for entry in (_description(attribute.value, self.index, self.local) for attribute in self.get(key)) if entry]

    def structured(self, key: str) -> list[dict]:
        """A structured field's values as objects."""
        return [data for data in (parse_value(attribute.value) for attribute in self.get(key)) if data]

    def first(self, key: str) -> str | None:
        """A single-valued field's value, trimmed; None when it has none."""
        found = self.get(key)
        return found[0].value.strip() if found else None


def _cpe_applicability(affected: list[dict]) -> list[dict]:
    """CPE applicability statements for the affected products that name CPE 2.3 strings."""
    nodes = []
    for product in affected:
        matches = [{"vulnerable": True, "criteria": cpe} for cpe in product.get("cpes") or [] if CPE23.match(cpe)]
        if matches:
            nodes.append({"operator": "OR", "negate": False, "cpeMatch": matches})
    return [{"nodes": nodes}] if nodes else []


def _problem_types(fields: Fields) -> list[dict]:
    problem_types = []
    for attribute in fields.get("cwe"):
        cwe_id = _cwe_id(attribute.value)
        if cwe_id is None:
            continue
        description = f"{cwe_id} {attribute.value_description}".strip() if attribute.value_description else cwe_id
        problem_types.append({"descriptions": [{"lang": gcve.CVD_LANGUAGE, "cweId": cwe_id, "description": description, "type": "CWE"}]})
    problem_types.extend(
        {"descriptions": [{"lang": gcve.CVD_LANGUAGE, "description": attribute.value.strip(), "type": "text"}]}
        for attribute in fields.get("problem_types")
    )
    return problem_types


def _impacts(fields: Fields) -> list[dict]:
    impacts = []
    for attribute in fields.get("impacts"):
        description = _description(attribute.value, fields.index, fields.local)
        if description is None:
            continue
        impact: dict[str, Any] = {"descriptions": [description]}
        capec = CAPEC_PREFIX.match(description["value"])
        if capec:
            impact["capecId"] = capec.group(1)
        impacts.append(impact)
    return impacts


def _metrics(fields: Fields) -> list[dict]:
    metrics = []
    for attribute in fields.get("cvss"):
        name, metric = cvss_metric(attribute.value)
        entry: dict[str, Any] = {"format": "CVSS", name: metric}
        if attribute.value_description and attribute.value_description.strip():
            entry["scenarios"] = [{"lang": gcve.CVD_LANGUAGE, "value": attribute.value_description.strip()}]
        metrics.append(entry)
    metrics.extend({"format": other.get("type") or "other", "other": other} for other in fields.structured("other_metrics"))
    return metrics


def _timeline(fields: Fields) -> list[dict]:
    timeline = []
    for event in fields.structured("timeline"):
        moment = parse_moment(str(event.get("time") or ""))
        if moment is not None and event.get("value"):
            timeline.append({"time": timestamp(moment), "lang": gcve.CVD_LANGUAGE, "value": event["value"]})
    return timeline


def _source(fields: Fields) -> dict:
    source: dict[str, Any] = {}
    discovery = fields.first("discovery")
    if discovery:
        source["discovery"] = discovery
    for key, name in (("defects", "defect"), ("advisories", "advisory")):
        found = [attribute.value.strip() for attribute in fields.get(key)]
        if found:
            source[name] = found
    return source


def x_gcve(fields: Fields, assignment: GcveAssignment) -> dict:
    """The GCVE extension (GCVE-BCP-05): the identifier, the record type, the relationships."""
    cve_id = fields.first("cve")
    relationships = [{"destId": cve_id, "type": "equal"}] if cve_id else []
    relationships.extend(fields.structured("related_records"))
    x_gcve: dict[str, Any] = {"vulnId": assignment.gcve_id, "recordType": fields.first("record_type") or gcve.DEFAULT_RECORD_TYPE}
    if relationships:
        x_gcve["relationships"] = relationships
    return x_gcve


def cna_content(report_item: ReportItem, fields: Fields | None = None) -> dict:
    """What a CVD Report says, as the CNA container of a record: title, descriptions, affected and the rest.

    Both records are built from it: the GCVE record (``build_record``) and the CVE record a CNA
    submits to CVE Services (``managers.cve_publication``); each adds its own provider metadata.

    Raises:
        RecordProblemError: When a CVSS value is not a vector.
    """
    fields = fields or Fields(report_item)
    cna: dict[str, Any] = {}
    date_public = parse_moment(fields.first("date_public"))
    if date_public is not None:
        cna["datePublic"] = timestamp(date_public)
    title = " ".join(part for part in (report_item.title_prefix, report_item.title) if part and part.strip()).strip()
    if title:
        cna["title"] = title
    cna["descriptions"] = fields.texts("description")
    cna["affected"] = fields.structured("affected_products")
    sections = {
        "cpeApplicability": _cpe_applicability(cna["affected"]),
        "problemTypes": _problem_types(fields),
        "references": fields.references,
        "impacts": _impacts(fields),
        "metrics": _metrics(fields),
        "configurations": fields.texts("configurations"),
        "workarounds": fields.texts("workarounds"),
        "solutions": fields.texts("solutions"),
        "exploits": fields.texts("exploits"),
        "timeline": _timeline(fields),
        "credits": [{"lang": gcve.CVD_LANGUAGE, **credit} for credit in fields.structured("credits") if credit.get("value")],
        "source": _source(fields),
        "tags": list(dict.fromkeys(tag for attribute in fields.get("tags") for tag in attribute.value.split("\n") if tag.strip())),
        "taxonomyMappings": fields.structured("taxonomy_mappings"),
    }
    # References are required, so they stay even when empty (and the record is then invalid).
    cna.update({name: section for name, section in sections.items() if section or name == "references"})
    return cna


def build_record(report_item: ReportItem, assignment: GcveAssignment, short_name: str | None = None) -> dict:
    """The GCVE record of a CVD Report.

    Args:
        report_item: The CVD Report.
        assignment: Its GCVE identifier.
        short_name: The GNA's short name, from the GCVE GNA directory (see model.organization_gna); left out when empty.

    Returns:
        dict: The record (CVE Record Format 5.2.0 with ``x_gcve``).

    Raises:
        RecordProblemError: When a CVSS value is not a vector.
    """
    fields = Fields(report_item)
    date_published = assignment.date_published or assignment.date_reserved
    date_updated = assignment.date_updated or date_published

    provider: dict[str, Any] = {"shortName": short_name} if short_name else {}
    provider["dateUpdated"] = timestamp(date_updated)
    cna: dict[str, Any] = {"providerMetadata": provider}
    cna["dateAssigned"] = timestamp(assignment.date_reserved)
    cna.update(cna_content(report_item, fields))
    cna["x_gcve"] = [x_gcve(fields, assignment)]

    metadata: dict[str, Any] = {}
    cve_id = fields.first("cve")
    if cve_id:
        metadata["cveId"] = cve_id
    metadata["state"] = "PUBLISHED"
    if short_name:
        metadata["assignerShortName"] = short_name
    metadata["dateReserved"] = timestamp(assignment.date_reserved)
    metadata["datePublished"] = timestamp(date_published)
    metadata["dateUpdated"] = timestamp(date_updated)

    return {"dataType": gcve.DATA_TYPE, "dataVersion": gcve.DATA_VERSION, "cveMetadata": metadata, "containers": {"cna": cna}}


def schema_errors(record: dict, limit: int = 3, pointer: str | None = None) -> list[str]:
    """What makes a record invalid against the (GCVE-relaxed) CVE Record Format, at most ``limit``.

    ``pointer`` checks a part of a record against its definition instead, e.g. a CNA container
    against ``definitions/cnaPublishedContainer``.
    """
    errors = sorted(_validator(pointer).iter_errors(record), key=_path_key)
    return [_describe(error) for error in errors[:limit]]


def content_problems(report_item: ReportItem, product_name: str) -> list[str]:
    """Why what a report says cannot be published as a record, GCVE or CVE; empty when it can.

    Args:
        report_item: The report to check.
        product_name: The product it is published in, for the message (a GCVE Advisory, a CVE Record).

    Returns:
        list[str]: The reasons, each naming the field.
    """
    report_type = report_item.report_item_type
    if report_type is None or report_type.system_key != gcve.CVD_TYPE_KEY:
        return [f"only CVD Reports can be published in a {product_name}"]
    found = []
    if (report_item.language or "") != gcve.CVD_LANGUAGE:
        found.append("a CVD Report must be written in English")

    values = field_values(report_item)
    fields = gcve.cvd_fields()
    for key, field in fields.items():
        count = len(values.get(key, []))
        if count < field.min_occurrence:
            found.append(f"{field.title}: required")
        elif count > field.max_occurrence:
            found.append(f"{field.title}: at most {field.max_occurrence}")
    for key, attributes in values.items():
        for attribute in attributes:
            attribute_type = _attribute_type(attribute)
            parameter = attribute.attribute_group_item.attribute.validator_parameter if attribute.attribute_group_item else None
            reason = validate_value(attribute_type, attribute.value, parameter)
            if reason is not None:
                found.append(f"{fields[key].title}: {reason}")
    return found


def problems(report_item: ReportItem, short_name: str | None = None) -> list[str]:
    """Why a report cannot be published as a GCVE record; empty when it can.

    Args:
        report_item: The report to check.
        short_name: The GNA's short name.

    Returns:
        list[str]: The reasons, each naming the field.
    """
    found = content_problems(report_item, gcve.GCVE_PRESET_NAME)
    if found and found[0].startswith("only CVD Reports"):
        return found
    assignment = report_item.gcve_assignment
    if assignment is None:
        return ["it has no GCVE identifier", *found]

    values = field_values(report_item)
    record_type = (values.get("record_type") or [None])[0]
    record_type_value = record_type.value.strip() if record_type is not None else gcve.DEFAULT_RECORD_TYPE
    if record_type_value not in gcve.OFFERED_RECORD_TYPES:
        found.append(f"Record type: '{record_type_value}' cannot be published")
    if record_type_value in gcve.RECORD_TYPES_NEEDING_RELATIONSHIPS and not values.get("related_records") and not values.get("cve"):
        found.append(f"Related records: a record of type '{record_type_value}' must relate to another record")

    if found:
        return found
    try:
        record = build_record(report_item, assignment, short_name)
    except RecordProblemError as error:
        return [f"CVSS: {error}"]
    return [f"record: {message}" for message in schema_errors(record)]


def records(report_items: Iterable[ReportItem], short_name: str | None = None) -> list[dict]:
    """The records of published CVD Reports, each once, skipping any that can no longer be built."""
    built = []
    seen: set[str] = set()
    for report_item in report_items:
        assignment = report_item.gcve_assignment
        if assignment is None or not assignment.published or assignment.gcve_id in seen:
            continue
        seen.add(assignment.gcve_id)
        try:
            built.append(build_record(report_item, assignment, short_name))
        except RecordProblemError as error:
            logger.warning(f"GCVE record {assignment.gcve_id} cannot be built: {error}")
    return built
