"""A published CVE record as the values of a CVD Report, to start a GCVE record from a CVE.

The reverse of ``gcve_publication.cna_content``: the CNA container of a record (as MITRE's CVE
Services publishes it, see ``cve_services.published_record``) becomes values of the CVD Report's
fields, in the form its editors store them - JSON with sorted keys for the structured fields, HTML
for the rich texts, ``287`` for a CWE, ``YYYY-MM-DD`` for a date. A report is then filled from
them, only where it holds nothing yet (``ReportItem.fill_cvd_fields`` for a saved one, the GUI for
one being created).

Where the CNA gives no CVSS, no CWE or no SSVC, CISA's ADP container (CVE "vulnrichment") gives
them, when it has them. What the record format derives on the way out is not taken back
(``cpeApplicability`` comes from the affected products' CPEs; the CVE ID's ``equal`` relationship
from the CVE field), nor anything a CVD Report has no field for (``x_`` extensions).

Every value is checked the way the field checks a typed one (``gcve_publication.validate_value``,
the CVSS vector parse); one that fails is left out and named in ``skipped``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC
from html import escape
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from managers import cve_services, gcve_publication
from shared.common import sanitize_content_html

from shared import gcve

if TYPE_CHECKING:
    from datetime import datetime

ENGLISH = "en"
CISA_ADP = "CISA-ADP"
# Vulnogram's placeholder scenario: it says nothing about the score.
DEFAULT_SCENARIO = "GENERAL"
CVSS_KEYS = ("cvssV4_0", "cvssV3_1", "cvssV3_0", "cvssV2_0")
SSVC = "ssvc"
# A title taken from the description is cut to this length.
TITLE_FROM_TEXT_LENGTH = 120
# The rich-text fields filled from lists of descriptions of the same name.
TEXT_SECTIONS = {"configurations": "configurations", "workarounds": "workarounds", "solutions": "solutions", "exploits": "exploits"}
CWE_LABEL = re.compile(r"^\s*CWE-[0-9]+\s*[:.,-]?\s*", re.IGNORECASE)
SAFE_HREF = re.compile(r"^(https?:|mailto:)", re.IGNORECASE)


class CveImportError(ValueError):
    """A CVE that cannot fill a report: the message says why."""


@dataclass
class ImportedValue:
    """One value of a field, as its editor stores it."""

    value: str
    value_description: str | None = None

    def to_json(self) -> dict:
        """What the GUI takes."""
        return {"value": self.value, "value_description": self.value_description}


@dataclass
class CvdImport:
    """What a CVE record fills a CVD Report with: its title, and values by field key."""

    cve_id: str
    title: str | None = None
    fields: dict[str, list[ImportedValue]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        """What the GUI takes."""
        return {
            "cve_id": self.cve_id,
            "title": self.title,
            "fields": {key: [value.to_json() for value in values] for key, values in self.fields.items()},
            "skipped": self.skipped,
        }


# -- values ----------------------------------------------------------------------------------


def _prune(value: object) -> object:
    """Drop what holds nothing, as the GUI's ``serializeStructured`` does (and sort the keys)."""
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, list):
        items = [item for item in (_prune(item) for item in value) if item is not None]
        return items or None
    if isinstance(value, dict):
        entries = {key: pruned for key in sorted(value) if (pruned := _prune(value[key])) is not None}
        return entries or None
    return value


def serialize(data: dict) -> str:
    """A structured value as the GUI stores it: JSON with sorted keys, empty parts left out."""
    pruned = _prune(data)
    return "" if pruned is None else json.dumps(pruned, ensure_ascii=False, separators=(",", ":"))


def _english(entries: object) -> list[dict]:
    """The English entries of a list of texts (``lang`` ``en`` or ``en-*``)."""
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict) and str(entry.get("lang") or "").lower().split("-")[0] == ENGLISH]


def _clean_html(html: str) -> str:
    """Third-party HTML made safe for the report: simplified tags, links only to the web or mail."""
    soup = BeautifulSoup(sanitize_content_html(html, ""), "html.parser")
    for link in soup.find_all("a"):
        if not SAFE_HREF.match(str(link.get("href") or "").strip()):
            link.unwrap()
    return str(soup).strip()


def _paragraphs(text: str) -> str:
    """Plain text as HTML paragraphs: blank lines part them, a single newline breaks a line."""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if block.strip()]
    return "".join("<p>" + "<br>".join(escape(line.strip()) for line in block.split("\n")) + "</p>" for block in blocks)


def rich_text(entry: dict) -> str | None:
    """A CVE text as rich text: its HTML (supporting media) when it has one, else its text."""
    for media in entry.get("supportingMedia") or []:
        if (
            isinstance(media, dict)
            and media.get("type") == "text/html"
            and not media.get("base64")
            and isinstance(media.get("value"), str)
            and media["value"].strip()
        ):
            html = _clean_html(media["value"])
            if gcve_publication.html_to_text(html):
                return html
    text = str(entry.get("value") or "").strip()
    return _paragraphs(text) or None


def _with_capec(html: str, capec_id: str | None) -> str:
    """An impact's text starting with its CAPEC ID, which is how the field names the pattern."""
    if not capec_id or gcve_publication.html_to_text(html).startswith(capec_id):
        return html
    if html.startswith("<p>"):
        return f"<p>{escape(capec_id)} {html[3:]}"
    return f"<p>{escape(capec_id)}</p>{html}"


def _moment(value: object) -> datetime | None:
    """A CVE timestamp, read as the date and timeline fields read theirs."""
    return gcve_publication.parse_moment(str(value or ""))


class _Collector:
    """Collects the values of each field, checked as the field checks them."""

    def __init__(self, cve_id: str) -> None:
        self.result = CvdImport(cve_id)
        self.fields = gcve.cvd_fields()
        self.types = {attribute.name: attribute for attribute in gcve.CVD_ATTRIBUTES}

    def _attribute_type(self, key: str) -> tuple[str, str | None]:
        cvd_field = self.fields[key]
        attribute = self.types.get(cvd_field.attribute)
        if attribute is None:  # a generic attribute: its type is its name
            return cvd_field.attribute, None
        return attribute.type, attribute.validator_parameter

    def add(self, key: str, value: str | None, description: str | None = None) -> None:
        """Add a value to a field, unless it is empty, invalid, repeated or one too many."""
        if value is None or not value.strip():
            return
        cvd_field = self.fields[key]
        values = self.result.fields.setdefault(key, [])
        if any(existing.value == value for existing in values):
            return
        if len(values) >= cvd_field.max_occurrence:
            self.result.skipped.append(f"{cvd_field.title}: only {cvd_field.max_occurrence} taken")
            return
        attribute_type, parameter = self._attribute_type(key)
        reason = gcve_publication.validate_value(attribute_type, value, parameter)
        if reason is None and attribute_type == "CVSS":
            try:
                gcve_publication.cvss_metric(value)
            except gcve_publication.RecordProblemError as error:
                reason = str(error)
        if reason is not None:
            self.result.skipped.append(f"{cvd_field.title}: {reason}")
            return
        values.append(ImportedValue(value, description.strip() if description and description.strip() else None))

    def add_structured(self, key: str, data: object) -> None:
        if isinstance(data, dict):
            self.add(key, serialize(data))

    def has(self, key: str) -> bool:
        return bool(self.result.fields.get(key))


def _cvss(collector: _Collector, metrics: object) -> None:
    for metric in metrics if isinstance(metrics, list) else []:
        if not isinstance(metric, dict):
            continue
        scenarios = [str(entry.get("value") or "").strip() for entry in _english(metric.get("scenarios"))]
        scenario = next((text for text in scenarios if text and text.upper() != DEFAULT_SCENARIO), None)
        for key in CVSS_KEYS:
            score = metric.get(key)
            if isinstance(score, dict) and isinstance(score.get("vectorString"), str):
                collector.add("cvss", score["vectorString"].strip(), scenario)


def _other_metrics(collector: _Collector, metrics: object, *, only: str | None = None) -> None:
    for metric in metrics if isinstance(metrics, list) else []:
        other = metric.get("other") if isinstance(metric, dict) else None
        if isinstance(other, dict) and (only is None or str(other.get("type") or "").lower() == only):
            collector.add_structured("other_metrics", other)


def _has_ssvc(collector: _Collector) -> bool:
    return any(
        str((gcve_publication.parse_value(value.value) or {}).get("type") or "").lower() == SSVC
        for value in collector.result.fields.get("other_metrics", [])
    )


def _cwes(collector: _Collector, problem_types: object, *, texts: bool) -> None:
    for problem_type in problem_types if isinstance(problem_types, list) else []:
        if not isinstance(problem_type, dict):
            continue
        for description in _english(problem_type.get("descriptions")):
            match = gcve_publication.CWE_NUMBER.match(str(description.get("cweId") or "").strip())
            text = str(description.get("description") or "").strip()
            if match:
                collector.add("cwe", match.group(1), CWE_LABEL.sub("", text))
            elif texts and text:
                collector.add("problem_types", text)


def _title(cna: dict, descriptions: list[dict]) -> str | None:
    """The record's title; for a record without one (many CNAs give none), its description's first sentence."""
    title = str(cna.get("title") or "").strip()
    if not title and descriptions:
        text = " ".join(str(descriptions[0].get("value") or "").split())
        title = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        if len(title) > TITLE_FROM_TEXT_LENGTH:
            title = title[:TITLE_FROM_TEXT_LENGTH].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return title[: gcve.TITLE_MAX_LENGTH] or None


def _cisa_adp(record: dict) -> dict:
    """CISA's ADP container of the record; empty when it has none."""
    adps = (record.get("containers") or {}).get("adp")
    for adp in adps if isinstance(adps, list) else []:
        if isinstance(adp, dict) and (adp.get("providerMetadata") or {}).get("shortName") == CISA_ADP:
            return adp
    return {}


def cvd_values(record: dict, cve_id: str | None = None) -> CvdImport:
    """The values a published CVE record fills a CVD Report with.

    Args:
        record: The CVE record (CVE Record Format 5.x).
        cve_id: The ID asked for; the record must be its.

    Raises:
        CveImportError: When the record is rejected, or is another CVE's.
    """
    metadata = record.get("cveMetadata") or {}
    record_id = str(metadata.get("cveId") or "").strip().upper()
    if cve_id is not None and record_id != cve_id:
        msg = f"CVE Services answered with the record of {record_id or 'another CVE'} for {cve_id}"
        raise CveImportError(msg)
    if str(metadata.get("state") or "").upper() == "REJECTED":
        msg = f"{record_id} is rejected: it has nothing to fill a report with"
        raise CveImportError(msg)
    cna = (record.get("containers") or {}).get("cna") or {}
    collector = _Collector(record_id)
    result = collector.result

    collector.add("cve", record_id)
    descriptions = _english(cna.get("descriptions"))[:1]
    for entry in descriptions:
        collector.add("description", rich_text(entry))
    result.title = _title(cna, descriptions)
    for key, section in TEXT_SECTIONS.items():
        for entry in _english(cna.get(section)):
            collector.add(key, rich_text(entry))
    for impact in cna.get("impacts") or []:
        if isinstance(impact, dict):
            for entry in _english(impact.get("descriptions"))[:1]:
                html = rich_text(entry)
                collector.add("impacts", _with_capec(html, impact.get("capecId")) if html else None)

    for product in cna.get("affected") or []:
        collector.add_structured("affected_products", product)
    for reference in cna.get("references") or []:
        if isinstance(reference, dict) and reference.get("url"):
            tags = [tag for tag in reference.get("tags") or [] if tag in gcve.REFERENCE_TAGS]
            collector.add_structured("references", {"url": reference["url"], "name": reference.get("name"), "tags": tags})

    _cvss(collector, cna.get("metrics"))
    _other_metrics(collector, cna.get("metrics"))
    _cwes(collector, cna.get("problemTypes"), texts=True)
    adp = _cisa_adp(record)
    if adp:
        if not collector.has("cvss"):
            _cvss(collector, adp.get("metrics"))
        if not _has_ssvc(collector):
            _other_metrics(collector, adp.get("metrics"), only=SSVC)
        if not collector.has("cwe"):
            _cwes(collector, adp.get("problemTypes"), texts=False)

    for mapping in cna.get("taxonomyMappings") or []:
        collector.add_structured("taxonomy_mappings", mapping)
    date_public = _moment(cna.get("datePublic"))
    if date_public is not None:
        collector.add("date_public", date_public.astimezone(UTC).date().isoformat())

    source = cna.get("source") if isinstance(cna.get("source"), dict) else {}
    if source.get("discovery") in gcve.DISCOVERY_VALUES:
        collector.add("discovery", source["discovery"])
    for key, name in (("defects", "defect"), ("advisories", "advisory")):
        for item in source.get(name) or []:
            if isinstance(item, str):
                collector.add(key, item.strip())
    tags = [tag for tag in gcve.CNA_TAGS if tag in (cna.get("tags") or [])]
    collector.add("tags", "\n".join(tags))

    for event in _english(cna.get("timeline")):
        moment = _moment(event.get("time"))
        if moment is not None:
            collector.add_structured("timeline", {"time": moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M"), "value": event.get("value")})
    for credit in _english(cna.get("credits")):
        credit_type = credit.get("type") if credit.get("type") in gcve.CREDIT_TYPES else None
        collector.add_structured("credits", {"value": credit.get("value"), "type": credit_type, "user": credit.get("user")})

    result.fields = {key: values for key, values in result.fields.items() if values}
    return result


def fetch(cve_id: str) -> CvdImport:
    """The values the published record of ``cve_id`` fills a CVD Report with.

    Raises:
        CveImportError: When it is not a CVE ID, or its record cannot fill a report.
        cve_services.CveServicesError: When CVE Services cannot be asked, or has no published record of it.
    """
    wanted = (cve_id or "").strip().upper()
    if not gcve.CVE_ID_PATTERN.match(wanted):
        msg = f"'{(cve_id or '').strip()}' is not a CVE ID (CVE-YYYY-NNNN)"
        raise CveImportError(msg)
    return cvd_values(cve_services.published_record(wanted), wanted)
